"""
PR-V3 测试 — HistoricalBaselineRanker + /race API

验证轨道 1（历史基线排序）的全链路：
  - 相似度匹配（精确 → 逐步放宽）
  - product_line / audience_segment / market 硬过滤
  - 多 outcome window 聚合口径
  - sort_by 校验
  - 多 plan 排序
  - /race API 双轨输出结构
"""

import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("MOODY_SECRET_KEY", "test-secret")
os.environ.setdefault("MOODY_UPLOAD_FOLDER", tempfile.mkdtemp())
os.environ.setdefault("MOODY_USERS", "slr:test-pass:Liren:admin")

from app.models.brandiction import HistoricalIntervention, HistoricalOutcomeWindow
from app.services.brandiction_store import BrandictionStore
from app.services.baseline_ranker import HistoricalBaselineRanker, VALID_SORT_FIELDS


def _fresh_store():
    BrandictionStore._reset_instance()
    db = os.path.join(tempfile.mkdtemp(), "test_ranker.db")
    return BrandictionStore(db)


def _seed_data(store):
    """Seed store with diverse interventions + outcomes for testing."""
    # Campaign A: redbook / social_seed / science / cn — good ROAS
    store.save_intervention(HistoricalIntervention(
        intervention_id="a1", run_id="r1", platform="redbook",
        channel_family="social_seed", theme="science", market="cn",
        product_line="moodyplus", audience_segment="general",
        budget=50000, spend=48000, date_start="2025-09-01",
    ))
    store.save_outcome(HistoricalOutcomeWindow(
        outcome_id="oa1", intervention_id="a1",
        roas=3.2, ctr=0.04, cvr=0.025,
        sessions=5000, purchases=400, aov=180.0, revenue=72000,
        date_start="2025-09-01",
    ))

    store.save_intervention(HistoricalIntervention(
        intervention_id="a2", run_id="r1", platform="redbook",
        channel_family="social_seed", theme="science", market="cn",
        product_line="moodyplus", audience_segment="general",
        budget=60000, spend=58000, date_start="2025-10-01",
    ))
    store.save_outcome(HistoricalOutcomeWindow(
        outcome_id="oa2", intervention_id="a2",
        roas=2.8, ctr=0.035, cvr=0.022,
        sessions=6000, purchases=480, aov=175.0, revenue=84000,
        date_start="2025-10-01",
    ))

    # Campaign B: douyin / short_video / beauty / cn — lower ROAS
    store.save_intervention(HistoricalIntervention(
        intervention_id="b1", run_id="r1", platform="douyin",
        channel_family="short_video", theme="beauty", market="cn",
        product_line="moodyplus", audience_segment="general",
        budget=80000, spend=78000, date_start="2025-09-15",
    ))
    store.save_outcome(HistoricalOutcomeWindow(
        outcome_id="ob1", intervention_id="b1",
        roas=1.5, ctr=0.06, cvr=0.015,
        sessions=12000, purchases=350, aov=160.0, revenue=56000,
        date_start="2025-09-15",
    ))

    store.save_intervention(HistoricalIntervention(
        intervention_id="b2", run_id="r1", platform="douyin",
        channel_family="short_video", theme="beauty", market="cn",
        product_line="moodyplus", audience_segment="general",
        budget=70000, spend=68000, date_start="2025-11-01",
    ))
    store.save_outcome(HistoricalOutcomeWindow(
        outcome_id="ob2", intervention_id="b2",
        roas=1.8, ctr=0.055, cvr=0.018,
        sessions=10000, purchases=380, aov=165.0, revenue=62700,
        date_start="2025-11-01",
    ))

    # Campaign C: google / search / science / us — different market
    store.save_intervention(HistoricalIntervention(
        intervention_id="c1", run_id="r1", platform="google",
        channel_family="search", theme="science", market="us",
        product_line="moodyplus", audience_segment="general",
        budget=40000, spend=38000, date_start="2025-10-01",
    ))
    store.save_outcome(HistoricalOutcomeWindow(
        outcome_id="oc1", intervention_id="c1",
        roas=4.0, ctr=0.03, cvr=0.03,
        sessions=3000, purchases=200, aov=220.0, revenue=44000,
        date_start="2025-10-01",
    ))


