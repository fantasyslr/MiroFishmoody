"""
Brandiction PR1 — 数据模型、存储、导入、API 测试
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
    CompetitorEvent,
    EvidenceArtifact,
)
from app.services.brandiction_store import BrandictionStore
from app.services.historical_importer import HistoricalImporter, ImportResult


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def _fresh_store():
    """每次返回一个全新的 SQLite store（临时文件）"""
    BrandictionStore._reset_instance()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = BrandictionStore(db_path=path)
    return store, path


def _cleanup(store, path):
    BrandictionStore._reset_instance()
    try:
        os.unlink(path)
    except OSError:
        pass


# ------------------------------------------------------------------
# Model tests
# ------------------------------------------------------------------

class TestModels:
    def test_intervention_from_dict_sparse(self):
        d = {"intervention_id": "iv1", "run_id": "r1"}
        iv = HistoricalIntervention.from_dict(d)
        assert iv.intervention_id == "iv1"
        assert iv.run_id == "r1"
        assert iv.theme is None
        assert iv.channel_mix is None

    def test_intervention_extra_fields(self):
        d = {"intervention_id": "iv1", "run_id": "r1", "custom_field": "hello"}
        iv = HistoricalIntervention.from_dict(d)
        assert iv.extra["custom_field"] == "hello"

    def test_intervention_to_dict_skips_none(self):
        iv = HistoricalIntervention(intervention_id="iv1", run_id="r1")
        d = iv.to_dict()
        assert "theme" not in d
        assert d["intervention_id"] == "iv1"

    def test_outcome_from_dict(self):
        d = {"outcome_id": "oc1", "intervention_id": "iv1", "impressions": 5000}
        oc = HistoricalOutcomeWindow.from_dict(d)
        assert oc.impressions == 5000
        assert oc.ctr is None

    def test_signal_from_dict(self):
        d = {"signal_id": "s1", "date": "2025-06-01", "value": 0.75}
        sig = BrandSignalSnapshot.from_dict(d)
        assert sig.value == 0.75

    def test_competitor_event_from_dict(self):
        d = {"event_id": "e1", "date": "2025-07-01", "competitor": "acuvue"}
        ev = CompetitorEvent.from_dict(d)
        assert ev.competitor == "acuvue"

    def test_evidence_from_dict(self):
        d = {"artifact_id": "a1", "artifact_type": "screenshot"}
        ev = EvidenceArtifact.from_dict(d)
        assert ev.artifact_type == "screenshot"


# ------------------------------------------------------------------
# Store tests
# ------------------------------------------------------------------

class TestStore:
    def test_save_and_get_intervention(self):
        store, path = _fresh_store()
        try:
            iv = HistoricalIntervention(intervention_id="iv1", run_id="r1", theme="comfort")
            store.save_intervention(iv)
            got = store.get_intervention("iv1")
            assert got is not None
            assert got.theme == "comfort"
        finally:
            _cleanup(store, path)

    def test_list_interventions_by_run(self):
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            store.save_intervention(HistoricalIntervention("iv2", "r1"))
            store.save_intervention(HistoricalIntervention("iv3", "r2"))
            assert len(store.list_interventions(run_id="r1")) == 2
            assert len(store.list_interventions()) == 3
        finally:
            _cleanup(store, path)

    def test_list_run_ids(self):
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            store.save_intervention(HistoricalIntervention("iv2", "r2"))
            ids = store.list_run_ids()
            assert set(ids) == {"r1", "r2"}
        finally:
            _cleanup(store, path)

    def test_save_and_list_outcomes(self):
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            store.save_outcome(HistoricalOutcomeWindow("oc1", "iv1", impressions=1000))
            store.save_outcome(HistoricalOutcomeWindow("oc2", "iv1", impressions=2000))
            outcomes = store.list_outcomes("iv1")
            assert len(outcomes) == 2
        finally:
            _cleanup(store, path)

    def test_save_and_list_signals(self):
        store, path = _fresh_store()
        try:
            store.save_signal(BrandSignalSnapshot("s1", "2025-06-01", value=0.8))
            store.save_signal(BrandSignalSnapshot("s2", "2025-07-01", value=0.6))
            all_sigs = store.list_signals()
            assert len(all_sigs) == 2
            filtered = store.list_signals(date_from="2025-06-15")
            assert len(filtered) == 1
        finally:
            _cleanup(store, path)

    def test_save_and_list_competitor_events(self):
        store, path = _fresh_store()
        try:
            store.save_competitor_event(CompetitorEvent("e1", "2025-06-01", "acuvue"))
            events = store.list_competitor_events()
            assert len(events) == 1
            assert events[0].competitor == "acuvue"
        finally:
            _cleanup(store, path)

    def test_save_and_list_evidence(self):
        store, path = _fresh_store()
        try:
            store.save_evidence(EvidenceArtifact("a1", intervention_id="iv1"))
            evs = store.list_evidence("iv1")
            assert len(evs) == 1
        finally:
            _cleanup(store, path)

    def test_stats(self):
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            store.save_outcome(HistoricalOutcomeWindow("oc1", "iv1"))
            store.save_signal(BrandSignalSnapshot("s1", "2025-06-01"))
            s = store.stats()
            assert s["interventions"] == 1
            assert s["outcomes"] == 1
            assert s["signals"] == 1
            assert s["runs"] == 1
        finally:
            _cleanup(store, path)

    def test_channel_mix_json_roundtrip(self):
        store, path = _fresh_store()
        try:
            iv = HistoricalIntervention("iv1", "r1", channel_mix=["douyin", "redbook"])
            store.save_intervention(iv)
            got = store.get_intervention("iv1")
            assert got.channel_mix == ["douyin", "redbook"]
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Importer tests
# ------------------------------------------------------------------

class TestImporter:
    def test_json_import_full(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {
                "interventions": [
                    {"intervention_id": "iv1", "run_id": "r1", "theme": "science"},
                    {"intervention_id": "iv2", "run_id": "r1", "theme": "comfort"},
                ],
                "outcomes": [
                    {"outcome_id": "oc1", "intervention_id": "iv1", "impressions": 5000},
                ],
                "signals": [
                    {"signal_id": "s1", "date": "2025-06-01", "value": 0.8},
                ],
                "competitor_events": [
                    {"event_id": "e1", "date": "2025-07-01", "competitor": "acuvue"},
                ],
                "evidence": [
                    {"artifact_id": "a1", "intervention_id": "iv1"},
                ],
            }
            result = importer.import_json(data)
            assert result.interventions == 2
            assert result.outcomes == 1
            assert result.signals == 1
            assert result.competitor_events == 1
            assert result.evidence == 1
            assert result.errors == []
        finally:
            _cleanup(store, path)

    def test_json_import_auto_id(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {"interventions": [{"run_id": "r1"}]}
            result = importer.import_json(data)
            assert result.interventions == 1
            ivs = store.list_interventions()
            assert len(ivs) == 1
            assert len(ivs[0].intervention_id) > 0
        finally:
            _cleanup(store, path)

    def test_json_import_auto_run_id(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {"interventions": [{"intervention_id": "iv1"}]}
            result = importer.import_json(data)
            assert result.interventions == 1
            iv = store.get_intervention("iv1")
            assert iv.run_id == "iv1"  # auto-filled from intervention_id
        finally:
            _cleanup(store, path)

    def test_json_import_outcome_missing_intervention_id(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {"outcomes": [{"outcome_id": "oc1"}]}
            result = importer.import_json(data)
            assert result.outcomes == 0
            assert len(result.errors) == 1
        finally:
            _cleanup(store, path)

    def test_json_import_signal_missing_date(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {"signals": [{"signal_id": "s1"}]}
            result = importer.import_json(data)
            assert result.signals == 0
            assert len(result.errors) == 1
        finally:
            _cleanup(store, path)

    def test_csv_interventions(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            csv_text = "intervention_id,run_id,theme,budget\niv1,r1,science,50000\niv2,r1,comfort,30000"
            result = importer.import_interventions_csv(csv_text)
            assert result.interventions == 2
            iv = store.get_intervention("iv1")
            assert iv.budget == 50000.0
        finally:
            _cleanup(store, path)

    def test_csv_interventions_with_run_id_override(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            csv_text = "intervention_id,theme\niv1,science"
            result = importer.import_interventions_csv(csv_text, run_id="override_run")
            assert result.interventions == 1
            iv = store.get_intervention("iv1")
            assert iv.run_id == "override_run"
        finally:
            _cleanup(store, path)

    def test_csv_outcomes(self):
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            importer = HistoricalImporter(store)
            csv_text = "outcome_id,intervention_id,impressions,ctr\noc1,iv1,5000,0.035"
            result = importer.import_outcomes_csv(csv_text)
            assert result.outcomes == 1
            ocs = store.list_outcomes("iv1")
            assert ocs[0].impressions == 5000
            assert ocs[0].ctr == 0.035
        finally:
            _cleanup(store, path)

    def test_csv_outcomes_missing_intervention_id(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            csv_text = "outcome_id,impressions\noc1,5000"
            result = importer.import_outcomes_csv(csv_text)
            assert result.outcomes == 0
            assert len(result.errors) == 1
        finally:
            _cleanup(store, path)

    def test_import_result_to_dict(self):
        r = ImportResult()
        r.interventions = 3
        r.errors.append("test error")
        d = r.to_dict()
        assert d["imported"]["interventions"] == 3
        assert d["errors"] == ["test error"]

    def test_csv_channel_mix_parsing(self):
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            csv_text = 'intervention_id,run_id,channel_mix\niv1,r1,"douyin,redbook,weibo"'
            result = importer.import_interventions_csv(csv_text)
            assert result.interventions == 1
            iv = store.get_intervention("iv1")
            assert iv.channel_mix == ["douyin", "redbook", "weibo"]
        finally:
            _cleanup(store, path)

    def test_sparse_json_import(self):
        """Only interventions, no other sections"""
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {"interventions": [{"intervention_id": "iv1", "run_id": "r1"}]}
            result = importer.import_json(data)
            assert result.interventions == 1
            assert result.outcomes == 0
            assert result.signals == 0
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Regression: Fix 1 — merge upsert 不丢旧字段
# ------------------------------------------------------------------

class TestMergeUpsert:
    def test_sparse_update_preserves_old_fields(self):
        """二次导入只带 theme，budget/spend 不应丢失"""
        store, path = _fresh_store()
        try:
            # 第一次：写入 budget + spend
            iv = HistoricalIntervention("iv1", "r1", budget=50000.0, spend=30000.0)
            store.save_intervention(iv)
            got = store.get_intervention("iv1")
            assert got.budget == 50000.0
            assert got.spend == 30000.0

            # 第二次：只更新 theme，不带 budget/spend
            iv2 = HistoricalIntervention("iv1", "r1", theme="science")
            store.save_intervention(iv2)
            got2 = store.get_intervention("iv1")
            assert got2.theme == "science"
            assert got2.budget == 50000.0, "budget should be preserved"
            assert got2.spend == 30000.0, "spend should be preserved"
        finally:
            _cleanup(store, path)

    def test_sparse_update_outcome_preserves_metrics(self):
        """二次导入 outcome 只带 comment_summary，数值指标不丢"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            oc = HistoricalOutcomeWindow("oc1", "iv1", impressions=5000, ctr=0.035)
            store.save_outcome(oc)

            # 只更新 comment_summary
            oc2 = HistoricalOutcomeWindow("oc1", "iv1", comment_summary="很好")
            store.save_outcome(oc2)

            got = store.list_outcomes("iv1")[0]
            assert got.comment_summary == "很好"
            assert got.impressions == 5000, "impressions should be preserved"
            assert got.ctr == 0.035, "ctr should be preserved"
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Regression: Fix 2 — 外键约束生效
# ------------------------------------------------------------------

