# E7 — Agent-Security Benchmark Setup (AgentDojo + InjecAgent behind the QFIRE proxy)

This document is the **reproducible record** for the E7 experiment environment: running
QFIRE's firewall proxy in front of the AgentDojo and InjecAgent agent-security benchmarks.
Run everything from this worktree:
`/Users/jim/Desktop/qfire/.claude/worktrees/e7-agent-benchmarks` (branch
`worktree-e7-agent-benchmarks`). Do **not** `cd` into the main checkout.

## Environment summary

| Component | Value |
|---|---|
| Python | **3.11.10** (via pyenv shim `python3.11`; the bare `python3` shim is 3.9.18, too old — agentdojo needs >=3.10) |
| venv | `.venv-e7/` (gitignored) |
| agentdojo | **0.1.35** (PyPI release) — the `local` provider IS present, so **no git fallback needed** |
| openai SDK | **2.40.0** — dependency resolver picked openai 2.x. It still exposes the `OpenAI` class with a `base_url` kwarg (`hasattr(openai, "OpenAI") == True`), which is all we need to point the client at the QFIRE proxy. `openai>=1.30` was requested explicitly and is satisfied. |
| InjecAgent | pinned to commit **f19c9f2** ("update"), in `third_party/InjecAgent/` (gitignored) |
| qfire binary | `target/release/qfire` (built `cargo build --release --features onnx`) |
| DeBERTa model | `models/deberta` → symlink to `/Users/jim/Desktop/qfire/models/deberta` (model.onnx + tokenizer.json), gitignored |

## Candidate agent models (to be smoke-picked in Task 3)

These are local models served via an OpenAI-compatible endpoint (e.g. Ollama / vLLM),
addressed through the QFIRE proxy:

- `gpt-oss:20b`
- `qwen3-coder:30b`
- `gemma3:27b`

## QFIRE proxy / BLOCK shape (to be verified in Task 2)

QFIRE runs as an OpenAI-compatible proxy. On a **BLOCK** decision it returns an
**OpenAI-shaped refusal** (a normal chat-completion response whose content is a refusal),
so both AgentDojo (openai `local` provider) and InjecAgent (patched `OpenAI` client with
`base_url`) treat it as an ordinary completion. Exact wire compatibility and the BLOCK
response shape are to be confirmed in Task 2.

---

## Step 1 — Build qfire + symlink the DeBERTa model

```bash
cd /Users/jim/Desktop/qfire/.claude/worktrees/e7-agent-benchmarks
cargo build --release --features onnx   # -> target/release/qfire (REQUIRED: --features onnx, else DeBERTa runs as a sub-ms lexical stub and the injection chain is not representative; all prior experiments build this way)

# DeBERTa ONNX is gitignored; reuse the main checkout's copy.
# NOTE: the worktree had no models/ dir, so create it first, then symlink the deberta subdir.
mkdir -p models
ln -sfn /Users/jim/Desktop/qfire/models/deberta models/deberta
ls -la models/deberta && ls target/release/qfire
```

`models/deberta` resolves to `model.onnx` (738 MB) + `tokenizer.json` (8.6 MB). Both
`models/` and `target/` are already gitignored, so the symlink and binary are never tracked.

## Step 2 — Python 3.11 venv + AgentDojo (pinned)

```bash
python3.11 -m venv .venv-e7
.venv-e7/bin/python -m pip install -U pip          # -> pip 26.1.2
.venv-e7/bin/python -m pip install "agentdojo==0.1.35"

# agentdojo has no __version__ attribute; query via importlib.metadata:
.venv-e7/bin/python -c "
from importlib.metadata import version
import openai
print('agentdojo', version('agentdojo'), '| openai', openai.__version__)"
# -> agentdojo 0.1.35 | openai 2.40.0
```

**Install path chosen: PyPI release v0.1.35 (NOT the git 089ed46 fallback).**
Reason: Step 4 confirmed the `local` provider (`LOCAL` enum value) is exposed by the
0.1.35 `benchmark` CLI, so the documented git fallback for a missing `local`/`openai-compatible`
provider was unnecessary.

