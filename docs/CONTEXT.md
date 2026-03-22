## 当前状态
**v0.9.0 已部署生产。** 代码修复全部完成，但 **SiliconFlow API 余额为 0**，评测数据无效需充值后重跑。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-03-20 | 安全拒绝直接返回+分类拒绝+评分引擎refuse修正，已部署 | 🔧修复 |
| 2 | 2026-03-20 | T198事实纠正快速路径+T171-200 golden keys扩展，已部署 | 🔧修复 |
| 3 | 2026-03-20 | 发现SiliconFlow API余额为0，所有LLM返回MOCK | ⚠️阻塞 |
| 4 | 2026-03-19 | V2评测系统200题+速度优化+空响应安全网+转化闭环增强 | ⚡优化 |
| 5 | 2026-03-19 | 隐式意图+情绪感知+Theater UI卡片+天气字段兼容 已部署 | 🚀部署 |

## v0.9.0 已提交改动
- `agent/orchestrator/agent.py` — unsafe直接拒绝路径（不走LLM）
- `agent/orchestrator/synthesis.py` — 分类拒绝(隐私/诈骗/冒充) + _UNSAFE_REQUEST_KW扩展
- `agent/orchestrator/router.py` — 事实纠正快速路径 + 扩大本地快速路径
- `agent/simulator/eval_v2_scoring.py` — refuse类题accuracy≥4 + SAFETY_REFUSAL_KW扩展
- `tests/e2e/eval_200.json` — T171-200 golden_keys扩展至6-10个
- `tests/test_orchestrator.py` — 新增事实纠正分类测试
- `agent/config/settings.py` — Stage1超时25s/15s
- `agent/orchestrator/theater.py` — 空响应安全网 + incremental放宽
- `agent/config/mega_prompt.py` — 服务闭环要求

## 评测状态（全部需充值后重跑）
之前的评测数据因API余额为0返回MOCK响应，**全部无效**。充值后需重跑全部200题。

## 未完成事项
- [ ] **SiliconFlow API 充值**（阻塞项）
- [ ] 充值后重跑全部200题评测
- [ ] before/after 对比验证

## 环境备忘
- **本地**：`~/Desktop/new_start/claude-code/travel-agent/`，前端3001，后端8000
- **生产**：150.158.192.237（腾讯云上海），前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **生产用户**：ubuntu (sudo)，SSH密钥已配置
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：GLM-5(reasoning) + GLM-4-32B(writing)，SiliconFlow API
- **评测系统**：tests/e2e/eval_200.json + eval_v2_scoring.py + run_eval_200.py
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（205 passed）
- **评测跑法**：`--server=http://150.158.192.237/travel-api`（走nginx，不是直连8000）
