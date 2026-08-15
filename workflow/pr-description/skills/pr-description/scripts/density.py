#!/usr/bin/env python3
"""Score a PR body against the density budget.

Reads a markdown body on stdin (or from a path) and reports the metrics the
skill's budget is defined on, plus a pass/fail verdict per metric.

The metrics deliberately run on *authored prose*, not raw body length. A
template that ships 120 words of author-liability checkboxes should not count
against the author, and neither should the HTML comments the template uses to
instruct them. What counts is what a reviewer has to read.

    python3 density.py < body.md
    python3 density.py body.md --changed-lines 800
    gh pr view 123 --json body -q .body | python3 density.py --json

Exit status is 1 if any hard budget is exceeded, so it can gate a workflow.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# --- budgets ---------------------------------------------------------------
# Calibrated against a 12-PR corpus; see references/density.md for the raw
# measurements and what each cap is actually correcting.
#
# Length is tiered on diff size because the corpus showed no correlation between
# the two: a 7-line config change drew 259 words and a 4,909-line feature drew
# 383. Absent a tier, a single cap either licenses the 7-line essay or punishes
# the migration that has genuine setup to explain.
#
# lead_words has a FLOOR as well as a ceiling, and the floor is the point. Nine
# of twelve PRs in the corpus opened directly on a `##` heading with no prose at
# all, so a reviewer scanning a list — or reading a notification email — never
# got a one-sentence answer to "what is this and why".
SMALL_DIFF_LINES = 50
LARGE_DIFF_LINES = 500

BUDGETS = {
    "small":  {"prose_words": 150, "bold_per_100w": 3.0, "max_para_words": 80},
    "normal": {"prose_words": 300, "bold_per_100w": 3.0, "max_para_words": 80},
    "large":  {"prose_words": 500, "bold_per_100w": 3.0, "max_para_words": 80},
}
LEAD_MIN, LEAD_MAX = 15, 60

# --- stripping -------------------------------------------------------------
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
FENCED = re.compile(r"^```.*?^```", re.S | re.M)
CHECKBOX = re.compile(r"^\s*[-*] \[[ xX]\] ", re.M)
HEADING = re.compile(r"^(#{1,6}) +(.+?)\s*$", re.M)
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)
BOLD = re.compile(r"\*\*(?!\s)([^*]+?)(?<!\s)\*\*")
FILE_REF = re.compile(r"[A-Za-z0-9_/.-]+\.[A-Za-z]{1,5}:[0-9]+(?:-[0-9]+)?")
LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.) +", re.M)


def strip_scaffolding(body: str) -> str:
    """Remove what the template supplied, keeping what the author wrote."""
    text = HTML_COMMENT.sub("", body)
    # Checkbox lines are attestations and expected-outcome markers, not prose.
    text = "\n".join(ln for ln in text.split("\n") if not CHECKBOX.match(ln))
    return text


def prose_of(text: str) -> str:
    """Prose only: no code fences, no table rows, no heading markers."""
    text = FENCED.sub("", text)
    text = TABLE_ROW.sub("", text)
    text = HEADING.sub(lambda m: "", text)
    return text


def paragraphs(prose: str) -> list[str]:
    out = []
    for block in re.split(r"\n\s*\n", prose):
        block = block.strip()
        if not block or BULLET.match(block):
            continue
        out.append(block)
    return out


def measure(body: str) -> dict:
    authored = strip_scaffolding(body)
    prose = prose_of(authored)

    words = len(prose.split())
    heads = HEADING.findall(authored)

    # The lead is everything before the first heading — what shows up in a
    # notification email and in the PR list hover.
    first = HEADING.search(authored)
    lead_src = authored[: first.start()] if first else authored
    lead_words = len(prose_of(lead_src).split())

    bolds = len(BOLD.findall(prose))
    paras = paragraphs(prose)

    return {
        "prose_words": words,
        "lead_words": lead_words,
        "headings": len(heads),
        "heading_titles": [h[1] for h in heads],
        "bullets": len(BULLET.findall(authored)),
        "bold_spans": bolds,
        "bold_per_100w": round(bolds * 100 / words, 1) if words else 0.0,
        "max_para_words": max((len(p.split()) for p in paras), default=0),
        "paragraphs": len(paras),
        "code_blocks": len(FENCED.findall(authored)),
        "tables": authored.count("|---") + authored.count("| ---"),
        "file_refs": len(FILE_REF.findall(authored)),
        "links": len(LINK.findall(authored)),
        "raw_words": len(body.split()),
    }


def tier_for(changed_lines: int | None) -> str:
    if changed_lines is None:
        return "normal"
    if changed_lines <= SMALL_DIFF_LINES:
        return "small"
    if changed_lines > LARGE_DIFF_LINES:
        return "large"
    return "normal"


def verdict(m: dict, changed_lines: int | None) -> tuple[list[str], str]:
    tier = tier_for(changed_lines)
    b = BUDGETS[tier]
    fails = []
    if m["prose_words"] > b["prose_words"]:
        fails.append(
            f"prose_words {m['prose_words']} > {b['prose_words']} "
            f"({tier} budget) — cut to the decision, move the rest to a follow-up comment"
        )
    if m["lead_words"] == 0:
        fails.append(
            f"lead_words 0 — no prose before the first heading. A reviewer scanning a list, or "
            "reading a notification, gets the title and nothing else. Open with one or two "
            f"sentences ({LEAD_MIN}-{LEAD_MAX} words): what changes, and why."
        )
    elif m["lead_words"] < LEAD_MIN:
        fails.append(
            f"lead_words {m['lead_words']} < {LEAD_MIN} — the lead is too thin to stand alone. "
            "Say what changes AND why it is happening now; one of the two is usually missing."
        )
    elif m["lead_words"] > LEAD_MAX:
        fails.append(
            f"lead_words {m['lead_words']} > {LEAD_MAX} — "
            "the lead is the one part guaranteed to be read; keep it to the claim"
        )
    if m["bold_per_100w"] > b["bold_per_100w"]:
        fails.append(
            f"bold_per_100w {m['bold_per_100w']} > {b['bold_per_100w']} — "
            "when everything is emphasized nothing is; bold the one claim per section that matters"
        )
    if m["max_para_words"] > b["max_para_words"]:
        fails.append(
            f"max_para_words {m['max_para_words']} > {b['max_para_words']} — "
            "split the longest paragraph or make it a list"
        )
    return fails, tier


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="markdown file; omit to read stdin")
    ap.add_argument("--changed-lines", type=int, default=None,
                    help="additions+deletions in the diff; selects the small (<=%d) / normal / "
                         "large (>%d) budget tier" % (SMALL_DIFF_LINES, LARGE_DIFF_LINES))
    ap.add_argument("--json", action="store_true", help="emit metrics as JSON")
    args = ap.parse_args()

    body = open(args.path, encoding="utf-8").read() if args.path else sys.stdin.read()
    m = measure(body)
    fails, tier = verdict(m, args.changed_lines)

    if args.json:
        print(json.dumps({"tier": tier, "metrics": m, "failures": fails}, indent=2))
        return 1 if fails else 0

    b = BUDGETS[tier]
    print(f"budget tier: {tier}" + (f"  ({args.changed_lines} changed lines)" if args.changed_lines else ""))
    print()
    lead_ok = LEAD_MIN <= m["lead_words"] <= LEAD_MAX
    print(f"  {'prose words':<16}{m['prose_words']:>7}   cap {b['prose_words']:<9}"
          f"{'FAIL' if m['prose_words'] > b['prose_words'] else 'ok'}")
    print(f"  {'lead words':<16}{m['lead_words']:>7}   {LEAD_MIN}-{LEAD_MAX:<11}"
          f"{'ok' if lead_ok else 'FAIL'}")
    for label, key in (("bold per 100w", "bold_per_100w"), ("longest para", "max_para_words")):
        got, cap = m[key], b[key]
        print(f"  {label:<16}{got:>7}   cap {cap:<9}{'FAIL' if got > cap else 'ok'}")
    print()
    print(f"  {'headings':<16}{m['headings']:>7}   {', '.join(m['heading_titles']) or '—'}")
    for label in ("bullets", "code_blocks", "tables", "file_refs", "links"):
        print(f"  {label:<16}{m[label]:>7}")
    print(f"  {'raw words':<16}{m['raw_words']:>7}   (incl. template scaffolding)")

    if fails:
        print("\nOver budget:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nWithin budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
