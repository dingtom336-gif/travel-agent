## 当前状态
**v0.8.0 生产部署完成。** PostgreSQL持久化(本地+生产)+CRUD API+Serper搜索+拖拽编辑+PDF导出+主动服务。200/200测试通过。SSE流+4 agent并行验证通过。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-12 | 本地：修复DATABASE_URL+alembic迁移+版本号v0.8.0 | 🖥️终端 |
| 2 | 2026-02-12 | 生产：安装PostgreSQL 14+创建travelmind库+设postgres密码 | 🖥️终端 |
| 3 | 2026-02-12 | 生产：git pull+pip install依赖+alembic upgrade(9表) | 🖥️终端 |
| 4 | 2026-02-12 | 生产：npm build+PM2 restart+冒烟测试通过(health+CRUD+SSE) | 🖥️终端 |

## 踩坑记录
- **【致命】5并发DeepSeek触发429**：减为4个+stagger解决
- **【重要】sse-starlette AppStatus泄漏**：autouse fixture重置解决
- **【注意】本地vs生产DB用户不同**：本地xiaozhang@localhost，生产postgres:postgres@localhost，通过.env覆盖

## 未完成事项
- [ ] 配置SERPER_API_KEY环境变量启用真实搜索

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **本地PG**：Postgres.app 18.1，端口5432，用户xiaozhang，库travelmind
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **生产PG**：PostgreSQL 14.20，端口5432，用户postgres，库travelmind
- **生产venv**：`/opt/travel-agent/venv/`
- **项目路径(生产)**：`/opt/travel-agent`
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3(主) + R1(反思)
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（200测试）

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0~v0.6.2 并发安全+Agent模板化+自测规范强化 (02-09~10)
- v0.7.0 性能优化11项(intent_classifier/streaming/heuristic/TIMING) (02-10)
- v0.7.1 生产部署验证+smoke test修复+Claude Code初始化 (02-10~11)
- v0.8.0 Phase 0-5 开发+本地PG配置 (02-11~12)
