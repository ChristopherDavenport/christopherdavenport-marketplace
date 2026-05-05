# Eval report: `pubsub`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **6**
- Models: **sonnet, haiku, opus**
- Total cost: **$1.75** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 5/6 | 4 / 0 / 2 | 87% → 100% (+13%) |
| `haiku` | 6/6 | 5 / 0 / 1 | 58% → 100% (+42%) |
| `opus` ¹ | 4/6 | 4 / 1 / 1 | 80% → 100% (+20%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 4 | 3/4 | 4/4 | 3/4 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 1/1 | 0/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `duplicate-processing` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `ordering-keys-not-working` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `publish-throughput-low` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `dead-letter-not-working` | skill_wins | ✗ = tie | ✓ ✓ skill | ✗ = tie |
| `simplest-publish` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-css-flexbox` | tie | ✓ = tie | ✓ = tie | ✗ ✗ baseline |

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

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more focused on the Go SDK context implied by the question, provides a concrete and accurate explanation of why fire-and-forget goroutines break lease extension, and gives a more precise idempotency example using msg.ID as the dedup key with a database unique constraint. Answer B covers the same topics but is written in Python, misses the goroutine/callback-return trap that is the most common Go-specific cause, and its idempotency example uses Redis with a TTL which can expire before the retention window ends—a subtle but real flaw.

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
| considers ack deadline / slow handler / lease extension | ✓ | `ack deadline` |

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

`msg.Ack()` being called doesn't guarantee exactly-once delivery. Several things can cause duplicates:

```
Publisher → Pub/Sub → Subscriber 1 ✓ Ack'd
                    → Subscriber 2 ✓ Ack'd  ← same message, different subscriber
                    → Subscriber 1 again    ← ack deadline expired before processing finished
```

### Root Causes

| Cause | Description |
|-------|-------------|
| **Ack deadline exceeded** | Processing takes longer than the deadline (default 10-60s), Pub/Sub assumes failure and redelivers |
| **Ack not confirmed** | Network issue means the ack never reached Pub/Sub |
| **At-least-once guarantee** | Pub/Sub explicitly guarantees this — duplicates are *by design* |
| **Multiple subscriptions** | Each subscription gets every message |
| **Subscriber crash** | Process died after processing but before ack was confirmed |

---

## Solutions

### 1. Extend the Ack Deadline During Long Processing

```python
import threading
from google.cloud import pubsub_v1

def process_message(msg):
    # Keep extending deadline while processing
    stop_event = threading.Event()
    
    def heartbeat():
        while not stop_event.wait(timeout=30):  # extend every 30s
            msg.modify_ack_deadline(60)          # push deadline 60s into future
    
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    
    try:
        do_slow_work(msg.data)
        msg.ack()
    except Exception as e:
        msg.nack()
        raise
    finally:
        stop_event.set()
        thread.join()
```

### 2. Idempotent Processing (Most Important)

**Design your handler so running it twice has the same effect as running it once:**

```python
def handle_message(msg):
    message_id = msg.message_id
    data = json.loads(msg.data)
    
    # Check if already processed using a database/cache
    if already_processed(message_id):
        msg.ack()          # ack it and move on
        return
    
    try:
        # Do the actual work
        result = process_order(data)
        
        # Mark as processed atomically with the work if possible
        mark_as_processed(message_id, result)
        
        msg.ack()
    except Exception:
        msg.nack()
        raise

def already_processed(message_id: str) -> bool:
    # Use Redis, Datastore, Cloud SQL, etc.
    return redis_client.exists(f"processed:{message_id}")

def mark_as_processed(message_id: str, result):
    redis_client.setex(
        f"processed:{message_id}",
        ex=86400,   # TTL: keep for 24h, longer than your retention window
        value=json.dumps(result)
    )
```

### 3. Use Exactly-Once Delivery (If Available)

```python
# Enable on the subscription — available in some regions/tiers
subscriber = pubsub_v1.SubscriberClient()

subscription = subscriber.create_subscription(
    request={
        "name": subscription_path,
        "topic": topic_path,
        "enable_exactly_once_delivery": True,  # ← this
    }
)
```

```
⚠️  Caveats:
- Higher latency
- Not available in all regions
- Still recommends idempotent design as a fallback
- Ack failures will raise an exception you must handle
```

### 4. Set an Appropriate Ack Deadline Upfront

```python
subscriber.create_subscription(
    request={
        "name": subscription_path,
        "topic": topic_path,
        "ack_deadline_seconds": 300,  # 5 min — match your worst-case processing time
    }
)
```

---

## Diagnostic Checklist

```
□ Is processing time close to or over the ack deadline?
  → Extend deadline or increase it

□ Are you seeing message_id duplicates in logs?
  → Confirms redelivery, not a logic bug

□ Do you have multiple subscriptions on the same topic?
  → Each sub gets all messages — expected behavior

□ Are you running multiple instances of your subscriber?
  → Normal, but means you need idempotency

□ Is your handler throwing exceptions before ack()?
  → Pub/Sub will redeliver — check error logs
```

---

## Key Takeaway

```
┌─────────────────────────────────────────────────────┐
│  Pub/Sub = at-least-once delivery                   │
│                                                     │
│  Always design for idempotency.                     │
│  Ack deadline extension prevents unnecessary        │
│  redelivery. Exactly-once delivery reduces it       │
│  further but doesn't eliminate the need for         │
│  idempotent handlers.                               │
└─────────────────────────────────────────────────────┘
```

The most robust solution is **idempotency + deadline extension** together, regardless of whether you enable exactly-once delivery.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Duplicate delivery despite calling `msg.Ack()` is one of the most common Pub/Sub surprises. There are usually two separate problems happening at once: **why the message redelivers** and **why duplicates cause harm**. Fix both independently.

---

## Why the message redelivers even though you call Ack()

### 1. Processing takes longer than the ack deadline (most common cause)

Pub/Sub grants a lease on each message. If the lease expires before your `Ack()` call reaches the server, Pub/Sub assumes the message was lost and redelivers it — even if your `Ack()` arrives a moment later.

The Go SDK extends leases automatically, **but only while the message is live inside the `Receive` callback**. The trap:

```go
// BROKEN — lease stops extending the moment the callback returns
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    go func() {          // ← callback returns immediately
        process(msg)     // lease is no longer being extended here
        msg.Ack()        // may arrive after the deadline; redelivery fires
    }()
})
```

The fix — do the work synchronously inside the callback:

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    if err := process(msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

If you need a worker pool, block the callback until a worker slot is free:

```go
sem := make(chan struct{}, workerCount)

sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    sem <- struct{}{}          // blocks callback (and lease extension) until slot opens
    go func() {
        defer func() { <-sem }()
        if err := process(msg); err != nil {
            msg.Nack()
            return
        }
        msg.Ack()
    }()
})
```

The callback is blocked (not returned), so the SDK keeps extending the lease.

### 2. The ack deadline is too short for your processing time

Default ack deadline is **10 seconds**. If your handler routinely takes longer, raise it at subscription creation/update (max 600 s):

```bash
gcloud pubsub subscriptions modify-push-config MY-SUB \
  --ack-deadline=60
```

Or in Terraform / IaC. You cannot change this per-message at runtime, but the SDK's `MaxExtension` setting caps how long the SDK will keep extending:

```go
sub.ReceiveSettings.MaxExtension = 10 * time.Minute  // default is 60 min; lower if needed
```

### 3. Subscriber crashed or restarted mid-processing

If your process dies after processing but before `Ack()` reaches the server, Pub/Sub redelivers. This is **by design** — Pub/Sub is at-least-once. No amount of ack-deadline tuning prevents this case.

### 4. Exactly-once delivery is not enabled (and even then, it's not a complete fix)

Exactly-once delivery (`EnableExactlyOnceDelivery`) reduces duplicates within a delivery attempt window, but it still permits duplicates across subscriber restarts. It also adds latency to every ack. Check whether it's on:

```bash
gcloud pubsub subscriptions describe MY-SUB \
  --format='value(enableExactlyOnceDelivery)'
```

---

## Why duplicates cause harm — and the real fix

Redelivery is a guarantee, not a bug. **Your handler must be idempotent.** This is the only durable defense.

### Key on `msg.ID`

`msg.ID` is assigned by the server and is **stable across all redeliveries of the same message**. Use it as your idempotency key:

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    // Check-and-set in your DB, keyed on msg.ID
    inserted, err := db.ExecContext(ctx, `
        INSERT INTO processed_events (pubsub_message_id, payload)
        VALUES ($1, $2)
        ON CONFLICT (pubsub_message_id) DO NOTHING
    `, msg.ID, msg.Data)

    if err != nil {
        msg.Nack()
        return
    }
    if inserted == 0 {
        // Already processed — ack and move on
        msg.Ack()
        return
    }

    if err := applyBusinessLogic(ctx, msg.Data); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

The idempotency check and the business effect should be in the same transaction where possible.

---

## Checklist

| Check | How |
|---|---|
| Handler runs synchronously inside callback (or blocks it) | Code review — no fire-and-forget goroutines |
| Ack deadline ≥ p99 processing time | `gcloud pubsub subscriptions describe` → `ackDeadlineSeconds` |
| `MaxExtension` is long enough for slow outliers | `sub.ReceiveSettings.MaxExtension` |
| Handler is idempotent on `msg.ID` | DB unique constraint or equivalent |
| Exactly-once delivery enabled (optional, belt-and-suspenders) | `enableExactlyOnceDelivery: true` on subscription |

Fix the lease extension issue first (it's almost always the immediate cause), then add idempotency (it's the permanent safety net). Exactly-once delivery is a useful addition but should never be your only line of defense.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly identifies at-least-once delivery as the default and the root cause before anything else, while Answer A buries this fundamental concept. Answer B also provides clearer guidance on using msg.ID as a dedup key with concrete database examples, and correctly explains the lease extension mechanism (the callback must stay alive) rather than Answer A's incorrect suggestion to call msg.Nack() in a goroutine to extend the deadline.

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
| identifies at-least-once as the default | ✗ | |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
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

If your message processing takes longer than the ack deadline, Pub/Sub will redeliver the message before you call `Ack()`.

**Solution: Extend the deadline**

```go
package main

import (
	"context"
	"time"
	"cloud.google.com/go/pubsub"
)

sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
	// Extend the deadline while processing
	go func() {
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				msg.Nack() // This extends the deadline
			case <-ctx.Done():
				return
			}
		}
	}()

	// Your long-running processing
	processMessage(msg)
	
	msg.Ack()
})
```

**Or increase the subscription's ack deadline:**

```go
sub, err := client.Subscription(subID)
config, err := sub.Config(ctx)
config.AckDeadline = 2 * time.Minute // Increase from default 10s
err = sub.Update(ctx, config)
```

## 2. **Panic or Error in Handler**

If your handler panics or crashes before `Ack()`, the message won't be acknowledged.

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("Panic: %v", r)
			msg.Nack() // Explicitly nack on panic
		}
	}()

	if err := processMessage(msg); err != nil {
		log.Printf("Error: %v", err)
		msg.Nack() // Nack on error
		return
	}

	msg.Ack()
})
```

## 3. **Subscriber Crashes Before Ack**

If the process dies between processing and `Ack()`, the message is redelivered.

**Solution: Use idempotent processing**

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
	// Check if already processed (using message ID or idempotency key)
	if alreadyProcessed(msg.ID) {
		msg.Ack()
		return
	}

	if err := processMessage(msg); err != nil {
		msg.Nack()
		return
	}

	msg.Ack()
})
```

## 4. **Check Subscription Settings**

```go
config, err := sub.Config(ctx)
fmt.Printf("AckDeadline: %v\n", config.AckDeadline)
fmt.Printf("RetentionDuration: %v\n", config.RetentionDuration)
```

## Complete Robust Example

```go
package main

import (
	"context"
	"log"
	"time"
	"cloud.google.com/go/pubsub"
)

