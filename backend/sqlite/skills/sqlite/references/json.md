# JSON1 / JSONB

The JSON1 extension ships built into SQLite (no extra build flag since 3.38). The 3.45 release added `JSONB`, a binary on-disk format that skips the parse step on every extract. The 3.38 release added the `->` and `->>` operators, which look like Postgres and read much better than the function syntax. Indexing JSON paths is done with generated columns — there's no special "JSON index" type.

## Storage: `JSON` (text) vs `JSONB` (binary)

```sql
-- Pre-3.45 or when interop with text JSON matters: store as TEXT
CREATE TABLE events_text (
  id   INTEGER PRIMARY KEY,
  data TEXT NOT NULL CHECK (json_valid(data))
) STRICT;

-- 3.45+: store as JSONB (BLOB) — faster repeated extracts
CREATE TABLE events_jsonb (
  id   INTEGER PRIMARY KEY,
  data BLOB NOT NULL CHECK (jsonb_valid(data))  -- jsonb_valid is 3.45+
) STRICT;

-- Insert: jsonb() converts JSON text → JSONB binary
INSERT INTO events_jsonb(data) VALUES (jsonb('{"user_id":"u1","amount":42}'));

-- Read back as text (e.g. for serialization to a client):
SELECT json(data) FROM events_jsonb;
```

Comparison:

| | `JSON` (TEXT) | `JSONB` (BLOB) |
|---|---|---|
| On-disk format | Human-readable JSON text | Binary, internal format |
| Parse cost per extract | Re-parses every read | Decoded inline |
| Storage size | Original text bytes | Comparable; binary is sometimes smaller |
| Tooling friendliness | `cat`, `grep`, dump tools all work | Opaque without `json()` to convert back |
| Interop with non-SQLite consumers | Direct | Must convert with `json()` first |
| Writes | Fast (no encoding) | Encoding cost on insert; usually negligible |

**Use `JSONB` when reads vastly outnumber writes**, when the same JSON column is extracted from many times per query, or when on-disk size matters. **Use text `JSON` when you frequently dump or otherwise inspect the file outside of SQLite.**

The `CHECK (json_valid(...))` constraint catches bad JSON at write time. Always include it.

## Operators: `->` and `->>` (3.38+)

```sql
SELECT data->'user'    FROM events;  -- returns JSON (a JSON object/array/value)
SELECT data->>'user'   FROM events;  -- returns SQL value (text/integer/real/null)

SELECT data->'address'->>'city' FROM events;  -- chain: JSON object, then SQL value
SELECT data->'tags'->>0         FROM events;  -- index into array
```

Rule of thumb: use `->>` (returns a SQL value) in `WHERE`, `ORDER BY`, generated column expressions, and anywhere you want a typed scalar. Use `->` only when you want to traverse further into the JSON.

These operators replace the older `json_extract(data, '$.path')` syntax for most uses. They're equivalent but more readable.

## Common Functions

| Function | What it does |
|---|---|
| `json(x)` | Validate and minify; returns the JSON text |
| `jsonb(x)` | Convert JSON text to JSONB binary (3.45+) |
| `json_extract(j, path, ...)` | Extract one or more paths; returns scalar or JSON |
| `json_object('key', val, ...)` | Build a JSON object |
| `json_array(val, ...)` | Build a JSON array |
| `json_set(j, path, val)` | Insert or replace at path |
| `json_replace(j, path, val)` | Replace at path only if it exists |
| `json_remove(j, path)` | Delete a path |
| `json_patch(j, p)` | Merge `p` into `j` (RFC 7396 merge patch) |
| `json_valid(x)` | 1 if valid JSON text, 0 otherwise |
| `json_type(j, path?)` | Returns `'object'`, `'array'`, `'integer'`, etc. |
| `json_each(j)` | Virtual table — one row per top-level element |
| `json_tree(j)` | Virtual table — one row per element, recursive |

