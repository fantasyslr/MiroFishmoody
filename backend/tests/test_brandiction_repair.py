"""
Tests for Brandiction data repair script and related fixes.

Covers:
  - market lowercase normalization
  - colored_lens → colored_lenses standardization
  - import_etl.py preserves source_type/source_id/raw_text_ref
  - empty signal date handling
  - test competitor_events isolation
  - rebuilt brand_state dates are current
"""

import json
import os
import sqlite3
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_db(tmp_path: str) -> str:
    """Create a minimal brandiction.db with known test data."""
    db_path = os.path.join(tmp_path, "brandiction.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")

    conn.executescript("""
        CREATE TABLE interventions (
            intervention_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            product_line TEXT DEFAULT 'moodyplus',
            date_start TEXT, date_end TEXT,
            theme TEXT, message_arc TEXT, channel_mix TEXT,
            budget REAL, spend REAL,
            audience_segment TEXT, market TEXT DEFAULT 'cn',
            campaign_id TEXT, creative_id TEXT, landing_page TEXT,
            platform TEXT, channel_family TEXT, objective TEXT,
            notes TEXT, extra TEXT DEFAULT '{}'
        );
        CREATE TABLE outcomes (
            outcome_id TEXT PRIMARY KEY,
            intervention_id TEXT NOT NULL,
            window_label TEXT, date_start TEXT, date_end TEXT,
            impressions INTEGER, clicks INTEGER,
            ctr REAL, cvr REAL, revenue REAL, roas REAL,
            brand_lift REAL, search_trend_delta REAL,
            comment_sentiment REAL, comment_summary TEXT,
            sessions INTEGER, pdp_views INTEGER, add_to_cart INTEGER,
            checkout_started INTEGER, purchases INTEGER,
            new_customers INTEGER, returning_customers INTEGER,
            aov REAL, extra TEXT DEFAULT '{}'
        );
        CREATE TABLE signals (
            signal_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            product_line TEXT DEFAULT 'moodyplus',
            audience_segment TEXT DEFAULT 'general',
            market TEXT DEFAULT 'cn',
            signal_type TEXT, dimension TEXT,
            value REAL, raw_text TEXT, source TEXT,
            source_type TEXT, source_id TEXT, raw_text_ref TEXT,
            extra TEXT DEFAULT '{}'
        );
        CREATE TABLE competitor_events (
            event_id TEXT PRIMARY KEY,
            date TEXT NOT NULL, competitor TEXT NOT NULL,
            market TEXT DEFAULT 'cn',
            event_type TEXT, description TEXT,
            impact_estimate TEXT, extra TEXT DEFAULT '{}'
        );
        CREATE TABLE brand_states (
            state_id TEXT PRIMARY KEY,
            as_of_date TEXT NOT NULL,
            product_line TEXT DEFAULT 'moodyplus',
            audience_segment TEXT DEFAULT 'general',
            market TEXT DEFAULT 'cn',
            science_credibility REAL DEFAULT 0.5,
            comfort_trust REAL DEFAULT 0.5,
            aesthetic_affinity REAL DEFAULT 0.5,
            price_sensitivity REAL DEFAULT 0.5,
            social_proof REAL DEFAULT 0.5,
            skepticism REAL DEFAULT 0.3,
            competitor_pressure REAL DEFAULT 0.3,
            confidence REAL DEFAULT 0.5,
            evidence_sources TEXT DEFAULT '[]',
            notes TEXT, extra TEXT DEFAULT '{}'
        );
        CREATE TABLE state_transitions (
            transition_id TEXT PRIMARY KEY,
            intervention_id TEXT NOT NULL,
            state_before_id TEXT NOT NULL,
            state_after_id TEXT NOT NULL,
            market TEXT DEFAULT 'cn',
            delta TEXT DEFAULT '{}',
            confidence REAL DEFAULT 0.5,
            method TEXT DEFAULT 'historical',
            notes TEXT, extra TEXT DEFAULT '{}'
        );
    """)

    # Insert test data with known issues
    conn.execute(
        "INSERT INTO interventions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("iv-1", "run1", "colored_lens", "2026-01-01", "2026-01-15",
         None, None, None, 1000, 800, "general", "US",
         None, None, None, "meta", None, "OUTCOME_AWARENESS", None, "{}"),
    )
    conn.execute(
        "INSERT INTO interventions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("iv-2", "run1", "moodyplus", "2026-02-01", "2026-02-15",
         "science", None, None, 2000, 1500, "general", "SG",
         None, None, None, "tiktok", None, None, None, "{}"),
    )

    # Signal with empty date
    conn.execute(
        "INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("sig-empty-1", "", "moodyplus", "general", "AU",
         "creator_engagement", "likes", 42.0, None, "https://example.com",
         None, None, None, "{}"),
    )
    # Signal with same source but valid date (for inference)
    conn.execute(
        "INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("sig-sibling-1", "2026-03-01", "moodyplus", "general", "AU",
         "creator_engagement", "comments", 10.0, None, "https://example.com",
         None, None, None, "{}"),
    )
    # Signal with empty date and no sibling
    conn.execute(
        "INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("sig-orphan-1", "", "moodyplus", "general", "CA",
         "creator_engagement", "likes", 5.0, None, "https://unique.com",
         None, None, None, "{}"),
    )

    # Test competitor event
    conn.execute(
        "INSERT INTO competitor_events VALUES (?,?,?,?,?,?,?,?)",
        ("ce-persist-1", "2025-03-01", "alcon", "us", "price_cut", None, "high", "{}"),
    )

    # Test brand_states
    conn.execute(
        "INSERT INTO brand_states (state_id, as_of_date, product_line, market) VALUES (?,?,?,?)",
        ("bs-initial-moodyplus-general-cn", "2025-01-01", "moodyplus", "cn"),
    )
    conn.execute(
        "INSERT INTO brand_states (state_id, as_of_date, product_line, market) VALUES (?,?,?,?)",
        ("bs-2025-02-01-test1", "2025-02-01", "sig_iso_test_line", "cn"),
    )

    # Test state_transition
    conn.execute(
        "INSERT INTO state_transitions (transition_id, intervention_id, state_before_id, state_after_id, market) "
        "VALUES (?,?,?,?,?)",
        ("tr-test-1", "iso-cn-1", "bs-initial-moodyplus-general-cn", "bs-2025-02-01-test1", "cn"),
    )

    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db(tmp_path):
    """Create a test DB and patch the repair script's DB_PATH."""
    db_path = _make_test_db(str(tmp_path))
    return db_path


