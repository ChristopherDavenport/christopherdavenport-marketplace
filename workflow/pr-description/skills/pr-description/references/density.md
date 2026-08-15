# Density

The budget exists because "write shorter" is not actionable and "too dense" is not measurable. These four numbers are.

## The budget

| Metric | Budget | What it corrects |
|---|---|---|
| `lead_words` | **15–60, required** | No answer before the first heading |
| `prose_words` | 150 / 300 / 500 by tier | Length set by what the author learned, not what the reviewer needs |
| `bold_per_100w` | ≤ 3.0 | Uniform emphasis, so nothing can be skimmed |
| `max_para_words` | ≤ 80 | Wall of text |

Tiers are on `additions + deletions`: **small** ≤ 50 lines → 150 words, **normal** 51–500 → 300, **large** > 500 → 500.

The metrics run on *authored prose*. The scorer strips HTML comments, checkbox lines, code fences, table rows, and heading markers before counting — a template that ships 120 words of attestation checkboxes should not count against the author, and a stack trace is not prose. This also means you cannot satisfy the budget by moving paragraphs into a table or a fenced block. That makes the body denser, not lighter, and the scorer is deliberately blind to it so the tactic yields nothing.

## Where the numbers came from

Calibrated against a twelve-PR corpus of real, review-bearing pull requests spanning 7 to 10,150 changed lines.

| Metric | min | median | p75 | max |
|---|---:|---:|---:|---:|
| prose words | 250 | 567 | 674 | 1167 |
| lead words | 0 | **0** | 54 | 181 |
| bold per 100w | 0.2 | 1.5 | 3.1 | 6.6 |
| longest paragraph | 37 | 70 | 88 | 103 |

Three things fell out of that corpus and each one set a cap.

**The lead was missing, not merely short.** Nine of twelve bodies had *zero* words before the first heading — the reader hit `## What It Does` immediately. A PR list, a notification email, and a Slack unfurl all show the title and then the first prose. With none, there is no one-sentence answer anywhere in the artifact. This is why `lead_words` has a floor, and why the floor is the highest-value line in the budget: it is additive, costs about twenty words, and is the only defect here that a reviewer experiences before opening the PR.

**Length tracked the change only weakly.** Spearman ρ = 0.49, Pearson r = 0.18. Words per hundred changed lines ranged from 6 to 3,700 — a seven-line config change drew 259 words while a 4,909-line feature drew 383. A single flat cap would either license the seven-line essay or punish the migration with real setup to explain, so the cap is tiered.

**Bold was load-bearing in the worst offenders.** The densest-feeling bodies were not the longest; they were the ones at 3–6.6 bold spans per hundred words. Uniform emphasis removes the reader's ability to triage, which is precisely the experience reviewers describe as "dense".

Scored against these caps, the corpus passes **0 of 12**. That is the finding, not a miscalibration — the budget describes a change in practice. Two of the twelve fail only on the lead and on bold, both of which are minutes of work.

## Running it

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-description/scripts/density.py draft.md --changed-lines 320
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-description/scripts/density.py draft.md --changed-lines 320 --json
gh pr view 42 --json body -q .body | python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-description/scripts/density.py --changed-lines 320
```

Exit status is 1 while any hard budget is exceeded, so it gates a workflow or a pre-push hook. Omitting `--changed-lines` assumes the normal tier.

Alongside the four budgeted metrics it reports headings, bullets, code blocks, tables, file references, links, and raw word count. Those are unbudgeted diagnostics — a body with nine headings or fourteen file:line references is usually a work record wearing a description's clothes, and the fix is in [placement.md](placement.md), not here.

## When the budget and the reviewer disagree

The budget is a default, not a law. A PR that genuinely needs 700 words is possible — a security fix with a disclosure timeline, a migration with a rollback procedure that must be inline. When that happens, say so in one line at the top of the body and keep going. What the budget forbids is exceeding it *silently*, which is how every one of the twelve got where it is.

Do not resolve an over-budget draft by deleting the caveats. Caveats are the highest-value content in a PR body. Resolve it by moving the *narrative* — how you found the problem, what you ruled out, what surprised you — into the follow-up comment.
