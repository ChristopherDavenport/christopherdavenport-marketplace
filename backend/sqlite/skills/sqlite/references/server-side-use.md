# Server-Side Use

SQLite has quietly become a credible application database for production HTTP services. Litestream proved that continuous WAL streaming gives you durable backup with near-zero RPO. LiteFS and Turso libSQL added replication. Cloudflare D1 ships SQLite at the edge. The recipe — WAL, busy_timeout, two-pool, BEGIN IMMEDIATE — is settled. This reference covers when to choose SQLite for an application, how to set it up, which replication tool fits which situation, and how to migrate the schema while it's serving traffic.

## When SQLite *Is* the Right Application Database

- **Read-heavy services with one writer** — internal tools, dashboards, content sites, most B2B SaaS where the data is per-tenant and tenants don't overlap.
- **Single-machine deployments** — Fly.io single-node services, Hetzner boxes, Raspberry Pi devices, anything where "just one server" is the architecture.
- **Edge / serverless** — Cloudflare D1, Turso embedded replicas. SQLite is the only mainstream SQL database that runs in the same process as your handler.
- **Per-tenant or per-customer databases** — one SQLite file per tenant scales horizontally trivially. No shared state to coordinate.
- **Embedded analytics caches** — local cache of a remote dataset that you regenerate from upstream.
- **CI/test fixtures** — a SQLite file is a perfect deterministic, snapshot-able fixture.

The operational simplicity is the headline benefit. No server to provision, no network round-trip, no separate backup pipeline (Litestream is one binary), no version-skew between client and server.

## When It Isn't

- **Multi-writer workloads from many machines** — SQLite is single-writer. If multiple application instances need to write the same database concurrently, you need a coordination layer (LiteFS forwards writes to the primary; libSQL has primary-replica semantics). Past a certain write rate, just use Postgres.
- **Geo-distributed writes with low cross-region latency** — same. Reads can be local with embedded replicas; writes still go to the primary.
- **Large-blob workloads** — SQLite handles BLOBs but isn't optimized for them. Object storage + SQLite metadata is usually the right shape.
- **Sub-second standby failover** — Litestream/LiteFS recovery is fast but not "milliseconds-of-downtime" fast. If you need that, pay the operational cost of a real HA database.
- **Heavy concurrent OLAP** — DuckDB exists for a reason. SQLite's planner is simple; analytics queries on big tables are not where it shines.

## Production Setup Checklist

Every server-side SQLite deployment should have these in place before serving traffic:

1. **`journal_mode=WAL`** — set once on the file, persists.
2. **`synchronous=NORMAL`** — set per-connection via DSN.
3. **`foreign_keys=ON`** — set per-connection via DSN.
4. **`busy_timeout=5000`** — set per-connection via DSN.
5. **`cache_size=-64000`** (64 MiB) or larger if RAM allows.
6. **Two-pool writer/reader split** — writer with `SetMaxOpenConns(1)`, reader with `4×CPU` or so.
7. **`BEGIN IMMEDIATE` for writer transactions** — wrap in a helper.
8. **Periodic `PRAGMA wal_checkpoint(TRUNCATE)`** — once a minute on the writer pool, in a background goroutine.
9. **`PRAGMA optimize` on shutdown** — both pools.
10. **Backup mechanism wired up** — Litestream, scheduled `VACUUM INTO`, or both.
11. **`PRAGMA quick_check` on startup** — surface corruption early.
12. **Schema migration tool** — even hand-rolled, with the 12-step recipe baked in for unsupported `ALTER TABLE` ops.

See [pragmas-and-tuning.md](pragmas-and-tuning.md), [transactions-and-concurrency.md](transactions-and-concurrency.md), and [go-client.md](go-client.md) for the details on each.

## Backup Strategies

### Litestream (continuous, near-zero RPO)

Litestream runs alongside your application and streams WAL frames to S3 (or any S3-compatible object store) as they're written. On restore, it replays the WAL stream from the last full snapshot.

```yaml
# /etc/litestream.yml
dbs:
  - path: /var/data/app.db
    replicas:
      - type: s3
        bucket: my-backups
        path: app/db
        region: us-east-1
```

Wins:

- Continuous backup with seconds of RPO.
- Point-in-time restore.
- One small Go binary running as a sidecar.
- Doesn't require coordinating with the application.

Caveats:

- Restore-and-resume is single-threaded — for large DBs, the initial restore is slow.
- It's a backup tool, not a replication tool. Multiple writers across machines is not supported (use LiteFS for that).
- On crash, the last few WAL frames may be lost — Litestream syncs to S3 every few seconds, not synchronously.

### Scheduled `VACUUM INTO` snapshots

Lower-tech, lower-RPO. Periodically copy the database to a snapshot file, ship the snapshot somewhere durable.

```go
// Once per hour or whatever cadence
_, _ = writeDB.ExecContext(ctx, "VACUUM INTO ?", "/snapshots/app-"+ts+".db")
// Then upload the snapshot file
```

Wins: no extra process, simple, the snapshot is a regular SQLite file you can open with any tool.

Caveats: large gaps between snapshots = larger RPO; transferring large files is bandwidth-heavy compared to streaming WAL frames.

Often the right answer: Litestream for continuous backup, plus a daily `VACUUM INTO` to S3 as a checkpoint you can restore to without WAL replay.

### Online backup API

The C-level API (`sqlite3_backup_init`/`step`/`finish`) gives you page-level control. Useful if you need progress reporting on huge databases or if you're streaming to a non-file destination. See [go-client.md](go-client.md) for the Go pattern.

