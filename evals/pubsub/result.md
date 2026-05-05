# Eval report: `pubsub`

- Cases: **6**
- Expectations met: **1/6** (skill_wins 0/4, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **0**, baseline won **2**, ties **4**
- Rubric pass-rate (over 5 scored case(s)): baseline **80%**, skill **80%** (Δ **+0%**)
- CLI cost: **$0.85** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `duplicate-processing` | skill_wins | ✗ | **tie** | 100% | 100% |
| `ordering-keys-not-working` | skill_wins | ✗ | **baseline** | 100% | 100% |
| `publish-throughput-low` | skill_wins | ✗ | **baseline** | 67% | 67% |
| `dead-letter-not-working` | skill_wins | ✗ | **tie** | 100% | 100% |
| `simplest-publish` | skill_wins_strict | ✗ | **tie** | 33% | 33% |
| `offtopic-css-flexbox` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `duplicate-processing`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
My Pub/Sub subscriber is processing the same message multiple times
even though I'm calling msg.Ack() at the end of every handler. What's
going on and how do I prevent it?
```

**Judge:** **tie** — Both answers are excellent and cover all four rubric criteria thoroughly. Answer A is slightly more detailed on lease extension mechanics and tuning parameters, while Answer B adds a valuable nuance about business keys vs msg.ID for upstream retries. Both recommend idempotency keyed on msg.ID, explain at-least-once semantics, cover ack deadline/slow handler issues, and mention exactly-once as a secondary option. The quality difference is negligible.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies at-least-once as the default | tie |
| recommends idempotency | tie |
| mentions msg.ID for dedup key | tie |
| considers ack deadline / slow handler / lease extension | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `Ack deadline` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `Ack-deadline` |

<details><summary>Baseline answer</summary>

Short version: this is almost certainly working as designed. Pub/Sub is **at-least-once** by default, so duplicates are expected — `Ack()` is a hint, not a guarantee. You defeat duplicates with **idempotency**, not with more careful acking.

## What's actually happening

Two distinct mechanisms produce redelivery, and you usually have both:

1. **At-least-once delivery is the default.** Even with a perfect handler that always acks, Pub/Sub may redeliver a message if the ack didn't reach the server in time, if the subscriber client crashed mid-flight, or simply because the service chose to. Treating this as a bug will lead you in circles.

2. **Ack deadline / lease expiry.** Each delivered message has an ack deadline. The Go client extends the lease in the background (up to `MaxExtension` / `MaxExtensionPeriod` on `ReceiveSettings`), but if your handler is slow — or blocks on something the lease extender can't keep up with — the lease lapses and Pub/Sub redelivers to *another* worker. Your original handler then finishes and calls `msg.Ack()` on a message that's already been redelivered. Classic duplicate.

## How to prevent it (in priority order)

**1. Make the handler idempotent.** This is the durable fix. Use a dedup key and a transactional "have I seen this?" check:

```go
func handle(ctx context.Context, msg *pubsub.Message) {
    // msg.ID is unique per *publish*, stable across redeliveries
    inserted, err := db.InsertIfAbsent(ctx, "processed_msgs", msg.ID)
    if err != nil {
        msg.Nack()
        return
    }
    if !inserted {
        msg.Ack() // already processed; just drop the dup
        return
    }
    // ... do the real work in the same tx as the insert ideally ...
    msg.Ack()
}
```

A **business key** (order ID, event ID from the payload) is often even better than `msg.ID`, because the same logical event republished by an upstream retry will share the business key but get a fresh `msg.ID`. Use `msg.ID` when you have nothing better.

**2. Audit your handler's runtime vs. the ack deadline.** If handlers are slow:
- Bump `ReceiveSettings.MaxExtension` (and/or `MaxExtensionPeriod`) so the client keeps extending the lease while you work.
- Or do the slow work asynchronously and ack quickly after persisting the job.
- If you genuinely can't finish in time and want a redelivery, call `msg.Nack()` explicitly rather than letting the lease silently lapse — it's faster and clearer.

**3. Reduce concurrent in-flight work** (`MaxOutstandingMessages`) if your workers are oversubscribed and starving the lease extender — that turns into "slow handler" symptoms even when the actual processing is fast.

**4. Only then consider exactly-once delivery.** Pub/Sub does support an exactly-once delivery mode on the subscription, but it tightens delivery semantics and changes ack behavior (acks become `AckWithResult`-style with confirmation). It reduces duplicates dramatically but doesn't eliminate the *application-level* need for idempotency across, say, retries from upstream systems. Turn it on if you want, but ship the idempotent handler first — that's what actually keeps your data correct.

## TL;DR
- Duplicates aren't a bug; at-least-once is the contract.
- Use `msg.ID` (or a business key) plus a dedup table to make the handler idempotent.
- Check whether slow handlers / lapsing ack deadlines are causing redelivery to a *second* worker before your first one finishes.
- Exactly-once is a nice-to-have on top, not a substitute.

</details>

<details><summary>Skill-loaded answer</summary>

Short answer: **Pub/Sub is at-least-once by default, so duplicates are expected — even when every `Ack()` succeeds.** `Ack()` is best-effort, not a contract that the message will never be redelivered. You need to make your handler idempotent, and you should also check whether your handler is running long enough to lose its lease.

## Why you're seeing duplicates

There are two independent causes, and you usually have both:

**1. At-least-once is the default.** Even if `Ack()` returns cleanly on your side, the ack RPC can be lost in flight, the subscriber can crash between handler completion and the ack being flushed, or Pub/Sub can simply redeliver during a leader change on the server side. The docs are explicit that duplicates are part of the contract — they're not a bug to be fixed at the transport layer.

**2. Ack-deadline expiry (slow handlers).** Each delivery comes with an ack deadline (default 10s, capped by `MaxExtension`). The Go client auto-extends the lease in the background via `modifyAckDeadline` calls, but:
   - If your handler blocks for longer than `ReceiveSettings.MaxExtension` (default 60 min, but often set lower), the lease lapses and the message is redelivered to *another* worker — often before your `Ack()` even runs.
   - If lease-extension RPCs fail (network blip, throttling) the same thing happens.
   - If you have many in-flight messages and a worker is saturated, extensions can be late.

So you can get a "double-process" pattern where two workers are both inside the handler at the same time, both call `Ack()`, and both succeed.

## How to prevent it

**Make the handler idempotent — this is the durable fix.**

The standard pattern is to dedup on `msg.ID`, which is stable across redeliveries of the same publish:

```go
func handle(ctx context.Context, msg *pubsub.Message) {
    // Atomic "claim" keyed on msg.ID. Use whatever your storage supports:
    // - INSERT ... ON CONFLICT DO NOTHING in Postgres
    // - SETNX with TTL in Redis
    // - A processed_messages table with msg.ID PRIMARY KEY
    claimed, err := store.Claim(ctx, msg.ID, ttl)
    if err != nil {
        msg.Nack()
        return
    }
    if !claimed {
        // Already processed (or in flight elsewhere). Ack and move on.
        msg.Ack()
        return
    }

    if err := doWork(ctx, msg); err != nil {
        store.Release(ctx, msg.ID) // let a retry try again
        msg.Nack()
        return
    }
    msg.Ack()
}
```

Notes:
- `msg.ID` is the right key for "same publish, redelivered." If you actually want to dedup based on payload meaning (e.g., the same order placed twice by the publisher), use a **business key** from the message attributes instead.
- The dedup record needs a TTL longer than the worst-case redelivery window — typically the subscription's message retention (default 7 days).

**Tune the lease so slow handlers don't trigger redelivery in the first place.**

```go
sub.ReceiveSettings.MaxExtension       = 10 * time.Minute  // cap on auto-extension
sub.ReceiveSettings.MaxExtensionPeriod = 60 * time.Second  // single extension chunk
sub.ReceiveSettings.MaxOutstandingMessages = 100           // back-pressure
```

If your handler routinely takes more than a few seconds, lower `MaxOutstandingMessages` so each worker isn't behind a backlog when the extender tries to bump deadlines, and raise `MaxExtension` to cover the p99 of your handler.

**Consider exactly-once delivery — but only after idempotency is in place.**

You can enable `EnableExactlyOnceDelivery` on the subscription. This makes Pub/Sub track ack state more carefully and reduces (not eliminates) duplicates, at the cost of higher latency and stricter ack semantics — `Ack()` now returns an `AckResponse` you should check, and an "ack" that the server didn't accept means the message *will* come back. It's a useful belt-and-suspenders, but it doesn't replace idempotent handlers — it complements them.

## TL;DR

- Duplicates are by design under at-least-once; `Ack()` doesn't promise uniqueness.
- The two contributing causes are (a) lost/delayed ack RPCs and (b) ack-deadline expiring on slow handlers before `Ack()` runs.
- Fix it with an idempotency check on `msg.ID` (or a business key) backed by durable storage.
- Then tune `MaxExtension` / `MaxOutstandingMessages` so the handler isn't losing its lease.
- Optionally turn on exactly-once delivery as a second layer — but keep the idempotency layer.

</details>

---

### `ordering-keys-not-working`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I set OrderingKey on my Pub/Sub messages when publishing but the
subscriber is still receiving them out of order. What's wrong?
```

**Judge:** **baseline** — Both answers cover all four rubric criteria well, but Answer A is slightly cleaner and more accurate. Answer B contains a minor inaccuracy by suggesting EnableMessageOrdering needs to be set 'on the client receiving messages' as a separate runtime step beyond subscription creation, which is misleading. Answer A's diagnostic checklist also includes a useful extra point about subscriber-side goroutine reordering. Overall both are excellent, but A is marginally more precise.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| requires EnableMessageOrdering on both sides | baseline |
| mentions EnableMessageOrdering by name | tie |
| clarifies per-key, not global | tie |
| mentions ResumePublish | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `BOTH the publisher and the subscri` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per-key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `both at subscri` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per-key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

<details><summary>Baseline answer</summary>

The most common cause: **`EnableMessageOrdering` has to be set on BOTH the publisher and the subscription.** Setting it on only one side silently fails — the publisher will respect ordering keys, but the subscription will still hand messages to your callback in arbitrary order.

### 1. Publisher side

```go
topic := client.Topic("my-topic")
topic.EnableMessageOrdering = true

res := topic.Publish(ctx, &pubsub.Message{
    OrderingKey: "user-123",
    Data:        payload,
})
```

### 2. Subscription side — easy to miss

The subscription itself must have been **created with message ordering enabled**. You can't toggle this after creation; you have to recreate the subscription.

```bash
gcloud pubsub subscriptions create my-sub \
    --topic=my-topic \
    --enable-message-ordering
```

Or in Go when creating it:

```go
_, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic:                 topic,
    EnableMessageOrdering: true,
})
```

If the subscription was created without that flag, the server is free to deliver out of order regardless of what the publisher did. Check with `gcloud pubsub subscriptions describe my-sub` — look for `enableMessageOrdering: true`.

### 3. Ordering is per-key, not global

Ordering is only guaranteed for messages that share the **same `OrderingKey`**. Two messages with different keys (or no key) can arrive in any order relative to each other. If you're expecting a global stream order, ordering keys won't give you that — you'd need a single key for everything (which throttles you to ~1 MB/s for that key).

### 4. The `ResumePublish` gotcha

This one bites people. If a `Publish` call for a given ordering key **fails**, the client library will **permanently block all further publishes for that key** until you explicitly call:

```go
res := topic.Publish(ctx, msg)
if _, err := res.Get(ctx); err != nil {
    topic.ResumePublish(msg.OrderingKey)
    // handle / retry
}
```

Without `ResumePublish`, every subsequent `Publish` with that key returns an error immediately and nothing flows. If "out of order" actually means "some messages aren't arriving at all after a transient error," this is almost certainly it.

### Quick diagnostic checklist

1. `gcloud pubsub subscriptions describe <sub>` → confirm `enableMessageOrdering: true`. **If false, recreate it.**
2. Confirm `topic.EnableMessageOrdering = true` in publisher code.
3. Confirm the messages you're comparing actually share the same `OrderingKey`.
4. Add error handling that calls `ResumePublish` on any publish failure.
5. Make sure your subscriber isn't doing concurrent processing across messages of the same key in a way that reorders them *after* receipt — the library delivers them in order, but if you fan out to goroutines, you reorder them yourself.

In my experience, #1 (subscription not created with the flag) accounts for ~80% of these reports.

</details>

<details><summary>Skill-loaded answer</summary>

There are a few likely culprits. The most common one is asymmetric configuration:

## 1. `EnableMessageOrdering` must be set on BOTH sides

This is by far the most frequent cause. Setting `OrderingKey` on a published message is necessary but not sufficient. You also need:

**Publisher side** — enable it on the topic's `PublishSettings`:
```go
topic := client.Topic("my-topic")
topic.EnableMessageOrdering = true
```

**Subscription side** — this is the one people miss. It must be enabled both at subscription-creation time *and* on the client receiving messages:

```go
// At creation:
sub, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic:                 topic,
    EnableMessageOrdering: true, // immutable after creation!
})

// And when receiving:
sub := client.Subscription("my-sub")
sub.ReceiveSettings.NumGoroutines = 1 // optional but helps
// (the subscription itself must have been created with ordering enabled)
```

If the subscription was created without `EnableMessageOrdering`, the server will deliver messages in any order regardless of what the publisher does — and it fails silently. You can't toggle it after creation; you have to recreate the subscription.

## 2. Ordering is per-key, not global

Messages are only ordered with respect to other messages sharing the **same** `OrderingKey`. If you're expecting a global total order across all messages, that's not what ordering keys give you. Two messages with different keys (or no key) can arrive in any order relative to each other.

## 3. After a publish error, the key is "stuck" until you call `ResumePublish`

If any publish for an ordering key fails, the client library will refuse to publish *any further messages* for that key — they'll all error out — until you explicitly call:

```go
result := topic.Publish(ctx, msg)
if _, err := result.Get(ctx); err != nil {
    topic.ResumePublish(msg.OrderingKey)
    // handle / retry
}
```

Without this, you may think things are "out of order" when really later messages were dropped at publish time.

## Quick diagnostic checklist

1. `gcloud pubsub subscriptions describe my-sub` — does it show `enableMessageOrdering: true`? If not, recreate it.
2. Is `topic.EnableMessageOrdering = true` set in your publisher code before any `Publish` call?
3. Are you actually putting the same `OrderingKey` on the messages you expect to be ordered?
4. Are you handling publish errors and calling `ResumePublish` for that key?
5. If you're using a regional endpoint, are publisher and subscriber in the same region? Ordering is preserved within a region.

In practice, #1 (subscription side missing the flag) accounts for the vast majority of "I set OrderingKey and it doesn't work" reports.

</details>

---

### `publish-throughput-low`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I'm only getting a few hundred messages per second from my Go
publisher into Pub/Sub, even though my topic should handle far more.
Each Publish call is small. What should I tune?
```

**Judge:** **baseline** — Both answers cover all three rubric criteria well, but Answer B is slightly more complete and better organized. B leads with the most impactful fix (per-publish blocking Get), adds useful extras like reusing the Topic object, ordering key warnings, compression hints, and quota sanity checks, and provides clearer shutdown guidance with the defer placement note. A is also excellent but B's additional depth and practical ordering of advice gives it a slight edge.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| tune PublishSettings batching | tie |
| warns against per-publish blocking Get | baseline |
| mentions Topic.Stop on shutdown | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✗ | |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✗ | |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

<details><summary>Baseline answer</summary>

The bottleneck is almost certainly that you're not actually batching — either your `PublishSettings` thresholds are too tight, or (much more commonly) you're calling `result.Get(ctx)` synchronously after each `Publish`, which silently defeats the client's batching entirely.

## 1. Stop calling `Get()` per message

`topic.Publish()` is asynchronous — it returns a `*PublishResult` and the message goes into an in-memory batch. If you write:

```go
// ANTI-PATTERN — turns async batching into synchronous one-at-a-time RPCs
for _, m := range msgs {
    r := topic.Publish(ctx, &pubsub.Message{Data: m})
    if _, err := r.Get(ctx); err != nil { ... }
}
```

…you've serialized everything. Each call waits for a full round trip before the next message even enters the batch, so the batch size is effectively 1 and you'll see exactly the "few hundred msg/s" you're describing.

The fix is **fan out the publishes, then collect results**:

```go
results := make([]*pubsub.PublishResult, 0, len(msgs))
for _, m := range msgs {
    results = append(results, topic.Publish(ctx, &pubsub.Message{Data: m}))
}
for _, r := range results {
    if _, err := r.Get(ctx); err != nil {
        // handle
    }
}
```

Or, in steady-state, hand the result to a goroutine (or just don't block on it at all if you're streaming).

## 2. Tune `PublishSettings`

The defaults are conservative for low-latency, low-volume use. For throughput, raise the batch thresholds:

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    DelayThreshold: 50 * time.Millisecond, // up from 10ms — let batches fill
    CountThreshold: 1000,                  // up from 100
    ByteThreshold:  1e6,                   // up from ~1MB; cap is ~10MB per request
    NumGoroutines:  runtime.GOMAXPROCS(0), // parallel publish workers per topic
    Timeout:        60 * time.Second,
    FlowControlSettings: pubsub.FlowControlSettings{
        MaxOutstandingMessages: 10000,
        MaxOutstandingBytes:    100 * 1024 * 1024,
        LimitExceededBehavior:  pubsub.FlowControlBlock,
    },
}
```

A batch flushes when **whichever threshold trips first**. With small messages and a tight `DelayThreshold`, you flush on the timer with batches of ~10 messages — that's your few hundred/s. Raising `DelayThreshold` (a bit) and `CountThreshold` (a lot) is the single biggest lever for tiny messages.

`NumGoroutines` controls how many concurrent publish RPCs are in flight per topic — with one goroutine and high RTT to the regional endpoint, you're throughput-limited by latency. Bump it.

## 3. Reuse the `*Topic`, don't recreate per call

`client.Topic("name")` is cheap, but each `*Topic` has its **own** batcher. If you create a new one per request you'll never accumulate a batch. Cache it for the lifetime of the process.

## 4. Call `topic.Stop()` on shutdown

`Stop()` flushes the in-memory batch and waits for pending publishes to finish. Without it, on `SIGTERM` or normal exit you'll silently drop whatever was sitting in the batcher — and the bigger you make `CountThreshold`/`DelayThreshold`, the more you stand to lose.

```go
defer topic.Stop()
```

(Make sure this runs *before* your `client.Close()` and before the process exits.)

## 5. Sanity-check the rest

- **Compression**: in recent versions of the client, `PublishSettings.EnableCompression = true` (with `CompressionBytesThreshold`) helps if you're CPU/bandwidth-bound at the wire.
- **Ordering keys**: if you're setting `OrderingKey`, ordered publishes serialize per key — that *will* cap throughput per key. Unset it if you don't need ordering.
- **Region**: publish to the topic's home region; cross-region RTT eats into per-RPC throughput, which `NumGoroutines` partially compensates for.
- **Quota**: confirm you're nowhere near the project's publish quota in Cloud Monitoring (`pubsub.googleapis.com/topic/send_request_count`) before assuming it's a client issue — but at "few hundred/s" you're nowhere close.

In practice: **fix the per-message `Get()` first**, then tune `PublishSettings`. That ordering matters because raising `CountThreshold` does nothing if your batches always have size 1.

</details>

<details><summary>Skill-loaded answer</summary>

A few hundred msg/s from a Go publisher almost always means you're publishing one-message-at-a-time end-to-end, which defeats the client's batching. Three things to tune (in order of impact):

## 1. Raise the batching thresholds in `PublishSettings`

The Go client batches in-process before it actually sends an RPC. The defaults are conservative for low-latency, single-message workloads. For throughput, push them up:

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    DelayThreshold: 100 * time.Millisecond, // default 10ms — wait longer to fill batch
    CountThreshold: 1000,                   // default 100  — more msgs per batch
    ByteThreshold:  1e6,                    // default 1MB  — bigger byte budget
    NumGoroutines:  runtime.NumCPU(),       // more concurrent publish RPCs
    Timeout:        60 * time.Second,
    FlowControlSettings: pubsub.FlowControlSettings{
        MaxOutstandingMessages: 10_000,
        MaxOutstandingBytes:    100 * 1024 * 1024,
        LimitExceededBehavior:  pubsub.FlowControlBlock,
    },
}
```

A batch flushes when **any one** threshold trips. With small messages, you're hitting `DelayThreshold` (10ms) constantly and shipping tiny batches — that's your few-hundred/s ceiling. Trading ~100ms of buffering for a 10× count threshold is usually the single biggest win.

## 2. Don't block on `result.Get()` after every Publish

This is the silent killer. `Topic.Publish` returns a `*PublishResult` immediately and is async — that's the whole point. If your code looks like:

```go
// ❌ This serializes everything; batching can't happen.
for _, m := range messages {
    r := topic.Publish(ctx, &pubsub.Message{Data: m})
    if _, err := r.Get(ctx); err != nil { ... }   // blocks until RPC returns
}
```

…you've turned the async, batched client into a synchronous one. Each `Get` waits for the server, so the next `Publish` doesn't even enter the batch until the previous round-trip completes.

Do this instead — fire-and-collect, check results in a separate goroutine (or at the end):

```go
// ✅ Publish in a tight loop, harvest results out-of-band.
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, m := range messages {
    results = append(results, topic.Publish(ctx, &pubsub.Message{Data: m}))
}
for _, r := range results {
    if _, err := r.Get(ctx); err != nil {
        // log / retry / fail
    }
}
```

Or hand each result to a worker pool — anything except inline `Get` per message.

## 3. Call `topic.Stop()` on shutdown

Because publishes sit in an in-memory batch up to `DelayThreshold`, if your process exits (or you cancel the context) without flushing, you'll silently drop the tail. On any clean shutdown path:

```go
topic.Stop() // blocks until all queued messages are sent (or fail)
```

This also matters during tests — you'll see "I published 1000 messages and only 873 arrived" if you forget.

## Quick checklist

- [ ] Raised `CountThreshold` / `DelayThreshold` / `ByteThreshold`?
- [ ] Increased `NumGoroutines` (parallel publish RPCs)?
- [ ] Removed any `result.Get()` call inside the publish loop?
- [ ] Reusing one `*pubsub.Topic` across the program (not creating per call)?
- [ ] `topic.Stop()` on shutdown?
- [ ] Flow control set so a burst doesn't OOM you when you raise the other knobs?

If you do all of the above and *still* plateau, then look at network egress, CPU on the publisher (proto marshaling), or whether you're CPU-bound producing the messages in the first place — but 99% of "few hundred msg/s" reports are #1 + #2.

</details>

---

### `dead-letter-not-working`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I configured a dead-letter topic on my Pub/Sub subscription with
maxDeliveryAttempts=5, but failed messages keep being retried
forever instead of going to the DLT. What did I miss?
```

