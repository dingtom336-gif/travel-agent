## 当前状态
**v0.9.1 已部署生产。** FlyAI（飞猪）真实数据集成 + 深度推理双模式切换上线。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-03-25 | search_handler.py 引号语法修复（3处中文引号→书名号）+ 导入路径 session_memory→session | 🔧修复 |
| 2 | 2026-03-25 | 本地环境恢复（venv2重建+.env从腾讯云恢复+node_modules+web build）+ 三方代码同步验证 | 🔧修复 |
| 3 | 2026-03-25 | 深度推理20题评测启动中 | 🧪评测 |
| 4 | 2026-03-24 | 深度推理按钮+搜索意图修复+FlyAI集成+workers修复 | 🚀功能 |
| 5 | 2026-03-22 | Aurora Ether UI 全量重构：27个文件换肤（暗色+毛玻璃+渐变），已部署生产 | 🎨重构 |

## 双模式架构 (2026-03-24)
- **Theater 模式**（默认关闭深度推理）：单次 Mega-LLM 快速响应，适合简单对话和规划
- **ReAct 模式**（开启深度推理）：完整多 Agent 管线（Planner→8Agent→Reflector→Synthesizer）
- **前端开关**：首页搜索栏+聊天页输入框上方，localStorage 持久化
- **search 直达**：查航班/酒店/景点 → 直接调工具返回表格，不经 LLM 重写

## FlyAI 集成 (2026-03-24)
- **数据源优先级**：FlyAI → Amap → Serper → Mock（三个工具统一）
- **新增文件**：`agent/tools/flyai/`（client.py + adapters.py），`agent/orchestrator/search_handler.py`
- **体验 key 限制**：不返回真实价格，用飞行时长/星级估算
- **生产网络**：flyai.open.fliggy.com 从腾讯云直连可达（无需代理）

## 已知问题
- [ ] ReAct 模式 Synthesizer 丢失工具细节（航班号等）→ 需优化 prompt 或直通工具数据
- [ ] 深度推理模式20题评测进行中（2026-03-25）
- [ ] FlyAI 正式 key 申请（解锁真实价格）→ [open.fly.ai](https://open.fly.ai/)
- [ ] SiliconFlow API 余额确认（阻塞200题评测）
- [ ] 航班搜索结果去重（AQ1002 重复3次）
- [x] search_handler.py 引号语法错误（已修复 2026-03-25）
- [x] search_handler.py 导入路径错误 session_memory→session（已修复 2026-03-25）
- [x] 本地 venv2/.env 被误删（已从腾讯云恢复 2026-03-25）
- [x] 腾讯云 git 落后2个提交（已 git pull 同步 2026-03-25）

## 环境备忘
- **本地**：`~/Desktop/new_start/claude-code/travel-agent/`，前端3001，后端8000
- **生产**：150.158.192.237（腾讯云上海），前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **⚠️ uvicorn workers=1**：in-memory state 不支持多 worker，勿改回 2
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：GLM-5(reasoning) + GLM-4-32B(writing)，SiliconFlow API
- **测试**：205 passed，`./agent/venv2/bin/python -m pytest tests/ -v`
