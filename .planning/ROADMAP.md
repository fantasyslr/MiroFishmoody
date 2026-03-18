# Roadmap: MiroFishmoody

## Milestones

- ✅ **v1.0 Campaign 推演引擎 MVP** - Phases 1-8 (shipped 2026-03-17)
- ✅ **v1.1 加固与增强** - Phases 9-12 (shipped 2026-03-17)
- ✅ **v2.0 大改造** - Phases 13-17 (shipped 2026-03-18)
- 🚧 **v2.1 部署修复 + 评审偏差修正** - Phases 18-20 (in progress)

## Phases

<details>
<summary>✅ v1.0 Campaign 推演引擎 MVP (Phases 1-8) - SHIPPED 2026-03-17</summary>

Phases 1-8 delivered the full MVP: user auth, campaign creation, image upload, Race path, Evaluate path, persona registry, multi-modal visual analysis, radar chart visualization, and both-path unified entry.

</details>

<details>
<summary>✅ v1.1 加固与增强 (Phases 9-12) - SHIPPED 2026-03-17</summary>

Phases 9-12 delivered: Both-mode cross-path navigation, Evaluate diagnostics panel wiring, thread safety + SQLite WAL hardening, bcrypt password hashing, PDF/image export, versioned iteration evaluation, and trend dashboard.

</details>

<details>
<summary>✅ v2.0 大改造 (Phases 13-17) - SHIPPED 2026-03-18</summary>

Phases 13-17 delivered: critical bug fixes + API contract lock, frontend rewrite (MiroFish pattern), global LLM semaphore + AgentScore schema, expanded persona pool + MultiJudge ensemble + devil's advocate + controversy badges, threading.Lock audit + BacktestEngine extraction.

</details>

### 🚧 v2.1 部署修复 + 评审偏差修正 (In Progress)

**Milestone Goal:** 修复生产入口 404，迁移到有状态部署平台（Railway），评审逻辑按 brief 类型切权重，建 benchmark 数据集 + 回归测试 runner

---

## Phases (v2.1)

- [ ] **Phase 18: Deployment Fix** - 修复生产 / 返回 404，迁移 Railway，双重健康检查确认部署正常
- [ ] **Phase 19: Brief-Type Weight Profiles** - brief_type 字段端到端贯穿，3 种评审权重配置，结果可追溯用了哪套权重
- [ ] **Phase 20: Benchmark Dataset + Regression Runner** - 10 组已标注 benchmark，回归 runner 按 brief 类型分别报告命中率

---

## Phase Details

### Phase 13: Critical Bug Fixes + API Contract Lock
**Goal**: 视觉评估结果可信（图片真实参与分析），Both 模式无 race condition，RunningPage 展示真实进度，API 契约已冻结以防重写期间 drift
**Depends on**: Phase 12 (v1.1 shipped)
**Requirements**: BUG-05, BUG-06, BUG-07, FE-08
**Success Criteria** (what must be TRUE):
  1. 发起 Evaluate 推演后，后台日志确认 AudiencePanel 和 PairwiseJudge 收到非空的 base64 图片数据（视觉分析不再盲评）
  2. Both 模式下同时发起 Race + Evaluate，两个 taskId 均在导航前写入 store，刷新后仍可轮询两条结果
  3. RunningPage 显示的进度百分比与后端 TaskManager 实际返回的 progress 字段一致，不再出现假定时步骤动画
  4. `contracts.ts` 文件存在并覆盖全部 Flask API endpoint 的请求/响应类型，`npm run build` 通过
**Plans**: 2 plans

Plans:
- [x] 13-01-PLAN.md — BUG-05 图片路径解析修复 — 提取 `resolve_image_path()` 工具函数，AudiencePanel + PairwiseJudge 统一调用
- [x] 13-02-PLAN.md — BUG-06 + BUG-07 + FE-08 — Both 模式 Promise.all fix、RunningPage 真实轮询、contracts.ts 生成

### Phase 14: Frontend Rewrite — Core Pages
**Goal**: 全部核心页面交互符合 MiroFish 参考模式：表单数据不丢失、进度展示真实、结果页冠军首屏可见、品类选择器显示人格预览、跨路径一致性可见
**Depends on**: Phase 13 (contracts.ts 必须先就位)
**Requirements**: FE-01, FE-02, FE-03, FE-04, FE-05, FE-06, FE-07
**Success Criteria** (what must be TRUE):
  1. 在 HomePage 填写方案信息后跳转至其他页面再返回，表单数据完整恢复（sessionStorage persist）
  2. EvaluateResultPage 顶部无需切换 tab 即可看到冠军方案名称和得分
  3. 选择品类后，侧边栏立即显示对应品类的人格名称列表和数量（moodyPlus 显示 6 个，colored_lenses 显示 5 个）
  4. Race winner 与 Evaluate winner 不一致时，结果页显示可见的警示 badge（不需要切 tab 才看到）
  5. 推演进行中，Step indicator 显示当前所处步骤（如"分析中"/"评审中"），与后端进度阶段对应
