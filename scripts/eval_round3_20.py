#!/usr/bin/env python3
"""Round 3: 20 all-new questions (no overlap with round 1 & 2).

Covers: weekend getaways, honeymoon variants, solo travel, group dynamics,
weather-dependent, cultural immersion, adventure sports, family reunion,
visa/entry, accommodation types, nightlife, photography, pet travel,
transit hubs, historical routes, festival timing, cross-border, wellness.
"""
import json
import sys
import time
import http.client

SERVER_HOST = "150.158.192.237"
SERVER_PATH = "/travel-api/api/chat/stream"

# Round 3: 20 all-new questions
TEST_CASES = [
  # --- Weekend getaway (1-2) ---
  {"id": "R301", "cat": "周末游", "diff": "S",
   "q": "上海周末两天能去哪玩？不想跑太远"},
  {"id": "R302", "cat": "周末游", "diff": "M",
   "q": "北京出发周末自驾2天，想找个人少的古镇泡温泉"},

  # --- Adventure / outdoor (3-4) ---
  {"id": "R303", "cat": "户外探险", "diff": "M",
   "q": "新手想尝试潜水，国内哪里适合考OW证？费用大概多少"},
  {"id": "R304", "cat": "户外探险", "diff": "C",
   "q": "想去稻城亚丁徒步，从成都出发7天，需要什么装备？有高反怎么办"},

  # --- Festival / timing (5-6) ---
  {"id": "R305", "cat": "节日时机", "diff": "S",
   "q": "什么时候去九寨沟最好看？"},
  {"id": "R306", "cat": "节日时机", "diff": "M",
   "q": "想去日本看樱花，什么时候去最合适？东京还是京都好"},

  # --- Accommodation types (7-8) ---
  {"id": "R307", "cat": "住宿类型", "diff": "S",
   "q": "民宿和酒店怎么选？各有什么优缺点"},
  {"id": "R308", "cat": "住宿类型", "diff": "M",
   "q": "大理想住洱海边的民宿，推荐几家性价比高的，最好有湖景房"},

  # --- Cross-border / visa (9-10) ---
  {"id": "R309", "cat": "出入境", "diff": "S",
   "q": "中国护照免签的国家有哪些？哪些值得去"},
  {"id": "R310", "cat": "出入境", "diff": "M",
   "q": "想去新西兰自驾，签证怎么办？中国驾照能用吗"},

  # --- Family reunion (11) ---
  {"id": "R311", "cat": "家庭聚会", "diff": "C",
   "q": "过年全家12口人（4个老人3个小孩）想找个地方团聚旅行，5天，预算4万，要有大别墅或连通房"},

  # --- Pet travel (12) ---
  {"id": "R312", "cat": "携宠出行", "diff": "M",
   "q": "带狗自驾出去玩，杭州周边哪些景区允许带宠物？需要注意什么"},

  # --- Wellness / relaxation (13) ---
  {"id": "R313", "cat": "康养度假", "diff": "M",
   "q": "工作太累想找个地方躺平一周，不要行程不要景点，只要安静和spa"},

  # --- Photography route (14) ---
  {"id": "R314", "cat": "摄影路线", "diff": "C",
   "q": "秋天拍红叶最美的5个地方，帮我按最佳拍摄时间排序，规划一条从北到南的路线"},

  # --- Historical / cultural route (15) ---
  {"id": "R315", "cat": "文化线路", "diff": "C",
   "q": "想沿着丝绸之路走一趟，西安到喀什，15天自驾，帮我规划路线和必看的历史遗迹"},

  # --- Nightlife (16) ---
  {"id": "R316", "cat": "夜生活", "diff": "S",
   "q": "长沙晚上有什么好玩的？夜市和酒吧推荐"},

  # --- Transit hub (17) ---
  {"id": "R317", "cat": "中转攻略", "diff": "S",
   "q": "在广州白云机场转机有6小时，能出去玩吗？去哪"},

  # --- Weather-dependent decision (18) ---
  {"id": "R318", "cat": "天气决策", "diff": "M",
   "q": "下周要去张家界，看天气预报有雨，还值得去吗？下雨天怎么玩"},

  # --- Group dynamics (19) ---
  {"id": "R319", "cat": "混合团体", "diff": "C",
   "q": "8个同事年假拼团，有人想海边有人想爬山有人想逛街，5天预算人均4000，从杭州出发怎么都满足"},

  # --- Solo backpacking (20) ---
  {"id": "R320", "cat": "独行背包", "diff": "M",
   "q": "大学生一个人穷游川西，10天预算3000够吗？怎么规划最省钱"},
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

  # Agent dispatch check — only for complex planning categories
  agent_names = [a["agent"] for a in agents if a.get("status") != "started"]
  planning_cats = ("户外探险", "家庭聚会", "摄影路线", "文化线路", "混合团体")
  expects_agents = diff == "C" and cat in planning_cats
  if expects_agents and not agent_names:
    issues.append("未调度Agent(规划类应走ReAct)")

  # Category-specific checks
  if cat == "周末游":
    if not any(kw in resp for kw in ("推荐", "周边", "周末", "两天", "景点",
                                      "古镇", "温泉", "玩")):
      issues.append("未提供周末游推荐")

  elif cat == "户外探险":
    if "潜水" in q and not any(kw in resp for kw in ("潜水", "OW", "PADI", "证",
                                                       "海南", "涠洲", "三亚")):
      issues.append("未包含潜水信息")
    if "稻城" in q and not any(kw in resp for kw in ("稻城", "亚丁", "高反", "海拔",
                                                       "装备", "徒步")):
      issues.append("未包含稻城亚丁信息")

  elif cat == "节日时机":
    if "九寨沟" in q and not any(kw in resp for kw in ("秋", "10月", "9月", "十月",
                                                         "九月", "金秋", "最佳")):
      issues.append("未回应最佳时间")
    if "樱花" in q and not any(kw in resp for kw in ("樱花", "3月", "4月", "三月",
                                                       "四月", "花期")):
      issues.append("未回应樱花季时间")

  elif cat == "住宿类型":
    if "民宿" in q and "酒店" in q and not any(kw in resp for kw in ("民宿", "酒店")):
      issues.append("未对比住宿类型")
    if "洱海" in q and not any(kw in resp for kw in ("洱海", "大理", "民宿", "海景",
                                                       "湖景")):
      issues.append("未包含洱海民宿推荐")

  elif cat == "出入境":
    if "免签" in q and not any(kw in resp for kw in ("免签", "落地签", "国家",
                                                       "护照")):
      issues.append("未包含免签信息")
    if "新西兰" in q and not any(kw in resp for kw in ("签证", "新西兰", "驾照",
                                                         "驾驶", "自驾")):
      issues.append("未包含新西兰签证/驾照信息")

  elif cat == "家庭聚会":
    if not any(kw in resp for kw in ("别墅", "套房", "连通", "家庭", "团聚",
                                      "全家", "老人", "孩子")):
      issues.append("未回应大家庭住宿需求")

  elif cat == "携宠出行":
    if not any(kw in resp for kw in ("宠物", "狗", "携带", "允许", "景区",
                                      "注意")):
      issues.append("未回应携宠需求")

  elif cat == "康养度假":
    if not any(kw in resp for kw in ("spa", "SPA", "温泉", "度假", "放松",
                                      "休闲", "安静", "疗愈", "躺")):
      issues.append("未回应康养度假需求")

  elif cat == "摄影路线":
    if not any(kw in resp for kw in ("红叶", "秋", "拍", "摄影", "最佳",
                                      "路线")):
      issues.append("未包含摄影路线信息")

  elif cat == "文化线路":
    if not any(kw in resp for kw in ("丝绸之路", "遗迹", "历史", "敦煌", "莫高",
                                      "路线", "自驾")):
      issues.append("未包含丝绸之路信息")

  elif cat == "夜生活":
    if not any(kw in resp for kw in ("夜市", "酒吧", "夜", "小吃", "太平街",
                                      "解放西", "长沙")):
      issues.append("未包含夜生活推荐")

  elif cat == "中转攻略":
    if not any(kw in resp for kw in ("转机", "小时", "白云", "机场", "出",
                                      "来得及", "时间")):
      issues.append("未回应中转可行性")

  elif cat == "天气决策":
    if not any(kw in resp for kw in ("雨", "天气", "值得", "雾", "云海",
                                      "建议", "注意")):
      issues.append("未回应天气影响")

  elif cat == "混合团体":
    if not any(kw in resp for kw in ("海", "山", "逛", "综合", "兼顾",
                                      "满足", "行程")):
      issues.append("未兼顾多方需求")

  elif cat == "独行背包":
    if not any(kw in resp for kw in ("省钱", "预算", "3000", "穷游", "青旅",
                                      "搭车", "性价比", "花费")):
      issues.append("未回应预算控制")

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
  print(f"  TravelMind Round 3 评测 20 题 (深度推理优先模式)")
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
  print(f"  Round 3 评测报告")
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
  output_path = "tests/e2e/eval_round3_20.json"
  with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
      "version": "v0.9.2-round3",
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
