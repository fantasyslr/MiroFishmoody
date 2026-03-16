#!/usr/bin/env python3
"""
半自动竞品事件采集器
从公开网页抓取 metadata，生成 draft CSV 供人工审核。
不直接写入 brandiction.db。

用法:
    python collect_competitor_events.py --watchlist ../uploads/templates/competitor_watchlist.yaml
    python collect_competitor_events.py --watchlist ../uploads/templates/competitor_watchlist.yaml --from 2026-03-10 --to 2026-03-16
"""

import argparse
import csv
import hashlib
import re
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, date
from html.parser import HTMLParser
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = {"price_cut", "new_launch", "campaign", "collab", "bundle_offer", "listing_change"}
VALID_IMPACTS = {"high", "medium", "low"}
VALID_SOURCES = {"official_site", "meta_ad_library", "google_ads_transparency", "tiktok_creative_center", "manual_note"}

DRAFT_COLUMNS = [
    "suggested_event_id",
    "date",
    "competitor",
    "market",
    "suggested_event_type",
    "suggested_impact_estimate",
    "description",
    "source",
    "source_url",
    "confidence",
    "review_status",
    "reviewer_notes",
]

# Keyword → (event_type, impact_estimate)
EVENT_KEYWORDS = {
    # price_cut
    r"\b(\d+%?\s*off)\b": ("price_cut", "medium"),
    r"\bsale\b": ("price_cut", "medium"),
    r"\bdiscount\b": ("price_cut", "medium"),
    r"\bclearance\b": ("price_cut", "high"),
    r"\bflash\s*sale\b": ("price_cut", "medium"),
    r"\bbogo\b": ("price_cut", "medium"),
    r"\bbuy\s*\d+\s*get\b": ("bundle_offer", "medium"),
    # new_launch
    r"\bnew\s*(arrival|launch|release|product|collection|series)\b": ("new_launch", "medium"),
    r"\bjust\s*dropped\b": ("new_launch", "medium"),
    r"\bcoming\s*soon\b": ("new_launch", "low"),
    r"\bpre-?order\b": ("new_launch", "low"),
    # campaign
    r"\bcampaign\b": ("campaign", "medium"),
    r"\blimited\s*edition\b": ("campaign", "high"),
    r"\bexclusive\b": ("campaign", "medium"),
    r"\bgiveaway\b": ("campaign", "low"),
    r"\bfree\s*shipping\b": ("campaign", "low"),
    # collab
    r"\bcollab(oration)?\b": ("collab", "high"),
    r"\bpartner(ship)?\b": ("collab", "medium"),
    r"\bx\s+[A-Z]": ("collab", "medium"),
    # bundle_offer
    r"\bbundle\b": ("bundle_offer", "medium"),
    r"\bcombo\b": ("bundle_offer", "low"),
    r"\bset\s*deal\b": ("bundle_offer", "low"),
}

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Minimal HTML title/meta parser
# ---------------------------------------------------------------------------

class MetaParser(HTMLParser):
    """Extract title, meta description, og tags, and visible text snippets."""

    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ""
        self.meta_description = ""
        self.og_title = ""
        self.og_description = ""
        self._text_chunks: list[str] = []
        self._skip_tags = {"script", "style", "noscript"}
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            if name == "description":
                self.meta_description = content
            elif prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._text_chunks.append(stripped)

    @property
    def visible_text(self) -> str:
        return " ".join(self._text_chunks[:200])  # first ~200 chunks


# ---------------------------------------------------------------------------
# Fetch & parse
# ---------------------------------------------------------------------------

