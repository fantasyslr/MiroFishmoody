"""
import_etl.py — 将 moody-etl 导出的 CSV 批量导入 Brandiction SQLite

用法:
    cd backend
    python scripts/import_etl.py /path/to/exports/2026-03-14

会自动备份现有 brandiction.db，然后用 INSERT OR REPLACE 批量写入。
"""

import csv
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime

BATCH_SIZE = 5000
DB_PATH = os.path.join(os.path.dirname(__file__), "../uploads/brandiction.db")


def backup_db(db_path: str) -> str:
    if not os.path.exists(db_path):
        return ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def read_csv(filepath: str) -> list[dict]:
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _str_or_none(v: str):
    return v if v else None


def _float_or_none(v: str):
    if not v or v.strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int_or_none(v: str):
    if not v or v.strip() == "":
        return None
    try:
        return int(float(v))  # handle "60.0" style
    except ValueError:
        return None


def transform_interventions(rows: list[dict], run_id: str) -> list[tuple]:
    """Return list of tuples matching INSERT column order."""
    result = []
    for r in rows:
        channel_mix_raw = _str_or_none(r.get("channel_mix", ""))
        channel_mix = json.dumps([channel_mix_raw]) if channel_mix_raw else None

        extra = _str_or_none(r.get("extra_json", "")) or "{}"

        result.append((
            r["intervention_id"],
            run_id,
            r.get("product_line") or "moodyplus",
            _str_or_none(r.get("date_start")),
            _str_or_none(r.get("date_end")),
            _str_or_none(r.get("theme")),
            _str_or_none(r.get("message_arc")),
            channel_mix,
            _float_or_none(r.get("budget", "")),
            _float_or_none(r.get("spend", "")),
            r.get("audience_segment") or "general",
            r.get("market") or "cn",
            _str_or_none(r.get("parent_campaign_id")),
            _str_or_none(r.get("source_entity_id")),
            _str_or_none(r.get("landing_url")),
            _str_or_none(r.get("source_platform")),
            _str_or_none(r.get("source_entity_level")),
            _str_or_none(r.get("objective")),
            _str_or_none(r.get("notes")),
            extra,
        ))
    return result


INTERVENTION_COLS = (
    "intervention_id", "run_id", "product_line",
    "date_start", "date_end", "theme", "message_arc",
    "channel_mix", "budget", "spend", "audience_segment", "market",
    "campaign_id", "creative_id", "landing_page",
    "platform", "channel_family", "objective", "notes", "extra",
)


def transform_outcomes(rows: list[dict]) -> list[tuple]:
    result = []
    for r in rows:
        extra = _str_or_none(r.get("extra_json", "")) or "{}"
        result.append((
            r["outcome_id"],
            r["intervention_id"],
            _str_or_none(r.get("window_label")),
            _str_or_none(r.get("date_start")),
            _str_or_none(r.get("date_end")),
            _int_or_none(r.get("impressions", "")),
            _int_or_none(r.get("clicks", "")),
            _float_or_none(r.get("ctr", "")),
            _float_or_none(r.get("cvr", "")),
            _float_or_none(r.get("revenue", "")),
            _float_or_none(r.get("roas", "")),
            _float_or_none(r.get("brand_lift", "")),
            _float_or_none(r.get("search_trend_delta", "")),
            _float_or_none(r.get("comment_sentiment", "")),
            _str_or_none(r.get("comment_summary")),
            _int_or_none(r.get("sessions", "")),
            None,  # pdp_views (not in CSV)
            _int_or_none(r.get("add_to_cart", "")),
            _int_or_none(r.get("checkout", "")),     # checkout -> checkout_started
            _int_or_none(r.get("orders", "")),        # orders -> purchases
            None,  # new_customers
            None,  # returning_customers
            _float_or_none(r.get("aov", "") if "aov" in r else ""),
            extra,
        ))
    return result


