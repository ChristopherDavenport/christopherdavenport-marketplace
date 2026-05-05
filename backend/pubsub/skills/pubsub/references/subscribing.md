# Subscribing — Receive, Flow Control, Ack/Nack Discipline

The subscriber side has one main entry point — `Subscription.Receive` — and a single tuning surface — `ReceiveSettings`. Get those two right and most production failures (OOM, redelivery storms, hung shutdown, "messages stuck") disappear. Get them wrong and the symptoms look like Pub/Sub bugs but are almost always misconfigured flow control or callback contract violations.

This reference covers the `Receive` contract, every `ReceiveSettings` field that matters, the lease-extension internals, and shutdown.

## The Receive Contract

```go
sub := client.Subscription("my-sub")

err := sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    // Do the work synchronously here.
    if err := process(ctx, m); err != nil {
        m.Nack()
        return
    }
    m.Ack()
})
```

Three rules govern this callback:

1. **Call `Ack()` or `Nack()` exactly once per message, before returning.** Never both, never neither. Forgetting causes redelivery after the lease expires; double-calling does nothing for `Ack` but is wasted work.
2. **Do the work synchronously inside the callback.** The SDK extends the lease only while the callback is running. Handing the message off to a background goroutine and returning means the lease stops extending — the message redelivers.
3. **`Receive` blocks until error or `ctx.Done()`.** Cancel the context to shut down cleanly. `Receive` returns `nil` on context cancellation (not an error).

Calling `Receive` twice concurrently on the same `*pubsub.Subscription` panics or returns an error. If you need parallel streams, get a second subscription handle (`client.Subscription("my-sub")` returns a fresh one).

## ReceiveSettings

Tune at the subscription handle:

```go
sub := client.Subscription("my-sub")
sub.ReceiveSettings = pubsub.ReceiveSettings{
    MaxOutstandingMessages: 100,
    MaxOutstandingBytes:    100 * 1024 * 1024,
    NumGoroutines:          10,
    MaxExtension:           60 * time.Minute,
    MaxExtensionPeriod:     0,                 // 0 = SDK default
    MinExtensionPeriod:     10 * time.Second,
    Synchronous:            false,             // false = StreamingPull (recommended)
}
```

| Setting | Default | Notes |
|---|---|---|
| `MaxOutstandingMessages` | 1000 | Cap on un-acked messages held by this subscriber. Lower for slow handlers or heavy messages |
| `MaxOutstandingBytes` | 1 GiB | Cap on un-acked total bytes. Lower for big messages or tight memory |
| `NumGoroutines` | 10 | Number of StreamingPull streams opened. More streams = higher throughput, higher memory |
| `MaxExtension` | 60 minutes | Maximum total time SDK will keep extending one message's lease. Set higher for long jobs |
| `MaxExtensionPeriod` | 0 (uncapped per extension) | Cap on a single lease-extension RPC's deadline. Useful for finer control over lease renewal cadence |
| `MinExtensionPeriod` | 0 (SDK chooses) | Floor on a single lease-extension RPC's deadline. Prevents over-aggressive renewal |
| `Synchronous` | false | When true, uses unary `Pull` instead of StreamingPull. Lower throughput; for testing or specific edge cases |

The two flow-control settings are the most important. They cap **per-`Receive`-call** outstanding work, not per-process. If you have 4 `Receive` calls (4 subscription handles) running, the cap is 4× what you set.

### Sizing Flow Control

A useful starting heuristic: `MaxOutstandingMessages = NumWorkers × 2`, where `NumWorkers` is your goroutine pool. This keeps every worker fed but doesn't let the queue grow unboundedly.

For `MaxOutstandingBytes`: a fraction of process memory you can afford to lose. If each message is 100 KiB and you can spare 1 GiB, that's ~10,000 messages — but the message count limit kicks in first.

If your handler is slow (>1s per message) and `MaxOutstandingMessages` is at its default of 1000, you'll have up to 1000 messages all extending leases simultaneously. The lease-extension RPCs aren't free; lower the cap.

### NumGoroutines

This controls the number of StreamingPull RPC streams the SDK opens. Each stream is one HTTP/2 stream plus background goroutines for ack/nack management.

- For low-throughput consumers (<100 msg/s): default 10 is fine.
- For high-throughput (>10k msg/s): raise to 50–100, but watch CPU overhead.
- Setting to 1 is a useful debugging tool — easier to reason about delivery order and goroutine state.

This is **not** the size of your worker pool — it's the size of the message-fetching pool. The callback is invoked from the SDK's internal scheduler, which is already concurrent.

## Ack and Nack

`m.Ack()` tells Pub/Sub the message is processed and won't be redelivered (modulo the at-least-once / exactly-once delivery semantics — see [delivery-guarantees.md](delivery-guarantees.md)).

`m.Nack()` tells Pub/Sub to redeliver immediately. The retry policy on the subscription controls subsequent backoff.

Patterns:

```go
func(ctx context.Context, m *pubsub.Message) {
    err := process(ctx, m)
    switch {
    case err == nil:
        m.Ack()
    case isPermanent(err):
        // Send to dead-letter via redelivery exhaustion, or write to a separate
        // sink and ack to drain the backlog.
        log.Printf("permanent failure for %s: %v", m.ID, err)
        m.Ack()  // or Nack to retry up to MaxDeliveryAttempts then DLT
    default:
        m.Nack()  // transient — let Pub/Sub redeliver with backoff
    }
}
```

