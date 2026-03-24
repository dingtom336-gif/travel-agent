## 当前状态
**v0.9.0 已部署生产。** FlyAI（飞猪）真实数据已集成，航班/酒店/景点搜索走飞猪实时数据。

## 最近操作记录
| # | 时间 | 操作摘要 | 类型 |
|---|------|---------|------|
| 1 | 2026-03-24 | FlyAI集成：工具层接入飞猪真实航班/酒店/景点数据，替换mock为最高优先级 | 🚀功能 |
| 2 | 2026-03-22 | Aurora Ether UI 全量重构：27个文件换肤（暗色+毛玻璃+渐变），已部署生产 | 🎨重构 |
| 3 | 2026-03-20 | 安全拒绝直接返回+分类拒绝+评分引擎refuse修正，已部署 | 🔧修复 |
| 4 | 2026-03-20 | 发现SiliconFlow API余额为0，所有LLM返回MOCK | ⚠️阻塞 |
| 5 | 2026-03-19 | V2评测系统200题+速度优化+空响应安全网+转化闭环增强 | ⚡优化 |

## Aurora Ether UI 重构 (2026-03-22)
- **设计系统**：深色底 #0c0e14 + 青蓝→靛紫渐变 + 毛玻璃面板
- **字体**：Inter(正文) + Plus Jakarta Sans(标题)，替换原 Geist
- **工具类**：glass-panel, aurora-glow, message-gradient, ghost-border, gradient-text, gradient-btn
- **Stitch 项目**：projects/15220985337847918774（8个屏幕，4页面×桌面+移动）
- **改动范围**：27个文件（4页面+6卡片+9聊天+2布局+4子组件+globals.css+layout.tsx）
- **逻辑层零改动**，纯视觉换肤

## FlyAI 集成 (2026-03-24)
- **数据源优先级**：FlyAI → Amap → Serper → Mock（三个工具统一）
- **新增文件**：`agent/tools/flyai/`（client.py + adapters.py）
- **体验 key 限制**：不返回真实价格，用飞行时长/星级估算补充
- **需要代理**：`FLYAI_PROXY=http://127.0.0.1:7890`（生产需确认网络可达性）
- **正式 key 申请**：[open.fly.ai](https://open.fly.ai/)

## 未完成事项
- [ ] **SiliconFlow API 充值确认**（阻塞评测）
- [ ] 充值后重跑全部200题评测
- [ ] FlyAI 正式 key 申请（解锁真实价格）
- [ ] 生产服务器网络确认（flyai.open.fliggy.com 可达性）

## 环境备忘
- **本地**：`~/Desktop/new_start/claude-code/travel-agent/`，前端3001，后端8000
- **生产**：150.158.192.237（腾讯云上海），前端 /travel (PM2:3003)，后端 /travel-api/ (PM2:8000)
- **生产用户**：ubuntu (sudo)，SSH密钥已配置
- **GitHub**：github.com/dingtom336-gif/travel-agent（remote已切HTTPS）
- **AI引擎**：GLM-5(reasoning) + GLM-4-32B(writing)，SiliconFlow API
- **评测系统**：tests/e2e/eval_200.json + eval_v2_scoring.py + run_eval_200.py
- **测试**：`./agent/venv2/bin/python -m pytest tests/ -v`（205 passed）
- **评测跑法**：`--server=http://150.158.192.237/travel-api`（走nginx，不是直连8000）
- **Stitch 设计稿**：web/.stitch/designs/（5个HTML参考文件）