## Step 3 — Clone + pin + patch InjecAgent

```bash
git clone https://github.com/uiuc-kang-lab/InjecAgent.git third_party/InjecAgent
cd third_party/InjecAgent && git checkout f19c9f2 && cd ../..

# requirements.txt openai pin found: bare "openai" (no version constraint).
# Full requirements.txt:  openai / anthropic / transformers / torch
.venv-e7/bin/python -m pip install -r third_party/InjecAgent/requirements.txt
# (this installs torch 2.12.0, transformers 5.9.0; transformers pulls tokenizers 0.22.2,
#  downgrading from 0.23.1 — agentdojo still imports fine afterward, verified.)

.venv-e7/bin/python -m pip install "openai>=1.30"   # already satisfied (2.40.0)
```

### InjecAgent patch (verbatim before/after — `src/models.py`, `GPTModel.__init__`)

`import os` is already present at line 1 of the file, so no import was added.

```diff
diff --git a/src/models.py b/src/models.py
index 2f9b71c..4773f7a 100644
--- a/src/models.py
+++ b/src/models.py
@@ -40,8 +40,8 @@ class GPTModel(BaseModel):
         super().__init__()  
         from openai import OpenAI
         self.client = OpenAI(
-            api_key = os.environ.get("OPENAI_API_KEY"),
-            organization = os.environ.get("OPENAI_ORGANIZATION")
+            api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
+            base_url=os.environ.get("OPENAI_BASE_URL"),
         )
         self.params = params
```

This points InjecAgent's OpenAI client at `OPENAI_BASE_URL` (the QFIRE proxy) and drops
the `organization` kwarg. Because `third_party/InjecAgent/` is gitignored (Step 5), this
patch lives **only in the working tree** — this SETUP.md is the reproducible record.

## Step 4 — Confirm the `local` provider + enumerate suites/tasks

```bash
.venv-e7/bin/python -m agentdojo.scripts.benchmark --help 2>&1 | grep -iE "local|model|attack|suite"
# --model [...|LOCAL|VLLM_PARSED]   <- LOCAL provider present
# --model-id TEXT                   The model id for local models.
# --tool-delimiter TEXT             Used for local models only.
# --attack TEXT                     manual/direct/ignore_previous/system_message/
#                                   injecagent/important_instructions(+variants)/
#                                   tool_knowledge/dos/swearwords_dos/captcha_dos/
#                                   offensive_email_dos/felony_dos
```

```bash
.venv-e7/bin/python -c "
from agentdojo.task_suite.load_suites import get_suites
s = get_suites('v1')
print({k:(len(v.user_tasks), len(v.injection_tasks)) for k,v in s.items()})
"
```

### Suite / task population (agentdojo 0.1.35, suite version `v1`)

This is the population that later subset selection stratifies from:

| Suite | user_tasks | injection_tasks |
|---|---|---|
| workspace | 40 | 6 |
| travel | 20 | 7 |
| banking | 16 | 9 |
| slack | 21 | 5 |
| **total** | **97** | **27** |

## Step 5 — gitignore E7 artifacts

Appended to `.gitignore` (existing entries kept; a `.venv-e6/` entry already existed):

```
# E7 agent-benchmark artifacts
/.venv-e7/
/third_party/InjecAgent/
/runs/
/results/
bench-out/e7/
```

Verification:

```bash
git status --short | grep -E "venv-e7|InjecAgent|/runs/|/results/" || echo "clean"   # -> clean
git check-ignore models/deberta target/release/qfire                                  # both ignored
```

Only `.gitignore` (and this `scripts/e7/SETUP.md`) are tracked changes for Task 0.

## Step 6 — Commit

```bash
git add scripts/e7/SETUP.md .gitignore
git commit -m "chore(E7): env setup — .venv-e7, agentdojo 0.1.35 pin, InjecAgent f19c9f2 + base_url patch"
```
