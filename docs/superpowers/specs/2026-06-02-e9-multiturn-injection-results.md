# E9 — Multi-turn / conversational injection — Results & Findings

**Date:** 2026-06-02
**Design:** [2026-06-02-e9-multiturn-injection-design.md](2026-06-02-e9-multiturn-injection-design.md)
**Plan:** [../plans/2026-06-02-e9-multiturn-injection.md](../plans/2026-06-02-e9-multiturn-injection.md)

**Setup.** 150 multi-turn conversations (`corpora/multiturn/`, seed 42), built
**deterministically** (templated benign glue around a *verbatim* malicious core — no LLM,
so intent is never diluted and the corpus is fully reproducible; this is a deliberate
improvement over the spec's LLM-glue): split-payload, context-priming, crescendo (40 each)
+ 30 benign clinical-adjacent. Each conversation is scored through QFIRE two ways via
`qfire bench`: **full-transcript** (`prompt_text` — QFIRE's default, the role-tagged
concatenation of all turns) vs **latest-turn-only** (`latest_user` — the naive per-message
view). Chains at the **calibrated** operating point: `bench_combined` (healthcare-domain
cores) / `default` (injection-domain cores); scope judge = **gemma2:9B**.

## Results (recall = % multi-turn attacks blocked)

| pattern | full-transcript (QFIRE default) | latest-turn-only | Δ |
|---|---|---|---|
| split-payload | **0.90** | 0.43 | **+0.48** |
| crescendo | **1.00** | 0.70 | +0.30 |
| context-priming | **0.78** | 0.65 | +0.13 |
| **benign (FPR)** | **0.00** | 0.00 | — |

## Findings

1. **Full-context evaluation is the win — QFIRE is already history-aware.** Across all
   three attack patterns the full transcript blocks far more than a per-message filter
   (0.78–1.00 vs 0.43–0.70), at **0.00 benign over-block**. The mechanism is structural:
   `engine.rs` scores `prompt_text` (the whole role-tagged conversation), so cross-turn
   buildup is visible to the scope judge and detectors by default — no stateful redesign
   needed.
2. **Split-payload is the clearest case.** Fragmenting the instruction across turns drops
   a per-message filter to 0.43 (it sees only the final fragment), while the full
   transcript reassembles it → 0.90. This is exactly the multi-turn evasion that defeats
   stateless single-layer filters in the literature.
3. **Honest residual: context-priming.** Even full-transcript recall is 0.78 here —
   attacks dressed as a previously-agreed, in-scope workflow are the hardest, because the
   priming makes the payload look legitimate to the scope judge. The fix is tighter scope
   rules (a definitional, not architectural, gap), not a stateful overhaul.

## Reproduction
- Corpus: `scripts/gen_multiturn.py --n 150 --seed 42` (deterministic; no Ollama).
- Scoring: `scripts/run_multiturn.py` (env `QFIRE_BIN`, `QFIRE_DEBERTA_DIR`,
  `QFIRE_JUDGE_MODEL=gemma2:9b`) → `qfire bench --no-cache` per (pattern × domain × mode),
  block_rate → `bench-out/multiturn/{groups,summary}.json`; `scripts/plot_multiturn.py`
  → `paper/figs/multiturn.png`.
- **Chain choice matters:** the strict `hipaa_phi` conjunction over-blocks benign ~1.00 at
  scale (paper §3.7 calibration cross-check); E9 uses the calibrated `bench_combined`
  (0.08-FPR operating point) so the benign-FPR comparison is meaningful — caught when a
  first pass with `hipaa_phi` returned benign FPR = 1.00.
- Judge = gemma2:9B (the Pareto-optimal judge from the cross-model ablation), an upgrade
  from the legacy llama3.2 default.

## Bottom line
The dominant production failure mode — multi-turn injection that no single message reveals
— is largely answered by QFIRE's existing full-transcript evaluation: 0.78–1.00 recall vs
0.43–0.70 for a per-message filter, at zero benign over-block. The remaining gap is
context-priming (in-scope-looking workflow), which points to scope-rule tightening rather
than a stateful redesign.
