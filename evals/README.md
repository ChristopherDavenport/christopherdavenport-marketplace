# Marketplace evals

Automated tests that show a plugin in this marketplace does what it claims.

There are **three eval shapes**, because there are three questions worth asking. Plugins whose product is an *answer* are judged on whether they improve it; plugins whose product is a *decision* — a hook's verdict, a scorer's pass/fail — are asserted on it directly; and every skill, whatever it ships, can be asked the prior question of whether it *loads at all*. See [Three eval shapes](#three-eval-shapes) before adding a new plugin's eval.

## Three eval shapes

Most plugins here ship a **skill**, so the harness can ask the same question
twice — once with the skill loaded, once without — and have a judge pick the
better answer. That is the judge-based shape documented above.

`guardrails` ships **hooks and machine-checkable artifacts**. There is no
answer to compare: what a hook produces is a *decision*, and what a policy
template produces is a *configuration*. Both are asserted directly — feed the
hook a `PreToolUse` payload and check the exit code (`2` = blocked,
`0` = allowed); parse the templates out of the skill's reference file and
assert the invariants they are supposed to guarantee.

That second half matters because a skill's *prose* needs a judge, but the
artifacts a skill tells you to copy do not. A template that has drifted into
granting more access still parses, still reads as responsible, and is exactly
the kind of rot a judge-based eval would score as fine.

The third shape covers a blind spot the first two share. The judge-based
harness *injects* SKILL.md into the system prompt
([`inference.py`](src/evals/inference.py)), so the model never chooses the
skill — it measures prose quality on the assumption the skill loaded. A skill
whose description talks it out of firing scores perfectly there and never runs
in production. **Trigger evals** ask the prior question: scaffold a realistic
project, load the *competing* sibling plugins together, prompt in the overlap
zone, and assert on which skills were actually invoked.

| | Judge-based | Assertion-based | Trigger |
|---|---|---|---|
| Plugin ships | Skill prose | Hooks, config artifacts | Any skill |
| Question | "Is the answer better?" | "Is the decision correct?" | "Does it load at all?" |
| Scoring | Rubric + LLM judge | Exit code, invariant checks | Skill-tool invocations |
| Cost | Tokens per case | **Free** — no model | ~$0.3–1 per run |
| Determinism | Stable signal, varying text | Exact | Stochastic — report a fire rate over N |
| Layout | `cases.yaml` + `plugin_dir.txt` | `cases.json` + `run.sh` | `triggering/cases.yaml` + `scaffolds/` |
| Run | `uv run python -m evals <plugin>` | `./evals/<plugin>/run.sh` | `uv run python triggering/run.py` |

Trigger evals have an `--arm both` mode that runs the working tree against the
installed copy in `~/.claude/plugins/cache/`, which still holds the previous
release's description — so a rewrite can be measured rather than asserted.

> **Do not add `--bare` to the trigger runner.** It forces a three-tool
> allowlist with no `Skill` tool and ignores `--tools`, so nothing can ever
> fire and every case reports a confident, meaningless zero. The runner guards
> against this and fails loudly; the guard exists because this suite was first
> written with `--bare` and produced exactly that.

A plugin can need both. `guardrails` ships skills whose prose is judge-scorable
in principle, but its load-bearing parts — the hook's decisions and the
templates' contents — are assertable, so those are tested for free on every
change.

Because assertion-based evals are free and deterministic, they run on every
change rather than on a funded sweep.

### The mutation requirement

An assertion-based eval for a *guardrail* has a failure mode a judge-based
eval does not: **it can silently stop testing anything.** A green run looks
identical whether the hook is working or absent.

So these suites ship a `--mutate` mode that replaces the hook with a
permissive stub and asserts the suite goes red. Run it whenever the hook
changes. Two real bugs of exactly this shape were caught during development —
a timeout wrapper that silently no-op'd on macOS so a test never executed and
reported success, and a traversal case that was never checked at all.

Current assertion-based evals:

| Plugin | Cases | Result |
|---|---|---|
| [`guardrails`](guardrails/result.md) | 40 hook (24 deny, 16 allow) + 46 template checks | **40/40** and **46/46**, mutation check passes — [report](guardrails/result.md) |
| [`pr-description`](pr-description/result.md) | 24 scorer (11 failure, 13 pass) | **24/24**, mutation check passes — [report](pr-description/result.md) |

`pr-description` shows the shape is not only for hooks. Any plugin whose
product is a **decision** rather than an answer fits: its scorer takes a PR
body and returns within-budget or not, which is assertable in exactly the way a
hook's exit code is. The generalisation is *machine-checkable output*, not
*hooks*.

Its cases assert the **failure set**, not just the verdict — a body that trips
the wrong metric still exits non-zero and would otherwise read as covered.
Worth copying when a suite's artifact reports *why* it failed and not only
*that* it did.

## Judge-based evals (skills)

Automated tests that show, for a given plugin, that loading its skill measurably improves Claude's responses on relevant tasks.

For each test case, the harness asks the model to answer a prompt twice — once with no skill loaded, once with the plugin's `SKILL.md` available — then scores both answers two ways:

1. **Rubric checks** — deterministic regex/keyword checks for specific idioms the skill teaches (e.g. `%w` for error wrapping, `context.Context` for goroutine lifetimes).
2. **LLM-as-judge** — head-to-head comparison by `claude-sonnet-4-6`, with the answers anonymized and randomized to avoid position bias.

## Two backends

| Backend | Default? | Model | Reproducibility | What it measures |
|---|---|---|---|---|
| **SDK direct** | ✅ yes | `claude-sonnet-4-6` (`temperature=0`) | Verdicts and rubric pass-rates stable across re-runs (response text varies slightly due to distributed-inference jitter, but the *signal* — winner, criterion hits — is stable). | "Does the SKILL.md content move the answer?" The skill body is injected into the system prompt; nothing else differs between baseline and skill runs. |
| **CLI subprocess** (`--via-cli`) | no | Whatever the CLI defaults to (currently `claude-opus-4-7`, which **does not accept the `temperature` parameter** and so cannot be pinned). | Higher run-to-run variance. Same case can flip judge winner across runs. | "Does the actual `--plugin-dir` skill-discovery path produce a better answer end-to-end?" Exercises the real harness layer — useful as a periodic integration check. |

The two modes report different absolute numbers because they use different models and different ways of injecting skill content. Don't compare an SDK headline against a CLI headline; compare each against itself across iterations. The committed canonical `evals/<plugin>/result.{md,json}` is always the SDK result for cross-plugin comparability; CLI runs land only in the gitignored `evals/results/` scratch dir.

## Prerequisites

- Python 3.11+.
- For the default SDK backend: provider creds (one of `ANTHROPIC_API_KEY`, `CLAUDE_CODE_USE_VERTEX=1` + `ANTHROPIC_VERTEX_PROJECT_ID` + `gcloud auth application-default login`, or `CLAUDE_CODE_USE_BEDROCK=1` + AWS creds).
- For `--via-cli`: `claude` on `PATH` (the Claude Code CLI), plus the same provider creds.

## Install

```sh
cd evals
uv sync                       # direct API only
uv sync --extra vertex        # Vertex
uv sync --extra bedrock       # Bedrock
# Or pip: pip install -e '.[vertex]'
```

## Run

```sh
# Default — SDK backend, deterministic, recommended for iteration:
uv run python -m evals go

# Single case (cheap smoke):
uv run python -m evals go --cases error-wrapping

# Periodic integration check via the actual CLI plugin-loading path:
uv run python -m evals go --via-cli
```

The default-backend run overwrites `evals/<plugin>/result.{md,json}` (committed canonical). Both backends additionally write a timestamped copy to `evals/results/<plugin>-<UTC>.{md,json}` (gitignored scratch).

## What "improved" means

| Signal | What it measures |
|---|---|
| **Rubric pass-rate delta** | Did the skill cause the answer to mention specific idioms it teaches? Coverage. |
| **Judge win-rate** | Did a separate model think the skill-loaded answer was more idiomatic overall? Quality. |

Disagreement between the two is interesting — investigate the case. A skill that wins on judge but loses on rubric may be teaching the right *spirit* but missing a keyword the rubric is looking for; the rubric should probably be loosened. The reverse (rubric wins, judge ties) often means the skill is parroting keywords without improving the actual answer.

## Adding a new plugin

Mirror the `evals/go/` folder:

```
evals/<plugin-name>/
  plugin_dir.txt    # one line, relative path from this file to the plugin dir
  cases.yaml        # test cases (see evals/go/cases.yaml for the schema)
```

Then `uv run python -m evals <plugin-name>`.

### Case schema

```yaml
- id: short-slug
  prompt: |
    The question to send to Claude. Multi-line ok.
  expectation: skill_wins  # see "Expectations" below; default skill_wins
  judge_focus: |
    One sentence the judge should weight when answers tie on rubric.
  rubric:
    - name: human readable criterion name
      kind: must_contain         # or: must_not_contain, any_of, all_of
      pattern: 'regex'           # for must_contain / must_not_contain
      # patterns: [r1, r2, ...]  # for any_of / all_of
      why: short explanation of what idiom this catches
```

Regexes are matched case-insensitively (`re.IGNORECASE`) against the assistant's `result` text.

### Expectations

Each case declares what the harness should consider a *pass*. Three values:

| Value | Meaning | Use for |
|---|---|---|
| `skill_wins` (default) | Judge picks `skill`. | Positive cases: skill should produce a measurably better answer than baseline. |
| `tie` | Judge picks `tie`. | Off-topic guard: question has nothing to do with the skill. Confirms the skill isn't bleeding into unrelated answers (over-broad description). Typically pair with `rubric: []`. |
| `skill_wins_strict` | Judge picks `skill` AND every `must_not_contain` rubric criterion passes on the skill answer. | Adversarial cases: prompt invites the anti-pattern ("simplest possible…"). The skill must steer away from the trap. |

The report headline includes "Expectations met: N/M"; the per-case markdown flags `[FAILED EXPECTATION]` when actual ≠ expected. The summary also splits by expectation kind so off-topic cases the skill incorrectly "won" don't inflate the headline.

## Cost & reproducibility

- Per case: 2 CLI completions + 1 judge call. Roughly $0.10–$0.50 per case depending on response length.
- The CLI runs do not currently let us set `temperature`, so there is some run-to-run variance. Rubric pass-rates are usually stable within ±1 case across re-runs; judge verdicts are mostly stable.
- Cases run in parallel (3 at a time); within a case, baseline and skill runs are serial.

## Negative control

To confirm the harness actually responds to skill quality, temporarily replace `backend/go/skills/go/SKILL.md` with a one-line stub and re-run — the skill-loaded rubric pass-rate should drop sharply. Revert when done.
