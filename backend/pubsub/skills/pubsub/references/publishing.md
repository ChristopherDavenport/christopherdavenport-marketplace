# Publishing — Batching, Flow Control, Ordering Keys

The Go publisher batches messages in memory and flushes them either when a batch threshold is hit or when `Topic.Stop()` is called. The defaults are tuned for low-latency service traffic, not high-throughput pipelines — most "publish is slow" reports trace back to either un-tuned batch settings, synchronous `PublishResult.Get()` calls that defeat batching, or ordering keys applied where they're not needed.

This reference covers `PublishSettings`, the `Publish` → `PublishResult.Get` lifecycle, ordering-key semantics, and shutdown discipline.

## The Publish Lifecycle

```go
topic := client.Topic("my-topic")

result := topic.Publish(ctx, &pubsub.Message{
    Data: []byte(`{"orderId": 42}`),
    Attributes: map[string]string{
        "region": "us",
        "type":   "order.created",
    },
})

// Get blocks until the publish completes (success or error).
id, err := result.Get(ctx)
if err != nil {
    return err
}
log.Printf("published %s", id)
```

Three things are happening:

1. `Publish` enqueues the message into an in-memory batch keyed by `(orderingKey, batch slot)`. It returns immediately with a `*PublishResult`.
2. A background goroutine flushes the batch when any threshold is hit (`CountThreshold`, `ByteThreshold`, `DelayThreshold`) — or when `Topic.Stop()` is called.
3. `PublishResult.Get(ctx)` blocks until the flush RPC returns and reports success/failure for that specific message.

If you call `Get` synchronously after every `Publish` you defeat batching — each message becomes its own RPC. The right pattern is to fan out:

```go
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, m := range messages {
    results = append(results, topic.Publish(ctx, m))
}
for _, r := range results {
    if _, err := r.Get(ctx); err != nil {
        return err
    }
}
```

Or use a worker goroutine that drains a channel of `*PublishResult` and logs/handles errors asynchronously.

## PublishSettings

