# Eval report: `pubsub`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **8**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.55** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 7/8 | 6 / 0 / 2 | 87% → 93% (+6%) |
| `haiku` | 8/8 | 7 / 0 / 1 | 67% → 96% (+30%) |
| `opus` ¹ | 8/8 | 7 / 0 / 1 | 82% → 100% (+18%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 6 | 5/6 | 6/6 | 6/6 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `duplicate-processing` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `ordering-keys-not-working` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `publish-throughput-low` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `dead-letter-not-working` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `graceful-shutdown` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `flow-control-oom` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `simplest-publish` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-css-flexbox` | tie | ✓ = tie | ✓ = tie | ✓ = tie |

## Per-case detail

### `duplicate-processing`

**Prompt**

```
My Pub/Sub subscriber is processing the same message multiple times
even though I'm calling msg.Ack() at the end of every handler. What's
going on and how do I prevent it?
```

**Judge focus:** The better answer explains at-least-once is the default, recommends
idempotency keyed on msg.ID, and considers slow-handler / lease
extension as a contributing cause before recommending exactly-once.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more thorough and idiomatic for the Go SDK context implied by the question (msg.Ack() style), explicitly diagnosing the goroutine/lease-extension trap as the most common cause, and providing a complete diagnostic checklist. Both answers cover all four rubric criteria, but Answer A's treatment of the slow-handler/lease-extension problem is more precise and actionable, and its use of msg.ID for deduplication is more clearly tied to the Go SDK's actual field name.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies at-least-once as the default | tie |
| recommends idempotency | tie |
| mentions msg.ID for dedup key | skill |
| considers ack deadline / slow handler / lease extension | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `At-least-once` |
| recommends idempotency | ✓ | `Idempoten` |
| mentions msg.ID for dedup key | ✓ | `message_id` |
| considers ack deadline / slow handler / lease extension | ✓ | `Ack deadline` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `ack deadline` |

<details><summary>sonnet: baseline answer</summary>

# Pub/Sub Duplicate Message Processing

## Why This Happens

`msg.Ack()` being called doesn't guarantee exactly-once delivery. Several things can cause redelivery **even after a successful Ack**:

```
Publisher → Pub/Sub → [Subscriber 1] ✓ Ack sent
                    ↘ [Subscriber 2] ← same message redelivered!
```

### Root Causes

| Cause | Explanation |
|-------|-------------|
| **Ack deadline exceeded** | Handler takes longer than `ackDeadline` (default 10s), Pub/Sub assumes failure and redelivers |
| **Ack not confirmed** | Ack is sent but lost in transit; Pub/Sub never received it |
| **Multiple subscribers** | Multiple instances pulling from the same subscription race each other |
| **At-least-once guarantee** | Pub/Sub explicitly guarantees at-least-once, never exactly-once |
| **Subscriber restart** | Process crashes after processing but before Ack is confirmed |

---

## Diagnosing Your Specific Case

```python
import time
import logging

def handler(msg):
    start = time.time()
    logging.info(f"Received message_id={msg.message_id} delivery_attempt={msg.delivery_attempt}")
    
    process(msg)
    
    elapsed = time.time() - start
    logging.info(f"Processing took {elapsed:.2f}s")  # Compare to ackDeadline
    
    msg.ack()
```

**Check `delivery_attempt`** — if it's > 1, the message was redelivered.

---

## Solutions

### 1. Fix Ack Deadline Exceeded (Most Common Cause)

```python
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()

flow_control = pubsub_v1.types.FlowControl(max_messages=10)

# Extend deadline to match your processing time
subscriber.subscribe(
    subscription_path,
    callback=handler,
    flow_control=flow_control,
)
```

**Extend the deadline while processing long tasks:**

```python
def handler(msg):
    # Modify ack deadline dynamically for long-running work
    msg.modify_ack_deadline(60)  # extend by 60 seconds
    
    do_long_running_work()       # your actual processing
    
    msg.ack()
```

Or configure it at the subscription level (max 600s):
```bash
gcloud pubsub subscriptions modify-push-config my-sub \
  --ack-deadline=120
```

---

### 2. Implement Idempotency (Most Robust Solution)

Make your handler safe to run multiple times — this is the **correct long-term fix** regardless of other mitigations:

```python
import redis

redis_client = redis.Redis()
PROCESSED_TTL = 86400  # 24 hours

def handler(msg):
    message_id = msg.message_id
    dedup_key = f"processed:{message_id}"
    
    # Atomic check-and-set
    already_processed = not redis_client.set(
        dedup_key,
        "1",
        nx=True,        # Only set if Not eXists
        ex=PROCESSED_TTL
    )
    
    if already_processed:
        logging.info(f"Skipping duplicate message_id={message_id}")
        msg.ack()       # Still ack it so it stops being redelivered
        return
    
    try:
        process(msg)
        msg.ack()
    except Exception as e:
        redis_client.delete(dedup_key)  # Allow retry on genuine failure
        msg.nack()
        raise
```

---

### 3. Use a Database for Idempotency (Durable Alternative)

```python
# Using a processed_messages table
def handler(msg):
    message_id = msg.message_id
    
    with db.transaction():
        # INSERT ... ON CONFLICT DO NOTHING
        inserted = db.execute("""
            INSERT INTO processed_messages (message_id, processed_at)
            VALUES (%s, NOW())
            ON CONFLICT (message_id) DO NOTHING
        """, [message_id]).rowcount
        
        if inserted == 0:
            msg.ack()
            return
            
        process_and_write_results(msg)  # Same transaction!
    
    msg.ack()
```

> ✅ **Advantage:** Processing and dedup record are atomic — no window where a crash causes reprocessing.

---

### 4. Enable Exactly-Once Delivery (GCP Feature)

```bash
# Create subscription with exactly-once delivery
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-exactly-once-delivery
```

```python
# Ack is now retried automatically until confirmed
# Check if it succeeded
def handler(msg):
    process(msg)
    
    ack_result = msg.ack_with_response()  # Returns a future
    try:
        ack_result.result(timeout=30)     # Blocks until Ack confirmed
    except Exception:
        logging.error("Ack failed — message will be redelivered")
```

> ⚠️ **Caveats:** Higher latency, higher cost, not available in all regions. Still not a substitute for idempotency.

---

## Decision Guide

```
Is processing time > ackDeadline?
├── YES → Extend ackDeadline or use modify_ack_deadline()
└── NO  ↓

Can you make the handler idempotent?
├── YES → Do that first (Redis or DB dedup) ← recommended always
└── NO  ↓

Do you need strict exactly-once?
├── YES → Enable exactly-once delivery + idempotency
└── NO  → Accept at-least-once, fix root cause of duplicates
```

---

## Quick Checklist

- [ ] Log `delivery_attempt` to confirm duplicates are actually happening
- [ ] Compare handler execution time to `ackDeadline`
- [ ] Add idempotency check using `message_id` as dedup key
- [ ] Ensure exceptions don't silently swallow the `ack()` call
- [ ] Consider exactly-once delivery if duplicates are unacceptable

The **most important takeaway**: always design handlers to be idempotent — Pub/Sub's at-least-once guarantee means duplicates are always *possible*, even with exactly-once delivery enabled.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Calling `msg.Ack()` is necessary but not sufficient. There are several independent reasons Pub/Sub redelivers a message even when your code reaches the `Ack()` call. Work through them in order.

---

## 1. Understand what "at-least-once" means

Pub/Sub's default delivery guarantee is **at-least-once**. The service can redeliver any message at any time — network hiccup, server-side failover, ack lost in transit. This is not a bug; it is the contract. **Your handler must be idempotent regardless of what else you fix below.**

---

## 2. Find the actual cause

### Cause A — Processing takes longer than the ack deadline (most common)

Pub/Sub grants a lease on each message. If the lease expires before your ack arrives, the message redelivers — even if your code eventually calls `Ack()`.

The Go SDK extends leases automatically, **but only while the message is live inside the `Receive` callback**. The trap:

```go
// BROKEN — callback returns immediately; lease stops extending
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    go func() {
        doSlowWork(msg)   // lease expired long before this finishes
        msg.Ack()
    }()
})
```

The callback returns, the SDK considers the message "done", lease extension stops, and Pub/Sub redelivers after the deadline.

**Fix — keep work inside the callback, or block until it finishes:**

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    // Work runs synchronously; SDK extends the lease the whole time.
    if err := doSlowWork(ctx, msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

If you need a worker pool, block the callback on a channel so the lease stays alive:

```go
sem := make(chan struct{}, workerCount)

sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    sem <- struct{}{}          // block here — lease keeps extending
    defer func() { <-sem }()
    if err := doSlowWork(ctx, msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

Also check `ReceiveSettings.MaxExtension`. Its default is 60 minutes, but if you set it lower than your actual processing time, leases expire on purpose:

```go
sub.ReceiveSettings.MaxExtension = 30 * time.Minute // raise if needed
```

### Cause B — Subscriber crashed or restarted before the ack was sent

If your process dies after doing the work but before `Ack()` is transmitted, Pub/Sub has no record of the ack and redelivers. This is unavoidable at the transport layer — it is exactly why idempotency is mandatory.

### Cause C — Multiple `Receive` calls on the same subscription

Each concurrent `Receive` call opens an independent `StreamingPull` stream. Pub/Sub can send the same message to more than one stream before either acks it. Never call `Receive` twice on the same subscription handle concurrently. Use `NumGoroutines` inside a single `Receive` call instead:

```go
sub.ReceiveSettings.NumGoroutines = 8  // parallel callbacks, one stream
```

### Cause D — Exactly-once delivery is not enabled

Even with perfect ack discipline, the default subscription can redeliver. Exactly-once delivery reduces (but does not eliminate) duplicates:

```go
// At subscription creation time only — cannot be changed later
subConfig := pubsub.SubscriptionConfig{
    Topic:                     topic,
    EnableExactlyOnceDelivery: true,
}
```

Check whether it is on:

```bash
gcloud pubsub subscriptions describe MY-SUB \
  --format='value(enableExactlyOnceDelivery)'
```

Note: EOD adds latency to every ack and still permits duplicates across subscriber restarts. It is not a substitute for idempotency.

---

## 3. Make your handler idempotent (non-negotiable)

Key on `msg.ID` — it is stable across all redeliveries of the same logical message:

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    if alreadyProcessed(ctx, msg.ID) {
        msg.Ack() // ack so it stops redelivering
        return
    }

    if err := processAndRecord(ctx, msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})

// processAndRecord writes the result AND marks msg.ID as processed
// in a single transaction (e.g., a DB upsert keyed on message_id).
func processAndRecord(ctx context.Context, msg *pubsub.Message) error {
    _, err := db.ExecContext(ctx,
        `INSERT INTO processed_events (message_id, payload, processed_at)
         VALUES ($1, $2, now())
         ON CONFLICT (message_id) DO NOTHING`,
        msg.ID, msg.Data,
    )
    return err
}
```

The `ON CONFLICT DO NOTHING` pattern makes the DB write idempotent. The `alreadyProcessed` check before doing expensive work avoids redundant computation on redeliveries.

---

## 4. Diagnostic checklist

| Check | Command / metric |
|---|---|
| Is the ack deadline long enough? | `gcloud pubsub subscriptions describe MY-SUB --format='value(ackDeadlineSeconds)'` |
| Is the backlog growing? | Cloud Monitoring: `pubsub.googleapis.com/subscription/num_undelivered_messages` |
| Are messages expiring before ack? | `pubsub.googleapis.com/subscription/oldest_unacked_message_age` — if this climbs, processing is slower than the lease |
| Is exactly-once on? | `--format='value(enableExactlyOnceDelivery)'` as above |
| Are there multiple `Receive` calls? | Audit your code; grep for `.Receive(` |

---

## Summary

| Root cause | Fix |
|---|---|
| Work handed off to goroutine; callback returns early | Keep work synchronous inside callback, or block callback on a semaphore |
| `MaxExtension` shorter than processing time | Raise `ReceiveSettings.MaxExtension` |
| Process crash between work and ack | Idempotent handler keyed on `msg.ID` — unavoidable otherwise |
| Multiple concurrent `Receive` calls | Use `NumGoroutines` inside one `Receive` call |
| Default at-least-once subscription | Enable `EnableExactlyOnceDelivery` **and** keep idempotent handler |

The single most important fix is always the idempotent handler. Everything else reduces redelivery frequency; idempotency makes redelivery harmless.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is significantly more comprehensive and better aligned with the rubric criteria. It explicitly leads with at-least-once as the default, provides a concrete idempotency example keyed on msg.ID with database unique constraints, and gives a detailed explanation of ack deadline/lease extension including the goroutine pitfall. Answer A covers these topics but less precisely — it mentions idempotency and msg.ID but buries the at-least-once explanation, and its lease extension discussion is shallower without explaining the goroutine/async return problem.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies at-least-once as the default | skill |
| recommends idempotency | skill |
| mentions msg.ID for dedup key | skill |
| considers ack deadline / slow handler / lease extension | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `Idempoten` |
| mentions msg.ID for dedup key | ✓ | `message_id` |
| considers ack deadline / slow handler / lease extension | ✓ | `Ack Deadline` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `At-Least-Once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `Ack Deadline` |

<details><summary>haiku: baseline answer</summary>

# Pub/Sub Duplicate Message Processing

This is a common issue with Pub/Sub subscribers. Here are the main causes and solutions:

## 1. **Ack Deadline Exceeded** (Most Common)

If your message handler takes longer than the ack deadline, Pub/Sub assumes processing failed and redelivers the message.

**Solution:** Increase the ack deadline or extend it during processing

```python
from google.cloud import pubsub_v1
import time

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

def callback(message):
    try:
        # Long-running operation
        process_message(message)
        message.ack()
    except Exception as e:
        print(f"Error: {e}")
        message.nack()  # Requeue on failure

# Increase ack deadline to 600 seconds (max)
flow_control = pubsub_v1.types.FlowControl(max_messages=10, max_bytes=1000)
streaming_pull_future = subscriber.subscribe(
    subscription_path, 
    callback=callback,
    flow_control=flow_control
)

# Set ack deadline on subscription (via gcloud or API)
# gcloud pubsub subscriptions update SUB_ID --ack-deadline=600
```

## 2. **Ack Before Processing Completes**

Calling `ack()` too early before async operations finish.

**Solution:** Only ack after all processing is complete

```python
def callback(message):
    try:
        # Process synchronously
        result = process_message(message)
        save_to_database(result)  # Wait for this
        message.ack()  # Ack only after everything is done
    except Exception as e:
        message.nack()
```

## 3. **Subscriber Crashes Before Ack**

Process dies between message receipt and ack.

**Solution:** Use proper error handling and graceful shutdown

```python
import signal
import sys

def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    streaming_pull_future.cancel()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def callback(message):
    try:
        process_message(message)
        message.ack()
    except Exception as e:
        print(f"Processing failed: {e}")
        message.nack()  # Requeue for retry

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
streaming_pull_future.result()
```

## 4. **Idempotency Issues**

Even with proper acking, Pub/Sub guarantees "at-least-once" delivery. Duplicates can still occur.

**Solution:** Make your handler idempotent

```python
def callback(message):
    message_id = message.message_id
    
    # Check if already processed
    if is_already_processed(message_id):
        message.ack()
        return
    
    try:
        process_message(message)
        mark_as_processed(message_id)
        message.ack()
    except Exception as e:
        message.nack()

def is_already_processed(message_id):
    # Check in database, cache, or deduplication service
    return db.exists(f"processed:{message_id}")

def mark_as_processed(message_id):
    db.set(f"processed:{message_id}", True, ex=86400)  # 24h TTL
```

## Quick Checklist

- ✅ Increase ack deadline if processing takes time
- ✅ Only ack after all processing completes
- ✅ Handle exceptions and nack on failure
- ✅ Implement graceful shutdown
- ✅ Make handlers idempotent
- ✅ Monitor for slow processing with logs

Which language/framework are you using? I can provide more specific code examples.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Duplicate Message Processing in Pub/Sub

This is the most common Pub/Sub gotcha. The root cause is almost always one of these three issues:

## 1. **At-Least-Once Delivery is the Default**

Pub/Sub guarantees **at-least-once delivery by default**, not exactly-once. This means:
- A message can be delivered multiple times even if you ack it correctly.
- Duplicates happen across subscriber restarts, network hiccups, or internal Pub/Sub retries.
- **Your handler MUST be idempotent** — the only durable defense.

**Check your subscription:**
```bash
gcloud pubsub subscriptions describe YOUR_SUB --format='value(enableExactlyOnceDelivery)'
```

If it returns `False`, you're on at-least-once. This is expected and correct — but your code must handle it.

---

## 2. **Your Handler is Not Idempotent**

Every side effect (database write, API call, message publish) must be keyed on a stable identifier so re-execution has no additional effect.

**❌ Not idempotent:**
```go
func handleMessage(ctx context.Context, msg *pubsub.Message) {
    var order Order
    json.Unmarshal(msg.Data, &order)
    
    // If this runs twice, you charge the customer twice
    db.Exec("INSERT INTO charges (customer_id, amount) VALUES (?, ?)", 
        order.CustomerID, order.Amount)
    
    msg.Ack()
}
```

**✅ Idempotent (keyed on msg.ID):**
```go
func handleMessage(ctx context.Context, msg *pubsub.Message) {
    var order Order
    json.Unmarshal(msg.Data, &order)
    
    // Upsert keyed on message ID — second execution is a no-op
    db.Exec(`
        INSERT INTO charges (message_id, customer_id, amount) 
        VALUES (?, ?, ?)
        ON CONFLICT(message_id) DO NOTHING
    `, msg.ID, order.CustomerID, order.Amount)
    
    msg.Ack()
}
```

**Key points:**
- `msg.ID` is server-assigned and stable across redeliveries — use it as a dedup key.
- Alternatively, use a business key (e.g., `order_id`) if it's unique per message.
- Add a unique constraint on the dedup column so the database enforces idempotency.

---

## 3. **Ack Deadline Expiration (Lease Extension Failure)**

If your handler takes longer than the ack deadline (default 10 seconds), the message lease expires and Pub/Sub redelivers it **even though you call `msg.Ack()`** at the end.

**Why this happens:**
- Pub/Sub extends the lease automatically **only while your callback is running**.
- If the callback returns before the work is done (e.g., you spawn a goroutine and return), the lease stops extending.
- When the deadline passes, Pub/Sub assumes the handler crashed and redelivers.

**❌ Broken (spawns goroutine and returns):**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    go func() {
        // This runs AFTER the callback returns
        // Lease is no longer extending — message redelivers in ~10s
        time.Sleep(30 * time.Second)
        processOrder(msg)
        msg.Ack()
    }()
    // Callback returns immediately — lease stops extending
})
```

**✅ Correct (synchronous work inside callback):**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    // All work happens here, synchronously
    // Lease extends automatically while this runs
    time.Sleep(30 * time.Second)
    processOrder(msg)
    msg.Ack()
    // Callback returns only after work is done
})
```

**If you need async work, use a bounded worker pool:**
```go
type WorkerPool struct {
    jobs chan *pubsub.Message
}

func (wp *WorkerPool) Start(ctx context.Context, numWorkers int) {
    for i := 0; i < numWorkers; i++ {
        go func() {
            for msg := range wp.jobs {
                processOrder(msg)
                msg.Ack()
            }
        }()
    }
}

sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    // Non-blocking send to worker pool
    select {
    case wp.jobs <- msg:
    case <-ctx.Done():
        msg.Nack()
    }
    // Callback returns, but lease extends until worker acks
})
```

**Tune the ack deadline if processing is genuinely slow:**
```go
sub.ReceiveSettings.MaxExtension = 10 * time.Minute  // Up to 10 min per message
```

But this is a band-aid — if messages take 10+ minutes, consider an external work queue (Cloud Tasks, Firestore, etc.) instead.

---

## 4. **Enable Exactly-Once Delivery (Optional, After Idempotency)**

If you've made your handler idempotent and still want stronger guarantees, enable exactly-once delivery:

```bash
gcloud pubsub subscriptions update YOUR_SUB --enable-exactly-once-delivery
```

**Important caveats:**
- EOD adds ~5–10ms latency to every ack (it writes to Firestore).
- It **still permits some duplicates** around subscriber restarts (within a ~1-hour dedup window).
- **Idempotency is still required** — EOD is not a substitute.
- Use EOD only if the extra latency is acceptable and you need stronger guarantees for compliance reasons.

---

## Diagnostic Checklist

1. **Is your handler idempotent?**
   - Every side effect keyed on `msg.ID` or a business key?
   - Unique constraint in the database?

2. **Does your handler finish before the ack deadline?**
   - Check logs for processing time.
   - If >10s, either raise `MaxExtension` or refactor to async with a worker pool.

3. **Are you calling `msg.Ack()` inside the callback, not in a spawned goroutine?**
   - The callback must not return until all work is done.

4. **Is the subscription on at-least-once or exactly-once?**
   - At-least-once is the default and is fine — just be idempotent.
   - Exactly-once is optional and adds latency; only enable if you've already fixed idempotency.

---

## Summary

| Root Cause | Fix |
|---|---|
| Handler not idempotent | Add `msg.ID` dedup key + unique constraint |
| Processing time > ack deadline | Raise `MaxExtension` or use worker pool |
| Async work in spawned goroutine | Move work into callback or use bounded worker pool |
| Want stronger guarantees | Enable exactly-once delivery **after** fixing idempotency |

**The golden rule:** Make your handler idempotent first. Everything else is tuning.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A more thoroughly addresses all four rubric criteria, particularly the slow-handler/lease-extension cause which it explains in depth with the goroutine handoff anti-pattern as a distinct cause. Answer A also provides a clearer prioritization (idempotency first, then deadline tuning, then exactly-once) and explicitly warns that exactly-once delivery is not a substitute for idempotency. Answer B covers the criteria but less deeply, and introduces some tangential points (panics, context cancellation) that dilute focus from the core issues.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies at-least-once as the default | tie |
| recommends idempotency | skill |
| mentions msg.ID for dedup key | tie |
| considers ack deadline / slow handler / lease extension | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `Ack Deadline` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `ack deadline` |

