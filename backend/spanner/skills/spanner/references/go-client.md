# Go Client SDK — `cloud.google.com/go/spanner`

The Go client uses a session pool: every read or transaction borrows a session and must return it. The single most common production bug is a missing `defer` that pins a session forever, slowly draining the pool until requests time out. Discipline around `Close()` / `Stop()` and around pure transaction closures fixes 90% of issues.

## Client Lifecycle

Create one `*spanner.Client` per database, per process. Reuse it. Close on shutdown.

```go
package main

import (
    "context"
    "log"

    "cloud.google.com/go/spanner"
)

func main() {
    ctx := context.Background()
    client, err := spanner.NewClient(ctx, "projects/p/instances/i/databases/d")
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()  // returns sessions, blocks until pool drains

    // ... use client ...
}
```

Config the pool when defaults aren't right:

```go
client, err := spanner.NewClientWithConfig(ctx, db, spanner.ClientConfig{
    SessionPoolConfig: spanner.SessionPoolConfig{
        MinOpened:           10,
        MaxOpened:           400,
        TrackSessionHandles: true,  // dev/staging — surfaces leaks
    },
})
```

`MaxOpened` should match the concurrency you actually need. Spanner instances have per-database session quotas; oversized pools waste them.

## The Three Defers

These three lines prevent almost every session leak:

```go
defer client.Close()
defer iter.Stop()    // for any RowIterator
defer txn.Close()    // for any ReadOnlyTransaction
```

Forgetting any of them holds a session for the entire process lifetime.

## Reading: Single, ReadOnlyTransaction, ReadWriteTransaction

### Single read (one row or one query)

```go
row, err := client.Single().ReadRow(ctx,
    "Singers", spanner.Key{singerID}, []string{"FirstName", "LastName"})
if err != nil {
    if spanner.ErrCode(err) == codes.NotFound { /* handle */ }
    return err
}

var first, last string
if err := row.Columns(&first, &last); err != nil {
    return err
}
```

### Single query

```go
iter := client.Single().Query(ctx, spanner.Statement{
    SQL: "SELECT FirstName, LastName FROM Singers WHERE BirthYear = @year",
    Params: map[string]interface{}{"year": int64(1970)},
})
defer iter.Stop()  // CRITICAL

for {
    row, err := iter.Next()
    if err == iterator.Done { break }
    if err != nil { return err }
    // ...
}
```

Or use `iter.Do`, which calls `Stop` for you:

```go
err := client.Single().Query(ctx, stmt).Do(func(row *spanner.Row) error {
    // ...
    return nil
})
```

### ReadOnlyTransaction (multiple reads, same snapshot)

```go
ro := client.ReadOnlyTransaction()
defer ro.Close()  // CRITICAL

iter := ro.Query(ctx, stmt)
defer iter.Stop()
// ...
```

### ReadWriteTransaction (read-then-write)

```go
_, err := client.ReadWriteTransaction(ctx, func(ctx context.Context, txn *spanner.ReadWriteTransaction) error {
    row, err := txn.ReadRow(ctx, "Accounts", spanner.Key{accountID}, []string{"Balance"})
    if err != nil { return err }

    var balance int64
    if err := row.Column(0, &balance); err != nil { return err }
    if balance < amount {
        return errInsufficientFunds  // non-retryable; rolls back
    }

    return txn.BufferWrite([]*spanner.Mutation{
        spanner.Update("Accounts", []string{"AccountId", "Balance"},
            []interface{}{accountID, balance - amount}),
    })
})
```

The closure may run multiple times — see [transactions.md](transactions.md) for the purity requirement.

## Reading Row Values

Three styles, pick by what your code wants:

```go
// 1. Positional (fast, fragile to column reorders)
var name string
var age int64
err := row.Columns(&name, &age)

// 2. By name (resilient to ordering)
err := row.ColumnByName("FirstName", &name)

// 3. Into a struct (best for many columns)
type Singer struct {
    SingerId  int64  `spanner:"SingerId"`
    FirstName string `spanner:"FirstName"`
    LastName  string `spanner:"LastName"`
}
var s Singer
err := row.ToStruct(&s)
```

Struct tags must match the column name exactly. Without a tag, the field name is used (also case-sensitive).

## Nullable Columns

A NULL value into a `string` panics. Use `spanner.NullString`/`NullInt64`/`NullFloat64`/`NullBool`/`NullTime` etc.:

```go
type Singer struct {
    SingerId  int64
    NickName  spanner.NullString  // column may be NULL
}

if s.NickName.Valid {
    fmt.Println(s.NickName.StringVal)
} else {
    // NULL
}
```

For optional pointer fields, you can also use `*string` etc., but `Null*` types are the idiom.

## Writing: Mutations vs DML

### Blind writes — use mutations

```go
m := spanner.InsertOrUpdate("Singers",
    []string{"SingerId", "FirstName", "LastName"},
    []interface{}{1, "Marc", "Richards"})

_, err := client.Apply(ctx, []*spanner.Mutation{m})
```

`client.Apply` runs a one-shot transaction with these mutations. For writes inside a `ReadWriteTransaction`, use `txn.BufferWrite([]*spanner.Mutation{...})`.

Mutation constructors:

- `spanner.Insert` — fails if row exists.
- `spanner.Update` — fails if row missing.
- `spanner.InsertOrUpdate` — upsert.
- `spanner.Replace` — replaces all non-key columns; missing values become NULL.
- `spanner.Delete` — by key or key range.

### Conditional writes — use DML

