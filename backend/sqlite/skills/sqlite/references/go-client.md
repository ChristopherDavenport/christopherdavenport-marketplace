# Go Client — `database/sql` with `mattn/go-sqlite3` or `modernc.org/sqlite`

Go talks to SQLite through `database/sql` and a driver. Pick **one** driver per project and stick with it — mixing in the same binary leads to confusing test failures. Almost every production bug in Go-on-SQLite traces back to per-connection pragmas not being in the DSN, or a single `*sql.DB` trying to handle both writes and reads with default pool settings.

## Driver Choice

| | `mattn/go-sqlite3` | `modernc.org/sqlite` |
|---|---|---|
| Implementation | cgo wrapping the SQLite C library | Pure Go (translated from C) |
| Speed | Fastest; effectively native SQLite | ~10–25% slower on write-heavy workloads |
| Cross-compilation | Needs a C toolchain for the target | Trivial — just `GOOS=... go build` |
| Binary size | Smaller (links libsqlite3 dynamically if available) | Larger (embeds the translated runtime) |
| Maturity | Very mature, widely deployed | Mature, widely deployed |
| Featureset | Full SQLite, all extensions, custom functions via cgo | Full SQLite, custom functions via Go |
| Build hassle | `CGO_ENABLED=1`; cross-compile is annoying | Zero hassle |

**Pick `mattn` if** you want maximum performance and don't mind cgo. **Pick `modernc` if** you want pure-Go builds (Alpine images without a C toolchain, easy cross-compile, fewer build dependencies).

Both drivers register under different names:

```go
// mattn
import _ "github.com/mattn/go-sqlite3"
db, _ := sql.Open("sqlite3", dsn)

// modernc
import _ "modernc.org/sqlite"
db, _ := sql.Open("sqlite", dsn)
```

The driver names differ (`sqlite3` vs `sqlite`), and the DSN pragma syntax differs (below).

## DSN Pragma Syntax

Per-connection pragmas (`foreign_keys`, `busy_timeout`, `synchronous`, `cache_size`, etc.) **must** be in the DSN. Setting them with `db.Exec` after `sql.Open` only affects whichever connection the pool happens to hand you — every subsequent connection in the pool opens fresh without the pragma.

### `mattn/go-sqlite3`

`mattn` exposes a fixed set of pragmas through `_`-prefixed query parameters:

```go
dsn := "file:app.db?_journal_mode=WAL" +
       "&_synchronous=NORMAL" +
       "&_foreign_keys=ON" +
       "&_busy_timeout=5000" +
       "&_cache_size=-64000" +
       "&_temp_store=MEMORY"
db, err := sql.Open("sqlite3", dsn)
```

Common parameters: `_journal_mode`, `_synchronous`, `_foreign_keys`, `_busy_timeout`, `_cache_size`, `_temp_store`, `_locking_mode`, `_secure_delete`, `_recursive_triggers`. For pragmas not in the list, use `_pragma=name(value)` (newer versions support this generic syntax).

### `modernc.org/sqlite`

`modernc` uses a generic `_pragma=` parameter, repeatable:

```go
dsn := "file:app.db" +
       "?_pragma=journal_mode(WAL)" +
       "&_pragma=synchronous(NORMAL)" +
       "&_pragma=foreign_keys(ON)" +
       "&_pragma=busy_timeout(5000)" +
       "&_pragma=cache_size(-64000)" +
       "&_pragma=temp_store(MEMORY)"
db, err := sql.Open("sqlite", dsn)
```

Each `_pragma=name(value)` runs as `PRAGMA name = value` on connection init. Anything `PRAGMA` accepts works.

### URL-encoding

Both drivers parse the DSN as a URL. Spaces and special characters in pragma values must be encoded. Use `url.Values{}` if you build it programmatically:

```go
v := url.Values{}
v.Set("_pragma", "journal_mode(WAL)")
v.Add("_pragma", "busy_timeout(5000)")
dsn := "file:app.db?" + v.Encode()
```

## The Two-Pool Pattern

