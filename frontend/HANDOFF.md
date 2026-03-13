# MiroFishmoody Frontend Handoff

最后更新：2026-03-13  
适用分支：`feat/moody-campaign-engine`

## 这份 handoff 是干什么的

这不是产品文档，也不是设计稿说明。  
它只负责把当前这条“前端专聊”对话压缩成一个可以跨电脑继续工作的上下文包。

## 这轮对话的硬约束

- 以后这条线只聊前端，不讨论后端实现。
- 项目：`MiroFishmoody`
- 定位：Moody 内部 campaign 决策市场
- 目标：把现有 Stitch / HTML 稿收成可实现的前端界面
- 语言：中文优先
- 视觉方向：
  - 奶油白 / 深咖 / 雾蓝灰
  - 少量酒红提示
  - 不要交易平台感
  - 不要普通 SaaS 后台感

## 这轮前端工作方式

先做：
- UI review
- 信息架构收口

再做：
- React / Tailwind 可实现版本

额外要求：
- 发现 design token、文案、组件结构问题时，直接指出，不要客气

## 已经收口的 5 个页面

1. 首页 / 总览台
2. 新建评审页
3. 运行中状态页
4. 结果页
5. 结算 / 历史页

## 已经做出的关键决策

### 1. 首页和总览台合并

不再拆成两个职责重叠页面，统一为 `总览台`。

### 2. 不再沿用旧 Vue 前端

旧前端已整体切到新的 React + Vite + Tailwind 前端壳，不继续沿用之前的 Vue 文件结构。

### 3. 统一 token

只保留一套颜色 token：

- `cream`
- `paper`
- `stone`
- `line`
- `coffee`
- `ink`
- `mist`
- `mist-soft`
- `wine`

### 4. 统一语言，不用交易术语

不要再往页面里放这类表达：

- 参与人数
- 计票
- 市场博弈
- 活跃交易头寸
- 盘口感术语
- 一键上线
- 执行发布

统一改成内部工作台语言，例如：

- 当前阶段
- 评审中
- 待结算
- 待校准
- 标记为优先测试
- 进入下一轮优化

### 5. 所有假数据都必须显式占位

如果不是 API 真值，不允许伪装成真实经营结果。  
统一使用：

- `示例数据`
- `待实际投放回填`

结果页已经改成定性等级和摘要，不再堆伪精度数字。

## 仓库里要先读的文件

### UI / IA 结论

- `frontend/UI_REVIEW.md`

### 前端入口

- `frontend/src/App.tsx`
- `frontend/src/components/layout/AppShell.tsx`

### 页面

- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/NewReviewPage.tsx`
- `frontend/src/pages/RunningStatusPage.tsx`
- `frontend/src/pages/ResultPage.tsx`
- `frontend/src/pages/HistoryPage.tsx`

### 共享组件

- `frontend/src/components/ui/SectionCard.tsx`
- `frontend/src/components/ui/StatusBadge.tsx`

### 统一示例数据 / 文案骨架

- `frontend/src/data/campaignDecisionData.ts`

### 设计 token / 全局样式

- `frontend/tailwind.config.js`
- `frontend/src/index.css`

## 当前前端状态

已经完成：

- 5 个核心页面的 React / Tailwind 壳
- 统一页面骨架
- 统一 token
- 中文化收口
- 去交易感
- 去普通 SaaS 后台感
- 结果页 action 收成单组
- 运行中页去技术系统化

已经验证：

- `npm run build`
- `npm run lint`

## 下一台电脑怎么继续

先拉代码并切到这个分支：

```bash
git clone https://github.com/fantasyslr/MiroFishmoody.git
cd MiroFishmoody
git checkout feat/moody-campaign-engine
cd frontend
npm install
npm run dev
```

然后在新电脑里，直接对 Codex 说：

```text
只继续做 MiroFishmoody 前端，不讨论后端。先读 frontend/HANDOFF.md、frontend/UI_REVIEW.md 和 frontend/src/data/campaignDecisionData.ts，再继续当前页面优化。
```

## 不建议怎么迁

不要依赖“把这条本地会话数据库硬拷过去”继续工作。  
能跨电脑稳定继续的，是仓库里的代码和 handoff，不是本地线程状态。
