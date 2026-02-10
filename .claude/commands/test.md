# 测试流程

## 输入
$ARGUMENTS

## 步骤

### 1. 单元测试
```bash
./agent/venv2/bin/python -m pytest tests/ -v
```
- 确认 199/200 通过（1个预存在失败: test_sse_pipeline）
- 如有新失败，立即定位修复

### 2. 冒烟测试（需要后端运行）
```bash
./agent/venv2/bin/python scripts/smoke_test.py
```
- 简单消息：首事件 <500ms, 首文本 <5s, 总时 <15s
- 复杂消息：首事件 <500ms, 首文本 <30s, 总时 <120s

### 3. E2E测试（需要前后端都运行）
```bash
npx playwright test tests/e2e/
```
- 验证页面加载、聊天交互、卡片渲染
- 截图保存到 tests/screenshots/

### 4. 性能验证（架构变更时）
```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"帮我规划3天东京旅行"}'
```
- 至少跑3次，记录时间
- 格式："用户在X秒内看到Y结果"

## 测试铁律
- API 200 ≠ 功能可用，必须验证响应体
- UI变更必须Playwright截图验证
- 测试失败不跳过，先修后提交
