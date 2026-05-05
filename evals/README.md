# Marketplace evals

Automated tests that show, for a given plugin in this marketplace, that loading its skill measurably improves Claude's responses on relevant tasks.

For each test case, the harness invokes `claude --print` twice — once with no skills loaded (`--bare`), once with the plugin under test loaded (`--bare --plugin-dir <plugin>`) — then scores both answers two ways:

1. **Rubric checks** — deterministic regex/keyword checks for specific idioms the skill teaches (e.g. `%w` for error wrapping, `context.Context` for goroutine lifetimes).
2. **LLM-as-judge** — head-to-head comparison by `claude-sonnet-4-6`, with the answers anonymized and randomized to avoid position bias.

Both runs use `--bare`, so they share the same auth path and disable hooks / auto-memory / `CLAUDE.md` auto-discovery — only plugin availability differs. That makes the comparison fair.

## Prerequisites

- `claude` on `PATH` (the Claude Code CLI).
- Python 3.11+.
- Auth for both the CLI runs and the SDK judge call. The harness mirrors the CLI's provider selection:
  - **Direct API**: `ANTHROPIC_API_KEY` exported.
  - **Vertex AI**: `CLAUDE_CODE_USE_VERTEX=1` and `ANTHROPIC_VERTEX_PROJECT_ID` set, plus `gcloud auth application-default login` done. Install with the `vertex` extra.
  - **Bedrock**: `CLAUDE_CODE_USE_BEDROCK=1` and standard AWS credentials. Install with the `bedrock` extra.

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
# Full Go suite (~3-5 min, ~$1-3 of API spend):
uv run python -m evals go

# Single case for a quick smoke test (~30s, ~$0.05):
uv run python -m evals go --cases error-wrapping

# Multiple cases:
uv run python -m evals go --cases error-wrapping goroutine-lifetime
```

Output lands in `evals/results/<plugin>-<UTC-iso>.{json,md}`. The JSON is the full structured record; the Markdown is the human-readable report (skim the headline + summary table, then dive into per-case detail).

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

## Cost & reproducibility

- Per case: 2 CLI completions + 1 judge call. Roughly $0.10–$0.50 per case depending on response length.
- The CLI runs do not currently let us set `temperature`, so there is some run-to-run variance. Rubric pass-rates are usually stable within ±1 case across re-runs; judge verdicts are mostly stable.
- Cases run in parallel (3 at a time); within a case, baseline and skill runs are serial.

## Negative control

To confirm the harness actually responds to skill quality, temporarily replace `backend/go/skills/go/SKILL.md` with a one-line stub and re-run — the skill-loaded rubric pass-rate should drop sharply. Revert when done.
