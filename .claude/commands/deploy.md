# 部署流程

## 步骤
1. 运行全量测试，确保通过：
   ```bash
   ./agent/venv2/bin/python -m pytest tests/ -v
   ```
2. 前端构建检查：
   ```bash
   cd web && npm run build
   ```
3. 提交并推送代码：
   ```bash
   git add -A && git commit && git push
   ```
4. SSH到生产服务器部署：
   ```bash
   ssh root@38.54.88.144 "cd /opt/travel-agent && git pull && cd web && npm run build && pm2 restart all"
   ```
5. 等待30秒后运行冒烟测试：
   ```bash
   ./agent/venv2/bin/python scripts/smoke_test.py
   ```
6. 验证通过后更新 docs/CONTEXT.md，记录部署版本和结果

## 回滚
如果冒烟测试失败：
```bash
ssh root@38.54.88.144 "cd /opt/travel-agent && git log --oneline -5"
# 确认回滚目标后：
ssh root@38.54.88.144 "cd /opt/travel-agent && git checkout <commit> && pm2 restart all"
```

## 注意事项
- 部署前必须本地测试通过
- 冒烟测试包含：简单消息 <15s、复杂消息 <120s
- 生产环境：38.54.88.144, PM2管理, nginx反代
