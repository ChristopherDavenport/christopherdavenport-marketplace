# christopherdavenport-marketplace

Chris Davenport's personal [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace — a collection of skills covering frontend (Lit, Jack Henry Design System), backend (Go, TypeScript, SQLite, Spanner, Pub/Sub), financial-services knowledge (US regulations, accounting fundamentals), and safety (harness-enforced guardrails for agentic sessions).

## Install

Add the marketplace, then install the plugins you want:

```
/plugin marketplace add christopherdavenport/christopherdavenport-marketplace
/plugin install <plugin-name>@christopherdavenport
```

For example: `/plugin install go@christopherdavenport`.

## Plugins

| Plugin | Category | Description |
| --- | --- | --- |
| [`financial-accounting`](knowledge/financial-accounting) | knowledge | Financial institution accounting fundamentals (journals, ledgers, sub-ledgers, chart of accounts) and US GAAP (FASB ASC) reference for FI operations. |
| [`financial-regs`](knowledge/financial-regs) | knowledge | US financial regulation lookup and compliance analysis. |
| [`lit`](frontend/lit) | frontend | Lit web component library expertise. |
| [`lit-router`](frontend/lit-router) | frontend | `@lit-labs/router` expertise. |
| [`jh-design-system`](frontend/jh-design-system) | frontend | Jack Henry Design System (jackhenry.design/v2) — components, foundations, tokens, content. |
| [`go`](backend/go) | backend | Go language best practices — Effective Go, Google + Uber style guides, Code Review Comments, modern stdlib (errors, context, slog, generics). |
| [`typescript`](backend/typescript) | backend | TypeScript best practices — type system, generics, utility & advanced types, discriminated unions, classes & OOP, error handling, async & cancellation, immutability, modules, strict tsconfig, naming, testing, plus a dedicated section on functional patterns. |
| [`sqlite`](backend/sqlite) | backend | SQLite best practices — STRICT tables, must-set pragmas, BEGIN IMMEDIATE vs DEFERRED, indexes and EXPLAIN QUERY PLAN, JSON1/JSONB, the Go client, and server-side production use (Litestream/LiteFS/Turso/D1). |
| [`spanner`](backend/spanner) | backend | Google Cloud Spanner best practices — schema design, interleaving, indexes, transactions, query/DML optimization, schema evolution, and the Go client SDK. |
| [`pubsub`](backend/pubsub) | backend | Google Cloud Pub/Sub best practices — topics & schemas, subscription types, delivery guarantees, ordering, dead-letter, ack deadline / lease, publisher batching, and the Go client SDK. |
| [`commit-story`](workflow/commit-story) | workflow | Split a batch of uncommitted work into a sequence of meaningful, individually-reviewable commits with reviewer-grade messages, guaranteeing the final tree is byte-identical to the start. |
| [`excalidraw`](workflow/excalidraw) | workflow | Read, create, and edit Excalidraw (`.excalidraw`) diagrams as data — inspect/summarize, generate schema-valid diagrams and flowcharts, add/move/restyle/connect shapes with bound arrows and labels, convert simple Mermaid, and validate. Export to PNG/SVG is documented (external tooling), not performed in-process. |
| [`pr-description`](workflow/pr-description) | workflow | Write a PR title and body a reviewer can act on in under a minute, sized to the change and to whatever pull-request template the repo ships. Requires a 15–60 word lead before the first heading, holds the body to a density budget tiered on diff size, and moves the record of how the work went into a follow-up comment. Ships a scorer the skill runs on its own draft before presenting it. |
| [`guardrails`](safety/guardrails) | safety | Containment for agentic sessions, built on Claude Code's OS-level sandbox rather than around it — a `sandbox-policy` skill covering the settings keys, the scopes that silently ignore misplaced keys, and four validated policy templates; `/guardrails-setup` to generate and install a policy the repo's build survives; `/guardrails-doctor` to report what is enforced rather than what is configured. Hooks cover only what the sandbox can't see: credential shapes in outbound MCP/`WebFetch` payloads, Bash calls that opt out with `dangerouslyDisableSandbox`, an audit log, and an opt-in `Stop` gate that refuses to let an agent finish on a red build. |

Each plugin's `SKILL.md` contains the full reference; the per-plugin `references/` folders break down topic-specific detail.

## Evals

