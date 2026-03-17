## 当前状态
**v0.9.0 已部署至腾讯云上海。** 6个MCP工具全部接入真实数据源（高德+和风天气+fawazahmed0+增强mock），三层fallback保障可用性。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-02-23 | 迁移至腾讯云上海150.158.192.237，全量部署+验证通过 | 🚀部署 |
| 2 | 2026-02-13 | 天气工具接入和风天气(primary)+Open-Meteo(fallback) | 🌤️API |
| 3 | 2026-02-13 | POI+酒店接入高德POI搜索(type=100000) | 🗺️API |
| 4 | 2026-02-13 | 地图服务接入高德路线规划+共享geocoding | 🗺️API |
| 5 | 2026-02-13 | 汇率接入fawazahmed0实时汇率CDN | 💱API |

## 踩坑记录
- **【致命】git add捡到168文件删除**：commit前必须只add目标文件，不用git add -A
- **【致命】PEP 263编码检测**：Python前2行注释含`coding:`会触发编码解析，避免注释中出现
- **【致命】5并发DeepSeek触发429**：减为4个+stagger解决

## 未完成事项
- [ ] E2E验证：curl测"去东京5天"，确认source字段为真实API

## 环境备忘
- **本地**：`~/Desktop/new_start/claude-code/travel-agent/`，前端3001，后端8000
- **本地PG**：Postgres.app 18.1，端口5432，用户xiaozhang，库travelmind
- **生产**：150.158.192.237（腾讯云上海），前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **生产用户**：ubuntu (sudo)，SSH密钥已配置
- **生产venv**：`/opt/travel-agent/venv/`
- **项目路径(生产)**：`/opt/travel-agent`
- **GitHub**：github.com/dingtom336-gif/travel-agent
- **AI引擎**：DeepSeek V3(主) + R1(反思)
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（200测试）
- **部署命令**：`ssh ubuntu@150.158.192.237 "cd /opt/travel-agent && git pull && cd web && npm run build && cd .. && pm2 restart all"`

## MCP工具数据源矩阵
| 工具 | Primary | Fallback | Final | source字段 |
|------|---------|----------|-------|-----------|
| 天气 | 和风天气 | Open-Meteo | mock | qweather/open-meteo/mock |
| POI | 高德POI | Serper | mock | amap/serper/mock |
| 酒店 | 高德POI(100000) | Serper | mock | amap/serper/mock |
| 路线 | 高德路线规划 | 查找表 | Haversine | amap/lookup/estimate |
| 汇率 | fawazahmed0 CDN | - | hardcoded | fawazahmed0/hardcoded |
| 航班 | Serper(可能被墙) | - | 增强mock(65+航线) | serper/estimated |

## 历史归档
- Wave 1-8 (02-07)：PRD→前端+后端+地图+UI审查+DeepSeek集成
- v0.3.2~v0.5.1 POI/语义/GenUI/模拟器/连贯性修复 (02-08~09)
- v0.6.0~v0.6.2 并发安全+Agent模板化+自测规范强化 (02-09~10)
- v0.7.0 性能优化11项(intent_classifier/streaming/heuristic/TIMING) (02-10)
- v0.7.1 生产部署验证+smoke test修复+Claude Code初始化 (02-10~11)
- v0.8.0 Phase 0-5 开发+本地PG配置+SSE滚动修复+手机端适配 (02-11~12)
- v0.9.0-dev MCP工具真实API接入(高德+和风+fawazahmed0+增强mock) (02-13)
