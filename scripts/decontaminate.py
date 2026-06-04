#!/usr/bin/env python3
"""Build a de-contaminated evaluation corpus that excludes deepset/prompt-injections
(which protectai/deberta-v3 was trained on). The jailbreak-classification subset
is genuinely held out for that detector, so it measures generalization.

Reads corpora/eval/combined.jsonl ({"prompt","label","source"}) and writes:
  corpora/eval_heldout/attacks/heldout_attacks.jsonl   ({"prompt"})
  corpora/eval_heldout/benign/heldout_benign.jsonl
(only rows whose source does NOT start with 'deepset')
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "corpora/eval/combined.jsonl")
OUT = os.path.join(BASE, "corpora/eval_heldout")


def main():
    os.makedirs(os.path.join(OUT, "attacks"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "benign"), exist_ok=True)
    na = nb = drop = 0
    with open(SRC) as f, \
         open(os.path.join(OUT, "attacks", "heldout_attacks.jsonl"), "w") as a, \
         open(os.path.join(OUT, "benign", "heldout_benign.jsonl"), "w") as b:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("source", "").startswith("deepset"):
                drop += 1
                continue
            if not o.get("prompt"):
                continue
            if o["label"] == "attack":
                a.write(json.dumps({"prompt": o["prompt"]}) + "\n"); na += 1
            else:
                b.write(json.dumps({"prompt": o["prompt"]}) + "\n"); nb += 1
    print(f"held-out (deepset removed): attacks={na} benign={nb} dropped={drop}")
    print("DECON_DONE")


if __name__ == "__main__":
    main()
