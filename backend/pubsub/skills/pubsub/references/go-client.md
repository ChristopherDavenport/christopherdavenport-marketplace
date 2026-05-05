# Go Client SDK — `cloud.google.com/go/pubsub`

The Go client centers on three handle types: `*pubsub.Client`, `*pubsub.Topic`, and `*pubsub.Subscription`. The lifecycle and concurrency rules differ for each, and most production bugs trace to misunderstanding which handles are safe to share, which must be `Stop()`-ed, and the strict callback contract for `Receive`. Get those right and the SDK is forgiving.

This reference covers handle lifecycle, the publish and receive paths in idiomatic form, error inspection, OpenTelemetry tracing, and the pitfalls.

## Client Lifecycle

Create one `*pubsub.Client` per project per process. Reuse it for every topic and subscription.

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
    defer client.Close()  // closes gRPC conns; blocks briefly

    // ... use client ...
}
```

`pubsub.NewClient` opens a gRPC connection pool and is heavy. Creating per-request is a common mistake that produces latency spikes and connection-pool exhaustion.

For multi-project use, create one client per project — there's no overhead beyond the connection pool, and credentials are typically scoped per project.

## Handle Concurrency

| Handle | Concurrency rule |
|---|---|
| `*pubsub.Client` | Safe across goroutines |
| `*pubsub.Topic` | Safe across goroutines for `Publish`. Re-use one handle per topic |
| `*pubsub.Subscription` | Safe across goroutines for admin ops. **`Receive` must run alone per handle** |

`client.Topic("name")` does not call the API — it just builds a handle. Cheap.

`client.Subscription("name")` is the same. If you need two parallel `Receive` loops on the same subscription, get two handles:

```go
sub1 := client.Subscription("my-sub")
sub2 := client.Subscription("my-sub")
go sub1.Receive(ctx, handler)
go sub2.Receive(ctx, handler)
```

But more workers does not always mean more throughput — `NumGoroutines` on one `ReceiveSettings` does the same job at lower overhead.

## Publish

```go
topic := client.Topic("my-topic")
topic.PublishSettings = pubsub.PublishSettings{
    CountThreshold: 1000,
    DelayThreshold: 50 * time.Millisecond,
}
defer topic.Stop()  // CRITICAL — flushes pending publishes

result := topic.Publish(ctx, &pubsub.Message{
    Data:       []byte("payload"),
    Attributes: map[string]string{"k": "v"},
})

id, err := result.Get(ctx)
if err != nil {
    return err
}
log.Printf("published %s", id)
```

For higher throughput, fan out and collect results separately:

```go
results := make([]*pubsub.PublishResult, 0, len(messages))
for _, m := range messages {
    results = append(results, topic.Publish(ctx, m))
}
for i, r := range results {
    if _, err := r.Get(ctx); err != nil {
        return fmt.Errorf("message %d: %w", i, err)
    }
}
```

See [publishing.md](publishing.md) for `PublishSettings` tuning and ordering keys.

## Receive

```go
sub := client.Subscription("my-sub")
sub.ReceiveSettings = pubsub.ReceiveSettings{
    MaxOutstandingMessages: 100,
    NumGoroutines:          10,
    MaxExtension:           60 * time.Minute,
}

err := sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    if err := process(ctx, m); err != nil {
        m.Nack()
        return
    }
    m.Ack()
})
if err != nil {
    log.Printf("receive: %v", err)
}
```

The callback contract:

1. Call `Ack()` or `Nack()` exactly once.
2. Do work synchronously inside the callback (the SDK extends the lease only while the callback is running).
3. Cancel the outer `ctx` to shut down `Receive`.

See [subscribing.md](subscribing.md) for `ReceiveSettings` and lease internals.

## Shutdown Order

```go
ctx, cancel := context.WithCancel(context.Background())
defer cancel()

// Start consumers
go func() {
    if err := sub.Receive(ctx, handler); err != nil {
        log.Printf("receive: %v", err)
    }
}()

// On shutdown signal:
<-stopSignal

// 1. Cancel context — Receive drains in-flight callbacks and returns
cancel()

// 2. Stop topics — flushes pending publishes
for _, t := range topics {
    t.Stop()
}

// 3. Close client
client.Close()
```

The order matters:

- Cancelling first lets `Receive` finish in-flight work cleanly.
- `Topic.Stop()` second ensures no pending publishes are dropped.
- `Client.Close()` last tears down the gRPC pool.

Reversing this loses in-flight messages on both sides.

## Error Inspection

Most errors are gRPC `status.Error`. Use the standard pattern:

```go
import (
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
)

if s, ok := status.FromError(err); ok {
    switch s.Code() {
    case codes.NotFound:
        // topic/subscription does not exist
    case codes.AlreadyExists:
        // CreateTopic on an existing topic
    case codes.PermissionDenied:
        // missing IAM
    case codes.FailedPrecondition:
        // ordering key blocked, schema validation failed
    case codes.ResourceExhausted:
        // quota
    case codes.Unavailable, codes.DeadlineExceeded:
        // transient — SDK usually retried; handle as failure
    }
}
```

For `Subscription.Receive` errors, check for context cancellation:

```go
err := sub.Receive(ctx, handler)
if err != nil && !errors.Is(err, context.Canceled) {
    return err
}
```

`Receive` returns `nil` on clean context cancellation in some SDK versions; check both.

### Publish Errors

`PublishResult.Get(ctx)` returns publish errors. Common ones:

| Code | Cause | Action |
|---|---|---|
| `InvalidArgument` | Schema validation, > 10 MiB, attribute limits | Fix message; don't retry |
| `FailedPrecondition` | Ordering key blocked | `topic.ResumePublish(key)` |
| `NotFound` | Topic doesn't exist | Verify name |
| `PermissionDenied` | Missing `roles/pubsub.publisher` | Fix IAM |
| `Unavailable` / `DeadlineExceeded` | Transient | SDK retried; surfaces only after budget |

## Admin Operations

```go
// Create a topic
topic, err := client.CreateTopic(ctx, "my-topic")

