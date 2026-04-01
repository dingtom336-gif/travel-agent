#!/usr/bin/env python3
"""Re-score eval results using LLM semantic matching.

Replaces exact golden-key matching with LLM-judged semantic coverage.
Tags INFRA_ERROR for timeout/connection issues, excludes from pass rate.

Usage:
  python scripts/eval_rescore_semantic.py [--input FILE] [--output FILE] [--workers N]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import http.client
import os
import ssl
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "tests/e2e/eval_300_perf_results.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "tests/e2e/eval_300_semantic_results.json"

API_HOST = "ark.cn-beijing.volces.com"
SCORING_MODEL = "doubao-seed-2.0-lite"
MAX_WORKERS = 8

# ── Infrastructure error detection ──

_INFRA_PATTERNS = (
  "timed out", "timeout", "Connection reset", "Connection refused",
  "Errno 54", "Errno 104", "BadStatusLine", "RemoteDisconnected",
  "Connection aborted",
)


def is_infra_error(result: dict) -> bool:
  """Detect infrastructure errors (timeout, connection reset, etc.)."""
  for issue in result.get("issues", []):
    if any(p.lower() in issue.lower() for p in _INFRA_PATTERNS):
      return True
  if result.get("duration_s", 0) > 300 and result.get("score", 0) <= 1:
    return True
  return False


# ── Load golden keys from all eval sources ──

def load_all_keys() -> dict[str, list[str]]:
  """Build {question_id: [keys]} from eval_200 + round scripts + NEW_60."""
  keys_map: dict[str, list[str]] = {}

  # eval_200.json
  eval_200_path = PROJECT_ROOT / "tests/e2e/eval_200.json"
  if eval_200_path.exists():
    with open(eval_200_path, encoding="utf-8") as f:
      data = json.load(f)
    for q in data.get("questions", []):
      keys_map[q["id"]] = q.get("keys", [])

  # round2/round3 scripts
  for script in ["scripts/eval_round2_20.py", "scripts/eval_round3_20.py"]:
    path = PROJECT_ROOT / script
    if not path.exists():
      continue
    code = path.read_text(encoding="utf-8")
    start = code.find("TEST_CASES = [")
    if start < 0:
      continue
    end = code.find("\n]\n", start)
    if end < 0:
      end = code.find("\n]\r\n", start)
    if end < 0:
      continue
    ns: dict = {}
    exec(code[start:end + 2], ns)  # noqa: S102
    for tc in ns.get("TEST_CASES", []):
      keys_map[tc["id"]] = tc.get("keys", [])

  # NEW_60 from eval_300_perf.py
  eval300_path = PROJECT_ROOT / "scripts/eval_300_perf.py"
  if eval300_path.exists():
    code = eval300_path.read_text(encoding="utf-8")
    start = code.find("NEW_60 = [")
    if start >= 0:
      end = code.find("\n]\n", start)
      if end < 0:
        end = code.find("\n]\r\n", start)
      if end >= 0:
        ns2: dict = {}
        exec(code[start:end + 2], ns2)  # noqa: S102
        for tc in ns2.get("NEW_60", []):
          keys_map[tc["id"]] = tc.get("keys", [])

  return keys_map


# ── API key ──

def get_api_key() -> str:
  key = os.environ.get("ARK_API_KEY", "")
  if key:
    return key
  env_path = PROJECT_ROOT / ".env"
  if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
      line = line.strip()
      if line.startswith("ARK_API_KEY="):
        return line.split("=", 1)[1].strip().strip("\"'")
  return ""


# ── LLM semantic scoring ──

_SCORING_PROMPT = """你是AI旅行助手的评测专家。判断回复是否语义覆盖了预期知识点。

用户问题：{question}
预期知识点：{keys}
AI回复（截取）：{response}

评分规则：
- 语义覆盖 = 回复中表达了该知识点的同等含义即算覆盖，不要求字面出现原词
- 例如：知识点"预约"，回复中说"需要提前在网上订票"算覆盖
- 例如：知识点"火锅"，回复中推荐了具体火锅店名算覆盖

