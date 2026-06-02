#!/usr/bin/env python3
"""E7 AgentDojo run driver.

Runs the AgentDojo agent-security benchmark twice over a stratified, *logged*
subset:

  * guard OFF -> agent talks directly to Ollama        (LOCAL_LLM_PORT=11434)
  * guard ON  -> agent talks through the QFIRE proxy   (LOCAL_LLM_PORT=8787)

The guard condition is selected purely by ``LOCAL_LLM_PORT`` (the AgentDojo
``LOCAL`` provider builds ``http://localhost:$LOCAL_LLM_PORT/v1``). For each
(suite, guard) we run both a BENIGN condition (no attack) and an ATTACK
condition (``--attack important_instructions``).

Everything that ran is captured in ``bench-out/e7/agentdojo_manifest.json`` —
the exact user_task / injection_task ids per suite, ports, logdirs, and the
per-(suite,guard,condition) return code + error. No silent caps: the subset is
clamped to the suite population and the clamp is recorded.

Run from the worktree root with the pinned venv::

    .venv-e7/bin/python scripts/e7/run_agentdojo.py --smoke

Result JSON layout (per case)::

    <logdir>/<pipeline>/<suite>/<user_task_id>/<attack_or_none>/<injection_or_none>.json

Each per-case JSON holds the transcript (``messages``), ``error``, ``injections``
and metadata, but NOT a precomputed verdict. AgentDojo computes utility/security
at aggregation time and prints ``Average utility: XX.XX%`` to stdout (captured
here per (suite,guard,condition)); the per-case verdicts are recomputed from the
transcripts by ``scripts/e7/parse_agentdojo.py`` using AgentDojo's own checkers.

Guard ON uses a per-suite domain-scope chain (``e7_<suite>``); the proxy is
restarted per suite with that chain.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & fixed facts (verified in SETUP.md / Tasks 1-3)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
SETUP_MD = REPO_ROOT / "scripts" / "e7" / "SETUP.md"
QFIRE_BIN = REPO_ROOT / "target" / "release" / "qfire"
DEBERTA_DIR = REPO_ROOT / "models" / "deberta"
MANIFEST_PATH = REPO_ROOT / "bench-out" / "e7" / "agentdojo_manifest.json"

# Suite population (agentdojo 0.1.35, suite version v1) — SETUP.md Step 4.
SUITE_POP = {
    "workspace": {"user": 40, "injection": 6},
    "travel": {"user": 20, "injection": 7},
    "banking": {"user": 16, "injection": 9},
    "slack": {"user": 21, "injection": 5},
}
ALL_SUITES = ["workspace", "travel", "banking", "slack"]

ATTACK = "important_instructions"

PORT_OFF = "11434"  # Ollama direct  -> guard OFF
PORT_ON = "8787"    # QFIRE proxy    -> guard ON
PROXY_ADDR = "127.0.0.1:8787"
JUDGE_MODEL = "gemma2:9b"


def chain_for(suite: str) -> str:
    """Per-suite domain-scope chain (rules/e7/scope_suites.yaml + chains/e7_<suite>.yaml)."""
    return f"e7_{suite}"

DEFAULT_MODEL_FALLBACK = "qwen3-coder:30b"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def read_setup_model() -> str:
    """Grep the ``MODEL=`` line out of SETUP.md."""
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


def task_ids(prefix: str, n: int) -> list[str]:
    return [f"{prefix}_{i}" for i in range(n)]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Proxy lifecycle (guard ON)
# ---------------------------------------------------------------------------
def start_proxy(chain: str) -> tuple[subprocess.Popen, Path]:
    """Start the QFIRE proxy (guard ON) with the given default chain and wait for
    /health. Caller MUST terminate the returned process (do it in a finally block)."""
    if not QFIRE_BIN.exists():
        raise FileNotFoundError(f"qfire binary not found: {QFIRE_BIN}")
    if not DEBERTA_DIR.exists():
        raise FileNotFoundError(f"DeBERTa dir not found: {DEBERTA_DIR}")

    log_path = REPO_ROOT / "bench-out" / "e7" / "qfire_proxy.log"
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
        "--chain", chain,
        "--openai-block-refusal",
    ]
    log(f"starting QFIRE proxy (guard ON, chain={chain}): {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                            stdout=logf, stderr=subprocess.STDOUT)

    health = f"http://{PROXY_ADDR}/health"
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            logf.flush()
            raise RuntimeError(
                f"QFIRE proxy exited early (code {proc.returncode}); see {log_path}")
        if http_ok(health):
            log(f"QFIRE proxy healthy at {health}")
            return proc, log_path
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
# Running one (suite, guard, condition)
# ---------------------------------------------------------------------------
def run_case(model: str, suite: str, guard: str, port: str, condition: str,
             ut_ids: list[str], it_ids: list[str], logdir: Path) -> dict:
    """Run a single AgentDojo invocation. Returns a result dict for the manifest."""
    cmd = [
        sys.executable, "-m", "agentdojo.scripts.benchmark",
        "--model", "LOCAL", "--model-id", model,
        "-s", suite,
        "--logdir", str(logdir),
    ]
    for ut in ut_ids:
        cmd += ["-ut", ut]
    if condition == "attack":
        cmd += ["--attack", ATTACK]
        for it in it_ids:
            cmd += ["-it", it]

    env = {**os.environ, "LOCAL_LLM_PORT": port}
    label = f"{suite}/{guard}/{condition}"
    log(f"RUN {label}: {len(ut_ids)} user tasks"
        + (f", {len(it_ids)} injection tasks, attack={ATTACK}" if condition == "attack" else ", benign")
        + f" (LOCAL_LLM_PORT={port}) -> {logdir}")

    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env,
                              capture_output=True, text=True)
        elapsed = round(time.time() - started, 1)
    except Exception as e:  # pragma: no cover - defensive
        elapsed = round(time.time() - started, 1)
        log(f"FAIL {label}: launch error {e}")
        return {"returncode": None, "error": f"launch error: {e}",
                "elapsed_s": elapsed, "avg_utility": None}

    stdout, stderr = proc.stdout or "", proc.stderr or ""
    avg_util = None
    m = re.search(r"Average utility:\s*([\d.]+)%", stdout)
    if m:
        avg_util = float(m.group(1))

    if proc.returncode != 0:
        tail = (stderr or stdout)[-1200:]
        log(f"FAIL {label}: rc={proc.returncode} ({elapsed}s)")
        log(f"  stderr/stdout tail: {tail.strip()[-600:]}")
        return {"returncode": proc.returncode,
                "error": tail.strip()[-1200:] or "nonzero return code",
                "elapsed_s": elapsed, "avg_utility": avg_util}

    log(f"OK   {label}: rc=0 ({elapsed}s)" + (f", avg_utility={avg_util}%" if avg_util is not None else ""))
    return {"returncode": 0, "error": None, "elapsed_s": elapsed, "avg_utility": avg_util}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def build_subset(suites: list[str], n_user: int, n_inj: int) -> dict:
    """Build the stratified subset, clamping to each suite's population and
    recording the clamp (no silent caps)."""
    subset = {}
    for s in suites:
        pop = SUITE_POP[s]
        u = min(n_user, pop["user"])
        i = min(n_inj, pop["injection"])
        subset[s] = {
            "user_tasks": task_ids("user_task", u),
            "injection_tasks": task_ids("injection_task", i),
            "user_requested": n_user,
            "user_population": pop["user"],
            "user_clamped": u < n_user,
            "injection_requested": n_inj,
            "injection_population": pop["injection"],
            "injection_clamped": i < n_inj,
        }
    return subset


def main() -> int:
    ap = argparse.ArgumentParser(description="E7 AgentDojo run driver (guard on/off).")
    ap.add_argument("--model", default=None,
                    help="Agent model-id (default: MODEL= from scripts/e7/SETUP.md).")
    ap.add_argument("--suites", nargs="+", default=ALL_SUITES, choices=ALL_SUITES,
                    help="Suites to run (default: all 4).")
    ap.add_argument("--user-tasks-per-suite", type=int, default=5,
                    help="user_task_0..N-1 per suite (clamped to population).")
    ap.add_argument("--injection-tasks-per-suite", type=int, default=2,
                    help="injection_task_0..M-1 per suite for the attack condition (clamped).")
    ap.add_argument("--guards", nargs="+", default=["off", "on"], choices=["off", "on"],
                    help="Guard conditions to run (default: off on).")
    ap.add_argument("--smoke", action="store_true",
                    help="Convenience: banking only, 1 user task, 1 injection task.")
    args = ap.parse_args()

    if args.smoke:
        suites = ["banking"]
        n_user, n_inj = 1, 1
    else:
        suites = args.suites
        n_user, n_inj = args.user_tasks_per_suite, args.injection_tasks_per_suite

    model = args.model or read_setup_model()
    subset = build_subset(suites, n_user, n_inj)

    log(f"model={model}")
    log(f"suites={suites}  user/suite={n_user}  injection/suite={n_inj}  guards={args.guards}")
    for s in suites:
        cfg = subset[s]
        clamp = []
        if cfg["user_clamped"]:
            clamp.append(f"user clamped {n_user}->{len(cfg['user_tasks'])}")
        if cfg["injection_clamped"]:
            clamp.append(f"injection clamped {n_inj}->{len(cfg['injection_tasks'])}")
        log(f"  {s}: {len(cfg['user_tasks'])} user, {len(cfg['injection_tasks'])} injection"
            + (f"  [{'; '.join(clamp)}]" if clamp else ""))

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "experiment": "E7-agentdojo",
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "smoke": args.smoke,
        "suites": suites,
        "attack": ATTACK,
        "guards": args.guards,
        "ports": {"off": PORT_OFF, "on": PORT_ON},
        "chains": {s: chain_for(s) for s in suites},
        "subset": subset,
        "logdirs": {g: str((REPO_ROOT / "runs" / "e7" / g)) for g in args.guards},
        "result_json_layout": "<logdir>/<pipeline>/<suite>/<user_task>/<attack_or_none>/<injection_or_none>.json",
        "runs": [],  # one entry per (suite, guard, condition)
    }

    def persist() -> None:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    persist()

    for guard in args.guards:
        port = PORT_ON if guard == "on" else PORT_OFF
        if guard == "off":
            if not http_ok(f"http://localhost:{PORT_OFF}/api/tags"):
                log(f"WARNING: Ollama not reachable at :{PORT_OFF}/api/tags (guard off may fail)")
            else:
                log(f"Ollama reachable at :{PORT_OFF} (guard off)")

        logdir = REPO_ROOT / "runs" / "e7" / guard
        for suite in suites:
            cfg = subset[suite]
            # Guard ON: each suite gets its own per-suite domain-scope chain, so
            # restart the proxy per suite with that chain as the default.
            chain = chain_for(suite) if guard == "on" else None
            proxy = None
            try:
                if guard == "on":
                    proxy = start_proxy(chain)[0]
                for condition in ("benign", "attack"):
                    res = run_case(model, suite, guard, port, condition,
                                   cfg["user_tasks"], cfg["injection_tasks"], logdir)
                    manifest["runs"].append({
                        "suite": suite, "guard": guard, "condition": condition,
                        "port": port, "chain": chain,
                        "user_tasks": cfg["user_tasks"],
                        "injection_tasks": cfg["injection_tasks"] if condition == "attack" else [],
                        "logdir": str(logdir),
                        **res,
                    })
                    persist()  # incremental — manifest survives a crash
            finally:
                stop_proxy(proxy)

    # Summary
    n_total = len(manifest["runs"])
    n_fail = sum(1 for r in manifest["runs"] if r["returncode"] != 0)
    persist()
    log(f"DONE: {n_total} (suite,guard,condition) runs, {n_fail} failed.")
    log(f"manifest -> {MANIFEST_PATH}")
    return 1 if n_fail == n_total and n_total > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
