# Schema Evolution — Long Operations and Irreversible Changes

Schema changes in Spanner are background operations that can take **hours** on large tables, run at lower priority than serving traffic, and have at least one mode (`ALTER COLUMN ... NOT NULL`) that can cause an immediate write outage *before* validation completes. Several changes are not supported at all and require a copy-and-rename migration.

## How Schema Updates Run

`gcloud spanner databases ddl update` (or the API equivalent) submits one or more DDL statements as a single long-running operation. The operation:

- Validates new constraints against existing data (where applicable).
- Backfills indexes from base table data.
- Migrates column types (for the supported subset of conversions).
- Returns success only after all background work completes.

Time scales with table size, instance compute, and serving load. Adding an index to a 100 GB table during peak hours can take many hours.

```sh
# Submit DDL
gcloud spanner databases ddl update mydb \
  --instance=myinstance \
  --ddl="CREATE INDEX SongsByDuration ON Songs(Duration)"

# Watch the operation
gcloud spanner operations list \
  --instance=myinstance \
  --database=mydb

gcloud spanner operations describe OPERATION_ID \
  --instance=myinstance \
  --database=mydb
```

In code, use `database/admin/api` or the equivalent client; both return long-running operation handles.

## Operations By Cost

| Operation | Roughly |
|---|---|
| `CREATE TABLE` (empty) | Seconds |
| `CREATE TABLE ... CREATE INDEX ...` in one DDL batch (empty) | Seconds |
| `ADD COLUMN` (no constraint) | Seconds |
| `DROP COLUMN` | Seconds (data reclaimed in background) |
| `CREATE INDEX` on existing table | Minutes to hours; scales with table size |
| `ALTER COLUMN ... NOT NULL` (with NULLs in data) | Validation hours; **immediately rejects new NULL writes during validation** |
| `ALTER COLUMN` size change (`STRING(100)` → `STRING(50)`) | Validation hours; rejects oversized writes |
| Adding a foreign key | Validation hours on large tables |

## The NOT NULL Outage

This is the most dangerous schema change in Spanner.

When you submit `ALTER TABLE T ALTER COLUMN c STRING(MAX) NOT NULL`:

1. **Immediately**, Spanner starts rejecting writes that would put NULL into `c`.
2. **In the background**, Spanner validates that no existing row has NULL in `c`.
3. If validation succeeds, the constraint is permanent.
4. If validation **fails**, the schema update rolls back — but you've been rejecting writes for the entire validation window. That's an outage.

Mitigation:

```sql
-- Step 1: confirm no NULLs
SELECT COUNT(*) FROM T WHERE c IS NULL;
-- Should be 0

-- Step 2: backfill any NULLs to a sentinel value (Partitioned DML for big tables)
UPDATE T SET c = '' WHERE c IS NULL;

-- Step 3: re-confirm
SELECT COUNT(*) FROM T WHERE c IS NULL;

-- Step 4: only now apply the constraint
ALTER TABLE T ALTER COLUMN c STRING(MAX) NOT NULL;
```

Same caution applies to shrinking column types and to size constraints.

## Unsupported Conversions

These are not allowed by `ALTER COLUMN`. The path is "create a new column, backfill, drop the old, rename":

- `STRING(36)` ↔ `UUID`
- `STRING(N)` ↔ `BYTES(N)`
- Numeric types of different sizes (most cases)
- Removing values from an `ENUM` used as a key column

Pattern:

```sql
-- 1. Add a new column of the desired type
ALTER TABLE Users ADD COLUMN NewId UUID;

-- 2. Backfill (Partitioned DML for big tables)
UPDATE Users SET NewId = SAFE_CAST(OldId AS UUID) WHERE NewId IS NULL;

-- 3. Make sure all reads/writes touch both columns (dual-write phase)
--    -- application code change here, deployed and stable

-- 4. After the dual-write window, switch reads to NewId
--    -- application code change

-- 5. Drop the old column
ALTER TABLE Users DROP COLUMN OldId;
```

For PK column changes, the table itself must be recreated — there is no `ALTER PRIMARY KEY`.

