# Eval report: `sqlite`

- Cases: **6**
- Expectations met: **3/6** (skill_wins 2/4, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **2**, baseline won **0**, ties **4**
- Rubric pass-rate (over 5 scored case(s)): baseline **70%**, skill **75%** (Δ **+5%**)
- CLI cost: **$0.47** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `busy-storms` | skill_wins | ✗ | **tie** | 100% | 100% |
| `pragmas-on-open` | skill_wins | ✗ | **tie** | 100% | 100% |
| `strict-tables` | skill_wins | ✓ | **skill** | 67% | 67% |
| `json-index` | skill_wins | ✓ | **skill** | 50% | 75% |
| `simplest-write-tx` | skill_wins_strict | ✗ | **tie** | 33% | 33% |
| `offtopic-python-comprehension` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `busy-storms`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Our Go service uses SQLite and we're getting SQLITE_BUSY errors all over
the place under modest load — maybe a couple writes per second on a
single-machine deployment. What's wrong and how do I fix it?
```

**Judge:** **tie** — Both answers are excellent and cover all four rubric criteria thoroughly. Answer A is slightly more structured with a clean checklist and mentions the WAL checkpoint issue with long-running reads. Answer B provides a slightly better explanation of why BEGIN DEFERRED causes unresolvable deadlocks (the busy handler isn't invoked for upgrade conflicts) and includes useful sanity checks about multi-process and network filesystem scenarios. Overall they are essentially equivalent in quality and completeness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends WAL journal mode | tie |
| mentions busy_timeout | tie |
| recommends BEGIN IMMEDIATE for writers | baseline |
| mentions two-pool / single writer pattern | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✓ | `BEGIN IMMEDIATE` |
| mentions two-pool / single writer pattern | ✓ | `two pool` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode = WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✓ | `BEGIN IMMEDIATE` |
| mentions two-pool / single writer pattern | ✓ | `SetMaxOpenConns(1)` |

<details><summary>Baseline answer</summary>

# SQLite under load in Go — fixing `SQLITE_BUSY`

This is one of the most common pitfalls with SQLite in Go. The good news: a couple writes per second is well within SQLite's capabilities. The bad news: the defaults of `database/sql` + `mattn/go-sqlite3` (or `modernc.org/sqlite`) are actively hostile to concurrent access. Here's what's going wrong and how to fix it.

## The root cause

SQLite allows **one writer at a time, period**. When a second connection tries to write while another is writing, it gets `SQLITE_BUSY`. Two things conspire to make this much worse than it should be in Go:

1. **`database/sql` opens a pool of connections.** Each connection is essentially an independent SQLite "session." So your single process behaves like multiple concurrent clients fighting over the database file.
2. **The default journal mode is `DELETE` (rollback journal)**, which means readers block writers and writers block readers. Mixed read/write workloads serialize badly.

## The fix, in order of importance

### 1. Enable WAL mode

This is the single biggest change. WAL lets readers and writers proceed concurrently (still one writer, but readers don't block):

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;   -- safe with WAL, much faster than FULL
```

Run these once at startup (they persist for `journal_mode`, but `synchronous` is per-connection — set it in your DSN).

### 2. Set a busy timeout

By default SQLite returns `SQLITE_BUSY` immediately. Tell it to wait and retry instead:

```sql
PRAGMA busy_timeout=5000;   -- milliseconds
```

This alone eliminates the vast majority of `SQLITE_BUSY` errors you're seeing.

### 3. Use separate pools for reads and writes

This is the trick most people miss. Open the database **twice**:

```go
// Writer: exactly one connection
writeDB, _ := sql.Open("sqlite3",
    "file:app.db?_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_txlock=immediate")
writeDB.SetMaxOpenConns(1)

// Reader: many connections OK
readDB, _ := sql.Open("sqlite3",
    "file:app.db?_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&mode=ro")
readDB.SetMaxOpenConns(max(4, runtime.NumCPU()))
```

Why `MaxOpenConns(1)` for the writer? Because there is only ever one writer in SQLite anyway. Forcing serialization in Go avoids deadlock scenarios where two pool connections each hold a read lock and both try to upgrade to write at the same time — a situation `busy_timeout` cannot resolve and which produces `SQLITE_BUSY` immediately, regardless of timeout.

### 4. Use `BEGIN IMMEDIATE` for write transactions

The default `BEGIN` is "deferred" — the connection starts as a reader and tries to upgrade when it hits the first `INSERT`/`UPDATE`. If another connection has upgraded first, you deadlock and get `SQLITE_BUSY` immediately (the busy handler is not invoked for upgrade conflicts).

`_txlock=immediate` in the DSN above makes Go's `db.Begin()` issue `BEGIN IMMEDIATE`, which acquires the write lock up front and lets `busy_timeout` actually do its job.

### 5. Don't hold transactions open

A long-running write transaction starves every other writer. Keep transactions short and don't do network I/O or user-facing waits inside them.

## Putting it together

A reasonable DSN for the writer:

```
file:app.db?_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_txlock=immediate&_foreign_keys=on&cache=shared
```

With `MaxOpenConns(1)` on the writer pool, a separate read-only pool, and WAL enabled, a couple of writes per second should be utterly trivial — SQLite can do thousands per second on a laptop SSD with this setup.

## Quick sanity checks

- Are you running multiple OS processes against the same DB file? WAL works across processes but the single-writer rule still applies — and `MaxOpenConns(1)` only helps within one process. If you have multiple processes, you need to either consolidate or accept some retry logic.
- Is the DB file on a network filesystem (NFS, SMB)? Don't. SQLite's locking is unreliable there.
- Are you using `modernc.org/sqlite`? The PRAGMA query string parameter names are slightly different (no underscore prefix); check its docs.

Fix WAL + busy_timeout + separate read/write pools + `BEGIN IMMEDIATE`, in that order, and the errors should disappear.

</details>

<details><summary>Skill-loaded answer</summary>

# SQLite Under Load in Go: Why You're Getting SQLITE_BUSY

A couple of writes per second is *trivial* for SQLite — it can do thousands. So the problem isn't load, it's almost certainly **how the Go `database/sql` connection pool interacts with SQLite's locking model**.

## The root cause

SQLite allows only **one writer at a time** for the entire database. When you open a connection in Go via `database/sql`, the pool will happily open many connections and hand them out to concurrent goroutines. The moment two of those connections try to write simultaneously, one gets `SQLITE_BUSY`.

There are usually three compounding issues:

1. **Default journal mode (DELETE)** — readers block writers and vice versa.
2. **No busy timeout** — the second writer gives up *immediately* instead of waiting.
3. **Multiple writer connections in the pool** — Go opens N connections, all racing for the write lock.

## The fix (in order of importance)

### 1. Enable WAL mode

Switch to Write-Ahead Logging. This is the single biggest improvement:

```sql
PRAGMA journal_mode = WAL;
```

In WAL mode, readers don't block the writer and the writer doesn't block readers. You only contend on writer-vs-writer.

### 2. Set a busy timeout

Tell SQLite to wait (and retry internally) instead of returning BUSY immediately:

```sql
PRAGMA busy_timeout = 5000;  -- milliseconds
```

Most modern SQLite drivers let you set this in the DSN.

### 3. Use *two* connection pools

This is the trick most Go + SQLite projects converge on:

```go
// One writer connection — serializes all writes
writeDB, _ := sql.Open("sqlite", dsn)
writeDB.SetMaxOpenConns(1)

// Many reader connections — concurrent in WAL mode
readDB, _ := sql.Open("sqlite", dsn)
readDB.SetMaxOpenConns(max(4, runtime.NumCPU()))
```

Route writes (INSERT/UPDATE/DELETE and write-transactions) to `writeDB`, reads to `readDB`. With `MaxOpenConns(1)` on the writer, Go itself serializes writers, so they never collide and never see BUSY from each other.

### 4. Use the right DSN options

For `mattn/go-sqlite3`:

```
file:app.db?_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_txlock=immediate
```

For `modernc.org/sqlite`:

```
file:app.db?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)&_pragma=synchronous(NORMAL)
```

Notes on the options:
- `_synchronous=NORMAL` is safe under WAL and much faster than FULL.
- `_txlock=immediate` makes `BEGIN` immediately acquire the write lock instead of upgrading a read transaction to a write one mid-flight — that upgrade path is the classic source of `SQLITE_BUSY` on `COMMIT`.

### 5. Avoid long-running read transactions

In WAL mode, a long-running read holds the WAL open and prevents checkpointing, which can balloon the `-wal` file and indirectly cause stalls. Keep transactions short, and don't `SELECT` rows then sit on them.

## Quick checklist

- [ ] `PRAGMA journal_mode=WAL`
- [ ] `PRAGMA busy_timeout=5000`
- [ ] `PRAGMA synchronous=NORMAL`
- [ ] Separate write pool with `SetMaxOpenConns(1)`
- [ ] Use `BEGIN IMMEDIATE` (or `_txlock=immediate`) for write transactions
- [ ] Keep transactions short

Do those and `SQLITE_BUSY` should essentially vanish at your load level — and SQLite will comfortably handle 10–100x more than what you're throwing at it now.

If you want, share your current DSN and pool setup (and which driver you're on — `mattn/go-sqlite3`, `modernc.org/sqlite`, or `crawshaw.io/sqlite`) and I can give you exact code.

</details>

---

### `pragmas-on-open`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I'm using `database/sql` with the SQLite driver in Go. I run
`db.Exec("PRAGMA foreign_keys=ON")` right after `sql.Open`, but my
foreign key constraints still don't seem to be enforced. What gives?
```

**Judge:** **tie** — Both answers are excellent and cover all three rubric criteria: they identify that foreign_keys is per-connection, explain that database/sql opens connections lazily via a pool, and recommend the DSN-based pragma approach. Answer B adds a fourth fix (db.Conn()) and covers a third driver (ncruces), while Answer A is slightly more concise. Neither has a meaningful advantage over the other on the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies pragma is per-connection | tie |
| recommends DSN-based pragma | tie |
| mentions database/sql opening lazily / multiple connections | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies pragma is per-connection | ✓ | `per-connection` |
| recommends DSN-based pragma | ✓ | `DSN` |
| mentions database/sql opening lazily / multiple connections | ✓ | `new connection` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies pragma is per-connection | ✓ | `per-connection` |
| recommends DSN-based pragma | ✓ | `DSN` |
| mentions database/sql opening lazily / multiple connections | ✓ | `new connection` |

<details><summary>Baseline answer</summary>

# The Problem: Connection Pooling

`database/sql` is a **connection pool**, not a single connection. When you call `db.Exec("PRAGMA foreign_keys=ON")`, that PRAGMA is applied to whichever single connection happens to handle that one statement. As soon as that connection goes back to the pool (or a different one is checked out for your next query), you're back to the SQLite default — foreign keys **off**.

In SQLite, `foreign_keys` is a *per-connection* setting, not a per-database one. So you need every connection in the pool to have it enabled.

## Fix 1 (recommended): Enable it in the DSN

Both popular SQLite drivers support setting PRAGMAs via the connection string, which means every new connection the pool opens will have the setting applied:

**`mattn/go-sqlite3`:**
```go
db, err := sql.Open("sqlite3", "file:app.db?_foreign_keys=on")
```

**`modernc.org/sqlite`:**
```go
db, err := sql.Open("sqlite", "file:app.db?_pragma=foreign_keys(1)")
```

While you're at it, you almost certainly also want:
```
?_journal_mode=WAL&_foreign_keys=on&_busy_timeout=5000
```

## Fix 2: Use a `Connector` with an init hook

If you can't use the DSN approach, register a driver that runs the PRAGMA on every new connection. With `mattn/go-sqlite3`:

```go
sql.Register("sqlite3_fk", &sqlite3.SQLiteDriver{
    ConnectHook: func(c *sqlite3.SQLiteConn) error {
        _, err := c.Exec("PRAGMA foreign_keys=ON;", nil)
        return err
    },
})
db, _ := sql.Open("sqlite3_fk", "app.db")
```

## Fix 3 (band-aid): Pin to one connection

```go
db.SetMaxOpenConns(1)
db.Exec("PRAGMA foreign_keys=ON")
```

This works but throws away concurrency, so it's really only suitable for tiny tools or tests.

## Quick verification

Once you think you've fixed it, confirm from a fresh connection:

```go
var on int
db.QueryRow("PRAGMA foreign_keys").Scan(&on)
fmt.Println("FK enforcement:", on == 1)
```

If that prints `true` consistently across many calls (try it in a loop), you're good. The DSN-based approach is the one I'd reach for by default.

</details>

<details><summary>Skill-loaded answer</summary>

# The Problem: Connection Pooling

`database/sql` is not a single connection — it's a **pool** of connections. When you call `db.Exec("PRAGMA foreign_keys=ON")`, that PRAGMA is applied to **only one** connection in the pool (whichever one happened to serve that `Exec` call). Every other connection — and any new connections the pool opens later — will have foreign keys **off** (the SQLite default).

So your next query likely runs on a different connection where FKs are still disabled, and the constraint silently isn't enforced.

This is also why `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout`, `PRAGMA synchronous`, etc. are notorious sources of the same bug.

# Fixes (pick one)

## 1. Use a DSN parameter (cleanest)

Most SQLite drivers accept PRAGMAs in the connection string, so they're applied every time a new connection is opened.

**`mattn/go-sqlite3`:**
```go
db, err := sql.Open("sqlite3", "file:app.db?_foreign_keys=on")
```

**`modernc.org/sqlite`:**
```go
db, err := sql.Open("sqlite", "file:app.db?_pragma=foreign_keys(1)")
```

**`ncruces/go-sqlite3`:**
```go
db, err := sql.Open("sqlite3", "file:app.db?_pragma=foreign_keys(on)")
```

## 2. Register a `ConnectHook` (mattn driver)

```go
sql.Register("sqlite3_fk",
    &sqlite3.SQLiteDriver{
        ConnectHook: func(conn *sqlite3.SQLiteConn) error {
            _, err := conn.Exec("PRAGMA foreign_keys=ON;", nil)
            return err
        },
    })

db, err := sql.Open("sqlite3_fk", "app.db")
```

This guarantees every new connection in the pool has FKs enabled.

## 3. Force a single connection (workaround)

```go
db.SetMaxOpenConns(1)
```

This works but throws away concurrency, so it's only really suitable for tiny CLIs or tests.

## 4. Use `db.Conn()` and stick to it

If you only need it for a particular section of code:

```go
conn, _ := db.Conn(ctx)
defer conn.Close()
conn.ExecContext(ctx, "PRAGMA foreign_keys=ON")
// use conn for subsequent queries...
```

Not what you want app-wide, but useful in narrow cases.

# How to verify

After whichever fix you choose, run:

```go
var v int
db.QueryRow("PRAGMA foreign_keys").Scan(&v)
fmt.Println("FK:", v) // should print 1
```

Run it in a loop a few times — if any iteration prints `0`, the pool is still serving you raw connections.

# Recommendation

Use **option 1** (DSN parameter) if your driver supports it — it's a one-line change and applies to every connection automatically. Fall back to **option 2** (ConnectHook) if you need to set multiple PRAGMAs or do other per-connection setup.

</details>

---

### `strict-tables`

**Expected:** `skill_wins` · **Met:** ✓

**Prompt**

```
I have a table with an INTEGER column that somehow ended up storing the
string 'banana'. SQLite never complained on insert. How is this even
legal, and how do I prevent it going forward?
```

**Judge:** **skill** — Both answers are nearly identical in quality, covering type affinity, STRICT tables, and migration. Answer A provides a slightly more complete and clearly structured migration recipe (the recreate-and-copy pattern with explicit SQL steps), which directly addresses the rubric's requirement about migration path for existing tables. Answer B mentions finding offenders but doesn't show the full recreate-and-copy recipe as explicitly. Both are excellent, but A edges out on the migration criterion.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains type affinity | tie |
| recommends STRICT tables | tie |
| mentions migration path for existing tables | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains type affinity | ✓ | `Type Affinit` |
| recommends STRICT tables | ✓ | `strict` |
| mentions migration path for existing tables | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains type affinity | ✓ | `Type Affinit` |
| recommends STRICT tables | ✓ | `STRICT` |
| mentions migration path for existing tables | ✗ | |

<details><summary>Baseline answer</summary>

# SQLite Type Affinity: Why 'banana' Fits in an INTEGER Column

## Why this is "legal"

SQLite uses **type affinity** rather than strict typing (its historical "manifest typing" model). The column type you declare is treated as a *hint*, not a constraint. Each value carries its own storage class (NULL, INTEGER, REAL, TEXT, BLOB), and SQLite tries to coerce values into the column's affinity on insert — but if the value can't be coerced (like `'banana'` into INTEGER), SQLite happily stores it as TEXT anyway.

The only column that enforces its declared type is `INTEGER PRIMARY KEY` (the rowid alias), and even that has quirks.

## How to prevent it going forward

You have three good options, in increasing order of strictness:

### 1. STRICT tables (SQLite 3.37+, released Nov 2021) — **recommended**

```sql
CREATE TABLE fruit_inventory (
    id     INTEGER PRIMARY KEY,
    count  INTEGER NOT NULL,
    name   TEXT NOT NULL
) STRICT;
```

With `STRICT`, inserting `'banana'` into `count` raises:
```
Error: cannot store TEXT value in INTEGER column
```

Allowed types in STRICT tables: `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, `ANY`.

### 2. CHECK constraints (works on any SQLite version)

```sql
CREATE TABLE fruit_inventory (
    id     INTEGER PRIMARY KEY,
    count  INTEGER NOT NULL CHECK (typeof(count) = 'integer'),
    name   TEXT    NOT NULL CHECK (typeof(name)  = 'text')
);
```

`typeof()` inspects the actual storage class of the stored value, so this catches the coercion failure cleanly.

### 3. Migrate existing data first

Before adding either guard, find the offenders:

```sql
SELECT rowid, count FROM fruit_inventory WHERE typeof(count) != 'integer';
```

Then fix or delete them, since `STRICT` and `CHECK` won't let you rebuild the table while bad rows exist.

## Quick recommendation

If you're on SQLite ≥ 3.37 (almost certainly true in 2026), just use **`STRICT` tables**. It's the closest SQLite gets to the type enforcement you'd expect from Postgres or MySQL, and it eliminates an entire category of silent data corruption bugs — including any sneaking into your `sqlite/` directory from eval runs.

</details>

<details><summary>Skill-loaded answer</summary>

# SQLite's "Type Affinity" — A Feature, Not a Bug 🍌

What you've encountered is SQLite's **type affinity** system, which is fundamentally different from every other major SQL database.

## Why this is "legal"

In SQLite, column types are **suggestions, not constraints**. When you declare a column as `INTEGER`, SQLite gives it INTEGER *affinity* — meaning it will *try* to convert values to integers when possible, but if it can't, it just stores whatever you gave it. The string `'banana'` can't be coerced to an integer, so SQLite shrugs and stores the text.

This behavior comes from SQLite's design philosophy of "manifest typing" — types belong to *values*, not *columns*. The only exception historically was `INTEGER PRIMARY KEY`, which is strictly enforced as a rowid alias.

## How to prevent it going forward

You have two good options, depending on your SQLite version:

### Option 1: STRICT tables (SQLite 3.37.0+, released Nov 2021)

This is the modern, recommended fix. Just append `STRICT` to your `CREATE TABLE`:

```sql
CREATE TABLE measurements (
    id    INTEGER PRIMARY KEY,
    count INTEGER NOT NULL,
    label TEXT
) STRICT;
```

Now `INSERT INTO measurements (count) VALUES ('banana')` will fail with:
```
Error: cannot store TEXT value in INTEGER column measurements.count
```

In STRICT mode, only these types are allowed: `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, `ANY`.

### Option 2: CHECK constraints (works on any version)

If you can't use STRICT (older SQLite, or you want finer control):

```sql
CREATE TABLE measurements (
    id    INTEGER PRIMARY KEY,
    count INTEGER NOT NULL CHECK (typeof(count) IN ('integer', 'null'))
);
```

The `typeof()` function returns the actual storage class of the value, so this rejects any non-integer write.

## Fixing the existing data

Before converting to STRICT, you'll need to clean up the offending rows:

```sql
-- Find them
SELECT rowid, count FROM measurements WHERE typeof(count) != 'integer';

-- Fix or delete them, then:
ALTER TABLE measurements RENAME TO measurements_old;
CREATE TABLE measurements (...) STRICT;
INSERT INTO measurements SELECT * FROM measurements_old;
DROP TABLE measurements_old;
```

## My recommendation

**Use `STRICT` on all new tables.** It brings SQLite's type behavior in line with what every developer coming from PostgreSQL/MySQL expects, and avoids exactly the kind of silent data corruption you just hit. Add `WITHOUT ROWID` too if you have a natural primary key and want the storage savings.

</details>

---

### `json-index`

**Expected:** `skill_wins` · **Met:** ✓

**Prompt**

```
I added a JSON column called `data` and created an index:
`CREATE INDEX events_user ON events(json_extract(data, '$.user_id'))`.
But my queries `WHERE data->>'user_id' = ?` are still doing full table
scans. What's wrong?
```

**Judge:** **skill** — Answer B explicitly recommends a generated column as a fix (Option 3) with the GENERATED ALWAYS AS syntax, which directly addresses the rubric's focus on recommending a STORED generated column. While neither answer mentions the STORED keyword explicitly, Answer B at least includes the generated column recommendation with proper syntax, whereas Answer A omits the generated column approach entirely. Both answers explain the expression mismatch and suggest EXPLAIN QUERY PLAN, but B is more complete per the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains the expression mismatch | tie |
| recommends generated column | skill |
| mentions STORED keyword | tie |
| suggests EXPLAIN QUERY PLAN | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✓ | `same expression` |
| recommends generated column | ✗ | |
| mentions STORED keyword | ✗ | |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✗ | |
| recommends generated column | ✓ | `generated column` |
| mentions STORED keyword | ✓ | `GENERATED ALWAYS` |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>Baseline answer</summary>

# The Problem: Expression Mismatch

SQLite's expression indexes are only used when the expression in your `WHERE` clause **textually/structurally matches** the indexed expression. Your index uses `json_extract(data, '$.user_id')` but your query uses `data->>'user_id'`. The planner doesn't treat these as equivalent — even though they look similar, they're not the same expression and they don't even return the same type:

- `json_extract(data, '$.user_id')` → returns the underlying JSON type (INTEGER, REAL, TEXT, etc.)
- `data->>'user_id'` → always returns SQL TEXT (or NULL)

So the index can't satisfy the query.

# Fix: Pick One and Be Consistent

**Option A — change the query to match the index:**
```sql
WHERE json_extract(data, '$.user_id') = ?
```

**Option B — change the index to match the query (usually what you want):**
```sql
DROP INDEX events_user;
CREATE INDEX events_user ON events(data->>'user_id');
```
Then `WHERE data->>'user_id' = ?` will use it.

# Verify with EXPLAIN QUERY PLAN

```sql
EXPLAIN QUERY PLAN
SELECT * FROM events WHERE data->>'user_id' = ?;
```
You should see `SEARCH events USING INDEX events_user (...)` instead of `SCAN events`.

# A Few Other Gotchas to Check

1. **Type affinity / parameter type.** If `user_id` is numeric in JSON and you indexed via `->>` (TEXT), make sure you bind the parameter as a string — otherwise SQLite may not match the index due to affinity differences. Using `json_extract` avoids this since it preserves the JSON type.
2. **`ANALYZE`.** Run `ANALYZE;` after creating the index so the planner has stats. Without it, on small tables it may still prefer a scan.
3. **NULLs / missing keys.** Rows where `data` is NULL or `user_id` is missing are still in the index (as NULL), but `= ?` won't match NULL — that's fine for equality lookups, just be aware.
4. **Determinism.** Expression indexes require deterministic expressions. Both `json_extract` and `->>` are deterministic, so you're good.
5. **SQLite version.** The `->>` operator requires SQLite 3.38.0+ (Feb 2022). On older versions it would parse as something else entirely. Check `SELECT sqlite_version();`.

In short: **make the expression in the `WHERE` clause identical to the expression in the `CREATE INDEX`**, and you'll get the index seek.

</details>

<details><summary>Skill-loaded answer</summary>

# The Problem: Expression Mismatch

SQLite's expression indexes only get used when the expression in your `WHERE` clause **textually matches** the expression used to build the index. You indexed `json_extract(data, '$.user_id')` but you're querying with `data->>'user_id'`. Even though they return the same value, SQLite's query planner doesn't see them as equivalent.

There's also a subtle semantic difference between the two:

- `json_extract(data, '$.user_id')` returns the value with its native JSON type (so a JSON string comes back as a SQL TEXT, a number as INTEGER/REAL, `null` as SQL NULL).
- `data->>'user_id'` (the `->>` operator) **always coerces to SQL TEXT** (or NULL). It's roughly `CAST(json_extract(...) AS TEXT)` with some nuances.

So even if SQLite *did* match them, the comparison semantics could differ.

# Fixes

Pick one of these — whichever matches how you want to query.

### Option 1: Make the index match the query

```sql
DROP INDEX events_user;
CREATE INDEX events_user ON events(data->>'user_id');
```

Now `WHERE data->>'user_id' = ?` will use it.

### Option 2: Make the query match the index

Keep the existing index and write:

```sql
WHERE json_extract(data, '$.user_id') = ?
```

### Option 3: Use a generated column (often the cleanest)

```sql
ALTER TABLE events
  ADD COLUMN user_id TEXT
  GENERATED ALWAYS AS (data->>'user_id');

CREATE INDEX events_user ON events(user_id);
```

Then queries like `WHERE user_id = ?` are obvious, indexable, and you don't have to remember the exact expression form.

# How to Verify

Always confirm with `EXPLAIN QUERY PLAN`:

```sql
EXPLAIN QUERY PLAN
SELECT * FROM events WHERE data->>'user_id' = '42';
```

You want to see something like `SEARCH events USING INDEX events_user (...)` rather than `SCAN events`.

# Other Gotchas to Check

1. **Parameter type mismatch.** If you bind an integer (`?` = `42`) but the indexed expression returns text (because `->>` coerces to TEXT), SQLite may not use the index efficiently due to type affinity rules. Bind the parameter as the same type the expression produces.
2. **`ANALYZE` not run.** After creating the index, run `ANALYZE;` so the planner has stats. Without it, the planner sometimes picks a scan for small or newly-built tables.
3. **SQLite version.** The `->` and `->>` operators require SQLite 3.38.0+ (Feb 2022). On older versions `->>` may parse but behave unexpectedly, or your build may not have JSON1 enabled at all (check with `SELECT sqlite_version();` and `PRAGMA compile_options;`).
4. **`NULL`s and missing keys.** Expression indexes don't index rows where the expression evaluates to NULL in a way that helps `IS NULL` lookups — but for `=` comparisons that's fine.

In your case, Option 1 or Option 3 is almost certainly what you want.

</details>

---

### `simplest-write-tx`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Just give me the simplest, fewest-lines way to write a row inside a
transaction in Go using `database/sql` with SQLite. I don't need
bells and whistles, just the shortest correct snippet.
```

**Judge:** **tie** — Neither answer addresses the core focus area: both use db.Begin() which generates BEGIN DEFERRED, neither uses BEGIN IMMEDIATE, and neither warns about SQLITE_BUSY or contention issues. Answer A at least acknowledges there's a 'simplest' version vs a 'correct' version, but neither answer meets the rubric criteria at all.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows BEGIN IMMEDIATE for the write tx | tie |
| avoids recommending plain BeginTx without warning | tie |
| warns about SQLITE_BUSY / contention / DEFERRED | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✗ | |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✗ | |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✗ | |

<details><summary>Baseline answer</summary>

```go
tx, _ := db.Begin()
tx.Exec("INSERT INTO t(col) VALUES(?)", val)
tx.Commit()
```

If you want it actually correct (handling errors and rollback on failure):

```go
tx, err := db.Begin()
if err != nil {
    return err
}
if _, err := tx.Exec("INSERT INTO t(col) VALUES(?)", val); err != nil {
    tx.Rollback()
    return err
}
return tx.Commit()
```

</details>

<details><summary>Skill-loaded answer</summary>

```go
tx, err := db.Begin()
if err != nil {
    return err
}
if _, err := tx.Exec("INSERT INTO t(col) VALUES(?)", val); err != nil {
    tx.Rollback()
    return err
}
return tx.Commit()
```

</details>

---

### `offtopic-python-comprehension`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the most idiomatic way to filter and transform a list in
Python using a single comprehension? Show me an example.
```

**Judge:** **tie** — Both answers are essentially equivalent in correctness, idiomaticity, and usefulness. They cover the same core concept with the same primary example, and both include the generator expression tip and the ternary vs. filter distinction. Answer A adds a map/filter comparison while Answer B adds a richer dict-based example, but neither addition is materially superior.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

The most idiomatic way is to combine filtering (`if`) and transformation in a single list comprehension:

```python
[expression for item in iterable if condition]
```

### Example

Say you have a list of numbers and you want the **squares of only the even numbers**:

```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

squared_evens = [n ** 2 for n in numbers if n % 2 == 0]

print(squared_evens)
# [4, 16, 36, 64, 100]
```

### How to read it

- `n ** 2` → the **transformation** (what each element becomes)
- `for n in numbers` → the **iteration**
- `if n % 2 == 0` → the **filter** (only keep evens)

### A slightly richer example

Extracting and uppercasing the names of users who are active:

```python
users = [
    {"name": "alice", "active": True},
    {"name": "bob", "active": False},
    {"name": "carol", "active": True},
]

active_names = [u["name"].upper() for u in users if u["active"]]

print(active_names)
# ['ALICE', 'CAROL']
```

### When to reach for something else

- If the logic gets complex (multiple conditions, nested transformations), prefer a regular `for` loop or a generator function for readability.
- If you don't need the full list in memory, use a **generator expression** instead — same syntax, just swap `[]` for `()`:

  ```python
  total = sum(n ** 2 for n in numbers if n % 2 == 0)
  ```

- For conditional *transformation* (not filtering), put the `if/else` **before** the `for`:

  ```python
  [n ** 2 if n % 2 == 0 else n for n in numbers]
  ```

The rule of thumb: **filter `if` goes at the end, ternary `if/else` goes at the front.**

</details>

<details><summary>Skill-loaded answer</summary>

The most idiomatic way to filter and transform a list in Python in a single pass is to use a **list comprehension** with an `if` clause for filtering and an expression at the front for transformation.

## Syntax

```python
[expression for item in iterable if condition]
```

- **`expression`** — what each kept item is transformed into
- **`condition`** — the filter predicate (only items where this is `True` are included)

## Example

Say you have a list of numbers and you want the **squares of only the even numbers**:

```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

squared_evens = [n ** 2 for n in numbers if n % 2 == 0]

print(squared_evens)
# [4, 16, 36, 64, 100]
```

## Why this is preferred over `map` + `filter`

You *could* write the same thing with `map` and `filter`:

```python
squared_evens = list(map(lambda n: n ** 2, filter(lambda n: n % 2 == 0, numbers)))
```

…but the comprehension is generally considered more Pythonic because it:

1. Reads top-to-bottom, left-to-right closer to plain English ("squares of n for each n in numbers if n is even").
2. Avoids the overhead and noise of `lambda`.
3. Keeps the transformation and the filter visually together.

## Bonus: conditional *expression* vs. filter

Don't confuse the trailing `if` (filter) with a ternary `if/else` in the expression position (which transforms but keeps every element):

```python
# Filters out odd numbers — result has fewer elements
[n ** 2 for n in numbers if n % 2 == 0]

# Keeps every element, but transforms differently — same length as input
[n ** 2 if n % 2 == 0 else n for n in numbers]
```

## When to reach for a generator expression instead

If you're going to immediately consume the result (e.g., feed it to `sum`, `any`, `max`), drop the brackets to avoid building an intermediate list:

```python
total = sum(n ** 2 for n in numbers if n % 2 == 0)  # 220
```

Same syntax, lazier evaluation — also very idiomatic.

</details>

---
