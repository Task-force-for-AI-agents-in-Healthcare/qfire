# Cross-Model Policy-Verbosity Ablation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repeat the policy-verbosity ablation across 5 judge models (~3B→~12B, 3 families) on a shared 300-attack subset, then chart the latency × accuracy × policy-length tradeoff (does the T2 sweet-spot hold; what does length cost in latency).

**Architecture:** Reuse the existing 16 judge-only conditions and benign corpora unchanged. Build a seeded 300-attack subset once; reuse the existing llama3.2 full dumps by positional slicing (dumps are corpus-ordered — `src/bench/mod.rs:141-165`); run the other 4 models via `QFIRE_JUDGE_MODEL` into per-model output dirs. Accuracy (TPR/TNR/J) comes from dumps, latency (`mean_detector_ms`) from each run's `bench.json`. A cross-model analyzer + 3-panel figure (J vs rung, latency vs rung, J-vs-latency Pareto) tells the story.

**Tech Stack:** existing `qfire` CLI (`bench`, `QFIRE_JUDGE_MODEL` env override), bash, Python 3 stdlib + matplotlib (already used for `scripts/plot_policy_length.py`), local Ollama.

> **⚠️ Amendment (during execution — the committed scripts are authoritative over the code blocks below).** The grid changed: `qwen3:4b`/`qwen3:8b` proved unusable as fast one-line judges (reasoning models that ramble and never emit `IN/OUT SCOPE`, ~10s/call, abstain→allow). Final 6-model grid: `llama3.2` (reused slice), `phi3.5:3.8b`, `llama3.1:8b`, `gemma2:9b`, `gemma4:latest`, `deepseek-r1:latest` (added at user request as a *working* but slow reasoning judge, ~4.1s/call). The attack subset was trimmed 300→**150** and renamed `attacks_subset` (count-agnostic) to keep the run ~9h. Task 1 (pull qwen3:8b) is moot — phi3.5/gemma2/deepseek-r1 were already installed. Slice rows are now **200** (150+50), not 350. See the design's "Grid revision" note for rationale.

---

## ⚠️ Critical constraints (read first)

1. **`--no-cache` on every bench run** — the verdict cache key omits scope
   (`src/engine.rs:244-250`); without it the 4 rungs of a domain collude. The
   driver must pass it.
2. **Same 300 attacks for every model.** All 4 run-models bench the *same* subset
   file; the llama3.2 reuse slices its existing dumps at the *same* attack indices
   (+ all 50 benign rows). Order must match: subset file is written in
   sorted-index order; the llama3.2 slice takes rows at those sorted indices then
   the benign rows.
3. **Dumps are corpus-ordered** (attacks `0..N-1` then benign `0..M-1`,
   `src/bench/mod.rs:141-165`). The llama3.2 full dumps have 929 attack rows then
   50 benign rows (979 total). Slice = `[rows[i] for i in sorted_idx]` (300) `+
   rows[929:979]` (50).
4. **Abstain is not separately measured** — `score` (`judge.rs:139`) maps abstain
   to ~0.7, colliding with weak-allow. Abstain surfaces as depressed TPR. Do not
   add an abstain column.
5. **Latency** = `mean_detector_ms` from each chain's entry in `bench.json`
   (judge-only ⇒ ≈ judge call time). llama3.2 latency comes from its existing
   full `bench-out/policy_length/<domain>/bench.json` (per-call latency is
   corpus-size-independent).

---

## File structure

