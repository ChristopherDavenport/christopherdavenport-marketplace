---
name: spanner
description: >
  Google Cloud Spanner: schema design, primary key / hotspot strategy,
  interleaving, transactions, query optimization, Go client SDK. Load when
  writing GoogleSQL DDL, picking a primary key or interleaving strategy,
  doing Spanner emulator work, or in code importing
  cloud.google.com/go/spanner. For local SQLite, use the sqlite skill
  instead.
---

# Google Cloud Spanner Best Practices

Spanner gives you horizontally scalable, externally consistent SQL — but the wrong primary key or transaction shape will silently cap your throughput and cause hotspots that look like outages. Many of these mistakes are *irreversible* in production: you cannot un-interleave a table, change primary key columns, or convert `STRING(36)` to `UUID`. This skill encodes the rules from Google's official Spanner docs so Claude can prevent these mistakes during schema design, query review, and Go client work.

## Scope

Covers: schema design; primary key strategy (UUIDs, `NEW_UUID`, `gen_random_uuid`, bit-reversed sequences, `BIT_REVERSED_POSITIVE`, `IDENTITY` columns, `GET_NEXT_SEQUENCE_VALUE`, `ShardId` with `FARM_FINGERPRINT`); interleaving (`INTERLEAVE IN PARENT`, interleaved indexes, `ON DELETE CASCADE`); secondary indexes (`STORING`/`INCLUDE`, `NULL_FILTERED`, `FORCE_INDEX`); query and DML optimization (`FORCE_JOIN_ORDER`, `JOIN_METHOD`, `STARTS_WITH`, `UNNEST`); transactions (`ReadOnlyTransaction`, `ReadWriteTransaction`, partitioned DML, stale / bounded-staleness reads, `MaxStaleness`, `WithTimestampBound`, external consistency, `Aborted` retries); session pool and leak diagnosis; commit timestamps (`PENDING_COMMIT_TIMESTAMP`); schema evolution (`ALTER TABLE NOT NULL`, DDL updates); Go client (`row.ToStruct`, `BufferWrite`, `spanner.Mutation`, `spanner.NullString` / `NullInt64`); the Spanner emulator.

## Core Rules

These cross-cut almost every Spanner task. Internalize them before reaching for a topic-specific reference.

- **Never lead a primary key (or non-interleaved index) with a monotonically increasing column** — sequential integers, `AUTO_INCREMENT`, `SERIAL`, `CURRENT_TIMESTAMP`. All writes pile onto one split, capping throughput at one server's limit.
- **Default to UUIDv4, bit-reversed sequences, or `IDENTITY (BIT_REVERSED_POSITIVE)`** for surrogate keys. Use `NEW_UUID()` (GoogleSQL) or `gen_random_uuid()` (PostgreSQL). For natural-but-monotonic keys (timestamps), prepend a hash-derived `ShardId = MOD(FARM_FINGERPRINT(...), N)` where `N ≈ node count`.
- **Interleaving is permanent** — `INTERLEAVE IN PARENT` cannot be undone after the table exists. Same for adding/removing key columns. Decide before the table holds production data.
- **Index leading-column rules are the same as PK leading-column rules.** A `CREATE INDEX … ON T(commit_timestamp)` is a hotspot waiting to fire.
- **Keep read-write transactions short and small.** No large scans inside `ReadWriteTransaction`. Hard limits: **80,000 mutations per transaction, 100 MiB per commit, 7 levels of interleave depth.**
- **Always parameterize queries.** Use `@param` and `UNNEST(@list)`. Use `STARTS_WITH(col, @prefix)` instead of `col LIKE @prefix` — `LIKE` with a parameter blocks plan caching and forces a full scan.
- **In Go: always defer `client.Close()`, `iter.Stop()` (or use `iter.Do()`), and `txn.Close()` for `ReadOnlyTransaction`.** Skipping any of these leaks sessions and eventually wedges the pool.
- **Use `ReadOnlyTransaction` (or `Single().WithTimestampBound(MaxStaleness(...))`) for reads.** Read-only transactions hold no locks and never abort during execution.
- **Adding `NOT NULL` to a column with NULLs immediately rejects writes** before validation completes — even if the schema update later rolls back, you've had an outage. Validate data first.
- **`ORDER BY` is required for any ordered result.** Spanner does not preserve insert order; result order changes between invocations without `ORDER BY`.
- **Co-locate related rows.** Interleaving and hash-shard prefixes both pay off because distributed transactions across splits cost more (more participants, more abort risk).
- **`ReadWriteTransaction` in the Go client auto-retries `Aborted` errors.** Make the transaction function pure with respect to side effects — it can run multiple times. No external state mutation, no log spam, no API calls inside the closure.