**Plans**: 4 plans

Plans:
- [x] 14-01-PLAN.md — FE-01 sessionStorage 表单持久化 + FE-03 品类人格预览
- [x] 14-02-PLAN.md — FE-02 Winner-first 结果布局 + FE-06 跨路径一致性 badge
- [x] 14-03-PLAN.md — FE-05 SplitPanel + LogBuffer 新 UI 组件 + FE-07 Step indicator
- [x] 14-04-PLAN.md — FE-04 导出可靠性修复（html2canvas 多页 PDF）

### Phase 15: Multi-Agent Foundation
**Goal**: 全局 LLM 并发上限已建立（防止 Bailian 429），所有 agent 输出共享统一 schema（防止新 agent 信号被 CampaignScorer 静默丢弃）
**Depends on**: Phase 13 (BUG-05 图片修复必须先完成，后端基础可信)
**Requirements**: MA-01, MA-02
**Success Criteria** (what must be TRUE):
  1. 5 方案 + 9 人格满载 Evaluate 推演中，LLM 并发调用数不超过 `MAX_LLM_CONCURRENT`（config.py 可配置），不出现 429 错误
  2. 新增一个 agent 类型并输出 `AgentScore` dataclass 后，CampaignScorer 自动将其纳入最终聚合（无需手工 wiring）
**Plans**: 2 plans

Plans:
- [x] 15-01-PLAN.md — MA-01 全局 LLMSemaphore 从 ImageAnalyzer 层提升至 LLMClient 层
- [x] 15-02-PLAN.md — MA-02 AgentScore schema dataclass + CampaignScorer 统一注册机制

### Phase 16: Multi-Agent Evaluation Enhancement
**Goal**: 评审团规模扩大、位置偏差已消除、反面视角已引入、争议分数可见于前端
**Depends on**: Phase 15 (全局 Semaphore 和 AgentScore schema 必须先就位)
**Requirements**: MA-03, MA-04, MA-05, MA-06, MA-07
**Success Criteria** (what must be TRUE):
  1. moodyPlus 品类 Evaluate 推演调用 9 个人格（PersonaRegistry 扩展后），colored_lenses 调用 8 个
  2. MultiJudge ensemble 中每对方案的 judge 调用有一半收到 (A,B) 顺序、一半收到 (B,A) 顺序（position alternation 可在日志中验证）
  3. devil's advocate judge 的异见投票在结果数据中独立标记（`dissent: true` 字段）
  4. 人格间评分标准差 >= 阈值的方案，EvaluateResultPage 展示"争议"badge
  5. ConsensusAgent 检测到离群评分时，结果 JSON 中对应人格评分带有 `suspect: true` 标记
**Plans**: 3 plans

Plans:
- [x] 16-01-PLAN.md — MA-03 PersonaRegistry 扩展（moodyPlus 6→9, colored_lenses 5→8）+ MA-04 MultiJudge 位置交替 ensemble
- [x] 16-02-PLAN.md — MA-07 ConsensusAgent stdev 离群值检测 + EvaluationOrchestrator 接入
- [x] 16-03-PLAN.md — MA-05 Devil's advocate judge + MA-06 争议 badge 前端（dissent + suspect 双信号）

### Phase 17: Tech Debt Paydown
**Goal**: threading.Lock 范围精确（I/O 和 LLM 调用不在锁内），BrandStateEngine 有表征测试覆盖且 BacktestEngine 已提取为独立类
**Depends on**: Phase 16 (所有 v2.0 功能已稳定，不与重构同期进行)
**Requirements**: TD-01, TD-02
**Success Criteria** (what must be TRUE):
  1. `_evaluation_store` 的所有 lock 作用域仅覆盖 dict 读写操作，LLM 调用和文件 I/O 不在 lock 内（代码审查可验证）
  2. BrandStateEngine 的 characterization tests 覆盖现有全部公开方法的输入输出，`pytest` 绿灯
  3. BacktestEngine 已从 BrandStateEngine 提取为独立文件，原 BrandStateEngine 引用该类，现有测试不变
**Plans**: 2 plans

Plans:
- [x] 17-01-PLAN.md — TD-01 threading.Lock 范围收窄（注释审计 + EvaluationOrchestrator 分步分离）
- [x] 17-02-PLAN.md — TD-02 BrandStateEngine characterization tests + BacktestEngine 提取（strangler fig）

