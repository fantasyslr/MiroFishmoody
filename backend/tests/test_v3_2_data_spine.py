"""
PR-V3-2 测试 — DTC Data Spine

验证新字段在 model → store → importer → API 全链路的正确流转。
"""

import json
import os
import tempfile
import unittest

# --- 让 import 能找到 app ---
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("MOODY_SECRET_KEY", "test-secret")
os.environ.setdefault("MOODY_UPLOAD_FOLDER", tempfile.mkdtemp())

from app.models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
)
from app.services.brandiction_store import BrandictionStore
from app.services.historical_importer import HistoricalImporter


def _fresh_store():
    BrandictionStore._reset_instance()
    db = os.path.join(tempfile.mkdtemp(), "test_v3_spine.db")
    return BrandictionStore(db)


# =====================================================================
# 1. Model 层 — 新字段可以赋值、序列化、反序列化
# =====================================================================

class TestInterventionV3Fields(unittest.TestCase):
    def test_new_fields_default_none(self):
        iv = HistoricalIntervention(intervention_id="iv1", run_id="r1")
        self.assertIsNone(iv.campaign_id)
        self.assertIsNone(iv.creative_id)
        self.assertIsNone(iv.landing_page)
        self.assertIsNone(iv.platform)
        self.assertIsNone(iv.channel_family)
        self.assertIsNone(iv.objective)

    def test_new_fields_roundtrip_dict(self):
        iv = HistoricalIntervention(
            intervention_id="iv1", run_id="r1",
            campaign_id="camp-123", creative_id="cr-456",
            landing_page="/products/daily", platform="meta",
            channel_family="paid_social", objective="conversion",
        )
        d = iv.to_dict()
        self.assertEqual(d["campaign_id"], "camp-123")
        self.assertEqual(d["platform"], "meta")
        self.assertEqual(d["objective"], "conversion")
        # from_dict roundtrip
        iv2 = HistoricalIntervention.from_dict(d)
        self.assertEqual(iv2.campaign_id, "camp-123")
        self.assertEqual(iv2.landing_page, "/products/daily")

    def test_to_dict_skips_none_new_fields(self):
        iv = HistoricalIntervention(intervention_id="iv1", run_id="r1")
        d = iv.to_dict()
        self.assertNotIn("campaign_id", d)
        self.assertNotIn("platform", d)


class TestOutcomeV3Fields(unittest.TestCase):
    def test_new_fields_default_none(self):
        oc = HistoricalOutcomeWindow(outcome_id="oc1", intervention_id="iv1")
        self.assertIsNone(oc.sessions)
        self.assertIsNone(oc.pdp_views)
        self.assertIsNone(oc.add_to_cart)
        self.assertIsNone(oc.checkout_started)
        self.assertIsNone(oc.purchases)
        self.assertIsNone(oc.new_customers)
        self.assertIsNone(oc.returning_customers)
        self.assertIsNone(oc.aov)

    def test_new_fields_roundtrip_dict(self):
        oc = HistoricalOutcomeWindow(
            outcome_id="oc1", intervention_id="iv1",
            sessions=5000, pdp_views=3200, add_to_cart=800,
            checkout_started=600, purchases=420,
            new_customers=280, returning_customers=140, aov=189.5,
        )
        d = oc.to_dict()
        self.assertEqual(d["sessions"], 5000)
        self.assertEqual(d["purchases"], 420)
        self.assertEqual(d["aov"], 189.5)
        oc2 = HistoricalOutcomeWindow.from_dict(d)
        self.assertEqual(oc2.new_customers, 280)
        self.assertEqual(oc2.returning_customers, 140)


