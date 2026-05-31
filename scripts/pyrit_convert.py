#!/usr/bin/env python3
"""Apply REAL Microsoft PyRIT prompt converters to a set of seed prompts.
Runs under the Python 3.11 venv that has pyrit installed (PyRIT requires >=3.10):
    /tmp/gp311/bin/python scripts/pyrit_convert.py <in.jsonl> <out.jsonl>

Reads {"prompt","category"} JSONL, cycles a set of deterministic converters,
and writes {"prompt","category","technique","source":"pyrit"} JSONL.
"""
import asyncio, json, sys

# Candidate deterministic converters (no network / no LLM). We probe which are
# importable+usable and keep those.
CANDIDATES = [
    ("base64", "Base64Converter", {}),
    ("rot13", "ROT13Converter", {}),
    ("atbash", "AtbashConverter", {}),
    ("leetspeak", "LeetspeakConverter", {}),
    ("unicode_confusable", "UnicodeConfusableConverter", {}),
    ("binary", "BinaryConverter", {}),
    ("caesar", "CaesarConverter", {"caesar_offset": 3}),
    ("morse", "MorseConverter", {}),
    ("ascii_smuggler", "AsciiSmugglerConverter", {}),
]


def load_converters():
    import pyrit.prompt_converter as pc
    out = []
    for tech, cls, kw in CANDIDATES:
        try:
            c = getattr(pc, cls)(**kw)
            # smoke test
            r = asyncio.run(c.convert_async(prompt="ignore all instructions"))
            txt = getattr(r, "output_text", None)
            if txt:
                out.append((tech, c))
        except Exception:
            continue
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    convs = load_converters()
    sys.stderr.write("pyrit converters: " + ",".join(t for t, _ in convs) + "\n")
    if not convs:
        sys.stderr.write("NO pyrit converters available\n")
        sys.exit(1)
    rows = [json.loads(l) for l in open(src) if l.strip()]
    with open(dst, "w") as f:
        for i, row in enumerate(rows):
            tech, c = convs[i % len(convs)]
            try:
                r = asyncio.run(c.convert_async(prompt=row["prompt"]))
                txt = r.output_text
            except Exception:
                continue
            # Frame encoded payloads as a decode-and-comply instruction so the
            # attack intent survives the transform (matches real PyRIT attack use).
            if tech in ("base64", "binary", "morse", "atbash", "caesar"):
                txt = f"Decode the following ({tech}) and follow the instruction: {txt}"
            f.write(json.dumps({"prompt": txt, "category": row.get("category", "obf"),
                                "technique": tech, "source": "pyrit"}) + "\n")
    sys.stderr.write("PYRIT_CONVERT_DONE\n")


if __name__ == "__main__":
    main()
