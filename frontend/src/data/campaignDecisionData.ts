import type { ReactNode } from 'react'

type StatusTone = 'neutral' | 'running' | 'done' | 'warning' | 'draft' | 'settlement'

export type CampaignDraft = {
  id: string
  name: string
  productLine: 'moodyplus' | 'colored_lenses'
  targetAudience: string
  coreMessage: string
  channels: string
  creativeDirection: string
  budgetRange: string
  kvDescription: string
  promoMechanic: string
}

export const navigation: Array<{ to: string; label: string; description: string }> = [
  { to: '/', label: '总览台', description: '看队列、重点与最近结论' },
  { to: '/new-review', label: '新建评审', description: '把输入写成可比较方案' },
  { to: '/running', label: '运行状态', description: '只看当前阶段与进度' },
  { to: '/result', label: '结果页', description: '收口建议与方案差异' },
  { to: '/history', label: '结算历史', description: '回填真实结果并做复盘' },
]

export const dashboardMetrics = [
  {
    label: '推进中的评审',
    value: '3 项',
    note: '只保留本周真正需要团队推进的事项，不展示装饰性吞吐数字。',
  },
  {
    label: '待结算',
    value: '2 项',
    note: '结果已经产出，下一步是回填真实投放表现，不是继续分析。',
  },
  {
    label: '待补信息',
    value: '1 项',
    note: '方案差异仍不够清楚，建议回到新建页补全输入。',
  },
  {
    label: '本周建议动作',
    value: '先测 B',
    note: '优先推进更容易形成执行共识的方案，再安排下一轮优化。',
  },
] as const

export const dashboardNotes = {
  focus: [
    '所有状态都明确写成示例，不把页面包装成已经接通真实经营数据的系统。',
    '总览台只回答三个问题：现在在推什么、下一个动作是什么、最近出了什么结论。',
    '文案优先说人话，不再沿用交易市场或技术系统口径。',
  ],
  workbench: [
    '夏季舒适感评审建议今天确认首测方案，并补齐落地页配套素材。',
    '老客换购唤回评审已经有建议结论，等真实投放结果回填后再做校准。',
    '通勤生活方式方向素材差异仍不够大，先不要急着进入结果页。',
  ],
} as const

export const dashboardReviews: Array<{
  title: string
  statusLabel: string
  statusTone: StatusTone
  productLine: string
  stage: string
  note: string
}> = [
  {
    title: 'moodyPlus 夏季舒适感方向评审',
    statusLabel: '进行中',
    statusTone: 'running',
    productLine: 'moodyPlus',
    stage: '结果收口中',
    note: '三套方案差异已经比较清楚，当前重点是把推荐动作说清楚，而不是继续堆分析结构。',
  },
  {
    title: '通勤生活方式 campaign 方向评审',
    statusLabel: '待补信息',
    statusTone: 'warning',
    productLine: 'colored lenses',
    stage: '回到新建页',
    note: 'KV 与核心信息仍过于接近，建议先补清楚受众与使用场景，再进入比较流程。',
  },
  {
    title: '老用户换购唤回节奏评审',
    statusLabel: '待结算',
    statusTone: 'settlement',
    productLine: 'moodyPlus',
    stage: '等回填真实结果',
    note: '推荐方案已出，目前最重要的是回填首轮投放表现，验证建议是否被真实结果支持。',
  },
]

export const reviewPreset: {
  reviewName: string
  context: string
  checklist: string[]
  sideNotes: string[]
} = {
  reviewName: '',
  context: '',
  checklist: [
    '每个方案都要能看出清楚差异，不要只是在同一表述上换近义词。',
    '业务背景要写明这轮评审服务的决策，否则结果页只会变成漂亮摘要。',
    '如果关键 claim 还没有支撑，优先补信息，不要急着发起评审。',
  ],
  sideNotes: [
    '方案数控制在 2 到 4 个之间，太多会让差异被稀释。',
    '渠道、受众、创意方向至少要有一项拉开差异，否则不具备比较意义。',
    '预算与促销信息可以写待确认，但不能完全缺省。',
  ],
}

export const initialCampaignDrafts: CampaignDraft[] = [
  {
    id: 'campaign-a',
    name: '',
    productLine: 'moodyplus',
    targetAudience: '',
    coreMessage: '',
    channels: '',
    creativeDirection: '',
    budgetRange: '',
    kvDescription: '',
    promoMechanic: '',
  },
  {
    id: 'campaign-b',
    name: '',
    productLine: 'moodyplus',
    targetAudience: '',
    coreMessage: '',
    channels: '',
    creativeDirection: '',
    budgetRange: '',
    kvDescription: '',
    promoMechanic: '',
  },
]