# =====================================================================
# 1. BaselineStats 计算
# =====================================================================

class TestQueryBaseline(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        _seed_data(self.store)
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_exact_match_redbook_science_cn(self):
        plan = {"platform": "redbook", "channel_family": "social_seed",
                "theme": "science", "market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.sample_size, 2)
        self.assertEqual(stats.match_quality, "exact")
        self.assertAlmostEqual(stats.roas_mean, 3.0, places=1)
        self.assertIsNotNone(stats.purchase_rate)
        self.assertGreater(stats.purchase_rate, 0)

    def test_exact_match_douyin_beauty(self):
        plan = {"platform": "douyin", "channel_family": "short_video",
                "theme": "beauty", "market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.sample_size, 2)
        self.assertAlmostEqual(stats.roas_mean, 1.65, places=1)

    def test_market_isolation_min1(self):
        """US plan should only find US data."""
        plan = {"platform": "google", "channel_family": "search",
                "theme": "science", "market": "us"}
        stats = self.ranker.query_baseline(plan, min_samples=1)
        self.assertEqual(stats.sample_size, 1)
        self.assertAlmostEqual(stats.roas_mean, 4.0, places=1)

    def test_market_isolation_strict(self):
        """US plan with min_samples=2 should not find enough."""
        plan = {"platform": "google", "channel_family": "search",
                "theme": "science", "market": "us"}
        stats = self.ranker.query_baseline(plan, min_samples=2)
        self.assertIn(stats.match_quality, ("partial", "fallback", "no_data"))

    def test_partial_match_fallback(self):
        """Plan with unknown landing_page should fall back to fewer match dims."""
        plan = {"platform": "redbook", "channel_family": "social_seed",
                "theme": "science", "market": "cn",
                "landing_page": "/nonexistent"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.sample_size, 2)

    def test_no_data(self):
        plan = {"platform": "snapchat", "market": "kr"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.sample_size, 0)
        self.assertEqual(stats.match_quality, "no_data")

    def test_stats_cpa(self):
        plan = {"platform": "redbook", "channel_family": "social_seed",
                "theme": "science", "market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertIsNotNone(stats.cpa)
        expected_cpa = (48000 + 58000) / (400 + 480)
        self.assertAlmostEqual(stats.cpa, expected_cpa, places=0)

    def test_stats_aov(self):
        plan = {"platform": "douyin", "theme": "beauty", "market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertIsNotNone(stats.aov_mean)
        self.assertAlmostEqual(stats.aov_mean, 162.5, places=0)


# =====================================================================
# 2. [High Fix] Market / product_line / audience_segment 硬过滤
# =====================================================================

class TestContextIsolation(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        _seed_data(self.store)
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_cn_plan_does_not_see_us_data(self):
        """CN plan should never include US data regardless of match relaxation."""
        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(plan, min_samples=1)
        # Should be 4 CN interventions, not 5
        self.assertEqual(stats.sample_size, 4)

    def test_us_plan_does_not_see_cn_data(self):
        plan = {"market": "us"}
        stats = self.ranker.query_baseline(plan, min_samples=1)
        self.assertEqual(stats.sample_size, 1)

    def test_cross_market_mixing_prevented(self):
        """
        Regression test: plan with only platform/channel_family/theme
        but explicit market should NOT mix markets.
        """
        # Add a CN google/search/science intervention
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="cn-google", run_id="r", platform="google",
            channel_family="search", theme="science", market="cn",
            product_line="moodyplus", spend=30000,
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="cn-google-oc", intervention_id="cn-google",
            roas=1.0,
        ))

        # US plan should still only see US data
        plan = {"platform": "google", "channel_family": "search",
                "theme": "science", "market": "us"}
        stats = self.ranker.query_baseline(plan, min_samples=1)
        self.assertEqual(stats.sample_size, 1)
        self.assertAlmostEqual(stats.roas_mean, 4.0, places=1)

    def test_product_line_isolation(self):
        """colored_lenses should not see moodyplus data."""
        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(
            plan, product_line="colored_lenses", min_samples=1,
        )
        self.assertEqual(stats.sample_size, 0)

    def test_audience_segment_isolation(self):
        """young_female segment should not see general data."""
        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(
            plan, audience_segment="young_female", min_samples=1,
        )
        self.assertEqual(stats.sample_size, 0)

    def test_match_dimensions_include_hard_filters(self):
        """match_dimensions should list hard filters."""
        plan = {"platform": "redbook", "channel_family": "social_seed",
                "theme": "science", "market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertIn("product_line", stats.match_dimensions)
        self.assertIn("audience_segment", stats.match_dimensions)
        self.assertIn("market", stats.match_dimensions)


# =====================================================================
# 3. [High Fix] 多 outcome window 聚合口径
# =====================================================================

class TestMultiWindowAggregation(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_multi_window_not_double_counted(self):
        """2 interventions, one with 2 windows: sample_size should be 2."""
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv1", run_id="r", market="cn",
            product_line="moodyplus", spend=30000,
        ))
        # week1 window
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="iv1-w1", intervention_id="iv1",
            window_label="week1",
            sessions=2000, purchases=100, revenue=20000,
            roas=2.0, date_start="2025-09-01",
        ))
        # month1 window (cumulative)
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="iv1-w2", intervention_id="iv1",
            window_label="month1",
            sessions=5000, purchases=300, revenue=60000,
            roas=3.0, date_start="2025-09-30",
        ))

        self.store.save_intervention(HistoricalIntervention(
            intervention_id="iv2", run_id="r", market="cn",
            product_line="moodyplus", spend=30000,
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="iv2-w1", intervention_id="iv2",
            sessions=4000, purchases=200, revenue=40000,
            roas=2.5, date_start="2025-10-01",
        ))

        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(plan)

        self.assertEqual(stats.sample_size, 2)

        # ROAS should use latest window per intervention:
        # iv1 latest = 3.0, iv2 = 2.5 → mean = 2.75
        self.assertAlmostEqual(stats.roas_mean, 2.75, places=2)

        # Sessions should be summed per intervention:
        # iv1 = 2000+5000=7000, iv2 = 4000 → mean = 5500
        self.assertAlmostEqual(stats.sessions_mean, 5500, places=0)

        # CPA = total_spend / total_purchases
        # iv1 purchases = 100+300=400, iv2 = 200
        # total_spend = 60000, total_purchases = 600
        self.assertAlmostEqual(stats.cpa, 60000 / 600, places=0)

    def test_single_window_same_as_before(self):
        """With single-window interventions, behavior should be identical."""
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="s1", run_id="r", market="cn",
            product_line="moodyplus", spend=50000,
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="s1-oc", intervention_id="s1",
            roas=3.0, sessions=5000, purchases=400,
        ))
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="s2", run_id="r", market="cn",
            product_line="moodyplus", spend=60000,
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="s2-oc", intervention_id="s2",
            roas=2.0, sessions=6000, purchases=300,
        ))

        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.sample_size, 2)
        self.assertAlmostEqual(stats.roas_mean, 2.5, places=1)
        self.assertAlmostEqual(stats.cpa, 110000 / 700, places=0)


