## 当前状态
**v0.8.0 本地就绪。** PostgreSQL已安装(Postgres.app 18.1)+Alembic迁移完成(9表)+CRUD API+Serper搜索+拖拽编辑+PDF导出+主动服务。200/200测试通过。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-11 | Phase 1-5: DB+API+前端+Serper+拖拽/PDF/主动服务 | 🖥️终端 |
| 2 | 2026-02-12 | 安装Postgres.app(PG 18.1)+创建travelmind库 | 🖥️终端 |
| 3 | 2026-02-12 | 修复DATABASE_URL(xiaozhang用户)+alembic upgrade head(9表) | 🖥️终端 |
| 4 | 2026-02-12 | 版本号升级至v0.8.0 | 🖥️终端 |

## 踩坑记录
- **【致命】5并发DeepSeek触发429**：减为4个+stagger解决
- **【重要】sse-starlette AppStatus泄漏**：autouse fixture重置解决
- **【注意】Postgres.app用OS用户**：DATABASE_URL需用xiaozhang@localhost而非postgres:postgres

## 未完成事项
- [ ] 配置SERPER_API_KEY环境变量启用真实搜索
- [ ] 生产部署v0.8.0(含PostgreSQL安装+alembic迁移)

## 环境备忘
- **本地**：`~/Desktop/claude-test/travel-agent/`，前端3001，后端8000
- **本地PG**：Postgres.app 18.1，端口5432，用户xiaozhang，库travelmind
- **生产**：38.54.88.144，前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
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
- v0.8.0 Phase 0-5 开发完成 (02-11)
