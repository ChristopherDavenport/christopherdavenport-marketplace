# Pragmas & Tuning

`PRAGMA` is SQLite's runtime configuration knob. Some pragmas persist with the database file, others are per-connection and reset every time `database/sql` opens a new pool member. Knowing which is which is the difference between a setting that "took" and a setting that's silently ignored on every other connection.

## The Must-Set-On-Every-Connection List

Set these on every connection your code opens. In Go, that means in the DSN — see [go-client.md](go-client.md).

```sql
PRAGMA journal_mode = WAL;       -- persists with file; idempotent
PRAGMA synchronous  = NORMAL;    -- per-connection in WAL mode; safe + fast
PRAGMA foreign_keys = ON;        -- per-connection; off by default
PRAGMA busy_timeout = 5000;      -- per-connection; ms to wait on lock
PRAGMA cache_size   = -64000;    -- per-connection; -KB ⇒ 64 MiB
PRAGMA temp_store   = MEMORY;    -- per-connection
PRAGMA mmap_size    = 134217728; -- per-connection; 128 MiB
```

Persistence summary:

| Pragma | Persists? | Notes |
|---|---|---|
| `journal_mode` | Yes (with file) | Setting it is idempotent; safe to issue on every connect |
| `synchronous` | No | Defaults to `FULL`; set per connection |
| `foreign_keys` | No | Defaults to `OFF`; **set per connection** |
| `busy_timeout` | No | Defaults to `0` (no waiting); set per connection |
| `cache_size` | No | Per-connection page cache size |
| `temp_store` | No | Where temp tables/indexes live |
| `mmap_size` | No | Per-connection mmap window |

## `journal_mode`

How SQLite implements rollback and crash recovery.

| Mode | Behavior | When to use |
|---|---|---|
| `DELETE` | **Default.** Rollback journal file is created and deleted per transaction. Readers block writers and vice versa via file locks. | Never, in 2026. |
| `TRUNCATE` | Like `DELETE` but truncates instead of deleting the journal file. Marginally faster on filesystems where delete is expensive. | If you can't use WAL (e.g. read-only filesystem with shared write?). Rare. |
| `PERSIST` | Like `DELETE` but zeroes the journal header instead of deleting. | Niche embedded use. |
| `MEMORY` | Journal in RAM. **Crash = corruption.** | Throwaway in-memory or test databases only. |
| `WAL` | Write-ahead log in a sidecar file. Readers see a consistent snapshot, writers append; checkpoint folds WAL into the main file. **Concurrent reads + one writer.** | Default for any application that does concurrent access. |
| `OFF` | No rollback support. Crash = corruption. | Bulk-load tooling that you can re-run from scratch on failure. Never in production. |

Switching to WAL is a one-time change that persists with the file:

```sql
PRAGMA journal_mode = WAL;  -- returns 'wal' on success
```

WAL adds two sidecar files: `db-wal` (the log) and `db-shm` (shared memory index). They must travel together — copying just the `.db` file leaves you with stale data.

## `synchronous`

How aggressively SQLite waits for disk fsync.

| Value | Behavior | Safe? |
|---|---|---|
| `OFF` (`0`) | No syncing. OS decides. | **Power loss = corruption.** Never. |
| `NORMAL` (`1`) | Sync at WAL checkpoints. Tight crash window where the last few transactions could be lost on power loss but the database stays consistent. | **Yes — with `WAL`.** This is the recommended pairing. |
| `FULL` (`2`) | **Default.** Sync after every commit. Durable across power loss. | Yes. Slower than `NORMAL` for high write rates. |
| `EXTRA` (`3`) | `FULL` plus extra sync of the directory entry. | For paranoid durability requirements. Rarely needed. |

The standard production combo is `journal_mode=WAL` + `synchronous=NORMAL`. You can lose at most the last few committed transactions on a power-loss crash; the database itself never corrupts. If you cannot tolerate even that loss, use `FULL`.

## `foreign_keys`

Off by default. Per-connection. Foreign-key declarations parse without it but are not enforced.

```sql
PRAGMA foreign_keys = ON;   -- this connection only
PRAGMA foreign_keys;        -- check current value (returns 0 or 1)
```

In Go, this **must** be in the DSN. `db.Exec("PRAGMA foreign_keys = ON")` runs on whatever connection the pool happens to hand you, and the next connection won't have it set.

## `busy_timeout`

When SQLite encounters a lock it can't acquire, by default it returns `SQLITE_BUSY` immediately. With `busy_timeout=N`, it instead retries with exponential-ish backoff for up to N milliseconds before giving up.

```sql
PRAGMA busy_timeout = 5000;  -- 5 seconds
```

