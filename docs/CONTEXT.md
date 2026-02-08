## 当前状态
**R1反思+Router修复+多专家协作恢复。** reflector用R1推理模型；router改进prompt+上下文感知，解决follow-up误判simple；llm_chat支持model参数。19测试通过。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-08 | 性能优化6步：max_tokens+并行+反思条件+超时+流式synthesis+重试 | 🖥️终端 |
| 2 | 2026-02-08 | 修复推理步骤0步bug（4处改动）+反思验证反馈 | 🖥️终端 |
| 3 | 2026-02-08 | R1反思+Router修复：5文件改动，多专家+右侧面板数据流恢复 | 🖥️终端 |
| 4 | 2026-02-08 | Footer添加版本号v0.3.0，弱化展示 | 🖥️终端 |

## 未完成事项
- [ ] 部署到生产服务器并验证
- [ ] E2E验证："塞尔维他5天游"反思纠错（R1）仍正常
- [ ] E2E验证：多轮对话follow-up走complex路径

## 环境备忘
- **本地开发**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **生产服务器**：38.54.88.144 (LightNode Tokyo, Ubuntu 22.04)
  - 前端：http://38.54.88.144/travel（PM2: travel-frontend, port 3003）
  - 后端API：http://38.54.88.144/travel-api/（PM2: travel-backend, port 8000）
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **更新流程**：`ssh → cd /opt/travel-agent && git pull → pm2 restart travel-backend`
- **AI引擎**：DeepSeek V3（deepseek-chat）+ R1（deepseek-reasoner，仅反思）
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（19个测试，零token）

## 核心文件索引
| 模块 | 关键文件 |
|------|---------|
| LLM 客户端 | `agent/llm/client.py` (llm_chat + llm_chat_stream + model参数 + 重试) |
| 配置 | `agent/config/settings.py` (DEEPSEEK_MODEL + DEEPSEEK_REASONER_MODEL) |
| Orchestrator | `agent/orchestrator/agent.py` (并行+流式synthesis+has_travel_context) |
| 反思引擎 | `agent/orchestrator/reflector.py` (R1模型) |
| 路由 | `agent/orchestrator/router.py` (改进prompt+上下文感知) |
| 状态提取 | `agent/orchestrator/state_extractor.py` |

## 历史归档
- Wave 1-8 (2026-02-07)：PRD → 前端+后端+地图+UI审查+DeepSeek集成
- SSE/超时/记忆/数据流修复 (2026-02-08)：多轮修复+12测试+部署
- 推理步骤UI重构 (2026-02-08)：ThinkingSteps.tsx新组件+ChatContainer改造+部署
- 三层反思机制 (2026-02-08)：Layer0纠错+Layer1规则+Layer2 LLM审查+7新测试+部署