// Create with config
topic, err := client.CreateTopicWithConfig(ctx, "my-topic", &pubsub.TopicConfig{
    RetentionDuration: 7 * 24 * time.Hour,
})

// Update
_, err = topic.Update(ctx, pubsub.TopicConfigToUpdate{
    RetentionDuration: 14 * 24 * time.Hour,
})

// Subscription
sub, err := client.CreateSubscription(ctx, "my-sub", pubsub.SubscriptionConfig{
    Topic:                     topic,
    AckDeadline:               30 * time.Second,
    EnableMessageOrdering:     true,
    EnableExactlyOnceDelivery: true,
    DeadLetterPolicy: &pubsub.DeadLetterPolicy{
        DeadLetterTopic:     "projects/my-project/topics/my-dlt",
        MaxDeliveryAttempts: 10,
    },
    RetryPolicy: &pubsub.RetryPolicy{
        MinimumBackoff: 10 * time.Second,
        MaximumBackoff: 600 * time.Second,
    },
})
```

Admin operations are idempotent in spirit: `CreateTopic` returns `AlreadyExists` if the topic already exists. Either check first or treat `AlreadyExists` as success:

```go
if _, err := client.CreateTopic(ctx, "my-topic"); err != nil {
    if status.Code(err) != codes.AlreadyExists {
        return err
    }
}
```

## OpenTelemetry Tracing

Recent SDK versions support OpenTelemetry tracing of publishes and receives. Enable per-client:

```go
client, err := pubsub.NewClientWithConfig(ctx, "my-project", &pubsub.ClientConfig{
    EnableOpenTelemetryTracing: true,
})
```

The publisher creates a span per `Publish` call; the subscriber's callback runs inside a span linked to the publisher span via the message's tracing attributes. Standard OTel exporters then carry the trace through your usual collector.

For propagation across service boundaries, the SDK injects/extracts trace context into message attributes automatically. No manual context plumbing needed.

## Emulator and Local Testing

```bash
gcloud beta emulators pubsub start --host-port=localhost:8085
$(gcloud beta emulators pubsub env-init)
```

The emulator sets `PUBSUB_EMULATOR_HOST=localhost:8085`. The Go SDK auto-detects this and connects without auth:

```go
client, err := pubsub.NewClient(ctx, "my-project")
// Connects to emulator if PUBSUB_EMULATOR_HOST is set
```

Limitations:

- No schemas (schema admin returns errors).
- No exactly-once delivery.
- No BigQuery / Cloud Storage subscriptions.
- No IAM enforcement.

Useful for unit/integration tests of the publish/subscribe path; not a substitute for staging tests of features the emulator doesn't implement.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| New `*pubsub.Client` per request | Connection pool churn, latency spikes |
| New `*pubsub.Topic` per publish | Defeats SDK batching |
| Forgetting `Topic.Stop()` | Pending publishes dropped on exit |
| Calling `Receive` twice on the same `*pubsub.Subscription` | Panic / error |
| Returning from the callback before `Ack`/`Nack` | Lease expires, redelivery |
| Spawning a goroutine in the callback and returning | Lease stops extending; redelivery |
| Logging or external API calls before `Ack`/`Nack` decisions in a way that double-fires on retry | Side effects double — handler should be idempotent |
| Ignoring `context.Canceled` from `Receive` | Treats clean shutdown as a failure |
| Catching `Unavailable` / `DeadlineExceeded` and aggressive retry | The SDK already retried; you're amplifying the back-pressure |

## Common Pitfalls

- **`PublishSettings` and `ReceiveSettings` aren't safe to mutate after the first use.** Set once at handle creation.
- **`m.Ack()` is fire-and-forget on at-least-once subscriptions.** No success/failure signal; use `AckWithResult` on EOD if you need it.
- **`Topic.Stop()` is blocking.** Don't call it from inside a `Publish`-error handler — you can deadlock.
- **`Subscription.Exists(ctx)` calls the API.** Cache the result if you check it repeatedly.
- **The default `ReceiveSettings.MaxOutstandingBytes = 1 GiB`** is too high for many workloads. Always size to your actual message size × concurrency.
- **`pubsub.Message.Attributes` is `nil` if the message has no attributes** — check before reading.
- **`m.OrderingKey` is empty string for unordered messages** — don't confuse with `nil`.
- **Context propagation through `Receive` callbacks** uses the SDK's per-message context, which is cancelled when the outer context is cancelled. Long-running handlers must respect `ctx.Done()`.
- **The emulator does NOT implement EOD or ordering reliably** — test those features against staging.

## Sources

- https://pkg.go.dev/cloud.google.com/go/pubsub
- https://cloud.google.com/pubsub/docs/publisher
- https://cloud.google.com/pubsub/docs/subscriber
- https://cloud.google.com/pubsub/docs/emulator
- https://cloud.google.com/pubsub/docs/open-telemetry-tracing
