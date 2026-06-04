#!/usr/bin/env python3
"""Generate the paper's LaTeX result tables + inline numbers from benchmark JSON.

Reads bench-out/{exp1,exp2,healthcare}/bench.json and bench-out/baselines.json;
writes paper/tables/*.tex and paper/numbers.tex. All numbers are measured.
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, "paper/tables")
os.makedirs(OUTDIR, exist_ok=True)


def load(path):
    try:
        with open(os.path.join(BASE, path)) as f:
            return json.load(f)
    except Exception:
        return None


def fmt(x, d=3):
    try:
        return f"{x:.{d}f}"
    except Exception:
        return "--"


def chain_rows(bench):
    rows = {}
    if not bench:
        return rows
    for r in bench.get("reports", []):
        rows[r["chain"]] = r["overall"]
    return rows


QFIRE_LABEL = [
    ("bench_regex", r"Regex denylist (lexical)"),
    ("bench_aho", r"Aho-Corasick keywords"),
    ("bench_entropy", r"Entropy heuristic"),
    ("bench_deberta", r"DeBERTa-v3 (ONNX, ours)"),
    ("bench_hybrid", r"\textbf{QFIRE hybrid}"),
    ("bench_hybrid_norm", r"\textbf{QFIRE hybrid + de-obf}"),
]
BASELINE_LABEL = [
    ("deberta-v3-injection", r"DeBERTa-v3 (protectai, PyTorch)"),
    ("promptguard-2-86m", r"PromptGuard-2 86M (Meta)"),
    ("prompt-injection-sentinel", r"Sentinel (qualifire, ModernBERT)"),
    ("deberta-70m-int8", r"DeBERTa-70M (hlyn-labs, INT8 ONNX)"),
    ("promptguard-2-22m", r"PromptGuard-2 22M (Meta)"),
    ("llm-judge-3.1-8b", r"LLM-judge only (llama3.1:8B)"),
]


def main():
    exp1 = load("bench-out/exp1/bench.json")
    base = load("bench-out/baselines.json")
    # Fold the E3 head-to-head baselines (Sentinel + bare LLM-judge) into the same
    # lookup so BASELINE_LABEL rows render without overwriting the main file.
    for extra in ("bench-out/baselines_e3_injection.json",
                  "bench-out/baselines_e10_injection.json"):
        ex = load(extra)
        if base and ex and ex.get("results"):
            base.setdefault("results", {}).update(
                {k: v for k, v in ex["results"].items() if "error" not in v})
    rows = chain_rows(exp1)

    # Table 1: main head-to-head
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
         r"System & Prec. & Rec. & F1 & FPR & AUC & p95 (ms) \\", r"\midrule"]
    if base:
        for key, lab in BASELINE_LABEL:
            r = base.get("results", {}).get(key)
            if not r or "error" in r:
                L.append(f"{lab} & \\multicolumn{{6}}{{c}}{{(unavailable)}} \\\\")
            else:
                lat = r.get("latency_ms", {})
                L.append(f"{lab} & {fmt(r['precision'])} & {fmt(r['recall'])} & {fmt(r['f1'])} "
                         f"& {fmt(r['fpr'])} & -- & {fmt(lat.get('p95',0),1)} \\\\")
        L.append(r"\midrule")
    for key, lab in QFIRE_LABEL:
        m = rows.get(key)
        if not m:
            continue
        L.append(f"{lab} & {fmt(m['precision'])} & {fmt(m['recall'])} & {fmt(m['f1'])} "
                 f"& {fmt(m['fpr'])} & {fmt(m['auc'])} & {fmt(m['p95_ms'],2)} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    open(os.path.join(OUTDIR, "main.tex"), "w").write("\n".join(L) + "\n")

    # Table 2: accuracy + Wilson CI
    L = [r"\begin{tabular}{lrl}", r"\toprule",
         r"System & Accuracy & 95\% Wilson CI \\", r"\midrule"]
    for key, lab in QFIRE_LABEL:
        m = rows.get(key)
        if not m:
            continue
        ci = f"[{fmt(m['acc_ci_low'])}, {fmt(m['acc_ci_high'])}]"
        L.append(f"{lab} & {fmt(m['accuracy'])} & {ci} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    open(os.path.join(OUTDIR, "accuracy_ci.tex"), "w").write("\n".join(L) + "\n")

    # Table 3: de-obfuscation (exp2)
    r2 = chain_rows(load("bench-out/exp2/bench.json"))
    if r2:
        L = [r"\begin{tabular}{lrrr}", r"\toprule",
             r"Configuration & Recall & F1 & $\Delta$F1 \\", r"\midrule"]
        base_f1 = r2.get("bench_hybrid", {}).get("f1")
        for key, lab in [("bench_hybrid", "Hybrid (no normalization)"),
                         ("bench_hybrid_norm", "Hybrid + de-obfuscation")]:
            m = r2.get(key)
            if not m:
                continue
            d = "" if base_f1 is None else fmt(m["f1"] - base_f1)
            L.append(f"{lab} & {fmt(m['recall'])} & {fmt(m['f1'])} & {d} \\\\")
        L += [r"\bottomrule", r"\end{tabular}"]
        open(os.path.join(OUTDIR, "deobf.tex"), "w").write("\n".join(L) + "\n")

    # Table 4: healthcare
    rhc = chain_rows(load("bench-out/healthcare/bench.json"))
    if rhc:
        L = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Chain & Block rate & FPR & Precision & Recall \\", r"\midrule"]
        for key, m in rhc.items():
            ek = key.replace("_", r"\_")
            L.append(f"\\texttt{{{ek}}} & {fmt(m['block_rate'])} & {fmt(m['fpr'])} "
                     f"& {fmt(m['precision'])} & {fmt(m['recall'])} \\\\")
        L += [r"\bottomrule", r"\end{tabular}"]
        open(os.path.join(OUTDIR, "healthcare.tex"), "w").write("\n".join(L) + "\n")

    # Inline numbers macros
    nums = []
    h = rows.get("bench_hybrid_norm") or rows.get("bench_hybrid")
    if h:
        nums.append(r"\newcommand{\qfiref}{%s}" % fmt(h["f1"]))
        nums.append(r"\newcommand{\qfirerecall}{%s}" % fmt(h["recall"]))
        nums.append(r"\newcommand{\qfireprec}{%s}" % fmt(h["precision"]))
    d = rows.get("bench_deberta")
    if d:
        nums.append(r"\newcommand{\debertaf}{%s}" % fmt(d["f1"]))
        nums.append(r"\newcommand{\debertap}{%s}" % fmt(d["p95_ms"], 3))
    if base and base.get("results", {}).get("deberta-v3-injection", {}).get("latency_ms"):
        nums.append(r"\newcommand{\pyp}{%s}" %
                    fmt(base["results"]["deberta-v3-injection"]["latency_ms"]["p95"], 1))
    open(os.path.join(BASE, "paper/numbers.tex"), "w").write("\n".join(nums) + "\n")

    print("Wrote tables + numbers.tex")
    print("TABLES_DONE")


if __name__ == "__main__":
    main()
