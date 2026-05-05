# Secondary Indexes — STORING, NULL_FILTERED, and Hidden Hotspots

Spanner secondary indexes are **stored as separate tables**, ordered by the index key columns. Every rule that applies to primary key design applies again here: a leading index column with monotonic values causes the same write hotspot as a monotonic primary key. Add `STORING` to make queries index-only, `NULL_FILTERED` to drop NULL rows from sparse indexes, and `INTERLEAVE IN` to co-locate index entries with a parent.

## How Indexes Work

A `CREATE INDEX` builds and maintains a second physical structure. Each row in the index contains:

1. The indexed columns (in the order declared).
2. Any `STORING` columns.
3. The base table's primary key (always appended for back-reference).

When you query through the index, Spanner does an index seek to find matching rows, then either uses the data already in the index (covered query) or does a second seek to the base table to fetch missing columns.

Every index doubles the cost of writes to its base table — every `INSERT`/`UPDATE`/`DELETE` updates the base row and one row in each affected index. Don't index every column "just in case."

## Basic Index

```sql
CREATE INDEX SingersByLastName ON Singers (LastName);

-- Used:
SELECT SingerId FROM Singers WHERE LastName = 'Smith';
```

The query is "covered" because `SingerId` is the base table's PK and is always present in the index.

## STORING / INCLUDE for Covered Queries

If the query reads non-key, non-indexed columns, Spanner does a second seek to the base table per matching row. Avoid that with `STORING`:

```sql
CREATE INDEX SingersByLastName
  ON Singers (LastName)
  STORING (FirstName, BirthDate);

-- Now this is index-only — no base-table seek
SELECT SingerId, FirstName, BirthDate
FROM Singers
WHERE LastName = 'Smith';
```

PostgreSQL dialect uses `INCLUDE` instead of `STORING`:

```sql
CREATE INDEX singers_by_last_name
  ON singers (last_name)
  INCLUDE (first_name, birth_date);
```

Trade-offs:

- **Storage:** every stored column is duplicated in the index.
- **Write cost:** every update to a stored column updates the index row too.
- **Don't STORE volatile columns** (counters, last-seen timestamps) — they trigger constant index churn for no read benefit.

## NULL_FILTERED Indexes

If most rows have NULL in the indexed column, drop them from the index entirely (GoogleSQL only):

```sql
CREATE NULL_FILTERED INDEX UsersByVerifiedEmail
  ON Users (VerifiedEmail);
```

Storage drops to one entry per non-NULL row. **Critical gotcha:** Spanner only uses this index for queries that explicitly exclude NULL. Otherwise it would return wrong results.

```sql
-- ✓ Uses the index — predicate excludes NULL
SELECT UserId FROM Users
WHERE VerifiedEmail IS NOT NULL AND VerifiedEmail = 'a@b.com';

-- ✗ Does NOT use the index — query could match a NULL row
SELECT UserId FROM Users WHERE VerifiedEmail = @email;
```

Equivalent in some cases:

```sql
-- ✓ Equality with non-null parameter is fine; optimizer infers IS NOT NULL
SELECT UserId FROM Users WHERE VerifiedEmail = 'a@b.com';
```

If the parameter could be NULL or the optimizer doesn't infer non-null, add `IS NOT NULL` explicitly.

## Interleaved Indexes

Co-locate the index with a parent table so index entries land in the same split as the parent row:

```sql
CREATE INDEX SongsByAlbumTitle
  ON Songs (SingerId, AlbumId, Title)
  INTERLEAVE IN Albums;
```

Constraints:

- The index's leading columns must match the parent table's primary key.
- Read efficiency wins are biggest when queries always filter on the parent key.

When to use:

- The index leading column would otherwise be a hotspot, but bound to a well-distributed parent key.
- Per-parent index queries dominate (e.g., "songs by title within this album").

See [interleaving.md](interleaving.md) for the broader interleaving model.

## Descending Columns

Annotate individual key columns with `DESC` for queries that scan in reverse:

```sql
CREATE INDEX UserSessionsByStartTime
  ON UserSessions (UserId, StartedAt DESC);

-- Adjacent rows in the index — no sort needed
SELECT * FROM UserSessions
WHERE UserId = @u
ORDER BY StartedAt DESC
LIMIT 50;
```

`DESC` does not change distribution (still hashed by the same data); it changes scan order. For Read API operations (`Read`/`StreamingRead`), inverted ranges (start > end) traverse the index in `DESC` order.

## Index Hotspots — The Hidden Trap