def fetch_page(url: str) -> str | None:
    """Fetch a public URL and return HTML text. Returns None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" in str(exc):
            # Retry with unverified context for public pages
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    return resp.read().decode(charset, errors="replace")
            except Exception as exc2:
                print(f"  [WARN] Failed to fetch {url} (ssl fallback): {exc2}", file=sys.stderr)
                return None
        print(f"  [WARN] Failed to fetch {url}: {exc}", file=sys.stderr)
        return None
    except (urllib.error.HTTPError, OSError, UnicodeDecodeError) as exc:
        print(f"  [WARN] Failed to fetch {url}: {exc}", file=sys.stderr)
        return None


def parse_meta(html: str) -> MetaParser:
    parser = MetaParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser


def detect_events(text: str) -> list[tuple[str, str, str]]:
    """Return list of (event_type, impact_estimate, matched_text) from keyword matching."""
    results = []
    text_lower = text.lower()
    seen_types: set[str] = set()
    for pattern, (etype, impact) in EVENT_KEYWORDS.items():
        for m in re.finditer(pattern, text_lower):
            if etype not in seen_types:
                # grab surrounding context (up to 80 chars)
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 50)
                context = text[start:end].replace("\n", " ").strip()
                results.append((etype, impact, context))
                seen_types.add(etype)
    return results


def make_event_id(competitor: str, source: str, date_str: str, desc: str) -> str:
    """Generate a deterministic event ID."""
    raw = f"{competitor}|{source}|{date_str}|{desc[:60]}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"ce-draft-{competitor[:10]}-{h}"


# ---------------------------------------------------------------------------
# Source processors
# ---------------------------------------------------------------------------

def process_official_site(competitor: str, markets: list[str], urls: list[str], date_str: str) -> list[dict]:
    """Scrape official site pages for event signals."""
    events = []
    for url in urls:
        print(f"  [official_site] Fetching {url}")
        html = fetch_page(url)
        if not html:
            continue
        meta = parse_meta(html)
        # Combine all text signals
        combined = " ".join(filter(None, [meta.title, meta.og_title, meta.meta_description, meta.og_description, meta.visible_text]))
        if not combined.strip():
            continue
        detected = detect_events(combined)
        for etype, impact, context in detected:
            for market in markets:
                desc = f"[auto] {context}"
                eid = make_event_id(competitor, "official_site", date_str, desc + market)
                events.append({
                    "suggested_event_id": eid,
                    "date": date_str,
                    "competitor": competitor,
                    "market": market,
                    "suggested_event_type": etype,
                    "suggested_impact_estimate": impact,
                    "description": desc,
                    "source": "official_site",
                    "source_url": url,
                    "confidence": "low",
                    "review_status": "pending",
                    "reviewer_notes": f"extraction_method=keyword_match; page_title={meta.title[:80]}",
                })
    return events


def process_ad_library(competitor: str, markets: list[str], urls: list[str], source_type: str, date_str: str) -> list[dict]:
    """
    Ad library pages (Meta/Google/TikTok) are JS-heavy and won't yield much from
    simple HTTP GET. We still try to get any server-rendered content, but mainly
    generate a 'manual_check' reminder event so the reviewer knows to visit.
    """
    events = []
    for url in urls:
        print(f"  [{source_type}] Fetching {url}")
        html = fetch_page(url)
        has_content = False
        if html:
            meta = parse_meta(html)
            combined = " ".join(filter(None, [meta.title, meta.og_title, meta.meta_description, meta.og_description]))
            detected = detect_events(combined)
            for etype, impact, context in detected:
                has_content = True
                for market in markets:
                    desc = f"[auto] {context}"
                    eid = make_event_id(competitor, source_type, date_str, desc + market)
                    events.append({
                        "suggested_event_id": eid,
                        "date": date_str,
                        "competitor": competitor,
                        "market": market,
                        "suggested_event_type": etype,
                        "suggested_impact_estimate": impact,
                        "description": desc,
                        "source": source_type,
                        "source_url": url,
                        "confidence": "low",
                        "review_status": "pending",
                        "reviewer_notes": f"extraction_method=keyword_match_on_meta; js_rendered=false",
                    })
        # Always generate a reminder to manually check this URL
        if not has_content:
            for market in markets[:1]:  # only one reminder per URL
                eid = make_event_id(competitor, source_type, date_str, "manual_check" + url)
                events.append({
                    "suggested_event_id": eid,
                    "date": date_str,
                    "competitor": competitor,
                    "market": market,
                    "suggested_event_type": "listing_change",
                    "suggested_impact_estimate": "low",
                    "description": f"[manual_check] Please visit this {source_type} URL and check for active ads/campaigns",
                    "source": source_type,
                    "source_url": url,
                    "confidence": "none",
                    "review_status": "pending",
                    "reviewer_notes": "extraction_method=manual_check_reminder; needs_browser=true",
                })
    return events


# ---------------------------------------------------------------------------
# Main collection logic
# ---------------------------------------------------------------------------

def load_watchlist(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("competitors", [])


def collect_all(watchlist_path: str, date_from: str | None, date_to: str | None, output_path: str):
    competitors = load_watchlist(watchlist_path)
    if not competitors:
        print("No competitors found in watchlist.", file=sys.stderr)
        sys.exit(1)

    today = date.today().isoformat()
    date_str = date_to or today  # use the end date as the event date if specified, else today

    all_events: list[dict] = []

    for comp in competitors:
        name = comp["competitor"]
        markets = comp.get("markets", ["global"])
        print(f"\n--- Processing: {name} ---")

        # Official sites
        official_urls = comp.get("official_site_urls", [])
        if official_urls:
            all_events.extend(process_official_site(name, markets, official_urls, date_str))

        # Meta Ad Library
        meta_urls = comp.get("meta_ad_library_urls", [])
        if meta_urls:
            all_events.extend(process_ad_library(name, markets, meta_urls, "meta_ad_library", date_str))

        # Google Ads Transparency
        google_urls = comp.get("google_ads_transparency_urls", [])
        if google_urls:
            all_events.extend(process_ad_library(name, markets, google_urls, "google_ads_transparency", date_str))

        # TikTok Creative Center
        tiktok_urls = comp.get("tiktok_creative_center_urls", [])
        if tiktok_urls:
            all_events.extend(process_ad_library(name, markets, tiktok_urls, "tiktok_creative_center", date_str))

    # Deduplicate by suggested_event_id
    seen_ids: set[str] = set()
    unique_events: list[dict] = []
    for ev in all_events:
        if ev["suggested_event_id"] not in seen_ids:
            seen_ids.add(ev["suggested_event_id"])
            unique_events.append(ev)

    # Write draft CSV
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DRAFT_COLUMNS)
        writer.writeheader()
        writer.writerows(unique_events)

    print(f"\n=== Done. {len(unique_events)} draft events written to {out} ===")
    print("Next step: review the CSV, set review_status to 'approved' or 'rejected', then run import_competitor_events.py")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="半自动竞品事件采集器")
    parser.add_argument("--watchlist", required=True, help="Path to competitor_watchlist.yaml")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date (YYYY-MM-DD), for reference only")
    parser.add_argument("--to", dest="date_to", default=None, help="End date (YYYY-MM-DD), used as event date")
    parser.add_argument("--output", default=None, help="Output draft CSV path (default: ../uploads/competitor_events_draft.csv)")
    args = parser.parse_args()

    output = args.output or str(Path(__file__).parent.parent / "uploads" / "competitor_events_draft.csv")
    collect_all(args.watchlist, args.date_from, args.date_to, output)


if __name__ == "__main__":
    main()
