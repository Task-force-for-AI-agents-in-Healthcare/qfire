# E6 — NeMo Guardrails full-stack baseline — Results

**Date:** 2026-06-02
**Design:** [E6 design](2026-06-01-e6-nemo-guardrails-baseline-design.md)
**Status:** done (Phase 1: head-to-head baseline). Fully offline. Raw JSON in
`bench-out/nemo_*.json` and `bench-out/adaptive/*__nemo.json`. Env recipe in
`nemo_config/SETUP.md`.

E6 adds NVIDIA **NeMo Guardrails** — the leading open guardrails *framework* — as the
first baseline covering all three QFIRE pillars at once (jailbreak + scope + PHI), to
answer "you never compared to a complete framework." Honest-negative discipline applied.

## Method (offline)

- **Framework:** NeMo Guardrails 0.17 in an isolated Python-3.11 venv (`.venv-e6/`),
  driven via Ollama's OpenAI-compatible `/v1` endpoint (native `engine: ollama` path is
  broken by a langchain/ollama version mismatch — see SETUP.md).
- **Full input-rail stack, fail-closed (any rail blocks → block):**
  1. `self check input` — semantic injection + positive-security scope (LLM,
     `llama3.1:8B`, a calibrated low-false-positive prompt in `nemo_config/prompts.yml`);
  2. `jailbreak detection heuristics` — length/perplexity (local `gpt2-large`);
  3. `detect sensitive data on input` — Presidio PII with a good-faith high-signal PHI
     identifier set (EMAIL, PHONE, SSN, MEDICAL/DRIVER LICENSE, BANK/CC/IBAN, IP);
     PERSON/DATE/LOCATION **excluded** because they pervade benign clinical text.
- **Backend:** local Ollama `llama3.1:8B` — the same model as the E3 bare-judge, so the
  comparison isolates the *framework*, not the model.
- **Corpora:** public injection (`eval`) and QFIRE-HealthBench, each a stratified
  **400/400** sample (latency makes the full corpora infeasible; `n` + reasoning
  reported, no silent caps), plus the four E1 adaptive sets (attack-only recall, capped
  200/set). seed 42.

## Results

### Detection (main corpora)

| corpus (400/400) | Prec | Recall | F1 | FPR | p50 / p95 latency |
|---|---|---|---|---|---|
| public injection | 0.847 | 0.650 | 0.736 | 0.117 | 842 ms / 2690 ms |
| QFIRE-HealthBench | 0.922 | 0.882 | **0.902** | 0.075 | 450 ms / — |

Reference points: on HealthBench, QFIRE `bench_combined` = F1 0.868 (R 0.829); generic
classifiers 0.57–0.78; bare llama3.1:8B judge F1 0.899. On public injection, QFIRE hybrid
F1 0.856 (p95 0.24 s); dedicated classifiers F1 0.86–0.98 (p95 0.05–0.43 s).

### Adaptive robustness (recall, attack-only)

| adaptive set | NeMo | QFIRE scope+PHI |
|---|---|---|
| scope-impersonation (healthcare) | 0.550 | 1.000 |
| paraphrase-to-evade | 0.483 | 1.000 |
| encoded (healthcare) | 0.305 | 1.000 |
| encoded (injection) | 0.545 | 1.000 |

## Findings (honest)

1. **Static healthcare — NeMo edges QFIRE (honest negative).** NeMo's full stack reaches
   F1 **0.902** on QFIRE-HealthBench, above QFIRE `bench_combined` (0.868) and the single
   classifiers (0.57–0.78): the LLM scope self-check + Presidio PII catch the scope/PHI
   threats generic classifiers structurally miss. A complete framework *can* close the
   static healthcare gap.
2. **Generic injection — NeMo loses.** F1 0.736 vs QFIRE 0.856, with a high FPR (0.117).
3. **Latency — NeMo loses by ~10×.** p95 2.7 s (several LLM-backed rails per prompt) vs
   QFIRE's ~0.24 s.
4. **Adaptive robustness — NeMo collapses (decisive).** 30–55% recall under firewall-aware
   attacks — folding alongside the single classifiers it is built from — while QFIRE's
   positive-security scope holds at 100%. The framework's static-corpus strength does not
   survive paraphrase/encoding/impersonation.
5. **Auditability.** NeMo's scope rail is an opaque LLM call (like the bare judge), not the
   inspectable, unit-testable YAML policy QFIRE deploys.

**Net:** the framework comparison *reinforces* the thesis — closing the healthcare gap is
necessary but not sufficient; doing so with bounded latency, auditable policy, and adaptive
robustness is QFIRE's contribution.

## Integration

NeMo rows added to the head-to-head table (Table `tab:main`) and the HealthBench table
(`tab:healthbench`), a NeMo bar added to the adaptive panel
(`paper/figs/adaptive_robustness.png`), and a `\subsection` (`sec:nemo`) + citation. The
adaptive-robustness finding (`sec:adaptive`) now names NeMo as a framework that collapses.

## Caveats

- Main-corpus numbers are a stratified 400/400 sample (latency); Wilson CIs are in the raw
  JSON. The qualitative conclusions (adaptive collapse, latency gap, generic-injection
  deficit) are robust to the sample.
- The self-check prompt and PII entity set are a good-faith, calibrated config; a different
  scope prompt or entity list would shift NeMo's operating point (we tuned for low benign
  over-block, not to weaken it).
- Phase 2 (mapping NeMo rail types into chainable QFIRE policies) remains deferred.