<details><summary>opus: baseline answer</summary>

# Why You're Seeing Duplicate Pub/Sub Messages

Pub/Sub guarantees **at-least-once** delivery, not exactly-once. Calling `msg.Ack()` at the end of your handler doesn't guarantee the message won't be redelivered. Here are the most common causes:

## 1. Ack Deadline Exceeded (Most Common)

If your handler takes longer than the subscription's **ack deadline** (default 10s), Pub/Sub assumes the message was lost and redelivers it — even if you eventually call `Ack()`.

**Fix:** The Go client library extends the deadline automatically via a lease manager, but only up to `MaxExtension` (default 60 min). Tune it:

```go
sub := client.Subscription("my-sub")
sub.ReceiveSettings.MaxExtension = 30 * time.Minute
sub.ReceiveSettings.MaxExtensionPeriod = 10 * time.Minute
sub.ReceiveSettings.MinExtensionPeriod = 60 * time.Second
```

If your handler genuinely takes longer than `MaxExtension`, raise it or shorten the work.

## 2. Handler Panics or Blocks Before `Ack()`

If your code panics, errors out early, or blocks on a channel/lock, `Ack()` never runs.

```go
sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    defer func() {
        if r := recover(); r != nil {
            log.Printf("panic: %v", r)
            m.Nack() // or Ack() if you want to drop it
        }
    }()
    // ... work ...
    m.Ack()
})
```

## 3. Ack Sent After Context Cancellation

Acks are sent over a streaming connection. If `ctx` is canceled (subscriber shutdown) before the ack actually flushes to the server, the message will be redelivered. Make sure you drain in-flight messages before exiting.

## 4. Pub/Sub Inherently Allows Duplicates

Even with perfect handler code, duplicates **will** occasionally happen due to:
- Network issues between the client and Pub/Sub
- Acks being lost in transit
- Republishes at the publisher side

This is by design.

## How to Actually Prevent Duplicate **Processing**

You have two options:

### Option A: Make your handler idempotent
Use a unique ID (either `msg.ID` or a business key in attributes) and deduplicate via:
- A database UNIQUE constraint
- Redis `SETNX` with TTL
- An idempotency table you check before processing

```go
ok, err := redis.SetNX(ctx, "msg:"+m.ID, 1, 24*time.Hour).Result()
if err != nil { m.Nack(); return }
if !ok { m.Ack(); return } // already processed
// ... do work ...
m.Ack()
```

### Option B: Enable Exactly-Once Delivery
On the subscription, enable exactly-once. It dramatically reduces (but doesn't entirely eliminate, across long timeframes) redelivery:

```bash
gcloud pubsub subscriptions update my-sub --enable-exactly-once-delivery
```

In Go, check the ack response so you know it was committed:

```go
sub.ReceiveSettings.EnableMessageOrdering = false // optional
sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    if err := doWork(m); err != nil {
        m.Nack()
        return
    }
    ar := m.AckWithResult()
    if _, err := ar.Get(ctx); err != nil {
        // ack was rejected — message may redeliver, don't commit side effects
        log.Printf("ack failed: %v", err)
    }
})
```

With exactly-once enabled, `AckWithResult()` lets you confirm the ack was actually accepted before committing irreversible side effects.

## TL;DR

`msg.Ack()` doesn't prevent redelivery — it just *tries to*. The realistic answer:

1. Check your handler isn't exceeding the ack deadline (raise `MaxExtension`).
2. Make sure `Ack()` actually runs (handle panics, errors).
3. **Design your consumer to be idempotent** — this is the only robust solution.
4. Optionally enable exactly-once delivery and use `AckWithResult()`.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Why you're seeing duplicates

Pub/Sub is **at-least-once by default** — duplicates are part of the contract, not a bug. Calling `msg.Ack()` doesn't prevent them. There are three common causes; you likely have one or more.

## Cause 1: Your handler is slower than the ack deadline

This is the most common cause. When `Subscription.Receive` invokes your callback, the Go SDK leases the message and **automatically extends the lease in the background** while your callback is running — but only up to `ReceiveSettings.MaxExtension` (default ~60 minutes, but the per-extension call still has to win the race against the ack deadline).

If your handler runs longer than the deadline (default 10s) and the lease-extension goroutine falls behind for any reason — slow network to Pub/Sub, GC pause, the SDK couldn't `modifyAckDeadline` in time — Pub/Sub considers the message un-acked and **redelivers it to another subscriber (or back to you)**, even though you eventually call `Ack()`. Your `Ack()` succeeds, but the duplicate is already in flight.

**Diagnose:**
```bash
gcloud pubsub subscriptions describe SUB_NAME \
  --format='value(ackDeadlineSeconds)'
```
Then compare to your handler's p99 latency.

**Fix:** raise the ack deadline at the subscription level (up to 600s), or for very long jobs, raise `ReceiveSettings.MaxExtension` and let the SDK keep the lease alive:
```go
sub.ReceiveSettings.MaxExtension = 30 * time.Minute
```

## Cause 2: You're handing work off to a goroutine inside the callback

This is the silent killer. If your callback does:

```go
sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    go process(m)   // ❌ callback returns immediately
    m.Ack()         // ❌ or worse, ack before processing finishes
})
```

…the SDK sees the callback return and **stops extending the lease**. The message redelivers as soon as the deadline expires. Even if you ack inside the goroutine, the redelivery is already on the wire.

**Fix:** do the work synchronously in the callback. If you need a worker pool, have the callback `select` on a channel and block until the worker reports completion:

```go
sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    done := make(chan error, 1)
    workQueue <- job{msg: m, done: done}
    if err := <-done; err != nil {
        m.Nack()
        return
    }
    m.Ack()
})
```

## Cause 3: Genuine at-least-once duplicates you can't engineer away

Even with a 10ms handler and a healthy lease, you'll occasionally get duplicates from:
- Subscriber crashes between processing and ack landing on the server
- Network partitions where your `Ack()` RPC didn't reach Pub/Sub
- Rebalancing across StreamingPull streams

**There is no configuration that eliminates these.** Even enabling exactly-once delivery (`EnableExactlyOnceDelivery=true` on the subscription) only *reduces* duplicates and adds latency to every ack — duplicates can still occur around subscriber restarts.

**The only durable fix is an idempotent handler.** Key your side effects on `msg.ID` (server-assigned, stable across redeliveries of the same message) or a business key with a uniqueness constraint:

```go
sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    // Insert into a dedup table with msg.ID as PK; ON CONFLICT DO NOTHING.
    // Or check before doing the side effect.
    inserted, err := db.ExecContext(ctx,
        `INSERT INTO processed_messages (id) VALUES ($1) ON CONFLICT DO NOTHING`,
        m.ID)
    if err != nil { m.Nack(); return }
    rows, _ := inserted.RowsAffected()
    if rows == 0 {
        m.Ack() // already processed; ack and move on
        return
    }
    if err := doTheRealWork(ctx, m); err != nil {
        m.Nack()
        return
    }
    m.Ack()
})
```

# Order of operations

1. **Make the handler idempotent first.** This protects you from all three causes and from future ones you haven't thought of.
2. **Then check handler latency vs. ack deadline.** If p99 is anywhere near the deadline, raise the deadline or `MaxExtension`. This reduces the *rate* of duplicates so you stop wasting work re-processing.
3. **Audit for goroutine handoffs in the callback.** Fix any you find.
4. **Only then consider exactly-once delivery** if your duplicate rate is still operationally painful. It's not a substitute for steps 1–3.

If you can share your `Receive` callback code and the subscription's `ackDeadlineSeconds`, I can point at the specific issue.

</details>

---

### `ordering-keys-not-working`

**Prompt**

```
I set OrderingKey on my Pub/Sub messages when publishing but the
subscriber is still receiving them out of order. What's wrong?
```

**Judge focus:** The better answer pinpoints that EnableMessageOrdering must be set
on BOTH publisher AND subscription, mentions ResumePublish on error,
and is clear that ordering is per-key, not global.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core requirements, but Answer B is more technically precise and accurate. Answer B correctly clarifies that EnableMessageOrdering on the subscription is set at creation time (not on the subscriber client), while Answer A conflates the subscription resource property with a subscriber client option. Answer B also provides a clearer explanation of ResumePublish with proper error handling context, and its per-key ordering explanation is more precise about what 'ordering' actually means in the subscriber callback context.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| requires EnableMessageOrdering on both sides | skill |
| mentions EnableMessageOrdering by name | tie |
| clarifies per-key, not global | tie |
| mentions ResumePublish | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `subscriptionName, receiver)     .setEnableMessageOrdering` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `Same OrderingKey` |
| mentions ResumePublish | ✓ | `resume after error publish` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `both** the publisher` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `same key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

<details><summary>sonnet: baseline answer</summary>

## Pub/Sub Message Ordering Troubleshooting

Setting `OrderingKey` on the publisher side is only **half the requirement**. Here are the most common reasons messages are still arriving out of order:

---

## 1. ✅ Enable Message Ordering on the Subscriber Client

This is the **most common mistake**. You must explicitly enable ordering on the subscriber client, not just the publisher.

```python
# Python example
from google.cloud import pubsub_v1

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# You must set enable_message_ordering=True here
flow_control = pubsub_v1.types.FlowControl()
subscriber.subscribe(
    subscription_path,
    callback=callback,
    enable_message_ordering=True  # ← THIS IS REQUIRED
)
```

```java
// Java example
Subscriber subscriber = Subscriber.newBuilder(subscriptionName, receiver)
    .setEnableMessageOrdering(true)  // ← THIS IS REQUIRED
    .build();
```

---

## 2. ✅ Enable Message Ordering on the Subscription (GCP Console / Terraform)

The **subscription itself** must have message ordering enabled at creation time.

```bash
# gcloud
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-message-ordering   # ← Required flag
```

```hcl
# Terraform
resource "google_pubsub_subscription" "example" {
  name  = "my-sub"
  topic = google_pubsub_topic.example.name

  enable_message_ordering = true  # ← Required
}
```

> ⚠️ **Note:** This cannot be changed after the subscription is created. You must delete and recreate it.

---

## 3. ✅ Publisher Must Also Enable Ordering

```python
# Python publisher
publisher = pubsub_v1.PublisherClient(
    publisher_options=pubsub_v1.types.PublisherOptions(
        enable_message_ordering=True  # ← Required on publisher too
    )
)
```

---

## 4. ✅ Use the Same OrderingKey for Related Messages

Messages are only ordered **within the same ordering key**. Different keys are independent.

```python
# These will be ordered relative to each other
publisher.publish(topic_path, b"msg1", ordering_key="user-123")
publisher.publish(topic_path, b"msg2", ordering_key="user-123")

# This has NO ordering guarantee relative to the above
publisher.publish(topic_path, b"msg3", ordering_key="user-456")
```

---

## 5. ✅ Handle Publisher Errors Correctly (Resume After Error)

If a publish fails for an ordering key, you **must explicitly resume** that key or all subsequent messages for that key will be rejected.

```python
# Python - resume after error
publisher.resume_publish(topic_path, ordering_key="user-123")
```

> Without this, the client intentionally blocks further messages on that key to prevent gaps in ordering.

---

## 6. ✅ Don't Use Multiple Subscriber Instances Pulling the Same Subscription

Multiple concurrent subscribers on the same subscription will break ordering since messages can be dispatched to different instances.

---

## Quick Checklist

| Requirement | Where |
|---|---|
| `enable_message_ordering=True` | Publisher client |
| `enable_message_ordering=True` | Subscriber client |
| `--enable-message-ordering` | Subscription resource |
| Same `ordering_key` for related messages | Each published message |
| Resume publish after errors | Publisher error handling |
| Single subscriber instance | Deployment architecture |

---

The **most likely culprit** is that the subscription resource itself was created without ordering enabled, or the subscriber client is missing `enable_message_ordering=True`.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Ordering in Pub/Sub requires **both sides** to opt in, and there are a few other ways it can silently break. Here's a systematic diagnosis.

## The Most Common Cause: Only One Side Has Ordering Enabled

Ordering requires `EnableMessageOrdering = true` on **both** the publisher topic handle **and** the subscription. Setting it on only one side silently disables the guarantee.

**Publisher side (Go):**
```go
topic := client.Topic("my-topic")
topic.EnableMessageOrdering = true  // ← must be set
```

**Subscription side — set at create/update time, not in the subscriber client:**
```go
// At subscription creation:
sub, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic:                 topic,
    EnableMessageOrdering: true,  // ← must be set here
})
```

Check your existing subscription:
```bash
gcloud pubsub subscriptions describe my-sub \
  --format='value(enableMessageOrdering)'
```

If it prints `False`, you need to **recreate the subscription** — this property cannot be changed on an existing subscription.

---

## The Other Failure Modes

### 1. Inconsistent or missing ordering keys

Every message that needs to be ordered relative to others must carry the **same non-empty ordering key**. Messages with different keys, or no key, are unordered relative to each other — by design.

```go
// ✅ All related messages share the same key
result := topic.Publish(ctx, &pubsub.Message{
    Data:        payload,
    OrderingKey: "customer-123",  // same key = ordered delivery
})

// ❌ Empty key — ordering is disabled for this message
result := topic.Publish(ctx, &pubsub.Message{
    Data:        payload,
    OrderingKey: "",  // treated as unordered
})
```

### 2. A publish error paused the key — and you didn't resume it

When a publish fails for a given ordering key, the client **stops accepting new publishes for that key** to prevent gaps in the sequence. Subsequent publishes return an error immediately. You must explicitly resume:

```go
result := topic.Publish(ctx, &pubsub.Message{
    Data:        []byte("event"),
    OrderingKey: "customer-123",
})
if _, err := result.Get(ctx); err != nil {
    // The key is now paused. Resume before publishing again.
    topic.ResumePublish("customer-123")
    // Then retry the failed message first, before new ones.
}
```

If you silently swallow publish errors and keep publishing, those messages go through while the failed one is dropped — producing gaps that look like out-of-order delivery.

### 3. Multiple publisher instances without coordination

Ordering is guaranteed **within a single publisher client** for a given key. If two separate processes publish to the same ordering key concurrently, Pub/Sub cannot guarantee their relative order — there's no distributed sequencing across publishers.

```
Publisher A: key="user-1" → msg 1, msg 3
Publisher B: key="user-1" → msg 2, msg 4
                                    ↑ interleaved, order undefined
```

For strict ordering, route all messages for a given key through a single publisher instance.

### 4. The subscriber is processing messages concurrently

Even with ordering enabled, if your subscriber callback spawns goroutines or hands work off asynchronously, **you** are processing out of order — Pub/Sub delivered them correctly but your code reordered them.

```go
// ❌ Breaks ordering — callback returns immediately, goroutines race
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    go func() {
        process(msg)  // concurrent, unordered execution
        msg.Ack()
    }()
})

// ✅ Preserves ordering — process synchronously before returning
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    process(msg)  // blocks until done
    msg.Ack()
})
```

With `EnableMessageOrdering = true` on the subscription, the SDK delivers messages for the same key **one at a time** — the next message for that key is not dispatched until the current callback returns and acks/nacks.

---

## Diagnostic Checklist

| Check | Command / Code |
|---|---|
| Subscription has ordering enabled | `gcloud pubsub subscriptions describe my-sub --format='value(enableMessageOrdering)'` |
| Publisher topic handle has ordering enabled | Look for `topic.EnableMessageOrdering = true` before first `Publish` call |
| All messages carry the same non-empty key | Log `msg.OrderingKey` on receipt; confirm no empty strings |
| Publish errors are handled and `ResumePublish` called | Audit error handling on every `result.Get(ctx)` |
| Subscriber callback is synchronous | Confirm no `go func()` inside the callback |
| Only one publisher per ordering key | Check your deployment topology |

Fix the subscription first (recreate if needed), then work through the rest of the list — the subscription flag is the most common miss and the only one that requires infrastructure changes.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies that EnableMessageOrdering must be set on both the publisher and the subscription, names the setting explicitly, clarifies per-key ordering, and mentions ResumePublish for error recovery. Answer B incorrectly focuses on flow control as the primary fix and never mentions EnableMessageOrdering by name or ResumePublish, making it fundamentally wrong about the root cause.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| requires EnableMessageOrdering on both sides | skill |
| mentions EnableMessageOrdering by name | skill |
| clarifies per-key, not global | skill |
| mentions ResumePublish | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✗ | |
| mentions EnableMessageOrdering by name | ✗ | |
| clarifies per-key, not global | ✓ | `same `OrderingKey` |
| mentions ResumePublish | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `BOTH the publisher AND the subscri` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per-key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

<details><summary>haiku: baseline answer</summary>

# Pub/Sub Message Ordering Issues

If you're setting `OrderingKey` but still receiving messages out of order, here are the most common causes:

## 1. **Subscriber Not Configured for Ordered Delivery** ⚠️ (Most Common)

You must explicitly enable ordered delivery on the **subscriber side**:

```python
# Python
subscriber = pubsub_v1.SubscriberClient()
flow_control = pubsub_v1.types.FlowControl(max_messages=100)
subscription_path = subscriber.subscription_path(project_id, subscription_id)

future = subscriber.subscribe(
    subscription_path,
    callback,
    flow_control=flow_control  # Required for ordering
)
```

```java
// Java
Subscriber subscriber = Subscriber.newBuilder(subscriptionName, receiver)
    .setFlowControl(
        FlowControl.newBuilder()
            .setMaxOutstandingMessages(100)
            .build())
    .build();
subscriber.startAsync();
```

## 2. **Flow Control Not Set Properly**

Ordering requires **sequential processing**. Ensure:
- `max_messages` is set (typically 100 or less)
- `max_bytes` is configured appropriately
- Messages are processed sequentially, not in parallel

```python
# ❌ Wrong - no flow control
subscriber.subscribe(subscription_path, callback)

# ✅ Correct
flow_control = pubsub_v1.types.FlowControl(
    max_messages=100,
    max_bytes=1000*1024*1024
)
subscriber.subscribe(subscription_path, callback, flow_control=flow_control)
```

## 3. **Different OrderingKeys Used**

Messages with **different OrderingKeys** are processed independently:

```python
# These will be ordered relative to each other
publisher.publish(topic_path, data, ordering_key="user-123")
publisher.publish(topic_path, data, ordering_key="user-123")

# These won't be ordered with the above (different key)
publisher.publish(topic_path, data, ordering_key="user-456")
```

## 4. **Subscriber Crashes/Restarts**

If your subscriber crashes while processing a message:
- That message is redelivered
- Ordering resumes from that point
- **Solution**: Implement proper error handling and idempotent processing

```python
def callback(message):
    try:
        process_message(message)
        message.ack()
    except Exception as e:
        # Don't ack - message will be redelivered
        logger.error(f"Failed to process: {e}")
```

## 5. **Verify OrderingKey is Actually Set**

Double-check that `OrderingKey` is being published:

```python
# ✅ Correct
future = publisher.publish(
    topic_path,
    data=b"message",
    ordering_key="my-key"  # Must be non-empty string
)

# ❌ Wrong - empty ordering key
future = publisher.publish(topic_path, data=b"message", ordering_key="")
```

## Quick Checklist

- [ ] `OrderingKey` is set on **all** published messages
- [ ] Subscriber has `FlowControl` configured with `max_messages`
- [ ] Using same `OrderingKey` for messages that should be ordered
- [ ] Subscriber processes messages sequentially (not parallel)
- [ ] No subscriber crashes without proper error handling

What language/framework are you using? I can provide more specific code examples.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Ordering Key Not Working: Diagnosis

You've hit the most common ordering-key trap: **ordering is only enforced if `EnableMessageOrdering = true` on BOTH the publisher AND the subscription.** Setting it on only one side silently disables ordering.

## Checklist

### 1. Publisher Side
Verify your `Topic` has ordering enabled:

```go
topic := client.Topic("my-topic")
topic.PublishSettings.EnableMessageOrdering = true

// Then publish with an ordering key
result := topic.Publish(ctx, &pubsub.Message{
    Data:      []byte("..."),
    OrderingKey: "user-123",  // ← Must be set
})
```

**Check:** Run `gcloud pubsub topics describe my-topic --format='value(messageStoragePolicy)'` — this won't show ordering status (it's a publisher-side setting), but confirm the topic exists and is in the right region.

### 2. Subscription Side (The Likely Culprit)
Ordering is a **subscription-level config**, not a runtime flag in the Go subscriber. Check if it's enabled:

```bash
gcloud pubsub subscriptions describe my-subscription \
  --format='value(enableMessageOrdering)'
```

If it returns `False` or is absent, **that's your problem.** You must enable it at subscription creation or update:

```bash
# Create with ordering enabled
gcloud pubsub subscriptions create my-subscription \
  --topic=my-topic \
  --enable-message-ordering

# Or update an existing subscription
gcloud pubsub subscriptions update my-subscription \
  --enable-message-ordering
```

**In Go code**, you cannot toggle this at runtime on an existing subscription. If you're creating a new one:

```go
sub, err := client.CreateSubscription(ctx, "my-subscription", pubsub.SubscriptionConfig{
    Topic:                   topic,
    EnableMessageOrdering:   true,  // ← Set at creation
})
```

### 3. Verify the Ordering Key is Actually Set
In your publisher, confirm every message has a non-empty `OrderingKey`:

```go
result := topic.Publish(ctx, &pubsub.Message{
    Data:       []byte("event data"),
    OrderingKey: "user-123",  // ← Must not be ""
})
```

An empty ordering key (`""`) disables ordering for that message.

### 4. Check for Publish Errors
If a publish fails (e.g., quota exceeded, schema validation), **all subsequent publishes for that ordering key are blocked** until you call `Topic.ResumePublish(orderingKey)`:

```go
result := topic.Publish(ctx, &pubsub.Message{
    Data:       []byte("..."),
    OrderingKey: "user-123",
})

err := result.Get(ctx)
if err != nil {
    log.Printf("Publish failed: %v", err)
    // Unblock this ordering key
    topic.ResumePublish("user-123")
}
```

If you don't resume, the key stays blocked and messages queue indefinitely.

## What "In Order" Actually Means

