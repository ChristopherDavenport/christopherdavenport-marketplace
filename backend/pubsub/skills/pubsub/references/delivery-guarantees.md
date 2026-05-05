# Delivery Guarantees — At-Least-Once, Exactly-Once, Ordering

Pub/Sub gives one of two delivery modes per subscription and one ordering guarantee, and they don't compose the way most people expect. The single most important rule is the simplest: **handlers must be idempotent regardless of which mode you choose**, because exactly-once still permits duplicates around restarts and ordering only applies per key.

This reference covers the two delivery modes, what they actually guarantee, the ordering model, and the idempotency patterns that make it all safe.

## Delivery Modes

| Mode | Default | Guarantee | Cost |
|---|---|---|---|
| **At-least-once** | Yes | Every published message is delivered ≥1 time per subscription | None — full throughput, low ack latency |
| **Exactly-once** | Opt-in (`enableExactlyOnceDelivery`) | Same message ID is not redelivered after a successful ack within a window | Higher ack latency; ack must be confirmed before lease expires |

Pub/Sub does not offer at-most-once. That mode is approximated by accepting duplicates at the consumer and handling them via idempotency.

### At-Least-Once

Every successful publish results in at least one delivery attempt to every subscription. Duplicates happen because:

- A subscriber crashed after processing but before acking.
- The ack RPC was lost on the network.
- The lease expired before the ack arrived.
- The subscriber explicitly nacked.

Pub/Sub will keep redelivering until either (a) you ack, (b) the message exceeds `messageRetentionDuration` and is dropped, or (c) `MaxDeliveryAttempts` is hit and the message goes to a dead-letter topic.

### Exactly-Once

Opt in per subscription:

```bash
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-exactly-once-delivery
```

What EOD guarantees:

- A message acknowledged successfully (ack RPC confirmed by Pub/Sub) is **not redelivered** within the message retention window.
- An ack that fails (lease expired before ack reached the server) results in redelivery.

What EOD does **not** guarantee:

- "Each message is processed exactly once" — your handler can run, then crash before acking, and the message redelivers.
- Idempotency — you still need it, because the boundary between "processed" and "acked" is where duplicates live.
- Ordering — orthogonal; needs `enableMessageOrdering` separately.

In Go, EOD changes the ack contract. Use `AckWithResult` to know whether the ack was confirmed:

```go
ar := m.AckWithResult()
status, err := ar.Get(ctx)
switch status {
case pubsub.AcknowledgeStatusSuccess:
    // ack durable; message will not redeliver
case pubsub.AcknowledgeStatusInvalidAckId:
    // lease already expired — message will redeliver
case pubsub.AcknowledgeStatusPermissionDenied, pubsub.AcknowledgeStatusFailedPrecondition, pubsub.AcknowledgeStatusOther:
    // various error cases — message may redeliver
}
```

If you don't care about the ack-result detail, plain `m.Ack()` still works on EOD subscriptions; you just don't get the durability signal.

EOD also costs latency: the ack RPC waits for confirmation, which adds round-trip time. For high-throughput consumers, EOD reduces achievable per-stream throughput.

### When to Choose EOD

| Scenario | Choice |
|---|---|
| Most service-to-service event flows | At-least-once + idempotent handler |
| Financial transactions, billing events, anything irreversible | EOD + idempotent handler (belt and suspenders) |
| Logs, metrics, telemetry | At-least-once; duplicates are fine |
| Webhook fan-out to third parties | At-least-once on a push subscription; no EOD on push |
| Anything where you'd write a dedup table anyway | Either; EOD just reduces the dedup table's hit rate |

EOD is not available on push subscriptions, BigQuery subscriptions, or Cloud Storage subscriptions.

## Ordering Guarantees

Pub/Sub offers per-ordering-key ordering only — never global ordering, never per-topic ordering.

| Mode | Guarantee |
|---|---|
| No ordering key | None — messages may arrive in any order |
| Ordering key set, both ends opted in | Messages with the same key arrive in publish order |
| Ordering key set, only publisher (or only subscription) opted in | Ordering silently disabled |
| Multiple ordering keys | Messages with different keys have no ordering relationship |

The "both ends opt in" requirement is unforgiving: there is no error, no warning, no metric. Ordering simply doesn't happen. Verify by inspecting both:

```bash
gcloud pubsub subscriptions describe my-sub --format='value(enableMessageOrdering)'
```

```go
fmt.Println(topic.PublishSettings.EnableMessageOrdering, topic.EnableMessageOrdering)
```

### Ordering and EOD Compose

