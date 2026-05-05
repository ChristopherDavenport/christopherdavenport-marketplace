# Transactions — Read-Only, Read-Write, and Partitioned DML

Spanner has three transaction types. Choosing the wrong one is one of the most common causes of bad latency, cascading aborts, and surprise outages. The rule of thumb: **start with the weakest type that satisfies the requirement** (read-only or stale read), and only escalate to a read-write transaction when the write logic genuinely depends on the read.

| Type | Locks | Aborts during execution? | Retry by client | Use for |
|---|---|---|---|---|
| Single read (`Single()`) | None | No | N/A | One-shot read, optionally stale |
| `ReadOnlyTransaction` | None | No | N/A | Multiple reads at the same timestamp |
| `ReadWriteTransaction` | Yes | Yes (`ABORTED`) | Yes (auto in Go) | Read-then-write where write depends on read |
| Partitioned DML | Yes (per partition) | Per-partition retry | Built-in | Bulk update/delete of millions of rows; idempotent only |

## ReadOnlyTransaction

Multiple reads, all at the same external-consistency timestamp. No locks, never aborts mid-execution.

```go
ctx := context.Background()
ro := client.ReadOnlyTransaction()
defer ro.Close()  // CRITICAL — leaks a session otherwise

iter := ro.Query(ctx, spanner.Statement{
    SQL: "SELECT SingerId, FirstName FROM Singers WHERE BirthYear = @year",
    Params: map[string]interface{}{"year": 1970},
})
defer iter.Stop()
for {
    row, err := iter.Next()
    if err == iterator.Done { break }
    if err != nil { return err }
    // process row
}
```

When to use:

- You need **multiple consistent reads** (two queries that should reflect the same logical instant).
- Read-heavy workloads — reads scale much higher than read-write.

Bounded staleness for lower latency / wider replica fan-out:

```go
ro := client.ReadOnlyTransaction().
    WithTimestampBound(spanner.MaxStaleness(10 * time.Second))
defer ro.Close()
```

## Single Read

Lightest weight; one read, no transaction needed:

```go
row, err := client.Single().ReadRow(ctx, "Singers", spanner.Key{1}, []string{"FirstName"})
```

For latency-sensitive paths, allow staleness:

```go
client.Single().
    WithTimestampBound(spanner.MaxStaleness(10 * time.Second)).
    Query(ctx, stmt)
```

`MaxStaleness(d)` gives the freshest data within `d` ago — any replica can serve it without a leader round-trip. For analytics on a slightly delayed snapshot, `ExactStaleness(d)` reads at exactly `now - d`.

## ReadWriteTransaction

The only transaction type that supports read-then-write atomicity. Use it when:

- The write you're about to do **depends on the value of the read** (transfer between accounts, conditional update, increment-and-set).
- You need locks to prevent concurrent modifications between read and write.

```go
_, err := client.ReadWriteTransaction(ctx, func(ctx context.Context, txn *spanner.ReadWriteTransaction) error {
    row, err := txn.ReadRow(ctx, "Accounts", spanner.Key{accountID}, []string{"Balance"})
    if err != nil { return err }

    var balance int64
    if err := row.Column(0, &balance); err != nil { return err }
    if balance < amount {
        return errInsufficientFunds  // returning a non-retryable error rolls back
    }

    return txn.BufferWrite([]*spanner.Mutation{
        spanner.Update("Accounts", []string{"AccountId", "Balance"},
            []interface{}{accountID, balance - amount}),
    })
})
```

### Critical Properties

1. **The closure may run multiple times.** The Go client automatically retries on `ABORTED`. Make the closure **pure** — no logging that double-fires, no API calls, no external mutation. If you must do a side effect, do it after `ReadWriteTransaction` returns successfully.
2. **Locks are held for the entire transaction.** Other transactions touching the same rows wait. Long transactions = lock contention = aborts elsewhere.
3. **Locks are at row + column granularity.** Two transactions writing different columns of the same row do *not* conflict.

### Lock Modes

- **Shared locks** on read columns.
- **Exclusive locks** on written columns.
- A read-then-write on the same row promotes from shared to exclusive — this is the most common abort cause when two transactions race.

Use `LockHint = LOCK_HINT_EXCLUSIVE` (or `txn.WithLockHint`) when you know the row will be updated, to acquire the exclusive lock on read and skip the upgrade phase.

## Partitioned DML

For bulk operations across millions of rows that **don't need transactional atomicity**:

```go
count, err := client.PartitionedUpdate(ctx, spanner.Statement{
    SQL: "UPDATE Users SET Status = 'inactive' WHERE LastSeen < @cutoff",
    Params: map[string]interface{}{
        "cutoff": time.Now().Add(-365 * 24 * time.Hour),
    },
})
```

Properties:

- Spanner partitions the work and runs each partition in its own internal transaction.
- **Statements must be idempotent** — Spanner may run a partition more than once on retry.
- Bypasses the 80,000-mutation / 100 MiB transaction limits.
- No atomicity across partitions; observers can see partially-applied state.
- Supported statements: `UPDATE` and `DELETE` only (no `INSERT`).
- The query must be a single statement on a single table; complex predicates may be rejected.

When **not** to use Partitioned DML:

- Logic depends on existing values (e.g., `SET balance = balance - 1`) — partitions can re-run, double-applying.
- You need atomicity (some other reader could see half the rows updated).
- The volume fits inside one transaction (use a regular `UPDATE` instead).

## Hard Limits

