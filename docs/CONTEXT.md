## 当前状态
**v0.6.0 Agent Teams 并行重构完成。** 4个Agent并行执行19个任务，全部完成。195测试(194通过)。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-09 | T2.4 State Extractor增强：AI上一问题注入槽位填充 | 🖥️终端 |
| 2 | 2026-02-09 | T2.5 Planner增量模式：follow-up复用上轮结果 | 🖥️终端 |
| 3 | 2026-02-09 | T4.2 Agent层测试：38测试覆盖BaseAgent+7子类 | 🖥️终端 |
| 4 | 2026-02-09 | T4.3 Orchestrator组件测试：44测试覆盖planner/router/extractor/context | 🖥️终端 |
| 5 | 2026-02-09 | T4.4 集成测试：17测试覆盖SSE管道+Orchestrator流程 | 🖥️终端 |

## 未完成事项
- [ ] 1个预存在测试失败(test_sse_pipeline::test_chat_stream_format_and_timing, _call_planner签名变更)
- [ ] 部署v0.6.0到生产并E2E验证

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3 + R1（仅反思）
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（195测试）
- **CORS**：默认 localhost:3000/3001，生产通过 CORS_ORIGINS 环境变量覆盖

## 核心文件索引
| 模块 | 关键文件 |
|------|---------|
| Orchestrator | agent.py(120行) + react_loop.py + synthesis.py + constants.py |
| Memory并发 | session.py/state_pool.py/profile.py 全部async+Lock |
| LLM缓存 | agent/llm/client.py(LRU) + rate_limiter.py(令牌桶) |
| 前端hooks | useSSEHandler.ts + useChatMessages.ts |
| SSE重连 | api-client.ts(retry+backoff) + ConnectionBanner.tsx |
| Zod校验 | web/lib/schemas.ts |

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- SSE/超时/记忆/数据流/推理UI/三层反思/性能优化/Router修复/中文化 (02-08)
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0 T1.1~T1.4 并发安全+内存泄漏+LLM增强+CORS (02-09)
- v0.6.0 T2.1~T2.3 Agent去重+模板化+Orchestrator拆分 (02-09)
- v0.6.0 T3.1~T3.5 ChatContainer/Message拆分+SSE重连+Zod+memo (02-09)
- v0.6.0 T4.1~T4.5 Memory/Agent/Orchestrator/集成/评分测试 (02-09)