```go
_, err := client.ReadWriteTransaction(ctx, func(ctx context.Context, txn *spanner.ReadWriteTransaction) error {
    n, err := txn.Update(ctx, spanner.Statement{
        SQL: "UPDATE Singers SET LastName = @new WHERE SingerId = @id",
        Params: map[string]interface{}{"new": newLast, "id": singerID},
    })
    if err != nil { return err }
    if n != 1 { return errNotFound }
    return nil
})
```

## Commit Timestamp

Spanner can write the actual commit timestamp into a column for you:

Schema:
```sql
ModificationTime TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true)
```

Go:
```go
m := spanner.InsertOrUpdate("Singers",
    []string{"SingerId", "FirstName", "ModificationTime"},
    []interface{}{1, "Marc", spanner.CommitTimestamp})
```

The literal `spanner.CommitTimestamp` is a sentinel — Spanner replaces it with the real commit time at commit. Don't put commit-timestamp columns in the leading PK position.

## Stale Reads

For latency-sensitive reads that don't need the absolute latest data:

```go
client.Single().
    WithTimestampBound(spanner.MaxStaleness(10 * time.Second)).
    Query(ctx, stmt)
```

`MaxStaleness(d)` lets any replica serve the read with data at most `d` old — no leader round-trip. Use for dashboards, recommendation feeds, search results, anywhere a few seconds of staleness is fine.

`ExactStaleness(d)` reads at exactly `now - d`, useful for analytics on a snapshot.

## Auto-Retry and Side-Effect Safety

`ReadWriteTransaction` automatically retries on `ABORTED` errors with exponential backoff. The closure may execute multiple times. **Do not** put inside the closure:

- `log.Print` (will log twice)
- HTTP calls, RPC calls to other services
- Mutations to in-process state (counters, channels, maps)
- Anything not idempotent

Defer side effects until after a successful return:

```go
ts, err := client.ReadWriteTransaction(ctx, func(...) error {
    // pure database work only
})
if err != nil { return err }
log.Printf("committed at %s", ts)  // safe — runs once
```

## Error Inspection

```go
import "google.golang.org/grpc/codes"

if spanner.ErrCode(err) == codes.NotFound { /* missing row */ }

desc := spanner.ErrDesc(err)
delay, ok := spanner.ExtractRetryDelay(err)  // retry-after for AlreadyExists, etc.

spannerErr := spanner.ToSpannerError(err)
```

Common codes:

| Code | Meaning | Common cause |
|---|---|---|
| `NotFound` | Row missing | Wrong key, deleted concurrently |
| `AlreadyExists` | Insert conflict | Concurrent insert; consider `InsertOrUpdate` |
| `FailedPrecondition` | Constraint or limit | NULL into NOT NULL, exceeded mutation limit, FK violation |
| `Aborted` | Transaction conflict | Auto-retried by `ReadWriteTransaction`; if you see it leaking, your closure is impure or too long |
| `DeadlineExceeded` | Context timeout | Either query too slow or timeout too tight |
| `ResourceExhausted` | Quota / pool | Session pool exhausted (often a leak), or instance CPU saturated |
| `Internal` | Server-side issue | Usually transient; safe to retry the operation |

## Detecting Session Leaks

In dev and staging, enable handle tracking:

```go
client, _ := spanner.NewClientWithConfig(ctx, db, spanner.ClientConfig{
    SessionPoolConfig: spanner.SessionPoolConfig{
        TrackSessionHandles: true,
        InactiveTransactionRemovalOptions: spanner.InactiveTransactionRemovalOptions{
            ActionOnInactiveTransaction: spanner.WarnAndClose,
        },
    },
})
```

Logs print stack traces of leaked sessions; `WarnAndClose` reclaims them after a timeout. Don't enable `WarnAndClose` blindly in production — closing an in-flight session aborts the transaction.

## Observability

OpenTelemetry metrics export by default in recent versions of the client. Key things to watch:

- `spanner/session_pool/sessions_in_use` vs `sessions_open` — pinned high → leak.
- `spanner/operation/latency` — tail latency tells you about contention.
- `spanner/aborted_transactions_total` — climbing → contention or slow transaction closures.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| Forgetting `defer iter.Stop()` | Session leak per query |
| Forgetting `defer txn.Close()` for `ReadOnlyTransaction` | Session leak per transaction |
| `log.Printf` inside `ReadWriteTransaction` closure | Double-logs on retry |
| Calling external APIs inside the closure | Double-side-effects on retry |
| Reading into `string` from a NULL-able column | Panic at runtime |
| Creating a new `*spanner.Client` per request | Session pool churn; latency spikes |
| Treating `ABORTED` as a fatal error | It's the normal contention signal; let `ReadWriteTransaction` retry it |
| Catching `ABORTED` and re-running manually | Loses jitter and backoff; usually wrong |

## Common Pitfalls

- **`iter.Do` doesn't propagate the loop body's return value.** If you return early, `Do` continues unless you return the error.
- **`row.Column(i, &x)` is positional and breaks on column reorder.** Prefer `ColumnByName` or `ToStruct`.
- **Struct field tags are case-sensitive and must match column names exactly.** A tag mismatch silently produces zero values.
- **`MaxOpened` too low under load.** New transactions wait; latency climbs. Tune to expected concurrency.
- **Holding a `ReadOnlyTransaction` open across a long-running goroutine.** Holds the session; close as soon as reads are done.
- **Returning an `*spanner.RowIterator` from a function.** Caller doesn't know to call `Stop`. Either consume inside the function with `Do`, or document the contract.

## Sources

- https://pkg.go.dev/cloud.google.com/go/spanner
- https://cloud.google.com/spanner/docs/transactions
- https://cloud.google.com/spanner/docs/dml-tasks