Pub/Sub guarantees **per-key ordering only**, not global ordering:
- Messages with `OrderingKey: "user-123"` arrive in publish order.
- Messages with `OrderingKey: "user-456"` arrive in publish order.
- But messages from different keys can interleave.

If you're seeing messages from the *same* key out of order, the subscription's `EnableMessageOrdering` is definitely `false`.

## Quick Fix

```bash
# 1. Check current state
gcloud pubsub subscriptions describe my-subscription \
  --format='value(enableMessageOrdering)'

# 2. If false, enable it
gcloud pubsub subscriptions update my-subscription \
  --enable-message-ordering

# 3. Verify
gcloud pubsub subscriptions describe my-subscription \
  --format='value(enableMessageOrdering)'
```

Then republish a batch of messages with the same `OrderingKey` — they should now arrive in order.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly covers all four rubric criteria: it names EnableMessageOrdering on both publisher and subscription, clarifies that ordering is per-key (not global), and prominently explains ResumePublish with a concrete code example. Answer A mentions most of these but treats ResumePublish only briefly and indirectly (as a 'stall' issue) without naming the method or showing how to call it.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| requires EnableMessageOrdering on both sides | tie |
| mentions EnableMessageOrdering by name | skill |
| clarifies per-key, not global | tie |
| mentions ResumePublish | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `on the subscription` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per-key` |
| mentions ResumePublish | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `EnableMessageOrdering: true, }) ```  Check an existing subscription:  ```bash gcloud pubsub subscr` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

<details><summary>opus: baseline answer</summary>

There are several common reasons ordering breaks even when you set `OrderingKey`. Check these:

## 1. Message ordering not enabled on the subscription
This is the most common issue. Setting `OrderingKey` on the publisher side does **nothing** unless the subscription has message ordering enabled.

```bash
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-message-ordering
```

You can't enable this on an existing subscription — you must recreate it.

Verify with:
```bash
gcloud pubsub subscriptions describe my-sub
# Look for: messageOrderingEnabled: true
```

## 2. Publisher not configured for ordering
The publisher client must also be configured to enable ordering. By default it's off in most client libraries.

**Go:**
```go
client.Publisher(topicID).EnableMessageOrdering = true
```

**Python:**
```python
publisher_options = pubsub_v1.types.PublisherOptions(
    enable_message_ordering=True
)
publisher = pubsub_v1.PublisherClient(publisher_options=publisher_options)
```

**Java:**
```java
Publisher.newBuilder(topicName)
    .setEnableMessageOrdering(true)
    .build();
```

Without this, the client may batch/parallelize publishes and ordering keys are effectively ignored.

## 3. Regional endpoint required
Ordering requires publishing through a **regional endpoint**, not the global one, for guarantees to hold:
```
us-east1-pubsub.googleapis.com:443
```
Most client libraries handle this automatically when ordering is enabled, but if you've overridden the endpoint, check it.

## 4. Multiple subscriber clients / high concurrency
Ordering is guaranteed **per ordering key, per subscriber client**. If you have multiple subscriber instances, messages with the same key still go to one client, but:
- If your subscriber processes messages in multiple threads/goroutines without serializing per-key, you'll see out-of-order processing in your application code even though delivery was ordered.
- Ack messages **before** processing the next one for that key.

## 5. A nack or unacked message blocks the key
If a message with an ordering key is nacked or expires, subsequent messages for that key are paused. After resuming, ordering may appear off if you mix old retries with new messages — but this usually manifests as stalls, not reordering.

## 6. Different ordering keys
Ordering is only guaranteed within the **same** ordering key. Messages with different keys can arrive in any order relative to each other.

---

**Quickest diagnostic:** Run `gcloud pubsub subscriptions describe <sub>` and confirm `messageOrderingEnabled: true`. If it's missing or false, that's your problem — recreate the subscription.

</details>

<details><summary>opus: skill-loaded answer</summary>

Setting `OrderingKey` on the message is only step 1 of 3. Pub/Sub silently delivers out of order if any one of these is missing:

## The 3 things you need

### 1. Enable ordering on the **publisher** `Topic` handle

```go
topic := client.Topic("my-topic")
topic.EnableMessageOrdering = true   // ← required, easy to forget
```

Without this, the Go client will accept your `OrderingKey` but won't actually serialize publishes per key. This is the most common cause.

### 2. Enable ordering on the **subscription** (at create time)

```bash
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-message-ordering
```

Or in Go, when creating:

```go
client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic:                 topic,
    EnableMessageOrdering: true,
})
```

Check an existing subscription:

```bash
gcloud pubsub subscriptions describe my-sub \
  --format='value(enableMessageOrdering)'
```

If this prints `False`, ordering is off and **you cannot turn it on after the fact** — you must recreate the subscription. This is the second most common cause.

### 3. Same region for publisher and subscriber, same `OrderingKey` value

Ordering is guaranteed only **per key, within a region**. Messages with different keys can interleave freely. Empty string `""` is treated as "no ordering key" — those messages are unordered.

## Other things that can break ordering

- **A publish error on a key blocks all subsequent publishes for that key.** Once any message with `OrderingKey="user-42"` fails, every later publish with that key returns an error until you call:
  ```go
  topic.ResumePublish("user-42")
  ```
  Always check `PublishResult.Get()` errors and call `ResumePublish` on failure, otherwise the key goes "stuck" and your subscriber sees a gap (which can look like reordering).

- **Nack'ing a message in an ordered subscription pauses delivery for that key** until the message is successfully acked. If you have a handler that nacks message N, message N+1 for the same key won't be delivered until N is resolved. Make sure you're not nacking and then seeing N+1 first via redelivery timing.

- **Don't run multiple `Receive` calls on the same subscription handle** — that's undefined behavior and will scramble order.

## Quick diagnostic checklist

```bash
# 1. Check subscription
gcloud pubsub subscriptions describe my-sub \
  --format='value(enableMessageOrdering)'
# Must print: True

# 2. Check publisher code
grep -n "EnableMessageOrdering" your_publisher.go
# Must find: topic.EnableMessageOrdering = true

# 3. Check publish error handling
grep -n "ResumePublish" your_publisher.go
# Should be present in your error path
```

If subscription ordering is `False`, that's your answer — recreate it. If it's `True` but the publisher flag is missing, add the flag and redeploy. 9 times out of 10 it's one of those two.

</details>

---

### `publish-throughput-low`

**Prompt**

```
I'm only getting a few hundred messages per second from my Go
publisher into Pub/Sub, even though my topic should handle far more.
Each Publish call is small. What should I tune?
```

**Judge focus:** The better answer raises the batching thresholds (CountThreshold,
DelayThreshold, ByteThreshold), warns against synchronous Get() per
publish, and reminds the user to call Topic.Stop() on shutdown.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core rubric criteria, but Answer B is more precise and practical. It correctly identifies the per-publish blocking Get() anti-pattern upfront with a clear code example, provides accurate default values for the batching settings (CountThreshold: 100, DelayThreshold: 10ms, ByteThreshold: 1 MiB), and adds valuable extras like the ordering key warning and the reuse-the-Topic-handle tip. Answer A has some inaccuracies (e.g., stating DelayThreshold default is 1ms, CountThreshold default is 1000) and its async result collection example has a subtle bug with the WaitGroup/channel pattern.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| tune PublishSettings batching | skill |
| warns against per-publish blocking Get | skill |
| mentions Topic.Stop on shutdown | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✓ | `don't call res.Get` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✓ | `defeats batch` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

<details><summary>sonnet: baseline answer</summary>

# Tuning Go Pub/Sub Publisher Throughput

The core issue is that the default `PublishSettings` are conservative and you're likely hitting **batching, goroutine, or flow control limits** before the service limit.

## The Default Problem

```go
// What most people write — one client, default settings, sequential publishes
client, _ := pubsub.NewClient(ctx, projectID)
topic := client.Topic(topicID)

// This looks async but is bottlenecked by default batch settings
for _, msg := range messages {
    topic.Publish(ctx, msg) // returns a PublishResult future
}
```

---

## Key Settings to Tune

### 1. Batch Size & Delay (Biggest Impact)

```go
topic.PublishSettings = pubsub.PublishSettings{
    // Default: 1000 messages — usually fine, but tune if needed
    CountThreshold: 1000,

    // Default: 10MB — keep this, it's the hard limit
    ByteThreshold: 10 * 1024 * 1024,

    // DEFAULT IS 1ms — this is often the silent killer
    // Pub/Sub waits this long to fill a batch before flushing
    // Increase to allow larger batches to form
    DelayThreshold: 50 * time.Millisecond,
}
```

### 2. Number of Publisher Goroutines

```go
topic.PublishSettings = pubsub.PublishSettings{
    DelayThreshold: 50 * time.Millisecond,
    CountThreshold: 1000,
    ByteThreshold:  10 * 1024 * 1024,

    // Default: GOMAXPROCS — often too low for I/O-bound publishing
    // Each goroutine handles one in-flight RPC batch
    NumGoroutines: 50, // tune based on your CPU/network
}
```

### 3. Flow Control (Prevents Blocking Your Publisher)

```go
topic.PublishSettings = pubsub.PublishSettings{
    DelayThreshold: 50 * time.Millisecond,
    CountThreshold: 1000,
    ByteThreshold:  10 * 1024 * 1024,
    NumGoroutines:  50,

    FlowControlSettings: pubsub.FlowControlSettings{
        MaxOutstandingMessages: 10000,    // default: 1000
        MaxOutstandingBytes:    100 * 1024 * 1024, // default: 10MB
        // LimitExceededBehavior: pubsub.FlowControlSignalError (fail fast)
        // or pubsub.FlowControlBlock (backpressure — safer default)
        LimitExceededBehavior: pubsub.FlowControlBlock,
    },
}
```

---

## Complete High-Throughput Example

```go
package main

import (
    "context"
    "fmt"
    "sync"
    "time"

    "cloud.google.com/go/pubsub"
    "google.golang.org/api/option"
    "google.golang.org/grpc"
)

func main() {
    ctx := context.Background()

    // Increase gRPC connection pool — default is 4, often a bottleneck
    client, err := pubsub.NewClient(ctx, "my-project",
        option.WithGRPCConnectionPool(10),
        option.WithGRPCDialOption(grpc.WithWriteBufferSize(1024*1024)),
    )
    if err != nil {
        panic(err)
    }
    defer client.Close()

    topic := client.Topic("my-topic")
    defer topic.Stop() // flushes pending messages — ALWAYS call this

    topic.PublishSettings = pubsub.PublishSettings{
        DelayThreshold: 50 * time.Millisecond,
        CountThreshold: 1000,
        ByteThreshold:  10 * 1024 * 1024,
        NumGoroutines:  50,
        FlowControlSettings: pubsub.FlowControlSettings{
            MaxOutstandingMessages: 10000,
            MaxOutstandingBytes:    512 * 1024 * 1024,
            LimitExceededBehavior:  pubsub.FlowControlBlock,
        },
    }

    // Collect results to check for errors without blocking publish loop
    var wg sync.WaitGroup
    results := make(chan *pubsub.PublishResult, 10000)

    // Error checker goroutine
    go func() {
        for res := range results {
            wg.Done()
            if _, err := res.Get(ctx); err != nil {
                fmt.Printf("publish error: %v\n", err)
            }
        }
    }()

    // Publish loop — don't call res.Get() inline, it serializes publishes
    for i := 0; i < 100000; i++ {
        wg.Add(1)
        res := topic.Publish(ctx, &pubsub.Message{
            Data: []byte(fmt.Sprintf("message-%d", i)),
        })
        results <- res
    }

    wg.Wait()
    close(results)
}
```

---

## Common Mistakes Checklist

| Mistake | Why It Hurts | Fix |
|---|---|---|
| Calling `res.Get()` in publish loop | Serializes all publishes | Collect results separately |
| Not calling `topic.Stop()` | Drops buffered messages on exit | Always defer `topic.Stop()` |
| Single gRPC connection | Saturates one connection | `WithGRPCConnectionPool(N)` |
| Low `NumGoroutines` | Few concurrent RPCs | Set to 20–100 |
| Low `DelayThreshold` | Tiny batches, many RPCs | Set to 10–100ms |
| Flow control too tight | Publisher blocks | Increase outstanding limits |

---

## Tuning Strategy

```
Start → Increase NumGoroutines → Increase gRPC pool
      → Increase DelayThreshold → Profile with pprof
      → Check Pub/Sub quota limits in Cloud Console
```

**Target metrics to watch:**
- `pubsub.googleapis.com/topic/send_message_operation_count`
- `pubsub.googleapis.com/topic/byte_cost` 
- gRPC connection saturation via `net/http/pprof`

With these settings you should reach **tens of thousands of messages/second** from a single client on reasonable hardware.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Low publish throughput with small messages almost always means you're paying per-message RPC overhead instead of batching. Here's a systematic fix.

## Diagnose first

```go
// Are you doing this? This is the problem.
for _, msg := range messages {
    result := topic.Publish(ctx, msg)
    _, err := result.Get(ctx)   // ← blocks until this one message is sent
    // ...
}
```

Calling `result.Get()` synchronously after each `Publish` forces one RPC per message. The SDK's internal batcher never accumulates anything.

---

## Fix 1: Collect results asynchronously

```go
results := make([]*pubsub.PublishResult, 0, len(messages))

// Fire all publishes without blocking.
for _, msg := range messages {
    results = append(results, topic.Publish(ctx, msg))
}

// Now wait for all of them.
for i, r := range results {
    id, err := r.Get(ctx)
    if err != nil {
        log.Printf("msg %d failed: %v", i, err)
    }
    _ = id
}
```

This lets the batcher accumulate messages across goroutines and flush them in large RPCs.

---

## Fix 2: Raise the batching thresholds

The defaults are conservative. For high-throughput publishers:

```go
topic, err := client.CreateTopic(ctx, topicID)
// or fetch an existing one:
topic = client.Topic(topicID)

topic.PublishSettings = pubsub.PublishSettings{
    // Flush when any of these thresholds is hit first.
    CountThreshold: 1000,           // default: 100 messages
    DelayThreshold: 50 * time.Millisecond, // default: 10ms
    ByteThreshold:  5 * 1024 * 1024,       // default: 1 MiB (max 10 MiB)

    // How many goroutines send RPCs in parallel.
    // Default is 25 * GOMAXPROCS; raise if you have many ordering keys
    // or are CPU-bound elsewhere.
    NumGoroutines: 16,

    // Total bytes buffered before Publish blocks the caller.
    // Raise if your producer is faster than the network.
    BufferedByteLimit: 100 * 1024 * 1024, // 100 MiB
    
    // How long Publish will block when BufferedByteLimit is reached
    // before returning an error. 0 = block indefinitely.
    Timeout: 60 * time.Second,
}
```

**Rule of thumb for small messages:** `CountThreshold` matters most. `DelayThreshold` caps your worst-case latency. `ByteThreshold` matters when messages are large.

---

## Fix 3: Ordering keys cap throughput — use them only where needed

If you're setting `OrderingKey` on every message, the SDK serializes publishes per key. With one key, you get one in-flight RPC at a time per key.

```go
// Only set OrderingKey when you actually need ordered delivery.
msg := &pubsub.Message{
    Data: payload,
    // OrderingKey: "only-if-you-need-it",
}
```

If you need ordering for some messages but not others, mix keyed and unkeyed publishes on the same topic.

---

## Fix 4: Flush cleanly on shutdown

```go
// topic.Stop() flushes all buffered messages before returning.
// Call it before client.Close().
defer topic.Stop()
defer client.Close()
```

Skipping `Stop()` silently drops any messages still in the batcher when your process exits.

---

## Fix 5: Reuse the Topic handle

```go
// Create once, reuse everywhere — the SDK batches across all callers.
topic := client.Topic("my-topic")
topic.PublishSettings = ...

// Pass topic to your workers; don't call client.Topic() in a loop.
```

Each `client.Topic()` call returns a new handle with its own batcher. Creating one per message defeats batching and leaks goroutines.

---

## Quick reference: what each knob does

| Setting | Default | When to raise |
|---|---|---|
| `CountThreshold` | 100 | Always for high-throughput small messages |
| `DelayThreshold` | 10ms | When you can tolerate slightly higher publish latency |
| `ByteThreshold` | 1 MiB | When messages are larger (up to 10 MiB max) |
| `NumGoroutines` | 25×GOMAXPROCS | When you have many ordering keys or high concurrency |
| `BufferedByteLimit` | 1 GiB | When producers outpace the network temporarily |

---

## What to expect

With async `Get()` and `CountThreshold: 1000`, a single Go process publishing small messages should comfortably reach tens of thousands of messages per second. The per-region quota ceiling is 10 GB/s ingress; you're unlikely to hit it from one host.

If throughput is still low after these changes, check `oldest_unacked_message_age` on the subscription side — a slow subscriber can create backpressure that surfaces as apparent publisher slowness.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B covers all three rubric criteria more thoroughly and accurately: it raises all three batching thresholds with clear explanations, explicitly warns against synchronous Get() calls with a detailed explanation of why it defeats batching, and prominently covers Topic.Stop() on shutdown with an explanation of message loss risk. Answer A covers the same ground but less completely—it mentions Topic.Stop() only implicitly and its treatment of the async Get() pattern is less thorough. Answer B also adds valuable bonus content (ordering keys as a throughput killer) without sacrificing clarity on the core criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| tune PublishSettings batching | skill |
| warns against per-publish blocking Get | skill |
| mentions Topic.Stop on shutdown | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✗ | |
| mentions Topic.Stop on shutdown | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✓ | `avoid blocking on Get(` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

<details><summary>haiku: baseline answer</summary>

# Tuning Go Pub/Sub Publisher Throughput

If you're bottlenecked at a few hundred msg/s, the issue is likely **batching and concurrency**, not message size. Here's what to tune:

## 1. **PublishSettings - Batch Configuration** (Most Important)

```go
topic := client.Topic("my-topic")
topic.PublishSettings.CountThreshold = 1000  // Default is 100
topic.PublishSettings.ByteThreshold = 1e7    // 10MB (default is 1MB)
topic.PublishSettings.DelayThreshold = 100 * time.Millisecond
```

**Key tuning:**
- **CountThreshold**: Increase from default 100 to 1000+. This batches more messages before sending.
- **ByteThreshold**: Increase to 10MB (default 1MB is conservative)
- **DelayThreshold**: Increase slightly (100-500ms) to allow more batching without adding latency

## 2. **Concurrency - Number of Goroutines**

```go
topic.PublishSettings.NumGoroutines = 10  // Default is 25
```

Increase this if you have CPU headroom. Try 50-100 for higher throughput.

## 3. **Full Example**

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    CountThreshold:  1000,
    ByteThreshold:   1e7,
    DelayThreshold:  100 * time.Millisecond,
    NumGoroutines:   50,
}

// Now publish
result := topic.Publish(ctx, &pubsub.Message{Data: []byte("msg")})
```

## 4. **Publish Pattern - Use Async Results**

Don't block on each result:

```go
// ❌ Slow - blocks on each publish
for _, msg := range messages {
    result := topic.Publish(ctx, &pubsub.Message{Data: msg})
    <-result.Ready()  // Blocks here!
}

// ✅ Fast - fire and forget, collect results later
results := make([]*pubsub.PublishResult, len(messages))
for i, msg := range messages {
    results[i] = topic.Publish(ctx, &pubsub.Message{Data: msg})
}

// Collect errors after
for _, result := range results {
    _, err := result.Get(ctx)
    if err != nil {
        log.Printf("Publish failed: %v", err)
    }
}
```

## 5. **Check Your Bottleneck**

Monitor these metrics:

```go
// Check if you're hitting quota limits
// Look at Pub/Sub metrics in Cloud Console:
// - Publish message operations
// - API call latency
// - Quota usage
```

## 6. **Other Considerations**

| Factor | Check |
|--------|-------|
| **Network** | Are you publishing from same region as topic? |
| **CPU** | Monitor CPU usage - if low, increase `NumGoroutines` |
| **Context timeout** | Ensure `ctx` timeout is reasonable (not too short) |
| **Credentials** | Using service account with proper permissions? |

## Typical Tuning Results

With defaults: ~100-500 msg/s  
With optimized settings: **10,000+ msg/s** (depending on message size and network)

Start with `CountThreshold=1000` and `NumGoroutines=50`, then benchmark and adjust based on your CPU/network constraints.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Publisher Throughput Tuning

You're hitting the default batching limits. Pub/Sub's Go SDK batches publishes to amortize RPC overhead, but the defaults are conservative for low-latency use cases. Here's the diagnosis and fix.

## The Problem

By default, `PublishSettings` batches only when **any** of these thresholds is hit:
- **100 messages** (`CountThreshold`)
- **10 milliseconds** (`DelayThreshold`)
- **1 MiB** (`ByteThreshold`)

With small messages, you're likely hitting the 10ms timer repeatedly, sending tiny batches. Each batch = one RPC, and RPCs have fixed overhead (~5–10ms latency). You're paying that cost per 100 messages instead of amortizing it across thousands.

## The Fix

Raise the batching thresholds in `PublishSettings`:

```go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, "my-project")
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	topic := client.Topic("my-topic")

	// Tune batching for throughput
	topic.PublishSettings.CountThreshold = 1000      // Wait for 1000 messages
	topic.PublishSettings.DelayThreshold = 100 * time.Millisecond // or 100ms
	topic.PublishSettings.ByteThreshold = 10 * 1024 * 1024 // 10 MiB

	// Publish in a worker goroutine to avoid blocking on Get()
	go func() {
		for i := 0; i < 100000; i++ {
			result := topic.Publish(ctx, &pubsub.Message{
				Data: []byte(fmt.Sprintf("message-%d", i)),
			})
			// Do NOT call Get() here — it blocks and defeats batching
			// Instead, collect results and check them later
			_ = result
		}
	}()

	// Collect results in a separate goroutine
	go func() {
		for i := 0; i < 100000; i++ {
			// This is a simplified example; in production, track results properly
		}
	}()

	time.Sleep(5 * time.Second)

	// Flush pending publishes and wait for all to complete
	topic.Stop()
	if err := client.Close(); err != nil {
		log.Fatal(err)
	}
}
```

## Key Tuning Parameters

| Setting | Default | Recommended | Notes |
|---|---|---|---|
| `CountThreshold` | 100 | 1000–10000 | Higher = fewer RPCs, higher latency per message |
| `DelayThreshold` | 10ms | 50–100ms | Increase to wait longer for a full batch |
| `ByteThreshold` | 1 MiB | 5–10 MiB | Increase if messages are small |
| `Timeout` | 60s | Keep default | Max time to wait for a batch before force-flush |

**Start with `CountThreshold=1000` and `DelayThreshold=100ms`**, then measure. If you need even higher throughput, raise `CountThreshold` to 5000–10000 (trade-off: higher per-message latency).

## Critical: Avoid Synchronous `Get()`

This is the **most common throughput killer**:

```go
// ❌ WRONG: Blocks on every publish
for i := 0; i < 100000; i++ {
	result := topic.Publish(ctx, &pubsub.Message{Data: []byte(...)})
	msgID, err := result.Get(ctx)  // Blocks until this message is sent!
	if err != nil {
		log.Fatal(err)
	}
}
```

Calling `Get()` synchronously defeats batching entirely — you're waiting for each message to be sent before publishing the next one. This caps you at ~100 messages/sec (one RPC per 10ms).

**Instead, collect results and check them asynchronously:**

```go
// ✅ CORRECT: Batches publishes
results := make([]*pubsub.PublishResult, 0, 100000)
for i := 0; i < 100000; i++ {
	result := topic.Publish(ctx, &pubsub.Message{
		Data: []byte(fmt.Sprintf("message-%d", i)),
	})
	results = append(results, result)
}

