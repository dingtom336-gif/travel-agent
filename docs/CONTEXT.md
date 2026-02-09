## 当前状态
**v0.5.1 模拟器发现三大问题修复完成。** 连贯性(Agent上下文注入+窗口扩展)、个性化(synthesis强制引用偏好)、Simple模式Trace记录、评分规则升级。19测试通过。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-09 | v0.5.1 Fix1: conversation_summary注入Agent上下文 + build_messages窗口10→20 | 🖥️终端 |
| 2 | 2026-02-09 | v0.5.1 Fix2: synthesis prompt强制个性化 + _build_personalization_instructions通用兜底 | 🖥️终端 |
| 3 | 2026-02-09 | v0.5.1 Fix3: _handle_simple添加trace记录(timing+agent+goal) | 🖥️终端 |
| 4 | 2026-02-09 | v0.5.1 Fix4: scoring_rules升级(tool_usage simple友好+personalization增强+coherence Q&A对齐) | 🖥️终端 |

## 未完成事项
- [ ] 重新跑全面模拟测试（5人格+3故障），验证评分提升
- [ ] 部署v0.5.1到生产并E2E验证

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **部署**：`ssh → cd /opt/travel-agent && git pull → pm2 restart travel-backend`
- **AI引擎**：DeepSeek V3 + R1（仅反思）
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（19测试）
- **模拟器密码**：`travelmind2026`，访问路径 `/debug/simulator`

## 核心文件索引
| 模块 | 关键文件 |
|------|---------|
| 连贯性修复 | `agent/orchestrator/agent.py` ← conversation_summary注入 |
| 上下文窗口 | `agent/orchestrator/context.py` ← build_messages 20条 |
| 评分规则 | `agent/simulator/scoring_rules.py` ← 3函数升级 |

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- SSE/超时/记忆/数据流/推理UI/三层反思/性能优化/Router修复/中文化 (02-08)
- v0.3.2 POI点击+真实地点+路线空间合理性 (02-08)
- v0.3.3 对话语义理解修复：extract_state注入history+existing_state (02-08)
- v0.4.0 Generative UI：react-markdown+卡片穿插文本+图片注入+RouteMap+BudgetChart (02-09)
- v0.5.0 世界模拟器：Fault Injection+Traces持久化+BattleRunner+Debug Console+6维雷达图 (02-09)
