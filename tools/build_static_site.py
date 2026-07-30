#!/usr/bin/env python3
"""Create the exact static directory uploaded to GitHub Pages."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
FILES = ["index.html", "404.html", "favicon.svg", "site.webmanifest", ".nojekyll"]
DIRECTORIES = ["assets", "css", "data", "js"]


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name in FILES:
        source = ROOT / name
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, OUT / name)
    for name in DIRECTORIES:
        source = ROOT / name
        if not source.is_dir():
            raise FileNotFoundError(source)
        shutil.copytree(source, OUT / name)
    print(f"Built GitHub Pages artifact: {OUT}")
    print(f"Files: {sum(1 for path in OUT.rglob('*') if path.is_file()):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
