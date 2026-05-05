---
name: pubsub
description: >
  Google Cloud Pub/Sub: topics and schemas, subscription types, delivery
  semantics, ordering, dead-letter topics, ack-deadline / flow control,
  Go client SDK. Use for Go code importing cloud.google.com/go/pubsub,
  .proto schemas attached to topics, or gcloud pubsub commands.
---

# Google Cloud Pub/Sub Best Practices

Pub/Sub is at-least-once by default and exactly-once on opt-in subscriptions, but only if the subscriber respects ack deadlines and the publisher uses ordering keys correctly. The frequent failure modes — duplicate processing, message loss after a subscriber crash, "stuck" subscriptions, OOM under load, push-endpoint retry storms — almost always trace to a handful of misconfigured knobs documented across many Google docs pages. This skill encodes those rules so Claude can prevent them during topic/subscription design, subscriber code review, and publisher tuning.

## Scope

Covers: topics and schemas (Avro, Protobuf, schema revisions, `BACKWARD`/`FORWARD` compatibility); subscription types (pull, push, `StreamingPull`, BigQuery, Cloud Storage); delivery semantics (at-least-once, exactly-once); ordering keys (`OrderingKey`, `EnableMessageOrdering`, `ResumePublish`); dead-letter topics (DLT/DLQ); ack-deadline and lease management (`modifyAckDeadline`, `MaxExtension`); flow control (`MaxOutstandingMessages`, `MaxOutstandingBytes`, `NumGoroutines`); message retention (`RetainAckedMessages`, seek, snapshot); subscription filters; retry policy and exponential backoff; publisher batching (`PublishSettings`, `CountThreshold`, `DelayThreshold`, `ByteThreshold`); the Go client (`Topic.Publish`, `Subscription.Receive`, `msg.Ack` / `msg.Nack`, `PublishResult`); monitoring metrics (`oldest_unacked_message_age`, `num_undelivered_messages`).

Out of scope: Pub/Sub Lite, Kafka, Cloud Tasks, Eventarc, Cloud Scheduler.

## Core Rules

These cross-cut almost every Pub/Sub task. Internalize them before reaching for a topic-specific reference.

- **Default delivery is at-least-once. Consumers MUST be idempotent** — keyed on `msg.ID` (server-assigned, stable across redeliveries) or a business key. Even exactly-once subscriptions can deliver duplicates across a subscriber restart window; idempotency is the only durable defense.
- **Ack deadlines extend automatically only while a message is inside `Receive`'s callback.** If the callback hands work off to a background goroutine and returns, the lease stops extending and the message redelivers. Do the work synchronously inside the callback or use a worker pool that the callback `select`s on.
- **Ordering keys require `EnableMessageOrdering = true` on BOTH publisher and subscription.** Setting it on only one side silently disables ordering. A publish error on one key blocks all subsequent publishes for that key — call `Topic.ResumePublish(orderingKey)` to recover.
- **Exactly-once delivery is opt-in per subscription** (`EnableExactlyOnceDelivery`) and adds latency to every ack. EOD reduces but does not eliminate duplicates — make handlers idempotent regardless.
- **Dead-letter topics need IAM bindings or messages silently fail to forward.** The Pub/Sub service account on the source subscription needs `roles/pubsub.publisher` on the DLT, and `roles/pubsub.subscriber` on the source subscription. Without both, retries continue forever.
- **`Subscription.Receive` blocks until error or `ctx.Done()` — and MUST be cancelled for clean shutdown.** Never call `Receive` twice concurrently on the same `*pubsub.Subscription`; spawn a second handle (or restructure your worker) if you need parallel streams.
- **Publisher batching defaults are conservative** (100 messages / 10ms / 1 MiB). For high-throughput publishers, raise `PublishSettings.CountThreshold`, `DelayThreshold`, and `ByteThreshold`; otherwise you pay per-message RPC overhead.
- **Flow control (`MaxOutstandingMessages` / `MaxOutstandingBytes`) is the only thing protecting subscribers from OOM.** Defaults are 1000 messages / 1 GiB per `Subscription.Receive` call. Lower them when each message is heavy or processing is slow.
- **Acked messages are gone unless `RetainAckedMessages = true`.** `Seek` to a past timestamp only replays what is still retained (default retention 7 days; configurable up to 31 days, or 7 days for retained acked messages).
- **Schema enforcement and compatibility mode are set at topic creation.** Default compatibility is `BACKWARD` for additive Avro/Proto changes — older subscribers can decode newer messages. Stricter modes (`FULL`, `FULL_TRANSITIVE`) reject more schema revisions.
- **Push subscription endpoints must respond 2xx within the ack deadline (10s default, 600s max).** A non-2xx counts as a nack; Pub/Sub backs off per the retry policy. Authenticate with OIDC token validation — never expose an unauthenticated push endpoint.
- **In Go: always `defer client.Close()`, call `topic.Stop()` to flush pending publishes, and cancel the context passed to `Receive` for graceful shutdown.** Skipping `Stop()` drops in-flight messages; skipping context cancellation hangs your process.
- **`Topic` is safe to share across goroutines; a single `Receive` call is not.** One `Topic` handle per topic, reused — the SDK batches publishes internally. One `Receive` invocation per subscription handle at a time.