JSONB equivalents (3.45+) for the building/mutation functions: `jsonb_object`, `jsonb_array`, `jsonb_set`, `jsonb_replace`, `jsonb_remove`, `jsonb_patch`. They take and return JSONB; use them when the column is JSONB to avoid a text round-trip.

## Indexing JSON Paths

You cannot index a JSON column directly — the column is opaque from the planner's perspective. Index the **path** instead, via a generated column.

```sql
CREATE TABLE events (
  id      INTEGER PRIMARY KEY,
  data    BLOB NOT NULL CHECK (jsonb_valid(data)),
  user_id TEXT GENERATED ALWAYS AS (data->>'user_id') STORED,
  amount  INTEGER GENERATED ALWAYS AS (data->>'amount') STORED
) STRICT;

CREATE INDEX events_user_id_idx ON events(user_id);
CREATE INDEX events_amount_idx  ON events(amount);
```

Then query the generated column:

```sql
SELECT * FROM events WHERE user_id = 'u1';      -- uses index
SELECT * FROM events WHERE amount > 100;        -- uses index
```

Important details:

- **Use `STORED`, not `VIRTUAL`.** Virtual generated columns can't be indexed efficiently; the index would have to recompute the expression on every operation.
- **Query the generated column, not the JSON path.** `WHERE data->>'user_id' = 'u1'` and `WHERE user_id = 'u1'` produce the same result, but only the latter uses the index reliably across SQLite versions. Always query the column.
- **The generated column expression must be deterministic.** `json_extract` and `->>` are deterministic; `unixepoch()` is not.

You *can* use an expression index directly: `CREATE INDEX events_user_id_idx ON events(data->>'user_id')`. It works, but the textual matching is fussier — the query has to use the exact same expression. Generated columns are clearer and the planner matches them more reliably.

## `json_each` and `json_tree` — Unnesting Arrays

The SQLite analog of `UNNEST`. Both are table-valued functions you join against.

```sql
-- Find all events with a 'tags' array containing 'urgent'
SELECT e.*
FROM events e, json_each(e.data, '$.tags') t
WHERE t.value = 'urgent';
```

`json_each(j)` yields one row per top-level element of `j`. `json_each(j, '$.path')` yields one row per element at that path. Columns: `key`, `value`, `type`, `atom`, `id`, `parent`, `fullkey`, `path`.

`json_tree(j)` recursively descends, yielding one row for every element at every depth. Use when you need to find a value anywhere in a nested structure.

## When to Use a JSON Column vs a Child Table

| Decision | JSON column | Child table |
|---|---|---|
| Need to query/filter individual fields with indexes | Possible (generated column + index per field) | Natural — every column is queryable |
| Number of fields varies per row | Natural | Painful (sparse columns or EAV) |
| Strict schema, every row has the same shape | Use a normal table — JSON adds zero value | Natural |
| Treated as opaque most of the time, occasionally extracted | Natural | Overkill |
| Need to enforce relationships across nested data | Awkward | Foreign keys, CHECK constraints, etc. |
| Aggregations across nested arrays | `json_each` — works but not fast | Natural with `GROUP BY` |

Rule of thumb: **if you need to query or index more than two or three fields, you want a child table.** JSON shines for "configuration blob", "raw event payload", "user preferences object" — things you fetch whole and rarely dig into. As soon as your application code is reaching into the same paths repeatedly, those paths want to be columns.

A common middle ground: keep the raw JSON for fidelity (`data BLOB`), and **also** project the hot paths into generated columns. You get queryable indexed access to the fields you care about without having to migrate every time the upstream payload adds an optional field.

## Sources

- https://www.sqlite.org/json1.html — JSON1 functions
- https://www.sqlite.org/jsonb.html — JSONB binary format (3.45+)
- https://www.sqlite.org/draft/json1.html#jptr — `->` and `->>` operators
- https://www.sqlite.org/expridx.html — expression indexes (works with JSON paths)
- https://www.sqlite.org/gencol.html — generated columns
