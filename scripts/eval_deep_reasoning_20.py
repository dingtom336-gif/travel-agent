#!/usr/bin/env python3
"""Deep reasoning mode 20-question evaluation.

Uses the SSE streaming endpoint to avoid nginx 504 timeouts.
Sends 20 diverse queries with deep_reasoning=True to the production API,
collects responses, and outputs a quality report.
"""
import json
import sys
import time
import http.client
import urllib.parse

SERVER_HOST = "150.158.192.237"
SERVER_PATH = "/travel-api/api/chat/stream"

# 20 test cases covering different scenarios
TEST_CASES = [
  # --- Flight search (1-3) ---
  {"id": "DR01", "cat": "航班查询", "q": "帮我查一下明天北京到三亚的航班"},
  {"id": "DR02", "cat": "航班查询", "q": "上海到成都后天的航班，要直飞的"},
  {"id": "DR03", "cat": "航班查询", "q": "广州飞东京下周五有什么航班？经济舱"},
  # --- Hotel search (4-6) ---
  {"id": "DR04", "cat": "酒店查询", "q": "三亚亚龙湾附近有什么五星级酒店推荐？"},
  {"id": "DR05", "cat": "酒店查询", "q": "杭州西湖边的酒店，价格300以内的"},
  {"id": "DR06", "cat": "酒店查询", "q": "成都春熙路附近适合带小孩住的酒店"},
  # --- POI search (7-9) ---
  {"id": "DR07", "cat": "景点查询", "q": "北京有哪些适合亲子游的景点？"},
  {"id": "DR08", "cat": "景点查询", "q": "西安必去的5个景点是什么"},
  {"id": "DR09", "cat": "景点查询", "q": "厦门鼓浪屿一日游怎么安排"},
  # --- Full trip planning (10-13) ---
  {"id": "DR10", "cat": "行程规划", "q": "帮我规划一个三亚5天4晚的亲子游行程，预算8000元"},
  {"id": "DR11", "cat": "行程规划", "q": "两个人去云南大理丽江玩7天，想深度游，预算1万"},
  {"id": "DR12", "cat": "行程规划", "q": "国庆想从上海出发去日本东京大阪玩5天"},
  {"id": "DR13", "cat": "行程规划", "q": "清明节3天假期，从深圳出发去哪里合适？预算3000"},
  # --- Knowledge / tips (14-16) ---
  {"id": "DR14", "cat": "旅行知识", "q": "去泰国需要准备什么？签证怎么办？"},
  {"id": "DR15", "cat": "旅行知识", "q": "冬天去哈尔滨玩需要注意什么？"},
  {"id": "DR16", "cat": "旅行知识", "q": "第一次坐邮轮有什么建议？"},
  # --- Complex / multi-constraint (17-19) ---
  {"id": "DR17", "cat": "复杂约束", "q": "我们4个人想五一从北京去海边玩3天，有老人和小孩，预算5000，不想太累"},
  {"id": "DR18", "cat": "复杂约束", "q": "蜜月旅行推荐，7天左右，预算2万，想去海岛但不要马尔代夫"},
  {"id": "DR19", "cat": "复杂约束", "q": "暑假带两个孩子（5岁和10岁）去哪里玩好？要有教育意义的"},
  # --- Edge case (20) ---
  {"id": "DR20", "cat": "边界场景", "q": "我现在在曼谷，护照丢了怎么办？"},
]


