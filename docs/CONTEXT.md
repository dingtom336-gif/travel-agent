## 当前状态
**v0.9.2 已部署生产。** 深度推理优先模式 + Synthesizer 空响应修复。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-03-25 | 深度推理优先：search 不再截断 + 默认开启 + Synthesizer 空响应修复 | 🚀功能+🔧修复 |
| 2 | 2026-03-25 | 混合20题评测：90%通过 4.10/5 复杂题全满分 | 🧪评测 |
| 3 | 2026-03-25 | search_handler.py 引号语法修复 + 导入路径修复 + 本地环境恢复 | 🔧修复 |
| 4 | 2026-03-24 | 深度推理按钮+搜索意图修复+FlyAI集成+workers修复 | 🚀功能 |
| 5 | 2026-03-22 | Aurora Ether UI 全量重构：27个文件换肤（暗色+毛玻璃+渐变），已部署生产 | 🎨重构 |

## 双模式架构 (2026-03-25 更新)
- **深度推理优先**（默认开启）：所有查询走完整 ReAct 管线（Planner→6Agent→Reflector→Synthesizer）
- **Theater 模式**（手动关闭深度推理时）：单次 Mega-LLM 快速响应，search 快速路径可用
- **前端开关**：首页搜索栏+聊天页输入框上方，localStorage 持久化，默认勾选
- **search 快速路径**：仅在 Theater 模式（深度推理关闭）时生效

## FlyAI 集成 (2026-03-24)
- **数据源优先级**：FlyAI → Amap → Serper → Mock（三个工具统一）
- **新增文件**：`agent/tools/flyai/`（client.py + adapters.py），`agent/orchestrator/search_handler.py`
- **体验 key 限制**：不返回真实价格，用飞行时长/星级估算
- **生产网络**：flyai.open.fliggy.com 从腾讯云直连可达（无需代理）

## 已知问题
- [ ] 简单查询走 ReAct 耗时偏长（40-70s vs Theater 1s）→ 考虑 Planner 对简单查询减少 Agent 数
- [ ] FlyAI 正式 key 申请（解锁真实价格）→ [open.fly.ai](https://open.fly.ai/)
- [ ] SiliconFlow API 余额确认（阻塞200题评测）
- [ ] 航班搜索结果去重（AQ1002 重复3次）
- [ ] 评分器关键词过窄（边界场景/事实纠正类误报）
- [x] Synthesizer 空响应（timeout 检查后移 + fallback 兜底，已修复 2026-03-25）
- [x] 深度推理模式 search 截断（已改为深度推理优先 2026-03-25）
- [x] search_handler.py 引号语法+导入路径（已修复 2026-03-25）

## 环境备忘
- **本地**：`~/Desktop/new_start/claude-code/travel-agent/`，前端3001，后端8000
- **生产**：150.158.192.237（腾讯云上海），前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **⚠️ uvicorn workers=1**：in-memory state 不支持多 worker，勿改回 2
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：GLM-5(reasoning) + GLM-4-32B(writing)，SiliconFlow API
- **测试**：205 passed，`./agent/venv2/bin/python -m pytest tests/ -v`
