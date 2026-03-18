---
phase: 17-tech-debt-paydown
verified: 2026-03-18T05:30:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "现有 pytest 测试仍然全绿"
    status: failed
    reason: "BacktestEngine 提取后，test_pr5_scenario.py::TestInjectCompetitorDelta::test_replay_and_backtest_share_helper 新增失败。该测试用 inspect.getsource 断言 BrandStateEngine.backtest() 方法体内包含 '_inject_competitor_delta'，委托重写后方法体只有 3 行委托代码，断言失败。"
    artifacts:
      - path: "backend/app/services/brand_state_engine.py"
        issue: "BrandStateEngine.backtest() 改为委托给 BacktestEngine，方法体不再含 _inject_competitor_delta"
      - path: "backend/tests/test_pr5_scenario.py"
        issue: "line 279: assert '_inject_competitor_delta' in bt_source — 断言基于方法体源码内容检查，被委托重写破坏"
    missing:
      - "更新 test_pr5_scenario.py::test_replay_and_backtest_share_helper，改为断言 BacktestEngine.backtest() 源码包含 _inject_competitor_delta（而不是 BrandStateEngine.backtest()），或直接测试委托行为而不检查源码内容"
---

# Phase 17: tech-debt-paydown Verification Report

**Phase Goal:** threading.Lock 范围精确（I/O 和 LLM 调用不在锁内），BrandStateEngine 有表征测试覆盖且 BacktestEngine 已提取为独立类
**Verified:** 2026-03-18T05:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_evaluation_store` 的所有 lock 作用域仅覆盖 dict 读写操作，没有任何 LLM 调用或 I/O 在 lock 内 | VERIFIED | campaign.py 7 处 `with _store_lock:` 块内均只有 dict `__contains__`, `.get()`, `.pop()`, 赋值操作；`_load_result` (I/O) 在 lock 外调用 |
| 2 | EvaluationOrchestrator 写入 evaluation_store 的 lock 作用域与 save_result_fn 调用分离 | VERIFIED | evaluation_orchestrator.py lines 152-162: dict write 在 `with self.store_lock:` 内，`save_result_fn` 调用在 lock 块之后，有 TD-01 step 1/step 2 注释明确分隔 |
| 3 | 现有 pytest 测试仍然全绿 | FAILED | `test_pr5_scenario.py::TestInjectCompetitorDelta::test_replay_and_backtest_share_helper` 新失败：inspect 检查 BrandStateEngine.backtest() 源码时断言 `_inject_competitor_delta` 存在，委托重写后断言失败 |
| 4 | BrandStateEngine 全部公开方法有 characterization tests，pytest 绿灯 | VERIFIED | 7 个 characterization tests 全部 PASSED（test_brand_state_characterization.py） |
| 5 | BacktestEngine 是独立文件，包含从 BrandStateEngine 提取的 backtest() 方法 | VERIFIED | `backend/app/services/backtest_engine.py` 存在，含 `BacktestEngine` 类和完整 `backtest()` 实现（172 行，含留一法回测完整逻辑） |

**Score:** 4/5 truths verified

---

## Required Artifacts

### Plan 01 — TD-01 Lock Scope

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/campaign.py` | 精确的 `_store_lock` 作用域（只包裹 dict 读写） | VERIFIED | 7 处 lock 块均只含 dict 操作；7 处 `TD-01: dict-only` 注释已添加 |
| `backend/app/services/evaluation_orchestrator.py` | store_lock 只在 dict 写操作那一行使用 | VERIFIED | lines 152-162 实现 step 1（dict under lock）和 step 2（file I/O outside lock）清晰分离 |

### Plan 02 — TD-02 BacktestEngine

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_brand_state_characterization.py` | BrandStateEngine 所有公开方法的 characterization tests | VERIFIED | 7 tests，7 PASSED，覆盖所有公开方法：`build_state_from_signals`, `compute_intervention_impact`, `replay_history`, `predict_impact`, `cognition_probability_board`, `simulate_scenario`, `backtest` |
| `backend/app/services/backtest_engine.py` | BacktestEngine 独立类，含 backtest() 方法 | VERIFIED | 文件存在（6607 bytes），`BacktestEngine` 类完整，`backtest()` 实现 172 行逻辑 |
| `backend/app/services/brand_state_engine.py` | BrandStateEngine.backtest() 委托给 BacktestEngine | VERIFIED | lines 1137-1148：lazy import + 3 行委托 `bt = BacktestEngine(self.store, self); return bt.backtest(...)` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `evaluation_orchestrator.py:run()` | `_evaluation_store dict` | `with self.store_lock` | VERIFIED | line 155: `with self.store_lock:` 包裹 dict 赋值；`save_result_fn` 在 lock 外 line 162 |
| `brand_state_engine.py:BrandStateEngine.backtest()` | `backtest_engine.py:BacktestEngine.backtest()` | lazy import + delegation | VERIFIED | `from .backtest_engine import BacktestEngine` at line 1146, delegation at line 1148 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TD-01 | 17-01-PLAN.md | threading.Lock 范围收窄 — 只在 dict ops 下加锁，不在 I/O 或 LLM 调用内 | SATISFIED | campaign.py 7 处注释验证 + evaluation_orchestrator.py step 分离注释验证；`grep -c "TD-01: dict-only"` = 8 |
| TD-02 | 17-02-PLAN.md | BrandStateEngine 渐进分解 — 先写表征测试，再拆分 God class | PARTIALLY SATISFIED | characterization tests 全绿；BacktestEngine 提取完成；但 test_pr5_scenario.py 中基于源码内容检查的旧测试因重构而失败 |

REQUIREMENTS.md 中 TD-01 和 TD-02 均映射到 Phase 17，无孤立需求。

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/tests/test_pr5_scenario.py` | 278-279 | `inspect.getsource` 断言方法体内容 — 脆性测试，重构必然破坏 | Warning | 委托提取后断言失败，测试需更新以反映新的委托架构 |

---

## Test Results Summary

```
tests/test_brand_state_characterization.py: 7 passed
tests/test_brand_state.py + tests/test_brandiction.py: 64 passed
Full suite (excl. test_phase56.py): 646 passed, 10 skipped, 2 failed
  - FAILED tests/test_pr5_scenario.py::TestInjectCompetitorDelta::test_replay_and_backtest_share_helper
    (NEW FAILURE — introduced by BacktestEngine strangler-fig extraction)
  - FAILED tests/test_smoke.py::TestEvaluationFlow::test_submit_and_check_status
    (PRE-EXISTING — LLM_API_KEY not set in test environment, unrelated to Phase 17)
```

---

## Gaps Summary

Phase 17 的核心交付物（lock 注释、characterization tests、BacktestEngine 提取）均已实现且可验证。

唯一的 gap 是 `test_pr5_scenario.py` 中一个预先存在的脆性测试因 strangler-fig 重构而失败。该测试用 `inspect.getsource(BrandStateEngine.backtest)` 直接检查方法体源码内容，这是一种与实现紧耦合的测试方式——任何委托/提取重构都会破坏它。

**修复方向（最小改动）：**

将 `test_replay_and_backtest_share_helper` 中的断言改为检查 `BacktestEngine.backtest()` 源码，或改为行为测试（用空 store 调用并断言返回结构），而不是检查方法体字符串内容。

---

_Verified: 2026-03-18T05:30:00Z_
_Verifier: Claude (gsd-verifier)_
