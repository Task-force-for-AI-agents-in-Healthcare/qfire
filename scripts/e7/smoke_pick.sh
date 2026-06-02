#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
source .venv-e7/bin/activate
export LOCAL_LLM_PORT=11434   # Ollama direct, guard-off
for M in gpt-oss:20b qwen3-coder:30b gemma3:27b; do
  echo "=== $M ==="
  python -m agentdojo.scripts.benchmark --model LOCAL --model-id "$M" \
    -s workspace -ut user_task_0 -ut user_task_1 -ut user_task_2 \
    --logdir runs/smoke/"${M//[:\/]/_}" 2>&1 | tail -25 || echo "MODEL $M FAILED"
done
