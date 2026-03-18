# Requirements: MiroFishmoody v2.1

**Defined:** 2026-03-18
**Core Value:** 让每一次 campaign 在上线前都能得到数据化的推演对比，用 AI 推演替代"拍脑袋"决策

## v2.1 Requirements

### Deployment Fix

- [ ] **DEPLOY-01**: 生产入口 / 返回正常页面而非 404 — `__init__.py` 静态路由静默失败时返回 503 + 日志告警
- [ ] **DEPLOY-02**: Dockerfile 构建断言 — build 阶段验证 `frontend/dist/index.html` 存在，不存在则构建失败
- [ ] **DEPLOY-03**: Railway 部署配置 — Dockerfile 原生部署，volume 挂载 `/app/backend/uploads`，env var 迁移
- [ ] **DEPLOY-04**: Railway 健康检查 — `/api/health` 200 + 前端 / 200 双重验证

### Brief-Type Evaluation

- [ ] **EVAL-01**: Campaign 模型新增 `brief_type` 字段 — BriefType enum（brand/seeding/conversion），API 层接收并传导
- [ ] **EVAL-02**: 前端表单新增 brief_type 选择器 — 品牌传播 / 达人种草 / 转化拉新，必选字段
- [ ] **EVAL-03**: WeightProfile 权重配置 — JSON 配置文件，3 种 brief 类型各有 6 维权重，env var 可覆盖
- [ ] **EVAL-04**: CampaignScorer 按 brief_type 加载权重 — 评分聚合时使用对应 brief 的维度权重而非平权
- [ ] **EVAL-05**: EvaluationResult 记录 weight_profile_version — 结果可追溯用了哪套权重

### Benchmark & Regression

- [ ] **BENCH-01**: Benchmark 数据集 schema — 输入（campaign set JSON）+ 预期冠军 + 标注置信度 + 理由
- [ ] **BENCH-02**: 种子数据集 — 至少 10 组已标注 campaign（品牌/种草/转化各 3-4 组）
- [ ] **BENCH-03**: 回归测试 runner — mock LLMClient，确定性回放，输出命中率报告

## Future Requirements (v2.x)

- **EVAL-06**: visual_diagnostics 接入评分维度（当前仅展示不参与评分）
- **EVAL-07**: LLM-based brief type 自动推断（当前要求用户手动选择）
- **BENCH-04**: 扩展 benchmark 到 30+ 样本后做权重自动优化

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vercel 部署修复 | 架构不兼容（长进程+SQLite+磁盘），已决定迁移 Railway |
| ML 权重自动优化 | 数据量不够（<200 样本），先用专家设计权重 |
| 实时 A/B 测试框架 | 内部工具规模不需要 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | Phase 18 | Pending |
| DEPLOY-02 | Phase 18 | Pending |
| DEPLOY-03 | Phase 18 | Pending |
| DEPLOY-04 | Phase 18 | Pending |
| EVAL-01 | Phase 19 | Pending |
| EVAL-02 | Phase 19 | Pending |
| EVAL-03 | Phase 19 | Pending |
| EVAL-04 | Phase 19 | Pending |
| EVAL-05 | Phase 19 | Pending |
| BENCH-01 | Phase 20 | Pending |
| BENCH-02 | Phase 20 | Pending |
| BENCH-03 | Phase 20 | Pending |

**Coverage:**
- v2.1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 — Phase mapping complete (Phases 18-20)*
