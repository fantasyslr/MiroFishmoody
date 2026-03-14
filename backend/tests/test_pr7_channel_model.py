"""
PR7: 三层渠道模型测试 — channel_family → platform → market

测试范围：
  1. 数据结构完整性（CHANNEL_FAMILIES, PLATFORM_REGISTRY, MARKET_ADJUSTMENTS）
  2. _build_channel_effectiveness() 生成逻辑
  3. 平台 override 机制
  4. _apply_channel_scaling() 的 market 参数
  5. market 参数在 predict/simulate/compare/backtest 的端到端传递
  6. 未知平台和未知 market 的 fallback
  7. 向后兼容性：cn market = 旧行为
  8. signal 层市场隔离 — 不同 market 的 signals 构出不同初始 state
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.brand_state_engine import (
    CHANNEL_FAMILIES,
    PLATFORM_REGISTRY,
    MARKET_ADJUSTMENTS,
    CHANNEL_EFFECTIVENESS,
    _build_channel_effectiveness,
    BrandStateEngine,
    PERCEPTION_DIMENSIONS,
)
from app.models.brand_state import PERCEPTION_DIMENSIONS as PD
from app.models.brandiction import HistoricalIntervention, HistoricalOutcomeWindow
from app.services.brandiction_store import BrandictionStore


def _fresh_engine():
    return BrandStateEngine(BrandictionStore())


class TestChannelFamilies(unittest.TestCase):
    """Layer 1: 渠道家族结构"""

    def test_all_families_have_coefficients(self):
        """每个 family 至少有一个维度系数"""
        for fam, dims in CHANNEL_FAMILIES.items():
            self.assertGreater(len(dims), 0, f"family '{fam}' 没有维度系数")

    def test_family_dimensions_are_valid(self):
        """family 系数中的维度名都在 PERCEPTION_DIMENSIONS 中"""
        for fam, dims in CHANNEL_FAMILIES.items():
            for d in dims:
                self.assertIn(d, PERCEPTION_DIMENSIONS, f"family '{fam}' 包含无效维度 '{d}'")

    def test_expected_families_exist(self):
        expected = {"short_video", "social_seed", "longform_content", "marketplace",
                    "search", "dtc_site", "crm", "influencer", "offline"}
        self.assertEqual(set(CHANNEL_FAMILIES.keys()), expected)


class TestPlatformRegistry(unittest.TestCase):
    """Layer 2: 平台注册表"""

    def test_all_platforms_reference_valid_family(self):
        """每个 platform 的 family 都存在于 CHANNEL_FAMILIES"""
        for platform, (family, _) in PLATFORM_REGISTRY.items():
            self.assertIn(family, CHANNEL_FAMILIES, f"platform '{platform}' 引用了不存在的 family '{family}'")

    def test_override_dimensions_are_valid(self):
        """平台 override 中的维度名都合法"""
        for platform, (_, overrides) in PLATFORM_REGISTRY.items():
            for d in overrides:
                self.assertIn(d, PERCEPTION_DIMENSIONS, f"platform '{platform}' override 包含无效维度 '{d}'")

    def test_domestic_platforms_present(self):
        domestic = {"douyin", "kuaishou", "redbook", "weibo", "wechat",
                    "bilibili", "zhihu", "tmall", "jd", "pdd", "dewu"}
        for p in domestic:
            self.assertIn(p, PLATFORM_REGISTRY, f"国内平台 '{p}' 缺失")

    def test_international_platforms_present(self):
        intl = {"tiktok", "instagram", "youtube", "facebook", "pinterest",
                "amazon", "shopee", "lazada", "rakuten"}
        for p in intl:
            self.assertIn(p, PLATFORM_REGISTRY, f"海外平台 '{p}' 缺失")

    def test_dtc_platforms_present(self):
        dtc = {"shopify", "dtc", "landing_page"}
        for p in dtc:
            self.assertIn(p, PLATFORM_REGISTRY, f"DTC 平台 '{p}' 缺失")

    def test_crm_platforms_present(self):
        crm = {"email", "sms", "wechat_crm", "line"}
        for p in crm:
            self.assertIn(p, PLATFORM_REGISTRY, f"CRM 平台 '{p}' 缺失")

    def test_influencer_platforms_present(self):
        inf = {"kol", "koc", "affiliate"}
        for p in inf:
            self.assertIn(p, PLATFORM_REGISTRY, f"Influencer 平台 '{p}' 缺失")

    def test_offline_platforms_present(self):
        off = {"offline", "pop_up", "optical_shop"}
        for p in off:
            self.assertIn(p, PLATFORM_REGISTRY, f"线下渠道 '{p}' 缺失")


class TestMarketAdjustments(unittest.TestCase):
    """Layer 3: 市场调节系数"""

    def test_cn_is_neutral(self):
        """cn 市场应为空 dict（基准市场）"""
        self.assertEqual(MARKET_ADJUSTMENTS["cn"], {})

    def test_expected_markets_exist(self):
        expected = {"cn", "us", "jp", "sea", "eu", "kr"}
        self.assertEqual(set(MARKET_ADJUSTMENTS.keys()), expected)

    def test_market_dimensions_are_valid(self):
        for market, dims in MARKET_ADJUSTMENTS.items():
            for d in dims:
                self.assertIn(d, PERCEPTION_DIMENSIONS, f"market '{market}' 包含无效维度 '{d}'")

    def test_jp_high_science_credibility(self):
        """日本市场应该对 science_credibility 有正向调节"""
        self.assertGreater(MARKET_ADJUSTMENTS["jp"]["science_credibility"], 1.0)

    def test_sea_high_price_sensitivity(self):
        """东南亚市场应该对 price_sensitivity 有正向调节"""
        self.assertGreater(MARKET_ADJUSTMENTS["sea"]["price_sensitivity"], 1.0)

    def test_kr_high_aesthetic_affinity(self):
        """韩国市场应该对 aesthetic_affinity 有正向调节"""
        self.assertGreater(MARKET_ADJUSTMENTS["kr"]["aesthetic_affinity"], 1.0)


class TestBuildChannelEffectiveness(unittest.TestCase):
    """_build_channel_effectiveness 生成 + override 机制"""

    def test_all_platforms_have_effectiveness(self):
        """CHANNEL_EFFECTIVENESS 包含 PLATFORM_REGISTRY 中的所有平台"""
        for p in PLATFORM_REGISTRY:
            self.assertIn(p, CHANNEL_EFFECTIVENESS)

    def test_douyin_inherits_short_video(self):
        """douyin (无 override) 应完全继承 short_video family"""
        eff = CHANNEL_EFFECTIVENESS["douyin"]
        for dim, val in CHANNEL_FAMILIES["short_video"].items():
            self.assertAlmostEqual(eff[dim], val)

    def test_redbook_override_aesthetic(self):
        """redbook 对 aesthetic_affinity 有 override，应覆盖 social_seed 的值"""
        eff = CHANNEL_EFFECTIVENESS["redbook"]
        # social_seed base = 1.3, override = 1.4
        self.assertAlmostEqual(eff["aesthetic_affinity"], 1.4)

    def test_bilibili_override_science(self):
        """bilibili 对 science_credibility 有 override = 1.4"""
        eff = CHANNEL_EFFECTIVENESS["bilibili"]
        self.assertAlmostEqual(eff["science_credibility"], 1.4)

    def test_pdd_override_price(self):
        """pdd 对 price_sensitivity 有 override = 1.5"""
        eff = CHANNEL_EFFECTIVENESS["pdd"]
        self.assertAlmostEqual(eff["price_sensitivity"], 1.5)

    def test_koc_override_skepticism(self):
        """koc 对 skepticism 有 override = 0.9 (更真实，质疑少)"""
        eff = CHANNEL_EFFECTIVENESS["koc"]
        self.assertAlmostEqual(eff["skepticism"], 0.9)

    def test_optical_shop_override_comfort(self):
        """optical_shop override comfort_trust = 1.5"""
        eff = CHANNEL_EFFECTIVENESS["optical_shop"]
        self.assertAlmostEqual(eff["comfort_trust"], 1.5)

    def test_rebuild_matches_constant(self):
        """重新 build 的结果应与模块级常量一致"""
        rebuilt = _build_channel_effectiveness()
        self.assertEqual(set(rebuilt.keys()), set(CHANNEL_EFFECTIVENESS.keys()))
        for p in rebuilt:
            for dim in rebuilt[p]:
                self.assertAlmostEqual(rebuilt[p][dim], CHANNEL_EFFECTIVENESS[p][dim])


class TestApplyChannelScalingMarket(unittest.TestCase):
    """_apply_channel_scaling 的 market 参数测试"""

    def _base_delta(self):
        return {d: 0.1 for d in PERCEPTION_DIMENSIONS}

    def test_cn_market_no_change(self):
        """cn market 应与无 market 参数效果一致（基准市场）"""
        delta = self._base_delta()
        result_cn = BrandStateEngine._apply_channel_scaling(delta, ["douyin"], market="cn")
        result_default = BrandStateEngine._apply_channel_scaling(delta, ["douyin"])
        for d in PERCEPTION_DIMENSIONS:
            self.assertAlmostEqual(result_cn[d], result_default[d])

    def test_jp_market_boosts_science(self):
        """jp market 应该增强 science_credibility"""
        delta = self._base_delta()
        result_cn = BrandStateEngine._apply_channel_scaling(delta, ["douyin"], market="cn")
        result_jp = BrandStateEngine._apply_channel_scaling(delta, ["douyin"], market="jp")
        self.assertGreater(result_jp["science_credibility"], result_cn["science_credibility"])

    def test_sea_market_boosts_price_sensitivity(self):
        """sea market 应该增强 price_sensitivity"""
        delta = self._base_delta()
        result_cn = BrandStateEngine._apply_channel_scaling(delta, ["tmall"], market="cn")
        result_sea = BrandStateEngine._apply_channel_scaling(delta, ["tmall"], market="sea")
        self.assertGreater(result_sea["price_sensitivity"], result_cn["price_sensitivity"])

    def test_kr_market_boosts_aesthetic(self):
        """kr market 应该增强 aesthetic_affinity"""
        delta = self._base_delta()
        result_cn = BrandStateEngine._apply_channel_scaling(delta, ["instagram"], market="cn")
        result_kr = BrandStateEngine._apply_channel_scaling(delta, ["instagram"], market="kr")
        self.assertGreater(result_kr["aesthetic_affinity"], result_cn["aesthetic_affinity"])

    def test_unknown_market_no_adjustment(self):
        """未知 market 不应有调节"""
        delta = self._base_delta()
        result_cn = BrandStateEngine._apply_channel_scaling(delta, ["douyin"], market="cn")
        result_xx = BrandStateEngine._apply_channel_scaling(delta, ["douyin"], market="xx")
        for d in PERCEPTION_DIMENSIONS:
            self.assertAlmostEqual(result_cn[d], result_xx[d])

    def test_market_applied_without_channel_mix(self):
        """即使没有 channel_mix，market 调节也应生效"""
        delta = self._base_delta()
        result = BrandStateEngine._apply_channel_scaling(delta, None, market="jp")
        # jp has science_credibility: 1.2, so 0.1 * 1.2 = 0.12
        self.assertAlmostEqual(result["science_credibility"], 0.12)

    def test_market_stacks_with_channel(self):
        """market 调节应叠加在渠道效能之上"""
        delta = self._base_delta()
        # bilibili: science_credibility = 1.4 (override)
        # jp market: science_credibility = 1.2
        # 最终 science_credibility = 0.1 * 1.4 * 1.2 = 0.168
        result = BrandStateEngine._apply_channel_scaling(delta, ["bilibili"], market="jp")
        self.assertAlmostEqual(result["science_credibility"], 0.168, places=3)

    def test_us_market_reduces_social_proof(self):
        """us market social_proof=0.9 应降低社交证明"""
        delta = self._base_delta()
        result_cn = BrandStateEngine._apply_channel_scaling(delta, ["redbook"], market="cn")
        result_us = BrandStateEngine._apply_channel_scaling(delta, ["instagram"], market="us")
        # Both are social_seed family with same social_proof base (1.2)
        # instagram has no social_proof override, so eff = 1.2
        # us market: social_proof *= 0.9 → 0.1 * 1.2 * 0.9 = 0.108
        self.assertAlmostEqual(result_us["social_proof"], 0.108, places=3)


class TestUnknownPlatformFallback(unittest.TestCase):
    """未知渠道的 fallback 行为"""

    def test_unknown_channel_defaults_to_1(self):
        """未知渠道应使用 1.0 系数（不影响 delta）"""
        delta = {d: 0.1 for d in PERCEPTION_DIMENSIONS}
        result = BrandStateEngine._apply_channel_scaling(delta, ["unknown_platform"])
        for d in PERCEPTION_DIMENSIONS:
            self.assertAlmostEqual(result[d], 0.1)

    def test_mixed_known_unknown_channels(self):
        """已知 + 未知渠道混合时，取平均"""
        delta = {d: 0.1 for d in PERCEPTION_DIMENSIONS}
        # douyin (short_video): social_proof=1.3
        # unknown: social_proof=1.0 (default)
        # 平均 = 1.15
        result = BrandStateEngine._apply_channel_scaling(delta, ["douyin", "unknown_platform"])
        self.assertAlmostEqual(result["social_proof"], 0.1 * 1.15, places=3)


class TestNewPlatformEndToEnd(unittest.TestCase):
    """新平台（国际/DTC/CRM）在预测中的端到端表现"""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_predict_with_tiktok(self):
        """用 tiktok 预测应正常返回"""
        plan = {"theme": "beauty", "channel_mix": ["tiktok"], "budget": 50000}
        result = self.engine.predict_impact(plan, product_line="moodyplus")
        self.assertIn("delta", result)
        self.assertIn("confidence", result)

    def test_predict_with_shopee(self):
        """用 shopee 预测应正常返回"""
        plan = {"theme": "comfort", "channel_mix": ["shopee"], "budget": 50000}
        result = self.engine.predict_impact(plan, product_line="moodyplus")
        self.assertIn("delta", result)

    def test_predict_with_email_crm(self):
        """用 email (CRM) 预测"""
        plan = {"theme": "comfort", "channel_mix": ["email"], "budget": 10000}
        result = self.engine.predict_impact(plan, product_line="moodyplus")
        self.assertIn("delta", result)

    def test_predict_with_koc(self):
        """用 koc (influencer) 预测"""
        plan = {"theme": "social", "channel_mix": ["koc"], "budget": 30000}
        result = self.engine.predict_impact(plan, product_line="moodyplus")
        self.assertIn("delta", result)

    def test_predict_with_optical_shop(self):
        """用 optical_shop (线下) 预测"""
        plan = {"theme": "science", "channel_mix": ["optical_shop"], "budget": 20000}
        result = self.engine.predict_impact(plan, product_line="moodyplus")
        self.assertIn("delta", result)

    def test_predict_with_shopify_dtc(self):
        """用 shopify (DTC) 预测"""
        plan = {"theme": "comfort", "channel_mix": ["shopify"], "budget": 30000}
        result = self.engine.predict_impact(plan, product_line="moodyplus")
        self.assertIn("delta", result)

    def test_crm_reduces_skepticism(self):
        """CRM 渠道 skepticism 系数 < 1.0，应降低质疑 delta"""
        delta = {d: 0.1 for d in PERCEPTION_DIMENSIONS}
        result = BrandStateEngine._apply_channel_scaling(delta, ["wechat_crm"])
        # crm family: skepticism=0.8
        self.assertLess(result["skepticism"], 0.1)

    def test_influencer_boosts_social_proof(self):
        """influencer 渠道 social_proof=1.4 应增强社交证明"""
        delta = {d: 0.1 for d in PERCEPTION_DIMENSIONS}
        result = BrandStateEngine._apply_channel_scaling(delta, ["kol"])
        self.assertGreater(result["social_proof"], 0.1)


class TestMarketInPredictFlow(unittest.TestCase):
    """market 参数在 predict_impact 中的传递"""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_predict_with_market_jp(self):
        """predict_impact 传入 market=jp 应正常返回"""
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000}
        result = self.engine.predict_impact(plan, market="jp")
        self.assertIn("delta", result)

    def test_compute_impact_jp_vs_cn_science_differs(self):
        """jp market 对 science_credibility 有 1.2x 调节，应严格大于 cn"""
        iv = HistoricalIntervention(
            intervention_id="mkt-test-1", run_id="mkt",
            theme="science", product_line="moodyplus",
            channel_mix=["bilibili"], budget=50000,
        )
        delta_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        delta_jp = self.engine.compute_intervention_impact(iv, [], market="jp")
        # jp science_credibility = cn × 1.2
        self.assertGreater(abs(delta_jp["science_credibility"]), abs(delta_cn["science_credibility"]))
        # 精确验证：bilibili science_credibility=1.4, jp market 1.2x → 0.05*1.4*1.2 vs 0.05*1.4
        self.assertAlmostEqual(delta_jp["science_credibility"] / delta_cn["science_credibility"], 1.2, places=2)

    def test_compute_impact_kr_vs_cn_aesthetic_differs(self):
        """kr market 对 aesthetic_affinity 有 1.3x 调节"""
        iv = HistoricalIntervention(
            intervention_id="mkt-test-2", run_id="mkt",
            theme="beauty", product_line="moodyplus",
            channel_mix=["instagram"], budget=50000,
        )
        delta_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        delta_kr = self.engine.compute_intervention_impact(iv, [], market="kr")
        self.assertGreater(abs(delta_kr["aesthetic_affinity"]), abs(delta_cn["aesthetic_affinity"]))

    def test_compute_impact_sea_vs_cn_price_differs(self):
        """sea market 对 price_sensitivity 有 1.3x 调节"""
        iv = HistoricalIntervention(
            intervention_id="mkt-test-3", run_id="mkt",
            theme="price", product_line="moodyplus",
            channel_mix=["shopee"], budget=30000,
        )
        delta_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        delta_sea = self.engine.compute_intervention_impact(iv, [], market="sea")
        self.assertGreater(abs(delta_sea["price_sensitivity"]), abs(delta_cn["price_sensitivity"]))


class TestMarketInSimulateFlow(unittest.TestCase):
    """market 参数在 simulate_scenario 中的传递"""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_simulate_with_market(self):
        """simulate_scenario 传入 market=kr 应正常返回"""
        steps = [{"theme": "beauty", "channel_mix": ["instagram"], "budget": 50000}]
        result = self.engine.simulate_scenario(steps=steps, market="kr")
        self.assertIn("timeline", result)
        self.assertEqual(len(result["timeline"]), 1)

    def test_simulate_kr_vs_cn_aesthetic_differs(self):
        """kr 市场应使 aesthetic_affinity 变化 >= cn"""
        steps = [{"theme": "beauty", "channel_mix": ["instagram"], "budget": 30000}]
        result_cn = self.engine.simulate_scenario(steps=steps, market="cn")
        result_kr = self.engine.simulate_scenario(steps=steps, market="kr")
        delta_cn = result_cn["cumulative_delta"]["aesthetic_affinity"]
        delta_kr = result_kr["cumulative_delta"]["aesthetic_affinity"]
        self.assertGreaterEqual(abs(delta_kr), abs(delta_cn))


class TestMarketInCompareFlow(unittest.TestCase):
    """market 参数在 compare_scenarios 中的传递"""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_compare_with_market(self):
        """compare_scenarios 传入 market=us 应正常返回"""
        scenarios = [
            {"name": "science", "steps": [{"theme": "science", "channel_mix": ["youtube"]}]},
            {"name": "beauty", "steps": [{"theme": "beauty", "channel_mix": ["instagram"]}]},
        ]
        result = self.engine.compare_scenarios(scenarios=scenarios, market="us")
        self.assertIn("scenarios", result)
        self.assertEqual(len(result["scenarios"]), 2)


class TestMarketInBacktestFlow(unittest.TestCase):
    """market 参数在 backtest 中的传递"""

    def setUp(self):
        self.engine = _fresh_engine()
        store = self.engine.store
        # 插入测试数据
        from app.models.brandiction import HistoricalIntervention, HistoricalOutcomeWindow
        iv = HistoricalIntervention(
            intervention_id="bt-mkt-1",
            run_id="bt-mkt",
            theme="science",
            product_line="moodyplus",
            channel_mix=["bilibili"],
            budget=50000,
            date_start="2025-01-01",
            date_end="2025-01-31",
            market="jp",
        )
        store.save_intervention(iv)
        oc = HistoricalOutcomeWindow(
            outcome_id="oc-mkt-1",
            intervention_id="bt-mkt-1",
            brand_lift=0.05,
            comment_sentiment=0.6,
        )
        store.save_outcome(oc)

    def test_backtest_with_market(self):
        """backtest 传入 market=jp 应正常返回"""
        result = self.engine.backtest(market="jp")
        self.assertIn("tested", result)
        self.assertGreaterEqual(result["tested"], 1)


class TestBackwardCompatibility(unittest.TestCase):
    """向后兼容：所有旧的渠道名仍然可用"""

    ORIGINAL_CHANNELS = ["douyin", "redbook", "bilibili", "weibo", "wechat", "tmall", "jd", "kuaishou"]

    def test_all_original_channels_in_registry(self):
        for ch in self.ORIGINAL_CHANNELS:
            self.assertIn(ch, PLATFORM_REGISTRY, f"原始渠道 '{ch}' 在 PLATFORM_REGISTRY 中缺失")
            self.assertIn(ch, CHANNEL_EFFECTIVENESS, f"原始渠道 '{ch}' 在 CHANNEL_EFFECTIVENESS 中缺失")

    def test_default_market_cn_preserves_behavior(self):
        """默认 market=cn 时，compute_intervention_impact 结果与不传 market 一致"""
        engine = _fresh_engine()
        iv = HistoricalIntervention(
            intervention_id="compat-1", run_id="compat",
            theme="science", product_line="moodyplus",
            channel_mix=["douyin", "bilibili"], budget=50000,
        )
        result_default = engine.compute_intervention_impact(iv, [])
        result_cn = engine.compute_intervention_impact(iv, [], market="cn")
        for d in PERCEPTION_DIMENSIONS:
            self.assertAlmostEqual(result_default[d], result_cn[d])


class TestNoOutcomesBranchMarket(unittest.TestCase):
    """回归测试：compute_intervention_impact no-outcomes 分支正确传递 market"""

    def setUp(self):
        self.engine = _fresh_engine()

    def _make_iv(self, theme="science", channel_mix=None, budget=50000):
        return HistoricalIntervention(
            intervention_id="no-oc-test", run_id="no-oc",
            theme=theme, product_line="moodyplus",
            channel_mix=channel_mix, budget=budget,
        )

    def test_no_outcomes_cn_ne_jp_with_channel(self):
        """严格回归：cn != jp，有渠道，no outcomes"""
        iv = self._make_iv(channel_mix=["bilibili"])
        d_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        d_jp = self.engine.compute_intervention_impact(iv, [], market="jp")
        # jp science_credibility 应严格大于 cn（1.2x 调节）
        self.assertGreater(d_jp["science_credibility"], d_cn["science_credibility"])
        # jp comfort_trust 也应更大（1.2x）
        # bilibili longform_content comfort_trust=1.2, no override
        # cn: 0 (no theme push on comfort_trust), jp: 0 × 1.2 = 0 — 只有被推动的维度才有差异
        # 但 science 有 0.05 base push → cn: 0.05*1.4 = 0.07, jp: 0.05*1.4*1.2 = 0.084
        ratio = d_jp["science_credibility"] / d_cn["science_credibility"]
        self.assertAlmostEqual(ratio, 1.2, places=2)

    def test_no_outcomes_cn_ne_jp_no_channel(self):
        """严格回归：cn != jp，无渠道，no outcomes"""
        iv = self._make_iv(channel_mix=None)
        d_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        d_jp = self.engine.compute_intervention_impact(iv, [], market="jp")
        self.assertGreater(d_jp["science_credibility"], d_cn["science_credibility"])
        ratio = d_jp["science_credibility"] / d_cn["science_credibility"]
        self.assertAlmostEqual(ratio, 1.2, places=2)

    def test_no_outcomes_cn_ne_kr_with_channel(self):
        """严格回归：cn != kr，有渠道，no outcomes"""
        iv = self._make_iv(theme="beauty", channel_mix=["instagram"])
        d_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        d_kr = self.engine.compute_intervention_impact(iv, [], market="kr")
        # kr aesthetic_affinity 应严格大于 cn（1.3x 调节）
        self.assertGreater(d_kr["aesthetic_affinity"], d_cn["aesthetic_affinity"])
        ratio = d_kr["aesthetic_affinity"] / d_cn["aesthetic_affinity"]
        self.assertAlmostEqual(ratio, 1.3, places=2)

    def test_no_outcomes_cn_ne_kr_no_channel(self):
        """严格回归：cn != kr，无渠道，no outcomes"""
        iv = self._make_iv(theme="beauty", channel_mix=None)
        d_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        d_kr = self.engine.compute_intervention_impact(iv, [], market="kr")
        self.assertGreater(d_kr["aesthetic_affinity"], d_cn["aesthetic_affinity"])
        ratio = d_kr["aesthetic_affinity"] / d_cn["aesthetic_affinity"]
        self.assertAlmostEqual(ratio, 1.3, places=2)

    def test_no_outcomes_cn_ne_sea_price(self):
        """严格回归：cn != sea price_sensitivity"""
        iv = self._make_iv(theme="price", channel_mix=["shopee"])
        d_cn = self.engine.compute_intervention_impact(iv, [], market="cn")
        d_sea = self.engine.compute_intervention_impact(iv, [], market="sea")
        self.assertGreater(d_sea["price_sensitivity"], d_cn["price_sensitivity"])
        ratio = d_sea["price_sensitivity"] / d_cn["price_sensitivity"]
        self.assertAlmostEqual(ratio, 1.3, places=2)


class TestMarketIsolation(unittest.TestCase):
    """跨市场隔离：cn/jp intervention 不互相干扰"""

    def setUp(self):
        self.engine = _fresh_engine()
        store = self.engine.store
        # cn 市场的 intervention
        iv_cn = HistoricalIntervention(
            intervention_id="iso-cn-1", run_id="iso",
            theme="science", product_line="moodyplus",
            channel_mix=["bilibili"], budget=50000,
            date_start="2025-01-01", date_end="2025-01-31",
            market="cn",
        )
        store.save_intervention(iv_cn)
        oc_cn = HistoricalOutcomeWindow(
            outcome_id="iso-oc-cn-1", intervention_id="iso-cn-1",
            brand_lift=0.08, comment_sentiment=0.7,
        )
        store.save_outcome(oc_cn)
        # jp 市场的 intervention
        iv_jp = HistoricalIntervention(
            intervention_id="iso-jp-1", run_id="iso",
            theme="science", product_line="moodyplus",
            channel_mix=["bilibili"], budget=50000,
            date_start="2025-02-01", date_end="2025-02-28",
            market="jp",
        )
        store.save_intervention(iv_jp)
        oc_jp = HistoricalOutcomeWindow(
            outcome_id="iso-oc-jp-1", intervention_id="iso-jp-1",
            brand_lift=0.12, comment_sentiment=0.9,
        )
        store.save_outcome(oc_jp)

    def test_replay_cn_only_sees_cn(self):
        """replay market=cn 只处理 cn intervention"""
        states = self.engine.replay_history(market="cn")
        iv_ids = [s.state_id for s in states if s.state_id.startswith("bs-after-")]
        self.assertTrue(any("iso-cn-1" in sid for sid in iv_ids))
        self.assertFalse(any("iso-jp-1" in sid for sid in iv_ids))

    def test_replay_jp_only_sees_jp(self):
        """replay market=jp 只处理 jp intervention"""
        states = self.engine.replay_history(market="jp")
        iv_ids = [s.state_id for s in states if s.state_id.startswith("bs-after-")]
        self.assertTrue(any("iso-jp-1" in sid for sid in iv_ids))
        self.assertFalse(any("iso-cn-1" in sid for sid in iv_ids))

    def test_replay_cn_jp_no_id_collision(self):
        """cn 和 jp replay 的确定性 ID 不会互相覆盖"""
        states_cn = self.engine.replay_history(market="cn")
        states_jp = self.engine.replay_history(market="jp")
        ids_cn = {s.state_id for s in states_cn}
        ids_jp = {s.state_id for s in states_jp}
        # 两个市场的 state_id 不应有交集
        self.assertEqual(ids_cn & ids_jp, set())

    def test_backtest_cn_only_sees_cn(self):
        """backtest market=cn 只测试 cn intervention"""
        result = self.engine.backtest(market="cn")
        tested_ids = [d["intervention_id"] for d in result["details"]]
        self.assertIn("iso-cn-1", tested_ids)
        self.assertNotIn("iso-jp-1", tested_ids)

    def test_backtest_jp_only_sees_jp(self):
        """backtest market=jp 只测试 jp intervention"""
        result = self.engine.backtest(market="jp")
        tested_ids = [d["intervention_id"] for d in result["details"]]
        self.assertIn("iso-jp-1", tested_ids)
        self.assertNotIn("iso-cn-1", tested_ids)

    def test_predict_cn_uses_cn_history(self):
        """predict market=cn 查找历史只用 cn 数据"""
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000}
        result_cn = self.engine.predict_impact(plan, market="cn")
        result_jp = self.engine.predict_impact(plan, market="jp")
        # cn 有 1 条历史 (brand_lift=0.08)，jp 有 1 条 (brand_lift=0.12)
        # 它们基于不同历史数据，所以 delta 应不同
        self.assertNotEqual(
            result_cn["delta"]["science_credibility"],
            result_jp["delta"]["science_credibility"],
        )

    def test_brand_state_market_persisted(self):
        """replay 生成的 BrandState 应包含 market 字段"""
        states = self.engine.replay_history(market="jp")
        for s in states:
            self.assertEqual(s.market, "jp")

    def test_competitor_events_market_isolated_replay(self):
        """competitor_events from one market must not leak into another market's replay"""
        from app.models.brandiction import CompetitorEvent
        store = self.engine.store
        # cn 竞品事件
        store.save_competitor_event(CompetitorEvent(
            event_id="ce-cn-1", date="2025-01-15",
            competitor="acuvue", market="cn",
            event_type="price_cut", impact_estimate="high",
        ))
        # jp 竞品事件
        store.save_competitor_event(CompetitorEvent(
            event_id="ce-jp-1", date="2025-02-15",
            competitor="seed", market="jp",
            event_type="new_launch", impact_estimate="medium",
        ))

        # list_competitor_events 按 market 正确过滤
        cn_events = store.list_competitor_events(market="cn")
        jp_events = store.list_competitor_events(market="jp")
        cn_ids = {e.event_id for e in cn_events}
        jp_ids = {e.event_id for e in jp_events}
        self.assertIn("ce-cn-1", cn_ids)
        self.assertNotIn("ce-jp-1", cn_ids)
        self.assertIn("ce-jp-1", jp_ids)
        self.assertNotIn("ce-cn-1", jp_ids)

        # replay cn 不应受 jp 竞品事件影响（反之亦然）
        states_cn = self.engine.replay_history(market="cn")
        states_jp = self.engine.replay_history(market="jp")
        # 两个市场的 replay 应独立完成
        self.assertTrue(len(states_cn) > 0)
        self.assertTrue(len(states_jp) > 0)

    def test_competitor_events_market_isolated_backtest(self):
        """competitor_events from one market must not leak into another market's backtest"""
        from app.models.brandiction import CompetitorEvent
        store = self.engine.store
        store.save_competitor_event(CompetitorEvent(
            event_id="ce-bt-cn-1", date="2025-01-15",
            competitor="acuvue", market="cn",
            event_type="campaign", impact_estimate="high",
        ))
        store.save_competitor_event(CompetitorEvent(
            event_id="ce-bt-jp-1", date="2025-02-15",
            competitor="seed", market="jp",
            event_type="new_launch", impact_estimate="high",
        ))
        # backtest for cn should not include jp competitor events
        result_cn = self.engine.backtest(market="cn")
        result_jp = self.engine.backtest(market="jp")
        # Both should complete without error
        self.assertIn("tested", result_cn)
        self.assertIn("tested", result_jp)

    def test_competitor_event_market_field_persisted(self):
        """CompetitorEvent.market field round-trips through DB"""
        from app.models.brandiction import CompetitorEvent
        store = self.engine.store
        store.save_competitor_event(CompetitorEvent(
            event_id="ce-persist-1", date="2025-03-01",
            competitor="alcon", market="us",
            event_type="price_cut",
        ))
        events = store.list_competitor_events(market="us")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].market, "us")
        self.assertEqual(events[0].competitor, "alcon")
        # Should not appear in cn
        cn_events = store.list_competitor_events(market="cn")
        ce_ids = {e.event_id for e in cn_events}
        self.assertNotIn("ce-persist-1", ce_ids)

    def test_latest_brand_state_market_isolated(self):
        """get_latest_brand_state 按 market 隔离"""
        self.engine.replay_history(market="cn")
        self.engine.replay_history(market="jp")
        store = self.engine.store
        latest_cn = store.get_latest_brand_state(market="cn")
        latest_jp = store.get_latest_brand_state(market="jp")
        self.assertIsNotNone(latest_cn)
        self.assertIsNotNone(latest_jp)
        self.assertEqual(latest_cn.market, "cn")
        self.assertEqual(latest_jp.market, "jp")
        # 两个市场的最新状态不应是同一个
        self.assertNotEqual(latest_cn.state_id, latest_jp.state_id)