class TestSignalV3Fields(unittest.TestCase):
    def test_new_fields_default_none(self):
        sig = BrandSignalSnapshot(signal_id="s1", date="2025-12-01")
        self.assertIsNone(sig.source_type)
        self.assertIsNone(sig.source_id)
        self.assertIsNone(sig.raw_text_ref)

    def test_new_fields_roundtrip_dict(self):
        sig = BrandSignalSnapshot(
            signal_id="s1", date="2025-12-01",
            source_type="dtc_site", source_id="order-batch-202512",
            raw_text_ref="/data/reviews/202512.jsonl",
        )
        d = sig.to_dict()
        self.assertEqual(d["source_type"], "dtc_site")
        sig2 = BrandSignalSnapshot.from_dict(d)
        self.assertEqual(sig2.raw_text_ref, "/data/reviews/202512.jsonl")


# =====================================================================
# 2. Store 层 — save → get/list 新字段持久化
# =====================================================================

class TestStoreInterventionV3(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()

    def test_save_and_get_new_fields(self):
        iv = HistoricalIntervention(
            intervention_id="iv-v3", run_id="r1",
            campaign_id="camp-001", creative_id="cr-002",
            landing_page="/lp/comfort", platform="douyin",
            channel_family="kol_seed", objective="awareness",
        )
        self.store.save_intervention(iv)
        got = self.store.get_intervention("iv-v3")
        self.assertIsNotNone(got)
        self.assertEqual(got.campaign_id, "camp-001")
        self.assertEqual(got.creative_id, "cr-002")
        self.assertEqual(got.landing_page, "/lp/comfort")
        self.assertEqual(got.platform, "douyin")
        self.assertEqual(got.channel_family, "kol_seed")
        self.assertEqual(got.objective, "awareness")

    def test_list_filter_campaign_id(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", campaign_id="camp-x",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", campaign_id="camp-y",
        ))
        result = self.store.list_interventions(campaign_id="camp-x")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intervention_id, "a")

    def test_list_filter_platform(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", platform="meta",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", platform="google",
        ))
        result = self.store.list_interventions(platform="meta")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intervention_id, "a")

    def test_list_filter_channel_family(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", channel_family="paid_social",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", channel_family="kol_seed",
        ))
        result = self.store.list_interventions(channel_family="kol_seed")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intervention_id, "b")

    def test_list_filter_landing_page(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", landing_page="/products/daily",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", landing_page="/products/color",
        ))
        result = self.store.list_interventions(landing_page="/products/daily")
        self.assertEqual(len(result), 1)

    def test_list_filter_market(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", market="cn",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", market="us",
        ))
        result = self.store.list_interventions(market="cn")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intervention_id, "a")

    def test_list_combined_filters(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", platform="meta", market="cn",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", platform="meta", market="us",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="c", run_id="r", platform="google", market="cn",
        ))
        result = self.store.list_interventions(platform="meta", market="cn")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intervention_id, "a")

    def test_merge_upsert_preserves_new_fields(self):
        """Merge upsert should update new fields without overwriting old ones."""
        iv1 = HistoricalIntervention(
            intervention_id="iv-m", run_id="r1",
            campaign_id="camp-001", theme="science",
        )
        self.store.save_intervention(iv1)
        # Second save adds platform, doesn't overwrite campaign_id
        iv2 = HistoricalIntervention(
            intervention_id="iv-m", run_id="r1",
            platform="meta",
        )
        self.store.save_intervention(iv2)
        got = self.store.get_intervention("iv-m")
        self.assertEqual(got.campaign_id, "camp-001")
        self.assertEqual(got.platform, "meta")
        self.assertEqual(got.theme, "science")


