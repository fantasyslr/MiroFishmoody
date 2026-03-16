"""
Brandiction Store — SQLite 持久化层

存储历史 intervention、outcome、signal、竞品事件、证据。
沿用 TaskManager 的 SQLite 模式：启动时建表，读写用 json 序列化扩展字段。

设计要点：
  - save_* 使用 merge 语义：已有记录只更新非 None 字段，不会覆盖旧值
  - 启用 PRAGMA foreign_keys，外键约束生效
"""

import json
import os
import sqlite3
import threading
from typing import List, Optional, Dict, Any

from ..config import Config
from ..models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
    CompetitorEvent,
    EvidenceArtifact,
)
from ..models.brand_state import (
    BrandState,
    PerceptionVector,
    StateTransition,
)


class BrandictionStore:
    """SQLite-backed store for Brandiction historical data."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._db_path = db_path or os.path.join(
                    Config.UPLOAD_FOLDER, "brandiction.db"
                )
                os.makedirs(os.path.dirname(inst._db_path), exist_ok=True)
                inst._init_db()
                cls._instance = inst
            return cls._instance

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS interventions (
                    intervention_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    product_line TEXT DEFAULT 'moodyplus',
                    date_start TEXT,
                    date_end TEXT,
                    theme TEXT,
                    message_arc TEXT,
                    channel_mix TEXT,
                    budget REAL,
                    spend REAL,
                    audience_segment TEXT,
                    market TEXT DEFAULT 'cn',
                    campaign_id TEXT,
                    creative_id TEXT,
                    landing_page TEXT,
                    platform TEXT,
                    channel_family TEXT,
                    objective TEXT,
                    notes TEXT,
                    extra TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    intervention_id TEXT NOT NULL,
                    window_label TEXT,
                    date_start TEXT,
                    date_end TEXT,
                    impressions INTEGER,
                    clicks INTEGER,
                    ctr REAL,
                    cvr REAL,
                    revenue REAL,
                    roas REAL,
                    brand_lift REAL,
                    search_trend_delta REAL,
                    comment_sentiment REAL,
                    comment_summary TEXT,
                    sessions INTEGER,
                    pdp_views INTEGER,
                    add_to_cart INTEGER,
                    checkout_started INTEGER,
                    purchases INTEGER,
                    new_customers INTEGER,
                    returning_customers INTEGER,
                    aov REAL,
                    extra TEXT DEFAULT '{}',
                    FOREIGN KEY (intervention_id) REFERENCES interventions(intervention_id)
                );

                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    product_line TEXT DEFAULT 'moodyplus',
                    audience_segment TEXT DEFAULT 'general',
                    market TEXT DEFAULT 'cn',
                    signal_type TEXT,
                    dimension TEXT,
                    value REAL,
                    raw_text TEXT,
                    source TEXT,
                    source_type TEXT,
                    source_id TEXT,
                    raw_text_ref TEXT,
                    extra TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS competitor_events (
                    event_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    competitor TEXT NOT NULL,
                    market TEXT DEFAULT 'cn',
                    event_type TEXT,
                    description TEXT,
                    impact_estimate TEXT,
                    extra TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS race_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    plans_json TEXT NOT NULL,
                    sort_by TEXT DEFAULT 'roas_mean',
                    result_json TEXT,
                    top_recommendation TEXT,
                    plans_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    hit INTEGER,
                    notes TEXT,
                    extra TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    artifact_id TEXT PRIMARY KEY,
                    intervention_id TEXT,
                    signal_id TEXT,
                    artifact_type TEXT,
                    file_path TEXT,
                    description TEXT,
                    uploaded_at TEXT,
                    extra TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS brand_states (
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
                    notes TEXT,
                    extra TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS state_transitions (
                    transition_id TEXT PRIMARY KEY,
                    intervention_id TEXT NOT NULL,
                    state_before_id TEXT NOT NULL,
                    state_after_id TEXT NOT NULL,
                    market TEXT DEFAULT 'cn',
                    delta TEXT DEFAULT '{}',
                    confidence REAL DEFAULT 0.5,
                    method TEXT DEFAULT 'historical',
                    notes TEXT,
                    extra TEXT DEFAULT '{}',
                    FOREIGN KEY (intervention_id) REFERENCES interventions(intervention_id),
                    FOREIGN KEY (state_before_id) REFERENCES brand_states(state_id),
                    FOREIGN KEY (state_after_id) REFERENCES brand_states(state_id)
                );

                CREATE INDEX IF NOT EXISTS idx_interventions_run ON interventions(run_id);
                CREATE INDEX IF NOT EXISTS idx_outcomes_intervention ON outcomes(intervention_id);
                CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date);
                CREATE INDEX IF NOT EXISTS idx_competitor_date ON competitor_events(date);
                CREATE INDEX IF NOT EXISTS idx_brand_states_date ON brand_states(as_of_date);
                CREATE INDEX IF NOT EXISTS idx_transitions_intervention ON state_transitions(intervention_id);
            """)
            # Migration: 为旧库补缺失列
            migrations = [
                ("signals", "audience_segment", "TEXT DEFAULT 'general'"),
                ("signals", "market", "TEXT DEFAULT 'cn'"),
                ("interventions", "market", "TEXT DEFAULT 'cn'"),
                ("brand_states", "market", "TEXT DEFAULT 'cn'"),
                ("state_transitions", "market", "TEXT DEFAULT 'cn'"),
                ("competitor_events", "market", "TEXT DEFAULT 'cn'"),
                # V3 data spine — interventions
                ("interventions", "campaign_id", "TEXT"),
                ("interventions", "creative_id", "TEXT"),
                ("interventions", "landing_page", "TEXT"),
                ("interventions", "platform", "TEXT"),
                ("interventions", "channel_family", "TEXT"),
                ("interventions", "objective", "TEXT"),
                ("interventions", "season_tag", "TEXT"),
                # V3 data spine — outcomes (DTC funnel)
                ("outcomes", "sessions", "INTEGER"),
                ("outcomes", "pdp_views", "INTEGER"),
                ("outcomes", "add_to_cart", "INTEGER"),
                ("outcomes", "checkout_started", "INTEGER"),
                ("outcomes", "purchases", "INTEGER"),
                ("outcomes", "new_customers", "INTEGER"),
                ("outcomes", "returning_customers", "INTEGER"),
                ("outcomes", "aov", "REAL"),
                # V3 data spine — signals (溯源)
                ("signals", "source_type", "TEXT"),
                ("signals", "source_id", "TEXT"),
                ("signals", "raw_text_ref", "TEXT"),
            ]
            for table, col, col_type in migrations:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass  # 列已存在
            # V3 indexes (created after migrations to ensure columns exist)
            v3_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_interventions_campaign ON interventions(campaign_id)",
                "CREATE INDEX IF NOT EXISTS idx_interventions_platform ON interventions(platform)",
                "CREATE INDEX IF NOT EXISTS idx_signals_source_type ON signals(source_type)",
            ]
            for idx_sql in v3_indexes:
                try:
                    conn.execute(idx_sql)
                except sqlite3.OperationalError:
                    pass

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ------------------------------------------------------------------
    # Generic merge helper
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_upsert(
        conn: sqlite3.Connection,
        table: str,
        pk_col: str,
        pk_val: str,
        columns: Dict[str, Any],
    ):
        """
        Merge/upsert 语义：
        - 如果行不存在，INSERT 全部字段
        - 如果行已存在，只更新 value 不为 None 的字段
        """
        existing = conn.execute(
            f"SELECT 1 FROM {table} WHERE {pk_col} = ?", (pk_val,)
        ).fetchone()

        if existing is None:
            # INSERT: 所有字段
            all_cols = {pk_col: pk_val, **columns}
            col_names = ", ".join(all_cols.keys())
            placeholders = ", ".join(["?"] * len(all_cols))
            conn.execute(
                f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
                list(all_cols.values()),
            )
        else:
            # UPDATE: 只更新非 None 字段
            updates = {k: v for k, v in columns.items() if v is not None}
            if not updates:
                return
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?",
                list(updates.values()) + [pk_val],
            )

    # ------------------------------------------------------------------
    # Interventions
    # ------------------------------------------------------------------

    def save_intervention(self, iv: HistoricalIntervention):
        with self._connect() as conn:
            self._merge_upsert(conn, "interventions", "intervention_id", iv.intervention_id, {
                "run_id": iv.run_id,
                "product_line": iv.product_line,
                "date_start": iv.date_start,
                "date_end": iv.date_end,
                "theme": iv.theme,
                "message_arc": iv.message_arc,
                "channel_mix": json.dumps(iv.channel_mix) if iv.channel_mix else None,
                "budget": iv.budget,
                "spend": iv.spend,
                "audience_segment": iv.audience_segment,
                "market": iv.market,
                "campaign_id": iv.campaign_id,
                "creative_id": iv.creative_id,
                "landing_page": iv.landing_page,
                "platform": iv.platform,
                "channel_family": iv.channel_family,
                "objective": iv.objective,
                "season_tag": iv.season_tag,
                "notes": iv.notes,
                "extra": json.dumps(iv.extra) if iv.extra else None,
            })

    def get_intervention(self, intervention_id: str) -> Optional[HistoricalIntervention]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM interventions WHERE intervention_id = ?",
                (intervention_id,),
            ).fetchone()
        return self._row_to_intervention(row) if row else None

    def list_interventions(
        self,
        run_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        creative_id: Optional[str] = None,
        platform: Optional[str] = None,
        channel_family: Optional[str] = None,
        landing_page: Optional[str] = None,
        objective: Optional[str] = None,
        market: Optional[str] = None,
    ) -> List[HistoricalIntervention]:
        clauses: list = []
        params: list = []
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if campaign_id:
            clauses.append("campaign_id = ?")
            params.append(campaign_id)
        if creative_id:
            clauses.append("creative_id = ?")
            params.append(creative_id)
        if platform:
            clauses.append("platform = ?")
            params.append(platform)
        if channel_family:
            clauses.append("channel_family = ?")
            params.append(channel_family)
        if landing_page:
            clauses.append("landing_page = ?")
            params.append(landing_page)
        if objective:
            clauses.append("objective = ?")
            params.append(objective)
        if market:
            clauses.append("market = ?")
            params.append(market)
        where = " AND ".join(clauses) if clauses else "1=1"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM interventions WHERE {where} ORDER BY date_start", params
            ).fetchall()
        return [self._row_to_intervention(r) for r in rows]

    def list_run_ids(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT run_id FROM interventions ORDER BY run_id"
            ).fetchall()
        return [r["run_id"] for r in rows]

    # ------------------------------------------------------------------
    # Outcomes
    # ------------------------------------------------------------------

    def save_outcome(self, oc: HistoricalOutcomeWindow):
        with self._connect() as conn:
            self._merge_upsert(conn, "outcomes", "outcome_id", oc.outcome_id, {
                "intervention_id": oc.intervention_id,
                "window_label": oc.window_label,
                "date_start": oc.date_start,
                "date_end": oc.date_end,
                "impressions": oc.impressions,
                "clicks": oc.clicks,
                "ctr": oc.ctr,
                "cvr": oc.cvr,
                "revenue": oc.revenue,
                "roas": oc.roas,
                "brand_lift": oc.brand_lift,
                "search_trend_delta": oc.search_trend_delta,
                "comment_sentiment": oc.comment_sentiment,
                "comment_summary": oc.comment_summary,
                "sessions": oc.sessions,
                "pdp_views": oc.pdp_views,
                "add_to_cart": oc.add_to_cart,
                "checkout_started": oc.checkout_started,
                "purchases": oc.purchases,
                "new_customers": oc.new_customers,
                "returning_customers": oc.returning_customers,
                "aov": oc.aov,
                "extra": json.dumps(oc.extra) if oc.extra else None,
            })

    def list_outcomes(self, intervention_id: str) -> List[HistoricalOutcomeWindow]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM outcomes WHERE intervention_id = ? ORDER BY date_start",
                (intervention_id,),
            ).fetchall()
        return [self._row_to_outcome(r) for r in rows]

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def save_signal(self, sig: BrandSignalSnapshot):
        with self._connect() as conn:
            self._merge_upsert(conn, "signals", "signal_id", sig.signal_id, {
                "date": sig.date,
                "product_line": sig.product_line,
                "audience_segment": sig.audience_segment,
                "market": sig.market,
                "signal_type": sig.signal_type,
                "dimension": sig.dimension,
                "value": sig.value,
                "raw_text": sig.raw_text,
                "source": sig.source,
                "source_type": sig.source_type,
                "source_id": sig.source_id,
                "raw_text_ref": sig.raw_text_ref,
                "extra": json.dumps(sig.extra) if sig.extra else None,
            })

    def list_signals(
        self,
        product_line: Optional[str] = None,
        audience_segment: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        dimension: Optional[str] = None,
        market: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> List[BrandSignalSnapshot]:
        clauses = []
        params: list = []
        if product_line:
            clauses.append("product_line = ?")
            params.append(product_line)
        if audience_segment:
            clauses.append("audience_segment = ?")
            params.append(audience_segment)
        if market:
            clauses.append("market = ?")
            params.append(market)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if date_from:
            clauses.append("date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("date <= ?")
            params.append(date_to)
        if dimension:
            clauses.append("dimension = ?")
            params.append(dimension)
        where = " AND ".join(clauses) if clauses else "1=1"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM signals WHERE {where} ORDER BY date", params
            ).fetchall()
        return [self._row_to_signal(r) for r in rows]

    # ------------------------------------------------------------------
    # Competitor events
    # ------------------------------------------------------------------

    def save_competitor_event(self, ev: CompetitorEvent):
        with self._connect() as conn:
            self._merge_upsert(conn, "competitor_events", "event_id", ev.event_id, {
                "date": ev.date,
                "competitor": ev.competitor,
                "market": ev.market,
                "event_type": ev.event_type,
                "description": ev.description,
                "impact_estimate": ev.impact_estimate,
                "extra": json.dumps(ev.extra) if ev.extra else None,
            })

    def list_competitor_events(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        market: Optional[str] = None,
    ) -> List[CompetitorEvent]:
        clauses = []
        params: list = []
        if market:
            clauses.append("market = ?")
            params.append(market)
        if date_from:
            clauses.append("date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("date <= ?")
            params.append(date_to)
        where = " AND ".join(clauses) if clauses else "1=1"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM competitor_events WHERE {where} ORDER BY date", params
            ).fetchall()
        return [self._row_to_competitor_event(r) for r in rows]

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------

    def save_evidence(self, ev: EvidenceArtifact):
        with self._connect() as conn:
            self._merge_upsert(conn, "evidence", "artifact_id", ev.artifact_id, {
                "intervention_id": ev.intervention_id,
                "signal_id": ev.signal_id,
                "artifact_type": ev.artifact_type,
                "file_path": ev.file_path,
                "description": ev.description,
                "uploaded_at": ev.uploaded_at,
                "extra": json.dumps(ev.extra) if ev.extra else None,
            })

    def list_evidence(self, intervention_id: Optional[str] = None) -> List[EvidenceArtifact]:
        with self._connect() as conn:
            if intervention_id:
                rows = conn.execute(
                    "SELECT * FROM evidence WHERE intervention_id = ?",
                    (intervention_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM evidence").fetchall()
        return [self._row_to_evidence(r) for r in rows]

    # ------------------------------------------------------------------
    # Brand States
    # ------------------------------------------------------------------

    def save_brand_state(self, bs: BrandState):
        p = bs.perception
        with self._connect() as conn:
            self._merge_upsert(conn, "brand_states", "state_id", bs.state_id, {
                "as_of_date": bs.as_of_date,
                "product_line": bs.product_line,
                "audience_segment": bs.audience_segment,
                "market": bs.market,
                "science_credibility": p.science_credibility,
                "comfort_trust": p.comfort_trust,
                "aesthetic_affinity": p.aesthetic_affinity,
                "price_sensitivity": p.price_sensitivity,
                "social_proof": p.social_proof,
                "skepticism": p.skepticism,
                "competitor_pressure": p.competitor_pressure,
                "confidence": bs.confidence,
                "evidence_sources": json.dumps(bs.evidence_sources),
                "notes": bs.notes,
                "extra": json.dumps(bs.extra) if bs.extra else None,
            })

    def get_brand_state(self, state_id: str) -> Optional[BrandState]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM brand_states WHERE state_id = ?", (state_id,)
            ).fetchone()
        return self._row_to_brand_state(row) if row else None

    def list_brand_states(
        self,
        product_line: Optional[str] = None,
        audience_segment: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        market: Optional[str] = None,
    ) -> List[BrandState]:
        clauses: list = []
        params: list = []
        if product_line:
            clauses.append("product_line = ?")
            params.append(product_line)
        if audience_segment:
            clauses.append("audience_segment = ?")
            params.append(audience_segment)
        if market:
            clauses.append("market = ?")
            params.append(market)
        if date_from:
            clauses.append("as_of_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("as_of_date <= ?")
            params.append(date_to)
        where = " AND ".join(clauses) if clauses else "1=1"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM brand_states WHERE {where} ORDER BY as_of_date", params
            ).fetchall()
        return [self._row_to_brand_state(r) for r in rows]

    def get_latest_brand_state(
        self,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
    ) -> Optional[BrandState]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM brand_states "
                "WHERE product_line = ? AND audience_segment = ? AND market = ? "
                "ORDER BY as_of_date DESC, state_id DESC LIMIT 1",
                (product_line, audience_segment, market),
            ).fetchone()
        return self._row_to_brand_state(row) if row else None

    # ------------------------------------------------------------------
    # State Transitions
    # ------------------------------------------------------------------

    def save_transition(self, tr: StateTransition):
        with self._connect() as conn:
            self._merge_upsert(conn, "state_transitions", "transition_id", tr.transition_id, {
                "intervention_id": tr.intervention_id,
                "state_before_id": tr.state_before_id,
                "state_after_id": tr.state_after_id,
                "market": tr.market,
                "delta": json.dumps(tr.delta),
                "confidence": tr.confidence,
                "method": tr.method,
                "notes": tr.notes,
                "extra": json.dumps(tr.extra) if tr.extra else None,
            })

    def list_transitions(self, intervention_id: Optional[str] = None) -> List[StateTransition]:
        with self._connect() as conn:
            if intervention_id:
                rows = conn.execute(
                    "SELECT * FROM state_transitions WHERE intervention_id = ?",
                    (intervention_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM state_transitions").fetchall()
        return [self._row_to_transition(r) for r in rows]

    # ------------------------------------------------------------------
    # Race Runs
    # ------------------------------------------------------------------

    def save_race_run(
        self,
        run_id: str,
        created_at: str,
        plans: list,
        sort_by: str = "roas_mean",
        result: Optional[Dict[str, Any]] = None,
        top_recommendation: Optional[str] = None,
        status: str = "pending",
        hit: Optional[bool] = None,
        notes: Optional[str] = None,
    ):
        with self._connect() as conn:
            self._merge_upsert(conn, "race_runs", "run_id", run_id, {
                "created_at": created_at,
                "plans_json": json.dumps(plans),
                "sort_by": sort_by,
                "result_json": json.dumps(result) if result is not None else None,
                "top_recommendation": top_recommendation,
                "plans_count": len(plans),
                "status": status,
                "hit": 1 if hit is True else (0 if hit is False else None),
                "notes": notes,
            })

    def list_race_runs(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM race_runs ORDER BY created_at DESC"
            ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            hit_val = d.get("hit")
            results.append({
                "id": d["run_id"],
                "date": d["created_at"],
                "plans_count": d.get("plans_count", 0),
                "top_recommendation": d.get("top_recommendation", ""),
                "status": d.get("status", "pending"),
                "hit": True if hit_val == 1 else (False if hit_val == 0 else None),
                "sort_by": d.get("sort_by", "roas_mean"),
            })
        return results

    def get_race_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM race_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        hit_val = d.get("hit")
        return {
            "id": d["run_id"],
            "date": d["created_at"],
            "plans_count": d.get("plans_count", 0),
            "top_recommendation": d.get("top_recommendation", ""),
            "status": d.get("status", "pending"),
            "hit": True if hit_val == 1 else (False if hit_val == 0 else None),
            "sort_by": d.get("sort_by", "roas_mean"),
            "plans": json.loads(d.get("plans_json") or "[]"),
            "result": json.loads(d.get("result_json") or "null"),
        }

    def update_race_run_resolution(
        self, run_id: str, status: str, hit: Optional[bool]
    ):
        with self._connect() as conn:
            hit_val = 1 if hit is True else (0 if hit is False else None)
            conn.execute(
                "UPDATE race_runs SET status = ?, hit = ? WHERE run_id = ?",
                (status, hit_val, run_id),
            )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            iv_count = conn.execute("SELECT COUNT(*) FROM interventions").fetchone()[0]
            oc_count = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
            sig_count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            ce_count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]
            ev_count = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
            run_count = conn.execute("SELECT COUNT(DISTINCT run_id) FROM interventions").fetchone()[0]
            bs_count = conn.execute("SELECT COUNT(*) FROM brand_states").fetchone()[0]
            tr_count = conn.execute("SELECT COUNT(*) FROM state_transitions").fetchone()[0]
        return {
            "interventions": iv_count,
            "outcomes": oc_count,
            "signals": sig_count,
            "competitor_events": ce_count,
            "evidence": ev_count,
            "runs": run_count,
            "brand_states": bs_count,
            "state_transitions": tr_count,
        }

    def stats_v3(self) -> Dict[str, Any]:
        """Extended stats for the V3 Data Spine dashboard."""
        with self._connect() as conn:
            iv_count = conn.execute("SELECT COUNT(*) FROM interventions").fetchone()[0]
            oc_count = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
            sig_count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            ce_count = conn.execute("SELECT COUNT(*) FROM competitor_events").fetchone()[0]

            # Market coverage: fraction of interventions per market
            market_rows = conn.execute(
                "SELECT COALESCE(market, 'cn') as m, COUNT(*) as c FROM interventions GROUP BY m"
            ).fetchall()
            total_iv = max(iv_count, 1)
            market_coverage = {r["m"]: round(r["c"] / total_iv, 3) for r in market_rows}

            # Platform coverage: fraction of interventions per platform
            platform_rows = conn.execute(
                "SELECT platform as p, COUNT(*) as c FROM interventions WHERE platform IS NOT NULL GROUP BY p"
            ).fetchall()
            platform_coverage = {r["p"]: round(r["c"] / total_iv, 3) for r in platform_rows}

            # Weakest dimensions: dimensions with fewest signals
            dim_rows = conn.execute(
                "SELECT dimension, COUNT(*) as c FROM signals WHERE dimension IS NOT NULL GROUP BY dimension ORDER BY c ASC"
            ).fetchall()
            weakest_dimensions = [r["dimension"] for r in dim_rows[:3]] if dim_rows else []

        return {
            "interventions_count": iv_count,
            "outcomes_count": oc_count,
            "signals_count": sig_count,
            "competitor_events_count": ce_count,
            "market_coverage": market_coverage,
            "platform_coverage": platform_coverage,
            "weakest_dimensions": weakest_dimensions,
        }

    # ------------------------------------------------------------------
    # Row converters
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_intervention(row: sqlite3.Row) -> HistoricalIntervention:
        d = dict(row)
        d["channel_mix"] = json.loads(d["channel_mix"]) if d.get("channel_mix") else None
        d["extra"] = json.loads(d.get("extra") or "{}")
        return HistoricalIntervention.from_dict(d)

    @staticmethod
    def _row_to_outcome(row: sqlite3.Row) -> HistoricalOutcomeWindow:
        d = dict(row)
        d["extra"] = json.loads(d.get("extra") or "{}")
        return HistoricalOutcomeWindow.from_dict(d)

    @staticmethod
    def _row_to_signal(row: sqlite3.Row) -> BrandSignalSnapshot:
        d = dict(row)
        d["extra"] = json.loads(d.get("extra") or "{}")
        return BrandSignalSnapshot.from_dict(d)

    @staticmethod
    def _row_to_competitor_event(row: sqlite3.Row) -> CompetitorEvent:
        d = dict(row)
        d["extra"] = json.loads(d.get("extra") or "{}")
        return CompetitorEvent.from_dict(d)

    @staticmethod
    def _row_to_evidence(row: sqlite3.Row) -> EvidenceArtifact:
        d = dict(row)
        d["extra"] = json.loads(d.get("extra") or "{}")
        return EvidenceArtifact.from_dict(d)

    @staticmethod
    def _row_to_brand_state(row: sqlite3.Row) -> BrandState:
        d = dict(row)
        perception = PerceptionVector(
            science_credibility=d.pop("science_credibility", 0.5),
            comfort_trust=d.pop("comfort_trust", 0.5),
            aesthetic_affinity=d.pop("aesthetic_affinity", 0.5),
            price_sensitivity=d.pop("price_sensitivity", 0.5),
            social_proof=d.pop("social_proof", 0.5),
            skepticism=d.pop("skepticism", 0.3),
            competitor_pressure=d.pop("competitor_pressure", 0.3),
        )
        d["perception"] = perception
        d["evidence_sources"] = json.loads(d.get("evidence_sources") or "[]")
        d["extra"] = json.loads(d.get("extra") or "{}")
        return BrandState.from_dict(d)

    @staticmethod
    def _row_to_transition(row: sqlite3.Row) -> StateTransition:
        d = dict(row)
        d["delta"] = json.loads(d.get("delta") or "{}")
        d["extra"] = json.loads(d.get("extra") or "{}")
        return StateTransition.from_dict(d)

    # ------------------------------------------------------------------
    # Reset (for testing)
    # ------------------------------------------------------------------

    @classmethod
    def _reset_instance(cls):
        """Reset singleton for testing."""
        cls._instance = None