The "ack on permanent failure" pattern works only when you have a separate sink for the failure (log, error topic, DLT entry). If you nack a permanently-failing message, you'll keep retrying it forever unless a dead-letter topic is configured.

### Ack on Exactly-Once Subscriptions

On EOD subscriptions, `Ack()` returns an `*AckResult`:

```go
ar := m.AckWithResult()
status, err := ar.Get(ctx)
if status == pubsub.AcknowledgeStatusSuccess {
    // permanent ack — safe to mark work done
} else {
    // ack lost (e.g., lease expired before ack RPC reached server)
    // message will redeliver; ensure idempotency
}
```

For at-least-once subscriptions, `m.Ack()` is fire-and-forget. EOD requires you to wait for the result if you want to know the ack reached the server.

## Lease Extension Internals

When the callback receives a message, the SDK starts a background goroutine that periodically calls `ModifyAckDeadline` to push the lease deadline into the future. The cadence is computed from message latency observed across the stream.

- Initial deadline: the subscription's `ackDeadlineSeconds` (default 10).
- Renewals: every ~half the deadline, the SDK extends.
- Cap: total extension stops at `MaxExtension` (default 60 min).
- After `MaxExtension`: lease is allowed to expire; message redelivers.

If the callback is still running at `MaxExtension`, you have two problems and one mitigation:

1. The work is genuinely too long for one message — split the unit of work or move to async (write to a state table, ack, run a separate worker).
2. The callback might have hung — add a timeout inside `process(ctx, m)`.
3. As a backstop, raise `MaxExtension` to match your worst-case processing time.

## Graceful Shutdown

```go
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

go func() {
    <-shutdownSignal
    cancel()  // tells Receive to drain and return
}()

err := sub.Receive(ctx, handler)
// Receive returned because ctx was cancelled. In-flight messages
// got their callbacks completed; un-Ack-ed ones will redeliver.
if err != nil && err != context.Canceled {
    log.Fatalf("receive failed: %v", err)
}
```

When `ctx` is cancelled, `Receive`:

1. Stops accepting new messages from the StreamingPull streams.
2. Waits for in-flight callbacks to complete (or for their contexts to time out).
3. Returns.

Messages whose callbacks are still running when the outer context is cancelled have their callback contexts cancelled too. Plan for this: long-running handlers should respect `ctx.Done()` and either finish quickly or `Nack` to allow redelivery.

## Synchronous vs StreamingPull

`ReceiveSettings.Synchronous = true` switches from StreamingPull (default) to unary `Pull` RPCs. Use this when:

- You're hitting StreamingPull-specific bugs in a particular environment.
- You want strict message-count batching (StreamingPull's flow control is more dynamic).
- You're testing with the emulator and StreamingPull misbehaves.

For nearly all production consumers, leave it false.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| Handing the message to a goroutine and returning from the callback | Lease stops extending → redelivery |
| Calling `Receive` twice on the same handle | Panics or errors |
| Forgetting `Ack`/`Nack` | Lease expires, message redelivers, "stuck" subscription |
| `Ack` then `Nack` (or vice versa) | Confuses local accounting; the second call is ignored |
| `MaxExtension = 24*time.Hour` "to be safe" | Stuck callbacks hold messages all day; redelivery never fires |
| Default `MaxOutstandingMessages` (1000) with multi-MB messages | OOM under burst |
| Restarting `Receive` in a tight loop on errors | Bombards Pub/Sub with stream creates; back off and retry |
| Doing all the work in the callback then a final `Ack` outside | Callback returns before `Ack` — message redelivers |
| Spawning a new `*pubsub.Client` per consumer | Wastes connections; one client per process is correct |

## Common Pitfalls

- **`Receive` returns `nil` on context cancellation, not `context.Canceled`.** Check both.
- **The callback's `ctx` is a child of `Receive`'s `ctx`.** When the outer is cancelled, the callback's `ctx` is cancelled too.
- **`Nack` is not always honored instantly.** Pub/Sub's retry policy backoff applies; if you want immediate redelivery, you can't get it.
- **Modifying `ReceiveSettings` after `Receive` is called has no effect.** Set them before the first `Receive`.
- **The SDK does not deduplicate redelivered messages for you.** Even with EOD, you must be idempotent (see [delivery-guarantees.md](delivery-guarantees.md)).
- **Long-tail latency in the callback skews lease extension.** A handful of slow messages drives the extension cadence for the whole stream — keep handler latency tight.
- **Synchronous=true with high `MaxOutstandingMessages`** can cause the unary `Pull` to return a giant batch all at once; throughput drops to the slowest handler in the batch.

## Sources

- https://cloud.google.com/pubsub/docs/pull
- https://cloud.google.com/pubsub/docs/lease-management
- https://cloud.google.com/pubsub/docs/exactly-once-delivery
- https://cloud.google.com/pubsub/docs/handling-failures
- https://pkg.go.dev/cloud.google.com/go/pubsub