You can have both: an ordered subscription with EOD. The combination is the strongest delivery mode Pub/Sub offers, and the slowest. Use only when both per-key ordering and at-most-once are genuinely required.

### Ordering and Errors

A failed publish for an ordering key blocks all subsequent publishes for that key. See [publishing.md](publishing.md) for `ResumePublish`.

A nacked message on an ordered subscription does **not** block subsequent messages for that key from being delivered. The semantics are "at least one delivery in publish order"; redelivery of a nacked message can interleave with later messages.

If you need strict in-order processing through the entire pipeline (publish → subscribe → handle), you must:

1. Use ordering keys end-to-end.
2. Process messages strictly serially per key (no goroutines per key).
3. Treat nack as a fatal signal — restart the per-key processor and re-fetch from where you left off (Pub/Sub redelivers from the unacked point).

## Message ID Stability

`m.ID` is the server-assigned message ID. Properties:

- **Stable across redeliveries.** A redelivered message has the same ID as the original delivery.
- **Unique within a topic.** No two distinct publishes share an ID.
- **Opaque** — treat as a string, don't parse.

Use `m.ID` as the key for an idempotency table:

```sql
CREATE TABLE processed_messages (
    message_id TEXT PRIMARY KEY,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Or in your handler:

```go
func handle(ctx context.Context, m *pubsub.Message) {
    if alreadyProcessed(ctx, m.ID) {
        m.Ack()  // duplicate; already done
        return
    }
    if err := process(ctx, m); err != nil {
        m.Nack()
        return
    }
    if err := markProcessed(ctx, m.ID); err != nil {
        m.Nack()  // could not record; let it redeliver
        return
    }
    m.Ack()
}
```

The check-then-act has a race: two concurrent deliveries of the same message can both see "not processed" and both run. Use a unique constraint on `message_id` so the second insert fails — that's your dedup gate.

### Business-Key Idempotency

`m.ID` dedups Pub/Sub-level redeliveries. It does not dedup application-level retries (the same logical event published twice with two different message IDs). For that, use a business key:

```go
m := &pubsub.Message{
    Data: payload,
    Attributes: map[string]string{
        "idempotencyKey": orderID + "-charged",
    },
}
```

The handler then checks `attributes["idempotencyKey"]` against a dedup table. This handles both Pub/Sub redeliveries and upstream double-publishes.

## Dedup Window

Pub/Sub's EOD dedup window is bounded by the subscription's `messageRetentionDuration` (default 7 days, max 31 days). After that, the message ID is forgotten and a redelivery (which would only happen on retention extension or `Seek` to a snapshot) would be treated as new.

Application-level dedup tables should bound their own retention to match — a `message_id` row from 30 days ago serves no purpose if the subscription retention is 7 days.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| "EOD means I don't need idempotency" | False; EOD permits duplicates around ack failures |
| Using random UUIDs as ordering keys | Spreads work but provides no ordering — just use no ordering key |
| One ordering key for all messages from one publisher | Serializes the entire publisher; throughput drops |
| Treating `m.PublishTime` as a deduplication key | Two distinct messages can share a publish time |
| `if !alreadyProcessed { process; markProcessed }` without unique-constraint enforcement | Race on concurrent redelivery |
| Per-tenant ordering with thousands of tenants and 1 worker per key | Ordered subscriptions need workers proportional to active key count |
| EOD on a high-throughput log/metrics stream | Costs more than it gives; at-least-once is right |

## Common Pitfalls

- **Push subscriptions can't use EOD.** If you need EOD, switch to pull.
- **`enableExactlyOnceDelivery` on the subscription needs `EnableMessageOrdering` separately** if you want both — they're independent flags.
- **`AckWithResult` on at-least-once subscriptions returns `Success` immediately** without server confirmation; the result is meaningful only on EOD.
- **A redelivered message has the same `m.ID` but a higher `m.DeliveryAttempt`** (when a DLT is configured). Use `DeliveryAttempt` to gate retry-aware behavior.
- **`m.Nack()` on an EOD subscription** still works the same way — you're just opting back into redelivery.
- **Snapshot-based replay can deliver messages your handler already acked** — this is the one case where EOD's no-redelivery guarantee is bypassed (you asked for it). Idempotency is essential.
- **Ordering keys cap subscriber parallelism per key.** A subscription with one hot key and `MaxOutstandingMessages = 1000` still processes that key serially.

## Sources

- https://cloud.google.com/pubsub/docs/exactly-once-delivery
- https://cloud.google.com/pubsub/docs/ordering
- https://cloud.google.com/pubsub/docs/subscriber
- https://cloud.google.com/pubsub/docs/handling-failures
- https://cloud.google.com/pubsub/docs/replay-overview
