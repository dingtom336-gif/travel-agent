# TravelMind — 对话式智能旅行规划平台

## 1. 产品概述

### 1.1 产品定位
基于 Agent Teams 架构的对话式旅行规划平台。用户通过自然语言描述任意模糊、复合、多维的出行意图，系统由多个专业 Agent 协同工作，自动拆解需求、调度工具、生成个性化旅行方案。

### 1.2 设计原则（源自小飞大脑策略）
- **看得懂**：不依赖预定义意图分类，用模型泛化能力理解任意用户表达
- **干得成**：多 Agent 协同 + 多工具智能调度，一站式解决复合需求
- **记得住**：长短期记忆 + 知识增强，千人千面 & 一人多面
- **自适应**：Generative UI，系统适应人而非人适应系统
- **会进化**：模拟演练 + 合成数据，自主进化飞轮

### 1.3 目标用户
出行用户（休闲旅游、商务出差、亲子游、毕业旅行等全场景）

---

## 2. 系统架构 — Agent Teams

### 2.1 架构总览

```
用户输入 (自然语言/语音/图片/地图圈选)
    │
    ▼
┌─────────────────────────────────────────────────┐
│           🧠 Orchestrator Agent (主控大脑)         │
│  职责：意图理解、任务拆解、Agent调度、结果整合       │
│  能力：ReAct Loop + Reflection + 模型路由          │
└─────────┬───────────────────────────┬─────────────┘
          │ 拆解 & 并行分发            │ 整合 & 输出
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│              Agent Teams (专业团队)                │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Transport │ │  Hotel   │ │   POI    │         │
│  │  Agent   │ │  Agent   │ │  Agent   │         │
│  │ 交通专家  │ │ 住宿专家  │ │ 目的地专家 │         │
│  └──────────┘ └──────────┘ └──────────┘         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Itinerary│ │  Budget  │ │ Knowledge│         │
│  │  Agent   │ │  Agent   │ │  Agent   │         │
│  │ 行程编排  │ │ 预算管家  │ │ 知识顾问  │         │
│  └──────────┘ └──────────┘ └──────────┘         │
│  ┌──────────┐ ┌──────────┐                       │
│  │ Weather  │ │ Customer │                       │
│  │  Agent   │ │ Service  │                       │
│  │ 天气助手  │ │ 客服专家  │                       │
│  └──────────┘ └──────────┘                       │
└─────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│           工具层 (MCP / Skills / APIs)             │
│  机票搜索 · 酒店搜索 · POI检索 · 地图服务 ·        │
│  天气查询 · 签证政策 · 汇率换算 · 日历服务 ·        │
│  路线规划算法 · 价格预测 · 图片搜索 ...             │
└─────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│           记忆层 (Memory)                          │
│  短期记忆(Session) · 长期记忆(用户画像) ·           │
│  知识库(RAG) · 状态池(全局参数)                     │
└─────────────────────────────────────────────────┘
```

### 2.2 Orchestrator Agent（主控大脑）

主控 Agent 是整个系统的核心中枢，不直接处理业务逻辑，而是：

| 能力 | 说明 |
|------|------|
| **意图理解** | 理解用户任意模糊/复合/多维表达，无预定义分类 |
| **任务拆解 (Decomposition)** | 通过 CoT 思维链，将复合意图拆解为可并行/串行的子任务序列 |
| **Agent 调度** | 根据子任务类型分发给对应专业 Agent，支持并行执行 |
| **结果整合** | 收集各 Agent 返回结果，上下文压缩后统一输出 |
| **自我反思 (Reflection)** | 校验结果一致性，检测冲突/错误，触发纠错重试 |
| **模型路由** | 简单问题走轻量模型快速响应，复杂规划走大模型深度推理 |

**ReAct Loop 核心流程：**
```
Thought → 分析用户意图，拆解为子任务
Action  → 调度对应Agent/工具执行
Observe → 收集执行结果，评估质量
Reflect → 检查是否满足用户需求，是否有冲突
→ 满足则整合输出，不满足则继续循环
```

