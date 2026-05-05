# Queries & Indexes

SQLite's planner is small but capable. The diagnosis tool is `EXPLAIN QUERY PLAN`, and the trick is recognizing the three outputs that matter: full scan, indexed search, and covering search. Indexes work the way you'd expect from any B-tree database — leading-column rule, composite indexes, partial indexes — with a few SQLite-specific gotchas around `LIKE`, `OR`, and expression matching.

## Reading `EXPLAIN QUERY PLAN`

```sql
EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = ? AND created_at > ?;
```

Three possible outputs in order of badness:

| Output | Meaning |
|---|---|
| `SCAN orders` | Full table scan. The planner couldn't use any index. Usually a problem at any non-trivial table size. |
| `SEARCH orders USING INDEX idx_customer` | Indexed seek, but the row is still fetched from the table for non-indexed columns. Good. |
| `SEARCH orders USING COVERING INDEX idx_customer` | Indexed seek, all columns the query needs are in the index. No table fetch. **Best.** |

Other phrases to recognize:

- `SEARCH ... USING ROWID` — direct rowid lookup (e.g. `WHERE id = ?` on `INTEGER PRIMARY KEY`). This is optimal — the rowid IS the B-tree key.
- `USE TEMP B-TREE FOR ORDER BY` — the planner is sorting in memory because no index matches the `ORDER BY`. Add an index, or accept the cost.
- `USE TEMP B-TREE FOR GROUP BY` — same, for grouping.
- `MULTI-INDEX OR` — the planner is using one index per `OR` branch and unioning the results. Often slower than rewriting as `UNION ALL` (see below).

`EXPLAIN` (without `QUERY PLAN`) shows the bytecode — useful for deep optimization but rarely needed.

## Index Design Rules

### Leading-column rule

A composite index `(a, b, c)` can serve queries that filter on:

- `a`
- `a, b`
- `a, b, c`

It **cannot** serve queries that filter only on `b`, only on `c`, or only on `b, c`. The leading column has to be in the predicate.

Order columns by selectivity: most-selective first (or by `WHERE`-clause shape, if you only ever query certain combinations).

### Covering indexes

Add columns the query *reads* (not just filters on) to the index, and the planner can serve the whole query from the index alone.

```sql
CREATE INDEX orders_customer_idx ON orders(customer_id, created_at, status);
-- Query: SELECT status FROM orders WHERE customer_id = ? AND created_at > ?;
-- EXPLAIN: SEARCH orders USING COVERING INDEX orders_customer_idx
```

Without `status` in the index, the planner has to fetch the row from the table for every match. Adding it doubles the index size (modestly) but eliminates the table fetch.

Don't index every column — only the ones that hot queries actually read. Wide indexes slow down writes.

### Partial indexes

An index with a `WHERE` clause. Only rows matching the clause are indexed.

```sql
CREATE INDEX orders_active_idx ON orders(customer_id)
  WHERE status = 'active';
```

Wins:

- Smaller index → faster lookups, less RAM, less disk.
- Faster maintenance — inserts/updates/deletes only touch the index when the row matches.
- The planner uses it for queries whose `WHERE` clause is **logically implied by** the index's `WHERE` clause: `WHERE status = 'active' AND customer_id = ?` matches.

The query's `WHERE` must include the partial index's predicate (or one that implies it). If the planner can't prove implication, it won't use the index. Keep the predicate simple — equality on a literal value works best.

### Expression indexes

Index a function of a column, not the column itself. Required for queries that wrap the column in a function.

```sql
CREATE INDEX users_email_lower_idx ON users(lower(email));
-- Query: SELECT id FROM users WHERE lower(email) = ?;
-- EXPLAIN: SEARCH users USING INDEX users_email_lower_idx
```

The `WHERE` clause expression must be **textually identical** (after normalization) to the indexed expression. `lower(email)` matches `lower(email)`; it does not match `LOWER(email)` (case is normalized but spelling is not), nor `lower(trim(email))` (different expression entirely).

For JSON paths, see [json.md](json.md) — the cleanest pattern is a generated column over the path, then a regular index on the generated column.

## `ANALYZE` and Statistics

Without statistics, the planner uses heuristics: it assumes uniform distribution, equal cost for any index, etc. Usually fine. Occasionally wrong in ways that turn a 1ms query into a 1s query.

