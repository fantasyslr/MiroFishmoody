#!/usr/bin/env python3
"""
End-to-end smoke test — 真实 Flask + 真实 LLM

Usage:
    python3 tests/e2e_smoke.py [--base-url http://127.0.0.1:5099]
"""

import sys
import time
import json
import urllib.request
import urllib.error

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5099"


def api(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health():
    print("=== 1. Health Check ===")
    status, body = api("GET", "/health")
    assert status == 200, f"Expected 200, got {status}"
    assert body["status"] == "ok"
    print(f"  OK: {body}")


def test_evaluate_success():
    print("\n=== 2. Campaign Evaluation (success path) ===")
    payload = {
        "context": "Moody Lenses Q2 2026 campaign planning, moodyPlus product line",
        "campaigns": [
            {
                "id": "mp_health",
                "name": "moodyPlus 眼健康守护计划",
                "product_line": "moodyplus",
                "target_audience": "25-35岁现有隐形眼镜佩戴者，关注眼健康",
                "core_message": "硅水凝胶材质，临床级透氧率，让双眼自由呼吸",
                "channels": ["小红书", "微信公众号", "眼科渠道"],
                "creative_direction": "专业医疗感视觉，白色+蓝色主色调，强调透氧数据对比",
                "kv_description": "裸眼 vs 佩戴对比，空气感视觉",
            },
            {
                "id": "mp_switch",
                "name": "Acuvue 用户转换计划",
                "product_line": "moodyplus",
                "target_audience": "Acuvue Define 现有用户",
                "core_message": "同样自然放大，更高透氧率，更多选择",
                "channels": ["Meta广告", "Google搜索", "KOL合作"],
                "creative_direction": "对比式创意，Acuvue vs moodyPlus 参数并列，真人佩戴对比",
                "promo_mechanic": "首购立减30元，附赠试戴装",
            },
            {
                "id": "mp_lifestyle",
                "name": "moodyPlus 轻生活方式",
                "product_line": "moodyplus",
                "target_audience": "22-30岁都市女性，追求自然美",
                "core_message": "看不见的舒适，看得见的自然",
                "channels": ["抖音", "小红书", "Instagram"],
                "creative_direction": "生活方式内容，运动/办公/约会场景，强调全天舒适",
            },
        ],
    }

    # Submit
    print("  Submitting 3 campaigns...")
    status, body = api("POST", "/api/campaign/evaluate", payload)
    assert status == 200, f"Submit failed: {status} {body}"
    task_id = body["task_id"]
    set_id = body["set_id"]
    print(f"  task_id={task_id}, set_id={set_id}")

    # Poll until done
    print("  Polling status...")
    for i in range(120):  # max 10 min
        time.sleep(5)
        status, task = api("GET", f"/api/campaign/evaluate/status/{task_id}")
        assert status == 200
        pct = task.get("progress", 0)
        msg = task.get("message", "")
        task_status = task.get("status", "")
        print(f"    [{i*5}s] {task_status} {pct}% — {msg}")

        if task_status == "completed":
            print(f"  Task completed!")
            break
        elif task_status == "failed":
            print(f"  TASK FAILED: {task.get('error')}")
            sys.exit(1)
    else:
        print("  TIMEOUT after 10 minutes")
        sys.exit(1)

    # Fetch result
    print("\n  Fetching result...")
    status, result = api("GET", f"/api/campaign/result/{set_id}")
    assert status == 200, f"Result fetch failed: {status}"

    # Validate structure
    print("\n=== 3. Result Validation ===")

    # Rankings
    rankings = result.get("rankings", [])
    assert len(rankings) == 3, f"Expected 3 rankings, got {len(rankings)}"
    for r in rankings:
        assert "rank" in r, "Missing rank"
        assert "composite_score" in r, "Missing composite_score"
        assert "verdict" in r, "Missing verdict"
        assert r["verdict"] in ("ship", "revise", "kill"), f"Bad verdict: {r['verdict']}"
        assert "panel_avg" in r, "Missing panel_avg"
        assert "pairwise_wins" in r, "Missing pairwise_wins"
        assert "top_objections" in r, "Missing top_objections"
        assert "top_strengths" in r, "Missing top_strengths"
        print(f"  #{r['rank']} {r['campaign_name']}: "
              f"score={r['composite_score']}, panel={r['panel_avg']}, "
              f"wins={r['pairwise_wins']}, verdict={r['verdict'].upper()}")

    # Panel scores
    panel = result.get("panel_scores", [])
    assert len(panel) == 15, f"Expected 15 panel scores (5 personas × 3 campaigns), got {len(panel)}"
    personas_seen = set(ps["persona_id"] for ps in panel)
    assert len(personas_seen) == 5, f"Expected 5 unique personas, got {len(personas_seen)}"
    print(f"  Panel scores: {len(panel)} entries, {len(personas_seen)} personas")

    # Pairwise results
    pw = result.get("pairwise_results", [])
    assert len(pw) == 3, f"Expected 3 pairwise comparisons, got {len(pw)}"
    for p in pw:
        assert "campaign_a_id" in p
        assert "campaign_b_id" in p
        assert "winner_id" in p  # can be null for tie
        assert "votes" in p
    print(f"  Pairwise: {len(pw)} matchups")

    # Summary
    assert result.get("summary"), "Missing summary"
    assert isinstance(result.get("assumptions"), list), "Missing assumptions"
    assert isinstance(result.get("confidence_notes"), list), "Missing confidence_notes"
    print(f"  Summary: {result['summary'][:100]}...")
    print(f"  Assumptions: {len(result['assumptions'])} items")
    print(f"  Confidence notes: {len(result['confidence_notes'])} items")

    print("\n  SUCCESS: All fields validated!")
    return set_id


def test_failure_paths():
    print("\n=== 4. Failure Path Tests ===")

    # 4a. Empty body
    print("  4a. Empty body...")
    status, body = api("POST", "/api/campaign/evaluate", {})
    assert status == 400, f"Expected 400, got {status}"
    print(f"    OK: {status} — {body.get('error', '')}")

    # 4b. Only 1 campaign
    print("  4b. Only 1 campaign...")
    status, body = api("POST", "/api/campaign/evaluate", {
        "campaigns": [{"name": "X", "product_line": "moodyplus", "core_message": "test"}]
    })
    assert status == 400, f"Expected 400, got {status}"
    print(f"    OK: {status} — {body.get('error', '')}")

    # 4c. Invalid product_line
    print("  4c. Invalid product_line...")
    status, body = api("POST", "/api/campaign/evaluate", {
        "campaigns": [
            {"name": "A", "product_line": "invalid", "core_message": "test"},
            {"name": "B", "product_line": "moodyplus", "core_message": "test"},
        ]
    })
    assert status == 400, f"Expected 400, got {status}"
    print(f"    OK: {status} — {body.get('error', '')}")

    # 4d. Missing name
    print("  4d. Missing name...")
    status, body = api("POST", "/api/campaign/evaluate", {
        "campaigns": [
            {"product_line": "moodyplus", "core_message": "test"},
            {"name": "B", "product_line": "moodyplus", "core_message": "test"},
        ]
    })
    assert status == 400, f"Expected 400, got {status}"
    print(f"    OK: {status} — {body.get('error', '')}")

    # 4e. Invalid task_id
    print("  4e. Invalid task_id...")
    status, body = api("GET", "/api/campaign/evaluate/status/nonexistent-id")
    assert status == 404, f"Expected 404, got {status}"
    print(f"    OK: {status} — {body.get('error', '')}")

    # 4f. Invalid set_id for result
    print("  4f. Invalid set_id for result...")
    status, body = api("GET", "/api/campaign/result/nonexistent-set")
    assert status == 404, f"Expected 404, got {status}"
    print(f"    OK: {status} — {body.get('error', '')}")

    print("\n  SUCCESS: All failure paths validated!")


if __name__ == "__main__":
    test_health()
    set_id = test_evaluate_success()
    test_failure_paths()
    print("\n" + "=" * 50)
    print("ALL E2E TESTS PASSED")
    print("=" * 50)