5000 ms is the standard. Tune higher only if you have intentionally long writer transactions (you probably shouldn't); lower causes spurious failures under normal contention.

`busy_timeout` is what makes WAL feel concurrent. Without it, two writers racing to upgrade to `RESERVED` will fight and one will fail; with it, the loser politely waits.

## `cache_size`

Page cache size. Per-connection.

```sql
PRAGMA cache_size = -64000;  -- 64 MiB (negative ⇒ kibibytes)
PRAGMA cache_size = 2000;    -- 2000 pages (positive ⇒ pages, page size from PRAGMA page_size)
```

The negative-KB form is more predictable since page size varies. For a typical service, 64–256 MiB per connection is reasonable; larger isn't usually worth it because the OS page cache covers the rest.

## `mmap_size`

Memory-map up to N bytes of the database file. Reads from the mmap region skip the page cache and avoid a syscall + memcpy. Per-connection.

```sql
PRAGMA mmap_size = 268435456;  -- 256 MiB
```

Trade-off: mmap competes with the OS page cache for RAM, so absurdly large values can hurt. 128–256 MiB is a reasonable starting point. Set to `0` to disable.

## `temp_store`

Where SQLite puts temporary tables and indexes (used internally by `ORDER BY`, `GROUP BY`, etc.).

```sql
PRAGMA temp_store = MEMORY;  -- 0=DEFAULT, 1=FILE, 2=MEMORY
```

`MEMORY` is fast and usually correct for application servers with adequate RAM. `FILE` (the default) is safer if memory is tight.

## `wal_autocheckpoint` and Manual Checkpoints

WAL accumulates frames until a checkpoint folds them back into the main database. By default, SQLite triggers an automatic checkpoint when the WAL hits ~1000 pages.

```sql
PRAGMA wal_autocheckpoint = 1000;  -- pages; 0 disables auto-checkpoint
```

Auto-checkpoints can be starved by continuous read load (a checkpoint cannot complete while any reader is still on a snapshot older than the checkpoint point). Symptoms: the `-wal` file grows without bound. Fix:

```sql
PRAGMA wal_checkpoint(TRUNCATE);  -- block until all readers finish, then truncate
PRAGMA wal_checkpoint(RESTART);   -- block until other writers finish, then restart WAL
PRAGMA wal_checkpoint(FULL);      -- checkpoint as much as possible without blocking new readers
PRAGMA wal_checkpoint(PASSIVE);   -- checkpoint what we can; default for auto
```

In a long-lived server, run `PRAGMA wal_checkpoint(TRUNCATE)` periodically (e.g. once a minute, in a background goroutine, on the writer connection) to keep the WAL bounded.

## `PRAGMA optimize`

Re-runs `ANALYZE` only on tables whose statistics have drifted enough to matter. Cheap when nothing's changed.

```sql
PRAGMA optimize;
```

The recommended pattern in long-running processes is to run it on every connection close. The driver doesn't do this automatically; wire it in your shutdown path or as a `Conn.Close` interceptor. See [go-client.md](go-client.md) for the Go pattern.

## `ANALYZE`

Computes index and column statistics into `sqlite_stat1`. The query planner uses these to pick join orders and index choices. Without statistics, the planner falls back to heuristics that are usually fine but occasionally wrong.

```sql
ANALYZE;                  -- whole DB
ANALYZE main.users;       -- one table
ANALYZE users.users_email_idx;  -- one index
```

Run after bulk loads. After that, `PRAGMA optimize` (which calls `ANALYZE` only where needed) is sufficient.

## `integrity_check` and `quick_check`

Diagnostic. Both scan the file for corruption.

```sql
PRAGMA integrity_check;     -- thorough; can take minutes on large DBs
PRAGMA quick_check;         -- skips some checks; much faster
```

Run `quick_check` on startup of any service that depends on a SQLite file you don't fully control (user uploads, external syncs). Run `integrity_check` after restoring from backup or recovering from a crash.

## `auto_vacuum`

Whether SQLite reclaims free pages automatically. Persists with the file. Set at file creation time — changing it later requires a `VACUUM`.

```sql
PRAGMA auto_vacuum = INCREMENTAL;  -- 0=NONE, 1=FULL, 2=INCREMENTAL
```

- `NONE` (default): free pages are reused but the file never shrinks. Run `VACUUM` manually to reclaim.
- `FULL`: the file shrinks at the end of every transaction that frees pages. Adds latency to every commit.
- `INCREMENTAL`: free pages are tracked but not released. Run `PRAGMA incremental_vacuum(N)` to release N pages on demand.

For most application databases, `INCREMENTAL` + a periodic `incremental_vacuum` (or `NONE` + occasional `VACUUM` during off-hours) is the right answer.

## `page_size`

The disk page size. Persists with the file. Set at file creation; changing later requires a `VACUUM`.

```sql
PRAGMA page_size = 4096;   -- match common filesystem block size
```

The default (4096) is correct for nearly everyone. Larger pages (8192, 16384, 32768, 65536) are worth considering for blob-heavy workloads where each row is many KB.

## Sources

- https://www.sqlite.org/pragma.html — full pragma reference
- https://www.sqlite.org/wal.html — WAL semantics, checkpoint mechanics
- https://www.sqlite.org/foreignkeys.html — `foreign_keys` enforcement
- https://www.sqlite.org/c3ref/busy_timeout.html — busy handler details
- https://www.sqlite.org/lang_analyze.html — `ANALYZE` and statistics
- https://www.sqlite.org/lang_vacuum.html — `VACUUM` and `auto_vacuum`