def call_sse_api(question, session_id=None):
  """Call the SSE streaming chat API with deep_reasoning=True.

  Parses SSE events and extracts text content + metadata.
  """
  payload = json.dumps({
    "message": question,
    "session_id": session_id or f"eval-dr-{int(time.time())}",
    "deep_reasoning": True,
  }).encode("utf-8")

  conn = http.client.HTTPConnection(SERVER_HOST, timeout=300)
  try:
    conn.request("POST", SERVER_PATH, body=payload, headers={
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    })
    resp = conn.getresponse()
    if resp.status != 200:
      body = resp.read().decode("utf-8", errors="replace")[:200]
      return {"error": f"HTTP {resp.status}: {body}", "text": "", "agents": [], "ui_components": []}

    # Parse SSE stream
    text_parts = []
    agents = []
    ui_components = []
    error_msg = ""
    buffer = ""

    while True:
      chunk = resp.read(4096)
      if not chunk:
        break
      buffer += chunk.decode("utf-8", errors="replace")

      while "\n\n" in buffer:
        event_block, buffer = buffer.split("\n\n", 1)
        event_type = ""
        event_data = ""
        for line in event_block.strip().split("\n"):
          if line.startswith("event:"):
            event_type = line[6:].strip()
          elif line.startswith("data:"):
            event_data = line[5:].strip()

        if not event_data:
          continue
        try:
          data = json.loads(event_data)
        except json.JSONDecodeError:
          continue

        if event_type == "text":
          text_parts.append(data.get("content", ""))
        elif event_type == "agent_start":
          agents.append({"agent": data.get("agent", ""), "status": "started"})
        elif event_type == "agent_result":
          agents.append({"agent": data.get("agent", ""), "status": data.get("status", "")})
        elif event_type == "ui_component":
          ui_components.append(data.get("type", "unknown"))
        elif event_type == "error":
          error_msg = data.get("error", "unknown error")

    full_text = "".join(text_parts)
    result = {
      "text": full_text,
      "agents": agents,
      "ui_components": ui_components,
    }
    if error_msg:
      result["error"] = error_msg
    return result

  except Exception as e:
    return {"error": str(e), "text": "", "agents": [], "ui_components": []}
  finally:
    conn.close()


def assess_quality(test_case, response_text, agents, ui_components):
  """Heuristic quality assessment."""
  issues = []
  q = test_case["q"]
  cat = test_case["cat"]
  resp = response_text or ""
  resp_len = len(resp)

  # Length check
  if resp_len < 50:
    issues.append("响应过短(<50字)")
  elif resp_len < 100 and cat in ("行程规划", "复杂约束"):
    issues.append("规划类响应偏短(<100字)")

  # Empty check
  if not resp.strip():
    issues.append("空响应")
    return 1, issues

  # Deep reasoning should dispatch agents
  agent_names = [a["agent"] for a in agents if a.get("status") != "started"]
  if not agent_names and cat not in ("边界场景",):
    issues.append("未调度任何Agent(可能走了Theater模式)")

  # Category-specific checks
  if cat == "航班查询":
    if not any(kw in resp for kw in ("航班", "航空", "出发", "到达", "起飞", "飞")):
      issues.append("未包含航班信息")
    # Check for specific flight details
    if not any(kw in resp for kw in ("航班号", "CA", "MU", "CZ", "HU", "ZH", "3U", "FM", "号")):
      if "flight_card" not in ui_components:
        issues.append("缺少具体航班号")

  elif cat == "酒店查询":
    if not any(kw in resp for kw in ("酒店", "住宿", "入住", "房间", "星级", "评分")):
      issues.append("未包含酒店信息")

  elif cat == "景点查询":
    if not any(kw in resp for kw in ("景点", "景区", "推荐", "游玩", "门票", "公园", "博物")):
      issues.append("未包含景点信息")

  elif cat == "行程规划":
    if not any(kw in resp for kw in ("Day", "第一天", "第1天", "行程", "上午", "下午", "day")):
      issues.append("未包含逐日行程")
    if "预算" in q and not any(kw in resp for kw in ("预算", "费用", "花费", "元", "¥")):
      issues.append("未回应预算约束")

  elif cat == "旅行知识":
    if resp_len < 150:
      issues.append("知识类响应信息量不足")

  elif cat == "复杂约束":
    if "老人" in q and not any(kw in resp for kw in ("老人", "老年", "长辈")):
      issues.append("未回应约束: 老人")
    if ("小孩" in q or "孩子" in q) and not any(kw in resp for kw in ("孩子", "小孩", "儿童", "亲子")):
      issues.append("未回应约束: 孩子")
    if "蜜月" in q and "蜜月" not in resp:
      issues.append("未回应约束: 蜜月")
    if "不要马尔代夫" in q and "马尔代夫" in resp:
      # Check if it's mentioned as excluded vs recommended
      idx = resp.find("马尔代夫")
      context = resp[max(0, idx - 20):idx + 30]
      if not any(kw in context for kw in ("不", "排除", "除了", "之外")):
        issues.append("违反排除约束(推荐了马尔代夫)")

  elif cat == "边界场景":
    if not any(kw in resp for kw in ("大使馆", "领事馆", "警方", "报警", "补办")):
      issues.append("未提供紧急情况指导")

  # Score: 5=excellent, 4=good, 3=acceptable, 2=poor, 1=fail
  if not issues:
    score = 5 if resp_len > 300 else 4
  elif len(issues) == 1 and "偏短" in issues[0]:
    score = 3
  elif "空响应" in str(issues):
    score = 1
  else:
    score = max(2, 4 - len(issues))

  return score, issues