### 2.3 专业 Agent 团队

#### Transport Agent（交通专家）
- **职责**：机票、火车票、大巴、自驾路线的搜索与推荐
- **工具**：机票搜索MCP、火车票搜索MCP、路线规划API、价格趋势预测
- **Skills**：联程拼接、中转最优策略、红眼航班规避、改签退票处理

#### Hotel Agent（住宿专家）
- **职责**：酒店/民宿搜索、对比、推荐
- **工具**：酒店搜索MCP、房型查询、价格对比、评价检索
- **Skills**：亲子酒店筛选、商务酒店匹配、性价比排序、地理位置优选

#### POI Agent（目的地专家）
- **职责**：景点/餐厅/购物/体验推荐
- **工具**：POI检索MCP、评分聚合、营业时间查询、门票价格查询
- **Skills**：小众景点挖掘、美食地图生成、主题线路推荐（文艺/冒险/亲子）

#### Itinerary Agent（行程编排师）
- **职责**：将各Agent结果编排为完整日程
- **工具**：路线优化算法、时间冲突检测、距离计算、地图渲染
- **Skills**：多日行程优化、紧凑/休闲模式切换、备选方案生成、实时动态调整

#### Budget Agent（预算管家）
- **职责**：预算估算、费用分摊、省钱建议
- **工具**：汇率换算MCP、价格历史查询、优惠券检索
- **Skills**：预算分配策略、穷游/奢华模式、费用AA计算

#### Knowledge Agent（知识顾问）
- **职责**：签证政策、出行贴士、文化禁忌、安全提醒
- **工具**：知识库RAG检索、政策实时爬取、时效性校验
- **Skills**：签证材料清单生成、入境须知汇总、时差/气候提醒

#### Weather Agent（天气助手）
- **职责**：目的地天气查询与行程天气适配
- **工具**：天气API、历史天气数据、穿衣建议生成
- **Skills**：雨季规避、最佳出行时间推荐、天气驱动行程调整

#### Customer Service Agent（客服专家）
- **职责**：售后问题处理、投诉协调、突发应急
- **工具**：订单查询MCP、退改签API、人工客服转接
- **Skills**：航班取消应急方案、酒店投诉处理、保险理赔指引

### 2.4 Agent 间协作模式

```
示例用户输入："春节带爸妈去日本玩5天，预算2万，老人腿脚不好，不要太累"

Orchestrator 拆解：
├─ [并行] Knowledge Agent → 日本春节签证政策 + 入境须知
├─ [并行] Weather Agent → 1-2月日本各城市天气
├─ [并行] Transport Agent → 春节往返日本机票（适老：直飞优先）
├─ [并行] POI Agent → 适老景点推荐（无障碍、少台阶）
│
├─ [等待上游] Hotel Agent → 根据推荐城市搜索适老酒店（电梯、无障碍）
├─ [等待上游] Itinerary Agent → 编排5日行程（每日步行<8000步、午休时间）
│
└─ [最终] Budget Agent → 预算分配校验，确保≤2万
     └─ Orchestrator → Reflection校验 → 整合输出
```

**协作原则：**
- 无依赖的子任务**并行执行**，减少等待时间
- 有依赖的子任务**串行编排**，上游结果作为下游输入
- 任何Agent执行失败，Orchestrator触发Reflection，决定重试/替代/降级
- 结果冲突时（如预算超标），Orchestrator协调相关Agent重新协商

---

## 3. 核心功能

### 3.1 对话式意图理解
- 支持任意自然语言输入，无需预定义意图分类
- 支持模糊表达：「想去个暖和的地方待几天」
- 支持复合需求：「找机票的同时推荐酒店，顺便看看签证怎么办」
- 支持多轮渐进细化：先给方向 → 再补约束 → 逐步确认
- 支持反悔修改：「刚才说的上海改成北京」→ 状态表自动更新

### 3.2 智能任务拆解与多Agent并行调度
- Orchestrator 基于 CoT 将复合意图拆解为子任务 DAG（有向无环图）
- 子任务自动分发给对应专业 Agent
- 支持并行执行 + 依赖等待 + 结果合并
- 支持执行中动态调整（某Agent失败后自动重路由）