OUTCOME_COLS = (
    "outcome_id", "intervention_id", "window_label",
    "date_start", "date_end",
    "impressions", "clicks", "ctr", "cvr", "revenue", "roas",
    "brand_lift", "search_trend_delta", "comment_sentiment", "comment_summary",
    "sessions", "pdp_views", "add_to_cart", "checkout_started", "purchases",
    "new_customers", "returning_customers", "aov", "extra",
)


def transform_signals(rows: list[dict]) -> list[tuple]:
    result = []
    for r in rows:
        extra = _str_or_none(r.get("extra_json", "")) or "{}"
        result.append((
            r["signal_id"],
            r["date"],
            r.get("product_line") or "moodyplus",
            r.get("audience_segment") or "general",
            r.get("market") or "cn",
            _str_or_none(r.get("signal_type")),
            _str_or_none(r.get("dimension")),
            _float_or_none(r.get("value", "")),
            _str_or_none(r.get("raw_text")),
            _str_or_none(r.get("source")),
            _str_or_none(r.get("source_type")),
            _str_or_none(r.get("source_id")),
            _str_or_none(r.get("raw_text_ref")),
            extra,
        ))
    return result


SIGNAL_COLS = (
    "signal_id", "date", "product_line", "audience_segment", "market",
    "signal_type", "dimension", "value", "raw_text", "source",
    "source_type", "source_id", "raw_text_ref", "extra",
)


def bulk_insert(conn: sqlite3.Connection, table: str, columns: tuple, rows: list[tuple]):
    if not rows:
        return
    col_str = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})"
    for i in range(0, len(rows), BATCH_SIZE):
        conn.executemany(sql, rows[i:i + BATCH_SIZE])


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/import_etl.py <export_dir>")
        print("例如: python scripts/import_etl.py /Users/slr/Downloads/moody-etl/exports/2026-03-14")
        sys.exit(1)

    export_dir = sys.argv[1]
    # Derive run_id from directory name (date)
    batch_date = os.path.basename(export_dir.rstrip("/"))
    run_id = f"etl_{batch_date}"

    iv_path = os.path.join(export_dir, "interventions.csv")
    oc_path = os.path.join(export_dir, "outcomes.csv")
    sig_path = os.path.join(export_dir, "signals.csv")

    for p in [iv_path, oc_path, sig_path]:
        if not os.path.exists(p):
            print(f"文件不存在: {p}")
            sys.exit(1)

    db_path = os.path.abspath(DB_PATH)
    print(f"目标数据库: {db_path}")
    print(f"批次 run_id: {run_id}")

    # Backup
    bak = backup_db(db_path)
    if bak:
        print(f"已备份到: {bak}")

    # Read CSVs
    t0 = time.time()
    print("读取 CSV ...")
    iv_rows = read_csv(iv_path)
    oc_rows = read_csv(oc_path)
    sig_rows = read_csv(sig_path)
    print(f"  interventions: {len(iv_rows)} 行")
    print(f"  outcomes:      {len(oc_rows)} 行")
    print(f"  signals:       {len(sig_rows)} 行")

    # Transform
    print("转换数据 ...")
    iv_tuples = transform_interventions(iv_rows, run_id)
    oc_tuples = transform_outcomes(oc_rows)
    sig_tuples = transform_signals(sig_rows)

    # Insert
    print("写入数据库 ...")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        conn.execute("BEGIN")
        bulk_insert(conn, "interventions", INTERVENTION_COLS, iv_tuples)
        print(f"  interventions 写入完成")
        bulk_insert(conn, "outcomes", OUTCOME_COLS, oc_tuples)
        print(f"  outcomes 写入完成")
        bulk_insert(conn, "signals", SIGNAL_COLS, sig_tuples)
        print(f"  signals 写入完成")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"写入失败，已回滚: {e}")
        sys.exit(1)

    # Verify
    counts = {}
    for table in ["interventions", "outcomes", "signals", "competitor_events", "brand_states"]:
        c = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        counts[table] = c

    elapsed = time.time() - t0
    print(f"\n导入完成 ({elapsed:.1f}s)")
    print("数据库当前行数:")
    for table, count in counts.items():
        print(f"  {table}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
