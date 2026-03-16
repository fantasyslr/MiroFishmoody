#!/usr/bin/env python3
"""
竞品事件导入脚本
将审核后的 draft CSV 导入 brandiction.db 的 competitor_events 表。

规则:
- 只导入 review_status=approved 的行
- 没有 source_url 的事件不能导入 (provenance 要求)
- 幂等: event_id 冲突时跳过 (不覆盖)
- market/event_type/impact_estimate 标准化
- provenance 信息存入 extra JSON

用法:
    python import_competitor_events.py --csv ../uploads/competitor_events_draft.csv --db ../uploads/brandiction.db
    python import_competitor_events.py --csv ../uploads/competitor_events_draft.csv --db ../uploads/brandiction.db --dry-run
"""

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = {"price_cut", "new_launch", "campaign", "collab", "bundle_offer", "listing_change"}
VALID_IMPACTS = {"high", "medium", "low"}
VALID_SOURCES = {"official_site", "meta_ad_library", "google_ads_transparency", "tiktok_creative_center", "manual_note"}

EVENT_TYPE_ALIASES = {
    "pricecut": "price_cut",
    "price cut": "price_cut",
    "newlaunch": "new_launch",
    "new launch": "new_launch",
    "new_product": "new_launch",
    "bundle": "bundle_offer",
    "bundleoffer": "bundle_offer",
    "bundle offer": "bundle_offer",
    "collaboration": "collab",
    "listing": "listing_change",
    "listingchange": "listing_change",
    "listing change": "listing_change",
}

IMPACT_ALIASES = {
    "h": "high",
    "m": "medium",
    "med": "medium",
    "l": "low",
}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_market(market: str) -> str:
    return market.strip().lower()


def normalize_event_type(et: str) -> str | None:
    et = et.strip().lower()
    if et in VALID_EVENT_TYPES:
        return et
    return EVENT_TYPE_ALIASES.get(et)


def normalize_impact(impact: str) -> str | None:
    impact = impact.strip().lower()
    if impact in VALID_IMPACTS:
        return impact
    return IMPACT_ALIASES.get(impact)


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------

def import_events(csv_path: str, db_path: str, dry_run: bool = False):
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("No rows found in CSV.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing event IDs for idempotency check
    cursor.execute("SELECT event_id FROM competitor_events")
    existing_ids = {r[0] for r in cursor.fetchall()}

    imported = 0
    skipped_status = 0
    skipped_exists = 0
    skipped_no_source = 0
    skipped_invalid = 0

    for row in rows:
        # Map from draft columns to import columns
        review_status = row.get("review_status", "").strip().lower()

        # Only import approved events
        if review_status != "approved":
            skipped_status += 1
            continue

        source_url = row.get("source_url", "").strip()
        if not source_url:
            skipped_no_source += 1
            eid = row.get("suggested_event_id") or row.get("event_id", "?")
            print(f"  [SKIP] {eid}: no source_url, cannot import as real event", file=sys.stderr)
            continue

        # Determine event_id: use event_id if present, else suggested_event_id with "draft" removed
        event_id = row.get("event_id", "").strip()
        if not event_id:
            suggested = row.get("suggested_event_id", "").strip()
            event_id = suggested.replace("-draft-", "-") if suggested else ""
        if not event_id:
            skipped_invalid += 1
            print(f"  [SKIP] row has no event_id", file=sys.stderr)
            continue

        # Idempotency: skip if already exists
        if event_id in existing_ids:
            skipped_exists += 1
            continue

        # Normalize fields
        market = normalize_market(row.get("market", "global"))
        event_type_raw = row.get("suggested_event_type") or row.get("event_type", "")
        event_type = normalize_event_type(event_type_raw)
        if not event_type:
            skipped_invalid += 1
            print(f"  [SKIP] {event_id}: invalid event_type '{event_type_raw}'", file=sys.stderr)
            continue

        impact_raw = row.get("suggested_impact_estimate") or row.get("impact_estimate", "medium")
        impact = normalize_impact(impact_raw)
        if not impact:
            impact = "medium"  # fallback

        date_val = row.get("date", "").strip()
        competitor = row.get("competitor", "").strip()
        description = row.get("description", "").strip()
        source = row.get("source", "").strip()
        reviewer_notes = row.get("reviewer_notes", "").strip()
        confidence = row.get("confidence", "").strip()

        # Build extra JSON with provenance
        extra = {
            "source": source,
            "source_url": source_url,
            "confidence": confidence,
            "reviewer_notes": reviewer_notes,
            "imported_from": "competitor_collector",
        }
        # Merge any existing notes
        notes = row.get("notes", "").strip()
        if notes:
            extra["original_notes"] = notes

        if dry_run:
            print(f"  [DRY-RUN] Would import: {event_id} | {competitor} | {event_type} | {market}")
            imported += 1
            continue

        try:
            cursor.execute(
                """INSERT INTO competitor_events (event_id, date, competitor, market, event_type, description, impact_estimate, extra)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, date_val, competitor, market, event_type, description, impact, json.dumps(extra)),
            )
            existing_ids.add(event_id)
            imported += 1
        except sqlite3.IntegrityError:
            skipped_exists += 1

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"\n=== Import Summary ===")
    print(f"  Imported:              {imported}")
    print(f"  Skipped (not approved): {skipped_status}")
    print(f"  Skipped (already exists): {skipped_exists}")
    print(f"  Skipped (no source_url): {skipped_no_source}")
    print(f"  Skipped (invalid data):  {skipped_invalid}")
    if dry_run:
        print("  (dry-run mode, no changes written)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="导入审核后的竞品事件到 brandiction.db")
    parser.add_argument("--csv", required=True, help="Path to reviewed draft CSV")
    parser.add_argument("--db", required=True, help="Path to brandiction.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"CSV file not found: {args.csv}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.db).exists():
        print(f"Database not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    import_events(args.csv, args.db, args.dry_run)


if __name__ == "__main__":
    main()
