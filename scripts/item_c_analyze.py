#!/usr/bin/env python3
"""Item C / expert validation: analyze filled reviewer forms -> stats + LaTeX Table 6.

Reads the sealed master key and the filled per-reviewer CSVs, then computes, per the §4
analysis plan:
  - expert consensus label (majority of Yes/No; Unsure dropped; ties reported)
  - expert--benchmark label agreement, overall and per category
  - inter-rater reliability: Fleiss' kappa, mean pairwise Cohen's kappa, Gwet's AC1
  - realism: mean / SD / % rated >= 3 ("plausible-or-better"), overall and per category
  - disagreement audit (every item where consensus != benchmark label)
  - equity cross-tab: are sensitive-topic benign prompts systematically rated "refuse"?
  - the QFIRE gold-seed sanity-check summary (from item_c_score.py), folded in

Emits LaTeX for Table~\\ref{tab:expertval}. If the reviewer forms are still empty (no
ratings collected yet), it prints the metrics it WOULD compute and writes a placeholder
table with XX cells, so the paper scaffold is ready before reviewers finish.

Run modes:
  python3 scripts/item_c_analyze.py            # analyze real forms (or placeholder if empty)
  python3 scripts/item_c_analyze.py --selftest # synthesize ratings, verify the math, PASS/FAIL
"""
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "corpora/expert_validation")
FORMS = os.path.join(DATA, "forms")
OUT = os.path.join(HERE, "bench-out/expert_validation")
N_REVIEWERS = 5

# study-category display order + label
CAT_ORDER = ["bulk_export", "phi_exfil", "phi_smuggle", "reidentification",
             "cross_patient", "clinical_advice", "benign"]
CAT_LABEL = {
    "bulk_export": "Bulk export", "phi_exfil": "PHI exfiltration",
    "phi_smuggle": "PHI smuggling", "reidentification": "Re-identification",
    "cross_patient": "Cross-patient access", "clinical_advice": "Out-of-scope advice",
    "benign": "Benign clinical",
}
SENSITIVE = {  # equity cross-tab keyword tags
    "mental_health": ["mental health", "psychiatr", "depress", "suicide", "crisis hotline",
                      "therapy", "counsel"],
    "reproductive": ["pregnan", "abortion", "contracept", "reproductive", "obstetric"],
    "substance_use": ["substance", "addiction", "opioid", "alcohol", "rehab", "overdose"],
    "hiv": ["hiv", "aids", "antiretroviral"],
}


# ----------------------------- reliability statistics -----------------------------
def fleiss_kappa(counts):
    """counts: list over items of [n_attack, n_benign] (rater counts, equal n per item)."""
    counts = [c for c in counts if sum(c) >= 2]
    if not counts:
        return float("nan")
    N = len(counts)
    n = sum(counts[0])
    if any(sum(c) != n for c in counts):  # ragged -> fall back to per-item normalization
        n = None
    # observed agreement per item
    P = []
    for c in counts:
        ni = sum(c)
        if ni < 2:
            continue
        P.append((sum(x * x for x in c) - ni) / (ni * (ni - 1)))
    Pbar = sum(P) / len(P)
    # category marginals
    tot = sum(sum(c) for c in counts)
    pj = [sum(c[k] for c in counts) / tot for k in range(2)]
    Pe = sum(p * p for p in pj)
    return (Pbar - Pe) / (1 - Pe) if Pe < 1 else 1.0


def gwet_ac1(counts):
    """Gwet's AC1 for q=2 categories, multi-rater (Gwet 2008 generalization)."""
    counts = [c for c in counts if sum(c) >= 2]
    if not counts:
        return float("nan")
    q = 2
    P = []
    for c in counts:
        ni = sum(c)
        P.append((sum(x * x for x in c) - ni) / (ni * (ni - 1)))
    Pa = sum(P) / len(P)
    tot = sum(sum(c) for c in counts)
    pj = [sum(c[k] for c in counts) / tot for k in range(q)]
    Pe = sum(p * (1 - p) for p in pj) / (q - 1)
    return (Pa - Pe) / (1 - Pe) if Pe < 1 else 1.0


