# Trigger evals — result

Run 2026-08-16, default model, with the full enabled plugin set competing.

## What prompted this

Two skills in this marketplace — `lit` and `typescript` — went unused across a
long run of real sessions in a Lit + TypeScript codebase, while sibling skills
covering narrower slices of the same work (`jh-design-system`, `lit-router`)
fired normally. The judge-based suite scored both unused skills fine, because
it injects `SKILL.md` into the system prompt and so never asks whether the
model would have chosen them.

The starting hypothesis was reciprocal suppression: `lit` said *"Not for the
lit-router, web-component-router, or jh-design-system skills"* while
`jh-design-system` said *"Not for the lit skill"*. A Lit view built from a
design system and a router is all three at once, so whichever loaded first
disclaimed the others.

## Results

| Case | arm | fire rate |
|---|---|---:|
| `lit-alongside-design-system-and-router` | pre-edit descriptions | 1/1 |
| `lit-alongside-design-system-and-router` | post-edit descriptions | 1/1 |
| `lit-under-design-system-framing` | pre-edit descriptions | 2/2 |
| `lit-under-design-system-framing` | post-edit descriptions | 2/2 |
| `typescript-on-type-design` | post-edit descriptions | 2/2 |

Eight scored runs. The two arms differ only in the plugin descriptions: the
runner points `--plugin-dir` at either the working tree or the installed copy
under `~/.claude/plugins/cache/`, which still holds the previous release.

## The finding is negative, and that matters

**Both arms pass.** `lit` fires reliably under the old descriptions too,
including in the design-system-led framing written specifically to reproduce
the conditions where it was missing. The suppression hypothesis is **not
supported**.

The rewrite stands on its own merits — prescriptive triggers, no reciprocal
disclaimers — but it is **not demonstrated to be a fix**, and the original
misses remain unexplained. The most likely untested difference is scale: these
cases run 9–25 turns, and the sessions where the skills were missing ran an
order of magnitude longer. A reasonable next hypothesis is that selection is
front-loaded — once a session has loaded siblings early, later work in an
adjacent area does not re-trigger — which needs a long-session case rather than
a single prompt.

## What the suite is worth anyway

1. It is a real regression guard: these arms assert the skills fire, and go red
   if a future description change suppresses them.
2. It caught a defect in itself. The first version ran under `--bare`, which
   exposes only `Bash`/`Edit`/`Read` — **no `Skill` tool** — and ignores
   `--tools`. Every case reported a clean zero that meant nothing. The runner
   now asserts the `Skill` tool is present and fails loudly instead.
3. It makes the blind spot in the judge-based suite explicit and testable.

## Rerun

    uv run python triggering/run.py                     # working tree, n=3
    uv run python triggering/run.py --arm both -n 3     # A/B vs installed copy
    uv run python triggering/run.py --case 'lit-*'      # filter