class TestMultiPlatformMixing(unittest.TestCase):
    """跨家族渠道混合"""

    def test_cross_family_mix(self):
        """短视频 + 电商 + CRM 混合应产生合理的混合系数"""
        delta = {d: 0.1 for d in PERCEPTION_DIMENSIONS}
        # douyin (short_video): social_proof=1.3
        # tmall (marketplace): social_proof=0.9
        # email (crm): social_proof=0.7
        # avg social_proof = (1.3 + 0.9 + 0.7) / 3 ≈ 0.967
        result = BrandStateEngine._apply_channel_scaling(delta, ["douyin", "tmall", "email"])
        expected_sp = 0.1 * (1.3 + 0.9 + 0.7) / 3
        self.assertAlmostEqual(result["social_proof"], expected_sp, places=3)

    def test_domestic_vs_international_same_family(self):
        """douyin 和 tiktok 同属 short_video，无 override 的维度应相同"""
        delta = {d: 0.1 for d in PERCEPTION_DIMENSIONS}
        result_douyin = BrandStateEngine._apply_channel_scaling(delta, ["douyin"])
        result_tiktok = BrandStateEngine._apply_channel_scaling(delta, ["tiktok"])
        # Both inherit short_video without overrides
        for d in PERCEPTION_DIMENSIONS:
            self.assertAlmostEqual(result_douyin[d], result_tiktok[d])


