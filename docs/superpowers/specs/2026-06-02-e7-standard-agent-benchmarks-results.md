# E7 — Standard agent benchmarks (AgentDojo + InjecAgent) — Results

**Date:** 2026-06-02
**Design:** [2026-06-02-e7-standard-agent-benchmarks-design.md](2026-06-02-e7-standard-agent-benchmarks-design.md)
**Plan:** [../plans/2026-06-02-e7-standard-agent-benchmarks.md](../plans/2026-06-02-e7-standard-agent-benchmarks.md)
**Status:** DONE. Paper §3.13 (`sec:agentbench`, after E4 §3.12) + Figure `paper/figs/agent_benchmarks.png` (`fig:agentbench`); `PAPER.md` §3.13. Reproducible env: `scripts/e7/SETUP.md`.

## Question
E4 showed QFIRE cuts an agent's harmful-action rate 0.375→0.000 on our **own**
mock-EHR harness. Does the inline-firewall result hold on the **community-standard**
agent-injection benchmarks the field reports (AgentDojo, InjecAgent)?

## Setup
- **Deployment:** QFIRE proxy (`qfire serve`, OpenAI-wire-compatible) in front of each
  benchmark; guard-on routes the agent through QFIRE, guard-off goes straight to Ollama.
  Selected purely by the agent's `base_url`/port.
- **Agent:** `qwen3-coder:30b` (smoke-picked: the only local candidate with reliable
  tool-calling via Ollama `/v1`; `gpt-oss:20b` emits no tool calls, `gemma3:27b` weak).
  Judge: `gemma2:9b`. Build: `cargo build --release --features onnx` (real DeBERTa).
- **Guard chain:** per-suite positive-security **domain** scope (`e7_<suite>` /
  `e7_injecagent`; `rules/e7/scope_*.yaml`) composed with the injection `default` chain
  (with E7-local injection-rule variants, see Deviations). AgentDojo attack:
  `important_instructions`. benchmark_version `v1.2.2`.
- **Coverage (stratified, logged in manifests — no silent caps):** AgentDojo 6 user × 3
  injection per suite × 4 suites → n=24 benign, n=72 security cases per guard. InjecAgent
  30 cases/split (dh+ds) → n=60 per guard. Wilson 95% CIs throughout.
- Scripts: `scripts/e7/{run_agentdojo,parse_agentdojo,run_injecagent,parse_injecagent,analyze_e7,plot_e7,calibrate}.py`;
  raw runs gitignored under `runs/`, `bench-out/e7/`; summary committed.

## Headline results

**AgentDojo** (Targeted ASR = fraction of security cases where the attacker goal
actually executed; benign utility = user tasks solved without attack):

| | Benign Utility | Utility-Under-Attack | Targeted ASR |
|---|---|---|---|
| guard OFF | 0.583 [0.39–0.76] | 0.417 | **0.181 [0.109–0.285]** |
| guard ON  | 0.208 [0.09–0.41] | 0.083 | **0.000 [0.000–0.051]** |

All 72 injected security cases contained; every suite to ASR 0 (per-suite OFF ASR:
banking 0.28, slack 0.22, travel 0.22, workspace 0.00).

**InjecAgent** (ASR over valid responses; Valid Rate = parseable tool-action rate):

| split | guard OFF ASR-valid | guard ON ASR-valid | Valid Rate off→on |
|---|---|---|---|
| direct-harm | 0.069 | 0.034 | 0.97→0.97 |
| data-stealing | 0.222 | 0.034 | 0.90→0.97 |
| **total** | **0.143 [0.074–0.257]** | **0.034 [0.010–0.117]** | 0.93→0.97 |

**Side-by-side (E4 mock-EHR):** harmful-action rate 0.375→0.000, benign completion
0.95→0.825.

## Reading
- **QFIRE substantially reduces attack success on both standard benchmarks** — AgentDojo
  ASR to 0 (deterministic block of every injected case), InjecAgent ~4× lower — matching
  the mock-EHR direction and the structural-defense line (CaMeL, tool-boundary firewalls).
