#!/usr/bin/env python3
"""E7 InjecAgent run driver (guard on/off).

Runs the InjecAgent indirect-prompt-injection benchmark twice over a *logged*
subset of its two splits (direct-harm ``dh`` + data-stealing ``ds``):

  * guard OFF -> agent talks directly to Ollama        (OPENAI_BASE_URL=:11434/v1)
  * guard ON  -> agent talks through the QFIRE proxy   (OPENAI_BASE_URL=:8787/v1)

The guard condition is selected purely by ``OPENAI_BASE_URL`` (InjecAgent's
patched ``GPTModel`` reads ``base_url`` + ``api_key`` from the env — see
``scripts/e7/SETUP.md`` Step 3). ``OPENAI_API_KEY=dummy`` for both (Ollama
ignores it; the patched client just needs a non-None key).

Higher ASR = worse (the indirect injection succeeded). Guard ON should LOWER ASR
relative to guard OFF. ``Valid Rate`` is the fraction of agent responses
InjecAgent could parse as a tool action; a QFIRE refusal parses as *invalid*
(not as a successful attack), which is the desired behaviour.

Subsetting (no silent caps)
---------------------------
InjecAgent has no ``--limit`` flag. We subset by TRIMMING the test-case files:
``third_party/InjecAgent/data/test_cases_{dh,ds}_base.json`` are JSON *arrays*.
We back each up to ``*.full.bak`` (once), write a truncated array keeping the
first ``--n-per-split`` cases, run, then ALWAYS restore the originals from backup
in a ``finally`` block so the repo data is never left trimmed. The exact kept
count per split is recorded in the manifest.

Caching
-------
InjecAgent's ``--use_cache`` reads cached step-1/step-2 outputs from the run's
output file, keyed only by ``(User Instruction, Tool Response)`` — it is
**endpoint-agnostic** (see ``src/evaluate_prompted_agent.py`` lines 49-71).
The output dir is also fixed by ``model_type/model_name/prompt_type`` with no
override flag, so guard-on would otherwise reuse guard-off's cached responses
and never actually traverse the proxy. To guarantee correctness we **DROP
``--use_cache`` entirely** (every case is re-inferenced under each guard) and,
between guards, delete the InjecAgent output dir so no stale rows survive. This
trades cache speed for the guarantee that guard-on truly goes through QFIRE.

Output
------
  * ``bench-out/e7/injecagent/<guard>/test_cases_{dh,ds}_base.json`` (copied results)
  * ``bench-out/e7/injecagent/<guard>/score.json`` (InjecAgent get_score dict)
  * ``bench-out/e7/injecagent_manifest.json``

Run from the worktree root with the pinned venv::

    .venv-e7/bin/python scripts/e7/run_injecagent.py --smoke
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & fixed facts (verified in SETUP.md / Tasks 0-3)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SETUP_MD = REPO_ROOT / "scripts" / "e7" / "SETUP.md"
QFIRE_BIN = REPO_ROOT / "target" / "release" / "qfire"
DEBERTA_DIR = REPO_ROOT / "models" / "deberta"
INJEC_DIR = REPO_ROOT / "third_party" / "InjecAgent"
INJEC_DATA = INJEC_DIR / "data"
OUT_ROOT = REPO_ROOT / "bench-out" / "e7" / "injecagent"
MANIFEST_PATH = REPO_ROOT / "bench-out" / "e7" / "injecagent_manifest.json"

SPLITS = ["dh", "ds"]          # direct-harm, data-stealing
SETTING = "base"
PROMPT_TYPE = "InjecAgent"
MODEL_TYPE = "GPT"             # InjecAgent's OpenAI-compatible client class

CHAIN = "e7_injecagent"
PROXY_ADDR = "127.0.0.1:8787"
JUDGE_MODEL = "gemma2:9b"

BASE_URL_OFF = "http://localhost:11434/v1"   # Ollama direct -> guard OFF
BASE_URL_ON = "http://localhost:8787/v1"     # QFIRE proxy   -> guard ON

DEFAULT_MODEL_FALLBACK = "qwen3-coder:30b"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def read_setup_model() -> str:
    try:
        text = SETUP_MD.read_text()
    except OSError:
        return DEFAULT_MODEL_FALLBACK
    m = re.search(r"^MODEL=(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else DEFAULT_MODEL_FALLBACK


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def out_dir_for(model: str) -> Path:
    """InjecAgent's hardcoded output dir (src/evaluate_prompted_agent.py line 32).
    The model name (incl. its colon) is used verbatim."""
    return INJEC_DIR / "results" / f"prompted_{MODEL_TYPE}_{model}_{PROMPT_TYPE}"


# ---------------------------------------------------------------------------
# Subset: trim test-case JSON arrays, restore from backup
# ---------------------------------------------------------------------------
def trim_data(n_per_split: int) -> dict:
    """Back up the full test-case files (once) and write truncated arrays keeping
    the first ``n_per_split`` cases each. Returns {split: kept_count}."""
    kept = {}
    for split in SPLITS:
        full = INJEC_DATA / f"test_cases_{split}_{SETTING}.json"
        bak = INJEC_DATA / f"test_cases_{split}_{SETTING}.full.bak"
        if not bak.exists():
            shutil.copy2(full, bak)
            log(f"backed up {full.name} -> {bak.name}")
        data = json.loads(bak.read_text())  # always trim from the pristine backup
        sub = data[:n_per_split]
        full.write_text(json.dumps(sub, indent=1))
        kept[split] = len(sub)
        log(f"trimmed {full.name}: kept {len(sub)}/{len(data)} cases")
    return kept


def restore_data() -> None:
    for split in SPLITS:
        full = INJEC_DATA / f"test_cases_{split}_{SETTING}.json"
        bak = INJEC_DATA / f"test_cases_{split}_{SETTING}.full.bak"
        if bak.exists():
            shutil.copy2(bak, full)
            log(f"restored {full.name} from {bak.name}")


# ---------------------------------------------------------------------------
# Proxy lifecycle (guard ON)
# ---------------------------------------------------------------------------
def start_proxy() -> subprocess.Popen:
    if not QFIRE_BIN.exists():
        raise FileNotFoundError(f"qfire binary not found: {QFIRE_BIN}")
    if not DEBERTA_DIR.exists():
        raise FileNotFoundError(f"DeBERTa dir not found: {DEBERTA_DIR}")

    log_path = REPO_ROOT / "bench-out" / "e7" / "qfire_proxy_injecagent.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logf = open(log_path, "ab")

    env = {
        **os.environ,
        "QFIRE_DEBERTA_DIR": str(DEBERTA_DIR),
        "QFIRE_JUDGE_MODEL": JUDGE_MODEL,
    }
    cmd = [
        str(QFIRE_BIN), "serve",
        "--addr", PROXY_ADDR,
        "--chain", CHAIN,
        "--openai-block-refusal",
    ]
    log(f"starting QFIRE proxy (guard ON, chain={CHAIN}): {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                            stdout=logf, stderr=subprocess.STDOUT)

    health = f"http://{PROXY_ADDR}/health"
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"QFIRE proxy exited early (code {proc.returncode}); see {log_path}")
        if http_ok(health):
            log(f"QFIRE proxy healthy at {health}")
            return proc
        time.sleep(0.5)
    proc.terminate()
    raise TimeoutError(f"QFIRE proxy did not become healthy within 30s; see {log_path}")


def stop_proxy(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    log("terminating QFIRE proxy")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        log("proxy did not stop; killing")
        proc.kill()
        proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# Running one guard condition
# ---------------------------------------------------------------------------
def run_guard(model: str, guard: str, base_url: str) -> dict:
    """Run InjecAgent (both splits) under one guard, copy results + score out.
    Returns a manifest entry."""
    out_dir = out_dir_for(model)
    # Fresh start: no stale rows from a previous guard can survive (we run
    # WITHOUT --use_cache, but also nuke the dir for full determinism).
    if out_dir.exists():
        shutil.rmtree(out_dir)
        log(f"cleared stale InjecAgent output dir {out_dir}")

    env = {
        **os.environ,
        "PYTHONPATH": ".",
        "OPENAI_BASE_URL": base_url,
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "dummy"),
    }
    cmd = [
        sys.executable, "src/evaluate_prompted_agent.py",
        "--model_type", MODEL_TYPE,
        "--model_name", model,
        "--setting", SETTING,
        "--prompt_type", PROMPT_TYPE,
        # NOTE: deliberately NOT passing --use_cache (endpoint-agnostic cache).
    ]
    log(f"RUN guard={guard} (OPENAI_BASE_URL={base_url}): {' '.join(cmd)}")

    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(INJEC_DIR), env=env,
                              capture_output=True, text=True)
        elapsed = round(time.time() - started, 1)
    except Exception as e:  # pragma: no cover - defensive
        elapsed = round(time.time() - started, 1)
        log(f"FAIL guard={guard}: launch error {e}")
        return {"returncode": None, "error": f"launch error: {e}",
                "elapsed_s": elapsed, "score": None, "result_paths": {}}

    stdout, stderr = proc.stdout or "", proc.stderr or ""

    # Copy the per-split result files out.
    dest = OUT_ROOT / guard
    dest.mkdir(parents=True, exist_ok=True)
    result_paths = {}
    for split in SPLITS:
        src = out_dir / f"test_cases_{split}_{SETTING}.json"
        if src.exists():
            dst = dest / f"test_cases_{split}_{SETTING}.json"
            shutil.copy2(src, dst)
            result_paths[split] = str(dst)
        else:
            log(f"WARNING guard={guard}: missing result file {src}")

    # Score: parse the score dict InjecAgent prints to stdout (JSON via
    # json.dumps(scores, indent=True) at the tail). Fall back to recomputing
    # from the copied files with src.utils.get_score.
    score = parse_score_stdout(stdout)
    if score is None:
        score = recompute_score(model)
    if score is not None:
        (dest / "score.json").write_text(json.dumps(score, indent=2))
        log(f"score guard={guard}: {json.dumps(score)}")
    else:
        log(f"WARNING guard={guard}: could not obtain score dict")

    if proc.returncode != 0:
        tail = (stderr or stdout)[-1500:]
        log(f"FAIL guard={guard}: rc={proc.returncode} ({elapsed}s)")
        log(f"  stderr/stdout tail: {tail.strip()[-700:]}")
        return {"returncode": proc.returncode,
                "error": tail.strip()[-1500:] or "nonzero return code",
                "elapsed_s": elapsed, "score": score,
                "result_paths": result_paths,
                "score_path": str(dest / "score.json") if score is not None else None}

    log(f"OK   guard={guard}: rc=0 ({elapsed}s)")
    return {"returncode": 0, "error": None, "elapsed_s": elapsed, "score": score,
            "result_paths": result_paths,
            "score_path": str(dest / "score.json") if score is not None else None}


def parse_score_stdout(stdout: str) -> dict | None:
    """InjecAgent ends with `print(json.dumps(scores, indent=True))`. Grab the
    last top-level JSON object containing '#Test Case'."""
    # Find candidate JSON objects (greedy from each '{' that looks like the score).
    for m in reversed(list(re.finditer(r"\{", stdout))):
        chunk = stdout[m.start():]
        # try progressively to load a balanced object
        depth = 0
        for i, ch in enumerate(chunk):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(chunk[: i + 1])
                    except Exception:
                        break
                    if isinstance(obj, dict) and "#Test Case" in obj:
                        return obj
                    break
    return None


def recompute_score(model: str) -> dict | None:
    """Recompute the score dict from the InjecAgent output files via its own
    get_score (run inside the InjecAgent dir so its relative paths resolve)."""
    out_dir = out_dir_for(model)
    files = {s: str(out_dir / f"test_cases_{s}_{SETTING}.json") for s in SPLITS}
    if not all(Path(p).exists() for p in files.values()):
        return None
    helper = (
        "import json,sys\n"
        "from src.utils import get_score\n"
        f"files={json.dumps(files)}\n"
        "print(json.dumps(get_score(files)))\n"
    )
    try:
        r = subprocess.run([sys.executable, "-c", helper], cwd=str(INJEC_DIR),
                           env={**os.environ, "PYTHONPATH": "."},
                           capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout.strip().splitlines()[-1])
        log(f"recompute_score failed: {r.stderr.strip()[-400:]}")
    except Exception as e:  # pragma: no cover
        log(f"recompute_score error: {e}")
    return None


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="E7 InjecAgent run driver (guard on/off).")
    ap.add_argument("--model", default=None,
                    help="Agent model name (default: MODEL= from scripts/e7/SETUP.md).")
    ap.add_argument("--n-per-split", type=int, default=20,
                    help="Cases kept per split (dh, ds). Default 20.")
    ap.add_argument("--guards", nargs="+", default=["off", "on"], choices=["off", "on"],
                    help="Guard conditions to run (default: off on).")
    ap.add_argument("--smoke", action="store_true",
                    help="Convenience: 3 cases per split.")
    args = ap.parse_args()

    n_per_split = 3 if args.smoke else args.n_per_split
    model = args.model or read_setup_model()

    log(f"model={model}")
    log(f"n_per_split={n_per_split}  splits={SPLITS}  guards={args.guards}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "experiment": "E7-injecagent",
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "smoke": args.smoke,
        "splits": SPLITS,
        "setting": SETTING,
        "prompt_type": PROMPT_TYPE,
        "chain": CHAIN,
        "n_per_split_requested": n_per_split,
        "n_per_split_kept": {},          # filled by trim_data
        "guards": args.guards,
        "openai_base_url": {"off": BASE_URL_OFF, "on": BASE_URL_ON},
        "use_cache": False,
        "cache_note": (
            "InjecAgent --use_cache is endpoint-agnostic (keyed by "
            "(User Instruction, Tool Response)); dropped entirely and the output "
            "dir is cleared between guards so guard-on truly traverses the proxy."
        ),
        "out_root": str(OUT_ROOT),
        "runs": {},                       # guard -> result entry
    }

    def persist() -> None:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    persist()

    try:
        kept = trim_data(n_per_split)
        manifest["n_per_split_kept"] = kept
        persist()

        for guard in args.guards:
            base_url = BASE_URL_ON if guard == "on" else BASE_URL_OFF
            if guard == "off":
                if not http_ok("http://localhost:11434/api/tags"):
                    log("WARNING: Ollama not reachable at :11434 (guard off may fail)")
            proxy = None
            try:
                if guard == "on":
                    proxy = start_proxy()
                res = run_guard(model, guard, base_url)
                res["openai_base_url"] = base_url
                manifest["runs"][guard] = res
                persist()
            finally:
                stop_proxy(proxy)
    finally:
        restore_data()
        persist()

    # Summary
    failed = [g for g, r in manifest["runs"].items() if r.get("returncode") != 0]
    log("SUMMARY (higher ASR = worse; guard-on should be lower):")
    for guard in args.guards:
        r = manifest["runs"].get(guard, {})
        sc = r.get("score") or {}
        log(f"  guard={guard}: "
            f"ASR-all(DH)={sc.get('ASR-all (Direct Harm)','?')} "
            f"ASR-all(DS)={sc.get('ASR-all (Data Stealing)','?')} "
            f"ASR-all(Total)={sc.get('ASR-all (Total)','?')} "
            f"ASR-valid(Total)={sc.get('ASR-valid (Total)','?')} "
            f"ValidRate={sc.get('Valid Rate','?')}")
    log(f"manifest -> {MANIFEST_PATH}")
    if failed:
        log(f"DONE with failures in guards: {failed}")
        return 1 if len(failed) == len(args.guards) else 0
    log("DONE: all guard runs returned 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