# =====================================================================
# 3b. [Medium Fix] Sparse plan match_quality 不应虚标
# =====================================================================

class TestSparseMatchQuality(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        _seed_data(self.store)
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_market_only_plan_is_fallback(self):
        """Plan with only market should be fallback, not exact."""
        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(plan, min_samples=1)
        self.assertEqual(stats.match_quality, "fallback")
        # match_dimensions 不应包含 plan 没指定的软维度
        self.assertNotIn("platform", stats.match_dimensions)
        self.assertNotIn("channel_family", stats.match_dimensions)
        self.assertNotIn("theme", stats.match_dimensions)

    def test_one_soft_dim_is_partial(self):
        """Plan with market + channel_family should be partial."""
        plan = {"market": "cn", "channel_family": "social_seed"}
        stats = self.ranker.query_baseline(plan, min_samples=1)
        self.assertIn(stats.match_quality, ("exact", "partial"))
        self.assertIn("channel_family", stats.match_dimensions)
        self.assertNotIn("platform", stats.match_dimensions)

    def test_full_plan_is_exact(self):
        """Plan with all dims specified should be exact."""
        plan = {"platform": "redbook", "channel_family": "social_seed",
                "theme": "science", "market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.match_quality, "exact")
        self.assertIn("platform", stats.match_dimensions)
        self.assertIn("channel_family", stats.match_dimensions)
        self.assertIn("theme", stats.match_dimensions)

    def test_partial_when_relaxed(self):
        """Plan specifying platform+theme but no data for that combo → relaxes."""
        plan = {"platform": "bilibili", "theme": "science", "market": "cn"}
        stats = self.ranker.query_baseline(plan, min_samples=2)
        # No bilibili science data → will relax. Should NOT be "exact".
        if stats.sample_size > 0:
            self.assertNotEqual(stats.match_quality, "exact")


# =====================================================================
# 3c. [Medium Fix] Drift 使用最新 outcome window 日期
# =====================================================================

class TestDriftUsesLatestOutcomeDate(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_old_intervention_with_recent_outcome_included_in_drift(self):
        """
        iv1 started 2025-01-01 but has a recent outcome window.
        Drift should include iv1 when computing recent stats.
        """
        from datetime import datetime, timedelta

        recent_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        # iv1: old intervention, recent outcome
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="old-iv", run_id="r", market="cn",
            product_line="moodyplus", spend=30000,
            date_start="2025-01-01",
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="old-iv-w1", intervention_id="old-iv",
            roas=5.0, sessions=3000, purchases=300,
            date_start="2025-01-15",
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="old-iv-w2", intervention_id="old-iv",
            roas=4.5, sessions=4000, purchases=400,
            date_start=recent_date,  # recent window
        ))

        # iv2: recent intervention
        self.store.save_intervention(HistoricalIntervention(
            intervention_id="new-iv", run_id="r", market="cn",
            product_line="moodyplus", spend=30000,
            date_start=recent_date,
        ))
        self.store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="new-iv-w1", intervention_id="new-iv",
            roas=2.0, sessions=5000, purchases=200,
            date_start=recent_date,
        ))

        plan = {"market": "cn"}
        stats = self.ranker.query_baseline(plan)
        self.assertEqual(stats.sample_size, 2)

        # Both should be "recent" for 30d drift
        # If drift only used iv.date_start, old-iv (2025-01-01) would be excluded
        # With the fix, old-iv's latest_outcome_date is recent_date → included
        if stats.drift_30d is not None:
            # drift_30d.roas should be ~0 since both are in the recent set
            # (recent mean == overall mean when all are recent)
            self.assertAlmostEqual(stats.drift_30d.get("roas", 0), 0.0, places=1)


