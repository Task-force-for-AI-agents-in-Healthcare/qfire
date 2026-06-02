#!/usr/bin/env python3
"""E6 driver: run NeMo Guardrails (full input-rail stack from nemo_config/) over a labeled
corpus and emit metrics in the SAME JSON shape as scripts/baselines.py, so NeMo slots into
the existing head-to-head / HealthBench tables and the adaptive panel. A prompt is BLOCKED
if ANY input rail stops it (fail-closed). Recall = block rate on attacks; FPR = block rate
on benign. Offline (Ollama /v1 + local Presidio/gpt2). Run with the E6 venv:

  .venv-e6/bin/python scripts/run_nemo.py --attacks <dir|file> --benign <dir|file> \
      --out bench-out/nemo_<corpus>.json [--sample 400] [--seed 42]
"""
import argparse, json, math, os, random, sys, time
os.environ.setdefault("OPENAI_API_KEY", "ollama-local")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path, label):
    p = path
    if os.path.isdir(path):
        for f in sorted(os.listdir(path)):
            if f.endswith(".jsonl"):
                p = os.path.join(path, f); break
    rows = []
    for ln in open(p):
        o = json.loads(ln)
        if o.get("prompt"):
            rows.append((o["prompt"], label))
    return rows


def wilson(succ, n):
    if n == 0:
        return [0.0, 0.0]
    z = 1.96; p = succ / n; d = 1 + z*z/n; c = p + z*z/(2*n)
    m = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return [max(0.0, (c-m)/d), min(1.0, (c+m)/d)]


def pct(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs); k = max(0, min(len(s)-1, int(round(q*(len(s)-1)))))
    return s[k]


def metrics(preds, labels):
    tp = sum(1 for p, l in zip(preds, labels) if l == "attack" and p)
    fn = sum(1 for p, l in zip(preds, labels) if l == "attack" and not p)
    fp = sum(1 for p, l in zip(preds, labels) if l == "benign" and p)
    tn = sum(1 for p, l in zip(preds, labels) if l == "benign" and not p)
    n = tp+fn+fp+tn
    prec = tp/(tp+fp) if tp+fp else 0.0
    rec = tp/(tp+fn) if tp+fn else 0.0
    f1 = 2*prec*rec/(prec+rec) if prec+rec else 0.0
    acc = (tp+tn)/n if n else 0.0
    return dict(tp=tp, fp=fp, tn=tn, fn=fn, n=n, precision=prec, recall=rec, f1=f1,
               accuracy=acc, acc_ci=wilson(tp+tn, n), recall_ci=wilson(tp, tp+fn),
               fpr=fp/(fp+tn) if fp+tn else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attacks", required=True)
    ap.add_argument("--benign", default="")
    ap.add_argument("--recall-only", action="store_true",
                    help="attack-only set (adaptive panel): recall = block rate, no benign")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=0, help="stratified N per class (0=all)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from nemoguardrails import LLMRails, RailsConfig
    from nemoguardrails.rails.llm.options import GenerationOptions
    rails = LLMRails(RailsConfig.from_path(os.path.join(BASE, "nemo_config")))
    opts = GenerationOptions(rails={"input": True, "dialog": False, "output": False,
                                    "retrieval": False}, log={"activated_rails": True})

    atk = load(args.attacks, "attack")
    ben = [] if (args.recall_only or not args.benign) else load(args.benign, "benign")
    if args.sample:
        rng = random.Random(args.seed)
        atk = rng.sample(atk, min(args.sample, len(atk)))
        if ben:
            ben = rng.sample(ben, min(args.sample, len(ben)))
    data = atk + ben
    print(f"corpus: {len(data)} ({len(atk)} atk / {len(ben)} ben)", flush=True)

    preds, labels, lat = [], [], []
    for i, (prompt, label) in enumerate(data):
        t0 = time.time()
        try:
            resp = rails.generate(messages=[{"role": "user", "content": prompt}], options=opts)
            ar = getattr(getattr(resp, "log", None), "activated_rails", None) or []
            blocked = any(getattr(r, "stop", False) for r in ar)
        except Exception as e:
            blocked = True  # fail-closed on rail error (matches guardrail deployment)
            if i < 3:
                print(f"  [warn] rail error on prompt {i}: {e}", flush=True)
        lat.append((time.time()-t0)*1000.0)
        preds.append(blocked); labels.append(label)
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(data)}  (running block-rate {sum(preds)/len(preds):.2f})", flush=True)

    m = metrics(preds, labels)
    m["latency_ms"] = dict(p50=pct(lat, 0.5), p95=pct(lat, 0.95), p99=pct(lat, 0.99),
                           mean=sum(lat)/len(lat) if lat else 0.0)
    m["model"] = "nemo-guardrails (self-check + jailbreak-heuristic + presidio-pii, llama3.1:8b)"
    out = {"corpus_size": len(data), "attacks": len(atk), "benign": len(ben),
           "results": {"nemo-guardrails": m}}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"\n{args.out}: R={m['recall']:.3f} P={m['precision']:.3f} F1={m['f1']:.3f} "
          f"FPR={m['fpr']:.3f} acc={m['accuracy']:.3f} p50={m['latency_ms']['p50']:.0f}ms")
    print("NEMO_RUN_DONE")


if __name__ == "__main__":
    main()
