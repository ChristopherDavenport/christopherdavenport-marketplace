# Topics & Schemas — Creation, Retention, Schema Evolution

A topic is a thin durable buffer with two important knobs: **how long messages are retained** and **whether publishes are validated against a schema**. Both are set at topic creation and can be widened later, but tightening them (shorter retention, stricter schema) requires care because the change applies to subsequent publishes only.

This reference covers topic configuration, the Avro/Protobuf schema model, and how to evolve a schema without breaking subscribers.

## Topic Properties

| Property | Default | Notes |
|---|---|---|
| `messageRetentionDuration` | 7 days | Min 10 minutes, max 31 days. Applies even to messages never delivered to any subscription. |
| `messageStoragePolicy.allowedPersistenceRegions` | All Google Cloud regions | Restrict for data residency; rejects publishes that would store outside |
| `kmsKeyName` | None (Google-managed) | CMEK for encryption-at-rest |
| `schemaSettings.schema` | None | Reference to a `projects/.../schemas/...` resource |
| `schemaSettings.encoding` | — | `JSON` or `BINARY` (BINARY only for Proto/Avro) |
| `schemaSettings.firstRevisionId` / `lastRevisionId` | None | Pin a revision range for validation |
| `ingestionDataSourceSettings` | None | For Pub/Sub topics that ingest from Kafka, Confluent Cloud, AWS Kinesis, etc. |

Create with gcloud:

```bash
gcloud pubsub topics create my-topic \
  --message-retention-duration=7d \
  --message-storage-policy-allowed-regions=us-central1,us-east1
```

Create with Go:

```go
topic, err := client.CreateTopicWithConfig(ctx, "my-topic", &pubsub.TopicConfig{
    RetentionDuration: 7 * 24 * time.Hour,
    MessageStoragePolicy: pubsub.MessageStoragePolicy{
        AllowedPersistenceRegions: []string{"us-central1", "us-east1"},
    },
})
```

## Topic-Level Retention vs Subscription-Level Retention

These are independent and additive:

- **Topic retention** keeps messages on the topic itself. Messages are kept for at least `messageRetentionDuration` after publish, even if every subscription has acked them. This is what enables `Seek` to a timestamp before the subscription was created.
- **Subscription retention** (`messageRetentionDuration` on the subscription, default 7 days) keeps **un-acked** messages on the subscription. This is what bounds how long a buggy subscriber can fall behind.
- **`retainAckedMessages: true`** on a subscription keeps acked messages within the retention window so `Seek` can replay them. Costs storage; turn off when not needed.

If you want `Seek` to work on a brand-new subscription that didn't exist when a message was published, you need topic-level retention. Otherwise the subscription only sees messages published after its creation.

## Schemas

A schema validates the structure of message bodies at publish time. Pub/Sub supports **Avro** and **Protocol Buffers**. Schemas live as their own GCP resources and topics reference them.

### Creating a Schema

Protobuf:

```bash
gcloud pubsub schemas create order-v1 \
  --type=PROTOCOL_BUFFER \
  --definition-file=order.proto
```

Avro:

```bash
gcloud pubsub schemas create order-v1 \
  --type=AVRO \
  --definition-file=order.avsc
```

Go:

```go
schemaClient, err := pubsub.NewSchemaClient(ctx, projectID)
defer schemaClient.Close()

avscBytes, _ := os.ReadFile("order.avsc")
schema, err := schemaClient.CreateSchema(ctx, "order-v1", pubsub.SchemaConfig{
    Type:       pubsub.SchemaAvro,
    Definition: string(avscBytes),
})
```

### Attaching a Schema to a Topic

```bash
gcloud pubsub topics create orders \
  --schema=order-v1 \
  --message-encoding=binary
```

Go:

```go
topic, err := client.CreateTopicWithConfig(ctx, "orders", &pubsub.TopicConfig{
    SchemaSettings: &pubsub.SchemaSettings{
        Schema:   "projects/my-project/schemas/order-v1",
        Encoding: pubsub.EncodingBinary,
    },
})
```

`Encoding` choices:

- **`BINARY`** — wire-format Proto or Avro binary. Smallest, fastest, but opaque outside a code path that has the schema. Use for service-to-service.
- **`JSON`** — JSON encoding of the Proto/Avro structure. Larger, but readable in logs and consumable from non-typed subscribers (e.g., a BigQuery subscription).

You cannot change encoding after topic creation.

### Schema Revisions

Schemas are versioned. Each `gcloud pubsub schemas commit` (or `CommitSchema` API call) creates a new revision; the schema resource has `firstRevisionId` and `lastRevisionId`. The topic's `schemaSettings` can pin to a single revision or accept a range.

Commit a new revision:

```bash
gcloud pubsub schemas commit order-v1 \
  --type=AVRO \
  --definition-file=order-v2.avsc
```

Pin a topic to revisions:

```bash
gcloud pubsub topics update orders \
  --schema-first-revision-id=abc123 \
  --schema-last-revision-id=def456
```

Publishes are validated against any revision in the pinned range. Subscribers should be prepared to read any revision in the range — this is what compatibility modes guarantee.

### Compatibility Modes

When you commit a new revision, Pub/Sub checks the diff against the previous revision under the topic's compatibility rules. Pub/Sub uses the standard schema-evolution rules from the Avro/Proto specs:

