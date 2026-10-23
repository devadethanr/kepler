#!/usr/bin/env bash
set -euo pipefail

LLAMA_CPP_PID_FILE="${LLAMA_CPP_PID_FILE:-/tmp/swingtradev3-llama.pid}"
if [[ ! -f "$LLAMA_CPP_PID_FILE" ]]; then
  echo "No swingtradev3 llama.cpp PID file found."
  exit 0
fi

pid="$(cat "$LLAMA_CPP_PID_FILE")"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
fi
rm -f "$LLAMA_CPP_PID_FILE"
echo "llama.cpp stopped."
