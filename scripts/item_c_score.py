#!/usr/bin/env python3
"""Item C / expert validation: score the gold-seed and the 200-prompt sample with QFIRE.

Runs the deployable healthcare chain (bench_combined: injection + PHI + scope) over:
  (1) the 40 expert-authored gold prompts  -> a real sanity-check result
      ("does QFIRE catch the clinician/privacy-authored attacks and pass the benign set?")
  (2) the 200-prompt blinded sample        -> hidden QFIRE verdicts, sealed into the
      master key so a later expert-vs-QFIRE comparison is possible. These verdicts are
      NOT shown to reviewers.

The qfire bench harness reads an --attacks dir and a --benign dir and dumps per-prompt
predictions in input order (all attacks first, then all benign). We write one file per
dir and keep the id order so the dump can be zipped back to prompt ids.

Outputs (under bench-out/expert_validation/):
  gold_scored.jsonl     per gold prompt: id, label, category, qfire blocked/score, correct
  gold_summary.json     attack-catch rate, benign pass rate, per-category breakdown
  sample_verdicts.jsonl per sample prompt: review_id, qfire blocked/score (hidden key)
"""
import json
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(HERE, "target/release/qfire")
DATA = os.path.join(HERE, "corpora/expert_validation")
OUT = os.path.join(HERE, "bench-out/expert_validation")
CHAIN = "bench_combined"
SEED = 42


def run_bench(records, label_key):
    """records: list of dicts with 'prompt' and a label (attack/benign under label_key).
    Returns list of {blocked, is_attack, score} aligned to attacks-then-benign order,
    plus the id order used."""
    attacks = [r for r in records if r[label_key] == "attack"]
    benign = [r for r in records if r[label_key] == "benign"]
    with tempfile.TemporaryDirectory() as td:
        adir = os.path.join(td, "attacks")
        bdir = os.path.join(td, "benign")
        os.makedirs(adir)
        os.makedirs(bdir)
        with open(os.path.join(adir, "a.jsonl"), "w") as f:
            for r in attacks:
                f.write(json.dumps({"prompt": r["prompt"]}) + "\n")
        with open(os.path.join(bdir, "b.jsonl"), "w") as f:
            for r in benign:
                f.write(json.dumps({"prompt": r["prompt"]}) + "\n")
        dump = os.path.join(td, "dump")
        outd = os.path.join(td, "out")
        env = dict(os.environ, QFIRE_DEBERTA_DIR=os.path.join(HERE, "models/deberta"))
        subprocess.run(
            [BIN, "bench", "--chain", CHAIN, "--attacks", adir, "--benign", bdir,
             "--seed", str(SEED), "--out", outd, "--dump", dump, "--no-cache", "--quiet"],
            check=True, env=env, cwd=HERE,
        )
        dumpfile = os.path.join(dump, f"{CHAIN}.jsonl")
        preds = [json.loads(l) for l in open(dumpfile) if l.strip()]
    ordered = attacks + benign
    assert len(preds) == len(ordered), f"{len(preds)} preds vs {len(ordered)} prompts"
    return ordered, preds


def main():
    os.makedirs(OUT, exist_ok=True)

    # --- (1) gold-seed sanity check ---
    gold = [json.loads(l) for l in open(os.path.join(DATA, "gold.jsonl")) if l.strip()]
    ordered, preds = run_bench(gold, "label")
    scored = []
    for r, p in zip(ordered, preds):
        correct = p["blocked"] == (r["label"] == "attack")
        scored.append({**{k: r[k] for k in ("gold_id", "persona", "label", "category",
                                            "corpus_category")},
                       "blocked": p["blocked"], "score": p["score"], "correct": correct})
    with open(os.path.join(OUT, "gold_scored.jsonl"), "w") as f:
        for s in scored:
            f.write(json.dumps(s) + "\n")

    atk = [s for s in scored if s["label"] == "attack"]
    ben = [s for s in scored if s["label"] == "benign"]
    caught = sum(s["blocked"] for s in atk)
    passed = sum(not s["blocked"] for s in ben)
    by_cat = {}
    for s in atk:
        c = s["category"]
        by_cat.setdefault(c, [0, 0])
        by_cat[c][1] += 1
        by_cat[c][0] += s["blocked"]
    summary = {
        "chain": CHAIN,
        "attacks_total": len(atk),
        "attacks_caught": caught,
        "attack_recall": round(caught / len(atk), 4),
        "benign_total": len(ben),
        "benign_passed": passed,
        "benign_fpr": round((len(ben) - passed) / len(ben), 4),
        "per_category_attack_recall": {c: f"{n}/{t}" for c, (n, t) in sorted(by_cat.items())},
    }
    with open(os.path.join(OUT, "gold_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # --- (2) 200-prompt sample: hidden QFIRE verdicts ---
    sample = [json.loads(l) for l in open(os.path.join(DATA, "sample.jsonl")) if l.strip()]
    s_ordered, s_preds = run_bench(
        [{"prompt": r["prompt"], "label": r["benchmark_label"], "review_id": r["review_id"]}
         for r in sample], "label")
    with open(os.path.join(OUT, "sample_verdicts.jsonl"), "w") as f:
        for r, p in zip(s_ordered, s_preds):
            f.write(json.dumps({"review_id": r["review_id"], "qfire_blocked": p["blocked"],
                                "qfire_score": p["score"]}) + "\n")

    print("=== GOLD-SEED SANITY CHECK (bench_combined) ===")
    print(f"  attacks caught: {caught}/{len(atk)}  (recall {summary['attack_recall']})")
    print(f"  benign passed:  {passed}/{len(ben)}  (FPR {summary['benign_fpr']})")
    print("  per-category attack recall:")
    for c, v in summary["per_category_attack_recall"].items():
        print(f"    {c:<20} {v}")
    misses = [s["gold_id"] for s in atk if not s["blocked"]] + \
             [s["gold_id"] for s in ben if s["blocked"]]
    if misses:
        print(f"  misclassified gold ids: {', '.join(misses)}")
    print(f"\nWrote gold_scored.jsonl, gold_summary.json, sample_verdicts.jsonl -> {OUT}/")


if __name__ == "__main__":
    main()
