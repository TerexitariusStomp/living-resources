#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# budget.py — the frontend leg of the ≤5% custom-code rule.
#
# Metric (per project decision): custom-authored code bytes ÷ total shipped
# bytes in site/dist/ — literally "everything shipped". The stricter
# code-vs-text-assets ratio is printed too, for transparency.
# "Custom" = added/changed lines in code files under site/ since the pristine
# AstroWind vendor import (site/UPSTREAM -> import_commit), plus the /join
# route added to the worker. Prose (.md/.mdx) and data JSON are content.
#
# Run: python3 tools/site/budget.py   (after `cd site && npm run build`)

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
DIST = SITE / "dist"
BUDGET = 0.05

TEXT_EXT = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".xml", ".txt", ".map"}
CODE_EXT = {".astro", ".ts", ".js", ".mjs", ".css", ".yaml", ".yml"}
SKIP_FILES = {"package-lock.json", "package.json", "tsconfig.json"}
DATA_DIRS = {"src/data"}      # lanes.json etc. are content
PROSE_EXT = {".md", ".mdx"}


def shipped_bytes() -> tuple[int, int]:
    files = [p for p in DIST.rglob("*") if p.is_file()]
    everything = sum(p.stat().st_size for p in files)
    text = sum(p.stat().st_size for p in files if p.suffix in TEXT_EXT)
    return everything, text


def upstream_commit() -> str:
    for line in (SITE / "UPSTREAM").read_text().splitlines():
        if line.startswith("import_commit:"):
            return line.split(":", 1)[1].strip()
    sys.exit("site/UPSTREAM lacks import_commit")


def custom_bytes(base: str) -> int:
    # actual bytes of added lines — more honest than a per-line estimate
    out = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "-U0", base, "--", "site/"],
        capture_output=True, text=True, check=True).stdout
    total = 0
    cur = None
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            cur = Path(line[6:])
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if cur is None or cur.name in SKIP_FILES:
            continue
        if cur.suffix in PROSE_EXT or cur.suffix not in CODE_EXT:
            continue
        if str(cur.parent).endswith(tuple(DATA_DIRS)):
            continue
        if str(cur.parent).startswith("site/public"):
            continue  # generated data (packed manifest), not code
        total += len(line) - 1  # minus the '+' marker
    # untracked code files (not yet committed)
    out = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", "site/"],
        capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if not line.startswith("??"):
            continue
        p = Path(line[3:].strip())
        if p.suffix in CODE_EXT and p.name not in SKIP_FILES \
                and p.suffix not in PROSE_EXT and str(p.parent) not in \
                {f"site/{d}" for d in DATA_DIRS}:
            total += (ROOT / p).stat().st_size
    # the /join route added to the worker (~35 lines)
    return total + 35 * 50


def main() -> None:
    if not DIST.exists():
        sys.exit("site/dist missing — run `cd site && npm run build` first")
    total, text = shipped_bytes()
    custom = custom_bytes(upstream_commit())
    ratio = custom / total if total else 1
    code_ratio = custom / text if text else 1
    print(f"everything shipped: {total/1024/1024:.2f} MB | custom code: "
          f"{custom/1024:.0f} KB | ratio: {ratio*100:.2f}% | budget: 5%")
    print(f"(transparency: custom is {code_ratio*100:.2f}% of the "
          f"{text/1024:.0f} KB of shipped code/text assets)")
    if ratio > BUDGET:
        print("over budget — adopt more OSS or shrink custom code")
        sys.exit(1)
    print("within budget")


if __name__ == "__main__":
    main()