| Path | Created/Modified | Responsibility |
|------|------------------|----------------|
| `scripts/make_attack_subset.py` | Create | Seeded 300-of-929 attack subset: writes the subset JSONL + the chosen sorted indices JSON. Pure helper `pick_indices` unit-tested. |
| `scripts/test_make_attack_subset.py` | Create | Tests for `pick_indices` (determinism, count, sorted, in-range). |
| `corpora/policy_length/attacks_subset/attacks_subset.jsonl` | Create (output) | The shared 300-attack subset. |
| `corpora/policy_length/attacks_subset/indices.json` | Create (output) | The 300 sorted attack indices (for the llama3.2 slice). |
| `scripts/slice_llama32_dumps.py` | Create | Positionally slice existing llama3.2 dumps → `bench-out/policy_length_llama3.2/`. Pure helper `slice_rows` unit-tested. |
| `scripts/test_slice_llama32_dumps.py` | Create | Tests for `slice_rows`. |
| `scripts/run_cross_model.sh` | Create | Per-model driver (QFIRE_JUDGE_MODEL, 4 domains × 4 rungs, --no-cache, --dump). |
| `scripts/analyze_cross_model.py` | Create | Cross-model metrics + latency → `bench-out/policy_length_xmodel/results.md`. Pure helpers unit-tested. |
| `scripts/test_analyze_cross_model.py` | Create | Tests for the cross-model loader/latency helpers. |
| `scripts/plot_cross_model.py` | Create | 3-panel figure → `paper/figs/policy_length_xmodel.png`. |
| `bench-out/policy_length_<model>/…` | Create (run output) | Per-model bench artifacts (gitignored). |
| `bench-out/policy_length_xmodel/results.md` | Create (run output) | Cross-model results table. |
| `docs/superpowers/specs/2026-05-31-cross-model-policy-verbosity-results.md` | Create | Findings doc. |

Models (slug = tag with `:`/`.`→`_`): `llama3.2:latest`→`llama3.2`, `qwen3:4b`→`qwen3_4b`, `llama3.1:8b`→`llama3.1_8b`, `qwen3:8b`→`qwen3_8b`, `gemma4:latest`→`gemma4`.

---

## Task 1: Pull qwen3:8b and confirm the model grid

**Files:** none (environment)

- [ ] **Step 1: Pull the one missing model**

Run: `ollama pull qwen3:8b`
Expected: completes; `ollama list | grep -E 'qwen3:8b'` shows a row.

- [ ] **Step 2: Confirm all 5 judge tags resolve**

Run:
```bash
for m in llama3.2:latest qwen3:4b llama3.1:8b qwen3:8b gemma4:latest; do
  echo -n "$m: "; ollama list | grep -q "^$m" && echo OK || echo MISSING
done
```
Expected: all 5 `OK`.

- [ ] **Step 3: Build the release binary (needed by the driver)**

Run: `cargo build --release 2>&1 | tail -2`
Expected: `Finished \`release\`...`.

(No commit — environment only.)

---

## Task 2: Seeded 300-attack subset

**Files:**
- Create: `scripts/make_attack_subset.py`
- Test: `scripts/test_make_attack_subset.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/test_make_attack_subset.py`:

```python
import make_attack_subset as m


def test_pick_indices_deterministic_and_sorted():
    a = m.pick_indices(929, 300, seed=42)
    b = m.pick_indices(929, 300, seed=42)
    assert a == b                      # deterministic
    assert len(a) == 300
    assert a == sorted(a)              # sorted ascending
    assert len(set(a)) == 300          # unique
    assert all(0 <= i < 929 for i in a)


def test_pick_indices_different_seed_differs():
    assert m.pick_indices(929, 300, seed=42) != m.pick_indices(929, 300, seed=7)


def test_pick_indices_caps_at_total():
    assert m.pick_indices(10, 300, seed=42) == list(range(10))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd scripts && python3 -m pytest test_make_attack_subset.py -q`
Expected: FAIL / ImportError (module missing).

- [ ] **Step 3: Write the script**

Create `scripts/make_attack_subset.py`:

