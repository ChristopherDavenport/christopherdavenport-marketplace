# Subscriptions — Pull, Push, BigQuery, Cloud Storage

A subscription is the durable cursor and delivery configuration for one consumer of a topic. Choosing the wrong type — or misconfiguring the ack deadline, retry policy, or push endpoint — causes the most common Pub/Sub production failures: redelivery storms, push-endpoint 500 cascades, silent message drop, and runaway backlogs.

This reference covers the four delivery types, the configuration surface common to all of them, and how to tune push endpoints and subscription filters.

## Delivery Types

| Type | Subscriber | Best for |
|---|---|---|
| **Pull** (StreamingPull) | Long-lived client running `Subscription.Receive` | Default for service-to-service consumers; the Go SDK uses StreamingPull under the hood |
| **Push** | HTTPS endpoint Pub/Sub POSTs to | Webhook integrations, Cloud Run/Functions, third-party endpoints |
| **BigQuery subscription** | A BigQuery table | Stream events directly into a table with no consumer code |
| **Cloud Storage subscription** | GCS bucket (writes batched files) | Archival, downstream batch processing, data-lake landing zone |

Pull and push deliver one message at a time per delivery; BigQuery and Cloud Storage subscriptions are managed exporters with their own batching.

You cannot change delivery type after creation. Re-create the subscription if you need to switch.

## Common Configuration

These properties apply to every subscription type:

| Property | Default | Notes |
|---|---|---|
| `ackDeadlineSeconds` | 10 | 10–600. Lease time before message is considered nacked |
| `messageRetentionDuration` | 7 days | 10 minutes to 31 days. Bounds backlog age before drop |
| `retainAckedMessages` | false | When true, acked messages are kept for replay via `Seek` |
| `expirationPolicy.ttl` | 31 days of inactivity | Subscription auto-deletes after this many days with no activity. Set to empty/unset to disable |
| `enableMessageOrdering` | false | Required to deliver ordered messages — must match publisher |
| `enableExactlyOnceDelivery` | false | Pull subscriptions only; opt in for EOD semantics |
| `filter` | empty | Server-side attribute filter; non-matching messages auto-acked |
| `deadLetterPolicy` | none | DLT name + `maxDeliveryAttempts` (5–100) |
| `retryPolicy` | minimal | `minimumBackoff` (default 10s), `maximumBackoff` (default 600s) |

> **`enableMessageOrdering` is set at the *subscription*, not in subscriber code.** It is a `SubscriptionConfig` property — created via `gcloud pubsub subscriptions create --enable-message-ordering` or `client.CreateSubscription(ctx, id, SubscriptionConfig{EnableMessageOrdering: true, ...})` in the Go SDK, and updateable via `subscription.Update(ctx, SubscriptionConfigToUpdate{...})`. There is **no separate runtime flag on the Go subscriber client** — once the subscription is configured, the server delivers per-key ordered messages and the subscriber receives them as they arrive. If you find yourself reaching for a `Subscription.EnableMessageOrdering = true` knob inside subscriber code, you are looking for something that does not exist; verify the subscription's existing config instead with `gcloud pubsub subscriptions describe SUB --format='value(enableMessageOrdering)'`. Setting it on only the publisher side (`topic.EnableMessageOrdering = true`) without matching subscription config silently disables ordering — see [delivery-guarantees.md](delivery-guarantees.md) for the both-ends inspection recipe.

## Pull Subscriptions

Created by default when no `pushConfig` is given:

```bash
gcloud pubsub subscriptions create my-sub \
  --topic=my-topic \
  --ack-deadline=30 \
  --message-retention-duration=7d \
  --enable-exactly-once-delivery
```

Go consumer:

```go
sub := client.Subscription("my-sub")
err := sub.Receive(ctx, func(ctx context.Context, m *pubsub.Message) {
    // process
    m.Ack()
})
```

The Go SDK uses **StreamingPull** internally — a long-lived bidirectional gRPC stream. Messages are delivered as they arrive; flow control is bidirectional.

You normally don't need to think about StreamingPull explicitly — it's the default. The unary `Pull` RPC exists but is rarely the right choice for production consumers.

See [references/subscribing.md](subscribing.md) for `Receive`/`ReceiveSettings` details.