def cohen_kappa(a, b):
    """a, b: aligned label lists (strings); ignores positions where either is None."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return float("nan")
    n = len(pairs)
    labels = sorted({x for p in pairs for x in p})
    po = sum(1 for x, y in pairs if x == y) / n
    pe = 0.0
    for L in labels:
        pa = sum(1 for x, _ in pairs if x == L) / n
        pb = sum(1 for _, y in pairs if y == L) / n
        pe += pa * pb
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def mean_pairwise_cohen(rater_labels):
    """rater_labels: dict reviewer -> {display_id: 'attack'|'benign'|None}. Returns mean kappa."""
    revs = sorted(rater_labels)
    ids = sorted({i for r in revs for i in rater_labels[r]})
    ks = []
    for i in range(len(revs)):
        for j in range(i + 1, len(revs)):
            a = [rater_labels[revs[i]].get(x) for x in ids]
            b = [rater_labels[revs[j]].get(x) for x in ids]
            k = cohen_kappa(a, b)
            if not math.isnan(k):
                ks.append(k)
    return sum(ks) / len(ks) if ks else float("nan")


# ----------------------------- data loading -----------------------------
def load_key():
    key = {}
    with open(os.path.join(FORMS, "master_key.csv")) as f:
        for row in csv.DictReader(f):
            key[row["display_id"]] = row
    return key


def load_ratings():
    """Returns reviewer -> {display_id: (realism:int|None, refuse:'Yes'|'No'|'Unsure'|None)}."""
    out = {}
    for r in range(1, N_REVIEWERS + 1):
        path = os.path.join(FORMS, f"reviewer_R{r}.csv")
        if not os.path.exists(path):
            continue
        d = {}
        with open(path) as f:
            for row in csv.DictReader(f):
                rl = row.get("Q1_realism", "").strip()
                rf = row.get("Q2_should_refuse", "").strip().lower()
                realism = int(rl) if rl.isdigit() else None
                refuse = {"yes": "Yes", "no": "No", "unsure": "Unsure"}.get(rf)
                d[row["display_id"]] = (realism, refuse)
        out[f"R{r}"] = d
    return out


def refuse_to_label(refuse):
    return {"Yes": "attack", "No": "benign"}.get(refuse)  # Unsure/None -> None


# ----------------------------- analysis -----------------------------
def analyze(key, ratings):
    ids = sorted(key)
    # reviewer label maps
    rlab = {rev: {i: refuse_to_label(ratings[rev].get(i, (None, None))[1]) for i in ids}
            for rev in ratings}
    realism = {rev: {i: ratings[rev].get(i, (None, None))[0] for i in ids} for rev in ratings}

    has_ratings = any(rlab[rev].get(i) is not None for rev in rlab for i in ids)

    # consensus per item
    consensus = {}
    for i in ids:
        votes = [rlab[rev][i] for rev in rlab if rlab[rev].get(i) is not None]
        if not votes:
            consensus[i] = None
            continue
        a = votes.count("attack")
        b = votes.count("benign")
        consensus[i] = "attack" if a > b else "benign" if b > a else "tie"

    def agreement(subset_ids):
        ok = tot = 0
        for i in subset_ids:
            c = consensus[i]
            if c in ("attack", "benign"):
                tot += 1
                ok += (c == key[i]["benchmark_label"])
        return (ok, tot, (ok / tot) if tot else float("nan"))

    sample_ids = [i for i in ids if key[i]["set"] == "sample"]
    gold_ids = [i for i in ids if key[i]["set"] == "gold"]

    per_cat = {}
    for cat in CAT_ORDER:
        cids = [i for i in sample_ids if key[i]["category"] == cat]
        ok, tot, frac = agreement(cids)
        # realism for this cat
        rv = [realism[rev][i] for rev in realism for i in cids if realism[rev].get(i) is not None]
        mean_r = sum(rv) / len(rv) if rv else float("nan")
        pct3 = sum(1 for x in rv if x >= 3) / len(rv) if rv else float("nan")
        per_cat[cat] = {"n": len(cids), "agree_ok": ok, "agree_tot": tot, "agree": frac,
                        "realism_mean": mean_r, "pct_ge3": pct3}

    overall = agreement(sample_ids)
    all_rv = [realism[rev][i] for rev in realism for i in sample_ids
              if realism[rev].get(i) is not None]
    overall_realism = (sum(all_rv) / len(all_rv)) if all_rv else float("nan")
    overall_sd = (math.sqrt(sum((x - overall_realism) ** 2 for x in all_rv) / len(all_rv))
                  if all_rv else float("nan"))
    overall_pct3 = (sum(1 for x in all_rv if x >= 3) / len(all_rv)) if all_rv else float("nan")

    # reliability over sample items, 2 categories
    counts = []
    for i in sample_ids:
        votes = [rlab[rev][i] for rev in rlab if rlab[rev].get(i) is not None]
        counts.append([votes.count("attack"), votes.count("benign")])
    fk = fleiss_kappa(counts)
    ac1 = gwet_ac1(counts)
    ck = mean_pairwise_cohen({rev: {i: rlab[rev][i] for i in sample_ids} for rev in rlab})

    # disagreement audit (sample)
    disagreements = [{"display_id": i, "true_id": key[i]["true_id"],
                      "category": key[i]["category"], "benchmark": key[i]["benchmark_label"],
                      "consensus": consensus[i]}
                     for i in sample_ids
                     if consensus[i] in ("attack", "benign")
                     and consensus[i] != key[i]["benchmark_label"]]
    ties = [i for i in sample_ids if consensus[i] == "tie"]

    # gold agreement (authored labels)
    gold_agree = agreement(gold_ids)

    # equity cross-tab: benign prompts (by benchmark) tagged sensitive, % consensus==attack
    equity = {}
    benign_ids = [i for i in ids if key[i]["benchmark_label"] == "benign"]
    # need prompt text; pull from forms (reviewer_R1 has prompts)
    prompts = {}
    with open(os.path.join(FORMS, "reviewer_R1.csv")) as f:
        for row in csv.DictReader(f):
            prompts[row["display_id"]] = row["prompt"].lower()
    for tag, kws in SENSITIVE.items():
        tagged = [i for i in benign_ids if any(k in prompts.get(i, "") for k in kws)]
        refused = sum(1 for i in tagged if consensus[i] == "attack")
        equity[tag] = {"n": len(tagged), "consensus_refuse": refused}

    return {
        "has_ratings": has_ratings,
        "overall": overall, "overall_realism": overall_realism, "overall_sd": overall_sd,
        "overall_pct3": overall_pct3, "per_cat": per_cat,
        "fleiss_kappa": fk, "gwet_ac1": ac1, "mean_cohen": ck,
        "gold_agree": gold_agree, "disagreements": disagreements, "ties": ties,
        "equity": equity, "n_reviewers": len(rlab),
    }


# ----------------------------- LaTeX emit -----------------------------
def fmt_pct(x):
    return f"{100 * x:.0f}\\%" if isinstance(x, float) and not math.isnan(x) else "XX\\%"


def fmt_num(x):
    return f"{x:.1f}" if isinstance(x, float) and not math.isnan(x) else "X.X"


def fmt_k(x):
    return f"{x:.2f}" if isinstance(x, float) and not math.isnan(x) else "0.XX"


def emit_latex(a):
    rows = []
    for cat in CAT_ORDER:
        c = a["per_cat"][cat]
        rows.append(f"{CAT_LABEL[cat]:<22} & {fmt_pct(c['agree'])} & "
                    f"{fmt_num(c['realism_mean'])} & {fmt_pct(c['pct_ge3'])} \\\\")
    overall_frac = a["overall"][2]
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[t]\\centering\\small\\color{{red}}
\\begin{{tabular}}{{lccc}}
\\toprule
Category & Expert--label ag. & Realism (mean/5) & \\% plausible$\\geq$3 \\\\
\\midrule
{body}
\\midrule
\\textbf{{Overall}} & \\textbf{{{fmt_pct(overall_frac)}}} & \\textbf{{{fmt_num(a['overall_realism'])}}} & \\textbf{{{fmt_pct(a['overall_pct3'])}}} \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{\\rev{{Expert validation of QFIRE-HealthBench ($n=200$; {a['n_reviewers'] or 'TBD'} reviewers,
3 clinicians + 2 HIM/privacy officers, blinded). Inter-rater Fleiss' $\\kappa={fmt_k(a['fleiss_kappa'])}$,
Gwet AC1 $={fmt_k(a['gwet_ac1'])}$, mean pairwise Cohen's $\\kappa={fmt_k(a['mean_cohen'])}$.}}}}
\\label{{tab:expertval}}
\\end{{table}}"""
    return tex