class TestStoreOutcomeV3(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv1", run_id="r1",
        ))

    def test_save_and_list_dtc_fields(self):
        oc = HistoricalOutcomeWindow(
            outcome_id="oc-v3", intervention_id="iv1",
            sessions=5000, pdp_views=3200, add_to_cart=800,
            checkout_started=600, purchases=420,
            new_customers=280, returning_customers=140, aov=189.5,
        )
        self.store.save_outcome(oc)
        results = self.store.list_outcomes("iv1")
        self.assertEqual(len(results), 1)
        got = results[0]
        self.assertEqual(got.sessions, 5000)
        self.assertEqual(got.pdp_views, 3200)
        self.assertEqual(got.add_to_cart, 800)
        self.assertEqual(got.checkout_started, 600)
        self.assertEqual(got.purchases, 420)
        self.assertEqual(got.new_customers, 280)
        self.assertEqual(got.returning_customers, 140)
        self.assertAlmostEqual(got.aov, 189.5)

    def test_dtc_fields_coexist_with_old_fields(self):
        oc = HistoricalOutcomeWindow(
            outcome_id="oc-both", intervention_id="iv1",
            impressions=100000, clicks=5000, ctr=0.05,
            revenue=80000, roas=2.5,
            sessions=6000, purchases=500, aov=160.0,
        )
        self.store.save_outcome(oc)
        got = self.store.list_outcomes("iv1")[0]
        self.assertEqual(got.impressions, 100000)
        self.assertEqual(got.sessions, 6000)
        self.assertEqual(got.purchases, 500)
        self.assertAlmostEqual(got.aov, 160.0)
        self.assertAlmostEqual(got.roas, 2.5)


class TestStoreSignalV3(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()

    def test_save_and_list_source_fields(self):
        sig = BrandSignalSnapshot(
            signal_id="s-v3", date="2025-12-01",
            source_type="dtc_site", source_id="batch-001",
            raw_text_ref="/data/reviews/batch001.jsonl",
        )
        self.store.save_signal(sig)
        results = self.store.list_signals()
        self.assertEqual(len(results), 1)
        got = results[0]
        self.assertEqual(got.source_type, "dtc_site")
        self.assertEqual(got.source_id, "batch-001")
        self.assertEqual(got.raw_text_ref, "/data/reviews/batch001.jsonl")

    def test_list_filter_source_type(self):
        self.store.save_signal(BrandSignalSnapshot(
            signal_id="s1", date="2025-12-01", source_type="dtc_site",
        ))
        self.store.save_signal(BrandSignalSnapshot(
            signal_id="s2", date="2025-12-01", source_type="meta_ads",
        ))
        self.store.save_signal(BrandSignalSnapshot(
            signal_id="s3", date="2025-12-01", source_type="dtc_site",
        ))
        result = self.store.list_signals(source_type="dtc_site")
        self.assertEqual(len(result), 2)
        result2 = self.store.list_signals(source_type="meta_ads")
        self.assertEqual(len(result2), 1)


# =====================================================================
# 3. Importer 层 — JSON / CSV 导入新字段
# =====================================================================

class TestImporterV3JSON(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.importer = HistoricalImporter(self.store)

    def test_import_intervention_v3_fields(self):
        data = {
            "interventions": [{
                "intervention_id": "iv-json",
                "run_id": "r1",
                "campaign_id": "camp-abc",
                "creative_id": "cr-xyz",
                "landing_page": "/products/daily",
                "platform": "meta",
                "channel_family": "paid_social",
                "objective": "conversion",
                "budget": 50000,
            }]
        }
        result = self.importer.import_json(data)
        self.assertEqual(result.interventions, 1)
        self.assertEqual(result.errors, [])
        got = self.store.get_intervention("iv-json")
        self.assertEqual(got.campaign_id, "camp-abc")
        self.assertEqual(got.platform, "meta")
        self.assertEqual(got.objective, "conversion")
        self.assertEqual(got.budget, 50000)

    def test_import_outcome_dtc_fields(self):
        # Need parent intervention first
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv1", run_id="r1",
        ))
        data = {
            "outcomes": [{
                "outcome_id": "oc-json",
                "intervention_id": "iv1",
                "sessions": "5000",
                "pdp_views": "3200",
                "add_to_cart": "800",
                "checkout_started": "600",
                "purchases": "420",
                "new_customers": "280",
                "returning_customers": "140",
                "aov": "189.5",
                "revenue": "79590",
            }]
        }
        result = self.importer.import_json(data)
        self.assertEqual(result.outcomes, 1)
        self.assertEqual(result.errors, [])
        got = self.store.list_outcomes("iv1")[0]
        self.assertEqual(got.sessions, 5000)
        self.assertEqual(got.purchases, 420)
        self.assertAlmostEqual(got.aov, 189.5)
        self.assertEqual(got.revenue, 79590)

    def test_import_signal_source_fields(self):
        data = {
            "signals": [{
                "signal_id": "s-json",
                "date": "2025-12-01",
                "source_type": "dtc_site",
                "source_id": "order-batch-202512",
                "raw_text_ref": "/data/reviews/202512.jsonl",
                "dimension": "comfort_trust",
                "value": 0.72,
            }]
        }
        result = self.importer.import_json(data)
        self.assertEqual(result.signals, 1)
        got = self.store.list_signals()[0]
        self.assertEqual(got.source_type, "dtc_site")
        self.assertEqual(got.source_id, "order-batch-202512")