class TestForeignKeys:
    def test_outcome_rejects_orphan_intervention_id(self):
        """没有对应 intervention 的 outcome 应该写入失败"""
        store, path = _fresh_store()
        try:
            import pytest
            oc = HistoricalOutcomeWindow("oc1", "nonexistent_iv")
            with pytest.raises(Exception):
                store.save_outcome(oc)
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Regression: Fix 3 — 数值类型校验
# ------------------------------------------------------------------

class TestTypeValidation:
    def test_json_import_bad_numeric_outcome(self):
        """非数值字段应该被剥离并产生 warning"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            importer = HistoricalImporter(store)
            data = {
                "outcomes": [{
                    "outcome_id": "oc1",
                    "intervention_id": "iv1",
                    "impressions": "abc",
                    "ctr": "not-a-float",
                }],
            }
            result = importer.import_json(data)
            assert result.outcomes == 1  # 仍然导入成功
            assert len(result.warnings) == 2  # 两个坏字段产生 warning

            # 坏字段不应进库
            oc = store.list_outcomes("iv1")[0]
            assert oc.impressions is None
            assert oc.ctr is None
        finally:
            _cleanup(store, path)

    def test_json_import_valid_numeric_string(self):
        """合法的数值字符串应该被正确转换"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            importer = HistoricalImporter(store)
            data = {
                "outcomes": [{
                    "outcome_id": "oc1",
                    "intervention_id": "iv1",
                    "impressions": "5000",
                    "ctr": "0.035",
                }],
            }
            result = importer.import_json(data)
            assert result.outcomes == 1
            assert result.warnings == []

            oc = store.list_outcomes("iv1")[0]
            assert oc.impressions == 5000
            assert oc.ctr == 0.035
        finally:
            _cleanup(store, path)

    def test_json_import_bad_numeric_signal(self):
        """signal value 为非数值时产生 warning"""
        store, path = _fresh_store()
        try:
            importer = HistoricalImporter(store)
            data = {
                "signals": [{
                    "signal_id": "s1",
                    "date": "2025-06-01",
                    "value": "invalid",
                }],
            }
            result = importer.import_json(data)
            assert result.signals == 1
            assert len(result.warnings) == 1
        finally:
            _cleanup(store, path)
