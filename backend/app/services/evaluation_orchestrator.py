"""
EvaluationOrchestrator — 评审流程编排器
"""

from collections import defaultdict
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..services.audience_panel import AudiencePanel
from ..config import Config
from ..services.pairwise_judge import PairwiseJudge
from ..services.campaign_scorer import CampaignScorer
from ..services.summary_generator import SummaryGenerator
from ..services.judge_calibration import JudgeCalibration
from ..services.resolution_tracker import ResolutionTracker
from ..models.evaluation import EvaluationResult
from ..services.image_analyzer import ImageAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger('ranker.services.orchestrator')


class EvaluationOrchestrator:
    """评审流程编排器 - 协调 Panel、Pairwise、Scoring、Summary 各阶段"""

    def __init__(self, task_manager: TaskManager, evaluation_store: dict, save_result_fn, store_lock=None):
        self.task_manager = task_manager
        self.evaluation_store = evaluation_store
        self.save_result_fn = save_result_fn
        self.store_lock = store_lock
        self.calibration = JudgeCalibration()  # 只实例化一次

    def run(self, task_id: str, campaign_set, category: str = None) -> dict:
        """Execute the full evaluation pipeline"""
        try:
            self.task_manager.update_task(
                task_id, status=TaskStatus.PROCESSING,
                progress=5, message="初始化评审引擎..."
            )

            llm = LLMClient()
            campaigns = campaign_set.campaigns

            # 加载校准权重
            judge_weights, persona_weights = self.calibration.get_weights()

            # Phase 1: Audience Panel
            self.task_manager.update_task(task_id, progress=10, message="Audience Panel 评审中...")
            panel = AudiencePanel(llm_client=llm, category=category)
            panel_scores = panel.evaluate_all(campaigns)

            # ConsensusAgent: detect outlier persona scores, mark suspect=True
            from ..services.consensus_agent import ConsensusAgent
            consensus = ConsensusAgent()
            panel_scores = consensus.detect(panel_scores)

            if not panel_scores:
                raise RuntimeError(
                    "Audience Panel 评审全部失败（0 个 persona 返回有效结果），"
                    "请检查 LLM API 配置和网络连接"
                )
            self.task_manager.update_task(task_id, progress=40, message="Panel 评审完成")

            # Phase 1.5: Image Analysis (parallel with panel scoring output)
            visual_diagnostics = {}
            campaigns_with_images = [c for c in campaigns if c.image_paths]
            if campaigns_with_images:
                self.task_manager.update_task(task_id, progress=42, message="素材图片诊断中...")
                try:
                    analyzer = ImageAnalyzer(llm_client=llm)

                    def _analyze_campaign(campaign):
                        profile = analyzer.analyze_plan_images(campaign.image_paths)
                        if profile and profile.get("diagnostics"):
                            return campaign.id, profile["diagnostics"]
                        return campaign.id, None

                    with ThreadPoolExecutor(max_workers=len(campaigns_with_images)) as executor:
                        futures = {
                            executor.submit(_analyze_campaign, c): c
                            for c in campaigns_with_images
                        }
                        for future in as_completed(futures):
                            try:
                                cid, diag = future.result()
                                if diag:
                                    visual_diagnostics[cid] = diag
                            except Exception as e:
                                logger.error(f"Campaign 图片诊断失败: {e}")
                except Exception as e:
                    logger.error(f"图片诊断服务异常，跳过: {e}")

            # Phase 2: Pairwise Judge
            self.task_manager.update_task(task_id, progress=45, message="Pairwise 对决中...")
            if Config.USE_MARKET_JUDGE:
                from ..services.market_judge import MarketJudge
                judge = MarketJudge(llm_client=llm)
                logger.info("使用 Market-Making Judge 模式")
            else:
                judge = PairwiseJudge(llm_client=llm)
            pairwise_results, bt_scores = judge.evaluate_all(campaigns)
            if not pairwise_results:
                raise RuntimeError(
                    "Pairwise 对决全部失败（0 个对决返回有效结果），"
                    "请检查 LLM API 配置和网络连接"
                )
            self.task_manager.update_task(task_id, progress=80, message="对决完成")

            # Phase 3: Scoring
            self.task_manager.update_task(task_id, progress=85, message="Scoring...")
            scorer = CampaignScorer(
                judge_weights=judge_weights,
                persona_weights=persona_weights,
            )
            rankings, scoreboard = scorer.score(
                campaigns, panel_scores, pairwise_results, bt_scores,
            )

            # Phase 5.1: 持久化 per-persona / per-judge 预测
            overall_scores = {c.campaign_id: c.overall_score for c in scoreboard.campaigns}
            self.calibration.save_predictions(
                set_id=campaign_set.set_id,
                persona_predictions=self._build_persona_predictions(panel_scores, campaigns),
                judge_predictions=self._build_judge_predictions(pairwise_results),
                campaign_win_probabilities=overall_scores,
            )

            # Phase 4: Summary
            self.task_manager.update_task(task_id, progress=90, message="生成总结报告...")
            summarizer = SummaryGenerator(llm_client=llm)
            summary_data = summarizer.generate(
                campaigns, rankings, panel_scores, pairwise_results,
            )

            # Resolution tracker
            resolver = ResolutionTracker()

            # 构建最终结果
            result = EvaluationResult(
                set_id=campaign_set.set_id,
                rankings=rankings,
                panel_scores=panel_scores,
                pairwise_results=pairwise_results,
                summary=summary_data["summary"],
                assumptions=summary_data["assumptions"],
                confidence_notes=summary_data["confidence_notes"],
                scoreboard=scoreboard.to_dict(),
                resolution_ready_fields=resolver.get_resolution_ready_fields(),
                visual_diagnostics=visual_diagnostics if visual_diagnostics else None,
            )

            result_dict = result.to_dict()
            if self.store_lock:
                with self.store_lock:
                    self.evaluation_store[campaign_set.set_id] = result_dict
            else:
                self.evaluation_store[campaign_set.set_id] = result_dict
            self.save_result_fn(campaign_set.set_id, result_dict)

            top = scoreboard.campaigns[0] if scoreboard.campaigns else None
            self.task_manager.complete_task(task_id, result={
                "set_id": campaign_set.set_id,
                "campaign_count": len(campaigns),
                "top_campaign": top.campaign_name if top else None,
                "top_verdict": top.verdict if top else None,
                "top_overall_score": round(top.overall_score, 3) if top else None,
                "too_close_to_call": scoreboard.too_close_to_call,
                "lead_margin": round(scoreboard.lead_margin, 3),
            })

        except Exception as e:
            logger.error(f"评审失败: {e}", exc_info=True)
            self.task_manager.fail_task(task_id, str(e))

    @staticmethod
    def _build_persona_predictions(panel_scores, campaigns):
        """
        从 panel_scores 构建 per-persona prediction records。
        每个 persona 对各 campaign 的 score 归一化为 preference (sum=1 per persona)。
        """
        # 按 persona 分组
        by_persona = defaultdict(list)
        for ps in panel_scores:
            by_persona[ps.persona_id].append(ps)

        records = []
        for persona_id, scores in by_persona.items():
            total = sum(s.score for s in scores)
            for s in scores:
                preference = s.score / total if total > 0 else 1.0 / len(scores)
                records.append({
                    "persona_id": s.persona_id,
                    "campaign_id": s.campaign_id,
                    "score": s.score,
                    "preference": round(preference, 4),
                })
        return records

    @staticmethod
    def _build_judge_predictions(pairwise_results):
        """
        从 pairwise_results 的 votes 构建 per-judge prediction records。
        """
        records = []
        for pr in pairwise_results:
            for vote in pr.votes:
                records.append({
                    "judge_id": vote.get("judge_id", ""),
                    "campaign_a_id": pr.campaign_a_id,
                    "campaign_b_id": pr.campaign_b_id,
                    "winner_pick": vote.get("winner", "tie"),
                    "dimensions": vote.get("dimensions", {}),
                })
        return records
