# Roadmap: MiroFishmoody

## Milestones

- v1.0 Campaign 推演引擎 MVP - Phases 1-8 (shipped 2026-03-17)
- v1.1 加固与增强 - Phases 9-12 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 Campaign 推演引擎 MVP (Phases 1-8) - SHIPPED 2026-03-17</summary>

- [x] **Phase 1: Image Pipeline Fix** - 修复图片路径解析 bug 和高分辨率图片溢出问题
- [x] **Phase 2: PersonaRegistry Service** - 将硬编码人格数组提取为独立配置化服务
- [x] **Phase 3: Category Persona Config** - 按品类配置独立评审人格集并自动加载
- [x] **Phase 4: Concurrent Image Analysis** - 并行图片分析 + LLM 速率控制
- [x] **Phase 5: Evaluate Quality** - PairwiseJudge 去偏 + 视觉诊断结构化
- [x] **Phase 6: Evaluate Frontend** - Evaluate 推演前端页面（发起、进度、结果）
- [x] **Phase 7: Unified Entry** - 统一推演入口（模式选择 + 统一表单）
- [x] **Phase 8: Results Enhancement** - 多方案并排对比 + 多维可视化 + 历史基线

</details>

### v1.1 加固与增强 (In Progress)

**Milestone Goal:** 修复 v1.0 遗留技术债，补全 Both 模式和 Evaluate 诊断，新增结果导出、迭代推演和趋势 Dashboard

- [ ] **Phase 9: Bug Fixes** - Both 模式跨页导航 + Evaluate 诊断面板数据接入
- [ ] **Phase 10: Stability & Security** - 线程安全 + SQLite WAL + 密码哈希 bcrypt
- [ ] **Phase 11: Export** - 推演结果导出 PDF 和图片
- [ ] **Phase 12: Iteration & Analytics** - 方案迭代推演版本对比 + 推演趋势 Dashboard

## Phase Details

<details>
<summary>v1.0 Phase Details (Phases 1-8)</summary>

### Phase 1: Image Pipeline Fix
**Goal**: 所有推演路径的图片处理正确工作，不再静默丢弃图片
**Depends on**: Nothing (first phase)
**Requirements**: BUG-01, BUG-02
**Success Criteria** (what must be TRUE):
  1. Evaluate 推演使用上传的图片 URL 时，图片被正确解析并送入 LLM 视觉分析，不再静默跳过
  2. 高分辨率图片（>1024px）在 base64 编码前被自动缩放，不触发 LLM token 限制错误
  3. 使用 `resolve_image_path()` 的统一路径解析逻辑，AudiencePanel 和 PairwiseJudge 不再直接调用 `os.path.exists()`
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md

### Phase 2: PersonaRegistry Service
**Goal**: 人格配置从硬编码提取为独立服务，支持 schema 校验的预设模板
**Depends on**: Nothing
**Requirements**: PERS-01, PERS-03
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md

### Phase 3: Category Persona Config
**Goal**: 透明片和彩片使用不同的评审人格集，系统根据品类自动加载
**Depends on**: Phase 2
**Requirements**: PERS-02, UNIF-03
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md
- [x] 03-02-PLAN.md

### Phase 4: Concurrent Image Analysis
**Goal**: 多张图片并行分析，单次推演时间显著缩短
**Depends on**: Phase 1
**Requirements**: PERF-01, PERF-02
**Plans**: 1 plan

Plans:
- [x] 04-01-PLAN.md

### Phase 5: Evaluate Quality
**Goal**: Evaluate 推演结果更可靠——去除位置偏差，诊断建议结构化
**Depends on**: Phase 1, Phase 2
**Requirements**: QUAL-01, QUAL-02
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md

### Phase 6: Evaluate Frontend
**Goal**: 用户可在前端完整使用 Evaluate 推演路径（发起、跟踪进度、查看结果）
**Depends on**: Phase 1, Phase 5
**Requirements**: EVAL-01, EVAL-02, EVAL-03
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md
- [x] 06-02-PLAN.md

### Phase 7: Unified Entry
**Goal**: 用户从统一入口选择推演模式并提交方案，无需理解后端 API 差异
**Depends on**: Phase 6
**Requirements**: UNIF-01, UNIF-02
**Plans**: 1 plan

Plans:
- [x] 07-01-PLAN.md

### Phase 8: Results Enhancement
**Goal**: 推演结果页提供多方案并排对比、多维可视化和历史基线定位
**Depends on**: Phase 6, Phase 7
**Requirements**: RES-01, RES-02, RES-03, QUAL-03
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md
- [x] 08-02-PLAN.md

</details>

