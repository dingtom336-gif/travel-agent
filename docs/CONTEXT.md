## 当前状态
**v0.6.2 修复信号量导致的卡死。** 移除并发信号量+恢复超时+恢复全并行。保留RPM 300、Router快速路径、Reflection短路、MAX_RETRIES=2。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-09 | v0.6.1 并发信号量导致卡死，反思后回滚 | 📋决策 |
| 2 | 2026-02-09 | v0.6.2 移除信号量+分批启动，恢复全并行asyncio.gather | 🖥️终端 |
| 3 | 2026-02-09 | 恢复LLM_TIMEOUT=30s, TASK_TIMEOUT=45s (20s太短) | 🖥️终端 |
| 4 | 2026-02-09 | 保留有效优化：RPM300/Router快速路径/Reflection短路/RETRIES=2 | 🖥️终端 |

## 踩坑记录
- **【重要】信号量+分批执行是反模式**：DeepSeek响应需要15-25s，信号量=3会把并行Agent串行化，总延迟从20s变成60s+。429重试是正常行为，由OpenAI SDK自动处理，不需要限制并发。
- **不要把HTTP超时降到DeepSeek响应时间以下**：DeepSeek V3正常响应15-25s，LLM_TIMEOUT=20s会触发大量误超时。

## 未完成事项
- [ ] 1个预存在测试失败(test_sse_pipeline, sse-starlette事件循环问题)
- [ ] 部署v0.6.2到生产并E2E验证

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3（反思也改用V3，不再用R1）
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（195测试）

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0 T1~T4 并发安全+Agent模板化+Orchestrator拆分+前端重构+195测试 (02-09)
- v0.6.1 错误的信号量优化导致卡死 (02-09)