# ----------------------------- self-test -----------------------------
def selftest():
    """Synthesize ratings with a known structure and assert the math behaves."""
    import random
    key = load_key()
    rng = random.Random(123)
    # fabricate ratings: experts agree with benchmark 92% of the time, realism mostly 4
    ratings = {}
    for r in range(1, N_REVIEWERS + 1):
        d = {}
        for did, row in key.items():
            truth = row["benchmark_label"]
            flip = rng.random() < 0.08
            lab = ("benign" if truth == "attack" else "attack") if flip else truth
            refuse = "Yes" if lab == "attack" else "No"
            if rng.random() < 0.03:
                refuse = "Unsure"
            realism = rng.choice([3, 4, 4, 4, 5]) if rng.random() < 0.9 else rng.choice([1, 2])
            d[did] = (realism, refuse)
        ratings[f"R{r}"] = d
    a = analyze(key, ratings)
    checks = []
    checks.append(("has_ratings", a["has_ratings"] is True))
    checks.append(("agreement in [0.80,1.0]", 0.80 <= a["overall"][2] <= 1.0))
    checks.append(("fleiss in [-1,1]", -1 <= a["fleiss_kappa"] <= 1))
    checks.append(("gwet AC1 in [-1,1]", -1 <= a["gwet_ac1"] <= 1))
    checks.append(("cohen in [-1,1]", -1 <= a["mean_cohen"] <= 1))
    checks.append(("AC1 >= 0.5 (high agreement)", a["gwet_ac1"] >= 0.5))
    checks.append(("realism mean ~4", 3.0 <= a["overall_realism"] <= 5.0))
    checks.append(("per-cat covers 7", len(a["per_cat"]) == 7))
    # known-kappa sanity: identical raters -> kappa 1; opposite -> < 0
    ident = [[5, 0]] * 10 + [[0, 5]] * 10
    opp = [[3, 2]] * 20
    checks.append(("fleiss identical==1", abs(fleiss_kappa(ident) - 1.0) < 1e-9))
    checks.append(("cohen identical==1", abs(cohen_kappa(["a"] * 5 + ["b"] * 5,
                                                         ["a"] * 5 + ["b"] * 5) - 1.0) < 1e-9))
    checks.append(("cohen opposite<=0", cohen_kappa(["a", "a", "b", "b"],
                                                    ["b", "b", "a", "a"]) <= 0))
    tex = emit_latex(a)
    checks.append(("latex has no XX (filled)", "XX" not in tex and "X.X" not in tex))
    ok = all(p for _, p in checks)
    print("=== SELF-TEST (synthetic ratings; NOT for paper) ===")
    for name, p in checks:
        print(f"  [{'PASS' if p else 'FAIL'}] {name}")
    print(f"  synthetic overall agreement={a['overall'][2]:.3f} "
          f"fleiss={a['fleiss_kappa']:.3f} ac1={a['gwet_ac1']:.3f} cohen={a['mean_cohen']:.3f}")
    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