# =====================================================================
# 4. [Medium Fix] sort_by 校验
# =====================================================================

class TestSortByValidation(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        _seed_data(self.store)
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_valid_sort_fields(self):
        for field in VALID_SORT_FIELDS:
            plans = [{"platform": "redbook", "theme": "science", "market": "cn"}]
            result = self.ranker.rank_campaigns(plans, sort_by=field)
            self.assertIn("ranking", result)

    def test_invalid_sort_by_raises(self):
        plans = [{"market": "cn"}]
        with self.assertRaises(ValueError) as ctx:
            self.ranker.rank_campaigns(plans, sort_by="nonsense")
        self.assertIn("nonsense", str(ctx.exception))

    def test_empty_sort_by_raises(self):
        plans = [{"market": "cn"}]
        with self.assertRaises(ValueError):
            self.ranker.rank_campaigns(plans, sort_by="")


# =====================================================================
# 5. 排序
# =====================================================================

class TestRankCampaigns(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()
        _seed_data(self.store)
        self.ranker = HistoricalBaselineRanker(self.store)

    def test_rank_by_roas(self):
        plans = [
            {"name": "redbook-science", "platform": "redbook",
             "channel_family": "social_seed", "theme": "science", "market": "cn"},
            {"name": "douyin-beauty", "platform": "douyin",
             "channel_family": "short_video", "theme": "beauty", "market": "cn"},
        ]
        result = self.ranker.rank_campaigns(plans, sort_by="roas_mean")
        ranking = result["ranking"]
        self.assertEqual(len(ranking), 2)
        self.assertEqual(ranking[0]["plan"]["name"], "redbook-science")
        self.assertEqual(ranking[0]["rank"], 1)
        self.assertEqual(ranking[1]["rank"], 2)

    def test_rank_by_purchase_rate(self):
        plans = [
            {"name": "redbook-science", "platform": "redbook",
             "channel_family": "social_seed", "theme": "science", "market": "cn"},
            {"name": "douyin-beauty", "platform": "douyin",
             "channel_family": "short_video", "theme": "beauty", "market": "cn"},
        ]
        result = self.ranker.rank_campaigns(plans, sort_by="purchase_rate")
        ranking = result["ranking"]
        self.assertEqual(ranking[0]["plan"]["name"], "redbook-science")

    def test_rank_with_no_data_plan(self):
        plans = [
            {"name": "has-data", "platform": "redbook",
             "channel_family": "social_seed", "theme": "science", "market": "cn"},
            {"name": "no-data", "platform": "snapchat", "market": "kr"},
        ]
        result = self.ranker.rank_campaigns(plans)
        ranking = result["ranking"]
        self.assertEqual(ranking[0]["plan"]["name"], "has-data")
        self.assertTrue(ranking[0]["data_sufficient"])
        self.assertFalse(ranking[1]["data_sufficient"])

    def test_recommendation_text(self):
        plans = [
            {"name": "A", "platform": "redbook", "channel_family": "social_seed",
             "theme": "science", "market": "cn"},
        ]
        result = self.ranker.rank_campaigns(plans)
        self.assertIn("A", result["recommendation"])
        self.assertIn("历史", result["recommendation"])

    def test_single_plan(self):
        plans = [{"platform": "redbook", "theme": "science", "market": "cn"}]
        result = self.ranker.rank_campaigns(plans)
        self.assertEqual(len(result["ranking"]), 1)
        self.assertEqual(result["ranking"][0]["rank"], 1)


# =====================================================================
# 6. /race API 端点
# =====================================================================

from app import create_app


def _make_app():
    BrandictionStore._reset_instance()
    db = os.path.join(tempfile.mkdtemp(), "test_race_api.db")
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    BrandictionStore._reset_instance()
    with app.app_context():
        store = BrandictionStore(db_path=db)
        _seed_data(store)
    return app, db


def _user_session(client):
    with client.session_transaction() as sess:
        sess["user"] = {"username": "slr", "display_name": "Liren", "role": "admin"}


class TestRaceAPI(unittest.TestCase):
    def setUp(self):
        self.app, self.db = _make_app()

    def tearDown(self):
        BrandictionStore._reset_instance()
        try:
            os.unlink(self.db)
        except OSError:
            pass

    def test_race_returns_dual_track(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race", json={
                "plans": [
                    {"name": "A", "platform": "redbook", "theme": "science",
                     "channel_family": "social_seed", "market": "cn"},
                    {"name": "B", "platform": "douyin", "theme": "beauty",
                     "channel_family": "short_video", "market": "cn"},
                ],
            })
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertIn("observed_baseline", data)
            self.assertIn("model_hypothesis", data)
            baseline = data["observed_baseline"]
            self.assertIn("ranking", baseline)
            self.assertEqual(len(baseline["ranking"]), 2)
            self.assertEqual(baseline["ranking"][0]["rank"], 1)
            hyp = data["model_hypothesis"]
            self.assertIn("不参与排名", hyp["note"])

    def test_race_without_hypothesis(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race", json={
                "plans": [{"name": "A", "platform": "redbook", "market": "cn"}],
                "include_hypothesis": False,
            })
            data = r.get_json()
            self.assertIsNone(data["model_hypothesis"])
            self.assertIn("ranking", data["observed_baseline"])

    def test_race_requires_plans(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race", json={})
            self.assertEqual(r.status_code, 400)

    def test_race_requires_login(self):
        with self.app.test_client() as c:
            r = c.post("/api/brandiction/race", json={"plans": [{}]})
            self.assertEqual(r.status_code, 401)

    def test_race_invalid_sort_by_returns_400(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race", json={
                "plans": [{"market": "cn"}],
                "sort_by": "nonsense",
            })
            self.assertEqual(r.status_code, 400)
            self.assertIn("sort_by", r.get_json()["error"])

    def test_race_top_level_market_injected(self):
        """Top-level market should be injected into plans without their own."""
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race", json={
                "plans": [{"platform": "redbook", "theme": "science"}],
                "market": "cn",
                "include_hypothesis": False,
            })
            self.assertEqual(r.status_code, 200)
            ranking = r.get_json()["observed_baseline"]["ranking"]
            self.assertTrue(ranking[0]["data_sufficient"])

    def test_race_sort_by_purchase_rate(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race", json={
                "plans": [
                    {"name": "A", "platform": "redbook", "theme": "science", "market": "cn"},
                    {"name": "B", "platform": "douyin", "theme": "beauty", "market": "cn"},
                ],
                "sort_by": "purchase_rate",
                "include_hypothesis": False,
            })
            data = r.get_json()
            self.assertEqual(data["observed_baseline"]["sort_by"], "purchase_rate")


