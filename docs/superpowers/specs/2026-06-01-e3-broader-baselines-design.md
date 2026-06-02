# E3 — Broader Baselines (Llama Guard + LLM-judge-only) — Design (DRAFT)

**Date:** 2026-06-01
**Backlog:** [paper-strengthening E3](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — written ahead during the E1 run. Resolve the *Open questions*
section and get approval before writing the implementation plan.

## Research question

The paper compares QFIRE only to PromptGuard-2 and protectai DeBERTa-v3. A reviewer
will ask: *"cherry-picked baselines — where's Llama Guard, the most-cited open
guardrail, and a plain LLM-judge?"* E3 adds two missing baselines to the existing
head-to-head and QFIRE-HealthBench tables so the comparison is complete.

## What's reused

- `scripts/baselines.py` — now argparse-enabled (`--attacks/--benign/--out/--models`,
  dir-aware loading) from the E1 fix. It runs HF classifier baselines and writes
  P/R/F1/FPR/AUC/latency with Wilson CIs.
- The existing corpora: `corpora/eval/{attacks,benign}` (public injection, 1,968) and
  `corpora/healthcare_bench/{attacks,benign}` (QFIRE-HealthBench, 2,000).
- The paper's baseline tables/figures (`scripts/make_tables.py`, `figs/`).

## New baselines

1. **Llama Guard (Meta).** A safety classifier that labels prompts safe/unsafe across
   hazard categories. Runs locally via **Ollama** (`ollama pull llama-guard3`) — fits
   the no-API-key story. Because it's generative (emits "safe"/"unsafe\n<cat>"), it
   needs an **Ollama adapter** distinct from baselines.py's transformers pipeline:
   add an Ollama branch to `baselines.py` (call `/api/chat`, parse safe/unsafe → block
   decision) keyed e.g. `("llama-guard-3", "ollama:llama-guard3")`.
2. **LLM-judge-only.** A single general model (no QFIRE scope scaffold, no rule graph)
   given a generic "is this prompt an attack / should it be blocked?" instruction —
   to isolate how much QFIRE's *scaffold* (scope + PHI + collapse) adds over a bare
   model. Reuse the Ollama adapter with a judge prompt; key e.g.
   `("llm-judge-llama3.1", "ollama:llama3.1:8b")`.

Both report the same metrics as the existing baselines and slot into the same tables.

## Method

- Extend `baselines.py` with an Ollama-backed `run_ollama_model(name, tag, ...)` that,
  per prompt, calls the model and maps its output to block/allow (Llama Guard:
  unsafe→block; judge: the IN/OUT or BLOCK/ALLOW verdict→block). Add the two entries
  to `MODELS` (or a separate `OLLAMA_MODELS` list selected by `--models`).
- Run on **both** corpora (public injection + QFIRE-HealthBench), seed 42, into the
  existing baselines JSON so `make_tables.py` picks them up.
- Add Llama Guard + LLM-judge rows to the head-to-head table (Table of detectors) and
  the HealthBench table; update the prose to place each relative to QFIRE.

## Deliverables

- `baselines.py` Ollama adapter (+ a unit test for the safe/unsafe and verdict parsing).
- A small `scripts/run_baselines_extra.sh` to run the two new models on both corpora.
- Updated baseline tables in `main.tex`/`PAPER.md` (regenerated via `make_tables.py`
  if it's wired, else hand-insert the rows), rebuilt PDF.
- Findings doc; backlog E3 ticked.

## Success criterion

Llama Guard and LLM-judge-only appear in the head-to-head and HealthBench tables with
the same metrics + CIs as the other baselines, and the narrative honestly places each
(expected: Llama Guard decent on overt injection, weak on healthcare PHI/scope like
the other classifiers; bare LLM-judge below QFIRE's scoped chain — quantify it).

## Resolved decisions (user, 2026-06-01)
1. **Llama Guard:** `llama-guard3:8b` (full, ~1–2 s/call via Ollama — the serious
   open-guardrail baseline).
2. **LLM-judge-only backing model:** `llama3.1:8b` (the strong judge from the
   judge-model ablation; isolates QFIRE's scaffold over a capable bare judge).
3. **Adapter location:** extend `baselines.py` (Ollama branch) — keeps all baselines
   in one tool for table-consistency.
4. **Corpora:** both main corpora (public injection + QFIRE-HealthBench) **AND** fold
   Llama Guard into the E1 adaptive panel sets (show it's evaded too).

## Caveats
- Llama Guard's categories aren't injection-specific; map "unsafe" → block, and note
  the mismatch (it targets content harm, not prompt injection / PHI scope).
- Ollama generative latency >> the 86M classifiers; report it (a fairness point for
  the latency story, not a detection knock).
