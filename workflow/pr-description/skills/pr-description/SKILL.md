---
name: pr-description
description: >
  Write a PR title and body that a reviewer can act on in under a minute, sized
  to the change and to whatever pull-request template the repo ships. Use when
  the user says "open a PR", "write the PR description", "draft a PR body",
  "update the description", or asks for a PR after a batch of work. Sources
  facts from the diff rather than the commit log, opens with a lead that answers
  "what and why" before any heading, holds the body to a measured density
  budget, and moves the record of how the work went into a follow-up comment
  instead of the body. Verifies the draft with a scorer before presenting it.
  Not for splitting work into commits (use commit-story), reviewing code,
  merging, or filling in another author's attestation checkboxes.
---

# PR description

A PR body is a decision aid, not a record. The reviewer arrives with a question — *should this merge, and what do I need to look at closely?* — and everything that does not help answer it is a tax on the person you are asking for a favour. The work you did to reach the change is real and worth keeping, but it belongs where someone can go find it, not in the first thing they read.

Agent-written descriptions fail in a characteristic way. They are not wrong; they are *undifferentiated*. Every finding is stated at the same volume, every section is filled because the template had a heading for it, and the length is a function of how much the author learned rather than how much the reviewer needs. The result reads as dense even when each individual sentence is good. This skill fixes altitude and proportion, and then checks its own output with a scorer rather than trusting that it followed its own advice.

## Scope

**Covers.** Drafting a PR title and body for a branch, against whatever template the repo ships. Includes reading the diff to source facts, sizing the body to the change, holding a measured density budget, deciding what belongs in the body versus a follow-up comment, honouring the repo's template semantics, and running the scorer before presenting. Also covers rewriting an existing over-dense description.

**Out of scope.** Splitting work into commits (that is `commit-story`), reviewing the code, running the build, pushing, merging, requesting reviewers, resolving conflicts, and setting labels or ticking checkboxes on the author's behalf. Drafting the body is the deliverable; actually opening the PR is the user's call unless they explicitly ask for it.

## When This Skill Is Triggered

- User says some variation of: "open a PR", "write the PR description", "draft a PR body", "write up this branch", "update the PR description", "make the description less dense".
- User has finished a batch of work on a branch and asks what to do next in a way that implies a PR.
- An existing PR description needs revising after review feedback about length or clarity.

Do *not* trigger for: commit messages (`commit-story`), issue bodies, release notes, or design docs. Those have different readers and different budgets.

## Core Rules

- **The lead is mandatory and comes before any heading.** One or two sentences, 15–60 words, answering what changes and why. This is the only part guaranteed to be read — it is what appears in a notification email, in a PR list hover, and in the reviewer's first two seconds. A body that opens directly on `## What It Does` has no answer anywhere. This is the single most common defect and the cheapest to fix.
- **Size the body to the change, not to what you learned.** Budget tiers are on diff size: ≤50 changed lines → 150 words, 51–500 → 300, >500 → 500. A one-line config flag does not earn four paragraphs no matter how much investigation preceded it.
- **The record of the work goes in a follow-up comment, not the body.** Investigation notes, dead ends, pre-existing failures you confirmed were pre-existing, lockfile archaeology, benchmark tables, phase-by-phase progress — all of it is valuable and none of it belongs in the body. Post it as the first comment on the PR and say so in one line. See [references/placement.md](references/placement.md) for the sorting rule.
- **Emphasis is a ranking, not a highlighter.** At most one bolded claim per section, and no more than three bold spans per hundred words. When every sentence carries emphasis the reader loses the ability to skim, which is exactly the "too dense" complaint.
- **Source facts from the diff, never from commit messages.** Run `git diff <base>...HEAD` and read the changed files. Commit subjects are a summary of a summary and are frequently stale or wrong. Detail in [references/evidence.md](references/evidence.md).
- **Never assert something you did not verify.** Do not write "all tests pass" unless you ran them, do not describe a performance improvement you did not measure, and do not invent a ticket reference. If the branch carries no ticket and the repo expects one, ask.
- **The repo's template is the schema; this skill is the style.** Read `.github/pull_request_template.md` (and `.github/PULL_REQUEST_TEMPLATE/`) first and follow its instructions, including the ones in HTML comments. Never invent sections it does not have, never drop sections it does have. See [references/templates.md](references/templates.md).
- **Leave the author's checkboxes and labels alone.** Attestation lists ("verified in production mode", "checked accessibility", browser matrices) are personal claims. Ticking them on the author's behalf asserts something you did not do. Leave every one unchecked and mention in your summary which labels need applying.
- **Never add an attribution footer** or any mention of how the description was produced.
- **Score before presenting.** Run the density scorer on the draft and fix what it flags. A rule that is never checked is advice, not a rule.

## Workflow

### Phase 1 — Orient

Find the base branch and the template before reading any code.

```sh
BASE=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||')
BASE=${BASE:-main}
git rev-parse --verify "origin/$BASE" >/dev/null 2>&1 || BASE=master

ls .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null
git diff --shortstat "origin/$BASE...HEAD"      # -> the budget tier
```

