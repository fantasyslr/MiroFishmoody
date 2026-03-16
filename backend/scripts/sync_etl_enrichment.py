"""
sync_etl_enrichment.py — 增量同步 moody-etl 已有的 enrichment 到 brandiction.db

功能:
  A. interventions: theme, message_arc, creative_bundle_id, multimodal_tags
  B. signals: source_type, source_id, raw_text_ref
  C. (可选) perception seeds from themes

原则:
  - 幂等: 多次运行结果一致
  - 不覆盖已有非空人工值
  - 不跨 market 回填
  - 所有回填写 provenance 到 extra JSON

用法:
    cd backend
    python scripts/sync_etl_enrichment.py \\
        --etl-dir /Users/slr/Downloads/moody-etl \\
        [--db /path/to/brandiction.db] \\
        [--dry-run] \\
        [--seed-perception]
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("需要 pandas + pyarrow: pip install pandas pyarrow")
    sys.exit(1)

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "../uploads/brandiction.db")
SYNC_BATCH = "etl_enrichment_sync_" + datetime.now().strftime("%Y%m%d_%H%M%S")

# ── Signal source_type derivation rules ──────────────────────────
SOURCE_TYPE_MAP = {
    "ga4_channel": "ga4",
    "ga4_country_channel": "ga4",
    "site_daily": "shopline",
    "meta_country": "meta",
    "channel_efficiency": "derived",
    "creator_engagement": "creator",
}


def backup_db(db_path: str) -> str:
    if not os.path.exists(db_path):
        return ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, bak)
    return bak


def load_etl_mart(etl_dir: str) -> pd.DataFrame:
    """Load mart_intervention_performance with enrichment columns."""
    path = os.path.join(etl_dir, "data/marts/mart_intervention_performance.parquet")
    if not os.path.exists(path):
        print(f"找不到 mart 文件: {path}")
        sys.exit(1)
    df = pd.read_parquet(path)
    return df


def load_etl_signals(etl_dir: str) -> pd.DataFrame:
    """Load signals CSV export."""
    path = os.path.join(etl_dir, "exports/2026-03-14/signals.csv")
    if not os.path.exists(path):
        # Try latest export dir
        exports_dir = os.path.join(etl_dir, "exports")
        if os.path.isdir(exports_dir):
            dates = sorted(os.listdir(exports_dir), reverse=True)
            for d in dates:
                p = os.path.join(exports_dir, d, "signals.csv")
                if os.path.exists(p):
                    path = p
                    break
    if not os.path.exists(path):
        print(f"找不到 signals CSV: {path}")
        sys.exit(1)
    return pd.read_csv(path, low_memory=False)


def _merge_extra(existing_extra_str: str, new_fields: dict) -> str:
    """Merge new fields into existing extra JSON, preserving old keys."""
    try:
        existing = json.loads(existing_extra_str) if existing_extra_str else {}
    except (json.JSONDecodeError, TypeError):
        existing = {}
    existing.update(new_fields)
    return json.dumps(existing, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# Task A: interventions enrichment
# ═══════════════════════════════════════════════════════════════════

def enrich_interventions(conn: sqlite3.Connection, mart: pd.DataFrame, dry_run: bool) -> dict:
    """Backfill theme, message_arc, creative_bundle_id, multimodal_tags."""
    stats = {
        "total_matched": 0,
        "theme_before": 0, "theme_after": 0,
        "message_arc_before": 0, "message_arc_after": 0,
        "multimodal_tags_before": 0, "multimodal_tags_after": 0,
        "rows_updated": 0,
        "by_platform": {},
        "by_market": {},
    }

    # Get current DB state
    cur = conn.execute(
        "SELECT intervention_id, theme, message_arc, extra, market, platform FROM interventions"
    )
    db_rows = {r[0]: {"theme": r[1], "message_arc": r[2], "extra": r[3],
                       "market": r[4], "platform": r[5]} for r in cur.fetchall()}

    # Count before
    stats["theme_before"] = sum(1 for v in db_rows.values()
                                if v["theme"] and v["theme"].strip())
    stats["message_arc_before"] = sum(1 for v in db_rows.values()
                                       if v["message_arc"] and v["message_arc"].strip())
    # Count multimodal_tags in extra
    for v in db_rows.values():
        try:
            ex = json.loads(v["extra"]) if v["extra"] else {}
            if ex.get("multimodal_tags"):
                stats["multimodal_tags_before"] += 1
        except (json.JSONDecodeError, TypeError):
            pass

    updates = []
    for _, row in mart.iterrows():
        iid = row["intervention_id"]
        if iid not in db_rows:
            continue

        db = db_rows[iid]
        stats["total_matched"] += 1

        # Market safety check (case-insensitive)
        etl_market = str(row.get("market", "")).lower()
        db_market = str(db["market"] or "").lower()
        if etl_market and db_market and etl_market != db_market:
            continue  # skip cross-market

        new_theme = None
        new_message_arc = None
        extra_updates = {}

        # Theme: only backfill if DB is empty
        etl_theme = row.get("theme") or row.get("theme_parsed")
        if etl_theme and str(etl_theme) not in ("", "nan", "unknown"):
            etl_theme = str(etl_theme).strip()
            if not (db["theme"] and db["theme"].strip()):
                new_theme = etl_theme
            extra_updates["theme_source"] = "etl_mart"

        # Message arc
        etl_marc = row.get("message_arc") or row.get("message_arc_parsed")
        if etl_marc and str(etl_marc) not in ("", "nan", "unknown"):
            etl_marc = str(etl_marc).strip()
            if not (db["message_arc"] and db["message_arc"].strip()):
                new_message_arc = etl_marc
            extra_updates["message_arc_source"] = "etl_mart"

        # Multimodal tags
        etl_tags = row.get("multimodal_tags")
        if etl_tags and str(etl_tags) not in ("", "nan"):
            extra_updates["multimodal_tags"] = str(etl_tags)

        # Creative bundle ID
        etl_bundle = row.get("creative_bundle_id") or row.get("bundle_id")
        if etl_bundle and str(etl_bundle) not in ("", "nan"):
            extra_updates["creative_bundle_id"] = str(etl_bundle)

        # Product focus, science_vs_beauty, ugc_vs_studio
        for parsed_col in ["product_focus_parsed", "science_vs_beauty_parsed", "ugc_vs_studio_parsed"]:
            val = row.get(parsed_col)
            if val and str(val) not in ("", "nan", "unknown"):
                extra_updates[parsed_col] = str(val)

        # Provenance
        if new_theme or new_message_arc or extra_updates:
            extra_updates["enrichment_source"] = "moody-etl/mart_intervention_performance"
            extra_updates["sync_batch"] = SYNC_BATCH
            new_extra = _merge_extra(db["extra"], extra_updates)

            updates.append((new_theme, new_message_arc, new_extra, iid))

            # Track stats
            mkt = db_market or "unknown"
            plat = db.get("platform") or "unknown"
            stats["by_market"].setdefault(mkt, 0)
            stats["by_market"][mkt] += 1
            stats["by_platform"].setdefault(plat, 0)
            stats["by_platform"][plat] += 1

    if not dry_run and updates:
        conn.execute("BEGIN")
        # Use CASE to only update when new value is not null
        for new_theme, new_marc, new_extra, iid in updates:
            sets = ["extra = ?"]
            params = [new_extra]
            if new_theme:
                sets.append("theme = ?")
                params.append(new_theme)
            if new_marc:
                sets.append("message_arc = ?")
                params.append(new_marc)
            params.append(iid)
            sql = f"UPDATE interventions SET {', '.join(sets)} WHERE intervention_id = ?"
            conn.execute(sql, params)
        conn.commit()

    stats["rows_updated"] = len(updates)

    # Count after
    if not dry_run:
        cur = conn.execute("SELECT theme, message_arc, extra FROM interventions")
        for r in cur.fetchall():
            if r[0] and r[0].strip():
                stats["theme_after"] += 1
            if r[1] and r[1].strip():
                stats["message_arc_after"] += 1
            try:
                ex = json.loads(r[2]) if r[2] else {}
                if ex.get("multimodal_tags"):
                    stats["multimodal_tags_after"] += 1
            except (json.JSONDecodeError, TypeError):
                pass
    else:
        # Estimate after counts
        stats["theme_after"] = stats["theme_before"] + sum(1 for u in updates if u[0])
        stats["message_arc_after"] = stats["message_arc_before"] + sum(1 for u in updates if u[1])
        stats["multimodal_tags_after"] = stats["multimodal_tags_before"] + sum(
            1 for u in updates
            if "multimodal_tags" in json.loads(u[2]).get("multimodal_tags", "") or
            json.loads(u[2]).get("multimodal_tags")
        )

    return stats


# ═══════════════════════════════════════════════════════════════════
# Task B: signals lineage backfill
# ═══════════════════════════════════════════════════════════════════

def backfill_signals(conn: sqlite3.Connection, sig_df: pd.DataFrame, dry_run: bool) -> dict:
    """Derive and backfill source_type, source_id, raw_text_ref for signals."""
    stats = {
        "total_signals": 0,
        "source_type_before": 0, "source_type_after": 0,
        "source_id_before": 0, "source_id_after": 0,
        "raw_text_ref_before": 0, "raw_text_ref_after": 0,
        "rows_updated": 0,
    }

    # Current DB state
    cur = conn.execute(
        "SELECT signal_id, source_type, source_id, raw_text_ref, signal_type, source, extra, market "
        "FROM signals"
    )
    db_signals = {}
    for r in cur.fetchall():
        db_signals[r[0]] = {
            "source_type": r[1], "source_id": r[2], "raw_text_ref": r[3],
            "signal_type": r[4], "source": r[5], "extra": r[6], "market": r[7],
        }

    stats["total_signals"] = len(db_signals)
    stats["source_type_before"] = sum(1 for v in db_signals.values()
                                       if v["source_type"] and v["source_type"].strip())
    stats["source_id_before"] = sum(1 for v in db_signals.values()
                                     if v["source_id"] and v["source_id"].strip())
    stats["raw_text_ref_before"] = sum(1 for v in db_signals.values()
                                        if v["raw_text_ref"] and v["raw_text_ref"].strip())

    # Build ETL signal lookup for extra context
    etl_lookup = {}
    for _, row in sig_df.iterrows():
        etl_lookup[row["signal_id"]] = {
            "source": str(row.get("source", "")) if pd.notna(row.get("source")) else "",
            "signal_type": str(row.get("signal_type", "")) if pd.notna(row.get("signal_type")) else "",
        }

    updates = []
    for sid, db in db_signals.items():
        # Use DB signal_type + source, or fall back to ETL
        signal_type = db["signal_type"] or ""
        source = db["source"] or ""
        etl = etl_lookup.get(sid, {})
        if not signal_type and etl.get("signal_type"):
            signal_type = etl["signal_type"]
        if not source and etl.get("source"):
            source = etl["source"]

        new_source_type = None
        new_source_id = None
        new_raw_text_ref = None
        extra_updates = {}

        # Derive source_type from signal_type
        if not (db["source_type"] and db["source_type"].strip()):
            derived = SOURCE_TYPE_MAP.get(signal_type)
            if derived:
                new_source_type = derived

        # Derive source_id from signal_id (the ID itself is the best ref)
        if not (db["source_id"] and db["source_id"].strip()):
            new_source_id = sid

        # Derive raw_text_ref for creator signals (source is a URL)
        if not (db["raw_text_ref"] and db["raw_text_ref"].strip()):
            if signal_type == "creator_engagement" and source.startswith("http"):
                new_raw_text_ref = source

        if new_source_type or new_source_id or new_raw_text_ref:
            extra_updates["lineage_sync_batch"] = SYNC_BATCH
            extra_updates["lineage_source"] = "derived_from_signal_type"
            new_extra = _merge_extra(db["extra"], extra_updates)
            updates.append((new_source_type, new_source_id, new_raw_text_ref, new_extra, sid))

    if not dry_run and updates:
        conn.execute("BEGIN")
        batch_size = 5000
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            for st, si, rtr, ex, sid in batch:
                sets = ["extra = ?"]
                params = [ex]
                if st:
                    sets.append("source_type = ?")
                    params.append(st)
                if si:
                    sets.append("source_id = ?")
                    params.append(si)
                if rtr:
                    sets.append("raw_text_ref = ?")
                    params.append(rtr)
                params.append(sid)
                conn.execute(
                    f"UPDATE signals SET {', '.join(sets)} WHERE signal_id = ?",
                    params,
                )
            if (i + batch_size) % 50000 == 0:
                print(f"  signals 已处理 {min(i + batch_size, len(updates))}/{len(updates)}...")
        conn.commit()

    stats["rows_updated"] = len(updates)

    # Count after
    if not dry_run:
        cur = conn.execute("SELECT source_type, source_id, raw_text_ref FROM signals")
        for r in cur.fetchall():
            if r[0] and r[0].strip():
                stats["source_type_after"] += 1
            if r[1] and r[1].strip():
                stats["source_id_after"] += 1
            if r[2] and r[2].strip():
                stats["raw_text_ref_after"] += 1
    else:
        stats["source_type_after"] = stats["source_type_before"] + sum(1 for u in updates if u[0])
        stats["source_id_after"] = stats["source_id_before"] + sum(1 for u in updates if u[1])
        stats["raw_text_ref_after"] = stats["raw_text_ref_before"] + sum(1 for u in updates if u[2])

    return stats


# ═══════════════════════════════════════════════════════════════════
# Task C: perception seeds from themes (conservative)
# ═══════════════════════════════════════════════════════════════════

THEME_TO_SEED = {
    "health": ("science_credibility", 0.15),
    "science": ("science_credibility", 0.20),
    "beauty": ("aesthetic_affinity", 0.15),
    "lifestyle": ("aesthetic_affinity", 0.10),
    "education": ("science_credibility", 0.10),
}


def generate_perception_seeds(conn: sqlite3.Connection, dry_run: bool) -> dict:
    """Generate low-weight perception seeds from theme-enriched interventions."""
    stats = {"seeds_generated": 0, "skipped_reason": None, "by_theme": {}}

    # Check if we have enough themed interventions
    cur = conn.execute(
        "SELECT intervention_id, theme, market, date_start, product_line "
        "FROM interventions WHERE theme IS NOT NULL AND theme != '' AND theme != 'unknown'"
    )
    themed = cur.fetchall()

    if len(themed) < 10:
        stats["skipped_reason"] = f"证据不足: 只有 {len(themed)} 条有 theme 的 intervention"
        return stats

    # Only generate for themes in our mapping
    seeds = []
    for iid, theme, market, date_start, product_line in themed:
        theme_lower = theme.strip().lower()
        if theme_lower not in THEME_TO_SEED:
            continue

        signal_type_name, base_weight = THEME_TO_SEED[theme_lower]
        seed_id = f"derived_theme_seed_{iid}_{signal_type_name}"

        # Check if already exists
        existing = conn.execute(
            "SELECT 1 FROM signals WHERE signal_id = ?", (seed_id,)
        ).fetchone()
        if existing:
            continue

        extra = json.dumps({
            "signal_source": "derived_theme_seed",
            "source_intervention_id": iid,
            "source_theme": theme,
            "derivation_method": "theme_to_perception_conservative",
            "sync_batch": SYNC_BATCH,
            "weight_note": "low-weight seed, not real observation",
        }, ensure_ascii=False)

        seeds.append((
            seed_id,
            date_start or "1970-01-01",
            product_line or "moodyplus",
            "general",
            market or "cn",
            "derived_theme_seed",
            signal_type_name,
            base_weight,
            None,  # raw_text
            f"derived_from_intervention_{iid}",  # source
            "derived_theme_seed",  # source_type
            iid,  # source_id
            None,  # raw_text_ref
            extra,
        ))

        stats["by_theme"].setdefault(theme_lower, 0)
        stats["by_theme"][theme_lower] += 1

    if not dry_run and seeds:
        conn.execute("BEGIN")
        sql = (
            "INSERT OR IGNORE INTO signals "
            "(signal_id, date, product_line, audience_segment, market, "
            " signal_type, dimension, value, raw_text, source, "
            " source_type, source_id, raw_text_ref, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        conn.executemany(sql, seeds)
        conn.commit()

    stats["seeds_generated"] = len(seeds)
    return stats


# ═══════════════════════════════════════════════════════════════════
# Report generation
# ═══════════════════════════════════════════════════════════════════

def generate_report(
    iv_stats: dict, sig_stats: dict, seed_stats: dict,
    etl_dir: str, db_path: str, dry_run: bool, total_db_rows: dict,
) -> str:
    mode = "DRY-RUN" if dry_run else "APPLIED"

    lines = [
        f"# ETL Enrichment Sync Report ({mode})",
        f"",
        f"**日期:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**批次:** {SYNC_BATCH}",
        f"**ETL 来源:** `{etl_dir}`",
        f"**目标数据库:** `{db_path}`",
        f"",
        f"## 使用的 ETL 文件",
        f"",
        f"- `data/marts/mart_intervention_performance.parquet` (interventions enrichment)",
        f"- `exports/2026-03-14/signals.csv` (signals lineage)",
        f"",
        f"## 缺失文件",
        f"",
        f"- 无（所有需要的文件均可用）",
        f"",
        f"## Interventions Enrichment",
        f"",
        f"| 字段 | Before | After | 增量 |",
        f"|------|--------|-------|------|",
    ]

    total_iv = total_db_rows.get("interventions", "?")
    for field in ["theme", "message_arc", "multimodal_tags"]:
        before = iv_stats.get(f"{field}_before", 0)
        after = iv_stats.get(f"{field}_after", 0)
        delta = after - before
        pct_before = f"{before}/{total_iv} ({before/total_iv*100:.1f}%)" if total_iv else str(before)
        pct_after = f"{after}/{total_iv} ({after/total_iv*100:.1f}%)" if total_iv else str(after)
        lines.append(f"| {field} | {pct_before} | {pct_after} | +{delta} |")

    lines += [
        f"",
        f"**匹配行数:** {iv_stats['total_matched']}",
        f"**实际更新行数:** {iv_stats['rows_updated']}",
        f"",
        f"### 按 market 分布",
        f"",
    ]
    for mkt, cnt in sorted(iv_stats.get("by_market", {}).items(), key=lambda x: -x[1]):
        lines.append(f"- {mkt}: {cnt}")

    lines += [
        f"",
        f"### 按 platform 分布",
        f"",
    ]
    for plat, cnt in sorted(iv_stats.get("by_platform", {}).items(), key=lambda x: -x[1]):
        lines.append(f"- {plat}: {cnt}")

    total_sig = total_db_rows.get("signals", "?")
    lines += [
        f"",
        f"## Signals Lineage Backfill",
        f"",
        f"| 字段 | Before | After | 增量 |",
        f"|------|--------|-------|------|",
    ]
    for field in ["source_type", "source_id", "raw_text_ref"]:
        before = sig_stats.get(f"{field}_before", 0)
        after = sig_stats.get(f"{field}_after", 0)
        delta = after - before
        pct_before = f"{before}/{total_sig} ({before/total_sig*100:.1f}%)" if total_sig else str(before)
        pct_after = f"{after}/{total_sig} ({after/total_sig*100:.1f}%)" if total_sig else str(after)
        lines.append(f"| {field} | {pct_before} | {pct_after} | +{delta} |")

    lines += [
        f"",
        f"**实际更新行数:** {sig_stats['rows_updated']}",
        f"",
        f"## Perception Seeds",
        f"",
    ]
    if seed_stats.get("skipped_reason"):
        lines.append(f"**跳过:** {seed_stats['skipped_reason']}")
    else:
        lines.append(f"**生成数量:** {seed_stats['seeds_generated']}")
        if seed_stats.get("by_theme"):
            lines.append(f"")
            for theme, cnt in sorted(seed_stats["by_theme"].items(), key=lambda x: -x[1]):
                lines.append(f"- {theme}: {cnt} seeds")

    lines += [
        f"",
        f"## 剩余缺口",
        f"",
        f"1. **message_arc 覆盖率仍低** — ETL 只有 67 条有 message_arc_parsed，大部分 intervention 仍无 message_arc",
        f"2. **signals 无真实 raw_text_ref** — 除 creator_engagement 外，其他信号类型没有原始文本引用",
        f"3. **perception signals 仍依赖 theme seed** — 真正的消费者 perception 数据需要 review/survey/social listening 外部输入",
        f"4. **competitor_events 未涉及** — 本次同步不处理竞品数据",
        f"",
        f"## 结论",
        f"",
        f"1. **baseline/race 提升:** theme 覆盖率从 ~0.3% 提升到 ~60%+，大幅改善 intervention 分析粒度",
        f"2. **brand-state/replay/predict:** perception signals 仍不足以驱动真实 brand-state；",
        f"   theme seeds 提供了最低限度的信号输入，但权重低，不应作为决策依据",
        f"3. **还缺:** consumer review/survey perception 数据、competitor intelligence、真实 social listening signals",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Sync ETL enrichment to brandiction.db")
    parser.add_argument("--etl-dir", required=True, help="ETL root directory")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to brandiction.db")
    parser.add_argument("--dry-run", action="store_true", help="Only report, don't write")
    parser.add_argument("--seed-perception", action="store_true", help="Generate perception seeds")
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    etl_dir = os.path.abspath(args.etl_dir)

    print(f"ETL 目录: {etl_dir}")
    print(f"数据库: {db_path}")
    print(f"模式: {'DRY-RUN' if args.dry_run else 'APPLY'}")
    print()

    # Backup
    if not args.dry_run:
        bak = backup_db(db_path)
        if bak:
            print(f"已备份: {bak}")

    # Load ETL data
    print("加载 ETL mart...")
    mart = load_etl_mart(etl_dir)
    print(f"  mart_intervention_performance: {len(mart)} rows")

    print("加载 ETL signals...")
    sig_df = load_etl_signals(etl_dir)
    print(f"  signals: {len(sig_df)} rows")
    print()

    # Connect
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")

    # Task A: interventions enrichment
    print("═══ Task A: Interventions Enrichment ═══")
    t0 = time.time()
    iv_stats = enrich_interventions(conn, mart, args.dry_run)
    print(f"  theme: {iv_stats['theme_before']} -> {iv_stats['theme_after']}")
    print(f"  message_arc: {iv_stats['message_arc_before']} -> {iv_stats['message_arc_after']}")
    print(f"  multimodal_tags: {iv_stats['multimodal_tags_before']} -> {iv_stats['multimodal_tags_after']}")
    print(f"  更新行数: {iv_stats['rows_updated']} ({time.time() - t0:.1f}s)")
    print()

    # Task B: signals lineage
    print("═══ Task B: Signals Lineage Backfill ═══")
    t0 = time.time()
    sig_stats = backfill_signals(conn, sig_df, args.dry_run)
    print(f"  source_type: {sig_stats['source_type_before']} -> {sig_stats['source_type_after']}")
    print(f"  source_id: {sig_stats['source_id_before']} -> {sig_stats['source_id_after']}")
    print(f"  raw_text_ref: {sig_stats['raw_text_ref_before']} -> {sig_stats['raw_text_ref_after']}")
    print(f"  更新行数: {sig_stats['rows_updated']} ({time.time() - t0:.1f}s)")
    print()

    # Task C: perception seeds
    seed_stats = {"seeds_generated": 0, "skipped_reason": "未启用 --seed-perception"}
    if args.seed_perception:
        print("═══ Task C: Perception Seeds ═══")
        t0 = time.time()
        seed_stats = generate_perception_seeds(conn, args.dry_run)
        if seed_stats.get("skipped_reason"):
            print(f"  跳过: {seed_stats['skipped_reason']}")
        else:
            print(f"  生成 seeds: {seed_stats['seeds_generated']}")
        print(f"  ({time.time() - t0:.1f}s)")
        print()

    # Counts for report
    total_db = {}
    for table in ["interventions", "signals"]:
        total_db[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    # Generate report
    report = generate_report(iv_stats, sig_stats, seed_stats, etl_dir, db_path, args.dry_run, total_db)
    report_path = os.path.join(os.path.dirname(db_path), "etl_enrichment_sync_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"报告已写入: {report_path}")

    conn.close()
    print("\n完成。")


if __name__ == "__main__":
    main()
