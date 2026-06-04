#!/usr/bin/env python3
"""E9 harness (bench-based, fast): score multi-turn conversations through QFIRE in two
modes — full-transcript (QFIRE default) vs latest-turn-only — using `qfire bench`, which
loads the model ONCE per corpus (vs a process-per-prompt `check`). Each conversation
becomes one prompt string (full = role-tagged transcript like src/ir.rs prompt_text;
latest = last user turn). Grouped by (pattern, domain); the domain picks the chain
(healthcare -> hipaa_phi, injection -> default). block_rate per group = recall (attack
groups) or FPR (benign group). Aggregated per pattern x mode (count-weighted over domains).

Env: QFIRE_BIN, QFIRE_DEBERTA_DIR, QFIRE_JUDGE_MODEL (we use gemma2:9b).
"""
import argparse
import glob
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import gen_multiturn as g

QB = os.environ.get("QFIRE_BIN", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target/release/qfire"))
# Use the *calibrated* operating-point chains, not the strict hipaa_phi conjunction
# (which over-blocks ~1.00 benign at scale, per the paper's 3.7 calibration cross-check).
# bench_combined is QFIRE-HealthBench's deployable inj+PHI+scope chain (0.83 R / 0.08 FPR).
CHAIN = {"healthcare": "bench_combined", "injection": "default"}


def write_corpus(path, prompts):
    with open(path, "w") as f:
        for p in prompts:
            f.write(json.dumps({"prompt": p}) + "\n")


def block_rate(out_dir):
    bj = json.load(open(os.path.join(out_dir, "bench.json")))
    return bj["reports"][0]["overall"]["block_rate"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default=os.path.join(BASE, "corpora/multiturn"))
    ap.add_argument("--out", default=os.path.join(BASE, "bench-out/multiturn"))
    ap.add_argument("--empty", default="/tmp/empty_benign")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.join(args.out, "inputs"), exist_ok=True)
    os.makedirs(args.empty, exist_ok=True)

    # Group convos by (pattern, domain, label).
    groups = {}
    for fp in sorted(glob.glob(os.path.join(args.indir, "*.jsonl"))):
        for line in open(fp):
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            key = (c["pattern"], c["domain"], c["label"])
            groups.setdefault(key, []).append(c)

    # Per (group, mode): write corpus, run bench, read block_rate.
    rows = []  # (pattern, domain, label, mode, n, block_rate)
    for (pattern, domain, label), convos in sorted(groups.items()):
        chain = CHAIN.get(domain, "default")
        for mode in ("full", "latest"):
            builder = g.full_transcript if mode == "full" else g.latest_user
            prompts = [builder(c["turns"]) for c in convos]
            tag = f"{pattern}__{domain}__{mode}"
            corpus = os.path.join(args.out, "inputs", f"{tag}.jsonl")
            write_corpus(corpus, prompts)
            out_dir = os.path.join(args.out, tag)
            r = subprocess.run([QB, "bench", "--chain", chain, "--attacks", corpus,
                                "--benign", args.empty, "--seed", str(args.seed),
                                "--no-cache", "--out", out_dir],
                               capture_output=True, text=True, timeout=1800)
            try:
                br = block_rate(out_dir)
            except Exception as e:
                br = None
                print(f"  [{tag}] bench ERR: {r.stderr[-200:] or e}", flush=True)
            rows.append((pattern, domain, label, mode, len(convos), br))
            print(f"  {tag}: n={len(convos)} chain={chain} block_rate={br}", flush=True)

    json.dump([{"pattern": p, "domain": d, "label": lab, "mode": m, "n": n, "block_rate": br}
               for (p, d, lab, m, n, br) in rows],
              open(os.path.join(args.out, "groups.json"), "w"), indent=1)

    # Aggregate per pattern x mode (count-weighted over domains).
    patterns = sorted({r[0] for r in rows})
    summary = {}
    for pat in patterns:
        label = next(r[2] for r in rows if r[0] == pat)
        metric = "recall" if label == "attack" else "fpr"
        entry = {"label": label}
        for mode in ("full", "latest"):
            sub = [r for r in rows if r[0] == pat and r[3] == mode and r[5] is not None]
            tot = sum(r[4] for r in sub)
            val = (sum(r[5] * r[4] for r in sub) / tot) if tot else None
            entry[f"{metric}_{mode}"] = round(val, 4) if val is not None else None
            entry["n"] = sum(r[4] for r in sub)
        summary[pat] = entry
    json.dump(summary, open(os.path.join(args.out, "summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    print("RUN_MULTITURN_DONE")


if __name__ == "__main__":
    main()
