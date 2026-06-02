# QFIRE-MultiTurn (E9)

150 multi-turn conversations for evaluating QFIRE's full-transcript vs latest-turn-only
robustness to cross-turn injection. **Deterministically generated** (no LLM, seed 42) by
`scripts/gen_multiturn.py`: a verbatim malicious core (from QFIRE-HealthBench / public
injection attacks) wrapped in templated benign glue, so intent is never diluted and the
corpus is fully reproducible.

Sets (one JSONL per file; obj = `{pattern, label, domain, turns:[[role,text],...]}`):
- `split_payload.jsonl` (40, attack) — core fragmented across turns; last user turn alone is insufficient.
- `context_priming.jsonl` (40, attack) — benign turns prime a false premise, then the core.
- `crescendo.jsonl` (40, attack) — escalating benign turns; the core arrives only last.
- `benign.jsonl` (30, benign) — clinical-adjacent multi-turn conversations (FPR anchor).

`domain` selects the QFIRE chain at scoring time (`healthcare`→`hipaa_phi`, `injection`→`default`).
All identifiers are synthetic (inherited from QFIRE-HealthBench).
