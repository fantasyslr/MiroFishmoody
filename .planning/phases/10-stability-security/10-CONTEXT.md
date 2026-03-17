# Phase 10: Stability & Security - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

后端基础设施加固：_evaluation_store 线程安全、SQLite WAL 模式、密码 bcrypt 哈希存储。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/evaluation_orchestrator.py`: _evaluation_store dict 需加锁
- `backend/app/models/`: SQLite 连接层
- `backend/app/api/auth.py`: 当前认证逻辑

### Established Patterns
- Flask + SQLite，单文件数据库
- 环境变量配置（.env）
- 现有 ThreadPoolExecutor + Semaphore 并发模式

### Integration Points
- _evaluation_store: EvaluationOrchestrator 读写
- SQLite: 所有 db.session 调用
- Auth: 登录/注册 API 路由

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
