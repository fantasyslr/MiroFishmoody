#!/usr/bin/env python3
"""
Meta Ad Library 半自动审核器
===========================
用 Playwright headed 模式打开 Meta Ad Library，辅助人工审核 competitor_events。
支持：持久登录态、人工过验证码、自动截图、证据采集、候选生成。

用法:
    # 首次运行（会打开浏览器让你登录 Meta）
    uv run python review_meta_ad_library.py

    # 指定输入文件
    uv run python review_meta_ad_library.py --input ../uploads/competitor_events_second_pass.csv

    # 只处理指定品牌
    uv run python review_meta_ad_library.py --competitors hapakristin,ttdeye

    # 跳过人工暂停（已有登录态时）
    uv run python review_meta_ad_library.py --no-pause

依赖:
    pip install playwright
    playwright install chromium
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
DEFAULT_INPUT = UPLOADS_DIR / "competitor_events_second_pass.csv"
RESULTS_CSV = UPLOADS_DIR / "meta_ad_library_review_results.csv"
REPORT_MD = UPLOADS_DIR / "meta_ad_library_review_report.md"
CANDIDATES_CSV = UPLOADS_DIR / "competitor_events_meta_candidates.csv"
SCREENSHOTS_DIR = UPLOADS_DIR / "meta_ad_library_screenshots"
USER_DATA_DIR = Path(__file__).resolve().parent.parent / ".playwright_meta_session"

PRIORITY_COMPETITORS = [
    "hapakristin", "ttdeye", "eyecandys", "pinkparadise", "olensglobal",
]

# Evidence keywords
DISCOUNT_KEYWORDS = re.compile(
    r"\b(\d+%?\s*off|save\s+\$?\d+|coupon|sale|clearance|discount|bogo|flash\s*sale|free\s+shipping)\b",
    re.IGNORECASE,
)
LAUNCH_KEYWORDS = re.compile(
    r"\b(new\s*(arrival|launch|collection|product|release)|just\s*dropped|coming\s*soon|pre-?order)\b",
    re.IGNORECASE,
)
PRODUCT_NAME_PATTERN = re.compile(
    r"(?:lens|color|contact|eye|kristin|dolly|ivory|glossy|natural|cosplay)\s*\w*",
    re.IGNORECASE,
)

RESULTS_COLUMNS = [
    "competitor", "source_url", "review_result", "suggested_event_type",
    "suggested_impact_estimate", "evidence_summary", "screenshot_path",
    "page_title", "observed_ad_count", "observed_claims",
    "observed_offer_terms", "observed_product_names", "reviewer_notes",
]

CANDIDATES_COLUMNS = [
    "date", "competitor", "market", "suggested_event_type",
    "suggested_impact_estimate", "description", "source", "source_url",
    "confidence", "evidence_summary", "review_status", "reviewer_notes",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ReviewResult:
    competitor: str = ""
    source_url: str = ""
    review_result: str = "blocked"  # confirmed / no_evidence / blocked / ambiguous
    suggested_event_type: str = ""
    suggested_impact_estimate: str = "low"
    evidence_summary: str = ""
    screenshot_path: str = ""
    page_title: str = ""
    observed_ad_count: str = "unknown"
    observed_claims: str = ""
    observed_offer_terms: str = ""
    observed_product_names: str = ""
    reviewer_notes: str = ""


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def load_pending_meta_rows(csv_path: Path) -> list[dict]:
    """Load only meta_ad_library + pending rows from the input CSV."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("source") == "meta_ad_library" and row.get("review_status") == "pending":
                rows.append(row)
    return rows


def filter_by_competitors(rows: list[dict], competitors: list[str] | None) -> list[dict]:
    """Filter rows to only specified competitors, preserving priority order."""
    if not competitors:
        return rows
    comp_set = set(c.lower().strip() for c in competitors)
    return [r for r in rows if r.get("competitor", "").lower().strip() in comp_set]


