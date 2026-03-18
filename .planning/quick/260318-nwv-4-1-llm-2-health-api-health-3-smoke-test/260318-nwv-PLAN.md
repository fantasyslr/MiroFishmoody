---
phase: quick
plan: 260318-nwv
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/__init__.py
  - backend/tests/test_smoke.py
  - backend/tests/e2e_smoke.py
  - backend/pyproject.toml
autonomous: true
requirements: [NWV-1, NWV-2, NWV-3, NWV-4]

must_haves:
  truths:
    - "GET /api/health 返回 llm 字段，值为 ok 或包含 error 描述"
    - "test_smoke.py 调用 /api/health 而非 /health，pytest 通过"
    - "e2e_smoke.py test_health() 调用 /api/health"
    - "pyproject.toml 包含 gunicorn 依赖，uv sync 可安装"
  artifacts:
    - path: "backend/app/__init__.py"
      provides: "/api/health 路由含 LLM 探测"
      contains: "llm"
    - path: "backend/tests/test_smoke.py"
      provides: "TestHealth 使用正确路由"
      contains: "/api/health"
    - path: "backend/tests/e2e_smoke.py"
      provides: "smoke test 使用正确路由"
      contains: "/api/health"
    - path: "backend/pyproject.toml"
      provides: "gunicorn 列在 dependencies"
      contains: "gunicorn"
  key_links:
    - from: "backend/app/__init__.py"
      to: "openai.OpenAI (Bailian endpoint)"
      via: "LLMClient 或 openai SDK 直调"
      pattern: "llm.*ok|openai"
---

<objective>
修复众测发现的 4 个问题：
1. /api/health 健康检查增加 LLM 连通性探测（用 openai SDK 发一条极短的 completion 请求）
2. test_smoke.py TestHealth 把 /health 改为 /api/health
3. e2e_smoke.py test_health() 把 /health 改为 /api/health
4. pyproject.toml 补 gunicorn 依赖

Purpose: Railway 生产环境健康检查覆盖 LLM 链路；smoke test 路径与实际路由对齐；gunicorn 生产启动不缺包。
Output: 4 个文件修改，pytest 通过。
</objective>

<execution_context>
@/Users/slr/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/slr/MiroFishmoody/.planning/STATE.md
@/Users/slr/MiroFishmoody/backend/app/__init__.py
@/Users/slr/MiroFishmoody/backend/tests/test_smoke.py
@/Users/slr/MiroFishmoody/backend/tests/e2e_smoke.py
@/Users/slr/MiroFishmoody/backend/pyproject.toml

<interfaces>
<!-- 现有 /api/health 路由骨架（backend/app/__init__.py L75-114） -->
@app.route('/api/health')
def health():
    checks = {"service": "Campaign Ranker Engine"}
    # ... db check, uploads_writable check, disk check ...
    overall = "ok" if all(...) else "degraded"
    return {"status": overall, **checks}

<!-- LLM 客户端引用（backend/app/services/） -->
<!-- 项目用 openai SDK + Bailian endpoint，Config.OPENAI_API_KEY / Config.OPENAI_BASE_URL -->
from app.config import Config
from openai import OpenAI
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: /api/health 增加 LLM 连通性探测</name>
  <files>backend/app/__init__.py</files>
  <action>
在 health() 函数内，现有 disk check 之后、return 之前，新增 LLM 探测块：

```python
# LLM connectivity
try:
    from openai import OpenAI as _OpenAI
    _client = _OpenAI(
        api_key=Config.OPENAI_API_KEY,
        base_url=Config.OPENAI_BASE_URL,
    )
    _client.chat.completions.create(
        model=Config.OPENAI_MODEL,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1,
        timeout=10,
    )
    checks["llm"] = "ok"
except Exception as _e:
    checks["llm"] = f"error: {_e}"
```

overall 判断行不需要改——llm 值为 "ok" 时通过，为 "error: ..." 时 overall 变 "degraded"（与现有 db/uploads 逻辑一致，non-"ok" string → not all）。

注意：import 放在函数体内（lazy import），保持与现有 sqlite3 导入风格一致。Config.OPENAI_MODEL 如不存在，用字面量 "qwen-plus" 兜底：
```python
model=getattr(Config, 'OPENAI_MODEL', 'qwen-plus'),
```
  </action>
  <verify>
    <automated>cd /Users/slr/MiroFishmoody/backend && uv run pytest tests/test_smoke.py::TestHealth -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>pytest TestHealth 通过；health 路由响应 JSON 包含 "llm" key</done>
</task>

<task type="auto">
  <name>Task 2: 对齐路由路径 + 补 gunicorn 依赖</name>
  <files>backend/tests/test_smoke.py, backend/tests/e2e_smoke.py, backend/pyproject.toml</files>
  <action>
**test_smoke.py（L170）：**
将 `client.get('/health')` 改为 `client.get('/api/health')`。
仅改这一处，不动其他内容。

**e2e_smoke.py（L33）：**
将 `api("GET", "/health")` 改为 `api("GET", "/api/health")`。
仅改这一处。

**pyproject.toml：**
在 `dependencies` 列表末尾追加：
```toml
"gunicorn>=21.0.0",
```
放在 `pydantic>=2.0.0` 行之后，保持缩进和格式一致。
  </action>
  <verify>
    <automated>cd /Users/slr/MiroFishmoody/backend && uv run pytest tests/test_smoke.py::TestHealth -x -q 2>&1 | tail -5 && grep 'gunicorn' pyproject.toml && grep '/api/health' tests/test_smoke.py tests/e2e_smoke.py</automated>
  </verify>
  <done>
    - test_smoke.py TestHealth 调用 /api/health，pytest 通过
    - e2e_smoke.py test_health() 调用 /api/health
    - pyproject.toml 包含 gunicorn>=21.0.0
  </done>
</task>

</tasks>

<verification>
cd /Users/slr/MiroFishmoody/backend && uv run pytest tests/test_smoke.py -x -q 2>&1 | tail -10
</verification>

<success_criteria>
- pytest tests/test_smoke.py 全部通过（包含 TestHealth）
- /api/health 响应体含 "llm" 字段
- e2e_smoke.py 不再引用 /health（仅 /api/health）
- pyproject.toml dependencies 含 gunicorn
</success_criteria>

<output>
完成后无需创建 SUMMARY.md（quick plan）。
</output>
