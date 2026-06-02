# E3 — Broader Baselines (Prompt-Injection Sentinel + LLM-judge-only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add two missing baselines — `qualifire/prompt-injection-sentinel` (a gated HF ModernBERT injection classifier) and a bare LLM-judge (`llama3.1:8b`, generic prompt) — to the head-to-head + QFIRE-HealthBench tables, fold Sentinel into the E1 adaptive panel, and tell the "a second dedicated injection classifier is evaded too; a bare judge < QFIRE scaffold" story with measured numbers.

**Architecture:** Sentinel reuses `scripts/baselines.py`'s existing HF-transformers `run_model()` (labels `{0:benign,1:jailbreak}` → injection = last logit = the existing `prob[-1]`; only needs the `MODELS` entry + `HF_TOKEN` passing). The bare judge uses a thin Ollama-backed `run_ollama_model()` (judge mode) in the same file. Run on both main corpora + the E1 adaptive sets; fold the new columns into the tables/figure.

**Tech Stack:** Python 3 + `transformers`/`torch` (Sentinel, gated → `HF_TOKEN`), stdlib `urllib` for Ollama `/api/chat` (`llama3.1:8b` bare judge), reuses `baselines.py` metrics + `make_tables.py`.

---

## ⚠️ Constraints
- **Llama Guard 3 is OUT.** It is a content-safety classifier (MLCommons hazards), not an injection detector — a category mismatch. Replaced by Sentinel (a real injection classifier). Any Llama-Guard / `is_unsafe` / `guard`-mode code is to be **removed**, not kept.
- **Sentinel is gated:** load with `HF_TOKEN` in the environment (the token's HF account has accepted the model terms). It is ModernBERT → needs recent `transformers` (≥4.48); the `/tmp/qbase` env already loads its config.
- **Resource contention:** Ollama is single-instance — run the bare-judge pass when no other Ollama-heavy experiment (E5) is active. Sentinel is a small HF classifier (CPU, no Ollama) — no contention.
- Block decision is the positive (attack) class; recall = block-rate on attacks (same convention as the existing HF baselines).
- **HF token is a runtime secret** — pass it via the environment at run time only; never write it into a committed file.

---

## Current state (uncommitted WIP from the interrupted Llama-Guard attempt)
`scripts/baselines.py` (modified, **uncommitted**) and `scripts/test_baselines_ollama.py` (untracked) already contain a full Ollama adapter with BOTH a Llama-Guard `guard` mode and the bare-judge `judge` mode, plus `is_unsafe`/`judge_blocks`. Task 1 below **revises** that WIP: delete the Llama-Guard pieces, keep the bare judge, and add Sentinel to the HF path. Do not start from a clean `baselines.py` — edit the current working-tree version.

---

## File structure
| Path | Create/Modify | Responsibility |
|------|---------------|----------------|
| `scripts/baselines.py` | Modify | Add Sentinel to `MODELS` + pass `HF_TOKEN` in `run_model`; trim `OLLAMA_MODELS` to the bare judge only; remove `is_unsafe` + the `guard` branch. |
| `scripts/test_baselines_ollama.py` | Modify | Keep the `judge_blocks` test; remove the `is_unsafe` test. |
| `scripts/run_e3_baselines.sh` | Create | Run Sentinel + bare-judge on injection + HealthBench corpora. |
| `scripts/analyze_adaptive.py` | Modify | Add a Sentinel column (reads `<set>__sentinel.json`). |
| `paper/tables/*.tex` via `make_tables.py` or hand-insert | Modify | Add Sentinel + bare-judge rows to the head-to-head + HealthBench tables. |
| `paper/main.tex`, `paper/PAPER.md`, `paper/main.pdf` | Modify | Update baseline prose + rebuild. |
| `docs/superpowers/specs/2026-06-01-e3-broader-baselines-results.md` | Create | Findings. |

---

## Task 1: Sentinel (HF) + bare-judge (Ollama) in baselines.py (TDD)

**Files:** Modify `scripts/baselines.py`, `scripts/test_baselines_ollama.py`

- [ ] **Step 1: Fix the test to the final surface (judge only)**

Overwrite `scripts/test_baselines_ollama.py` with exactly:

```python
import baselines as b


def test_judge_blocks():
    assert b.judge_blocks("BLOCK: tries to exfiltrate the system prompt") is True
    assert b.judge_blocks("ALLOW") is False
    assert b.judge_blocks("allow - benign question") is False
    # unparseable -> conservative allow (do not over-count blocks)
    assert b.judge_blocks("I'm not sure about that") is False


def test_sentinel_registered():
    keys = [k for k, _ in b.MODELS]
    assert "prompt-injection-sentinel" in keys
    # bare judge present, Llama Guard removed
    ok = [n for n, _, _ in b.OLLAMA_MODELS]
    assert "llm-judge-3.1-8b" in ok
    assert not any("guard" in n for n in ok)
```

- [ ] **Step 2: Run the test to verify the Sentinel/guard assertions fail**

Run: `cd scripts && python3 -m pytest test_baselines_ollama.py -q`
Expected: `test_judge_blocks` passes; `test_sentinel_registered` FAILS (Sentinel not yet in `MODELS`, Llama Guard still present).

- [ ] **Step 3: Add Sentinel to `MODELS`**

In `scripts/baselines.py`, change the `MODELS` list to:

```python
MODELS = [
    ("deberta-v3-injection", "protectai/deberta-v3-base-prompt-injection"),
    ("promptguard-2-86m", "meta-llama/Llama-Prompt-Guard-2-86M"),
    ("prompt-injection-sentinel", "qualifire/prompt-injection-sentinel"),
]
```

(Sentinel labels are `{0:benign, 1:jailbreak}` → injection = last logit, which `run_model`
already uses as `inj = float(prob[-1])`. No parsing change needed.)

- [ ] **Step 4: Pass `HF_TOKEN` in `run_model` (gated download)**

In `run_model`, change the load lines so the gated Sentinel (and PromptGuard-2) weights
download when an `HF_TOKEN` is set, and stay backward-compatible when it isn't:

```python
    tok_env = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    kw = {"token": tok_env} if tok_env else {}
    tok = AutoTokenizer.from_pretrained(repo, **kw)
    model = AutoModelForSequenceClassification.from_pretrained(repo, **kw)
```

- [ ] **Step 5: Remove Llama Guard, keep the bare judge**

Set `OLLAMA_MODELS` to the bare judge only:

```python
OLLAMA_MODELS = [
    ("llm-judge-3.1-8b", "ollama:llama3.1:8b", "judge"),
]
```

Delete the `is_unsafe` function entirely. In `run_ollama_model`, delete the
`if mode == "guard":` branch so the body is just the judge path:

```python
def run_ollama_model(name, tag_spec, mode, prompts, labels):
    tag = tag_spec.split("ollama:", 1)[1]
    preds, lat = [], []
    for i, p in enumerate(prompts):
        t0 = time.perf_counter()
        try:
            out = _ollama_chat(tag, JUDGE_SYS, f"Prompt:\n{p}")
            blocked = judge_blocks(out)
        except Exception:
            blocked = False
        lat.append((time.perf_counter() - t0) * 1000.0)
        preds.append(blocked)
        if (i + 1) % 250 == 0:
            print(f"  [{name}] {i+1}/{len(prompts)}", flush=True)
    m = metrics(preds, labels)
    m["latency_ms"] = dict(p50=pct(lat, 0.5), p95=pct(lat, 0.95), p99=pct(lat, 0.99),
                           mean=sum(lat) / len(lat))
    m["model"] = tag_spec
    return m
```

(Leave `judge_blocks`, `_ollama_chat`, `JUDGE_SYS`, and the `main()` Ollama dispatch
loop as they are — they already work for the judge.)

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd scripts && python3 -m pytest test_baselines_ollama.py -q`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/baselines.py scripts/test_baselines_ollama.py
git commit -m "feat(E3): Sentinel (HF injection classifier) + bare LLM-judge baselines; drop Llama Guard (content-safety, not injection)"
```

---

## Task 2: Smoke both new baselines

**Files:** none

- [ ] **Step 1: Smoke Sentinel + bare-judge on a tiny corpus**

Run (CAP keeps it to 5 attacks / 5 benign; `HF_TOKEN` lets Sentinel download):
```bash
cd /Users/jim/Desktop/qfire/.claude/worktrees/e3-baselines
PY=/tmp/qbase/bin/python; [ -x "$PY" ] || PY=python3
QFIRE_BASELINE_CAP=5 HF_TOKEN="$HF_TOKEN" $PY scripts/baselines.py \
  --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --models "sentinel,llm-judge" --out bench-out/_e3smoke.json 2>&1 | tail -8
$PY -c "import json;d=json.load(open('bench-out/_e3smoke.json'))['results'];print({k:(round(v['recall'],2) if 'recall' in v else v.get('error','?')) for k,v in d.items()})"
rm -f bench-out/_e3smoke.json
```
Expected: both `prompt-injection-sentinel` and `llm-judge-3.1-8b` produce a recall
number (not an error/SKIPPED). The Sentinel weights download on first run (needs
`HF_TOKEN` exported in the shell). If Sentinel errors with a ModernBERT/`KeyError`,
the env's `transformers` is too old — `pip install -U transformers` in `/tmp/qbase`.

(No commit — smoke only. The HF token is supplied via the environment, never committed.)

---

## Task 3: Run on both main corpora

**Files:** `scripts/run_e3_baselines.sh`

- [ ] **Step 1: Write the runner**

Create `scripts/run_e3_baselines.sh`:

```bash
#!/usr/bin/env bash
# E3: score qualifire/prompt-injection-sentinel (HF, gated -> needs HF_TOKEN) + a bare
# LLM-judge (llama3.1:8b via Ollama) on the two main corpora, into the baseline JSONs
# make_tables.py reads. Run the bare-judge pass when no other Ollama-heavy job is active.
# Requires HF_TOKEN exported for the gated Sentinel download.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=python3
[ -x /tmp/qbase/bin/python ] && PY=/tmp/qbase/bin/python
: "${HF_TOKEN:?set HF_TOKEN (gated Sentinel repo) before running}"
echo "== public injection =="
$PY scripts/baselines.py --attacks corpora/eval/attacks --benign corpora/eval/benign \
  --models "sentinel,llm-judge" --out bench-out/baselines_e3_injection.json
echo "== QFIRE-HealthBench =="
$PY scripts/baselines.py --attacks corpora/healthcare_bench/attacks --benign corpora/healthcare_bench/benign \
  --models "sentinel,llm-judge" --out bench-out/baselines_e3_healthbench.json
echo "E3_BASELINES_DONE"
```

- [ ] **Step 2: chmod + syntax-check, then run when Ollama is free**

Run: `chmod +x scripts/run_e3_baselines.sh && bash -n scripts/run_e3_baselines.sh && echo "syntax OK"`.
Full pass (with `HF_TOKEN` exported, Ollama free): `./scripts/run_e3_baselines.sh` →
`E3_BASELINES_DONE`; verify both JSONs have `results.prompt-injection-sentinel.recall`
and `results.llm-judge-3.1-8b.recall`.

- [ ] **Step 3: Commit the runner + result JSONs**

```bash
git add scripts/run_e3_baselines.sh
git add -f bench-out/baselines_e3_injection.json bench-out/baselines_e3_healthbench.json
git commit -m "results(E3): Sentinel + bare-judge on public injection + QFIRE-HealthBench"
```

---

## Task 4: Fold Sentinel into the E1 adaptive panel

**Files:** Modify `scripts/analyze_adaptive.py`

- [ ] **Step 1: Score Sentinel on the 4 E1 adaptive sets**

Sentinel is a fast HF classifier (no Ollama) — safe to run anytime. With `HF_TOKEN` set:
```bash
PY=/tmp/qbase/bin/python; [ -x "$PY" ] || PY=python3
for s in impersonation_healthcare paraphrase_evaded encoded_healthcare encoded_injection; do
  HF_TOKEN="$HF_TOKEN" $PY scripts/baselines.py --attacks corpora/adaptive/$s --benign corpora/eval/benign \
    --models sentinel --out bench-out/adaptive/${s}__sentinel.json
done
```
Expected: 4 `<set>__sentinel.json` files with `results.prompt-injection-sentinel.recall`.

- [ ] **Step 2: Add a Sentinel reader to `analyze_adaptive.py`**

Add next to `_promptguard` (match the existing style; `ROOT` is the adaptive dir):

```python
def _sentinel(set_name):
    p = os.path.join(ROOT, f"{set_name}__sentinel.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    res = d.get("results", d)
    for k, v in res.items():
        if isinstance(v, dict) and "recall" in v and "sentinel" in k.lower():
            return v["recall"]
    return None
```

Then in `main()`, add `sent = _sentinel(s)` per set, store `summary[s]["sentinel"] = sent`,
add a `Sentinel` column to the results table (via the existing `cell()` helper), and
include `sent` in the `cls = max(...)` classifier-gap computation alongside DeBERTa /
PromptGuard (skip `None`s so a missing file doesn't crash the max).

- [ ] **Step 3: Re-run the analyzer + commit**

```bash
python3 scripts/analyze_adaptive.py && grep -i "sentinel" bench-out/adaptive/results.md
git add scripts/analyze_adaptive.py
git add -f bench-out/adaptive/results.md bench-out/adaptive/summary.json bench-out/adaptive/*__sentinel.json
git commit -m "results(E3): fold Sentinel into the E1 adaptive panel (a 2nd dedicated classifier, evaded too)"
```

---

## Task 5: Tables + paper prose

**Files:** Modify `scripts/make_tables.py` (or hand-insert), `paper/main.tex`, `paper/PAPER.md`

- [ ] **Step 1: Add the new baseline rows to the head-to-head + HealthBench tables**

`make_tables.py` reads the baseline JSON(s) for baseline rows. Either (a) merge the E3
result JSONs into the JSON(s) `make_tables.py` reads so existing logic picks them up, or
(b) extend `make_tables.py` to also read `baselines_e3_injection.json` /
`baselines_e3_healthbench.json` and emit `prompt-injection-sentinel` + `llm-judge-3.1-8b`
rows (P/R/F1/FPR/p50). Inspect `make_tables.py` `main()` first to choose the lower-risk
path. Regenerate: `python3 scripts/make_tables.py`.

- [ ] **Step 2: Update the baseline prose in `main.tex` + `PAPER.md`**

In the head-to-head and HealthBench results sections, add one sentence placing each new
baseline with the **real** Task-3 numbers, e.g.: "A second dedicated injection
classifier, Prompt-Injection Sentinel (ModernBERT), reaches F1~X on public injection but
only R recall on QFIRE-HealthBench — like DeBERTa/PromptGuard it carries no scope/PHI
signal — and is evaded by the adaptive attacks (E1 panel); a bare \texttt{llama3.1:8b}
judge reaches J, below QFIRE's scoped chain by D." Do not invent numbers.

- [ ] **Step 3: Build the PDF**

Run: `python3 scripts/build_paper.py 2>&1 | tail -3` → `OK — built …/paper/main.pdf`.

- [ ] **Step 4: Commit**

```bash
git add scripts/make_tables.py paper/tables paper/main.tex paper/PAPER.md paper/main.pdf
git commit -m "paper(E3): Sentinel + bare-judge rows in baseline tables + prose"
```

---

## Task 6: Findings + backlog + merge

**Files:** Create `docs/superpowers/specs/2026-06-01-e3-broader-baselines-results.md`; Modify backlog

- [ ] **Step 1: Write the findings doc** from the real numbers (both corpora + the
adaptive Sentinel column): where Sentinel lands vs PromptGuard-2 / DeBERTa / QFIRE on
injection and HealthBench, that Sentinel is also evaded by the E1 adaptive attacks, and
the bare-judge-vs-QFIRE-scaffold delta. Note the Llama-Guard category-mismatch rationale
(why it was swapped for Sentinel) and the gated-repo reproduction note (HF terms +
`HF_TOKEN`). Do NOT invent numbers. Keep honest-negative discipline.

- [ ] **Step 2: Tick backlog E3, commit, merge to master**

In the backlog charter, update the E3 heading to "Broader baselines (Prompt-Injection
Sentinel + LLM-judge-only)", set `**Status:**` to `[x] done`, and link the results doc.
```bash
git add docs/superpowers/specs/2026-06-01-e3-broader-baselines-results.md docs/superpowers/specs/2026-06-01-paper-strengthening-experiments-backlog.md docs/superpowers/specs/2026-06-01-e3-broader-baselines-design.md docs/superpowers/plans/2026-06-01-e3-broader-baselines.md
git commit -m "results(E3): findings; backlog E3 done"
git fetch origin && git rebase origin/master
git push origin worktree-e3-baselines:master   # fast-forward; if rejected, rebase onto origin/master then push
```

---

## Self-review notes
- Sentinel (HF, decision 1) → Task 1 Steps 3-4 + Task 3 + Task 4. ✓
- Bare-judge llama3.1:8b generic prompt (decisions 2,5) → Task 1 Step 5 (`JUDGE_SYS`/`judge_blocks` already present) + Task 3. ✓
- Llama Guard removed (decision 1) → Task 1 Step 5 (drop `OLLAMA_MODELS` guard entry, `is_unsafe`, guard branch); test asserts no `guard` key. ✓
- Both main corpora → Task 3; Sentinel folded into E1 adaptive panel (decision 4) → Task 4. ✓
- Tables + prose → Task 5; findings + merge → Task 6. ✓
- Adapter in baselines.py (decision 3) → Task 1. ✓
- Gated Sentinel: `HF_TOKEN` passed in `run_model` (Step 4) and exported in every run step; token never committed. ✓
- Type consistency: `judge_blocks`, `run_ollama_model(name,tag_spec,mode,...)` (mode kept but only "judge" used), `OLLAMA_MODELS` entries `(key,"ollama:tag",mode)`, `MODELS` 2-tuples `(key, repo)`, analyzer `_sentinel` → `summary[*]["sentinel"]`. ✓
- **Risk:** Sentinel ModernBERT needs recent `transformers`; mitigated (Task 2 notes the upgrade) and the E1 env already loads its config.
