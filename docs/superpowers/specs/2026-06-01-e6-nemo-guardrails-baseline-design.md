# E6 — NeMo Guardrails full-stack baseline — Design (DRAFT)

**Date:** 2026-06-01
**Backlog:** [paper-strengthening backlog](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — decisions resolved with the user 2026-06-01 (scope = both,
baseline first; rails = full stack; Phase 2 deferred). Pending user review of this spec
before writing the implementation plan.

## Research question

The paper now compares QFIRE to dedicated injection classifiers (DeBERTa,
PromptGuard-2, qualifire Sentinel) and a bare LLM-judge (E3). A reviewer can still ask:
*"you never compared to a complete guardrails **framework**."* **NVIDIA NeMo Guardrails**
is the leading open framework and is the first baseline that covers **all three QFIRE
pillars at once**:

| QFIRE pillar | NeMo Guardrails rail |
|---|---|
| injection detection | **jailbreak detection** (heuristic / self-check / model) |
| positive-security scope | **topic control** (allowed-topics rail) |
| HIPAA PHI panel | **PII / sensitive-data** rail (Presidio-based, non-LLM) |

E6 asks: **does a production-grade, full-stack guardrails framework close the healthcare
scope/PHI gap that QFIRE targets — and at what latency?** This is the most direct
whole-system comparison in the paper. Honest-negative discipline applies: if NeMo
matches or beats QFIRE on any corpus, we report it plainly.

## Scope (resolved)

- **Phase 1 (this spec): head-to-head baseline.** Run NeMo Guardrails as a full-stack
  guardrail (jailbreak + topic-control + PII) on the same corpora and slot it into the
  existing comparison tables/figures + the E1 adaptive panel.
- **Phase 2 (DEFERRED to a separate spec):** implement NeMo's rail types as chainable
  QFIRE policies (rail→QFIRE-rule mapping, runnable example chains, possibly a
  Presidio-backed PII node). Not built here; noted as follow-up.

## What's reused vs new

- **Reused:** the labeled corpora `corpora/eval/{attacks,benign}` (public injection,
  1,968) and `corpora/healthcare_bench/{attacks,benign}` (QFIRE-HealthBench, 2,000); the
  4 E1 adaptive sets; the metrics convention (attack = positive; block = positive
  prediction; P/R/F1/FPR/accuracy + 95% Wilson CI + latency p50/p95/p99); the paper
  baseline tables/figures.
- **New:** NeMo is a YAML/Colang-configured framework, **not** an HF
  `AutoModelForSequenceClassification`, so it cannot reuse `baselines.py`'s `run_model`.
  We add a dedicated driver `scripts/run_nemo.py` + a `nemo_config/` rails config that
  loads each prompt, runs the input rails, and maps "any rail blocks → block" to the
  same metrics/JSON shape `make_tables.py`/`analyze_adaptive.py` already read.

## Method

**Rails (full stack, resolved).** Enable NeMo **input rails**:
1. **Jailbreak detection** — NeMo's jailbreak detection rail (default to the heuristic +
   LLM self-check path; the NIM jailbreak model is avoided to stay API-free — see Open
   questions).
2. **Topic control** — an allowed-topics rail configured per corpus to the
   positive-security scope: a *clinical-workflow* allow-list for QFIRE-HealthBench, a
   *generic-assistant* allow-list for the public corpus. This is the analog of QFIRE's
   scope judge and the fiddly part of the config.
3. **PII / sensitive data** — Presidio analyzer (local, non-LLM) configured for the PHI
   identifier set (names, MRN, email, dates, SSN, phone) used by QFIRE's PHI panel.

**Backend (resolved).** No paid API (hard project constraint). NeMo's LLM-backed rails
(self-check, topic control) run on **local Ollama**, model **`llama3.1:8B`** — the same
model as the E3 bare-judge baseline, so the comparison isolates *framework* vs
*QFIRE scaffold*, not model choice. Presidio is local. Configure NeMo's LLM provider to
the Ollama OpenAI-compatible endpoint (`http://localhost:11434`).

**Block rule.** Positive (attack) class = NeMo blocks if **any** enabled input rail
refuses/flags the prompt (standard fail-closed guardrail deployment). Recall = block
rate on attacks; FPR = block rate on benign.