**Judge:** **tie** — Both answers are nearly identical in quality, correctly identifying the IAM bindings on the Pub/Sub service account as the root cause, mentioning both the publisher role on the DLT and the subscriber role on the source subscription, and providing correct gcloud commands. Answer B has a slight edge in explaining *why* the subscriber role feels redundant but is necessary, and adds a useful tip about having a subscription on the DLT, while Answer A adds a useful tip about triggering service agent creation. Overall the differences are marginal.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies IAM as the cause | tie |
| mentions publisher role on DLT | tie |
| mentions subscriber role on source | skill |
| mentions Pub/Sub service account | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies IAM as the cause | ✓ | `IAM` |
| mentions publisher role on DLT | ✓ | `roles/pubsub.publisher` |
| mentions subscriber role on source | ✓ | `roles/pubsub.subscriber` |
| mentions Pub/Sub service account | ✓ | `service account` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies IAM as the cause | ✓ | `IAM` |
| mentions publisher role on DLT | ✓ | `roles/pubsub.publisher` |
| mentions subscriber role on source | ✓ | `roles/pubsub.subscriber` |
| mentions Pub/Sub service account | ✓ | `service account` |

<details><summary>Baseline answer</summary>

## The most likely culprit: missing IAM grants for the Pub/Sub service agent