If there is no template, use the default shape in [references/templates.md](references/templates.md). If there are several under `PULL_REQUEST_TEMPLATE/`, ask which applies rather than guessing.

### Phase 2 — Gather evidence

```sh
git diff "origin/$BASE...HEAD"          # the truth
git diff --stat "origin/$BASE...HEAD"
git log "origin/$BASE..HEAD" --oneline  # context only, never the source
```

Read the changed files where the diff alone hides intent. Note the changed-line total — it selects the budget tier. Detail in [references/evidence.md](references/evidence.md).

### Phase 3 — Sort

Before drafting, split what you know into three piles: **body** (what the reviewer needs to decide), **comment** (the record of the work), **neither** (true but inert). Most of what an agent learns lands in the second and third piles. [references/placement.md](references/placement.md) has the test.

### Phase 4 — Draft

Write the title, then the lead, then the template's sections in order.

- **Title:** what changed, in terms the reader's user would recognise. Match the repo's existing prefix convention if it has one — check `git log --oneline -20` and recent PR titles. Name the behaviour, not the refactor. Append a ticket only if you actually know one.
- **Lead:** 15–60 words, before the first heading. What changes, and why now.
- **Sections:** fill what the template asks for. Where a section genuinely does not apply, leave it empty rather than writing "None" — an empty section reads as "not applicable", the word "None" reads as an assertion.

### Phase 5 — Score

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-description/scripts/density.py draft.md --changed-lines <N>
```

Fix every failure and re-run. The scorer reports prose words against the tier cap, the lead-length window, bold density, and the longest paragraph. It exits non-zero while anything is over. Do not present a draft that has not passed — and do not "fix" it by moving prose into a table or a code fence, which the scorer excludes by design and which makes the body denser rather than lighter.

### Phase 6 — Present

Show the user the title, the body, and — separately — the follow-up comment. Say which labels need applying and which checkboxes you deliberately left unticked. Then stop. Do not open the PR (`mcp__github__create_pull_request`) unless the user asked you to, and if they did, post the follow-up comment immediately after.

## Examples

### Example 1 — Small change, over-explained

A one-line change enabling an API in a config file. 7 changed lines. The investigation to find *which* config file took twenty minutes.

Wrong: 250 words explaining the config hierarchy, which files were ruled out, and how the API enablement propagates.

Right — the whole body, small tier, 150-word cap, comes in at 31:

> Enables the Vision API on the platform services project so the receipt-parsing
> spike can call it. Config-only; no code paths change until the spike lands.
>
> ## How To Test
> - Apply the plan and confirm the API shows as enabled on the project.

The twenty minutes of hierarchy archaeology goes in the follow-up comment, where the next person to hunt for the right file will find it.

### Example 2 — Large migration, needs the lead

A 2,400-line refactor replacing a hand-rolled cache with a library. The author has real findings: two behaviours change, one dependency is pre-1.0, and three test failures on the branch also fail on the base.

The body gets: the lead, what changes, the two behaviour changes a reviewer must look at, and the pre-1.0 risk with its containment. That is roughly 400 words and fits the large tier.

The follow-up comment gets: the phase plan, the evidence that the three failures are pre-existing, and the lockfile drift discovered on the way. All of it is worth keeping. None of it helps the reviewer decide.

### Example 3 — Rewriting an over-dense description

User points at an existing PR and says the reviewers find it impenetrable.

```sh
mcp__github__pull_request_read   owner: <owner>  repo: <repo>  pullNumber: <n>
#   returns the body plus additions/deletions; write the body to /tmp/pr-body.md
#   yourself if you want to pipe it into the density scorer
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr-description/scripts/density.py /tmp/pr-body.md --changed-lines <N>
```

Let the scorer name the defects, then rewrite against them. Do not discard the excised material — offer it back as the follow-up comment. The usual outcome is that nothing was wrong with the content and everything was wrong with where it sat.

## Troubleshooting

| Symptom | Reference |
|---|---|
| Repo has several templates under `.github/PULL_REQUEST_TEMPLATE/` | [references/templates.md](references/templates.md) |
| Template's checklist format is ambiguous (bullets vs. checkboxes) | [references/templates.md](references/templates.md) |
| Draft is over the word cap but everything in it seems necessary | [references/placement.md](references/placement.md) |
| Scorer flags the lead but the template starts with a heading | [references/density.md](references/density.md) |
| Diff is huge and mostly generated or vendored | [references/evidence.md](references/evidence.md) |
| Branch has no ticket and the repo's title convention wants one | [references/templates.md](references/templates.md) |
| PR is a long-running integration branch, not a single change | [references/placement.md](references/placement.md) |

## Topic References

- [Density](references/density.md) — the budget, the corpus it was calibrated against, what each cap corrects, and how to run and read the scorer.
- [Templates](references/templates.md) — discovering the template, reading its HTML-comment instructions, multi-template repos, checklist semantics, checkbox and label discipline, and the default shape when there is no template.
- [Evidence](references/evidence.md) — sourcing from the diff rather than the log, reading past generated and vendored churn, what may be asserted and what must be verified first.
- [Placement](references/placement.md) — the body / comment / neither sorting rule, with the failure modes it catches.