// Check results after publishing is done
for i, result := range results {
	msgID, err := result.Get(ctx)
	if err != nil {
		log.Printf("message %d failed: %v", i, err)
	}
}
```

Or use a worker pool to check results in parallel:

```go
// Publish all, then drain results in a goroutine
go func() {
	for _, result := range results {
		msgID, err := result.Get(ctx)
		if err != nil {
			log.Printf("publish failed: %v", err)
		}
	}
}()
```

## Ordering Keys: The Silent Throughput Killer

If you're using `OrderingKey` on every message, **that's your bottleneck**:

```go
// ❌ This serializes all publishes per key
result := topic.Publish(ctx, &pubsub.Message{
	Data: []byte(...),
	OrderingKey: "my-key",  // All messages with this key are serialized
})
```

Ordering keys force per-key serialization on the publisher side. If all messages have the same key, you get **one message at a time**, no batching. Throughput drops to ~10–50 msg/sec.

**Use ordering keys only where order matters** (e.g., per-user event streams). For unordered messages, omit `OrderingKey`:

```go
// ✅ No ordering key = full batching
result := topic.Publish(ctx, &pubsub.Message{
	Data: []byte(...),
	// No OrderingKey
})
```

If you need ordering for *some* messages and throughput for others, mix them:

```go
// Ordered messages (e.g., per-user)
if needsOrdering {
	topic.Publish(ctx, &pubsub.Message{
		Data: []byte(...),
		OrderingKey: userID,
	})
} else {
	// Unordered messages batch freely
	topic.Publish(ctx, &pubsub.Message{
		Data: []byte(...),
	})
}
```

## Verify the Fix

Monitor with `gcloud`:

```bash
# Watch publish rate (messages/sec)
gcloud pubsub topics list --format='table(name,messageStoragePolicy)' \
  && gcloud monitoring time-series list \
  --filter='metric.type="pubsub.googleapis.com/topic/publish_message_operation_count"'
```

Or check the Cloud Console → Pub/Sub → Topics → your topic → Metrics tab. You should see:
- **Publish message operation count** dropping (fewer RPCs)
- **Publish message request count** rising (more messages per RPC)
- **Publish latency (p50/p99)** rising slightly (batching adds latency)

## Shutdown: Don't Lose In-Flight Messages

**Always call `topic.Stop()` before `client.Close()`:**

```go
// Flush all pending publishes
topic.Stop()

// Then close the client
if err := client.Close(); err != nil {
	log.Fatal(err)
}
```

Skipping `Stop()` drops in-flight messages on process exit. `Stop()` blocks until all pending publishes are sent or the context times out.

## Summary

| Action | Impact |
|---|---|
| Raise `CountThreshold` to 1000+ | 10–100x throughput gain |
| Raise `DelayThreshold` to 50–100ms | Allows larger batches to form |
| Raise `ByteThreshold` to 5–10 MiB | Handles larger messages efficiently |
| Remove synchronous `Get()` calls | 100–1000x throughput gain (this is usually the culprit) |
| Remove unnecessary `OrderingKey` | 10–100x throughput gain if you were using it globally |
| Call `topic.Stop()` on shutdown | Prevents message loss |

Start with the synchronous `Get()` audit — that's the most common cause of "only a few hundred msg/sec" on a topic that should handle thousands.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover all three rubric criteria well, but Answer A is more focused and idiomatic. Answer A clearly shows the fire-and-collect pattern as the canonical fix, explicitly names all three batching thresholds with concrete values, and prominently calls out Topic.Stop() as a correctness concern. Answer B is also solid but introduces some noise (e.g., suggesting NumGoroutines = 4*runtime.NumCPU() which overrides a reasonable default, and the goroutine-per-message fan-out pattern which can cause goroutine explosion), making it slightly less idiomatic in its recommendations.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| tune PublishSettings batching | skill |
| warns against per-publish blocking Get | tie |
| mentions Topic.Stop on shutdown | skill |

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
| warns against per-publish blocking Get | ✓ | `defeats batch` |
| mentions Topic.Stop on shutdown | ✓ | `Topic.Stop` |

<details><summary>opus: baseline answer</summary>

A few hundred msgs/sec from a Go publisher almost always means you're bottlenecked on the client, not Pub/Sub. The defaults are conservative. Things to look at, roughly in order of impact:

## 1. Batching settings (`PublishSettings`)

The Go client batches messages per topic. Defaults are:
- `DelayThreshold`: 10ms
- `CountThreshold`: 100
- `ByteThreshold`: 1MB

If your messages are tiny and you call `Publish` infrequently per goroutine, you may be flushing on the 10ms timer with very few messages per batch. Try:

```go
topic.PublishSettings.DelayThreshold = 50 * time.Millisecond
topic.PublishSettings.CountThreshold = 1000   // up to 1000 max
topic.PublishSettings.ByteThreshold = 5e6
```

`CountThreshold` is capped at 1000 server-side. Larger `DelayThreshold` lets batches fill, at the cost of latency.

## 2. Concurrency / goroutines per topic

```go
topic.PublishSettings.NumGoroutines = 4 * runtime.NumCPU()
```

Default is `25 * GOMAXPROCS`, which is usually fine, but each goroutine maintains a stream. More importantly, make sure **you** are calling `Publish` from many goroutines — `Publish` is non-blocking and returns a `*PublishResult`, but if you `Get()` synchronously after each call you've serialized the whole pipeline.

Don't do this:
```go
for _, m := range msgs {
    r := topic.Publish(ctx, m)
    _, err := r.Get(ctx) // <-- serializes everything
}
```

Do this — fan out the `Get` calls:
```go
for _, m := range msgs {
    r := topic.Publish(ctx, m)
    go func() {
        if _, err := r.Get(ctx); err != nil { ... }
    }()
}
```

Or buffer the results and check them later.

## 3. Flow control

Outbound flow control is off by default. If you're saturating memory it's worth setting, but it can also throttle you if misconfigured:

```go
topic.PublishSettings.FlowControlSettings = pubsub.FlowControlSettings{
    MaxOutstandingMessages: 100_000,
    MaxOutstandingBytes:    1 << 30,
    LimitExceededBehavior:  pubsub.FlowControlBlock,
}
```

## 4. Reuse the `*Topic`

Don't call `client.Topic("foo")` per publish in a hot path — or rather, don't recreate it inside loops in a way that makes you `Stop()` and re-bundle. One `*Topic` per topic, kept for the process lifetime. Call `topic.Stop()` only on shutdown.

## 5. Reuse the `*Client`

Same — one client per process. The underlying gRPC connection pool is shared.

## 6. gRPC connection pool

For very high throughput, increase the gRPC connection pool:

```go
client, err := pubsub.NewClient(ctx, projectID,
    option.WithGRPCConnectionPool(8))
```

Default is 4. Each connection multiplexes streams but has practical concurrency limits.

## 7. Check what's actually slow

Before tuning blindly, look at the publish latency metric (`pubsub.googleapis.com/topic/send_request_count` and request latencies in Cloud Monitoring), and enable client tracing or just measure how long `Publish → Get` takes. If individual RPCs are fast but throughput is low, it's batching/concurrency. If RPCs are slow, it's network or auth.

## Typical fix

For most "few hundred msgs/sec" cases the culprit is **calling `Get()` synchronously after each `Publish`**. Fix that first; the batcher can't help you if you only ever have one message in flight.

</details>

<details><summary>opus: skill-loaded answer</summary>

Short answer: your default `PublishSettings` are batching too conservatively, and you may be defeating batching entirely by `Get()`-ing each result synchronously. Fix both.

## The two most likely causes

**1. Synchronous `Get()` after every `Publish`** — this is the #1 throughput killer.

```go
// ❌ WRONG — defeats batching, ~hundreds msg/sec ceiling
for _, m := range messages {
    result := topic.Publish(ctx, m)
    id, err := result.Get(ctx) // blocks until this single message is sent
    ...
}
```

`Topic.Publish` returns immediately and queues the message into an internal batcher. Calling `Get()` in the same loop iteration blocks until that batch flushes, so you never accumulate a batch worth sending.

```go
// ✅ RIGHT — fire-and-collect, lets the batcher fill
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, m := range messages {
    results = append(results, topic.Publish(ctx, m))
}
// Drain results on a worker goroutine, or after the publish loop:
for _, r := range results {
    id, err := r.Get(ctx)
    if err != nil {
        // handle (often retryable; consider ResumePublish if using ordering keys)
    }
}
```

**2. Conservative `PublishSettings` defaults**

The defaults are roughly: 100 messages, 1 MiB, **10ms** delay. For high throughput, raise them:

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    DelayThreshold: 50 * time.Millisecond,  // was 10ms — let batches fill
    CountThreshold: 1000,                   // was 100
    ByteThreshold:  5 * 1024 * 1024,        // was ~1 MiB; raise to 5–10 MiB
    NumGoroutines:  // leave default unless profiling says otherwise
        0,
    Timeout: 60 * time.Second,
}
```

`DelayThreshold` is usually the most impactful knob — 10ms is too short for a batch to fill at moderate publish rates.

## Other things to check

- **Ordering keys.** If every message has an `OrderingKey`, the publisher serializes per key, which caps throughput. Use ordering keys only on messages that need order; leave the rest with `OrderingKey = ""`.
- **One `Topic` handle, reused.** `Topic` is goroutine-safe and the batcher lives on the handle. Don't call `client.Topic("...")` per publish — create it once, reuse it.
- **`Topic.Stop()` on shutdown.** Without it, the final un-flushed batch is dropped on process exit. This doesn't affect steady-state throughput but matters for correctness.
- **Publisher flow control** (`PublishSettings.FlowControlSettings`) is off by default. If you're queueing faster than the network drains, you can OOM — but that's a separate concern from your current throughput problem.

## Suggested order of operations

1. Audit your publish loop for synchronous `Get()`. Fix that first — it alone often gets you 10–100× improvement.
2. Raise `DelayThreshold` to 50–100ms and `CountThreshold` to 1000.
3. Re-measure. If still bottlenecked, raise `ByteThreshold` and check whether ordering keys are in play.
4. If you're now hitting a hard ceiling, you may be at the per-region publish quota — check the Pub/Sub quota page and Cloud Monitoring's `topic/send_request_count`.

Want me to look at your actual publish code to spot which of these is biting you?

</details>

---

### `dead-letter-not-working`

**Prompt**

```
I configured a dead-letter topic on my Pub/Sub subscription with
maxDeliveryAttempts=5, but failed messages keep being retried
forever instead of going to the DLT. What did I miss?
```

**Judge focus:** The better answer pinpoints the IAM bindings (publisher on the DLT
AND subscriber on the source) without which DLT forwarding silently
fails.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly identify all four rubric criteria: IAM as the root cause, publisher role on DLT, subscriber role on source subscription, and the Pub/Sub service account. Answer A is slightly more concise and better structured for quick diagnosis, while Answer B adds useful extras like the minimum maxDeliveryAttempts value (5), the update_mask requirement for Python client, and the googclient_deliveryattempt attribute for debugging. Neither answer is clearly superior overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies IAM as the cause | tie |
| mentions publisher role on DLT | tie |
| mentions subscriber role on source | tie |
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

<details><summary>sonnet: baseline answer</summary>

## Pub/Sub Dead Letter Topic Not Working

This is a very common misconfiguration. There are usually **several things working together** that need to be correct.

---

## The Most Common Causes

### 1. Missing IAM Permissions (Most Frequent Culprit)

Pub/Sub uses a **service account** to forward messages to the DLT. If it lacks permissions, it silently fails and keeps retrying.

```bash
# Get your project's Pub/Sub service account
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

echo "Service Account: $PUBSUB_SA"

# Grant Publisher role on the dead-letter TOPIC
gcloud pubsub topics add-iam-policy-binding your-dead-letter-topic \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher"

# Grant Subscriber role on the ORIGINAL subscription
# (Pub/Sub needs to ack messages before forwarding them)
gcloud pubsub subscriptions add-iam-policy-binding your-original-subscription \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber"
```

> ⚠️ **Both permissions are required.** Missing the Subscriber role on the source subscription is easy to overlook.

---

### 2. Verify Your Subscription Configuration Is Actually Set

```bash
# Confirm DLT config is really there
gcloud pubsub subscriptions describe your-subscription

# Look for this block in the output:
# deadLetterPolicy:
#   deadLetterTopic: projects/YOUR_PROJECT/topics/your-dead-letter-topic
#   maxDeliveryAttempts: 5
```

```python
# If creating/updating via Python client - correct way
from google.cloud import pubsub_v1
from google.pubsub_v1.types import DeadLetterPolicy

subscriber = pubsub_v1.SubscriberClient()

dead_letter_policy = DeadLetterPolicy(
    dead_letter_topic="projects/YOUR_PROJECT/topics/your-dead-letter-topic",
    max_delivery_attempts=5,  # Must be between 5 and 100
)

# UPDATE requires update_mask - missing this is another common bug
subscription = {
    "name": "projects/YOUR_PROJECT/subscriptions/your-subscription",
    "dead_letter_policy": dead_letter_policy,
}

update_mask = {"paths": ["dead_letter_policy"]}  # Don't forget this!

subscriber.update_subscription(
    request={"subscription": subscription, "update_mask": update_mask}
)
```

---

### 3. The DLT Topic Must Exist Before the Subscription

```bash
# Create DLT topic FIRST
gcloud pubsub topics create your-dead-letter-topic

# Then create/update the subscription
gcloud pubsub subscriptions create your-subscription \
  --topic=your-main-topic \
  --dead-letter-topic=projects/YOUR_PROJECT/topics/your-dead-letter-topic \
  --max-delivery-attempts=5
```

---

### 4. Understand How Delivery Attempts Are Counted

```
┌─────────────────────────────────────────────────────────┐
│  maxDeliveryAttempts = 5                                │
│                                                         │
│  Attempt 1: delivered → subscriber NACKs               │
│  Attempt 2: redelivered → subscriber NACKs             │
│  Attempt 3: redelivered → subscriber NACKs             │
│  Attempt 4: redelivered → subscriber NACKs             │
│  Attempt 5: redelivered → subscriber NACKs             │
│             ↓                                           │
│         Forwarded to DLT ✓                             │
└─────────────────────────────────────────────────────────┘

⚠️  If your subscriber lets the ackDeadline EXPIRE instead
    of explicitly NACKing, the attempt counter still
    increments — but more slowly.
```

---

### 5. The DLT Itself Needs a Subscription (or messages vanish)

```bash
# Messages published to DLT are lost if nothing subscribes to it!
gcloud pubsub subscriptions create your-dead-letter-sub \
  --topic=your-dead-letter-topic \
  --ack-deadline=60
```

---

## Quick Diagnostic Checklist

```
[ ] DLT topic exists before subscription was created
[ ] Pub/Sub SA has roles/pubsub.publisher on DLT topic
[ ] Pub/Sub SA has roles/pubsub.subscriber on source subscription
[ ] maxDeliveryAttempts is between 5–100 (not less than 5)
[ ] Subscription describe output shows deadLetterPolicy block
[ ] DLT topic has at least one subscription
[ ] Subscriber is explicitly NACKing (not just crashing/timing out)
```

---

## Verify It's Working

```bash
# Watch delivery attempt count on a specific message
# The attribute is added automatically by Pub/Sub
gcloud pubsub subscriptions pull your-subscription --auto-ack

# Messages will have this attribute:
# googclient_deliveryattempt: "3"  ← increments each retry

# Check DLT subscription for forwarded messages
gcloud pubsub subscriptions pull your-dead-letter-sub --auto-ack
```

---

## Summary

| Issue | Fix |
|---|---|
| Missing Publisher on DLT | Grant `pubsub.publisher` to Pub/Sub SA |
| Missing Subscriber on source | Grant `pubsub.subscriber` to Pub/Sub SA |
| DLT didn't exist yet | Create topic first, recreate subscription |
| `maxDeliveryAttempts < 5` | Minimum allowed value is **5** |
| No subscription on DLT | Create one or messages are silently dropped |

The **IAM permissions** issue accounts for ~90% of cases where this silently fails.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The most common cause is missing IAM bindings — Pub/Sub silently continues retrying instead of forwarding to the DLT when the service account lacks permission. There are usually two or three things wrong at once. Work through this checklist in order.

---

## 1. Grant the required IAM bindings (most common cause)

Pub/Sub uses a **project-level service account** to forward messages. It needs two roles:

| Role | On what resource | Why |
|---|---|---|
| `roles/pubsub.publisher` | The **dead-letter topic** | So it can publish the failed message |
| `roles/pubsub.subscriber` | The **source subscription** | So it can ack the message off the source |

Both are required. Missing either one causes silent retry-forever behavior.

**Find your service account:**
```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
echo $PUBSUB_SA
```

**Grant the bindings:**
```bash
# Publisher role on the dead-letter topic
gcloud pubsub topics add-iam-policy-binding YOUR_DLT_TOPIC \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher"

# Subscriber role on the source subscription
gcloud pubsub subscriptions add-iam-policy-binding YOUR_SOURCE_SUBSCRIPTION \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber"
```

---

## 2. Verify the DLT is actually attached

Confirm the subscription config reflects what you think it does:

```bash
gcloud pubsub subscriptions describe YOUR_SOURCE_SUBSCRIPTION \
  --format='yaml(deadLetterPolicy)'
```

Expected output:
```yaml
deadLetterPolicy:
  deadLetterTopic: projects/YOUR_PROJECT/topics/YOUR_DLT_TOPIC
  maxDeliveryAttempts: 5
```

If this is empty or missing, the DLT was never attached (or was attached to a different subscription). Re-apply it:

```bash
gcloud pubsub subscriptions modify-push-config YOUR_SOURCE_SUBSCRIPTION \
  --dead-letter-topic=YOUR_DLT_TOPIC \
  --max-delivery-attempts=5
```

---

## 3. Understand what counts as a "delivery attempt"

`maxDeliveryAttempts` counts **Pub/Sub-level delivery attempts**, not your application's internal retry loops. A delivery attempt is only counted when Pub/Sub delivers the message to your subscriber and the subscriber either nacks it or lets the ack deadline expire.

Two things that do **not** increment the counter:
- Your handler catching an exception and retrying internally without nacking
- Your handler returning without calling `msg.Ack()` or `msg.Nack()` (the lease just expires and redelivers — this *does* eventually count, but slowly)

**In Go, make sure you're explicitly nacking on failure:**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    if err := process(msg); err != nil {
        msg.Nack() // ← required; tells Pub/Sub this attempt failed
        return
    }
    msg.Ack()
})
```

If your handler panics or the process crashes before calling either, the ack deadline expires and the attempt *does* count — but slowly (one attempt per deadline expiry, default 10s, up to 600s).

---

## 4. Check that the DLT itself has a subscription

Messages forwarded to the DLT are gone if nothing is subscribed to it. The DLT is just a regular topic — create a subscription on it so you can inspect failures:

```bash
gcloud pubsub subscriptions create YOUR_DLT_SUB \
  --topic=YOUR_DLT_TOPIC \
  --message-retention-duration=7d
```

Then pull to confirm messages are arriving:
```bash
gcloud pubsub subscriptions pull YOUR_DLT_SUB --limit=5 --auto-ack
```

---

## 5. Confirm the DLT is in the same project (or adjust permissions)

The DLT can be in a different project, but the IAM bindings in step 1 must be applied in **that project** using the service account from the **source project**. Cross-project DLTs are valid but the binding target changes — this is a frequent source of confusion.

---

## Quick diagnostic summary

```
Retrying forever?
├── gcloud subscriptions describe → deadLetterPolicy missing?  → Re-attach DLT
├── IAM bindings missing?                                       → Grant publisher + subscriber roles
├── Handler not calling msg.Nack()?                            → Fix subscriber code
└── DLT has no subscription?                                   → Create one to observe failures
```

Fix the IAM bindings first — that's the cause in the vast majority of cases.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B directly and prominently identifies the IAM bindings as the root cause, specifying both the publisher role on the DLT and the subscriber role on the source subscription, along with the exact Pub/Sub service account name. Answer A only briefly mentions IAM in a table row and focuses primarily on configuration syntax, missing the core insight about why DLT forwarding silently fails.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies IAM as the cause | skill |
| mentions publisher role on DLT | skill |
| mentions subscriber role on source | skill |
| mentions Pub/Sub service account | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies IAM as the cause | ✓ | `IAM` |
| mentions publisher role on DLT | ✓ | `publish` on the DLT` |
| mentions subscriber role on source | ✗ | |
| mentions Pub/Sub service account | ✓ | `service account` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies IAM as the cause | ✓ | `IAM` |
| mentions publisher role on DLT | ✓ | `roles/pubsub.publisher` |
| mentions subscriber role on source | ✓ | `roles/pubsub.subscriber` |
| mentions Pub/Sub service account | ✓ | `service account` |