### 3.3 行程生成与可视化
- 多日行程时间线展示（每日景点、交通、用餐、住宿）
- 地图路线可视化（POI标注、交通连线、步行距离）
- 预算分配饼图
- 天气日历叠加展示
- 支持"对比模式"：并排展示2-3套方案的优劣

### 3.4 Generative UI 动态编排
- **原子组件库**：机票卡片、酒店卡片、POI卡片、地图组件、时间线组件、天气组件、预算表格、对比表格等
- **意图驱动编排**：Agent根据用户意图和数据特征，实时决定组装哪些组件
  - 查机票 → 机票列表卡片 + 价格趋势图
  - 做攻略 → POI卡片网格 + 地图标注
  - 完整规划 → 时间线 + 地图 + 各类卡片嵌套
- **设备自适应**：
  - PC/宽屏：信息密度高，多列布局，对比表格
  - 手机端：单列流式，大字体，核心信息优先
- **流式渲染**：借鉴 RSC 理念，组件骨架先渲染，数据逐步填充，消除白屏

### 3.5 用户画像与个性化
- **短期记忆**：当轮对话上下文，自动压缩去水、槽位化状态管理
- **长期记忆**：跨会话用户偏好沉淀（价格敏感度、品牌偏好、出行风格）
- **一人多面**：识别当前场景（商务/亲子/独行），动态切换推荐策略
- **个性化话术**：「考虑到您之前习惯住希尔顿，这边也为您保留了推荐」

### 3.6 行程编辑与迭代
- 对话式修改：「第二天太紧了，减掉一个景点」
- 手动拖拽调整（日程时间线上拖拽排序）
- 局部重新规划：仅重新生成某一天/某一环节
- 版本管理：保留历史版本，支持回退

### 3.7 主动服务与应急
- 行程中天气突变 → 主动推送备选室内方案
- 航班取消/延误 → 自动搜索替代航班 + 通知用户
- 目的地突发事件 → 安全提醒 + 行程调整建议
- 异步处理通知：耗时操作（退改签处理）完成后主动回复

### 3.8 模拟演练与自进化
- **用户模拟器**：构建多类型虚拟用户（犹豫型、价格敏感型、需求模糊型），自动生成复杂对话测试
- **环境模拟器**：模拟工具超时、库存变化、价格波动等异常
- **AI裁判评估**：多维度评分（意图理解准确度、工具调用规范性、回复质量）
- **合成数据驱动训练**：优秀轨迹 → 合成数据 → 模型微调，形成自进化飞轮

---

## 4. 页面设计

### 4.1 首页
- 顶部：品牌标识 + 搜索/对话入口
- 中部：智能引导卡片（「带孩子去哪玩？」「周末短途游」「签证怎么办」）
- 底部：历史行程快捷入口
- 移动端：全屏对话入口 + 底部Tab导航

### 4.2 对话页（核心页面）
- 左侧/上方：对话流（支持文本、卡片、地图等混合渲染）
- 右侧/下方：实时行程预览面板（随对话动态更新）
- 输入区：文本输入 + 语音输入 + 图片上传 + 地图圈选
- 流式输出：Agent思考过程可视化（「正在搜索机票...」「正在规划路线...」）
- 移动端：单列全屏对话流，行程预览为底部抽屉

### 4.3 行程结果页
- Tab切换：时间线视图 / 地图视图 / 预算视图
- 时间线：每日卡片（景点+交通+住宿），支持展开/折叠
- 地图：全行程路线 + POI标注，支持点击查看详情
- 预算：分类饼图 + 明细表格
- 操作栏：分享、导出PDF、收藏、继续对话优化
- 移动端：底部Tab切换视图，卡片竖向排列

### 4.4 个人中心
- 历史行程列表（按时间排序，支持搜索）
- 个人偏好设置（出行风格、预算偏好、住宿偏好等）
- 收藏夹（收藏的景点、酒店、攻略）
- 账户设置

