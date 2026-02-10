# 新功能开发流程

## 输入
$ARGUMENTS

## 步骤
1. 阅读 docs/PRD.md 和 docs/CONTEXT.md 了解项目现状
2. 分析需求，确认影响范围（哪些文件需要改动）
3. 如果涉及架构决策，先询问用户确认方案
4. 按以下顺序实现：
   - 后端：models.py → teams/ → orchestrator/ → main.py
   - 前端：lib/types.ts → components/ → app/页面
5. 每个改动后列出修改的文件
6. 编写/更新测试：
   - 后端：tests/ 下对应测试文件
   - 前端：如涉及UI，写 Playwright E2E 测试
7. 运行测试验证：
   ```bash
   ./agent/venv2/bin/python -m pytest tests/ -v
   ```
8. 更新 docs/CONTEXT.md 记录本次变更
9. 提交代码（一个功能 = 一次commit）

## 检查清单
- [ ] 单文件不超过500行
- [ ] async函数有try/catch
- [ ] API响应体内容正确（不只是200）
- [ ] 前端渲染正确（Playwright截图验证）
- [ ] CONTEXT.md已更新
