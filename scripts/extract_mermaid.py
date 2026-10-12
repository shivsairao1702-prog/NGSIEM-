#!/usr/bin/env python3
"""Extract every ```mermaid fenced block from tracked Markdown files into .mmd files.

Each output file is named after its source and the line the block starts on, so a
rendering failure in CI points straight at the offending diagram:

    01-architecture__docs__03-sizing.md__L21.mmd

Usage: extract_mermaid.py OUTPUT_DIR [ROOT]
"""
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^```mermaid\s*$\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)
SKIP_DIRS = {".git", "node_modules"}


def extract(root: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for md in sorted(root.rglob("*.md")):
        if SKIP_DIRS & set(md.relative_to(root).parts):
            continue
        text = md.read_text(encoding="utf-8")
        for match in FENCE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            name = "__".join(md.relative_to(root).parts) + f"__L{line}.mmd"
            target = out / name
            target.write_text(match.group(1), encoding="utf-8")
            written.append(target)
    return written


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    files = extract(Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd(), Path(sys.argv[1]))
    for f in files:
        print(f)
    print(f"extracted {len(files)} Mermaid block(s)", file=sys.stderr)
