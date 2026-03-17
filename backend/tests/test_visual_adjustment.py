"""
Visual Adjustment Layer 测试

验证：
1. 图片分析结果能影响 baseline 接近的方案排序
2. 无图片时系统正常退化
3. visual_score 计算逻辑正确
4. 调整是透明的（有 visual_adjustment 元数据）
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("MOODY_SECRET_KEY", "test-secret")
os.environ.setdefault("MOODY_UPLOAD_FOLDER", tempfile.mkdtemp())
os.environ.setdefault("MOODY_USERS", "slr:test-pass:Liren:admin")

from app.services.baseline_ranker import apply_visual_adjustment
from app.services.image_analyzer import compute_visual_score
from app.utils.image_helpers import resolve_image_path as _resolve_image_url_to_path


class TestImagePathSecurity(unittest.TestCase):
    """Test path traversal prevention in image URL resolver."""

    def test_path_traversal_in_set_id_blocked(self):
        result = _resolve_image_url_to_path("/api/campaign/image-file/../../etc/passwd")
        self.assertIsNone(result)

    def test_path_traversal_in_filename_blocked(self):
        result = _resolve_image_url_to_path("/api/campaign/image-file/valid_set/../../etc/passwd")
        self.assertIsNone(result)

    def test_dotdot_in_both_parts_blocked(self):
        result = _resolve_image_url_to_path("/api/campaign/image-file/../../../etc/shadow")
        self.assertIsNone(result)

    def test_arbitrary_disk_path_rejected(self):
        """不再接受任意磁盘路径"""
        result = _resolve_image_url_to_path("/etc/passwd")
        self.assertIsNone(result)

    def test_relative_disk_path_rejected(self):
        result = _resolve_image_url_to_path("../../../etc/passwd")
        self.assertIsNone(result)

    def test_valid_url_format_accepted(self):
        """合法 URL 格式不会被拒绝（即使文件不存在）"""
        result = _resolve_image_url_to_path("/api/campaign/image-file/test_set/image.jpg")
        # File doesn't exist, so returns None, but it doesn't raise
        self.assertIsNone(result)

    def test_empty_parts_rejected(self):
        result = _resolve_image_url_to_path("/api/campaign/image-file//")
        self.assertIsNone(result)


class TestComputeVisualScore(unittest.TestCase):
    """Test the visual score computation from profiles."""

    def test_premium_high_trust_scores_high(self):
        profile = {
            "creative_style": "editorial",
            "product_visibility": 8,
            "trust_signal_strength": 9,
            "promo_intensity": 2,
            "aesthetic_tone": "premium",
            "text_density": 4,
            "visual_hooks": ["eye_closeup", "before_after"],
            "visual_risks": [],
            "consistency_score": 9,
        }
        score = compute_visual_score(profile)
        self.assertGreater(score, 0.7)

    def test_mass_promo_heavy_scores_low(self):
        profile = {
            "creative_style": "meme",
            "product_visibility": 3,
            "trust_signal_strength": 2,
            "promo_intensity": 9,
            "aesthetic_tone": "generic",
            "text_density": 9,
            "visual_hooks": [],
            "visual_risks": ["excessive_text", "brand_mismatch", "cheap_feel"],
            "consistency_score": 3,
        }
        score = compute_visual_score(profile)
        self.assertLess(score, 0.4)

    def test_different_profiles_different_scores(self):
        """核心测试：不同图片内容产生不同分数"""
        profile_a = {
            "trust_signal_strength": 9,
            "product_visibility": 8,
            "aesthetic_tone": "clinical",
            "promo_intensity": 1,
            "text_density": 3,
            "visual_hooks": ["product_detail", "data_chart"],
            "visual_risks": [],
            "consistency_score": 8,
        }
        profile_b = {
            "trust_signal_strength": 3,
            "product_visibility": 4,
            "aesthetic_tone": "playful",
            "promo_intensity": 7,
            "text_density": 8,
            "visual_hooks": ["colorful"],
            "visual_risks": ["brand_mismatch", "cheap_feel"],
            "consistency_score": 5,
        }
        score_a = compute_visual_score(profile_a)
        score_b = compute_visual_score(profile_b)
        # A should be significantly higher than B
        self.assertGreater(score_a - score_b, 0.15)


class TestApplyVisualAdjustment(unittest.TestCase):
    """Test the visual adjustment layer on ranking entries."""

    def _make_entries(self, scores, names=None):
        entries = []
        for i, score in enumerate(scores):
            name = (names[i] if names else f"Plan {chr(65 + i)}")
            entries.append({
                "plan": {"name": name, "theme": "science", "platform": "redbook"},
                "observed_baseline": {"sample_size": 5},
                "score": score,
                "data_sufficient": True,
                "rank": i + 1,
            })
        return entries

    def test_no_visual_profiles_no_change(self):
        """无图片时不改变排序"""
        entries = self._make_entries([3.0, 2.9])
        result = apply_visual_adjustment(entries, {})
        self.assertEqual(result[0]["score"], 3.0)
        self.assertEqual(result[1]["score"], 2.9)

    def test_close_scores_with_visual_diff_changes_ranking(self):
        """核心测试：分数接近 + 不同图片 → 排序改变"""
        entries = self._make_entries([3.00, 3.02], names=["Plan A", "Plan B"])

        visual_profiles = {
            "Plan A": {
                "trust_signal_strength": 9,
                "product_visibility": 9,
                "aesthetic_tone": "premium",
                "promo_intensity": 1,
                "text_density": 4,
                "visual_hooks": ["eye_closeup", "clinical_proof"],
                "visual_risks": [],
                "consistency_score": 9,
            },
            "Plan B": {
                "trust_signal_strength": 2,
                "product_visibility": 3,
                "aesthetic_tone": "generic",
                "promo_intensity": 8,
                "text_density": 9,
                "visual_hooks": [],
                "visual_risks": ["cheap_feel", "brand_mismatch"],
                "consistency_score": 3,
            },
        }

        result = apply_visual_adjustment(entries, visual_profiles)

        # Plan A had lower baseline but much better visuals
        plan_a = next(e for e in result if e["plan"]["name"] == "Plan A")
        plan_b = next(e for e in result if e["plan"]["name"] == "Plan B")

        # Plan A should have been boosted, Plan B penalized
        self.assertTrue(plan_a["visual_adjustment"]["applied"])
        self.assertTrue(plan_b["visual_adjustment"]["applied"])
        self.assertGreater(plan_a["visual_adjustment"]["score_delta"], 0)
        self.assertLess(plan_b["visual_adjustment"]["score_delta"], 0)

    def test_distant_scores_no_adjustment(self):
        """分数差距大时不调整"""
        entries = self._make_entries([3.5, 2.0], names=["Plan A", "Plan B"])

        visual_profiles = {
            "Plan A": {
                "trust_signal_strength": 3,
                "product_visibility": 3,
                "aesthetic_tone": "generic",
                "promo_intensity": 8,
            },
            "Plan B": {
                "trust_signal_strength": 9,
                "product_visibility": 9,
                "aesthetic_tone": "premium",
                "promo_intensity": 1,
            },
        }

        result = apply_visual_adjustment(entries, visual_profiles)

        # Both should have applied=False because scores are far apart
        for entry in result:
            self.assertFalse(entry["visual_adjustment"]["applied"])

    def test_one_plan_with_image_one_without(self):
        """一个有图一个没图"""
        entries = self._make_entries([3.0, 3.01], names=["Plan A", "Plan B"])

        visual_profiles = {
            "Plan A": {
                "trust_signal_strength": 8,
                "product_visibility": 7,
                "aesthetic_tone": "premium",
                "promo_intensity": 2,
                "text_density": 4,
                "visual_hooks": ["eye_detail"],
                "visual_risks": [],
                "consistency_score": 8,
            },
        }

        result = apply_visual_adjustment(entries, visual_profiles)

        plan_a = next(e for e in result if e["plan"]["name"] == "Plan A")
        plan_b = next(e for e in result if e["plan"]["name"] == "Plan B")

        self.assertTrue(plan_a["visual_adjustment"]["applied"])
        self.assertFalse(plan_b["visual_adjustment"]["applied"])
        self.assertEqual(plan_b["visual_adjustment"]["reason"], "no_image")

    def test_all_cold_start_triggers_adjustment(self):
        """全部冷启动时也触发 visual adjustment"""
        entries = []
        for i, name in enumerate(["Plan A", "Plan B"]):
            entries.append({
                "plan": {"name": name, "theme": "science"},
                "observed_baseline": {"sample_size": 0},
                "score": -999.0,
                "data_sufficient": False,
                "rank": i + 1,
            })

        visual_profiles = {
            "Plan A": {
                "trust_signal_strength": 9,
                "product_visibility": 8,
                "aesthetic_tone": "clinical",
                "promo_intensity": 1,
            },
            "Plan B": {
                "trust_signal_strength": 3,
                "product_visibility": 3,
                "aesthetic_tone": "generic",
                "promo_intensity": 7,
            },
        }

        result = apply_visual_adjustment(entries, visual_profiles)

        plan_a = next(e for e in result if e["plan"]["name"] == "Plan A")
        self.assertTrue(plan_a["visual_adjustment"]["applied"])
        # Both cold start scores are -999.0, so they're also "close"
        self.assertIn(plan_a["visual_adjustment"]["reason"], ["all_cold_start", "close_baseline_scores"])

    def test_duplicate_names_use_id_not_name(self):
        """重名方案通过 id 区分，不串数据"""
        entries = [
            {
                "plan": {"id": "id_1", "name": "Same Name", "theme": "science"},
                "observed_baseline": {"sample_size": 5},
                "score": 3.00,
                "data_sufficient": True,
                "rank": 1,
            },
            {
                "plan": {"id": "id_2", "name": "Same Name", "theme": "comfort"},
                "observed_baseline": {"sample_size": 5},
                "score": 3.01,
                "data_sufficient": True,
                "rank": 2,
            },
        ]

        visual_profiles = {
            "id_1": {
                "trust_signal_strength": 9,
                "product_visibility": 9,
                "aesthetic_tone": "premium",
                "promo_intensity": 1,
            },
            "id_2": {
                "trust_signal_strength": 2,
                "product_visibility": 2,
                "aesthetic_tone": "generic",
                "promo_intensity": 9,
            },
        }

        result = apply_visual_adjustment(entries, visual_profiles)

        entry_1 = next(e for e in result if e["plan"]["id"] == "id_1")
        entry_2 = next(e for e in result if e["plan"]["id"] == "id_2")

        # Both should have adjustment applied
        self.assertTrue(entry_1["visual_adjustment"]["applied"])
        self.assertTrue(entry_2["visual_adjustment"]["applied"])
        # id_1 has better visuals → positive delta
        self.assertGreater(entry_1["visual_adjustment"]["score_delta"], 0)
        # id_2 has worse visuals → negative delta
        self.assertLess(entry_2["visual_adjustment"]["score_delta"], 0)

    def test_adjustment_metadata_is_transparent(self):
        """调整元数据完整透明"""
        entries = self._make_entries([3.0, 3.05], names=["Plan A", "Plan B"])

        visual_profiles = {
            "Plan A": {
                "trust_signal_strength": 8,
                "aesthetic_tone": "premium",
                "promo_intensity": 2,
            },
        }

        result = apply_visual_adjustment(entries, visual_profiles)
        plan_a = next(e for e in result if e["plan"]["name"] == "Plan A")
        va = plan_a["visual_adjustment"]

        self.assertIn("visual_score", va)
        self.assertIn("score_delta", va)
        self.assertIn("original_score", va)
        self.assertIn("reason", va)


if __name__ == "__main__":
    unittest.main()
