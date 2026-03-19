## 当前状态
**v0.8.0 线上运行 + v0.9.0 本地开发中（速度+上下文+评测体系）。** Theater Mode 两阶段流水线 + SiliconFlow GLM-5/GLM-4-32B。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-03-19 | V2评测系统200题+5维评分引擎+运行器，已跑部分baseline | 📊评测 |
| 2 | 2026-03-19 | 速度优化6文件改造(超时/快速路径/无LLM摘要/running summary) | ⚡优化 |
| 3 | 2026-03-19 | 空响应fallback安全网+转化闭环提示词增强 | 🔧修复 |
| 4 | 2026-03-19 | 隐式意图+情绪感知+Theater UI卡片+天气字段兼容 已部署 | 🚀部署 |
| 5 | 2026-02-23 | 迁移至腾讯云上海150.158.192.237 | 🚀部署 |

## v0.9.0 改动文件清单（本地未提交）
- `agent/config/settings.py` — Stage1超时25s/15s, LLM_TIMEOUT 30s
- `agent/memory/session.py` — running summary API (_summaries/get_summary/update_summary)
- `agent/orchestrator/context.py` — fast_summarize + update_running_summary (无LLM)
- `agent/orchestrator/theater.py` — mega_prompt传summary参数 + 近2轮500字 + incremental放宽 + 空响应安全网
- `agent/orchestrator/agent.py` — _update_summary_safe 3路径调用
- `agent/orchestrator/router.py` — 扩大本地快速路径 + 目的地直跳plan
- `agent/config/mega_prompt.py` — 服务闭环要求 + clarify推进感
- `tests/test_orchestrator.py` — 3个context测试待修（context重写导致断言过时）

## 评测baseline（部分完成）
| 范围 | 类别 | 通过率 | 平均分 | 状态 |
|------|------|:------:|:------:|------|
| T101-110 | 行中即时 | 90% | 3.90 | ✅ |
| T111-120 | 行中即时 | 60% | 3.14 | ✅ |
| T161-170 | 交易决策 | 80% | 3.71 | ✅ |
| T171-180 | 鲁棒性 | 88% | 3.59 | ✅ |
| T1-40 | 基础事实 | — | — | ⏳ |
| T41-100 | 多约束规划 | — | — | ⏳ |
| T121-160 | 行中+交易 | — | — | ⏳ |
| T181-200 | 鲁棒性 | — | — | ⏳ |

## 已发现系统性问题
1. **空响应(0字)** — T101/T113/T161/T180, Stage1超时fallback链断裂 → **已修复(待部署)**
2. **转化/闭环弱** — 全局2.9-3.0分 → **提示词已增强(待部署)**
3. **平台业务知识缺失** — T168飞猪闪住等概念模型不懂
4. **答非所问** — T112/T119字多但偏题，模型走了错误推理路径

## 未完成事项
- [ ] 3个失败测试修复（context重写导致）
- [ ] 全部代码commit + push + 部署
- [ ] 评测baseline跑完（剩余~120题）
- [ ] 部署后跑评测对比 before/after

## 环境备忘
- **本地**：`~/Desktop/new_start/claude-code/travel-agent/`，前端3001，后端8000
- **生产**：150.158.192.237（腾讯云上海），前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **生产用户**：ubuntu (sudo)，SSH密钥已配置
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：GLM-5(reasoning) + GLM-4-32B(writing)，SiliconFlow API
- **评测系统**：tests/e2e/eval_200.json + eval_v2_scoring.py + run_eval_200.py
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（199/202通过，3个待修）
