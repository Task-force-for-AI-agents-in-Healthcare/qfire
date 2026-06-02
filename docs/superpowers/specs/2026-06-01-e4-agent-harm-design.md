# E4 — End-to-End Agent Harm Reduction — Design (DRAFT)

**Date:** 2026-06-01
**Backlog:** [paper-strengthening E4](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — written ahead during the E1 run. This is the **largest** E-item
and likely needs decomposition into sub-projects (see below). Resolve *Open questions*
and get approval before any plan.

## Research question

The paper firewalls *prompts* but never shows blocking prevents *downstream harm* —
the "so what" for the agentic framing. E4 puts QFIRE in front of a real tool-using
agent over a mock EHR/tool sandbox and measures **harmful-action rate** (with vs
without the firewall) plus **benign task-completion** (the utility cost of safety).

## Where the firewall sits

QFIRE guards the agent's calls to its backing LLM (the proxy; base-URL swap, already
built: `qfire serve`, `src/proxy/mod.rs`). Flow:

```
user / injected content → agent loop → (LLM call via QFIRE proxy) → model
                                          │ BLOCK → refusal; agent can't get the
                                          │         malicious instruction → no harmful tool call
                                          └ ALLOW → forward → agent acts (tool calls)
```

A malicious or injection-bearing prompt that would drive the agent to a forbidden
tool action (PHI export, cross-patient read, instruction override) is blocked before
the model emits that action. We measure whether that actually prevents the harmful
*tool invocation* end-to-end.

## Components (candidate sub-projects)

1. **Mock tool sandbox** — a local HTTP server exposing EHR-like tools over **synthetic**
   data: `get_appointment`, `list_clinic_info` (benign/in-scope) and
   `export_all_records`, `read_other_patient_chart`, `send_external_email`,
   `reveal_system_prompt` (harmful/out-of-scope). It **logs every tool invocation** —
   the ground truth for harmful-action detection. No real PHI.
2. **Agent loop** — a tool-calling ReAct-style loop on a local model (Ollama), whose
   LLM endpoint is the QFIRE proxy (base-URL swap). Deterministic-ish (seed, temp 0).
3. **Task suite** — scripted episodes: *benign* tasks (should complete via benign
   tools) and *attack* episodes (direct malicious request and/or indirect injection in
   tool-returned content) that should drive a forbidden tool call absent the firewall.
4. **Harness** — run each episode **with** and **without** QFIRE in front; record the
   set of tool calls per episode; classify each as harmful (forbidden tool/args) or
   benign-complete. Metrics: harmful-action rate (with/without), benign completion rate
   (with/without), and the deltas.

## Metrics & success criterion

- **Harmful-action rate**: fraction of attack episodes that reach a forbidden tool
  call — expect a large drop with QFIRE.
- **Benign task-completion rate**: fraction of benign episodes completed — expect a
  small drop with QFIRE (the over-refusal/utility cost).
- Success = an end-to-end utility-vs-safety result (harm ↓↓, utility ≈) — the most
  compelling argument for the agentic framing. Honest-negative: report any benign
  tasks QFIRE breaks and any attacks that still get through.

## Deliverables (per sub-project, sequenced)

- Mock tool server + synthetic dataset (+ tests on tool-call logging).
- Agent loop wired through `qfire serve` (with/without toggle).
- Task suite (benign + attack episodes, intent labels).
- Harness + analyzer + figure (`paper/figs/agent_harm.png`: harmful-action & benign
  completion, with/without). Findings doc + paper subsection; backlog E4 ticked.

## Resolved decisions (user, 2026-06-01)
1. **Agent framework / model / protocol:** hand-rolled minimal **ReAct loop** on
   **llama3.1:8b**, parsing a **simple text-action protocol** (`ACTION: tool(args)`) —
   no framework deps, robust to weak local function-calling, fully reproducible.
2. **Threat:** **both direct + indirect injection** — direct malicious requests AND
   malicious text embedded in tool-returned "records" (the stronger agentic threat
   QFIRE's prompt-boundary firewall targets).
3. **Decomposition:** **split into 4 sequential sub-projects** (sandbox → agent →
   task-suite → harness), each its own spec/plan/build, integrated at the end. **Do
   E4 last** (after E3, E5).

### Still to settle when E4 is brainstormed (per sub-project)
- Which QFIRE chain guards the agent (likely `hipaa_phi`) and on which turn(s)
  (user turn, tool-content turn, or both — indirect injection implies tool-content).
- Exact forbidden-tool list + "harmful action" arg conditions (e.g. cross-patient =
  `patient_id` ≠ session patient).
- Episode counts (benign vs attack) for tight rates.
These are deferred to E4's own brainstorm since it's decomposed and runs last.

## Caveats
- A mock sandbox is a model of harm, not production; results bound a controlled setting.
- Local-model tool-calling flakiness can confound benign completion — separate
  "agent failed to use the tool" from "firewall blocked it."
- This measures harm prevented *via the prompt boundary*; QFIRE does not police tool
  calls directly — frame the claim precisely.
