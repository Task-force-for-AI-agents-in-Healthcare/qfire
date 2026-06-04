#!/usr/bin/env python3
"""Item C / expert validation: freeze a seeded stratified sample of QFIRE-HealthBench.

Draws 25 plaintext (technique == "none") prompts from each of the 6 attack categories
under study + 50 benign = 200 prompts. Obfuscated variants (base64/rot13/unicode/...) are
excluded by design: they are not human-readable and the de-obfuscation pipeline is
validated separately. Selection is deterministic (seed below); a manifest records exactly
which corpus rows were drawn so the sample is reproducible and auditable.

Outputs (under corpora/expert_validation/):
  sample.jsonl   one record per sampled prompt (review_id, prompt, benchmark label/category)
  manifest.json  seed, per-category counts, and the ordered list of source line indices
"""
import json
import os
import random

SEED = 42
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(HERE, "corpora/healthcare_bench/dataset.jsonl")
OUTDIR = os.path.join(HERE, "corpora/expert_validation")

# Study category -> corpus category id, and how many to draw.
ATTACK_CATS = {
    "bulk_export": 25,
    "phi_exfil": 25,
    "phi_smuggle": 25,
    "reidentification": 25,
    "cross_patient": 25,
    "clinical_advice": 25,
}
N_BENIGN = 50


def load_corpus():
    rows = []
    with open(DATASET) as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            r["_idx"] = idx  # stable provenance: line number in dataset.jsonl
            rows.append(r)
    return rows


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rows = load_corpus()
    rng = random.Random(SEED)

    # Pools: only plaintext prompts are eligible for human review.
    def plaintext(r):
        return r.get("technique", "none") == "none"

    pools = {c: [r for r in rows if r["label"] == "malicious"
                 and r["category"] == c and plaintext(r)] for c in ATTACK_CATS}
    benign_pool = [r for r in rows if r["label"] == "benign" and plaintext(r)]

    selected = []
    per_cat = {}
    for cat, n in ATTACK_CATS.items():
        pool = pools[cat]
        take = min(n, len(pool))
        if take < n:
            print(f"  WARN: {cat} has only {len(pool)} plaintext prompts; drawing {take}")
        # sort by stable idx before sampling so seed fully determines the draw
        pool = sorted(pool, key=lambda r: r["_idx"])
        selected.extend(rng.sample(pool, take))
        per_cat[cat] = take

    benign_pool = sorted(benign_pool, key=lambda r: r["_idx"])
    take_b = min(N_BENIGN, len(benign_pool))
    selected.extend(rng.sample(benign_pool, take_b))
    per_cat["benign"] = take_b

    # Stable review ids assigned in a fixed (category, idx) order -> reproducible.
    selected = sorted(selected, key=lambda r: (r["label"] != "benign", r["category"], r["_idx"]))
    sample = []
    for i, r in enumerate(selected, start=1):
        rid = f"EV{i:04d}"
        sample.append({
            "review_id": rid,
            "prompt": r["prompt"],
            "benchmark_label": "attack" if r["label"] == "malicious" else "benign",
            "benchmark_category": r["category"],
            "source": r.get("source", "native"),
            "src_idx": r["_idx"],
        })

    with open(os.path.join(OUTDIR, "sample.jsonl"), "w") as f:
        for rec in sample:
            f.write(json.dumps(rec) + "\n")

    manifest = {
        "seed": SEED,
        "dataset": "corpora/healthcare_bench/dataset.jsonl",
        "filter": "technique == none (plaintext only)",
        "total": len(sample),
        "per_category": per_cat,
        "src_indices": [rec["src_idx"] for rec in sample],
        "review_ids": {rec["review_id"]: {"category": rec["benchmark_category"],
                                           "label": rec["benchmark_label"],
                                           "src_idx": rec["src_idx"]} for rec in sample},
    }
    with open(os.path.join(OUTDIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote {len(sample)} prompts -> {OUTDIR}/sample.jsonl")
    for c, n in per_cat.items():
        print(f"  {c:<18} {n}")


if __name__ == "__main__":
    main()