| Limit | Value | What hits it |
|---|---|---|
| Mutations per commit | 80,000 | Each modified column counts; secondary indexes count too |
| Commit request size | 100 MiB | Total wire size of all mutations |
| Interleave depth | 7 levels | Schema time; not a runtime limit |
| Concurrent sessions per client | Pool-configurable | Default 100; tune for high concurrency |
| Maximum statement size | 1 MiB | Long IN-lists or huge SQL |

Hitting the mutation limit raises a `BadUsage` (`FAILED_PRECONDITION`) error. Either split the work or move to Partitioned DML.

## Mutations vs DML

A `ReadWriteTransaction` accepts both forms of writes:

| | Mutations (`spanner.Insert`, `Update`, `Delete`, `InsertOrUpdate`) | DML (`UPDATE`/`INSERT`/`DELETE` SQL) |
|---|---|---|
| Speed (blind writes) | Faster — sent at commit only | Slower — round-trip per statement |
| Read-modify-write | No (mutations are blind) | Yes (`UPDATE T SET x = x + 1`) |
| Returns affected rows | Count via `RowCount` after commit | Yes |
| `THEN RETURN` / `RETURNING` | No | Yes |
| Counts toward mutation limit | Yes | Yes (post-execution) |

Rule: blind writes → mutations. Conditional updates / `RETURNING` → DML. Mix freely within one transaction.

## External Consistency

Spanner provides **external consistency** (the strongest level — beyond serializable). Concretely: if transaction T1 commits before T2 begins (in real time), every observer sees T1's effects before T2's. This is what makes Spanner usable for global ledgers and audit logs without explicit coordination.

You don't enable it; it's the default. The cost is the TrueTime commit-wait — a few milliseconds added to commit latency.

## Common Abort Causes and Fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ABORTED` rate climbs under load | Lock contention on a hot row | Shorten transactions; split the hot row across more rows; reduce concurrent writers |
| `ABORTED` after `ReadRow` then `Update` | Lock upgrade conflict | Use `LockHint = LOCK_HINT_EXCLUSIVE` on the read |
| `ABORTED` with very long stack of retries | Transaction is too slow / does too much | Move read-only work outside; remove API calls from inside the closure |
| `ABORTED` on a single-row write | Hot row hit by many writers | Re-shape data so writes spread across rows |
| Side effects (logs, emails) double-fire | Closure not pure | Move side effects outside `ReadWriteTransaction` (use the returned timestamp) |
| `Transaction X is no longer alive` | Held idle too long | Don't pause inside the closure; commit promptly |
| `FAILED_PRECONDITION: too many mutations` | >80K mutations | Split the work, or use Partitioned DML |

## Transaction Patterns

### Idempotent commit with a UUID

If your write must be retry-safe at the application level (e.g., HTTP request retries), generate a request UUID and store it as a deduplication marker in the same transaction:

```go
_, err := client.ReadWriteTransaction(ctx, func(ctx context.Context, txn *spanner.ReadWriteTransaction) error {
    _, err := txn.ReadRow(ctx, "ProcessedRequests", spanner.Key{requestUUID}, []string{"RequestId"})
    if err == nil {
        return nil  // already processed, skip
    }
    if spanner.ErrCode(err) != codes.NotFound {
        return err
    }
    return txn.BufferWrite([]*spanner.Mutation{
        spanner.Insert("ProcessedRequests", []string{"RequestId", "ProcessedAt"},
            []interface{}{requestUUID, spanner.CommitTimestamp}),
        // ... actual writes
    })
})
```

### Read-only, multiple consistent queries

```go
ro := client.ReadOnlyTransaction()
defer ro.Close()

users := query(ro, "SELECT * FROM Users WHERE Active")
groups := query(ro, "SELECT * FROM Groups")
// users and groups reflect the exact same database snapshot
```

### Bulk delete

```go
count, err := client.PartitionedUpdate(ctx, spanner.Statement{
    SQL: "DELETE FROM Sessions WHERE ExpiresAt < CURRENT_TIMESTAMP()",
})
```

## Anti-Patterns

| Pattern | Problem |
|---|---|
| Calling external APIs (Slack, billing) inside `ReadWriteTransaction` | Closure may retry → double-call |
| Using `ReadWriteTransaction` for read-only work | Wastes locks, blocks other writers, slower |
| Holding a transaction idle (waiting for user input) | Spanner can release locks and abort |
| Partitioned DML for non-idempotent statements | Re-applied work corrupts data |
| Catching `ABORTED` and re-running manually instead of letting `ReadWriteTransaction` handle it | Loses backoff and jitter; usually wrong |
| Setting tight client-side timeouts shorter than commit-wait | Spurious `Canceled` errors right at commit |

## Common Pitfalls

- **Logging inside the closure.** Logs double on retry. Defer logs until after the transaction returns successfully.
- **Counting iterations to "detect" retries.** The closure has no idea it's been retried; design for purity instead.
- **Using `Mutation` when you actually need read-modify-write.** Mutations are blind writes; they'll silently overwrite without seeing current state.
- **Mixing `Insert` with `InsertOrUpdate` carelessly.** `Insert` fails on conflict; `InsertOrUpdate` (upsert) silently overwrites — choose deliberately.
- **Forgetting Partitioned DML's idempotency requirement.** A retry can re-apply, so `SET x = x + 1` is unsafe; `SET status = 'inactive'` is fine.

## Sources

- https://cloud.google.com/spanner/docs/transactions
- https://cloud.google.com/spanner/docs/dml-tasks
- https://cloud.google.com/spanner/docs/sql-best-practices
