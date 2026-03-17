# Roadmap: MiroFishmoody

## Overview

MiroFishmoody 的 v1 目标是将已有的 Evaluate 后端能力完整暴露到前端，同时修复图片管道 bug、提升并发性能、按品类配置人格画像。路线从基础修复出发，逐层构建人格配置、并发性能、评审质量，最终交付统一推演入口和增强结果视图。8 个 phase 按依赖关系排列，每个 phase 交付一个可验证的完整能力。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Image Pipeline Fix** - 修复图片路径解析 bug 和高分辨率图片溢出问题
- [ ] **Phase 2: PersonaRegistry Service** - 将硬编码人格数组提取为独立配置化服务
- [ ] **Phase 3: Category Persona Config** - 按品类配置独立评审人格集并自动加载
- [ ] **Phase 4: Concurrent Image Analysis** - 并行图片分析 + LLM 速率控制
- [ ] **Phase 5: Evaluate Quality** - PairwiseJudge 去偏 + 视觉诊断结构化
- [ ] **Phase 6: Evaluate Frontend** - Evaluate 推演前端页面（发起、进度、结果）
- [ ] **Phase 7: Unified Entry** - 统一推演入口（模式选择 + 统一表单）
- [ ] **Phase 8: Results Enhancement** - 多方案并排对比 + 多维可视化 + 历史基线

## Phase Details

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
- [ ] 01-01-PLAN.md — 创建共享 image_helpers 工具模块（URL 解析 + 自动缩放 + base64 编码）
- [ ] 01-02-PLAN.md — 将三个服务的图片处理逻辑迁移到共享工具 + 集成测试

### Phase 2: PersonaRegistry Service
**Goal**: 人格配置从硬编码提取为独立服务，支持 schema 校验的预设模板
**Depends on**: Nothing (independent of Phase 1, but ordered for clarity)
**Requirements**: PERS-01, PERS-03
**Success Criteria** (what must be TRUE):
  1. PersonaRegistry 作为独立服务存在，AudiencePanel 通过 registry 获取人格列表而非硬编码数组
  2. 人格配置使用 JSON 预设模板，每个人格通过 schema 校验（包含 name、role、evaluation_focus 等必需字段）
  3. 无效人格配置（缺少必需字段或格式错误）被拒绝并返回明确错误信息
**Plans**: 1 plan

Plans:
- [ ] 02-01-PLAN.md — 创建 PersonaRegistry 服务 + JSON 预设 + schema 校验 + 接入 AudiencePanel

### Phase 3: Category Persona Config
**Goal**: 透明片和彩片使用不同的评审人格集，系统根据品类自动加载
**Depends on**: Phase 2
**Requirements**: PERS-02, UNIF-03
**Success Criteria** (what must be TRUE):
  1. moodyPlus（透明片）和 colored_lenses（彩片）各有独立的评审人格预设集
  2. 用户选择品类后，系统自动从 PersonaRegistry 加载对应品类的人格集，无需手动选择人格
  3. API 层支持按品类参数返回对应人格配置
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — 创建品类人格预设 JSON + PersonaRegistry 品类加载支持
- [ ] 03-02-PLAN.md — Evaluate/Race API 接入 category 参数，自动加载品类人格

### Phase 4: Concurrent Image Analysis
**Goal**: 多张图片并行分析，单次推演时间显著缩短
**Depends on**: Phase 1 (correct image handling must work first)
**Requirements**: PERF-01, PERF-02
**Success Criteria** (what must be TRUE):
  1. ImageAnalyzer 使用 ThreadPoolExecutor 并发处理多张图片，而非串行逐张分析
  2. LLM 并发请求通过 semaphore 限制（默认 max_workers=3），避免百炼 API 限流
  3. 5 张图片的推演总时间 <= 5 分钟（相比串行的 15-25 分钟）
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md — ImageAnalyzer 并发化 + Semaphore 限流 + race_campaigns 并行分析

### Phase 5: Evaluate Quality
**Goal**: Evaluate 推演结果更可靠——去除位置偏差，诊断建议结构化
**Depends on**: Phase 1 (images must work), Phase 2 (personas must be configurable)
**Requirements**: QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. PairwiseJudge 对每对 campaign 进行正反两次评审（A vs B 和 B vs A），标记不一致判断
  2. ImageAnalyzer 输出结构化诊断（JSON 格式的"问题 -> 建议"列表），而非自由文本段落
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Evaluate Frontend
**Goal**: 用户可在前端完整使用 Evaluate 推演路径（发起、跟踪进度、查看结果）
**Depends on**: Phase 1, Phase 5 (image fix + quality improvements before UI)
**Requirements**: EVAL-01, EVAL-02, EVAL-03
**Success Criteria** (what must be TRUE):
  1. 用户可在前端页面发起 Evaluate 深度评审推演，无需使用 API 工具
  2. 推演进行中，页面展示实时进度（当前阶段名称、已完成百分比）
  3. 推演完成后，结果页展示每个评审人格的打分、两两对比胜负、Bradley-Terry 综合排名
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Unified Entry
**Goal**: 用户从统一入口选择推演模式并提交方案，无需理解后端 API 差异
**Depends on**: Phase 6 (Evaluate frontend must exist)
**Requirements**: UNIF-01, UNIF-02
**Success Criteria** (what must be TRUE):
  1. HomePage 提供模式选择器，用户可选择 Race（快速）、Evaluate（深度）、或 Both（联合）模式
  2. 一套统一表单支持所有推演模式，用户填写一次方案信息即可发起所选模式的推演
  3. 选择 Both 模式时，Race 和 Evaluate 推演同时启动，各自独立展示进度和结果
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

### Phase 8: Results Enhancement
**Goal**: 推演结果页提供多方案并排对比、多维可视化和历史基线定位
**Depends on**: Phase 6 (Evaluate results page exists), Phase 7 (unified entry delivers results)
**Requirements**: RES-01, RES-02, RES-03, QUAL-03
**Success Criteria** (what must be TRUE):
  1. 推演结果页支持并排展示多个 campaign 方案的分数和视觉素材缩略图
  2. 各维度分数（视觉吸引力、品牌契合度、受众共鸣等）以雷达图或柱状图形式对比展示
  3. 每个方案展示其在历史 campaign 数据中的 percentile 位置（如"超过 75% 的历史 campaign"）
  4. 每个方案展示结构化的视觉改进建议（来自 Phase 5 的结构化诊断输出）
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Image Pipeline Fix | 0/2 | Planned | - |
| 2. PersonaRegistry Service | 0/1 | Not started | - |
| 3. Category Persona Config | 0/2 | Planned | - |
| 4. Concurrent Image Analysis | 0/1 | Planned | - |
| 5. Evaluate Quality | 0/1 | Not started | - |
| 6. Evaluate Frontend | 0/2 | Not started | - |
| 7. Unified Entry | 0/1 | Not started | - |
| 8. Results Enhancement | 0/2 | Not started | - |
