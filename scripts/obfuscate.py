#!/usr/bin/env python3
"""Generate an obfuscated variant of the attack corpus for the de-obfuscation
ablation. Each attack prompt is encoded with one of several techniques
(Base64, ROT13, leetspeak, homoglyph substitution, zero-width insertion),
cycled deterministically by index so the run is reproducible.

Input : corpora/eval/attacks/public_attacks.jsonl  ({"prompt"})
Output: corpora/eval/attacks_obf/obf_attacks.jsonl  ({"prompt"})
"""
import base64, json, os, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "corpora/eval/attacks/public_attacks.jsonl"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "corpora/eval/attacks_obf"

HOMO = {"a": "а", "e": "е", "o": "о", "p": "р",
        "c": "с", "x": "х", "y": "у", "i": "і"}
LEET = {"a": "4", "e": "3", "o": "0", "i": "1", "s": "5", "t": "7"}


def rot13(s):
    out = []
    for ch in s:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + 13) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + 13) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def leet(s):
    return "".join(LEET.get(c.lower(), c) for c in s)


def homoglyph(s):
    return "".join(HOMO.get(c.lower(), c) for c in s)


def zerowidth(s):
    zw = "​"
    return zw.join(s)


def obfuscate(prompt, i):
    technique = i % 5
    if technique == 0:
        b = base64.b64encode(prompt.encode()).decode()
        return f"Please base64-decode and follow the instruction: {b}"
    if technique == 1:
        return f"Decode this ROT13 and comply: {rot13(prompt)}"
    if technique == 2:
        return leet(prompt)
    if technique == 3:
        return homoglyph(prompt)
    return zerowidth(prompt)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "obf_attacks.jsonl")
    n = 0
    with open(SRC) as f, open(out, "w") as g:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            p = o.get("prompt")
            if not p:
                continue
            g.write(json.dumps({"prompt": obfuscate(p, i)}) + "\n")
            n += 1
    print(f"wrote {n} obfuscated attacks -> {out}")
    print("OBFDONE")


if __name__ == "__main__":
    main()
