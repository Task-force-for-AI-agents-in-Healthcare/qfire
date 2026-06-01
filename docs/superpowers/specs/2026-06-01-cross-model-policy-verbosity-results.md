# Cross-Model Policy-Verbosity Ablation — Results & Findings

**Date:** 2026-06-01
**Design:** [2026-05-31-cross-model-policy-verbosity-design.md](2026-05-31-cross-model-policy-verbosity-design.md)
**Plan:** [../plans/2026-05-31-cross-model-policy-verbosity.md](../plans/2026-05-31-cross-model-policy-verbosity.md)
**Extends:** the single-model ablation ([2026-05-31-policy-verbosity-ablation-results.md](2026-05-31-policy-verbosity-ablation-results.md)).

**Setup.** The same 16 conditions (4 domains × 4 verbosity rungs T0→T3, judge-only
chains, `--no-cache`, seed 42, 50 in-domain benign/domain) run across **6 judge
models** on a **seeded 150-attack subset** (`attacks_subset`, shared by all models;
llama3.2 reused by positionally slicing its full-run dumps to the same subset).
J = TPR + TNR − 1. Latency = `mean_detector_ms` per chain (judge-only ⇒ ≈ judge
call time), pooled = mean across the 4 domains. Raw per-model dumps regenerate via
`scripts/run_cross_model.sh`; analysis via `scripts/analyze_cross_model.py`
(`bench-out/policy_length_xmodel/results.md`); figure via
`scripts/plot_cross_model.py` → `paper/figs/policy_length_xmodel.png`.

> **Grid note.** The originally-proposed `qwen3:4b`/`qwen3:8b` were dropped: they
> are reasoning models that emit a long "Thinking…" monologue and never produce the
> required one-line `IN/OUT SCOPE` verdict (~10 s/call, abstain→allow), unusable as
> fast judges — replaced by `phi3.5:3.8b` and `gemma2:9b`. `deepseek-r1:latest` was
> added (at request) as a *working* reasoning judge. DeepSeek-V3.2 is not runnable
> locally (~600B+).

## Pooled metrics (J vs rung, per model)

| model | ~size | family | T0 | T1 | T2 | T3 | latency (ms/call) |
|---|---|---|---|---|---|---|---|
| llama3.2 | ~3B | Llama | +0.807 | +0.632 | **+0.857** | +0.767 | ~610–660 |
| phi3.5:3.8b | ~3.8B | Phi | +0.340 | +0.237 | +0.637 | **+0.712** | ~1100–1680 |
| llama3.1:8b | ~8B | Llama | **+0.947** | +0.838 | +0.925 | +0.870 | ~800–880 |
| gemma2:9b | ~9B | Gemma | **+0.955** | +0.923 | +0.933 | +0.928 | ~850–920 |
| gemma4 | ~12B | Gemma | **+0.908** | +0.863 | +0.893 | +0.883 | ~3200–5200 |
| deepseek-r1 | ~7B (reasoning) | DeepSeek | +0.748 | +0.725 | **+0.787** | +0.697 | ~4200–5000 |

(Per-condition TPR/TNR/over-refusal are in `bench-out/policy_length_xmodel/results.md`.)

## Headline finding

**The "T2 sweet-spot" is an artifact of weak judges; judge capability — not policy
verbosity — sets the firewall's ceiling.**

- **The non-monotone length curve appears only for the weak judges.** Llama 3.2
  (~3B) peaks at T2; Phi-3.5 (~3.8B) rises *monotonically* (J 0.34→0.24→0.64→0.71),
  because terse policies make it over-refuse badly (T0/T1 benign pass rate
  0.45/0.27) and only the full policy pulls it up — to a still-mediocre 0.71.
- **Capable mid-size judges are nearly length-invariant.** Gemma 2 9B holds
  J ≈ 0.92–0.96 at *every* rung (best at the 3-word T0); Llama 3.1 8B
  0.95/0.84/0.93/0.87. A better judge does not need a verbose policy; a weak one
  cannot be rescued by one.
- **Bigger/slower is not better.** Gemma 4 (~12B, ~4.2 s/call) and DeepSeek-R1
  (reasoning, ~4.8 s/call) are **Pareto-dominated** — lower J at 4–5× the latency —
  by Gemma 2 9B / Llama 3.1 8B at ~0.85 s. The reasoning judge even blocks *fewer*
  attacks (TPR ~0.83–0.87 vs ≥0.97 for the others).
- **Verbosity is a latency tax once the judge is competent.** Within every model,
  per-call latency rises with rung (e.g. Gemma 4 T0→T2: 3.2→5.2 s/call) — for no
  accuracy gain on the capable judges.

**Deployment recipe:** a competent mid-size instruct judge (Gemma 2 9B or
Llama 3.1 8B) with a short, explicit (T0–T2) policy — not a larger or reasoning
judge, and not a maximal firewall prompt.

## Relation to the single-model study

The single-model result (Llama 3.2: T1 trap, T2 sweet-spot, T3 regression) is a
faithful description **of that weak 3B judge** — and reproduces here on the
150-attack subset (T0 0.807 / T1 0.632 / T2 0.857 / T3 0.767). The cross-model run
shows it does **not** generalize: it is a property of weak judges, and the open
caveat from that study ("a larger model may follow long policies more faithfully")
resolves to *yes* — capable models follow even the terse policy.

## Caveats

- **Single machine, warm latencies.** Latency is indicative of relative cost on
  one Mac/Ollama setup (one model loaded at a time), not an absolute benchmark of
  each model's intrinsic speed; figures can shift with hardware/quantization.
- **Model-generated benign sets** (50/domain) add noise to *absolute* per-domain
  TNR (incl. the known healthcare meta-commentary contamination); the cross-model
  *shape* comparison rests on the same prompts for every model, so the relative
  ordering is robust.
- **150-attack subset** (down from 929/300 for tractability across 6 models). TPR
  is already saturated for the non-reasoning judges, so this estimates block-rate
  tightly; the differentiator (over-refusal) is measured on the full 50 benign.
- DeepSeek-R1's lower TPR is a genuine accuracy result on this subset, not an
  abstain artifact (its verdicts parse cleanly: attacks→~0.85, benign→~0.15).

## Paper

Folded into the manuscript: `paper/main.tex` §5.3.7 ("Across judge models:
capability substitutes for verbosity") + Figure 10 (`figs/policy_length_xmodel.png`),
mirrored in `paper/PAPER.md` §3.8.
