"""
TDD tests for Plan 19-03 Task 1:
EvaluationOrchestrator.run() accepts and propagates brief_type parameter.
"""

import inspect
import pytest
from unittest.mock import MagicMock, patch
from app.services.evaluation_orchestrator import EvaluationOrchestrator
from app.models.campaign import BriefType
from app.services.brief_weights import WEIGHT_PROFILE_VERSIONS


class TestOrchestratorBriefTypeSignature:
    """brief_type 参数存在于 run() 签名中"""

    def test_run_has_brief_type_param(self):
        sig = inspect.signature(EvaluationOrchestrator.run)
        assert 'brief_type' in sig.parameters, "run() should have brief_type parameter"

    def test_brief_type_defaults_to_none(self):
        sig = inspect.signature(EvaluationOrchestrator.run)
        param = sig.parameters['brief_type']
        assert param.default is None, "brief_type should default to None"


class TestOrchestratorBriefTypeIntegration:
    """brief_type 正确传导到 CampaignScorer 和 EvaluationResult"""

    def _make_orchestrator(self):
        task_manager = MagicMock()
        task_manager.update_task = MagicMock()
        task_manager.complete_task = MagicMock()
        task_manager.fail_task = MagicMock()

        evaluation_store = {}
        save_fn = MagicMock()

        return EvaluationOrchestrator(
            task_manager=task_manager,
            evaluation_store=evaluation_store,
            save_result_fn=save_fn,
        )

    def _make_campaign_set(self):
        campaign_set = MagicMock()
        campaign_set.set_id = "test_set_001"
        campaign_set.campaigns = [MagicMock(), MagicMock()]
        return campaign_set

    @patch('app.services.evaluation_orchestrator.CampaignScorer')
    @patch('app.services.evaluation_orchestrator.AudiencePanel')
    @patch('app.services.evaluation_orchestrator.MultiJudgeEnsemble')
    @patch('app.services.evaluation_orchestrator.SummaryGenerator')
    @patch('app.services.evaluation_orchestrator.LLMClient')
    def test_brief_type_passed_to_scorer(self, mock_llm, mock_summary, mock_judge, mock_panel, mock_scorer):
        """brief_type=BriefType.BRAND 时 CampaignScorer 以 brief_type=BriefType.BRAND 实例化"""
        orchestrator = self._make_orchestrator()
        campaign_set = self._make_campaign_set()

        # Setup mocks
        panel_instance = MagicMock()
        panel_scores = [MagicMock(persona_id='p1', campaign_id='c1', score=0.8)]
        panel_instance.evaluate_all.return_value = panel_scores
        mock_panel.return_value = panel_instance

        judge_instance = MagicMock()
        judge_instance.evaluate_all.return_value = ([MagicMock()], {})
        mock_judge.return_value = judge_instance

        scorer_instance = MagicMock()
        mock_campaign = MagicMock()
        mock_campaign.campaign_id = 'c1'
        mock_campaign.overall_score = 0.9
        mock_campaign.campaign_name = 'Test Campaign'
        mock_campaign.verdict = 'ship'
        scoreboard_mock = MagicMock()
        scoreboard_mock.campaigns = [mock_campaign]
        scoreboard_mock.too_close_to_call = False
        scoreboard_mock.lead_margin = 0.1
        scoreboard_mock.to_dict.return_value = {}
        scorer_instance.score.return_value = ([], scoreboard_mock)
        mock_scorer.return_value = scorer_instance

        summary_instance = MagicMock()
        summary_instance.generate.return_value = {'summary': '', 'assumptions': [], 'confidence_notes': []}
        mock_summary.return_value = summary_instance

        # ConsensusAgent is lazy-imported inside run(), so patch at the module level
        with patch('app.services.consensus_agent.ConsensusAgent') as mock_consensus_cls, \
             patch('app.services.evaluation_orchestrator.ResolutionTracker'), \
             patch('app.services.evaluation_orchestrator.JudgeCalibration') as mock_cal, \
             patch('app.services.evaluation_orchestrator.ImageAnalyzer'), \
             patch('app.services.evaluation_orchestrator.Config') as mock_cfg:
            mock_cfg.USE_MARKET_JUDGE = False
            cal_instance = MagicMock()
            cal_instance.get_weights.return_value = (None, None)
            mock_cal.return_value = cal_instance
            orchestrator.calibration = cal_instance

            consensus_instance = MagicMock()
            consensus_instance.detect.return_value = panel_scores
            mock_consensus_cls.return_value = consensus_instance

            # Patch the lazy import path
            import app.services.evaluation_orchestrator as orch_module
            orig_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else None

            orchestrator.run('task_001', campaign_set, brief_type=BriefType.BRAND)

        # Verify CampaignScorer was called with brief_type=BriefType.BRAND
        mock_scorer.assert_called_once()
        call_kwargs = mock_scorer.call_args.kwargs
        assert call_kwargs.get('brief_type') == BriefType.BRAND, \
            f"CampaignScorer should be called with brief_type=BriefType.BRAND, got {call_kwargs}"

    def test_weight_profile_versions_has_brand(self):
        """WEIGHT_PROFILE_VERSIONS 包含 brand 键，值为 brand-v1"""
        assert 'brand' in WEIGHT_PROFILE_VERSIONS
        assert WEIGHT_PROFILE_VERSIONS['brand'] == 'brand-v1'

    def test_weight_profile_versions_has_all_types(self):
        """WEIGHT_PROFILE_VERSIONS 包含全部三种 brief_type"""
        for bt in ('brand', 'seeding', 'conversion'):
            assert bt in WEIGHT_PROFILE_VERSIONS, f"Missing {bt} in WEIGHT_PROFILE_VERSIONS"