def sort_by_priority(rows: list[dict]) -> list[dict]:
    """Sort rows by PRIORITY_COMPETITORS order, unknowns last."""
    priority_map = {c: i for i, c in enumerate(PRIORITY_COMPETITORS)}
    return sorted(rows, key=lambda r: priority_map.get(r.get("competitor", ""), 999))


def write_results_csv(results: list[ReviewResult], path: Path):
    """Write review results to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_COLUMNS)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def write_candidates_csv(results: list[ReviewResult], path: Path):
    """Generate candidate events from confirmed results only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    candidates = [r for r in results if r.review_result == "confirmed"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CANDIDATES_COLUMNS)
        writer.writeheader()
        for r in candidates:
            writer.writerow({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "competitor": r.competitor,
                "market": "global",
                "suggested_event_type": r.suggested_event_type,
                "suggested_impact_estimate": r.suggested_impact_estimate,
                "description": f"Meta Ad Library 发现活跃广告: {r.observed_claims[:120]}" if r.observed_claims else f"Meta Ad Library 发现活跃广告投放",
                "source": "meta_ad_library",
                "source_url": r.source_url,
                "confidence": "medium" if r.observed_ad_count not in ("unknown", "0", "") else "low",
                "evidence_summary": r.evidence_summary,
                "review_status": "pending_review",
                "reviewer_notes": f"screenshot: {r.screenshot_path}; {r.reviewer_notes}",
            })