### What **not** to do

- **`cp app.db backup.db` while a writer is active.** You'll copy a torn file *and* miss the WAL. Even with no writer, you must include `app.db-wal` and `app.db-shm` to be safe.
- **`rsync` of the database directory mid-write.** Same problem. If you must use `rsync`, run a `wal_checkpoint(TRUNCATE)` first, then immediately stop writes for the duration of the copy.
- **Filesystem snapshots without a checkpoint.** ZFS / LVM / EBS snapshots are atomic at the block level, so the file isn't torn — but if there's WAL activity, the snapshot includes a partial WAL that may not replay cleanly.

## Replication Patterns

### Litestream — read from primary, replicate to S3 only

Single writer on one machine. S3 holds the durable copy. Reads come from the local file. **Not a replication tool for hot reads.**

### LiteFS — primary-replica via FUSE

LiteFS mounts a FUSE filesystem under your application; writes on a follower are forwarded to the primary; replication is page-level via the LiteFS protocol.

Use when:

- You want hot read replicas in multiple regions on Fly.io.
- You can tolerate write forwarding latency from followers to the primary.
- You're OK running LiteFS as a sidecar and giving up some operational simplicity.

### Turso libSQL — embedded replicas with sync

libSQL is a SQLite fork with a native replication protocol. The Turso platform offers managed primaries and embedded replicas (a SQLite file in your application's process that periodically syncs from the primary). Local reads are SQLite-fast; writes go to the primary over the network.

Use when:

- You want global low-latency reads without running LiteFS yourself.
- You're OK with a hosted primary (Turso) or willing to run libSQL primaries.
- You need explicit primary-replica semantics with conflict resolution.

### Cloudflare D1

SQLite-on-edge offering. Each D1 database is geographically pinned but reachable from any Worker. Limited featureset (no extensions, no custom functions), but operationally trivial.

Use when:

- You're already on Cloudflare Workers.
- Your data fits the D1 size limits and your queries fit the Workers CPU budget.

### Picking between them

| Need | Tool |
|---|---|
| Continuous backup, no replication | Litestream |
| Hot read replicas, single primary, Fly.io | LiteFS |
| Global low-latency reads, managed | Turso libSQL embedded replicas |
| Cloudflare Workers stack | D1 |
| Just one machine, no cross-region | Litestream + maybe scheduled `VACUUM INTO` |

## HTTP Request Handling Pattern

```go
// Read handler — no transaction, just query
func handleGet(w http.ResponseWriter, r *http.Request) {
    var name string
    err := readDB.QueryRowContext(r.Context(),
        "SELECT name FROM users WHERE id = ?", id).Scan(&name)
    // ...
}

// Write handler — BEGIN IMMEDIATE wrapper, short transaction, no external I/O inside
func handlePost(w http.ResponseWriter, r *http.Request) {
    err := WithTx(r.Context(), writeDB, func(tx *sql.Tx) error {
        if _, err := tx.ExecContext(r.Context(),
            "INSERT INTO ... (...) VALUES (...)"); err != nil {
            return err
        }
        // No HTTP calls, no slow CPU work, no waiting on the user.
        return nil
    })
    // ...
}
```

Two rules: **don't hold a write transaction across network or user input**, and **use the writer pool (one connection) for writes, the reader pool for reads**.

## Schema Migration on a Live Database

The schema is a single shared file. Migrations run while the application is serving traffic. Two principles:

1. **Use the writer pool** (`SetMaxOpenConns(1)`) for the migration. The migration is itself a write transaction; running it through the same one-connection pool naturally serializes it against application writers.
2. **Hold an `EXCLUSIVE` transaction** for the duration of any DDL that takes more than a few milliseconds. This blocks all readers and writers, but in WAL mode that's brief and cleaner than mid-migration races.

For supported `ALTER TABLE` operations (add column, rename column, drop column on 3.35+), the migration is a single `ALTER TABLE` and takes microseconds.

For unsupported operations, the [12-step recipe](schema-design.md#the-12-step-recipe) is the answer. Two adjustments for the live-database case:

- **Run it inside `BEGIN EXCLUSIVE`** — the entire recipe must be atomic. Any partial state is unrecoverable.
- **Validate FK invariants with `PRAGMA foreign_key_check`** before `COMMIT`. If invariants are violated, `ROLLBACK` and figure out the bad data.
- **For huge tables, the copy step (`INSERT INTO new SELECT * FROM old`) is the bottleneck.** It blocks readers and writers. Strategies for very large tables:
  - Migrate during a maintenance window with traffic stopped.
  - Use a progressive migration: add the new column nullable, backfill in chunks outside a transaction, then switch reads/writes over.
  - For genuinely huge SQLite databases, ask whether SQLite is still the right tool.

After the migration, **every connection in your pools needs to re-set `PRAGMA foreign_keys = ON`** — the migration toggled it off on the connection that did the work. Recycle your pools or restart the service.

## Sources

- https://www.sqlite.org/whentouse.html — when SQLite is appropriate
- https://litestream.io/ — Litestream docs
- https://fly.io/docs/litefs/ — LiteFS docs
- https://docs.turso.tech/ — Turso libSQL docs
- https://developers.cloudflare.com/d1/ — Cloudflare D1
- https://www.sqlite.org/backup.html — online backup API
- https://www.sqlite.org/lang_vacuum.html — `VACUUM INTO`
- https://www.sqlite.org/lang_altertable.html — `ALTER TABLE` and the 12-step recipe
