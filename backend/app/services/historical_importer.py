"""
Historical Importer — 导入历史 intervention / outcome / signal 数据

支持 JSON 和 CSV 格式。允许稀疏数据 — 缺失字段自动填 None。
自动生成缺失的 ID 字段。
"""

import csv
import io
import json
import uuid
from typing import List, Dict, Any, Tuple  # noqa: F401 — Tuple used in _coerce_numeric

from ..models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
    CompetitorEvent,
    EvidenceArtifact,
)
from .brandiction_store import BrandictionStore


class ImportResult:
    """导入结果汇总"""

    def __init__(self):
        self.interventions: int = 0
        self.outcomes: int = 0
        self.signals: int = 0
        self.competitor_events: int = 0
        self.evidence: int = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "imported": {
                "interventions": self.interventions,
                "outcomes": self.outcomes,
                "signals": self.signals,
                "competitor_events": self.competitor_events,
                "evidence": self.evidence,
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


class HistoricalImporter:
    """导入历史数据到 BrandictionStore"""

    def __init__(self, store: BrandictionStore = None):
        self.store = store or BrandictionStore()

    def import_json(self, data: Dict[str, Any]) -> ImportResult:
        """
        导入 JSON 格式数据。

        Expected structure:
        {
          "interventions": [...],
          "outcomes": [...],
          "signals": [...],
          "competitor_events": [...],
          "evidence": [...]
        }

        所有顶层 key 都是可选的。
        """
        result = ImportResult()

        for item in data.get("interventions", []):
            try:
                item = self._ensure_id(item, "intervention_id")
                if "run_id" not in item or not item["run_id"]:
                    item["run_id"] = item["intervention_id"]
                item = self._coerce_numeric(
                    item, self._INTERVENTION_NUMERIC, result.warnings, "intervention",
                )
                iv = HistoricalIntervention.from_dict(item)
                self.store.save_intervention(iv)
                result.interventions += 1
            except Exception as e:
                result.errors.append(f"intervention: {e} — data: {_truncate(item)}")

        for item in data.get("outcomes", []):
            try:
                item = self._ensure_id(item, "outcome_id")
                if "intervention_id" not in item or not item["intervention_id"]:
                    result.errors.append(f"outcome missing intervention_id: {_truncate(item)}")
                    continue
                item = self._coerce_numeric(
                    item, self._OUTCOME_NUMERIC, result.warnings, "outcome",
                )
                oc = HistoricalOutcomeWindow.from_dict(item)
                self.store.save_outcome(oc)
                result.outcomes += 1
            except Exception as e:
                result.errors.append(f"outcome: {e} — data: {_truncate(item)}")

        for item in data.get("signals", []):
            try:
                item = self._ensure_id(item, "signal_id")
                if "date" not in item or not item["date"]:
                    result.errors.append(f"signal missing date: {_truncate(item)}")
                    continue
                item = self._coerce_numeric(
                    item, self._SIGNAL_NUMERIC, result.warnings, "signal",
                )
                sig = BrandSignalSnapshot.from_dict(item)
                self.store.save_signal(sig)
                result.signals += 1
            except Exception as e:
                result.errors.append(f"signal: {e} — data: {_truncate(item)}")

        for item in data.get("competitor_events", []):
            try:
                item = self._ensure_id(item, "event_id")
                if "date" not in item or not item["date"]:
                    result.errors.append(f"competitor_event missing date: {_truncate(item)}")
                    continue
                if "competitor" not in item or not item["competitor"]:
                    result.errors.append(f"competitor_event missing competitor: {_truncate(item)}")
                    continue
                ev = CompetitorEvent.from_dict(item)
                self.store.save_competitor_event(ev)
                result.competitor_events += 1
            except Exception as e:
                result.errors.append(f"competitor_event: {e} — data: {_truncate(item)}")

        for item in data.get("evidence", []):
            try:
                item = self._ensure_id(item, "artifact_id")
                ev = EvidenceArtifact.from_dict(item)
                self.store.save_evidence(ev)
                result.evidence += 1
            except Exception as e:
                result.errors.append(f"evidence: {e} — data: {_truncate(item)}")

        return result

    def import_interventions_csv(self, csv_text: str, run_id: str = None) -> ImportResult:
        """
        从 CSV 导入 interventions。
        CSV header 对应 HistoricalIntervention 字段名。
        channel_mix 字段如果存在，用逗号分隔。
        """
        result = ImportResult()
        reader = csv.DictReader(io.StringIO(csv_text))

        for row_num, row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v.strip() for k, v in row.items() if v and v.strip()}
                row = self._ensure_id(row, "intervention_id")
                if run_id:
                    row["run_id"] = run_id
                elif "run_id" not in row or not row["run_id"]:
                    row["run_id"] = row["intervention_id"]

                # Parse numeric fields
                row = self._coerce_numeric(
                    row, self._INTERVENTION_NUMERIC, result.warnings,
                    f"csv row {row_num}",
                )

                # Parse channel_mix as comma-separated
                if "channel_mix" in row and isinstance(row["channel_mix"], str):
                    row["channel_mix"] = [c.strip() for c in row["channel_mix"].split(",") if c.strip()]

                iv = HistoricalIntervention.from_dict(row)
                self.store.save_intervention(iv)
                result.interventions += 1
            except Exception as e:
                result.errors.append(f"row {row_num}: {e}")

        return result

    def import_outcomes_csv(self, csv_text: str) -> ImportResult:
        """从 CSV 导入 outcomes。"""
        result = ImportResult()
        reader = csv.DictReader(io.StringIO(csv_text))
        for row_num, row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v.strip() for k, v in row.items() if v and v.strip()}
                row = self._ensure_id(row, "outcome_id")
                if "intervention_id" not in row or not row["intervention_id"]:
                    result.errors.append(f"row {row_num}: missing intervention_id")
                    continue

                row = self._coerce_numeric(
                    row, self._OUTCOME_NUMERIC, result.warnings,
                    f"csv row {row_num}",
                )

                oc = HistoricalOutcomeWindow.from_dict(row)
                self.store.save_outcome(oc)
                result.outcomes += 1
            except Exception as e:
                result.errors.append(f"row {row_num}: {e}")

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_id(d: Dict[str, Any], id_field: str) -> Dict[str, Any]:
        d = dict(d)
        if id_field not in d or not d[id_field]:
            d[id_field] = str(uuid.uuid4())[:12]
        return d

    @staticmethod
    def _coerce_numeric(d: Dict[str, Any], fields: Tuple[str, ...], errors: List[str], context: str) -> Dict[str, Any]:
        """
        对指定字段做数值类型转换。
        无法转换的字段删除并记入 errors。
        """
        d = dict(d)
        for f in fields:
            if f not in d or d[f] is None:
                continue
            v = d[f]
            if isinstance(v, (int, float)):
                continue
            try:
                d[f] = float(v) if ("." in str(v)) else int(v)
            except (ValueError, TypeError):
                errors.append(f"{context}: field '{f}' 无法转为数值: {v!r}")
                del d[f]
        return d

    # Numeric field definitions per entity type
    _INTERVENTION_NUMERIC = ("budget", "spend")
    _OUTCOME_NUMERIC = (
        "impressions", "clicks", "ctr", "cvr", "revenue", "roas",
        "brand_lift", "search_trend_delta", "comment_sentiment",
        "sessions", "pdp_views", "add_to_cart", "checkout_started",
        "purchases", "new_customers", "returning_customers", "aov",
    )
    _SIGNAL_NUMERIC = ("value",)


def _truncate(obj: Any, max_len: int = 120) -> str:
    s = str(obj)
    return s[:max_len] + "..." if len(s) > max_len else s
