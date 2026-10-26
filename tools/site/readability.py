#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# readability.py — fail the build if the plain-language pages drift above a
# middle-school reading level. Reads the BUILT html in site/dist (run
# `npm run build` first).
#
# Pass rules:
#   - index.html: whole-page Flesch-Kincaid grade <= 7.0 (all collected
#     blocks joined, each terminated with a period).
#   - every block of 15+ words must be <= 9.0.
#   - developers/ is a technical page: only blocks inside data-reading="plain"
#     elements are gated (same <= 9.0 rule).
#   - elements with data-reading="skip" (citations, mono footnotes) are
#     exempt — but they are for metadata, not explanations.
#
# Degrades loudly: missing textstat -> exit 2 with an install hint.

import sys
from html.parser import HTMLParser
from pathlib import Path

try:
    import textstat
except ImportError:
    print("textstat missing — run: python3 -m pip install --user -r tools/site/requirements.txt")
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "site" / "dist"

PAGE_GRADE = 7.0      # joined-block grade cap on plain pages
BLOCK_GRADE = 9.0     # cap for any single 15+ word block
MIN_WORDS = 15

SKIP_TAGS = {"nav", "header", "footer", "code", "pre", "script", "style", "svg"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "dd", "td", "figcaption"}

# (file, scope): scope "plain" = only data-reading="plain" subtrees
PAGES = [
    ("index.html", "all"),
    ("developers/index.html", "plain"),
]


class Collector(HTMLParser):
    """Collect visible text blocks inside <main>. Stack entries carry the
    counter values they came in with, so end tags restore them exactly."""

    def __init__(self, scope):
        super().__init__(convert_charrefs=True)
        self.scope = scope
        self.in_main = 0
        self.skip = 0
        self.plain = 0
        self.stack = []          # (tag, was_skip, was_plain, is_main)
        self.cur = None
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        was_skip = self.skip
        was_plain = self.plain
        was_main = self.in_main
        if tag == "main":
            self.in_main += 1
        if tag in SKIP_TAGS or a.get("data-reading") == "skip":
            self.skip += 1
        if a.get("data-reading") == "plain":
            self.plain += 1
        self.stack.append((tag, was_skip, was_plain, was_main))
        wanted = self.scope == "all" or self.plain > 0
        if self.in_main and not self.skip and wanted and tag in BLOCK_TAGS and self.cur is None:
            self.cur = []

    def handle_startendtag(self, tag, attrs):
        # self-closing tags contribute no text and no nesting
        pass

    def handle_endtag(self, tag):
        # pop to matching tag (tolerate malformed nesting)
        while self.stack:
            t, was_skip, was_plain, was_main = self.stack.pop()
            self.skip, self.plain, self.in_main = was_skip, was_plain, was_main
            if t == tag:
                break
        if self.cur is not None and tag in BLOCK_TAGS:
            text = " ".join("".join(self.cur).split())
            if text:
                self.blocks.append(text)
            self.cur = None

    def handle_data(self, data):
        if self.cur is not None:
            self.cur.append(data)


def score_page(path, scope):
    p = DIST / path
    if not p.is_file():
        print(f"missing {p} — run `npm run build` in site/ first")
        sys.exit(2)
    c = Collector(scope)
    c.feed(p.read_text(errors="replace"))
    return c.blocks


def grade(blocks):
    """FK grade of blocks joined as pseudo-sentences."""
    text = " ".join(b if b.endswith((".", "!", "?", ":")) else b + "." for b in blocks)
    return textstat.flesch_kincaid_grade(text) if text.strip() else 0.0


def main():
    failures = []
    for path, scope in PAGES:
        blocks = score_page(path, scope)
        page_grade = grade(blocks) if scope == "all" else None
        hard = sorted(
            ((textstat.flesch_kincaid_grade(b), b) for b in blocks if len(b.split()) >= MIN_WORDS),
            reverse=True,
        )
        over = [h for h in hard if h[0] > BLOCK_GRADE]
        line = f"{path}: {len(blocks)} blocks"
        if page_grade is not None:
            line += f" | page grade {page_grade:.1f} (cap {PAGE_GRADE})"
        line += f" | {len(over)} blocks over {BLOCK_GRADE}"
        print(line)
        for g, b in hard[:5]:
            print(f"    {g:5.1f}  {b[:80]}")
        if page_grade is not None and page_grade > PAGE_GRADE:
            failures.append(f"{path}: page grade {page_grade:.1f} > {PAGE_GRADE}")
        failures += [f"{path}: block grade {g:.1f} > {BLOCK_GRADE}: {b[:60]}" for g, b in over]

    if failures:
        print("\nreadability gate FAILED:")
        for f in failures:
            print("  " + f)
        sys.exit(1)
    print("\nreadability ok — all gated pages <= grade", PAGE_GRADE)


if __name__ == "__main__":
    main()