## When to Use Each Concept

| Scenario | Use | Why |
|---|---|---|
| Surrogate primary key for a new table | `NEW_UUID()` or `IDENTITY (BIT_REVERSED_POSITIVE)` | Random distribution; no hotspot at scale |
| Time-ordered log with high write rate | `(ShardId, EventTime DESC, ...)` where `ShardId = MOD(FARM_FINGERPRINT(...), N)` | Spreads writes across N splits while keeping recent rows adjacent |
| "Newest N rows for this user" query | `(UserId, EventTime DESC)` PK or interleaved index | DESC keeps recent rows adjacent under each parent |
| Child rows almost always read with parent | `INTERLEAVE IN PARENT … ON DELETE CASCADE` | Co-located on disk; joins are local; cascade cleans up |
| Cross-row referential integrity without locality | `FOREIGN KEY` (not interleave) | Interleaving is permanent; FK is reversible |
| Cover an index lookup without a base-table read | `STORING (col1, col2, ...)` (GoogleSQL) / `INCLUDE` (PostgreSQL) | Eliminates the second key-range read |
| Index a sparse/optional column | `CREATE NULL_FILTERED INDEX` *plus* `WHERE col IS NOT NULL` in queries | Smaller index; **forgetting the WHERE filter skips the index** |
| Multiple consistent reads | `client.ReadOnlyTransaction()` (defer Close) | Same timestamp across all reads; no locks; no aborts |
| Single read that doesn't need strict freshness | `client.Single().WithTimestampBound(MaxStaleness(10*time.Second))` | Lower latency, can be served by any replica |
| Update-after-read where the write depends on the read | `client.ReadWriteTransaction` | Only transaction type with read-then-write atomicity |
| Bulk update/delete of millions of rows | Partitioned DML (`PartitionedUpdate`) | Bypasses the 80K mutation / 100 MiB transaction limits; idempotent only |
| Many independent inserts/updates in one trip | `client.Apply([]*spanner.Mutation{...})` | Cheaper than DML for blind writes; respects mutation limits |
| Prefix match on a column | `STARTS_WITH(col, @prefix)` | Plan-cacheable, uses index; `LIKE @x` forces a scan |
| List membership filter | `WHERE k IN UNNEST(@keys)` | Parameter-friendly; lets optimizer use seek operations |
| Filter by recently-modified rows | `WHERE commit_ts > @cutoff` with `OPTIONS (allow_commit_timestamp=true)` column | Spanner can prune by commit-timestamp metadata |
| Need `now()` written by Spanner itself | `spanner.CommitTimestamp` (Go) / `PENDING_COMMIT_TIMESTAMP()` (SQL) | True commit-time, monotonic per-key; do not put it in the leading PK |

## Examples

Example 1: User says "our Spanner write throughput is flat at ~2k QPS no matter how many nodes I add"
Actions:
1. Inspect the schema for monotonic leading PK columns (`Id INT64 GENERATED BY DEFAULT AS IDENTITY` *without* `BIT_REVERSED_POSITIVE`, plain timestamps, sequence columns).
2. Confirm with a hotspot check: `SELECT COUNT(*) FROM ... GROUP BY MOD(FARM_FINGERPRINT(CAST(pk AS STRING)), 100)` should be roughly uniform.
3. Migrate to `NEW_UUID()`, `IDENTITY (BIT_REVERSED_POSITIVE)`, or a `ShardId` prefix — see [references/schema-design.md](references/schema-design.md).
Result: Writes spread across splits; throughput scales with nodes again.

Example 2: User says "my Go service keeps logging `Aborted` errors and the request latency is spiking"
Actions:
1. Find the `ReadWriteTransaction` callback. Audit it for: large reads (`SELECT *` without a key predicate), external API calls, long CPU work, side effects (logging that double-fires on retry).
2. Move read-only work out into a `ReadOnlyTransaction` or `Single()` read.
3. Confirm the closure is pure — `Aborted` triggers an automatic retry by the client; impure closures cause double-effects. See [references/transactions.md](references/transactions.md) and [references/go-client.md](references/go-client.md).
Result: Transactions are short, abort rate falls, latency stabilizes.

