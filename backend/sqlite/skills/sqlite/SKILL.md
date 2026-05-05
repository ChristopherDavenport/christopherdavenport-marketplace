---
name: sqlite
description: >
  SQLite best practices: pragmas (WAL, busy_timeout, foreign_keys), locking
  model, BEGIN modes, index design, JSON1, Go client patterns, Litestream /
  LiteFS / D1. Use for .sqlite/.db files or Go code importing
  modernc.org/sqlite or mattn/go-sqlite3. Not for the spanner skill or
  client/server SQL.
---

# SQLite Best Practices

SQLite is the most-deployed database in the world precisely because it gets out of your way: zero-config, embedded, ACID, one file. That same minimalism hides the sharp edges. The default journal mode is `DELETE` (slow, contended), foreign keys are off by default *per connection*, types are advisory under the legacy affinity rules, and the difference between `BEGIN DEFERRED` and `BEGIN IMMEDIATE` is the difference between a clean writer queue and a flood of `SQLITE_BUSY` errors under any real load. This skill encodes the rules from sqlite.org so Claude can prevent these mistakes during schema design, query review, pragma configuration, and Go client work.

## Scope

Covers: schema design with type affinity and `STRICT` tables; primary keys (rowid alias, `WITHOUT ROWID`, `AUTOINCREMENT` cost); generated columns; the must-set pragmas (`journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout`, `cache_size`, `temp_store`, `mmap_size`, `optimize`); the locking model (`UNLOCKED`/`SHARED`/`RESERVED`/`PENDING`/`EXCLUSIVE`) and how WAL changes it; `BEGIN IMMEDIATE` vs `DEFERRED` vs `EXCLUSIVE`; `SQLITE_BUSY` / `SQLITE_LOCKED` / `SQLITE_BUSY_SNAPSHOT` recovery; reading `EXPLAIN QUERY PLAN`; index design (covering, partial, expression); JSON1 / JSONB (`json_extract`, `json_each`, generated-column indexing, `->` / `->>`); the Go client (`database/sql` with `mattn/go-sqlite3` or `modernc.org/sqlite`, DSN pragma syntax, two-pool writer/reader pattern, context cancellation, NULL scanning, `VACUUM INTO` from Go); server-side production use (Litestream / LiteFS / Turso libSQL / Cloudflare D1 patterns, online backup vs `cp`, migrating a live database).

## Core Rules

These cross-cut almost every SQLite task. Internalize them before reaching for a topic-specific reference.

