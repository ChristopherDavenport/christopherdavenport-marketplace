# christopherdavenport-marketplace

Chris Davenport's personal [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace — a collection of skills covering frontend (Lit, Jack Henry Design System), backend (Go, TypeScript, SQLite, Spanner, Pub/Sub), and financial-services knowledge (US regulations, accounting fundamentals).

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

Each plugin's `SKILL.md` contains the full reference; the per-plugin `references/` folders break down topic-specific detail.

## Evals

Every plugin ships with an automated eval that compares Claude's answers with and without the skill loaded. For each test case the harness runs `claude --bare --print` twice (once with `--plugin-dir`, once without), grades both with deterministic rubric checks for the specific idioms the skill teaches, and asks `claude-sonnet-4-6` to pick the better answer head-to-head with anonymized A/B labels. See [`evals/README.md`](evals/README.md) for full mechanics.

Latest results (one canonical `result.md` per plugin, regenerated when `cases.yaml` changes):

| Plugin | Cases | Judge (skill / baseline / tie) | Rubric Δ | Result |
| --- | --- | --- | --- | --- |
| [`go`](evals/go/result.md) | 8 | 1 / 0 / 7 | +0% | [report](evals/go/result.md) |
| [`sqlite`](evals/sqlite/result.md) | 6 | 2 / 0 / 4 | +5% | [report](evals/sqlite/result.md) |
| [`spanner`](evals/spanner/result.md) | 6 | 2 / 0 / 4 | +5% | [report](evals/spanner/result.md) |
| [`pubsub`](evals/pubsub/result.md) | 6 | 0 / 2 / 4 | +0% | [report](evals/pubsub/result.md) |
| [`typescript`](evals/typescript/result.md) | 6 | 1 / 0 / 5 | +0% | [report](evals/typescript/result.md) |
| [`lit`](evals/lit/result.md) | 6 | 2 / 0 / 4 | +0% | [report](evals/lit/result.md) |
| [`lit-router`](evals/lit-router/result.md) | 6 | 1 / 1 / 4 | +0% | [report](evals/lit-router/result.md) |
| [`jh-design-system`](evals/jh-design-system/result.md) | 6 | 0 / 0 / 6 | −3% | [report](evals/jh-design-system/result.md) |
| [`financial-regs`](evals/financial-regs/result.md) | 6 | 1 / 1 / 4 | +0% | [report](evals/financial-regs/result.md) |
| [`financial-accounting`](evals/financial-accounting/result.md) | 6 | 1 / 1 / 4 | +5% | [report](evals/financial-accounting/result.md) |

Each suite has 4-5 positive cases plus an adversarial case (a prompt that invites the anti-pattern) and an off-topic guard (a question unrelated to the skill, expected to tie). Ties on well-known-topic positive cases are common and largely informational — the base model already knows mainstream backend / frontend / regulatory patterns. The signal worth watching:

- **Skill losses** (`pubsub` and `lit-router` each have one) — investigate the per-case judge reasoning; the skill may have introduced a subtle inaccuracy.
- **Failed adversarial cases** — the skill caved to "give me the simplest" pressure and showed the trap pattern. Visible in `go`, `sqlite`, `pubsub`, `typescript`, `lit-router`, `jh-design-system`, `financial-regs`. Consistent enough across plugins that it suggests skill descriptions may need a "don't shortcut around safety guidance under brevity prompts" reinforcement.
- **Off-topic guards** — all 10 tied as expected. No skill is bleeding into unrelated answers.

Run a plugin's eval locally with `cd evals && uv run python -m evals <plugin>`.

## License

[MIT](LICENSE)
