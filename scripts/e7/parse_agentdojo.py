#!/usr/bin/env python3
"""E7 AgentDojo parser.

Turns AgentDojo per-case run logs (written by ``scripts/e7/run_agentdojo.py``)
into the three native AgentDojo metrics, per suite and pooled, for guard
``off``/``on``, each with a Wilson 95% confidence interval:

  * **Benign Utility**       = fraction of user tasks solved in the *no-attack*
                               run (attack ``none``).
  * **Utility Under Attack** = fraction of user tasks solved in the *attack* run
                               (attack ``important_instructions``).
  * **Targeted ASR**         = fraction of security checks that are ``False``
                               (i.e. the attacker goal WAS achieved). In
                               AgentDojo, ``security == True`` means the attack
                               was CONTAINED, so ASR = 1 - mean(security).

Layout consumed (per case)::

    runs/e7/<guard>/<pipeline>/<suite>/<user_task>/<attack_or_none>/<injection_or_none>.json

Verdicts are read via AgentDojo's own loader (``agentdojo.benchmark`` —
``load_task_results``), which reconstructs a ``TaskResults`` carrying the
``utility`` / ``security`` booleans for each case.

NOTE on the API: the spec referenced ``load_suite_results`` returning a
``SuiteResults`` TypedDict. In the pinned agentdojo (0.1.35) the real signature
is::

    load_suite_results(suite_name, pipeline_name, attack_name,
                       logdir=Path("../runs"), benchmark_version="v1.2.2")
        -> (results_without_injections, results_with_injections)

i.e. it returns a *tuple of dicts* keyed by ``(user_task_id, injection_task_id)``
with ``TaskResults`` values (not bare bools), and it iterates over the FULL
suite population — so it raises ``FileNotFoundError`` on a *subset* run like
ours. We therefore drive AgentDojo's ``load_task_results`` over exactly the
cases present on disk (same module, same recompute path), which is robust to the
stratified subset the driver produces.

Run as a script to eyeball a compact table::

    .venv-e7/bin/python scripts/e7/parse_agentdojo.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Pure stats helpers (no AgentDojo dependency) — unit-tested directly.
# ---------------------------------------------------------------------------
ATTACK = "important_instructions"


def wilson(succ: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI. Copied from scripts/e4/analyze_e4.py."""
    if n == 0:
        return (0.0, 0.0)
    p = succ / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def summarize(n_benign_solved: int, n_benign: int,
              n_attack_solved: int, n_sec_contained: int, n_security: int) -> dict:
    """Pure: turn raw counts into rates + Wilson CIs.

    Args:
        n_benign_solved: user tasks solved in the no-attack run.
        n_benign:        total user tasks in the no-attack run.
        n_attack_solved: user tasks solved in the attack run.
        n_sec_contained: security checks that PASSED (attack contained).
        n_security:      total security checks in the attack run.

    ``n_security`` is also the denominator for Utility-Under-Attack here only if
    attack-run user-task evaluation has the same count; we keep them separate
    and use ``n_security`` for both the UUA and ASR denominators since the
    attack run produces one (user_task, injection_task) case per security
    check. Targeted ASR = fraction of security checks that are False =
    (n_security - n_sec_contained) / n_security.
    """
    benign_utility = (n_benign_solved / n_benign) if n_benign else 0.0
    uua = (n_attack_solved / n_security) if n_security else 0.0
    n_breached = n_security - n_sec_contained
    targeted_asr = (n_breached / n_security) if n_security else 0.0

    b_lo, b_hi = wilson(n_benign_solved, n_benign)
    u_lo, u_hi = wilson(n_attack_solved, n_security)
    a_lo, a_hi = wilson(n_breached, n_security)

    return {
        "benign_utility": benign_utility,
        "benign_utility_ci": [b_lo, b_hi],
        "n_benign": n_benign,
        "utility_under_attack": uua,
        "uua_ci": [u_lo, u_hi],
        "targeted_asr": targeted_asr,
        "targeted_asr_ci": [a_lo, a_hi],
        "n_security": n_security,
    }


# ---------------------------------------------------------------------------
# Filesystem discovery + AgentDojo loader.
# ---------------------------------------------------------------------------
def _discover_pipeline(guard_dir: Path) -> str | None:
    """The single subdir under runs/e7/<guard> is the pipeline_name."""
    subdirs = [d for d in guard_dir.iterdir() if d.is_dir()]
    if not subdirs:
        return None
    if len(subdirs) > 1:
        # Be deterministic but loud: prefer the one that looks like a pipeline
        # (has suite subdirs). Fall back to the first sorted.
        subdirs.sort(key=lambda d: d.name)
    return subdirs[0].name


def _discover_benchmark_version(pipeline_dir: Path) -> str:
    """Read benchmark_version from any per-case JSON under the pipeline dir."""
    for jf in pipeline_dir.rglob("*.json"):
        try:
            ver = json.loads(jf.read_text()).get("benchmark_version")
        except (OSError, json.JSONDecodeError):
            continue
        if ver:
            return ver
    return "v1.2.2"  # agentdojo default


def _present_suites(pipeline_dir: Path) -> list[str]:
    return sorted(d.name for d in pipeline_dir.iterdir() if d.is_dir())


