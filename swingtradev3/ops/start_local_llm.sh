#!/usr/bin/env bash
set -euo pipefail

LLAMA_CPP_PORT="${LLAMA_CPP_PORT:-8080}"
LLAMA_CPP_GPU="${LLAMA_CPP_GPU:-0}"
LLAMA_CPP_PID_FILE="${LLAMA_CPP_PID_FILE:-/tmp/swingtradev3-llama.pid}"
LLAMA_CPP_LOG_FILE="${LLAMA_CPP_LOG_FILE:-/tmp/swingtradev3-llama.log}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if curl -fsS --max-time 2 "http://127.0.0.1:${LLAMA_CPP_PORT}/health" >/dev/null 2>&1; then
  echo "llama.cpp is already healthy on port ${LLAMA_CPP_PORT}."
  exit 0
fi
if [[ -f "$LLAMA_CPP_PID_FILE" ]]; then
  old_pid="$(cat "$LLAMA_CPP_PID_FILE")"
  if kill -0 "$old_pid" 2>/dev/null; then
    echo "Recorded llama.cpp PID $old_pid is running but unhealthy." >&2
    exit 1
  fi
  rm -f "$LLAMA_CPP_PID_FILE"
fi

CUDA_VISIBLE_DEVICES="$LLAMA_CPP_GPU" setsid "$SCRIPT_DIR/run_local_llm.sh" \
  >"$LLAMA_CPP_LOG_FILE" 2>&1 < /dev/null &
pid=$!
echo "$pid" > "$LLAMA_CPP_PID_FILE"

for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "http://127.0.0.1:${LLAMA_CPP_PORT}/health" >/dev/null 2>&1; then
    echo "llama.cpp started: pid=$pid port=$LLAMA_CPP_PORT gpu=$LLAMA_CPP_GPU"
    echo "log=$LLAMA_CPP_LOG_FILE"
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "llama.cpp exited during startup. Last log lines:" >&2
    tail -n 40 "$LLAMA_CPP_LOG_FILE" >&2
    exit 1
  fi
  sleep 1
done

echo "llama.cpp did not become healthy within 60 seconds." >&2
tail -n 40 "$LLAMA_CPP_LOG_FILE" >&2
exit 1
