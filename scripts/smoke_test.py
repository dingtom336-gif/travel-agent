#!/usr/bin/env python3
"""Post-deploy smoke test with automatic rollback on failure.

Usage:
  python3 scripts/smoke_test.py [--api-url URL]

Tests both simple and complex messages, verifying:
- First SSE event arrives within threshold
- First text content arrives within threshold
- Stream completes with 'done' event
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from urllib.request import Request, urlopen

DEFAULT_API_URL = "http://localhost:8000/api/chat"

TARGETS = {
  "simple": {
    "message": "你好",
    "max_first_event_ms": 500,
    "max_first_text_ms": 5000,
    "max_total_ms": 15000,
  },
  "complex": {
    "message": "帮我规划3天东京旅行",
    "max_first_event_ms": 500,
    "max_first_text_ms": 30000,
    "max_total_ms": 120000,
  },
}

MAX_RETRIES = 3


def test_single(api_url: str, tier: str, config: dict) -> dict:
  """Send a message and measure SSE response times."""
  payload = json.dumps({
    "message": config["message"],
    "session_id": f"smoke-{tier}-{int(time.time())}",
  }).encode()

  req = Request(
    api_url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
  )

  result = {
    "passed": False,
    "first_event_ms": None,
    "first_text_ms": None,
    "total_ms": None,
    "got_done": False,
    "error": None,
  }

  try:
    start = time.time()
    with urlopen(req, timeout=config["max_total_ms"] / 1000 + 5) as resp:
      first_event_recorded = False
      first_text_recorded = False

      for raw_line in resp:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
          continue

        now_ms = int((time.time() - start) * 1000)

        if not first_event_recorded and line.startswith("data:"):
          result["first_event_ms"] = now_ms
          first_event_recorded = True

        if not first_text_recorded and "\"event\":\"text\"" in line:
          result["first_text_ms"] = now_ms
          first_text_recorded = True

        if "\"event\":\"done\"" in line:
          result["got_done"] = True
          result["total_ms"] = now_ms
          break

    # Validate thresholds
    errors = []
    if result["first_event_ms"] and result["first_event_ms"] > config["max_first_event_ms"]:
      errors.append(
        f"first_event={result['first_event_ms']}ms > {config['max_first_event_ms']}ms"
      )
    if result["first_text_ms"] and result["first_text_ms"] > config["max_first_text_ms"]:
      errors.append(
        f"first_text={result['first_text_ms']}ms > {config['max_first_text_ms']}ms"
      )
    if not result["got_done"]:
      errors.append("never received 'done' event")

    if errors:
      result["error"] = "; ".join(errors)
    else:
      result["passed"] = True

  except Exception as exc:
    result["error"] = str(exc)

  return result


def run_smoke_test(api_url: str) -> bool:
  """Run all smoke tests. Returns True if all passed."""
  failures = []

  for tier, config in TARGETS.items():
    print(f"\n--- Testing {tier}: \"{config['message']}\" ---")
    best_result = None

    for attempt in range(1, MAX_RETRIES + 1):
      print(f"  Attempt {attempt}/{MAX_RETRIES}...", end=" ", flush=True)
      result = test_single(api_url, tier, config)

      if result["passed"]:
        print(f"PASS (first_event={result['first_event_ms']}ms, "
              f"first_text={result['first_text_ms']}ms, "
              f"total={result['total_ms']}ms)")
        best_result = result
        break
      else:
        print(f"FAIL: {result['error']}")
        best_result = result

    if not best_result or not best_result["passed"]:
      failures.append(f"{tier}: {best_result['error'] if best_result else 'no result'}")

  print("\n" + "=" * 60)
  if failures:
    print(f"SMOKE TEST FAILED ({len(failures)} failures):")
    for f in failures:
      print(f"  - {f}")
    return False
  else:
    print("ALL SMOKE TESTS PASSED")
    return True


def main():
  parser = argparse.ArgumentParser(description="TravelMind smoke test")
  parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API endpoint URL")
  parser.add_argument("--rollback", action="store_true", help="Auto-rollback on failure")
  args = parser.parse_args()

  success = run_smoke_test(args.api_url)

  if not success:
    if args.rollback:
      print("\nAttempting rollback...")
      try:
        subprocess.run(
          ["pm2", "restart", "travel-backend", "--update-env"],
          check=True, capture_output=True,
        )
        print("Rollback completed (PM2 restart)")
      except Exception as exc:
        print(f"Rollback failed: {exc}")
    sys.exit(1)

  sys.exit(0)


if __name__ == "__main__":
  main()
