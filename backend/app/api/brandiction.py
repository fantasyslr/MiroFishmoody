"""
Brandiction API — 历史数据导入、查询、BrandState、认知路径概率板、回测、情景模拟

POST /api/brandiction/import-history     — 导入 JSON 格式历史数据
POST /api/brandiction/import-csv         — 导入 CSV 格式（interventions 或 outcomes）
GET  /api/brandiction/history/<run_id>   — 按 run_id 查询 interventions + outcomes
GET  /api/brandiction/history            — 列出所有 run_id
GET  /api/brandiction/signals            — 查询 brand signals
GET  /api/brandiction/competitor-events  — 查询竞品事件
GET  /api/brandiction/stats              — 数据库统计

GET  /api/brandiction/brand-state        — 查询 BrandState 时间线
GET  /api/brandiction/brand-state/latest — 获取最新 BrandState
POST /api/brandiction/brand-state/build  — 从 signals 构建 BrandState 快照
POST /api/brandiction/replay             — 回放历史数据，生成状态时间线
POST /api/brandiction/predict            — 预测干预影响
POST /api/brandiction/probability-board  — 认知路径概率板
POST /api/brandiction/backtest           — 回测验证预测准确度
POST /api/brandiction/simulate           — 多步情景模拟
POST /api/brandiction/compare-scenarios  — 多情景对比
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from ..auth import login_required, admin_required
from ..services.brandiction_store import BrandictionStore
from ..services.historical_importer import HistoricalImporter
from ..services.brand_state_engine import BrandStateEngine
from ..services.baseline_ranker import HistoricalBaselineRanker, apply_visual_adjustment
from ..services.image_analyzer import ImageAnalyzer
from ..utils.logger import get_logger

_logger = get_logger("ranker.api.brandiction")

brandiction_bp = Blueprint("brandiction", __name__)


def _build_visual_reasoning(profile: dict) -> str:
    """从 visual profile 构建可读的视觉分析推理文本"""
    parts = ["【视觉素材分析】"]
    style = profile.get("creative_style", "unknown")
    tone = profile.get("aesthetic_tone", "unknown")
    claim = profile.get("visual_claim_focus", "unknown")
    parts.append(f"素材风格: {style}，审美调性: {tone}，卖点方向: {claim}")

    trust = profile.get("trust_signal_strength")
    promo = profile.get("promo_intensity")
    if trust is not None:
        parts.append(f"信任信号: {trust}/10")
    if promo is not None:
        parts.append(f"促销感: {promo}/10")

    hooks = profile.get("visual_hooks", [])
    if hooks:
        parts.append(f"视觉钩子: {', '.join(str(h) for h in hooks)}")
    risks = profile.get("visual_risks", [])
    if risks:
        parts.append(f"视觉风险: {', '.join(str(r) for r in risks)}")
    summary = profile.get("summary", "")
    if summary:
        parts.append(f"总结: {summary}")
    return "。".join(parts)


def _store() -> BrandictionStore:
    return BrandictionStore()


def _importer() -> HistoricalImporter:
    return HistoricalImporter(_store())


def _engine() -> BrandStateEngine:
    return BrandStateEngine(_store())


def _ranker() -> HistoricalBaselineRanker:
    return HistoricalBaselineRanker(_store())


# ------------------------------------------------------------------
# Import
# ------------------------------------------------------------------

@brandiction_bp.route("/import-history", methods=["POST"])
@admin_required
def import_history():
    """导入 JSON 格式历史数据（interventions / outcomes / signals / competitor_events / evidence）"""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空，需要 JSON 格式"}), 400

    result = _importer().import_json(data)
    return jsonify(result.to_dict()), 200


@brandiction_bp.route("/import-csv", methods=["POST"])
@admin_required
def import_csv():
    """
    导入 CSV 格式数据。
    Query params:
      type: interventions | outcomes (required)
      run_id: 指定 run_id（仅 interventions，可选）
    Body: raw CSV text
    """
    data_type = request.args.get("type", "")
    if data_type not in ("interventions", "outcomes"):
        return jsonify({"error": "type 参数必须是 interventions 或 outcomes"}), 400

    csv_text = request.get_data(as_text=True)
    if not csv_text.strip():
        return jsonify({"error": "CSV 内容为空"}), 400

    importer = _importer()
    if data_type == "interventions":
        run_id = request.args.get("run_id")
        result = importer.import_interventions_csv(csv_text, run_id=run_id)
    else:
        result = importer.import_outcomes_csv(csv_text)

    return jsonify(result.to_dict()), 200


# ------------------------------------------------------------------
# Query: History by run_id
# ------------------------------------------------------------------

@brandiction_bp.route("/history", methods=["GET"])
@login_required
def list_runs():
    """列出所有 run_id"""
    store = _store()
    run_ids = store.list_run_ids()
    return jsonify({"run_ids": run_ids, "count": len(run_ids)})


@brandiction_bp.route("/interventions", methods=["GET"])
@login_required
def list_interventions():
    """
    查询 interventions。
    Query params: run_id, campaign_id, creative_id, platform, channel_family,
                  landing_page, objective, market
    """
    store = _store()
    interventions = store.list_interventions(
        run_id=request.args.get("run_id"),
        campaign_id=request.args.get("campaign_id"),
        creative_id=request.args.get("creative_id"),
        platform=request.args.get("platform"),
        channel_family=request.args.get("channel_family"),
        landing_page=request.args.get("landing_page"),
        objective=request.args.get("objective"),
        market=request.args.get("market"),
    )
    return jsonify({
        "interventions": [iv.to_dict() for iv in interventions],
        "count": len(interventions),
    })


@brandiction_bp.route("/history/<run_id>", methods=["GET"])
@login_required
def get_history(run_id: str):
    """按 run_id 查询所有 interventions 及其 outcomes"""
    store = _store()
    interventions = store.list_interventions(run_id=run_id)
    if not interventions:
        return jsonify({"error": f"run_id '{run_id}' 不存在"}), 404

    items = []
    for iv in interventions:
        outcomes = store.list_outcomes(iv.intervention_id)
        evidence = store.list_evidence(iv.intervention_id)
        items.append({
            "intervention": iv.to_dict(),
            "outcomes": [o.to_dict() for o in outcomes],
            "evidence": [e.to_dict() for e in evidence],
        })

    return jsonify({
        "run_id": run_id,
        "intervention_count": len(items),
        "items": items,
    })


# ------------------------------------------------------------------
# Query: Signals
# ------------------------------------------------------------------

@brandiction_bp.route("/signals", methods=["GET"])
@login_required
def list_signals():
    """
    查询 brand signals。
    Query params: product_line, audience_segment, date_from, date_to, dimension, market, source_type, source_id
    """
    store = _store()
    signals = store.list_signals(
        product_line=request.args.get("product_line"),
        audience_segment=request.args.get("audience_segment"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        dimension=request.args.get("dimension"),
        market=request.args.get("market"),
        source_type=request.args.get("source_type"),
        source_id=request.args.get("source_id"),
    )
    return jsonify({
        "signals": [s.to_dict() for s in signals],
        "count": len(signals),
    })


# ------------------------------------------------------------------
# Query: Competitor events
# ------------------------------------------------------------------

@brandiction_bp.route("/competitor-events", methods=["GET"])
@admin_required
def list_competitor_events():
    """查询竞品事件。Query params: date_from, date_to, market"""
    store = _store()
    events = store.list_competitor_events(
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        market=request.args.get("market"),
    )
    return jsonify({
        "events": [e.to_dict() for e in events],
        "count": len(events),
    })


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------

@brandiction_bp.route("/stats", methods=["GET"])
@admin_required
def stats():
    """数据库统计 — V3 Data Spine dashboard format"""
    return jsonify(_store().stats_v3())


# ------------------------------------------------------------------
# BrandState
# ------------------------------------------------------------------

@brandiction_bp.route("/brand-state", methods=["GET"])
@login_required
def list_brand_states():
    """查询 BrandState 时间线。Query params: product_line, audience_segment, date_from, date_to"""
    store = _store()
    states = store.list_brand_states(
        product_line=request.args.get("product_line"),
        audience_segment=request.args.get("audience_segment"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        market=request.args.get("market"),
    )
    return jsonify({
        "states": [s.to_dict() for s in states],
        "count": len(states),
    })


@brandiction_bp.route("/brand-state/latest", methods=["GET"])
@login_required
def get_latest_state():
    """获取最新 BrandState。Query params: product_line, audience_segment"""
    product_line = request.args.get("product_line", "moodyplus")
    audience_segment = request.args.get("audience_segment", "general")
    market = request.args.get("market", "cn")
    state = _store().get_latest_brand_state(product_line, audience_segment, market=market)
    if not state:
        return jsonify({"error": "暂无 BrandState 数据，请先导入历史数据并执行 replay"}), 404
    return jsonify(state.to_dict())


@brandiction_bp.route("/brand-state/build", methods=["POST"])
@admin_required
def build_brand_state():
    """从 signals 构建指定日期的 BrandState 快照"""
    data = request.get_json(force=True, silent=True) or {}
    as_of_date = data.get("as_of_date")
    if not as_of_date:
        return jsonify({"error": "需要 as_of_date 参数"}), 400

    engine = _engine()
    state = engine.build_state_from_signals(
        as_of_date=as_of_date,
        product_line=data.get("product_line", "moodyplus"),
        audience_segment=data.get("audience_segment", "general"),
        market=data.get("market", "cn"),
    )
    return jsonify(state.to_dict())


# ------------------------------------------------------------------
# Replay & Predict
# ------------------------------------------------------------------

@brandiction_bp.route("/replay", methods=["POST"])
@admin_required
def replay_history():
    """回放历史数据，生成 BrandState 时间线"""
    data = request.get_json(force=True, silent=True) or {}
    product_line = data.get("product_line", "moodyplus")
    audience_segment = data.get("audience_segment", "general")

    market = data.get("market", "cn")

    engine = _engine()
    states = engine.replay_history(
        product_line=product_line, audience_segment=audience_segment,
        market=market,
    )

    return jsonify({
        "states": [s.to_dict() for s in states],
        "count": len(states),
        "product_line": product_line,
        "audience_segment": audience_segment,
        "market": market,
    })


@brandiction_bp.route("/predict", methods=["POST"])
@login_required
def predict_impact():
    """
    预测单个干预计划的状态影响。

    Body:
    {
      "theme": "science_credibility",
      "channel_mix": ["douyin", "redbook"],
      "budget": 50000,
      "product_line": "moodyplus"
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "需要 JSON 格式的干预计划"}), 400
    if not (data.get("theme") or "").strip():
        return jsonify({"error": "需要 theme 参数（认知路径，如 science_credibility / comfort_beauty）"}), 400

    engine = _engine()
    # 如果请求 diffusion 增强
    use_diffusion = data.get("use_diffusion", False)
    if use_diffusion:
        result = engine.predict_with_diffusion(
            intervention_plan=data,
            product_line=data.get("product_line", "moodyplus"),
            audience_segment=data.get("audience_segment", "general"),
            market=data.get("market", "cn"),
            diffusion_rounds=data.get("diffusion_rounds", 6),
            diffusion_seed=data.get("diffusion_seed"),
        )
    else:
        result = engine.predict_impact(
            intervention_plan=data,
            product_line=data.get("product_line", "moodyplus"),
            audience_segment=data.get("audience_segment", "general"),
            market=data.get("market", "cn"),
        )
    return jsonify(result)