```python
#!/usr/bin/env python3
"""Build a seeded 300-of-929 attack subset for the cross-model policy-verbosity
ablation, shared by every judge model. Writes the subset JSONL (in sorted-index
order) and the chosen sorted indices (so the existing llama3.2 dumps can be sliced
positionally to the same attacks).

Usage: python3 scripts/make_attack_subset.py --n 300 --seed 42
"""
import argparse
import json
import os
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATTACKS = os.path.join(BASE, "corpora/eval/attacks/public_attacks.jsonl")
OUT_DIR = os.path.join(BASE, "corpora/policy_length/attacks_subset")


def pick_indices(total, n, seed):
    """Deterministic sorted sample of min(n, total) unique indices from range(total)."""
    if n >= total:
        return list(range(total))
    rng = random.Random(seed)
    return sorted(rng.sample(range(total), n))


def load_attacks():
    with open(ATTACKS) as f:
        return [json.loads(l)["prompt"] for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    attacks = load_attacks()
    idx = pick_indices(len(attacks), args.n, args.seed)
    os.makedirs(OUT_DIR, exist_ok=True)
    sub_path = os.path.join(OUT_DIR, "attacks_subset.jsonl")
    with open(sub_path, "w") as f:
        for i in idx:
            f.write(json.dumps({"prompt": attacks[i]}) + "\n")
    idx_path = os.path.join(OUT_DIR, "indices.json")
    with open(idx_path, "w") as f:
        json.dump({"total": len(attacks), "n": len(idx), "seed": args.seed,
                   "indices": idx}, f)
    print(f"wrote {len(idx)} attacks -> {sub_path}")
    print(f"wrote indices -> {idx_path}")
    print("SUBSET_DONE")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd scripts && python3 -m pytest test_make_attack_subset.py -q`
Expected: 3 passed.

- [ ] **Step 5: Build the subset**

Run: `python3 scripts/make_attack_subset.py --n 300 --seed 42`
Expected: `wrote 300 attacks -> …/attacks_subset.jsonl`, indices written, `SUBSET_DONE`.
Verify: `wc -l < corpora/policy_length/attacks_subset/attacks_subset.jsonl` → 300.

- [ ] **Step 6: Commit**

```bash
git add scripts/make_attack_subset.py scripts/test_make_attack_subset.py corpora/policy_length/attacks_subset
git commit -m "feat(xmodel): seeded 300-attack subset + indices for cross-model ablation"
```

---

## Task 3: Reuse llama3.2 by slicing its existing dumps

**Files:**
- Create: `scripts/slice_llama32_dumps.py`
- Test: `scripts/test_slice_llama32_dumps.py`

This reads the chosen indices from Task 2 and the existing full llama3.2 dumps
(`bench-out/policy_length/<domain>/dump/pl_<domain>_t*.jsonl`, 929 attacks + 50
benign rows in order) and writes sliced dumps to
`bench-out/policy_length_llama3.2/<domain>/dump/` containing exactly the 300
chosen attack rows (in sorted-index order) followed by all 50 benign rows.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_slice_llama32_dumps.py`:

```python
import slice_llama32_dumps as s


def test_slice_rows_picks_attacks_then_all_benign():
    # 5 attack rows (a0..a4) + 3 benign rows (b0..b2)
    rows = [{"is_attack": True, "tag": f"a{i}"} for i in range(5)] + \
           [{"is_attack": False, "tag": f"b{i}"} for i in range(3)]
    out = s.slice_rows(rows, n_attacks_total=5, indices=[1, 3])
    tags = [r["tag"] for r in out]
    assert tags == ["a1", "a3", "b0", "b1", "b2"]   # chosen attacks, then ALL benign


def test_slice_rows_validates_attack_count():
    rows = [{"is_attack": True}] * 4 + [{"is_attack": False}] * 2
    # caller claims 5 attacks but only 4 present -> error
    try:
        s.slice_rows(rows, n_attacks_total=5, indices=[0])
        assert False, "expected ValueError"
    except ValueError:
        pass
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd scripts && python3 -m pytest test_slice_llama32_dumps.py -q`
Expected: FAIL / ImportError.

- [ ] **Step 3: Write the script**

Create `scripts/slice_llama32_dumps.py`:

```python
#!/usr/bin/env python3
"""Slice the existing full llama3.2 policy-length dumps down to the shared
300-attack subset (+ all 50 benign), so llama3.2 is comparable to the run models
without re-running. Dumps are corpus-ordered: attacks[0..A-1] then benign[0..B-1]
(src/bench/mod.rs:141-165).

Usage: python3 scripts/slice_llama32_dumps.py
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(BASE, "bench-out/policy_length")
DST_ROOT = os.path.join(BASE, "bench-out/policy_length_llama3.2")
IDX_PATH = os.path.join(BASE, "corpora/policy_length/attacks_subset/indices.json")
DOMAINS = ["marketing", "healthcare", "code", "sql"]
RUNGS = ["t0", "t1", "t2", "t3"]


def slice_rows(rows, n_attacks_total, indices):
    """Return chosen attack rows (by index, in given order) + all benign rows.
    Validates that the dump's attack-row count matches n_attacks_total."""
    attacks = [r for r in rows if r["is_attack"]]
    benign = [r for r in rows if not r["is_attack"]]
    if len(attacks) != n_attacks_total:
        raise ValueError(f"expected {n_attacks_total} attack rows, got {len(attacks)}")
    return [attacks[i] for i in indices] + benign