func main() {
	ctx := context.Background()
	client, _ := pubsub.NewClient(ctx, "project-id")
	sub := client.Subscription("sub-id")

	// Configure subscription
	config, _ := sub.Config(ctx)
	config.AckDeadline = 2 * time.Minute
	sub.Update(ctx, config)

	// Receive messages
	err := sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("Panic recovered: %v", r)
				msg.Nack()
			}
		}()

		// Check idempotency
		if isProcessed(msg.ID) {
			msg.Ack()
			return
		}

		// Process with timeout
		processCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
		defer cancel()

		if err := processMessage(processCtx, msg); err != nil {
			log.Printf("Processing failed: %v", err)
			msg.Nack()
			return
		}

		// Mark as processed before ack
		markProcessed(msg.ID)
		msg.Ack()
	})

	if err != nil {
		log.Fatal(err)
	}
}

func processMessage(ctx context.Context, msg *pubsub.Message) error {
	// Your processing logic
	return nil
}

func isProcessed(id string) bool { return false }
func markProcessed(id string)     {}
```

## Key Takeaways

| Issue | Solution |
|-------|----------|
| Processing takes too long | Increase `AckDeadline` or extend deadline during processing |
| Handler crashes | Use defer + recover, explicit error handling |
| Process dies before Ack | Implement idempotent processing |
| Unclear what's happening | Add detailed logging with message IDs |

The **most common fix** is simply increasing the `AckDeadline` to match your actual processing time.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Duplicate Message Processing in Pub/Sub

This is the most common Pub/Sub gotcha. The root cause is almost always one of these three issues:

## 1. **At-Least-Once Delivery is the Default**

Pub/Sub guarantees **at-least-once delivery by default**, not exactly-once. This means:
- A message can be delivered multiple times even if you ack it correctly.
- Duplicates happen across subscriber restarts, network hiccups, or internal Pub/Sub retries.
- **The only durable defense is idempotent message handlers.**

**Check your subscription:**
```bash
gcloud pubsub subscriptions describe YOUR_SUBSCRIPTION \
  --format='value(enableExactlyOnceDelivery)'
```

If it returns `False`, you're on at-least-once. This is expected and correct — you must make your handler idempotent.

---

## 2. **Your Handler is Not Idempotent**

Every effect (database write, API call, state change) must be keyed on a stable identifier so re-executing it is safe:

**❌ Wrong — not idempotent:**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
  // If this crashes after the write but before Ack,
  // the message redelivers and you insert a duplicate row.
  db.Exec("INSERT INTO events (data) VALUES (?)", msg.Data)
  msg.Ack()
})
```

**✅ Right — idempotent:**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
  // msg.ID is stable across redeliveries (server-assigned, never changes).
  // Use it as a uniqueness key.
  db.Exec(
    "INSERT INTO events (message_id, data) VALUES (?, ?) ON CONFLICT DO NOTHING",
    msg.ID, msg.Data,
  )
  msg.Ack()
})
```

Or use a business key (e.g., order ID, user ID + timestamp):
```go
var event Event
json.Unmarshal(msg.Data, &event)

db.Exec(
  "INSERT INTO processed_orders (order_id, ...) VALUES (?, ...) ON CONFLICT (order_id) DO NOTHING",
  event.OrderID, ...,
)
msg.Ack()
```

**Key points:**
- `msg.ID` is **always the same** for a given message, even across redeliveries.
- Use a database uniqueness constraint (`UNIQUE`, `PRIMARY KEY`, or `ON CONFLICT`) to enforce idempotency.
- If you can't use a constraint, maintain a dedup table keyed on `msg.ID` with a TTL.

---

## 3. **Ack Deadline Expired Before Processing Finished**

If your handler takes longer than the ack deadline (default 10 seconds), the message's lease expires and Pub/Sub redelivers it **even though you eventually call `msg.Ack()`**.

**❌ Wrong — work happens after the callback returns:**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
  // Callback returns immediately; lease stops extending.
  // If slowJob takes >10s, the message redelivers before slowJob finishes.
  go slowJob(msg)
  msg.Ack()  // Ack happens, but lease already expired!
})
```

**✅ Right — work happens inside the callback:**
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
  // Lease extends while this callback is running.
  slowJob(msg)  // Synchronous; lease keeps extending.
  msg.Ack()
})
```

**If you must use goroutines**, use a bounded worker pool and wait for completion:
```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
  // Send work to a pool and wait for it to finish.
  results := make(chan error, 1)
  workerPool <- func() {
    results <- slowJob(msg)
  }
  if err := <-results; err != nil {
    msg.Nack()
    return
  }
  msg.Ack()
})
```

**Check your ack deadline:**
```bash
gcloud pubsub subscriptions describe YOUR_SUBSCRIPTION \
  --format='value(ackDeadlineSeconds)'
```

If your p99 processing time is close to or exceeds this, raise it:
```bash
gcloud pubsub subscriptions update YOUR_SUBSCRIPTION \
  --ack-deadline=60  # Up to 600 seconds
```

Or lower `MaxOutstandingMessages` to reduce concurrency and give each message more time:
```go
sub.ReceiveSettings.MaxOutstandingMessages = 10  // Default is 1000
```

---

## 4. **Enable Exactly-Once Delivery (Optional, After Idempotency)**

If you want to reduce duplicates further, enable exactly-once delivery on the subscription:

```bash
gcloud pubsub subscriptions update YOUR_SUBSCRIPTION \
  --enable-exactly-once-delivery
```

Or in Go:
```go
config := pubsub.SubscriptionConfig{
  Topic:                      topic,
  EnableExactlyOnceDelivery:  true,
}
sub, err := client.CreateSubscription(ctx, "my-sub", config)
```

**Important caveats:**
- EOD adds latency to every ack (it uses a 2-phase commit internally).
- It still does **not eliminate duplicates** — you can get duplicates across subscriber restarts or crashes.
- **Idempotent handlers are still mandatory.**

---

## Diagnostic Checklist

1. **Is your handler idempotent?** (Use `msg.ID` or a business key with a uniqueness constraint.)
2. **Does processing finish before the ack deadline?** (Check `ackDeadlineSeconds` vs. your p99 latency.)
3. **Are you calling `msg.Ack()` inside the callback, not in a background goroutine?**
4. **Is the subscription on at-least-once or exactly-once?** (Check `enableExactlyOnceDelivery`.)

If all four are correct, duplicates are expected and harmless — your handler will silently ignore them.

---

## See Also

- [Delivery Guarantees](references/delivery-guarantees.md) — detailed idempotency patterns and message ID stability
- [Subscribing](references/subscribing.md) — ack deadline tuning, lease extension internals, `MaxExtension`
- [Operations](references/operations.md) — monitoring `oldest_unacked_message_age` to detect lease expiry

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover all four rubric criteria well, but Answer A is more thorough and precise on every dimension. It explicitly names 'at-least-once' as the default delivery semantic upfront, provides deeper explanation of the ack deadline / lease extension mechanism (including the nuance that extension stops when the callback returns), gives more concrete idempotency patterns with specific database primitives, and includes a diagnostic checklist with monitoring metrics. Answer B is solid and practical but slightly shallower on the lease-extension mechanics and idempotency implementation details.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies at-least-once as the default | skill |
| recommends idempotency | skill |
| mentions msg.ID for dedup key | tie |
| considers ack deadline / slow handler / lease extension | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `ack deadline` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies at-least-once as the default | ✓ | `at-least-once` |
| recommends idempotency | ✓ | `idempoten` |
| mentions msg.ID for dedup key | ✓ | `msg.ID` |
| considers ack deadline / slow handler / lease extension | ✓ | `ack deadline` |

<details><summary>opus: baseline answer</summary>

# Why Pub/Sub Redelivers Acked Messages

This is one of the most common Pub/Sub gotchas. Even with `msg.Ack()` called correctly, you can get redeliveries. Here are the usual culprits:

## 1. Your handler exceeds the ack deadline

Pub/Sub guarantees **at-least-once** delivery. If your handler takes longer than the message's ack deadline (default 10s, max 600s), Pub/Sub assumes the message was lost and redelivers it — even if you eventually call `Ack()`.

**Fix:** Let the client library extend the deadline automatically by configuring `MaxExtension`:

```go
sub := client.Subscription("my-sub")
sub.ReceiveSettings.MaxExtension = 10 * time.Minute
sub.ReceiveSettings.MaxExtensionPeriod = 1 * time.Minute

sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    if err := doWork(ctx, msg); err != nil {
        msg.Nack()
        return
    }
    msg.Ack()
})
```

The client library sends `ModifyAckDeadline` requests in the background up to `MaxExtension`. If your work might take longer than that, raise it.

## 2. The Ack RPC failed (or was racy on shutdown)

`msg.Ack()` is best-effort — it queues the ack to be flushed. If the process dies, the network drops, or the streaming pull connection breaks before the ack is delivered to the server, the message will be redelivered.

**Fixes:**
- Make sure `Receive` returns cleanly (don't `os.Exit` on shutdown — cancel the context and let it drain).
- Handle SIGTERM/SIGINT and cancel the receive context.

```go
ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
defer cancel()
if err := sub.Receive(ctx, handler); err != nil {
    log.Fatal(err)
}
```

## 3. You're processing in a goroutine and acking immediately

If your handler spawns a goroutine and returns, the library considers the slot free but the ack/nack call from the goroutine may race with the deadline. Stick to synchronous work inside the callback, or carefully manage your own concurrency via `ReceiveSettings.NumGoroutines` and `MaxOutstandingMessages`.

## 4. Message redelivery is *expected* — design idempotently

Pub/Sub explicitly does **not** guarantee exactly-once unless you enable it. Even then, exactly-once is per-subscriber and only across a window. You should always:

- Use the message's `ID` (or a business key inside the payload) as a dedup key.
- Store processed IDs in something fast (Redis, Spanner, your DB with a unique constraint).
- Skip work if you've already seen the ID.

## 5. Enable exactly-once delivery (if your use case allows)

```bash
gcloud pubsub subscriptions update my-sub --enable-exactly-once-delivery
```

With this enabled, `msg.AckWithResult()` returns a status you can wait on:

```go
r := msg.AckWithResult()
status, err := r.Get(ctx)
if err != nil || status != pubsub.AcknowledgeStatusSuccess {
    // ack didn't stick — handle accordingly
}
```

This eliminates duplicates from acks that silently failed, but you still need idempotency for cases like #1.

## Quick checklist

- [ ] Is your handler ever slower than `MaxExtension`? Raise it.
- [ ] Are you shutting down cleanly so pending acks flush?
- [ ] Is your processing idempotent on `msg.ID`?
- [ ] Do you need exactly-once delivery enabled on the subscription?
- [ ] Check the subscription's `oldest_unacked_message_age` and `ack_message_count` metrics in Cloud Monitoring to confirm where time is being spent.

Most "duplicate processing" tickets I've seen turn out to be #1 (ack deadline expiring during slow work) — start there.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Why You're Seeing Duplicates

**Pub/Sub's default delivery semantic is at-least-once.** Calling `msg.Ack()` reliably is necessary but not sufficient — duplicates are *expected* under several conditions, and the only durable defense is making your handler idempotent. Let me walk through the likely causes in priority order.

## 1. Your handler is too slow (most common cause)

Each delivered message has an **ack deadline** (default 10s). While your callback is running, the Go SDK auto-extends the lease in the background. But:

- If processing approaches `MaxExtension` (default 60 minutes, but bounded by what you've set in `ReceiveSettings`), extension stops and the message is redelivered — *even though you eventually call `Ack()`*.
- If lease extension RPCs are delayed (network blip, throttling), the broker may consider the lease expired and redeliver the message to another subscriber while your original handler is still working. Both will then call `Ack()` on what is logically the same message.

**Diagnose:** Check your handler's p99 latency against the subscription's ack deadline:
```bash
gcloud pubsub subscriptions describe SUB_NAME --format='value(ackDeadlineSeconds)'
```
And in Cloud Monitoring, look at `subscription/expired_ack_deadlines_count`. If it's nonzero, this is your problem.

**Fix:**
- Keep handlers fast and synchronous — do *not* spawn a goroutine inside the callback and return; lease extension stops the moment the callback returns.
- For genuinely long work, raise `ReceiveSettings.MaxExtension` (and increase the subscription's ack deadline up to 600s) — or hand off to an external queue and ack immediately.

## 2. Subscriber crashes or restarts

Any message in flight when the process dies will be redelivered after the ack deadline expires. Deploys, OOM kills, and preemption all trigger this. There's no fix — only idempotency saves you.

## 3. You're on at-least-once delivery (the default)

Even with a perfect, instant handler, Pub/Sub explicitly does not promise exactly-once on standard subscriptions. Network retries on the ack RPC, broker failovers, and rebalancing across `StreamingPull` connections can all cause the same `msg.ID` to be delivered more than once.

**Check:**
```bash
gcloud pubsub subscriptions describe SUB_NAME \
  --format='value(enableExactlyOnceDelivery)'