```sql
ANALYZE;             -- whole DB; cheap on small DBs, slow on huge ones
ANALYZE main.orders; -- one table
```

Stats live in `sqlite_stat1`. Inspect them:

```sql
SELECT * FROM sqlite_stat1 WHERE tbl='orders';
-- tbl    idx                    stat
-- orders orders_customer_idx    100000 50
-- (100k rows, average ~50 rows per distinct customer_id)
```

After bulk loads, run `ANALYZE`. After that, `PRAGMA optimize` (re-runs `ANALYZE` only on tables that drifted) is the maintenance pattern. See [pragmas-and-tuning.md](pragmas-and-tuning.md).

## Query Gotchas

### `LIKE 'foo%'` and indexes

`LIKE` uses an index for prefix patterns *only* if all of these hold:

- The column has `COLLATE BINARY` (the default) **or** `case_sensitive_like=ON`.
- The pattern is a constant prefix followed by `%` (or no wildcard at all).
- The right-hand side is a literal or parameter that the planner can analyze.

In practice, the safest patterns are:

```sql
-- Use GLOB instead — case-sensitive, always uses the index for prefixes:
SELECT * FROM users WHERE name GLOB 'John*';

-- Or anchor with comparison operators:
SELECT * FROM users WHERE name >= 'John' AND name < 'Joho';
```

For case-insensitive prefix search, declare the column `COLLATE NOCASE` and create an index — `LIKE 'john%'` will then use the index.

### `OR` clauses

```sql
SELECT * FROM orders WHERE customer_id = ? OR status = 'pending';
```

The planner can handle this with a `MULTI-INDEX OR`, but performance is often worse than expected. Rewrite as `UNION ALL` when both branches benefit from indexes:

```sql
SELECT * FROM orders WHERE customer_id = ?
UNION ALL
SELECT * FROM orders WHERE status = 'pending' AND customer_id != ?;
-- (the != avoids duplicating rows that match both)
```

Ugly but often 10× faster.

### Subquery flattening

The planner tries to flatten subqueries into the parent. If it can't (correlated subquery, aggregates with no `GROUP BY`, etc.), the subquery materializes into a temporary table. `EXPLAIN QUERY PLAN` will show `MATERIALIZE` or `CO-ROUTINE` for these.

Most non-trivial subqueries are fine. Watch for:

- Correlated subqueries inside loops — the inner query runs per row.
- `IN (SELECT ...)` on large inner result sets — sometimes faster as a join.

### `ORDER BY` and indexes

`ORDER BY` is satisfied for free by an index whose leading columns match. Mismatches force a sort:

```sql
CREATE INDEX e ON events(user_id, created_at DESC);
SELECT * FROM events WHERE user_id = ? ORDER BY created_at DESC;  -- free; uses index
SELECT * FROM events WHERE user_id = ? ORDER BY created_at ASC;   -- needs sort
```

For ascending+descending mixed orders, you need separate indexes (or accept the sort).

### `LIMIT` and indexes

`LIMIT N` lets the planner stop early — it's free when the data already comes out of the index in the right order. Pair `LIMIT` with an index-friendly `ORDER BY` for "newest N" queries.

## `WITHOUT ROWID` Performance Notes

`WITHOUT ROWID` tables store rows directly under the primary key in a B-tree. Trade-offs:

- PK lookups are faster (one B-tree descent, no rowid indirection).
- Secondary index entries store the full PK, not a small rowid. For composite or wide PKs, every secondary index gets larger.
- Range scans over wide rows are slower because the data and tree are interleaved on the same pages — less cache locality.

Best fit: narrow rows, small PK, lots of PK lookups, few secondary indexes. Otherwise stick with rowid tables.

## Sources

- https://www.sqlite.org/eqp.html — `EXPLAIN QUERY PLAN`
- https://www.sqlite.org/optoverview.html — query optimizer overview
- https://www.sqlite.org/queryplanner.html — planner internals
- https://www.sqlite.org/partialindex.html — partial indexes
- https://www.sqlite.org/expridx.html — expression indexes
- https://www.sqlite.org/lang_analyze.html — `ANALYZE` and `sqlite_stat1`
- https://www.sqlite.org/optoverview.html#the_like_optimization — `LIKE` and indexes
- https://www.sqlite.org/withoutrowid.html — `WITHOUT ROWID` performance
