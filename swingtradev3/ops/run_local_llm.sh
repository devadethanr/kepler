#!/usr/bin/env bash
set -euo pipefail

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/local-llm/llama.cpp}"
LLAMA_CPP_BIN="${LLAMA_CPP_BIN:-$LLAMA_CPP_DIR/build-cuda13/bin/llama-server}"
LLAMA_CPP_MODEL="${LLAMA_CPP_MODEL:-}"
LLAMA_CPP_PORT="${LLAMA_CPP_PORT:-8080}"
LLAMA_CPP_GPU="${LLAMA_CPP_GPU:-0}"

if [[ -z "$LLAMA_CPP_MODEL" ]]; then
  LLAMA_CPP_MODEL="$(find "$LLAMA_CPP_DIR/models/qwen3-4b-instruct" -name '*.gguf' -print -quit)"
fi
if [[ ! -x "$LLAMA_CPP_BIN" ]]; then
  echo "Missing CUDA 13 llama-server: $LLAMA_CPP_BIN" >&2
  exit 1
fi
if [[ -z "$LLAMA_CPP_MODEL" || ! -f "$LLAMA_CPP_MODEL" ]]; then
  echo "Missing GGUF model. Set LLAMA_CPP_MODEL to its absolute path." >&2
  exit 1
fi

cd "$LLAMA_CPP_DIR"
export CUDA_VISIBLE_DEVICES="$LLAMA_CPP_GPU"
exec "$LLAMA_CPP_BIN" \
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
  --reasoning-budget 0
