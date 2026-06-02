#!/usr/bin/env python3
"""Fast calibration of the self-check (injection+scope) prompt for the NeMo baseline.
Tests a candidate prompt against N benign + N attack from a corpus via Ollama /v1 with
NeMo-like settings (temp 0, short max_tokens, parse 'yes'->block). Reports benign FP and
attack recall so the prompt is a FAIR config (low over-block, high catch) before the full
run. Usage: python3 scripts/nemo_calibrate.py <corpus_dir> [N]"""
import json, os, sys, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path, n):
    rows = []
    p = path if os.path.isfile(path) else None
    if p is None:
        for f in sorted(os.listdir(path)):
            if f.endswith(".jsonl"):
                p = os.path.join(path, f); break
    for ln in open(p):
        o = json.loads(ln)
        if o.get("prompt"):
            rows.append(o["prompt"])
        if len(rows) >= n:
            break
    return rows


def selfcheck(prompt_tmpl, user, model="llama3.1:8b"):
    content = prompt_tmpl.replace("{{ user_input }}", user)
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 5,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request("http://localhost:11434/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read())["choices"][0]["message"]["content"].strip().lower()
    return out.startswith("yes") or out == "yes"  # block if yes


def main():
    corpus = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    tmpl = open(os.path.join(BASE, "nemo_config", "selfcheck_prompt.txt")).read()
    atk = load(os.path.join(corpus, "attacks"), n)
    ben = load(os.path.join(corpus, "benign"), n)
    tp = sum(selfcheck(tmpl, p) for p in atk)
    fp = sum(selfcheck(tmpl, p) for p in ben)
    print(f"corpus={corpus} n_atk={len(atk)} n_ben={len(ben)}")
    print(f"  attack recall (block rate) = {tp}/{len(atk)} = {tp/len(atk):.2f}")
    print(f"  benign FP   (block rate) = {fp}/{len(ben)} = {fp/len(ben):.2f}")


if __name__ == "__main__":
    main()
