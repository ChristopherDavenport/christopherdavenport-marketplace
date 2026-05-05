# Schema Design — Types, Primary Keys, ALTER TABLE

SQLite's defaults are forgiving in ways that surprise developers coming from Postgres or MySQL. Type declarations are advisory under the legacy affinity rules. Foreign keys parse but don't enforce until you flip a per-connection pragma. `ALTER TABLE` covers maybe a third of the operations you'd reach for elsewhere. This reference covers the schema-level decisions that prevent the worst surprises and the recipe for everything `ALTER TABLE` won't do.

## Type Affinity vs `STRICT`

A regular SQLite table has **type affinity**, not types. Each column has one of five storage classes (`NULL`, `INTEGER`, `REAL`, `TEXT`, `BLOB`) and an affinity (`TEXT`, `NUMERIC`, `INTEGER`, `REAL`, `BLOB`) derived from the declared type. On `INSERT`, SQLite *tries* to coerce the value to match the affinity, but it stores whatever it can't coerce as-is.

```sql
CREATE TABLE loose (id INTEGER, name TEXT);
INSERT INTO loose VALUES ('banana', 42);  -- works! id stores 'banana', name stores '42'
SELECT typeof(id), typeof(name) FROM loose;  -- text, integer
```

This is on by default, has been since SQLite 3.0, and is responsible for an enormous amount of "how is this data even legal" tickets.

### `STRICT` tables (3.37+)

Append `STRICT` after the closing paren and SQLite enforces declared types like every other database:

```sql
CREATE TABLE strict_loose (
  id   INTEGER NOT NULL,
  name TEXT    NOT NULL
) STRICT;

INSERT INTO strict_loose VALUES ('banana', 42);
-- Error: cannot store TEXT value in INTEGER column strict_loose.id
```

`STRICT` tables only allow these column types: `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, and `ANY`. (Use `ANY` deliberately when you actually want a polymorphic column — it's the supported escape hatch.)

**Default to `STRICT` for every new table.** The only reason not to is interop with legacy code that depends on affinity coercion.

You cannot retrofit `STRICT` onto an existing table — that's a 12-step migration (below).

## Primary Keys

### `INTEGER PRIMARY KEY` is the rowid alias

Every regular SQLite table has a hidden 64-bit rowid. Declaring a column `INTEGER PRIMARY KEY` (and *only* this exact phrasing — `INT PRIMARY KEY` does not count) makes that column an alias for the rowid. The column shares storage with the rowid, lookups by it are O(log n) without a secondary index, and inserts get an automatically assigned monotonically increasing value if you don't supply one.

```sql
CREATE TABLE users (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL
) STRICT;
```

This is the right default for new tables.

### `AUTOINCREMENT` — almost never what you want

Adding `AUTOINCREMENT` after `INTEGER PRIMARY KEY` changes one thing: it guarantees the assigned ID is strictly greater than any value ever used in the table, including for deleted rows. The cost is a row in the `sqlite_sequence` table that's read and updated on every insert.

```sql
-- Don't do this unless you have a real reason:
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ...
) STRICT;
```

Without `AUTOINCREMENT`, SQLite picks `MAX(id) + 1`, which means deleted IDs at the high-water mark can be reused. For most application data this doesn't matter; for audit trails and external references where you must guarantee never-reused IDs, `AUTOINCREMENT` is the answer. Otherwise skip it.

### `WITHOUT ROWID`

Tables can be declared `WITHOUT ROWID`, which makes the user-defined primary key the actual on-disk B-tree key (rather than a secondary index pointing back to a hidden rowid). It's worth it when:

- The primary key is **not** a single `INTEGER` column (e.g. a composite key, or a `TEXT` UUID).
- Rows are narrow (a few columns, no large `TEXT` or `BLOB`).
- The dominant access is "look up by full PK".

```sql
CREATE TABLE user_settings (
  user_id INTEGER NOT NULL,
  key     TEXT    NOT NULL,
  value   TEXT,
  PRIMARY KEY (user_id, key)
) WITHOUT ROWID, STRICT;
```

When **not** to use it:

- Single `INTEGER` PK — `INTEGER PRIMARY KEY` is already as efficient as it gets.
- Wide rows or large `TEXT`/`BLOB` columns — these get stored on overflow pages keyed by rowid; without a rowid they get scattered into the index pages, which destroys cache locality.
- Tables with many secondary indexes — every index entry duplicates the full PK.

`WITHOUT ROWID` is permanent for the table — switching requires a 12-step migration.

## Generated Columns

Computed columns derived from other columns or expressions. Two flavors:

- `VIRTUAL` (default): not stored, computed on every read. Free disk, costs CPU per query.
- `STORED`: stored at insert/update time. Costs disk, free per query. Required for indexing JSON paths efficiently.

```sql
CREATE TABLE events (
  id        INTEGER PRIMARY KEY,
  data      BLOB NOT NULL,                                    -- JSONB blob
  user_id   TEXT GENERATED ALWAYS AS (data->>'user_id') STORED,
  created   INTEGER GENERATED ALWAYS AS (data->>'created_at') VIRTUAL
) STRICT;