class TestImporterV3CSV(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.importer = HistoricalImporter(self.store)

    def test_csv_intervention_v3_fields(self):
        csv_text = (
            "intervention_id,run_id,campaign_id,platform,channel_family,objective,budget\n"
            "iv-csv,r1,camp-csv,google,paid_search,traffic,30000\n"
        )
        result = self.importer.import_interventions_csv(csv_text)
        self.assertEqual(result.interventions, 1)
        self.assertEqual(result.errors, [])
        got = self.store.get_intervention("iv-csv")
        self.assertEqual(got.campaign_id, "camp-csv")
        self.assertEqual(got.platform, "google")
        self.assertEqual(got.channel_family, "paid_search")
        self.assertEqual(got.objective, "traffic")
        self.assertEqual(got.budget, 30000)

    def test_csv_outcome_dtc_fields(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv1", run_id="r1",
        ))
        csv_text = (
            "outcome_id,intervention_id,sessions,pdp_views,purchases,aov,revenue\n"
            "oc-csv,iv1,4000,2500,300,175.5,52650\n"
        )
        result = self.importer.import_outcomes_csv(csv_text)
        self.assertEqual(result.outcomes, 1)
        self.assertEqual(result.errors, [])
        got = self.store.list_outcomes("iv1")[0]
        self.assertEqual(got.sessions, 4000)
        self.assertEqual(got.pdp_views, 2500)
        self.assertEqual(got.purchases, 300)
        self.assertAlmostEqual(got.aov, 175.5)


# =====================================================================
# 4. 向后兼容 — 不带新字段的旧数据仍可导入
# =====================================================================

class TestBackwardCompatibility(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.importer = HistoricalImporter(self.store)

    def test_old_format_intervention_still_works(self):
        data = {
            "interventions": [{
                "intervention_id": "iv-old",
                "run_id": "r1",
                "theme": "science_credibility",
                "budget": 50000,
            }]
        }
        result = self.importer.import_json(data)
        self.assertEqual(result.interventions, 1)
        self.assertEqual(result.errors, [])
        got = self.store.get_intervention("iv-old")
        self.assertEqual(got.theme, "science_credibility")
        self.assertIsNone(got.campaign_id)
        self.assertIsNone(got.platform)

    def test_old_format_outcome_still_works(self):
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv1", run_id="r1",
        ))
        data = {
            "outcomes": [{
                "outcome_id": "oc-old",
                "intervention_id": "iv1",
                "impressions": 100000,
                "clicks": 5000,
                "revenue": 80000,
            }]
        }
        result = self.importer.import_json(data)
        self.assertEqual(result.outcomes, 1)
        got = self.store.list_outcomes("iv1")[0]
        self.assertEqual(got.impressions, 100000)
        self.assertIsNone(got.sessions)
        self.assertIsNone(got.purchases)

    def test_old_csv_no_v3_columns(self):
        csv_text = (
            "intervention_id,run_id,theme,budget\n"
            "iv-csv-old,r1,comfort_beauty,40000\n"
        )
        result = self.importer.import_interventions_csv(csv_text)
        self.assertEqual(result.interventions, 1)
        got = self.store.get_intervention("iv-csv-old")
        self.assertEqual(got.theme, "comfort_beauty")
        self.assertIsNone(got.campaign_id)


