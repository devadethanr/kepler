#!/usr/bin/env bash
set -euo pipefail

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/local-llm/llama.cpp}"
LLAMA_CPP_BIN="${LLAMA_CPP_BIN:-$LLAMA_CPP_DIR/build-cuda13/bin/llama-server}"
LLAMA_CPP_MODEL="${LLAMA_CPP_MODEL:-}"
LLAMA_CPP_PORT="${LLAMA_CPP_PORT:-8080}"
LLAMA_CPP_GPU="${LLAMA_CPP_GPU:-0}"
LLAMA_CPP_PID_FILE="${LLAMA_CPP_PID_FILE:-/tmp/swingtradev3-llama.pid}"
LLAMA_CPP_LOG_FILE="${LLAMA_CPP_LOG_FILE:-/tmp/swingtradev3-llama.log}"

if [[ -z "$LLAMA_CPP_MODEL" ]]; then
  LLAMA_CPP_MODEL="$(find "$LLAMA_CPP_DIR/models/qwen3-4b-instruct" -name '*.gguf' -print -quit)"
fi

if [[ ! -x "$LLAMA_CPP_BIN" ]]; then
  echo "Missing CUDA 13 llama-server: $LLAMA_CPP_BIN" >&2
  echo "Build it with the command documented in docs/architecture/phase-13-slow-brain-plan.md." >&2
  exit 1
fi
if [[ -z "$LLAMA_CPP_MODEL" || ! -f "$LLAMA_CPP_MODEL" ]]; then
  echo "Missing GGUF model. Set LLAMA_CPP_MODEL to its absolute path." >&2
  exit 1
fi

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

cd "$LLAMA_CPP_DIR"
CUDA_VISIBLE_DEVICES="$LLAMA_CPP_GPU" setsid "$LLAMA_CPP_BIN" \
  -m "$LLAMA_CPP_MODEL" \
  --host 0.0.0.0 \
  --port "$LLAMA_CPP_PORT" \
  --ctx-size 8192 \
  --parallel 1 \
  --n-gpu-layers 99 \
  --split-mode none \
  --main-gpu 0 \
  --flash-attn on \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --batch-size 512 \
  --ubatch-size 128 \
  --threads 6 \
  --threads-batch 12 \
  --cache-ram 0 \
  --reasoning off \
  --reasoning-budget 0 \
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