class TestRaceHistoryAPI(unittest.TestCase):
    def setUp(self):
        self.app, self.db = _make_app()

    def tearDown(self):
        BrandictionStore._reset_instance()
        try:
            os.unlink(self.db)
        except OSError:
            pass

    def test_race_auto_persists_run(self):
        """POST /race should auto-persist a race_run record."""
        with self.app.test_client() as c:
            _user_session(c)
            c.post("/api/brandiction/race", json={
                "plans": [{"name": "Test Plan", "platform": "redbook", "market": "cn"}],
                "include_hypothesis": False,
            })
            r = c.get("/api/brandiction/race-history")
            self.assertEqual(r.status_code, 200)
            runs = r.get_json()["runs"]
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["plans_count"], 1)
            self.assertEqual(runs[0]["status"], "pending")
            self.assertIn("Test Plan", runs[0]["top_recommendation"])

    def test_race_history_empty(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/race-history")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["runs"], [])

    def test_race_history_detail(self):
        with self.app.test_client() as c:
            _user_session(c)
            c.post("/api/brandiction/race", json={
                "plans": [{"name": "A", "platform": "redbook", "market": "cn"}],
                "include_hypothesis": False,
            })
            runs = c.get("/api/brandiction/race-history").get_json()["runs"]
            run_id = runs[0]["id"]
            r = c.get(f"/api/brandiction/race-history/{run_id}")
            self.assertEqual(r.status_code, 200)
            detail = r.get_json()
            self.assertIn("result", detail)
            self.assertIn("plans", detail)

    def test_race_history_detail_not_found(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/race-history/nonexistent")
            self.assertEqual(r.status_code, 404)

    def test_resolve_race_run(self):
        with self.app.test_client() as c:
            _user_session(c)
            c.post("/api/brandiction/race", json={
                "plans": [{"name": "A", "platform": "redbook", "market": "cn"}],
                "include_hypothesis": False,
            })
            runs = c.get("/api/brandiction/race-history").get_json()["runs"]
            run_id = runs[0]["id"]
            r = c.post(f"/api/brandiction/race-history/{run_id}/resolve", json={
                "status": "verified", "hit": True,
            })
            self.assertEqual(r.status_code, 200)
            updated = c.get(f"/api/brandiction/race-history/{run_id}").get_json()
            self.assertEqual(updated["status"], "verified")
            self.assertTrue(updated["hit"])

    def test_resolve_not_found(self):
        with self.app.test_client() as c:
            _user_session(c)
            r = c.post("/api/brandiction/race-history/fake/resolve", json={
                "status": "verified", "hit": False,
            })
            self.assertEqual(r.status_code, 404)

    def test_stats_v3_format(self):
        """GET /stats should return V3 dashboard format."""
        with self.app.test_client() as c:
            _user_session(c)
            r = c.get("/api/brandiction/stats")
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            self.assertIn("interventions_count", data)
            self.assertIn("outcomes_count", data)
            self.assertIn("signals_count", data)
            self.assertIn("competitor_events_count", data)
            self.assertIn("market_coverage", data)
            self.assertIn("platform_coverage", data)
            self.assertIn("weakest_dimensions", data)
            self.assertIsInstance(data["market_coverage"], dict)


if __name__ == "__main__":
    unittest.main()