# =====================================================================
# 5. 边界条件
# =====================================================================

class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()

    def test_empty_string_platform_not_filtered(self):
        """Empty string filter should not match anything (treated as no filter)."""
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", platform="meta",
        ))
        # Empty string → no filter → returns all
        result = self.store.list_interventions(platform="")
        # Empty string is falsy, so filter is skipped
        self.assertEqual(len(result), 1)

    def test_numeric_coercion_in_dtc_fields(self):
        """String numbers in DTC fields should be coerced to int/float."""
        importer = HistoricalImporter(self.store)
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv1", run_id="r1",
        ))
        data = {
            "outcomes": [{
                "outcome_id": "oc-coerce",
                "intervention_id": "iv1",
                "sessions": "3500",
                "aov": "189.50",
                "purchases": "abc",  # bad value
            }]
        }
        result = importer.import_json(data)
        self.assertEqual(result.outcomes, 1)
        self.assertTrue(any("purchases" in w for w in result.warnings))
        got = self.store.list_outcomes("iv1")[0]
        self.assertEqual(got.sessions, 3500)
        self.assertAlmostEqual(got.aov, 189.5)
        self.assertIsNone(got.purchases)  # coercion failed, field removed

    def test_unknown_fields_go_to_extra(self):
        """Fields not in the dataclass go to extra dict."""
        iv = HistoricalIntervention.from_dict({
            "intervention_id": "iv-extra",
            "run_id": "r1",
            "some_future_field": "hello",
        })
        self.assertEqual(iv.extra.get("some_future_field"), "hello")


# =====================================================================
# 6. Store — creative_id / objective / source_id 过滤
# =====================================================================

class TestStoreCreativeObjectiveFilters(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="a", run_id="r", creative_id="cr-001", objective="awareness",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="b", run_id="r", creative_id="cr-002", objective="conversion",
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="c", run_id="r", creative_id="cr-001", objective="conversion",
        ))

    def test_filter_creative_id(self):
        result = self.store.list_interventions(creative_id="cr-001")
        self.assertEqual(len(result), 2)
        ids = {r.intervention_id for r in result}
        self.assertEqual(ids, {"a", "c"})

    def test_filter_objective(self):
        result = self.store.list_interventions(objective="conversion")
        self.assertEqual(len(result), 2)
        ids = {r.intervention_id for r in result}
        self.assertEqual(ids, {"b", "c"})

    def test_filter_creative_id_and_objective(self):
        result = self.store.list_interventions(creative_id="cr-001", objective="awareness")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].intervention_id, "a")


class TestStoreSourceIdFilter(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.store.save_signal(BrandSignalSnapshot(
            signal_id="s1", date="2025-12-01", source_type="dtc_site", source_id="batch-A",
        ))
        self.store.save_signal(BrandSignalSnapshot(
            signal_id="s2", date="2025-12-01", source_type="dtc_site", source_id="batch-B",
        ))
        self.store.save_signal(BrandSignalSnapshot(
            signal_id="s3", date="2025-12-01", source_type="meta_ads", source_id="batch-A",
        ))

    def test_filter_source_id(self):
        result = self.store.list_signals(source_id="batch-A")
        self.assertEqual(len(result), 2)

    def test_filter_source_type_and_source_id(self):
        result = self.store.list_signals(source_type="dtc_site", source_id="batch-A")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].signal_id, "s1")


# =====================================================================
# 7. API request-level — /interventions 和 /signals 新过滤
# =====================================================================

