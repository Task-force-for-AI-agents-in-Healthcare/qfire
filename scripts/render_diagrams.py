#!/usr/bin/env python3
"""Render the paper's Mermaid diagrams (paper/diagrams/*.mmd) to high-res PNGs in
paper/figs/ using mermaid-cli (mmdc) via npx, driving the system Chrome so no
Chromium download is needed.

Usage:
    python3 scripts/render_diagrams.py            # render all *.mmd
    python3 scripts/render_diagrams.py deberta    # render one by stem

PNGs land in paper/figs/<stem>.png at 3x scale on a white background, ready to
embed in Markdown:  ![...](figs/deberta.png)
"""
import glob
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAG = os.path.join(BASE, "paper", "diagrams")
FIGS = os.path.join(BASE, "paper", "figs")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render(mmd):
    stem = os.path.splitext(os.path.basename(mmd))[0]
    out = os.path.join(FIGS, stem + ".png")
    cmd = [
        "npx", "-y", "-p", "@mermaid-js/mermaid-cli", "mmdc",
        "-i", mmd, "-o", out,
        "-b", "white", "-s", "3",
        "-c", os.path.join(DIAG, "mermaid.config.json"),
        "-p", os.path.join(DIAG, "puppeteer.json"),
    ]
    env = dict(os.environ, PUPPETEER_EXECUTABLE_PATH=CHROME)
    print(f"rendering {stem} ...", flush=True)
    r = subprocess.run(cmd, cwd=DIAG, env=env, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        print(f"  FAILED ({r.returncode})")
        print((r.stdout + r.stderr)[-800:])
        return False
    sz = os.path.getsize(out)
    print(f"  ok -> {out} ({sz} bytes)")
    return True


def main():
    os.makedirs(FIGS, exist_ok=True)
    targets = sys.argv[1:]
    mmds = sorted(glob.glob(os.path.join(DIAG, "*.mmd")))
    if targets:
        mmds = [m for m in mmds if os.path.splitext(os.path.basename(m))[0] in targets]
    ok = all(render(m) for m in mmds)
    print("DIAGRAMS_DONE" if ok else "DIAGRAMS_HAD_FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
