## 当前状态
**v0.6.0 重构进行中。** T1.1~T1.4 全部完成，96测试通过。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-09 | T1.1 并发安全：三模块加 asyncio.Lock | 🖥️终端 |
| 2 | 2026-02-09 | T1.2 内存泄漏防护：TTL+LRU+trace上限 | 🖥️终端 |
| 3 | 2026-02-09 | T1.3 LLM层增强：LRU缓存 + 令牌桶速率限制 | 🖥️终端 |
| 4 | 2026-02-09 | T1.4 CORS收紧：默认白名单 localhost:3000/3001 | ⚙️配置 |

## 未完成事项
- [ ] orchestrator 调用方需更新为 await（后续任务）

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3 + R1（仅反思）
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（96测试）
- **CORS**：默认 localhost:3000/3001，生产通过 CORS_ORIGINS 环境变量覆盖

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- SSE/超时/记忆/数据流/推理UI/三层反思/性能优化/Router修复/中文化 (02-08)
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0 T1.1~T1.3 并发安全+内存泄漏+LLM增强 (02-09)