### Phase 18: Deployment Fix
**Goal**: 生产环境入口 / 正常返回页面，Railway 部署稳定，SQLite 和上传文件在容器重启后持久化，健康检查双重验证通过
**Depends on**: Phase 17 (v2.0 shipped)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. 访问 Railway 部署 URL 的 `/` 返回 HTTP 200 并渲染前端页面，不再出现 404
  2. 发起一次 Evaluate 推演并等待完成，重启 Railway service 后再访问推演结果页，结果仍然可见（SQLite + 上传图片持久化确认）
  3. Dockerfile 构建阶段若 `frontend/dist/index.html` 不存在则构建失败，不将空白容器推送到生产
  4. `/api/health` 返回 `uploads_writable: ok` 且 `/` 返回 200，两个检查同时通过
**Plans**: 2 plans

Plans:
- [ ] 18-01-PLAN.md — Flask /api/health 路由 + 503 fallback + Dockerfile 构建断言 (DEPLOY-01, DEPLOY-02, DEPLOY-04)
- [ ] 18-02-PLAN.md — Railway gunicorn PORT 绑定 + railway.json + Dashboard volume/env 配置 (DEPLOY-03, DEPLOY-04)

### Phase 19: Brief-Type Weight Profiles
**Goal**: 用户在发起推演时必须选择 brief 类型（品牌传播/达人种草/转化拉新），评审引擎按选定类型加载对应维度权重，每条历史结果可追溯当时用了哪套权重
**Depends on**: Phase 18 (生产部署可用，才能做用户行为验证)
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):
  1. 推演发起表单包含 brief 类型必选字段（品牌传播/达人种草/转化拉新），未选择时提交被阻止并显示提示
  2. 选择"品牌传播"发起 Evaluate 推演，结果 JSON 中的维度权重与 `brief_weights.py` 的 brand 配置一致（可用日志或结果文件验证）
  3. 选择"转化拉新"发起推演，`conversion_readiness` 维度权重显著高于"品牌传播"推演的同维度权重（权重差异可测量）
  4. 每条 EvaluationResult 记录包含 `weight_profile_version` 字段，历史结果重新打开后可看到当时使用的权重版本
  5. 传入未知 brief_type 字符串时，API 返回 HTTP 400 而非 500 内部错误
**Plans**: TBD

Plans:
- [ ] 19-01-PLAN.md — EVAL-01 + EVAL-03: BriefType enum + brief_weights.py 权重配置文件
- [ ] 19-02-PLAN.md — EVAL-04 + EVAL-05: CampaignScorer 按 brief_type 加载权重 + EvaluationResult 记录 weight_profile_version
- [ ] 19-03-PLAN.md — EVAL-02: 前端表单 brief_type 选择器 + API 边界 400 校验

### Phase 20: Benchmark Dataset + Regression Runner
**Goal**: 品牌团队有一套已标注 benchmark 数据集，可用 CLI 命令按 brief 类型分别测量评审引擎命中率，future 权重调整可快速回归验证
**Depends on**: Phase 19 (权重配置必须先稳定，标注数据才有意义)
**Requirements**: BENCH-01, BENCH-02, BENCH-03
**Success Criteria** (what must be TRUE):
  1. `backend/tests/fixtures/benchmark/` 目录中存在至少 10 组已标注 campaign JSON，每组包含 brief_type 标签、预期冠军和标注理由
  2. 运行 `python benchmark/run.py` 输出 `brand_accuracy`、`seeding_accuracy`、`conversion_accuracy` 三个独立命中率，不只报告单一聚合数字
  3. benchmark runner 使用 mock LLMClient（不调用真实 Bailian API），可在 CI 环境中确定性回放
**Plans**: TBD

Plans:
- [ ] 20-01-PLAN.md — BENCH-01 + BENCH-02: Benchmark schema 设计 + 10 组种子数据标注
- [ ] 20-02-PLAN.md — BENCH-03: 回归测试 runner（mock LLMClient + 命中率报告）

---

## Progress

**Execution Order:** 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-8. MVP | v1.0 | 12/12 | Complete | 2026-03-17 |
| 9-12. 加固 | v1.1 | 8/8 | Complete | 2026-03-17 |
| 13. Bug Fixes + Contract Lock | v2.0 | 2/2 | Complete | 2026-03-18 |
| 14. Frontend Rewrite | v2.0 | 4/4 | Complete | 2026-03-18 |
| 15. Multi-Agent Foundation | v2.0 | 2/2 | Complete | 2026-03-18 |
| 16. Multi-Agent Enhancement | v2.0 | 3/3 | Complete | 2026-03-18 |
| 17. Tech Debt | v2.0 | 2/2 | Complete | 2026-03-18 |
| 18. Deployment Fix | v2.1 | 0/2 | Not started | - |
| 19. Brief-Type Weight Profiles | v2.1 | 0/3 | Not started | - |
| 20. Benchmark Dataset + Runner | v2.1 | 0/2 | Not started | - |