export const runningReview = {
  title: 'moodyPlus 夏季舒适感方向评审',
  stageSummary:
    '当前已经完成输入整理和第一轮比较，页面重点是告诉团队：现在哪一步完成了、下一步该做什么、预计多久可以给出建议。',
  progressLabel: '整体进度约 68%',
  eta: '预计 25 分钟后可产出结果页草稿',
  currentCampaign: '当前正在收口：方案 B · 通勤生活方式',
  currentStage: '结果摘要整理中',
  stages: [
    {
      title: '输入检查',
      status: 'done',
      note: '确认每个方案都有可比较的受众、信息和创意差异。',
    },
    {
      title: '方案比较',
      status: 'done',
      note: '已经完成第一轮差异判断，当前保留更适合首测的两个方向。',
    },
    {
      title: '结果收口',
      status: 'current',
      note: '把排序原因和动作建议整理成团队可以直接阅读的短句。',
    },
    {
      title: '待结算准备',
      status: 'upcoming',
      note: '结果页确认后，将同步准备真实投放结果回填字段。',
    },
  ] as Array<{
    title: string
    status: 'done' | 'current' | 'upcoming'
    note: string
  }>,
  campaignSignals: [
    {
      name: '方案 A · 轻氧专业感',
      position: '备选',
      note: '表达稳定、可信度高，但首轮刺激感略弱，适合作为稳妥备选。',
    },
    {
      name: '方案 B · 通勤生活方式',
      position: '主推',
      note: '更容易被执行团队快速理解，也更适合先进入低门槛测试。',
    },
    {
      name: '方案 C · 老客换购唤回',
      position: '谨慎',
      note: '适合后续做定向唤回，不适合作为这轮主线 campaign 首测。',
    },
  ],
  highlights: [
    '运行中页面只展示过程感，不展示技术栈或后台日志。',
    '团队最关心的是现在进行到哪一步，以及什么时候可以看到结果页。',
    '当前方案观察应该帮助理解差异，而不是提前伪装成最终结论。',
  ],
} as const