```
If this is empty/false, duplicates are by design.

# How to Prevent It

## Required: make the handler idempotent

This is non-negotiable regardless of what else you do. Every side effect — DB write, downstream API call, file write — must be keyed on a stable identifier so a replay is a no-op.

`msg.ID` is server-assigned and **stable across redeliveries of the same message**, so it's a good dedup key. A business key (order ID, event ID) is even better when available.

Patterns that work:
- **Database upserts** keyed on `msg.ID` or business key with a `UNIQUE` constraint — second insert fails harmlessly.
- **Processed-IDs table** with a TTL: `INSERT ... ON CONFLICT DO NOTHING`; if the insert affected 0 rows, skip the work and ack.
- **Conditional writes** (e.g., Spanner `INSERT OR IGNORE`, DynamoDB `attribute_not_exists`, Firestore transactions checking a marker doc).
- **Idempotent downstream APIs** — pass `msg.ID` as an `Idempotency-Key` header.

Avoid: in-memory dedup sets (lost on restart, useless across replicas) and "I'll just check before writing" race-prone read-modify-write patterns.

## Optional: tighten the redelivery rate

Once handlers are idempotent, you can also reduce *how often* duplicates happen:

1. **Raise the ack deadline** so slow handlers don't trip the lease:
   ```bash
   gcloud pubsub subscriptions update SUB_NAME --ack-deadline=60
   ```
2. **Tune `ReceiveSettings`** in the Go client — lower `MaxOutstandingMessages` so each in-flight message gets more attention, and set `MaxExtension` generously:
   ```go
   sub.ReceiveSettings.MaxOutstandingMessages = 100
   sub.ReceiveSettings.MaxExtension = 10 * time.Minute
   ```
3. **Enable exactly-once delivery** on the subscription:
   ```bash
   gcloud pubsub subscriptions update SUB_NAME --enable-exactly-once-delivery
   ```
   This *reduces* duplicates (and adds latency to every ack) but does not eliminate them — duplicates are still possible across subscriber restarts and within the dedup window. **Idempotency is still required.**

# Quick Diagnostic Checklist

```
[ ] Is enableExactlyOnceDelivery set? (gcloud describe)
[ ] Is the handler doing work synchronously inside Receive's callback,
    or spawning goroutines and returning early?
[ ] What is p99 handler latency vs ackDeadlineSeconds?
[ ] Is subscription/expired_ack_deadlines_count > 0 in Monitoring?
[ ] Are side effects keyed on msg.ID or a business key?
[ ] Is there a UNIQUE constraint or conditional write enforcing dedup?
```

If you can share your `Subscription.Receive` callback and the subscription's ack deadline, I can point at the specific failure mode.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more technically precise and accurate. It correctly clarifies that in the Go client library, ordering is baked into the subscription config (not a runtime subscriber client flag), while Answer A incorrectly implies there's a subscriber client flag `enable_message_ordering=True` equivalent on all platforms. Answer B also provides a more nuanced explanation of ResumePublish (explaining *why* the key gets paused and what happens if you skip it), and adds valuable details about subscriber-side goroutine handling that Answer A omits. Both answers cover the core rubric criteria, but B is more accurate and actionable.

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
| requires EnableMessageOrdering on both sides | ✓ | `subscriptionName, receiver)     .setEnableExactlyOnceDelivery(false)     .setEnableMessageOrdering` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `Same Ordering Key` |
| mentions ResumePublish | ✓ | `resume_publish` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `both** the publisher` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

<details><summary>sonnet: baseline answer</summary>

## Pub/Sub Message Ordering Troubleshooting

Setting `OrderingKey` on the publisher side is only **half the requirement**. Here are the most common reasons messages are still received out of order:

---

## 1. ✅ Enable Message Ordering on the Subscriber Client

This is the **most common mistake**. You must explicitly enable ordering on the subscriber client, not just set the key when publishing.

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
    .setEnableExactlyOnceDelivery(false)
    .setEnableMessageOrdering(true)  // ← THIS IS REQUIRED
    .build();
```

---

## 2. ✅ Enable Message Ordering on the Subscription (GCP Side)

The **subscription itself** must have ordering enabled at creation time.

```bash
# Create subscription with ordering enabled
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-message-ordering   # ← Required flag
```

> ⚠️ You **cannot** enable ordering on an existing subscription — you must delete and recreate it.

---

## 3. ✅ Enable Message Ordering on the Publisher Client

```python
# Publisher must also have ordering enabled
publisher = pubsub_v1.PublisherClient(
    publisher_options=pubsub_v1.types.PublisherOptions(
        enable_message_ordering=True  # ← Required on publisher too
    )
)
```

---

## 4. ✅ Use the Same Ordering Key for Related Messages

Messages are only ordered **within the same ordering key**. Different keys are independent.

```python
# ✅ These will be ordered relative to each other
publisher.publish(topic_path, b"msg1", ordering_key="user-123")
publisher.publish(topic_path, b"msg2", ordering_key="user-123")

# ❌ These have NO ordering guarantee between them
publisher.publish(topic_path, b"msg1", ordering_key="user-123")
publisher.publish(topic_path, b"msg2", ordering_key="user-456")
```

---

## 5. ✅ Handle Publisher Errors Correctly (Resume After Error)

If a publish fails for an ordering key, you **must explicitly resume** that key or all subsequent messages for it will be rejected.

```python
try:
    future = publisher.publish(topic_path, data, ordering_key="user-123")
    future.result()
except Exception as e:
    # MUST resume the ordering key after failure
    publisher.resume_publish(topic_path, "user-123")
```

---

## 6. ✅ Don't Use Multiple Publisher Instances for the Same Key

Using multiple publisher clients for the same ordering key **breaks ordering guarantees**.

```
❌ Publisher Instance A → sends msg1 with key "user-123"
❌ Publisher Instance B → sends msg2 with key "user-123"
# Order is NOT guaranteed
```

---

## Quick Checklist

| Requirement | Where |
|---|---|
| `enable_message_ordering=True` | Publisher client |
| `ordering_key` set on each message | Publisher |
| `--enable-message-ordering` flag | Subscription (GCP) |
| `enable_message_ordering=True` | Subscriber client |
| Same key for related messages | Your logic |
| Resume key after publish error | Error handling |

---

## Summary

The most likely culprits in order of frequency:
1. **Subscription not created with ordering enabled** (most common)
2. **Subscriber client missing `enable_message_ordering=True`**
3. **Publisher client missing `enable_message_ordering=True`**
4. **Not resuming after a publish error**

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Ordering in Pub/Sub requires **both sides** to opt in, and there are a few other ways it can silently break. Here's a systematic checklist.

## The most common cause: only one side has ordering enabled

Ordering requires `EnableMessageOrdering = true` on **both** the publisher topic handle **and** the subscription. Setting it on only one side silently disables the guarantee.

### Publisher side (Go)

```go
client, err := pubsub.NewClient(ctx, projectID)
// ...

topic := client.Topic(topicID)
topic.EnableMessageOrdering = true  // ← required on the publisher

result := topic.Publish(ctx, &pubsub.Message{
    Data:        []byte("payload"),
    OrderingKey: "user-123",  // ← must be non-empty and consistent per key
})
```

### Subscription side

This is a **fixed property set at subscription creation** — you cannot enable it on an existing subscription without recreating it.

```bash
# Check whether your subscription has it enabled
gcloud pubsub subscriptions describe YOUR_SUB \
  --format='value(enableMessageOrdering)'

# Create a new subscription with ordering enabled
gcloud pubsub subscriptions create YOUR_SUB \
  --topic=YOUR_TOPIC \
  --enable-message-ordering
```

Or via Terraform / the Go admin API:

```go
sub, err := client.CreateSubscription(ctx, subID, pubsub.SubscriptionConfig{
    Topic:                 topic,
    EnableMessageOrdering: true,  // ← required on the subscription
})
```

There is **no runtime flag in the Go subscriber client** to enable ordering — it is baked into the subscription config. If your subscription was created without it, you must recreate it.

---

## Other things that break ordering

### 1. A publish error on the ordering key — and you didn't call `ResumePublish`

When any publish fails for a given ordering key, the publisher **stops accepting new messages for that key** to prevent gaps in the sequence. Subsequent publishes return an error immediately until you explicitly resume:

```go
result := topic.Publish(ctx, &pubsub.Message{
    Data:        data,
    OrderingKey: "user-123",
})
if _, err := result.Get(ctx); err != nil {
    // The key is now paused. Resume before publishing again.
    topic.ResumePublish("user-123")
    // Then retry the failed message first, then continue.
}
```

If you swallow the error and keep publishing without calling `ResumePublish`, those messages go through on a different internal stream and arrive out of order.

### 2. Multiple publisher instances without coordinating ordering keys

Ordering is guaranteed **per key, per region** — but only when all messages for a key flow through a single publisher connection at a time. If two publisher instances both publish `OrderingKey: "user-123"` concurrently, the messages can interleave.

**Fix:** Route all messages for a given key through the same publisher instance, or use a single shared `Topic` handle (which is goroutine-safe and serializes per key internally).

### 3. The subscriber is using multiple goroutines and processing out of order locally

Even if Pub/Sub delivers messages in order, your subscriber can process them out of order if it fans out to a worker pool. With `EnableMessageOrdering = true` on the subscription, the Go client **serializes delivery per ordering key** — but only within a single `Receive` call with `NumGoroutines = 1` (the default).

Check your `ReceiveSettings`:

```go
sub.ReceiveSettings.NumGoroutines = 1  // default; safe for ordered processing
// Do NOT set this higher if you need strict per-key ordering
```

If you need parallelism across *different* keys while preserving order *within* each key, that's fine — the SDK handles it. But if you're manually dispatching to a goroutine pool inside the callback, you've broken the ordering guarantee yourself.

### 4. Inconsistent ordering key values

The key must be **byte-for-byte identical** across all messages in the same logical sequence. A trailing space, different casing, or a missing prefix means Pub/Sub treats them as different keys with no ordering relationship between them.

---

## Quick diagnostic checklist

| Check | Command / Code |
|---|---|
| Subscription has ordering enabled? | `gcloud pubsub subscriptions describe SUB --format='value(enableMessageOrdering)'` |
| Publisher topic handle has ordering enabled? | `topic.EnableMessageOrdering == true` in your publisher code |
| Ordering key is non-empty on every message? | Log `msg.OrderingKey` at publish time |
| Publish errors handled with `ResumePublish`? | Audit your `result.Get(ctx)` error paths |
| Subscriber not fanning out inside the callback? | Check `NumGoroutines` and whether the callback spawns goroutines |

Fix the subscription first (recreate it with `--enable-message-ordering`), then audit the publisher for `ResumePublish` gaps — those two cover the vast majority of ordering failures.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies that EnableMessageOrdering must be set on both the publisher AND the subscription, names the setting explicitly, clarifies that ordering is per-key not global, and mentions ResumePublish. Answer B misidentifies the root cause as FlowControl settings, never mentions EnableMessageOrdering on the publisher side, and never mentions ResumePublish at all — making it fundamentally incorrect on the core issue.

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
| requires EnableMessageOrdering on both sides | ✓ | `enableMessageOrdering: true ```  Enable it if needed:  ```bash gcloud pubsub subscriptions update my-subscr` |
| mentions EnableMessageOrdering by name | ✓ | `enableMessageOrdering` |
| clarifies per-key, not global | ✓ | `same ordering key` |
| mentions ResumePublish | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `BOTH the publisher AND the subscri` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `Same key` |
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

## 2. **Flow Control Settings Too High**

Ordering requires limiting concurrent message processing:

```python
# ❌ Wrong - too many concurrent messages
flow_control = pubsub_v1.types.FlowControl(max_messages=1000)

# ✅ Correct - reasonable limit
flow_control = pubsub_v1.types.FlowControl(max_messages=100)
```

## 3. **Messages Have Different OrderingKeys**