- **Set `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, and `busy_timeout=5000` on every connection.** `journal_mode` and `synchronous` persist with the file; `foreign_keys` and `busy_timeout` are *per-connection* and reset every time `database/sql` opens a fresh one. The pragmas belong in the DSN, not in a one-off `Exec` after open.
- **Use `STRICT` tables for new schemas.** Without `STRICT`, SQLite happily stores `'banana'` in an `INTEGER` column under type affinity. With `STRICT`, you get the static typing every other database has had for decades.
- **`INTEGER PRIMARY KEY` is the rowid alias and is what you almost always want.** Skip `AUTOINCREMENT` — it adds a write to `sqlite_sequence` on every insert and only changes behavior in the corner case of guaranteeing rowids never reuse deleted values. `INTEGER PRIMARY KEY` alone is monotonic enough for ordinary use.
- **`WITHOUT ROWID` is for narrow tables with a non-`INTEGER` composite primary key.** Don't reach for it by default — wide rows, large `TEXT`/`BLOB` columns, and anything that would otherwise use `INTEGER PRIMARY KEY` belong in a regular rowid table.
- **Use `BEGIN IMMEDIATE` for any transaction that will write.** The default `BEGIN DEFERRED` upgrades from `SHARED` to `RESERVED` on the first write, and that upgrade is what triggers `SQLITE_BUSY` under contention. `BEGIN IMMEDIATE` acquires `RESERVED` up front, so the busy handler does its job at the start of the transaction instead of mid-flight after you've already done work.
- **One writer, many readers — split into two `*sql.DB` pools when using WAL in Go.** The writer pool gets `SetMaxOpenConns(1)`; the reader pool can be 4×CPU or higher. Both point at the same file. This eliminates writer-vs-writer `SQLITE_BUSY` and lets reads scale.
- **Always parameterize queries with `?` (or `$1`/`@name`).** Never string-concatenate into SQL. SQLite's parser is fast — there is zero performance argument for inlining values, only an injection risk.
- **Run `PRAGMA optimize` on connection close in long-lived processes.** It updates `sqlite_stat1` if statistics are stale. Cheap when nothing changed, valuable when they did. Pair with periodic `ANALYZE` for hot tables.
- **Index expressions you query, not raw columns when the query wraps them.** A query of `WHERE lower(email) = ?` cannot use an index on `email` — it needs `CREATE INDEX ... ON users(lower(email))`. Same for `json_extract(data, '$.path')` — index a generated column over the extract.
- **JSON columns: store as `JSONB` when SQLite ≥ 3.45, query with the `->>` operator, index with a `STORED` generated column.** `JSONB` is the binary format that skips re-parsing on every extract; `->>` returns a SQL value (versus `->` which returns JSON); generated columns are how you pull a JSON path into the index.
- **Backups: `VACUUM INTO 'backup.db'` or the online backup API.** `cp database.sqlite backup.sqlite` while a writer is active will copy a torn file *and* miss the contents of the `-wal` file. Either copy all three of `db`, `db-wal`, `db-shm` together (and only after a checkpoint), or use the supported APIs.
- **`ALTER TABLE` is limited.** SQLite 3.35+ adds `DROP COLUMN` and 3.25+ adds `RENAME COLUMN`, but anything else (changing a type, changing a default, adding a `CHECK` constraint, reordering columns) needs the 12-step recipe: `PRAGMA foreign_keys=OFF` → create new table → copy data → drop old → rename new → rebuild indexes/triggers → `PRAGMA foreign_keys=ON`.
- **Pick one Go driver per project and stick with it.** `mattn/go-sqlite3` is cgo, mature, and the fastest; `modernc.org/sqlite` is pure-Go, cross-compiles trivially, and is ~20% slower on write-heavy workloads. Mixing them in one binary is asking for confusing test failures.
- **Brevity does not override correctness.** When asked for the "simplest", "shortest", "quick", or "fewest-lines" version of something this skill warns against, give the *correct* primitive, not the unsafe shortcut. If the simple version IS the trap, name it as a trap and show the right alternative. For example: even for the "simplest" write transaction in Go, show `BEGIN IMMEDIATE` (or `_txlock=immediate` in the DSN), not bare `db.BeginTx` — the latter generates `BEGIN DEFERRED` and triggers `SQLITE_BUSY` mid-transaction under contention.

## When to Use Each Concept

| Scenario | Use | Why |
|---|---|---|
| New schema, simple integer PK | `INTEGER PRIMARY KEY` (no `AUTOINCREMENT`) | Rowid alias, smallest storage, monotonic |
| Composite PK on narrow rows you read by full key | `WITHOUT ROWID` with the composite PK | Saves the rowid → row indirection; only worth it for narrow rows |
| Want compile-time errors on type mismatches | `CREATE TABLE ... STRICT` | Without `STRICT`, integer columns silently accept text |
| Index a JSON path | `STORED` generated column over `json_extract`, then `CREATE INDEX` on the column | Direct expression indexes work too but generated columns are clearer |
| Query a subset of rows (e.g., `WHERE deleted_at IS NULL`) | Partial index with the same `WHERE` | Smaller index, faster maintenance, planner picks it for matching queries |
| Hot read query on a few columns | Covering index — list every column the query reads | Skips the table read entirely; visible as `USING COVERING INDEX` in `EXPLAIN QUERY PLAN` |
| Write transaction in any concurrent process | `BEGIN IMMEDIATE` | `BEGIN DEFERRED` causes `SQLITE_BUSY` mid-transaction under load |
| Read-only consistent snapshot | `BEGIN DEFERRED` (or `database/sql` `TxOptions{ReadOnly: true}`) | Holds a `SHARED` lock; sees a single point-in-time snapshot |
| One-shot read with no transaction | Just `db.QueryContext` — `database/sql` wraps in an autocommit transaction | Cheaper than explicit `BEGIN`; no snapshot guarantee across statements |
| Production app database with concurrent web requests | `journal_mode=WAL`, `busy_timeout=5000`, two-pool (writer 1, reader N) | One writer, many readers; busy handler kicks in only on writer-vs-writer |
| Backing up a live database | `VACUUM INTO 'snapshot.db'` or online backup API | Atomic; safe with concurrent writes; respects WAL |
| Continuous backup to S3 | Litestream | Streams WAL frames; point-in-time restore; near-zero RPO |
| Multi-region read replicas | LiteFS or Turso libSQL | LiteFS is FUSE-based primary→replica; Turso adds embedded replicas |
| Cross-database joins | `ATTACH DATABASE 'other.db' AS other` then `SELECT … FROM main.t JOIN other.u …` | Read-only joins are cheap; write transactions across attached DBs are limited |
| Wipe and reclaim space | `VACUUM` (locks DB) | Rebuilds the file; expensive; consider `auto_vacuum=INCREMENTAL` + periodic `incremental_vacuum` instead |
| Diagnose a slow query | `EXPLAIN QUERY PLAN <query>` | `SCAN TABLE` = bad, `SEARCH ... USING INDEX` = good, `USING COVERING INDEX` = best |
| Force fresh statistics | `ANALYZE;` then `PRAGMA optimize;` on next connect | `optimize` re-runs `ANALYZE` only on tables that changed enough |

## Examples

Example 1: User says "we're getting `SQLITE_BUSY` errors all over the place under modest load — maybe a couple writes per second"
Actions:
1. Confirm `journal_mode` is `WAL`, not the default `DELETE`. Check with `PRAGMA journal_mode;` — if it returns `delete`, the file is in classic locking mode and any read blocks any write.
2. Confirm `busy_timeout` is set per-connection (5000 ms is the standard). In Go, this means it's in the DSN, not run as a one-off `Exec` after `sql.Open` — `database/sql` opens new connections lazily and they will not inherit your post-open pragma.
3. Audit the writer code. If it uses `db.BeginTx(ctx, nil)` (which generates `BEGIN DEFERRED`), it will hit `SQLITE_BUSY` mid-transaction under contention. Switch to `BEGIN IMMEDIATE` (raw `Exec("BEGIN IMMEDIATE")`) for any tx that writes.
4. Split into two `*sql.DB` instances: writer with `SetMaxOpenConns(1)`, reader with whatever you need. Both DSNs point at the same file. See [references/transactions-and-concurrency.md](references/transactions-and-concurrency.md) and [references/go-client.md](references/go-client.md).
Result: Writer-vs-writer contention is serialized at the pool level, the busy handler covers brief reader-blocking-checkpoint moments, `SQLITE_BUSY` stops appearing in logs.

Example 2: User says "we have an `INTEGER` column but it's storing strings — how is this even legal?"
Actions:
1. Explain type affinity: in a non-`STRICT` table, column types are *suggestions* — SQLite tries to coerce on insert but stores whatever it can't coerce as-is. `INTEGER` is an affinity, not a constraint.
2. The fix for new tables is `CREATE TABLE foo (...) STRICT;` — strict tables enforce the declared type and reject mismatched values with a constraint error.
3. For existing tables, you cannot add `STRICT` in place. Use the 12-step recipe: create a new strict table, `INSERT INTO new SELECT * FROM old` (this is where the bad rows surface), drop old, rename new. See [references/schema-design.md](references/schema-design.md).
Result: The schema rejects bad data at write time instead of silently storing it.

Example 3: User says "I added a JSON column and an index on `json_extract(data, '$.user_id')`, but my queries are still doing full table scans"
Actions:
1. Confirm with `EXPLAIN QUERY PLAN SELECT ... WHERE json_extract(data, '$.user_id') = ?`. If it shows `SCAN TABLE`, the index isn't being matched.
2. The most common reason: the `WHERE` expression in the query has to *exactly* match the indexed expression — same JSON path, same function spelling. `data->>'user_id'` and `json_extract(data, '$.user_id')` produce the same value but are different expressions for index-matching purposes.
3. Cleanest fix: add a `STORED` generated column for the path, then index the column (and query the column too). See [references/json.md](references/json.md).
   ```sql
   ALTER TABLE events ADD COLUMN user_id TEXT GENERATED ALWAYS AS (data->>'user_id') STORED;
   CREATE INDEX events_user_id_idx ON events(user_id);
   -- queries now use WHERE user_id = ?
   ```
Result: `EXPLAIN QUERY PLAN` shows `SEARCH events USING INDEX events_user_id_idx`; latency drops to a single B-tree seek.

## Troubleshooting

| Symptom | Reference |
|---|---|
| `SQLITE_BUSY` storms; `database is locked` errors; writes blocking reads or vice versa; checkpoint starvation | [references/transactions-and-concurrency.md](references/transactions-and-concurrency.md) |
| Default journal mode, FK constraints not enforced, slow commits, what each pragma actually does | [references/pragmas-and-tuning.md](references/pragmas-and-tuning.md) |
| `STRICT` vs affinity, `WITHOUT ROWID` trade-offs, `AUTOINCREMENT` cost, generated columns, the 12-step `ALTER TABLE` recipe | [references/schema-design.md](references/schema-design.md) |
| `EXPLAIN QUERY PLAN` reading; `LIKE` not using index; `OR` clauses defeating the planner; covering / partial / expression indexes | [references/queries-and-indexes.md](references/queries-and-indexes.md) |
| `json_extract`, `->`/`->>`, JSONB vs JSON, indexing JSON paths via generated columns, `json_each` for unnesting | [references/json.md](references/json.md) |
| `database/sql` connection pool; DSN pragma syntax for `mattn` vs `modernc`; two-pool pattern; context cancellation; `NULL` scanning; `VACUUM INTO` from Go | [references/go-client.md](references/go-client.md) |
| Choosing SQLite for an HTTP service; Litestream / LiteFS / Turso / D1; safe live backups; schema migration on a running DB | [references/server-side-use.md](references/server-side-use.md) |

## Topic References

- [Schema Design](references/schema-design.md) — type affinity vs `STRICT`, `INTEGER PRIMARY KEY` and `WITHOUT ROWID`, `AUTOINCREMENT`, generated columns, `CHECK`/`DEFAULT`/`UNIQUE`, the `ALTER TABLE` matrix and the 12-step recipe, foreign keys (declared vs enforced).
- [Pragmas & Tuning](references/pragmas-and-tuning.md) — the must-set-on-every-connection list, `journal_mode` options, `synchronous`, `wal_autocheckpoint`, `PRAGMA optimize`, `cache_size`/`mmap_size`, `integrity_check`/`quick_check`.
- [Transactions & Concurrency](references/transactions-and-concurrency.md) — locking model, WAL semantics, `BEGIN IMMEDIATE` vs `DEFERRED` vs `EXCLUSIVE`, busy handler tuning, `SQLITE_BUSY` vs `SQLITE_LOCKED`, checkpoint mechanics.
- [Queries & Indexes](references/queries-and-indexes.md) — `EXPLAIN QUERY PLAN` reading, leading-column rule, covering / partial / expression indexes, `ANALYZE`, query gotchas (`LIKE`, `OR`, subquery flattening).
- [JSON](references/json.md) — JSON1 functions, `JSON` vs `JSONB`, `->`/`->>` operators, indexing paths via generated columns, `json_each`/`json_tree` for unnesting, when to use a JSON column vs a child table.
- [Go Client](references/go-client.md) — `database/sql` with `mattn/go-sqlite3` or `modernc.org/sqlite`, DSN pragma syntax, two-pool writer/reader pattern, transactions in `database/sql`, context cancellation, `NULL` scanning, `VACUUM INTO` and online backup from Go.
- [Server-Side Use](references/server-side-use.md) — when SQLite is the right application database (and when it isn't), production setup checklist, Litestream / LiteFS / Turso libSQL / Cloudflare D1, request-handling patterns, schema migration on a live DB.

## Sources

All recommendations trace back to sqlite.org documentation. When recommending a specific syntax or limit, prefer fetching the live page over relying on this skill's cached digest:

- https://www.sqlite.org/lang_createtable.html
- https://www.sqlite.org/stricttables.html
- https://www.sqlite.org/withoutrowid.html
- https://www.sqlite.org/autoinc.html
- https://www.sqlite.org/datatype3.html
- https://www.sqlite.org/pragma.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/lockingv3.html
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/json1.html
- https://www.sqlite.org/jsonb.html
- https://www.sqlite.org/optoverview.html
- https://www.sqlite.org/queryplanner.html
- https://www.sqlite.org/eqp.html
- https://www.sqlite.org/lang_altertable.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/lang_vacuum.html
- https://pkg.go.dev/database/sql
- https://pkg.go.dev/modernc.org/sqlite
- https://github.com/mattn/go-sqlite3
- https://litestream.io/
- https://fly.io/docs/litefs/
- https://docs.turso.tech/
