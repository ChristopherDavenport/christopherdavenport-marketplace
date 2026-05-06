# Eval report: `sqlite`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **8**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.51** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 8/8 | 7 / 0 / 1 | 71% → 96% (+25%) |
| `haiku` | 7/8 | 7 / 1 / 0 | 61% → 96% (+36%) |
| `opus` ¹ | 7/8 | 6 / 1 / 1 | 80% → 96% (+17%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 6 | 6/6 | 6/6 | 5/6 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 0/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `busy-storms` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `pragmas-on-open` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `strict-tables` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `json-index` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `json-arrow-vs-double-arrow` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `covering-index-design` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ ✗ baseline |
| `simplest-write-tx` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-python-comprehension` | tie | ✓ = tie | ✗ ✗ baseline | ✓ = tie |

## Per-case detail

### `busy-storms`

**Prompt**

```
Our Go service uses SQLite and we're getting SQLITE_BUSY errors all over
the place under modest load — maybe a couple writes per second on a
single-machine deployment. What's wrong and how do I fix it?
```

**Judge focus:** The better answer addresses the root cause (default journal mode, missing
busy_timeout, BEGIN DEFERRED for writes, no writer/reader split), not
just "increase the timeout".

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A more thoroughly addresses all four root causes, particularly the subtle BEGIN DEFERRED vs BEGIN IMMEDIATE distinction which is the most commonly missed issue. It provides the `_txlock=immediate` DSN parameter as the cleanest solution, explains why setting pragmas via `db.Exec` after `sql.Open` doesn't work (a critical Go-specific gotcha), and covers the driver-specific DSN syntax differences. Answer B mentions `_txlock=immediate` only in a table without explanation, and its `WithTx` implementation still uses `BeginTx` with nil options (BEGIN DEFERRED) without addressing the upgrade problem.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends WAL journal mode | tie |
| mentions busy_timeout | skill |
| recommends BEGIN IMMEDIATE for writers | skill |
| mentions two-pool / single writer pattern | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✗ | |
| mentions two-pool / single writer pattern | ✓ | `SetMaxOpenConns(1)` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✓ | `BEGIN IMMEDIATE` |
| mentions two-pool / single writer pattern | ✓ | `SetMaxOpenConns(1)` |

<details><summary>sonnet: baseline answer</summary>

# Fixing SQLite SQLITE_BUSY Errors in Go

## Why This Is Happening

SQLite has a **single-writer architecture**. Your Go service is almost certainly hitting these common mistakes:

### Root Causes

```
┌─────────────────────────────────────────────────────────┐
│  1. Multiple connections competing for write locks      │
│  2. WAL mode not enabled (default journal mode)         │
│  3. Busy timeout not set (default = 0ms, fail instantly)│
│  4. Transactions held open too long                     │
│  5. Connection pool with multiple writers               │
└─────────────────────────────────────────────────────────┘
```

---

## The Fix

### 1. Use a Single Writer Connection + Separate Reader Pool

```go
package database

import (
    "context"
    "database/sql"
    "fmt"
    _ "github.com/mattn/go-sqlite3"
)

type DB struct {
    writer *sql.DB
    reader *sql.DB
}

func Open(path string) (*DB, error) {
    writer, err := openWriter(path)
    if err != nil {
        return nil, fmt.Errorf("open writer: %w", err)
    }

    reader, err := openReader(path)
    if err != nil {
        return nil, fmt.Errorf("open reader: %w", err)
    }

    return &DB{writer: writer, reader: reader}, nil
}

func openWriter(path string) (*sql.DB, error) {
    // Single connection for writes — SQLite only allows one writer anyway
    db, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_foreign_keys=ON")
    if err != nil {
        return nil, err
    }

    // CRITICAL: only one writer connection
    db.SetMaxOpenConns(1)
    db.SetMaxIdleConns(1)

    if err := db.Ping(); err != nil {
        return nil, err
    }

    return db, nil
}

func openReader(path string) (*sql.DB, error) {
    // Readers can be concurrent in WAL mode
    db, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_busy_timeout=5000&mode=ro&_foreign_keys=ON")
    if err != nil {
        return nil, err
    }

    // Multiple readers are fine with WAL
    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

### 2. Route Reads and Writes Appropriately

```go
// Write goes to the single writer
func (db *DB) Exec(ctx context.Context, query string, args ...any) (sql.Result, error) {
    return db.writer.ExecContext(ctx, query, args...)
}

// Reads go to the reader pool
func (db *DB) Query(ctx context.Context, query string, args ...any) (*sql.Rows, error) {
    return db.reader.QueryContext(ctx, query, args...)
}

// Transactions always use the writer
func (db *DB) WithTx(ctx context.Context, fn func(*sql.Tx) error) error {
    tx, err := db.writer.BeginTx(ctx, nil)
    if err != nil {
        return fmt.Errorf("begin tx: %w", err)
    }

    if err := fn(tx); err != nil {
        _ = tx.Rollback()
        return err
    }

    return tx.Commit()
}
```

### 3. Keep Transactions Short

```go
// BAD: transaction held open while doing other work
func (db *DB) BadExample(ctx context.Context, userID int) error {
    return db.WithTx(ctx, func(tx *sql.Tx) error {
        _, err := tx.ExecContext(ctx, "UPDATE users SET last_seen = ? WHERE id = ?", time.Now(), userID)
        if err != nil {
            return err
        }

        result := callSlowExternalAPI() // ← NEVER do this inside a transaction
        _, err = tx.ExecContext(ctx, "INSERT INTO logs (data) VALUES (?)", result)
        return err
    })
}

// GOOD: do all prep work outside the transaction
func (db *DB) GoodExample(ctx context.Context, userID int) error {
    result := callSlowExternalAPI() // ← outside the transaction

    return db.WithTx(ctx, func(tx *sql.Tx) error {
        _, err := tx.ExecContext(ctx, "UPDATE users SET last_seen = ? WHERE id = ?", time.Now(), userID)
        if err != nil {
            return err
        }
        _, err = tx.ExecContext(ctx, "INSERT INTO logs (data) VALUES (?)", result)
        return err
    })
}
```

### 4. Verify WAL Mode Is Actually Active

```go
func verifyWALMode(db *sql.DB) error {
    var mode string
    err := db.QueryRow("PRAGMA journal_mode").Scan(&mode)
    if err != nil {
        return err
    }
    if mode != "wal" {
        return fmt.Errorf("expected WAL mode, got %q — check your connection string", mode)
    }
    return nil
}
```

---

## Key PRAGMA Reference

| PRAGMA | Recommended Value | Why |
|--------|------------------|-----|
| `_journal_mode` | `WAL` | Readers don't block writers |
| `_busy_timeout` | `5000` (ms) | Retry instead of instant fail |
| `_synchronous` | `NORMAL` | Safe with WAL, much faster than FULL |
| `_foreign_keys` | `ON` | Enforce FK constraints |
| `_txlock` | `immediate` | Fail fast on write contention rather than mid-transaction |

---

## Checklist

```
[ ] WAL mode enabled
[ ] Writer pool capped at MaxOpenConns(1)
[ ] busy_timeout set (5000ms is a reasonable start)
[ ] No slow operations inside transactions
[ ] Rows closed promptly (defer rows.Close())
[ ] No connection string differences between connections
    (different pragmas = different effective settings)
```

---

## When You've Outgrown SQLite

If you're hitting these limits even after the fixes above, consider:
- **PostgreSQL/MySQL** — proper multi-writer support
- **Litestream** — SQLite replication if you want to stay on SQLite
- **rqlite** — distributed SQLite

For a few writes per second on a single machine, the fixes above should be more than sufficient. The most common culprit is `MaxOpenConns` not being set to `1` on the writer.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

`SQLITE_BUSY` under light load almost always means one of three specific mistakes, and they compound each other. Let me walk through each one, then show you the complete fix.

## The three root causes

### 1. Wrong journal mode

Check what you're running:

```sql
PRAGMA journal_mode;
```

If it returns `delete`, you're in classic rollback-journal mode. Every writer holds an `EXCLUSIVE` lock for the entire transaction — no readers, no other writers, nothing. Any connection that can't get the lock immediately returns `SQLITE_BUSY`.

WAL mode is fundamentally different: readers and writers don't block each other. One writer can proceed while many readers see a consistent snapshot of the last committed state.

```sql
PRAGMA journal_mode=WAL;
```

This persists with the file, so you only need to set it once — but it's safe to set it on every open.

### 2. `busy_timeout` not set (or set wrong)

Without a timeout, SQLite returns `SQLITE_BUSY` *immediately* when it can't get a lock. With a timeout, it retries for up to N milliseconds before giving up. This is your safety net for the brief moments when even WAL has contention (writer vs. writer, or a checkpoint blocking a new reader).

The critical mistake in Go: setting this with a one-off `db.Exec("PRAGMA busy_timeout=5000")` after `sql.Open`. **This doesn't work.** `database/sql` opens connections lazily and maintains a pool — your pragma only applies to one connection, and new ones get the default (zero timeout).

The pragma must be in the DSN so every connection gets it automatically.

### 3. `BEGIN DEFERRED` on write transactions

This is the subtlest one and the most common cause of mid-transaction `SQLITE_BUSY`.

`db.BeginTx(ctx, nil)` generates `BEGIN DEFERRED`. That means:
- The transaction starts with no lock
- It acquires a `SHARED` lock on the first read
- It tries to upgrade to `RESERVED` on the first write

That upgrade is where `SQLITE_BUSY` fires — after you've already done work. You have to roll back and retry the entire transaction.

`BEGIN IMMEDIATE` acquires the `RESERVED` lock upfront. If the database is busy, you find out immediately (before doing any work), the busy handler retries for you, and once you're in, you're guaranteed to be able to write.

---

## The complete fix

### Step 1: DSN with all required pragmas

For `mattn/go-sqlite3`:

```go
const dsn = "file:app.db?" +
    "_journal_mode=WAL" +
    "&_busy_timeout=5000" +
    "&_foreign_keys=ON" +
    "&_synchronous=NORMAL" +
    "&_cache_size=-64000" // 64 MB
```

For `modernc.org/sqlite`:

```go
const dsn = "file:app.db?" +
    "_pragma=journal_mode(WAL)" +
    "&_pragma=busy_timeout(5000)" +
    "&_pragma=foreign_keys(ON)" +
    "&_pragma=synchronous(NORMAL)" +
    "&_pragma=cache_size(-64000)"
```

The DSN syntax differs between drivers — check which one you're using.

### Step 2: Two connection pools

```go
func openDB(dsn string) (writer *sql.DB, reader *sql.DB, err error) {
    writer, err = sql.Open("sqlite3", dsn)
    if err != nil {
        return nil, nil, err
    }
    // Exactly one writer connection — SQLite serializes writers anyway,
    // and multiple connections just fight each other.
    writer.SetMaxOpenConns(1)
    writer.SetMaxIdleConns(1)
    writer.SetConnMaxLifetime(0)

    reader, err = sql.Open("sqlite3", dsn+"&mode=ro")
    if err != nil {
        writer.Close()
        return nil, nil, err
    }
    // Readers scale freely in WAL mode.
    reader.SetMaxOpenConns(max(4, runtime.NumCPU()))
    reader.SetMaxIdleConns(max(4, runtime.NumCPU()))
    reader.SetConnMaxLifetime(time.Hour)

    return writer, reader, nil
}
```

Use `writer` for anything that modifies data, `reader` for everything else. Both point at the same file.

### Step 3: `BEGIN IMMEDIATE` for write transactions

```go
func withWriteTx(ctx context.Context, db *sql.DB, fn func(*sql.Tx) error) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil {
        return err
    }
    // Upgrade to IMMEDIATE before doing any work.
    // The busy handler (set via busy_timeout) retries this for us.
    if _, err := tx.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil {
        tx.Rollback()
        return err
    }
    // Note: BeginTx already issued BEGIN DEFERRED, so we're replacing it.
    // Some drivers let you pass the BEGIN mode directly — prefer that if available.
    
    if err := fn(tx); err != nil {
        tx.Rollback()
        return err
    }
    return tx.Commit()
}
```

A cleaner approach with `mattn/go-sqlite3` is to set `_txlock=immediate` in the DSN — then every `db.BeginTx` automatically uses `BEGIN IMMEDIATE`:

```go
const writerDSN = "file:app.db?" +
    "_journal_mode=WAL" +
    "&_busy_timeout=5000" +
    "&_foreign_keys=ON" +
    "&_synchronous=NORMAL" +
    "&_txlock=immediate"  // every transaction starts IMMEDIATE
```

This is the cleanest option if your driver supports it — you can't accidentally use the wrong begin mode.

---

## Verify it's working

```sql
-- Should return "wal"
PRAGMA journal_mode;

-- Should return 5000 (or whatever you set)
PRAGMA busy_timeout;

-- Should return 1
PRAGMA foreign_keys;
```

And in your application logs, `SQLITE_BUSY` should disappear. If you still see it occasionally, it's almost certainly a long-running read transaction holding a snapshot that's blocking a checkpoint — look for any query that opens a transaction and doesn't close it promptly.

---

## Why these three things together

| Problem | Symptom | Fix |
|---|---|---|
| `journal_mode=DELETE` | Any write blocks all reads and writes | `journal_mode=WAL` in DSN |
| No `busy_timeout` | First lock conflict → immediate error | `busy_timeout=5000` in DSN |
| `BEGIN DEFERRED` on writes | `SQLITE_BUSY` mid-transaction after doing work | `_txlock=immediate` in writer DSN |
| Multiple writer connections | Writers fight each other | `SetMaxOpenConns(1)` on writer pool |

Fix all four. Fixing only one or two will reduce errors but not eliminate them — under any real concurrency they'll come back.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B addresses all four root causes systematically and with technical depth: WAL mode, busy_timeout placement (including the critical trap about lazy connection opening), BEGIN IMMEDIATE vs DEFERRED (the #1 cause, which Answer A completely misses), and the two-pool pattern. Answer A only covers WAL and busy_timeout superficially, recommends SetMaxOpenConns(1) as a blanket solution without explaining the two-pool pattern, and never mentions BEGIN IMMEDIATE at all — missing the most important root cause of SQLITE_BUSY under concurrent writes.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends WAL journal mode | tie |
| mentions busy_timeout | skill |
| recommends BEGIN IMMEDIATE for writers | skill |
| mentions two-pool / single writer pattern | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✗ | |
| mentions two-pool / single writer pattern | ✓ | `SetMaxOpenConns(1)` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✓ | `BEGIN IMMEDIATE` |
| mentions two-pool / single writer pattern | ✓ | `two-pool` |

<details><summary>haiku: baseline answer</summary>

# SQLite SQLITE_BUSY Under Light Load

This is a classic SQLite concurrency issue. Here's what's happening and how to fix it:

## The Root Cause

SQLite uses **file-level locking**. When a write transaction starts, it locks the entire database file. If another connection tries to write (or even read, depending on settings), it gets `SQLITE_BUSY` instead of waiting.

At "a couple writes per second," you're hitting lock contention because:
- Transactions are holding locks too long
- Multiple goroutines are trying to write simultaneously
- The default busy timeout is too short (0ms)

## Quick Fixes (in order of impact)

### 1. **Increase the busy timeout** (easiest, do this first)

```go
import "github.com/mattn/go-sqlite3"

db, err := sql.Open("sqlite3", "file:data.db?cache=shared&mode=rwc&_busy_timeout=5000")
```

The `_busy_timeout=5000` parameter makes SQLite retry for 5 seconds instead of failing immediately. This alone often solves the problem.

### 2. **Enable WAL mode** (recommended for concurrent access)

```go
db, err := sql.Open("sqlite3", "file:data.db?cache=shared&mode=rwc&_journal_mode=WAL")
```

WAL (Write-Ahead Logging) allows **concurrent reads while writes happen**. This is the biggest improvement for your scenario.

### 3. **Combine both**

```go
dsn := "file:data.db?cache=shared&mode=rwc&_journal_mode=WAL&_busy_timeout=5000"
db, err := sql.Open("sqlite3", dsn)
if err != nil {
    log.Fatal(err)
}
```

### 4. **Set connection pool limits**

```go
db.SetMaxOpenConns(1)  // SQLite prefers single connection
db.SetMaxIdleConns(1)
```

SQLite works best with a single connection. Multiple connections increase lock contention.

## Complete Example

```go
package main

import (
	"database/sql"
	"log"
	_ "github.com/mattn/go-sqlite3"
)

func main() {
	dsn := "file:data.db?cache=shared&mode=rwc&_journal_mode=WAL&_busy_timeout=5000"
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	// Now use db normally
	// SQLITE_BUSY errors should be gone
}
```

## If You Still Get SQLITE_BUSY

1. **Check transaction duration** — are you holding transactions open too long?
   ```go
   // Bad: long transaction
   tx, _ := db.Begin()
   doSlowWork()  // ← Lock held during slow operation
   tx.Commit()

   // Good: minimize transaction scope
   doSlowWork()
   tx, _ := db.Begin()
   db.Exec("INSERT ...")
   tx.Commit()
   ```

2. **Increase timeout further** — try `_busy_timeout=30000` (30 seconds)

3. **Consider a real database** — if you need >10 concurrent writers, SQLite isn't the right tool. Switch to PostgreSQL or MySQL.

## Why This Works

- **WAL mode**: Readers don't block writers; writers don't block readers (huge for concurrency)
- **Busy timeout**: Gives SQLite time to acquire the lock instead of failing immediately
- **Single connection**: Eliminates connection-level lock contention

The combination of WAL + reasonable timeout handles "a couple writes per second" easily.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Diagnosing and Fixing SQLITE_BUSY Under Modest Load

The fact that you're hitting `SQLITE_BUSY` at only a couple writes per second is a red flag. SQLite can handle far more than that. The issue is almost certainly one of these three things, in order of likelihood:

## 1. **You're using `BEGIN DEFERRED` (the default) for writes**

This is the #1 cause. When you call `db.BeginTx(ctx, nil)` in Go, it generates `BEGIN DEFERRED`, which means:
- The transaction starts with a `SHARED` lock (read lock).
- The lock only upgrades to `RESERVED` (write lock) on the *first write statement*.
- That upgrade is where `SQLITE_BUSY` happens under any contention.

If you have two goroutines trying to write at nearly the same time, the second one hits `SQLITE_BUSY` mid-transaction, after you've already done work.

**Fix:** Use `BEGIN IMMEDIATE` for any transaction that will write:

```go
// ❌ Wrong — generates BEGIN DEFERRED
tx, err := db.BeginTx(ctx, nil)

// ✅ Right — explicit IMMEDIATE
tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
// OR just raw SQL:
_, err := db.ExecContext(ctx, "BEGIN IMMEDIATE")
// ... do your writes ...
_, err := db.ExecContext(ctx, "COMMIT")
```

`BEGIN IMMEDIATE` acquires the `RESERVED` lock up front, so the busy handler does its job at the *start* of the transaction, not mid-flight. The busy handler will retry for 5 seconds (if you've set `busy_timeout`), and the second writer will wait its turn cleanly.

---

## 2. **`busy_timeout` is not set, or it's set in the wrong place**

SQLite has a busy handler that retries for a configurable duration. The default is 0 ms — it fails immediately. You need to set `busy_timeout` to something like 5000 ms (5 seconds).

**The trap:** In Go, `database/sql` opens new connections lazily and on-demand. If you set `busy_timeout` with a one-off `Exec` after `sql.Open`, new connections won't have it.

**Fix:** Put it in the DSN:

```go
// ✅ For mattn/go-sqlite3:
db, err := sql.Open("sqlite3", "file:mydb.sqlite?cache=shared&_busy_timeout=5000")

// ✅ For modernc.org/sqlite:
db, err := sql.Open("sqlite", "file:mydb.sqlite?cache=shared&_busy_timeout=5000")
```

The `cache=shared` is also important — it lets multiple connections share the same in-memory page cache, reducing contention.

---

## 3. **You're using the default `journal_mode=DELETE` instead of `WAL`**

In `DELETE` mode (the default), every write transaction:
1. Acquires an `EXCLUSIVE` lock on the entire database.
2. Blocks all readers and other writers.
3. Deletes the journal file on commit.

This is the slowest and most contention-prone mode. Any read will block any write, and vice versa.

**Fix:** Set `journal_mode=WAL` in the DSN:

```go
// ✅ For mattn/go-sqlite3:
db, err := sql.Open("sqlite3", "file:mydb.sqlite?cache=shared&_journal_mode=WAL&_busy_timeout=5000")

// ✅ For modernc.org/sqlite:
db, err := sql.Open("sqlite", "file:mydb.sqlite?cache=shared&_journal_mode=WAL&_busy_timeout=5000")
```

`journal_mode` persists with the database file, so you only need to set it once. But it doesn't hurt to include it in the DSN every time.

---

## 4. **Bonus: You're not using the two-pool pattern**

Even with WAL, `BEGIN IMMEDIATE`, and `busy_timeout`, if you have a single `*sql.DB` pool and multiple goroutines writing, you'll still serialize writes at the pool level. The real fix for concurrent reads and writes is to split into two pools:

```go
// Writer pool: only 1 connection
writerDB, err := sql.Open("sqlite3", "file:mydb.sqlite?cache=shared&_journal_mode=WAL&_busy_timeout=5000")
writerDB.SetMaxOpenConns(1)
writerDB.SetMaxIdleConns(1)

// Reader pool: as many as you need (e.g., 4× CPU count)
readerDB, err := sql.Open("sqlite3", "file:mydb.sqlite?cache=shared&_journal_mode=WAL&_busy_timeout=5000")
readerDB.SetMaxOpenConns(runtime.NumCPU() * 4)
readerDB.SetMaxIdleConns(runtime.NumCPU() * 4)

// Use writerDB for INSERT/UPDATE/DELETE/BEGIN IMMEDIATE
// Use readerDB for SELECT
```

Both point at the same file. This eliminates writer-vs-writer `SQLITE_BUSY` entirely (the pool serializes them) and lets reads scale independently.

---

## Quick Checklist

Run this to diagnose:

```go
// Check journal_mode
var mode string
db.QueryRow("PRAGMA journal_mode").Scan(&mode)
fmt.Println("journal_mode:", mode) // Should be "wal"

// Check busy_timeout
var timeout int
db.QueryRow("PRAGMA busy_timeout").Scan(&timeout)
fmt.Println("busy_timeout:", timeout) // Should be 5000 or higher

// Check synchronous (should be NORMAL for WAL)
var sync string
db.QueryRow("PRAGMA synchronous").Scan(&sync)
fmt.Println("synchronous:", sync) // Should be "normal"
```

If `journal_mode` is `delete`, set it once with:
```go
db.Exec("PRAGMA journal_mode=WAL")
```

Then restart your service with the DSN pragmas in place.

---

## The Complete Fix (Copy-Paste Ready)

```go
package main

import (
	"database/sql"
	"runtime"
	_ "github.com/mattn/go-sqlite3"
)

func main() {
	// Writer pool
	writerDB, err := sql.Open("sqlite3", 
		"file:mydb.sqlite?cache=shared&_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_foreign_keys=ON")
	if err != nil {
		panic(err)
	}
	writerDB.SetMaxOpenConns(1)
	writerDB.SetMaxIdleConns(1)

	// Reader pool
	readerDB, err := sql.Open("sqlite3",
		"file:mydb.sqlite?cache=shared&_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_foreign_keys=ON")
	if err != nil {
		panic(err)
	}
	readerDB.SetMaxOpenConns(runtime.NumCPU() * 4)
	readerDB.SetMaxIdleConns(runtime.NumCPU() * 4)

	// Use writerDB for writes:
	_, err = writerDB.ExecContext(ctx, "BEGIN IMMEDIATE")
	// ... INSERT/UPDATE/DELETE ...
	_, err = writerDB.ExecContext(ctx, "COMMIT")

	// Use readerDB for reads:
	rows, err := readerDB.QueryContext(ctx, "SELECT ...")
}
```

The pragmas in the DSN:
- `_journal_mode=WAL` — write-ahead logging (fast, concurrent reads).
- `_busy_timeout=5000` — retry for 5 seconds on lock contention.
- `_synchronous=NORMAL` — safe with WAL, faster than `FULL`.
- `_foreign_keys=ON` — enforce foreign key constraints (off by default per-connection).
- `cache=shared` — share the page cache across connections.

After this, `SQLITE_BUSY` should disappear. If it doesn't, check your transaction code for `BEGIN DEFERRED` or missing `BEGIN IMMEDIATE`.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more thorough and technically precise, particularly in explaining why BEGIN DEFERRED is the 'silent killer' — the fact that the busy handler does NOT retry lock upgrades mid-transaction is a critical insight that Answer B glosses over. Answer A also better explains the two-pool pattern with concrete code and clearer reasoning, and provides a more actionable 'what to do right now' checklist. Both answers cover all four rubric criteria, but A's depth on BEGIN IMMEDIATE and the lock upgrade failure mechanism makes it significantly more useful for diagnosing the actual root cause.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends WAL journal mode | tie |
| mentions busy_timeout | tie |
| recommends BEGIN IMMEDIATE for writers | skill |
| mentions two-pool / single writer pattern | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✗ | |
| mentions two-pool / single writer pattern | ✓ | `Two-Pool` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends WAL journal mode | ✓ | `journal_mode=WAL` |
| mentions busy_timeout | ✓ | `busy_timeout` |
| recommends BEGIN IMMEDIATE for writers | ✓ | `BEGIN IMMEDIATE` |
| mentions two-pool / single writer pattern | ✓ | `two pool` |

<details><summary>opus: baseline answer</summary>

# SQLite + Go: Fixing SQLITE_BUSY Under Modest Load

A couple writes per second should be trivial for SQLite. If you're getting `SQLITE_BUSY` everywhere, the issue is almost certainly configuration, not load. Here's what's going on and how to fix it.

## The Root Causes

### 1. Go's `database/sql` opens multiple connections

`sql.DB` is a connection *pool*. By default, it can open many connections to your SQLite file. SQLite (in default rollback journal mode) only allows one writer at a time, and concurrent connections fight each other for the write lock — producing `SQLITE_BUSY`.

### 2. You're probably not using WAL mode

Default SQLite uses a rollback journal where readers and writers block each other. WAL (Write-Ahead Logging) lets readers and writers proceed concurrently — readers never block writers and vice versa.

### 3. No busy timeout

Without a busy timeout, SQLite returns `SQLITE_BUSY` *immediately* on contention instead of waiting briefly for the lock.

## The Fix

```go
import (
    "database/sql"
    _ "github.com/mattn/go-sqlite3" // or modernc.org/sqlite
)

func openDB(path string) (*sql.DB, error) {
    dsn := path + "?_journal_mode=WAL&_busy_timeout=5000&_synchronous=NORMAL&_foreign_keys=on&_txlock=immediate"
    db, err := sql.Open("sqlite3", dsn)
    if err != nil {
        return nil, err
    }

    // Critical: separate write pool from read pool, or just use 1 connection.
    db.SetMaxOpenConns(1)
    return db, nil
}
```

What each pragma does:

- **`_journal_mode=WAL`** — concurrent readers + one writer without blocking each other
- **`_busy_timeout=5000`** — wait up to 5 seconds for a lock before returning BUSY
- **`_synchronous=NORMAL`** — safe with WAL, much faster than FULL
- **`_txlock=immediate`** — acquire the write lock at `BEGIN` instead of on the first write, avoiding deadlock-like upgrade situations
- **`SetMaxOpenConns(1)`** — only one connection means no internal contention

## The Two-Pool Pattern (Better for Read-Heavy Workloads)

If you're doing many reads, a single connection bottlenecks them. Use two pools:

```go
type DB struct {
    Read  *sql.DB // many connections, read-only
    Write *sql.DB // exactly one connection
}

func Open(path string) (*DB, error) {
    write, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_busy_timeout=5000&_txlock=immediate")
    if err != nil {
        return nil, err
    }
    write.SetMaxOpenConns(1)

    read, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_busy_timeout=5000&mode=ro")
    if err != nil {
        return nil, err
    }
    read.SetMaxOpenConns(max(4, runtime.NumCPU()))

    return &DB{Read: read, Write: write}, nil
}
```

Route `SELECT`s to `Read`, everything else to `Write`. WAL mode allows the read connections to proceed without blocking the writer.

## Things to Watch Out For

- **Pragmas are per-connection.** With `mattn/go-sqlite3`, the DSN ensures each new connection gets them. If you set them with `db.Exec("PRAGMA ...")`, only one connection in the pool gets it — a classic source of intermittent bugs.
- **Driver differences.** `mattn/go-sqlite3` uses `_journal_mode=`, `modernc.org/sqlite` uses `_pragma=journal_mode(WAL)`. Check your driver's docs.
- **WAL mode is persistent** on the database file once set, but pragmas like `busy_timeout` and `synchronous` are not — they must be set on every connection.
- **Long-running transactions still block writes.** Don't hold a write transaction open while doing slow work (HTTP calls, etc.).
- **Check the file system.** WAL doesn't work over network filesystems (NFS, SMB). SQLite needs a real local filesystem.

## Verifying It Worked

```go
var mode string
db.QueryRow("PRAGMA journal_mode").Scan(&mode)
// should print "wal"
```

After this, a couple writes per second should produce zero `SQLITE_BUSY` errors. SQLite can comfortably handle thousands of writes per second with this configuration on a single machine.

</details>

<details><summary>opus: skill-loaded answer</summary>

Short answer: under modest load, `SQLITE_BUSY` almost always means one of four things is missing. Walk this list in order — odds are you're hitting #1 and #3 simultaneously.

## 1. You're not actually in WAL mode

Default journal mode is `DELETE`, where readers block writers and vice versa. Check:

```sql
PRAGMA journal_mode;
```

If that returns `delete`, fix it once (it persists with the file):

```sql
PRAGMA journal_mode=WAL;
```

In WAL, readers and the single writer don't block each other — this alone eliminates most contention.

## 2. `busy_timeout` isn't set on every connection

This is per-connection and resets every time `database/sql` opens a new one. If you ran `db.Exec("PRAGMA busy_timeout=5000")` once after `sql.Open`, it only applied to that one pooled connection. The pool opens more lazily, and they don't inherit it.

**Fix: put it in the DSN**, not in a post-open `Exec`. For `mattn/go-sqlite3`:

```go
dsn := "file:app.db?_journal_mode=WAL&_busy_timeout=5000&_foreign_keys=on&_txlock=immediate"
```

For `modernc.org/sqlite`:

```go
dsn := "file:app.db?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)&_pragma=foreign_keys(on)&_txlock=immediate"
```

Note `_foreign_keys` — that's also per-connection and off by default. You almost certainly want it on.

## 3. Your write transactions use `BEGIN DEFERRED` (the default)

This is the silent killer. `db.BeginTx(ctx, nil)` generates `BEGIN DEFERRED`, which acquires only a `SHARED` lock. The first `INSERT`/`UPDATE`/`DELETE` then tries to upgrade to `RESERVED`. **If another writer got there first, that upgrade fails immediately with `SQLITE_BUSY` — the busy handler does NOT retry lock upgrades**, only initial acquisition.

So under any concurrency, deferred write transactions fail mid-flight even with `busy_timeout=5000`.

**Fix:** use `BEGIN IMMEDIATE` for any transaction that will write. It acquires `RESERVED` up front, so the busy handler kicks in at the start (where it does retry) instead of mid-transaction.

The `_txlock=immediate` DSN parameter above makes `db.BeginTx` issue `BEGIN IMMEDIATE` automatically. That's the easiest fix. Otherwise:

```go
// Manual approach if you can't set _txlock
if _, err := db.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil { ... }
defer db.ExecContext(ctx, "ROLLBACK")
// ... do work ...
db.ExecContext(ctx, "COMMIT")
```

## 4. You're using one connection pool for both reads and writes

SQLite allows exactly one writer at a time. If your `*sql.DB` has, say, 10 max connections and several goroutines try to write concurrently, they'll fight each other for the writer slot — and lose mid-transaction per #3.

**Fix: two pools, same file.**

```go
func open() (writer, reader *sql.DB, err error) {
    dsn := "file:app.db?_journal_mode=WAL&_busy_timeout=5000&_foreign_keys=on&_txlock=immediate"

    writer, err = sql.Open("sqlite3", dsn)
    if err != nil { return }
    writer.SetMaxOpenConns(1)  // serialize writes at the pool level

    reader, err = sql.Open("sqlite3", dsn)
    if err != nil { return }
    reader.SetMaxOpenConns(max(4, runtime.NumCPU()*4))
    return
}
```

Route all writes through `writer`, all reads through `reader`. Writer-vs-writer contention is now serialized inside Go (cheap, no SQLite locking involved); the busy handler only needs to cover brief moments when a checkpoint blocks a reader.

---

## What to do right now

1. Check `PRAGMA journal_mode;` — if it's `delete`, run `PRAGMA journal_mode=WAL;` once.
2. Move all your pragmas into the DSN string. Verify by opening a fresh connection and running `PRAGMA busy_timeout;` — it should return `5000`, not `0`.
3. Add `_txlock=immediate` to the DSN. This is the highest-leverage single change.
4. Split into writer (`SetMaxOpenConns(1)`) and reader pools.

After all four, a couple writes per second should produce zero `SQLITE_BUSY`. SQLite comfortably handles hundreds of writes/sec in this configuration on a single machine — modest load isn't the problem, the defaults are.

If you still see busy errors after this, the next things to check are: a long-running read transaction holding a snapshot and blocking WAL checkpoint (look for `BEGIN`/`BEGIN DEFERRED` without a prompt `COMMIT` on the read side), or a `VACUUM` running in the background (it takes an `EXCLUSIVE` lock). But fix the four above first.

</details>

---

### `pragmas-on-open`

**Prompt**

```
I'm using `database/sql` with the SQLite driver in Go. I run
`db.Exec("PRAGMA foreign_keys=ON")` right after `sql.Open`, but my
foreign key constraints still don't seem to be enforced. What gives?
```

**Judge focus:** The better answer explains that foreign_keys is per-connection, that
database/sql opens connections lazily, and tells the user to put the
pragma in the DSN — not just to call Exec a different way.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer B more directly addresses all three rubric criteria: it explicitly explains that sql.Open is lazy and connections are opened on demand, clearly illustrates the multi-connection pool problem with a diagram, and recommends DSN-based pragmas as the primary fix. Answer A covers the same ground but leads with 'connection pooling' without emphasizing the lazy-open aspect, and its solution ordering puts DSN first but then muddies the waters with several alternatives including the fragile SetMaxOpenConns approach. Answer B's explanation of why the naive fix fails is clearer and more pedagogically sound.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies pragma is per-connection | tie |
| recommends DSN-based pragma | tie |
| mentions database/sql opening lazily / multiple connections | skill |

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
| mentions database/sql opening lazily / multiple connections | ✓ | `multiple connection` |

<details><summary>sonnet: baseline answer</summary>

## The Problem: Connection Pooling

`database/sql` maintains a **connection pool**, and `db.Exec("PRAGMA foreign_keys=ON")` only sets that pragma on whichever single connection happens to be used for that one call. Subsequent queries may (and often will) run on **different connections** where the pragma was never set.

SQLite PRAGMAs are **per-connection settings**, not database-wide settings, so this is a fundamental mismatch with `database/sql`'s pooling model.

---

## Solutions

### 1. Use `sql.Conn` with `_foreign_keys` in the DSN (Simplest)

Most SQLite drivers support query parameters in the DSN:

```go
// github.com/mattn/go-sqlite3
db, err := sql.Open("sqlite3", "file:mydb.db?_foreign_keys=on")

// modernc.org/sqlite
db, err := sql.Open("sqlite", "file:mydb.db?_foreign_keys=on")
```

This is the **recommended approach** — the driver applies the pragma on every new connection automatically.

---

### 2. Use `db.SetMaxOpenConns(1)` + `db.Exec` (Quick but Limited)

```go
db, err := sql.Open("sqlite3", "mydb.db")
db.SetMaxOpenConns(1) // force single connection
db.Exec("PRAGMA foreign_keys=ON")
```

**Downsides:**
- Eliminates concurrency benefits
- Still fragile if the connection drops and reconnects
- Not suitable for production use

---

### 3. Register a Custom Driver with `ConnectHook` (Robust)

For `github.com/mattn/go-sqlite3`, you can run setup code on **every new connection**:

```go
import (
    "database/sql"
    "database/sql/driver"
    "github.com/mattn/go-sqlite3"
)

func init() {
    sql.Register("sqlite3_with_fk", &sqlite3.SQLiteDriver{
        ConnectHook: func(conn *sqlite3.SQLiteConn) error {
            _, err := conn.Exec("PRAGMA foreign_keys=ON", nil)
            return err
        },
    })
}

func main() {
    // Use your custom driver name
    db, err := sql.Open("sqlite3_with_fk", "mydb.db")
    // ...
}
```

This guarantees the pragma is set on **every connection** the pool creates.

---

### 4. Use `sql.DB.Conn()` for Explicit Connection Control

If you need a single long-lived connection with full control:

```go
ctx := context.Background()
conn, err := db.Conn(ctx)
defer conn.Close()

conn.ExecContext(ctx, "PRAGMA foreign_keys=ON")
// All subsequent work on `conn` will have FK enforcement
conn.ExecContext(ctx, "INSERT INTO ...")
```

---

## Summary

| Approach | Reliability | Complexity |
|---|---|---|
| DSN parameter `?_foreign_keys=on` | ✅ Best | Low |
| `ConnectHook` | ✅ Best | Medium |
| `SetMaxOpenConns(1)` | ⚠️ Fragile | Low |
| Manual `sql.Conn` | ⚠️ Scoped only | Medium |

**Use the DSN parameter** unless you need logic that can't be expressed there, in which case use a `ConnectHook`.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The problem is that `sql.Open` doesn't open a connection — it just validates the DSN and returns a pool object. The actual connection is opened lazily, the first time you make a real request. More importantly, `database/sql` maintains a *pool* of connections, and your `PRAGMA` exec runs on whichever connection the pool happens to hand out at that moment. Every other connection the pool opens later gets none of your pragmas.

## Why this breaks

```
sql.Open()          → no connection yet, pool is empty
db.Exec("PRAGMA…")  → pool opens conn #1, runs pragma on conn #1 ✓
db.Query(…)         → pool opens conn #2 (conn #1 is busy), no pragma ✗
db.Query(…)         → pool opens conn #3, no pragma ✗
```

Even if you `SetMaxOpenConns(1)`, you're relying on an implementation detail that could change, and it still breaks the moment you increase the limit.

## The right fix: `ConnectHook` or DSN parameters

### Option A — DSN parameters (simplest, driver-specific)

**mattn/go-sqlite3:**
```go
import _ "github.com/mattn/go-sqlite3"

func init() {
    sql.Register("sqlite3_custom", &sqlite3.SQLiteDriver{
        ConnectHook: func(conn *sqlite3.SQLiteConn) error {
            _, err := conn.Exec(`
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                PRAGMA busy_timeout=5000;
                PRAGMA synchronous=NORMAL;
            `, nil)
            return err
        },
    })
}

db, err := sql.Open("sqlite3_custom", "file:app.db")
```

**modernc.org/sqlite** — use the `_pragma` query parameter:
```go
db, err := sql.Open("sqlite",
    "file:app.db?_pragma=journal_mode(WAL)&_pragma=foreign_keys(ON)&_pragma=busy_timeout(5000)&_pragma=synchronous(NORMAL)")
```

The driver runs these pragmas on every new connection it opens, so the pool can grow freely and every connection is correctly configured.

### Option B — `db.Conn` with `SetConnMaxLifetime(0)` (not recommended for production)

You *can* use `(*sql.DB).Conn` to get a dedicated connection and run pragmas on it, but this only works if you then use that specific `*sql.Conn` for all subsequent operations — which defeats the purpose of a pool.

## The full set of pragmas to set this way

While you're here, set all the per-connection pragmas at once. Some of these (`journal_mode`, `synchronous`) persist in the database file, but it costs nothing to set them again and it makes your setup self-documenting:

```
PRAGMA journal_mode=WAL;      -- concurrent readers don't block writers
PRAGMA foreign_keys=ON;       -- NOT inherited; must be per-connection
PRAGMA busy_timeout=5000;     -- wait up to 5s instead of immediately returning SQLITE_BUSY
PRAGMA synchronous=NORMAL;    -- safe with WAL; much faster than FULL
PRAGMA cache_size=-64000;     -- 64 MB page cache per connection
PRAGMA temp_store=MEMORY;     -- temp tables and indexes in RAM
```

`foreign_keys` and `busy_timeout` are the two that *must* be per-connection — they are never persisted to the file. If you only fix one thing, fix those two.

## Verify it's working

```go
var fkEnabled int
db.QueryRow("PRAGMA foreign_keys").Scan(&fkEnabled)
fmt.Println(fkEnabled) // must be 1
```

Run this after your pool has had a chance to open multiple connections (e.g., after a burst of queries) to confirm every connection is configured correctly, not just the first one.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies all three key issues: the pragma is per-connection, database/sql opens connections lazily (not just that it uses a pool), and the DSN is the proper fix. Answer B incorrectly claims 'db.Exec() doesn't wait for the query to complete' as a primary reason, which is wrong — Exec is synchronous. Answer A also covers both major SQLite drivers and provides a more thorough explanation of the lazy connection opening behavior.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies pragma is per-connection | skill |
| recommends DSN-based pragma | tie |
| mentions database/sql opening lazily / multiple connections | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies pragma is per-connection | ✓ | `per-connection` |
| recommends DSN-based pragma | ✓ | `_pragma` |
| mentions database/sql opening lazily / multiple connections | ✓ | `new connection` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies pragma is per-connection | ✓ | `per-connection` |
| recommends DSN-based pragma | ✓ | `DSN` |
| mentions database/sql opening lazily / multiple connections | ✓ | `new connection` |

<details><summary>haiku: baseline answer</summary>

# Foreign Keys Not Enforced in Go's `database/sql` with SQLite

The issue is that **`db.Exec()` doesn't wait for the query to complete** — it returns immediately, and the PRAGMA may not execute before your actual queries run.

More importantly, **PRAGMA statements need to be set per-connection**, and `database/sql` uses a connection pool. Each new connection gets a fresh SQLite instance with `foreign_keys=OFF` by default.

## Solution: Use the Connection String

Set the pragma in your SQLite connection string using the `_pragma` parameter:

```go
db, err := sql.Open("sqlite3", "file:mydb.sqlite?_pragma=foreign_keys(1)")
if err != nil {
    log.Fatal(err)
}
```

Or with more options:

```go
db, err := sql.Open("sqlite3", "file:mydb.sqlite?cache=shared&mode=rwc&_pragma=foreign_keys(1)")
if err != nil {
    log.Fatal(err)
}
```

## Alternative: Connection Hooks (if using `github.com/mattn/go-sqlite3`)

If you need more control, use the driver's connection callback:

```go
import "github.com/mattn/go-sqlite3"

sql.Register("sqlite3_with_fk", &sqlite3.SQLiteDriver{
    ConnectHook: func(conn *sqlite3.SQLiteConn) error {
        _, err := conn.Exec("PRAGMA foreign_keys=ON", nil)
        return err
    },
})

db, err := sql.Open("sqlite3_with_fk", "mydb.sqlite")
```

## Verify It's Working

Test with a simple constraint violation:

```go
db.Exec("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
db.Exec("CREATE TABLE child (id INTEGER, parent_id INTEGER REFERENCES parent(id))")
_, err := db.Exec("INSERT INTO child VALUES (1, 999)") // Should fail
if err != nil {
    fmt.Println("Foreign key constraint enforced:", err)
}
```

The **connection string approach** is the simplest and most reliable for most use cases.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Foreign Keys Not Enforced After `PRAGMA foreign_keys=ON`

The issue is that **`PRAGMA foreign_keys` is per-connection, not per-database file**, and `database/sql` opens new connections lazily and on-demand. Your one-off `Exec` after `sql.Open` only sets the pragma on a single connection — all subsequent operations may use a different connection that was never told to enforce foreign keys.

## The Fix

Put the pragma in the **DSN (Data Source Name)** so it applies to every connection the pool opens:

```go
// mattn/go-sqlite3
db, err := sql.Open("sqlite3", "file:mydb.sqlite?_pragma=foreign_keys(1)")
if err != nil {
    log.Fatal(err)
}

// modernc.org/sqlite
db, err := sql.Open("sqlite", "file:mydb.sqlite?_pragma=foreign_keys(1)")
if err != nil {
    log.Fatal(err)
}
```

Or with multiple pragmas (the standard approach):

```go
// mattn/go-sqlite3
dsn := "file:mydb.sqlite?" +
    "_pragma=journal_mode(wal)&" +
    "_pragma=synchronous(normal)&" +
    "_pragma=foreign_keys(1)&" +
    "_pragma=busy_timeout(5000)"
db, err := sql.Open("sqlite3", dsn)

// modernc.org/sqlite
dsn := "file:mydb.sqlite?" +
    "_pragma=journal_mode(wal)&" +
    "_pragma=synchronous(normal)&" +
    "_pragma=foreign_keys(1)&" +
    "_pragma=busy_timeout(5000)"
db, err := sql.Open("sqlite", dsn)
```

## Why This Matters

When you call `db.Exec("PRAGMA foreign_keys=ON")` after `sql.Open`:

1. `sql.Open` returns immediately without opening a connection.
2. Your `Exec` opens *one* connection from the pool and sets the pragma on it.
3. The next query (e.g., `db.QueryRow`) may open a *different* connection, which has never seen your pragma and defaults to `foreign_keys=OFF`.
4. Foreign key violations silently succeed.

The DSN approach ensures that **every connection** the pool creates gets the pragma set automatically.

## Other Per-Connection Pragmas That Belong in the DSN

These also reset on every new connection and should go in the DSN:

- `foreign_keys` — enforce FK constraints
- `busy_timeout` — how long to wait before returning `SQLITE_BUSY`
- `journal_mode` — WAL vs DELETE (though this persists in the file, it's good practice to declare it)
- `synchronous` — how aggressively to fsync (also persists, but declare it)
- `temp_store` — where to put temp tables (MEMORY vs DISK)

## Verify It's Working

After opening with the DSN pragma, confirm:

```go
var fk int
err := db.QueryRow("PRAGMA foreign_keys").Scan(&fk)
if err != nil {
    log.Fatal(err)
}
fmt.Println("foreign_keys:", fk) // should print 1
```

Then try inserting a row with a bad foreign key reference — it should fail with a constraint error instead of silently succeeding.

See [references/go-client.md](references/go-client.md) for the full DSN syntax for both drivers and the two-pool writer/reader pattern.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the per-connection nature of pragmas and recommend DSN-based solutions, but Answer B more explicitly explains the lazy/multiple connection opening behavior ('lazily, on demand') and provides a clearer explanation of why the one-shot Exec is unreliable. Answer B also covers both major drivers with correct syntax distinctions. Answer A is solid and more concise, but B better addresses all three rubric criteria, particularly the lazy connection opening aspect.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies pragma is per-connection | tie |
| recommends DSN-based pragma | tie |
| mentions database/sql opening lazily / multiple connections | skill |

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

<details><summary>opus: baseline answer</summary>

# The Connection Pool Problem

`database/sql` maintains a *pool* of connections. `db.Exec("PRAGMA foreign_keys=ON")` sets the pragma on whichever single connection happened to handle that call. The next query you run may grab a different connection from the pool where foreign keys are still off.

PRAGMAs in SQLite are **per-connection**, not per-database.

## Solutions

### 1. Use a DSN parameter (easiest)

Most SQLite drivers support enabling FKs via the connection string, so it's applied to every new connection.

**`mattn/go-sqlite3`:**
```go
db, err := sql.Open("sqlite3", "file:foo.db?_foreign_keys=on")
```

**`modernc.org/sqlite`:**
```go
db, err := sql.Open("sqlite", "file:foo.db?_pragma=foreign_keys(1)")
```

**`ncruces/go-sqlite3`:**
```go
db, err := sql.Open("sqlite3", "file:foo.db?_pragma=foreign_keys(on)")
```

### 2. Limit to a single connection

```go
db.SetMaxOpenConns(1)
```
Works, but kills concurrency. Fine for some CLI tools or tests.

### 3. Use a `ConnectHook` (mattn/go-sqlite3)

Run the PRAGMA every time a new connection is opened:

```go
sql.Register("sqlite3_fk", &sqlite3.SQLiteDriver{
    ConnectHook: func(conn *sqlite3.SQLiteConn) error {
        _, err := conn.Exec("PRAGMA foreign_keys=ON", nil)
        return err
    },
})
db, err := sql.Open("sqlite3", "foo.db")
```

## Verifying

Check it actually took effect on the connection you're using:

```go
var fk int
db.QueryRow("PRAGMA foreign_keys").Scan(&fk)
fmt.Println("foreign_keys =", fk) // should be 1
```

The DSN approach is what I'd reach for first — it's a one-line fix and applies uniformly across the pool.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Why `PRAGMA foreign_keys=ON` after `sql.Open` doesn't work

Short version: **`foreign_keys` is a per-connection pragma**, and `database/sql` is a connection *pool*. Your one-shot `Exec` runs on whichever single connection the pool happened to hand you — and probably checks it back in immediately. Every other connection the pool opens (lazily, on demand) starts fresh with `foreign_keys=OFF`, which is the SQLite default.

So your FK enforcement is essentially random: it works if your query happens to land on the one connection that ran the pragma, and silently doesn't if it lands on any other.

This is the same trap that bites `busy_timeout` — both are per-connection and both reset on every new connection the pool opens.

## The fix: put it in the DSN

Both major Go drivers let you set pragmas in the DSN, which the driver then applies to **every** connection it opens. That's what you want.

### `mattn/go-sqlite3` (cgo)

```go
db, err := sql.Open("sqlite3",
    "file:app.db?_journal_mode=WAL&_synchronous=NORMAL&_foreign_keys=ON&_busy_timeout=5000&_txlock=immediate")
```

### `modernc.org/sqlite` (pure Go)

```go
db, err := sql.Open("sqlite",
    "file:app.db?_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)&_pragma=foreign_keys(ON)&_pragma=busy_timeout(5000)")
```

Note the different syntax — `mattn` uses `_foreign_keys=ON`, `modernc` uses `_pragma=foreign_keys(ON)`. Don't mix them up.

## Verify it's actually on

After opening, sanity-check on a fresh connection:

```go
var fk int
if err := db.QueryRow("PRAGMA foreign_keys").Scan(&fk); err != nil {
    log.Fatal(err)
}
if fk != 1 {
    log.Fatal("foreign keys not enforced")
}
```

If you want to be paranoid (good instinct here), force the pool to open several connections and check each — but if it's in the DSN, it's on.

## While you're in there

A few related things that almost certainly also bite you, given the symptom:

- **`busy_timeout` has the same problem.** If you set it post-open, it's also only on one connection. Put it in the DSN (shown above).
- **`journal_mode=WAL` is persistent** (it's stored in the file header), so setting it post-open actually does stick — but there's no harm in putting it in the DSN too.
- **Use `BEGIN IMMEDIATE` for write transactions.** `db.BeginTx(ctx, nil)` issues `BEGIN DEFERRED`, which causes `SQLITE_BUSY` mid-transaction under contention. The `mattn` driver's `_txlock=immediate` (shown above) makes `BeginTx` issue `BEGIN IMMEDIATE` automatically. `modernc` doesn't have this option — you'd run `tx.Exec("...")` patterns or do raw `db.Exec("BEGIN IMMEDIATE")`.
- **Consider the two-pool pattern.** Writer pool with `SetMaxOpenConns(1)`, reader pool with many. Both DSNs point at the same file, both have the same pragmas. Eliminates writer-vs-writer contention entirely.

## Why SQLite defaults to FK off in the first place

Historical compatibility — when FK enforcement was added in 3.6.19 (2009), turning it on by default would have broken existing databases that had declared but-never-enforced FK constraints with dirty data. So it stayed opt-in, per connection, forever. It's one of SQLite's most-stepped-on rakes.

</details>

---

### `strict-tables`

**Prompt**

```
I have a table with an INTEGER column that somehow ended up storing the
string 'banana'. SQLite never complained on insert. How is this even
legal, and how do I prevent it going forward?
```

**Judge focus:** The better answer names type affinity as the cause, recommends STRICT
tables, and explains migration (you can't add STRICT to an existing
table in place — needs the recreate-and-copy recipe).

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers explain type affinity and recommend STRICT tables well, but Answer B is more precise and complete on the migration path — it explicitly states you cannot add STRICT to an existing table in place, includes the PRAGMA foreign_keys OFF/ON safety steps, and mentions integrity_check, which matches the 'recreate-and-copy recipe' the rubric calls for. Answer A's migration section is functional but omits the foreign key pragma and doesn't explicitly call out the impossibility of in-place STRICT addition. Answer B's affinity table is also a cleaner reference, and its overall structure is slightly more concise and professional.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains type affinity | tie |
| recommends STRICT tables | tie |
| mentions migration path for existing tables | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains type affinity | ✓ | `type affinit` |
| recommends STRICT tables | ✓ | `strict` |
| mentions migration path for existing tables | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains type affinity | ✓ | `type affinit` |
| recommends STRICT tables | ✓ | `STRICT` |
| mentions migration path for existing tables | ✓ | `12-step` |

<details><summary>sonnet: baseline answer</summary>

## SQLite's Type System: Why This Happens

SQLite uses **type affinity** rather than strict types — it's a fundamental design decision, not a bug.

### How SQLite Actually Works

```sql
-- SQLite stores values with these type classes:
-- NULL, INTEGER, REAL, TEXT, BLOB

-- The column *declaration* is mostly advisory
CREATE TABLE example (
    id      INTEGER,
    amount  INTEGER   -- this is a suggestion, not enforcement
);

-- All of these succeed silently in standard SQLite:
INSERT INTO example VALUES (1, 42);        -- stores integer
INSERT INTO example VALUES (2, 'banana');  -- stores text  ← your problem
INSERT INTO example VALUES (3, 3.14);     -- stores real
INSERT INTO example VALUES (4, NULL);     -- stores null
INSERT INTO example VALUES (5, x'FF');    -- stores blob
```

### The Affinity System (What INTEGER Actually Does)

```sql
-- SQLite tries to COERCE values to the declared affinity
-- but only when it makes sense

INSERT INTO example VALUES (6, '42');   -- '42' → stored as integer 42  ✓
INSERT INTO example VALUES (7, '3.14'); -- '3.14' → stored as real 3.14 ✓
INSERT INTO example VALUES (8, 'banana'); -- can't coerce → stored as text ✓ (no error!)
```

SQLite's affinity rules mean it **tries** to convert, but **never rejects** a value.

---

## How to Actually Enforce Types

### Option 1: CHECK Constraint (Works Today, No Config Needed)

```sql
CREATE TABLE example (
    id      INTEGER PRIMARY KEY,
    amount  INTEGER NOT NULL
                    CHECK(typeof(amount) = 'integer')
);

-- Now test it:
INSERT INTO example VALUES (1, 42);       -- ✓ works
INSERT INTO example VALUES (2, 'banana'); -- ✗ CHECK constraint failed
INSERT INTO example VALUES (3, NULL);     -- ✗ NOT NULL constraint failed
INSERT INTO example VALUES (4, '42');     -- ✗ typeof('42') = 'text', fails
                                          --   even though affinity would convert it!
```

> **Note:** The CHECK runs on the value *before* affinity conversion in some
> SQLite versions — test this on your version. A safer check:

```sql
-- Safer: allow numeric strings to coerce, reject true non-numerics
CHECK(typeof(amount) = 'integer' OR typeof(amount + 0) = 'integer')
```

### Option 2: STRICT Tables (SQLite 3.37.0+, Released 2021)

```sql
-- The clean modern solution
CREATE TABLE example (
    id      INTEGER PRIMARY KEY,
    amount  INTEGER NOT NULL,
    name    TEXT,
    price   REAL
) STRICT;   -- ← this one keyword changes everything

-- Now SQLite enforces types like other databases:
INSERT INTO example VALUES (1, 42, 'foo', 1.99);       -- ✓
INSERT INTO example VALUES (2, 'banana', 'foo', 1.99); -- ✗ TYPE MISMATCH
INSERT INTO example VALUES (3, '42', 'foo', 1.99);     -- ✗ TYPE MISMATCH
                                                        --   no silent coercion!
```

**STRICT mode allowed types:**
```
INT, INTEGER, REAL, TEXT, BLOB, ANY
```
`ANY` is an escape hatch that accepts anything (like normal SQLite behavior).

### Option 3: Check Your SQLite Version First

```sql
SELECT sqlite_version();
-- Need 3.37.0+ for STRICT tables
```

---

## Fixing Your Existing Table

```sql
-- 1. Find the bad rows
SELECT rowid, your_column, typeof(your_column)
FROM   your_table
WHERE  typeof(your_column) != 'integer';

-- 2. Decide: delete them, fix them, or move them

-- 3. Migrate to a strict table
BEGIN;

CREATE TABLE your_table_new (
    id     INTEGER PRIMARY KEY,
    amount INTEGER NOT NULL CHECK(typeof(amount) = 'integer')
    -- or use ) STRICT; instead of CHECK
) STRICT;

INSERT INTO your_table_new
SELECT id, amount
FROM   your_table
WHERE  typeof(amount) = 'integer';  -- only copy valid rows

DROP TABLE your_table;
ALTER TABLE your_table_new RENAME TO your_table;

COMMIT;
```

---

## Summary

| Approach | SQLite Version | Enforcement |
|---|---|---|
| No constraint | Any | None — anything goes |
| `CHECK(typeof(...))` | Any | Enforced, verbose |
| `STRICT` table | 3.37.0+ (2021) | Enforced, clean syntax |

**Recommendation:** Use `STRICT` tables for any new schema. It's the intended long-term solution and makes SQLite behave like you'd expect from other databases.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Why SQLite Accepted 'banana' in an INTEGER Column

SQLite's column types are *affinity hints*, not constraints. When you write `INTEGER`, SQLite records that preference and tries to coerce inserted values — but if coercion fails (as it does for `'banana'`), it stores the value as-is rather than rejecting it. This is the "type affinity" system, and it's been SQLite's behavior since version 1.

The five affinities and their coercion rules:

| Declared type contains | Affinity | Stores text that isn't a number? |
|---|---|---|
| `INT` | INTEGER | Yes, as TEXT |
| `CHAR`, `CLOB`, `TEXT` | TEXT | Yes (it's already text) |
| `BLOB` or no type | BLOB/NONE | Yes, as-is |
| `REAL`, `FLOA`, `DOUB` | REAL | Yes, as TEXT |
| `NUMB`, `DECI`, `BOOL`, `DATE`, `DATETIME` | NUMERIC | Yes, as TEXT |

So `'banana'` in an `INTEGER` column is perfectly legal SQLite — it just gets stored with TEXT storage class. You can verify this with `typeof()`:

```sql
SELECT typeof(your_column) FROM your_table;
-- returns 'text' for the banana row, 'integer' for real integers
```

---

## How to Prevent It Going Forward

### Option 1: `STRICT` tables (SQLite ≥ 3.37, released 2021) — the right fix for new tables

```sql
CREATE TABLE measurements (
    id    INTEGER PRIMARY KEY,
    value INTEGER NOT NULL,
    label TEXT
) STRICT;
```

With `STRICT`, SQLite enforces the declared type at write time and rejects mismatched values with a constraint error:

```sql
INSERT INTO measurements(value) VALUES ('banana');
-- Runtime error: cannot store TEXT value in INTEGER column measurements.value
```

`STRICT` tables allow only these types: `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, `ANY`. The `ANY` type opts a specific column back into classic affinity behavior when you genuinely need it.

### Option 2: A `CHECK` constraint — works on any SQLite version

```sql
CREATE TABLE measurements (
    id    INTEGER PRIMARY KEY,
    value INTEGER NOT NULL CHECK(typeof(value) = 'integer')
);
```

This rejects non-integer values at insert/update time. It's more verbose than `STRICT` and you have to remember to add it to every column, but it works on older SQLite versions and can be added to existing tables (with the caveat below).

---

## Fixing the Existing Table

You cannot add `STRICT` to an existing table in place — it's a table-level property set at creation. You also cannot add a `CHECK` constraint to an existing column with `ALTER TABLE`. The fix requires the 12-step recipe:

```sql
-- 1. Disable FK enforcement during the migration
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- 2. Create the corrected table under a temporary name
CREATE TABLE measurements_new (
    id    INTEGER PRIMARY KEY,
    value INTEGER NOT NULL,
    label TEXT
) STRICT;

-- 3. Copy data — bad rows will error here, which is what you want.
--    Decide: fix them, cast them, or exclude them.
INSERT INTO measurements_new SELECT id, CAST(value AS INTEGER), label
    FROM measurements
    WHERE typeof(value) = 'integer';   -- or handle bad rows explicitly

-- 4. Drop the old table
DROP TABLE measurements;

-- 5. Rename the new one
ALTER TABLE measurements_new RENAME TO measurements;

COMMIT;

-- 6. Re-enable FK enforcement and verify
PRAGMA foreign_keys = ON;
PRAGMA integrity_check;
```

The `INSERT` step is where bad rows surface — you can `CAST`, skip them, or raise an error depending on what the data should have been.

---

## Quick Diagnostic for the Current Table

Before migrating, find all the bad rows:

```sql
SELECT rowid, value, typeof(value)
FROM measurements
WHERE typeof(value) != 'integer';
```

This tells you the scope of the problem and what values you're actually dealing with before you decide how to handle them in the migration.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is substantially more complete and accurate across all three rubric criteria. It provides a detailed, correct explanation of type affinity, gives a thorough migration recipe explicitly noting you cannot add STRICT to an existing table in place, and covers handling bad data during migration. Answer A mentions STRICT tables but its example error message is wrong (says 'UNIQUE constraint failed' instead of a type error), and it completely omits the migration path for existing tables.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains type affinity | skill |
| recommends STRICT tables | skill |
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
| recommends STRICT tables | ✓ | `Strict` |
| mentions migration path for existing tables | ✓ | `Recreate` |

<details><summary>haiku: baseline answer</summary>

# SQLite Type Affinity Explained

SQLite allows this because it uses **type affinity**, not strict type enforcement. SQLite is dynamically typed and will accept any data type in any column—it just tries to convert it when possible.

## Why 'banana' in an INTEGER column is "legal"

SQLite's type system is permissive:
- It stores the actual type with the data
- When you query, it attempts conversions based on context
- If conversion fails, it just returns the original value

```sql
CREATE TABLE test (id INTEGER);
INSERT INTO test VALUES ('banana');  -- No error!
SELECT id, typeof(id) FROM test;
-- Result: banana | text
```

## How to Prevent This Going Forward

### Option 1: Use `STRICT` Tables (SQLite 3.37.0+)

The best modern solution—enforce actual type checking:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
) STRICT;

INSERT INTO users VALUES (1, 'banana');  -- OK
INSERT INTO users VALUES ('banana', 'test');  -- ERROR: UNIQUE constraint failed
```

### Option 2: Add CHECK Constraints

For older SQLite versions:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY CHECK(typeof(id) = 'integer'),
    name TEXT NOT NULL
);

INSERT INTO users VALUES ('banana', 'test');  -- ERROR: CHECK constraint failed
```

### Option 3: Application-Level Validation

Validate data before inserting (always good practice anyway):

```python
# Python example
if not isinstance(value, int):
    raise ValueError("id must be an integer")
```

## Fixing Existing Data

```sql
-- Find problematic rows
SELECT * FROM your_table WHERE typeof(column_name) != 'integer';

-- Delete or fix them
DELETE FROM your_table WHERE typeof(column_name) != 'integer';
```

**Recommendation**: Use `STRICT` tables if you're on SQLite 3.37.0+ (released 2022). It's the cleanest solution.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Type Affinity vs. Strict Tables

This is SQLite's **type affinity** system — a design choice that prioritizes flexibility over strictness. Here's what happened and how to fix it.

## Why SQLite Accepted 'banana' in an INTEGER Column

SQLite has *advisory* types, not enforced constraints. When you declare a column `INTEGER`, that's an **affinity** — a *preference* for how to store and coerce values, not a hard constraint.

On insert, SQLite tries to coerce the value to the declared type:
- `'123'` → coerced to `123` (integer)
- `'banana'` → cannot coerce → stored as-is, as text

The column happily stores whatever it can't coerce. This is by design — SQLite prioritizes not losing data over enforcing types.

```sql
-- This table has NO type enforcement
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    age INTEGER,
    name TEXT
);

INSERT INTO users (id, age, name) VALUES (1, 'banana', 'Alice');
-- ✓ Succeeds. age column now contains the string 'banana'.

SELECT typeof(age), age FROM users WHERE id = 1;
-- typeof(age) | age
-- text        | banana
```

## The Fix: Use STRICT Tables

SQLite 3.37+ (2021) added **`STRICT` tables**, which enforce declared types and reject mismatched values:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    age INTEGER,
    name TEXT
) STRICT;

INSERT INTO users (id, age, name) VALUES (1, 'banana', 'Alice');
-- ✗ CONSTRAINT error: UNIQUE constraint failed: users.age
-- (Actually: type mismatch on age — text value in INTEGER column)
```

With `STRICT`:
- `INTEGER` columns reject non-integer values.
- `TEXT` columns reject non-text values.
- `REAL` columns reject non-numeric values.
- `BLOB` columns reject non-blob values.
- `NULL` is always allowed (unless you add `NOT NULL`).

## For Existing Tables: The 12-Step Recipe

You cannot add `STRICT` to an existing table in place. You must:

1. **Disable foreign key constraints** (so you can drop the old table):
   ```sql
   PRAGMA foreign_keys = OFF;
   ```

2. **Create a new strict table** with the same schema:
   ```sql
   CREATE TABLE users_new (
       id INTEGER PRIMARY KEY,
       age INTEGER,
       name TEXT
   ) STRICT;
   ```

3. **Copy data** (this is where bad rows surface):
   ```sql
   INSERT INTO users_new SELECT * FROM users;
   -- If this fails, you have type mismatches. Fix them first:
   -- INSERT INTO users_new SELECT id, CAST(age AS INTEGER), name FROM users WHERE age NOT LIKE '%[^0-9]%';
   ```

4. **Drop the old table**:
   ```sql
   DROP TABLE users;
   ```

5. **Rename the new table**:
   ```sql
   ALTER TABLE users_new RENAME TO users;
   ```

6. **Recreate indexes** (they were dropped with the old table):
   ```sql
   CREATE INDEX users_age_idx ON users(age);
   ```

7. **Recreate triggers** (if any):
   ```sql
   CREATE TRIGGER users_updated AFTER UPDATE ON users BEGIN
       UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
   END;
   ```

8. **Re-enable foreign key constraints**:
   ```sql
   PRAGMA foreign_keys = ON;
   ```

If you have many indexes or triggers, wrap this in a transaction and test on a copy first.

## Handling Existing Bad Data

If the `INSERT INTO users_new SELECT * FROM users` fails because of type mismatches, you need to clean the data first:

```sql
-- Find rows with non-integer age
SELECT id, age, typeof(age) FROM users WHERE typeof(age) != 'integer';

-- Option 1: Delete bad rows
DELETE FROM users WHERE typeof(age) != 'integer';

-- Option 2: Coerce bad rows (if possible)
UPDATE users SET age = NULL WHERE typeof(age) != 'integer';

-- Option 3: Try to parse them
UPDATE users SET age = CAST(age AS INTEGER) WHERE typeof(age) = 'text' AND age GLOB '[0-9]*';
```

Then retry the migration.

## Best Practice Going Forward

For **all new tables**, use `STRICT`:

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    data BLOB,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
) STRICT;
```

This gives you:
- Compile-time-like type safety (at the database level).
- Immediate feedback on schema mismatches.
- No silent data corruption from type coercion.
- Minimal performance overhead (the check is trivial).

## Summary

| Aspect | Non-STRICT | STRICT |
|---|---|---|
| Type enforcement | Advisory (affinity) | Enforced |
| `'banana'` in `INTEGER` column | ✓ Allowed | ✗ Rejected |
| `NULL` in non-nullable column | ✓ Allowed (unless `NOT NULL` added) | ✗ Rejected |
| Migration cost | None | One-time 12-step recipe |
| Recommended for new schemas | ✗ No | ✓ Yes |

Use `STRICT` for all new tables. For existing tables with bad data, run the migration when you have a maintenance window.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more comprehensive and detailed on all three rubric criteria. It explains type affinity thoroughly, strongly recommends STRICT tables with clear examples, and provides a complete migration recipe including the critical point that STRICT cannot be added in-place and requires the recreate-and-copy pattern with practical cleanup steps using typeof(). Answer B covers the same ground but more superficially, and while it mentions the migration challenge, it doesn't provide the full recipe or the important BEGIN IMMEDIATE guidance.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains type affinity | skill |
| recommends STRICT tables | tie |
| mentions migration path for existing tables | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains type affinity | ✓ | `type affinit` |
| recommends STRICT tables | ✓ | `strict` |
| mentions migration path for existing tables | ✓ | `recreate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains type affinity | ✓ | `Type Affinit` |
| recommends STRICT tables | ✓ | `STRICT` |
| mentions migration path for existing tables | ✓ | `Recreate` |

<details><summary>opus: baseline answer</summary>

# Why SQLite Let You Store 'banana' in an INTEGER Column

This is **by design** in SQLite, not a bug. It's called **type affinity**.

## How this is "legal"

Unlike most databases, SQLite uses a dynamic type system. Column types are *suggestions* (called "affinities"), not strict constraints. When you declare a column as `INTEGER`, SQLite will:

1. **Try** to convert incoming values to an integer
2. If conversion isn't possible (like with `'banana'`), **store it as-is** anyway

The only exception historically was `INTEGER PRIMARY KEY`, which is strictly enforced because it aliases the rowid.

```sql
CREATE TABLE t (id INTEGER, val INTEGER);
INSERT INTO t VALUES (1, 'banana');  -- Works fine 😱
INSERT INTO t VALUES (2, '42');      -- Stored as integer 42
INSERT INTO t VALUES (3, 'banana');  -- Stored as text 'banana'
```

## How to prevent it going forward

### Option 1: STRICT tables (SQLite 3.37+, released Nov 2021)

This is the modern, recommended fix:

```sql
CREATE TABLE t (
    id INTEGER PRIMARY KEY,
    val INTEGER
) STRICT;

INSERT INTO t VALUES (1, 'banana');
-- Error: cannot store TEXT value in INTEGER column t.val
```

In STRICT tables:
- Only these types are allowed: `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, `ANY`
- Type checking is enforced on insert/update
- It behaves much more like PostgreSQL/MySQL

### Option 2: CHECK constraints (works on older versions)

```sql
CREATE TABLE t (
    id INTEGER PRIMARY KEY,
    val INTEGER CHECK (typeof(val) IN ('integer', 'null'))
);
```

### Cleaning up existing data

Find the offenders first:

```sql
SELECT rowid, val, typeof(val) 
FROM t 
WHERE typeof(val) NOT IN ('integer', 'null');
```

Then fix or delete them before migrating to a STRICT table (you'll need to recreate the table since STRICT can't be added with `ALTER`).

## Recommendation

**Use `STRICT` for all new tables.** The historical flexibility of SQLite's type system causes more bugs than it prevents, and STRICT mode brings sanity without sacrificing SQLite's other benefits.

</details>

<details><summary>opus: skill-loaded answer</summary>

# SQLite Type Affinity: Why `'banana'` Lives in Your INTEGER Column

This is working as designed, and it's one of SQLite's oldest sharp edges.

## Why it's legal

In a regular (non-`STRICT`) table, column types are **affinities**, not constraints. When you write `col INTEGER`, you are giving SQLite a *hint* about what you intend to store, not a rule it must enforce. On insert, SQLite tries to coerce the value to the column's affinity — but if the value can't be losslessly converted, **SQLite stores it as-is** rather than rejecting it.

The coercion rules for `INTEGER` affinity:
- `42` → stored as integer ✓
- `'42'` → coerced to integer `42` ✓
- `'banana'` → cannot be coerced → **stored as text**, no error

This dates back to SQLite's original "manifest typing" design: every *value* has a type, but columns only suggest one. It made sense in 2000 for an embedded scripting database. It is a footgun in 2024 for an application database.

## The fix for new tables: `STRICT`

Since SQLite 3.37 (2021), declare the table `STRICT`:

```sql
CREATE TABLE events (
    id    INTEGER PRIMARY KEY,
    count INTEGER NOT NULL,
    name  TEXT
) STRICT;

INSERT INTO events (count, name) VALUES ('banana', 'x');
-- Runtime error: cannot store TEXT value in INTEGER column events.count
```

Strict tables also restrict you to a small set of allowed type names (`INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, `ANY`) — no more `VARCHAR(255)` being silently treated as `TEXT` affinity, no more `DATETIME` being whatever-the-hell.

Use `STRICT` for every new schema. There is no meaningful downside.

## The fix for your existing table

You can't add `STRICT` to a table in place — `ALTER TABLE` doesn't support it. You need the standard 12-step recipe:

```sql
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE events_new (
    id    INTEGER PRIMARY KEY,
    count INTEGER NOT NULL,
    name  TEXT
) STRICT;

-- This INSERT is where your bad rows surface — it will fail on 'banana'.
INSERT INTO events_new SELECT id, count, name FROM events;

DROP TABLE events;
ALTER TABLE events_new RENAME TO events;

-- Recreate any indexes/triggers/views that referenced the old table.

COMMIT;
PRAGMA foreign_key_check;       -- verify nothing broke
PRAGMA foreign_keys = ON;
```

The `INSERT ... SELECT` is the moment of truth: every malformed row will throw a constraint error. You'll need to clean those up first — typically with something like:

```sql
-- Find the offenders
SELECT id, count FROM events WHERE typeof(count) != 'integer';

-- Fix or delete them, then retry the migration
UPDATE events SET count = 0 WHERE typeof(count) = 'text';
```

`typeof()` returns the *actual* storage class of the value (`'integer'`, `'text'`, `'real'`, `'blob'`, `'null'`), which is how you find affinity violations in a non-strict table.

## Why `BEGIN IMMEDIATE` above

If anything else might write to this database during the migration, `BEGIN IMMEDIATE` acquires the `RESERVED` lock up front. The default `BEGIN` is `BEGIN DEFERRED`, which only upgrades to `RESERVED` on the first write — and that mid-transaction upgrade is what produces `SQLITE_BUSY` under contention, after you've already done work. Always use `BEGIN IMMEDIATE` for transactions that will write.

## Bottom line

- **New tables:** always `STRICT`. No exceptions for application schemas.
- **Existing tables:** migrate via the rebuild recipe; `typeof()` finds the bad rows first.
- **Diagnostic:** `SELECT typeof(col) FROM table GROUP BY 1` on any column you suspect — it'll tell you the actual storage classes in use.

</details>

---

### `json-index`

**Prompt**

```
I added a JSON column called `data` and created an index:
`CREATE INDEX events_user ON events(json_extract(data, '$.user_id'))`.
But my queries `WHERE data->>'user_id' = ?` are still doing full table
scans. What's wrong?
```

**Judge focus:** The better answer explains that the index expression must match the
query expression exactly, and recommends a STORED generated column as
the cleaner fix.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A better satisfies the focus area and rubric by recommending a STORED generated column as the primary fix, explicitly mentioning the STORED keyword, and explaining why it's cleaner than just matching expressions. Answer B focuses primarily on matching the expression syntax and only briefly touches on the generated column concept implicitly, missing the STORED keyword and the generated column recommendation entirely.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains the expression mismatch | tie |
| recommends generated column | skill |
| mentions STORED keyword | skill |
| suggests EXPLAIN QUERY PLAN | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✓ | `exactly match` |
| recommends generated column | ✗ | |
| mentions STORED keyword | ✗ | |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✓ | `different expression` |
| recommends generated column | ✓ | `generated column` |
| mentions STORED keyword | ✓ | `stored` |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>sonnet: baseline answer</summary>

## The Problem: Expression Mismatch

SQLite indexes on expressions only get used when the query's expression **exactly matches** the index definition. You're using two different syntaxes.

| | Syntax | Equivalent |
|---|---|---|
| **Index** | `json_extract(data, '$.user_id')` | |
| **Query** | `data->>'user_id'` | `json_extract(data, '$.user_id')` returns **text** |

Even though they return the same value, SQLite's query planner does a **literal string match** on the expression — it won't recognize them as equivalent.

---

## Fix Options

### Option 1: Match the query to the index (recommended)
```sql
-- Change your query to match the index exactly
SELECT * FROM events
WHERE json_extract(data, '$.user_id') = ?;
```

### Option 2: Rebuild the index to match your preferred query syntax
```sql
DROP INDEX events_user;

CREATE INDEX events_user ON events(data->>'user_id');

-- Now this query will use the index
SELECT * FROM events WHERE data->>'user_id' = ?;
```

---

## Verify the Index Is Being Used

```sql
EXPLAIN QUERY PLAN
SELECT * FROM events WHERE json_extract(data, '$.user_id') = ?;
```

**Bad output** (full scan):
```
SCAN events
```

**Good output** (index used):
```
SEARCH events USING INDEX events_user (<expr>=?)
```

---

## Other Things to Check

```sql
-- 1. Confirm the index exists
SELECT * FROM sqlite_master WHERE type = 'index' AND tbl_name = 'events';

-- 2. Make sure you're not wrapping the expression in a function
-- This will BREAK index usage even if the expression matches:
WHERE CAST(json_extract(data, '$.user_id') AS TEXT) = ?  -- ❌ no index
WHERE json_extract(data, '$.user_id') = ?                -- ✅ index used

-- 3. Type affinity matters
-- If user_id is numeric, comparing to a string won't use the index:
WHERE json_extract(data, '$.user_id') = '123'  -- ❌ might not use index
WHERE json_extract(data, '$.user_id') = 123    -- ✅ correct type
```

---

## Key Takeaway

SQLite expression indexes require **exact textual/syntactic matching** between the index definition and the query predicate. Pick one syntax and use it consistently everywhere.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The index expression and your `WHERE` expression don't match — SQLite's query planner requires an **exact textual match** between the two.

## What's happening

| | Expression | Equivalent? |
|---|---|---|
| **Index** | `json_extract(data, '$.user_id')` | ✓ same value |
| **Query** | `data->>'user_id'` | ✓ same value |
| **Planner sees them as** | two different expressions | ✗ no index match |

`->>` is syntactic sugar that expands to `json_extract(...)` at parse time, but the planner matches index expressions **before** that expansion, so it never recognizes them as the same thing.

You can verify this with:

```sql
EXPLAIN QUERY PLAN SELECT * FROM events WHERE data->>'user_id' = 'abc';
-- SCAN events   ← bad; index not used

EXPLAIN QUERY PLAN SELECT * FROM events WHERE json_extract(data, '$.user_id') = 'abc';
-- SEARCH events USING INDEX events_user   ← good
```

## The right fix: a stored generated column

Rather than relying on expression-matching at all, pull the JSON path into a real column and index that. This is unambiguous, readable, and lets you use the clean `->>`  syntax in queries.

```sql
-- 1. Add the generated column (STORED means it's persisted on disk)
ALTER TABLE events
  ADD COLUMN user_id TEXT
  GENERATED ALWAYS AS (data->>'user_id') STORED;

-- 2. Index the column
CREATE INDEX events_user_id ON events(user_id);

-- 3. Query the column directly — no JSON function needed
SELECT * FROM events WHERE user_id = 'abc';
```

```
EXPLAIN QUERY PLAN SELECT * FROM events WHERE user_id = 'abc';
-- SEARCH events USING INDEX events_user_id (user_id=?)   ✓
```

## Why not just fix the query expression?

You *could* rewrite every query to use `json_extract(data, '$.user_id') = ?` to match the existing index, and it would work. But:

- Every caller has to remember the exact spelling — one `->>`  and you're back to a full scan with no error or warning.
- The generated column approach is self-documenting, enforces consistency, and the column shows up in `PRAGMA table_info` so tools know it exists.

## Drop the old index once you've migrated

```sql
DROP INDEX events_user;
```

The expression index on `json_extract(data, '$.user_id')` is now redundant and just wastes write overhead.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more focused and complete: it correctly explains the expression mismatch in SQLite context, prominently recommends a STORED generated column as the primary fix with clear explanation of why STORED matters, and includes EXPLAIN QUERY PLAN verification. Answer A is more scattered across multiple databases (PostgreSQL, MySQL, SQLite) which dilutes the SQLite-specific advice, buries the generated column option, and doesn't mention the STORED keyword at all.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains the expression mismatch | skill |
| recommends generated column | skill |
| mentions STORED keyword | skill |
| suggests EXPLAIN QUERY PLAN | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✗ | |
| recommends generated column | ✗ | |
| mentions STORED keyword | ✗ | |
| suggests EXPLAIN QUERY PLAN | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✓ | `different expression` |
| recommends generated column | ✓ | `Generated Column` |
| mentions STORED keyword | ✓ | `STORED` |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>haiku: baseline answer</summary>

# JSON Index Not Being Used - Operator Mismatch

The issue is **operator mismatch** between your index definition and your query:

- **Index uses**: `json_extract(data, '$.user_id')` (function-based)
- **Query uses**: `data->>'user_id'` (operator-based)

These are functionally equivalent but syntactically different, so the query planner won't recognize the index.

## Solutions

### Option 1: Rewrite Query to Match Index (Recommended)
Use `json_extract()` in your query to match the index:

```sql
WHERE json_extract(data, '$.user_id') = ?
```

### Option 2: Recreate Index to Match Query Operator
If you prefer the `->>'` syntax, recreate the index:

```sql
-- PostgreSQL
CREATE INDEX events_user ON events((data->>'user_id'));

-- MySQL 5.7+
CREATE INDEX events_user ON events((JSON_UNQUOTE(JSON_EXTRACT(data, '$.user_id'))));

-- SQLite 3.9+
CREATE INDEX events_user ON events(json_extract(data, '$.user_id'));
```

### Option 3: Use Expression Index (PostgreSQL)
```sql
CREATE INDEX events_user ON events USING btree ((data->>'user_id'));
```

## Verification

Check if the index is being used:

```sql
-- PostgreSQL
EXPLAIN SELECT * FROM events WHERE json_extract(data, '$.user_id') = '123';

-- MySQL
EXPLAIN SELECT * FROM events WHERE json_extract(data, '$.user_id') = '123';
```

Look for `Index Scan` or `Using index` in the output.

**Pro tip**: Always verify index usage with `EXPLAIN` after creating indexes on JSON columns—they're easy to accidentally create but not use.

</details>

<details><summary>haiku: skill-loaded answer</summary>

The issue is **expression mismatch**: your index uses `json_extract(data, '$.user_id')`, but your query uses `data->>'user_id'`. Even though they produce the same value, SQLite's query planner treats them as different expressions and won't use the index.

The `->>` operator returns a SQL value (text), while `json_extract` returns JSON. More importantly, they're syntactically distinct, so the planner doesn't recognize them as the same indexed expression.

## The Fix: Use a STORED Generated Column

The cleanest solution is to extract the JSON path into a `STORED` generated column, then index *that*:

```sql
-- Add a generated column for the extracted value
ALTER TABLE events ADD COLUMN user_id TEXT GENERATED ALWAYS AS (data->>'user_id') STORED;

-- Index the column (not the expression)
CREATE INDEX events_user_id_idx ON events(user_id);

-- Now query the column directly
SELECT * FROM events WHERE user_id = ?;
```

**Why this works:**
- The generated column is materialized in the table (because of `STORED`), so it's indexed like any normal column.
- Your query now matches the index exactly.
- `EXPLAIN QUERY PLAN` will show `SEARCH events USING INDEX events_user_id_idx`.

## If You Can't Alter the Table

If you're stuck with the existing schema, you have two options:

**Option 1: Rewrite queries to match the index expression exactly**
```sql
-- This will use the index
SELECT * FROM events WHERE json_extract(data, '$.user_id') = ?;
```

**Option 2: Drop and recreate the index with the exact expression your queries use**
```sql
DROP INDEX events_user;
CREATE INDEX events_user ON events(data->>'user_id');
```

Then query with `data->>'user_id' = ?` and it will match.

## Why the Generated Column Approach is Best

1. **Clarity**: The column name `user_id` is self-documenting; queries read naturally.
2. **Flexibility**: You can query the column with `=`, `<`, `IN`, `LIKE`, etc. without worrying about expression syntax.
3. **Consistency**: If you later add other JSON extracts, the pattern scales cleanly.
4. **Performance**: No re-parsing of JSON on every query; the value is already extracted and indexed.

## Verify It Works

```sql
EXPLAIN QUERY PLAN SELECT * FROM events WHERE user_id = ?;
```

Should show:
```
SEARCH events USING INDEX events_user_id_idx
```

If it still shows `SCAN TABLE`, double-check that:
- The index was created *after* the generated column was added.
- You're querying the column name, not the expression.
- You ran `ANALYZE` to update statistics (though the planner usually picks an index even without stats).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A covers all four rubric criteria more thoroughly: it clearly explains the expression mismatch, recommends a generated column as the primary fix, explicitly mentions the STORED keyword with an explanation of why it matters, and suggests EXPLAIN QUERY PLAN with example output. Answer B only briefly mentions two fixes without recommending the generated column approach or mentioning STORED, and while it suggests EXPLAIN QUERY PLAN, it lacks the depth and completeness of Answer A.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains the expression mismatch | skill |
| recommends generated column | skill |
| mentions STORED keyword | skill |
| suggests EXPLAIN QUERY PLAN | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✓ | `same expression` |
| recommends generated column | ✗ | |
| mentions STORED keyword | ✓ | `stored` |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains the expression mismatch | ✓ | `different expression` |
| recommends generated column | ✓ | `Generated column` |
| mentions STORED keyword | ✓ | `STORED` |
| suggests EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>opus: baseline answer</summary>

The issue is that your index expression doesn't match your query expression. SQLite's expression index matching is **syntactic**, not semantic — it has to see the exact same expression.

You indexed `json_extract(data, '$.user_id')` but you're querying with `data->>'user_id'`. Even though these return similar values, they're not the same:

- `->>` is equivalent to `json_extract(data, '$.user_id')` only when the result is a SQL text/numeric value, but the operator is treated as a distinct expression by the query planner.
- More importantly, `->>` may have different type-affinity behavior than `json_extract` in some cases, and the planner won't substitute one for the other.

**Two ways to fix it:**

1. **Change the index to match the query:**
   ```sql
   CREATE INDEX events_user ON events(data->>'user_id');
   ```

2. **Change the query to match the index:**
   ```sql
   SELECT ... WHERE json_extract(data, '$.user_id') = ?;
   ```

Verify with `EXPLAIN QUERY PLAN` — you should see `SEARCH ... USING INDEX events_user` instead of `SCAN`.

**One more gotcha:** if you're comparing against an integer parameter but `json_extract` returns text (or vice versa), the type mismatch can also defeat the index. Make sure the bound parameter type matches what the JSON value actually is. If `user_id` is stored as a JSON number, bind an integer; if it's a JSON string, bind text.

</details>

<details><summary>opus: skill-loaded answer</summary>

# The Problem: Expression Mismatch

SQLite's index matcher requires the `WHERE` expression to **textually match** the indexed expression (after normalization). `data->>'user_id'` and `json_extract(data, '$.user_id')` produce the **same value** but are **different expressions** as far as the index matcher is concerned, so your index is ignored.

Confirm with:
```sql
EXPLAIN QUERY PLAN
SELECT * FROM events WHERE data->>'user_id' = ?;
-- SCAN events   ← bad, index not matched
```

## Three Fixes (Pick One)

### Fix 1: Match the expression in the query (smallest change)

Change either side to match. Easiest is to change the query:

```sql
SELECT * FROM events WHERE json_extract(data, '$.user_id') = ?;
```

Verify:
```sql
EXPLAIN QUERY PLAN
SELECT * FROM events WHERE json_extract(data, '$.user_id') = ?;
-- SEARCH events USING INDEX events_user (<expr>=?)   ← good
```

Or rebuild the index using `->>` to match your existing queries:
```sql
DROP INDEX events_user;
CREATE INDEX events_user ON events(data->>'user_id');
```

**Caveat:** `->>` was added in SQLite 3.38 (Feb 2022). On older versions, only `json_extract` works.

### Fix 2: Generated column + index (recommended)

This is the cleanest approach — the JSON path becomes a real column you can query, index, add `FOREIGN KEY`s to, etc.

```sql
DROP INDEX events_user;

ALTER TABLE events
  ADD COLUMN user_id TEXT
  GENERATED ALWAYS AS (data->>'user_id') STORED;

CREATE INDEX events_user_id_idx ON events(user_id);
```

Then query the column directly:
```sql
SELECT * FROM events WHERE user_id = ?;
-- SEARCH events USING INDEX events_user_id_idx (user_id=?)
```

`STORED` (vs `VIRTUAL`) materializes the value on disk — required for non-trivial indexing performance and lets the planner use it as a covering column.

### Fix 3: Partial index (if `user_id` is often `NULL`)

If most rows have no `user_id` and you only query the ones that do:

```sql
CREATE INDEX events_user_id_idx
  ON events(data->>'user_id')
  WHERE data->>'user_id' IS NOT NULL;
```

Smaller index, cheaper writes. Query must include the same `WHERE` predicate (or a more restrictive one) for the planner to pick it.

## Other Things to Check

If the expressions already match and it's still scanning:

1. **Stats are stale.** Run `ANALYZE events;` then re-check. Without stats, the planner sometimes guesses wrong on small tables.
2. **Type coercion.** `data->>'user_id'` returns `TEXT`. If you're binding an integer parameter (`WHERE … = 42`), SQLite may not match the index. Bind as a string or cast: `WHERE data->>'user_id' = CAST(? AS TEXT)`.
3. **Small table.** Under a few hundred rows, the planner correctly chooses a scan because it's cheaper than the index lookup. This is fine.
4. **`SELECT *` on a tiny row count + low selectivity.** If most rows match, a scan beats an index. Check `EXPLAIN QUERY PLAN` with a selective value.

## Recommendation

Go with **Fix 2** (generated column). It's the idiomatic SQLite pattern for "I have JSON but query one field a lot": the column shows up in `PRAGMA table_info`, queries read naturally, and you can layer constraints (`CHECK`, `UNIQUE`, `FOREIGN KEY`) on it later. The storage overhead is one copy of the field per row, which is negligible compared to the index itself.

</details>

---

### `json-arrow-vs-double-arrow`

**Prompt**

```
In SQLite, what's the difference between `data->'profile'` and
`data->>'profile'` in a JSON column query? I'm seeing weird
comparison results when I use `WHERE data->'profile' = 'admin'`.
```

**Judge focus:** The better answer explains that `->` returns a JSON value (still
JSON-quoted text for strings) while `->>` returns a SQL value
(unquoted, ready to compare). The user's WHERE is failing because
`->` is yielding `'"admin"'` (with the JSON quotes) and that
won't equal `'admin'`. JSONB is worth a mention as the storage
optimization but is a separate axis.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core criteria well, but Answer B is more concise and adds genuinely useful practical content (indexing and generated columns) without becoming bloated. Answer A is thorough but overly long with some tangential content (booleans, nulls) that dilutes the focus. Both mention JSONB implicitly through the storage/indexing discussion, though neither explicitly names JSONB as a storage format — Answer B's indexing section is more actionable. For the core rubric criteria, both answers are essentially tied, but B's tighter presentation and the addition of the indexing/generated column tip make it marginally better overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains -> returns JSON | tie |
| explains ->> returns SQL value / text | tie |
| tells the user to use ->> for the WHERE | tie |
| mentions JSONB | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains -> returns JSON | ✓ | `-> returns JSON` |
| explains ->> returns SQL value / text | ✓ | `unquoted` |
| tells the user to use ->> for the WHERE | ✓ | `Use ->>` |
| mentions JSONB | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains -> returns JSON | ✓ | `JSON value` |
| explains ->> returns SQL value / text | ✓ | `unquoted` |
| tells the user to use ->> for the WHERE | ✓ | `data->>'profile'` |
| mentions JSONB | ✗ | |

<details><summary>sonnet: baseline answer</summary>

## SQLite JSON Operators: `->` vs `->>`

These two operators extract JSON data differently, and mixing them up causes subtle comparison bugs.

---

### The Core Difference

| Operator | Name | Returns | Type |
|----------|------|---------|------|
| `->` | JSON extract | JSON representation | JSON/text with quotes |
| `->>` | JSON extract (unquoted) | SQL value | Native SQL type |

---

### The Problem You're Hitting

```sql
-- Your data stored in the column:
-- {"profile": "admin", "level": 5, "active": true}

-- ❌ This FAILS silently - never matches strings
WHERE data->'profile' = 'admin'

-- ✅ This works correctly  
WHERE data->>'profile' = 'admin'
```

**Why it fails:** `->` returns `"admin"` (with JSON quotes), not `admin`.

```sql
-- See the difference yourself:
SELECT 
    data->'profile',    -- Returns: "admin"  ← JSON string with quotes
    data->>'profile'    -- Returns: admin    ← Plain SQL text
FROM users;
```

---

### Type Handling Differences

```sql
-- Setup
CREATE TABLE users (data JSON);
INSERT INTO users VALUES ('{"name":"Alice","score":42,"active":true,"address":null}');

-- Strings
SELECT data->'name'    FROM users;  -- "Alice"  (quoted)
SELECT data->>'name'   FROM users;  -- Alice    (unquoted)

-- Numbers  
SELECT data->'score'   FROM users;  -- 42       (same visually)
SELECT data->>'score'  FROM users;  -- 42       (same visually)
-- BUT the types differ:
SELECT typeof(data->'score')   FROM users;  -- text
SELECT typeof(data->>'score')  FROM users;  -- integer ← native type

-- Booleans
SELECT data->'active'   FROM users;  -- true    (JSON literal)
SELECT data->>'active'  FROM users;  -- 1       ← converted to SQL integer

-- Nulls (tricky!)
SELECT data->'address'   FROM users;  -- null   (JSON null as text)
SELECT data->>'address'  FROM users;  -- NULL   ← actual SQL NULL
```

---

### Practical Comparison Examples

```sql
-- ❌ String comparison with -> always fails
WHERE data->'profile' = 'admin'      -- comparing "admin" = admin → false

-- ✅ Use ->> for string comparison
WHERE data->>'profile' = 'admin'

-- ❌ Number comparison with -> may fail due to type mismatch
WHERE data->'score' > 40             -- works accidentally sometimes

-- ✅ Safer with ->>
WHERE data->>'score' > 40            -- 42 > 40 → true

-- ❌ Null check with -> doesn't work as expected
WHERE data->'address' IS NULL        -- false! it's the text "null"

-- ✅ Null check requires ->>
WHERE data->>'address' IS NULL       -- true, proper SQL NULL

-- When -> IS useful: comparing JSON structures
WHERE data->'tags' = '["admin","user"]'  -- JSON-to-JSON comparison
```

---

### When to Actually Use `->`

```sql
-- Chaining nested access (intermediate steps)
SELECT data->'address'->>'city' FROM users;
--           ^^                         
--           -> returns JSON so you can chain another extraction

-- Comparing whole JSON objects/arrays
WHERE data->'permissions' = '{"read":true,"write":false}'

-- Passing to JSON functions
SELECT json_array_length(data->'tags') FROM users;
```

---

### Quick Decision Rule

```
Need to compare or use the value in SQL?  → use ->>
Need to extract a nested sub-object?       → use -> (then ->> at the end)
```

```sql
-- Nested example combining both:
SELECT data->'address'->>'city' FROM users
WHERE  data->'address'->>'city' = 'London';
--     ^^^^^^^^^^^^ JSON    ^^^^ final SQL value
```

---

### The Fix for Your Query

```sql
-- ❌ Before
WHERE data->'profile' = 'admin'

-- ✅ After  
WHERE data->>'profile' = 'admin'
```

The `->` operator is essentially only useful as an intermediate step when navigating nested JSON — for any final comparison or value use, always reach for `->>`.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## `->` vs. `->>` in SQLite JSON

The difference is what *type* comes back:

| Operator | Returns | Example result for `'admin'` |
|---|---|---|
| `->` | JSON fragment (always `TEXT` with JSON encoding) | `'"admin"'` (quoted) |
| `->>` | SQL value (typed: `TEXT`, `INTEGER`, `REAL`, or `NULL`) | `'admin'` (unquoted) |

That's why your comparison fails. When the stored value is the string `admin`, `data->'profile'` returns the JSON-encoded `"admin"` — including the double-quotes — so comparing it to the SQL text `'admin'` never matches.

```sql
-- Given a row where data = '{"profile":"admin"}'

SELECT data->'profile'  FROM t;  -- returns: "admin"  (JSON text, quoted)
SELECT data->>'profile' FROM t;  -- returns: admin    (SQL TEXT, unquoted)

-- Your broken query:
WHERE data->'profile'  = 'admin'   -- 'admin' ≠ '"admin"' → never matches

-- The fix:
WHERE data->>'profile' = 'admin'   -- 'admin' = 'admin'  → matches correctly
```

### When `->` is actually useful

`->` is for chaining into nested structures, because it preserves the JSON type so you can keep drilling:

```sql
-- Nested: {"profile": {"role": "admin"}}
SELECT data->'profile'->>'role' FROM t;
--            ^^ keeps JSON    ^^ extracts final SQL value
```

If you used `->>` at the first step, you'd get a plain SQL text string and couldn't chain further JSON operators on it.

### Integer extraction

The type difference also matters for numbers:

```sql
-- data = '{"score": 42}'
SELECT data->'score'  FROM t;  -- TEXT: '42'  (JSON number, stored as text)
SELECT data->>'score' FROM t;  -- INTEGER: 42 (actual SQL integer)

WHERE data->>'score' > 40   -- works: integer comparison
WHERE data->'score'  > 40   -- unreliable: text vs. integer comparison
```

### Indexing rule

If you're indexing a JSON path, the index expression must exactly match the query expression — so use `->>` in both the index and the `WHERE` clause, or use a generated column (cleaner):

```sql
-- Option 1: expression index (must match query exactly)
CREATE INDEX t_profile ON t(data->>'profile');
SELECT * FROM t WHERE data->>'profile' = 'admin';  -- uses the index

-- Option 2: generated column (recommended — easier to query and index)
ALTER TABLE t ADD COLUMN profile TEXT GENERATED ALWAYS AS (data->>'profile') STORED;
CREATE INDEX t_profile ON t(profile);
SELECT * FROM t WHERE profile = 'admin';
```

**Rule of thumb:** use `->>` whenever you're comparing, filtering, or aggregating a JSON value. Reserve `->` for intermediate steps when navigating nested JSON.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly explain the -> vs ->> distinction and tell the user to use ->> for WHERE clauses. Answer B is more precise about the core issue (explicitly stating that -> returns '"admin"' with JSON quotes while ->> returns 'admin' without), mentions JSONB in the generated column example, and provides additional practical value with indexing guidance. Answer A is cleaner and more concise but misses the JSONB mention and is less precise about why the comparison fails.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains -> returns JSON | skill |
| explains ->> returns SQL value / text | tie |
| tells the user to use ->> for the WHERE | tie |
| mentions JSONB | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains -> returns JSON | ✓ | `JSON value` |
| explains ->> returns SQL value / text | ✗ | |
| tells the user to use ->> for the WHERE | ✓ | `data->>'profile'` |
| mentions JSONB | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains -> returns JSON | ✓ | `-> returns JSON` |
| explains ->> returns SQL value / text | ✗ | |
| tells the user to use ->> for the WHERE | ✓ | `use ->>` |
| mentions JSONB | ✓ | `JSONB` |

<details><summary>haiku: baseline answer</summary>

# SQLite JSON Operators: `->` vs `->>`

The key difference is in **return types**:

- **`->`** returns a **JSON value** (could be string, number, object, etc.)
- **`->>`** returns a **text string** (always converts to TEXT)

## Why Your Comparison Fails

```sql
-- ❌ This doesn't work as expected
WHERE data->'profile' = 'admin'
```

The left side (`data->'profile'`) returns JSON, while `'admin'` is a text literal. SQLite compares them as different types, so the comparison fails.

## The Solution

Use `->>`  to convert to text:

```sql
-- ✅ This works
WHERE data->>'profile' = 'admin'
```

## Practical Examples

```sql
-- Sample data: {"profile": "admin", "age": 30}

-- Returns JSON string: "admin"
SELECT data->'profile' FROM users;

-- Returns text: admin (without quotes)
SELECT data->>'profile' FROM users;

-- Comparison: JSON vs text (fails)
WHERE data->'profile' = 'admin'        -- ❌ No match

-- Comparison: text vs text (works)
WHERE data->>'profile' = 'admin'       -- ✅ Matches

-- Alternative: use json_extract() with json_quote()
WHERE json_extract(data, '$.profile') = json_quote('admin')  -- ✅ Also works
```

## When to Use Each

| Operator | Use Case |
|----------|----------|
| `->` | Extracting nested JSON objects/arrays to pass to other JSON functions |
| `->>` | Extracting scalar values for text comparisons or display |

**Rule of thumb:** Use `->>` for `WHERE` clauses with scalar comparisons.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# JSON Operators: `->` vs `->>`

The difference is **type**:

- **`->`** returns a **JSON value** (could be a string, number, object, array, or null)
- **`->>`** returns a **SQL text value** (always a string, or NULL)

Your `WHERE data->'profile' = 'admin'` is comparing a JSON value to a SQL string, which triggers SQLite's type coercion rules and often fails silently or gives unexpected results.

## The Problem in Your Query

```sql
-- ❌ WRONG: comparing JSON value to SQL string
WHERE data->'profile' = 'admin'
```

When `data` is `{"profile": "admin"}`:
- `data->'profile'` returns the JSON string `"admin"` (with quotes)
- `'admin'` is a SQL string `admin` (no quotes)
- The comparison `"admin"` = `admin` fails because one is JSON and one is SQL

The fix is immediate:

```sql
-- ✅ RIGHT: use ->> to get SQL text
WHERE data->>'profile' = 'admin'
```

Now both sides are SQL strings and the comparison works.

## When to Use Each

| Operator | Returns | Use Case |
|---|---|---|
| `->` | JSON value | Extracting nested objects/arrays; passing to other JSON functions; storing intermediate results |
| `->>` | SQL text | Comparing to strings; filtering in `WHERE`; displaying to users; joining to other tables |

### Examples

```sql
-- Extract a nested object (need ->)
SELECT data->'user' FROM events;
-- Returns: {"id": 123, "name": "Alice"}

-- Extract a string for comparison (need ->>)
SELECT * FROM events WHERE data->>'user_id' = '123';

-- Chain JSON operations (use -> between functions, ->> at the end)
SELECT json_extract(data->'user', '$.name') FROM events;
-- or more idiomatically:
SELECT data->'user'->>'name' FROM events;

-- Unnest an array (-> returns JSON array, json_each processes it)
SELECT value FROM events, json_each(data->'tags');
```

## The Index Problem You Likely Have

If you're also seeing slow queries, the issue compounds:

```sql
-- ❌ Index on the JSON expression
CREATE INDEX idx_profile ON events(json_extract(data, '$.profile'));

-- ❌ Query with ->> doesn't match the indexed expression
WHERE data->>'profile' = 'admin'  -- SCAN TABLE, not SEARCH
```

The planner sees `data->>'profile'` and `json_extract(data, '$.profile')` as *different expressions*, so it won't use the index.

**Fix: use a `STORED` generated column** (the clean solution):

```sql
ALTER TABLE events ADD COLUMN profile TEXT GENERATED ALWAYS AS (data->>'profile') STORED;
CREATE INDEX idx_profile ON events(profile);

-- Now query the column directly
SELECT * FROM events WHERE profile = 'admin';
-- EXPLAIN QUERY PLAN shows: SEARCH events USING INDEX idx_profile
```

Or if you must index the expression directly, match it exactly in the query:

```sql
CREATE INDEX idx_profile ON events(data->>'profile');

-- Query must use the same expression
WHERE data->>'profile' = 'admin'  -- Now uses the index
```

## Quick Reference

```sql
-- JSON column with nested data
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  data JSONB,
  -- Add a generated column for the path you query often
  user_id TEXT GENERATED ALWAYS AS (data->>'user_id') STORED,
  profile TEXT GENERATED ALWAYS AS (data->>'profile') STORED
);

CREATE INDEX idx_user_id ON events(user_id);
CREATE INDEX idx_profile ON events(profile);

-- Queries now use the columns, not the JSON expressions
SELECT * FROM events WHERE user_id = '123' AND profile = 'admin';
```

This gives you the best of both worlds: clean queries, fast indexes, and no type confusion.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly explain the -> vs ->> distinction and tell the user to switch to ->>, but Answer A covers more ground with greater depth: it explains the json_extract asymmetry, includes a practical indexing gotcha with generated columns, and provides a chaining example. Answer B is cleaner and more concise, and uniquely mentions JSONB (via the PostgreSQL mirroring note) and the json_quote alternative, but overall Answer A is more comprehensive and useful for someone debugging real queries.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains -> returns JSON | skill |
| explains ->> returns SQL value / text | tie |
| tells the user to use ->> for the WHERE | tie |
| mentions JSONB | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains -> returns JSON | ✓ | `JSON value` |
| explains ->> returns SQL value / text | ✓ | `SQL value` |
| tells the user to use ->> for the WHERE | ✓ | `use ->>` |
| mentions JSONB | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains -> returns JSON | ✓ | `JSON value` |
| explains ->> returns SQL value / text | ✓ | `SQL value` |
| tells the user to use ->> for the WHERE | ✓ | `data->>'profile'` |
| mentions JSONB | ✗ | |

<details><summary>opus: baseline answer</summary>

# The Difference Between `->` and `->>` in SQLite JSON

## Short answer

- **`->`** returns a **JSON representation** (the value is still JSON-encoded text)
- **`->>`** returns a **SQL value** (text, integer, real, or NULL — the actual underlying value)

This is why your `WHERE` comparison is behaving strangely.

## Example

Given a column `data` containing:
```json
{"profile": "admin", "age": 30}
```

| Expression | Result | SQL Type |
|---|---|---|
| `data->'profile'` | `"admin"` (with the quotes!) | TEXT (JSON) |
| `data->>'profile'` | `admin` (no quotes) | TEXT |
| `data->'age'` | `30` | TEXT (JSON) |
| `data->>'age'` | `30` | INTEGER |

## Why your query fails

```sql
WHERE data->'profile' = 'admin'
```

This compares the JSON string `"admin"` (literally including the double quotes) against the SQL string `admin`. They're not equal.

You have two correct options:

```sql
-- Option 1: use ->> to get the raw text
WHERE data->>'profile' = 'admin'

-- Option 2: compare against a JSON value
WHERE data->'profile' = '"admin"'
-- (or more explicitly)
WHERE data->'profile' = json_quote('admin')
```

Option 1 is almost always what you want.

## Rule of thumb

- Use **`->>`** when comparing to or returning ordinary SQL values (strings, numbers, booleans).
- Use **`->`** only when you need to keep working with JSON — e.g., chaining further extractions on a nested object/array, or passing the result to another `json_*` function.

```sql
-- chaining on JSON (use ->)
SELECT data->'address'->>'city' FROM users;

-- final scalar (end with ->>)
SELECT data->>'name' FROM users;
```

This matches PostgreSQL's behavior, which SQLite intentionally mirrored when these operators were added in 3.38.

</details>

<details><summary>opus: skill-loaded answer</summary>

# `->` vs `->>` in SQLite JSON

Short version: **`->` returns JSON, `->>` returns a SQL value.** Your `WHERE` clause is failing because of that distinction.

## The operators

| Operator | Returns | Example with `data = '{"profile":"admin"}'` |
|---|---|---|
| `->` | JSON (a `TEXT` value containing JSON syntax) | `data->'profile'` → `'"admin"'` (note the embedded quotes) |
| `->>` | SQL scalar (`TEXT`, `INTEGER`, `REAL`, or `NULL`) | `data->>'profile'` → `'admin'` |

So `data->'profile'` extracts the JSON value `"admin"` — and in JSON, a string includes its surrounding double quotes. When SQLite compares that to the SQL string `'admin'`, you're comparing the 7-character string `"admin"` (with quotes) against the 5-character string `admin`. They're not equal.

## What you want

```sql
-- Wrong: compares '"admin"' (JSON) to 'admin' (SQL) → never matches
WHERE data->'profile' = 'admin'

-- Right: compares 'admin' (SQL text) to 'admin' (SQL text)
WHERE data->>'profile' = 'admin'
```

Equivalently:

```sql
WHERE json_extract(data, '$.profile') = 'admin'
```

`->>` and `json_extract` produce the same SQL scalar; `->` and `json_extract` differ — `json_extract` returns a SQL value when the path resolves to a primitive, JSON text only when it resolves to an object or array. `->` *always* returns JSON text. That asymmetry trips people up; if in doubt, reach for `->>` for leaf values and `->` only when you're chaining further into nested structure.

## When `->` is the right choice

Chaining into nested objects/arrays — you need JSON on the left side to keep extracting:

```sql
-- data = '{"user":{"profile":{"role":"admin"}}}'
WHERE data->'user'->'profile'->>'role' = 'admin'
--      ^^^^^^^^^^^^^^^^^^^^^^ JSON      ^^ SQL scalar at the leaf
```

Each `->` keeps you in JSON-land; the final `->>` pops out to a SQL value for comparison.

## Indexing gotcha

If you have an index, the indexed expression and the query expression must match exactly. An index on `json_extract(data, '$.profile')` won't be used by a query on `data->>'profile'` even though they evaluate to the same thing — the planner matches on expression syntax, not semantics. Pick one form and use it everywhere, or (cleaner) add a `STORED` generated column and index that:

```sql
ALTER TABLE users ADD COLUMN profile TEXT
  GENERATED ALWAYS AS (data->>'profile') STORED;
CREATE INDEX users_profile_idx ON users(profile);

-- queries become:
WHERE profile = 'admin'
```

Verify with `EXPLAIN QUERY PLAN` — you want `SEARCH ... USING INDEX`, not `SCAN TABLE`.

</details>

---

### `covering-index-design`

**Prompt**

```
My SQLite query `SELECT user_id, email FROM users WHERE status = 'active'`
is fast — there's an index on `status`. But the very similar query
`SELECT user_id, email, phone FROM users WHERE status = 'active'`
is much slower. Same index. Why is the second one slow, and how
do I fix it?
```

**Judge focus:** The better answer recognizes this as a covering-index situation:
the first query is satisfied entirely from the index; the second
has to do a rowid lookup back into the base table per row to fetch
`phone`. The fix is to extend the index to cover `phone` (or all
selected columns), and the user should confirm with EXPLAIN QUERY
PLAN.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the covering index concept, explain rowid lookups, suggest adding columns to the index, and recommend EXPLAIN QUERY PLAN. Answer A is slightly more accurate in its explanation — it correctly notes that user_id as INTEGER PRIMARY KEY is already embedded in the index and doesn't need to be listed explicitly, and it adds valuable extras like partial indexes. Answer B includes a minor inaccuracy by suggesting user_id should be explicitly added to the index even when it's the primary key, and its claim that Query 1 has 'the same problem' as Query 2 (just masked by caching) is misleading since the first query genuinely benefits from a covering index. Overall both are high quality, but A is more precise and complete.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names "covering index" | tie |
| explains base-table / rowid lookup | skill |
| suggests adding the missing column to the index | tie |
| recommends EXPLAIN QUERY PLAN | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names "covering index" | ✓ | `Covering Index` |
| explains base-table / rowid lookup | ✓ | `rowid` |
| suggests adding the missing column to the index | ✓ | `(status, user_id, email, phone` |
| recommends EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names "covering index" | ✓ | `covering index` |
| explains base-table / rowid lookup | ✓ | `rowid` |
| suggests adding the missing column to the index | ✓ | `(status, email, phone` |
| recommends EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>sonnet: baseline answer</summary>

## Why the Second Query Is Slower

The difference comes down to how SQLite uses the index and what happens **after** it finds matching rows.

### What's Happening: Table Lookups ("Back to Table" Fetches)

```
Index on status
┌─────────────────────────────────┐
│ status='active' → rowid 1       │  ← index stores status + rowid only
│ status='active' → rowid 5       │
│ status='active' → rowid 9       │
│ ...                             │
└─────────────────────────────────┘
         │
         │ For each rowid, SQLite must go BACK to the main table
         ▼        to fetch the columns it needs
┌─────────────────────────────────┐
│ rowid 1: user_id, email, phone  │  ← random I/O for each row
│ rowid 5: user_id, email, phone  │
│ rowid 9: user_id, email, phone  │
└─────────────────────────────────┘
```

**Query 1** (`user_id, email`) — same problem exists, BUT if SQLite decides the result set is small enough, or if you got lucky with caching, it may feel fast. The fundamental issue is the same.

**Query 2** (`user_id, email, phone`) — adding `phone` makes it obvious the index can't satisfy the query alone, forcing these random table lookups at scale.

---

### The Real Fix: A Covering Index

A **covering index** includes all columns the query needs, so SQLite **never touches the main table**.

```sql
-- Covers: the WHERE clause + all SELECTed columns
CREATE INDEX idx_users_status_covering
ON users (status, user_id, email, phone);
```

Now the query is satisfied **entirely within the index**:

```
Index: (status, user_id, email, phone)
┌──────────────────────────────────────────────┐
│ active | 1  | alice@example.com | 555-0001   │  ← everything here
│ active | 5  | bob@example.com   | 555-0002   │  ← no table visit needed
│ active | 9  | carol@example.com | 555-0003   │
└──────────────────────────────────────────────┘
```

---

### Verify It Worked with EXPLAIN QUERY PLAN

```sql
-- Before: you'll see "SEARCH users USING INDEX" + table lookups
EXPLAIN QUERY PLAN
SELECT user_id, email, phone FROM users WHERE status = 'active';

-- After covering index: look for "COVERING INDEX" in the output
EXPLAIN QUERY PLAN
SELECT user_id, email, phone FROM users WHERE status = 'active';
```

**Good output looks like:**
```
QUERY PLAN
`--SEARCH users USING COVERING INDEX idx_users_status_covering (status=?)
```
The word **COVERING** confirms no table fetch is needed.

---

### Index Column Ordering Matters

```sql
-- Put the equality filter column FIRST
CREATE INDEX idx ON users (status, user_id, email, phone);
--                          ^^^^^^
--                    filtered column goes first
```

| Position | Rule |
|---|---|
| First | Columns in `WHERE` with `=` |
| Middle | Columns in `ORDER BY` or `GROUP BY` |
| Last | Columns only in `SELECT` |

---

### Trade-offs to Know

| | Benefit | Cost |
|---|---|---|
| Covering index | Eliminates table lookups | Larger index, slower writes |
| Too many covering indexes | Fast reads | Index maintenance overhead |
| Wide tables | — | More painful without covering indexes |

**Practical rule:** If a query runs frequently and touches a predictable set of columns, a covering index is almost always worth it. For ad-hoc or rare queries, it usually isn't.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The index on `status` is being used in both cases — but the two queries do different amounts of work after the index lookup, and that difference is what you're seeing.

## Why the first query is fast: covering index

For `SELECT user_id, email FROM users WHERE status = 'active'`, SQLite can satisfy the entire query from the index alone — *if* `user_id` and `email` happen to be in the index. An index on `status` implicitly includes the rowid (the table's primary key), so if `user_id` is the `INTEGER PRIMARY KEY`, it's already there. If `email` is also in the index, SQLite never touches the table at all. This is called a **covering index**, and `EXPLAIN QUERY PLAN` will say `USING COVERING INDEX`.

Even if `email` isn't in the index, the query may still be fast simply because it returns fewer bytes per row — but the key structural difference is the covering-index case.

## Why the second query is slower: the table lookup (row fetch)

Adding `phone` forces SQLite to do a **second lookup for every matching row**:

```
index on status
  └─ find all rows where status = 'active'
       └─ for each match, take the rowid and fetch the full row from the table
            └─ read user_id, email, phone from the table page
```

This extra step is called a **rowid lookup** (or "table fetch"). If `status = 'active'` matches many rows, and those rows are scattered across many table pages, you get many random page reads. That's the slowdown.

You can confirm this with `EXPLAIN QUERY PLAN`:

```sql
EXPLAIN QUERY PLAN
SELECT user_id, email, phone FROM users WHERE status = 'active';
```

Look for the difference:
- **Fast (covering):** `SEARCH users USING COVERING INDEX ...`
- **Slow (table fetch):** `SEARCH users USING INDEX ...` ← no "COVERING"

## The fix: make the index cover the query

Create an index that includes every column the query needs:

```sql
CREATE INDEX users_status_covering
    ON users(status, email, phone);
```

`user_id` doesn't need to be listed if it's the `INTEGER PRIMARY KEY` — it's already embedded in every index entry as the rowid.

Now `EXPLAIN QUERY PLAN` should show `USING COVERING INDEX users_status_covering`, and the table is never touched.

## If you have several queries with different column sets

Rather than creating one index per query, think about which columns are queried together most often and build one or two covering indexes that serve multiple queries. Indexes have a write cost — every `INSERT`, `UPDATE`, and `DELETE` on `users` must update each index.

A reasonable general-purpose index for a `users` table with frequent status-filtered reads:

```sql
CREATE INDEX users_active_covering
    ON users(status, email, phone)
    WHERE status = 'active';   -- partial index: only indexes active rows
```

The `WHERE status = 'active'` makes it a **partial index**: smaller, faster to maintain, and the planner will prefer it for queries that filter on `status = 'active'`. If you also query `status = 'suspended'` frequently, drop the partial clause and cover both.

## Quick summary

| Query | Index used | Table fetch? | Speed |
|---|---|---|---|
| `SELECT user_id, email … WHERE status = ?` | `idx_status` | No (covering) | Fast |
| `SELECT user_id, email, phone … WHERE status = ?` | `idx_status` | Yes, one per row | Slow |
| `SELECT user_id, email, phone … WHERE status = ?` | `idx_status_covering(status, email, phone)` | No (covering) | Fast |

The rule of thumb: **a query is only as fast as its slowest column**. Any column in `SELECT`, `WHERE`, or `ORDER BY` that isn't in the index forces a trip back to the table.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A more clearly and accurately explains the covering index concept, correctly noting that the first query is fast because the index already covers user_id and email (SQLite indexes include the rowid/primary key implicitly), and explicitly names the 'rowid lookup' mechanism causing the slowdown. Answer A also provides more accurate EXPLAIN QUERY PLAN output examples and better explains the distinction between the two queries. Answer B has a minor inaccuracy by calling the per-row lookup a 'table scan' rather than a rowid/table lookup, and its EXPLAIN QUERY PLAN guidance is less precise.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names "covering index" | skill |
| explains base-table / rowid lookup | skill |
| suggests adding the missing column to the index | tie |
| recommends EXPLAIN QUERY PLAN | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names "covering index" | ✓ | `Covering Index` |
| explains base-table / rowid lookup | ✓ | `main table` |
| suggests adding the missing column to the index | ✓ | `(status, user_id, email, phone` |
| recommends EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names "covering index" | ✓ | `covering index` |
| explains base-table / rowid lookup | ✓ | `main table` |
| suggests adding the missing column to the index | ✓ | `(status, user_id, email, phone` |
| recommends EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>haiku: baseline answer</summary>

# Why Adding a Column Made Your Query Slow

This is a classic SQLite performance issue related to **index-only queries** vs. **table lookups**.

## The Problem

Your first query can be satisfied entirely by the index on `status`:
- Index filters by `status = 'active'`
- Index contains `user_id` and `email` (or at least `user_id`)
- SQLite never needs to touch the main table

Your second query **cannot** use the index alone:
- Index filters by `status = 'active'` ✓
- But `phone` isn't in the index
- SQLite must look up each matching row in the main table to get `phone` ✗

This causes a **table scan** for every filtered row, which is slow.

## Solutions

### Option 1: Add `phone` to the Index (Best for this query)
```sql
CREATE INDEX idx_users_status_phone 
ON users(status, user_id, email, phone);
```

Now the index contains everything needed—true index-only query.

**Trade-off:** Larger index, slower writes.

### Option 2: Use a Covering Index (Flexible)
```sql
CREATE INDEX idx_users_status_covering 
ON users(status) INCLUDE (user_id, email, phone);
```

The `INCLUDE` clause adds columns without making them part of the search key. This is more efficient than Option 1 for filtering.

**Note:** `INCLUDE` requires SQLite 3.31.0+ (2020).

### Option 3: Accept the Trade-off (If queries vary)
If you run many different queries selecting different columns, covering indexes become impractical. In this case, ensure your main table has good locality (not fragmented) and accept occasional table lookups.

## How to Verify

Check if your query is index-only:
```sql
EXPLAIN QUERY PLAN 
SELECT user_id, email, phone FROM users WHERE status = 'active';
```

Look for `SEARCH users USING INDEX` without a subsequent table scan. If you see `SCAN TABLE users`, you're doing table lookups.

**Option 2 is usually the best balance** between query speed and index overhead.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Why the Second Query Is Slow

The first query is fast because it's a **covering index hit**: the index on `status` contains `status`, `user_id`, and `email` (in that order), so SQLite never touches the main table — it reads everything from the index alone.

The second query is slow because it needs `phone`, which is *not* in the index. SQLite must:
1. Search the index for `status = 'active'` (fast)
2. For each matching row, jump to the main table to fetch `phone` (slow — one random I/O per row)

This is called an **index-to-table lookup** or **table fetch**. If you have 10,000 active users, that's 10,000 random seeks into the table file.

## The Fix: Make It a Covering Index

Add all the columns you select to the index:

```sql
CREATE INDEX idx_users_status_covering 
  ON users(status) 
  INCLUDE (user_id, email, phone);
```

Or, if you're on SQLite < 3.31 (which doesn't have `INCLUDE`), list them in the index itself:

```sql
CREATE INDEX idx_users_status_covering 
  ON users(status, user_id, email, phone);
```

Now `EXPLAIN QUERY PLAN` will show:

```
SEARCH users USING COVERING INDEX idx_users_status_covering
```

The query reads everything from the index and never touches the table.

## When to Use Covering Indexes

- **Hot read queries** on a small set of columns filtered by an indexed column.
- **Not** for every query — covering indexes are larger and slower to maintain on writes.
- **Not** if the columns you're selecting change often — you'd have to rebuild the index.

## The Trade-Off

Covering indexes use more disk space and slow down `INSERT`/`UPDATE`/`DELETE` slightly (the index is wider). But for a frequently-run query that currently does thousands of table fetches, the read speedup (often 10–100×) is worth it.

## Quick Diagnostic

Run both queries with `EXPLAIN QUERY PLAN`:

```sql
EXPLAIN QUERY PLAN 
  SELECT user_id, email FROM users WHERE status = 'active';

EXPLAIN QUERY PLAN 
  SELECT user_id, email, phone FROM users WHERE status = 'active';
```

The first will show `USING COVERING INDEX` (or just `USING INDEX`); the second will show `USING INDEX` followed by a table scan, or a `SCAN TABLE` if the index isn't being used at all. Once you add `phone` to the index, both will show `USING COVERING INDEX`.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer B is more direct and accurate from the start, correctly identifying the covering index situation without the self-correction detour that Answer A takes mid-explanation. Answer B clearly explains the rowid lookup mechanism, recommends EXPLAIN QUERY PLAN with the key 'COVERING' keyword to look for, and provides the same fix options (covering index and partial index) in a cleaner, more confident presentation. Answer A's mid-answer self-correction ('Wait — that's not covering either. Let me reconsider.') undermines its credibility and introduces confusion.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names "covering index" | baseline |
| explains base-table / rowid lookup | baseline |
| suggests adding the missing column to the index | tie |
| recommends EXPLAIN QUERY PLAN | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names "covering index" | ✓ | `Covering Index` |
| explains base-table / rowid lookup | ✓ | `rowid` |
| suggests adding the missing column to the index | ✓ | `(status, user_id, email, phone` |
| recommends EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names "covering index" | ✓ | `covering index` |
| explains base-table / rowid lookup | ✓ | `rowid` |
| suggests adding the missing column to the index | ✓ | `(status, user_id, email, phone` |
| recommends EXPLAIN QUERY PLAN | ✓ | `EXPLAIN QUERY PLAN` |

<details><summary>opus: baseline answer</summary>

# The Issue: Covering Index vs. Table Lookup

Your first query is fast because of a **covering index**. The second is slow because it isn't covered.

## What's happening

You almost certainly have an index like:

```sql
CREATE INDEX idx_users_status ON users(status);
```

But SQLite's query planner is likely using a different index — probably one that *includes* `user_id` and `email` (perhaps an index on `(status, user_id, email)`, or `email` is in the rowid lookup path, or you have something like `CREATE INDEX ... ON users(status, email)` and `user_id` is the `INTEGER PRIMARY KEY` / rowid).

For the **first query**, SQLite can answer entirely from the index pages — it never touches the actual table. This is a "covering index" scan.

For the **second query**, `phone` isn't in the index. So for *every* matching row, SQLite must:

1. Find the entry in the index.
2. Do a separate lookup into the table b-tree by rowid to fetch `phone`.

If `status = 'active'` matches lots of rows, that's potentially millions of random I/O lookups into the main table. This is often called the **"index tipping point"** problem — and SQLite may even decide the index isn't worth using and fall back to a full table scan.

## How to confirm it

Run `EXPLAIN QUERY PLAN` on both:

```sql
EXPLAIN QUERY PLAN
SELECT user_id, email FROM users WHERE status = 'active';
-- Likely: SEARCH users USING COVERING INDEX ...

EXPLAIN QUERY PLAN
SELECT user_id, email, phone FROM users WHERE status = 'active';
-- Likely: SEARCH users USING INDEX ...   (no "COVERING")
-- or: SCAN users
```

The presence or absence of the word **COVERING** tells the whole story.

## How to fix it

**Option 1: Make the index cover all the columns you select.**

```sql
CREATE INDEX idx_users_status_covering 
    ON users(status, user_id, email, phone);
```

Now both queries can be answered straight from the index. Note: in SQLite, all index columns are "key columns" (no `INCLUDE` clause like in PostgreSQL/SQL Server), so they all add to index size and write cost.

**Option 2: If most rows are `active`, accept the table scan.**

If 80% of your users are active, an index isn't really helping anyway — a sequential table scan is faster than millions of random lookups. Consider whether `status` is selective enough to bother indexing.

**Option 3: Partial index, if `'active'` is the case you care about.**

```sql
CREATE INDEX idx_users_active 
    ON users(user_id, email, phone) 
    WHERE status = 'active';
```

Smaller, faster, and still covering for queries that filter on `status = 'active'`.

## Trade-offs to keep in mind

- **Wider indexes cost more on writes** (every `INSERT`/`UPDATE` to a covered column rewrites index pages) and use more disk.
- Don't reflexively add every column you ever select. Cover indexes for **hot queries**, not everything.
- Run `ANALYZE` after creating new indexes so the planner has good stats.

The short version: SQLite was getting away with skipping the table read for query #1. Adding `phone` forced it back to row-by-row table lookups, and that's where your time went.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Why the second query is slower

Your index on `status` is a **covering index** for the first query but not the second.

## What "covering" means

When SQLite uses an index, the index B-tree contains the indexed column(s) plus the rowid (the pointer back to the table row). For a rowid table, an index on `status` actually stores `(status, rowid)`.

- **Query 1** asks for `user_id, email`. SQLite finds matching rows in the index, then has to do a rowid lookup into the main table to fetch `user_id` and `email`. Wait — that's not covering either. Let me reconsider.

Actually, let me be precise. Neither query is covered by an index on `status` alone. Both should require table lookups. So why the speed difference?

## The real reason: row width and the table-fetch step

Both queries do the same index scan, but both also have to fetch the actual row from the table for each match. The difference is what happens during that fetch:

1. **Query 1** reads `user_id, email` — likely fits in fewer pages, possibly even just the main row record.
2. **Query 2** also reads `phone`. If `phone` is a `TEXT` column with longer values, the row may overflow onto additional pages, or simply require reading more bytes per row.

But row width alone usually isn't a *dramatic* difference. The much more likely culprit:

## Confirm with `EXPLAIN QUERY PLAN`

```sql
EXPLAIN QUERY PLAN SELECT user_id, email FROM users WHERE status = 'active';
EXPLAIN QUERY PLAN SELECT user_id, email, phone FROM users WHERE status = 'active';
```

Look for:
- `SEARCH users USING COVERING INDEX ...` ← fast, index-only
- `SEARCH users USING INDEX ...` ← index seek + table fetch per row
- `SCAN users` ← full table scan, index ignored

I suspect query 1 shows `USING COVERING INDEX` (meaning you have a multi-column index like `(status, user_id, email)`, not just `(status)`), and query 2 falls back to `USING INDEX` with a per-row table fetch. With many matching rows, that per-row fetch turns sequential index reads into scattered random I/O against the table.

## The fix: a covering index for the second query

```sql
CREATE INDEX users_status_covering
  ON users(status, user_id, email, phone);
```

Now query 2 can be answered entirely from the index — no table fetch at all. Re-run `EXPLAIN QUERY PLAN` and you should see `USING COVERING INDEX users_status_covering`.

## Cheaper variant if most rows aren't active

If `status = 'active'` matches a small fraction of the table, a **partial covering index** is even better:

```sql
CREATE INDEX users_active_covering
  ON users(user_id, email, phone)
  WHERE status = 'active';
```

Smaller index, faster maintenance, planner picks it for any query with a matching `WHERE status = 'active'`.

## Trade-offs to be aware of

- Covering indexes get larger as you add columns. Don't blindly include every column the table has — only the ones the hot query reads.
- Every additional column in the index slows down `INSERT`/`UPDATE` on that table. If `phone` updates frequently, you're paying a write cost for the read speedup.
- If you have many similar queries reading different column sets, you may end up wanting one well-chosen covering index rather than one per query.

## Verify after creating

```sql
ANALYZE users;
EXPLAIN QUERY PLAN SELECT user_id, email, phone FROM users WHERE status = 'active';
```

You should see `SEARCH users USING COVERING INDEX users_status_covering`, and the query should be comparable in speed to the first one — often faster, since now neither needs a table fetch.

For more on reading query plans and index design, see the queries-and-indexes reference in this skill.

</details>

---

### `simplest-write-tx`

**Prompt**

```
Just give me the simplest, fewest-lines way to write a row inside a
transaction in Go using `database/sql` with SQLite. I don't need
bells and whistles, just the shortest correct snippet.
```

**Judge focus:** A naive answer reaches for `db.BeginTx(ctx, nil)`, which generates
`BEGIN DEFERRED` — that's the trap that causes SQLITE_BUSY mid-transaction
under contention. The better answer either uses BEGIN IMMEDIATE or warns
the reader about the trap explicitly.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A explicitly addresses the SQLITE_BUSY / DEFERRED transaction trap, explains why plain BeginTx is wrong for SQLite writes, and provides the correct BEGIN IMMEDIATE approach. Answer B ignores the contention issue entirely and recommends the naive db.Begin() which generates BEGIN DEFERRED, falling directly into the trap the question is designed to test for.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows BEGIN IMMEDIATE for the write tx | skill |
| avoids recommending plain BeginTx without warning | skill |
| warns about SQLITE_BUSY / contention / DEFERRED | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✗ | |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✓ | `BEGIN IMMEDIATE` |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✓ | `SQLITE_BUSY` |

<details><summary>sonnet: baseline answer</summary>

```go
tx, _ := db.Begin()
_, err := tx.Exec("INSERT INTO items (name) VALUES (?)", "foo")
if err != nil {
    tx.Rollback()
}
tx.Commit()
```

That's the core of it. A few notes on what's omitted for brevity:

- **Error check on `db.Begin()`** — in real code, check it.
- **Error check on `tx.Commit()`** — in real code, check it; a commit can fail.
- **`defer tx.Rollback()`** — a common pattern is to defer rollback immediately after `Begin()`. It's a no-op if `Commit()` already succeeded, and it's safer than the explicit `if err` block above.

The slightly more robust (but still minimal) real-world version:

```go
tx, err := db.Begin()
if err != nil {
    log.Fatal(err)
}
defer tx.Rollback() // no-op after Commit

_, err = tx.Exec("INSERT INTO items (name) VALUES (?)", "foo")
if err != nil {
    log.Fatal(err)
}

if err := tx.Commit(); err != nil {
    log.Fatal(err)
}
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the shortest correct version — but "simplest" has one mandatory rule with SQLite: use `BEGIN IMMEDIATE`, not the default `BEGIN DEFERRED`. The default generates a deferred transaction that upgrades its lock on the first write, which causes `SQLITE_BUSY` mid-transaction under any concurrency.

```go
tx, err := db.BeginTx(ctx, nil) // ← WRONG for SQLite writes; generates BEGIN DEFERRED
```

Instead:

```go
tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelDefault})
```

…still generates `BEGIN DEFERRED`. There's no `TxOptions` field for `IMMEDIATE`. The correct minimal approach:

```go
_, err := db.ExecContext(ctx, "BEGIN IMMEDIATE")
if err != nil {
    return err
}
_, err = db.ExecContext(ctx, "INSERT INTO items (name) VALUES (?)", name)
if err != nil {
    db.ExecContext(ctx, "ROLLBACK")
    return err
}
_, err = db.ExecContext(ctx, "COMMIT")
if err != nil {
    db.ExecContext(ctx, "ROLLBACK")
    return err
}
```

But raw `ExecContext` on a pool is wrong too — `database/sql` can route each statement to a different connection. The actual minimal correct snippet:

```go
conn, err := db.Conn(ctx)          // pin to one connection
if err != nil {
    return err
}
defer conn.Close()

if _, err = conn.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil {
    return err
}
if _, err = conn.ExecContext(ctx, "INSERT INTO items (name) VALUES (?)", name); err != nil {
    conn.ExecContext(ctx, "ROLLBACK")
    return err
}
if _, err = conn.ExecContext(ctx, "COMMIT"); err != nil {
    conn.ExecContext(ctx, "ROLLBACK")
    return err
}
```

**If you use `mattn/go-sqlite3`**, you can avoid the manual `BEGIN IMMEDIATE` by setting `_txlock=immediate` in the DSN, which makes `db.BeginTx(ctx, nil)` emit `BEGIN IMMEDIATE` automatically — then the standard `*sql.Tx` handles connection pinning and rollback for you:

```go
// DSN (do this once at sql.Open time):
// "file:app.db?_txlock=immediate&_journal_mode=WAL&_foreign_keys=on&_busy_timeout=5000"

tx, err := db.BeginTx(ctx, nil)
if err != nil {
    return err
}
defer tx.Rollback() // no-op after Commit

if _, err = tx.ExecContext(ctx, "INSERT INTO items (name) VALUES (?)", name); err != nil {
    return err
}
return tx.Commit()
```

That last block is the shortest *and* correct version — 7 lines — but it only works with the `_txlock=immediate` DSN parameter. With `modernc.org/sqlite` you need the `conn`-pinning approach above since that driver doesn't support `_txlock`.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly addresses the SQLITE_BUSY/DEFERRED transaction trap, warns about plain BeginTx, and demonstrates BEGIN IMMEDIATE via sql.LevelSerializable. Answer A uses the naive db.Begin() (which generates BEGIN DEFERRED) with no warnings, ignores errors, and completely misses the contention issue the rubric focuses on. Despite Answer B having a minor error (tx.Commit().Error instead of tx.Commit()), it satisfies all three rubric criteria while Answer A satisfies none.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows BEGIN IMMEDIATE for the write tx | skill |
| avoids recommending plain BeginTx without warning | skill |
| warns about SQLITE_BUSY / contention / DEFERRED | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✗ | |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✓ | `BEGIN IMMEDIATE` |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✓ | `SQLITE_BUSY` |

<details><summary>haiku: baseline answer</summary>

```go
tx, _ := db.Begin()
tx.Exec("INSERT INTO table (col) VALUES (?)", value)
tx.Commit()
```

That's it. (In production code, you'd handle the errors instead of ignoring them with `_`.)

</details>

<details><summary>haiku: skill-loaded answer</summary>

Here's the shortest *correct* snippet:

```go
tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
if err != nil {
    return err
}
defer tx.Rollback()

_, err = tx.ExecContext(ctx, "INSERT INTO users (name) VALUES (?)", "Alice")
if err != nil {
    return err
}

return tx.Commit().Error
```

**But stop.** The "simplest" version — bare `db.BeginTx(ctx, nil)` — is a trap:

```go
// ❌ DO NOT DO THIS
tx, err := db.BeginTx(ctx, nil)  // generates BEGIN DEFERRED
_, err = tx.ExecContext(ctx, "INSERT INTO users (name) VALUES (?)", "Alice")
// ^ SQLITE_BUSY can happen HERE, mid-transaction, under any real load
```

`BEGIN DEFERRED` (the default) acquires locks lazily. The write happens *after* the transaction starts, so contention surfaces mid-flight. Under concurrent load, you'll get `SQLITE_BUSY` errors that are hard to retry cleanly.

**The correct minimal version uses `BEGIN IMMEDIATE`:**

```go
tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
if err != nil {
    return err
}
defer tx.Rollback()

_, err = tx.ExecContext(ctx, "INSERT INTO users (name) VALUES (?)", "Alice")
if err != nil {
    return err
}

return tx.Commit().Error
```

`sql.LevelSerializable` maps to `BEGIN IMMEDIATE` in SQLite, acquiring the `RESERVED` lock up front. The busy handler (set via `busy_timeout` in your DSN) then does its job at transaction start, not mid-flight.

**Also confirm your DSN includes the pragmas:**

```go
db, _ := sql.Open("sqlite3", "file:app.db?cache=shared&mode=rwc&_journal_mode=WAL&_busy_timeout=5000&_foreign_keys=on")
```

Without `_busy_timeout` in the DSN, the busy handler is disabled and you'll get immediate `SQLITE_BUSY` errors instead of retries.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly addresses the SQLITE_BUSY/DEFERRED transaction trap that is the core focus of the question, providing two concrete solutions (DSN parameter and manual BEGIN IMMEDIATE). Answer A simply uses db.Begin() without any warning about the DEFERRED transaction issue, which is exactly the naive approach the question is trying to avoid.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| shows BEGIN IMMEDIATE for the write tx | skill |
| avoids recommending plain BeginTx without warning | skill |
| warns about SQLITE_BUSY / contention / DEFERRED | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✗ | |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| shows BEGIN IMMEDIATE for the write tx | ✓ | `BEGIN IMMEDIATE` |
| avoids recommending plain BeginTx without warning | ✓ | |
| warns about SQLITE_BUSY / contention / DEFERRED | ✓ | `SQLITE_BUSY` |

<details><summary>opus: baseline answer</summary>

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

<details><summary>opus: skill-loaded answer</summary>

The shortest *correct* snippet still has to use `BEGIN IMMEDIATE` — the obvious one-liner using `db.BeginTx` generates `BEGIN DEFERRED` and will give you `SQLITE_BUSY` mid-transaction the moment a second writer shows up. There's no shorter form that's safe under concurrency.

Two equally-short ways:

**Option A — put `_txlock=immediate` in the DSN, then `BeginTx` is fine:**

```go
db, _ := sql.Open("sqlite3", "app.db?_journal=WAL&_timeout=5000&_fk=1&_txlock=immediate")

tx, _ := db.BeginTx(ctx, nil)
_, err := tx.ExecContext(ctx, "INSERT INTO t(x) VALUES (?)", 42)
if err != nil { tx.Rollback(); return err }
return tx.Commit()
```

(DSN param names shown are for `mattn/go-sqlite3`; for `modernc.org/sqlite` use `_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)&_pragma=foreign_keys(on)&_txlock=immediate`.)

**Option B — issue `BEGIN IMMEDIATE` yourself:**

```go
if _, err := db.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil { return err }
if _, err := db.ExecContext(ctx, "INSERT INTO t(x) VALUES (?)", 42); err != nil {
    db.ExecContext(ctx, "ROLLBACK"); return err
}
_, err := db.ExecContext(ctx, "COMMIT")
return err
```

Option A is what I'd actually use — set the DSN once at startup and every `BeginTx` call afterward is correct by default.

The trap to avoid: `tx, _ := db.BeginTx(ctx, nil)` *without* `_txlock=immediate` in the DSN. It looks identical, it's one line shorter in setup, and it's the single most common source of `SQLITE_BUSY` errors in Go SQLite code.

</details>

---

### `offtopic-python-comprehension`

**Prompt**

```
What's the most idiomatic way to filter and transform a list in
Python using a single comprehension? Show me an example.
```

**Judge focus:** This question has nothing to do with SQLite. Both answers should be
essentially equivalent. Pick "tie" unless one is materially wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality, correctness, and idiomaticity. They cover the same core concepts (filter+transform syntax, realistic examples, generator alternative, when not to use comprehensions) with similar depth and clarity. Neither is materially better than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## Filtering and Transforming with List Comprehensions

The most idiomatic Python approach combines **filtering** (the `if` clause) and **transformation** (the expression) in a single comprehension.

### Basic Syntax
```python
[transform(item) for item in iterable if condition(item)]
```

### Practical Example
```python
# Raw sales data with some invalid entries
sales = [120, -15, 340, 0, 89, -5, 210, 450]

# Filter out invalid sales (≤ 0) and apply a 10% bonus in one comprehension
adjusted_sales = [sale * 1.10 for sale in sales if sale > 0]

print(adjusted_sales)
# [132.0, 374.0, 97.9, 231.00000000000003, 495.00000000000006]
```

### More Real-World Example
```python
users = [
    {"name": "alice", "age": 17, "active": True},
    {"name": "bob",   "age": 25, "active": False},
    {"name": "carol", "age": 30, "active": True},
    {"name": "dave",  "age": 15, "active": True},
]

# Get formatted names of active adult users
eligible = [
    user["name"].title()
    for user in users
    if user["active"] and user["age"] >= 18
]

print(eligible)  # ['Alice', 'Carol']
```

### Comparison with Alternatives
```python
words = ["hello", "world", "python", "hi", "code"]

# ✅ Idiomatic — list comprehension (preferred)
long_words = [w.upper() for w in words if len(w) > 4]

# ❌ Verbose — traditional loop
long_words = []
for w in words:
    if len(w) > 4:
        long_words.append(w.upper())

# ⚠️ Functional — works but less readable in Python
long_words = list(map(str.upper, filter(lambda w: len(w) > 4, words)))

print(long_words)  # ['HELLO', 'WORLD', 'PYTHON']
```

### Key Rules for Readability
| Situation | Recommendation |
|-----------|---------------|
| Simple filter + transform | Single-line comprehension ✅ |
| Complex logic | Extract to a function, call it in the comprehension |
| Multiple nested loops | Consider a regular loop for clarity |
| Large datasets | Use a **generator expression** `()` instead of `[]` |

```python
# For large datasets — generator is memory efficient
total = sum(sale * 1.10 for sale in sales if sale > 0)  # No list created
```

**The golden rule:** if you can't read it naturally in one glance, break it up.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## List Comprehensions in Python

The idiomatic pattern combines filtering and transformation in a single comprehension:

```python
[transform(item) for item in iterable if condition(item)]
```

### Example: Filter and Transform in One Pass

```python
# Raw data: mixed list of values
readings = [4, -1, 7, 0, -3, 12, 5, -8, 2]

# Keep only positive readings, then square them
result = [x ** 2 for x in readings if x > 0]

print(result)  # [16, 49, 144, 25, 4]
```

The three parts, left to right:
- **`x ** 2`** — transformation applied to each kept item
- **`for x in readings`** — iteration
- **`if x > 0`** — filter (items failing this are dropped entirely)

### A More Realistic Example

```python
users = [
    {"name": "alice", "age": 17},
    {"name": "bob",   "age": 23},
    {"name": "carol", "age": 15},
    {"name": "dave",  "age": 31},
]

# Adults only, with names title-cased
names = [u["name"].title() for u in users if u["age"] >= 18]

print(names)  # ['Bob', 'Dave']
```

### When to Use a Generator Instead

If you're passing the result directly to a function (like `sum`, `max`, or `join`) and don't need the full list in memory, swap the brackets for parentheses:

```python
total = sum(x ** 2 for x in readings if x > 0)  # No intermediate list built
```

### When *Not* to Use a Comprehension

| Situation | Better choice |
|---|---|
| Logic requires multiple statements | `for` loop with a regular `if` block |
| Transformation is complex | Extract a named function, then `map()` or a loop |
| Nested comprehensions exceed one level | Explicit `for` loops — readability wins |

The guiding principle from the Python docs: a comprehension should be **readable in one glance**. If you have to pause to parse it, a loop is clearer.

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer B is materially more useful and complete, providing multiple practical examples with clear explanations of why list comprehensions are idiomatic. Answer A, while technically correct, spends significant space deflecting the question by noting it's a 'SQLite skill' and redirecting to SQLite topics, which is unhelpful and slightly condescending given the question is straightforward Python.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| idiomatic | baseline |
| correct | tie |
| useful | baseline |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# List Comprehension for Filter + Transform

The most idiomatic way is a **list comprehension with a conditional**:

```python
# Basic syntax: [transform(x) for x in iterable if condition(x)]

numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Filter even numbers AND square them
result = [x**2 for x in numbers if x % 2 == 0]
print(result)  # [4, 16, 36, 64, 100]
```

## More Practical Examples

**Example 1: Clean and uppercase strings**
```python
words = ["hello", "WORLD", "python", "CODE"]

# Filter out short words and uppercase them
result = [word.upper() for word in words if len(word) > 4]
print(result)  # ['HELLO', 'WORLD', 'PYTHON']
```

**Example 2: Extract and convert data**
```python
data = [
    {"name": "Alice", "age": 25},
    {"name": "Bob", "age": 17},
    {"name": "Charlie", "age": 30},
]

# Get names of adults only
adults = [person["name"] for person in data if person["age"] >= 18]
print(adults)  # ['Alice', 'Charlie']
```

## Why This is Idiomatic

✅ **Readable** - Clear intent in one line  
✅ **Efficient** - Faster than `filter()` + `map()`  
✅ **Pythonic** - Preferred over functional approaches  
✅ **Concise** - No temporary variables needed  

This is the standard Python approach and what most developers expect to see.

</details>

<details><summary>haiku: skill-loaded answer</summary>

This question is about Python list comprehensions, not SQLite. I'm Claude with the SQLite skill, so I'm specialized in SQLite best practices, schema design, transactions, indexing, and Go client patterns.

For Python list comprehensions, you'd want to ask a general Python question or consult Python documentation. That said, the idiomatic pattern is:

```python
# Filter and transform in one comprehension
result = [transform(x) for x in iterable if condition(x)]
```

Example:
```python
# Get squares of even numbers
squares_of_evens = [x**2 for x in range(10) if x % 2 == 0]
# [0, 4, 16, 36, 64]
```

---

**If you have a SQLite question**, I'm here to help. For example:
- How to filter and transform rows in a query (use `SELECT` with `WHERE` and expressions)
- How to index a computed column for fast filtering (use a generated column + index)
- How to handle JSON filtering in SQLite (use `json_extract` or `->>` with a generated-column index)

What SQLite problem can I help you solve?

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are correct, idiomatic, and well-structured. They cover the same core concept with clear examples and similar advice about when not to use comprehensions. Neither is materially better than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

# Filtering and Transforming with List Comprehensions

The most idiomatic way is to combine the transformation expression with an `if` clause in a single list comprehension:

```python
[expression for item in iterable if condition]
```

## Example

Say you have a list of numbers and want to **square only the even ones**:

```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

squared_evens = [n**2 for n in numbers if n % 2 == 0]

print(squared_evens)
# [4, 16, 36, 64, 100]
```

## How to Read It

Think of it left-to-right as three parts:
1. **`n**2`** — what to do with each item (transform)
2. **`for n in numbers`** — where items come from (iterate)
3. **`if n % 2 == 0`** — which items to keep (filter)

## A More Realistic Example

Extracting and normalizing valid email addresses from user data:

```python
users = [
    {"name": "Alice", "email": "ALICE@example.com"},
    {"name": "Bob",   "email": None},
    {"name": "Carol", "email": "Carol@Example.COM"},
    {"name": "Dave",  "email": ""},
]

emails = [u["email"].lower() for u in users if u["email"]]

print(emails)
# ['alice@example.com', 'carol@example.com']
```

## When *Not* to Use One

If your comprehension starts wrapping across multiple lines with nested conditions, prefer a regular `for` loop or a generator function — readability beats cleverness. A good rule of thumb: if you can't say it out loud in one breath, break it up.

</details>

<details><summary>opus: skill-loaded answer</summary>

This question is about Python list comprehensions and isn't related to SQLite, so the skill loaded for this conversation doesn't apply. Here's a direct answer:

The idiomatic single-comprehension form combines a `for` clause with an `if` filter, transforming the kept elements with an expression on the left:

```python
[expr(x) for x in iterable if predicate(x)]
```

## Example

Say you have a list of orders and want the doubled totals of only the completed ones:

```python
orders = [
    {"id": 1, "total": 50, "status": "completed"},
    {"id": 2, "total": 30, "status": "pending"},
    {"id": 3, "total": 75, "status": "completed"},
    {"id": 4, "total": 20, "status": "cancelled"},
]

doubled_completed = [o["total"] * 2 for o in orders if o["status"] == "completed"]
# [100, 150]
```

Reading order: **filter** with the trailing `if`, then **transform** with the leading expression. Mentally it's "give me `expr(x)` for each `x` that passes `predicate(x)`."

## A few related idioms worth knowing

- **Generator expression** when you don't need the full list materialized (e.g., feeding `sum`, `any`, `max`):
  ```python
  total = sum(o["total"] for o in orders if o["status"] == "completed")
  ```
  Same syntax, parentheses instead of brackets, lazy evaluation.

- **Dict / set comprehensions** use the same shape:
  ```python
  {o["id"]: o["total"] for o in orders if o["status"] == "completed"}
  {o["status"] for o in orders}
  ```

- **Conditional expression on the left** (transform differs by condition, but you keep every element) — this is *not* filtering, it's a ternary inside the transform:
  ```python
  [o["total"] if o["status"] == "completed" else 0 for o in orders]
  ```
  Note the `if/else` is *before* the `for`, versus the filter `if` which comes *after*.

## When to break it up

If the predicate or the transform gets complex enough that the comprehension wraps onto three-plus lines or needs a comment to explain it, prefer a regular `for` loop or extract a helper function. Comprehensions are idiomatic when they read as a single thought; past that they hurt more than they help.

</details>

---