**Corpora & adaptive.** Run on **both** main corpora and **fold NeMo into the E1
adaptive panel** (4 sets), exactly as Sentinel was, so the figure/table gain a NeMo
column. (See latency risk — may require sampling.)

## Deliverables

- `scripts/run_nemo.py` — per-prompt NeMo driver → metrics JSON (`results.nemo-guardrails`),
  `--attacks/--benign/--out/--limit`, mirroring `baselines.py`'s output shape.
- `nemo_config/` — `config.yml` (rails + Ollama LLM provider) + Colang/topic specs
  (clinical and generic scope variants).
- `scripts/run_e6_nemo.sh` — run NeMo on both corpora + the 4 adaptive sets.
- Result JSONs in `bench-out/`; NeMo rows folded into the head-to-head + HealthBench
  tables and the adaptive figure/panel (extend `analyze_adaptive.py` with a `_nemo`
  reader; hand-insert table rows + a figure bar).
- Prose in `main.tex` + `PAPER.md`; rebuilt PDF.
- Findings doc; backlog E6 ticked; merge to master.

## Success criterion

NeMo Guardrails (full stack) appears in the head-to-head + HealthBench tables and the
adaptive panel with the same metrics + CIs, and the narrative honestly places it vs
QFIRE on each axis — **detection** (does the framework's PII+topic+jailbreak stack close
the healthcare gap that single classifiers miss?), **latency** (multiple LLM rails per
prompt vs QFIRE's bounded short-circuiting path), and **adaptive robustness**. Expected
shape (to be measured, not assumed): NeMo's Presidio PII helps on identifier-bearing PHI
like QFIRE's PHI panel; topic control helps on scope; jailbreak ≈ other classifiers on
overt injection; overall a real framework comparison with a large latency gap. Report
any axis where NeMo ties/beats QFIRE.

## Resolved decisions (user, 2026-06-01)
1. **Scope:** both — head-to-head **baseline first**, then map rails into QFIRE policies
   (Phase 2 **deferred** to a separate spec).
2. **Rails:** **full stack** — jailbreak + topic-control + PII (Presidio), to match
   QFIRE's combined inj+scope+PHI chain.
3. **Backend:** local **Ollama `llama3.1:8B`** for LLM-backed rails (API-free; same
   model as the E3 bare-judge so framework-vs-scaffold is isolated); Presidio local.
4. **Block rule:** any input rail blocks → block (fail-closed).
5. **Corpora:** both main corpora + fold into the E1 adaptive panel.

## Feasibility & risks (resolve in the plan / design review)
- **Install:** `nemoguardrails`, `presidio-analyzer`, `presidio-anonymizer`, a spaCy
  model (`en_core_web_lg`), and an Ollama-backed LLM provider. Confirm a smoke
  (block/allow on 2–3 prompts) before the full run.
- **Latency / throughput (biggest risk):** a full-stack NeMo input pass runs several
  rails, ≥1–2 of them LLM calls, so **seconds per prompt**. ~6,000 prompts (2 corpora +
  adaptive) could take **many hours**. Mitigations: (a) run on the **non-LLM rails
  first** (Presidio + jailbreak heuristic) cheaply, then LLM rails; (b) **sample** N per
  corpus (e.g. 400 attack / 400 benign, stratified) and report `n` + CIs; (c) overnight
  background run. Decide sampling-vs-full in the plan. **No silent caps** — log whatever
  is sampled.
- **Topic-control config quality:** the allowed-topics spec is subjective; write it to
  mirror QFIRE's scope rules and version it for reproducibility. A poorly-specified
  scope unfairly weakens NeMo — calibrate the allow-list to be a fair, good-faith config
  and say so.
- **Ollama contention:** serialize with any other Ollama-heavy run; single instance.

## Open questions for the design review
1. **Jailbreak rail variant:** heuristic-only (fast, weak), LLM self-check (Ollama,
   slower), or the NIM jailbreak model (best, but needs NGC/API → likely excluded).
   Proposed default: **heuristic + LLM self-check** (API-free).
2. **Full corpus vs sample:** run all ~6,000 prompts (overnight) or a stratified sample?
   Proposed default: **stratified sample (~400/400 per corpus, full adaptive sets)** with
   reported `n` + CIs, upgradeable to full if latency permits.
3. **Topic-control allow-lists:** one clinical + one generic spec — confirm the
   clinical scope mirrors QFIRE's `hc_*` scope rules.