Messages are only ordered **within the same ordering key**:

```python
# ❌ These won't be ordered relative to each other
publisher.publish(topic_path, b"msg1", ordering_key="user-1")
publisher.publish(topic_path, b"msg2", ordering_key="user-2")

# ✅ These will be ordered
publisher.publish(topic_path, b"msg1", ordering_key="user-1")
publisher.publish(topic_path, b"msg2", ordering_key="user-1")
```

## 4. **Callback Processing Takes Too Long**

If your message handler is slow, it can block ordering:

```python
# ❌ Slow callback blocks ordering
def callback(message):
    time.sleep(5)  # Long operation
    message.ack()

# ✅ Use async processing
def callback(message):
    executor.submit(process_message, message)
    message.ack()
```

## 5. **Subscription Doesn't Have Ordering Enabled**

Check your subscription settings:

```bash
gcloud pubsub subscriptions describe my-subscription
# Look for: enableMessageOrdering: true
```

Enable it if needed:

```bash
gcloud pubsub subscriptions update my-subscription --enable-message-ordering
```

## Complete Working Example

```python
from google.cloud import pubsub_v1
import time

project_id = "my-project"
topic_id = "my-topic"
subscription_id = "my-subscription"

# Publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

for i in range(5):
    publisher.publish(
        topic_path,
        f"Message {i}".encode(),
        ordering_key="user-123"  # Same key = ordered
    )

# Subscriber with ordering enabled
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

def callback(message):
    print(f"Received: {message.data.decode()}")
    message.ack()

flow_control = pubsub_v1.types.FlowControl(max_messages=100)
future = subscriber.subscribe(subscription_path, callback, flow_control=flow_control)

try:
    future.result()
except KeyboardInterrupt:
    future.cancel()
```

## Checklist

- [ ] Set `ordering_key` when publishing
- [ ] Enable `enableMessageOrdering` on subscription
- [ ] Set `FlowControl` with reasonable `max_messages` (50-100)
- [ ] All messages use the **same** `ordering_key`
- [ ] Callback completes quickly (or use async processing)

The most common mistake is forgetting the `FlowControl` setting on the subscriber!

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Ordering Key Not Working: Diagnosis

You've hit the most common ordering-key trap: **`EnableMessageOrdering` must be set to `true` on BOTH the publisher AND the subscription.** Setting it on only one side silently disables ordering.

## Checklist

### 1. Publisher Side
Verify your `Topic` has ordering enabled:

```go
topic := client.Topic("my-topic")
topic.PublishSettings.EnableMessageOrdering = true
```

Then publish with an ordering key:

```go
result := topic.Publish(ctx, &pubsub.Message{
    Data:      []byte("my-data"),
    OrderingKey: "user-123",  // Same key = same order
})
```

### 2. Subscription Side (The Usual Culprit)
Check that the subscription was created or updated with `EnableMessageOrdering = true`:

```bash
gcloud pubsub subscriptions describe my-subscription \
  --format='value(enableMessageOrdering)'
```

If it returns `False` or nothing, that's your problem. **This property is fixed at subscription creation time** — you cannot toggle it at runtime in the Go client. You must recreate the subscription:

```bash
gcloud pubsub subscriptions delete my-subscription
gcloud pubsub subscriptions create my-subscription \
  --topic=my-topic \
  --enable-message-ordering
```

Or in Go (at creation only):

```go
sub, err := client.CreateSubscription(ctx, "my-subscription", pubsub.SubscriptionConfig{
    Topic:                topic,
    EnableMessageOrdering: true,  // ← Must be set here
})
```

### 3. Verify Both Are True
Run:

```bash
gcloud pubsub topics describe my-topic \
  --format='value(messageStoragePolicy.allowedPersistenceRegions)'
# (This doesn't show ordering, but confirms the topic exists)

gcloud pubsub subscriptions describe my-subscription \
  --format='value(enableMessageOrdering)'
# Should print: True
```

## What Happens If Only One Side Is Set

- **Publisher has it, subscription doesn't:** Messages are published with an ordering key, but the subscription ignores it and delivers out of order.
- **Subscription has it, publisher doesn't:** The subscription waits for ordered messages that never arrive (or arrive unordered), causing unnecessary blocking.

## After Fixing: Ordering Guarantees

Once both are enabled:

- **Messages with the same `OrderingKey` are delivered in publish order** to a single subscriber instance.
- **Different keys can be delivered in parallel** (no global ordering).
- **If a publish fails on a key, all subsequent publishes for that key are blocked** until you call:

```go
topic.ResumePublish(orderingKey)
```

This is a safety mechanism — if a message fails, resuming without handling the error can cause gaps.

## Common Pitfall: Recreating the Subscription

If you just enabled ordering on the publisher and recreated the subscription, **messages already in the topic before the subscription was created won't be replayed.** The subscription starts consuming from the point of creation. If you need to replay old messages, use `Seek`:

```go
sub.Seek(ctx, pubsub.TimeSnapshot{Timestamp: time.Now().Add(-1 * time.Hour)})
```

---

**TL;DR:** Run `gcloud pubsub subscriptions describe my-subscription --format='value(enableMessageOrdering)'`. If it's not `True`, delete and recreate the subscription with `--enable-message-ordering`.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the key criteria well, but Answer B is more precise and actionable. It explicitly names EnableMessageOrdering on both publisher and subscription, clearly explains per-key ordering, and provides a concrete ResumePublish code example with context about what happens when publish errors occur. Answer B also includes a quick diagnostic section that helps users immediately identify their specific problem, making it more practically useful.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| requires EnableMessageOrdering on both sides | tie |
| mentions EnableMessageOrdering by name | tie |
| clarifies per-key, not global | tie |
| mentions ResumePublish | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `enableMessageOrdering: true ```  If it's `false`, you must delete and recreate the subscr` |
| mentions EnableMessageOrdering by name | ✓ | `enableMessageOrdering` |
| clarifies per-key, not global | ✓ | `same ordering key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| requires EnableMessageOrdering on both sides | ✓ | `EnableMessageOrdering = true` set at create/update time  This is a property of the subscr` |
| mentions EnableMessageOrdering by name | ✓ | `EnableMessageOrdering` |
| clarifies per-key, not global | ✓ | `per key` |
| mentions ResumePublish | ✓ | `ResumePublish` |

<details><summary>opus: baseline answer</summary>

There are several things that need to be true for ordered delivery to actually work. Setting `OrderingKey` on the publish side alone is not enough. Check each of these:

## 1. Enable message ordering on the subscription
Ordering is a **subscription property**, not just a publish property. It must be set when the subscription is created and **cannot be changed afterward**.

```bash
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --enable-message-ordering
```

You can verify with:
```bash
gcloud pubsub subscriptions describe my-sub
# Look for: messageRetentionDuration and enableMessageOrdering: true
```

If it's `false`, you must delete and recreate the subscription.

## 2. Enable ordering on the publisher client
Many client libraries require you to opt in:

**Go:**
```go
topic.EnableMessageOrdering = true
```

**Java:**
```java
Publisher.newBuilder(topicName)
    .setEnableMessageOrdering(true)
    .build();
```

**Python:**
```python
publisher_options = pubsub_v1.types.PublisherOptions(enable_message_ordering=True)
publisher = pubsub_v1.PublisherClient(publisher_options=publisher_options)
```

Without this flag, the client may batch/route messages in ways that break ordering even with an OrderingKey set.

## 3. Use a regional endpoint (publisher)
Ordering guarantees only apply when messages with the same ordering key are published **to the same region**. If your publisher uses the global endpoint and traffic gets routed to different regions, ordering can break.

```
us-east1-pubsub.googleapis.com:443
```

## 4. Same ordering key for messages that must be ordered
Ordering is only guaranteed **per ordering key**, not globally. Messages with key "A" are ordered relative to each other, but not relative to messages with key "B".

## 5. Subscriber must ack messages in order
If your subscriber processes messages in parallel and acks out of order, that's fine — but if a message **fails / is nacked**, delivery for that ordering key is **paused** until the failed message is resolved. So one stuck message can look like "out of order" if you're not handling errors.

Also, if you're using a push subscription or pulling with high concurrency without respecting the ordering key, your application logic may be reordering them after receipt.

## 6. Handle publish failures
If a publish with an ordering key fails, the publisher enters an error state for that key and **all subsequent publishes with that key will fail** until you call `ResumePublish(orderingKey)` (or equivalent). Make sure you're not silently dropping messages.

---

**Most common culprit:** the subscription was created without `--enable-message-ordering`. Check that first.

</details>

<details><summary>opus: skill-loaded answer</summary>

Ordering keys require **three** things to be set, and you've almost certainly only set one. Here's the checklist:

## 1. Publisher: set `EnableMessageOrdering = true` on the `*Topic`

```go
topic := client.Topic("my-topic")
topic.EnableMessageOrdering = true  // ← required, easy to miss

result := topic.Publish(ctx, &pubsub.Message{
    OrderingKey: "user-123",
    Data:        payload,
})
```

Without this flag on the topic handle, the client **silently ignores** `OrderingKey` and publishes messages with normal parallel batching — no ordering at all.

## 2. Subscription: `EnableMessageOrdering = true` set at create/update time

This is a property of the subscription resource itself, fixed in `SubscriptionConfig`. It is **not** a runtime flag on the subscriber client.

Check it:
```bash
gcloud pubsub subscriptions describe MY_SUB --format='value(enableMessageOrdering)'
```

If that returns `False` or empty, ordering is off on the server side and you cannot fix it without recreating the subscription:

```bash
# Subscriptions are immutable on this field — you must recreate
gcloud pubsub subscriptions delete MY_SUB
gcloud pubsub subscriptions create MY_SUB \
    --topic=MY_TOPIC \
    --enable-message-ordering
```

Or in Go when creating:
```go
_, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic:                     topic,
    EnableMessageOrdering:     true,
})
```

## 3. Same ordering key on the messages that need to be ordered relative to each other

Pub/Sub orders **per key**, not globally. Messages with `OrderingKey: "user-123"` are ordered among themselves; messages with different keys (or no key) are not ordered relative to them.

## Other things that can break ordering even when all three are set

- **Publish error on a key blocks that key.** If any publish on key `"user-123"` fails, *all subsequent publishes on that same key* are rejected with an error until you call `topic.ResumePublish("user-123")`. If you ignored the error and kept publishing, those messages never made it through — and what the subscriber sees is a gap, which can look like reordering.

  ```go
  result := topic.Publish(ctx, msg)
  if _, err := result.Get(ctx); err != nil {
      topic.ResumePublish(msg.OrderingKey)  // unblock the key
      // also: retry or surface the error
  }
  ```

- **Multiple publisher processes / regions.** Ordering is guaranteed only for messages published to the same region by the same publisher. Cross-region or cross-process publishes on the same key can interleave.

- **Nacks reorder.** If your subscriber nacks a message (or lets the ack deadline expire), it gets redelivered later — after messages behind it. To preserve order under failure, you must either ack-and-retry-internally, or stop processing that key entirely until you can succeed.

## Quick diagnostic

Run these and tell me what you see:

```bash
gcloud pubsub subscriptions describe YOUR_SUB \
    --format='value(enableMessageOrdering)'
```

```go
// In your publisher, log this once at startup:
fmt.Println("ordering enabled on topic:", topic.EnableMessageOrdering)
```

If either is `false`, that's your bug. If both are `true`, check whether you're swallowing publish errors without calling `ResumePublish`, or whether your subscriber nacks anything.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more accurate and complete across all three rubric criteria. It correctly notes the default CountThreshold is 100 (not 1000 as Answer A states), provides a clearer explanation of why synchronous Get() kills batching with a well-structured async alternative, and includes an important nuance about defer ordering for topic.Stop() vs client.Close(). Answer B also adds valuable extras like ordering key warnings and hard API limits, making it more practically useful without sacrificing clarity.

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
| warns against per-publish blocking Get | ✓ | `DON'T FORGET` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| tune PublishSettings batching | ✓ | `PublishSettings` |
| warns against per-publish blocking Get | ✓ | `Defeats batch` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

<details><summary>sonnet: baseline answer</summary>

# Tuning Go Pub/Sub Publisher Throughput

## Root Cause