# ---------------------------------------------------------------------------
# Import repair functions
# ---------------------------------------------------------------------------

import importlib
import sys

def _get_repair_module():
    """Import repair script as a module."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "repair_brandiction_data.py"
    )
    spec = importlib.util.spec_from_file_location("repair_brandiction_data", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestP0MarketNormalization:
    def test_uppercase_markets_lowered(self, test_db):
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        result = repair.p0_normalize_markets(conn, dry_run=False)
        conn.commit()

        # Check interventions
        row = conn.execute(
            "SELECT market FROM interventions WHERE intervention_id = 'iv-1'"
        ).fetchone()
        assert row["market"] == "us"

        row = conn.execute(
            "SELECT market FROM interventions WHERE intervention_id = 'iv-2'"
        ).fetchone()
        assert row["market"] == "sg"

        # No uppercase markets should remain
        bad = conn.execute(
            "SELECT COUNT(*) FROM interventions WHERE market != lower(market)"
        ).fetchone()[0]
        assert bad == 0
        conn.close()


class TestP0ProductLine:
    def test_colored_lens_to_colored_lenses(self, test_db):
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        result = repair.p0_normalize_product_line(conn, dry_run=False)
        conn.commit()

        row = conn.execute(
            "SELECT product_line FROM interventions WHERE intervention_id = 'iv-1'"
        ).fetchone()
        assert row["product_line"] == "colored_lenses"

        # moodyplus unchanged
        row = conn.execute(
            "SELECT product_line FROM interventions WHERE intervention_id = 'iv-2'"
        ).fetchone()
        assert row["product_line"] == "moodyplus"
        conn.close()


class TestP0EmptyDates:
    def test_empty_dates_fixed(self, test_db):
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        result = repair.p0_fix_empty_dates(conn, dry_run=False)
        conn.commit()

        # sig-empty-1 should be inferred from sibling
        row = conn.execute(
            "SELECT date, extra FROM signals WHERE signal_id = 'sig-empty-1'"
        ).fetchone()
        assert row["date"] == "2026-03-01"
        extra = json.loads(row["extra"])
        assert extra.get("date_inferred") is True

        # sig-orphan-1 should be sentinel
        row = conn.execute(
            "SELECT date, extra FROM signals WHERE signal_id = 'sig-orphan-1'"
        ).fetchone()
        assert row["date"] == "1970-01-01"
        extra = json.loads(row["extra"])
        assert extra.get("date_unknown") is True

        # No empty dates remain
        bad = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE date = ''"
        ).fetchone()[0]
        assert bad == 0
        conn.close()


class TestP1CompetitorEventsIsolation:
    def test_test_events_marked(self, test_db):
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        result = repair.p1_isolate_test_competitor_events(conn, dry_run=False)
        conn.commit()

        row = conn.execute(
            "SELECT extra FROM competitor_events WHERE event_id = 'ce-persist-1'"
        ).fetchone()
        extra = json.loads(row["extra"])
        assert extra["is_test_data"] is True
        conn.close()

    def test_production_filter_excludes_test(self, test_db):
        """Verify the recommended production filter works."""
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        repair.p1_isolate_test_competitor_events(conn, dry_run=False)
        conn.commit()

        # Production query should exclude test events
        rows = conn.execute(
            "SELECT * FROM competitor_events WHERE json_extract(extra, '$.is_test_data') IS NULL"
        ).fetchall()
        assert len(rows) == 0  # all events in test DB are test data
        conn.close()


class TestP2StateRebuild:
    def test_test_states_cleared(self, test_db):
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        result = repair.p2_clear_test_states(conn, dry_run=False)
        conn.commit()

        # sig_iso_test_line states should be gone
        count = conn.execute(
            "SELECT COUNT(*) FROM brand_states WHERE product_line = 'sig_iso_test_line'"
        ).fetchone()[0]
        assert count == 0

        # Test transitions gone
        count = conn.execute("SELECT COUNT(*) FROM state_transitions").fetchone()[0]
        assert count == 0
        conn.close()

    def test_rebuilt_states_have_current_dates(self, test_db):
        repair = _get_repair_module()
        conn = repair.connect(test_db)
        conn.execute("BEGIN")
        repair.p0_normalize_markets(conn)
        repair.p0_normalize_product_line(conn)
        repair.p2_clear_test_states(conn)
        result = repair.p2_rebuild_brand_states(conn)
        conn.commit()

        # Should have rebuilt states
        rows = conn.execute(
            "SELECT as_of_date, product_line, market FROM brand_states ORDER BY as_of_date DESC"
        ).fetchall()
        assert len(rows) > 0

        # Latest state should be from 2026, not 2025-02-28
        latest = rows[0]
        assert latest["as_of_date"] >= "2026-01-01"
        conn.close()


class TestImportETLSourceFields:
    def test_transform_signals_preserves_source_fields(self):
        """Verify import_etl.transform_signals reads source_type/source_id/raw_text_ref from CSV."""
        repair_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        spec = importlib.util.spec_from_file_location(
            "import_etl",
            os.path.join(repair_dir, "import_etl.py"),
        )
        etl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(etl)

        # Simulate a CSV row with source fields
        rows = [{
            "signal_id": "test-sig-1",
            "date": "2026-03-01",
            "product_line": "moodyplus",
            "audience_segment": "general",
            "market": "us",
            "signal_type": "ga4_channel",
            "dimension": "sessions",
            "value": "100",
            "raw_text": "",
            "source": "ga4",
            "source_type": "analytics",
            "source_id": "ga4-prop-123",
            "raw_text_ref": "ref-456",
            "extra_json": "{}",
        }]

        result = etl.transform_signals(rows)
        assert len(result) == 1
        t = result[0]
        # source_type is index 10, source_id is 11, raw_text_ref is 12
        assert t[10] == "analytics"
        assert t[11] == "ga4-prop-123"
        assert t[12] == "ref-456"

    def test_transform_signals_none_when_missing(self):
        """source fields default to None when CSV columns are absent."""
        repair_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        spec = importlib.util.spec_from_file_location(
            "import_etl",
            os.path.join(repair_dir, "import_etl.py"),
        )
        etl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(etl)

        rows = [{
            "signal_id": "test-sig-2",
            "date": "2026-03-01",
            "product_line": "moodyplus",
            "audience_segment": "general",
            "market": "us",
            "signal_type": "ga4_channel",
            "dimension": "sessions",
            "value": "100",
            "raw_text": "",
            "source": "ga4",
            "extra_json": "{}",
        }]

        result = etl.transform_signals(rows)
        t = result[0]
        assert t[10] is None  # source_type
        assert t[11] is None  # source_id
        assert t[12] is None  # raw_text_ref
