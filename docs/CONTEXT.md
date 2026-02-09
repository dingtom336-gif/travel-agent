## 当前状态
**v0.7.0 性能优化完成。** 本地测试 199/200 通过（1个预存在失败）。待部署验证。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-10 | v0.7.0 全部11项改动实现完毕，测试199/200通过 | 🖥️终端 |
| 2 | 2026-02-10 | 新建intent_classifier.py(本地分类<1ms)替换LLM Router(~20s) | ⚙️配置 |
| 3 | 2026-02-10 | synthesis流式化+planner启发式+agent立即SSE+TIMING日志 | 🖥️终端 |
| 4 | 2026-02-10 | reflector恢复R1模型+JSON解析增强+目的地误报修复 | 🖥️终端 |
| 5 | 2026-02-10 | 闭环铁律固化到CLAUDE.md+self-test.md(含反死循环保护) | ⚙️配置 |

## 踩坑记录
- **【重要】组件无上下文模式**：修一个组件上下文缺失时，必须排查同管道所有组件
- **【致命】先查日志再改代码**：已固化到CLAUDE.md强制规则
- **【新】heuristic拦截破坏旧测试**：planner启发式拦截旅行消息导致mock LLM路径跑不到，需传previous_tasks强制LLM路径

## 未完成事项
- [ ] 部署v0.7.0到生产并运行smoke_test.py
- [ ] 1个预存在测试失败(test_sse_pipeline, sse-starlette事件循环问题)

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3(主) + R1(反思)
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（200测试）

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0 并发安全+Agent模板化+Orchestrator拆分+前端重构+195测试 (02-09)
- v0.6.1 错误的信号量优化→v0.6.2 回滚修复+自测规范强化 (02-09~10)