| Mode | What's allowed | When to use |
|---|---|---|
| `BACKWARD` (default for additive) | New revision can read old data — adding optional fields, adding enum values | Most common; safe for "old subscribers, new data" |
| `FORWARD` | Old revision can read new data — removing optional fields | "New subscribers, old data" — rare |
| `FULL` | Both `BACKWARD` and `FORWARD` | Strictest single-step; safe both directions |
| `BACKWARD_TRANSITIVE` / `FORWARD_TRANSITIVE` / `FULL_TRANSITIVE` | Same but checked against **every** prior revision, not just the last | Long-lived schemas where any historical subscriber may still exist |

Compatibility is checked at **commit** time. If the diff fails the rule, the commit is rejected; the existing schema stays the active one.

There is no "compatibility mode" knob on the topic itself — Pub/Sub applies the rules baked into Avro/Proto. To force stricter checks, pin the topic to specific revisions and use a separate review process before committing.

## Evolving a Schema Without Breaking Subscribers

The safe pattern:

1. **Add optional fields, never remove or rename required ones.** Default values keep old subscribers reading new messages.
2. **Commit the new revision** under the schema name. The commit fails if the diff breaks `BACKWARD` compatibility.
3. **Verify subscribers can decode the new revision** in staging. The library decoding (e.g., `proto.Unmarshal`) ignores unknown fields by default but does not fill in defaults the same way across languages.
4. **Roll out subscriber code that uses the new fields.** Old subscribers continue working because they ignore the unknown fields.
5. **Roll out publishers that emit the new fields.** Now both sides know about them.
6. **Optionally pin the topic to the new revision range** once all publishers and subscribers are upgraded.

Reverse for a removal: ensure no subscriber depends on a field, then commit a revision that drops it (this often fails `BACKWARD` and requires `FORWARD` mode or a fresh schema).

### Rejected Publishes

If a publish fails schema validation, the API returns `INVALID_ARGUMENT` and the message is not stored. The publisher's `PublishResult.Get` returns the error.

## Topic Naming and Lookup

Topic names are case-sensitive and must match `projects/PROJECT/topics/NAME` format internally; the `NAME` portion follows GCP resource-name rules (3–255 chars, must start with a letter, alphanumerics and `- _ . ~ + %` allowed).

In Go you usually use the short name and the client builds the full name:

```go
topic := client.Topic("orders")           // implicit project from client
topic := client.TopicInProject("orders", "other-project")
```

`client.Topic` does not call the API — it just builds a handle. Use `topic.Exists(ctx)` to check, or attempt a publish and handle `NotFound`.

## Ingestion Topics

Pub/Sub topics can ingest directly from external sources (no client publish needed):

- **Kafka** (Confluent Cloud, MSK)
- **AWS Kinesis Data Streams**
- **Cloud Storage** (file watch)

Configure via `ingestionDataSourceSettings` at topic creation. The topic still has subscriptions; only the publishing side is replaced. Useful for migrating off Kafka or fanning out an existing stream into BigQuery via a Pub/Sub BigQuery subscription.

## Anti-Patterns

| Pattern | Problem |
|---|---|
| Setting `messageRetentionDuration` to the minimum (10 min) "to save cost" | A 30-minute outage in your subscriber loses all messages |
| Schema with no compatibility plan | Publisher and subscriber drift; old subscribers crash on new fields |
| Renaming a Proto field by changing field name (same number) | Wire-compatible but breaks JSON encoding and any name-based deserialization |
| Removing a Proto field number | Old messages still in the queue contain the field — decode errors on consumer |
| `BINARY` encoding with no consumer-side schema management | Messages are opaque; debugging requires the schema, which lives only in GCP |
| Treating subscription retention and topic retention as the same thing | They serve different purposes; `Seek` to before subscription creation needs topic retention |
| Setting `retainAckedMessages: true` on every subscription "for safety" | Unbounded storage cost growth; only set when replay is a real requirement |

## Common Pitfalls

- **Schema validation is on the topic, not the subscription.** A subscriber receives whatever the topic accepted — if your topic schema is permissive, your subscriber sees the variety.
- **Avro `null` union order matters.** Avro distinguishes `["null", "string"]` (default null) from `["string", "null"]` (default string) — the first is the Pub/Sub convention for optional fields.
- **Proto `oneof` fields don't have defaults.** A subscriber compiled against an older `oneof` set cannot represent newer cases — choose `oneof` carefully.
- **Encoding can't change after creation.** If you need both `JSON` (for BigQuery sub) and `BINARY` (for service-to-service), create two topics or accept JSON everywhere.
- **Schemas are project-scoped.** A schema in project A cannot be referenced from a topic in project B; create the schema in the consuming project, or duplicate it.
- **The schema's `revisionCreateTime` is what `Seek` and pinning operate on, not your commit message.** Tag revisions externally if you need human-meaningful version names.

## Sources

- https://cloud.google.com/pubsub/docs/admin
- https://cloud.google.com/pubsub/docs/schemas
- https://cloud.google.com/pubsub/docs/commit-schemas
- https://cloud.google.com/pubsub/docs/replay-overview
- https://cloud.google.com/pubsub/docs/ingestion-overview
