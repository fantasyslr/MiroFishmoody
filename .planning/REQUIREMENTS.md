# Requirements: MiroFishmoody v2.0

**Defined:** 2026-03-18
**Core Value:** 让每一次 campaign 在上线前都能得到数据化的推演对比，用 AI 推演替代"拍脑袋"决策

## v2.0 Requirements

### Critical Bug Fixes

- [x] **BUG-05**: 图片路径解析修复 — AudiencePanel/PairwiseJudge 对 API URL 调用 `os.path.exists()` 恒返回 False，视觉评估实为盲评
- [x] **BUG-06**: Both 模式 race condition 修复 — `Promise.all` 确保 Race + Evaluate POST 均完成后再导航，evaluateTaskId 必须在导航前存储
- [x] **BUG-07**: RunningPage 假动画替换为真实后端轮询 — 当前用假定时步骤动画，无真实进度信号

### Frontend Rewrite

- [x] **FE-01**: 表单状态持久化 — sessionStorage save/restore，导航不丢数据
- [x] **FE-02**: Winner-first 结果页布局 — EvaluateResultPage 顶部直接展示冠军方案，无需切换 tab
- [x] **FE-03**: 品类选择器显示人格预览 — 选择品类后侧边显示人格名称和数量
- [x] **FE-04**: 导出可靠性修复 — 测试并修复 html2canvas PDF 在 5 方案满载下的导出
- [x] **FE-05**: SplitPanel + LogBuffer 新 UI 组件 — 参考 MiroFish 双面板分割和日志缓冲模式
- [x] **FE-06**: 跨路径一致性 badge — Race winner vs Evaluate winner 矛盾时显示警示标记
- [x] **FE-07**: Step indicator 进度指示器 — 参考 MiroFish 步骤指示器模式，展示推演流程进度
- [x] **FE-08**: API 契约锁定 — `contracts.ts` 冻结 API 类型定义，防止重写过程中 contract drift

### Multi-Agent Backend

- [x] **MA-01**: 全局 LLM Semaphore — 从 ImageAnalyzer 层提升到 LLMClient 层，统一并发控制，防止 Bailian 429
- [ ] **MA-02**: AgentScore schema 统一 — 所有 agent 输出统一 schema，确保 CampaignScorer 不静默丢失新 agent 信号
- [ ] **MA-03**: PersonaRegistry 扩展 — moodyPlus 6→9 人格，colored_lenses 5→8 人格
- [ ] **MA-04**: MultiJudge 位置交替 ensemble — 每对方案多个独立 judge，强制轮换呈现顺序消除 position bias
- [ ] **MA-05**: Devil's advocate judge perspective — JUDGE_PERSPECTIVES 新增反面视角，标记异见投票
- [ ] **MA-06**: Cross-persona 争议分数 + badge — 人格评分标准差作为"争议"指标，前端展示 badge
- [ ] **MA-07**: ConsensusAgent 异常值检测 — `statistics.stdev` 检测评分离群值，标记可疑评分

### Tech Debt

- [ ] **TD-01**: threading.Lock 范围收窄 — 只在 dict ops 下加锁，不在 I/O 或 LLM 调用内
- [ ] **TD-02**: BrandStateEngine 渐进分解 — 先写表征测试（characterization tests），再逐步拆分 God class

## Future Requirements (v2.x)

- **FUTURE-01**: Persona confidence flagging — 二次 LLM 校验评分-理由一致性（成本翻倍，需先验证用户需求）
- **FUTURE-02**: Calibrated scoring against historical winners — 需历史结果数据管道，当前不具备
- **FUTURE-03**: AgentDiffusion 预权重集成 — 已有服务但 wiring 复杂度高，v2.0 先不接入

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vue.js / D3.js 迁移 | MiroFish 是 Vue 项目，但我们参考 UX 模式而非框架 |
| WebSocket 实时推送 | 2s 轮询对内部工具够用，WebSocket 增加部署复杂度 |
| Celery + Redis | <10 并发用户，ThreadPoolExecutor 够用 |
| LangChain / LangGraph | 现有 OpenAI SDK 直连够用，不需要框架抽象层 |
| 视频/GIF 素材推演 | LLM vision 按帧计费，成本和复杂度过高 |
| 移动端 App | Web 优先，内部工具不需要原生 App |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-05 | Phase 13 | Complete |
| BUG-06 | Phase 13 | Complete |
| BUG-07 | Phase 13 | Complete |
| FE-08 | Phase 13 | Complete |
| FE-01 | Phase 14 | Complete |
| FE-02 | Phase 14 | Complete |
| FE-03 | Phase 14 | Complete |
| FE-04 | Phase 14 | Complete |
| FE-05 | Phase 14 | Complete |
| FE-06 | Phase 14 | Complete |
| FE-07 | Phase 14 | Complete |
| MA-01 | Phase 15 | Complete |
| MA-02 | Phase 15 | Pending |
| MA-03 | Phase 16 | Pending |
| MA-04 | Phase 16 | Pending |
| MA-05 | Phase 16 | Pending |
| MA-06 | Phase 16 | Pending |
| MA-07 | Phase 16 | Pending |
| TD-01 | Phase 17 | Pending |
| TD-02 | Phase 17 | Pending |

**Coverage:**
- v2.0 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 — traceability mapped after roadmap creation*