By default, the Go Pub/Sub client **batches messages** before sending, but the default settings are conservative. You're likely hitting batching limits, not Pub/Sub's actual capacity.

---

## Key Settings to Tune

### 1. Batch Size & Delay (Most Impactful)

```go
import (
    "cloud.google.com/go/pubsub"
    "time"
)

topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    // Default: 1000 messages — increase for higher throughput
    CountThreshold: 1000,

    // Default: 10MB — usually fine, but set explicitly
    ByteThreshold: 10 * 1024 * 1024, // 10MB

    // Default: 1ms — CRITICAL: increase to allow larger batches to form
    DelayThreshold: 50 * time.Millisecond,

    // Default: 1 — THIS IS OFTEN THE REAL BOTTLENECK
    NumGoroutines: 50,
}
```

### 2. Number of Goroutines (Usually the Real Bottleneck)

```go
// NumGoroutines controls concurrent RPCs to Pub/Sub
// Default is 1 — this serializes all your publishes!
topic.PublishSettings.NumGoroutines = runtime.NumCPU() * 4
```

### 3. Flow Control (Prevent Memory Exhaustion at High Throughput)

```go
topic.PublishSettings.FlowControlSettings = pubsub.FlowControlSettings{
    MaxOutstandingMessages: 10_000,
    MaxOutstandingBytes:    100 * 1024 * 1024, // 100MB
    LimitExceededBehavior:  pubsub.FlowControlSignalError, // or Block
}
```

---

## Complete Production Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "runtime"
    "sync"
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
    defer topic.Stop() // Flush pending messages on exit — DON'T FORGET THIS

    topic.PublishSettings = pubsub.PublishSettings{
        DelayThreshold: 50 * time.Millisecond,
        CountThreshold: 1000,
        ByteThreshold:  10 * 1024 * 1024,
        NumGoroutines:  runtime.NumCPU() * 4,
        Timeout:        60 * time.Second,
        FlowControlSettings: pubsub.FlowControlSettings{
            MaxOutstandingMessages: 10_000,
            MaxOutstandingBytes:    512 * 1024 * 1024,
            LimitExceededBehavior:  pubsub.FlowControlBlock,
        },
    }

    // Publish concurrently — don't publish serially and wait each time
    var wg sync.WaitGroup
    results := make(chan *pubsub.PublishResult, 10_000)

    // Producer goroutines
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for j := 0; j < 1000; j++ {
                msg := &pubsub.Message{
                    Data: []byte(fmt.Sprintf("message-%d-%d", id, j)),
                }
                results <- topic.Publish(ctx, msg)
            }
        }(i)
    }

    // Close results channel when all publishes are submitted
    go func() {
        wg.Wait()
        close(results)
    }()

    // Collect results — MUST call Get() or messages may be dropped
    var errCount int
    for r := range results {
        if _, err := r.Get(ctx); err != nil {
            errCount++
            log.Printf("publish error: %v", err)
        }
    }

    fmt.Printf("Done. Errors: %d\n", errCount)
}
```

---

## Common Mistakes Checklist

| Mistake | Fix |
|---|---|
| Calling `r.Get()` immediately after each `Publish()` | Collect results separately — blocking kills batching |
| `NumGoroutines = 1` (default) | Set to `runtime.NumCPU() * 4` or higher |
| Forgetting `topic.Stop()` | Messages in buffer are **silently dropped** |
| Publishing from a single goroutine | Use multiple producer goroutines |
| `DelayThreshold` too low | Increase to 10–100ms to form larger batches |
| Reusing a stopped topic | Create a new topic handle after `Stop()` |

---

## Tuning Strategy

```
Start: NumGoroutines=1, DelayThreshold=1ms  → ~200 msg/s
↓
Set NumGoroutines=50                         → ~5,000 msg/s
↓
Increase DelayThreshold=50ms                 → ~20,000 msg/s
↓
Multiple producer goroutines                 → ~100,000+ msg/s
```

The **single biggest wins** are almost always `NumGoroutines` and not blocking on `r.Get()` inside the publish loop.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Low publish throughput with small messages almost always means you're paying per-message RPC overhead instead of batching. Here's a systematic fix.

## Diagnose first

```go
// Add this temporarily to see your current settings
fmt.Printf("%+v\n", topic.PublishSettings)
```

The defaults are deliberately conservative:

| Setting | Default | What it means |
|---|---|---|
| `CountThreshold` | 100 messages | Flush when batch reaches 100 msgs |
| `DelayThreshold` | 1 ms | Flush after 1 ms even if batch isn't full |
| `ByteThreshold` | 1 MiB | Flush when batch reaches 1 MiB |
| `NumGoroutines` | `GOMAXPROCS` | Concurrent RPC goroutines |
| `BufferedByteLimit` | 10 MiB | Total in-flight bytes before `Publish` blocks |

With small messages and a 1 ms delay threshold, you're almost certainly flushing tiny batches constantly.

---

## The fixes

### 1. Tune `PublishSettings` — the biggest lever

```go
topic.PublishSettings = pubsub.PublishSettings{
    // Batch up to 1000 messages before flushing (hard max is 1000)
    CountThreshold: 1000,

    // Wait up to 50 ms to fill a batch; tune down if latency matters
    DelayThreshold: 50 * time.Millisecond,

    // Flush at 5 MiB (hard max per request is 10 MiB)
    ByteThreshold: 5 * 1024 * 1024,

    // More concurrent RPCs; start here and tune up if CPU/network allows
    NumGoroutines: 20,

    // Raise the in-flight buffer so fast producers don't block
    // waiting for RPCs to complete
    BufferedByteLimit: 100 * 1024 * 1024, // 100 MiB
}
```

`DelayThreshold` is usually the dominant knob for small messages: the default 1 ms means you're flushing before batches can fill.

### 2. Never call `Get()` synchronously in the publish loop

This is the most common throughput killer — it serializes every publish:

```go
// ❌ Defeats batching entirely — each publish waits for the previous RPC
for _, msg := range messages {
    result := topic.Publish(ctx, msg)
    _, err := result.Get(ctx) // blocks here
    if err != nil { ... }
}

// ✅ Collect results, then drain them after the publish loop
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, msg := range messages {
    results = append(results, topic.Publish(ctx, msg))
}
// Now drain — RPCs have been batching while you were publishing
for i, r := range results {
    id, err := r.Get(ctx)
    if err != nil {
        log.Printf("msg %d failed: %v", i, err)
    }
    _ = id
}
```

For continuous streams, drain results in a separate goroutine:

```go
var wg sync.WaitGroup
for _, msg := range messages {
    r := topic.Publish(ctx, msg)
    wg.Add(1)
    go func(r *pubsub.PublishResult) {
        defer wg.Done()
        if _, err := r.Get(ctx); err != nil {
            log.Printf("publish failed: %v", err)
        }
    }(r)
}
wg.Wait()
```

### 3. Check for ordering keys on all messages

Ordering keys force per-key serialization on the publisher side. If you're stamping every message with the same key (or any key when order doesn't matter), remove them:

```go
// ❌ Unnecessary ordering key caps throughput
topic.Publish(ctx, &pubsub.Message{
    Data:        data,
    OrderingKey: "all-messages", // don't do this unless you need order
})

// ✅ No key = full parallel batching
topic.Publish(ctx, &pubsub.Message{Data: data})
```

If you genuinely need ordering, use many distinct keys (one per logical stream) rather than one global key.

### 4. Flush cleanly on shutdown

`topic.Stop()` flushes the in-flight batch and waits for all pending RPCs. Without it, the last batch is silently dropped when your process exits.

```go
defer client.Close()  // closes the gRPC connection
defer topic.Stop()    // ← must come AFTER client.Close() in defer order,
                      //   meaning it runs BEFORE — flushes first, then closes
```

Because `defer` runs LIFO, write them in this order so `Stop` runs before `Close`:

```go
defer client.Close()
defer topic.Stop()
// topic.Stop() runs first (LIFO), then client.Close()
```

---

## Expected impact

| Change | Typical throughput gain |
|---|---|
| `DelayThreshold` 1ms → 50ms | 10–50× for small messages |
| `CountThreshold` 100 → 1000 | Fills batches before delay fires |
| Async `Get()` | Removes serialization bottleneck |
| `NumGoroutines` increase | Linear up to network/CPU ceiling |

Start with `DelayThreshold` and the async `Get()` pattern — those two changes alone usually move the needle from hundreds to tens of thousands of messages per second on a single publisher instance.

---

## Hard limits to keep in mind

- Max **1000 messages** per batch (Pub/Sub API limit — `CountThreshold` is capped here)
- Max **10 MiB** per publish request
- Per-region publish quota is **1 GB/s** by default (requestable increase)
- If you're still hitting a ceiling after tuning, run multiple publisher instances or goroutines, each with their own `Topic` handle

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more thorough and precise on all three rubric criteria. It explicitly explains why the defaults cause low throughput (the 10ms timer math), strongly warns against per-publish blocking Get() with a clear anti-pattern/correct-pattern comparison, and explicitly calls out topic.Stop() as critical for flushing batches on shutdown. Answer A covers the same ground but less precisely—it mentions Stop() only in a comment and doesn't emphasize it as a shutdown requirement.

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
| warns against per-publish blocking Get | ✓ | `Don't Block on `Get` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

<details><summary>haiku: baseline answer</summary>

# Tuning Go Pub/Sub Publisher Performance

If you're getting only hundreds of messages/sec when your topic can handle more, the issue is likely **batching and concurrency**, not the topic itself. Here's what to tune:

## 1. **Enable Message Batching** (Most Important)

By default, the Go client batches messages, but the defaults are conservative:

```go
topic := client.Topic("my-topic")

// Tune these settings
topic.PublishSettings.CountThreshold = 1000    // Batch after N messages
topic.PublishSettings.DelayThreshold = 100 * time.Millisecond  // Or after this duration
topic.PublishSettings.ByteThreshold = 1e7      // Or after N bytes (~10MB)
```

**Key tuning:**
- Increase `CountThreshold` (default is 100) — batch more messages together
- Increase `DelayThreshold` slightly if latency allows (default is 10ms)
- Adjust `ByteThreshold` based on your message size

## 2. **Increase Concurrency**

The client limits concurrent publish requests:

```go
topic.PublishSettings.NumGoroutines = 25  // Default is often 10
```

Increase this if you have CPU headroom and network capacity.

## 3. **Use Async Publishing Correctly**

Make sure you're not blocking on results:

```go
// ❌ SLOW - blocks waiting for each result
for _, msg := range messages {
    result := topic.Publish(ctx, &pubsub.Message{Data: msg})
    <-result.Ready()  // Blocks here!
}

// ✅ FAST - fire and forget (or collect later)
results := make([]*pubsub.PublishResult, 0)
for _, msg := range messages {
    result := topic.Publish(ctx, &pubsub.Message{Data: msg})
    results = append(results, result)
}

// Wait for all at the end
for _, result := range results {
    _, err := result.Get(ctx)
    if err != nil {
        log.Fatal(err)
    }
}
```

## 4. **Check Your Context**

Ensure your context isn't timing out:

```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()
```

For high-throughput publishing, use a longer timeout or `context.Background()`.

## 5. **Monitor What's Actually Happening**

Add metrics to see where time is spent:

```go
start := time.Now()
result := topic.Publish(ctx, &pubsub.Message{Data: data})
id, err := result.Get(ctx)
elapsed := time.Since(start)
log.Printf("Publish took %v", elapsed)
```

## Example Optimized Setup

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    CountThreshold:  1000,
    DelayThreshold:  100 * time.Millisecond,
    ByteThreshold:   1e7,
    NumGoroutines:   25,
}

// Publish many messages
results := make([]*pubsub.PublishResult, len(messages))
for i, msg := range messages {
    results[i] = topic.Publish(ctx, &pubsub.Message{Data: msg})
}