---

## 5. 技术架构

### 5.1 技术选型

| 层级 | 选型 | 理由 |
|------|------|------|
| **前端** | Next.js 14 (App Router) + TypeScript | RSC 流式渲染，契合 Generative UI |
| **UI** | Tailwind CSS + shadcn/ui | 原子化组件，响应式，移动端适配 |
| **Agent 服务** | Python FastAPI | AI 生态成熟，LangChain/LangGraph 支持 Agent Teams 编排 |
| **Agent 框架** | 自研 Orchestrator + ReAct Loop | 轻量、可控，无外部框架依赖 |
| **AI 引擎** | DeepSeek API（OpenAI 兼容） | 性价比高，中文能力强 |
| **短期记忆** | 内存 Session + LLM 压缩摘要 | MVP 阶段，后续可换 Redis |
| **长期存储** | 内存 Profile（MVP） | 后续迁移 PostgreSQL |
| **知识库** | 内存 RAG（MVP） | 后续迁移 pgvector |
| **消息队列** | asyncio.gather 并行 | MVP 阶段，后续可换 Redis Streams |
| **部署** | PM2 + Nginx（LightNode Tokyo） | 前后端同机，nginx 反向代理 |
| **未来 App** | Capacitor | Web → 原生 App，最低成本 |

### 5.2 SSE 数据流架构

```
Agent Tool执行 → result.data (含 tool_data)
    │
    ├─ SSE agent_result 事件 → data 字段包含完整 result.data
    │
    ├─ ui_mapper.py → 提取 tool_data → 发 ui_component SSE 事件
    │   (transport→flight_card, hotel→hotel_card, poi→poi_card,
    │    weather→weather_card, itinerary→timeline_card, budget→budget_chart)
    │
    └─ _synthesize() → truncate_tool_data → 加入合成 prompt

前端接收：
    ChatContainer.tsx
    ├─ agent_result → dispatchAgentData() → TravelPlanContext
    ├─ ui_component → appendUIPayload() → 消息内嵌卡片
    └─ done → SET_SESSION + sessionStorage 持久化

    ItinerarySidebar.tsx ← useTravelPlan() ← TravelPlanContext
    (实时渲染航班/酒店/天气/POI/日程/预算)

    /itinerary/[id] ← sessionStorage("travel_plan_" + id)
```

### 5.3 项目结构