# ----------------------------- main -----------------------------
def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    key = load_key()
    ratings = load_ratings()
    a = analyze(key, ratings)

    os.makedirs(OUT, exist_ok=True)
    tex = emit_latex(a)
    with open(os.path.join(OUT, "table_expertval.tex"), "w") as f:
        f.write(tex + "\n")

    # fold in QFIRE gold sanity check if present
    gs = None
    gsf = os.path.join(OUT, "gold_summary.json")
    if os.path.exists(gsf):
        gs = json.load(open(gsf))

    print("=== EXPERT VALIDATION ANALYSIS ===")
    if not a["has_ratings"]:
        print("  No reviewer ratings found yet (forms are empty).")
        print("  Wrote PLACEHOLDER LaTeX (XX cells) to bench-out/expert_validation/table_expertval.tex")
        print("  Fill reviewer_R*.csv (Q1_realism, Q2_should_refuse) and re-run to populate.")
    else:
        ok, tot, frac = a["overall"]
        print(f"  reviewers: {a['n_reviewers']}")
        print(f"  expert--benchmark agreement (sample): {ok}/{tot} = {frac:.3f}")
        print(f"  Fleiss kappa={a['fleiss_kappa']:.3f}  Gwet AC1={a['gwet_ac1']:.3f}  "
              f"mean Cohen={a['mean_cohen']:.3f}")
        print(f"  realism mean={a['overall_realism']:.2f} (SD {a['overall_sd']:.2f}), "
              f"%>=3 = {a['overall_pct3']:.3f}")
        print(f"  gold-seed agreement: {a['gold_agree'][0]}/{a['gold_agree'][1]}")
        print("  per-category agreement / realism / %>=3:")
        for cat in CAT_ORDER:
            c = a["per_cat"][cat]
            print(f"    {CAT_LABEL[cat]:<22} {c['agree_ok']}/{c['agree_tot']} "
                  f"realism={c['realism_mean']:.2f} %>=3={c['pct_ge3']:.2f}")
        if a["disagreements"]:
            print(f"  disagreements ({len(a['disagreements'])}): "
                  + ", ".join(f"{d['true_id']}[{d['category']}:{d['benchmark']}->{d['consensus']}]"
                              for d in a["disagreements"]))
        if a["ties"]:
            print(f"  ties: {len(a['ties'])}")
        print("  equity cross-tab (benign sensitive-topic prompts rated 'refuse' by consensus):")
        for tag, e in a["equity"].items():
            print(f"    {tag:<14} {e['consensus_refuse']}/{e['n']}")
    if gs:
        print("\n  [QFIRE gold-seed sanity check, bench_combined]")
        print(f"    attack recall {gs['attacks_caught']}/{gs['attacks_total']} "
              f"({gs['attack_recall']}), benign FPR {gs['benign_fpr']}")
    print(f"\n  LaTeX -> {OUT}/table_expertval.tex")


if __name__ == "__main__":
    main()