## When to Use Each Concept

| Scenario | Use | Why |
|---|---|---|
| New service consuming events at scale | Pull subscription with StreamingPull (Go SDK default) | Bidirectional flow control, lower latency than push |
| Webhook-style fan-out to existing HTTP service | Push subscription with OIDC auth | No long-lived consumer; Pub/Sub handles retries |
| Stream events directly to a BigQuery table | BigQuery subscription | No subscriber code; built-in schema mapping |
| Archive every message to GCS | Cloud Storage subscription | Same — managed, no subscriber code |
| Need strict per-key ordering | `OrderingKey` + `EnableMessageOrdering=true` on both ends | Only ordering guarantee Pub/Sub offers (per-key, not global) |
| Cannot tolerate any duplicates | Exactly-once subscription **plus** idempotent handler | EOD reduces duplicates; idempotency is still the safety net |
| Bad-message poison pill | Dead-letter topic with `MaxDeliveryAttempts` (5–100) | After N failed acks, message republished to DLT for triage |
| Replay last N hours after a buggy deploy | Snapshot before deploy, `Seek` after rollback | Snapshots preserve un-acked state up to 7 days from creation |
| Replay to an exact wall-clock timestamp | `Seek(time.Time)` on a subscription with retention covering that point | Cheaper than snapshots when you only need a timestamp restore |
| Filter messages without subscriber-side discard | Subscription filter on attributes (`attributes.region = "us"`) | Filtered messages auto-acked, never delivered, no client cost |
| High-volume publish | Tune `PublishSettings.CountThreshold` / `DelayThreshold` / `ByteThreshold` | Defaults batch only ~100 msgs / 10ms / 1MB; raise for throughput |
| Subscriber OOM under load | Lower `MaxOutstandingMessages` / `MaxOutstandingBytes` | Caps in-flight work per `Subscription.Receive` call |
| Long processing per message (>10 min) | Set `MaxExtension` higher, or hand off to an external work queue | Lease extension stops at `MaxExtension`; then redelivery fires |
| Schema evolution on a typed topic | `BACKWARD` compatibility (default) for additive changes | Old subscribers can read new messages; safest evolution path |
| Want at-most-once semantics | Not supported. Use idempotent handlers + dedup table | Pub/Sub does not offer at-most-once; this is by design |

## Examples

Example 1: User says "my subscriber processes the same message multiple times even though I'm calling msg.Ack()"
Actions:
1. Confirm subscription type. Default is at-least-once — duplicates are expected. Check via `gcloud pubsub subscriptions describe SUB --format='value(enableExactlyOnceDelivery)'`.
2. Audit handler idempotency: every effect (DB write, downstream call) must be keyed on `msg.ID` or a business key with a uniqueness constraint. See [references/delivery-guarantees.md](references/delivery-guarantees.md).
3. Look for processing time near the ack deadline. If the handler runs >10s on a 10s-deadline subscription, the lease extension may be lagging — slow handlers cause redelivery even with correct ack calls. See [references/subscribing.md](references/subscribing.md).
4. Only after idempotency is in place, consider enabling exactly-once delivery. EOD adds ack latency and still permits some duplicates around restarts.
Result: Duplicate effects stop because the handler is now idempotent, and the redelivery rate falls because lease extension keeps up with processing time.

Example 2: User says "my push subscription endpoint is getting hammered with retries — error rate is climbing in our logs"
Actions:
1. Check the endpoint's p99 response time. Push subscriptions retry on any non-2xx **or** any response slower than the ack deadline (10s default). See [references/subscriptions.md](references/subscriptions.md).
2. Verify the retry policy is set with exponential backoff (`minimumBackoff`, `maximumBackoff`). Without it, Pub/Sub retries aggressively.
3. Configure a dead-letter topic with `MaxDeliveryAttempts` so a poison message can't loop forever. Confirm IAM bindings (publisher role on DLT, subscriber role on source).
4. If the endpoint is genuinely overloaded, raise the ack deadline (up to 600s) or switch to a pull subscription with backpressure. See [references/operations.md](references/operations.md).
Result: Retry storm subsides because slow responses no longer trigger redelivery, and poison messages drain to the DLT instead of recycling.

