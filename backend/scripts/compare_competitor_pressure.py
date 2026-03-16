#!/usr/bin/env python3
"""
Competitor Pressure A/B 对比脚本
在同一个 market 上跑两次 backtest：
  A) 无竞品事件 (baseline)
  B) 有竞品事件 (with_events)
对比 competitor_pressure 维度的差异。

由于当前真实事件 market=global，而系统用严格 market 过滤，
本脚本也对 global market 的 interventions 做 backtest。

同时模拟：如果将 global 事件映射到 us market 会怎样。

用法:
    python compare_competitor_pressure.py --db ../uploads/brandiction.db
"""

import argparse
import copy
import json
import sqlite3
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.brandiction_store import BrandictionStore
from app.services.brand_state_engine import BrandStateEngine, PERCEPTION_DIMENSIONS


def run_comparison(db_path: str):
    store = BrandictionStore(db_path)
    engine = BrandStateEngine(store)

    print("=" * 70)
    print("COMPETITOR PRESSURE A/B COMPARISON")
    print("=" * 70)

    # ---------------------------------------------------------------
    # Part 1: Check what events exist per market
    # ---------------------------------------------------------------
    print("\n--- 1. Competitor Events by Market ---")
    for mkt in ["global", "us", "cn", "jp", "sg", "kr"]:
        events = store.list_competitor_events(market=mkt)
        real_events = [e for e in events if not (e.extra or {}).get("is_test_data")]
        test_events = [e for e in events if (e.extra or {}).get("is_test_data")]
        if events:
            print(f"  {mkt}: {len(real_events)} real + {len(test_events)} test = {len(events)} total")
            for e in real_events:
                print(f"    [{e.event_id}] {e.competitor} | {e.event_type} | impact={e.impact_estimate}")

    # ---------------------------------------------------------------
    # Part 2: Backtest on 'global' market (where our events live)
    # ---------------------------------------------------------------
    print("\n--- 2. Backtest: global market ---")
    global_events = store.list_competitor_events(market="global")
    real_global = [e for e in global_events if not (e.extra or {}).get("is_test_data")]
    print(f"  Real global competitor events: {len(real_global)}")

    # Check interventions count
    all_ivs = store.list_interventions()
    global_ivs = [iv for iv in all_ivs if (iv.market or "cn") == "global"]
    print(f"  Global market interventions: {len(global_ivs)}")

    if global_ivs:
        # Run backtest with events
        result_with = engine.backtest(product_line="moodyplus", audience_segment="general", market="global")
        print(f"\n  Backtest WITH competitor events (market=global):")
        print(f"    tested: {result_with['tested']}, skipped: {result_with['skipped']}")
        print(f"    overall MAE: {result_with['mean_absolute_error']}")
        print(f"    per-dimension MAE:")
        for dim, mae in result_with.get("per_dimension_mae", {}).items():
            marker = " <<<" if dim == "competitor_pressure" else ""
            print(f"      {dim}: {mae}{marker}")

        # Now temporarily remove global competitor events and re-run
        # We do this by creating a patched engine with no events
        print(f"\n  Backtest WITHOUT competitor events (removing global events temporarily):")
        _backup_events(store, db_path, "global")
        try:
            result_without = engine.backtest(product_line="moodyplus", audience_segment="general", market="global")
            print(f"    tested: {result_without['tested']}, skipped: {result_without['skipped']}")
            print(f"    overall MAE: {result_without['mean_absolute_error']}")
            print(f"    per-dimension MAE:")
            for dim, mae in result_without.get("per_dimension_mae", {}).items():
                marker = " <<<" if dim == "competitor_pressure" else ""
                print(f"      {dim}: {mae}{marker}")
        finally:
            _restore_events(store, db_path, "global")

        # Diff
        print(f"\n  --- DIFF (with_events - without_events) ---")
        mae_w = result_with.get("per_dimension_mae", {})
        mae_wo = result_without.get("per_dimension_mae", {})
        for dim in PERCEPTION_DIMENSIONS:
            w = mae_w.get(dim, 0)
            wo = mae_wo.get(dim, 0)
            diff = round(w - wo, 4)
            if abs(diff) > 0.0001:
                direction = "+" if diff > 0 else ""
                print(f"    {dim}: {direction}{diff} (with={w}, without={wo})")
            else:
                print(f"    {dim}: no change")

        # Check individual details for competitor_pressure impact
        print(f"\n  --- Competitor Pressure in Individual Predictions ---")
        for d in result_with.get("details", []):
            cp_actual = d["actual_delta"].get("competitor_pressure", 0)
            cp_pred = d["predicted_delta"].get("competitor_pressure", 0)
            if abs(cp_actual) > 0.001 or abs(cp_pred) > 0.001:
                print(f"    {d['intervention_id']}: actual_cp={cp_actual}, predicted_cp={cp_pred}, error={d['absolute_errors'].get('competitor_pressure', 0)}")
    else:
        print("  No global interventions found. Cannot run backtest on global market.")

    # ---------------------------------------------------------------
    # Part 3: US market analysis (where most competitors are active)
    # ---------------------------------------------------------------
    print("\n--- 3. US Market Analysis ---")
    us_ivs = [iv for iv in all_ivs if (iv.market or "cn") == "us"]
    us_events = store.list_competitor_events(market="us")
    real_us = [e for e in us_events if not (e.extra or {}).get("is_test_data")]
    print(f"  US interventions: {len(us_ivs)}")
    print(f"  US competitor events (real): {len(real_us)}")
    print(f"  US competitor events (test): {len(us_events) - len(real_us)}")

    if us_ivs:
        result_us = engine.backtest(product_line="moodyplus", audience_segment="general", market="us")
        print(f"\n  Backtest on US market:")
        print(f"    tested: {result_us['tested']}, skipped: {result_us['skipped']}")
        print(f"    overall MAE: {result_us['mean_absolute_error']}")
        cp_mae = result_us.get("per_dimension_mae", {}).get("competitor_pressure", "N/A")
        print(f"    competitor_pressure MAE: {cp_mae}")

    # ---------------------------------------------------------------
    # Part 4: Simulation — what if global events were US events?
    # ---------------------------------------------------------------
    print("\n--- 4. Simulation: What if global events mapped to US? ---")
    if real_global and us_ivs:
        # Temporarily copy global events as US events
        conn = sqlite3.connect(db_path)
        sim_ids = []
        for ev in real_global:
            sim_id = f"sim-us-{ev.event_id}"
            sim_ids.append(sim_id)
            extra = dict(ev.extra or {})
            extra["simulated_from"] = ev.event_id
            extra["original_market"] = "global"
            try:
                conn.execute(
                    "INSERT INTO competitor_events (event_id, date, competitor, market, event_type, description, impact_estimate, extra) VALUES (?,?,?,?,?,?,?,?)",
                    (sim_id, ev.date, ev.competitor, "us", ev.event_type, ev.description, ev.impact_estimate, json.dumps(extra))
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        conn.close()

        try:
            result_us_sim = engine.backtest(product_line="moodyplus", audience_segment="general", market="us")
            print(f"  Backtest US with simulated competitor events:")
            print(f"    tested: {result_us_sim['tested']}, skipped: {result_us_sim['skipped']}")
            print(f"    overall MAE: {result_us_sim['mean_absolute_error']}")
            cp_mae_sim = result_us_sim.get("per_dimension_mae", {}).get("competitor_pressure", "N/A")
            print(f"    competitor_pressure MAE: {cp_mae_sim}")

            # Compare to US without simulation
            if us_ivs:
                mae_us_before = result_us.get("per_dimension_mae", {}).get("competitor_pressure", 0)
                mae_us_after = result_us_sim.get("per_dimension_mae", {}).get("competitor_pressure", 0) if isinstance(cp_mae_sim, (int, float)) else 0
                diff = round(mae_us_after - mae_us_before, 4) if isinstance(mae_us_after, (int, float)) else "N/A"
                print(f"\n    competitor_pressure MAE change: {diff}")
                print(f"    overall MAE: {result_us.get('mean_absolute_error', 0)} → {result_us_sim['mean_absolute_error']}")

            # Show which interventions were affected
            for d in result_us_sim.get("details", []):
                cp_actual = d["actual_delta"].get("competitor_pressure", 0)
                cp_pred = d["predicted_delta"].get("competitor_pressure", 0)
                if abs(cp_actual) > 0.001 or abs(cp_pred) > 0.001:
                    print(f"    {d['intervention_id']}: actual_cp={cp_actual}, predicted_cp={cp_pred}")
        finally:
            # Clean up simulated events
            conn = sqlite3.connect(db_path)
            for sim_id in sim_ids:
                conn.execute("DELETE FROM competitor_events WHERE event_id = ?", (sim_id,))
            conn.commit()
            conn.close()
            print("\n  (Simulated US events cleaned up)")
    else:
        print("  Skipped — no global events or no US interventions")

    # ---------------------------------------------------------------
    # Part 5: Summary & Recommendation
    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SUMMARY & RECOMMENDATION")
    print("=" * 70)


def _backup_events(store, db_path, market):
    """Temporarily remove competitor events for a market."""
    conn = sqlite3.connect(db_path)
    conn.execute(f"CREATE TABLE IF NOT EXISTS _ce_backup_{market} AS SELECT * FROM competitor_events WHERE market = ?", (market,))
    conn.execute("DELETE FROM competitor_events WHERE market = ?", (market,))
    conn.commit()
    conn.close()


def _restore_events(store, db_path, market):
    """Restore backed up competitor events."""
    conn = sqlite3.connect(db_path)
    conn.execute(f"INSERT OR IGNORE INTO competitor_events SELECT * FROM _ce_backup_{market}")
    conn.execute(f"DROP TABLE IF EXISTS _ce_backup_{market}")
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Competitor pressure A/B comparison")
    parser.add_argument("--db", required=True, help="Path to brandiction.db")
    args = parser.parse_args()
    run_comparison(args.db)


if __name__ == "__main__":
    main()