def main():
    meta = json.load(open(IDX_PATH))
    indices, total = meta["indices"], meta["total"]
    for d in DOMAINS:
        out_dir = os.path.join(DST_ROOT, d, "dump")
        os.makedirs(out_dir, exist_ok=True)
        for r in RUNGS:
            src = os.path.join(SRC_ROOT, d, "dump", f"pl_{d}_{r}.jsonl")
            rows = [json.loads(l) for l in open(src) if l.strip()]
            sliced = slice_rows(rows, total, indices)
            dst = os.path.join(out_dir, f"pl_{d}_{r}.jsonl")
            with open(dst, "w") as f:
                for row in sliced:
                    f.write(json.dumps(row) + "\n")
            print(f"{d}/{r}: {len(rows)} -> {len(sliced)} rows")
    print("SLICE_DONE")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd scripts && python3 -m pytest test_slice_llama32_dumps.py -q`
Expected: 2 passed.

- [ ] **Step 5: Produce the sliced llama3.2 dumps**

Run: `python3 scripts/slice_llama32_dumps.py`
Expected: 16 lines `…: 979 -> 350 rows` and `SLICE_DONE`.
Verify: `wc -l < bench-out/policy_length_llama3.2/marketing/dump/pl_marketing_t0.jsonl` → 350 (300 attacks + 50 benign).

- [ ] **Step 6: Commit the scripts (not the gitignored dumps)**

```bash
git add scripts/slice_llama32_dumps.py scripts/test_slice_llama32_dumps.py
git commit -m "feat(xmodel): slice existing llama3.2 dumps to the 300-attack subset"
```

---

## Task 4: Per-model bench driver

**Files:**
- Create: `scripts/run_cross_model.sh`

- [ ] **Step 1: Write the driver**

Create `scripts/run_cross_model.sh`:

```bash
#!/usr/bin/env bash
# Cross-model policy-verbosity ablation. For each judge model (except llama3.2,
# which is reused via slice_llama32_dumps.py), run the 16 conditions on the shared
# 300-attack subset + 50 in-domain benign/domain, varying only QFIRE_JUDGE_MODEL.
# --no-cache is REQUIRED (the verdict cache key omits scope). Latency is captured
# in each run's bench.json (mean_detector_ms; judge-only => ~judge call time).
set -uo pipefail
cd "$(dirname "$0")/.."

QFIRE=./target/release/qfire
SEED=42
ATTACKS=corpora/policy_length/attacks_subset

cargo build --release

# tag -> output slug
run_model() {
  local tag="$1" slug="$2"
  echo "=================== model: $tag ($slug) ==================="
  for d in marketing healthcare code sql; do
    echo "--- $slug / $d ---"
    local OUT="bench-out/policy_length_${slug}/$d"
    mkdir -p "$OUT/dump"
    QFIRE_JUDGE_MODEL="$tag" "$QFIRE" bench \
      --chain pl_${d}_t0 --chain pl_${d}_t1 --chain pl_${d}_t2 --chain pl_${d}_t3 \
      --attacks "$ATTACKS" \
      --benign "corpora/policy_length/$d/benign" \
      --seed "$SEED" \
      --no-cache \
      --dump "$OUT/dump" \
      --out "$OUT"
  done
}

