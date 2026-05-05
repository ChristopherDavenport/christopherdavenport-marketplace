# Queries & DML — Parameterization, Predicates, and Plan Caching

Most Spanner query problems come down to three things: unparameterized SQL, predicates that prevent index use, and an assumption that result rows come back in a particular order. Fix those and the optimizer does its job.

## Always Parameterize

Use `@param` placeholders, never string interpolation. Parameters give you:

- **Plan caching.** Spanner reuses the compiled plan across calls with different values.
- **Injection safety.** Parameters can never be interpreted as SQL.
- **Type clarity.** The driver knows the type; no implicit conversion bugs.

```sql
-- Recommended
SELECT * FROM Singers WHERE LastName = @last;

-- Even for IN-lists
SELECT * FROM Singers WHERE SingerId IN UNNEST(@ids);
```

```go
stmt := spanner.Statement{
    SQL: "SELECT * FROM Singers WHERE SingerId IN UNNEST(@ids)",
    Params: map[string]interface{}{"ids": []int64{1, 2, 3}},
}
```

Parameters can appear anywhere a literal value is expected. They cannot substitute identifiers (table names, column names) — those must be string-built before query time.

## STARTS_WITH, Not LIKE @prefix

Parameterized `LIKE` is a hidden full-scan trigger:

```sql
-- Anti-pattern: query optimizer can't peek inside @pattern
WHERE Title LIKE @pattern    -- pattern is e.g. 'foo%'
```

Replace with `STARTS_WITH` (or an anchored range):

```sql
-- Good: optimizer sees a prefix; uses any index on Title
WHERE STARTS_WITH(Title, @prefix)

-- Equivalent — works even where STARTS_WITH isn't available
WHERE Title >= @prefix AND Title < CONCAT(@prefix, '\xff')
```

Constant `LIKE` patterns (`LIKE 'foo%'` with a literal) are fine — the optimizer rewrites them. The issue is specifically `LIKE` with a parameter.

## ORDER BY Is Required for Ordering

Spanner does not preserve insert order. Without `ORDER BY`, rows come back in whatever order is convenient:

```sql
-- Order is undefined; may change between runs
SELECT * FROM Events;

-- Required
SELECT * FROM Events ORDER BY EventId;
```

If you only need a few rows, `ORDER BY ... LIMIT N` is much cheaper than scanning everything — Spanner can stream from a sorted index.

## Index-Friendly Predicates

For Spanner to use an index:

- The predicate must touch the leading index column(s).
- The predicate must be index-decidable (equality, range, `STARTS_WITH`, `IN UNNEST`).
- For `NULL_FILTERED` indexes, must include `IS NOT NULL` (see [indexes.md](indexes.md)).

```sql
-- Good
WHERE LastName = @last
WHERE BirthYear BETWEEN 1970 AND 1980
WHERE SingerId IN UNNEST(@ids)
WHERE STARTS_WITH(Email, @domain_prefix)

-- Bad — function on indexed column hides it from the optimizer
WHERE LOWER(Email) = LOWER(@email)

-- Fix: store the lowercased value in a generated column and index it
LowerEmail STRING(MAX) AS (LOWER(Email)) STORED;
CREATE INDEX UsersByLowerEmail ON Users(LowerEmail);
```

## Sparse Keys: UNNEST vs BETWEEN

For a sparse set of keys (a few hundred non-contiguous IDs), `UNNEST` is right; `BETWEEN` is wrong:

```sql
-- Bad: scans everything between min and max
WHERE Id BETWEEN 1000 AND 9999000

-- Good: seek per ID
WHERE Id IN UNNEST(@ids)    -- where @ids is the actual list
```

For dense ranges, `BETWEEN` is correct.

## Commit Timestamp Filtering

Define a column with `OPTIONS (allow_commit_timestamp=true)` and write `spanner.CommitTimestamp` to it:

```sql
CREATE TABLE Singers (
  SingerId         INT64 NOT NULL,
  ...
  ModificationTime TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (SingerId);
```

```go
m := spanner.InsertOrUpdate("Singers",
    []string{"SingerId", "ModificationTime"},
    []interface{}{singerId, spanner.CommitTimestamp})
```

Now you can prune by it:

```sql
SELECT * FROM Singers
WHERE ModificationTime > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR);
```

Spanner can use commit-timestamp metadata to skip blocks that don't contain matching data.