// Wait for all
for _, result := range results {
    _, err := result.Get(ctx)
    // handle err
}
```

## Quick Checklist

- [ ] Increase `CountThreshold` to 500-1000
- [ ] Increase `NumGoroutines` to 20-50
- [ ] Use async publishing (don't block on each result)
- [ ] Batch your publishes in a loop rather than one-at-a-time
- [ ] Check context timeout isn't too short
- [ ] Verify network/CPU aren't saturated on your publisher

Start with `CountThreshold=1000` and `NumGoroutines=25` and measure. You should see dramatic improvement.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Publisher Throughput Tuning

You're hitting the default batching limits. Pub/Sub's Go SDK batches publishes to amortize RPC overhead, but the defaults are conservative for low-latency use cases. Here's the fix:

## The Problem

By default, `PublishSettings` batches only when **any** of these thresholds is hit:
- **100 messages** (`CountThreshold`)
- **10 milliseconds** (`DelayThreshold`)
- **1 MiB** (`ByteThreshold`)

For small messages, you're likely hitting the 10ms timer repeatedly, sending ~100 msgs/batch. At 10ms per batch, that's ~10 batches/sec × 100 msgs = ~1000 msgs/sec max — and you're probably lower because of network latency variance.

## The Fix

Raise the batching thresholds to match your throughput target:

```go
topic := client.Topic("my-topic")
topic.PublishSettings.CountThreshold = 1000      // Wait for 1000 msgs
topic.PublishSettings.DelayThreshold = 100 * time.Millisecond  // or 100ms
topic.PublishSettings.ByteThreshold = 10 * 1024 * 1024  // 10 MiB

// Now publish
for i := 0; i < 100000; i++ {
    result := topic.Publish(ctx, &pubsub.Message{
        Data: []byte(fmt.Sprintf("msg-%d", i)),
    })
    // Do NOT call result.Get() synchronously — that defeats batching.
    // Instead, collect results and Get() them on a background goroutine.
    _ = result
}

// Flush pending publishes before shutdown.
topic.Stop()
```

## Critical: Don't Block on `Get()`

The **biggest throughput killer** is calling `result.Get()` synchronously after each publish:

```go
// ❌ WRONG — defeats batching, ~1 RPC per message
for i := 0; i < 100000; i++ {
    result := topic.Publish(ctx, &pubsub.Message{Data: []byte(...)})
    msgID, err := result.Get(ctx)  // Blocks until this message is ack'd by Pub/Sub
}
```

Instead, collect results and wait on a background goroutine:

```go
// ✅ RIGHT — batching works, results collected asynchronously
results := make([]*pubsub.PublishResult, 0, 100000)
for i := 0; i < 100000; i++ {
    result := topic.Publish(ctx, &pubsub.Message{Data: []byte(...)})
    results = append(results, result)
}

// Wait for all in parallel (or on a worker pool)
var wg sync.WaitGroup
for _, result := range results {
    wg.Add(1)
    go func(r *pubsub.PublishResult) {
        defer wg.Done()
        _, err := r.Get(ctx)
        if err != nil {
            log.Printf("publish error: %v", err)
        }
    }(result)
}
wg.Wait()

topic.Stop()  // Flush any final batch
```

## Tuning Guidelines

| Scenario | CountThreshold | DelayThreshold | ByteThreshold |
|---|---|---|---|
| Low-latency, small msgs | 100–500 | 5–10ms | 100 KiB |
| Balanced (default) | 100 | 10ms | 1 MiB |
| High throughput, small msgs | 1000–5000 | 50–100ms | 5–10 MiB |
| High throughput, large msgs | 100–500 | 50–100ms | 10–50 MiB |

**Start with `CountThreshold=1000` and `DelayThreshold=100ms`** for most workloads. Measure end-to-end latency (publish to subscriber receives) and adjust down if you need lower latency.

## Other Throughput Killers

1. **Ordering keys on all messages** — ordering forces per-key serialization. Use ordering keys only where order matters; mix ordered and unordered publishes if needed.
2. **Missing `topic.Stop()` on shutdown** — in-flight batches are dropped. Always call `Stop()` before exiting.
3. **Publish errors blocking the key** — if a message with `OrderingKey="foo"` fails, all subsequent publishes for `"foo"` block until you call `topic.ResumePublish("foo")`. See [references/publishing.md](references/publishing.md) for error handling.

## Monitoring

Check your actual throughput with:
```bash
gcloud pubsub topics describe my-topic --format='value(messageStoragePolicy)'
gcloud monitoring time-series list --filter='resource.type="pubsub_topic" AND metric.type="pubsub.googleapis.com/topic/publish_message_operation_count"'
```

If you're still capped after tuning, you may be hitting the **per-region quota** (default 10k msgs/sec per topic). Request a quota increase via the Cloud Console.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the three key criteria well, but Answer A is more precise on the batching thresholds (explicitly recommending raising DelayThreshold to 100ms and ByteThreshold to 5MiB, not just CountThreshold), gives a clearer explanation of why synchronous Get() defeats batching, and prominently calls out Topic.Stop() with an explanation of consequences. Answer B adds useful extras (gRPC connection pool, flow control) but slightly undersells DelayThreshold tuning and buries Topic.Stop() in a passing mention rather than giving it its own section.

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
| warns against per-publish blocking Get | ✓ | `Don't `Get` |
| mentions Topic.Stop on shutdown | ✓ | `topic.Stop` |

<details><summary>opus: baseline answer</summary>

A few hundred msg/sec from a Go publisher to Pub/Sub almost always means you're bottlenecked on the **client**, not the topic. Pub/Sub topics scale to millions of messages/sec; the Go client just needs to be configured and used correctly.

Here's what to look at, in rough order of impact:

## 1. Batch settings (`PublishSettings`)

The defaults are conservative. Tune these on `topic.PublishSettings`:

```go
topic.PublishSettings = pubsub.PublishSettings{
    DelayThreshold: 10 * time.Millisecond, // default 10ms — fine
    CountThreshold: 1000,                   // default 100 — raise it
    ByteThreshold:  1e6,                    // default 1MB — usually fine
    NumGoroutines:  runtime.NumCPU(),       // default 25*GOMAXPROCS, try tuning
    Timeout:        60 * time.Second,
}
```

For small messages, `CountThreshold` is usually the limit. Raising it from 100 → 1000 lets the client pack more per RPC.

## 2. Don't block on every `Result.Get`

This is the #1 mistake. If you do:

```go
for _, msg := range messages {
    r := topic.Publish(ctx, msg)
    _, err := r.Get(ctx) // <-- serializes everything
}
```

…you've defeated batching entirely. Instead, fan out:

```go
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, m := range messages {
    results = append(results, topic.Publish(ctx, m))
}
for _, r := range results {
    if _, err := r.Get(ctx); err != nil { /* handle */ }
}
```

Or handle results in a separate goroutine / errgroup with a worker pool.

## 3. Reuse the client and topic

`pubsub.Client` and `*pubsub.Topic` are safe for concurrent use and maintain the gRPC connection pool and batchers. Don't create a new one per request. Call `topic.Stop()` only at shutdown to flush.

## 4. Increase gRPC connections

Under high throughput, a single HTTP/2 connection becomes the bottleneck (stream concurrency limit). Bump connection pool size when constructing the client:

```go
client, err := pubsub.NewClient(ctx, projectID,
    option.WithGRPCConnectionPool(runtime.NumCPU()),
)
```

A pool of 4–8 is usually plenty.

## 5. Flow control

Enable publisher flow control so you don't OOM but also don't stall:

```go
topic.PublishSettings.FlowControlSettings = pubsub.FlowControlSettings{
    MaxOutstandingMessages: 10000,
    MaxOutstandingBytes:    100 * 1024 * 1024,
    LimitExceededBehavior:  pubsub.FlowControlBlock,
}
```

## 6. Check ordering keys

If you're setting `OrderingKey`, throughput per key is limited (messages with the same key must publish serially). Either remove ordering or spread across many keys.

## 7. Verify it's actually the client

- Run with `GODEBUG=http2debug=1` or enable OpenTelemetry tracing on the client to see RPC latency.
- Check Cloud Monitoring: `pubsub.googleapis.com/topic/send_request_count` and request latency. If RPC latency is fine but rate is low, it's batching/concurrency. If latency is high, it's network/region.
- Make sure your publisher runs in the same region as the topic.

## Quick checklist

| Symptom | Likely fix |
|---|---|
| Calling `Get` inline | Fan out results |
| ~100 msg/batch ceiling | Raise `CountThreshold` |
| One connection saturating | `WithGRPCConnectionPool` |
| Using ordering keys | Use more keys or drop ordering |
| New client per call | Reuse client/topic |

In practice, fixing the `Result.Get` pattern + raising `CountThreshold` + a connection pool of 4 will typically take you from a few hundred to tens of thousands of msg/sec on a single VM.

</details>

<details><summary>opus: skill-loaded answer</summary>

Short answer: your defaults are throttling you. The Go client batches publishes, but the default thresholds are tiny (100 msgs / 10 ms / 1 MiB), and a couple of common code patterns defeat batching entirely. Tune in this order:

## 1. Raise `PublishSettings` thresholds

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    CountThreshold: 1000,                  // default 100
    DelayThreshold: 100 * time.Millisecond, // default 10ms
    ByteThreshold:  5 * 1024 * 1024,       // default 1 MiB; raise to 5–10 MiB
    NumGoroutines:  runtime.NumCPU(),      // parallel publish RPCs per topic
    Timeout:        60 * time.Second,
}
```

A batch flushes when **any** threshold is hit. With small messages, `CountThreshold` and `DelayThreshold` are what matter — raising `CountThreshold` lets more messages amortize each RPC's overhead; raising `DelayThreshold` gives the batcher time to fill up.

## 2. Don't `Get()` synchronously after every Publish

This is the most common throughput killer:

```go
// ❌ Defeats batching — each Publish waits for its own RPC round-trip
for _, m := range messages {
    res := topic.Publish(ctx, m)
    if _, err := res.Get(ctx); err != nil { ... }
}
```

`Publish` is non-blocking and returns immediately — it hands the message to the batcher. Calling `Get()` in the same loop iteration forces the batch to flush with one message in it. Instead, fire all publishes first, then collect results on a separate goroutine:

```go
// ✅ Lets the batcher accumulate
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, m := range messages {
    results = append(results, topic.Publish(ctx, m))
}
// Drain in a goroutine, or after the publish loop
for _, r := range results {
    if _, err := r.Get(ctx); err != nil { /* handle */ }
}
```

## 3. Reuse one `*pubsub.Topic` handle

`Topic` is goroutine-safe and holds the batcher state. If you're calling `client.Topic("name")` per request, you're getting a fresh handle with an empty batch each time. Create it once at startup and share it.

## 4. Check for ordering keys

If every message has the same `OrderingKey` (or you set one unnecessarily), publishes for that key are serialized — capping you at roughly one in-flight batch per key. Only use ordering keys where order actually matters, and partition across many keys when you do.

## 5. Always `topic.Stop()` on shutdown

```go
defer topic.Stop() // flushes pending batches
```

This isn't a throughput fix, but without it your last batch (up to several seconds of messages on the new settings) is silently dropped on process exit.

## What to expect

After (1)–(3), small-message throughput on a single publisher should jump from hundreds/sec into the tens of thousands/sec range, bounded by your per-region publish quota. If you're still slow after that, check:

- Region locality — publishing across regions adds RTT to every batch RPC.
- `oldest_unacked_message_age` and publish-side error metrics, in case you're hitting quota and the client is retrying.

The "Publishing" reference in this skill has the full settings rundown if you want to dig further.

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly identify all four rubric criteria: IAM as the root cause, publisher role on the DLT, subscriber role on the source subscription, and the Pub/Sub service account format. Answer A is slightly more concise and better organized with a clear table, while Answer B adds a Terraform example and a Python code sample that broaden its practical utility. Neither answer is meaningfully superior on the core rubric criteria.

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

## Most Common Root Causes

### 1. Missing IAM Permissions (Most Frequent Culprit)

The Pub/Sub service account needs permissions on **both** the dead-letter topic **and** your original subscription.

```bash
# Get your project's Pub/Sub service account
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

echo "Service Account: $PUBSUB_SA"

# Grant Publisher role on the dead-letter topic
gcloud pubsub topics add-iam-policy-binding your-dead-letter-topic \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher"

# Grant Subscriber role on the ORIGINAL subscription
# (needed so Pub/Sub can acknowledge messages on your behalf)
gcloud pubsub subscriptions add-iam-policy-binding your-original-subscription \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber"
```

> ⚠️ Without these permissions, Pub/Sub **silently fails** to forward to the DLT and just keeps retrying. No error is surfaced to you.

---

### 2. `maxDeliveryAttempts` Range Violation

```bash
# WRONG - out of valid range
maxDeliveryAttempts=1   # Too low
maxDeliveryAttempts=100 # Too high