<details><summary>haiku: baseline answer</summary>

# Dead-Letter Topic Configuration Issue

The most common reason messages aren't reaching your DLT is that you're missing the **`deadLetterPolicy`** configuration. Setting `maxDeliveryAttempts` alone isn't enough.

## What You Need

You must configure **both**:

1. **`deadLetterPolicy`** - specifies the DLT topic
2. **`maxDeliveryAttempts`** - sets the retry limit

## Example: Correct Configuration

### Using gcloud CLI
```bash
gcloud pubsub subscriptions update my-subscription \
  --dead-letter-topic=projects/PROJECT_ID/topics/my-dlq-topic \
  --max-delivery-attempts=5
```

### Using Terraform
```hcl
resource "google_pubsub_subscription" "example" {
  name  = "my-subscription"
  topic = google_pubsub_topic.example.name

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }
}
```

### Using Python Client
```python
from google.cloud import pubsub_v1

subscriber_client = pubsub_v1.SubscriberClient()
subscription_path = subscriber_client.subscription_path(project_id, subscription_id)

dead_letter_policy = pubsub_v1.types.DeadLetterPolicy(
    dead_letter_topic=dlq_topic_path,
    max_delivery_attempts=5
)

subscription = pubsub_v1.types.Subscription(
    name=subscription_path,
    dead_letter_policy=dead_letter_policy
)

updated_subscription = subscriber_client.update_subscription(
    {"subscription": subscription, "update_mask": {"paths": ["dead_letter_policy"]}}
)
```

## Other Common Issues

| Issue | Solution |
|-------|----------|
| DLT topic doesn't exist | Create the topic first: `gcloud pubsub topics create my-dlq-topic` |
| Missing IAM permissions | Ensure service account has `pubsub.topics.publish` on the DLT topic |
| `maxDeliveryAttempts=0` | This disables DLT; use `≥1` |
| Subscription still retrying | Verify with `gcloud pubsub subscriptions describe my-subscription` |

## Verify Configuration

```bash
gcloud pubsub subscriptions describe my-subscription --format=json
```

Look for the `deadLetterPolicy` section in the output.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Dead-Letter Topic Not Receiving Failed Messages

The most common cause is **missing or incomplete IAM bindings**. The Pub/Sub service account needs explicit permissions to publish to the DLT and subscribe to the source subscription, or messages silently fail to forward and loop forever.

## Checklist

### 1. **Verify IAM Bindings (Most Common Miss)**

The Pub/Sub service account (`service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com`) must have:

- **`roles/pubsub.publisher`** on the **dead-letter topic** (so it can republish failed messages)
- **`roles/pubsub.subscriber`** on the **source subscription** (so it can consume and nack messages)

Check bindings:

```bash
# On the dead-letter topic
gcloud pubsub topics get-iam-policy DLT_TOPIC_NAME

# On the source subscription
gcloud pubsub subscriptions get-iam-policy SOURCE_SUB_NAME
```

If the service account is missing, grant it:

```bash
# Publisher role on DLT
gcloud pubsub topics add-iam-policy-binding DLT_TOPIC_NAME \
  --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/pubsub.publisher

# Subscriber role on source subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUB_NAME \
  --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/pubsub.subscriber
```

### 2. **Confirm DLT Configuration on the Subscription**

Verify the DLT is actually attached and `maxDeliveryAttempts` is set:

```bash
gcloud pubsub subscriptions describe SOURCE_SUB_NAME --format='value(deadLetterPolicy)'
```

Expected output:
```
deadLetterPolicy:
  deadLetterTopic: projects/PROJECT_ID/topics/DLT_TOPIC_NAME
  maxDeliveryAttempts: 5
```

If `deadLetterPolicy` is empty or missing, update it:

```bash
gcloud pubsub subscriptions update SOURCE_SUB_NAME \
  --dead-letter-topic=DLT_TOPIC_NAME \
  --max-delivery-attempts=5
```

### 3. **Check Retry Policy (Secondary Cause)**

If the retry policy is missing or misconfigured, Pub/Sub may retry aggressively before respecting `maxDeliveryAttempts`. Verify:

```bash
gcloud pubsub subscriptions describe SOURCE_SUB_NAME --format='value(retryPolicy)'
```

If empty, add exponential backoff:

```bash
gcloud pubsub subscriptions update SOURCE_SUB_NAME \
  --min-retry-delay=10s \
  --max-retry-delay=600s
```

### 4. **Verify the DLT Topic Exists and Is Writable**

```bash
gcloud pubsub topics describe DLT_TOPIC_NAME
```

If it doesn't exist, create it:

```bash
gcloud pubsub topics create DLT_TOPIC_NAME
```

### 5. **Check Subscription State**

If the subscription is in a bad state (e.g., after a failed update), try:

```bash
gcloud pubsub subscriptions update SOURCE_SUB_NAME \
  --dead-letter-topic=DLT_TOPIC_NAME \
  --max-delivery-attempts=5
```

## In Go Code

If you're creating the subscription programmatically:

```go
sub, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic: topic,
    DeadLetterPolicy: &pubsub.DeadLetterPolicy{
        DeadLetterTopic: client.Topic("my-dlt"),
        MaxDeliveryAttempts: 5,
    },
    RetryPolicy: &pubsub.RetryPolicy{
        MinimumBackoff: 10 * time.Second,
        MaximumBackoff: 600 * time.Second,
    },
})
```

**Ensure the DLT topic is created first**, and the service account running your code has `roles/pubsub.admin` (or at least `roles/pubsub.editor`) on both the source subscription and DLT topic.

## Debugging

To confirm messages are actually failing (not just being acked):

1. **Check the subscription's unacked message count:**
   ```bash
   gcloud pubsub subscriptions describe SOURCE_SUB_NAME --format='value(numUndeliveredMessages)'
   ```
   If this is growing, messages are being nacked or timing out.

2. **Monitor the DLT for incoming messages:**
   ```bash
   gcloud pubsub subscriptions pull dlt-debug-sub --auto-ack --limit=10
   ```
   (Create a temporary pull subscription on the DLT to inspect messages.)

3. **Check Cloud Logging for Pub/Sub errors:**
   ```bash
   gcloud logging read "resource.type=pubsub_subscription AND resource.labels.subscription_id=SOURCE_SUB_NAME" \
     --limit=50 --format=json
   ```

## Summary

**Most likely fix:** Add the Pub/Sub service account to both the DLT (publisher role) and source subscription (subscriber role). Without both, the DLT policy is silently ignored and retries loop forever.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the IAM issue with the same two required bindings and mention the Pub/Sub service account. Answer A is slightly more complete and actionable, providing a script to dynamically retrieve the project number, verification commands for the IAM policies, and a note about attaching a subscription to the DLT. Both answers are essentially equivalent on the rubric criteria, but Answer A's additional practical details (verification steps, dynamic project number lookup) give it a slight edge.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies IAM as the cause | tie |
| mentions publisher role on DLT | tie |
| mentions subscriber role on source | tie |
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

<details><summary>opus: baseline answer</summary>

The most common cause: **the Pub/Sub service account doesn't have the required IAM permissions on the dead-letter topic and the source subscription.**

Configuring `maxDeliveryAttempts` alone isn't enough. Pub/Sub uses a Google-managed service account to forward messages to the DLT, and if it lacks permissions, the forward silently fails and the message just keeps being redelivered.

### What you need to do

1. **Find the Pub/Sub service account for your project:**
   ```
   service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com
   ```

2. **Grant Publisher on the dead-letter topic:**
   ```bash
   gcloud pubsub topics add-iam-policy-binding <DLT_TOPIC> \
     --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com" \
     --role="roles/pubsub.publisher"
   ```

3. **Grant Subscriber on the source subscription** (so Pub/Sub can ack the original message after forwarding):
   ```bash
   gcloud pubsub subscriptions add-iam-policy-binding <SOURCE_SUB> \
     --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com" \
     --role="roles/pubsub.subscriber"
   ```

### Other things to double-check

- **Your subscriber must `nack()` (or let the ack deadline expire).** If your code is throwing an exception but the client library is still ack-ing, the delivery attempt counter never increments. Each nack/timeout = 1 attempt.
- **The delivery attempt counter is best-effort.** If you're using pull and not enabling `EnableMessageOrdering`/exactly-once or doing custom ack handling, make sure you're using a client library version that propagates the `delivery_attempt` field properly.
- **Check the DLT actually exists** in the same project (or that cross-project IAM is set up).
- **Look at subscription metrics** in Cloud Monitoring: `subscription/dead_letter_message_count` will be zero if forwarding is failing, and you'll often see logs in Cloud Logging like `Failed to forward message to dead-letter topic` with a permission error.

The IAM step is by far the #1 gotcha — the UI lets you configure the DLT without warning you about it.

</details>

<details><summary>opus: skill-loaded answer</summary>

The almost-certain cause: **missing IAM bindings on the Pub/Sub service account.** Configuring `deadLetterPolicy` on the subscription is necessary but not sufficient — Pub/Sub needs explicit permission to publish to the DLT and to ack messages on the source subscription. Without both, the forward silently fails and retries continue forever.

## Fix

First, find your project's Pub/Sub service account. It has the form:

```
service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com
```

Get your project number:

```bash
gcloud projects describe PROJECT_ID --format='value(projectNumber)'
```

Then grant both bindings:

```bash
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# 1. Allow Pub/Sub to publish to the dead-letter topic
gcloud pubsub topics add-iam-policy-binding DLT_NAME \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher"

# 2. Allow Pub/Sub to ack/forward messages on the source subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUB_NAME \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber"
```

Both roles are required:
- **`pubsub.publisher` on the DLT** — so Pub/Sub can write the failed message there.
- **`pubsub.subscriber` on the source subscription** — so Pub/Sub can ack the original message after forwarding it.

If either is missing, the forward fails silently and the message stays in the source subscription, getting redelivered indefinitely.

## Verify

Check the bindings exist:

```bash
gcloud pubsub topics get-iam-policy DLT_NAME
gcloud pubsub subscriptions get-iam-policy SOURCE_SUB_NAME
```

Then watch the metric `subscription/dead_letter_message_count` in Cloud Monitoring — it should start incrementing once a message hits its 5th nack.

## Other things to double-check

If IAM is correct and messages still don't forward, verify:

1. **The handler is actually nack'ing (or letting the ack deadline expire).** A delivery only counts toward `maxDeliveryAttempts` when the message is negatively acknowledged or times out. If your code is throwing an exception *after* `Ack()`, the message is already acked and won't retry at all.
2. **`deadLetterPolicy` is actually set on the subscription:**
   ```bash
   gcloud pubsub subscriptions describe SOURCE_SUB_NAME \
     --format='value(deadLetterPolicy)'
   ```
   Should print the DLT path and `maxDeliveryAttempts: 5`. Empty output means the policy didn't apply.
3. **The DLT itself has a subscription attached.** Messages forwarded to a DLT with no subscriber will sit there until the topic's message retention expires (default 7 days), then be lost. Create a subscription on the DLT for triage.

The IAM gap is by far the most common cause, though — fix that first and the redelivery loop should stop within a few minutes.

</details>

---

### `graceful-shutdown`

**Prompt**

```
My Go service has a Pub/Sub subscriber and publisher. On shutdown,
I cancel the context, but the Receive goroutine seems to hang and
in-flight publishes get lost. What's the right shutdown sequence?
```

**Judge focus:** The better answer prescribes a specific order: cancel the context
so Subscription.Receive returns, drain in-flight handlers, call
Topic.Stop() to flush the publish batch, then close the client.
It explains *why* each step matters — Receive blocks until the
context is cancelled or an unrecoverable error fires; Topic.Stop
flushes batched publishes; Client.Close releases the gRPC
connection.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the required shutdown sequence correctly, but Answer B is more precise and idiomatic. B correctly explains that Receive itself waits for in-flight callbacks to drain (so you don't need a separate WaitGroup), uses defer's LIFO ordering elegantly, and avoids the subtle race condition in A where wg.Add(1) inside the callback can still race if Receive exits. B also better explains *why* Receive blocks (it drains its internal buffer waiting for callbacks), and its trap explanations are clearer and more actionable. A introduces unnecessary complexity with two separate contexts and a manual WaitGroup that duplicates what Receive already does internally.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cancel ctx to break out of Receive | tie |
| explains Receive blocks until ctx.Done or error | skill |
| calls Topic.Stop before client.Close | tie |
| mentions order of operations matters | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cancel ctx to break out of Receive | ✓ | `Cancel()` |
| explains Receive blocks until ctx.Done or error | ✓ | `until receiveCtx` |
| calls Topic.Stop before client.Close | ✗ | |
| mentions order of operations matters | ✓ | `sequence` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cancel ctx to break out of Receive | ✓ | `cancel()` |
| explains Receive blocks until ctx.Done or error | ✗ | |
| calls Topic.Stop before client.Close | ✓ | `topic.Stop()` is called, the batcher's buffer is discarded. `client.Close` |
| mentions order of operations matters | ✓ | `order` |

<details><summary>sonnet: baseline answer</summary>

# Graceful Shutdown for Go Pub/Sub Services

## The Core Problem

Canceling the context is **not enough** — you need a coordinated sequence that:
1. Stops accepting new messages
2. Finishes processing in-flight messages
3. Flushes pending publishes
4. Only then exits

Here's a complete, production-ready implementation:

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "log"
    "os"
    "os/signal"
    "sync"
    "syscall"
    "time"

    "cloud.google.com/go/pubsub"
)

// Service encapsulates the subscriber and publisher with clean lifecycle management.
type Service struct {
    client     *pubsub.Client
    subClient  *pubsub.Subscription
    pubTopic   *pubsub.Topic

    // receiveCtx is cancelled first — stops Receive() from pulling new messages.
    receiveCtx    context.Context
    receiveCancel context.CancelFunc

    // publishCtx is cancelled after all messages are processed — stops new publishes.
    publishCtx    context.Context
    publishCancel context.CancelFunc

    // wg tracks in-flight message handlers.
    wg sync.WaitGroup
}

func NewService(projectID, subID, topicID string) (*Service, error) {
    ctx := context.Background()
    client, err := pubsub.NewClient(ctx, projectID)
    if err != nil {
        return nil, fmt.Errorf("creating pubsub client: %w", err)
    }

    receiveCtx, receiveCancel := context.WithCancel(context.Background())
    publishCtx, publishCancel := context.WithCancel(context.Background())

    topic := client.Topic(topicID)
    // IMPORTANT: Configure topic flush behavior.
    // PublishSettings controls batching — these affect what gets lost on shutdown.
    topic.PublishSettings.DelayThreshold = 100 * time.Millisecond
    topic.PublishSettings.CountThreshold = 100
    topic.PublishSettings.ByteThreshold = 1e6
    topic.PublishSettings.Timeout = 30 * time.Second

    sub := client.Subscription(subID)
    // Control how many messages are processed concurrently.
    sub.ReceiveSettings.MaxOutstandingMessages = 10
    sub.ReceiveSettings.NumGoroutines = 2

    return &Service{
        client:        client,
        subClient:     sub,
        pubTopic:      topic,
        receiveCtx:    receiveCtx,
        receiveCancel: receiveCancel,
        publishCtx:    publishCtx,
        publishCancel: publishCancel,
    }, nil
}

// Start begins receiving messages. Blocks until receiveCtx is cancelled.
func (s *Service) Start() error {
    log.Println("subscriber: starting")

    err := s.subClient.Receive(s.receiveCtx, func(ctx context.Context, msg *pubsub.Message) {
        // Track this handler so shutdown can wait for it.
        s.wg.Add(1)
        defer s.wg.Done()

        if err := s.handleMessage(msg); err != nil {
            log.Printf("handler error, nacking: %v", err)
            msg.Nack()
            return
        }
        msg.Ack()
    })

    // Receive returns nil when context is cancelled — that's expected.
    if err != nil && !errors.Is(err, context.Canceled) {
        return fmt.Errorf("subscriber receive: %w", err)
    }

    log.Println("subscriber: receive loop exited")
    return nil
}

func (s *Service) handleMessage(msg *pubsub.Message) error {
    // Use publishCtx here — not the message ctx — so publishes can complete
    // even after the subscriber context is cancelled.
    result := s.pubTopic.Publish(s.publishCtx, &pubsub.Message{
        Data: []byte(fmt.Sprintf("processed: %s", msg.Data)),
    })

    // Block until the publish is confirmed (or fails).
    // This is critical — fire-and-forget publishes WILL be lost on shutdown.
    if _, err := result.Get(s.publishCtx); err != nil {
        return fmt.Errorf("publishing result: %w", err)
    }

    return nil
}

// Shutdown performs the coordinated shutdown sequence.
func (s *Service) Shutdown(timeout time.Duration) error {
    log.Println("shutdown: starting")

    // ── Step 1 ──────────────────────────────────────────────────────────────
    // Stop pulling new messages. Receive() will return after in-flight
    // handlers complete (it waits internally for its own goroutines).
    log.Println("shutdown: cancelling receive context")
    s.receiveCancel()

    // ── Step 2 ──────────────────────────────────────────────────────────────
    // Wait for all message handlers to finish, with a timeout.
    // Handlers may still be publishing at this point.
    log.Println("shutdown: waiting for in-flight handlers")
    done := make(chan struct{})
    go func() {
        s.wg.Wait()
        close(done)
    }()

    select {
    case <-done:
        log.Println("shutdown: all handlers finished")
    case <-time.After(timeout):
        // Handlers took too long — we'll proceed but publishes may be lost.
        log.Println("shutdown: WARNING handler drain timed out")
    }

    // ── Step 3 ──────────────────────────────────────────────────────────────
    // Now cancel the publish context — no new publishes will be accepted.
    log.Println("shutdown: cancelling publish context")
    s.publishCancel()

    // ── Step 4 ──────────────────────────────────────────────────────────────
    // Flush the topic. This blocks until all buffered messages are sent
    // or the topic's Timeout is reached. This is the critical step that
    // prevents losing batched-but-not-yet-sent messages.
    log.Println("shutdown: flushing topic")
    s.pubTopic.Stop() // blocks until all pending publishes complete

    // ── Step 5 ──────────────────────────────────────────────────────────────
    // Close the client — releases gRPC connections.
    log.Println("shutdown: closing client")
    if err := s.client.Close(); err != nil {
        return fmt.Errorf("closing client: %w", err)
    }

    log.Println("shutdown: complete")
    return nil
}

func main() {
    svc, err := NewService("my-project", "my-sub", "my-topic")
    if err != nil {
        log.Fatalf("creating service: %v", err)
    }

    // Run subscriber in background.
    startErr := make(chan error, 1)
    go func() {
        startErr <- svc.Start()
    }()

    // Wait for OS signal or subscriber failure.
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

    select {
    case sig := <-quit:
        log.Printf("main: received signal %v", sig)
    case err := <-startErr:
        log.Printf("main: subscriber failed: %v", err)
    }

    if err := svc.Shutdown(30 * time.Second); err != nil {
        log.Printf("main: shutdown error: %v", err)
        os.Exit(1)
    }
}
```

## Why Each Step Matters

```
Signal received
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: receiveCancel()                                      │
│   • Stops Receive() from pulling NEW messages from Pub/Sub   │
│   • In-flight handlers continue running                      │
│   • Receive() itself blocks until its goroutines finish      │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: wg.Wait() with timeout                               │
│   • Waits for YOUR handler goroutines to complete            │
│   • Handlers may still be calling Publish() at this point    │
│   • Timeout prevents hanging forever on a stuck handler      │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: publishCancel()                                      │
│   • Cancels context used for new Publish() calls             │
│   • Must happen AFTER handlers finish, not before            │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: topic.Stop()                ← THE CRITICAL STEP      │
│   • Flushes the internal publish buffer                      │
│   • Waits for all in-flight gRPC publish calls to complete   │
│   • Without this, batched messages are silently dropped      │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: client.Close()                                       │
│   • Closes gRPC connections cleanly                          │
└─────────────────────────────────────────────────────────────┘
```

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Cancelling one context for both receive and publish | Publish context cancelled before handlers finish → lost messages |
| Not calling `topic.Stop()` | Batched messages silently dropped |
| Fire-and-forget `Publish()` (not calling `result.Get()`) | No way to know if publish succeeded; lost on shutdown |
| `wg.Add(1)` outside the handler | Race condition if Receive exits before Add runs |
| Calling `client.Close()` before `topic.Stop()` | Closes gRPC connection while publishes are in-flight |

## Key Takeaways

- **Two separate contexts**: receive and publish have different lifetimes
- **`topic.Stop()` is mandatory**: it's the only way to flush the publish buffer
- **Always call `result.Get()`**: fire-and-forget publishes cannot be tracked or retried
- **`wg.Add(1)` inside the handler**: the handler *is* the goroutine, so this is safe and race-free

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Shutdown ordering is the most common source of both hangs and lost messages in Go Pub/Sub services. The two problems have different root causes and need to be fixed independently.

## Why each problem happens

**`Receive` hangs** because cancelling the context is necessary but not sufficient. `Receive` drains its internal buffer before returning — if your callback is blocked waiting on a channel, a lock, or a downstream call, the drain never completes. The context cancellation stops *new* message delivery but waits for in-flight callbacks to finish.

**Publishes get lost** because `topic.Publish` is asynchronous. It hands the message to an internal batcher and returns a `PublishResult` immediately. If the process exits before `topic.Stop()` is called, the batcher's buffer is discarded. `client.Close()` does **not** flush pending publishes — `topic.Stop()` does.

## The correct shutdown sequence

```
stop accepting new work
  → signal Receive to stop delivering new messages  (cancel ctx)
  → wait for in-flight callbacks to finish           (Receive returns)
  → flush the publisher batcher                      (topic.Stop)
  → release SDK resources                            (client.Close)