Tune at topic-handle creation:

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    CountThreshold:   1000,                  // flush when 1000 msgs accumulate
    ByteThreshold:    5 * 1024 * 1024,       // or when batch reaches 5 MiB
    DelayThreshold:   100 * time.Millisecond,// or 100ms after first message
    BufferedByteLimit: 100 * 1024 * 1024,    // total in-flight per topic before Publish blocks
    Timeout:          60 * time.Second,      // RPC timeout per batch
    NumGoroutines:    runtime.GOMAXPROCS(0), // batch workers
    FlowControlSettings: pubsub.FlowControlSettings{
        MaxOutstandingMessages: 10000,
        MaxOutstandingBytes:    100 * 1024 * 1024,
        LimitExceededBehavior:  pubsub.FlowControlBlock,
    },
}
```

| Setting | Default | When to raise | When to lower |
|---|---|---|---|
| `CountThreshold` | 100 | High-volume publishers (>1k msg/s) | Latency-sensitive (<100/s) — keep low to flush sooner |
| `ByteThreshold` | 1 MiB | Large messages or large batches | Tight memory budget |
| `DelayThreshold` | 10 ms | High-volume — 50–100ms amortizes RPC | Already low |
| `BufferedByteLimit` | 10 MiB | High burst publishers; otherwise `Publish` blocks | Tight memory budget |
| `Timeout` | 60s | Rare; very large batches in slow regions | Aggressive failure detection |
| `NumGoroutines` | `GOMAXPROCS` | Many concurrent topics | Single-topic workloads — defaults are fine |

The 1 MiB Pub/Sub message size limit applies to a single message — your `ByteThreshold` is about batch size, not individual message size. A single 10 MiB message is rejected regardless of batch settings.

### Sanity-Check Quota Before Tuning Batches

Before raising `CountThreshold` or `ByteThreshold` in pursuit of throughput, confirm you are not already against your project's per-region publish quota. A quota wall is indistinguishable from an under-tuned publisher in subscriber-side metrics — both look like "messages aren't arriving fast enough" — but raising batch thresholds against a quota ceiling does nothing. Check with:

```sh
gcloud quotas list --service=pubsub.googleapis.com --consumer=projects/YOUR_PROJECT
```

If the quota is the binding constraint, request an increase via the Cloud Console quotas page rather than changing client-side knobs. The error code that confirms quota exhaustion is `RESOURCE_EXHAUSTED` — see the error table later in this file.

### Payload Size and Compression

Per-message size is its own throughput lever, distinct from batch tuning. Two effects:

1. **Smaller messages → more per batch.** `CountThreshold` caps message count and `ByteThreshold` caps batch bytes; whichever fires first flushes. Halving payload size lets `ByteThreshold` accommodate roughly twice as many messages before flush, amortizing RPC overhead better.
2. **Smaller messages → less network bandwidth.** Throughput in messages/sec is bounded by network throughput in bytes/sec; halving payload size roughly doubles the message rate the same connection can sustain.

Concrete moves for payloads >1 KiB of structured data:

- **Switch JSON to Protobuf** — typically 3–10× smaller for the same data, plus faster encode/decode in both publisher and subscriber. Pub/Sub topics also support [Proto schemas](topics-and-schemas.md) for server-side validation.
- **gzip the body** before publishing if you must keep a text format. Decompress in the subscriber. Adds CPU cost on both sides; usually a net win above ~1 KiB.

The 1 MiB per-message and 10 MiB per-publish-RPC limits are hard ceilings, not targets. Most high-throughput publishers stay well below both — single-digit KiB messages with `CountThreshold=1000` is a common sweet spot.

### Flow Control on the Publisher

`FlowControlSettings` caps how much un-acked publish work can accumulate in the publisher. Without it, a slow Pub/Sub backend or downstream outage causes unbounded memory growth.

`LimitExceededBehavior`:

- **`FlowControlBlock`** (recommended) — `Publish` calls block when the limit is hit, applying backpressure to the producer.
- **`FlowControlSignalError`** — `Publish` returns an error immediately. Use when you have a queue upstream that can absorb the backpressure.
- **`FlowControlIgnore`** (default) — no cap. Memory can grow unboundedly under load.

For any production publisher, set this to `FlowControlBlock` with limits sized to your memory budget.

## Ordering Keys

Pub/Sub guarantees per-key ordering — messages with the same `OrderingKey` are delivered to subscribers in the order they were successfully published. Messages with different keys (or no key) have no ordering relationship.

Both sides must opt in:

```go
// Publisher
topic := client.Topic("my-topic")
topic.EnableMessageOrdering = true
topic.PublishSettings.EnableMessageOrdering = true  // also accepts here

result := topic.Publish(ctx, &pubsub.Message{
    Data:        []byte("..."),
    OrderingKey: "user-42",
})
```

```bash
# Subscription
gcloud pubsub subscriptions create ordered-sub \
  --topic=my-topic \
  --enable-message-ordering
```

Setting it on only one side silently disables ordering — there is no error.

### The ResumePublish Trap

If a publish for an ordering key fails, **all subsequent publishes for that key are rejected** with the same error until you call `Topic.ResumePublish(orderingKey)`. This is the opposite of normal at-least-once retry behavior — Pub/Sub deliberately blocks the key to prevent reordering after a publish failure.

```go
result := topic.Publish(ctx, msg)
if _, err := result.Get(ctx); err != nil {
    // every future Publish with the same OrderingKey will fail until we resume
    topic.ResumePublish(msg.OrderingKey)
    return err
}
```

You usually want to call `ResumePublish` from your error handler. The exception is when the failure is unrecoverable for the key (e.g., a poison message that always fails validation) — then you may want to leave the key blocked while you triage.

### Throughput Cost

Per-key ordering serializes publishes for that key. The publisher cannot batch two messages for the same key into parallel RPCs. If 99% of your messages share one ordering key, you've effectively serialized your publisher.

Use ordering keys only where ordering is required (one key per user, per session, per device) — not as a "tag" or "partition" mechanism for unrelated reasons.

You can mix ordered and unordered publishes on the same topic; messages with no `OrderingKey` are never blocked by an ordered key's failure.

## Attributes vs Body

| | Attributes | Body (`Data`) |
|---|---|---|
| Type | `map[string]string` | `[]byte` |
| Size limit | 100 attributes, key ≤256 bytes, value ≤1024 bytes | 10 MiB total message including attributes |
| Filterable | Yes (server-side filter) | No |
| Schema-validated | No | Yes (if topic has a schema) |
| Use for | Routing, classification, dedup keys | Payload |

Anything you want to filter on at the subscription level must live in attributes. Anything large or schema-typed goes in the body. Common attributes: `eventType`, `region`, `tenantId`, `idempotencyKey`, `traceId`.

## Topic.Stop and Shutdown

`Topic.Stop()` flushes the in-memory batch, drains in-flight RPCs, and closes the topic handle. Skipping it drops un-flushed messages on process exit:

```go
defer topic.Stop()
```

Order at process shutdown:

```go
// 1. Stop accepting new work
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