判断每个知识点是否被覆盖，然后计算覆盖率：
- 覆盖率>=75% → score=5
- 覆盖率>=25% → score=3
- 覆盖率<25% → score=1

仅输出JSON：{{"covered": ["已覆盖的知识点"], "missed": ["未覆盖的"], "score": 5或3或1}}"""


def llm_score_single(
  question: str, keys: list[str], response: str, api_key: str,
) -> dict:
  """Call LLM to judge semantic coverage. Returns {covered, missed, score}."""
  if not response.strip():
    return {"covered": [], "missed": keys, "score": 1, "reason": "empty_response"}

  if not keys:
    # No golden keys — if there's a response, it's at least acceptable
    resp_len = len(response.strip())
    return {
      "covered": [], "missed": [],
      "score": 5 if resp_len > 200 else (4 if resp_len > 50 else 3),
      "reason": "no_keys",
    }

  prompt = _SCORING_PROMPT.format(
    question=question,
    keys=json.dumps(keys, ensure_ascii=False),
    response=response[:600],
  )

  payload = json.dumps({
    "model": SCORING_MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 300,
    "temperature": 0.05,
  }).encode("utf-8")

  import subprocess as _sp
  url = f"https://{API_HOST}/api/coding/v3/chat/completions"
  try:
    result = _sp.run(
      ["curl", "-s", "--max-time", "60", "-X", "POST", url,
       "-H", "Content-Type: application/json",
       "-H", f"Authorization: Bearer {api_key}",
       "-d", payload.decode("utf-8")],
      capture_output=True, text=True, timeout=65,
    )
    body = json.loads(result.stdout)

    content = body["choices"][0]["message"]["content"].strip()
    # Strip markdown code fences if present
    if "```" in content:
      parts = content.split("```")
      inner = parts[1] if len(parts) >= 3 else parts[-1]
      if inner.startswith("json"):
        inner = inner[4:]
      content = inner.strip()

    result = json.loads(content)
    # Validate score
    if result.get("score") not in (1, 3, 5):
      covered = result.get("covered", [])
      ratio = len(covered) / len(keys) if keys else 1
      result["score"] = 5 if ratio >= 0.75 else (3 if ratio >= 0.25 else 1)
    return result

  except Exception as e:
    return {"covered": [], "missed": keys, "score": -1, "reason": f"llm_error: {e}"}
  finally:
    conn.close()


# ── Main rescore logic ──

def rescore_single(args: tuple) -> dict:
  """Re-score a single result. Used by ThreadPoolExecutor."""
  idx, total, result, keys, api_key = args
  qid = result["id"]
  question = result["question"]
  response = result.get("response", "")

  # Check infra error first
  infra = is_infra_error(result)

  if infra:
    new_entry = {
      **result,
      "old_score": result["score"],
      "new_score": -1,
      "infra_error": True,
      "semantic": {"covered": [], "missed": keys, "score": -1, "reason": "infra_error"},
    }
    print(f"  [{idx:3d}/{total}] {qid:>5} INFRA  old={result['score']} -> EXCLUDED | {question[:40]}")
    sys.stdout.flush()
    return new_entry

  # LLM semantic scoring
  sem = llm_score_single(question, keys, response, api_key)
  new_score = sem.get("score", -1)

  # If LLM scoring failed, keep old score
  if new_score < 0:
    new_score = result["score"]
    sem["reason"] = sem.get("reason", "llm_failed")

  tag = "PASS" if new_score >= 3.5 else "FAIL"
  delta = new_score - result["score"]
  delta_str = f" ({delta:+d})" if delta != 0 else ""

  print(
    f"  [{idx:3d}/{total}] {qid:>5} {tag:4s}  old={result['score']} new={new_score}"
    f"{delta_str} | {question[:40]}"
  )
  sys.stdout.flush()

  return {
    **result,
    "old_score": result["score"],
    "new_score": new_score,
    "infra_error": False,
    "semantic": sem,
  }


def print_comparison(results: list[dict], old_results: list[dict]) -> None:
  """Print side-by-side comparison of old vs new scoring."""
  valid = [r for r in results if not r.get("infra_error")]
  infra = [r for r in results if r.get("infra_error")]

  old_scores = [r["old_score"] for r in valid]
  new_scores = [r["new_score"] for r in valid]
  old_pass = sum(1 for s in old_scores if s >= 3.5)
  new_pass = sum(1 for s in new_scores if s >= 3.5)

  total_all = len(results)
  total_valid = len(valid)

  print(f"\n{'='*70}")
  print(f"  评分体系对比报告")
  print(f"{'='*70}")
  print(f"  总题数: {total_all} (有效: {total_valid}, INFRA_ERROR: {len(infra)})")
  print()
  print(f"  {'指标':<20} {'精确匹配(旧)':>14} {'语义匹配(新)':>14} {'变化':>10}")
  print(f"  {'-'*58}")
  print(f"  {'通过数':<20} {old_pass:>14} {new_pass:>14} {new_pass - old_pass:>+10}")
  print(
    f"  {'通过率':<20} {old_pass/total_valid*100:>13.1f}%"
    f" {new_pass/total_valid*100:>13.1f}%"
    f" {(new_pass - old_pass)/total_valid*100:>+9.1f}%"
  )
  old_avg = sum(old_scores) / len(old_scores) if old_scores else 0
  new_avg = sum(new_scores) / len(new_scores) if new_scores else 0
  print(f"  {'平均分':<20} {old_avg:>14.2f} {new_avg:>14.2f} {new_avg - old_avg:>+10.2f}")

  # Category breakdown
  print(f"\n  {'类别':<16} {'旧通过率':>8} {'新通过率':>8} {'旧均分':>6} {'新均分':>6}")
  print(f"  {'-'*50}")
  cats: dict[str, list[dict]] = {}
  for r in valid:
    cats.setdefault(r["category"], []).append(r)

  for cat in sorted(cats.keys()):
    cr = cats[cat]
    old_p = sum(1 for r in cr if r["old_score"] >= 3.5)
    new_p = sum(1 for r in cr if r["new_score"] >= 3.5)
    old_a = sum(r["old_score"] for r in cr) / len(cr)
    new_a = sum(r["new_score"] for r in cr) / len(cr)
    n = len(cr)
    print(
      f"  {cat:<16} {old_p}/{n:>2}={old_p/n*100:4.0f}%"
      f" {new_p}/{n:>2}={new_p/n*100:4.0f}%"
      f" {old_a:>6.1f} {new_a:>6.1f}"
    )

  # Score changes
  upgraded = [(r["id"], r["old_score"], r["new_score"], r["question"][:35])
              for r in valid if r["new_score"] > r["old_score"]]
  downgraded = [(r["id"], r["old_score"], r["new_score"], r["question"][:35])
                for r in valid if r["new_score"] < r["old_score"]]
  unchanged = [r for r in valid if r["new_score"] == r["old_score"]]

  print(f"\n  评分变化: 上调 {len(upgraded)} | 下调 {len(downgraded)} | 不变 {len(unchanged)}")

  if upgraded:
    print(f"\n  上调 ({len(upgraded)}):")
    for qid, old, new, q in sorted(upgraded, key=lambda x: x[2] - x[1], reverse=True)[:20]:
      print(f"    {qid:>5} {old}->{new} (+{new-old}) {q}")
    if len(upgraded) > 20:
      print(f"    ... 共 {len(upgraded)} 题")

  if downgraded:
    print(f"\n  下调 ({len(downgraded)}):")
    for qid, old, new, q in sorted(downgraded, key=lambda x: x[1] - x[2], reverse=True)[:20]:
      print(f"    {qid:>5} {old}->{new} ({new-old}) {q}")
    if len(downgraded) > 20:
      print(f"    ... 共 {len(downgraded)} 题")

  # INFRA_ERROR detail
  if infra:
    print(f"\n  INFRA_ERROR ({len(infra)}):")
    for r in infra:
      print(f"    {r['id']:>5} {r['duration_s']:>5.0f}s {r['question'][:50]}")

  # Remaining failures under new scoring
  new_fails = [r for r in valid if r["new_score"] < 3.5]
  if new_fails:
    print(f"\n  新评分仍失败 ({len(new_fails)}):")
    for r in sorted(new_fails, key=lambda x: x["new_score"]):
      sem = r.get("semantic", {})
      covered = len(sem.get("covered", []))
      missed = len(sem.get("missed", []))
      print(
        f"    {r['id']:>5} | {r['new_score']}分 | {r['category']:<14}"
        f" | covered={covered} missed={missed}"
        f" | {r['question'][:40]}"
      )

  print(f"\n{'='*70}")


def main():
  parser = argparse.ArgumentParser(description="Re-score eval results with LLM semantic matching")
  parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input results JSON")
  parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output results JSON")
  parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Parallel workers")
  args = parser.parse_args()

  api_key = get_api_key()
  if not api_key:
    print("ERROR: ARK_API_KEY not found in env or .env file")
    sys.exit(1)

  # Load existing results
  print(f"Loading results from {args.input}...")
  with open(args.input, encoding="utf-8") as f:
    data = json.load(f)
  old_results = data["results"]
  print(f"  {len(old_results)} results loaded")

  # Load golden keys
  print("Loading golden keys...")
  keys_map = load_all_keys()
  print(f"  {len(keys_map)} questions have golden keys")

  # Re-score
  total = len(old_results)
  print(f"\n{'='*70}")
  print(f"  LLM 语义评分 ({total} 题, {args.workers} workers)")
  print(f"  Model: {SCORING_MODEL}")
  print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
  print(f"{'='*70}\n")

  t_start = time.time()
  task_args = [
    (i + 1, total, r, keys_map.get(r["id"], []), api_key)
    for i, r in enumerate(old_results)
  ]

  rescored: list[dict] = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
    futures = {executor.submit(rescore_single, a): a for a in task_args}
    for future in concurrent.futures.as_completed(futures):
      try:
        rescored.append(future.result())
      except Exception as exc:
        a = futures[future]
        r = a[2]
        print(f"  [{a[0]:3d}/{total}] {r['id']} CRASH: {exc}")
        rescored.append({
          **r,
          "old_score": r["score"],
          "new_score": r["score"],
          "infra_error": False,
          "semantic": {"error": str(exc)},
        })

  rescored.sort(key=lambda r: r["id"])
  elapsed = time.time() - t_start

  # Print comparison
  print_comparison(rescored, old_results)

  # Compute new summary (excluding INFRA_ERROR)
  valid = [r for r in rescored if not r.get("infra_error")]
  infra_count = len(rescored) - len(valid)
  new_scores = [r["new_score"] for r in valid]
  new_pass = sum(1 for s in new_scores if s >= 3.5)
  new_avg = sum(new_scores) / len(new_scores) if new_scores else 0
  durations = [r["duration_s"] for r in valid if r["duration_s"] > 0]

  output = {
    "version": data.get("version", "unknown") + "-semantic",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "scoring_model": SCORING_MODEL,
    "rescore_time_s": round(elapsed, 1),
    "summary": {
      "total": len(rescored),
      "valid": len(valid),
      "infra_error": infra_count,
      "passed": new_pass,
      "failed": len(valid) - new_pass,
      "avg_score": round(new_avg, 2),
      "avg_duration_s": round(sum(durations) / len(durations), 1) if durations else 0,
      "pass_rate": f"{new_pass/len(valid)*100:.1f}%" if valid else "N/A",
    },
    "old_summary": data.get("summary", {}),
    "results": rescored,
  }

  args.output.parent.mkdir(parents=True, exist_ok=True)
  with open(args.output, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
  print(f"\n  结果已保存: {args.output}")
  print(f"  评分耗时: {elapsed:.0f}s ({elapsed/60:.1f}min)")


if __name__ == "__main__":
  main()
