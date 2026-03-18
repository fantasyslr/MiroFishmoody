"""
Benchmark Regression Runner

CLI 入口：读取 benchmark fixture 文件，通过 MockLLMClient 确定性回放，
输出各 brief_type 的命中率报告。

用法：
    cd backend
    uv run python benchmark/run.py
    uv run python benchmark/run.py "tests/fixtures/benchmark/*.json"
"""

import glob
import json
import sys
import os
from collections import defaultdict
from typing import Dict
from unittest.mock import patch

# 将 backend 目录加入 path，使相对 import 可用
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.models.campaign import Campaign, CampaignSet, BriefType, ProductLine
from app.services.evaluation_orchestrator import EvaluationOrchestrator
from benchmark.mock_llm_client import MockLLMClient


# ------------------------------------------------------------------ #
#  In-memory TaskManager (no SQLite, no side effects)
# ------------------------------------------------------------------ #

class _InMemoryTaskManager:
    """最小 TaskManager 实现，仅用于 benchmark runner。不写 SQLite。"""

    def __init__(self):
        self._tasks: Dict[str, dict] = {}

    def create_task(self, task_type: str = "benchmark", metadata=None):
        """兼容 TaskManager.create_task 签名，返回 task_id 字符串。"""
        import uuid
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "",
            "result": None,
            "error": None,
        }
        return task_id

    def update_task(self, task_id: str, status=None, progress=None, message=None,
                    result=None, error=None, progress_detail=None):
        if task_id not in self._tasks:
            self._tasks[task_id] = {"status": "pending", "progress": 0}
        t = self._tasks[task_id]
        if status is not None:
            t["status"] = status.value if hasattr(status, "value") else status
        if progress is not None:
            t["progress"] = progress
        if message is not None:
            t["message"] = message
        if result is not None:
            t["result"] = result
        if error is not None:
            t["error"] = error

    def get_task(self, task_id: str):
        return self._tasks.get(task_id)

    def complete_task(self, task_id: str, result: dict):
        self.update_task(task_id, status="completed", progress=100,
                         message="任务完成", result=result)

    def fail_task(self, task_id: str, error: str):
        self.update_task(task_id, status="failed", message="任务失败", error=error)


# ------------------------------------------------------------------ #
#  Fixture loading
# ------------------------------------------------------------------ #