**Important:** never put a commit-timestamp column in the **leading** PK position (it's monotonic — see [schema-design.md](schema-design.md)). It's safe in non-key columns or as a non-leading key column.

## DML and Lock Scope

DML statements lock the rows and columns they touch. An efficient predicate keeps the lock set small:

```sql
-- Good: PK lookup, single-row lock
UPDATE Singers SET FirstName = @new WHERE SingerId = @id;

-- Bad: locks every Singer that matches → huge lock set, contention
UPDATE Singers SET LastSeen = CURRENT_TIMESTAMP()
WHERE FirstName = @first AND LastName = @last;
```

If the second form is necessary, ensure there's an index on `(FirstName, LastName)` so Spanner doesn't lock the entire table during the scan.

## THEN RETURN / RETURNING

Get back inserted/updated values without a separate query:

```sql
-- GoogleSQL
INSERT INTO Singers (SingerId, FirstName, LastName)
VALUES (NEW_UUID(), @first, @last)
THEN RETURN SingerId, CreatedAt;

-- PostgreSQL dialect
INSERT INTO singers (first_name, last_name)
VALUES ($1, $2)
RETURNING singer_id, created_at;
```

Useful for:

- Generated columns (`AS (...) STORED`).
- Default values (`DEFAULT NEW_UUID()`).
- The commit-timestamp column.
- IDENTITY-assigned IDs.

Saves one round-trip per row.

## Sequential Statement Execution

Inside a `ReadWriteTransaction`, statements execute **sequentially** — they are not parallelized. For bulk DML, batching multiple `UPDATE`s into one transaction does not save round-trips.

Options:

- Use mutations (`spanner.Insert`/`Update` collected into one `BufferWrite`) — sent at commit only, no per-statement RTT.
- For very large batches, use Partitioned DML or chunk into many transactions.

## Query Hints

After confirming a plan via `EXPLAIN`, lock it in:

```sql
SELECT s.SingerId
FROM Singers@{FORCE_INDEX=SingersByLastName} s
WHERE s.LastName = @last;
```

Other hints:

```sql
JOIN@{FORCE_JOIN_ORDER=TRUE} a ON s.SingerId = a.SingerId
JOIN@{JOIN_METHOD=HASH_JOIN}  a ON s.SingerId = a.SingerId
```

Use only when the optimizer is demonstrably wrong. Re-check on optimizer-version upgrades — your hint may now hurt.

## EXPLAIN

```sql
EXPLAIN SELECT * FROM Singers WHERE LastName = @last;
```

Look for:

- `Distributed Union` over many splits → fan-out (sometimes unavoidable; sometimes a sign of missing predicate).
- `Table Scan` over the base table when an index exists → index not used; check predicate shape and `NULL_FILTERED` requirements.
- `Sort` operator → missing/wrong `ORDER BY` index.

`EXPLAIN ANALYZE` runs the query and reports actual times per operator.

## Avoid Large Reads in Read-Write Transactions

A `SELECT *` inside `ReadWriteTransaction` acquires shared locks on every row read, blocking other writers and risking aborts. Move read-only work to a `ReadOnlyTransaction`:

```go
// Bad
client.ReadWriteTransaction(ctx, func(ctx, txn) error {
    iter := txn.Query(ctx, allRows)  // locks everything
    ...
})

// Good
ro := client.ReadOnlyTransaction()
defer ro.Close()
iter := ro.Query(ctx, allRows)  // no locks
```

See [transactions.md](transactions.md) for transaction selection.

## Mutations vs DML — Which to Use

| Need | Use |
|---|---|
| Blind insert/update/delete (no read involved) | `spanner.Insert`/`Update`/`Delete` mutations |
| Conditional update (`SET x = x + 1`) | DML |
| Need rows back (`THEN RETURN`) | DML |
| Maximum throughput for many writes | Mutations + `client.Apply` or `BufferWrite` |
| Bulk `UPDATE`/`DELETE` of millions of rows | Partitioned DML |

Both count toward the 80,000-mutation / 100 MiB transaction limits.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| `WHERE col LIKE @pattern` | Forces full scan; use `STARTS_WITH` |
| `WHERE LOWER(col) = ...` on an indexed column | Disables index; use a generated column or store-lowercase |
| `WHERE Id BETWEEN @lo AND @hi` for sparse IDs | Scans everything in range; use `IN UNNEST` |
| `SELECT *` followed by client-side ordering | Spanner doesn't pre-sort; cheaper to add `ORDER BY` and `LIMIT` |
| Concatenating user input into SQL | Injection risk; no plan caching; use `@param` |
| `UPDATE T SET ... WHERE T.x = T.x + 1` inside Partitioned DML | Not idempotent — partition retry double-applies |
| Iterating row-at-a-time with a separate transaction per row | Round-trip per row; batch into mutations |

## Common Pitfalls

- **Assuming `IN (...)` literal lists cache plans.** They don't — each list size is a different plan. Use `IN UNNEST(@list)` instead.
- **Forgetting `OPTIONS (allow_commit_timestamp=true)`** when defining a commit-timestamp column. Without it, writing `spanner.CommitTimestamp` raises an error.
- **Using `CURRENT_TIMESTAMP()` as if it were a commit time.** It's the time the SQL query started, not the commit time. Use `PENDING_COMMIT_TIMESTAMP()` / `spanner.CommitTimestamp` for true commit time.
- **Mixing literal and parameterized predicates inconsistently.** Each literal value creates a separate cached plan; each parameter shares one plan.
- **Counting rows by `SELECT COUNT(*) FROM BigTable`.** That's a full scan. Maintain a counter table updated transactionally, or accept eventual consistency from a daily aggregation.

## Sources

- https://cloud.google.com/spanner/docs/sql-best-practices
- https://cloud.google.com/spanner/docs/dml-tasks
- https://cloud.google.com/spanner/docs/transactions