def main():
  results = []
  total = len(TEST_CASES)
  print(f"\n{'='*60}")
  print(f"  TravelMind 深度推理模式 20 题评测 (SSE)")
  print(f"  服务器: http://{SERVER_HOST}")
  print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
  print(f"{'='*60}\n")

  for i, tc in enumerate(TEST_CASES, 1):
    print(f"[{i:2d}/{total}] {tc['id']} [{tc['cat']}] {tc['q'][:40]}...")
    sys.stdout.flush()

    start = time.time()
    resp = call_sse_api(tc["q"])
    duration = time.time() - start

    response_text = resp.get("text", "")
    error = resp.get("error", "")
    agents = resp.get("agents", [])
    ui_components = resp.get("ui_components", [])

    if error and not response_text:
      score = 1
      issues = [f"API错误: {error[:100]}"]
    else:
      score, issues = assess_quality(tc, response_text, agents, ui_components)
      if error:
        issues.append(f"(有错误但仍有响应: {error[:60]})")

    agent_names = list(set(a["agent"] for a in agents if a.get("agent")))
    result = {
      "id": tc["id"],
      "category": tc["cat"],
      "question": tc["q"],
      "response": response_text[:800],
      "response_length": len(response_text),
      "score": score,
      "issues": issues,
      "duration_s": round(duration, 1),
      "agents_dispatched": agent_names,
      "ui_components": ui_components,
    }
    results.append(result)

    status = "PASS" if score >= 3 else "FAIL"
    issue_str = f" [{', '.join(issues)}]" if issues else ""
    agents_str = f" agents={','.join(agent_names)}" if agent_names else ""
    ui_str = f" ui={','.join(ui_components)}" if ui_components else ""
    print(f"       -> {status} score={score}/5 len={len(response_text)} "
          f"time={duration:.1f}s{agents_str}{ui_str}{issue_str}")
    sys.stdout.flush()

  # --- Summary ---
  scores = [r["score"] for r in results]
  avg_score = sum(scores) / len(scores)
  pass_count = sum(1 for s in scores if s >= 3)
  fail_count = total - pass_count
  avg_duration = sum(r["duration_s"] for r in results) / len(results)

  print(f"\n{'='*60}")
  print(f"  评测报告")
  print(f"{'='*60}")
  print(f"  通过率: {pass_count}/{total} ({pass_count/total*100:.0f}%)")
  print(f"  平均分: {avg_score:.2f}/5")
  print(f"  平均耗时: {avg_duration:.1f}s")
  print()

  # Per-category breakdown
  cats = {}
  for r in results:
    cat = r["category"]
    if cat not in cats:
      cats[cat] = []
    cats[cat].append(r["score"])

  print("  分类统计:")
  for cat, cat_scores in cats.items():
    cat_avg = sum(cat_scores) / len(cat_scores)
    cat_pass = sum(1 for s in cat_scores if s >= 3)
    print(f"    {cat:<8} 通过{cat_pass}/{len(cat_scores)} 平均{cat_avg:.1f}")

  # List failures
  failures = [r for r in results if r["score"] < 3]
  if failures:
    print(f"\n  失败用例 ({len(failures)}):")
    for r in failures:
      print(f"    {r['id']} [{r['category']}] score={r['score']} "
            f"issues={r['issues']}")

  # List all issues
  all_issues = []
  for r in results:
    for issue in r["issues"]:
      all_issues.append(f"{r['id']}: {issue}")
  if all_issues:
    print(f"\n  全部问题 ({len(all_issues)}):")
    for issue in all_issues:
      print(f"    - {issue}")

  print(f"\n{'='*60}\n")

  # Save results
  output_path = "tests/e2e/eval_deep_reasoning_20.json"
  with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
      "version": "v0.9.1",
      "mode": "deep_reasoning",
      "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
      "server": f"http://{SERVER_HOST}",
      "summary": {
        "total": total,
        "passed": pass_count,
        "failed": fail_count,
        "avg_score": round(avg_score, 2),
        "avg_duration_s": round(avg_duration, 1),
      },
      "results": results,
    }, f, ensure_ascii=False, indent=2)
  print(f"  结果已保存: {output_path}")


if __name__ == "__main__":
  main()
