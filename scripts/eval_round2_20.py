#!/usr/bin/env python3
"""Round 2: 20 all-new questions (no overlap with round 1).

Covers: seasonal travel, special demographics, transport modes, food/culture,
comparison/decision, multi-city, budget extremes, safety, booking logistics.
"""
import json
import sys
import time
import http.client

SERVER_HOST = "150.158.192.237"
SERVER_PATH = "/travel-api/api/chat/stream"

# Round 2: 20 all-new questions
TEST_CASES = [
  # --- Seasonal / weather-sensitive (1-2) ---
  {"id": "R201", "cat": "季节出行", "diff": "S",
   "q": "7月份国内哪里凉快适合避暑？"},
  {"id": "R202", "cat": "季节出行", "diff": "M",
   "q": "12月想看雪景，从杭州出发4天3晚，两个人预算6000"},

  # --- Transport-specific (3-4) ---
  {"id": "R203", "cat": "交通方式", "diff": "S",
   "q": "北京到西安坐高铁要多久？大概多少钱"},
  {"id": "R204", "cat": "交通方式", "diff": "M",
   "q": "从上海自驾去青岛怎么走？路上有什么值得停留的地方"},

  # --- Food & culture focused (5-6) ---
  {"id": "R205", "cat": "美食文化", "diff": "S",
   "q": "去西安必吃的十大美食是什么"},
  {"id": "R206", "cat": "美食文化", "diff": "M",
   "q": "想来一次广东顺德美食之旅，3天2晚，帮我安排每顿吃什么"},

  # --- Comparison / decision (7-8) ---
  {"id": "R207", "cat": "比较决策", "diff": "M",
   "q": "普吉岛和巴厘岛哪个更适合带3岁小孩去？"},
  {"id": "R208", "cat": "比较决策", "diff": "M",
   "q": "五一去张家界还是黄山好？人少景美的那个"},

  # --- Special demographics (9-11) ---
  {"id": "R209", "cat": "特殊人群", "diff": "M",
   "q": "一个人女生独自去西藏安全吗？需要注意什么"},
  {"id": "R210", "cat": "特殊人群", "diff": "C",
   "q": "带轮椅上的爷爷出去玩，北京周边2天1晚，要无障碍设施好的"},
  {"id": "R211", "cat": "特殊人群", "diff": "S",
   "q": "孕妇可以坐飞机吗？几个月以内可以飞"},

  # --- Budget extremes (12-13) ---
  {"id": "R212", "cat": "预算极端", "diff": "C",
   "q": "500块钱能在哪里玩两天？从南京出发，要好玩不能太穷酸"},
  {"id": "R213", "cat": "预算极端", "diff": "C",
   "q": "预算不限，想要最顶级的马尔代夫体验，2个人7天，越奢华越好"},

  # --- Multi-city / complex routing (14-15) ---
  {"id": "R214", "cat": "多城市", "diff": "C",
   "q": "15天环游欧洲，巴黎-瑞士-意大利-西班牙，两个人预算5万，帮我规划路线和交通"},
  {"id": "R215", "cat": "多城市", "diff": "M",
   "q": "国庆从成都出发，想去甘南-青海湖-敦煌一圈，自驾10天可以吗"},

  # --- Booking logistics (16-17) ---
  {"id": "R216", "cat": "预订实务", "diff": "S",
   "q": "酒店预订后可以免费取消吗？一般取消政策是什么"},
  {"id": "R217", "cat": "预订实务", "diff": "S",
   "q": "机票买贵了能退差价吗？什么时候买机票最便宜"},

  # --- Safety / emergency (18) ---
  {"id": "R218", "cat": "安全应急", "diff": "M",
   "q": "去东南亚旅游怎么防止被骗？有哪些常见骗术"},

  # --- Niche / creative (19-20) ---
  {"id": "R219", "cat": "小众玩法", "diff": "M",
   "q": "不想去热门景点，求一个贵州小众秘境5天行程"},
  {"id": "R220", "cat": "小众玩法", "diff": "C",
   "q": "想体验中国最美的5条徒步路线，帮我对比难度、最佳季节和费用"},
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
  planning_cats = ("季节出行", "美食文化", "比较决策", "特殊人群", "预算极端",
                   "多城市", "小众玩法")
  expects_agents = diff in ("M", "C") and cat in planning_cats
  if expects_agents and not agent_names:
    issues.append("未调度Agent(规划类应走ReAct)")

  # Category-specific checks
  if cat == "季节出行":
    if not any(kw in resp for kw in ("避暑", "凉快", "温度", "气候", "雪", "冬",
                                      "推荐", "适合", "度", "℃")):
      issues.append("未回应季节/气候需求")
    if diff == "M" and "预算" in q:
      if not any(kw in resp for kw in ("预算", "费用", "花费", "元", "¥", "价格")):
        issues.append("未回应预算约束")

  elif cat == "交通方式":
    if "高铁" in q and not any(kw in resp for kw in ("高铁", "动车", "小时", "车次",
                                                       "二等座", "一等座", "元")):
      issues.append("未包含高铁信息")
    if "自驾" in q and not any(kw in resp for kw in ("自驾", "高速", "公里", "km",
                                                       "路线", "服务区", "收费")):
      issues.append("未包含自驾路线信息")

  elif cat == "美食文化":
    if not any(kw in resp for kw in ("美食", "小吃", "餐厅", "店", "吃", "菜",
                                      "面", "肉", "汤", "馆")):
      issues.append("未包含美食推荐")

  elif cat == "比较决策":
    # Should mention BOTH options and give comparison
    if "普吉" in q and "巴厘" in q:
      if "普吉" not in resp or "巴厘" not in resp:
        issues.append("未对比两个选项")
    if "张家界" in q and "黄山" in q:
      if "张家界" not in resp or "黄山" not in resp:
        issues.append("未对比两个选项")

  elif cat == "特殊人群":
    if "女生独自" in q and not any(kw in resp for kw in ("安全", "注意", "建议",
                                                          "独自", "一个人")):
      issues.append("未回应安全顾虑")
    if "轮椅" in q and not any(kw in resp for kw in ("轮椅", "无障碍", "残障",
                                                       "便利", "电梯")):
      issues.append("未回应无障碍需求")
    if "孕妇" in q and not any(kw in resp for kw in ("孕", "怀孕", "周", "月份",
                                                       "航空公司", "医生")):
      issues.append("未回应孕妇乘机问题")

  elif cat == "预算极端":
    if "500" in q and not any(kw in resp for kw in ("预算", "费用", "元", "花",
                                                      "省", "性价比")):
      issues.append("未回应极低预算约束")
    if "不限" in q and "奢华" in q:
      if not any(kw in resp for kw in ("奢华", "顶级", "五星", "别墅", "水上",
                                        "套房", "私人")):
        issues.append("未体现高端奢华定位")

  elif cat == "多城市":
    # Should have multi-day structure
    if not any(kw in resp for kw in ("Day", "第一天", "第1天", "行程", "上午",
                                      "下午", "day", "DAY", "路线")):
      issues.append("未包含多城市路线规划")

  elif cat == "预订实务":
    if resp_len < 80:
      issues.append("预订知识响应信息量不足")

  elif cat == "安全应急":
    if not any(kw in resp for kw in ("骗", "防", "注意", "安全", "警惕", "套路")):
      issues.append("未提供防骗指导")

  elif cat == "小众玩法":
    if resp_len < 150:
      issues.append("小众推荐信息量不足")
    if "徒步" in q and not any(kw in resp for kw in ("徒步", "线路", "路线",
                                                       "公里", "km", "难度")):
      issues.append("未包含徒步路线信息")

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
  print(f"  TravelMind Round 2 评测 20 题 (深度推理优先模式)")
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
  print(f"  Round 2 评测报告")
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
  output_path = "tests/e2e/eval_round2_20.json"
  with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
      "version": "v0.9.2-round2",
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
