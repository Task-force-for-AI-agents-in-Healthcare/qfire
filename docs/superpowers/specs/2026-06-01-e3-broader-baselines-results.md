# E3 — Broader Baselines (Sentinel + bare LLM-judge) — Results & Findings

**Date:** 2026-06-01
**Design:** [2026-06-01-e3-broader-baselines-design.md](2026-06-01-e3-broader-baselines-design.md)
**Plan:** [../plans/2026-06-01-e3-broader-baselines.md](../plans/2026-06-01-e3-broader-baselines.md)

**Setup.** Two baselines added to the existing head-to-head and QFIRE-HealthBench
comparisons, on the identical labeled corpora, seed 42:
1. **qualifire `prompt-injection-sentinel`** — a gated HF **ModernBERT** injection
   classifier (labels `{0:benign, 1:jailbreak}`; injection = last logit, reusing
   `baselines.py`'s `prob[-1]` path). A second *purpose-built* injection detector, to
   answer "you only compared to two classifiers."
2. **Bare `llama3.1:8B` LLM-judge** — a single block/allow call with a generic prompt
   and **no** QFIRE rule graph (Ollama), to isolate the scope/PHI scaffold's
   contribution from raw LLM judgment.

**Why not Llama Guard 3 (originally proposed).** Llama Guard is a *content-safety*
classifier over the MLCommons hazard taxonomy (violence, hate, self-harm, …), not a
prompt-injection or scope/PHI detector. Scoring its "unsafe" as an injection decision
would be a category mismatch that strawmans it, so we replaced it with Sentinel, an
on-task injection classifier. (This was caught mid-build and is noted in the paper's
Baselines paragraph.)

## Public injection (929 atk / 1,039 ben)

| System | Prec. | Rec. | F1 | FPR | p95 |
|---|---|---|---|---|---|
| protectai DeBERTa-v3 (PyTorch) | 0.984 | 0.721 | 0.832 | 0.011 | 195 ms |
| Meta PromptGuard-2-86M | 0.997 | 0.755 | 0.859 | 0.002 | 47 ms |
| **qualifire Sentinel (ModernBERT)** | 0.987 | **0.973** | **0.980** | 0.012 | 431 ms |
| LLM-judge only (llama3.1:8B, no scaffold) | 0.902 | 0.573 | 0.700 | 0.056 | 2012 ms |
| QFIRE hybrid | 0.967 | 0.767 | 0.856 | 0.023 | short-circuited |

**Sentinel is the strongest system on clean public injection (F1 0.980)** — above
PromptGuard-2/QFIRE (~0.86). Expected: a dedicated detector on in-distribution overt
injection is exactly its wheelhouse. The bare judge is the weakest learned baseline
here (F1 0.70) and by far the slowest (p95 2 s).

## QFIRE-HealthBench (1,000 atk / 1,000 ben)

| System | Prec. | Rec. | F1 | FPR |
|---|---|---|---|---|
| protectai DeBERTa-v3 | 1.000 | 0.574 | 0.729 | 0.000 |
| Meta PromptGuard-2-86M | 0.998 | 0.402 | 0.573 | 0.001 |
| **qualifire Sentinel (ModernBERT)** | 1.000 | **0.638** | 0.779 | 0.000 |
| llama3.1:8B judge (bare, no scaffold) | 0.989 | **0.824** | 0.899 | 0.009 |
| **QFIRE `bench_combined` (inj+PHI+scope)** | 0.911 | **0.829** | **0.868** | 0.081 |

**Two findings, one reinforcing the thesis and one honest-negative:**

1. **Even a strong injection classifier misses the healthcare gap.** Sentinel — best
   on public injection — recovers only **0.638** recall here, better than PromptGuard-2
   (0.40) and DeBERTa (0.57) but still **below QFIRE (0.83)**, leaving >⅓ of clinical
   threats through. The gap is structural: most healthcare threats (PHI exfil,
   cross-patient, re-identification, bulk export, out-of-scope clinical advice) carry
   no jailbreak token, so no injection classifier — however good — models them.

2. **Honest-negative: a bare LLM-judge nearly matches QFIRE on static HealthBench.**
   The scaffold-free `llama3.1:8B` judge reaches recall **0.824** / F1 **0.899**,
   essentially tying QFIRE's combined chain (0.83 / 0.87) and slightly exceeding it on
   F1. On in-distribution clinical text, a capable instruct model asked the right
   block/allow question recovers most threats on its own — the scope/PHI *detection*
   delta over a good bare judge is ≈0 on this corpus. We report this plainly.

   **Where the scaffold still earns its place** (supported by measured data):
   - **Consistency across threat types** — the same bare judge **collapses on generic
     injection** (F1 0.70 vs Sentinel 0.98, QFIRE 0.86); it is not a dependable single
     detector, whereas QFIRE is competitive on both corpora.
   - **Latency** — bare-judge p95 is 0.6–2 s/prompt vs QFIRE's bounded,
     cheap-before-expensive short-circuiting path.
   - **Auditability / determinism** — QFIRE gives a per-rule audit trail and a
     deterministic PHI/identifier guarantee; one opaque LLM call gives neither.
   - **Adaptive robustness (measured)** — QFIRE's positive-security scope chain is
     **uniformly 100%** under the E1 adaptive attacks; the bare judge, run through the
     same panel, **collapses to 34–59%** (impersonation 34.2%, paraphrase 44.9%,
     encoded-healthcare 40.4%, encoded-injection 59.1% — just 34–45% on the three
     healthcare-relevant families). Notably
     the *scope-aware* judge (90.8–98.5%) vastly outperforms the *generic* bare judge —
     so the scaffold's scope prompt, not merely "having an LLM judge," is what holds up.
     A single generic block/allow judgment is itself evadable once the adversary adapts.

## Sentinel + bare-judge folded into the E1 adaptive panel (recall = % blocked)

| adaptive family | DeBERTa | PromptGuard-2 | **Sentinel** | bare-judge | scope-judge | QFIRE scope+PHI |
|---|---|---|---|---|---|---|
| scope-impersonation (healthcare) | 15.0% | 12.5% | **45.0%** | 34.2% | 90.8% | 100% |
| paraphrase-to-evade | 0.0% | 20.2% | **49.4%** | 44.9% | 98.9% | 100% |
| encoded (healthcare) | 54.4% | 44.2% | **71.3%** | 40.4% | 96.5% | 100% |
| encoded (injection) | 49.0% | 38.5% | **53.3%** | 59.1% | 98.5% | 100% |

The **bare judge** that tied QFIRE on static HealthBench (recall 0.82) blocks only
**34–59%** of adaptive attacks (just 34–45% on the three healthcare-relevant families;
59% on encoded-injection, where residual injection signal survives encoding) — far below
the *scope-aware* judge (90.8–98.5%) and QFIRE (100%). The scaffold's value under attack
is the scope prompt + composition, not the LLM.

**Sentinel is the most robust of the three classifiers on every adaptive family** —
consistent with it being the best classifier — **yet still leaks 29–55%** of these
attacks, while QFIRE blocks 100%. This sharpens the E1 story: the adaptive gap is
structural (out-of-scope is out-of-scope however phrased/encoded), not a deficiency of
weak classifiers. The scope−best-classifier gap is now +28.7% to +55.0% (vs the best
of DeBERTa/PromptGuard/Sentinel).

## Reproduction
- Code: `scripts/baselines.py` (Sentinel in `MODELS` + `HF_TOKEN` passthrough; bare
  judge via `run_ollama_model` judge mode), `scripts/run_e3_baselines.sh`.
- Sentinel is **gated**: the runner's HF account must accept the model terms at
  <https://huggingface.co/qualifire/prompt-injection-sentinel> and an `HF_TOKEN` must
  be exported (never committed). Sentinel is ModernBERT → needs `transformers` ≥4.48.
- Main corpora: `./scripts/run_e3_baselines.sh` → `bench-out/baselines_e3_*.json`.
- Adaptive panel: `baselines.py --models sentinel` per set →
  `bench-out/adaptive/<set>__sentinel.json`; `scripts/analyze_adaptive.py`;
  `scripts/plot_adaptive.py` → `paper/figs/adaptive_robustness.png`.
- Tables: hand-inserted into `paper/tables/{main,healthbench}.tex`;
  `scripts/make_tables.py` also updated to emit the rows on a main-repo regen.

## Open items / candidate follow-ups
- **[done, 4/4]** Ran the **bare judge through the full E1 adaptive panel** — it collapses
  to **34–59%** (34.2 / 44.9 / 40.4 / 59.1), hypothesis confirmed: a generic judgment is
  evadable, converting the HealthBench honest-negative into a clean scaffold win on
  robustness. The `encoded_injection` set (the slow one) initially wedged the local Ollama
  on a pathological 24k-char prompt (#719); completed via a resilient driver
  (`/tmp/run_encinj_judge.py`: 60s per-call timeout + periodic runner reset + `ollama stop`
  recovery on hang). Same model/JUDGE_SYS/parser as `baselines.py` — `ollama stop` recovery
  treats an unprocessable prompt as not-blocked, which is the correct "judge failed to
  block" outcome.

## Bottom line
A second, stronger injection classifier (Sentinel) **confirms** the healthcare-gap
thesis — it tops clean injection yet still misses a third of clinical threats and is
evaded by adaptive attacks. A bare LLM-judge **ties QFIRE's detection on static
HealthBench**, an honest result that relocates the scaffold's measured value from raw
recall to consistency-across-threats, latency, auditability/determinism, and
(demonstrated for the scope chain) adaptive robustness.
