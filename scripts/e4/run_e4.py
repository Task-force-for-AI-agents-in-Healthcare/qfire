#!/usr/bin/env python3
"""E4 harness: run each episode under {guard off, guard on} with a real llama3.1:8b
ReAct agent; write one JSON line per (episode, condition) with the tool-call log and
outcome flags. Offline. Usage: python3 scripts/e4/run_e4.py [--limit N] [--model llama3.1:8b]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sandbox as sb, agent as ag, episodes as ep

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(BASE, "bench-out/e4"); os.makedirs(OUT, exist_ok=True)


def one(episode, guard, llm):
    w = sb.World()
    res = ag.run_episode(task=episode["task"], world=w, llm=llm, guard=guard,
                         injected=episode.get("injected"))
    calls = [{"tool": c.tool, "args": c.args, "harmful": c.harmful} for c in w.log]
    benign_complete = (episode["kind"] == "benign"
                       and any(c["tool"] == episode.get("expected_tool") for c in calls)
                       and not w.reached_harm())
    return {"id": episode["id"], "kind": episode["kind"],
            "vector": episode.get("vector"), "guard": guard is not None,
            "harm": w.reached_harm(), "benign_complete": benign_complete,
            "refused": res.get("refused", False),
            "blocked_inputs": res["blocked_inputs"], "calls": calls}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="llama3.1:8b")
    args = ap.parse_args()
    eps = ep.build()
    if args.limit:
        eps = eps[: args.limit]
    llm = ag.ollama(args.model, seed=42)
    guard = ag.QfireGuard(chain="bench_combined")
    rows = []
    for i, e in enumerate(eps):
        for g in (None, guard):           # OFF then ON
            rows.append(one(e, g, llm))
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(eps)} episodes", flush=True)
    with open(os.path.join(OUT, "runs.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} rows -> {OUT}/runs.jsonl")
    print("E4_RUN_DONE")


if __name__ == "__main__":
    main()