run_model "qwen3:4b"     "qwen3_4b"
run_model "llama3.1:8b"  "llama3.1_8b"
run_model "qwen3:8b"     "qwen3_8b"
run_model "gemma4:latest" "gemma4"
echo "XMODEL_RUN_DONE"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/run_cross_model.sh`

- [ ] **Step 3: Smoke-test ONE model on a tiny limit (do NOT run the full driver — that is Task 6)**

Run (qwen3:4b, 2 rungs, 3 prompts — proves wiring + per-model dump path + bench.json):
```bash
QFIRE_JUDGE_MODEL=qwen3:4b ./target/release/qfire bench \
  --chain pl_marketing_t0 --chain pl_marketing_t3 \
  --attacks corpora/policy_length/attacks_subset \
  --benign corpora/policy_length/marketing/benign \
  --seed 42 --no-cache --limit 3 \
  --dump bench-out/policy_length_qwen3_4b/_smoke/dump \
  --out bench-out/policy_length_qwen3_4b/_smoke
```
Expected: completes; `bench-out/policy_length_qwen3_4b/_smoke/bench.json` exists.

- [ ] **Step 4: Verify bench.json carries per-chain latency (mean_detector_ms)**

Run:
```bash
python3 -c "import json; d=json.load(open('bench-out/policy_length_qwen3_4b/_smoke/bench.json')); r=d['reports'][0]; print(r['chain'], 'mean_detector_ms=', round(r['overall']['mean_detector_ms'],1)); assert 'mean_detector_ms' in r['overall']"
```
Expected: prints a chain id and a `mean_detector_ms=` number; no assertion error.

- [ ] **Step 5: Clean up smoke output and commit the driver**

```bash
rm -rf bench-out/policy_length_qwen3_4b/_smoke
git add scripts/run_cross_model.sh
git commit -m "feat(xmodel): per-model bench driver (QFIRE_JUDGE_MODEL, --no-cache, --dump)"
```

---

## Task 5: Cross-model analyzer

**Files:**
- Create: `scripts/analyze_cross_model.py`
- Test: `scripts/test_analyze_cross_model.py`

Reads each model's dumps + `bench.json`, computes per (model, domain, rung)
accuracy (reusing `analyze_policy_length.metrics`) and per-call latency, pools
across domains per (model, rung), and writes
`bench-out/policy_length_xmodel/results.md`.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_analyze_cross_model.py`:

```python
import analyze_cross_model as x


def test_pooled_latency_is_mean_across_domains():
    # mean_detector_ms per domain for one (model,rung)
    assert x.pooled_latency([10.0, 20.0, 30.0, 40.0]) == 25.0


def test_pooled_latency_ignores_none():
    assert x.pooled_latency([10.0, None, 30.0]) == 20.0


def test_pooled_latency_all_none_is_none():
    assert x.pooled_latency([None, None]) is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd scripts && python3 -m pytest test_analyze_cross_model.py -q`
Expected: FAIL / ImportError.

- [ ] **Step 3: Write the analyzer**

Create `scripts/analyze_cross_model.py`:

