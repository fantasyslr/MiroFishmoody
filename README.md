<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFishmoody Logo" width="60%"/>

# MiroFishmoody

**为 Moody Lenses 重构的电商 Campaign Choice Engine**

从“预测万物”的社会仿真，转向“上线前选更优方案”的电商决策引擎。

[English](./README-EN.md) | [中文](./README.md)

</div>

## 项目定位

**MiroFishmoody** 是基于 [MiroFish](https://github.com/666ghj/MiroFish) 的一条产品化 fork，目标不是继续做重型舆情/社会模拟，而是服务于 **Moody Lenses** 的电商投放场景：

- 在多个 campaign 方案之间做结构化对比
- 在上线前找出更可能赢的 angle、hook 和 narrative
- 把“经验判断”变成可复盘、可比较、可校准的评审流程

它回答的不是“未来一定会怎样”，而是：

- `A / B / C` 三个方案里谁更值得上
- 哪个方案更抓眼球、更可信、更适配目标受众
- 哪些 objection、claim 风险或品牌表达问题会拖垮转化
- 当前方案应当 `ship / revise / kill`

## 为什么做这个 fork

电商 campaign 的早期决策，常常在“好不好看”“会不会有用”“我觉得用户会喜欢”这种主观判断里打转。

对 Moody 来说，这不够。

我们要的是一个 **campaign choice engine**：

- 不假装预测真实 ROAS / GMV
- 不用一个人的经验覆盖全部用户反应
- 不把“大家觉得不错”当成结论
- 用多视角评审、方案对战和结构化结论，提升方案选择胜率

## Moody 业务语境

这个 fork 面向 **Moody Lenses** 的真实业务场景设计：

- 两条产品线：`colored lenses` 与 `moodyPlus`
- 品牌竞争点是 `function + aesthetics`，不是简单打折
- `moodyPlus` 主要面向已有隐形眼镜佩戴者，重视自然感、舒适感与眼健康安心感
- Meta、Google、influencer 等渠道的素材评审，需要先做方案筛选，再进入真实投放验证

## 这个系统重点评什么

当前设计关注的是 **相对排序**，而不是绝对预测。

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
- pairwise comparison
- audience-specific feedback
- objections and revision directions
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
- Summary generation
- 后续 calibration layer

## 当前状态

这是一个 **正在公开推进中的重构 fork**。

当前主线不是做“完整自治世界”，而是把原始 MiroFish 的重型结构压缩成一个更适合电商团队使用的选择器。

当前公开仓库的目标是：

1. 先完成对外叙事与方向对齐
2. 再持续同步代码层的清理、重构和验证
3. 最终把 fork 收敛成一个真正能用于 pre-launch campaign review 的系统

换句话说，这个仓库现在更适合被理解为：

> 一个围绕 Moody Lenses 场景重构中的 campaign evaluator，而不是原始 MiroFish 的简单换皮版本。

## 预期工作流

长期目标中的工作流大致如下：

1. 输入多个 campaign 方案
2. 选择产品线与目标受众
3. 由 audience panel 做多视角评审
4. 由 judge engine 做 pairwise 对战
5. 生成 ranking、objections、summary 与建议动作

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

它首先是一个 **更可量化的方案选择器**。

## 致谢

- 原始项目：[MiroFish](https://github.com/666ghj/MiroFish)
- 原始社会仿真方向为这个 fork 提供了多 agent 推演的起点

后续代码与文档会继续围绕 **Moody Lenses campaign choice engine** 这一目标收敛。