`maxDeliveryAttempts=5` only takes effect if the **Pub/Sub service account** has permission to (a) publish to the dead-letter topic and (b) acknowledge messages on the source subscription. If either grant is missing, Pub/Sub silently falls back to normal retry behavior and the message is redelivered forever.

### Fix

Find your project's Pub/Sub service agent (note: it's the *service* account, not your app's SA):

```
service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com
```

Then grant both roles:

```bash
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# Allow Pub/Sub to publish to the DLT
gcloud pubsub topics add-iam-policy-binding DLT_TOPIC \
  --member="serviceAccount:${SA}" \
  --role="roles/pubsub.publisher"

# Allow Pub/Sub to ack the message on the source subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUB \
  --member="serviceAccount:${SA}" \
  --role="roles/pubsub.subscriber"
```

If the service agent doesn't exist yet, trigger its creation once with:
```bash
gcloud beta services identity create --service=pubsub --project="$PROJECT_ID"
```

### Other things worth verifying

1. **Are you actually NACK'ing (or letting the ack deadline expire)?** Delivery attempts only increment on negative acknowledgement / deadline expiry. If your subscriber is silently catching the exception and ACK'ing, the counter never advances.
2. **`deliveryAttempt` attribute present?** Pull a message and check `message.delivery_attempt`. If it's `None`/missing, the dead-letter policy isn't actually attached to the subscription you're consuming from. Re-check with:
   ```bash
   gcloud pubsub subscriptions describe SOURCE_SUB --format='value(deadLetterPolicy)'
   ```