- **The honest contrast is the utility cost.** It is *small* in the tightly-scoped
  healthcare panel (0.95→0.825) but *large* here (0.58→0.21 on AgentDojo): a broad
  per-suite "general assistant" scope conservatively refuses many legitimate
  out-of-the-ordinary actions (e.g. a travel task that emails an itinerary to a named
  third party; a banking task that pays an external payee). This **reinforces the paper's
  thesis** — QFIRE's value is greatest where the operator can declare a *precise* domain;
  a blunt generic scope still eliminates injection success but pays more utility for it.
  (InjecAgent has no benign-task analog; its near-constant Valid Rate shows the guard
  isn't simply garbling outputs.)

## Findings surfaced during implementation (all handled, all disclosed)
1. **Proxy bug:** on BLOCK the proxy returned HTTP 403 + a `{"qfire":...}` body, which the
   OpenAI Python SDK (used by both harnesses) raises on — blocks registered as harness
   *errors*, not contained attacks. Fix: opt-in `qfire serve --openai-block-refusal` →
   returns a 200 OpenAI-shaped `chat.completion` whose assistant message is the refusal
   (realistic firewall behavior; default 403 unchanged). New, unit-tested.
2. **Framing self-collision:** QFIRE serializes the transcript for detection with
   `[system]`/`[assistant]` role tags (`src/ir.rs prompt_text`), and the shared
   `injection_delimiter_escape` regex `\[/?(INST|SYS|system|assistant)\]` matched its own
   framing → every system-prompt-bearing request blocked. Single-prompt `bench` never hit
   this. Per user decision (chain-only, no core change): E7-local
   `e7_injection_delimiter_escape` narrows the bracket alternation to real Llama tokens.
3. **Generic scope can't do dynamic per-task scope.** A single "stay on the user's task"
   judge can't distinguish a user-requested sensitive action from an injected one (both
   are e.g. "send money"); it blocked benign and attack alike. Per user decision: use
   **per-suite domain** scopes (fixed domain + data-is-not-instructions principle),
   analogous to the healthcare domain scope — the deployment-realistic instantiation.
4. **Latent shared-rule FPs on agent transcripts:** `injection_jailbreak_dan` matched
   "stan" inside "under**stan**d"/"as**sistan**t" (no word boundary); the
   `injection_encoding_obfuscation` entropy node fired on legitimate high-entropy tool
   data (IBANs, ids). E7-local variants fix both (word-boundary; drop entropy node). Core
   shared rules and headline chains unchanged.
5. **AgentDojo `security` semantics:** an injection task's `security()` returns **True iff
   the attack goal actually executed** (verified against post-run environment). So
   `security==True` is a BREACH; Targeted ASR = mean(security==True). (First parser pass
   had it inverted; caught and fixed against ground-truth transcripts.)
6. **Per-suite task IDs differ:** slack has no `injection_task_0`; travel's are unordered.
   Driver reads real IDs from the suite rather than assuming `<kind>_task_0..N`.

## Caveats
- One mid-size **local** agent (no paid API): absolute benign utility is modest and
  guard-off ASR is model-dependent; the guard-on ASR≈0 is a property of the deterministic
  block.
- The scope judge (`gemma2:9b`, temperature 0) is mildly **stochastic** on borderline
  benign cases — absorbed by the Wilson intervals; reproducibility caveat noted (no seed
  is forwarded to the judge; not changed, per the chain-only scope).
- E7-local rule/scope files live under `rules/e7/` and `chains/e7_*.yaml`; the InjecAgent
  source patch + two missing-dep fixes (nltk, lazy `together` import) are recorded in
  `scripts/e7/SETUP.md` (the gitignored `third_party/InjecAgent/` holds them).

## Reproduce
See `scripts/e7/SETUP.md`. Then:
```
.venv-e7/bin/python scripts/e7/run_agentdojo.py --user-tasks-per-suite 6 --injection-tasks-per-suite 3
.venv-e7/bin/python scripts/e7/run_injecagent.py --n-per-split 30
.venv-e7/bin/python scripts/e7/analyze_e7.py    # -> bench-out/e7/summary.json + results.md
.venv-e7/bin/python scripts/e7/plot_e7.py       # -> paper/figs/agent_benchmarks.png
```
