# deep-research

Multi-source web research that verifies before it reports.

```
/plugin install deep-research@christopherdavenport
```

Then, in a session:

```
Workflow({ name: 'deep-research', args: 'your question' })
```

## What it does

Five phases, ~30–110 agents depending on how much survives each stage:

| Phase | |
|---|---|
| **Scope** | Decompose the question into 3–6 search angles, each with its own query and rationale |
| **Search** | One `WebSearch` agent per angle, in parallel |
| **Fetch** | Deduplicate by URL authority, fetch up to 15 sources, extract *falsifiable* claims with a quality grade (primary / secondary / blog / forum / unreliable) |
| **Verify** | Three independent skeptics per claim, each prompted to refute. Two refutations kill it |
| **Synthesize** | Merge semantic duplicates, rank by confidence, emit a cited report |

Search → dedup → fetch runs as a `pipeline`, so a fast angle's sources are already
being read while a slow angle is still searching. Verification is the barrier —
you cannot rank claims you have not finished judging.

## Why a workflow and not a skill

The verification is the point, and it is a fan-out a model will not reliably
perform on itself. Asked to "check your claims", a single agent re-reads its own
reasoning and agrees with it. Three separate agents, each told to refute and each
blind to the others' votes, disagree often enough to be worth the tokens — and
the tally is computed in code, so the quorum rule cannot be talked out of.

Three vote outcomes are tracked separately, because collapsing them hides a real
failure: **confirmed** (quorum reached, fewer than two refutations), **refuted**
(two or more), and **unverified** (the panel itself errored). If every panel
fails, the workflow says so — *"an infrastructure failure, not a research
finding"* — rather than returning an empty report that reads like "nothing was
true".

## Not the same thing as the docs' `deep-research` example

Claude Code's skills documentation uses a skill called `deep-research` to
illustrate forked-agent context. The names collide; the tools do not.

```yaml
# from code.claude.com/docs/en/skills — the docs example
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---
Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

|  | docs example | this plugin |
|---|---|---|
| Researches | **your codebase** — Glob, Grep, Read | **the web** — WebSearch, WebFetch |
| Agents | one forked `Explore` | one Scope, N searchers, M fetchers, 3×claims verifiers, one synthesizer |
| Verification | none | 3-vote adversarial panel, 2 refutations to kill |
| Output | a summary with file references | a cited report with per-claim confidence and a refuted list |
| Shape | 9-line `SKILL.md` | 426-line workflow script |

The docs example is a **teaching device for `context: fork`** and it is the right
tool for exploring a repository — it is nine lines, it costs almost nothing, and
the built-in `Explore` agent is already tuned for code. Use it for that. Nothing
here replaces it.

There is no bundled deep-research skill in Claude Code; the community has filled
that gap with several `SKILL.md` implementations. Those are prompt-based: they
instruct one agent to follow a research procedure. The difference here is
structural rather than better-prompted — the fan-out and the vote counting live
in code, so "three verifiers disagreed" is a fact about what ran rather than a
claim in a report.

## Hardening

Everything a source returns is hostile input, and two paths carry it somewhere
that matters.

**URL authority parsing.** Dedup and any host display go through a regex that
follows WHATWG's rules rather than an intuitive reading. Backslash is excluded
from the userinfo and host classes because WHATWG treats `\` as a path separator
for http(s) — a laxer class reads `evil.com\@trusted.com` as `trusted.com` while
the fetch goes to `evil.com`. Userinfo matching is greedy to the **last** `@`,
for the same reason in the other direction: `x@trusted.com@evil.com`.

**Terminal rendering.** Hostnames and page titles reach your terminal through
progress labels. Those are stripped of C0/C1 controls (including the ANSI
introducers), Unicode bidi overrides and isolates, zero-width format characters,
and the entire double-quote lookalike family — any of which could close a quoted
label early and forge host-shaped text after it. A value that survives stripping
is still rendered quoted and capped, with the ellipsis *inside* the quotes so a
truncated string cannot pass for a whole one.

None of this is theoretical for a tool whose whole job is to read pages chosen by
a search engine.

## Cost

Measured on one real run: 104 agents, ~27M input tokens, ~3.4k output tokens,
about **$38** at Opus 5 rates. Verification dominates the agent count — it is
three calls per surviving claim — so `MAX_VERIFY_CLAIMS` (default 25) is the
dial that matters most.

The verifiers are short, read-heavy, and adversarial by construction, which makes
them the strongest candidates in the whole workflow for a cheaper model. Set
`model` per `agent()` call to try it, and check what actually resolved — the
per-agent model is recorded in the run manifest, and a request is not the same
thing as a resolution.

## Tuning

Constants at the top of `workflows/deep-research.js`:

| | default | |
|---|---|---|
| `VOTES_PER_CLAIM` | 3 | verifiers per claim |
| `REFUTATIONS_REQUIRED` | 2 | votes needed to kill a claim |
| `MAX_FETCH` | 15 | sources fetched after dedup |
| `MAX_VERIFY_CLAIMS` | 25 | claims that reach the panel, ranked by importance then source quality |

Anything dropped by a cap is reported rather than silently discarded.

## When not to use it

- Exploring a codebase — use `Explore`, or the docs' forked-skill example.
- A question with one obvious authoritative source — a single `WebFetch` is
  cheaper and just as correct.
- An underspecified question. The workflow's `whenToUse` says to narrow scope
  first, because five search angles derived from a vague question produce five
  vague searches.