3. **DLT in a different project?** The IAM bindings must be applied in the project that owns the DLT *and* the project that owns the subscription, using the **subscription's** project's Pub/Sub service agent.
4. **Ordering keys / exactly-once enabled?** Neither prevents DLT routing, but check that `maxDeliveryAttempts` is between 5 and 100 — values outside that range are rejected/clamped.
5. **Updated an existing subscription?** Make sure the policy actually persisted (`gcloud pubsub subscriptions describe ...`) — a typo in the topic path will be accepted at create time but fail silently at delivery time if IAM isn't right.

In ~90% of "DLT isn't working" cases I've seen, it's #1 (the IAM grant on the service agent). Start there.

</details>

<details><summary>Skill-loaded answer</summary>

## The almost-certain culprit: IAM on the Pub/Sub service agent

Setting `deadLetterPolicy.deadLetterTopic` and `maxDeliveryAttempts` is only half the configuration. Pub/Sub forwards undeliverable messages on your behalf using the **Pub/Sub service account**:

```
service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com
```

That principal needs **two** role bindings, and if either is missing, DLT forwarding silently no-ops and the message just keeps redelivering until you ack it or it expires:

1. **`roles/pubsub.publisher` on the dead-letter topic** — so the service can publish the failed message there.
2. **`roles/pubsub.subscriber` on the source subscription** — so the service can acknowledge the original message after it has been forwarded. This one trips people up because it feels redundant ("I'm already the subscriber!"), but the *Pub/Sub service itself* needs it to ack on your behalf.