Example 3: User says "publish throughput is much lower than expected — I'm only getting a few hundred messages per second"
Actions:
1. Check `PublishSettings`. The defaults batch only ~100 messages or 10ms — raise `CountThreshold` to 1000+, `DelayThreshold` to 50–100ms, `ByteThreshold` to 5–10 MiB. See [references/publishing.md](references/publishing.md).
2. Verify `Topic.Publish` results are `Get()`-ed on a worker goroutine, not synchronously after each publish. Synchronous `Get()` defeats batching.
3. Check for an ordering key applied to all messages. Ordering keys force per-key serialization on the publisher side and cap throughput. Use ordering keys only where order matters; mix unordered and ordered publishes if needed.
4. Confirm `Topic.Stop()` is called on shutdown so the final batch flushes. See [references/go-client.md](references/go-client.md).
Result: Throughput rises to the per-region quota ceiling because batching now amortizes RPC overhead across many messages.

## Troubleshooting

| Symptom | Reference |
|---|---|
| Schema enforcement rejects a publish; need to evolve a Proto/Avro schema; topic retention questions; `RetainAckedMessages` behavior | [references/topics-and-schemas.md](references/topics-and-schemas.md) |
| Choosing pull vs push vs BigQuery vs GCS; subscription filters not matching; push endpoint 500s; ack deadline tuning; expiration policy | [references/subscriptions.md](references/subscriptions.md) |
| Publish throughput plateau; ordering-key publish blocked after error; `PublishResult.Get` hanging; messages lost on shutdown | [references/publishing.md](references/publishing.md) |
| Subscriber OOM; flow-control tuning; "lease expired" / redelivery despite Ack; `Receive` not exiting; concurrent `Receive` calls | [references/subscribing.md](references/subscribing.md) |
| Duplicate processing despite Ack; ordering guarantees questions; exactly-once vs at-least-once choice; dedup window | [references/delivery-guarantees.md](references/delivery-guarantees.md) |
| Session/goroutine leaks; `Topic.Stop` vs `Client.Close` ordering; `Receive` callback contract; OpenTelemetry tracing | [references/go-client.md](references/go-client.md) |
| Quotas hit; backlog growth alarm; setting up DLT with IAM; `Seek`/snapshot recipes; cost surprises from retention | [references/operations.md](references/operations.md) |

## Topic References

- [Topics & Schemas](references/topics-and-schemas.md) — topic creation, message retention, `RetainAckedMessages`, Avro/Protobuf schemas, schema revisions, compatibility modes, encoding, schema evolution playbook
- [Subscriptions](references/subscriptions.md) — pull vs StreamingPull vs push, BigQuery & GCS export subscriptions, attribute filters, expiration, ack deadline, push endpoint config (OIDC, retry, response budget)
- [Publishing](references/publishing.md) — `PublishSettings` (count/byte/delay thresholds, buffer limits, timeouts), publisher flow control, `PublishResult.Get`, ordering keys and `ResumePublish`, attributes vs body, shutdown
- [Subscribing](references/subscribing.md) — `Subscription.Receive` semantics, `ReceiveSettings` (max outstanding, NumGoroutines, MaxExtension), ack/nack discipline, lease internals, graceful shutdown
- [Delivery Guarantees](references/delivery-guarantees.md) — at-least-once vs exactly-once, ordering (per-key only), idempotency patterns, message ID stability, dedup window
- [Go Client SDK](references/go-client.md) — `cloud.google.com/go/pubsub`: `Client` lifecycle, `Topic`/`Subscription` handles, callback contract, shutdown order, error wrapping, OpenTelemetry, common pitfalls
- [Operations](references/operations.md) — quotas, monitoring (`oldest_unacked_message_age`, `num_undelivered_messages`), DLT setup with IAM, retry policy, `Seek` and snapshots, capacity planning, cost levers

## Sources

All recommendations trace back to Google's official documentation. When recommending a specific syntax or limit, prefer fetching the live page over relying on this skill's cached digest:

- https://cloud.google.com/pubsub/docs/overview
- https://cloud.google.com/pubsub/docs/publisher
- https://cloud.google.com/pubsub/docs/subscriber
- https://cloud.google.com/pubsub/docs/subscription-properties
- https://cloud.google.com/pubsub/docs/exactly-once-delivery
- https://cloud.google.com/pubsub/docs/ordering
- https://cloud.google.com/pubsub/docs/handling-failures
- https://cloud.google.com/pubsub/docs/schemas
- https://cloud.google.com/pubsub/docs/replay-overview
- https://cloud.google.com/pubsub/docs/push
- https://cloud.google.com/pubsub/quotas
- https://pkg.go.dev/cloud.google.com/go/pubsub
