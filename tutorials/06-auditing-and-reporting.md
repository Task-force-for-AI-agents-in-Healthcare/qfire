# 06 · Auditing & reporting

**Goal:** use QFIRE's immutable audit log to answer "what did the firewall decide,
and why?" — for compliance, forensics, and tuning.

**Time:** ~5 minutes. **Cost:** $0.

---

## Every decision is logged

`check`, `run`, and the `serve` proxy all append one JSON line per decision to
the audit log (`audit.jsonl` by default, set via `audit_path` in `qfire.toml`).
The log is **append-only** — it's an evidence trail, not mutable state.

A record:

```json
{
  "ts": "2026-05-30T21:59:21.337169+00:00",
  "event": "check",
  "terminal": "block",
  "chain_id": "default",
  "chain_version": 1,
  "deciding_rule": "injection_classifier_only",
  "deciding_node": "deberta",
  "reason": "injection probability 0.982 (threshold 0.50)",
  "prompt_hash": "b56f8900…62b12",
  "qfire_version": "…",
  "nodes": [ /* per-detector verdicts: kind, version, score, ms */ ],
  "wall_clock_ms": 0.23,
  "summed_detector_ms": 0.21
}
```

Note what is **not** there: the raw prompt. Only a `prompt_hash` is stored, so the
log doesn't become a new place sensitive prompts leak — while still letting you
prove the same prompt recurred and exactly which detector versions decided it.

## 1. Summarize the log

```bash
qfire report audit.jsonl
```

```
audit: audit.jsonl
  records:   253
  allowed:   116
  blocked:   137
  avg wall:  1403.0ms
  total cost: $-0.000000
```

(`report` defaults to `audit.jsonl`, so the path is optional.) Cost is ~$0 here
because the runs forwarded to local Ollama; with a paid provider the per-call
cost estimates accumulate.

## 2. Slice it with jq

The log is plain JSONL, so standard tooling works.

**Which rules block the most?**

```bash
jq -r 'select(.terminal=="block") | .deciding_rule' audit.jsonl \
  | sort | uniq -c | sort -rn
```

**Block rate per chain:**

```bash
jq -r '"\(.chain_id)\t\(.terminal)"' audit.jsonl \
  | sort | uniq -c
```

**Slowest decisions (latency outliers):**

```bash
jq -r '"\(.wall_clock_ms)\t\(.chain_id)\t\(.deciding_rule)"' audit.jsonl \
  | sort -rn | head
```

**Everything a single prompt triggered** (by hash):

```bash
jq 'select(.prompt_hash | startswith("b56f8900")) | {ts, terminal, deciding_rule, reason}' audit.jsonl
```

## 3. Machine-readable output for dashboards

`report --json` emits the records as a JSON **array** (every field, parsed) —
ideal for piping into your own aggregation:

```bash
# block rate from the JSON array
qfire report audit.jsonl --json \
  | jq '[.[] | .terminal] | {total: length, blocked: (map(select(.=="block")) | length)}'
```

Wire this into a cron job or CI step to track block rate and latency drift over
time.

## 4. Production tips

- **Rotate** the log like any append-only log (e.g. `logrotate`); each run is
  self-describing via `qfire_version` + `chain_version`, so split files stay
  analyzable.
- **`serve --redact`** keeps block *reasons* out of the client response while the
  full reason is still written to the audit log — you keep accountability without
  tipping off a probing attacker.
- The `prompt_hash` lets you correlate a user report ("my request was blocked")
  to the exact decision without ever storing the prompt text.

---

### What you learned

- Every ALLOW/BLOCK is appended to an immutable JSONL log — hash, not raw prompt.
- `qfire report` gives a quick summary; `--json` feeds dashboards.
- Plain `jq` answers "which rule blocked most", "block rate per chain", and
  "what did this prompt trigger".

---

**You've finished the tutorials.** From here:

- Browse the full rule library: `qfire rules list`
- Read the design spec in [`docs/`](../docs/) and the [paper](../paper/main.pdf)
- Skim the [README](../README.md) for the architecture and CLI reference