## Push Subscriptions

Pub/Sub POSTs each message to your HTTPS endpoint. Your endpoint returns 2xx within the ack deadline to ack, or any non-2xx (or no response) to nack.

```bash
gcloud pubsub subscriptions create webhook-sub \
  --topic=my-topic \
  --push-endpoint=https://example.com/pubsub \
  --push-auth-service-account=pubsub-pusher@my-proj.iam.gserviceaccount.com \
  --push-auth-token-audience=https://example.com \
  --ack-deadline=30
```

The endpoint receives a JSON envelope:

```json
{
  "message": {
    "data": "base64-encoded-body",
    "attributes": {"key": "value"},
    "messageId": "...",
    "publishTime": "2026-01-01T00:00:00Z",
    "orderingKey": "..."
  },
  "subscription": "projects/.../subscriptions/webhook-sub"
}
```

### Push Authentication

Always set `--push-auth-service-account` and `--push-auth-token-audience`. Pub/Sub then signs each request with an OIDC token. Your endpoint MUST validate it:

- Verify the JWT signature against Google's public keys.
- Verify `aud` matches the configured audience.
- Verify `email` (and optionally `email_verified`) matches the configured service account.

Cloud Run and Cloud Functions validate the token automatically when you configure the endpoint with `--no-allow-unauthenticated` and grant the service account `roles/run.invoker`. For other endpoints, validate manually using a JWT library.

Without OIDC validation, your endpoint is exposed to anyone who knows the URL. Pub/Sub adds no IP allowlisting.

### Push Retry Policy

A push subscription always retries on non-2xx. Configure backoff:

```bash
gcloud pubsub subscriptions update webhook-sub \
  --min-retry-delay=10s \
  --max-retry-delay=600s
```

Without an explicit policy, Pub/Sub uses a fast retry that can overwhelm your endpoint during a partial outage.

For poison messages, attach a dead-letter topic so a permanently failing message stops retrying after N attempts:

```bash
gcloud pubsub subscriptions update webhook-sub \
  --dead-letter-topic=webhook-dlt \
  --max-delivery-attempts=10
```

See [references/operations.md](operations.md) for IAM bindings required for DLTs to actually forward.

### Push Response Time Budget

Your endpoint must respond within the ack deadline (10s default, up to 600s). Slow responses are treated as nacks and trigger redelivery. If your handler is slow:

1. Raise `ackDeadlineSeconds` (up to 600).
2. Move the work to an async worker queue and 2xx immediately.
3. Switch to a pull subscription where the SDK extends the lease automatically.

## BigQuery Subscriptions

Stream messages directly to a BigQuery table — no consumer code:

```bash
gcloud pubsub subscriptions create bq-sub \
  --topic=my-topic \
  --bigquery-table=my-project:my_dataset.my_table \
  --use-table-schema
```

Modes:

- **`--use-topic-schema`** — uses the topic's attached Pub/Sub schema (Avro/Proto) to map fields to columns. Requires a typed topic.
- **`--use-table-schema`** — maps message JSON fields to BigQuery columns by name. Requires `JSON` topic encoding (or no schema).
- **Without either** — writes the raw message body and metadata into a fixed-schema table (`subscription_name`, `message_id`, `publish_time`, `data`, `attributes`).

The Pub/Sub service account needs `roles/bigquery.dataEditor` on the dataset; without it, messages back up on the subscription.

`--write-metadata` adds Pub/Sub metadata columns alongside the schema mapping. `--drop-unknown-fields` silently discards JSON fields that don't match the table schema (otherwise the message goes to the DLT).

## Cloud Storage Subscriptions

Batch messages to GCS files:

```bash
gcloud pubsub subscriptions create gcs-sub \
  --topic=my-topic \
  --cloud-storage-bucket=my-archive-bucket \
  --cloud-storage-file-prefix=events/ \
  --cloud-storage-file-suffix=.jsonl \
  --cloud-storage-max-bytes=10MB \
  --cloud-storage-max-duration=300s
```

Files are flushed when **either** `max-bytes` or `max-duration` is hit. Output formats: `--cloud-storage-output-format=text` (one message body per line) or `--cloud-storage-output-format=avro` (typed Avro records).

