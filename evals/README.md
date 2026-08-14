# Marketplace evals

Automated tests that show a plugin in this marketplace does what it claims.

There are **two eval shapes**, because there are two kinds of plugin here. Skill-shipping plugins are judged on whether they improve an answer; hook-shipping plugins are asserted on the decisions they make. See [Two eval shapes](#two-eval-shapes) before adding a new plugin's eval.

## Two eval shapes

Most plugins here ship a **skill**, so the harness can ask the same question
twice — once with the skill loaded, once without — and have a judge pick the
better answer. That is the judge-based shape documented above.

`guardrails` ships **hooks**. There is no answer to compare: what a hook
produces is a *decision*. So it is evaluated by assertion instead — feed the
hook a `PreToolUse` payload and check the exit code (`2` = blocked,
`0` = allowed).

| | Judge-based | Assertion-based |
|---|---|---|
| Plugin ships | Skills | Hooks |
| Question | "Is the answer better?" | "Is the decision correct?" |
| Scoring | Rubric + LLM judge | Exit code |
| Cost | Tokens per case | **Free** — no model |
| Determinism | Stable signal, varying text | Exact |
| Layout | `cases.yaml` + `plugin_dir.txt` | `cases.json` + `run.sh` |
| Run | `uv run python -m evals <plugin>` | `./evals/<plugin>/run.sh` |

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
| [`guardrails`](guardrails/result.md) | 34 (24 deny, 10 allow) | **34/34**, mutation check passes — [report](guardrails/result.md) |

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