CREATE INDEX events_user_id_idx ON events(user_id);
```

Use `STORED` when you want to index the column. `VIRTUAL` is fine for occasional reads or for documenting derived values.

## Constraints

```sql
CREATE TABLE accounts (
  id         INTEGER PRIMARY KEY,
  email      TEXT NOT NULL UNIQUE,
  status     TEXT NOT NULL DEFAULT 'active'
              CHECK (status IN ('active','suspended','deleted')),
  balance    INTEGER NOT NULL DEFAULT 0
              CHECK (balance >= 0),
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
) STRICT;
```

- `NOT NULL` and `UNIQUE` work as expected.
- `DEFAULT` accepts literals or `()`-wrapped expressions (`(unixepoch())`, `(uuid())`, etc.).
- `CHECK` runs on every insert/update; cheap inline expressions are fine, expensive ones are not.
- `UNIQUE` creates an implicit index. For composite uniqueness, use a table-level constraint or a unique index directly.

## Foreign Keys — Declared vs Enforced

SQLite parses `FOREIGN KEY` declarations but **does not enforce them by default**. Enforcement is a per-connection pragma:

```sql
PRAGMA foreign_keys = ON;
```

This is the single sharpest edge in SQLite. The pragma is per-connection, so:

- It must be set on **every** connection your code opens.
- In Go's `database/sql`, that means in the DSN — pool members opened later will not inherit a pragma you set with `db.Exec` after `Open`.
- During the 12-step `ALTER TABLE` recipe, you must explicitly turn it **off** so you can rebuild the table without cascade fireworks.

```sql
CREATE TABLE orders (
  id          INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
  ...
) STRICT;
```

Cascade options: `RESTRICT` (default — refuse), `NO ACTION` (refuse on commit), `CASCADE` (delete/update children), `SET NULL`, `SET DEFAULT`. Pick `RESTRICT` unless you have a specific reason.

## `ALTER TABLE` — What's Supported

| Operation | Version | Supported |
|---|---|---|
| `ADD COLUMN` | All | Yes (column can have `DEFAULT` and `NOT NULL` if `DEFAULT` is non-NULL) |
| `RENAME TO` (table) | All | Yes |
| `RENAME COLUMN` | 3.25+ | Yes — rewrites references in views, triggers, etc. |
| `DROP COLUMN` | 3.35+ | Yes — but rewrites the table |
| Change column type | — | **No** — needs full table rewrite |
| Change `DEFAULT` | — | **No** |
| Add `CHECK` constraint | — | **No** |
| Reorder columns | — | **No** |
| Add `NOT NULL` to existing column | — | **No** |
| Convert to `STRICT` | — | **No** |
| Convert to `WITHOUT ROWID` | — | **No** |

For everything in the No rows, you need:

## The 12-Step Recipe

The official recipe for any unsupported `ALTER TABLE`. From sqlite.org/lang_altertable.html.

```sql
PRAGMA foreign_keys = OFF;          -- 1. Disable FK enforcement
BEGIN;                              -- 2. Open transaction

-- 3. Read the existing schema you want to preserve
--    (indexes, triggers, views referencing the table) so you can recreate them.
--    Query: SELECT sql FROM sqlite_schema WHERE tbl_name='old_table' AND type IN ('index','trigger','view');

CREATE TABLE new_table (...) STRICT;  -- 4. Create new table with the new schema

INSERT INTO new_table SELECT ... FROM old_table;  -- 5. Copy data
                                                   --    (this is where bad rows surface under STRICT)

DROP TABLE old_table;               -- 6. Drop the old table

ALTER TABLE new_table RENAME TO old_table;  -- 7. Rename new to old

-- 8. Recreate indexes, triggers, views from step 3.

PRAGMA foreign_key_check;           -- 9. Verify FK invariants still hold

COMMIT;                             -- 10. Commit

PRAGMA foreign_keys = ON;           -- 11. Re-enable FK enforcement (this connection only)

PRAGMA integrity_check;             -- 12. Verify no corruption (cheap; do it)
```

Two non-obvious points:

- **Foreign keys must be disabled before `BEGIN`**, not inside the transaction. Toggling `foreign_keys` mid-transaction is a no-op.
- **Don't enable foreign keys before `COMMIT`** — re-enabling them while the schema is half-rebuilt can fail constraint checks on intermediate state.

If you have multiple connections open, each one needs `PRAGMA foreign_keys = ON` set independently after the migration. Restart your service or recycle pool connections after a schema change of this shape.

## Sources

- https://www.sqlite.org/datatype3.html — type affinity rules
- https://www.sqlite.org/stricttables.html — `STRICT` tables
- https://www.sqlite.org/lang_createtable.html — `CREATE TABLE`, `WITHOUT ROWID`, generated columns
- https://www.sqlite.org/withoutrowid.html — when to use `WITHOUT ROWID`
- https://www.sqlite.org/autoinc.html — `AUTOINCREMENT` semantics and cost
- https://www.sqlite.org/foreignkeys.html — foreign key enforcement
- https://www.sqlite.org/lang_altertable.html — `ALTER TABLE` and the 12-step recipe