Because indexes are tables, the same hotspot rules apply:

**Anti-pattern:**

```sql
-- All inserts hit the same index split
CREATE INDEX EventsByCommitTime ON Events (CommitTime);
```

**Fixes:**

1. **Don't index it.** If you can answer the query with a `WHERE CommitTime > @cutoff` against the base table (especially with a commit-timestamp column — see [queries-and-dml.md](queries-and-dml.md)), skip the index.
2. **Interleave the index** under a well-distributed parent (`INTERLEAVE IN Users`).
3. **Hash-shard the index** by adding a `ShardId` column to the base table and including it as the index's leading column:

   ```sql
   CREATE INDEX EventsByCommitTime
     ON Events (ShardId, CommitTime DESC);
   ```

## Query Hints

The optimizer is good but not infallible. After confirming an index helps via `EXPLAIN`, you can lock in its use:

```sql
SELECT s.SingerId
FROM Singers@{FORCE_INDEX=SingersByLastName} s
WHERE s.LastName = 'Smith';
```

Other hints:

```sql
-- Force join order
SELECT *
FROM Singers s
JOIN@{FORCE_JOIN_ORDER=TRUE} Albums a ON s.SingerId = a.SingerId;

-- Force join method
SELECT *
FROM Singers s
JOIN@{JOIN_METHOD=HASH_JOIN} Albums a ON s.SingerId = a.SingerId;
```

Use sparingly and re-check on optimizer-version upgrades. Don't slap `FORCE_INDEX` on every query "to be safe" — it disables future plan improvements.

## Index Backfill

Creating an index on an existing large table is a long background operation:

- Time scales with table size and instance compute capacity.
- Runs at lower priority than serving traffic.
- Visible as a long-running operation in `gcloud spanner operations list`.

For multiple indexes, batch the DDL into one `gcloud spanner databases ddl update` call — Spanner can sometimes share scan work, and you submit one operation to monitor. See [schema-evolution.md](schema-evolution.md).

## Cost Mental Model

For each index, every base-table write triggers:

- 1 base row read (for old values, if needed).
- 1 base row write.
- N index entry writes (one per index that includes a changed column).

Index commit cost ≈ `1 + (number of indexes touching changed columns)`. A table with 8 indexes pays ~9× the write cost of an unindexed table per modified row.

## When to Use What

| Situation | Choice |
|---|---|
| Frequent equality / range filter on a column | Plain index on that column |
| Same plus reading a few non-indexed columns | `STORING` those columns |
| Most rows have NULL in the indexed column | `NULL_FILTERED` (and remember `IS NOT NULL` in queries) |
| Per-parent queries (`WHERE parent_key = ...`) dominate | `INTERLEAVE IN parent` |
| `ORDER BY col DESC LIMIT N` is the hot path | `col DESC` in the index |
| Want to lock in the optimizer's choice | `@{FORCE_INDEX=name}` after verifying with `EXPLAIN` |
| Need composite filtering | Multi-column index, leading with the most-selective column |

## Anti-Patterns

| Pattern | Problem |
|---|---|
| `CREATE INDEX X ON T (commit_ts)` | Write hotspot; index leading column monotonic |
| `STORING` columns that change frequently | Index churn on every update with no read benefit |
| `NULL_FILTERED` index without `IS NOT NULL` in queries | Spanner won't use the index; you wonder why your query is slow |
| Indexing every column "for flexibility" | Each index multiplies write cost; throughput collapses |
| `FORCE_INDEX` on a query whose plan you haven't verified | Locks in a possibly-suboptimal plan; survives optimizer upgrades |
| Adding many indexes after the table is huge | Each `CREATE INDEX` runs for hours; production load amplified |

## Common Pitfalls

- **Forgetting NULL_FILTERED's WHERE-clause requirement.** Without `IS NOT NULL`, the optimizer skips the index and you get a full scan.
- **Over-using `STORING`.** A 10-column STORING list on a high-write table doubles your write IOPS for marginal read benefit.
- **Indexing a `commit_timestamp` column directly.** Hidden hotspot; use a sharded leading column or skip the index.
- **Assuming index creation is instant.** On a 1 TB table, a new index can take many hours. Schedule and monitor.
- **`@{FORCE_INDEX}` syntax errors.** The hint goes on the table reference (`FROM T@{FORCE_INDEX=I}`), not in the `WHERE` clause.

## Sources

- https://cloud.google.com/spanner/docs/secondary-indexes
- https://cloud.google.com/spanner/docs/sql-best-practices
