#!/usr/bin/env python3
"""E2E benchmark runner for TravelMind Theater Mode.

Runs all queries from test_queries.json against the live server,
collects timing, routing, and quality metrics, outputs a summary table.
"""
import asyncio
import json
import time
import sys
from pathlib import Path

import httpx

SERVER = "http://localhost:8000"
QUERIES_FILE = Path(__file__).parent / (sys.argv[1] if len(sys.argv) > 1 else "test_queries.json")
RESULTS_FILE = QUERIES_FILE.with_name(QUERIES_FILE.stem + "_results.json")
TIMEOUT = 150  # max seconds per query


async def run_query(client: httpx.AsyncClient, q: dict) -> dict:
  """Send a query to the SSE endpoint and collect metrics."""
  qid = q["id"]
  qtype = q["type"]
  query = q["query"]

  t0 = time.time()
  ttfb = None  # time to first text byte
  events = []
  chars = []
  sections = set()
  has_done = False
  intent = ""
  error = ""

  try:
    async with client.stream(
      "POST", f"{SERVER}/api/chat/stream",
      json={"message": query},
      timeout=TIMEOUT,
    ) as resp:
      async for line in resp.aiter_lines():
        if not line.strip():
          continue
        if line.startswith("event: "):
          events.append(line[7:].strip())
        elif line.startswith("data: "):
          data_str = line[6:].strip()
          try:
            data = json.loads(data_str)
          except json.JSONDecodeError:
            continue
          # Track first text content
          if "content" in data and ttfb is None:
            ttfb = time.time() - t0
          if "content" in data:
            chars.append(data["content"])
          # Track sections
          content_str = data.get("content", "")
          if "SECTION:" in content_str:
            import re
            for m in re.finditer(r"SECTION:(\w+)", content_str):
              sections.add(m.group(1))
          # Track done
          if data.get("session_id"):
            has_done = True
  except httpx.ReadTimeout:
    error = "TIMEOUT"
  except Exception as exc:
    error = str(exc)[:100]

  total_ms = int((time.time() - t0) * 1000)
  ttfb_ms = int(ttfb * 1000) if ttfb else None
  full_text = "".join(chars)

  return {
    "id": qid,
    "type": qtype,
    "query": query[:30],
    "total_ms": total_ms,
    "ttfb_ms": ttfb_ms,
    "chars": len(full_text),
    "sections": sorted(sections),
    "has_done": has_done,
    "events_count": len(events),
    "error": error,
    "preview": full_text[:150].replace("\n", " "),
  }


async def main():
  queries = json.loads(QUERIES_FILE.read_text())

  # Check server health
  async with httpx.AsyncClient() as client:
    try:
      r = await client.get(f"{SERVER}/health", timeout=5)
      health = r.json()
      print(f"Server: {health.get('llm_model', '?')} | API key: {health.get('has_api_key')}")
    except Exception as e:
      print(f"Server not reachable: {e}")
      sys.exit(1)

  # Run queries sequentially (to avoid rate limits)
  results = []
  total = len(queries)

  async with httpx.AsyncClient() as client:
    for i, q in enumerate(queries):
      qid = q["id"]
      print(f"\n[{i+1}/{total}] #{qid} ({q['type']}) {q['query'][:35]}...", flush=True)
      result = await run_query(client, q)
      results.append(result)

      status = "✅" if result["has_done"] and not result["error"] else "❌"
      print(f"  {status} {result['total_ms']}ms | TTFB:{result['ttfb_ms']}ms | {result['chars']}字 | {result['error'] or 'OK'}", flush=True)

      # Brief pause between queries to avoid rate limiting
      await asyncio.sleep(1)

  # Save full results
  RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2))
  print(f"\nFull results saved to {RESULTS_FILE}")

  # Print summary table
  print(f"\n{'='*80}")
  print(f"  E2E Benchmark Summary ({total} queries)")
  print(f"{'='*80}\n")

  for qtype in ["simple", "plan", "fuzzy", "emotional"]:
    type_results = [r for r in results if r["type"] == qtype]
    if not type_results:
      continue

    ok = sum(1 for r in type_results if r["has_done"] and not r["error"])
    fail = len(type_results) - ok
    avg_ms = sum(r["total_ms"] for r in type_results) // len(type_results)
    avg_ttfb = [r["ttfb_ms"] for r in type_results if r["ttfb_ms"]]
    avg_ttfb_ms = sum(avg_ttfb) // len(avg_ttfb) if avg_ttfb else 0
    avg_chars = sum(r["chars"] for r in type_results) // len(type_results)

    print(f"  {qtype.upper():10} | {ok}/{len(type_results)} OK | avg {avg_ms/1000:.1f}s | TTFB {avg_ttfb_ms/1000:.1f}s | avg {avg_chars}字")
    if fail:
      for r in type_results:
        if r["error"]:
          print(f"    ❌ #{r['id']} {r['error']}")

  # Overall
  total_ok = sum(1 for r in results if r["has_done"] and not r["error"])
  total_avg = sum(r["total_ms"] for r in results) // len(results)
  print(f"\n  TOTAL: {total_ok}/{total} OK | avg {total_avg/1000:.1f}s")
  print(f"{'='*80}")


if __name__ == "__main__":
  asyncio.run(main())
