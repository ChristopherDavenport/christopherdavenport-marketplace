# Operations — Quotas, Monitoring, DLT, Seek, Cost

The Pub/Sub control plane is mostly self-managed, but a handful of operational decisions — quota awareness, the right monitoring metrics, dead-letter topic IAM, and replay strategy — separate teams that handle Pub/Sub incidents from teams that don't. Each is small in isolation; missing any one can turn a transient spike into a multi-hour outage.

This reference covers quotas, the metrics that actually matter, dead-letter topic setup, `Seek` and snapshot recipes, and cost levers.

## Quotas

Pub/Sub publishes per-region quotas; the defaults are generous but not unlimited.

| Resource | Default per region | Where it bites |
|---|---|---|
| Publish throughput | Many GiB/s | Burst publishers without batching |
| Subscriber pull throughput | Many GiB/s | Same |
| Topics per project | 10,000 | Per-tenant topic patterns |
| Subscriptions per project | 10,000 | Same |
| Schemas per project | 10,000 | Schema-per-revision misuse |
| Message size | 10 MiB | Big payloads — use GCS pointer pattern instead |
| Attributes per message | 100 | Misusing attributes for payload |
| Attribute key/value size | 256 / 1024 bytes | Same |
| Ack deadline | 600s max | Long-processing handlers — split work |
| Subscription retention | 31 days max | Long-paused subscribers — they expire silently |
| Snapshot lifetime | 7 days from creation | Replay windows |

Always check the live quota page — limits change. Per-region throughput is shared with other tenants and can be tighter in newer regions.

When quota is hit, the SDK retries with backoff. Persistent `RESOURCE_EXHAUSTED` errors mean either you need a quota increase request, or you're using Pub/Sub for something it isn't sized for (e.g., a per-tenant topic explosion).

## Metrics That Matter

Cloud Monitoring publishes many Pub/Sub metrics; these are the ones that catch real incidents.

### Subscription Health

| Metric | What it tells you | Alert when |
|---|---|---|
| `subscription/oldest_unacked_message_age` | Age of the oldest un-acked message | Climbs above your SLO (e.g., 5 min). Means subscriber can't keep up |
| `subscription/num_undelivered_messages` | Backlog size | Grows continuously — subscriber slower than publisher |
| `subscription/ack_message_count` | Messages acked per second | Drops to zero — subscriber crashed or stalled |
| `subscription/expired_ack_deadlines_count` | Lease expirations | Climbing — handlers slower than ack deadline + extension |
| `subscription/retry_message_count` | Redeliveries | Spike correlates with handler errors or transient outages |
| `subscription/dead_letter_message_count` | Messages forwarded to DLT | Any non-zero value → poison messages need triage |

The two most important alerts are:

- `oldest_unacked_message_age > threshold` — your SLO ceiling on processing latency.
- `num_undelivered_messages` derivative > 0 sustained — backlog is growing.

### Publisher Health

| Metric | What it tells you |
|---|---|
| `topic/send_message_operation_count` | Publish RPC count — drops to zero means publisher stopped |
| `topic/send_request_count` | Publish requests — should track message count divided by batch size |
| `topic/byte_cost` | Bytes published (used for billing) |

### Per-Region

Pub/Sub metrics are per-region. A subscriber in `us-central1` sees its region's view; a publisher in `us-east1` may publish into any region. Look at the topic's `messageStoragePolicy` to know where messages live.

## Dead-Letter Topics

A DLT is a regular topic that receives messages a subscription failed to deliver after `MaxDeliveryAttempts` (5–100). Set up:

```bash
# 1. Create the DLT
gcloud pubsub topics create my-dlt

# 2. Create a subscription on the DLT for triage
gcloud pubsub subscriptions create my-dlt-sub --topic=my-dlt

# 3. Attach the DLT to the source subscription
gcloud pubsub subscriptions update my-source-sub \
  --dead-letter-topic=my-dlt \
  --max-delivery-attempts=10

# 4. Grant IAM — both grants are required
PROJECT_NUMBER=$(gcloud projects describe my-project --format='value(projectNumber)')
SVC=service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com

gcloud pubsub topics add-iam-policy-binding my-dlt \
  --member="serviceAccount:${SVC}" --role=roles/pubsub.publisher

gcloud pubsub subscriptions add-iam-policy-binding my-source-sub \
  --member="serviceAccount:${SVC}" --role=roles/pubsub.subscriber
```