```python
#!/usr/bin/env python3
"""Cross-model policy-verbosity analysis. For each model × rung (pooled across the
4 domains): accuracy (TPR/TNR/over-refusal/J) from the dumps, and per-call latency
(mean_detector_ms) from each run's bench.json. Writes
bench-out/policy_length_xmodel/results.md.

llama3.2 reads from bench-out/policy_length_llama3.2/ (sliced dumps) for accuracy
and from the ORIGINAL full bench-out/policy_length/<domain>/bench.json for latency
(per-call latency is corpus-size-independent).

Usage: python3 scripts/analyze_cross_model.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import analyze_policy_length as ap  # reuse metrics()

DOMAINS = ["marketing", "healthcare", "code", "sql"]
RUNGS = ["t0", "t1", "t2", "t3"]
OUT_DIR = os.path.join(BASE, "bench-out/policy_length_xmodel")

# (display name, tag, dump-root, latency-bench-root)
MODELS = [
    ("llama3.2", "llama3.2:latest", "bench-out/policy_length_llama3.2", "bench-out/policy_length"),
    ("qwen3:4b", "qwen3:4b", "bench-out/policy_length_qwen3_4b", "bench-out/policy_length_qwen3_4b"),
    ("llama3.1:8b", "llama3.1:8b", "bench-out/policy_length_llama3.1_8b", "bench-out/policy_length_llama3.1_8b"),
    ("qwen3:8b", "qwen3:8b", "bench-out/policy_length_qwen3_8b", "bench-out/policy_length_qwen3_8b"),
    ("gemma4", "gemma4:latest", "bench-out/policy_length_gemma4", "bench-out/policy_length_gemma4"),
]


def pooled_latency(vals):
    """Mean of per-domain mean_detector_ms, ignoring None."""
    xs = [v for v in vals if v is not None]
    return sum(xs) / len(xs) if xs else None


def load_dump_rows(dump_root, domain, rung):
    path = os.path.join(BASE, dump_root, domain, "dump", f"pl_{domain}_{rung}.jsonl")
    if not os.path.exists(path):
        return None
    return [json.loads(l) for l in open(path) if l.strip()]


def chain_latency(bench_root, domain, rung):
    """mean_detector_ms for chain pl_<domain>_<rung> from a domain's bench.json."""
    path = os.path.join(BASE, bench_root, domain, "bench.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    cid = f"pl_{domain}_{rung}"
    for r in d.get("reports", []):
        if r.get("chain") == cid:
            return r["overall"].get("mean_detector_ms")
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    lines = ["# Cross-Model Policy-Verbosity Ablation — Results", "",
             "300-attack seeded subset + 50 in-domain benign/domain, judge-only, "
             "--no-cache, seed 42. J = TPR + TNR - 1. Latency = mean per-call "
             "detector ms (judge-only), averaged across domains.", "",
             "| model | rung | TPR | TNR | over-refusal | J | latency (ms/call) |",
             "|---|---|---|---|---|---|---|"]
    # collect for the figure-feed print at the end
    summary = {}
    for name, tag, dump_root, lat_root in MODELS:
        summary[name] = {}
        for rung in RUNGS:
            pooled_rows, lats = [], []
            for d in DOMAINS:
                rows = load_dump_rows(dump_root, d, rung)
                if rows:
                    pooled_rows.extend(rows)
                lats.append(chain_latency(lat_root, d, rung))
            if not pooled_rows:
                lines.append(f"| {name} | {rung} | — | — | — | — | (no dumps) |")
                continue
            m = ap.metrics(pooled_rows)
            lat = pooled_latency(lats)
            lat_s = f"{lat:.0f}" if lat is not None else "—"
            summary[name][rung] = {"j": m["youden_j"], "tpr": m["tpr"],
                                   "tnr": m["tnr"], "lat": lat}
            lines.append(f"| {name} | {rung} | {m['tpr']:.3f} | {m['tnr']:.3f} | "
                         f"{m['over_refusal']:.3f} | {m['youden_j']:+.3f} | {lat_s} |")
    out = os.path.join(OUT_DIR, "results.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", out)
    print("ANALYZE_XMODEL_DONE")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd scripts && python3 -m pytest test_analyze_cross_model.py -q`
Expected: 3 passed (pooled_latency: mean, ignores-None, all-None).

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze_cross_model.py scripts/test_analyze_cross_model.py
git commit -m "feat(xmodel): cross-model analyzer (accuracy from dumps + latency from bench.json)"
```

---

## Task 6: Full cross-model run + analysis

**Files:** run outputs under `bench-out/policy_length_<model>/`, `bench-out/policy_length_xmodel/results.md`

- [ ] **Step 1: Confirm prerequisites**

Run:
```bash
ls corpora/policy_length/attacks_subset/attacks_subset.jsonl
ls bench-out/policy_length_llama3.2/marketing/dump/pl_marketing_t0.jsonl
ollama list | grep -E 'qwen3:4b|qwen3:8b|llama3.1:8b|gemma4'
```
Expected: subset present, llama3.2 slice present, all run-models listed.

- [ ] **Step 2: Run the 4 models (background; hours — gemma4 is the long pole)**

Run: `./scripts/run_cross_model.sh 2>&1 | tee bench-out/policy_length_xmodel_run.log`
Expected: per-model/per-domain headers, ending `XMODEL_RUN_DONE`.
(If executing via subagent, run this in the foreground of a long-lived background task; do not detach with `nohup &`.)

- [ ] **Step 3: Verify dump completeness (each rung = 350 rows: 300 attacks + 50 benign)**

Run:
```bash
for slug in qwen3_4b llama3.1_8b qwen3_8b gemma4; do
  for d in marketing healthcare code sql; do
    for t in t0 t1 t2 t3; do
      f="bench-out/policy_length_$slug/$d/dump/pl_${d}_${t}.jsonl"
      n=$([ -f "$f" ] && wc -l < "$f" || echo MISSING)
      [ "$n" = "350" ] || echo "CHECK $slug/$d/$t: $n"
    done
  done