@brandiction_bp.route("/probability-board", methods=["POST"])
@login_required
def probability_board():
    """
    认知路径概率板 — Brandiction Phase A 核心输出。

    Body:
    {
      "plans": [
        {"theme": "science_credibility", "budget": 50000},
        {"theme": "comfort_beauty", "budget": 50000}
      ],
      "product_line": "moodyplus"
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "plans" not in data:
        return jsonify({"error": "需要 plans 数组"}), 400

    plans = data["plans"]
    if not isinstance(plans, list) or len(plans) < 1:
        return jsonify({"error": "plans 至少需要 1 个干预计划"}), 400

    missing_theme = [i for i, p in enumerate(plans) if not (p.get("theme") or "").strip()]
    if missing_theme:
        return jsonify({"error": f"plans[{missing_theme[0]}] 缺少 theme 参数"}), 400

    engine = _engine()
    result = engine.cognition_probability_board(
        intervention_plans=plans,
        product_line=data.get("product_line", "moodyplus"),
        audience_segment=data.get("audience_segment", "general"),
        market=data.get("market", "cn"),
    )
    return jsonify(result)


# ------------------------------------------------------------------
# Backtest
# ------------------------------------------------------------------

@brandiction_bp.route("/backtest", methods=["POST"])
@admin_required
def backtest():
    """
    回测验证 — 留一法评估预测准确度。

    Body (可选):
    {
      "product_line": "moodyplus",
      "audience_segment": "general"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    engine = _engine()
    result = engine.backtest(
        product_line=data.get("product_line", "moodyplus"),
        audience_segment=data.get("audience_segment", "general"),
        market=data.get("market", "cn"),
    )
    return jsonify(result)


# ------------------------------------------------------------------
# Scenario Simulation
# ------------------------------------------------------------------

@brandiction_bp.route("/simulate", methods=["POST"])
@login_required
def simulate_scenario():
    """
    多步情景模拟 — 模拟一系列计划干预的累积效果。

    Body:
    {
      "steps": [
        {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000,
         "date_start": "2025-07-01", "date_end": "2025-07-31"},
        {"theme": "comfort", "channel_mix": ["redbook"], "budget": 80000}
      ],
      "product_line": "moodyplus",
      "audience_segment": "general"
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "steps" not in data:
        return jsonify({"error": "需要 steps 数组"}), 400

    steps = data["steps"]
    if not isinstance(steps, list) or len(steps) < 1:
        return jsonify({"error": "steps 至少需要 1 步"}), 400

    missing_theme = [i for i, s in enumerate(steps) if not (s.get("theme") or "").strip()]
    if missing_theme:
        return jsonify({"error": f"steps[{missing_theme[0]}] 缺少 theme 参数"}), 400

    engine = _engine()
    try:
        result = engine.simulate_scenario(
            steps=steps,
            product_line=data.get("product_line", "moodyplus"),
            audience_segment=data.get("audience_segment", "general"),
            market=data.get("market", "cn"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@brandiction_bp.route("/compare-scenarios", methods=["POST"])
@login_required
def compare_scenarios():
    """
    多情景对比 — 并排比较多条时间线。

    Body:
    {
      "scenarios": [
        {
          "name": "重科普路线",
          "steps": [{"theme": "science", ...}, {"theme": "science", ...}]
        },
        {
          "name": "颜值种草路线",
          "steps": [{"theme": "beauty", ...}, {"theme": "beauty", ...}]
        }
      ],
      "product_line": "moodyplus"
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data or "scenarios" not in data:
        return jsonify({"error": "需要 scenarios 数组"}), 400

    scenarios = data["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) < 1:
        return jsonify({"error": "scenarios 至少需要 1 条"}), 400

    engine = _engine()
    try:
        result = engine.compare_scenarios(
            scenarios=scenarios,
            product_line=data.get("product_line", "moodyplus"),
            audience_segment=data.get("audience_segment", "general"),
            market=data.get("market", "cn"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


# ------------------------------------------------------------------
# Race History
# ------------------------------------------------------------------

@brandiction_bp.route("/race-history", methods=["GET"])
@login_required
def race_history():
    """列出所有 race run 记录"""
    runs = _store().list_race_runs()
    return jsonify({"runs": runs})


@brandiction_bp.route("/race-history/<run_id>", methods=["GET"])
@login_required
def get_race_run(run_id: str):
    """获取单次 race run 详情（含完整结果）"""
    run = _store().get_race_run(run_id)
    if not run:
        return jsonify({"error": f"race run '{run_id}' 不存在"}), 404
    return jsonify(run)


@brandiction_bp.route("/race-history/<run_id>/resolve", methods=["POST"])
@admin_required
def resolve_race_run(run_id: str):
    """
    标记 race run 的实际结果。

    Body: {"status": "verified", "hit": true}
    """
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status", "verified")
    hit = data.get("hit")
    store = _store()
    existing = store.get_race_run(run_id)
    if not existing:
        return jsonify({"error": f"race run '{run_id}' 不存在"}), 404
    store.update_race_run_resolution(run_id, status, hit)
    return jsonify({"status": "ok", "run_id": run_id})


# ------------------------------------------------------------------
# V3 Race — dual-track campaign ranking
# ------------------------------------------------------------------

@brandiction_bp.route("/race", methods=["POST"])
@login_required
def race_campaigns():
    """
    V3 赛马排序 — 双轨输出。

    Track 1 (observed_baseline): 真实历史漏斗数据排序，决定排名。
    Track 2 (model_hypothesis): 感知模型假设，仅供解释/风险提示，不参与排名。

    Body:
    {
      "plans": [
        {"name": "小红书科普", "theme": "science_credibility",
         "platform": "redbook", "channel_family": "social_seed",
         "market": "cn", "budget": 50000}
      ],
      "sort_by": "roas_mean",
      "include_hypothesis": true
    }

    sort_by options: roas_mean (default), purchase_rate, revenue_mean, cvr_mean
    """
    data = request.get_json(force=True, silent=True)
    if not data or "plans" not in data:
        return jsonify({"error": "需要 plans 数组"}), 400

    plans = data["plans"]
    if not isinstance(plans, list) or len(plans) < 1:
        return jsonify({"error": "plans 至少需要 1 个 campaign plan"}), 400

    sort_by = data.get("sort_by", "roas_mean")
    include_hypothesis = data.get("include_hypothesis", True)
    product_line = data.get("product_line", "moodyplus")
    category = data.get("category", product_line)  # explicit category or fall back to product_line
    audience_segment = data.get("audience_segment", "general")
    market = data.get("market", "cn")
    season_tag = data.get("season_tag")  # 618 / double11 / cny / regular

    _logger.info(f"Race category: {category}, product_line: {product_line}")

    # Inject top-level market into plans that don't specify their own
    for plan in plans:
        if not plan.get("market"):
            plan["market"] = market

    # Track 1: historical baseline ranking (drives the actual ranking)
    ranker = _ranker()
    try:
        baseline_result = ranker.rank_campaigns(
            plans=plans, sort_by=sort_by,
            product_line=product_line, audience_segment=audience_segment,
            season_tag=season_tag,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Image analysis: analyze visual content for plans with images
    visual_profiles = {}  # plan_id -> visual_profile (keyed by id, not name)
    plans_with_images = [p for p in plans if p.get("image_paths")]
    if plans_with_images:
        try:
            analyzer = ImageAnalyzer()
            for plan in plans_with_images:
                plan_id = plan.get("id") or plan.get("name", "")
                image_paths = plan.get("image_paths", [])
                if not image_paths:
                    continue
                profile = analyzer.analyze_plan_images(image_paths)
                if profile:
                    visual_profiles[plan_id] = profile
                    _logger.info(
                        f"图片分析完成: {plan.get('name', plan_id)} ({len(image_paths)} 张图片)"
                    )
        except Exception as e:
            _logger.error(f"图片分析服务异常，跳过: {e}")

    # Visual adjustment: apply image-aware differentiation to ranking
    if visual_profiles and baseline_result.get("ranking"):
        baseline_result["ranking"] = apply_visual_adjustment(
            baseline_result["ranking"],
            visual_profiles,
        )
        # Re-generate recommendation after adjustment
        baseline_result["recommendation"] = ranker._generate_recommendation(
            baseline_result["ranking"], sort_by
        )

    # Track 2: perception model hypothesis (explanation only, now image-aware)
    hypothesis = None
    if include_hypothesis:
        engine = _engine()
        hypothesis_plans = []
        for plan in plans:
            if not (plan.get("theme") or "").strip():
                hypothesis_plans.append({"plan": plan, "note": "缺少 theme，无法生成假设"})
                continue
            # Bridge platform → channel_mix so predict_impact actually uses it
            hyp_plan = dict(plan)
            if hyp_plan.get("platform") and not hyp_plan.get("channel_mix"):
                hyp_plan["channel_mix"] = [hyp_plan["platform"]]
            try:
                pred = engine.predict_impact(
                    intervention_plan=hyp_plan,
                    product_line=product_line,
                    audience_segment=audience_segment,
                    market=hyp_plan.get("market", market),
                )
                plan_id = plan.get("id") or plan.get("name", "")
                visual_profile = visual_profiles.get(plan_id)

                hyp_entry = {
                    "plan": plan,
                    "predicted_delta": pred["delta"],
                    "confidence": pred["confidence"],
                    "reasoning": pred["reasoning"],
                    "similar_interventions": pred.get("similar_interventions", 0),
                }

                # Inject visual analysis into hypothesis reasoning
                if visual_profile:
                    visual_reasoning = _build_visual_reasoning(visual_profile)
                    hyp_entry["reasoning"] = (
                        pred["reasoning"] + "\n\n" + visual_reasoning
                    )
                    hyp_entry["visual_profile"] = visual_profile

                hypothesis_plans.append(hyp_entry)
            except Exception as e:
                hypothesis_plans.append({"plan": plan, "error": str(e)})
        hypothesis = {
            "note": "模型假设仅供解释和风险提示，不参与排名。图片分析结果已纳入推理",
            "plans": hypothesis_plans,
        }

    # Attach visual_profiles to response for frontend rendering
    visual_analysis_output = None
    if visual_profiles:
        visual_analysis_output = {
            "note": "图片内容分析已参与排序判别",
            "profiles": visual_profiles,
        }

    # Auto-persist race run
    race_run_id = f"race_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    top_rec = ""
    if baseline_result.get("ranking"):
        top_entry = baseline_result["ranking"][0]
        top_plan = top_entry.get("plan", {})
        top_rec = top_plan.get("name", "") or f"Plan #{top_entry.get('rank', 1)}"

    result_payload = {
        "category": category,
        "observed_baseline": baseline_result,
        "model_hypothesis": hypothesis,
        "visual_analysis": visual_analysis_output,
    }
    store = _store()
    store.save_race_run(
        run_id=race_run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        plans=plans,
        sort_by=sort_by,
        result=result_payload,
        top_recommendation=top_rec,
        status="pending",
    )

    return jsonify(result_payload)
