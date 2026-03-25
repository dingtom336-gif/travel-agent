#!/usr/bin/env python3
"""Mixed 20-question evaluation (simple + complex).

All queries sent with deep_reasoning=True (new default).
Tests the deep-reasoning-priority mode: search queries now go through
full ReAct pipeline instead of search fast-path.
"""
import json
import sys
import time
import http.client

SERVER_HOST = "150.158.192.237"
SERVER_PATH = "/travel-api/api/chat/stream"

# 20 mixed test cases: simple (S) and complex (C)
TEST_CASES = [
  # --- Simple: casual chat (1-2) ---
  {"id": "MX01", "cat": "闲聊", "diff": "S",
   "q": "你好，你是谁？能帮我做什么？"},
  {"id": "MX02", "cat": "闲聊", "diff": "S",
   "q": "谢谢你的帮助，再见！"},

  # --- Simple: single search (3-5) ---
  {"id": "MX03", "cat": "航班查询", "diff": "S",
   "q": "明天北京到上海的航班"},
  {"id": "MX04", "cat": "酒店查询", "diff": "S",
   "q": "杭州西湖附近有什么酒店"},
  {"id": "MX05", "cat": "景点查询", "diff": "S",
   "q": "成都有什么好玩的地方"},

  # --- Simple: travel knowledge (6-8) ---
  {"id": "MX06", "cat": "旅行知识", "diff": "S",
   "q": "去日本旅游需要签证吗"},
  {"id": "MX07", "cat": "旅行知识", "diff": "S",
   "q": "坐飞机能带多少液体"},
  {"id": "MX08", "cat": "旅行知识", "diff": "S",
   "q": "护照和签证有什么区别"},

  # --- Medium: trip planning (9-12) ---
  {"id": "MX09", "cat": "行程规划", "diff": "M",
   "q": "帮我规划一个厦门3天2晚的行程"},
  {"id": "MX10", "cat": "行程规划", "diff": "M",
   "q": "五一假期从广州出发去桂林玩4天，预算5000"},
  {"id": "MX11", "cat": "行程规划", "diff": "M",
   "q": "两个人从北京去成都重庆玩6天，想吃火锅看熊猫"},
  {"id": "MX12", "cat": "行程规划", "diff": "M",
   "q": "春节去三亚5天4晚亲子游，预算1万"},

  # --- Complex: multi-constraint (13-17) ---
  {"id": "MX13", "cat": "复杂约束", "diff": "C",
   "q": "我们6个人想暑假从上海去云南玩7天，有2个老人膝盖不好不能爬山，2个小孩要有趣味性，预算人均3000"},
  {"id": "MX14", "cat": "复杂约束", "diff": "C",
   "q": "蜜月旅行10天，预算3万，想去海岛但不要东南亚，要有浮潜和SPA"},
  {"id": "MX15", "cat": "复杂约束", "diff": "C",
   "q": "公司团建15人，从深圳出发2天1晚，要有团队活动和聚餐，预算人均800"},
  {"id": "MX16", "cat": "复杂约束", "diff": "C",
   "q": "带父母第一次出国，5天左右，他们不会英语，想去文化底蕴深的地方，预算2万"},
  {"id": "MX17", "cat": "复杂约束", "diff": "C",
   "q": "毕业旅行4个女生从武汉出发，7天穷游，总预算8000，想拍好看的照片"},

  # --- Edge / boundary (18-20) ---
  {"id": "MX18", "cat": "边界场景", "diff": "S",
   "q": "我在国外手机被偷了怎么办"},
  {"id": "MX19", "cat": "边界场景", "diff": "M",
   "q": "航班取消了，航空公司不赔偿怎么投诉"},
  {"id": "MX20", "cat": "事实纠正", "diff": "S",
   "q": "听说长城是在明朝才开始建的对吗"},
]


