<div align="center">

<img src="./static/image/MiroFishmoody_logo.png" alt="MiroFishmoody Logo" width="60%"/>

# MiroFishmoody

**为 Moody Lenses 重构的 Internal Decision Market**

从“预测万物”的社会仿真，转向“上线前给方案定价”的电商内部决策市场。

[English](./README-EN.md) | [中文](./README.md)

</div>

## 项目定位

**MiroFishmoody** 是基于 [MiroFish](https://github.com/666ghj/MiroFish) 的一条产品化 fork，目标不是继续做重型舆情/社会模拟，而是服务于 **Moody Lenses** 的电商投放场景：

- 在多个 campaign 方案之间做结构化对比
- 在上线前找出更可能赢的 angle、hook 和 narrative
- 把“经验判断”变成可复盘、可比较、可校准的内部决策市场

它回答的不是“未来一定会怎样”，而是：

- `A / B / C` 三个方案里谁更值得上
- 哪个方案更抓眼球、更可信、更适配目标受众
- 哪些 objection、claim 风险或品牌表达问题会拖垮转化
- 当前方案应当 `ship / revise / kill`
- 哪些方案只是“看起来不错”，但没有足够 edge 值得下注

## 为什么做这个 fork

电商 campaign 的早期决策，常常在“好不好看”“会不会有用”“我觉得用户会喜欢”这种主观判断里打转。

对 Moody 来说，这不够。

我们要的是一个 **internal decision market**：

- 不假装预测真实 ROAS / GMV
- 不用一个人的经验覆盖全部用户反应
- 不把“大家觉得不错”当成结论
- 用多视角评审、方案对战、概率化输出和赛后校准，提升方案选择胜率

## 方法论血统

这个项目的下一跳，不只是从 AI 来的，也明确是从 **币圈 / prediction market / event pricing** 文化里长出来的。

如果没有这些经历，我大概率也不会想到把一个多-agent evaluator，推进成一个 **internal decision market**。

这里真正被借过来的，不是“发币”那一套，而是下面这套思维方式：

- 把分歧拿来定价，而不是拿来空谈
- 把“我觉得”逼成“你愿意给它多少概率”
- 把 bull case 和 bear case 同时摆上台面
- 把结论和赛后结果绑定，允许系统被结算、被打脸、被校准

所以这个仓库也想明确向那条 lineage 致意：

- 向早期 prediction market builders 致意
- 向 crypto-native event market players 致意
- 向把 `odds`、`edge`、`implied probability` 带进日常决策讨论的人致意
- 也向像 **SBF** 这一代交易圈人物所代表的那种“先问市场怎么定价分歧，而不是先问谁声音更大”的思维习惯致意

这里的致意只针对 **epistemic machinery** 和信息聚合方法，不是对后来所有人、所有项目或所有结果的背书。

## Moody 业务语境

这个 fork 面向 **Moody Lenses** 的真实业务场景设计：

- 两条产品线：`colored lenses` 与 `moodyPlus`
- 品牌竞争点是 `function + aesthetics`，不是简单打折
- `moodyPlus` 主要面向已有隐形眼镜佩戴者，重视自然感、舒适感与眼健康安心感
- Meta、Google、influencer 等渠道的素材评审，需要先做方案筛选，再进入真实投放验证

## 这个系统重点评什么

当前设计关注的是 **相对排序 + 概率定价**，而不是绝对预测。

核心评审维度包括：

- Hook strength
- Visual / aesthetic pull
- Message clarity
- Trust and claim believability
- Audience fit
- Objection pressure
- Brand risk

最终输出应聚焦：

- ranking
- probability board
- sub-markets
- pairwise comparison
- spread / uncertainty
- audience-specific feedback
- objections and revision directions
- resolution-ready fields
- `ship / revise / kill`

## 重构方向

这个 fork 的重构原则很明确：

**保留**

- 多视角 agent 评审
- 多方案对战而不是单方案打分
- 结构化总结与决策输出

**删除**

- Zep 图谱
- GraphRAG
- Twitter / Reddit 社交环境
- 长时社会模拟
- “预测万物”的泛化叙事

**重写**

- Audience panel
- Pairwise judge engine
- Campaign scoring
- Probability aggregation
- Sub-market evaluation
- Resolution tracking
- Judge calibration
- Summary generation
- 后续 calibration layer 持续增强

## 当前状态

这是一个 **正在公开推进中的重构 fork**。

当前主线不是做“完整自治世界”，而是把原始 MiroFish 的重型结构压缩成一个更适合电商团队使用的 **internal decision market**。

当前公开仓库的目标是：

1. 先完成对外叙事与方向对齐
2. 再持续同步代码层的清理、重构和验证
3. 最终把 fork 收敛成一个真正能用于 pre-launch campaign review 的系统

换句话说，这个仓库现在更适合被理解为：

> 一个围绕 Moody Lenses 场景重构中的 internal decision market，而不是原始 MiroFish 的简单换皮版本。

## 预期工作流

长期目标中的工作流大致如下：

1. 输入多个 campaign 方案
2. 选择产品线与目标受众
3. 由 audience panel 做多视角评审
4. 由 judge engine 做 pairwise 对战
5. 生成 probability board、sub-markets、ranking、objections 与建议动作
6. 赛后用真实投放结果做 resolution 与 calibration

## 为什么币圈人会秒懂

如果你来自 prediction market、event pricing、交易或赔率文化，这个项目的味道会很熟。

因为它本质上做的是同一件事：

- 不再问“你喜不喜欢这个方案”
- 而是问“你愿意给它多少概率”
- 不再只给观点
- 而是给 `price`、`spread`、`edge`、`resolution`

区别只在于，这里被定价的不是 election、macro event 或 token narrative，而是 **Moody 的 campaign concept**。

## 为什么电商团队真的能用

对电商团队来说，这不是一个“更会说话的创意 review 机器人”，而是一个把早期拍脑袋决策结构化的系统。

它适合用来：

- 在正式花预算前筛掉明显弱方案
- 在多个 angle 之间找到更值得先测的那个
- 把“我觉得会赢”拆成可讨论的子问题
- 让创意、投放、品牌和落地页判断进入同一个决策面板

它不替代真实投放测试，但能显著减少低质量测试进入媒体的概率。

## 适用场景

- Meta campaign angle 预筛选
- 创意方向选择
- LP angle 对比
- Influencer script / brief 的早期评审
- `colored lenses` 与 `moodyPlus` 的受众差异化判断

## 不解决什么

这个系统不应该被当成：

- 真实利润预测器
- 归因系统替代品
- 媒体 buying engine
- “一定会爆”的神谕工具

它首先是一个 **更可量化的方案选择器 / 内部决策市场**。

## 致谢

- 原始项目：[MiroFish](https://github.com/666ghj/MiroFish)
- 原始社会仿真方向为这个 fork 提供了多 agent 推演的起点
- 这套新方向也明确借鉴了 **crypto-native prediction markets / event contracts / forecasting communities** 的方法论
- 如果没有币圈里那套关于 `pricing disagreement`、`finding edge`、`settling against reality` 的训练，这个方向不会成形
- 这里也特别致意那些让“市场化聚合观点”变得更可见的玩家与社区，包括早期 prediction market builders、crypto event market 玩家，以及像 **SBF** 这样的交易圈代表人物所体现出的那部分思维影响
- 我们借用的是：`implied probability`、`sub-markets`、`resolution`、`calibration`
- 我们**不**借用的是：发币、链上交易、公开投机市场

后续代码与文档会继续围绕 **Moody Lenses internal decision market** 这一目标收敛。
