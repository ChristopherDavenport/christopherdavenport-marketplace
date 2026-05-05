# Transactions & Concurrency

SQLite is single-writer. Always has been. WAL doesn't change that — it changes how readers and writers interact with each other while there's at most one writer holding the database. Most production SQLite trouble traces back to two writers fighting for the database, a busy handler that isn't tuned, or a `BEGIN DEFERRED` upgrading to `RESERVED` mid-transaction and losing the race.

## The Locking Model (rollback journal mode)

Five lock states, acquired in order:

| Lock | Held by | Blocks |
|---|---|---|
| `UNLOCKED` | Nobody | Nothing |
| `SHARED` | Each reader | Writers acquiring `EXCLUSIVE` |
| `RESERVED` | One writer (writes pending) | Other writers acquiring `RESERVED`/`EXCLUSIVE`; allows new `SHARED` |
| `PENDING` | One writer (about to commit) | New `SHARED` acquisitions; existing readers can finish |
| `EXCLUSIVE` | One writer (committing) | All other access |

In `journal_mode=DELETE` (the default), the writer escalates `SHARED → RESERVED → PENDING → EXCLUSIVE`, and during `EXCLUSIVE` no readers can be active. This is why classic SQLite is slow under concurrency: every commit briefly locks out every reader.

## How WAL Changes It

In `journal_mode=WAL`, writes go to a separate log file. The main database isn't modified during a transaction, so:

- **Readers don't block writers.** Readers see a snapshot from the moment they began; the writer can append new frames without disturbing them.
- **Writers don't block readers.** Same reason.
- **Writers still block writers.** Only one writer at a time. SQLite serializes them.