def _user_task_dirs(suite_dir: Path) -> list[str]:
    """user_task_* directories actually present (skip injection_task_* probe
    dirs the driver writes for FP checks)."""
    return sorted(
        d.name for d in suite_dir.iterdir()
        if d.is_dir() and d.name.startswith("user_task_")
    )


def _count_suite(pipeline: str, suite: str, suite_dir: Path,
                 logdir: Path, benchmark_version: str, note) -> tuple[int, int, int, int, int]:
    """Return (n_benign_solved, n_benign, n_attack_solved, n_sec_contained,
    n_security) for one (suite, guard), counting only cases present on disk via
    AgentDojo's own load_task_results."""
    from agentdojo.benchmark import load_task_results

    n_benign_solved = n_benign = 0
    n_attack_solved = n_sec_contained = n_security = 0

    for ut in _user_task_dirs(suite_dir):
        # Benign (no-attack) case.
        benign_json = suite_dir / ut / "none" / "none.json"
        if benign_json.exists():
            try:
                r = load_task_results(pipeline, suite, ut, "none", "none", logdir)
                n_benign += 1
                n_benign_solved += int(bool(r.utility))
            except Exception as e:  # pragma: no cover - defensive
                note(f"skip benign {suite}/{ut}: {e}")

        # Attack cases: one per injection_task present under the attack dir.
        attack_dir = suite_dir / ut / ATTACK
        if attack_dir.is_dir():
            for inj_json in sorted(attack_dir.glob("*.json")):
                it = inj_json.stem
                try:
                    r = load_task_results(pipeline, suite, ut, ATTACK, it, logdir)
                except Exception as e:  # pragma: no cover - defensive
                    note(f"skip attack {suite}/{ut}/{it}: {e}")
                    continue
                n_security += 1
                n_attack_solved += int(bool(r.utility))
                n_sec_contained += int(bool(r.security))

    return n_benign_solved, n_benign, n_attack_solved, n_sec_contained, n_security


def aggregate(runs_dir: str = "runs/e7") -> dict:
    """Per-guard, per-suite + pooled metrics with Wilson CIs.

    See module docstring for the metric definitions. Pooled = counts summed
    across suites (NOT mean-of-means). Robust to a suite/condition being
    absent (skipped with a logged note rather than crashing).
    """
    runs = Path(runs_dir)
    out: dict = {}

    def note(msg: str) -> None:
        print(f"[parse_agentdojo] {msg}", flush=True)

    for guard in ("off", "on"):
        guard_dir = runs / guard
        if not guard_dir.is_dir():
            continue

        pipeline = _discover_pipeline(guard_dir)
        if pipeline is None:
            note(f"no pipeline dir under {guard_dir}; skipping guard={guard}")
            continue
        pipeline_dir = guard_dir / pipeline
        benchmark_version = _discover_benchmark_version(pipeline_dir)

        per_suite: dict = {}
        # Pooled accumulators.
        p_bs = p_bn = p_as = p_sc = p_sn = 0

        for suite in _present_suites(pipeline_dir):
            suite_dir = pipeline_dir / suite
            if not _user_task_dirs(suite_dir):
                note(f"no user_task dirs in {guard}/{suite}; skipping")
                continue
            try:
                bs, bn, as_, sc, sn = _count_suite(
                    pipeline, suite, suite_dir, guard_dir, benchmark_version, note)
            except Exception as e:  # pragma: no cover - defensive
                note(f"skip suite {guard}/{suite}: {e}")
                continue
            per_suite[suite] = summarize(bs, bn, as_, sc, sn)
            p_bs += bs; p_bn += bn; p_as += as_; p_sc += sc; p_sn += sn

        out[guard] = {
            "pipeline": pipeline,
            "benchmark_version": benchmark_version,
            "per_suite": per_suite,
            "pooled": summarize(p_bs, p_bn, p_as, p_sc, p_sn),
        }

    return out


# ---------------------------------------------------------------------------
# __main__ : pretty-print a compact table (writes nothing).
# ---------------------------------------------------------------------------
def _fmt_row(name: str, b: dict) -> str:
    return (
        f"  {name:<12} "
        f"benign={b['benign_utility']:.3f} [{b['benign_utility_ci'][0]:.3f},{b['benign_utility_ci'][1]:.3f}] (n={b['n_benign']})  "
        f"UUA={b['utility_under_attack']:.3f} [{b['uua_ci'][0]:.3f},{b['uua_ci'][1]:.3f}]  "
        f"ASR={b['targeted_asr']:.3f} [{b['targeted_asr_ci'][0]:.3f},{b['targeted_asr_ci'][1]:.3f}] (n={b['n_security']})"
    )


def main() -> int:
    out = aggregate()
    if not out:
        print("No runs found under runs/e7/{off,on}.")
        return 0
    for guard in ("off", "on"):
        if guard not in out:
            print(f"\n=== guard {guard.upper()}: (no runs) ===")
            continue
        g = out[guard]
        print(f"\n=== guard {guard.upper()}  "
              f"(pipeline={g['pipeline']}, benchmark_version={g['benchmark_version']}) ===")
        for suite, b in g["per_suite"].items():
            print(_fmt_row(suite, b))
        print(_fmt_row("POOLED", g["pooled"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