Without those two IAM grants, Pub/Sub silently fails to forward — messages keep retrying past `MaxDeliveryAttempts` and you'll see no DLT activity. This is the single most common DLT misconfiguration.

The Pub/Sub service account is `service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com`. It exists in any project that has used Pub/Sub.

### DLT Patterns

A DLT subscription is just a regular subscription — your triage tool can be:

- A pull subscriber that logs each dead-lettered message to a structured store for inspection.
- A push subscription to a Cloud Function that opens a ticket.
- A BigQuery subscription that lands every dead-lettered message in a table for SQL analysis.

Messages on the DLT carry attributes describing the original delivery:

- `googclient_deliveryattempt` — number of attempts before forwarding
- `CloudPubSubDeadLetterSourceDeliveryCount` — same data via attribute
- `CloudPubSubDeadLetterSourceSubscription` — name of the source subscription
- `CloudPubSubDeadLetterSourceTopicPublishTime` — original publish time

Use these to correlate DLT entries back to the source.

### Republishing from a DLT

Once you've fixed the bug, you may want to re-publish DLT'd messages to the original topic. There's no built-in tool; write a one-off script:

```go
err := dltSub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    result := sourceTopic.Publish(ctx, &pubsub.Message{
        Data:       m.Data,
        Attributes: m.Attributes,  // preserve original attributes
    })
    if _, err := result.Get(ctx); err != nil {
        m.Nack()
        return
    }
    m.Ack()
})
```

Run with `MaxOutstandingMessages = 10` to throttle. Be careful: republishing a DLT entry restarts the delivery-attempt counter.

## Retry Policy

Independent of DLT, the retry policy controls how aggressively Pub/Sub retries delivery between attempts:

```bash
gcloud pubsub subscriptions update my-sub \
  --min-retry-delay=10s \
  --max-retry-delay=600s
```

Default backoff is fast (~10s minimum). For push subscriptions or subscribers that struggle under retry pressure, raise these.

`maxDeliveryAttempts` (DLT) and the retry policy compose: each attempt waits per the retry policy, and after `MaxDeliveryAttempts` the message goes to the DLT.

## Seek and Snapshots

`Seek` rewinds (or fast-forwards) a subscription's cursor. Two flavors:

### Seek to Timestamp

```bash
gcloud pubsub subscriptions seek my-sub \
  --time=2026-04-01T00:00:00Z
```

```go
err := sub.SeekToTime(ctx, time.Date(2026, 4, 1, 0, 0, 0, 0, time.UTC))
```

Re-delivers all messages with `publishTime >= the seek time`, subject to retention. If `retainAckedMessages` is false on the subscription, only un-acked messages within retention are replayed.

To replay messages that were already acked, you need either `retainAckedMessages=true` (set before the messages were acked) or a snapshot taken before the ack.

### Snapshots

A snapshot freezes the un-acked state of a subscription at a point in time. Useful as a "save point" before a risky deploy:

```bash
gcloud pubsub snapshots create pre-deploy-snapshot --subscription=my-sub

# Deploy. If something breaks:
gcloud pubsub subscriptions seek my-sub --snapshot=pre-deploy-snapshot
```

Properties:

- A snapshot expires 7 days after creation. Configurable up to the topic's `messageRetentionDuration` (default 7 days, max 31 days).
- Snapshots are bound to a subscription; you can't apply a snapshot taken on `sub-A` to `sub-B`.
- After `Seek` to a snapshot, the subscription redelivers everything that was un-acked at snapshot time, plus everything published since.
- Idempotency in the consumer is essential — replayed messages have the same `m.ID` and your dedup table protects you (though `Seek` is exactly the case where you might want to bypass dedup to re-process).

### Seek Forward

`Seek` to a future timestamp acks every un-delivered message up to that point. Useful for "skip the backlog" recovery when a subscriber has fallen so far behind that re-processing is impossible:

```bash
gcloud pubsub subscriptions seek my-sub --time=$(date -u +%FT%TZ)
```

