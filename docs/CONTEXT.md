## 当前状态
**v0.6.1 性能修复完成。** 修复Agent失败(并发限流+信号量) + 推理速度优化(Router快速路径+分批启动+Reflector改用chat模型)。195测试(194通过)。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-09 | Fix1: 并发限流 LLM_MAX_CONCURRENT=3 + RPM 60→300 + 信号量 | 🖥️终端 |
| 2 | 2026-02-09 | Fix2: Reflection短路(成功<2跳过) + consistency_checker改用chat模型 | 🖥️终端 |
| 3 | 2026-02-09 | Fix3: Router快速路径(有travel context跳过LLM) | 🖥️终端 |
| 4 | 2026-02-09 | Fix4: 超时调优 LLM_TIMEOUT 30→20, TASK_TIMEOUT 45→30, RETRIES 1→2 | 🖥️终端 |
| 5 | 2026-02-09 | Fix5: Agent分批启动(batch=3, stagger=200ms) | 🖥️终端 |

## 未完成事项
- [ ] 1个预存在测试失败(test_sse_pipeline, sse-starlette事件循环问题)
- [ ] 部署v0.6.1到生产并E2E验证

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3（反思也改用V3，不再用R1）
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（195测试）
- **CORS**：默认 localhost:3000/3001，生产通过 CORS_ORIGINS 环境变量覆盖

## 核心文件索引
| 模块 | 关键文件 |
|------|---------|
| Orchestrator | agent.py + react_loop.py + synthesis.py + constants.py |
| LLM限流 | rate_limiter.py(信号量+令牌桶) + client.py(LRU+重试) |
| Memory并发 | session.py/state_pool.py/profile.py 全部async+Lock |

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- SSE/超时/记忆/数据流/推理UI/三层反思/性能优化/Router修复/中文化 (02-08)
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0 T1~T4 并发安全+Agent模板化+Orchestrator拆分+前端重构+195测试 (02-09)