// 2. Flush all topics
for _, t := range topics {
    t.Stop()  // blocks until batch drains or context is cancelled at outer scope
}

// 3. Close client
client.Close()
```

If you're publishing during shutdown (e.g., final audit events), `Publish` after `Stop` returns an error — collect those upstream and decide whether they go to a fallback (disk, secondary system) or are lost.

## Publish Errors

`PublishResult.Get` returns gRPC errors. Common ones:

| Code | Meaning | Action |
|---|---|---|
| `OK` (no error) | Published, returns server-assigned message ID | None |
| `INVALID_ARGUMENT` | Schema validation failed, or message > 10 MiB, or attribute limit exceeded | Fix the message; do not retry as-is |
| `FAILED_PRECONDITION` | Ordering key blocked by prior failure | Call `ResumePublish` then retry |
| `NOT_FOUND` | Topic does not exist | Check name; do not retry blindly |
| `PERMISSION_DENIED` | Missing `roles/pubsub.publisher` | Fix IAM; do not retry |
| `UNAVAILABLE` / `DEADLINE_EXCEEDED` | Transient | The SDK retries with backoff; only surfaces if the retry budget is exhausted |
| `RESOURCE_EXHAUSTED` | Per-region publish quota | Slow down; the SDK retries but there's a ceiling |

The Go client retries `UNAVAILABLE`, `DEADLINE_EXCEEDED`, and similar transient codes automatically. Configure retry behavior via `topic.PublishSettings.Timeout` and the underlying call options if needed.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| `id, err := topic.Publish(ctx, m).Get(ctx)` in a tight loop | Defeats batching; each message is one RPC |
| `OrderingKey` set to a low-cardinality value ("us", "high") | Serializes large fractions of the publisher |
| Forgetting `Topic.Stop()` on shutdown | In-flight batches dropped on exit |
| Forgetting `ResumePublish` after an ordering-key failure | All future publishes for the key fail forever |
| Using attributes for the message payload | Tight 1 KiB per attribute limit; not schema-validated |
| Using `FlowControlIgnore` (default) in production | Unbounded memory growth on backend slowdown |
| Creating a new `Topic` handle per publish | Wastes the SDK's batching; create once and reuse |
| Putting the publisher's commit timestamp in the body when you need it as an attribute (or vice versa) | Filterable vs queryable distinction matters at retrieval time |

## Common Pitfalls

- **`Publish` on an ordering key blocked from a prior error doesn't return immediately** — it queues, then fails when the SDK realizes the key is blocked. Call `ResumePublish` synchronously in the error path.
- **Schema validation runs server-side** at publish time. The SDK does not pre-validate; you'll see `INVALID_ARGUMENT` from `Get`, not from `Publish`.
- **`PublishSettings` is not goroutine-safe to mutate** after the first `Publish`. Set it once at topic-handle creation.
- **`Topic.Stop()` is idempotent and blocking.** Calling it twice is fine; calling it from inside an RPC error handler can deadlock.
- **`BufferedByteLimit` counts bytes in flight, not bytes in batches.** A small batch threshold with a large buffer limit means many parallel batches, which is usually what you want.
- **OpenTelemetry tracing** propagates from the publisher's context if you use `otelpubsub` — don't drop the context between `Publish` and `Get`.

## Sources

- https://cloud.google.com/pubsub/docs/publisher
- https://cloud.google.com/pubsub/docs/batch-messaging
- https://cloud.google.com/pubsub/docs/ordering
- https://cloud.google.com/pubsub/docs/publish-best-practices
- https://pkg.go.dev/cloud.google.com/go/pubsub