def write_report(results: list[ReviewResult], path: Path):
    """Generate the Markdown review report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    confirmed = [r for r in results if r.review_result == "confirmed"]
    no_ev = [r for r in results if r.review_result == "no_evidence"]
    blocked = [r for r in results if r.review_result == "blocked"]
    ambiguous = [r for r in results if r.review_result == "ambiguous"]

    lines = [
        "# Meta Ad Library 半自动审核报告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**处理工具**: review_meta_ad_library.py (Playwright headed)",
        "",
        "---",
        "",
        "## 总体统计",
        "",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| 总处理条数 | {len(results)} |",
        f"| confirmed (有明确广告证据) | {len(confirmed)} |",
        f"| no_evidence (无活跃广告) | {len(no_ev)} |",
        f"| blocked (403/登录/验证码) | {len(blocked)} |",
        f"| ambiguous (有广告但证据不足) | {len(ambiguous)} |",
        "",
    ]

    if confirmed:
        lines += [
            "## 推荐优先审核 (confirmed)",
            "",
            "| # | 品牌 | 事件类型 | 广告数 | 关键证据 | 截图 |",
            "|---|------|---------|--------|---------|------|",
        ]
        for i, r in enumerate(confirmed, 1):
            claim_short = (r.observed_claims[:60] + "...") if len(r.observed_claims) > 60 else r.observed_claims
            ss = f"[截图]({r.screenshot_path})" if r.screenshot_path else "无"
            lines.append(f"| {i} | {r.competitor} | {r.suggested_event_type} | {r.observed_ad_count} | {claim_short} | {ss} |")
        lines += [""]

        lines += ["### 每条为什么值得看 & 看什么", ""]
        for i, r in enumerate(confirmed, 1):
            lines += [
                f"**{i}. {r.competitor}**",
                f"- 证据: {r.evidence_summary}",
                f"- 截图: `{r.screenshot_path}`",
                f"- 审核时看: 截图中广告创意是否包含明确促销/新品信息，确认不是常驻广告",
                "",
            ]

    if blocked:
        lines += [
            "## 被阻断的条目 (blocked)",
            "",
        ]
        for r in blocked:
            lines.append(f"- **{r.competitor}**: {r.reviewer_notes}")
        lines.append("")

    if ambiguous:
        lines += [
            "## 证据模糊的条目 (ambiguous)",
            "",
        ]
        for r in ambiguous:
            lines.append(f"- **{r.competitor}**: {r.evidence_summary}")
        lines.append("")

    if no_ev:
        lines += [
            "## 无证据的条目 (no_evidence)",
            "",
        ]
        for r in no_ev:
            lines.append(f"- **{r.competitor}**: 搜索后未发现活跃广告")
        lines.append("")

    lines += [
        "---",
        "",
        "## 使用说明",
        "",
        "### 首次运行",
        "```bash",
        "cd backend",
        "uv pip install playwright",
        "uv run playwright install chromium",
        "uv run python scripts/review_meta_ad_library.py",
        "```",
        "浏览器会打开 Meta Ad Library，如果需要登录会暂停等你操作。",
        "",
        "### 浏览器卡住时",
        "脚本会在每个 URL 前检测页面状态。如果遇到验证码/登录页，",
        "终端会提示 `请在浏览器中完成操作，然后按 Enter 继续...`。",
        "手动完成后按 Enter 即可继续。",
        "",
        "### 重用 session",
        "登录态保存在 `backend/.playwright_meta_session/`。",
        "下次运行不需要重新登录（除非 cookie 过期）。",
        "如需清除：`rm -rf backend/.playwright_meta_session/`",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Page analysis (pure functions, no Playwright dependency)
# ---------------------------------------------------------------------------

def analyze_page_text(text: str) -> dict:
    """Extract evidence signals from page text. Pure function, no browser needed."""
    text_lower = text.lower()

    discount_matches = DISCOUNT_KEYWORDS.findall(text)
    launch_matches = LAUNCH_KEYWORDS.findall(text)
    product_matches = PRODUCT_NAME_PATTERN.findall(text)

    # Try to extract ad count from Meta Ad Library patterns
    ad_count = "unknown"
    # Pattern: "X results" or "About X ads"
    count_match = re.search(r"(\d[\d,]*)\s*(?:results?|ads?)\b", text_lower)
    if count_match:
        ad_count = count_match.group(1).replace(",", "")

    # Check for "no results" signals
    if any(phrase in text_lower for phrase in [
        "no results", "no ads match", "we didn't find any",
        "0 results", "try a different search",
    ]):
        ad_count = "0"

    return {
        "discount_matches": list(set(discount_matches)),
        "launch_matches": [m if isinstance(m, str) else m[0] for m in set(launch_matches)],
        "product_names": list(set(product_matches))[:10],
        "ad_count": ad_count,
        "has_discount_evidence": len(discount_matches) > 0,
        "has_launch_evidence": len(launch_matches) > 0,
    }


def classify_result(analysis: dict, page_loaded: bool, was_blocked: bool) -> tuple[str, str, str]:
    """
    Classify review result based on analysis.
    Returns (review_result, suggested_event_type, impact_estimate).
    """
    if was_blocked:
        return "blocked", "", "low"

    if not page_loaded:
        return "blocked", "", "low"

    has_ads = analysis["ad_count"] not in ("unknown", "0", "")
    has_discount = analysis["has_discount_evidence"]
    has_launch = analysis["has_launch_evidence"]

    if analysis["ad_count"] == "0":
        return "no_evidence", "", "low"

    if has_discount and has_ads:
        return "confirmed", "campaign", "medium"

    if has_launch and has_ads:
        return "confirmed", "new_launch", "medium"

    if has_ads and int(analysis["ad_count"]) > 0 if analysis["ad_count"].isdigit() else False:
        # Ads exist but no clear discount/launch signal
        if int(analysis["ad_count"]) >= 10:
            return "confirmed", "campaign", "medium"
        else:
            return "ambiguous", "campaign", "low"

    if has_discount or has_launch:
        # Keywords found but ad count unknown
        return "ambiguous", "campaign" if has_discount else "new_launch", "low"

    return "no_evidence", "", "low"


def build_evidence_summary(analysis: dict, review_result: str) -> str:
    """Build a human-readable evidence summary."""
    parts = []

    if analysis["ad_count"] != "unknown":
        parts.append(f"观察到广告数: {analysis['ad_count']}")

    if analysis["discount_matches"]:
        parts.append(f"折扣关键词: {', '.join(analysis['discount_matches'][:5])}")

    if analysis["launch_matches"]:
        parts.append(f"新品关键词: {', '.join(analysis['launch_matches'][:5])}")

    if analysis["product_names"]:
        parts.append(f"产品名: {', '.join(analysis['product_names'][:5])}")

    if not parts:
        if review_result == "no_evidence":
            return "页面搜索无结果或无活跃广告"
        elif review_result == "blocked":
            return "页面被阻断，无法获取内容"
        return "未发现明确证据"

    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Browser automation
# ---------------------------------------------------------------------------

def run_browser_review(rows: list[dict], no_pause: bool = False) -> list[ReviewResult]:
    """
    Open Meta Ad Library URLs in a Playwright headed browser.
    Returns ReviewResult for each row.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    except ImportError:
        print("=" * 60)
        print("Playwright 未安装。请运行:")
        print("  uv pip install playwright")
        print("  uv run playwright install chromium")
        print("=" * 60)
        sys.exit(1)

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    results: list[ReviewResult] = []

    with sync_playwright() as p:
        # Persistent context: keeps cookies/login across runs
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        # First: navigate to Meta Ad Library landing to check login status
        print("\n🔍 正在打开 Meta Ad Library 首页检测登录状态...")
        page.goto("https://www.facebook.com/ads/library/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Check if blocked/login required
        if _needs_human_intervention(page) and not no_pause:
            print("\n" + "=" * 60)
            print("⚠️  需要人工操作：请在浏览器中完成登录/验证码")
            print("   完成后按 Enter 继续...")
            print("=" * 60)
            input()

        # Process each row
        for i, row in enumerate(rows):
            competitor = row.get("competitor", "unknown")
            source_url = row.get("source_url", "")
            print(f"\n[{i+1}/{len(rows)}] 处理 {competitor}: {source_url}")

            result = ReviewResult(
                competitor=competitor,
                source_url=source_url,
            )

            try:
                page.goto(source_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)  # Let dynamic content load

                # Check for blocks
                if _needs_human_intervention(page):
                    if no_pause:
                        result.review_result = "blocked"
                        result.reviewer_notes = "页面需要人工操作但 --no-pause 已设置"
                        results.append(result)
                        continue
                    else:
                        print(f"  ⚠️  {competitor} 页面需要人工操作，请在浏览器中完成，然后按 Enter...")
                        input()
                        time.sleep(2)

                # Get page content
                result.page_title = page.title()
                page_text = page.inner_text("body")

                # Take screenshot
                ss_name = f"{competitor}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                ss_path = SCREENSHOTS_DIR / ss_name
                page.screenshot(path=str(ss_path), full_page=False)
                result.screenshot_path = str(ss_path)
                print(f"  📸 截图: {ss_name}")

                # Analyze
                analysis = analyze_page_text(page_text)
                review_result, event_type, impact = classify_result(
                    analysis, page_loaded=True, was_blocked=False
                )

                result.review_result = review_result
                result.suggested_event_type = event_type
                result.suggested_impact_estimate = impact
                result.observed_ad_count = analysis["ad_count"]
                result.observed_claims = "; ".join(
                    analysis["discount_matches"][:5] + analysis["launch_matches"][:5]
                )
                result.observed_offer_terms = ", ".join(analysis["discount_matches"][:5])
                result.observed_product_names = ", ".join(analysis["product_names"][:5])
                result.evidence_summary = build_evidence_summary(analysis, review_result)
                result.reviewer_notes = (
                    f"page_title={result.page_title}; "
                    f"ad_count={analysis['ad_count']}; "
                    f"discount_kw={len(analysis['discount_matches'])}; "
                    f"launch_kw={len(analysis['launch_matches'])}"
                )

                status_icon = {
                    "confirmed": "✅",
                    "no_evidence": "❌",
                    "blocked": "🚫",
                    "ambiguous": "🔶",
                }.get(review_result, "❓")
                print(f"  {status_icon} 结果: {review_result} | 广告数: {analysis['ad_count']} | 类型: {event_type or 'N/A'}")

            except PwTimeout:
                result.review_result = "blocked"
                result.reviewer_notes = "页面加载超时 (30s)"
                result.evidence_summary = "页面加载超时，无法获取内容"
                print(f"  🚫 超时")
            except Exception as e:
                result.review_result = "blocked"
                result.reviewer_notes = f"异常: {str(e)[:200]}"
                result.evidence_summary = f"脚本异常: {str(e)[:100]}"
                print(f"  🚫 异常: {e}")

            results.append(result)

        # Close browser
        print("\n📋 处理完成，关闭浏览器...")
        context.close()

    return results


def _needs_human_intervention(page) -> bool:
    """Detect if the page is showing a login, captcha, or consent wall."""
    try:
        url = page.url.lower()
        title = page.title().lower()
        # Login page
        if "login" in url or "checkpoint" in url:
            return True
        # Consent/cookie wall
        if "consent" in url:
            return True
        # Check for common block indicators in body
        body_text = page.inner_text("body")[:2000].lower()
        block_signals = [
            "log in to continue",
            "log into facebook",
            "create new account",
            "enter the code shown",
            "security check",
            "confirm your identity",
            "please verify",
        ]
        return any(signal in body_text for signal in block_signals)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Dry-run mode (no browser, for testing)
# ---------------------------------------------------------------------------

def run_dry(rows: list[dict]) -> list[ReviewResult]:
    """Generate placeholder results without a browser, for testing/CI."""
    results = []
    for row in rows:
        r = ReviewResult(
            competitor=row.get("competitor", "unknown"),
            source_url=row.get("source_url", ""),
            review_result="blocked",
            reviewer_notes="dry_run 模式，未启动浏览器",
            evidence_summary="dry_run 模式，无浏览器证据",
        )
        results.append(r)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Meta Ad Library 半自动审核器")
    parser.add_argument("--input", type=str, default=str(DEFAULT_INPUT),
                        help="输入 CSV 文件路径")
    parser.add_argument("--competitors", type=str, default=None,
                        help="逗号分隔的品牌列表，例如: hapakristin,ttdeye")
    parser.add_argument("--no-pause", action="store_true",
                        help="跳过所有人工暂停（已有登录态时使用）")
    parser.add_argument("--dry-run", action="store_true",
                        help="测试模式，不启动浏览器")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_path}")
        sys.exit(1)

    # Load and filter
    rows = load_pending_meta_rows(input_path)
    print(f"📊 从 {input_path.name} 加载了 {len(rows)} 条 meta_ad_library pending 记录")

    comp_list = [c.strip() for c in args.competitors.split(",")] if args.competitors else None
    rows = filter_by_competitors(rows, comp_list)
    rows = sort_by_priority(rows)
    print(f"📊 过滤后待处理: {len(rows)} 条")

    if not rows:
        print("✅ 无需处理的记录")
        sys.exit(0)

    for r in rows:
        print(f"  - {r['competitor']}: {r['source_url'][:70]}...")

    # Run
    if args.dry_run:
        results = run_dry(rows)
    else:
        results = run_browser_review(rows, no_pause=args.no_pause)

    # Write outputs
    write_results_csv(results, RESULTS_CSV)
    print(f"\n📄 结果 CSV: {RESULTS_CSV}")

    write_candidates_csv(results, CANDIDATES_CSV)
    confirmed_count = sum(1 for r in results if r.review_result == "confirmed")
    print(f"📄 候选 CSV: {CANDIDATES_CSV} ({confirmed_count} 条 confirmed)")

    write_report(results, REPORT_MD)
    print(f"📄 审核报告: {REPORT_MD}")

    print(f"📁 截图目录: {SCREENSHOTS_DIR}")
    print("\n✅ 完成")


if __name__ == "__main__":
    main()