### Phase 9: Bug Fixes
**Goal**: Both 模式完整可用，Evaluate 结果页诊断面板显示真实数据
**Depends on**: Phase 8 (v1.0 complete)
**Requirements**: BUG-03, BUG-04
**Success Criteria** (what must be TRUE):
  1. 用户完成 Both 模式推演后，ResultPage 显示可点击的链接跳转到 EvaluateResultPage 查看深度评审结果
  2. Evaluate 结果页的诊断面板（DiagnosticsPanel）展示每个 campaign 方案的视觉诊断数据（issues + recommendations），不再为空
  3. Evaluate 管线在推演过程中产出图片诊断数据，并正确传递到前端 diagnosticsMap
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md — Both 模式 getBothModeState 消费 + 跨页导航链接
- [ ] 09-02-PLAN.md — Evaluate 管线接入图片诊断产出 + diagnosticsMap 数据传递

### Phase 10: Stability & Security
**Goal**: 并发访问安全，数据库不因并发锁阻塞，密码不以明文存储
**Depends on**: Phase 9 (bug fixes first)
**Requirements**: STAB-01, STAB-02, SEC-01
**Success Criteria** (what must be TRUE):
  1. 多个用户同时发起 Evaluate 推演时，_evaluation_store 的读写不会产生数据竞争或丢失
  2. 并发数据库写入（如多个推演同时保存结果）不会触发 SQLite "database is locked" 错误
  3. 用户密码以 bcrypt 哈希存储，数据库中不存在明文密码
  4. 已有明文密码在首次登录时自动迁移为 bcrypt 哈希
**Plans**: 2 plans

Plans:
- [ ] 10-01-PLAN.md — _evaluation_store threading.Lock + SQLite WAL 模式 + busy_timeout
- [ ] 10-02-PLAN.md — 密码 bcrypt 哈希（加载时哈希 + bcrypt 验证）

### Phase 11: Export
**Goal**: 用户可将推演结果导出为 PDF 报告或图片，方便分享和存档
**Depends on**: Phase 9 (diagnostics data must be real before exporting)
**Requirements**: EXP-01, EXP-02
**Success Criteria** (what must be TRUE):
  1. 用户在结果页点击"导出 PDF"按钮，下载包含方案对比、评分雷达图、诊断建议的 PDF 报告
  2. 用户在结果页点击"导出图片"按钮，下载结果卡片的 PNG/JPG 截图，适合发送到微信/钉钉
  3. 导出内容包含所有可视化组件（雷达图、百分位条、诊断面板），不出现空白或缺失
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md — html2canvas + jsPDF 安装 + exportUtils 工具 + ResultPage 导出按钮
- [ ] 11-02-PLAN.md — EvaluateResultPage 导出按钮 + 导出质量人工验证

### Phase 12: Iteration & Analytics
**Goal**: 用户可对同一 campaign 迭代推演并对比版本改善，跨 campaign 追踪推演趋势
**Depends on**: Phase 9 (complete result data), Phase 10 (stable storage)
**Requirements**: ITER-01, ANAL-01
**Success Criteria** (what must be TRUE):
  1. 用户修改 campaign 方案后重新推演，系统自动关联为同一 campaign 的新版本
  2. 版本对比视图并排展示两个版本的评分变化，标注改善和退步的维度
  3. Dashboard 页面展示跨 campaign 的推演分数趋势图（时间轴 x 分数 y）
  4. Dashboard 支持按品类筛选，分别查看透明片和彩片的推演趋势
**Plans**: 2 plans

Plans:
- [ ] 12-01: Campaign 版本关联模型 + 迭代推演 API + 版本对比视图
- [ ] 12-02: 推演趋势 Dashboard 页面（趋势图 + 品类筛选）

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10 -> 11 -> 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Image Pipeline Fix | v1.0 | 2/2 | Complete | 2026-03-17 |
| 2. PersonaRegistry Service | v1.0 | 1/1 | Complete | 2026-03-17 |
| 3. Category Persona Config | v1.0 | 2/2 | Complete | 2026-03-17 |
| 4. Concurrent Image Analysis | v1.0 | 1/1 | Complete | 2026-03-17 |
| 5. Evaluate Quality | v1.0 | 1/1 | Complete | 2026-03-17 |
| 6. Evaluate Frontend | v1.0 | 2/2 | Complete | 2026-03-17 |
| 7. Unified Entry | v1.0 | 1/1 | Complete | 2026-03-17 |
| 8. Results Enhancement | v1.0 | 2/2 | Complete | 2026-03-17 |
| 9. Bug Fixes | 2/2 | Complete   | 2026-03-17 | - |
| 10. Stability & Security | 2/2 | Complete    | 2026-03-17 | - |
| 11. Export | v1.1 | 0/2 | Not started | - |
| 12. Iteration & Analytics | v1.1 | 0/2 | Not started | - |