The Pub/Sub service account needs `roles/storage.objectCreator` on the bucket. Same pattern as BigQuery — missing IAM causes silent backlog growth.

## Subscription Filters

Server-side filter on message attributes (not body):

```bash
gcloud pubsub subscriptions create us-sub \
  --topic=events \
  --message-filter='attributes.region = "us"'
```

Filtered-out messages are **automatically acked** and never delivered. This is cheaper than client-side filtering because:

- The subscriber pays no flow-control budget for filtered messages.
- Backlog metrics reflect only messages this subscription cares about.
- The publisher pays no per-subscription delivery cost for the filtered set.

Filter expression syntax (subset of CEL):

```
attributes.region = "us"
attributes.priority != "low"
attributes:eventType
hasPrefix(attributes.path, "/users/")
NOT (attributes.region = "eu") AND attributes.priority = "high"
```

The filter is set at creation and **cannot be modified later**. To change a filter, create a new subscription and migrate consumers.

## Ack Deadline

The ack deadline is the time Pub/Sub waits between delivery and the deadline before considering a message un-acked and eligible for redelivery.

| Setting | Behavior |
|---|---|
| Pull subscription | SDK extends lease automatically while message is in callback (up to `MaxExtension`) |
| Push subscription | Endpoint must respond 2xx within `ackDeadlineSeconds` |
| Default | 10 seconds |
| Max | 600 seconds (10 minutes) |

For pull subscriptions, prefer leaving `ackDeadlineSeconds` at 10–60s and rely on SDK auto-extension. Long initial deadlines mean a crashed worker holds messages for the full window before they redeliver.

For push, set the deadline to your endpoint's p99 response time plus a buffer.

## Expiration Policy

By default, a subscription with no activity for 31 days is automatically deleted. "Activity" includes any consumer connection, ack, or modify-ack-deadline call.

Disable for long-quiet subscriptions:

```bash
gcloud pubsub subscriptions update my-sub --expiration-period=never
```

This bites surprisingly often: a subscription used only during incident replay, or for a paused service, vanishes silently.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| Push endpoint without OIDC validation | Anyone with the URL can post fake messages |
| Push endpoint that does heavy work synchronously | Slow responses → nack → redelivery storm |
| Pull subscription with no flow-control tuning under high message size | Subscriber OOMs because default `MaxOutstandingBytes` (1 GiB) is too high for the workload |
| Filter on body content (not possible) | Filters apply to attributes only; encode classification into attributes at publish time |
| Changing the filter expression by editing `gcloud subscriptions update` | Filter cannot be updated; needs subscription recreation |
| BigQuery subscription with no `--drop-unknown-fields` and an evolving topic | Schema-mismatched messages go to DLT (or get stuck) |
| Default `expiration-period=31d` on a subscription used only during failover drills | Subscription disappears between drills |
| Setting `enableMessageOrdering` on subscription but not publisher (or vice versa) | Ordering silently disabled |

## Common Pitfalls

- **Push subscriptions need both `--push-auth-service-account` AND IAM.** Granting the service account `roles/run.invoker` on a Cloud Run service is separate from the push config.
- **Filter expressions must use exact-match, not LIKE.** `attributes.region = "us-central1"` works; partial match needs `hasPrefix`/`hasSuffix` functions.
- **BigQuery subscription writes are at-least-once into BigQuery too.** Duplicates can land in the table — pair with a primary key + dedup query, or accept duplicates.
- **`messageRetentionDuration` does NOT extend a message's life past the topic's retention.** The topic-level setting is the upper bound.
- **Re-creating a subscription with the same name resets the cursor.** Old un-acked messages are gone; consumer starts from "now."
- **Enabling exactly-once on an existing subscription requires no consumer-side change** for ack semantics, but ack latency rises and `MaxExtension` should be reviewed.

## Sources

- https://cloud.google.com/pubsub/docs/subscriber
- https://cloud.google.com/pubsub/docs/subscription-properties
- https://cloud.google.com/pubsub/docs/push
- https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions
- https://cloud.google.com/pubsub/docs/bigquery
- https://cloud.google.com/pubsub/docs/cloudstorage
- https://cloud.google.com/pubsub/docs/filtering
- https://cloud.google.com/pubsub/docs/handling-failures
