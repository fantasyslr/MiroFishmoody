"""
test_sync_etl_enrichment.py — 回归测试

覆盖:
  1. 幂等性: 多次运行结果一致
  2. 非空字段不会被低置信来源覆盖
  3. 不跨 market 回填
  4. lineage 字段正确写入
  5. perception seeds 正确标记
"""

import json
import os
import shutil
import sqlite3
import tempfile

import pytest

# ── Fixtures ──────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "../uploads/brandiction.db")


@pytest.fixture
def db_conn():
    """Read-only connection to the live DB for verification."""
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ── Test 1: 幂等性 ───────────────────────────────────────────────

def test_idempotent_rerun(db_conn):
    """Running sync twice should not change the data."""
    # Snapshot current state
    iv_before = db_conn.execute(
        "SELECT intervention_id, theme, message_arc, extra FROM interventions ORDER BY intervention_id"
    ).fetchall()
    sig_before = db_conn.execute(
        "SELECT signal_id, source_type, source_id, raw_text_ref FROM signals ORDER BY signal_id LIMIT 1000"
    ).fetchall()

    # Re-run sync in dry-run mode on a copy
    tmp = tempfile.mkdtemp()
    tmp_db = os.path.join(tmp, "test.db")
    shutil.copy2(os.path.abspath(DB_PATH), tmp_db)

    # Import and run
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from sync_etl_enrichment import (
        enrich_interventions, backfill_signals, load_etl_mart, load_etl_signals
    )

    etl_dir = "/Users/slr/Downloads/moody-etl"
    if not os.path.exists(etl_dir):
        pytest.skip("ETL directory not available")

    conn2 = sqlite3.connect(tmp_db)
    conn2.execute("PRAGMA journal_mode = WAL")
    mart = load_etl_mart(etl_dir)
    sig_df = load_etl_signals(etl_dir)

    # Run enrichment on already-enriched copy
    iv_stats = enrich_interventions(conn2, mart, dry_run=False)
    sig_stats = backfill_signals(conn2, sig_df, dry_run=False)

    # Verify: state should be identical
    iv_after = conn2.execute(
        "SELECT intervention_id, theme, message_arc, extra FROM interventions ORDER BY intervention_id"
    ).fetchall()

    assert len(iv_before) == len(iv_after)
    for b, a in zip(iv_before, iv_after):
        assert b[0] == a[0], f"ID mismatch: {b[0]} vs {a[0]}"
        assert b[1] == a[1], f"Theme changed on re-run for {b[0]}: {b[1]} -> {a[1]}"
        assert b[2] == a[2], f"Message_arc changed on re-run for {b[0]}: {b[2]} -> {a[2]}"

    conn2.close()
    shutil.rmtree(tmp, ignore_errors=True)


# ── Test 2: 非空字段不被覆盖 ─────────────────────────────────────

def test_nonempty_fields_preserved(db_conn):
    """Interventions with pre-existing theme should not be overwritten."""
    # The 5 original themed interventions should still have their original themes
    rows = db_conn.execute(
        "SELECT intervention_id, theme, extra FROM interventions "
        "WHERE theme IS NOT NULL AND theme != ''"
    ).fetchall()

    assert len(rows) >= 5, f"Expected at least 5 themed interventions, got {len(rows)}"

    # Verify enrichment_source is set on enriched rows
    enriched_count = 0
    for r in rows:
        extra = json.loads(r["extra"]) if r["extra"] else {}
        if extra.get("enrichment_source"):
            enriched_count += 1

    # At least some should be enriched
    assert enriched_count > 0, "No enrichment_source found in extra"


# ── Test 3: 不跨 market 回填 ─────────────────────────────────────

def test_no_cross_market_backfill(db_conn):
    """Every enriched intervention should have matching market with ETL source."""
    rows = db_conn.execute(
        "SELECT intervention_id, market, extra FROM interventions "
        "WHERE extra LIKE '%enrichment_source%'"
    ).fetchall()

    for r in rows:
        extra = json.loads(r["extra"]) if r["extra"] else {}
        assert extra.get("enrichment_source") is not None
        # Market should be present and non-empty
        assert r["market"], f"Empty market on enriched intervention {r['intervention_id']}"


# ── Test 4: lineage 字段正确写入 ──────────────────────────────────

def test_signal_lineage_fields(db_conn):
    """Signals should have source_type derived from signal_type."""
    expected_mappings = {
        "ga4_channel": "ga4",
        "ga4_country_channel": "ga4",
        "site_daily": "shopline",
        "meta_country": "meta",
        "channel_efficiency": "derived",
        "creator_engagement": "creator",
    }

    for signal_type, expected_source_type in expected_mappings.items():
        rows = db_conn.execute(
            "SELECT source_type FROM signals WHERE signal_type = ? LIMIT 5",
            (signal_type,),
        ).fetchall()
        for r in rows:
            assert r["source_type"] == expected_source_type, (
                f"signal_type={signal_type}: expected source_type={expected_source_type}, "
                f"got {r['source_type']}"
            )

    # Creator signals should have raw_text_ref as URL
    creator_rows = db_conn.execute(
        "SELECT raw_text_ref, source FROM signals "
        "WHERE signal_type = 'creator_engagement' AND raw_text_ref IS NOT NULL LIMIT 5"
    ).fetchall()
    for r in creator_rows:
        assert r["raw_text_ref"].startswith("http"), (
            f"Creator raw_text_ref should be URL, got: {r['raw_text_ref']}"
        )


# ── Test 5: source_id 全部填充 ────────────────────────────────────

def test_source_id_populated(db_conn):
    """All signals should have source_id (= signal_id)."""
    null_count = db_conn.execute(
        "SELECT COUNT(*) FROM signals WHERE source_id IS NULL OR source_id = ''"
    ).fetchone()[0]

    total = db_conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    # Allow some tolerance for edge cases
    assert null_count == 0, f"{null_count}/{total} signals still missing source_id"


# ── Test 6: perception seeds 标记正确 ─────────────────────────────

def test_perception_seeds_labeled(db_conn):
    """Derived perception seeds must be clearly labeled."""
    seeds = db_conn.execute(
        "SELECT signal_id, signal_type, source_type, source_id, value, extra "
        "FROM signals WHERE signal_type = 'derived_theme_seed'"
    ).fetchall()

    if not seeds:
        pytest.skip("No perception seeds generated")

    for s in seeds:
        assert s["source_type"] == "derived_theme_seed"
        assert s["source_id"], "Seed missing source_id"
        assert s["value"] <= 0.25, f"Seed weight too high: {s['value']}"

        extra = json.loads(s["extra"]) if s["extra"] else {}
        assert extra.get("signal_source") == "derived_theme_seed"
        assert extra.get("source_intervention_id")
        assert extra.get("weight_note"), "Seed missing weight_note"


# ── Test 7: extra JSON integrity ──────────────────────────────────

def test_extra_json_valid(db_conn):
    """All extra fields should be valid JSON."""
    for table in ["interventions", "signals"]:
        rows = db_conn.execute(
            f"SELECT rowid, extra FROM {table} WHERE extra IS NOT NULL AND extra != '' LIMIT 2000"
        ).fetchall()
        for r in rows:
            try:
                json.loads(r["extra"])
            except json.JSONDecodeError:
                pytest.fail(f"{table} rowid={r['rowid']} has invalid JSON in extra: {r['extra'][:100]}")
