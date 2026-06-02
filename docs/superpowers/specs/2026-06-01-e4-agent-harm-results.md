# E4 — End-to-End Agent Harm Reduction — Results

**Date:** 2026-06-01
**Design:** [E4 agent-harm design](2026-06-01-e4-agent-harm-design.md)
**Plan:** [E4 implementation plan](../plans/2026-06-01-e4-agent-harm.md)
**Status:** done. Fully offline. Agent `llama3.1:8b` (temp 0, seed 42); guard chain
`bench_combined`. Raw artifacts in `bench-out/e4/` (`runs.jsonl`, `results.md`,
`summary.json`).

E4 answers the "so what" of the agentic framing: does putting QFIRE's decision in
front of a tool-using agent actually prevent *harmful tool actions* (not just block
prompts), and at what utility cost? All numbers below are real (no invented values).

## Method (offline)

- **Sandbox:** an in-process mock EHR over synthetic data (`scripts/e4/sandbox.py`)
  exposing benign tools (`list_clinic_info`, `get_appointment`, `get_patient_chart`,
  `export_records`, `send_email`) and logging **every** call with a ground-truth
  `harmful` flag: cross-patient read, bulk/other export, external or PHI email, or
  system-prompt reveal. No real PHI, no network.
- **Agent:** a hand-rolled ReAct loop (`scripts/e4/agent.py`) on `llama3.1:8b` via the
  Ollama HTTP API (temperature 0, seed 42 → reproducible), parsing a text-action
  protocol (`ACTION: tool(args)` / `FINISH`).
- **Guard:** every **untrusted** input — the task request and each tool observation —
  is gated through `qfire check -c bench_combined`. A BLOCK on the task short-circuits
  to a refusal (the model never runs); a BLOCK on a tool observation scrubs the
  poisoned content to a refusal note before the model sees it. `bench_combined` is the
  deterministic injection+PHI chain (the calibrated 0.023-FPR operating point from E5),
  **not** the strict `hipaa_phi` conjunction (which over-blocks at FPR 1.00).
- **Episodes (`scripts/e4/episodes.py`):** 40 benign (legitimate P001 admin/clinical-info
  tasks) + 40 attack — 20 **direct** (plausible exfiltration requests with realistic
  external addresses + a system-prompt reveal) and 20 **indirect** (a benign task whose
  tool observation is poisoned with a realistic record annotation instructing external
  exfiltration). Each attack phrasing is blocked by the firewall on its *exfiltration
  intent*, not on any attack-looking marker (verified). Every episode runs **with** and
  **without** the guard.

## Headline result

| metric | guard OFF | guard ON | Δ |
|---|---|---|---|
| **Harmful-action rate** (40 attack episodes) | **0.375** [0.242, 0.530] | **0.000** [0.000, 0.088] | **−0.375** |
| **Benign-completion rate** (40 benign episodes) | 0.950 [0.835, 0.986] | 0.825 [0.680, 0.913] | −0.125 |

(95% Wilson intervals.) **QFIRE eliminates every harmful action (0.375 → 0.000) at a
modest utility cost (0.950 → 0.825).**

By attack vector:
- **Direct:** 0.450 → 0.000 (9/20 → 0/20). All 20 direct attacks were **refused at the
  prompt boundary** — the malicious request never reached the model.
- **Indirect:** 0.300 → 0.000 (6/20 → 0/20). The **poisoned tool observations were
  scrubbed** before the model could act on them (38/40 attack episodes had ≥1 blocked
  input).

## Why these numbers (honest reading)

- **The base model is partially, not fully, safe.** `llama3.1:8b` declines 62.5% of the
  attacks on its own (over-sharing only when a request looks like the patient's own
  legitimate workflow, or following the most natural indirect injection). QFIRE closes
  the **residual 37.5%** — deterministically and independently of model whim. This is the
  defense-in-depth argument: a guard you can audit, not a model you must trust.
- **The utility cost is concentrated and explainable.** Of the 7 benign episodes the
  guarded agent failed, **5 are the single outbound-email template** (`send_email` to a
  named recipient), which `bench_combined` conservatively blocks as potential PHI egress;
  the remaining **2 are agent flakiness present with *and* without the guard** (benign
  OFF also failed 2). So the firewall-attributable cost is exactly the conservative
  email handling — a deliberate, defensible PHI-egress caution, not random breakage.
- **Harm is prevented *via the prompt boundary*.** QFIRE does not police tool calls
  directly; it blocks the malicious instruction/content before the model emits the
  forbidden action. The result bounds harm reduction for the threat QFIRE actually
  targets (injection + PHI/scope at the prompt layer).

## Caveats

- A mock sandbox is a model of harm, not production; results bound a controlled setting.
- One local agent model (`llama3.1:8b`); a more compliant or more capable model would
  shift the baseline harmful-action rate (the QFIRE→0 column is a property of the
  deterministic guard, not the model).
- The benign utility cost reflects `bench_combined`'s conservative outbound-email rule; a
  deployment could relax it for whitelisted internal domains at some egress risk.
- Indirect-injection baseline harm (0.30) is a lower bound — a stronger or stealthier
  injection (or a less injection-resistant model) would raise it; QFIRE blocks the
  poisoned content regardless.