done; echo "completeness check done"
```
Expected: only `completeness check done` (every rung is 350; any mismatch prints a CHECK line).

- [ ] **Step 4: Run the analyzer**

Run: `python3 scripts/analyze_cross_model.py`
Expected: `wrote …/results.md` and `ANALYZE_XMODEL_DONE`.

- [ ] **Step 5: Sanity-check results**

Run: `cat bench-out/policy_length_xmodel/results.md`
Expected: 20 rows (5 models × 4 rungs), each with TPR/TNR/J and a latency number. Sanity: latency rises with rung within a model (T3 prompt is longer); gemma4 latency ≫ qwen3:4b; if a model shows TPR collapsing at some rung, that is the abstain/format-failure mode (note it).

- [ ] **Step 6: Commit the results doc (bench-out is gitignored; force-add only results.md)**

```bash
git add -f bench-out/policy_length_xmodel/results.md
git commit -m "results(xmodel): cross-model policy-verbosity metrics + latency"
```

---

## Task 7: Cross-model figure

**Files:**
- Create: `scripts/plot_cross_model.py`
- Output: `paper/figs/policy_length_xmodel.png`

- [ ] **Step 1: Write the plotting script**

Create `scripts/plot_cross_model.py`:

```python
#!/usr/bin/env python3
"""Render the cross-model policy-verbosity figure: (a) Youden's J vs rung per
model, (b) per-call latency vs rung per model (log y), (c) J-vs-latency Pareto.
Reuses analyze_cross_model's loaders. Writes paper/figs/policy_length_xmodel.png.

Usage: python3 scripts/plot_cross_model.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import analyze_cross_model as x
import analyze_policy_length as ap

RUNGS = ["t0", "t1", "t2", "t3"]
RUNG_LABELS = ["T0", "T1", "T2", "T3"]
OUT = os.path.join(BASE, "paper/figs/policy_length_xmodel.png")
COLORS = ["#000000", "#4C72B0", "#55A868", "#8172B3", "#C44E52"]


def collect():
    """Return {model_name: {rung: {j,tpr,tnr,lat}}} pooled across domains."""
    data = {}
    for name, tag, dump_root, lat_root in x.MODELS:
        data[name] = {}
        for rung in RUNGS:
            rows, lats = [], []
            for d in x.DOMAINS:
                r = x.load_dump_rows(dump_root, d, rung)
                if r:
                    rows.extend(r)
                lats.append(x.chain_latency(lat_root, d, rung))
            if not rows:
                continue
            m = ap.metrics(rows)
            data[name][rung] = {"j": m["youden_j"], "tpr": m["tpr"],
                                "tnr": m["tnr"], "lat": x.pooled_latency(lats)}
    return data


def main():
    data = collect()
    xs = list(range(4))
    fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(15, 4.4))

    for ci, (name, series) in enumerate(data.items()):
        c = COLORS[ci % len(COLORS)]
        js = [series.get(r, {}).get("j") for r in RUNGS]
        ls = [series.get(r, {}).get("lat") for r in RUNGS]
        axA.plot(xs, js, marker="o", lw=2, color=c, label=name)
        if any(v is not None for v in ls):
            axB.plot(xs, ls, marker="o", lw=2, color=c, label=name)
        for ri, r in enumerate(RUNGS):
            s = series.get(r)
            if s and s["lat"] is not None:
                axC.scatter(s["lat"], s["j"], color=c, s=40)
                axC.annotate(RUNG_LABELS[ri], (s["lat"], s["j"]),
                             textcoords="offset points", xytext=(4, 3), fontsize=7)

    axA.set_xticks(xs); axA.set_xticklabels(RUNG_LABELS)
    axA.set_ylabel("Youden's J"); axA.set_title("(a) Accuracy vs policy length")
    axA.grid(True, alpha=0.3); axA.legend(fontsize=8)

    axB.set_xticks(xs); axB.set_xticklabels(RUNG_LABELS)
    axB.set_yscale("log")
    axB.set_ylabel("mean ms / call (log)"); axB.set_title("(b) Latency vs policy length")
    axB.grid(True, alpha=0.3, which="both"); axB.legend(fontsize=8)

    axC.set_xlabel("mean ms / call"); axC.set_ylabel("Youden's J")
    axC.set_title("(c) Quality-vs-latency (all model×rung)")
    axC.grid(True, alpha=0.3)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the figure**

Run: `python3 scripts/plot_cross_model.py`
Expected: `wrote …/paper/figs/policy_length_xmodel.png`; file exists and is non-trivial (`ls -la paper/figs/policy_length_xmodel.png`).

- [ ] **Step 3: Eyeball the figure**

Open/read `paper/figs/policy_length_xmodel.png`. Sanity: panel (a) has 5 model lines over T0–T3; panel (b) shows latency rising left→right and gemma4 highest; panel (c) is a scatter of 20 points with rung labels.

- [ ] **Step 4: Commit the figure + script**

```bash
git add scripts/plot_cross_model.py paper/figs/policy_length_xmodel.png
git commit -m "feat(xmodel): 3-panel cross-model figure (J vs rung, latency vs rung, Pareto)"
```

---

## Task 8: Findings doc

**Files:**
- Create: `docs/superpowers/specs/2026-05-31-cross-model-policy-verbosity-results.md`

- [ ] **Step 1: Write the findings doc from the actual numbers**

Read `bench-out/policy_length_xmodel/results.md` and create
`docs/superpowers/specs/2026-05-31-cross-model-policy-verbosity-results.md` with:
the setup (5 models, 300-attack subset, judge-only, --no-cache, seed 42), the
per-(model, rung) table copied from results.md, an embedded reference to
`paper/figs/policy_length_xmodel.png`, and a **Findings** section answering the two
research questions with the observed numbers:
(1) does the T2 sweet-spot / non-monotone curve replicate across families/sizes
(report per model whether J peaks at T2 and whether T3 regresses);
(2) the latency×length tradeoff (does per-call latency rise with rung, by how much
on the slow vs fast models; which (model, rung) is Pareto-efficient).
Call out any model whose TPR collapses (abstain/format-failure) and a caveats
section (single machine warm-latency; model-generated benign; healthcare benign
meta-commentary as in the prior results doc). Do NOT invent numbers — use the
table.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-05-31-cross-model-policy-verbosity-results.md
git commit -m "results(xmodel): cross-model findings (replication + latency tradeoff)"
```

---

## Self-review notes (spec coverage)

- 5-model grid + qwen3:8b pull → Task 1. ✓
- 300-attack seeded subset, shared → Task 2. ✓
- llama3.2 reuse by positional slice (corpus-ordered dumps) → Task 3. ✓
- Per-model driver, QFIRE_JUDGE_MODEL, --no-cache, --dump, per-model dirs → Task 4/6. ✓
- Accuracy from dumps (reuse metrics()), latency from bench.json mean_detector_ms, pooled = mean across domains → Task 5. ✓
- 3-panel figure (J vs rung, latency vs rung, Pareto) → Task 7. ✓
- Findings doc; paper integration out of scope → Task 8. ✓
- Abstain not separately instrumented; surfaces as depressed TPR → noted in Task 5/6/8. ✓ (matches corrected design)
- TDD with failing-first tests on pure helpers (pick_indices, slice_rows, pooled_latency/model_slug) → Tasks 2/3/5. ✓
- Type consistency: `slice_rows(rows, n_attacks_total, indices)`, `pick_indices(total, n, seed)`, `pooled_latency(vals)`, `chain_latency(bench_root, domain, rung)`, `load_dump_rows(dump_root, domain, rung)` used consistently across analyzer + plot (plot reuses the analyzer's `MODELS`, `DOMAINS`, loaders). ✓