def _load_fixture(path: str):
    """从 JSON fixture 文件加载数据，返回 (raw_data, CampaignSet)。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    campaigns = []
    for c in data["campaigns"]:
        pl_raw = c.get("product_line", "colored_lenses")
        try:
            pl = ProductLine(pl_raw)
        except ValueError:
            pl = ProductLine.COLORED

        campaigns.append(Campaign(
            id=c["id"],
            name=c["name"],
            product_line=pl,
            target_audience=c.get("target_audience", ""),
            core_message=c.get("core_message", ""),
            channels=c.get("channels", []),
            creative_direction=c.get("creative_direction", ""),
            budget_range=c.get("budget_range"),
            kv_description=c.get("kv_description"),
            promo_mechanic=c.get("promo_mechanic"),
        ))

    campaign_set = CampaignSet(set_id=data["id"], campaigns=campaigns)
    return data, campaign_set


# ------------------------------------------------------------------ #
#  Accuracy calculation (exported for testing)
# ------------------------------------------------------------------ #

def calculate_accuracy(hits: Dict[str, int], totals: Dict[str, int]) -> Dict[str, float]:
    """计算每种 brief_type 的命中率。

    Args:
        hits:   brief_type -> 命中数
        totals: brief_type -> 总样本数

    Returns:
        brief_type -> accuracy (float, 0.0-1.0)
    """
    result = {}
    for bt, total in totals.items():
        if total == 0:
            result[bt] = 0.0
        else:
            result[bt] = hits.get(bt, 0) / total
    return result


# ------------------------------------------------------------------ #
#  Main runner
# ------------------------------------------------------------------ #

def run_benchmark(fixture_glob: str = None) -> Dict[str, float]:
    """运行 benchmark 回归，返回各 brief_type 命中率。

    Args:
        fixture_glob: fixture 文件 glob 模式，默认读取
                      tests/fixtures/benchmark/*.json

    Returns:
        {"brand": float, "seeding": float, "conversion": float, "overall": float}
    """
    if fixture_glob is None:
        # 相对于 backend/ 目录的路径
        fixture_glob = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests", "fixtures", "benchmark", "*.json"
        )

    files = sorted(glob.glob(fixture_glob))
    if not files:
        print(f"[WARNING] No fixture files found at: {fixture_glob}", file=sys.stderr)
        return {}

    task_manager = _InMemoryTaskManager()
    evaluation_store: Dict = {}

    def _noop_save(set_id, result_dict):
        pass  # benchmark runner 不持久化评审结果

    orchestrator = EvaluationOrchestrator(
        task_manager=task_manager,
        evaluation_store=evaluation_store,
        save_result_fn=_noop_save,
    )

    hits: Dict[str, int] = defaultdict(int)
    totals: Dict[str, int] = defaultdict(int)

    for fixture_path in files:
        data, campaign_set = _load_fixture(fixture_path)
        brief_type_str = data.get("brief_type", "")
        try:
            brief_type_enum = BriefType(brief_type_str)
        except ValueError:
            print(f"[SKIP] Unknown brief_type '{brief_type_str}' in {fixture_path}",
                  file=sys.stderr)
            continue

        # category 使用第一个 campaign 的 product_line 值
        category = data["campaigns"][0].get("product_line", "colored_lenses")

        # 在 orchestrator.run() 调用期间，将真实 LLMClient 替换为 MockLLMClient
        # patch 目标是 evaluation_orchestrator 模块中 import 的 LLMClient 名称
        with patch(
            "app.services.evaluation_orchestrator.LLMClient",
            MockLLMClient
        ):
            orchestrator.run(
                campaign_set.set_id,
                campaign_set,
                category=category,
                brief_type=brief_type_enum,
            )

        # 从 evaluation_store 读取结果（orchestrator.run() 没有 return）
        result_dict = evaluation_store.get(campaign_set.set_id)
        if result_dict is None:
            # 任务可能失败，尝试从 task_manager 获取错误信息
            task_info = task_manager.get_task(campaign_set.set_id)
            err = task_info.get("error") if task_info else "unknown error"
            print(f"[ERROR] {os.path.basename(fixture_path)}: {err}", file=sys.stderr)
            totals[brief_type_str] += 1
            continue

        rankings = result_dict.get("rankings", [])
        if not rankings:
            print(f"[ERROR] {os.path.basename(fixture_path)}: empty rankings",
                  file=sys.stderr)
            totals[brief_type_str] += 1
            continue

        predicted_winner = rankings[0]["campaign_id"]
        expected_winner = data["expected_winner_id"]

        totals[brief_type_str] += 1
        if predicted_winner == expected_winner:
            hits[brief_type_str] += 1

    # 计算命中率
    accuracy = calculate_accuracy(dict(hits), dict(totals))

    # 打印报告
    print("=== Benchmark Regression Report ===")
    BRIEF_ORDER = ["brand", "seeding", "conversion"]
    total_hits = 0
    total_count = 0
    for bt in BRIEF_ORDER:
        if bt in totals:
            h = hits.get(bt, 0)
            t = totals[bt]
            acc = accuracy.get(bt, 0.0)
            print(f"{bt:<12}{h}/{t}  accuracy={acc:.2f}")
            total_hits += h
            total_count += t
    # Also print any brief_types not in BRIEF_ORDER
    for bt in sorted(totals.keys()):
        if bt not in BRIEF_ORDER:
            h = hits.get(bt, 0)
            t = totals[bt]
            acc = accuracy.get(bt, 0.0)
            print(f"{bt:<12}{h}/{t}  accuracy={acc:.2f}")
            total_hits += h
            total_count += t

    print("---")
    overall = total_hits / total_count if total_count > 0 else 0.0
    print(f"{'overall':<12}{total_hits}/{total_count}  accuracy={overall:.2f}")

    accuracy["overall"] = overall
    return accuracy


# ------------------------------------------------------------------ #
#  CLI entry point
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    fixture_dir = sys.argv[1] if len(sys.argv) > 1 else None
    run_benchmark(fixture_dir)