```go
package storage

import (
    "database/sql"
    "runtime"

    _ "modernc.org/sqlite"
)

func Open(path string) (writeDB, readDB *sql.DB, err error) {
    base := "file:" + path +
        "?_pragma=journal_mode(WAL)" +
        "&_pragma=synchronous(NORMAL)" +
        "&_pragma=foreign_keys(ON)" +
        "&_pragma=busy_timeout(5000)" +
        "&_pragma=cache_size(-64000)" +
        "&_pragma=temp_store(MEMORY)"

    writeDB, err = sql.Open("sqlite", base)
    if err != nil { return nil, nil, err }
    writeDB.SetMaxOpenConns(1)            // serialize writers in Go
    writeDB.SetMaxIdleConns(1)
    writeDB.SetConnMaxLifetime(0)         // never recycle the writer

    readDB, err = sql.Open("sqlite", base)
    if err != nil { writeDB.Close(); return nil, nil, err }
    readDB.SetMaxOpenConns(runtime.NumCPU() * 4)
    readDB.SetMaxIdleConns(runtime.NumCPU())
    readDB.SetConnMaxLifetime(0)

    return writeDB, readDB, nil
}
```

Why two pools:

- The writer pool's `SetMaxOpenConns(1)` queues writers in Go's mutex, **before** they hit SQLite. Eliminates writer-vs-writer `SQLITE_BUSY`.
- The reader pool can be wide; readers don't block each other in WAL mode.
- The busy handler still covers reader-vs-checkpoint and the brief writer-vs-checkpoint windows.

`SetConnMaxLifetime(0)` keeps connections alive forever. Recycling connections has a hidden cost in SQLite: the new connection has to re-set its per-connection pragmas. The DSN does this automatically, so you never get a connection without `foreign_keys=ON`, but each open has a small startup cost.

## `BEGIN IMMEDIATE` in `database/sql`

`database/sql`'s `BeginTx(ctx, opts)` issues a plain `BEGIN`, which is `DEFERRED`. For writers, you want `IMMEDIATE`. The cleanest pattern: a helper that grabs a connection and runs raw `BEGIN IMMEDIATE`:

```go
func WithTx(ctx context.Context, db *sql.DB, fn func(*sql.Tx) error) error {
    conn, err := db.Conn(ctx)
    if err != nil { return err }
    defer conn.Close()

    if _, err := conn.ExecContext(ctx, "BEGIN IMMEDIATE"); err != nil {
        return err
    }

    tx, err := conn.BeginTx(ctx, nil)  // attaches a Tx to the existing transaction
    if err != nil {
        _, _ = conn.ExecContext(ctx, "ROLLBACK")
        return err
    }

    if err := fn(tx); err != nil {
        _ = tx.Rollback()
        return err
    }
    return tx.Commit()
}
```

The trick is that `BEGIN IMMEDIATE` puts the connection in a transaction, and the subsequent `BeginTx` then operates on it. Some teams skip the `Tx` entirely and just use the `conn` directly with explicit `COMMIT`/`ROLLBACK` — also fine, just remember to do the rollback on error.

For read-only queries, `db.QueryContext` directly is fine — no need for an explicit transaction unless you specifically want a consistent snapshot across multiple statements.

## Context Cancellation

Both drivers wire `ctx.Done()` to SQLite's interrupt mechanism. A long-running query whose context is cancelled returns promptly with an error. This is implemented via `sqlite3_progress_handler` (called every N VM instructions) — it's reliable for queries that touch many rows but may have a short delay for queries blocked on I/O.

```go
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
rows, err := db.QueryContext(ctx, "SELECT ... FROM huge_table")
```

The cancellation error from both drivers wraps `sqlite3.SQLITE_INTERRUPT` (or `sqlite.SQLITE_INTERRUPT` for modernc). It's not always `context.Canceled` — check with the driver-specific error code if you need to distinguish.

## `NULL` Handling

Scanning `NULL` into a non-pointer Go type fails:

```go
var name string
err := row.Scan(&name)  // panics if the row is NULL
```

Use either pointer types or `database/sql.Null*`:

```go
var name *string                    // nil if NULL
var name2 sql.NullString            // .Valid + .String
var n   sql.NullInt64               // .Valid + .Int64
var t   sql.NullTime                // .Valid + .Time
```

Pointers are usually nicer to work with downstream. `sql.Null*` is more explicit about intent and works better when scanning into structs from libraries that need to distinguish "absent" from "zero".