```

Each step must complete before the next begins. Here is a minimal but complete example:

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	client, err := pubsub.NewClient(ctx, "my-project")
	if err != nil {
		log.Fatal(err)
	}
	// client.Close is last — after topic.Stop flushes pending publishes.
	defer client.Close()

	topic := client.Topic("my-topic")
	// topic.Stop flushes the batcher. Must happen before client.Close.
	// Wrapping in defer means it runs before the defer above (LIFO order).
	defer topic.Stop()

	sub := client.Subscription("my-subscription")
	sub.ReceiveSettings.MaxOutstandingMessages = 100 // tune for your workload

	// receiveErr carries the result of Receive so main can inspect it.
	receiveErr := make(chan error, 1)

	go func() {
		err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
			// All processing happens synchronously here.
			// Receive will not return until every in-flight callback returns.
			if err := process(ctx, topic, msg); err != nil {
				msg.Nack()
				return
			}
			msg.Ack()
		})
		receiveErr <- err
	}()

	// Wait for a signal or a fatal Receive error.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-quit:
		log.Printf("signal %v received, shutting down", sig)
	case err := <-receiveErr:
		// Receive returned on its own (e.g. a non-retryable RPC error).
		if err != nil && !errors.Is(err, context.Canceled) {
			log.Printf("Receive exited with error: %v", err)
		}
		return // defers (topic.Stop, client.Close) run here
	}

	// Cancel the context. Receive stops delivering new messages and waits
	// for all in-flight callbacks to return before it exits.
	cancel()

	// Wait for Receive to confirm it has drained.
	// Add a deadline so a stuck callback can't block shutdown forever.
	select {
	case err := <-receiveErr:
		if err != nil && !errors.Is(err, context.Canceled) {
			log.Printf("Receive error after cancel: %v", err)
		}
	case <-time.After(30 * time.Second):
		log.Print("WARNING: Receive did not drain within 30s; forcing shutdown")
	}

	// Defers run here in LIFO order: topic.Stop() then client.Close().
}

func process(ctx context.Context, topic *pubsub.Topic, msg *pubsub.Message) error {
	// Publish something in response to the received message.
	result := topic.Publish(ctx, &pubsub.Message{
		Data: []byte(fmt.Sprintf("processed: %s", msg.ID)),
	})

	// Collect the publish result synchronously inside the callback.
	// This is the only safe place — if you hand it to a background goroutine
	// and return, the callback exits, the lease stops extending, and the
	// message redelivers even though you called Ack.
	if _, err := result.Get(ctx); err != nil {
		return fmt.Errorf("publish failed: %w", err)
	}
	return nil
}
```

## The three traps this avoids

**Trap 1 — handing `PublishResult.Get` to a background goroutine**

```go
// WRONG: callback returns immediately; lease stops extending;
// message redelivers even if the publish succeeds.
go func() {
    result.Get(ctx)
    msg.Ack()
}()
```

The ack-deadline extension runs only while the callback is executing. Return early and the lease expires.

**Trap 2 — calling `client.Close()` before `topic.Stop()`**

```go
// WRONG: Close does not flush the batcher.
defer client.Close()
defer topic.Stop() // runs first (LIFO) — this is actually correct with defer
```

With `defer`, LIFO order saves you here, but if you call them explicitly in the wrong order, `Close` tears down the connection before `Stop` can flush. Always `Stop` before `Close`.

**Trap 3 — not waiting for `Receive` to return**

```go
cancel()
client.Close() // WRONG: Receive may still be in a callback; Close races with it
```

`Receive` is still running callbacks after `cancel()` returns. You must wait on the `receiveErr` channel (or a `sync.WaitGroup`) before closing the client.

## Quick reference