### Fix it with gcloud

```bash
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# 1) Publisher on the DLT
gcloud pubsub topics add-iam-policy-binding DLT_TOPIC \
  --member="$SA" --role=roles/pubsub.publisher

# 2) Subscriber on the source subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUB \
  --member="$SA" --role=roles/pubsub.subscriber
```

Within a minute or two, messages that nack (or whose ack deadline lapses) 5 times will start landing in the DLT.

### A few other things worth double-checking

- **You're actually nacking (or letting the deadline expire) on every attempt.** `maxDeliveryAttempts` counts *delivery attempts*, not application-level errors. If your subscriber is silently extending the ack deadline (e.g., the client library's lease management) or modacking, those still count as the same attempt — so the count grows as expected, but only when the message is genuinely redelivered. Confirm via the `subscription/dead_letter_message_count` and `subscription/expired_ack_deadlines_count` metrics.
- **The DLT exists in the same project / is reachable.** Cross-project DLTs work, but the binding above must be done in the *DLT's* project.
- **`maxDeliveryAttempts` is between 5 and 100.** Values outside that range are rejected; some IaC tools mask the error.
- **There's a subscription on the DLT.** Forwarding works without one, but the messages will be silently dropped after the topic's retention window — easy to mistake for "DLT isn't working."
- **You didn't accidentally clear the policy on an update.** `gcloud pubsub subscriptions update` requires you to re-pass `--dead-letter-topic` and `--max-delivery-attempts` together; omitting one effectively removes the policy in some Terraform providers too.