# Valid range is 5–100 inclusive
maxDeliveryAttempts=5   # Minimum valid value
maxDeliveryAttempts=10  # Typical value
```

---

### 3. Delivery Attempt Count Isn't Incrementing

Pub/Sub only increments the delivery attempt counter when it receives a **NACK** or the **ack deadline expires**. If your subscriber is doing this, the counter never advances:

```python
# ❌ BAD - silently dropping the message, counter may not increment correctly
def callback(message):
    try:
        process(message)
    except Exception:
        pass  # Neither acking nor nacking!
    message.ack()  # Acking even on failure - DLT never triggered

# ✅ GOOD - explicitly NACK so the attempt counter increments
def callback(message):
    try:
        process(message)
        message.ack()
    except Exception as e:
        print(f"Processing failed: {e}")
        message.nack()  # Explicit NACK triggers retry counting
```

---

### 4. Verifying Your Subscription Configuration

```bash
# Check that DLT is actually configured on the subscription
gcloud pubsub subscriptions describe your-subscription --format=json | \
  jq '.deadLetterPolicy'

# Expected output:
# {
#   "deadLetterTopic": "projects/your-project/topics/your-dead-letter-topic",
#   "maxDeliveryAttempts": 5
# }

# If output is null, the DLT was never actually set
```

---

### 5. Updating an Existing Subscription (Easy to Miss)

```bash
# Creating a new subscription with DLT - correct
gcloud pubsub subscriptions create your-subscription \
  --topic=your-topic \
  --dead-letter-topic=projects/your-project/topics/your-dead-letter-topic \
  --max-delivery-attempts=5

# Updating an EXISTING subscription - requires explicit update command
gcloud pubsub subscriptions modify-push-config your-subscription  # ❌ Wrong command

# ✅ Correct way to update existing subscription
gcloud pubsub subscriptions update your-subscription \
  --dead-letter-topic=projects/your-project/topics/your-dead-letter-topic \
  --max-delivery-attempts=5
```

---

## Complete Working Terraform Example

```hcl
locals {
  project_number = data.google_project.project.number
  pubsub_sa      = "service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

data "google_project" "project" {}

resource "google_pubsub_topic" "main" {
  name = "your-topic"
}

resource "google_pubsub_topic" "dead_letter" {
  name = "your-dead-letter-topic"
}

resource "google_pubsub_subscription" "main" {
  name  = "your-subscription"
  topic = google_pubsub_topic.main.name

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5  # Valid range: 5-100
  }

  # Give enough time for processing before ack deadline expires
  ack_deadline_seconds = 60
}

# Critical: Publisher on DLT
resource "google_pubsub_topic_iam_member" "dlt_publisher" {
  topic  = google_pubsub_topic.dead_letter.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${local.pubsub_sa}"
}

# Critical: Subscriber on original subscription
resource "google_pubsub_subscription_iam_member" "original_subscriber" {
  subscription = google_pubsub_subscription.main.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${local.pubsub_sa}"
}
```

---

## Diagnostic Checklist

```
[ ] IAM: Pub/Sub SA has Publisher on dead-letter topic
[ ] IAM: Pub/Sub SA has Subscriber on original subscription
[ ] maxDeliveryAttempts is between 5 and 100
[ ] Subscriber explicitly NACKs on failure (not silently acking)
[ ] Verified DLT config with `describe` command (not just assuming it applied)
[ ] DLT topic exists in the same project (cross-project needs full resource path)
[ ] A subscription exists on the DLT itself (to actually receive the messages)
```

---

## Quick Verification Test

```bash
# Monitor delivery attempt counts in real time
gcloud pubsub subscriptions describe your-subscription \
  --format="value(deadLetterPolicy)"

# Check if messages are arriving in DLT
# (you need a subscription on the DLT to pull from it)
gcloud pubsub subscriptions create dlt-debug-sub \
  --topic=your-dead-letter-topic

gcloud pubsub subscriptions pull dlt-debug-sub --limit=10 --auto-ack
```

**The IAM permissions issue is almost certainly your problem** — it's the most common cause and Pub/Sub gives you zero indication that it's failing to forward messages because of it.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The most common cause is missing IAM bindings — Pub/Sub silently continues retrying instead of forwarding to the DLT when the service account lacks permission. There are usually two or three things to check in order.

## 1. IAM bindings (most likely cause)

Pub/Sub uses a **per-project service account** to forward messages. It needs two roles, and both are required:

| Role | On what resource | Why |
|---|---|---|
| `roles/pubsub.publisher` | The dead-letter **topic** | So it can publish the failed message |
| `roles/pubsub.subscriber` | The **source subscription** | So it can ack the message after forwarding |

The service account follows the pattern:
```
service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com
```

Get your project number and grant both roles:

```bash
PROJECT_ID=your-project-id
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# Publisher role on the dead-letter topic
gcloud pubsub topics add-iam-policy-binding your-dlt-topic \
  --member="serviceAccount:${SA}" \
  --role="roles/pubsub.publisher"

# Subscriber role on the source subscription
gcloud pubsub subscriptions add-iam-policy-binding your-source-subscription \
  --member="serviceAccount:${SA}" \
  --role="roles/pubsub.subscriber"
```

Missing **either** binding causes silent retry loops. There is no error surfaced to the publisher or subscriber — the only signal is that `num_undelivered_messages` keeps climbing and the DLT stays empty.

---

## 2. Verify the DLT is actually attached

Confirm the subscription has the dead-letter policy set correctly:

```bash
gcloud pubsub subscriptions describe your-source-subscription \
  --format='yaml(deadLetterPolicy)'
```

Expected output:
```yaml
deadLetterPolicy:
  deadLetterTopic: projects/your-project/topics/your-dlt-topic
  maxDeliveryAttempts: 5
```

If this is empty, the DLT was never attached (or was attached to the wrong subscription). Re-apply it:

```bash
gcloud pubsub subscriptions modify-push-config your-source-subscription \
  --dead-letter-topic=projects/your-project/topics/your-dlt-topic \
  --max-delivery-attempts=5
```

---

## 3. Understand what counts as a "delivery attempt"

`maxDeliveryAttempts` counts **ack-deadline expirations and explicit nacks**, not wall-clock time. A few things can reset or stall the counter:

- **Your subscriber is neither acking nor nacking** — if the handler crashes or the process restarts before calling `msg.Ack()` or `msg.Nack()`, the lease expires and redelivery happens, but the attempt counter does increment. If the process is restarting very quickly, check whether it's actually reaching the handler at all.
- **The ack deadline is very long** — with a 600s deadline and slow processing, it can take a long time to accumulate 5 attempts. Lower the deadline or explicitly `msg.Nack()` immediately on unrecoverable errors instead of waiting for expiry.
- **Exactly-once delivery is enabled** — EOD interacts with the attempt counter in subtle ways. If you don't need EOD, disable it on the source subscription.

In Go, always nack explicitly on unrecoverable errors rather than letting the lease expire:

```go
sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
    if err := process(msg); err != nil {
        if isUnrecoverable(err) {
            msg.Nack() // counts as an attempt immediately
            return
        }
        msg.Nack() // retryable — still nack, let backoff handle it
        return
    }
    msg.Ack()
})
```

---

## 4. Confirm the DLT has a subscription

The DLT itself needs at least one subscription, otherwise forwarded messages are accepted but immediately discarded (no subscriber = no retention beyond the topic's message retention window). Create one if it's missing:

```bash
gcloud pubsub subscriptions create your-dlt-sub \
  --topic=your-dlt-topic \
  --message-retention-duration=7d
```

---

## Quick diagnostic checklist

```
[ ] IAM: publisher role on DLT topic
[ ] IAM: subscriber role on source subscription
[ ] deadLetterPolicy confirmed on source subscription (gcloud describe)
[ ] maxDeliveryAttempts is 5–100 (values outside this range are rejected)
[ ] Subscriber is calling msg.Nack() on failures, not silently dropping
[ ] DLT has at least one subscription so messages aren't silently discarded
```

The IAM step catches the problem in the vast majority of cases — start there.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly identifies both required IAM bindings — publisher on the DLT and subscriber on the source subscription — which is the core of the focus area. Answer A only mentions the publisher role on the DLT and completely omits the subscriber role on the source subscription, which is a critical miss. Answer B also correctly names the Pub/Sub service account format and provides commands for both bindings.

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

The most common reason messages aren't reaching your DLT is that you're missing the **IAM permission** for Pub/Sub to *publish* to the dead-letter topic.

## Required Setup

### 1. **Grant Publishing Permission**
The Pub/Sub service account needs `pubsub.publisher` role on the dead-letter topic:

```bash
gcloud pubsub topics add-iam-policy-binding YOUR_DLT_TOPIC \
  --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/pubsub.editor
```

Or more restrictively:
```bash
gcloud pubsub topics add-iam-policy-binding YOUR_DLT_TOPIC \
  --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

### 2. **Verify Configuration**
Check your subscription settings:

```bash
gcloud pubsub subscriptions describe YOUR_SUBSCRIPTION \
  --format='value(deadLetterPolicy)'
```

Should show:
```
deadLetterPolicy:
  deadLetterTopic: projects/PROJECT_ID/topics/YOUR_DLT_TOPIC
  maxDeliveryAttempts: 5
```

## Other Checklist Items

- ✅ **DLT exists** in the same project
- ✅ **maxDeliveryAttempts** is set (not just the topic configured)
- ✅ **Subscription has a push/pull handler** that actually rejects messages (returns NACK or error)
- ✅ **Check Cloud Logging** for DLT delivery errors:
  ```bash
  gcloud logging read "resource.type=pubsub_subscription AND 
    jsonPayload.subscription_id=YOUR_SUBSCRIPTION" --limit 50
  ```

## Testing

Send a test message and verify it reaches the DLT after 5 failed attempts:

```bash
gcloud pubsub subscriptions pull YOUR_DLT_SUBSCRIPTION --auto-ack --limit=1
```

The IAM permission is the #1 culprit—without it, Pub/Sub silently fails to deliver to the DLT.

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

If the service account is missing, add it:

```bash
# Grant publisher on DLT
gcloud pubsub topics add-iam-policy-binding DLT_TOPIC_NAME \
  --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/pubsub.publisher

# Grant subscriber on source subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUB_NAME \
  --member=serviceAccount:service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/pubsub.subscriber
```

### 2. **Confirm DLT Configuration on the Subscription**

Verify the DLT is actually attached and `maxDeliveryAttempts` is set:

```bash
gcloud pubsub subscriptions describe SOURCE_SUB_NAME \
  --format='value(deadLetterPolicy)'
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

### 3. **Check the Retry Policy**

If no explicit retry policy is set, Pub/Sub uses aggressive defaults (immediate retries). Confirm the retry policy is configured with exponential backoff:

```bash
gcloud pubsub subscriptions describe SOURCE_SUB_NAME \
  --format='value(retryPolicy)'
```

Expected output:
```
retryPolicy:
  minimumBackoff: 10s
  maximumBackoff: 600s
```

If missing, add one:

```bash
gcloud pubsub subscriptions update SOURCE_SUB_NAME \
  --min-retry-delay=10s \
  --max-retry-delay=600s
```

### 4. **Verify the DLT Topic Exists and Is Accessible**

```bash
gcloud pubsub topics describe DLT_TOPIC_NAME
```

If the topic doesn't exist or you get a permission error, create it or fix access:

```bash
gcloud pubsub topics create DLT_TOPIC_NAME
```

### 5. **Check Subscription Expiration Policy**

If the subscription has an expiration policy that deletes it before messages reach the DLT, they'll be lost. Verify:

```bash
gcloud pubsub subscriptions describe SOURCE_SUB_NAME \
  --format='value(expirationPolicy)'
```

If set to a short duration, remove or extend it:

```bash
gcloud pubsub subscriptions update SOURCE_SUB_NAME \
  --clear-expiration-policy