Use with caution — you're acknowledging messages without processing them. Document the data loss in your incident report.

## Cost Levers

Pub/Sub bills on three things:

| Component | Pricing dimension | How to control |
|---|---|---|
| Throughput | Per TiB published, per TiB delivered | Smaller messages, fewer subscriptions, batch where possible |
| Storage | Per GiB-month for retained messages | Lower `messageRetentionDuration`, don't set `retainAckedMessages` unless replay is required |
| Egress | Cross-region delivery costs more than same-region | Co-locate publishers and subscribers in the same region |

Practical optimizations:

- **Don't retain acked messages by default.** Storage cost adds up over weeks.
- **Don't keep snapshots forever.** They expire automatically, but un-needed snapshots that get extended past 7 days are pure cost.
- **Filter at the subscription, not the consumer.** A subscription filter that drops 90% of messages saves the delivery cost; a client-side discard pays it.
- **Use BigQuery subscriptions instead of a custom subscriber writing to BigQuery.** Cheaper at scale and removes a hop.
- **Batch publishes.** Per-message overhead adds up at high volume.
- **Multi-region storage policies have per-region cost.** Restrict `allowedPersistenceRegions` if your data residency allows.

## Capacity Planning

Sizing a subscriber:

1. Measure handler p99 latency.
2. Target throughput = (concurrency / p99). E.g., `MaxOutstandingMessages=100`, p99 = 200ms → ~500 msg/s ceiling per `Receive` call.
3. If you need more, raise `NumGoroutines` (more streams) before raising `MaxOutstandingMessages` (more concurrent in-flight messages, more lease management overhead).
4. Watch `oldest_unacked_message_age`. If it climbs during normal load, you need more workers or shorter handler latency.

Sizing a publisher:

1. Measure publish rate per producer.
2. Tune `PublishSettings.CountThreshold` and `DelayThreshold` so each batch contains a meaningful number of messages (e.g., 100–1000).
3. Use `BufferedByteLimit` to cap memory under burst.
4. For multi-publisher setups, share the `*pubsub.Topic` handle within a process; the SDK batches across all callers.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| Per-tenant topic with thousands of tenants | Topic-count quota; admin overhead. Use one topic with attribute filters instead |
| DLT without IAM grants | Messages retry forever; DLT stays empty |
| Treating `oldest_unacked_message_age` and `num_undelivered_messages` as the same metric | They diverge; backlog can be small but old |
| Snapshot retention "forever" by extending repeatedly | Storage cost; usually a sign the deploy gate is wrong |
| `Seek` forward to clear a backlog without recording what was dropped | Silent data loss in the incident timeline |
| No retry policy + push subscription | Default backoff is aggressive; push endpoint melts |
| `messageRetentionDuration` too short to absorb a weekend outage | Buy yourself headroom — storage is cheap relative to the cost of message loss |
| One per-region topic per business event type × 30 regions | Quota explosion; usually a single topic with attributes is the right design |

## Common Pitfalls

- **The Pub/Sub service account must exist before IAM bindings work.** It's auto-created on first Pub/Sub use; new projects may need a one-time `gcloud pubsub topics list` to trigger creation.
- **`Seek` doesn't pause the subscription.** New publishes still deliver; only the un-acked frontier moves.
- **Snapshots are per-subscription.** If you have N subscriptions on a topic and want to roll back all of them, you need N snapshots.
- **`maxDeliveryAttempts` counts only deliveries that result in a nack or lease expiration.** A successfully-acked message resets the counter for that message ID.
- **Quota errors come back as `RESOURCE_EXHAUSTED`** with a message containing the quota name. Don't retry blindly — investigate the producer.
- **DLT-forwarded messages keep their original `messageId`.** Your dedup table will treat them as already-seen if you've processed before.
- **Subscription expiration is silent.** A 31-day-quiet subscription disappears with no alert.

## Sources

- https://cloud.google.com/pubsub/quotas
- https://cloud.google.com/pubsub/docs/monitoring
- https://cloud.google.com/pubsub/docs/handling-failures
- https://cloud.google.com/pubsub/docs/replay-overview
- https://cloud.google.com/pubsub/docs/replay-message
- https://cloud.google.com/pubsub/pricing
