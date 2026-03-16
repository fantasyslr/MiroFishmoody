#!/usr/bin/env python3
"""
Global → Market Applicability 辅助层
读取 competitor_events 中的 global 事件，结合竞品 profile，
生成 candidate_markets 建议，输出到 CSV。

不修改原始 competitor_events，不写回主表。

用法:
    python generate_market_hints.py --db ../uploads/brandiction.db --watchlist ../uploads/templates/competitor_watchlist.yaml
"""

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Competitor → market profile
# 基于 watchlist + 行业认知，判断每个竞品的主要活跃市场
# ---------------------------------------------------------------------------

# Fallback: if competitor not in watchlist, infer from interventions data
DEFAULT_MARKET_PROFILE = {
    "olensglobal": {"primary": ["kr", "us", "sg"], "rationale": "Korean brand, strong in Asia + US DTC"},
    "ttdeye": {"primary": ["us", "sg", "au", "ca"], "rationale": "China-origin DTC, heavy English-market ads"},
    "dimplecolor": {"primary": ["us"], "rationale": "US-focused DTC colored lens brand"},
    "unibling": {"primary": ["us", "kr", "sg"], "rationale": "Korea-origin, global DTC"},
    "eyecandys": {"primary": ["us", "ca", "au"], "rationale": "US-based DTC, ships NA + AU"},
    "pinkparadise": {"primary": ["us", "sg", "au", "ca"], "rationale": "Long-running global DTC, pinkyparadise.com"},
    "hapakristin": {"primary": ["us", "kr"], "rationale": "Influencer brand, Korea-origin, US DTC focus"},
    "just4kira": {"primary": ["us"], "rationale": "US-focused anime/cosplay lens DTC"},
}


def load_watchlist_markets(watchlist_path: str) -> dict[str, list[str]]:
    """Extract competitor → markets from watchlist yaml."""
    if not watchlist_path or not Path(watchlist_path).exists():
        return {}
    with open(watchlist_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = {}
    for comp in data.get("competitors", []):
        name = comp["competitor"]
        markets = comp.get("markets", [])
        result[name] = markets
    return result


def get_candidate_markets(competitor: str, watchlist_markets: dict) -> tuple[list[str], str]:
    """Return (candidate_markets, rationale) for a competitor."""
    # Priority 1: watchlist config
    if competitor in watchlist_markets and watchlist_markets[competitor]:
        markets = [m for m in watchlist_markets[competitor] if m != "global"]
        if markets:
            return markets, f"from watchlist config: {watchlist_markets[competitor]}"

    # Priority 2: built-in profile
    if competitor in DEFAULT_MARKET_PROFILE:
        profile = DEFAULT_MARKET_PROFILE[competitor]
        return profile["primary"], profile["rationale"]

    # Priority 3: unknown → keep global only
    return [], "unknown competitor, no market mapping available"


def get_interventions_markets(db_path: str) -> set[str]:
    """Get set of markets that have interventions data."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT DISTINCT market FROM interventions WHERE market != 'unknown'").fetchall()
    conn.close()
    return {r[0] for r in rows}


def generate_hints(db_path: str, watchlist_path: str, output_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get global competitor events (only real ones, not test data)
    rows = conn.execute("""
        SELECT event_id, date, competitor, market, event_type, impact_estimate,
               description, extra
        FROM competitor_events
        WHERE market = 'global'
          AND (json_extract(extra, '$.is_test_data') IS NULL
               OR json_extract(extra, '$.is_test_data') = 0)
    """).fetchall()
    conn.close()

    if not rows:
        print("No global competitor events found.")
        return

    watchlist_markets = load_watchlist_markets(watchlist_path)
    active_markets = get_interventions_markets(db_path)

    hints = []
    for row in rows:
        competitor = row["competitor"]
        extra = json.loads(row["extra"] or "{}")
        source_url = extra.get("source_url", "")

        candidate_markets, rationale = get_candidate_markets(competitor, watchlist_markets)

        # Filter to only markets that have interventions data (actionable)
        actionable = [m for m in candidate_markets if m in active_markets]
        non_actionable = [m for m in candidate_markets if m not in active_markets]

        # Confidence based on how specific the source is
        if ".com/" in source_url and not source_url.endswith(".com/"):
            # Deeper page → slightly higher confidence
            conf = "medium"
        else:
            # Homepage only → low confidence for market specificity
            conf = "low"

        hints.append({
            "event_id": row["event_id"],
            "competitor": competitor,
            "event_type": row["event_type"],
            "original_market": row["market"],
            "candidate_markets": "|".join(actionable) if actionable else "none_with_data",
            "candidate_markets_no_data": "|".join(non_actionable) if non_actionable else "",
            "rationale": rationale,
            "confidence": conf,
            "source_url": source_url,
            "note": f"global event from {source_url}; not auto-split to market-specific records",
        })

    # Write CSV
    fieldnames = [
        "event_id", "competitor", "event_type", "original_market",
        "candidate_markets", "candidate_markets_no_data",
        "rationale", "confidence", "source_url", "note",
    ]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(hints)

    print(f"Generated {len(hints)} market hints → {out}")

    # Summary
    print("\n--- Market Hint Summary ---")
    for h in hints:
        print(f"  {h['event_id']} ({h['competitor']}, {h['event_type']})")
        print(f"    candidate_markets (with data): {h['candidate_markets']}")
        if h['candidate_markets_no_data']:
            print(f"    candidate_markets (no data):   {h['candidate_markets_no_data']}")
        print(f"    confidence: {h['confidence']} | rationale: {h['rationale']}")


def main():
    parser = argparse.ArgumentParser(description="Global→Market applicability hints for competitor events")
    parser.add_argument("--db", required=True, help="Path to brandiction.db")
    parser.add_argument("--watchlist", default=None, help="Path to competitor_watchlist.yaml")
    parser.add_argument("--output", default=None, help="Output CSV path")
    args = parser.parse_args()

    output = args.output or str(Path(__file__).parent.parent / "uploads" / "competitor_events_market_hint.csv")
    generate_hints(args.db, args.watchlist, output)


if __name__ == "__main__":
    main()