def call_sse_api(question, session_id=None):
  """Call the SSE streaming chat API with deep_reasoning=True."""
  payload = json.dumps({
    "message": question,
    "session_id": session_id or f"eval-mx-{int(time.time())}",
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
      return {"error": f"HTTP {resp.status}: {body}", "text": "",
              "agents": [], "ui_components": [], "mode": "unknown"}

    text_parts = []
    agents = []
    ui_components = []
    error_msg = ""
    detected_mode = "unknown"
    buffer = ""

    while True:
      chunk = resp.read(4096)
      if not chunk:
        break
      buffer += chunk.decode("utf-8", errors="replace").replace("\r\n", "\n")

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
        elif event_type == "thinking":
          detected_mode = "react"
        elif event_type == "agent_start":
          agents.append({"agent": data.get("agent", ""), "status": "started"})
          detected_mode = "react"
        elif event_type == "agent_result":
          agents.append({"agent": data.get("agent", ""),
                         "status": data.get("status", "")})
        elif event_type == "ui_component":
          ui_components.append(data.get("type", "unknown"))
        elif event_type == "error":
          error_msg = data.get("error", "unknown error")

    # Detect mode from response pattern
    if detected_mode == "unknown":
      if agents:
        detected_mode = "react"
      elif any(kw in "".join(text_parts) for kw in ("数据来源", "飞猪")):
        detected_mode = "search_fastpath"
      else:
        detected_mode = "theater"

    full_text = "".join(text_parts)
    result = {
      "text": full_text,
      "agents": agents,
      "ui_components": ui_components,
      "mode": detected_mode,
    }
    if error_msg:
      result["error"] = error_msg
    return result

  except Exception as e:
    return {"error": str(e), "text": "", "agents": [],
            "ui_components": [], "mode": "error"}
  finally:
    conn.close()


def assess_quality(test_case, response_text, agents, ui_components, mode):
  """Heuristic quality assessment — mode-aware."""
  issues = []
  q = test_case["q"]
  cat = test_case["cat"]
  diff = test_case["diff"]
  resp = response_text or ""
  resp_len = len(resp)

  # Empty check
  if not resp.strip():
    issues.append("空响应")
    return 1, issues

  # Length check
  if resp_len < 30:
    issues.append(f"响应过短({resp_len}字)")

  # Agent dispatch check — only for categories that SHOULD use agents
  agent_names = [a["agent"] for a in agents if a.get("status") != "started"]
  expects_agents = cat in ("行程规划", "复杂约束")
  if expects_agents and not agent_names:
    issues.append("未调度Agent(规划类应走ReAct)")

  # Category-specific checks
  if cat == "闲聊":
    if resp_len < 20:
      issues.append("闲聊响应过短")

  elif cat == "航班查询":
    if not any(kw in resp for kw in ("航班", "航空", "出发", "到达", "飞")):
      issues.append("未包含航班信息")

  elif cat == "酒店查询":
    if not any(kw in resp for kw in ("酒店", "住宿", "入住", "房间", "星级", "评分", "推荐")):
      issues.append("未包含酒店信息")

  elif cat == "景点查询":
    if not any(kw in resp for kw in ("景点", "景区", "推荐", "游玩", "门票", "公园", "博物", "好玩")):
      issues.append("未包含景点信息")

  elif cat == "行程规划":
    if not any(kw in resp for kw in ("Day", "第一天", "第1天", "行程", "上午", "下午", "day", "DAY")):
      issues.append("未包含逐日行程")
    if "预算" in q and not any(kw in resp for kw in ("预算", "费用", "花费", "元", "¥", "价格", "成本")):
      issues.append("未回应预算约束")

  elif cat == "旅行知识":
    if resp_len < 80:
      issues.append("知识类响应信息量不足")

  elif cat == "复杂约束":
    constraint_checks = [
      ("老人", ("老人", "老年", "长辈", "膝盖")),
      ("小孩", ("孩子", "小孩", "儿童", "亲子", "趣味")),
      ("蜜月", ("蜜月", "浪漫", "度蜜月")),
      ("不要东南亚", None),  # special handling
      ("团建", ("团建", "团队", "活动")),
      ("不会英语", ("语言", "英语", "中文", "翻译", "沟通")),
      ("穷游", ("预算", "省钱", "穷游", "性价比", "花费")),
      ("拍照", ("拍照", "照片", "打卡", "拍摄", "出片")),
    ]
    for keyword, match_words in constraint_checks:
      if keyword in q:
        if keyword == "不要东南亚":
          sea_countries = ("泰国", "越南", "柬埔寨", "印尼", "菲律宾", "缅甸", "老挝")
          for country in sea_countries:
            if country in resp:
              idx = resp.find(country)
              ctx = resp[max(0, idx - 20):idx + 30]
              if not any(neg in ctx for neg in ("不", "排除", "除了", "避开")):
                issues.append(f"违反排除约束(推荐了{country})")
                break
        elif match_words and not any(kw in resp for kw in match_words):
          issues.append(f"未回应约束: {keyword}")

  elif cat == "边界场景":
    if "手机被偷" in q and not any(kw in resp for kw in ("报警", "挂失", "大使馆", "领事馆", "求助", "SOS")):
      issues.append("未提供紧急情况指导")
    if "航班取消" in q and not any(kw in resp for kw in ("赔偿", "投诉", "维权", "民航局", "客服", "12326")):
      issues.append("未提供维权指导")

  elif cat == "事实纠正":
    if not any(kw in resp for kw in ("秦", "战国", "春秋", "西周", "汉", "不是", "不完全", "其实")):
      issues.append("未纠正事实错误(长城始建于秦/战国)")

  # Score: 5=excellent, 4=good, 3=acceptable, 2=poor, 1=fail
  if not issues:
    if diff == "C" and resp_len > 500:
      score = 5
    elif resp_len > 200:
      score = 5
    else:
      score = 4
  elif len(issues) == 1 and "偏短" in str(issues[0]):
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
  print(f"  TravelMind 混合评测 20 题 (深度推理优先模式)")
  print(f"  服务器: http://{SERVER_HOST}")
  print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
  print(f"{'='*60}\n")

  for i, tc in enumerate(TEST_CASES, 1):
    print(f"[{i:2d}/{total}] {tc['id']} [{tc['diff']}][{tc['cat']}] "
          f"{tc['q'][:40]}...")
    sys.stdout.flush()

    start = time.time()
    resp = call_sse_api(tc["q"])
    duration = time.time() - start

    response_text = resp.get("text", "")
    error = resp.get("error", "")
    agents = resp.get("agents", [])
    ui_components = resp.get("ui_components", [])
    mode = resp.get("mode", "unknown")

    if error and not response_text:
      score = 1
      issues = [f"API错误: {error[:100]}"]
    else:
      score, issues = assess_quality(
        tc, response_text, agents, ui_components, mode)
      if error:
        issues.append(f"(有错误但仍有响应: {error[:60]})")

    agent_names = list(set(a["agent"] for a in agents if a.get("agent")))
    result = {
      "id": tc["id"],
      "category": tc["cat"],
      "difficulty": tc["diff"],
      "question": tc["q"],
      "response": response_text[:1000],
      "response_length": len(response_text),
      "score": score,
      "issues": issues,
      "duration_s": round(duration, 1),
      "mode": mode,
      "agents_dispatched": agent_names,
      "ui_components": ui_components,
    }
    results.append(result)

    status = "PASS" if score >= 3 else "FAIL"
    issue_str = f" [{', '.join(issues)}]" if issues else ""
    agents_str = f" agents={','.join(agent_names)}" if agent_names else ""
    print(f"       -> {status} score={score}/5 mode={mode} "
          f"len={len(response_text)} time={duration:.1f}s"
          f"{agents_str}{issue_str}")
    sys.stdout.flush()

  # --- Summary ---
  scores = [r["score"] for r in results]
  avg_score = sum(scores) / len(scores)
  pass_count = sum(1 for s in scores if s >= 3)
  fail_count = total - pass_count
  avg_duration = sum(r["duration_s"] for r in results) / len(results)

  # Duration by difficulty
  dur_s = [r["duration_s"] for r in results if r["difficulty"] == "S"]
  dur_m = [r["duration_s"] for r in results if r["difficulty"] == "M"]
  dur_c = [r["duration_s"] for r in results if r["difficulty"] == "C"]

  print(f"\n{'='*60}")
  print(f"  混合评测报告")
  print(f"{'='*60}")
  print(f"  通过率: {pass_count}/{total} ({pass_count/total*100:.0f}%)")
  print(f"  平均分: {avg_score:.2f}/5")
  print(f"  平均耗时: {avg_duration:.1f}s")
  if dur_s:
    print(f"    简单题(S): {sum(dur_s)/len(dur_s):.1f}s")
  if dur_m:
    print(f"    中等题(M): {sum(dur_m)/len(dur_m):.1f}s")
  if dur_c:
    print(f"    复杂题(C): {sum(dur_c)/len(dur_c):.1f}s")
  print()

  # Per-category breakdown
  cats = {}
  for r in results:
    cat = r["category"]
    if cat not in cats:
      cats[cat] = {"scores": [], "modes": []}
    cats[cat]["scores"].append(r["score"])
    cats[cat]["modes"].append(r["mode"])

  print("  分类统计:")
  print(f"  {'分类':<8} {'通过率':<10} {'平均分':<8} {'模式'}")
  print(f"  {'-'*50}")
  for cat, data in cats.items():
    cat_avg = sum(data["scores"]) / len(data["scores"])
    cat_pass = sum(1 for s in data["scores"] if s >= 3)
    modes = set(data["modes"])
    print(f"  {cat:<8} {cat_pass}/{len(data['scores']):<8} "
          f"{cat_avg:.1f}      {','.join(modes)}")

  # Per-difficulty breakdown
  print()
  print("  难度统计:")
  for diff_label, diff_key in [("简单(S)", "S"), ("中等(M)", "M"), ("复杂(C)", "C")]:
    diff_results = [r for r in results if r["difficulty"] == diff_key]
    if diff_results:
      d_scores = [r["score"] for r in diff_results]
      d_avg = sum(d_scores) / len(d_scores)
      d_pass = sum(1 for s in d_scores if s >= 3)
      print(f"    {diff_label}: 通过{d_pass}/{len(diff_results)} "
            f"平均{d_avg:.1f}")

  # Mode distribution
  print()
  mode_counts = {}
  for r in results:
    m = r["mode"]
    mode_counts[m] = mode_counts.get(m, 0) + 1
  print("  路由模式分布:")
  for m, count in sorted(mode_counts.items()):
    print(f"    {m}: {count}题")

  # List failures
  failures = [r for r in results if r["score"] < 3]
  if failures:
    print(f"\n  失败用例 ({len(failures)}):")
    for r in failures:
      print(f"    {r['id']} [{r['difficulty']}][{r['category']}] "
            f"score={r['score']} mode={r['mode']} "
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
  output_path = "tests/e2e/eval_mixed_20.json"
  with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
      "version": "v0.9.1-dr-priority",
      "mode": "deep_reasoning_priority",
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
