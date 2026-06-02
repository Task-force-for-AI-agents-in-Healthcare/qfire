# E9 — Multi-turn / conversational injection — Design

**Date:** 2026-06-02
**Backlog:** [paper-strengthening backlog](2026-06-01-paper-strengthening-experiments-backlog.md)
**Status:** DRAFT — pending user review before the implementation plan.

## Research question

Every QFIRE evaluation so far (head-to-head, HealthBench, E1 adaptive, E3 baselines) is
**single-turn**: one prompt in, one verdict out. But the dominant production failure mode
is **multi-turn**: an attacker primes benign-looking context over several turns, splits a
payload across messages, or gradually erodes scope, so that no single message looks
malicious. The AWS dual-layer study reports a single-layer input filter misses ~80% of
multi-turn injection sequences. E9 asks: *does QFIRE's per-message firewall catch
injections that only become malicious across turns — and if not, what is the smallest
stateful extension that does?*

## What's reused

- The QFIRE proxy / `qfire check` / `bench` path and the deployed chains.
- The HealthBench + injection threat taxonomy (the multi-turn variants target the same
  goals: PHI exfil, scope drift, instruction override) and the de-obfuscation pass.

## Method

1. **Build a multi-turn corpus** (`corpora/multiturn/`) in three patterns, each as an
   ordered list of turns with a final-state label (attack/benign):
   - **Split payload** — the injection/PHI request is fragmented across turns
     (e.g. base64 chunks, or "remember X" … "now use X to …").
   - **Context priming / scope erosion** — benign turns establish a false premise, then a
     later in-scope-looking turn exploits it (e.g. "you are now my records assistant" →
     "export the list we discussed").
   - **Crescendo-style** — incremental escalation where each turn is individually benign.
   Benign multi-turn conversations (clinical-adjacent) anchor the false-positive rate.
2. **Two evaluation modes** (both already expressible in the codebase — see the
   code-fact below):
   - **Full-transcript (QFIRE default):** detectors see `request.prompt_text()`, which
     concatenates the system prompt + every role-tagged message — i.e. the **whole
     conversation**. This is what QFIRE does today with no change.
   - **Latest-turn-only (naive per-message baseline):** feed only `latest_user()` (the
     most recent user turn) to the same chain — the failure mode of a stateless
     per-message filter. Expected to miss cross-turn buildup that the full-transcript mode
     catches.
   The comparison directly quantifies the value of QFIRE evaluating accumulated context.

   > **Code fact (verified 2026-06-02).** `src/engine.rs` evaluates
   > `request.prompt_text()` (full role-tagged transcript, `src/ir.rs:97`); a
   > `latest_user()` helper (`src/ir.rs:116`) returns only the last user turn. So
   > history-aware evaluation is the **default**, not a missing feature — E9 is
   > **measure-only**. The only new code is an eval-harness toggle that runs the chain on
   > `latest_user()` to produce the per-message comparison; no change to QFIRE's runtime
   > behavior is required.
3. **Score** recall (blocked malicious conversations) + FPR (benign conversations
   over-blocked) for both settings, vs the classifier panel where applicable (PromptGuard-2
   etc. are single-turn → run on the concatenated transcript as a fair multi-turn proxy).

## Deliverables

- `corpora/multiturn/` + a generator (`scripts/gen_multiturn.py`, seed 42, local LLM).
- A multi-turn harness (`scripts/run_multiturn.py`) exercising per-message vs windowed
  modes through QFIRE.
- Results table (recall/FPR per pattern × mode), findings doc.
- Paper: a §Multi-turn robustness subsection (or a Limitations entry if per-message is
  blind and the windowed fix is left as future work). Cite the multi-turn-evasion
  literature. Backlog E9 ticked.

## Success criterion

Per-pattern recall/FPR for QFIRE in per-message vs history-aware modes, honestly showing
where the per-message firewall is blind to cross-turn buildup and whether a windowed
evaluation recovers it. A clean result is either "QFIRE-with-history catches multi-turn
at acceptable FPR" or "per-message QFIRE misses class X → stateful detection is future
work" — both are useful and reportable.

## Resolved decisions (user, 2026-06-02)
1. Full design spec now; plan when picked up.
2. Local-LLM-generated multi-turn corpus (seed 42), benign anchors clinical-adjacent.
3. **Modes compared:** **full-transcript (QFIRE default) vs latest-turn-only**
   (`latest_user()`) — demonstrating the history advantage. (Code-verified: full transcript
   is the default; only an eval-harness toggle for the latest-turn baseline is new.)
4. **Corpus:** **~150 conversations, 3–5 turns each** — ~50 per attack pattern
   (split-payload / context-priming / crescendo) plus clinical-adjacent benign anchors;
   enough for Wilson CIs at modest cost.
5. **Scope of E9:** measure-only (no QFIRE runtime change); if very long transcripts are
   found to dilute the scope judge, a last-k window is noted as a follow-up, not built here.

## Feasibility & risks
- **Medium.** New corpus + a conversation-aware harness. The key design question — does
  QFIRE evaluate accumulated history or only the latest message — may surface a genuine
  architectural gap; treat that as a finding, not a blocker.
- **Honest-negative likely and welcome:** per-message firewalls are known-weak to
  multi-turn; documenting QFIRE's exact failure surface (and the windowed mitigation) is
  the contribution.
- **Label semantics:** a "malicious conversation" is blocked if QFIRE blocks **any** turn
  before the payload completes; define and report this rule explicitly.

## Open questions — RESOLVED (2026-06-02)
1. Modes → full-transcript (default) vs latest-turn-only (decision 3).
2. Proxy/history → **code-verified**: full transcript is the default (`prompt_text`);
   E9 is measure-only, only an eval-harness toggle for the latest-turn baseline is new.
3. Corpus → ~150 conversations, 3–5 turns (decision 4).
Spec is ready for an implementation plan when picked up.