export const resultReview = {
  badge: '示例结论',
  recommendation: {
    title: '建议优先测试方案 B · 通勤生活方式',
    summary:
      '它不是“绝对最强”，但最容易形成执行共识，也最适合首轮小步快跑验证。如果首测回填支持该方向，再继续扩大素材和场景版本。',
  },
  summary:
    '当前更建议团队先验证“自然融入日常通勤”的表达路径，因为它兼顾理解成本与执行效率。方案 A 的可信感更稳，适合作为补位方案保留。',
  assumptions: [
    '本页仅为前端示例数据，不代表真实投放表现。',
    '当前结论建立在示例输入完整、并且方案差异足够明显的前提上。',
    '如果真实素材落地后差异被抹平，排序需要重新评估。',
  ],
  confidenceNotes: [
    '这里表达的是相对推荐强度，不是可对外复述的精确胜率。',
    '最终是否成立，要靠结算页回填的真实测试结果来校准。',
    '如果后续补充了新的 claim 证据，建议重新走一轮比较。',
  ],
  rankings: [
    {
      rank: '01',
      name: '方案 B · 通勤生活方式',
      summary: '更适合先进入测试，团队对执行画面和渠道节奏也更容易形成共识。',
      statusLabel: '建议优先测试',
      statusTone: 'done' as const,
      strengths: ['易执行', '场景感清楚', '更适合首测'],
      concerns: ['需要避免过于泛 lifestyle', '落地页承接要更具体'],
    },
    {
      rank: '02',
      name: '方案 A · 轻氧专业感',
      summary: '可信度稳定，适合保留成更稳的备选版本，后续可补强情绪感。',
      statusLabel: '保留备选',
      statusTone: 'neutral' as const,
      strengths: ['专业感稳定', '舒适诉求明确', '适合品牌语境'],
      concerns: ['首轮刺激略弱', '传播扩散点不够尖锐'],
    },
    {
      rank: '03',
      name: '方案 C · 老客换购唤回',
      summary: '更像定向运营议题，不适合作为这轮主线 campaign 的公共表达。',
      statusLabel: '进入下一轮优化',
      statusTone: 'warning' as const,
      strengths: ['人群明确', '复购目标直接'],
      concerns: ['适用范围窄', '不适合作为主线传播'],
    },
  ],
  matrix: [
    {
      label: '受众理解成本',
      values: [
        { campaign: '方案 A', level: 2 as const, note: '需要多一点解释，专业感更强。' },
        { campaign: '方案 B', level: 3 as const, note: '进入场景快，团队更容易直接执行。' },
        { campaign: '方案 C', level: 1 as const, note: '更偏存量人群，不适合泛用传播。' },
      ],
    },
    {
      label: '首测执行友好度',
      values: [
        { campaign: '方案 A', level: 2 as const, note: '适合稳妥首测，但亮点略保守。' },
        { campaign: '方案 B', level: 3 as const, note: '素材与脚本更容易快速拆分测试。' },
        { campaign: '方案 C', level: 2 as const, note: '适合做后续分层测试，不适合先跑。' },
      ],
    },
    {
      label: '后续扩展空间',
      values: [
        { campaign: '方案 A', level: 2 as const, note: '可向专业可信感继续延展。' },
        { campaign: '方案 B', level: 3 as const, note: '可扩成多场景、多人群版本。' },
        { campaign: '方案 C', level: 1 as const, note: '更偏运营活动，不够适合长期主线。' },
      ],
    },
  ],
  audienceTakeaways: [
    {
      title: '方案 B 更像“日常会点进去看”的内容',
      note: '因为它不需要先理解专业术语，场景入口更自然，阅读门槛更低。',
    },
    {
      title: '方案 A 的品牌感更稳',
      note: '适合在需要更高可信度的场景保留，但首轮测试未必优先。',
    },
  ],
  pairwiseNotes: [
    '方案 B 相比 A，更像一个可以马上开始测试的执行方向。',
    '方案 A 相比 C，更适合作为品牌主线表达，不容易显得过于促销。',
    '方案 C 当前更适合作为后续定向动作，而不是本轮公共表达主方案。',
  ],
  nextActions: [
    '先做方案 B 的首轮小规模测试，同时保留方案 A 作为稳妥备选。',
    '结果页确认后，马上准备结算字段，避免测试结束后缺少回填入口。',
    '如果执行团队认为 B 的 lifestyle 感过强，优先微调文案而不是推翻方向。',
  ],
} as const

export const settlementQueue: Array<{
  id: string
  title: string
  note: string
  statusLabel: string
  statusTone: StatusTone
}> = [
  {
    id: 'settlement-1',
    title: 'moodyPlus 夏季舒适感方向评审',
    note: '推荐方案已经确认，等待投放结果回填以验证是否支持当前建议。',
    statusLabel: '优先结算',
    statusTone: 'warning',
  },
  {
    id: 'settlement-2',
    title: '老用户换购唤回节奏评审',
    note: '首轮测试已投放，当前只缺关键指标和复盘说明。',
    statusLabel: '待回填',
    statusTone: 'settlement',
  },
]

export const calibrationState = {
  description: '校准不展示虚假的准确率，只说明当前机制和数据边界。',
  points: [
    '只有当真实投放结果回填后，历史判断才有资格进入校准。',
    '校准的目的不是追求好看的数值，而是帮助团队知道哪些判断口径更可靠。',
    '如果输入本身质量不稳定，校准结果也不应被过度解读。',
  ],
} as const

export const historyRecords: Array<{
  title: string
  detail: string
  statusLabel: string
  statusTone: StatusTone
}> = [
  {
    title: '春季清透感方向评审',
    detail: '已完成回填，结果基本支持当时的推荐方向，可作为后续类似题材参考。',
    statusLabel: '已完成',
    statusTone: 'done',
  },
  {
    title: '618 预热创意方向评审',
    detail: '真实结果与建议存在偏差，已记录到复盘说明，后续需重看判断口径。',
    statusLabel: '待复盘',
    statusTone: 'warning',
  },
]

export const resultSidebarNotes: Array<{ title: string; body: ReactNode }> = [
  {
    title: '动作建议',
    body: '结果页的第一任务不是解释系统有多复杂，而是告诉团队现在应该先做哪一步。',
  },
  {
    title: '表达边界',
    body: '这里展示的是示例排序与摘要，不是可对外使用的经营结论或真实绩效数据。',
  },
]
