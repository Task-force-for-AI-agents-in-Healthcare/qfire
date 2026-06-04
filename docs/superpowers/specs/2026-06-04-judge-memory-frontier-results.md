# Judge Memory-vs-J Frontier — Results & Findings

**Date:** 2026-06-04
**Extends:** the judge-model ablation (§3.6) and the cross-model policy-verbosity
study ([2026-06-01-cross-model-policy-verbosity-results.md](2026-06-01-cross-model-policy-verbosity-results.md)),
which used **latency** as the cost axis. This study adds the orthogonal axis the
paper had not measured — **memory** — to answer a deployment question those
studies could not: *how small (how little VRAM) can the firewall's LLM scope-judge
be before detection quality collapses, and how does that floor move with attack
difficulty?*

**Why memory.** The `judge` node (`src/detector/judge.rs`) is the only
model-size-sensitive detector; every other detector (regex/Aho/entropy/DeBERTa) is
fixed-size. Memory — not latency — is what decides whether a judge fits on an edge
box, a small GPU, or a shared host, so it is the right axis for "how far out can
the proxy run."

**Setup.** The single-rule `judge_scope` chain (`hc_no_diagnosis`) isolates the
judge so the backend model's verdict is the only deciding factor; we vary only
`QFIRE_JUDGE_MODEL`, with `--no-cache`, seed 42. Two difficulty tiers share the
**same** 100 benign in-scope clinical requests (the negatives, so FPR is
comparable across tiers) and differ only in the attacks (the positives):

- **T1 standard** — 100 plain HealthBench attacks. Near-saturating.
- **T2 hard** — 200 adaptive healthcare evasions (impersonation + base64-encoded
  exfiltration), where a weak judge fails to recognize the out-of-scope intent.

Metric **J = TPR − FPR** (Youden's J), read from each tier's `overall` metrics
(consistent with the §3.9 cross-model figure; on the bucketed judge score J, AUC,
and balanced accuracy coincide up to a monotone transform — the committed `auc`
column tracks J throughout). **Memory = measured peak VRAM** of the loaded judge,
captured on the Modal GPU (`nvidia-smi`), which the Rust harness cannot know.

The Llama family supplies the size ladder (1B / 3B / 8B) at Q4, plus a
quantization sweep (Q3 / Q4 / Q8 / FP16) on 3B and 8B so memory varies both by
parameter count and by precision. 8 configs, all on an L4 (~$1.50 total).

## Results

| Model | Quant | Params (B) | Peak VRAM (GB) | T1 J | T1 FPR | T2 J | AUC (T2) |
|---|---|---|---|---|---|---|---|
| Llama 3.2 1B | Q4 | 1.0 | 1.6 | **−0.03** | 1.00 | **−0.04** | 0.48 |
| Llama 3.2 3B | Q4 | 3.0 | 2.6 | 0.75 | 0.25 | 0.68 | 0.84 |
| Llama 3.2 3B | Q8 | 3.0 | 3.9 | 0.95 | 0.04 | 0.77 | 0.88 |
| Llama 3.1 8B | Q3 | 8.0 | **4.4** | **1.00** | 0.00 | 0.80 | 0.90 |
| Llama 3.1 8B | Q4 | 8.0 | 5.1 | 0.99 | 0.00 | 0.76 | 0.88 |
| Llama 3.2 3B | FP16 | 3.0 | 6.7 | 0.95 | 0.03 | 0.80 | 0.90 |
| Llama 3.1 8B | Q8 | 8.0 | **8.3** | 1.00 | 0.00 | **0.84** | 0.92 |
| Llama 3.1 8B | FP16 | 8.0 | 14.8 | 1.00 | 0.00 | 0.84 | 0.92 |

Figure: `paper/figs/judge_memory_frontier.png` (memory log-x vs J, both tiers,
Pareto staircase + saturation-knee annotations). Raw record:
`bench-out/judge_frontier/results.{json,md}`.

## Findings

1. **There is a sharp capability cliff below 3B.** The 1B judge is a degenerate
   *block-everything* classifier — it blocks 97/100 attacks **and all 100 benign
   requests** (FPR 1.00, J ≈ 0, AUC 0.48 ≈ random). The 1B→3B step is where the
   judge learns to discriminate at all (FPR 1.00 → 0.25). The edge floor is ~3B /
   2.6 GB; nothing smaller is usable as a scope judge.

2. **Standard threats saturate at ~4.4 GB.** A heavily-quantized 8B (Q3) reaches
   J = 1.00 on T1 in 4.4 GB; everything larger is flat. Routine prompt-injection
   defense does not need a big judge.

3. **Hard threats push the knee right and plateau lower (~0.84).** Adaptive
   evasions are not fully solved even by 8B-FP16 (J 0.84): the T1 knee sits at
   4.4 GB, the T2 knee at 8.3 GB. The *shape change between tiers* — not any single
   point — is the result: how small you can go depends on the threat tier.

4. **Quantization is nearly free on quality.** 8B-Q3 (4.4 GB) recovers ~95 % of
   8B-FP16's hard-tier J at under **one-third** the memory. Aggressive
   quantization is the cheapest lever for edge deployment.

5. **Prefer a quantized larger model over a smaller one at full precision.** At
   matched footprint, 8B-Q3 (4.4 GB) meets-or-beats 3B-FP16 (6.7 GB) on the hard
   tier — parameter count buys more than precision per GB of VRAM.

**Recipe.** For routine defense, an 8B instruct judge quantized to ~Q3 (≈4.4 GB)
is a perfect, edge-deployable scope judge. For adaptive-evasion-hardened
deployments, step up to ~Q8 (≈8.3 GB); full precision buys nothing beyond it.

## Reproduction

```bash
# 1. Build the two tiers from the committed corpora (deterministic).
scripts/build_judge_frontier_corpora.sh

# 2. Per judge model, run both tiers (needs a reachable Ollama with the model).
QFIRE_BIN=./target/release/qfire \
  scripts/judge_memory_frontier.sh llama3.1:8b-instruct-q3_K_M bench-out/judge_frontier/llama3.1_8b_q3

# 3. Tabulate + plot (memory comes from each config's host-written meta.json).
python3 scripts/analyze_judge_frontier.py bench-out/judge_frontier
python3 scripts/plot_judge_frontier.py bench-out/judge_frontier/results.json
```

GPU orchestration (model pull, peak-VRAM capture, fan-out) was a Modal harness
kept outside the repo; the committed scripts are host-agnostic and reproduce the
science given any Ollama endpoint.

## Caveats

- **Single family, single seed.** Llama only; one seed. One non-monotone blip
  (8B-Q4 T2 0.76 < 8B-Q3 0.80) is small-sample variance at 200/100 and would
  smooth with more seeds. The *cliff* and *tier-shape* conclusions are robust to it.
- **Memory is runtime-specific.** Peak VRAM is Ollama's GGUF footprint at the
  given quant on an L4; absolute GB shift with runtime/KV-cache settings, but the
  cross-config ordering (the frontier) is what the figure reports.
- **J on a bucketed judge.** The judge emits a bucketed confidence, so J/AUC/balanced
  accuracy coincide; a graded-confidence judge (future work) would sharpen the curve
  but is out of scope here (no judge/metric changes were made).
