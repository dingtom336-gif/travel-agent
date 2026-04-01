#!/usr/bin/env python3
"""Run V2 200-question evaluation against TravelMind live server.

Usage:
  python run_eval_200.py                        # Run all 200 questions
  python run_eval_200.py --cat=basic_info       # Run one category
  python run_eval_200.py --range=41-60          # Run T041-T060
  python run_eval_200.py --cat=robustness --server=http://150.158.192.237:8000
  python run_eval_200.py --concurrency=3        # Run 3 queries in parallel
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

# Add project root for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agent.simulator.eval_v2_scoring import V2Evaluator  # noqa: E402

EVAL_FILE = Path(__file__).parent / "eval_200.json"
RESULTS_FILE = Path(__file__).parent / "eval_200_results.json"
DEFAULT_SERVER = "http://localhost:8000"
TIMEOUT = 180


def parse_args() -> dict:
  """Parse CLI arguments."""
  opts = {
    "cat": None, "range": None,
    "server": DEFAULT_SERVER, "concurrency": 1,
  }
  for arg in sys.argv[1:]:
    if "=" in arg:
      key, val = arg.lstrip("-").split("=", 1)
      if key == "concurrency":
        opts[key] = int(val)
      elif key == "range":
        parts = val.split("-")
        opts[key] = (int(parts[0]), int(parts[1]))
      else:
        opts[key] = val
  return opts


async def _send_single_message(
  client: httpx.AsyncClient,
  server: str,
  message: str,
  session_id: str | None = None,
) -> tuple[str, str | None, str]:
  """Send a single message to SSE endpoint, return (full_text, session_id, error)."""
  text_parts: list[str] = []
  returned_session_id: str | None = session_id
  error = ""

  try:
    payload: dict = {"message": message}
    if session_id:
      payload["session_id"] = session_id
    async with client.stream(
      "POST", f"{server}/api/chat/stream",
      json=payload,
      timeout=TIMEOUT,
    ) as resp:
      async for line in resp.aiter_lines():
        if not line.strip():
          continue
        if line.startswith("data: "):
          try:
            data = json.loads(line[6:].strip())
          except json.JSONDecodeError:
            continue
          if "content" in data:
            text_parts.append(data["content"])
          if data.get("session_id"):
            returned_session_id = data["session_id"]
  except httpx.ReadTimeout:
    error = "TIMEOUT"
  except Exception as exc:
    error = str(exc)[:200]

  return "".join(text_parts), returned_session_id, error


async def run_query(
  client: httpx.AsyncClient,
  question: dict,
  server: str,
) -> dict:
  """Send a question to SSE endpoint, collect full response.

  If the question has a 'context' field, send context messages first
  (using the same session_id) to establish conversation history,
  then send the actual question for evaluation.
  """
  qid = question["id"]
  query = question["q"]
  context_msgs = question.get("context", [])

  t0 = time.time()
  ttfb = None
  text_parts: list[str] = []
  has_done = False
  events_count = 0
  error = ""
  session_id: str | None = None
  context_count = len(context_msgs)

  # Phase 1: Send context messages to build conversation history
  for ctx_msg in context_msgs:
    ctx_text, session_id, ctx_error = await _send_single_message(
      client, server, ctx_msg["content"], session_id,
    )
    if ctx_error:
      error = f"CONTEXT_ERROR: {ctx_error}"
      break
    # Brief pause between context messages
    await asyncio.sleep(0.5)

  # Phase 2: Send the actual evaluation question
  if not error:
    try:
      payload: dict = {"message": query}
      if session_id:
        payload["session_id"] = session_id
      async with client.stream(
        "POST", f"{server}/api/chat/stream",
        json=payload,
        timeout=TIMEOUT,
      ) as resp:
        async for line in resp.aiter_lines():
          if not line.strip():
            continue
          if line.startswith("event: "):
            events_count += 1
          elif line.startswith("data: "):
            try:
              data = json.loads(line[6:].strip())
            except json.JSONDecodeError:
              continue
            if "content" in data and ttfb is None:
              ttfb = time.time() - t0
            if "content" in data:
              text_parts.append(data["content"])
            if data.get("session_id"):
              has_done = True
    except httpx.ReadTimeout:
      error = "TIMEOUT"
    except Exception as exc:
      error = str(exc)[:200]

  total_ms = int((time.time() - t0) * 1000)
  ttfb_ms = int(ttfb * 1000) if ttfb else None
  full_text = "".join(text_parts)

  return {
    "id": qid,
    "cat": question.get("cat", ""),
    "query": query,
    "response": full_text,
    "total_ms": total_ms,
    "ttfb_ms": ttfb_ms,
    "chars": len(full_text),
    "has_done": has_done,
    "events_count": events_count,
    "error": error,
    "context_turns": context_count,
  }


async def run_batch(
  client: httpx.AsyncClient,
  questions: list[dict],
  server: str,
  concurrency: int,
) -> list[dict]:
  """Run queries with optional concurrency."""
  if concurrency <= 1:
    results = []
    for q in questions:
      r = await run_query(client, q, server)
      results.append(r)
      await asyncio.sleep(1)
    return results

  # Concurrent execution with semaphore
  sem = asyncio.Semaphore(concurrency)
  async def _run(q: dict) -> dict:
    async with sem:
      r = await run_query(client, q, server)
      await asyncio.sleep(0.5)
      return r

  return await asyncio.gather(*[_run(q) for q in questions])


def print_summary(summary: dict) -> None:
  """Print formatted summary table."""
  print(f"\n{'=' * 70}")
  print(f"  V2 EVALUATION SUMMARY")
  print(f"{'=' * 70}")
  print(f"  Total: {summary['count']} | Valid: {summary['valid']} | Errors: {summary['errors']}")
  print(f"  Avg Score: {summary['avg_score']}/5.0 | Pass Rate: {summary['pass_rate']}")

  cat_stats = summary.get("category_stats", {})
  if cat_stats:
    # Category order
    cat_order = [
      "basic_info", "constrained_plan", "in_trip",
      "transaction", "robustness",
    ]
    cat_labels = {
      "basic_info": "基础事实",
      "constrained_plan": "多约束规划",
      "in_trip": "行中即时",
      "transaction": "交易决策",
      "robustness": "鲁棒性/安全",
    }
    print(f"\n  {'Category':<14} {'Label':<12} {'N':>4} {'Avg':>6} {'Min':>6} {'Max':>6} {'Pass':>8}")
    print(f"  {'-' * 60}")
    for cat in cat_order:
      if cat in cat_stats:
        s = cat_stats[cat]
        label = cat_labels.get(cat, cat)
        print(
          f"  {cat:<14} {label:<12} {s['count']:>4} "
          f"{s['avg']:>6} {s['min']:>6} {s['max']:>6} "
          f"{s['pass']}/{s['count']:>3}"
        )

  dim_stats = summary.get("dimension_stats", {})
  if dim_stats:
    print(f"\n  {'Dimension':<12} {'Label':<10} {'Avg':>6} {'Min':>5} {'Max':>5}")
    print(f"  {'-' * 45}")
    for dim_key in ["accuracy", "constraint", "reasoning", "conversion", "safety"]:
      if dim_key in dim_stats:
        d = dim_stats[dim_key]
        print(
          f"  {dim_key:<12} {d['label']:<10} "
          f"{d['avg']:>6} {d['min']:>5} {d['max']:>5}"
        )

  fa = summary.get("failure_attribution", {})
  if fa:
    print(f"\n  Failure Attribution (worst dimension per failed question):")
    for dim_name, count in fa.items():
      print(f"    {dim_name}: {count} questions")

  print(f"{'=' * 70}")


async def main() -> None:
  opts = parse_args()
  server = opts["server"]
  concurrency = opts["concurrency"]

  # Load eval set
  eval_data = json.loads(EVAL_FILE.read_text())
  questions = eval_data["questions"]
  cat_overrides = {
    k: v.get("weight_override", {})
    for k, v in eval_data.get("categories", {}).items()
  }

  # Apply filters
  if opts["cat"]:
    questions = [q for q in questions if q["cat"] == opts["cat"]]
  if opts["range"]:
    lo, hi = opts["range"]
    questions = [
      q for q in questions
      if lo <= int(q["id"][1:]) <= hi
    ]

  total = len(questions)
  multi_turn_count = sum(1 for q in questions if q.get("context"))
  print(f"TravelMind V2 Evaluation — {total} questions ({multi_turn_count} multi-turn)")
  print(f"Server: {server} | Concurrency: {concurrency}")
  print(f"{'=' * 70}")

  # Health check
  async with httpx.AsyncClient() as client:
    try:
      r = await client.get(f"{server}/health", timeout=15)
      health = r.json()
      model = health.get("llm_model", "?")
      has_key = "yes" if health.get("has_api_key") else "no"
      print(f"Server OK | Model: {model} | API key: {has_key}\n")
    except Exception as e:
      print(f"Server not reachable: {e}")
      sys.exit(1)

  # Run evaluation
  evaluator = V2Evaluator(weight_overrides=cat_overrides)
  eval_results: list[dict] = []

  async with httpx.AsyncClient() as client:
    raw_results = await run_batch(client, questions, server, concurrency)

  # Score all results
  for i, (q, result) in enumerate(zip(questions, raw_results)):
    qid = q["id"]
    if result["error"]:
      print(f"  [{i+1}/{total}] {qid} ❌ {result['error']}")
      eval_results.append({
        "question_id": qid,
        "category": q["cat"],
        "final_score": 0,
        "pass": False,
        "error": result["error"],
        "dimensions": {},
        "raw": result,
      })
    else:
      ev = evaluator.evaluate(result["response"], q)
      ev["raw"] = result
      eval_results.append(ev)

      status = "✅" if ev["pass"] else "⚠️"
      ms = result["total_ms"]
      chars = result["chars"]
      fs = ev["final_score"]
      ctx_info = f" | ctx:{result.get('context_turns', 0)}" if result.get("context_turns") else ""
      print(
        f"  [{i+1}/{total}] {qid} {status} "
        f"{ms}ms | {chars}字 | {fs}/5.0{ctx_info}"
      )

      # Show dimension details for failures
      if not ev["pass"]:
        for dim_key, dim_data in ev["dimensions"].items():
          if dim_data["score"] <= 2:
            print(
              f"    ↳ {dim_data['label']}: "
              f"{dim_data['score']}/5 — {dim_data['reason']}"
            )

  # Generate summary
  summary = evaluator.evaluate_batch(eval_results)

  # Save full output
  output = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "server": server,
    "total_questions": total,
    "evaluations": eval_results,
    "summary": summary,
  }
  RESULTS_FILE.write_text(
    json.dumps(output, ensure_ascii=False, indent=2)
  )
  print(f"\nResults saved to {RESULTS_FILE}")

  print_summary(summary)


if __name__ == "__main__":
  asyncio.run(main())