In ~90% of "DLT isn't catching anything" reports I've seen, it's #1 — the missing `roles/pubsub.subscriber` grant on the source subscription for the Pub/Sub service agent. Start there.

</details>

---

### `simplest-publish`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Just give me the simplest, fewest-lines Go snippet to publish a
message to a Pub/Sub topic and make sure it actually went through
before the program exits.
```

**Judge:** **tie** — Both answers are essentially identical in code and explanation. Neither calls Topic.Stop() before exit, and neither warns about the Get()-in-a-loop batching trap. Since both answers fail the same rubric criteria equally, the result is a tie.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| calls Topic.Stop() before exit | tie |
| warns about Get() in a loop | tie |
| avoids loop with Get inside without warning | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| calls Topic.Stop() before exit | ✗ | |
| warns about Get() in a loop | ✗ | |
| avoids loop with Get inside without warning | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| calls Topic.Stop() before exit | ✗ | |
| warns about Get() in a loop | ✗ | |
| avoids loop with Get inside without warning | ✓ | |

<details><summary>Baseline answer</summary>

```go
package main

import (
	"context"
	"log"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, "your-project-id")
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	result := client.Topic("your-topic-id").Publish(ctx, &pubsub.Message{Data: []byte("hello")})
	if _, err := result.Get(ctx); err != nil {
		log.Fatal(err)
	}
}
```

The key is `result.Get(ctx)` — it blocks until the publish actually succeeds (or fails), so you know the message went through before `main` returns.

</details>

<details><summary>Skill-loaded answer</summary>

```go
package main

import (
	"context"
	"log"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, "my-project")
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	result := client.Topic("my-topic").Publish(ctx, &pubsub.Message{Data: []byte("hello")})
	if _, err := result.Get(ctx); err != nil {
		log.Fatal(err)
	}
}
```

Calling `result.Get(ctx)` blocks until the publish is acknowledged by the server, so you know it went through before the program exits.

</details>

---

### `offtopic-css-flexbox`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the simplest CSS to vertically and horizontally center a
div inside its parent, using flexbox?
```

**Judge:** **tie** — Both answers provide identical CSS code and essentially the same explanation. The minor differences in wording are negligible and neither answer is materially better than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

```css
.parent {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

That's it. `justify-content: center` handles horizontal centering, and `align-items: center` handles vertical centering. The child `div` needs no special styling.

If the parent needs an explicit height (e.g., to fill the viewport), add something like `min-height: 100vh`.

</details>

<details><summary>Skill-loaded answer</summary>

```css
.parent {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

That's it. `justify-content: center` handles horizontal centering and `align-items: center` handles vertical centering along the flex axes (assuming the default `flex-direction: row`).

If you also want the parent to fill the viewport, add `min-height: 100vh` (or some explicit height), since flexbox centers within the parent's actual dimensions.

</details>

---
