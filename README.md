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

## License

[MIT](LICENSE)
