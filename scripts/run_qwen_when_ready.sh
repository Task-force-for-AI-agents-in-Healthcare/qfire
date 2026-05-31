#!/usr/bin/env bash
# Wait for a new qwen3.x (non-coder) Ollama tag to appear + respond, then run the
# judge-model ablation on it after the base sweep (llama3.1+gemma4) finishes.
set +e
cd /Users/jim/Desktop/qfire || exit 1

echo "[qwen-poller] waiting for a qwen3.x tag (not qwen3-coder)..."
TAG=""
for _ in $(seq 1 360); do            # up to ~3h (30s interval)
  TAG=$(ollama list 2>/dev/null | awk 'NR>1{print $1}' \
        | grep -Ei '^qwen3' | grep -vi 'coder' | head -1)
  if [ -n "$TAG" ]; then
    # confirm it actually loads/responds
    r=$(curl -s http://localhost:11434/api/generate \
         -d "{\"model\":\"$TAG\",\"prompt\":\"Reply one word: ok\",\"stream\":false}" 2>/dev/null)
    if echo "$r" | grep -q '"response"'; then
      echo "[qwen-poller] found and verified: $TAG"
      break
    fi
  fi
  TAG=""
  sleep 30
done

if [ -z "$TAG" ]; then
  echo "[qwen-poller] no qwen3.x tag became available; exiting."
  exit 0
fi

echo "[qwen-poller] waiting for base sweep to finish..."
for _ in $(seq 1 600); do
  grep -q "JUDGE_ABL_ALL_DONE" /tmp/jabl.log 2>/dev/null && break
  sleep 20
done

echo "[qwen-poller] running ablation for $TAG"
bash scripts/judge_model_ablation.sh "$TAG"
echo "QWEN_ABL_DONE_$TAG"