```
travel-agent/
├── web/                          # Next.js 前端
│   ├── app/
│   │   ├── page.tsx              # 首页
│   │   ├── chat/page.tsx         # 对话页
│   │   ├── itinerary/[id]/       # 行程结果页
│   │   ├── profile/              # 个人中心
│   │   └── api/                  # BFF 接口（代理转发）
│   ├── components/
│   │   ├── chat/                 # 对话组件
│   │   ├── cards/                # 原子化卡片组件
│   │   │   ├── FlightCard.tsx
│   │   │   ├── HotelCard.tsx
│   │   │   ├── POICard.tsx
│   │   │   ├── WeatherCard.tsx
│   │   │   ├── BudgetChart.tsx
│   │   │   └── TimelineCard.tsx
│   │   ├── map/                  # 地图组件
│   │   └── ui/                   # shadcn/ui 基础组件
│   └── lib/
│       ├── stream.ts             # 流式渲染工具
│       └── api-client.ts         # Agent 服务请求
│
├── agent/                        # Python Agent 服务
│   ├── main.py                   # FastAPI 入口
│   ├── orchestrator/             # 主控 Agent
│   │   ├── agent.py              # Orchestrator 核心逻辑
│   │   ├── context.py            # 记忆压缩（近2轮原文+旧对话摘要）
│   │   ├── state_extractor.py    # 旅行参数提取（LLM+启发式）
│   │   ├── planner.py            # 任务拆解 (Decomposition)
│   │   ├── reflector.py          # 自我反思 (Reflection)
│   │   └── router.py             # 模型路由策略
│   ├── teams/                    # 专业 Agent 团队
│   │   ├── transport.py          # 交通专家
│   │   ├── hotel.py              # 住宿专家
│   │   ├── poi.py                # 目的地专家
│   │   ├── itinerary.py          # 行程编排师
│   │   ├── budget.py             # 预算管家
│   │   ├── knowledge.py          # 知识顾问
│   │   ├── weather.py            # 天气助手
│   │   └── customer_service.py   # 客服专家
│   ├── tools/                    # 三层工具体系
│   │   ├── mcp/                  # 原子工具 (MCP)
│   │   │   ├── flight_search.py
│   │   │   ├── hotel_search.py
│   │   │   ├── poi_search.py
│   │   │   ├── weather_api.py
│   │   │   ├── map_service.py
│   │   │   └── currency.py
│   │   └── skills/               # 组合技能 (Skills)
│   │       ├── transit_optimizer.py
│   │       ├── budget_allocator.py
│   │       └── itinerary_optimizer.py
│   ├── memory/                   # 记忆系统
│   │   ├── session.py            # 短期记忆（上下文压缩、槽位化）
│   │   ├── profile.py            # 长期记忆（用户画像）
│   │   ├── knowledge.py          # 知识库 (RAG)
│   │   └── state_pool.py         # 全局状态池
│   ├── simulator/                # 模拟演练系统
│   │   ├── user_simulator.py     # 用户模拟器
│   │   ├── env_simulator.py      # 环境模拟器
│   │   └── evaluator.py          # AI 裁判评估
│   └── config/
│       ├── prompts/              # 各 Agent 的 System Prompt
│       └── settings.py           # 配置
│
├── docs/
│   ├── PRD.md
│   └── CONTEXT.md
├── docker-compose.yml
└── README.md
```

---

## 6. 数据模型

### 6.1 用户表 (users)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| email | VARCHAR | 邮箱 |
| name | VARCHAR | 昵称 |
| avatar_url | VARCHAR | 头像 |
| created_at | TIMESTAMP | 注册时间 |

### 6.2 用户画像表 (user_profiles)
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | UUID | 关联用户 |
| travel_style | JSONB | 出行风格偏好（冒险/休闲/文艺...） |
| budget_preference | VARCHAR | 预算偏好（经济/舒适/奢华） |
| accommodation_pref | JSONB | 住宿偏好（品牌/类型/设施） |
| transport_pref | JSONB | 交通偏好（直飞/经济/时间优先） |
| dietary_restrictions | JSONB | 饮食限制 |
| accessibility_needs | JSONB | 无障碍需求 |
| history_summary | TEXT | 历史行为摘要（定期压缩更新） |

### 6.3 会话表 (sessions)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 关联用户 |
| title | VARCHAR | 会话标题（自动生成） |
| status | VARCHAR | active / archived |
| context_summary | TEXT | 上下文摘要（自动压缩） |
| state_pool | JSONB | 全局状态池（目的地、日期、人数、预算等） |
| created_at | TIMESTAMP | 创建时间 |

### 6.4 消息表 (messages)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| session_id | UUID | 关联会话 |
| role | VARCHAR | user / assistant / system |
| content | TEXT | 文本内容 |
| ui_payload | JSONB | Generative UI 组件数据 |
| agent_trace | JSONB | Agent执行轨迹（用于调试和评测） |
| created_at | TIMESTAMP | 时间戳 |

### 6.5 行程表 (itineraries)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| session_id | UUID | 关联会话 |
| user_id | UUID | 关联用户 |
| title | VARCHAR | 行程标题 |
| destination | VARCHAR | 目的地 |
| start_date | DATE | 出发日期 |
| end_date | DATE | 结束日期 |
| travelers | JSONB | 出行人信息 |
| total_budget | DECIMAL | 总预算 |
| status | VARCHAR | draft / confirmed / in_progress / completed |
| version | INT | 版本号（支持历史回退） |

### 6.6 日程明细表 (itinerary_days)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| itinerary_id | UUID | 关联行程 |
| day_number | INT | 第几天 |
| date | DATE | 具体日期 |
| items | JSONB | 当日安排（景点/交通/住宿/餐饮，含时间、费用） |
| weather_info | JSONB | 天气信息 |
| tips | TEXT | 当日贴士 |

