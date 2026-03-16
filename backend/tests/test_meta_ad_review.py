"""
Tests for review_meta_ad_library.py
覆盖: CSV 过滤、分类逻辑、输出生成
"""

import csv
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from review_meta_ad_library import (
    load_pending_meta_rows,
    filter_by_competitors,
    sort_by_priority,
    analyze_page_text,
    classify_result,
    build_evidence_summary,
    write_results_csv,
    write_candidates_csv,
    ReviewResult,
    RESULTS_COLUMNS,
    CANDIDATES_COLUMNS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV with mixed source/status rows."""
    csv_path = tmp_path / "test_input.csv"
    rows = [
        # Should be selected: meta + pending
        {
            "parent_event_id": "ce-1", "date": "2026-03-16",
            "competitor": "hapakristin", "market": "global",
            "suggested_event_type": "campaign", "suggested_impact_estimate": "low",
            "description": "Meta search", "source": "meta_ad_library",
            "source_url": "https://www.facebook.com/ads/library/?q=hapakristin",
            "confidence": "none", "evidence_summary": "", "review_status": "pending",
            "reviewer_notes": "",
        },
        # Should be selected: meta + pending
        {
            "parent_event_id": "ce-2", "date": "2026-03-16",
            "competitor": "ttdeye", "market": "global",
            "suggested_event_type": "campaign", "suggested_impact_estimate": "low",
            "description": "Meta search", "source": "meta_ad_library",
            "source_url": "https://www.facebook.com/ads/library/?q=ttdeye",
            "confidence": "none", "evidence_summary": "", "review_status": "pending",
            "reviewer_notes": "",
        },
        # Should NOT be selected: google source
        {
            "parent_event_id": "ce-3", "date": "2026-03-16",
            "competitor": "hapakristin", "market": "global",
            "suggested_event_type": "campaign", "suggested_impact_estimate": "low",
            "description": "Google search", "source": "google_ads_transparency",
            "source_url": "https://adstransparency.google.com/?search_text=hapakristin",
            "confidence": "none", "evidence_summary": "", "review_status": "pending",
            "reviewer_notes": "",
        },
        # Should NOT be selected: already approved
        {
            "parent_event_id": "ce-4", "date": "2026-03-16",
            "competitor": "eyecandys", "market": "global",
            "suggested_event_type": "price_cut", "suggested_impact_estimate": "medium",
            "description": "15% off", "source": "meta_ad_library",
            "source_url": "https://www.facebook.com/ads/library/?q=eyecandys",
            "confidence": "medium", "evidence_summary": "confirmed", "review_status": "approved",
            "reviewer_notes": "",
        },
        # Should be selected: meta + pending, low-priority brand
        {
            "parent_event_id": "ce-5", "date": "2026-03-16",
            "competitor": "just4kira", "market": "global",
            "suggested_event_type": "campaign", "suggested_impact_estimate": "low",
            "description": "Meta search", "source": "meta_ad_library",
            "source_url": "https://www.facebook.com/ads/library/?q=just4kira",
            "confidence": "none", "evidence_summary": "", "review_status": "pending",
            "reviewer_notes": "",
        },
    ]
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


# ---------------------------------------------------------------------------
# Test 1: CSV filtering logic
# ---------------------------------------------------------------------------

class TestCSVFiltering:
    def test_loads_only_meta_pending(self, sample_csv):
        """Only meta_ad_library + pending rows should be loaded."""
        rows = load_pending_meta_rows(sample_csv)
        assert len(rows) == 3  # hapakristin, ttdeye, just4kira
        sources = {r["source"] for r in rows}
        assert sources == {"meta_ad_library"}
        statuses = {r["review_status"] for r in rows}
        assert statuses == {"pending"}

    def test_excludes_approved_meta(self, sample_csv):
        """Approved meta rows must not be included."""
        rows = load_pending_meta_rows(sample_csv)
        competitors = [r["competitor"] for r in rows]
        # eyecandys is approved, should not appear
        assert "eyecandys" not in competitors

    def test_excludes_google_source(self, sample_csv):
        """Google source rows must not be included even if pending."""
        rows = load_pending_meta_rows(sample_csv)
        sources = [r["source"] for r in rows]
        assert "google_ads_transparency" not in sources

    def test_filter_by_competitors(self, sample_csv):
        """Filter to specific competitors."""
        rows = load_pending_meta_rows(sample_csv)
        filtered = filter_by_competitors(rows, ["hapakristin", "ttdeye"])
        assert len(filtered) == 2
        assert {r["competitor"] for r in filtered} == {"hapakristin", "ttdeye"}

    def test_filter_none_returns_all(self, sample_csv):
        """None competitor filter returns all rows."""
        rows = load_pending_meta_rows(sample_csv)
        filtered = filter_by_competitors(rows, None)
        assert len(filtered) == len(rows)

    def test_sort_by_priority(self, sample_csv):
        """Priority competitors should come first."""
        rows = load_pending_meta_rows(sample_csv)
        sorted_rows = sort_by_priority(rows)
        # hapakristin (priority 0) before ttdeye (priority 1) before just4kira (not in list)
        assert sorted_rows[0]["competitor"] == "hapakristin"
        assert sorted_rows[1]["competitor"] == "ttdeye"
        assert sorted_rows[2]["competitor"] == "just4kira"


# ---------------------------------------------------------------------------
# Test 2: Classification logic (blocked / ambiguous / confirmed)
# ---------------------------------------------------------------------------

class TestClassification:
    def test_blocked_when_was_blocked(self):
        """Blocked flag should override everything."""
        analysis = {"ad_count": "10", "has_discount_evidence": True, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=True)
        assert result == "blocked"

    def test_blocked_when_page_not_loaded(self):
        analysis = {"ad_count": "0", "has_discount_evidence": False, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=False, was_blocked=False)
        assert result == "blocked"

    def test_no_evidence_zero_ads(self):
        analysis = {"ad_count": "0", "has_discount_evidence": False, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "no_evidence"

    def test_confirmed_discount_with_ads(self):
        """Discount keywords + known ad count = confirmed campaign."""
        analysis = {"ad_count": "5", "has_discount_evidence": True, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "confirmed"
        assert etype == "campaign"
        assert impact == "medium"

    def test_confirmed_launch_with_ads(self):
        analysis = {"ad_count": "3", "has_discount_evidence": False, "has_launch_evidence": True}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "confirmed"
        assert etype == "new_launch"

    def test_confirmed_high_ad_count(self):
        """Many ads even without keywords = confirmed campaign."""
        analysis = {"ad_count": "25", "has_discount_evidence": False, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "confirmed"
        assert etype == "campaign"

    def test_ambiguous_few_ads_no_keywords(self):
        """Few ads, no keywords = ambiguous."""
        analysis = {"ad_count": "3", "has_discount_evidence": False, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "ambiguous"

    def test_ambiguous_keywords_no_count(self):
        """Keywords found but ad count unknown."""
        analysis = {"ad_count": "unknown", "has_discount_evidence": True, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "ambiguous"

    def test_no_evidence_unknown_no_keywords(self):
        """No ads, no keywords, no evidence."""
        analysis = {"ad_count": "unknown", "has_discount_evidence": False, "has_launch_evidence": False}
        result, etype, impact = classify_result(analysis, page_loaded=True, was_blocked=False)
        assert result == "no_evidence"


# ---------------------------------------------------------------------------
# Test 3: Only confirmed generates candidates
# ---------------------------------------------------------------------------

class TestCandidateGeneration:
    def test_only_confirmed_in_candidates(self, tmp_path):
        """Only confirmed results should appear in candidates CSV."""
        results = [
            ReviewResult(competitor="hapakristin", source_url="http://x",
                         review_result="confirmed", suggested_event_type="campaign",
                         suggested_impact_estimate="medium", observed_claims="50% off",
                         evidence_summary="Found active ads with discount"),
            ReviewResult(competitor="ttdeye", source_url="http://y",
                         review_result="blocked"),
            ReviewResult(competitor="eyecandys", source_url="http://z",
                         review_result="ambiguous", suggested_event_type="campaign"),
            ReviewResult(competitor="olensglobal", source_url="http://w",
                         review_result="no_evidence"),
        ]
        out_path = tmp_path / "candidates.csv"
        write_candidates_csv(results, out_path)

        with open(out_path, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        assert len(reader) == 1
        assert reader[0]["competitor"] == "hapakristin"
        assert reader[0]["review_status"] == "pending_review"
        assert reader[0]["suggested_event_type"] == "campaign"

    def test_empty_candidates_when_no_confirmed(self, tmp_path):
        """No confirmed = empty candidates file (header only)."""
        results = [
            ReviewResult(competitor="a", review_result="blocked"),
            ReviewResult(competitor="b", review_result="no_evidence"),
        ]
        out_path = tmp_path / "candidates.csv"
        write_candidates_csv(results, out_path)

        with open(out_path, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 0

    def test_results_csv_all_types(self, tmp_path):
        """All result types should be written to results CSV."""
        results = [
            ReviewResult(competitor="a", review_result="confirmed"),
            ReviewResult(competitor="b", review_result="blocked"),
            ReviewResult(competitor="c", review_result="ambiguous"),
            ReviewResult(competitor="d", review_result="no_evidence"),
        ]
        out_path = tmp_path / "results.csv"
        write_results_csv(results, out_path)

        with open(out_path, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 4
        types = {r["review_result"] for r in reader}
        assert types == {"confirmed", "blocked", "ambiguous", "no_evidence"}


# ---------------------------------------------------------------------------
# Test: Page text analysis
# ---------------------------------------------------------------------------

class TestPageAnalysis:
    def test_detects_discount(self):
        text = "Shop now! 30% off all colored contacts. Free shipping on $50+"
        analysis = analyze_page_text(text)
        assert analysis["has_discount_evidence"]
        assert any("30% off" in m for m in analysis["discount_matches"])

    def test_detects_launch(self):
        text = "Just dropped: New Arrival Dolly Kristin Beige lens collection"
        analysis = analyze_page_text(text)
        assert analysis["has_launch_evidence"]

    def test_detects_ad_count(self):
        text = "Showing 42 results for hapakristin"
        analysis = analyze_page_text(text)
        assert analysis["ad_count"] == "42"

    def test_detects_no_results(self):
        text = "No results found. Try a different search term."
        analysis = analyze_page_text(text)
        assert analysis["ad_count"] == "0"

    def test_no_false_positives(self):
        text = "Welcome to Meta Ad Library. Search for ads by advertiser or keyword."
        analysis = analyze_page_text(text)
        assert not analysis["has_discount_evidence"]
        assert not analysis["has_launch_evidence"]
