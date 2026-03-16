"""
竞品事件采集器回归测试
覆盖: draft生成、approved才能导入、标准化、幂等、source_url必须
"""

import csv
import json
import os
import sqlite3
import tempfile

import pytest

# Add parent to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from collect_competitor_events import detect_events, make_event_id, DRAFT_COLUMNS
from import_competitor_events import (
    normalize_market,
    normalize_event_type,
    normalize_impact,
    import_events,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary brandiction.db with competitor_events table."""
    db_path = str(tmp_path / "test_brandiction.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE competitor_events (
            event_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            competitor TEXT NOT NULL,
            event_type TEXT,
            description TEXT,
            impact_estimate TEXT,
            extra TEXT DEFAULT '{}',
            market TEXT DEFAULT 'cn'
        )
    """)
    conn.execute("CREATE INDEX idx_competitor_date ON competitor_events(date)")
    conn.commit()
    conn.close()
    return db_path


def _write_draft_csv(tmp_path, rows: list[dict], filename="draft.csv") -> str:
    """Write a draft CSV with given rows."""
    csv_path = str(tmp_path / filename)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DRAFT_COLUMNS)
        writer.writeheader()
        for row in rows:
            full_row = {col: "" for col in DRAFT_COLUMNS}
            full_row.update(row)
            writer.writerow(full_row)
    return csv_path


# ---------------------------------------------------------------------------
# Test 1: Draft event generation (detect_events)
# ---------------------------------------------------------------------------

class TestDraftGeneration:
    def test_detect_sale(self):
        events = detect_events("Big Summer Sale! 50% off all lenses")
        types = [e[0] for e in events]
        assert "price_cut" in types

    def test_detect_new_launch(self):
        events = detect_events("New Arrival: Crystal Blue daily lenses now available")
        types = [e[0] for e in events]
        assert "new_launch" in types

    def test_detect_collab(self):
        events = detect_events("Exciting collaboration with Disney for limited edition lenses")
        types = [e[0] for e in events]
        assert "collab" in types

    def test_detect_bundle(self):
        events = detect_events("Buy 2 Get 1 Free on all colored lenses")
        types = [e[0] for e in events]
        assert "bundle_offer" in types

    def test_no_events_in_plain_text(self):
        events = detect_events("Contact lenses for daily wear. FDA approved materials.")
        assert len(events) == 0

    def test_event_id_deterministic(self):
        id1 = make_event_id("olens", "official_site", "2026-03-16", "sale 50% off")
        id2 = make_event_id("olens", "official_site", "2026-03-16", "sale 50% off")
        assert id1 == id2

    def test_event_id_different_for_different_inputs(self):
        id1 = make_event_id("olens", "official_site", "2026-03-16", "sale")
        id2 = make_event_id("ttdeye", "official_site", "2026-03-16", "sale")
        assert id1 != id2


# ---------------------------------------------------------------------------
# Test 2: Only approved events can be imported
# ---------------------------------------------------------------------------