For typed JSON-like columns, you can implement `sql.Scanner` and `driver.Valuer` on your own type to scan and serialize transparently:

```go
type Tags []string

func (t *Tags) Scan(src any) error {
    if src == nil { *t = nil; return nil }
    b, ok := src.([]byte)
    if !ok { return fmt.Errorf("tags: expected []byte, got %T", src) }
    return json.Unmarshal(b, t)
}

func (t Tags) Value() (driver.Value, error) {
    return json.Marshal(t)
}
```

## Prepared Statements

`db.Prepare` returns a `*sql.Stmt` that is per-pool, not per-connection. Internally `database/sql` re-prepares it on each connection as needed. The driver caches by SQL text, so re-using the same query string across calls is automatic.

For hot paths, prepare once and reuse:

```go
stmt, err := db.PrepareContext(ctx, "SELECT name FROM users WHERE id = ?")
if err != nil { return err }
defer stmt.Close()

for _, id := range ids {
    var name string
    if err := stmt.QueryRowContext(ctx, id).Scan(&name); err != nil { return err }
    // ...
}
```

Always `defer stmt.Close()` for long-lived statements in a long-running process.

## `VACUUM INTO` and Backup from Go

The simplest backup is `VACUUM INTO`:

```go
_, err := db.ExecContext(ctx, "VACUUM INTO ?", "/path/to/snapshot.db")
```

This runs against the writer pool, takes a brief lock, and produces a clean copy. Safe with concurrent readers; brief contention with concurrent writers.

For more control, both drivers expose the online backup API through a driver-specific `Conn.Raw` callback. The pattern (modernc shown):

```go
import "modernc.org/sqlite"

dst, _ := sql.Open("sqlite", "file:backup.db")
dstConn, _ := dst.Conn(ctx)
defer dstConn.Close()

srcConn, _ := db.Conn(ctx)
defer srcConn.Close()

err := dstConn.Raw(func(dstRaw any) error {
    return srcConn.Raw(func(srcRaw any) error {
        sqlDst := dstRaw.(*sqlite.Conn)
        sqlSrc := srcRaw.(*sqlite.Conn)
        // call sqlite3_backup_init / step / finish via the driver's helpers
        _ = sqlDst; _ = sqlSrc
        return nil
    })
})
```

For most use cases `VACUUM INTO` is enough and far simpler. Reach for the online backup API only when you need page-level progress (e.g. for huge databases) or when you're streaming to a non-file destination.

## `PRAGMA optimize` on Shutdown

In a long-running service, run `PRAGMA optimize` before shutting down each pool:

```go
func Close(writeDB, readDB *sql.DB) error {
    _, _ = writeDB.Exec("PRAGMA optimize")
    if err := writeDB.Close(); err != nil { return err }
    _, _ = readDB.Exec("PRAGMA optimize")
    return readDB.Close()
}
```

Cheap when stats are fresh; valuable when they're stale. Doesn't hurt either way.

## Common Mistakes

- **Setting pragmas with `db.Exec` after `sql.Open`** — only affects one pool member. Pragmas belong in the DSN.
- **One pool for both reads and writes with high concurrency** — every read can collide with the writer's brief upgrade window. Split into two pools.
- **`db.BeginTx` without thinking about begin mode** — that's `BEGIN DEFERRED`. For writers, use the `WithTx` helper above.
- **Scanning `NULL` into a `string`** — runtime error. Use `*string` or `sql.NullString`.
- **Forgetting `defer rows.Close()`** — on a long-running query, this leaks the connection until the GC eventually runs. `defer rows.Close()` is mandatory after `db.Query`.
- **Mixing `mattn` and `modernc` in the same binary** — different driver names, different pragma syntaxes, very confusing test failures. Pick one.

## Sources

- https://pkg.go.dev/database/sql — `database/sql` reference
- https://github.com/mattn/go-sqlite3 — `mattn` driver, DSN parameters
- https://pkg.go.dev/modernc.org/sqlite — `modernc` driver
- https://www.sqlite.org/c3ref/interrupt.html — interrupt mechanism
- https://www.sqlite.org/backup.html — online backup API
- https://www.sqlite.org/lang_vacuum.html — `VACUUM INTO`
