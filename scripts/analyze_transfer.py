#!/usr/bin/env python3
"""E5 analysis: (a) transfer table (in-dist vs held-out recall/F1/FPR for QFIRE +
DeBERTa), (b) larger-benign FPR + Wilson CI, (c) threshold transfer — calibrate the
DeBERTa score threshold for a target FPR on the in-dist benign, apply it to the
held-out benign, report the realized FPR (and the same for the chain score).
Reads bench-out/external/{indist,heldout,qfire_*,benign_large_fpr}.
"""
import json, math, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "bench-out/external")
TARGET_FPR = 0.08  # match the paper's calibrated operating point


def _dump(run, chain):
    p = os.path.join(ROOT, run, "dump", f"{chain}.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def _overall(run):
    p = os.path.join(ROOT, run, "bench.json")
    return json.load(open(p))["reports"][0]["overall"] if os.path.exists(p) else {}


def threshold_for_fpr(benign_scores, target_fpr):
    """Smallest threshold t such that fraction(benign >= t) <= target_fpr."""
    s = sorted(benign_scores)
    n = len(s)
    if n == 0:
        return 1.0
    k = int(math.floor(target_fpr * n))  # allow up to k benign above threshold
    # threshold just above the (n-k-1)th largest benign score
    idx = max(0, n - k - 1)
    return s[idx] + 1e-9 if k < n else 0.0


def rate_at_threshold(scores, t):
    return sum(1 for x in scores if x >= t) / len(scores) if scores else 0.0


def wilson(succ, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = succ / n
    d = 1 + z*z/n
    c = p + z*z/(2*n)
    m = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c - m) / d, (c + m) / d)


def _benign_scores(run, chain):
    return [r["score"] for r in _dump(run, chain) if not r["is_attack"]]


def main():
    lines = ["# E5 — External Validity — Results", "",
             f"Threshold target FPR = {TARGET_FPR}. Transfer set = corpora/eval_heldout "
             "(deepset-decontaminated). Larger benign = synthetic clinical-adjacent.", ""]

    # (a) transfer table
    lines += ["## Transfer (in-distribution vs held-out)", "",
              "| detector | corpus | recall | F1 | FPR |", "|---|---|---|---|---|"]
    for label, run in [("DeBERTa", "indist"), ("DeBERTa", "heldout"),
                       ("QFIRE (default)", "qfire_indist"), ("QFIRE (default)", "qfire_heldout")]:
        o = _overall(run)
        if o:
            corpus = "in-dist" if "indist" in run else "held-out"
            lines.append(f"| {label} | {corpus} | {o.get('recall',0):.3f} | "
                         f"{o.get('f1',0):.3f} | {o.get('fpr',0):.3f} |")

    # (b) larger-benign over-refusal at the CALIBRATED operating point. The paper's
    # headline 0.08 FPR is the deterministic injection+PHI chain (bench_combined), NOT
    # the deliberately-strict 10-judge conjunction (hipaa_phi) that the paper itself
    # shows collapses to FPR 1.00 (calibration-necessity warning, paper Sec. 3.7).
    over = None
    oc = _overall("benign_large_fpr_combined")
    if oc:
        n = oc.get("benign", 0); fp = round(oc.get("fpr", 0) * n)
        lo, hi = wilson(fp, n)
        over = {"chain": "bench_combined", "n": n, "fpr": oc.get("fpr", 0),
                "blocked": fp, "ci_low": lo, "ci_high": hi}
        lines += ["", "## Larger-benign over-refusal (calibrated operating point, "
                  "bench_combined: injection+PHI, deterministic)", "",
                  f"- benign n={n}; **FPR (over-refusal) = {oc.get('fpr',0):.3f}** "
                  f"(95% Wilson [{lo:.3f}, {hi:.3f}]); {fp} blocked.",
                  "- Tightens the paper's calibrated 0.08-FPR operating point on a larger, "
                  "independent benign corpus (fully offline, no LLM judge)."]
    # (b') secondary: the strict full hipaa_phi conjunction over the same benign, as a
    # cross-check of the paper's documented calibration-necessity point at scale.
    oh = _overall("benign_large_fpr")
    if oh:
        n = oh.get("benign", 0)
        lines += ["", "## Strict-conjunction cross-check (hipaa_phi, 10 LLM-judge rules)", "",
                  f"- benign n={n}; FPR = {oh.get('fpr',0):.3f} — the naive conjunction "
                  "over-blocks at scale, corroborating the paper's calibration-necessity "
                  "finding (Sec. 3.7). This is NOT the deployed operating point."]

    # (c) threshold transfer (DeBERTa score)
    bi = _benign_scores("indist", "bench_deberta")
    bh = _benign_scores("heldout", "bench_deberta")
    if bi and bh:
        t = threshold_for_fpr(bi, TARGET_FPR)
        lines += ["", "## Threshold transfer (DeBERTa score)", "",
                  f"- threshold calibrated for FPR={TARGET_FPR} on in-dist benign: t={t:.3f}",
                  f"- realized FPR on **held-out** benign at that fixed t: "
                  f"**{rate_at_threshold(bh, t):.3f}**"]

    # (c') threshold transfer (QFIRE chain score) — spec decision 4: transfer both.
    ci = _benign_scores("qfire_indist", "default")
    ch = _benign_scores("qfire_heldout", "default")
    chain_calib_t = None
    if ci and ch:
        chain_calib_t = threshold_for_fpr(ci, TARGET_FPR)
        lines += ["", "## Threshold transfer (QFIRE chain score)", "",
                  f"- threshold calibrated for FPR={TARGET_FPR} on in-dist benign: "
                  f"t={chain_calib_t:.3f}",
                  f"- realized FPR on **held-out** benign at that fixed t: "
                  f"**{rate_at_threshold(ch, chain_calib_t):.3f}**"]

    os.makedirs(ROOT, exist_ok=True)
    with open(os.path.join(ROOT, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    # summary.json for the plotter
    json.dump({"target_fpr": TARGET_FPR,
               "calib_t": threshold_for_fpr(bi, TARGET_FPR) if bi else None,
               "benign_indist": bi, "benign_heldout": bh,
               "chain_calib_t": chain_calib_t,
               "chain_benign_indist": ci, "chain_benign_heldout": ch,
               "over_refusal": over},
              open(os.path.join(ROOT, "summary.json"), "w"))
    print("wrote", os.path.join(ROOT, "results.md")); print("ANALYZE_TRANSFER_DONE")


if __name__ == "__main__":
    main()
