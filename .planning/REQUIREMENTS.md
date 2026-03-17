# Requirements: MiroFishmoody

**Defined:** 2026-03-17
**Core Value:** 让每一次 campaign 在上线前都能得到数据化的推演对比，用 AI 推演替代"拍脑袋"决策

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Bug Fix

- [x] **BUG-01**: Evaluate 路径的图片路径解析正确工作 — `AudiencePanel` 和 `PairwiseJudge` 使用统一的 `resolve_image_path()` 而非 `os.path.exists()` 检查 URL 字符串
- [x] **BUG-02**: 上传图片在 base64 编码前自动缩放至 max 1024px — 防止高分辨率图片超出 LLM token 限制

### Performance

- [x] **PERF-01**: 多张图片并行分析 — ImageAnalyzer 使用 ThreadPoolExecutor 并发处理，单次推演 ≤ 5 分钟
- [x] **PERF-02**: LLM 并发调用有速率控制 — 使用 semaphore 限制并发 LLM 请求数（默认 max_workers=3），避免百炼 API 限流

### Persona

- [x] **PERS-01**: 创建 PersonaRegistry 服务 — 从硬编码人格数组提取为独立服务，支持配置化
- [x] **PERS-02**: 按品类配置评审人格 — moodyPlus（透明片）和 colored_lenses（彩片）各有独立的评审人格集
- [x] **PERS-03**: 人格配置为预设集而非自由文本 — 使用策展好的人格模板，带 schema 校验

### Evaluate Frontend

- [x] **EVAL-01**: Evaluate 推演页面 — 用户可在前端发起深度评审推演，包含进度轮询和结果展示
- [x] **EVAL-02**: 异步任务进度展示 — 用户可看到 Evaluate 推演的实时进度（当前阶段、已完成百分比）
- [x] **EVAL-03**: Evaluate 结果页面展示评审团打分详情 — 包含每个人格的评分、两两对比结果、BT 综合排名

### Unified Entry

- [x] **UNIF-01**: 统一推演入口 — 在 HomePage 添加模式选择器（Race / Evaluate / Both）
- [x] **UNIF-02**: 统一方案录入表单 — 一套表单支持两种推演路径，用户无需知道后端 API 差异
- [x] **UNIF-03**: 品类选择驱动人格 — 用户选品类后，系统自动加载对应品类的评审人格预设

### Results

- [x] **RES-01**: 多方案并排对比视图 — 推演结果页支持并排展示多个 campaign 方案的分数和视觉素材
- [x] **RES-02**: 多维度评分可视化 — 用雷达图或柱状图展示各维度（视觉吸引力、品牌契合度、受众共鸣等）分数对比
- [x] **RES-03**: 历史基线分位展示 — 每个 campaign 方案展示其在历史数据中的 percentile 位置

### Quality

- [x] **QUAL-01**: PairwiseJudge 位置互换去偏 — 每对 campaign 正反各评一次，标记不一致判断
- [x] **QUAL-02**: 视觉诊断建议结构化 — ImageAnalyzer 输出从自由文本改为结构化"问题 → 建议"格式
- [x] **QUAL-03**: 视觉诊断建议在结果页展示 — 每个 campaign 方案展示具体的视觉改进建议

## v1.1 Requirements

Requirements for v1.1 加固与增强. Each maps to roadmap phases.

### Bug Fix

- [ ] **BUG-03**: Both 模式 ResultPage 显示跳转到 EvaluateResultPage 的导航链接 — getBothModeState 已存储但未消费
- [ ] **BUG-04**: Evaluate 结果页诊断面板数据接入 — 当前 diagnosticsMap 为空，Evaluate 管线需产出图片诊断数据

### Stability

- [ ] **STAB-01**: _evaluation_store 线程安全 — 加 threading.Lock 保护并发读写
- [ ] **STAB-02**: SQLite WAL 模式 — 启用 WAL journal_mode + busy_timeout 减少并发锁

### Security

- [ ] **SEC-01**: 密码哈希存储 — 从明文改为 bcrypt

### Export

- [ ] **EXP-01**: 推演结果导出 PDF — 可截图式结果卡片或 PDF 报告
- [ ] **EXP-02**: 推演结果导出图片 — 适合社交媒体/即时通讯分享

### Iteration

- [ ] **ITER-01**: 方案迭代推演（版本对比） — 同一 campaign 修改后重新推演，自动对比版本间改善

### Analytics

- [ ] **ANAL-01**: 推演趋势 Dashboard — 跨 campaign 追踪推演分数变化趋势

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Stability

- **STAB-03**: _evaluation_store LRU 淘汰 — 限制内存中最大条目数（如 100），防止内存泄漏

### Security

- **SEC-02**: SECRET_KEY 强制配置 — 移除硬编码 fallback，未设置时启动报错
- **SEC-03**: FLASK_DEBUG 默认关闭 — 生产环境默认 False

### Iteration

- **ITER-02**: 受众人格自定义 — 超越预设模板，支持自定义人格描述

### Analytics

- **ANAL-02**: Race + Evaluate 交叉对比视图 — 两条路径排名一致性分析

## Out of Scope

| Feature | Reason |
|---------|--------|
| 视频/GIF 素材推演 | LLM vision 按帧计费，成本和复杂度过高 |
| AI 自动生成创意素材 | 推演工具定位是评估，不是生成 |
| 真人消费者 panel 调研 | 成本高、速度慢，已有独立调研流程 |
| 实时 A/B 投放测试 | 超出推演范畴，涉及广告平台和预算 |
| 眼动追踪/注意力热力图 | 需专用模型，非通用 LLM 能力 |
| 跨渠道投放效果预测 | 需各平台历史投放数据，远超当前数据基础 |
| 移动端 App | Web 优先，内部工具不需要原生 App |
| PostgreSQL 迁移 | 内部工具用户量小，SQLite 够用 |
| BrandStateEngine 重构 | 当前能用，等 characterization tests 建好后再拆 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 1: Image Pipeline Fix | Complete |
| BUG-02 | Phase 1: Image Pipeline Fix | Complete |
| PERS-01 | Phase 2: PersonaRegistry Service | Complete |
| PERS-03 | Phase 2: PersonaRegistry Service | Complete |
| PERS-02 | Phase 3: Category Persona Config | Complete |
| UNIF-03 | Phase 3: Category Persona Config | Complete |
| PERF-01 | Phase 4: Concurrent Image Analysis | Complete |
| PERF-02 | Phase 4: Concurrent Image Analysis | Complete |
| QUAL-01 | Phase 5: Evaluate Quality | Complete |
| QUAL-02 | Phase 5: Evaluate Quality | Complete |
| EVAL-01 | Phase 6: Evaluate Frontend | Complete |
| EVAL-02 | Phase 6: Evaluate Frontend | Complete |
| EVAL-03 | Phase 6: Evaluate Frontend | Complete |
| UNIF-01 | Phase 7: Unified Entry | Complete |
| UNIF-02 | Phase 7: Unified Entry | Complete |
| RES-01 | Phase 8: Results Enhancement | Complete |
| RES-02 | Phase 8: Results Enhancement | Complete |
| RES-03 | Phase 8: Results Enhancement | Complete |
| QUAL-03 | Phase 8: Results Enhancement | Complete |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after v1.1 requirements definition*
