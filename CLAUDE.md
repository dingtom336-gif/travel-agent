# TravelMind Agent - 项目 CLAUDE.md

## 技术栈
- **后端**: Python 3.9+ / FastAPI 0.115 / DeepSeek API (OpenAI兼容)
- **前端**: Next.js 16 / React 19 / TypeScript 5 / Tailwind CSS 4
- **地图**: Leaflet 1.9 + react-leaflet 5
- **验证**: Pydantic v2 (后端) / Zod 4 (前端)
- **流式**: SSE (sse-starlette)
- **测试**: pytest (200 tests, asyncio_mode=auto) / Playwright (E2E)

## 项目结构
```
agent/           # Python FastAPI 后端
  main.py        # 入口 (POST /api/chat/stream, GET /health)
  orchestrator/  # 中枢：ReAct循环、任务规划、反思、合成
  teams/         # 8个专家Agent (transport/hotel/poi/itinerary/budget/knowledge/weather/customer_service)
  llm/           # DeepSeek客户端 + 限流
  memory/        # SessionMemory / StatePool / ProfileManager / KnowledgeBase
  tools/         # MCP原子工具 + 复合Skills
  simulator/     # 对战评测系统 (5人设×3场景×6D评分)
  config/        # 设置 + 系统提示词
web/             # Next.js 前端
  app/           # App Router 页面 (/, /chat, /itinerary/[id], /profile, /debug/simulator)
  components/    # chat/ cards/ map/ ui/ profile/ simulator/
  lib/           # types, schemas, api-client, hooks
tests/           # pytest 单元+集成测试
tests/e2e/       # Playwright E2E 测试
scripts/         # smoke_test.py 冒烟测试
docs/            # PRD.md, CONTEXT.md
```

## 部署信息
- **生产服务器**: 腾讯云上海 150.158.192.237 (ubuntu用户，SSH密钥登录)
- **进程管理**: PM2
- **前端**: PM2:3003 → nginx `/travel`
- **后端**: PM2:8000 → nginx `/travel-api/`
- **项目路径(生产)**: `/opt/travel-agent`
- **本地开发**: 前端 3001, 后端 8000
- **GitHub**: github.com/dingtom336-gif/travel-agent

## 常用命令
```bash
# 后端
cd agent && ../agent/venv2/bin/python -m uvicorn main:app --reload --port 8000
./agent/venv2/bin/python -m pytest tests/ -v

# 前端
cd web && npm run dev      # 开发 (port 3001)
cd web && npm run build    # 构建

# 冒烟测试
./agent/venv2/bin/python scripts/smoke_test.py

# E2E测试
npx playwright test tests/e2e/

# 生产部署
ssh ubuntu@150.158.192.237 "cd /opt/travel-agent && git pull && cd web && npm run build && cd .. && pm2 restart all"
```

## 代码规范
- Python: PEP 8, 2空格缩进, 全async/await, try/catch必须
- TypeScript: React 19 hooks, React.memo包裹cards, Zod运行时校验
- 单文件 ≤ 500行
- const/let, 禁止var
- 对话中文, 代码注释英文, commit message中文

## 架构关键决策
- **ReAct循环**: Orchestrator → Planner(DAG分解) → ReactEngine(并行执行) → Reflector(R1验证) → Synthesizer(流式输出)
- **Agent模板方法**: BaseAgent.execute() → _run_tools → _build_prompt → _call_claude → _post_process
- **内存全异步**: asyncio.Lock保护, SessionMemory 2h TTL, StatePool全局参数
- **DeepSeek并发限制**: 最多3并发, stagger延迟防429
- **SSE事件类型**: thinking / agent_start / agent_result / text / ui_component / done

## 环境变量 (.env)
- `DEEPSEEK_API_KEY` (必需)
- `CORS_ORIGINS` (生产覆盖)

## 已知问题
- 1个预存在测试失败: test_sse_pipeline (sse-starlette事件循环)
- 工具层全mock, 无真实航班/酒店API
- 内存存储: 全in-memory, 未迁移数据库