from app import create_app


def _make_app():
    BrandictionStore._reset_instance()
    db = os.path.join(tempfile.mkdtemp(), "test_api_v3.db")
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    BrandictionStore._reset_instance()
    with app.app_context():
        BrandictionStore(db_path=db)
    return app, db


def _admin_session(client):
    from app.auth import _password_version
    with client.session_transaction() as sess:
        sess["user"] = {"username": "slr", "display_name": "Liren", "role": "admin", "_pw_ver": _password_version("slr")}


def _user_session(client):
    from app.auth import _password_version
    with client.session_transaction() as sess:
        sess["user"] = {"username": "tester1", "display_name": "Tester1", "role": "user", "_pw_ver": _password_version("tester1")}


class TestAPIInterventionsEndpoint(unittest.TestCase):
    def setUp(self):
        self.app, self.db = _make_app()
        with self.app.app_context():
            store = BrandictionStore()
            store.save_intervention(HistoricalIntervention(
                intervention_id="iv-1", run_id="r1",
                campaign_id="camp-x", creative_id="cr-a",
                platform="meta", objective="conversion", market="cn",
            ))
            store.save_intervention(HistoricalIntervention(
                intervention_id="iv-2", run_id="r1",
                campaign_id="camp-y", creative_id="cr-b",
                platform="google", objective="traffic", market="us",
            ))
            store.save_intervention(HistoricalIntervention(
                intervention_id="iv-3", run_id="r1",
                campaign_id="camp-x", creative_id="cr-a",
                platform="meta", objective="awareness", market="cn",
            ))

    def tearDown(self):
        BrandictionStore._reset_instance()
        try:
            os.unlink(self.db)
        except OSError:
            pass

    def test_list_all(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/interventions")
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertEqual(data["count"], 3)

    def test_filter_campaign_id(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/interventions?campaign_id=camp-x")
            data = r.get_json()
            self.assertEqual(data["count"], 2)

    def test_filter_creative_id(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/interventions?creative_id=cr-b")
            data = r.get_json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["interventions"][0]["intervention_id"], "iv-2")

    def test_filter_objective(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/interventions?objective=conversion")
            data = r.get_json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["interventions"][0]["intervention_id"], "iv-1")

    def test_filter_platform_and_market(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/interventions?platform=meta&market=cn")
            data = r.get_json()
            self.assertEqual(data["count"], 2)

    def test_requires_login(self):
        with self.app.test_client() as c:
            r = c.get("/api/brandiction/interventions")
            self.assertEqual(r.status_code, 401)


class TestAPISignalsSourceFilter(unittest.TestCase):
    def setUp(self):
        self.app, self.db = _make_app()
        with self.app.app_context():
            store = BrandictionStore()
            store.save_signal(BrandSignalSnapshot(
                signal_id="s1", date="2025-12-01",
                source_type="dtc_site", source_id="batch-A",
            ))
            store.save_signal(BrandSignalSnapshot(
                signal_id="s2", date="2025-12-01",
                source_type="meta_ads", source_id="camp-001",
            ))
            store.save_signal(BrandSignalSnapshot(
                signal_id="s3", date="2025-12-01",
                source_type="dtc_site", source_id="batch-B",
            ))

    def tearDown(self):
        BrandictionStore._reset_instance()
        try:
            os.unlink(self.db)
        except OSError:
            pass

    def test_filter_source_type(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/signals?source_type=dtc_site")
            data = r.get_json()
            self.assertEqual(data["count"], 2)

    def test_filter_source_id(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/signals?source_id=batch-A")
            data = r.get_json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["signals"][0]["signal_id"], "s1")

    def test_filter_source_type_and_source_id(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/signals?source_type=dtc_site&source_id=batch-B")
            data = r.get_json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["signals"][0]["signal_id"], "s3")


if __name__ == "__main__":
    unittest.main()
