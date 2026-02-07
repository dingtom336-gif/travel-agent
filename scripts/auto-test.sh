#!/bin/bash
# Smart test router: only run tests when relevant files are modified.
# Called by Claude hook on PostToolUse (Edit/Write).
# Reads file path from stdin JSON. Zero LLM token cost.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTEST="$PROJECT_ROOT/agent/venv2/bin/python -m pytest"

# Read hook input JSON from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# SSE-related files → run protocol + pipeline tests
if echo "$FILE_PATH" | grep -qE "(models|main|orchestrator/agent)\.py$"; then
  echo "🧪 SSE file changed → running protocol tests..."
  cd "$PROJECT_ROOT"
  $VENV_PYTEST tests/test_sse_format.py tests/test_sse_pipeline.py -q --tb=short 2>&1 | tail -5
fi

# LLM/config files → run timeout tests
if echo "$FILE_PATH" | grep -qE "(llm/client|config/settings)\.py$"; then
  echo "🧪 LLM config changed → running timeout tests..."
  cd "$PROJECT_ROOT"
  $VENV_PYTEST tests/test_timeout.py -q --tb=short 2>&1 | tail -5
fi