The `EXCLUSIVE` lock only appears briefly during checkpoints (and even then, in `PASSIVE` mode, it's short and non-blocking for new readers).

This is the main reason any production application server should use WAL. The cost is the `-wal` and `-shm` sidecar files (which means backup tools have to know about them — see [server-side-use.md](server-side-use.md)).

## `BEGIN` Modes

SQLite has three transaction begin modes. The choice has direct production consequences.

### `BEGIN DEFERRED` (default)

```sql
BEGIN;            -- same as BEGIN DEFERRED
-- ... reads ...
INSERT INTO ...;  -- THIS is when SQLite tries to acquire RESERVED
COMMIT;
```

The transaction starts in `SHARED` mode. The first time you write, it tries to upgrade to `RESERVED`. **If another writer already holds `RESERVED`, you get `SQLITE_BUSY` mid-transaction**, after you've already done some work. The busy handler kicks in only at this upgrade point — and if it eventually fails, you've wasted the work.

This is the source of most "random `SQLITE_BUSY`" reports.

### `BEGIN IMMEDIATE`

```sql
BEGIN IMMEDIATE;  -- acquires RESERVED right now
-- ... reads and writes ...
COMMIT;
```

Acquires `RESERVED` immediately. If another writer has it, the busy handler waits at the *start* of the transaction. Your transaction either gets the lock and proceeds without further contention, or it fails up-front before doing any work.

**Use `BEGIN IMMEDIATE` for any transaction that will write.** This is non-negotiable in any concurrent application.

### `BEGIN EXCLUSIVE`

```sql
BEGIN EXCLUSIVE;  -- acquires EXCLUSIVE right now
-- ... ...
COMMIT;
```

Acquires `EXCLUSIVE`. Blocks all other access (readers and writers). In WAL mode, the practical effect is the same as `IMMEDIATE` for most workloads — the only difference is that `EXCLUSIVE` prevents new readers from starting transactions during the txn.

Almost never needed. Reach for it for schema migrations or other operations where you genuinely want exclusive access.

### `database/sql` and `BEGIN IMMEDIATE`

`database/sql` does not let you specify the begin mode through `TxOptions`. The driver translates `BeginTx` into a plain `BEGIN`, which is `DEFERRED`. To get `IMMEDIATE`, you have two choices:

1. Set `TxOptions{ReadOnly: true}` for read-only transactions (driver-specific behavior — `mattn/go-sqlite3` issues `BEGIN` and treats writes as errors; `modernc.org/sqlite` similar).
2. For writers, get a raw connection and run `BEGIN IMMEDIATE` yourself:

```go
conn, err := db.Conn(ctx)
if err != nil { return err }
defer conn.Close()

if _, err := conn.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil { return err }
defer conn.ExecContext(ctx, "ROLLBACK")  // safe no-op after COMMIT

// ... do work on conn ...

_, err = conn.ExecContext(ctx, "COMMIT")
```

See [go-client.md](go-client.md) for a wrapper helper.

## `busy_timeout` and the Busy Handler

When SQLite encounters a lock it can't acquire, the **busy handler** decides whether to wait or return `SQLITE_BUSY`. The default busy handler returns `SQLITE_BUSY` immediately. With `PRAGMA busy_timeout = N`, SQLite installs a built-in handler that backs off and retries for up to N milliseconds.

```sql
PRAGMA busy_timeout = 5000;  -- 5 seconds
```

Tuning notes:

- **5000 ms is the standard.** Long enough to absorb checkpoint pauses and brief writer contention; short enough to surface real deadlocks.
- **Going below 1000 ms** causes spurious failures during normal checkpoint or writer-handoff windows.
- **Going above ~30000 ms** masks real deadlocks and turns them into hung requests.
- The busy handler **does not** retry inside a `BEGIN IMMEDIATE` waiting for `RESERVED` — that's the same mechanism but the wait happens up-front instead of mid-transaction.

## `SQLITE_BUSY` vs `SQLITE_LOCKED` vs `SQLITE_BUSY_SNAPSHOT`

| Code | Cause | Recovery |
|---|---|---|
| `SQLITE_BUSY` (5) | Couldn't acquire a lock — another connection has it | Retry the whole transaction. Usually with the busy handler doing it for you. |
| `SQLITE_LOCKED` (6) | Couldn't acquire a lock from **the same connection** (e.g. stepping a query while another statement on the same connection holds a write) | Bug — close the conflicting statement first. Not retryable. |
| `SQLITE_BUSY_SNAPSHOT` (517) | WAL-only: writer's commit would invalidate this connection's read snapshot | Roll back, retry. The busy handler does **not** help here — it's a snapshot conflict, not a lock conflict. |

For `SQLITE_BUSY_SNAPSHOT`, the recovery is application-level: catch it, roll back, restart the transaction. Both Go drivers surface this as a regular error; check the error code with `errors.Is` or by inspecting the driver-specific error type (see [go-client.md](go-client.md)).

## The Two-Pool Pattern

In WAL mode with `database/sql`, the cleanest architecture is two `*sql.DB` instances against the same file:

```go
// Writer pool: one connection, serializes all writes
writeDB, _ := sql.Open("sqlite3", dsn)
writeDB.SetMaxOpenConns(1)

// Reader pool: many connections, reads in parallel
readDB, _ := sql.Open("sqlite3", dsn)
readDB.SetMaxOpenConns(runtime.NumCPU() * 4)
```

Why this works:

- The writer pool's `SetMaxOpenConns(1)` means **the application** serializes writers, before they hit SQLite. No `SQLITE_BUSY` between writers — they queue at the Go level.
- The reader pool can be as wide as you want; readers in WAL mode don't conflict with each other.
- The busy handler still covers brief writer-vs-checkpoint moments and reader snapshot windows.
- `BEGIN IMMEDIATE` on the writer pool is now optional (the pool already serializes), but still good practice for clarity.

This is the pattern used by Litestream, Litestream-aware applications, and most production Go-on-SQLite services.

## Checkpoint Mechanics

The WAL is a log of frames. A checkpoint folds those frames back into the main database file. Modes:

| Mode | Behavior |
|---|---|
| `PASSIVE` | Default for auto-checkpoint. Folds what it can without blocking new readers; stops when it would have to wait. |
| `FULL` | Folds all frames it can without forcing readers off their snapshot. |
| `RESTART` | Like `FULL`, then waits for other writers to finish so the next writer can start at WAL frame 0. |
| `TRUNCATE` | Like `RESTART`, then truncates the WAL file to zero bytes. |

Auto-checkpoint runs in `PASSIVE` mode whenever the WAL grows past `wal_autocheckpoint` pages (default 1000). Under continuous read load, `PASSIVE` checkpoints can be starved indefinitely — readers stuck on old snapshots prevent the checkpoint point from advancing, and the WAL grows unboundedly.

The fix is a periodic explicit checkpoint on the writer connection:

```go
// Background goroutine on the writer pool
ticker := time.NewTicker(time.Minute)
for range ticker.C {
    _, _ = writeDB.Exec("PRAGMA wal_checkpoint(TRUNCATE)")
}
```

`TRUNCATE` blocks until all current readers finish, then reclaims the WAL file. On a healthy system that's milliseconds. On a system with a long-running reader, it'll wait — which is the correct behavior; it tells you the reader is the problem.

## Transaction Discipline

- **Never hold a transaction across user input or external network I/O.** Open the transaction, do your work, commit. The longer a writer holds `RESERVED`, the more readers get queued behind it.
- **Don't put long CPU work inside a writer transaction.** Same reason. Compute outside, write quickly.
- **Don't open nested transactions** unless you specifically want savepoints. SQLite supports `SAVEPOINT name` / `RELEASE name` / `ROLLBACK TO name` for nested rollback, but `BEGIN` inside a `BEGIN` is an error.
- **Read-only work belongs in a read-only transaction** (or no transaction at all). It's served from the WAL snapshot, holds no `RESERVED`, and never blocks writes.

## Sources

- https://www.sqlite.org/lockingv3.html — locking model
- https://www.sqlite.org/wal.html — WAL semantics
- https://www.sqlite.org/lang_transaction.html — `BEGIN` modes
- https://www.sqlite.org/c3ref/busy_handler.html — busy handler
- https://www.sqlite.org/rescode.html — error codes
- https://www.sqlite.org/lang_savepoint.html — savepoints