Plugins here carry one of [two eval shapes](evals/README.md#two-eval-shapes). Plugins whose product is an *answer* use the judge-based sweep below. Plugins whose product is a *decision* — `guardrails`' hook verdicts, `pr-description`'s budget scorer — are asserted directly, which is free and deterministic, so those suites run on every change instead of appearing in this table.

The judge-based harness compares Claude's answers with and without the skill loaded across three models — Haiku 4.5, Sonnet 4.6, and Opus 4.7. For each (case × model) the harness calls the model twice via the SDK at `temperature=0` (Sonnet/Haiku) — once with no system prompt, once with the plugin's `SKILL.md` injected — grades both answers with deterministic rubric checks, and asks `claude-sonnet-4-6` to pick the better answer head-to-head with anonymized A/B labels. See [`evals/README.md`](evals/README.md) for full mechanics.

Latest results — judge wins per model (`skill / baseline / tie` out of 8–10 cases):

| Plugin | Haiku | Sonnet | Opus¹ | Result |
| --- | --- | --- | --- | --- |
| [`go`](evals/go/result.md) | **9 / 0 / 1** | 7 / 1 / 2 | **7 / 0 / 3** | [report](evals/go/result.md) |
| [`sqlite`](evals/sqlite/result.md) | 7 / 1 / 0 | **7 / 0 / 1** | 6 / 1 / 1 | [report](evals/sqlite/result.md) |
| [`spanner`](evals/spanner/result.md) | 7 / 1 / 0 | 7 / 1 / 0 | **7 / 0 / 1** | [report](evals/spanner/result.md) |
| [`pubsub`](evals/pubsub/result.md) | **7 / 0 / 1** | **6 / 0 / 2** | **7 / 0 / 1** | [report](evals/pubsub/result.md) |
| [`typescript`](evals/typescript/result.md) | **7 / 0 / 1** | **4 / 0 / 4** | **4 / 0 / 4** | [report](evals/typescript/result.md) |
| [`lit`](evals/lit/result.md) | 7 / 1 / 1 | 5 / 1 / 3 | 5 / 1 / 3 | [report](evals/lit/result.md) |
| [`lit-router`](evals/lit-router/result.md) | **8 / 0 / 1** | 6 / 1 / 2 | 4 / 2 / 3 | [report](evals/lit-router/result.md) |
| [`jh-design-system`](evals/jh-design-system/result.md) | 7 / 1 / 0 | 6 / 1 / 1 | **7 / 0 / 1** | [report](evals/jh-design-system/result.md) |
| [`financial-regs`](evals/financial-regs/result.md) | 7 / 2 / 0 | 7 / 1 / 1 | 6 / 2 / 1 | [report](evals/financial-regs/result.md) |
| [`financial-accounting`](evals/financial-accounting/result.md) | 7 / 2 / 0 | 6 / 1 / 2 | **8 / 0 / 1** | [report](evals/financial-accounting/result.md) |

**Bold** = no baseline wins (skill never made answers worse). ¹ Opus does not accept the `temperature` parameter — its column is an indicator, not a measurement (re-runs may flip individual verdicts).

Total spend for one full 3-model sweep across all 10 plugins: **~$26**.

### Reading the table

- **Look across the row.** A skill that wins on Haiku and Sonnet but ties on Opus is one Opus users can probably skip — Opus already knows the material. A skill that wins everywhere is universally worth installing.
- **Smaller models tend to gain more.** The skill content provides bigger lift when the baseline is weaker. Haiku columns are the strongest "should I install this?" signal because they show maximum potential value.
- **Baseline wins are the alarm.** A 1 in the middle of the cell means the skill made at least one answer *worse* than no skill. Investigate the per-case judge reasoning in the linked report.

### Default eval mode going forward

Iteration uses **Sonnet + Haiku** (the deterministic pair) — `uv run python -m evals <plugin>` runs both at temperature 0, no Opus. That sweep is ~$1 per plugin and produces stable verdicts you can diff between SKILL.md edits. Opus is opt-in via `--models sonnet,haiku,opus` for the periodic full-picture refresh; its column in the canonical may go stale in between.

Each suite has 6-8 positive cases plus an adversarial case (a prompt that invites the anti-pattern) and an off-topic guard (a question unrelated to the skill, expected to tie).

Run a plugin's eval locally with `cd evals && uv run python -m evals <plugin>`.

## License

[MIT](LICENSE)