### 6.7 Agent执行记录表 (agent_traces)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| session_id | UUID | 关联会话 |
| message_id | UUID | 关联消息 |
| agent_name | VARCHAR | 执行的Agent名称 |
| action | VARCHAR | 执行的动作 |
| input_params | JSONB | 输入参数 |
| output_result | JSONB | 输出结果 |
| status | VARCHAR | success / failed / retried |
| duration_ms | INT | 耗时(ms) |
| reflection | TEXT | 反思/纠错记录 |
| created_at | TIMESTAMP | 时间戳 |

---

## 7. API 设计

### 7.1 对话接口（流式）

```
POST /api/chat/stream
Content-Type: application/json

Request:
{
  "session_id": "uuid",       // 可选，新对话不传
  "message": "春节带爸妈去日本5天，预算2万",
  "attachments": []            // 图片/文件附件
}

Response: Server-Sent Events (SSE)
event: thinking
data: {"agent": "orchestrator", "thought": "用户想春节带父母去日本..."}

event: agent_start
data: {"agent": "transport", "task": "搜索春节直飞日本航班"}

event: agent_start
data: {"agent": "weather", "task": "查询1-2月日本天气"}

event: ui_component
data: {"type": "flight_card", "status": "loading", "skeleton": true}

event: ui_component
data: {"type": "flight_card", "status": "loaded", "data": {...}}

event: text
data: {"content": "为您找到以下方案..."}

event: done
data: {"session_id": "uuid", "itinerary_id": "uuid"}
```

### 7.2 行程 CRUD

```
GET    /api/itineraries              # 用户行程列表
GET    /api/itineraries/:id          # 行程详情
PUT    /api/itineraries/:id          # 手动编辑行程
DELETE /api/itineraries/:id          # 删除行程
POST   /api/itineraries/:id/export   # 导出PDF
POST   /api/itineraries/:id/share    # 生成分享链接
```

### 7.3 用户画像

```
GET    /api/profile                  # 获取用户画像
PUT    /api/profile                  # 更新偏好设置
GET    /api/profile/history          # 历史行程摘要
```

### 7.4 Agent调试（内部）

```
GET    /api/debug/traces/:session_id     # 查看Agent执行轨迹
POST   /api/debug/simulate               # 触发模拟演练
GET    /api/debug/evaluate/:session_id   # 查看AI裁判评分
```

---

## 8. 指标体系

### 8.1 北极星指标
| 指标 | 定义 | 目标 |
|------|------|------|
| 多轮对话渗透率 | 进行3轮+对话的用户占比 | >50% |
| 行程生成完成率 | 成功生成完整行程的会话占比 | >80% |
| 用户7日留存率 | 7天内回访用户占比 | >30% |

### 8.2 过程指标

**意图理解层：**
- 意图->Agent路由准确率 >95%
- 槽位填充准确率 >90%
- 多轮对话意图连贯率 >90%

**Agent调度层：**
- Agent/工具调用成功率（无报错） >95%
- 子任务并行效率（平均并行度） >2.5
- 端到端响应时间（首token） <3s

**记忆与知识层：**
- 上下文连贯度（10轮+无折损） >85%
- 长期记忆命中率（个性化推荐采纳率） >40%
- 知识库准确率 >95%

**输出质量：**
- 行程结果3分率（满意/非常满意） >60%
- 行程结果2分率（可用） >85%

---

## 9. 非功能需求

| 维度 | 要求 |
|------|------|
| **性能** | 首token响应 <3s，完整行程生成 <30s |
| **并发** | 支持 1000 并发会话 |
| **可用性** | 99.9% SLA |
| **安全** | 用户数据加密存储，对话内容不用于模型训练 |
| **可观测** | Agent执行全链路Trace，异常自动告警 |
| **移动适配** | 所有页面响应式设计，支持 PWA |
| **国际化** | 初期中文，架构预留 i18n |