```

## In Go Code

If you're creating the subscription programmatically, ensure the DLT is set:

```go
sub, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
  Topic: topic,
  DeadLetterPolicy: &pubsub.DeadLetterPolicy{
    DeadLetterTopic: dlTopic,
    MaxDeliveryAttempts: 5,
  },
  RetryPolicy: &pubsub.RetryPolicy{
    MinimumBackoff: 10 * time.Second,
    MaximumBackoff: 600 * time.Second,
  },
})
```

Then **manually grant IAM** as shown above — the Go SDK does not auto-grant permissions.

## Debugging: Where Are the Messages?

1. **Check the DLT for messages:**
   ```bash
   gcloud pubsub subscriptions pull dlt-debug-sub --auto-ack --limit=10
   ```
   (Create a temporary pull subscription on the DLT if you don't have one.)

2. **Monitor the source subscription's backlog:**
   ```bash
   gcloud pubsub subscriptions describe SOURCE_SUB_NAME \
     --format='value(numUndeliveredMessages)'
   ```
   If this grows indefinitely, messages are not reaching the DLT.

3. **Check Pub/Sub logs** (Cloud Logging):
   ```bash
   gcloud logging read \
     'resource.type="pubsub_subscription" AND resource.labels.subscription_id="SOURCE_SUB_NAME"' \
     --limit=50 --format=json
   ```
   Look for errors mentioning the DLT or IAM denials.

## Summary

**99% of the time:** Add the Pub/Sub service account with `roles/pubsub.publisher` on the DLT and `roles/pubsub.subscriber` on the source subscription. After that, messages will flow to the DLT after `maxDeliveryAttempts` is exceeded.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly identify IAM as the root cause, mention the Pub/Sub service account, and specify both the publisher role on the DLT and subscriber role on the source subscription. Answer A provides slightly more detail on failure modes (e.g., what happens if only one binding is set) and verification steps, while Answer B adds a useful tip about triggering service agent creation in fresh projects. Neither answer is meaningfully superior across all rubric criteria.

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

The most common cause: **the Pub/Sub service account doesn't have the right IAM permissions** to forward messages to the dead-letter topic and acknowledge them on the source subscription.

When you configure a dead-letter topic, Pub/Sub itself (not your subscriber) needs to:
1. **Publish** to the dead-letter topic
2. **Acknowledge** the original message on the source subscription

If either permission is missing, Pub/Sub silently keeps redelivering the message — `maxDeliveryAttempts` is effectively ignored.

### Fix

Find your project's Pub/Sub service account:

```
service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com
```

Grant it both roles:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# Allow publishing to the DLT
gcloud pubsub topics add-iam-policy-binding DEAD_LETTER_TOPIC \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher"

# Allow acking the original subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUBSCRIPTION \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber"
```

### Other things to check

- **The subscriber must actually nack (or let the ack deadline expire)**. If your code catches the exception and acks the message, that counts as a successful delivery and the counter never advances.
- **Delivery attempt count is best-effort**. It's only tracked when `enableMessageOrdering` isn't interfering, and it can take slightly more than `maxDeliveryAttempts` nacks before the message moves. But "forever" indicates IAM, not this.
- **Check the subscription config** actually shows the DLT:
  ```bash
  gcloud pubsub subscriptions describe SOURCE_SUBSCRIPTION
  ```
  Look for `deadLetterPolicy` with both `deadLetterTopic` and `maxDeliveryAttempts`.
- **The Pub/Sub service agent must exist** in your project. It's auto-created the first time you use Pub/Sub, but in fresh projects you may need to trigger it (e.g., via `gcloud beta services identity create --service=pubsub.googleapis.com`).
- **DLT must have a subscription** if you want to actually see the messages land — otherwise they're published and immediately dropped per the topic's retention.

99% of the time it's the IAM binding on the dead-letter topic. Add `roles/pubsub.publisher` to the Pub/Sub service agent and the messages will start flowing.

</details>

<details><summary>opus: skill-loaded answer</summary>

The almost-certain cause: **missing IAM bindings**. Configuring `maxDeliveryAttempts` on the subscription is only half the setup — Pub/Sub uses a service account to forward dead-lettered messages, and that account needs explicit permissions on both ends. Without them, the forward silently fails and the message just keeps retrying.

## What to check

You need the Pub/Sub **service account** for your project (not your own credentials):

```
service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com
```

Find your project number with `gcloud projects describe PROJECT_ID --format='value(projectNumber)'`.

That service account needs **two** role bindings:

1. **`roles/pubsub.publisher` on the dead-letter topic** — so it can publish the failed message to the DLT.
2. **`roles/pubsub.subscriber` on the source subscription** — so it can ack the message on the source after forwarding.

Both are required. If only #1 is set, the message gets republished to the DLT but never acked on the source, so it keeps redelivering. If only #2 is set, the forward fails outright.

## Fix

```bash
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

# 1. Grant publisher on the DLT
gcloud pubsub topics add-iam-policy-binding DLT_NAME \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.publisher"

# 2. Grant subscriber on the source subscription
gcloud pubsub subscriptions add-iam-policy-binding SOURCE_SUB_NAME \
  --member="serviceAccount:${PUBSUB_SA}" \
  --role="roles/pubsub.subscriber"
```

## Verify it's working

After the bindings propagate (usually seconds, sometimes a minute):

- Check the source subscription's `num_undelivered_messages` metric — backlog should start draining.
- Check the DLT for incoming messages: `gcloud pubsub subscriptions pull DLT_SUB --auto-ack --limit=10` (you'll need a subscription on the DLT to inspect them).
- Confirm the wiring on the source: `gcloud pubsub subscriptions describe SOURCE_SUB --format='yaml(deadLetterPolicy)'` should show both `deadLetterTopic` and `maxDeliveryAttempts`.

## Other things that can look like this (less common)

- **Acks vs nacks aren't being counted.** A delivery attempt only counts toward `maxDeliveryAttempts` when the message is **nacked** or the **ack deadline expires**. If your handler is throwing but something is silently acking the message anyway (or it's being filtered out before your handler), the attempt counter never advances. Check that your handler is actually calling `msg.Nack()` on failure (or letting the deadline expire by not calling anything).
- **`maxDeliveryAttempts` is a best-effort threshold.** Pub/Sub may deliver a few extra times beyond the configured value before forwarding — but "a few extra," not "forever." If you're seeing dozens or hundreds of retries with no DLT delivery, it's IAM, not threshold drift.
- **The DLT itself has no subscription**, so you assume nothing is arriving. Messages published to a topic with no subscriptions are dropped. Create a subscription on the DLT before testing, or you'll think the forward isn't working when it actually is.

Start with the IAM check — that's the cause about 95% of the time when "DLT configured but messages retry forever" is the symptom.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B includes `defer topic.Stop()` which is explicitly called out in the rubric as required, and provides a clear explanation of why it matters (silent message drops without it). Answer B also warns about the batching implications of `Publish` being asynchronous, addressing the 'warns about Get() in a loop' concern by explaining the batching trap. Answer A omits `topic.Stop()` entirely and doesn't warn about the batching behavior or the loop trap.

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

The key detail is **`result.Get(ctx)`**. `Publish` itself is non-blocking — it just queues the message locally. Calling `.Get()` on the returned `PublishResult` is what blocks until the Pub/Sub server acknowledges receipt and hands back the server-assigned message ID, guaranteeing the message actually made it before the program exits.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the minimal correct version:

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
	defer topic.Stop() // flushes the pending batch before exit

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

Two lines that look optional but aren't:

- **`defer topic.Stop()`** — `Publish` is asynchronous and batches messages internally. Without `Stop()`, any message still in the buffer when `main` returns is silently dropped. `Stop()` flushes the batch and blocks until it drains.
- **`result.Get(ctx)`** — this is what actually blocks until Pub/Sub acknowledges the message server-side and returns the stable message ID. Without it you have no confirmation the message was ever sent, and you'd also be racing `topic.Stop()`.

The "even simpler" version that skips one of these is a trap: it compiles, runs without errors, and silently loses messages.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly calls topic.Stop() before exit and explains why it matters for flushing batched messages, while Answer A omits this entirely. Answer B also handles errors properly and explains the batching trap, making it both more correct and more educational. Answer A's silence on Stop() and the batching implication is exactly the trap the rubric warns against.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| calls Topic.Stop() before exit | skill |
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
	log.Println("Message published")
}
```

The key is `result.Get(ctx)` — it blocks until the message is actually published or returns an error.

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

**Why this is correct, not a trap:**

The `result.Get(ctx)` call blocks until the message is actually published to Pub/Sub (or fails). Without it, `Publish` just queues the message in a local batch — if your program exits before the batch flushes, the message is lost.

The `topic.Stop()` call at the end ensures any remaining batched messages are flushed before the process exits. Omitting it is a silent data-loss bug.

If you skip either of these, you have a "simple" snippet that loses messages on shutdown.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is superior on all three rubric criteria. It calls topic.Stop() with a defer and explains why it matters, it explicitly warns about the Get-in-a-loop anti-pattern and explains the collect-then-Get alternative, and it correctly handles the one-message case while teaching safe habits. Answer B omits topic.Stop() entirely (the topic is created inline and never stopped), and provides no warning about the batching trap when using Get in a loop.

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
| warns about Get() in a loop | ✓ | `defeats batch` |
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
	log.Printf("published msg ID: %s", id)
}
```

The key bit is `result.Get(ctx)` — it blocks until the server actually acknowledges the publish (or returns an error), so you know it went through before exiting.

</details>

<details><summary>opus: skill-loaded answer</summary>

The simplest *correct* version is short — but a few lines that look "simpler" are traps. Here's the right one, then what to avoid.

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

That's it. Two things are doing real work and are not optional:

1. **`result.Get(ctx)`** — `Publish` is async and returns immediately. Without `Get`, the program can exit before the message is sent. `Get` blocks until the Pub/Sub server has durably accepted the message and returns the server-assigned message ID (or an error).

2. **`topic.Stop()` (and `client.Close()`)** — `Stop` flushes any in-flight batch and waits for outstanding publishes. With only one message and a `Get` on it, `Stop` is technically redundant *here*, but leaving it in is the habit that keeps you safe the moment you publish a second message or move this into a loop. `client.Close()` releases the gRPC connection.

### What "simpler" versions get wrong

- **Omitting `topic.Stop()`** — fine for exactly one `Get`-ed publish, silently drops messages the moment you publish more than one without `Get`-ing each.
- **Calling `Get` inside a publish loop** — defeats batching and tanks throughput. The right pattern for many messages is to collect `*PublishResult`s and `Get` them after the loop, or just rely on `topic.Stop()` to flush and check errors via a results slice.
- **Skipping the error check on `Get`** — a successful return from `Publish` means "queued locally," not "delivered." Only `Get`'s error tells you it actually went through.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same correct CSS solution with identical properties and values. Answer B includes a helpful HTML example and a reference table, while Answer A is more concise. Neither is materially wrong or better given the focus area guidance.

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

| Property | Value | Effect |
|---|---|---|
| `justify-content` | `center` | Centers horizontally |
| `align-items` | `center` | Centers vertically |

That's it! No need for `position: absolute`, negative margins, or `transform` hacks.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

```css
.parent {
  display: flex;
  align-items: center;     /* vertical */
  justify-content: center; /* horizontal */
}
```

That's it — no sizing or positioning needed on the child.

**Quick notes:**
- The parent needs a defined height (e.g. `height: 100vh`) for vertical centering to be visible
- Works for any number of children; they'll all be centered
- If you only need one axis, drop the property you don't need

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide essentially identical CSS solutions with the same three properties. Answer B adds slightly more explanation with bullet points, but both are correct and equally useful for this question.

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

The parent needs a defined height for vertical centering to work. If you want the child to take up space, you can also add `width: 100%` or `width: 100vw` to the parent.

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers provide the same correct CSS code. Answer B adds a useful practical note about needing a defined height on the parent for vertical centering to be visible, which is a common gotcha that makes it slightly more helpful.

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

That's it. `display: flex` on the parent, then `justify-content: center` handles horizontal centering and `align-items: center` handles vertical centering.

Make sure the parent has a defined height (e.g., `height: 100vh`) so there's vertical space to center within.

</details>

<details><summary>opus: skill-loaded answer</summary>

```css
.parent {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

That's it — `justify-content` handles the horizontal axis and `align-items` handles the vertical axis (assuming the default `flex-direction: row`). The child `div` needs no special styling.

</details>

---