| Call | What it does | When |
|---|---|---|
| `cancel()` | Stops new message delivery to callbacks | First, on shutdown signal |
| `<-receiveErr` | Waits for all in-flight callbacks to finish | After `cancel()` |
| `topic.Stop()` | Flushes the publish batcher, blocks until done | After `Receive` returns |
| `client.Close()` | Releases gRPC connections | Last |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B prescribes the correct order more precisely: topic.Stop() before cancelling the context, then waiting for Receive, then client.Close(). Answer A incorrectly calls sub.Stop() (which doesn't exist on Subscription) instead of cancelling the context to unblock Receive, and places topic.Stop() after waiting for Receive rather than before cancelling the context. Answer B also explicitly explains why topic.Stop() should come before context cancellation (to avoid cancelling in-flight publishes) and provides clearer reasoning for each step.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cancel ctx to break out of Receive | skill |
| explains Receive blocks until ctx.Done or error | skill |
| calls Topic.Stop before client.Close | tie |
| mentions order of operations matters | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cancel ctx to break out of Receive | ✓ | `cancel()` |
| explains Receive blocks until ctx.Done or error | ✓ | `ctx.Done` |
| calls Topic.Stop before client.Close | ✓ | `Stop() 	 	// 5. Close client 	return s.client.Close()` |
| mentions order of operations matters | ✓ | `Sequence` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cancel ctx to break out of Receive | ✓ | `cancel()` |
| explains Receive blocks until ctx.Done or error | ✓ | `until done or ctx` |
| calls Topic.Stop before client.Close | ✓ | `topic.Stop()`** ```go cancel()  // Unblocks Receive, but... client.Close` |
| mentions order of operations matters | ✓ | `order` |

<details><summary>haiku: baseline answer</summary>

# Proper Pub/Sub Shutdown Sequence in Go

The issue is that canceling the context doesn't immediately stop `Receive()` or wait for in-flight operations. Here's the correct shutdown pattern:

## ✅ Correct Shutdown Sequence

```go
package main

import (
	"context"
	"log"
	"sync"
	"time"

	"cloud.google.com/go/pubsub"
)

type Service struct {
	sub       *pubsub.Subscription
	pub       *pubsub.Topic
	client    *pubsub.Client
	wg        sync.WaitGroup
	stopChan  chan struct{}
}

func (s *Service) Start(ctx context.Context) error {
	s.stopChan = make(chan struct{})
	
	// Start subscriber
	s.wg.Add(1)
	go s.receiveMessages(ctx)
	
	return nil
}

func (s *Service) receiveMessages(ctx context.Context) {
	defer s.wg.Done()
	
	err := s.sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
		// Process message
		log.Printf("Received: %s", string(msg.Data))
		msg.Ack()
	})
	
	if err != nil && err != context.Canceled {
		log.Printf("Receive error: %v", err)
	}
}

func (s *Service) Shutdown(ctx context.Context) error {
	// 1. Stop accepting new messages
	close(s.stopChan)
	
	// 2. Stop the Receive goroutine
	s.sub.Stop()
	
	// 3. Wait for in-flight messages with timeout
	done := make(chan struct{})
	go func() {
		s.wg.Wait()
		close(done)
	}()
	
	select {
	case <-done:
		log.Println("All messages processed")
	case <-ctx.Done():
		return ctx.Err()
	}
	
	// 4. Flush pending publishes
	s.pub.Stop()
	
	// 5. Close client
	return s.client.Close()
}
```

## Key Points

| Step | Why It Matters |
|------|---|
| **`sub.Stop()`** | Stops accepting new messages immediately |
| **`wg.Wait()`** | Waits for in-flight message handlers to complete |
| **Timeout on wait** | Prevents hanging indefinitely |
| **`pub.Stop()`** | Flushes pending publishes before closing |
| **`client.Close()`** | Final cleanup |

## ⚠️ Common Mistakes

```go
// ❌ WRONG: Just canceling context
cancel()
// Receive() may still be blocked, publishes lost

// ❌ WRONG: Not calling Stop()
// Context cancellation alone doesn't unblock Receive()

// ❌ WRONG: Not waiting for handlers
// Shutdown returns before messages are processed
```

## Complete Example with Graceful Shutdown

```go
func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	service := &Service{}
	if err := service.Start(ctx); err != nil {
		log.Fatal(err)
	}
	
	// Simulate shutdown signal
	time.Sleep(5 * time.Second)
	
	// Graceful shutdown with 30-second timeout
	shutdownCtx, shutdownCancel := context.WithTimeout(
		context.Background(),
		30*time.Second,
	)
	defer shutdownCancel()
	
	if err := service.Shutdown(shutdownCtx); err != nil {
		log.Printf("Shutdown error: %v", err)
	}
}
```

## For Publishers Only

If you only have a publisher:

```go
func (s *Service) Shutdown(ctx context.Context) error {
	// Flush all pending publishes
	s.pub.Stop()
	return s.client.Close()
}
```

The `Stop()` method blocks until all pending publishes complete or the context times out.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Pub/Sub Shutdown Sequence in Go

You're hitting two separate shutdown bugs. Here's the correct order:

## The Right Sequence

```go
func main() {
    ctx := context.Background()
    client, err := pubsub.NewClient(ctx, projectID)
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()  // ← Always last

    topic := client.Topic(topicID)
    sub := client.Subscription(subID)

    // Start subscriber in a goroutine
    subErr := make(chan error, 1)
    go func() {
        subErr <- sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
            // Process message
            msg.Ack()
        })
    }()

    // ... your service runs ...

    // On shutdown signal (SIGTERM, etc.):
    shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    // Step 1: Stop accepting new publishes and flush in-flight ones
    topic.Stop()

    // Step 2: Cancel the subscriber context to unblock Receive
    cancel()  // This cancels the original ctx passed to Receive

    // Step 3: Wait for Receive to exit (with timeout)
    select {
    case err := <-subErr:
        if err != nil && err != context.Canceled {
            log.Printf("Receive error: %v", err)
        }
    case <-shutdownCtx.Done():
        log.Printf("Subscriber did not exit within timeout")
    }

    // Step 4: Close the client (idempotent, safe after Stop/Receive exit)
    client.Close()
}
```

## Why Each Step Matters

| Step | What It Does | If You Skip It |
|---|---|---|
| `topic.Stop()` | Flushes all pending publishes and blocks new `Publish` calls | In-flight messages are dropped on process exit |
| Cancel context | Unblocks `Receive` so it can exit | `Receive` hangs forever; process hangs on shutdown |
| Wait for `Receive` | Ensures subscriber has cleaned up before closing the client | Race condition; client closes while `Receive` is still running |
| `client.Close()` | Closes all connections and cleans up resources | Goroutine/connection leaks |

## Common Mistakes

**❌ Mistake 1: Cancelling context without `topic.Stop()`**
```go
cancel()  // Unblocks Receive, but...
client.Close()  // In-flight publishes are lost
```
The `Receive` goroutine exits, but pending `Publish` calls never flush. Messages disappear.

**❌ Mistake 2: Calling `client.Close()` before `Receive` exits**
```go
cancel()
client.Close()  // Closes connections while Receive is still running
// Race condition; Receive may panic or hang
```

**❌ Mistake 3: Not waiting for `Receive` to exit**
```go
topic.Stop()
cancel()
// Immediately return from main()
// Receive is still running; process exits before cleanup
```

**❌ Mistake 4: Using the same context for both publisher and subscriber**
```go
ctx, cancel := context.WithCancel(context.Background())
topic := client.Topic(topicID)
sub := client.Subscription(subID)

go sub.Receive(ctx, handler)  // ← Same ctx
topic.Publish(ctx, msg)       // ← Same ctx

cancel()  // Cancels both at once; publishes may not flush
```
If you cancel early, `Publish` calls fail before `Stop()` can flush them.

## Correct Pattern with Graceful Shutdown

```go
func (s *Service) Shutdown(ctx context.Context) error {
    // Flush all pending publishes (blocks until done or ctx expires)
    s.topic.Stop()

    // Signal subscriber to exit
    s.cancelReceive()

    // Wait for subscriber goroutine to finish
    select {
    case <-s.receiveDone:
        // Clean exit
    case <-ctx.Done():
        return fmt.Errorf("subscriber did not exit in time")
    }

    // Now safe to close the client
    return s.client.Close()
}

func (s *Service) Start(ctx context.Context) error {
    s.receiveDone = make(chan struct{})
    go func() {
        defer close(s.receiveDone)
        err := s.sub.Receive(ctx, s.handleMessage)
        if err != nil && err != context.Canceled {
            log.Printf("Receive error: %v", err)
        }
    }()
    return nil
}
```

## Key Takeaways

1. **`topic.Stop()` must come before cancelling the context.** It flushes pending publishes; cancelling the context stops accepting new ones.
2. **Always wait for `Receive` to exit** before closing the client. Use a channel or `sync.WaitGroup` to signal completion.
3. **Use a separate context for the subscriber** so you can cancel it independently of publisher operations.
4. **`client.Close()` is always last** — it's idempotent and safe, but only after all goroutines have exited.
5. **Set a timeout on shutdown** (e.g., 30s) so a stuck `Receive` doesn't hang your process indefinitely.

See [references/go-client.md](references/go-client.md) for the full lifecycle contract and [references/publishing.md](references/publishing.md) for `Stop()` semantics.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the required shutdown sequence well, but Answer A is more thorough and precise on every criterion. It explicitly explains why Receive blocks until ctx.Done or an error fires and until all callbacks return, gives a cleaner code example with LIFO defer ordering, and more clearly articulates why the order of operations matters (subscribers may publish, so they must drain before publishers stop). Answer B is solid but slightly less complete in explaining the Receive blocking semantics and uses a WaitGroup pattern that is somewhat redundant given that Receive already waits for callbacks.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| cancel ctx to break out of Receive | skill |
| explains Receive blocks until ctx.Done or error | skill |
| calls Topic.Stop before client.Close | tie |
| mentions order of operations matters | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cancel ctx to break out of Receive | ✓ | `cancel()` |
| explains Receive blocks until ctx.Done or error | ✓ | `ctx.Done` |
| calls Topic.Stop before client.Close | ✓ | `topic.Stop()` is what actually drains the publish buffer; just canceling a context doesn't.  ## Sketch  ```go func run(ctx context.Context) error {     client, …` |
| mentions order of operations matters | ✓ | `order` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| cancel ctx to break out of Receive | ✓ | `cancel()` |
| explains Receive blocks until ctx.Done or error | ✓ | `ctx.Done` |
| calls Topic.Stop before client.Close | ✓ | `topic.Stop() on each topic      → flushes pending publish batches 4. Call client.Close` |
| mentions order of operations matters | ✓ | `order` |

<details><summary>opus: baseline answer</summary>

# Pub/Sub Graceful Shutdown in Go

The right ordering matters because the subscriber and publisher have different lifecycles. Here's the sequence that works reliably:

## The correct order

1. **Stop accepting new work** (HTTP server, etc.)
2. **Cancel the subscriber's `Receive` context** — let in-flight message handlers finish (Ack/Nack)
3. **Wait for handlers to drain**
4. **Call `topic.Stop()` on publishers** — this flushes buffered messages and blocks until pending publishes complete
5. **Close the client(s)**

## Why your current code hangs / loses messages

- `Receive` returns only after **all message callbacks return**. If a callback tries to publish during shutdown and the publisher is already closed (or its context is canceled), it blocks or errors → `Receive` never returns.
- Canceling the context passed to `topic.Publish` cancels the in-flight RPC. The message is lost. You want to let `Stop()` flush instead.
- `topic.Stop()` is what actually drains the publish buffer; just canceling a context doesn't.

## Sketch

```go
func run(ctx context.Context) error {
    client, _ := pubsub.NewClient(ctx, projectID)
    defer client.Close()

    topic := client.Topic("out")
    sub := client.Subscription("in")

    // Separate context for Receive so we control cancellation explicitly.
    recvCtx, cancelRecv := context.WithCancel(context.Background())

    var handlersWG sync.WaitGroup
    recvDone := make(chan error, 1)

    go func() {
        recvDone <- sub.Receive(recvCtx, func(mctx context.Context, m *pubsub.Message) {
            handlersWG.Add(1)
            defer handlersWG.Done()

            // IMPORTANT: don't pass recvCtx to Publish. Use a context
            // that isn't canceled at shutdown, so Stop() can flush.
            result := topic.Publish(context.Background(), &pubsub.Message{Data: m.Data})
            if _, err := result.Get(mctx); err != nil {
                m.Nack()
                return
            }
            m.Ack()
        })
    }()

    // Wait for shutdown signal...
    <-ctx.Done()

    // 1. Stop pulling new messages and let in-flight callbacks finish.
    cancelRecv()
    if err := <-recvDone; err != nil && !errors.Is(err, context.Canceled) {
        log.Printf("receive error: %v", err)
    }
    handlersWG.Wait()

    // 2. Flush the publisher. Stop() blocks until all buffered messages
    //    are sent or permanently fail.
    topic.Stop()

    return nil
}
```

## Key gotchas

- **Don't pass the request/receive context to `Publish`.** If you do, canceling it at shutdown drops queued messages. Use `context.Background()` (or a long-lived shutdown context) and rely on `topic.Stop()` to bound publish duration.
- **Tune `ReceiveSettings.Synchronous` or `MaxOutstandingMessages`** if you have very long handlers — otherwise shutdown can be slow because `Receive` waits for all of them.
- **Set a hard deadline** on the whole shutdown so a stuck handler can't pin the process forever:
  ```go
  shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
  defer cancel()
  ```
  Then run the drain in a goroutine and select on `shutdownCtx.Done()`.
- **Don't `client.Close()` before `topic.Stop()`** — that yanks the connection out from under the flush.

The mental model: `Receive`'s context controls *intake*, `topic.Stop()` controls *outtake*. You stop intake first, drain handlers, then flush outtake.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Correct Pub/Sub Shutdown Sequence in Go

You're hitting two distinct issues. Let me address each, then give you the canonical pattern.

## What's going wrong

**Lost publishes:** Cancelling the context does *not* flush the publisher's internal batch. `Topic.Publish` returns immediately and buffers messages; they're only sent when a batch threshold trips or you call `Topic.Stop()`. If you exit before `Stop()` returns, in-flight batches are dropped on the floor — `PublishResult.Get()` will return an error, but the messages are gone.

**Receive "hanging":** `Subscription.Receive` is supposed to return when its context is cancelled, but it waits for all in-flight callbacks to return first. If your callbacks check `ctx.Done()` on the *same* context you cancelled, fine — but if they're blocked on a downstream call (DB write, HTTP request, channel send to the publisher you just stopped), `Receive` will sit there waiting for them.

The classic deadlock: subscriber callback publishes a message and calls `result.Get(ctx)` with the cancelled context → `Get` returns an error → the callback nacks → but if you've already called `Topic.Stop()`, publishes fail and your callback may loop or block.

## Correct shutdown order

```
1. Cancel the subscriber context        → stop pulling new messages
2. Wait for Receive() to return         → all callbacks have finished
3. Call topic.Stop() on each topic      → flushes pending publish batches
4. Call client.Close()                  → tears down gRPC connections
```

The order matters: subscribers may publish, so subscribers must drain *before* publishers stop.

## Pattern

```go
func run(ctx context.Context) error {
    client, err := pubsub.NewClient(ctx, projectID)
    if err != nil {
        return err
    }
    defer client.Close() // (4) last

    topic := client.Topic("outbound")
    topic.EnableMessageOrdering = true // if you need it
    defer topic.Stop() // (3) flushes pending batches; blocks until done

    sub := client.Subscription("inbound")
    sub.ReceiveSettings.MaxOutstandingMessages = 100
    sub.ReceiveSettings.NumGoroutines = 1

    // Separate context for Receive so we control its lifetime.
    recvCtx, cancelRecv := context.WithCancel(ctx)
    defer cancelRecv()

    recvDone := make(chan error, 1)
    go func() {
        recvDone <- sub.Receive(recvCtx, func(cbCtx context.Context, msg *pubsub.Message) {
            // Do work synchronously. Don't hand off to a background goroutine
            // and return — the lease stops extending the moment this returns.
            if err := handle(cbCtx, topic, msg); err != nil {
                msg.Nack()
                return
            }
            msg.Ack()
        })
    }()

    // Wait for outer shutdown signal.
    <-ctx.Done()

    // (1) Stop pulling new messages and wait for in-flight callbacks.
    cancelRecv()

    // (2) Block until Receive returns — all callbacks have finished publishing.
    if err := <-recvDone; err != nil && err != context.Canceled {
        log.Printf("Receive returned: %v", err)
    }

    // defers fire in LIFO order: topic.Stop() then client.Close().
    return nil
}
```

## Critical details

- **Don't reuse the cancelled context inside callbacks for publishing.** When your subscriber callback publishes a message, pass a *fresh* context (or `context.Background()` with a timeout) to `result.Get()`. Otherwise, on shutdown, the cancelled context kills the publish wait before `Stop()` can flush it. The callback's `cbCtx` is cancelled when `Receive` is shutting down — that's the wrong context to pass to a publish you want to complete.

- **`topic.Stop()` blocks until pending batches are flushed.** This is the line that prevents lost publishes. It is idempotent and safe in `defer`.

- **Don't call `Receive` again after it returns.** Once it exits (cleanly or with error), that `Subscription` invocation is done. If you want to restart, call `Receive` again — but not concurrently with the previous one.

- **If callbacks block forever, `Receive` blocks forever.** Cancellation does not forcibly kill your callback. Make sure `handle()` respects `cbCtx.Done()` (or has its own timeout) on every potentially-blocking call. A common fix: `handleCtx, cancel := context.WithTimeout(cbCtx, 30*time.Second); defer cancel()`.

- **Set a hard deadline on shutdown.** In production, wrap the whole shutdown sequence in a timeout so a stuck callback doesn't prevent process exit:

  ```go
  shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
  defer cancel()
  // ... but note: defers above will still try to run topic.Stop() etc.
  // Use shutdownCtx for any work you do during shutdown, not for the defers.
  ```

  If `topic.Stop()` itself is hanging (rare, network-related), you'd need to wrap it in a goroutine with a timeout, but that means accepting message loss.

## Quick checklist

- [ ] `defer client.Close()` registered first (runs last)
- [ ] `defer topic.Stop()` registered after client (runs before Close)
- [ ] Separate cancellable context for `Receive`, distinct from your shutdown signal context
- [ ] `Receive` runs in its own goroutine; main path waits on a done channel
- [ ] Callbacks do work synchronously, don't spawn-and-return
- [ ] Publishes inside callbacks use a *non-cancelled* context for `result.Get()`
- [ ] Callbacks have their own timeouts on downstream calls

For more detail on the publisher and subscriber lifecycle separately, see `references/publishing.md` and `references/subscribing.md` in the pubsub skill, and `references/go-client.md` for the full Client/Topic/Subscription contract.

</details>

---

### `flow-control-oom`

**Prompt**

```
My Pub/Sub subscriber is OOM-killing despite only having ~50
subscriptions. Each message takes about 10 seconds of CPU/IO to
process and the subscriber pulls thousands at a time. What's
actually limiting how many messages I have in flight, and how do
I tune it?
```

**Judge focus:** The better answer points at ReceiveSettings.MaxOutstandingMessages
and MaxOutstandingBytes as the in-flight cap (defaults are large —
~1000 messages / 1 GiB), explains they only protect once the
handler returns or Ack/Nack fires, and tells the user to lower
them when handlers are slow or messages are heavy.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more accurate and focused on the Go SDK, correctly naming `ReceiveSettings.MaxOutstandingMessages` and `MaxOutstandingBytes` with their actual defaults (1000 messages / 1 GiB), and explaining that the cap applies while the callback is running (not just at ack/nack). Answer B mixes Python, Java, and Go examples with incorrect defaults (claiming Python's max_bytes default is 100 MB rather than 1 GiB), and its ASCII diagram misrepresents how flow control works. Answer A also provides superior coverage of the ack-deadline interaction and the goroutine-handoff anti-pattern.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names the flow-control settings | skill |
| explains they cap concurrent in-flight work | skill |
| tells the user to lower the cap for slow / heavy messages | tie |
| mentions ack deadline as a related axis | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names the flow-control settings | ✓ | `MaxOutstandingMessages` |
| explains they cap concurrent in-flight work | ✓ | `In-Flight` |
| tells the user to lower the cap for slow / heavy messages | ✓ | `LOWER` |
| mentions ack deadline as a related axis | ✓ | `MaxExtension` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names the flow-control settings | ✓ | `MaxOutstandingMessages` |
| explains they cap concurrent in-flight work | ✓ | `in-flight` |
| tells the user to lower the cap for slow / heavy messages | ✗ | |
| mentions ack deadline as a related axis | ✓ | `ack-deadline` |

<details><summary>sonnet: baseline answer</summary>

## The Core Problem

You're hitting a **flow control** misunderstanding. The Pub/Sub client library pulls messages aggressively and buffers them in memory before your code ever sees them, so you can have thousands of messages sitting in RAM waiting to be processed while your workers are busy with the current batch.

---

## What Actually Controls In-Flight Messages

There are **three independent limits**, and the most restrictive one wins:

```
┌─────────────────────────────────────────────────────────────┐
│                    Pub/Sub Client Library                    │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  max_messages│    │  max_bytes   │    │ max_lease_    │  │
│  │  (count)    │    │  (RAM)       │    │ duration      │  │
│  └──────┬──────┘    └──────┬───────┘    └──────┬────────┘  │
│         │                  │                    │           │
│         └──────────────────┴────────────────────┘          │
│                            │                               │
│                     FlowControl                            │
│                     (the gatekeeper)                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                    Your callback/handler
```

| Limit | Default (Python) | What it does |
|---|---|---|
| `max_messages` | **1000** | Max messages pulled and held in memory |
| `max_bytes` | **100 MB** | Max total byte size of buffered messages |
| `max_lease_duration` | **1 hour** | How long before a message is nacked/redelivered |

**Your situation:** With 10s processing time and 1000 buffered messages, you're holding potentially gigabytes of message payloads in RAM before processing even starts.

---

## The Fix: Tune Flow Control

### Python (google-cloud-pubsub)

```python
from google.cloud import pubsub_v1
from google.api_core import retry

# Calculate your actual capacity:
# - How many messages can you process concurrently?
# - How much RAM can each message payload consume?

flow_control = pubsub_v1.types.FlowControl(
    max_messages=50,          # Match your actual worker concurrency
    max_bytes=50 * 1024 * 1024,  # 50 MB hard ceiling on buffered payload
    max_lease_duration=60,    # Seconds; must be > your processing time
                              # but not so long that failures stall redelivery
)

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

streaming_pull_future = subscriber.subscribe(
    subscription_path,
    callback=your_callback,
    flow_control=flow_control,
    # Also tune the executor thread pool:
    scheduler=pubsub_v1.subscriber.scheduler.ThreadScheduler(
        executor=concurrent.futures.ThreadPoolExecutor(max_workers=10)
    )
)
```

### Java (spring-cloud-gcp / google-cloud-java)

```java
FlowControlSettings flowControlSettings = FlowControlSettings.newBuilder()
    .setMaxOutstandingElementCount(50L)
    .setMaxOutstandingRequestBytes(50L * 1024 * 1024)
    .setLimitExceededBehavior(
        FlowController.LimitExceededBehavior.Block  // vs ThrowException
    )
    .build();

Subscriber subscriber = Subscriber.newBuilder(subscriptionName, receiver)
    .setFlowControlSettings(flowControlSettings)
    .setParallelPullCount(1)          // number of streaming pull connections
    .setExecutorProvider(
        InstantiatingExecutorProvider.newBuilder()
            .setExecutorThreadCount(10)
            .build()
    )
    .build();
```

### Go

```go
sub.ReceiveSettings = pubsub.ReceiveSettings{
    MaxOutstandingMessages: 50,
    MaxOutstandingBytes:    50 * 1024 * 1024,
    NumGoroutines:          10,   // parallel pulls
    MaxExtension:           60 * time.Second,
    MaxExtensionPeriod:     0,    // let library manage
}
```

---

## Sizing the Numbers Correctly

```
                    Your processing pipeline
                    
Messages/sec you can handle = (worker_threads) / (seconds_per_message)
                            = 10 workers / 10 seconds
                            = 1 message/sec throughput

Reasonable buffer = throughput × acceptable_latency_seconds
                  = 1 msg/sec × 30 seconds
                  = ~30 messages buffered at once

So max_messages = 30-50 is sensible, NOT 1000
```

**For bytes:**
```
max_bytes = max_messages × avg_message_size × safety_factor
          = 50 × 1MB × 2
          = 100 MB

Set this LOWER than your available RAM minus your app's working set
```

---

## The Lease Duration Trap

This is a subtle OOM amplifier:

```
Timeline with 10s processing and default 1-hour lease:

t=0:    Pull 1000 messages, all held in memory
t=10s:  First 10 processed and acked
t=20s:  Next 10 processed...
t=16min: Still holding ~900 messages in RAM
t=1hr:  Unprocessed messages get redelivered → DUPLICATE WORK
```

**Fix:** Set `max_lease_duration` to something like `processing_time × 3` with a floor of 60 seconds. The library will auto-extend leases for messages actively being processed.

---

## Checklist

```
[ ] Set max_messages to match actual worker concurrency (not default 1000)
[ ] Set max_bytes to a fraction of available container RAM
[ ] Set max_lease_duration > your p99 processing time
[ ] Set thread pool size to match max_messages (no point having 1000 slots, 5 threads)
[ ] Set LimitExceededBehavior to Block, not ThrowException
[ ] Monitor: subscription/num_undelivered_messages in Cloud Monitoring
[ ] Consider: is your processing actually parallelizable, or is it I/O bound?
```

---

## Quick Sanity Check

If you're still OOM after tuning flow control, check whether your **callback itself** is accumulating state — e.g., appending results to a list, building a batch for downstream writes, etc. Flow control only limits what the *library* buffers; your application code can still leak memory independently.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The OOM is almost certainly caused by the default flow-control limits being far too permissive for your workload. Here is exactly what is happening and how to fix it.

## What actually controls in-flight messages

`Subscription.Receive` has two independent governors, both set in `ReceiveSettings`:

| Setting | Default | What it caps |
|---|---|---|
| `MaxOutstandingMessages` | 1,000 | Count of messages whose callbacks have started but not yet acked/nacked |
| `MaxOutstandingBytes` | 1,073,741,824 (1 GiB) | Total size of those same in-flight messages |

**Both limits apply simultaneously.** Pub/Sub stops pulling new messages the moment either ceiling is hit. With 10-second processing time and defaults, you can have up to 1,000 messages in memory at once — each holding whatever data it carries plus your processing state. That is almost certainly your OOM source.

There is a third knob that interacts with the above:

| Setting | Default | What it controls |
|---|---|---|
| `NumGoroutines` | 10 | Goroutines used for `StreamingPull` RPCs (not callback concurrency) |

`NumGoroutines` is **not** a concurrency cap on your callback. The SDK dispatches each message to its own goroutine. The only thing preventing unbounded goroutine spawning is `MaxOutstandingMessages`.

## Sizing the limits for your workload

With 10-second processing time, work backwards from how much memory you can safely allocate to in-flight messages:

```
MaxOutstandingMessages = floor(memory_budget_bytes / avg_message_bytes_in_memory)
```

"Bytes in memory" means the message payload **plus** whatever your handler allocates per message during processing. If each message is 10 KB on the wire but your handler builds a 5 MB intermediate structure, budget 5 MB per slot, not 10 KB.

A concrete example: 512 MiB budget, 2 MiB per message in flight → cap at **256 messages**.

Set `MaxOutstandingBytes` to the same budget as a belt-and-suspenders guard:

```go
sub.ReceiveSettings = pubsub.ReceiveSettings{
    MaxOutstandingMessages: 256,
    MaxOutstandingBytes:    512 * 1024 * 1024, // 512 MiB
    MaxExtension:           20 * time.Minute,  // see below
    NumGoroutines:          10,                // leave this alone unless you have network latency issues
}
```

## The ack-deadline trap with 10-second processing

The default ack deadline is **10 seconds**, and the SDK extends it automatically — but only while the message is inside the `Receive` callback. With 10-second CPU/IO work you are right at the edge. If processing occasionally runs long, the lease expires and the message redelivers, which means:

1. You now have the original message **and** the redelivery both in flight.
2. Your in-flight count climbs past your cap.
3. Memory spikes.

Fix this by raising `MaxExtension` to comfortably exceed your worst-case processing time. 20 minutes is a safe ceiling for 10-second average work with variance:

```go
MaxExtension: 20 * time.Minute,
```

The SDK will keep extending the lease in the background as long as the callback has not returned.

## The callback-goroutine handoff trap

If your handler looks like this, you have a hidden leak:

```go
// WRONG — callback returns immediately, lease stops extending,
// message redelivers, and your goroutine pool is unbounded
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    go func() {
        process(msg)
        msg.Ack()
    }()
})
```

The callback must not return until processing is complete. The correct pattern:

```go
// RIGHT — callback blocks until work is done
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    if err := process(msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

If you need a bounded worker pool (e.g., to limit DB connections), use a semaphore inside the callback, not a goroutine handoff:

```go
sem := make(chan struct{}, 20) // at most 20 concurrent DB operations

sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    sem <- struct{}{}        // block here if pool is full
    defer func() { <-sem }()

    if err := process(msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

This keeps the callback alive (lease extends), caps concurrency, and lets `MaxOutstandingMessages` do its job as the outer gate.

## Putting it together

```go
client, err := pubsub.NewClient(ctx, projectID)
if err != nil { ... }
defer client.Close()

sub := client.Subscription(subscriptionID)
sub.ReceiveSettings = pubsub.ReceiveSettings{
    // Tune these two to your memory budget
    MaxOutstandingMessages: 256,
    MaxOutstandingBytes:    512 * 1024 * 1024,

    // Must exceed worst-case processing time
    MaxExtension: 20 * time.Minute,

    // Leave at default unless you have high network latency
    NumGoroutines: 10,
}

sem := make(chan struct{}, 20) // optional: cap DB/IO concurrency independently

if err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    sem <- struct{}{}
    defer func() { <-sem }()

    if err := process(msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
}); err != nil && !errors.Is(err, context.Canceled) {
    log.Fatal(err)
}
```

## Monitoring to validate the tuning

After deploying, watch these two Cloud Monitoring metrics on your subscription:

- **`subscription/num_undelivered_messages`** — backlog size. Should be stable or draining, not growing.
- **`subscription/oldest_unacked_message_age`** — if this climbs past your ack deadline, you have a redelivery loop.

If `oldest_unacked_message_age` is high but your handler is completing, the lease extension is not keeping up — raise `MaxExtension` further or check that you are not doing the goroutine-handoff anti-pattern above.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies ReceiveSettings.MaxOutstandingMessages and MaxOutstandingBytes as the primary flow-control knobs, explains their defaults (1000 messages / 1 GiB), and gives clear guidance on lowering them for slow handlers. Answer B misidentifies maxExtension as the 'key insight' and incorrectly states the default for maxOutstandingBytes as 100MB (it's 1 GiB), and its explanation of the OOM cause via re-delivery duplicates is confused and misleading. Answer A also mentions ack deadline as a related axis and provides a coherent tuning formula.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names the flow-control settings | skill |
| explains they cap concurrent in-flight work | skill |
| tells the user to lower the cap for slow / heavy messages | skill |
| mentions ack deadline as a related axis | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names the flow-control settings | ✓ | `maxOutstandingMessages` |
| explains they cap concurrent in-flight work | ✓ | `In-Flight` |
| tells the user to lower the cap for slow / heavy messages | ✓ | `Reduce` |
| mentions ack deadline as a related axis | ✓ | `maxExtension` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names the flow-control settings | ✓ | `MaxOutstandingMessages` |
| explains they cap concurrent in-flight work | ✓ | `in-flight` |
| tells the user to lower the cap for slow / heavy messages | ✓ | `Lower` |
| mentions ack deadline as a related axis | ✗ | |

<details><summary>haiku: baseline answer</summary>

# Pub/Sub Subscriber Memory Tuning

The key insight: **you're likely hitting the `maxExtension` limit**, not subscription count. Here's what's actually limiting you:

## What Controls In-Flight Messages

1. **`maxExtension` (default: 600 seconds)** - The total time a message can be held before being re-delivered
   - If processing takes 10s and you pull 1000 messages, you're holding them for ~10,000 seconds total
   - Messages beyond `maxExtension` get re-delivered, creating duplicates and memory pressure

2. **`maxOutstandingMessages`** (default: 1000) - Hard cap on messages pulled at once
   - This is your immediate limiter, but it's not the memory problem

3. **`maxOutstandingBytes`** (default: 100MB) - Memory cap per subscriber
   - This is likely what's killing you

## The Real Problem

With 10-second processing per message:
```
1000 messages × 10 seconds = 10,000 seconds of holding time
But maxExtension = 600 seconds
→ Messages get re-delivered while still in memory
→ Duplicates pile up
→ OOM
```

## Solutions (in order of effectiveness)

### 1. **Reduce `maxOutstandingMessages`** (Immediate fix)
```python
subscriber = subscriber_client.subscribe(
    subscription_path,
    callback,
    flow_control=pubsub_v1.types.FlowControl(
        max_messages=100,  # Down from 1000
        max_bytes=10 * 1024 * 1024,  # 10MB instead of 100MB
    ),
)
```

Start with `max_messages = (600 seconds / 10 seconds per message) = 60` as a baseline.

### 2. **Increase `maxExtension`** (If you control message TTL)
```python
# In your subscriber callback, extend the deadline
def callback(message):
    # Extend before processing
    message.drop_by_deadline = time.time() + 30  # 30 more seconds
    
    # Do your 10-second work
    process_message(message)
    
    message.ack()
```

Or use `modify_ack_deadline()`:
```python
subscriber_client.modify_ack_deadline(
    request={
        "subscription": subscription_path,
        "ack_ids": [message.ack_id],
        "ack_deadline_seconds": 30,  # Extend deadline
    }
)
```

### 3. **Batch processing** (Best for throughput)
```python
messages_batch = []

def callback(message):
    messages_batch.append(message)
    if len(messages_batch) >= 10:
        process_batch(messages_batch)
        for msg in messages_batch:
            msg.ack()
        messages_batch.clear()
    else:
        message.nack()  # Redeliver, we'll process in batch
```

### 4. **Increase subscriber resources**
If you genuinely need high throughput:
```python
# Multiple subscriber instances (recommended)
# Each with reduced flow control:
flow_control=pubsub_v1.types.FlowControl(
    max_messages=50,
    max_bytes=5 * 1024 * 1024,
)
```

## Diagnostic Checklist

```python
# Log what's actually happening
def callback(message):
    start = time.time()
    try:
        process_message(message)
        elapsed = time.time() - start
        print(f"Processed in {elapsed:.2f}s, ack_deadline: {message.ack_deadline}")
    except Exception as e:
        print(f"Failed after {time.time() - start:.2f}s: {e}")
        message.nack()
    else:
        message.ack()
```

## Quick Win

**Start here:**
```python
flow_control=pubsub_v1.types.FlowControl(
    max_messages=50,  # Conservative
    max_bytes=10 * 1024 * 1024,  # 10MB
)
```

Then monitor memory and gradually increase until you hit OOM again. The sweet spot is usually `max_messages = (ack_deadline / avg_processing_time) × 0.8`.

What language/client are you using? The exact API varies slightly.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Pub/Sub Subscriber OOM: Flow Control Tuning

You're hitting the **flow-control ceiling**, not the subscription count. The Go SDK's `Subscription.Receive` has two independent limits that cap in-flight messages *per call*, and you're almost certainly maxing out the default **1000 messages / 1 GiB** before your handler finishes processing them.

## What's Actually Limiting You

When you call `subscription.Receive(ctx, callback)`, the SDK maintains a local buffer of unacked messages. Two knobs control this:

| Knob | Default | Your Scenario |
|---|---|---|
| `MaxOutstandingMessages` | 1000 | **You're hitting this.** 1000 msgs × 10s each = 10,000s of queued work. |
| `MaxOutstandingBytes` | 1 GiB | Probably not the bottleneck unless messages are huge. |

The SDK **will not pull more messages from the broker** once either limit is reached. But those 1000 messages are already in your process's memory, and if each one spawns a goroutine or holds a resource, you OOM before the handler finishes.

The key insight: **flow control is per `Receive` call, not per subscription.** 50 subscriptions × 1000 msgs each = 50,000 in-flight messages if you call `Receive` on all 50 concurrently.

## How to Diagnose

1. **Check your current settings:**
   ```go
   sub := client.Subscription("my-sub")
   settings := sub.ReceiveSettings
   fmt.Printf("MaxOutstandingMessages: %d\n", settings.MaxOutstandingMessages)
   fmt.Printf("MaxOutstandingBytes: %d\n", settings.MaxOutstandingBytes)
   fmt.Printf("NumGoroutines: %d\n", settings.NumGoroutines)
   ```
   If you haven't set them, you're using defaults.

2. **Estimate your memory per message:**
   - Message body size (check `msg.Data` length in logs)
   - Any context you attach (goroutine stack, buffered channels, etc.)
   - Multiply by `MaxOutstandingMessages` to get peak in-flight memory

3. **Check if you're calling `Receive` on multiple subscriptions concurrently:**
   ```go
   // BAD: 50 Receive calls in parallel = 50 × 1000 msgs in memory
   for _, sub := range subscriptions {
       go sub.Receive(ctx, callback)
   }
   
   // GOOD: one Receive per subscription, sequentially or with a bounded pool
   ```

## Tuning Strategy

### Step 1: Lower `MaxOutstandingMessages`

Start aggressive — your 10-second handler means you want **at most 10–20 messages in flight** to keep CPU busy without buffering:

```go
sub := client.Subscription("my-sub")
sub.ReceiveSettings.MaxOutstandingMessages = 20  // Not 1000
sub.ReceiveSettings.MaxOutstandingBytes = 100 * 1024 * 1024  // 100 MiB, not 1 GiB

err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    // Synchronous processing — takes ~10s
    processMessage(msg)
    msg.Ack()
})
```

**Why 20?** If you have 4 CPU cores and each message takes 10s, you can process ~0.4 messages/core/sec. 20 messages gives you a small buffer for jitter without exploding memory.

### Step 2: Tune `NumGoroutines` (if using a worker pool)

The SDK spawns `NumGoroutines` (default 10) to call your callback. If your callback is synchronous (blocks until `msg.Ack()`), this is fine — the goroutines are the bottleneck, not the message buffer.

```go
sub.ReceiveSettings.NumGoroutines = 4  // Match your CPU cores
sub.ReceiveSettings.MaxOutstandingMessages = 20
```

With 4 goroutines and 20 max messages, you'll have ~5 messages per goroutine queued, which is reasonable.

### Step 3: Handle 50 Subscriptions Without Multiplying In-Flight

**Do NOT call `Receive` on all 50 subscriptions concurrently.** Instead:

```go
// Option A: Sequential (simple, but one subscription blocks others)
for _, sub := range subscriptions {
    err := sub.Receive(ctx, callback)
    if err != nil && err != context.Canceled {
        log.Printf("Receive error: %v", err)
    }
}

// Option B: Bounded pool (recommended)
const maxConcurrentReceives = 5
sem := make(chan struct{}, maxConcurrentReceives)
var wg sync.WaitGroup

for _, sub := range subscriptions {
    wg.Add(1)
    go func(s *pubsub.Subscription) {
        defer wg.Done()
        sem <- struct{}{}        // Acquire
        defer func() { <-sem }() // Release
        
        err := s.Receive(ctx, callback)
        if err != nil && err != context.Canceled {
            log.Printf("Receive error: %v", err)
        }
    }(sub)
}

wg.Wait()
```

With Option B and 5 concurrent `Receive` calls, you cap in-flight at **5 × 20 = 100 messages**, not 50,000.

### Step 4: Validate with Metrics

Monitor these Pub/Sub metrics to confirm tuning:

```bash
gcloud monitoring time-series list \
  --filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages"' \
  --format='table(metric.labels.subscription_id, points[0].value.int64_value)'
```

- **`num_undelivered_messages`**: Should stay low (< 100) if flow control is working.
- **`oldest_unacked_message_age`**: Should not grow unbounded. If it climbs, your handler is slower than the publish rate.

## Complete Example

```go
package main

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	client, err := pubsub.NewClient(ctx, "my-project")
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	subscriptions := []*pubsub.Subscription{
		client.Subscription("sub-1"),
		client.Subscription("sub-2"),
		// ... 48 more
	}

	// Tune flow control per subscription
	for _, sub := range subscriptions {
		sub.ReceiveSettings.MaxOutstandingMessages = 20
		sub.ReceiveSettings.MaxOutstandingBytes = 100 * 1024 * 1024
		sub.ReceiveSettings.NumGoroutines = 4
	}

	// Bound concurrent Receive calls
	const maxConcurrentReceives = 5
	sem := make(chan struct{}, maxConcurrentReceives)
	var wg sync.WaitGroup

	for _, sub := range subscriptions {
		wg.Add(1)
		go func(s *pubsub.Subscription) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			err := s.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
				// Synchronous processing — takes ~10s
				if err := processMessage(msg); err != nil {
					log.Printf("Process error: %v", err)
					msg.Nack()
					return
				}
				msg.Ack()
			})
			if err != nil && err != context.Canceled {
				log.Printf("Receive error on %s: %v", s.ID(), err)
			}
		}(sub)
	}

	wg.Wait()
}

func processMessage(msg *pubsub.Message) error {
	// Simulate 10s of work
	time.Sleep(10 * time.Second)
	fmt.Printf("Processed message %s\n", msg.ID)
	return nil
}
```

## Key Takeaways

| Problem | Solution |
|---|---|
| OOM with default 1000 msgs | Lower `MaxOutstandingMessages` to 10–50 based on handler latency |
| 50 subscriptions = 50,000 in-flight | Use a semaphore to bound concurrent `Receive` calls to 5–10 |
| Handler takes 10s but CPU idle | Increase `NumGoroutines` to match cores, or raise `MaxOutstandingMessages` slightly |
| Backlog growing despite tuning | Handler is slower than publish rate — add more subscriber instances or optimize processing |

**The rule:** `MaxOutstandingMessages` should be roughly `(handler_latency_seconds × publish_rate_per_second) / num_goroutines`. For 10s latency, 100 msgs/sec publish rate, and 4 goroutines: `(10 × 100) / 4 = 250` — so start at 250 and lower if memory is still tight.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more precise and complete: it correctly names both `MaxOutstandingMessages` and `MaxOutstandingBytes` as the primary Go client settings, explains the multiplicative effect across 50 subscriptions (50×1000=50,000), and covers the ack deadline/MaxExtension axis explicitly. Answer B is reasonable but mixes client libraries (Python, Java, Go) in a way that dilutes focus, uses slightly incorrect Python defaults (100 MiB vs 1 GiB), and is less precise about how the flow control interacts with slow handlers and lease extension.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names the flow-control settings | skill |
| explains they cap concurrent in-flight work | skill |
| tells the user to lower the cap for slow / heavy messages | tie |
| mentions ack deadline as a related axis | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names the flow-control settings | ✓ | `MaxOutstandingMessages` |
| explains they cap concurrent in-flight work | ✓ | `outstanding` |
| tells the user to lower the cap for slow / heavy messages | ✓ | `lower` |
| mentions ack deadline as a related axis | ✓ | `ack deadline` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names the flow-control settings | ✓ | `MaxOutstandingMessages` |
| explains they cap concurrent in-flight work | ✓ | `in-flight` |
| tells the user to lower the cap for slow / heavy messages | ✓ | `lower` |
| mentions ack deadline as a related axis | ✓ | `ack deadline` |

<details><summary>opus: baseline answer</summary>

# What's actually happening

Pub/Sub's streaming pull client is **flow-controlled by leases, not by your subscription count**. The client library opens StreamingPull connections and aggressively pulls messages up to its flow control limits, then holds them in memory while extending their ack deadlines via the lease management thread.

The defaults are surprisingly generous. In the Python client, for example:
- `max_messages`: **1000** outstanding messages
- `max_bytes`: **100 MiB** outstanding
- `max_lease_duration`: 1 hour

Java and Go have similarly large defaults. So with 50 subscriptions × 1000 messages × message payload + processing overhead, you can easily blow past container memory even though "only 50 subscriptions" sounds modest.

The compounding problem: messages take 10s each to process. If your executor only has, say, 10 worker threads, you're processing 10 at a time but the client has already pulled and is leasing **1000**. Those 990 leased-but-not-yet-processed messages sit in memory, getting their deadlines extended, until a worker frees up.

# What to tune

The right knob is **FlowControl** on the subscriber, set to roughly `concurrent_workers × small_multiplier`:

**Python:**
```python
from google.cloud import pubsub_v1

flow_control = pubsub_v1.types.FlowControl(
    max_messages=20,        # ~2x your worker count
    max_bytes=10 * 1024 * 1024,
)

# Bound the executor too
executor = futures.ThreadPoolExecutor(max_workers=10)
scheduler = pubsub_v1.subscriber.scheduler.ThreadScheduler(executor=executor)

subscriber.subscribe(sub_path, callback, flow_control=flow_control,
                     scheduler=scheduler)
```

**Java:**
```java
Subscriber.newBuilder(sub, receiver)
    .setFlowControlSettings(FlowControlSettings.newBuilder()
        .setMaxOutstandingElementCount(20L)
        .setMaxOutstandingRequestBytes(10L * 1024 * 1024)
        .build())
    .setExecutorProvider(...) // bounded
    .build();
```

**Go:**
```go
sub.ReceiveSettings.MaxOutstandingMessages = 20
sub.ReceiveSettings.MaxOutstandingBytes = 10 * 1024 * 1024
sub.ReceiveSettings.NumGoroutines = 1  // streams per client
```

# Sizing rule of thumb

For long-running messages, set `max_messages ≈ 1.5–2× concurrent_processing_capacity`. With 10s processing and 10 workers, 20 outstanding gives you a small buffer without ballooning memory. If you have 50 subscriptions in one process, divide that budget across them — each subscriber has its own flow control.

Also worth checking:
- **Subscription's `ack_deadline`** vs `max_lease_duration`: the client extends deadlines automatically up to `max_lease_duration`, so make sure that's longer than your worst-case processing time (default 1h is usually fine).
- **`NumGoroutines` / stream count**: more streams = more parallel pulling, more memory pressure. One stream per process is often enough.
- **Horizontal scaling**: 50 subs × 10s/msg in one container is a lot. Split across pods and let each have a small flow control window.

# Quick diagnostic

Look at the `subscription/num_outstanding_messages` metric in Cloud Monitoring per subscriber instance. If it's pinned near your `max_messages` ceiling and your processing rate is much lower, that's your memory.

</details>

<details><summary>opus: skill-loaded answer</summary>

# What's actually limiting in-flight messages

The thing pulling "thousands at a time" is **`ReceiveSettings.MaxOutstandingMessages`** on each `Subscription.Receive` call. The Go client defaults are:

```go
MaxOutstandingMessages = 1000   // per Receive call
MaxOutstandingBytes    = 1 << 30 // 1 GiB per Receive call
NumGoroutines          = 10      // StreamingPull streams per Receive call
```

These limits are **per `Receive` call, not per process**. With ~50 subscriptions each running their own `Receive`, your effective ceiling is **50 × 1000 = 50,000 messages and 50 GiB of buffer budget** before flow control kicks in. That's your OOM.

`NumGoroutines` is also misleading — it controls the number of StreamingPull *streams*, not the worker concurrency. Each stream can deliver messages to many concurrent callback goroutines, bounded only by `MaxOutstandingMessages`.

# Why slow handlers make this worse

With 10s processing per message:

1. The SDK leases a message and starts auto-extending the ack deadline via `modifyAckDeadline` calls in the background.
2. The message stays in the in-memory buffer (counting against `MaxOutstandingMessages` / `MaxOutstandingBytes`) for the entire 10s.
3. At 1000 outstanding × 10s, you're holding up to 1000 messages resident per subscription continuously.
4. If processing exceeds `MaxExtension` (default: unlimited in newer SDK versions, but historically 60 min), the lease stops extending and the message redelivers — adding *more* in-flight copies, not fewer.

# How to tune it

For 50 subscriptions × 10s handlers, you want a small per-subscription budget:

```go
sub := client.Subscription("my-sub")
sub.ReceiveSettings = pubsub.ReceiveSettings{
    // Cap in-flight per subscription. With 50 subs, this is 50*20 = 1000 total.
    MaxOutstandingMessages: 20,

    // Cap bytes too — pick based on your message size. 50 MiB per sub
    // gives 2.5 GiB total ceiling across 50 subs.
    MaxOutstandingBytes: 50 << 20,

    // Fewer streams per sub; you don't need 10 when concurrency is 20.
    NumGoroutines: 1,

    // Cap how long the SDK will keep extending the lease. If a handler
    // hangs past this, let it redeliver rather than pinning memory.
    MaxExtension: 10 * time.Minute,

    // Optional: cap a single extension period. Default is fine for most.
    MaxExtensionPeriod: 0,
}

err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    // Synchronous work here. Do NOT spawn a goroutine and return —
    // the lease stops extending the moment this function returns.
    process(msg)
    msg.Ack()
})
```

# Sizing rule of thumb

```
total in-flight ≈ Σ (MaxOutstandingMessages_i × avg_message_bytes_i)
```

Pick a process-wide memory budget (say, 2 GiB), divide by 50 subscriptions, divide by your average message size, and use that as `MaxOutstandingMessages` per subscription. With heavy handlers, also factor in working-set memory per concurrent message — if `process()` allocates 10 MiB of scratch space, 20 concurrent × 10 MiB = 200 MiB just for live processing, on top of buffered messages.

# Things to check while you're in there

1. **Synchronous handler.** The callback must do the work and call `Ack()` *before* returning. If you're doing `go process(msg)` and returning immediately, lease extension stops, you get redelivery, and the "thousands in flight" balloons further.
2. **Concurrent `Receive` calls.** Never call `Receive` twice on the same `*pubsub.Subscription` handle. If you have 50 subscriptions, you should have 50 `Subscription` handles and 50 `Receive` invocations.
3. **Graceful shutdown.** Cancel the context passed to `Receive` so it drains in-flight messages cleanly. Otherwise on SIGTERM you'll redeliver everything that was mid-processing.
4. **Watch `oldest_unacked_message_age`** in Cloud Monitoring. If it climbs after lowering `MaxOutstandingMessages`, you're now under-provisioned — raise the limit or add subscriber replicas. Pub/Sub is designed for horizontal scaling: more subscriber instances each pulling a small budget beats one instance pulling a huge one.
5. **If 10s is mostly I/O wait**, you may want higher `MaxOutstandingMessages` per sub but spread across more replicas, since the memory cost per in-flight message is lower when the handler isn't holding large buffers.

The short version: defaults assume light, fast handlers. With 10s/message × 50 subscriptions, you have to opt out of the defaults explicitly — `MaxOutstandingMessages` is the knob, and you want it small.

</details>

---

### `simplest-publish`

**Prompt**

```
Just give me the simplest, fewest-lines Go snippet to publish a
message to a Pub/Sub topic and make sure it actually went through
before the program exits.
```

**Judge focus:** The naive "shortest correct" snippet is `topic.Publish(...).Get(ctx)`
which blocks per-message — fine for one message but the trap is
teaching this as the default. The better answer either uses Get
correctly for the one-message case AND warns about the batching
implication, or shows the collect-then-Get pattern. It must call
Topic.Stop() before exit (or explain why Get() makes Stop optional
here).

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A explicitly calls `topic.Stop()` with a clear explanation of why it's required and the LIFO defer ordering, while Answer B omits `topic.Stop()` entirely. Answer A also explicitly warns about the Get-in-a-loop anti-pattern and explains the correct collect-then-Get pattern for bulk publishing. Answer B only explains `result.Get()` but misses the Stop requirement and the batching trap.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| calls Topic.Stop() before exit | skill |
| warns about Get() in a loop | skill |
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
| calls Topic.Stop() before exit | ✓ | `topic.Stop` |
| warns about Get() in a loop | ✓ | `in a loop` |
| avoids loop with Get inside without warning | ✓ | |

<details><summary>sonnet: baseline answer</summary>

```go
package main

import (
	"context"
	"fmt"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx := context.Background()

	client, err := pubsub.NewClient(ctx, "my-project")
	if err != nil {
		panic(err)
	}
	defer client.Close()

	topic := client.Topic("my-topic")

	result := topic.Publish(ctx, &pubsub.Message{Data: []byte("hello")})

	// Block until the server confirms the message was received.
	id, err := result.Get(ctx)
	if err != nil {
		panic(err)
	}

	fmt.Println("Published message ID:", id)
}
```

The key detail is **`result.Get(ctx)`** — `Publish` itself is async and only enqueues the message locally. Calling `.Get()` on the returned `PublishResult` blocks until the Pub/Sub server acknowledges it (returning the server-assigned message ID), so you're guaranteed it went through before the program exits.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the minimal correct version — with one trap called out explicitly:

```go
package main

import (
	"context"
	"fmt"
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

	topic := client.Topic("my-topic")
	defer topic.Stop() // flushes the batch before exit — required

	result := topic.Publish(ctx, &pubsub.Message{
		Data: []byte("hello"),
	})

	// Block until the server confirms receipt.
	id, err := result.Get(ctx)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("published message ID:", id)
}
```

## Two things that look optional but aren't

**`topic.Stop()`** — `Publish` is asynchronous; it queues the message into a batch and returns immediately. Without `Stop()`, any messages still in the buffer are silently dropped when `main` returns. `Stop()` flushes the buffer and waits for all in-flight RPCs to finish. It must run *before* `client.Close()`, which is why the `defer` order matters (defers run LIFO, so `topic.Stop()` fires first).

**`result.Get(ctx)`** — This is what actually blocks until Pub/Sub acknowledges the message server-side and returns the assigned message ID. Without it you have no confirmation the message was accepted, and any publish error is silently swallowed.

## The trap this avoids

A common "even simpler" version calls `topic.Publish(...)` in a loop and then calls `result.Get(...)` in a second loop. That defeats batching — the SDK can't batch messages that are already waiting on `Get`. The pattern above (publish → immediately call `Get` on the result) is fine for a single message. For bulk publishing, collect all `PublishResult`s first, *then* call `Get` on each.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly calls topic.Stop() before exit and explains why it matters, while Answer A omits Stop() entirely. Answer B also handles errors properly and explains the batching implications, whereas Answer A silently discards errors and provides no warning about the Get()-in-a-loop trap. Answer B is more complete, correct, and educational per the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| calls Topic.Stop() before exit | skill |
| warns about Get() in a loop | skill |
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
| calls Topic.Stop() before exit | ✓ | `topic.Stop` |
| warns about Get() in a loop | ✓ | `batch` |
| avoids loop with Get inside without warning | ✓ | |

<details><summary>haiku: baseline answer</summary>

```go
package main

import (
	"context"
	"log"

	"cloud.google.com/go/pubsub"
)

func main() {
	ctx := context.Background()
	client, _ := pubsub.NewClient(ctx, "your-project-id")
	defer client.Close()

	result := client.Topic("your-topic").Publish(ctx, &pubsub.Message{Data: []byte("hello")})
	_, _ = result.Get(ctx) // blocks until published
}
```

The key is `result.Get(ctx)` — it blocks until the message is actually published or returns an error if it fails.

</details>

<details><summary>haiku: skill-loaded answer</summary>

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

	topic := client.Topic("your-topic-name")
	result := topic.Publish(ctx, &pubsub.Message{
		Data: []byte("hello world"),
	})

	// Block until publish completes and get the message ID
	msgID, err := result.Get(ctx)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("Published message ID: %s\n", msgID)

	// Flush any remaining batched messages before exit
	topic.Stop()
}
```

**Why this is the correct minimal version:**

- `result.Get(ctx)` blocks until the message is actually published (or fails). Without it, the message may still be in a batch buffer when your program exits.
- `topic.Stop()` flushes the final batch. Omitting this silently drops in-flight messages on shutdown — a common trap.
- `defer client.Close()` cleans up resources.

If you skip `Stop()` or `Get()`, you have a race condition where the process exits before Pub/Sub confirms delivery. The snippet above guarantees the message reached the service before returning.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is superior on all three rubric criteria. It calls topic.Stop() before exit (via defer) and explicitly explains why it matters, while Answer A omits Stop() entirely. Answer B also warns about the Get()-in-a-loop batching trap and even provides the correct alternative pattern, while Answer A gives no such warning. Answer A's omission of topic.Stop() is a real correctness issue that the rubric specifically targets.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| calls Topic.Stop() before exit | skill |
| warns about Get() in a loop | skill |
| avoids loop with Get inside without warning | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| calls Topic.Stop() before exit | ✗ | |
| warns about Get() in a loop | ✗ | |
| avoids loop with Get inside without warning | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| calls Topic.Stop() before exit | ✓ | `topic.Stop` |
| warns about Get() in a loop | ✓ | `in a loop` |
| avoids loop with Get inside without warning | ✓ | |

<details><summary>opus: baseline answer</summary>

Here's the minimal snippet:

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

	result := client.Topic("your-topic").Publish(ctx, &pubsub.Message{
		Data: []byte("hello world"),
	})

	id, err := result.Get(ctx) // blocks until publish completes
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("published message ID: %s", id)
}
```

The key is `result.Get(ctx)` — it blocks until the message is actually acknowledged by the server, so you know it went through before the program exits.

</details>

<details><summary>opus: skill-loaded answer</summary>

The simple version is a trap: the obvious one-liner — `topic.Publish(ctx, msg).Get(ctx)` then exit — *works*, but if you ever publish more than one message that way you've defeated batching entirely (each `Get` blocks until that single message's RPC completes, so you get one RPC per message). And if you skip `topic.Stop()` on a publisher that has any in-flight messages, those get dropped on process exit.

Here's the correct minimal version:

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

	topic := client.Topic("my-topic")
	defer topic.Stop() // flushes pending batches

	result := topic.Publish(ctx, &pubsub.Message{Data: []byte("hello")})

	id, err := result.Get(ctx) // blocks until the server acks the publish
	if err != nil {
		log.Fatalf("publish failed: %v", err)
	}
	log.Printf("published %s", id)
}
```

Why each line is non-negotiable:

- **`defer client.Close()`** — releases the gRPC connection.
- **`defer topic.Stop()`** — flushes any batched-but-not-yet-sent messages. For a single `Publish` followed by `Get`, the message is already on the wire, but `Stop` is the habit you want; the day you add a second `Publish` call without it, you'll silently drop messages on exit.
- **`result.Get(ctx)`** — this is what makes "actually went through before the program exits" true. It returns the server-assigned message ID on success or an error. Without it you have no confirmation.

If you're publishing many messages in a loop, **don't** call `Get` inside the loop — collect the `*PublishResult` values and `Get` them after the loop (or from a worker goroutine), so the client can batch.

</details>

---

### `offtopic-css-flexbox`

**Prompt**

```
What's the simplest CSS to vertically and horizontally center a
div inside its parent, using flexbox?
```

**Judge focus:** This question has nothing to do with Pub/Sub. Both answers should be
essentially equivalent. Pick "tie" unless one is materially wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same correct CSS solution with identical properties. Answer B includes a slightly more complete example by showing the height property integrated into the main CSS block and adds a note about flex-direction, while Answer A uses a table format for quick reference. Neither is materially better or worse.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## Centering a Div with Flexbox

Here's the simplest CSS to center a div both vertically and horizontally:

```css
.parent {
  display: flex;
  justify-content: center; /* horizontal */
  align-items: center;     /* vertical */
}
```

```html
<div class="parent">
  <div class="child">Centered!</div>
</div>
```

> **Note:** The parent needs a defined height for vertical centering to work (e.g. `height: 100vh` or `height: 100%`).

### Quick Reference

| Property | Effect |
|---|---|
| `justify-content: center` | Centers along the **main axis** (horizontal by default) |
| `align-items: center` | Centers along the **cross axis** (vertical by default) |

That's it — just **3 lines** on the parent element! No need to touch the child element at all.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the simplest flexbox centering CSS:

```css
.parent {
  display: flex;
  align-items: center;
  justify-content: center;
}
```

That's it — no properties needed on the child div.

**Quick breakdown:**
- `align-items: center` — centers along the **cross axis** (vertically, in a row layout)
- `justify-content: center` — centers along the **main axis** (horizontally, in a row layout)

**One thing to note:** the parent needs a defined height for vertical centering to be visible, otherwise it just shrinks to fit its content:

```css
.parent {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh; /* or any fixed/percentage height */
}
```

If you need to support centering **multiple children** and want them in a column instead, just add `flex-direction: column` — `align-items` and `justify-content` swap their axes accordingly.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same correct CSS solution with identical properties. Answer B includes slightly more explanation and a complete HTML example, but the core content is equivalent and neither is materially wrong or better for this CSS question.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# Centering with Flexbox

```css
.parent {
  display: flex;
  justify-content: center;  /* horizontal */
  align-items: center;      /* vertical */
  height: 100vh;            /* or any height */
}
```

That's it! The three essential properties are:
- **`display: flex`** — enables flexbox
- **`justify-content: center`** — centers horizontally
- **`align-items: center`** — centers vertically

The parent needs a defined height for vertical centering to work. Here's a complete example:

```html
<style>
  .parent {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
  }
</style>

<div class="parent">
  <div>Centered content</div>
</div>
```

</details>

<details><summary>haiku: skill-loaded answer</summary>

```css
.parent {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh; /* or any height */
}
```

That's it. `justify-content: center` centers horizontally, `align-items: center` centers vertically. The parent needs an explicit height for vertical centering to be visible.

If the parent's height is already defined (e.g., by its own parent or layout), you can skip the `height` line.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide identical CSS code and are both correct. Answer B adds slightly more explanation about what each property does, but the difference is minimal and both are equally useful for the question asked.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

```css
.parent {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

That's it. `justify-content` handles horizontal centering (along the main axis), and `align-items` handles vertical centering (along the cross axis). The child `div` doesn't need any special styles.

</details>

<details><summary>opus: skill-loaded answer</summary>

```css
.parent {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

That's it — three lines on the parent. The child needs no special styles.

</details>

---
