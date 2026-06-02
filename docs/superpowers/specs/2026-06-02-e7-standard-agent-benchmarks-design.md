# E7 — Standard agent benchmarks (AgentDojo + InjecAgent) — Design

**Date:** 2026-06-02
**Backlog:** [paper-strengthening backlog](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — decisions resolved with the user 2026-06-02 (AgentDojo + InjecAgent,
**complementing** the healthcare mock-EHR harness, cited alongside it). Pending user
review of this spec before writing the implementation plan.

## Research question

E4 showed QFIRE cuts an agent's harmful-action rate from 0.38→0.00 on a **healthcare
mock-EHR** sandbox. A reviewer will ask: *"that's your own custom harness — does it hold
on the community-standard agent-injection benchmarks the rest of the field reports?"*
Both CaMeL~\cite{camel2025} and the tool-boundary-firewall work~\cite{firewallsbench2026}
evaluate on **AgentDojo**, **InjecAgent**, Agent Security Bench, and τ-Bench. E7 runs
QFIRE (proxy) on the two most-cited — **AgentDojo** (tool-use tasks with injected
attacks) and **InjecAgent** (indirect, tool-response-embedded injection) — as an
external-validity complement to E4, reported with their native metrics.

## What's reused

- The **QFIRE proxy** (`qfire serve`), which is wire-compatible with the
  OpenAI/Anthropic/Gemini/Ollama APIs — so an existing agent harness routes through
  QFIRE by changing only its base URL.
- The E4 agent model + local Ollama backend (no paid API), and the with/without-guard
  harness pattern from E4.
- QFIRE's `default` (injection) + `hipaa_phi`/scope chains; for general-domain agent
  tasks a `default`-style injection+scope chain (no PHI panel) is the fair config.

## New

- AgentDojo and InjecAgent are external Python frameworks. E7 adds thin **integration
  drivers** (`scripts/run_agentdojo.py`, `scripts/run_injecagent.py`) that (a) stand up
  `qfire serve` pointed at Ollama, (b) configure the benchmark's model client
  `base_url` to the QFIRE proxy, and (c) run each benchmark twice — **guard on**
  (through QFIRE) and **guard off** (direct to Ollama) — collecting the benchmark's
  native metrics.

## Method

- **AgentDojo** (97 tasks, 629 security cases across workspace/banking/travel/Slack).
  Native metrics: **Benign Utility** (task success, no attack), **Utility Under Attack**
  (task success while an injection is present), and **Targeted ASR** (rate the agent
  executes the attacker's goal). Run guard-on vs guard-off; report all three per suite
  and pooled, with the **ASR drop** and the **benign-utility cost** (same safety-vs-utility
  framing as E4).
- **InjecAgent** (indirect prompt injection: malicious instructions embedded in tool
  responses; ~1k cases, "direct harm" + "data stealing" splits). Metric: **ASR** with
  vs without QFIRE on the tool-output boundary.
- **Backend (no paid API).** The agent runs on the most capable **local** tool-calling
  model available (candidates on this host: `gpt-oss:20b`, `qwen3-coder:30b`,
  `gemma3:27b`, `llama3.1:8B`); pick by a benign-utility smoke and report the choice.
  QFIRE's LLM-judge (if scope rules are enabled) uses the same local backend.
- **Fairness.** QFIRE sees the same prompts/tool-outputs the agent sees, at the proxy
  boundary. Where QFIRE only inspects the *prompt* (not tool calls directly), state that
  explicitly — harm is prevented via the prompt/tool-output boundary, as in E4.

## Deliverables

- `scripts/run_agentdojo.py`, `scripts/run_injecagent.py` (+ a setup note for installing
  the two benchmarks in a pinned venv).
- Result JSONs; an external-agent-validity table (ASR / Benign Utility / Utility-Under-
  Attack, guard on/off) for AgentDojo suites + InjecAgent.
- Paper: a subsection (or extension of the E4 §) placing QFIRE's standard-benchmark
  numbers next to the mock-EHR result and citing CaMeL/firewalls for comparison; cite
  AgentDojo + InjecAgent. Rebuilt PDF.
- Findings doc; backlog E7 ticked.

## Success criterion

QFIRE's ASR-reduction and benign-utility-cost reported on AgentDojo (per-suite + pooled)
and InjecAgent with their native metrics, placed honestly against (i) the E4 mock-EHR
result and (ii) published CaMeL/firewall numbers. Expected: QFIRE meaningfully lowers
Targeted ASR at a modest benign-utility cost; honest-negative if utility drops sharply
or ASR reduction is weaker than on the healthcare harness.

## Resolved decisions (user, 2026-06-02)
1. **Benchmarks:** AgentDojo **and** InjecAgent (direct + indirect agent threats).
2. **Relationship to E4:** **complement** the healthcare mock-EHR (do not replace);
   report side-by-side and cite the standard benchmarks alongside.
3. **Backend:** local only (no paid API) — strongest available local tool-calling model.
4. **Agent model:** **smoke-pick the strongest local model** (compare gpt-oss:20b /
   qwen3-coder:30b / gemma3:27b on a benign-utility smoke; pick the best and report it).
   Prioritizes a clean benign-utility signal over E4 parity; report the chosen model and
   its no-guard baseline utility so the safety-vs-utility delta is interpretable.
5. **Coverage:** **stratified subset** across AgentDojo's 4 suites + InjecAgent's splits,
   with reported `n` and Wilson CIs; log exactly what is sampled (no silent caps). Full
   run only if latency permits.
6. **QFIRE chain:** **injection `default` + a generic positive-security scope rule**
   ("stay on the user's task; no out-of-scope tool actions") — exercises QFIRE's actual
   differentiator on agents. The benign over-block this may cause is measured and reported
   (not hidden), consistent with the §3.3 over-refusal discipline.

## Feasibility & risks (resolve in plan / review)
- **Integration effort (medium-high):** AgentDojo/InjecAgent expect an OpenAI-style
  endpoint; QFIRE's proxy must slot in as that endpoint and forward to Ollama. Verify a
  2–3 task smoke before the full run.
- **Local-model utility ceiling (main risk):** AgentDojo benign utility depends on a
  capable tool-calling agent; a small local model may score low benign utility even
  *without* QFIRE, compressing the safety-vs-utility signal. Mitigation: use the best
  local model, report its baseline utility, and frame results as "QFIRE's ASR reduction
  at the utility the local agent achieves." This is an honest constraint of the no-paid-API
  rule — state it.
- **Throughput:** agent episodes are multi-step LLM loops → slow on one Ollama instance;
  budget an overnight run and/or a task subset (report `n`, no silent caps).
- **Benchmark version pinning:** snapshot AgentDojo/InjecAgent commit hashes for repro.

## Open questions — RESOLVED (2026-06-02)
1. Agent model → smoke-pick the strongest local model (decision 4).
2. Coverage → stratified subset with `n` + CIs (decision 5).
3. QFIRE chain → injection `default` + generic scope rule, over-block measured
   (decision 6).
Spec is ready for an implementation plan when picked up.