## Irreversible Schema Decisions

You cannot undo:

- **`INTERLEAVE IN PARENT`** — once interleaved, always interleaved (under that parent). See [interleaving.md](interleaving.md).
- **Adding or removing primary key columns.** Recreate the table.
- **Reordering primary key columns.** Recreate the table.

For all three, the migration is: create a new table with the desired shape, copy data, switch the application to the new table, drop the old. Plan capacity for double the storage during the cutover.

## View Invalidation

If you change a column referenced by a view, the schema update validates against the existing view and **fails** if the view would break:

```sql
-- View references s.LastName
CREATE VIEW SingerNames SQL SECURITY INVOKER AS
SELECT s.SingerId, s.LastName FROM Singers s;

-- This fails because the view would no longer compile
ALTER TABLE Singers DROP COLUMN LastName;
```

Either drop or recreate the view first, then alter the underlying table.

## Batching Index Creates

Spanner can sometimes share scan work across multiple index creates submitted in the same DDL batch:

```sh
gcloud spanner databases ddl update mydb \
  --instance=myinstance \
  --ddl-file=batch.ddl
```

`batch.ddl`:

```sql
CREATE INDEX SongsByName    ON Songs(Name);
CREATE INDEX SongsByArtist  ON Songs(Artist);
CREATE INDEX SongsByDuration ON Songs(Duration);
```

Submit as one operation to monitor; less ceremony than submitting three separate operations.

For very large tables, expect the operation to run for hours regardless. Schedule during low-traffic windows so the background work has more compute headroom.

## Schema Versioning

Spanner keeps old schema versions until they're no longer referenced by any open transaction or stale read. While they exist, they consume resources. Long-running stale-read clients (`ExactStaleness` with hours-long bounds) can pin old versions; close them or reduce staleness if a heavy migration is running.

## Operational Checklist

Before submitting a non-trivial schema change to production:

1. **Test in a staging instance with comparable data volume.** Schema-update timing on a 1 GB staging copy tells you nothing about a 1 TB production table.
2. **Validate data preconditions.** For `NOT NULL`/size constraints, run the appropriate `SELECT COUNT(*) WHERE ...` first.
3. **Check for view dependencies.** `SELECT * FROM information_schema.views WHERE view_definition LIKE '%column_name%'`.
4. **Schedule for off-peak.** Background operations run at lower priority; lower production load means faster completion.
5. **Submit one batch.** Group related DDLs; don't drip them in.
6. **Monitor the operation.** `gcloud spanner operations describe`. Have a kill switch (`gcloud spanner operations cancel`).
7. **Plan rollback for application code, not for schema.** Most schema changes can't be cleanly rolled back; the safe path is forward-only with backwards-compatible code (dual-read/dual-write) for one or more deploys.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| `ALTER TABLE T ALTER COLUMN c NOT NULL` without validating NULLs first | Immediate write rejection; potential outage |
| Submitting many one-off `ALTER`/`CREATE INDEX` calls instead of batching | More operations to track; no shared scan work |
| Running long schema updates during traffic peaks | Update takes longer; competes with serving load |
| Assuming `ALTER COLUMN` can change types arbitrarily | Many conversions are unsupported; copy-rename instead |
| Renaming a column referenced by a view without updating the view first | Schema update fails |
| Trying to "un-interleave" a table | Not supported; recreate |
| Adding a `FOREIGN KEY` to a table with existing violating data | Validation fails; constraint never applies |

## Common Pitfalls

- **Estimated times in the docs are optimistic.** Plan for the upper end of the range, not the average.
- **Cancelled operations don't always fully roll back instantly.** Some intermediate state may persist briefly.
- **Schema migrations on multi-region instances are slower** because changes propagate across regions.
- **`information_schema` queries** are how you introspect — use it to find columns, indexes, views referencing a column you're about to change.
- **Monitoring the operation reveals only progress, not data correctness.** A successful operation isn't proof the new constraint is what you wanted; verify with a `SELECT` after.

## Sources

- https://cloud.google.com/spanner/docs/schema-updates
- https://cloud.google.com/spanner/docs/schema-and-data-model