Example 3: User says "this query is slow, the index isn't being used: `SELECT ... WHERE name LIKE @prefix`"
Actions:
1. Replace `name LIKE @prefix` with `STARTS_WITH(name, @prefix)` (or anchor: `name >= @prefix AND name < @prefix_end`).
2. Confirm the index covers the columns needed; add a `STORING` clause if the query reads non-key columns.
3. Force the optimizer with `@{FORCE_INDEX=...}` only after confirming the index helps via `EXPLAIN`. See [references/queries-and-dml.md](references/queries-and-dml.md) and [references/indexes.md](references/indexes.md).
Result: Query uses the index; latency drops from full-scan to index seek.

## Troubleshooting

| Symptom | Reference |
|---|---|
| Write throughput plateaus regardless of node count; `Latency by key range` shows one hot split | [references/schema-design.md](references/schema-design.md) |
| Need to split a large `ShardId` table; choosing N; UUID vs bit-reversed vs hash; ARRAY in PK errors | [references/schema-design.md](references/schema-design.md) |
| Joins between parent/child are slow; want CASCADE delete; hit "INTERLEAVE depth exceeded"; trying to un-interleave | [references/interleaving.md](references/interleaving.md) |
| Index not used; `NULL_FILTERED` index returns wrong rows; sparse column index too big; over-indexing slows commits | [references/indexes.md](references/indexes.md) |
| `ABORTED`/`FAILED_PRECONDITION` retries; deadlocks; "transaction too large"; partitioned DML idempotency; lock contention | [references/transactions.md](references/transactions.md) |
| `LIKE @x` not using index; `BETWEEN` over sparse keys; missing `ORDER BY`; need rows-modified count; `THEN RETURN` | [references/queries-and-dml.md](references/queries-and-dml.md) |
| Session pool exhausted; `defer iter.Stop()` missing; nullable column into `string`; `ToStruct` field tags; auto-retry side effects | [references/go-client.md](references/go-client.md) |
| `ALTER TABLE` taking hours; `NOT NULL` add caused outage; can't drop interleaved table; `STRING(36)` ↔ `UUID` fails | [references/schema-evolution.md](references/schema-evolution.md) |

## Topic References

- [Schema Design](references/schema-design.md) — primary keys, hotspots, UUID / bit-reversed / IDENTITY, hash sharding, key reordering, ARRAY-in-PK, multi-tenant patterns
- [Interleaving](references/interleaving.md) — `INTERLEAVE IN PARENT`, `ON DELETE CASCADE`, locality, depth limit, when to choose interleave over foreign keys, irreversibility
- [Secondary Indexes](references/indexes.md) — `CREATE INDEX`, `STORING` / `INCLUDE`, `NULL_FILTERED`, `INTERLEAVE IN`, `FORCE_INDEX`, descending columns, leading-key hotspots
- [Transactions](references/transactions.md) — read-only vs read-write vs partitioned DML, lock model, abort/retry semantics, mutation/size limits, deadlocks, external consistency
- [Queries & DML](references/queries-and-dml.md) — parameterized queries, `STARTS_WITH`, `UNNEST`, `ORDER BY` requirements, `THEN RETURN` / `RETURNING`, query hints, commit-timestamp filtering, mutation vs DML
- [Go Client SDK](references/go-client.md) — `cloud.google.com/go/spanner`: session pool, `defer` discipline, `NullString`/`NullInt64`, `row.ToStruct`, `Mutation`, stale reads, leak detection, error inspection
- [Schema Evolution](references/schema-evolution.md) — `gcloud spanner databases ddl update`, validation timelines, `NOT NULL` outage, unsupported conversions, view invalidation, batching index creates

## Sources

All recommendations trace back to Google's official documentation. When recommending a specific syntax or limit, prefer fetching the live page over relying on this skill's cached digest:

- https://cloud.google.com/spanner/docs/schema-design
- https://cloud.google.com/spanner/docs/schema-and-data-model
- https://cloud.google.com/spanner/docs/primary-key-default-value
- https://cloud.google.com/spanner/docs/secondary-indexes
- https://cloud.google.com/spanner/docs/transactions
- https://cloud.google.com/spanner/docs/sql-best-practices
- https://cloud.google.com/spanner/docs/dml-tasks
- https://cloud.google.com/spanner/docs/schema-updates
- https://pkg.go.dev/cloud.google.com/go/spanner
