#!/usr/bin/env python3
"""Tabulate the judge memory-vs-J frontier.

Walks a results root with one subdir per (model, quant) config:

    <root>/<config>/meta.json        # written by the Modal runner (see below)
    <root>/<config>/t1/bench.json    # qfire bench output, standard tier
    <root>/<config>/t2/bench.json    # qfire bench output, hard tier

`meta.json` contract (host-measured fields the Rust harness cannot know):
    {
      "label": "Llama 3.2 1B", "family": "Llama", "params_b": 1.0,
      "quant": "Q4_K_M", "model_tag": "llama3.2:1b",
      "peak_vram_mb": 2310.0, "weights_mb": 900.0
    }

Youden's J = TPR - FPR = recall - fpr, read from each tier's `overall` metrics.
Writes <root>/results.json and <root>/results.md.

Usage: python3 scripts/analyze_judge_frontier.py [results-root]
       (default root: bench-out/judge_frontier)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "bench-out/judge_frontier")
TIERS = ["t1", "t2"]
TIER_LABEL = {"t1": "T1 standard", "t2": "T2 hard"}


def load_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def tier_metrics(config_dir, tier):
    d = load_json(os.path.join(config_dir, tier, "bench.json"))
    if not d or not d.get("reports"):
        return None
    m = d["reports"][0]["overall"]
    recall = m.get("recall", 0.0)   # TPR
    fpr = m.get("fpr", 0.0)
    return {
        "tpr": recall,
        "fpr": fpr,
        "j": recall - fpr,          # Youden's J
        "f1": m.get("f1", 0.0),
        "auc": m.get("auc", 0.0),
        "p50_ms": m.get("p50_ms", 0.0),
        "attacks": m.get("attacks", 0),
        "benign": m.get("benign", 0),
    }


def discover(results_root):
    rows = []
    if not os.path.isdir(results_root):
        return rows
    for name in sorted(os.listdir(results_root)):
        cfg = os.path.join(results_root, name)
        if not os.path.isdir(cfg):
            continue
        meta = load_json(os.path.join(cfg, "meta.json")) or {}
        row = {"config": name, "meta": meta, "tiers": {}}
        for t in TIERS:
            tm = tier_metrics(cfg, t)
            if tm:
                row["tiers"][t] = tm
        if row["tiers"]:
            rows.append(row)
    # Order by measured memory, then params (helps the frontier read top-to-bottom).
    rows.sort(key=lambda r: (r["meta"].get("peak_vram_mb") or 1e12,
                             r["meta"].get("params_b") or 1e12))
    return rows


def fmt(x, nd=3):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else "-"


def write_markdown(rows, path):
    lines = ["# Judge memory-vs-J frontier", ""]
    lines.append(f"Configs: {len(rows)}. Metric: Youden's J = TPR - FPR. "
                 "Memory = measured peak VRAM (GB) of the loaded judge model.")
    lines.append("")
    for t in TIERS:
        lines.append(f"## {TIER_LABEL[t]}")
        lines.append("")
        lines.append("| Model | Quant | Params (B) | Peak VRAM (GB) | TPR | FPR | **J** | F1 | AUC | p50 (s) |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            tm = r["tiers"].get(t)
            if not tm:
                continue
            m = r["meta"]
            vram = m.get("peak_vram_mb")
            vram_gb = fmt(vram / 1024.0, 2) if vram else "-"
            lines.append(
                f"| {m.get('label', r['config'])} | {m.get('quant', '-')} | "
                f"{fmt(m.get('params_b'), 1)} | {vram_gb} | "
                f"{fmt(tm['tpr'])} | {fmt(tm['fpr'])} | **{fmt(tm['j'])}** | "
                f"{fmt(tm['f1'])} | {fmt(tm['auc'])} | {fmt(tm['p50_ms'] / 1000.0, 2)} |"
            )
        lines.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    rows = discover(RESULTS)
    if not rows:
        print(f"no configs found under {RESULTS}", file=sys.stderr)
        sys.exit(1)
    out_json = os.path.join(RESULTS, "results.json")
    out_md = os.path.join(RESULTS, "results.md")
    with open(out_json, "w") as fh:
        json.dump(rows, fh, indent=2)
    write_markdown(rows, out_md)
    print(f"wrote {out_json}\nwrote {out_md}  ({len(rows)} configs)")
    # Console summary.
    for r in rows:
        m = r["meta"]
        js = "  ".join(f"{t}:J={fmt(r['tiers'][t]['j'], 2)}" for t in TIERS if t in r["tiers"])
        vram = m.get("peak_vram_mb")
        vram_s = f"{vram/1024.0:.2f}GB" if vram else "?GB"
        print(f"  {m.get('label', r['config']):<22} {vram_s:>8}  {js}")


if __name__ == "__main__":
    main()