class TestSignalMarketIsolation(unittest.TestCase):
    """signal 层市场隔离 — 核心回归测试"""

    # 用独立 product_line 避免与其他测试的 signal 数据交叉污染
    PL = "sig_iso_test_line"

    def setUp(self):
        self.engine = _fresh_engine()
        store = self.engine.store
        from app.models.brandiction import BrandSignalSnapshot

        # cn 市场的 science_credibility 信号：值 = 0.7
        store.save_signal(BrandSignalSnapshot(
            signal_id="sig-cn-sci-1",
            date="2025-01-15",
            product_line=self.PL,
            audience_segment="general",
            market="cn",
            dimension="science_credibility",
            value=0.7,
            source="tmall_reviews",
        ))
        # jp 市场的 science_credibility 信号：值 = 0.9（日本消费者更看重科学背书）
        store.save_signal(BrandSignalSnapshot(
            signal_id="sig-jp-sci-1",
            date="2025-01-15",
            product_line=self.PL,
            audience_segment="general",
            market="jp",
            dimension="science_credibility",
            value=0.9,
            source="rakuten_reviews",
        ))
        # cn 市场的 aesthetic_affinity 信号
        store.save_signal(BrandSignalSnapshot(
            signal_id="sig-cn-aes-1",
            date="2025-01-15",
            product_line=self.PL,
            audience_segment="general",
            market="cn",
            dimension="aesthetic_affinity",
            value=0.6,
            source="redbook_corpus",
        ))

    def test_build_state_cn_jp_different_perception(self):
        """同日期/同 product_line/同 segment，不同 market 的 signals 构出不同 perception"""
        state_cn = self.engine.build_state_from_signals(
            "2025-02-01", product_line=self.PL, market="cn",
        )
        state_jp = self.engine.build_state_from_signals(
            "2025-02-01", product_line=self.PL, market="jp",
        )
        # cn 有 science_credibility=0.7，jp 有 science_credibility=0.9
        self.assertAlmostEqual(
            state_cn.perception.science_credibility, 0.7, places=2,
        )
        self.assertAlmostEqual(
            state_jp.perception.science_credibility, 0.9, places=2,
        )
        self.assertNotAlmostEqual(
            state_cn.perception.science_credibility,
            state_jp.perception.science_credibility,
            places=2,
        )

    def test_build_state_cn_has_aesthetic_jp_does_not(self):
        """cn 有 aesthetic_affinity 信号，jp 没有 → jp 回退到默认值 0.5"""
        state_cn = self.engine.build_state_from_signals(
            "2025-02-01", product_line=self.PL, market="cn",
        )
        state_jp = self.engine.build_state_from_signals(
            "2025-02-01", product_line=self.PL, market="jp",
        )
        self.assertAlmostEqual(
            state_cn.perception.aesthetic_affinity, 0.6, places=2,
        )
        # jp 没有 aesthetic 信号 → 默认值 0.5
        self.assertAlmostEqual(
            state_jp.perception.aesthetic_affinity, 0.5, places=2,
        )

    def test_deterministic_builder_also_isolated(self):
        """_build_state_from_signals_deterministic 同样按 market 隔离"""
        state_cn = self.engine._build_state_from_signals_deterministic(
            "2025-02-01", product_line=self.PL, market="cn",
        )
        state_jp = self.engine._build_state_from_signals_deterministic(
            "2025-02-01", product_line=self.PL, market="jp",
        )
        # ID 不同
        self.assertNotEqual(state_cn.state_id, state_jp.state_id)
        self.assertIn("-cn", state_cn.state_id)
        self.assertIn("-jp", state_jp.state_id)
        # perception 不同
        self.assertNotAlmostEqual(
            state_cn.perception.science_credibility,
            state_jp.perception.science_credibility,
            places=2,
        )

    def test_list_signals_market_filter(self):
        """store.list_signals(market=...) 正确过滤"""
        store = self.engine.store
        cn_sigs = store.list_signals(market="cn")
        jp_sigs = store.list_signals(market="jp")
        cn_ids = {s.signal_id for s in cn_sigs}
        jp_ids = {s.signal_id for s in jp_sigs}
        # cn 应有 2 条（sci + aes），jp 应有 1 条（sci）
        self.assertIn("sig-cn-sci-1", cn_ids)
        self.assertIn("sig-cn-aes-1", cn_ids)
        self.assertNotIn("sig-jp-sci-1", cn_ids)
        self.assertIn("sig-jp-sci-1", jp_ids)
        self.assertNotIn("sig-cn-sci-1", jp_ids)

    def test_signal_market_field_persisted(self):
        """BrandSignalSnapshot.market 正确持久化"""
        store = self.engine.store
        jp_sigs = store.list_signals(market="jp")
        self.assertEqual(len(jp_sigs), 1)
        self.assertEqual(jp_sigs[0].market, "jp")

    def test_replay_initial_state_uses_market_signals(self):
        """replay 的初始 state 应该基于对应 market 的 signals 构建"""
        store = self.engine.store
        # 给 cn 和 jp 各加一条 intervention 以触发 replay
        iv_cn = HistoricalIntervention(
            intervention_id="sig-iso-cn-1", run_id="sig-iso",
            theme="science", product_line=self.PL,
            date_start="2025-02-01", date_end="2025-02-28",
            market="cn",
        )
        store.save_intervention(iv_cn)
        store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="sig-iso-oc-cn-1", intervention_id="sig-iso-cn-1",
            brand_lift=0.05,
        ))
        iv_jp = HistoricalIntervention(
            intervention_id="sig-iso-jp-1", run_id="sig-iso",
            theme="science", product_line=self.PL,
            date_start="2025-02-01", date_end="2025-02-28",
            market="jp",
        )
        store.save_intervention(iv_jp)
        store.save_outcome(HistoricalOutcomeWindow(
            outcome_id="sig-iso-oc-jp-1", intervention_id="sig-iso-jp-1",
            brand_lift=0.05,
        ))

        states_cn = self.engine.replay_history(product_line=self.PL, market="cn")
        states_jp = self.engine.replay_history(product_line=self.PL, market="jp")

        # 初始 state 的 science_credibility 应不同（cn=0.7 vs jp=0.9 来自 signals）
        initial_cn = states_cn[0]
        initial_jp = states_jp[0]
        self.assertAlmostEqual(initial_cn.perception.science_credibility, 0.7, places=2)
        self.assertAlmostEqual(initial_jp.perception.science_credibility, 0.9, places=2)


class TestBrandSignalSnapshotMarketField(unittest.TestCase):
    """BrandSignalSnapshot model 的 market 字段"""

    def test_default_market_is_cn(self):
        from app.models.brandiction import BrandSignalSnapshot
        sig = BrandSignalSnapshot(signal_id="t1", date="2025-01-01")
        self.assertEqual(sig.market, "cn")

    def test_market_in_to_dict(self):
        from app.models.brandiction import BrandSignalSnapshot
        sig = BrandSignalSnapshot(signal_id="t2", date="2025-01-01", market="jp")
        d = sig.to_dict()
        self.assertEqual(d["market"], "jp")

    def test_market_from_dict(self):
        from app.models.brandiction import BrandSignalSnapshot
        sig = BrandSignalSnapshot.from_dict({
            "signal_id": "t3", "date": "2025-01-01", "market": "sea",
        })
        self.assertEqual(sig.market, "sea")


if __name__ == "__main__":
    unittest.main()