class TestApprovedOnly:
    def test_pending_not_imported(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-test-001",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "price_cut",
            "suggested_impact_estimate": "medium",
            "description": "test event",
            "source": "official_site",
            "source_url": "https://example.com",
            "confidence": "low",
            "review_status": "pending",
            "reviewer_notes": "",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 0

    def test_approved_imported(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-test-002",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "new_launch",
            "suggested_impact_estimate": "high",
            "description": "approved event",
            "source": "official_site",
            "source_url": "https://example.com/launch",
            "confidence": "medium",
            "review_status": "approved",
            "reviewer_notes": "looks real",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 1

    def test_rejected_not_imported(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-test-003",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "campaign",
            "suggested_impact_estimate": "low",
            "description": "rejected event",
            "source": "official_site",
            "source_url": "https://example.com/rejected",
            "confidence": "low",
            "review_status": "rejected",
            "reviewer_notes": "not a real event",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 0


# ---------------------------------------------------------------------------
# Test 3: Normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    def test_market_lowercase(self):
        assert normalize_market("US") == "us"
        assert normalize_market("  Global  ") == "global"
        assert normalize_market("KR") == "kr"

    def test_event_type_normalization(self):
        assert normalize_event_type("price_cut") == "price_cut"
        assert normalize_event_type("Price Cut") == "price_cut"
        assert normalize_event_type("newlaunch") == "new_launch"
        assert normalize_event_type("collaboration") == "collab"
        assert normalize_event_type("bundle") == "bundle_offer"
        assert normalize_event_type("nonsense") is None

    def test_impact_normalization(self):
        assert normalize_impact("high") == "high"
        assert normalize_impact("H") == "high"
        assert normalize_impact("Med") == "medium"
        assert normalize_impact("LOW") == "low"
        assert normalize_impact("L") == "low"

    def test_normalized_values_in_db(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-norm-001",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "US",
            "suggested_event_type": "Price Cut",
            "suggested_impact_estimate": "H",
            "description": "normalization test",
            "source": "official_site",
            "source_url": "https://example.com/norm",
            "confidence": "low",
            "review_status": "approved",
            "reviewer_notes": "",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        row = conn.execute("SELECT market, event_type, impact_estimate FROM competitor_events").fetchone()
        conn.close()
        assert row[0] == "us"
        assert row[1] == "price_cut"
        assert row[2] == "high"


# ---------------------------------------------------------------------------
# Test 4: Idempotent import
# ---------------------------------------------------------------------------

class TestIdempotent:
    def test_double_import_no_duplicates(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-idem-001",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "campaign",
            "suggested_impact_estimate": "medium",
            "description": "idempotent test",
            "source": "official_site",
            "source_url": "https://example.com/idem",
            "confidence": "medium",
            "review_status": "approved",
            "reviewer_notes": "",
        }])
        import_events(csv_path, test_db)
        import_events(csv_path, test_db)  # second import
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# Test 5: No source_url → cannot import
# ---------------------------------------------------------------------------

class TestSourceUrlRequired:
    def test_no_source_url_rejected(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-nosrc-001",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "price_cut",
            "suggested_impact_estimate": "medium",
            "description": "no source url event",
            "source": "manual_note",
            "source_url": "",
            "confidence": "high",
            "review_status": "approved",
            "reviewer_notes": "",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 0

    def test_with_source_url_accepted(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-hassrc-001",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "price_cut",
            "suggested_impact_estimate": "medium",
            "description": "has source url",
            "source": "official_site",
            "source_url": "https://example.com/real",
            "confidence": "high",
            "review_status": "approved",
            "reviewer_notes": "",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 1


# ---------------------------------------------------------------------------
# Test: Provenance preserved in extra
# ---------------------------------------------------------------------------

class TestProvenance:
    def test_extra_contains_provenance(self, test_db, tmp_path):
        csv_path = _write_draft_csv(tmp_path, [{
            "suggested_event_id": "ce-draft-prov-001",
            "date": "2026-03-16",
            "competitor": "testbrand",
            "market": "us",
            "suggested_event_type": "new_launch",
            "suggested_impact_estimate": "high",
            "description": "provenance test",
            "source": "official_site",
            "source_url": "https://example.com/provenance",
            "confidence": "medium",
            "review_status": "approved",
            "reviewer_notes": "verified by team",
        }])
        import_events(csv_path, test_db)
        conn = sqlite3.connect(test_db)
        extra_str = conn.execute("SELECT extra FROM competitor_events WHERE event_id='ce-prov-001'").fetchone()[0]
        conn.close()
        extra = json.loads(extra_str)
        assert extra["source"] == "official_site"
        assert extra["source_url"] == "https://example.com/provenance"
        assert extra["imported_from"] == "competitor_collector"


# ---------------------------------------------------------------------------
# Test: Test data isolation
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_uses_isolated_db(self, test_db):
        """Verify test DB is separate from production."""
        assert "test_brandiction.db" in test_db
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
        conn.close()
        assert count == 0  # fresh isolated DB
