# Interleaving — Locality, Limits, and the Irreversible Choice

Interleaving (`INTERLEAVE IN PARENT`) physically co-locates child rows next to their parent row on disk. When done right it makes parent-child joins local (no cross-split RPC) and lets `ON DELETE CASCADE` clean up children for free. When done wrong it locks you into a permanent schema decision that you cannot undo.

## What Interleaving Actually Does

Spanner stores rows in primary-key order. An interleaved child shares its parent's leading key columns, so each child row sits immediately after its parent in the key space:

```
Singers/Singer:1
Singers/Singer:1/Albums/Album:1
Singers/Singer:1/Albums/Album:2
Singers/Singer:1/Albums/Album:1/Songs/Song:1
Singers/Singer:1/Albums/Album:1/Songs/Song:2
Singers/Singer:2
Singers/Singer:2/Albums/Album:1
...
```

Consequences:

- A parent and all its descendants land in the same split (until they exceed the split-size threshold).
- Joins on the shared key columns are **local** — no fan-out across the cluster.
- Deleting the parent with `ON DELETE CASCADE` deletes the children atomically with no separate query.
- A query for "all rows for this parent" is a single contiguous scan.

## Syntax

```sql
CREATE TABLE Singers (
  SingerId  INT64 NOT NULL,
  FirstName STRING(1024),
  LastName  STRING(1024),
) PRIMARY KEY (SingerId);

CREATE TABLE Albums (
  SingerId  INT64 NOT NULL,    -- must match parent's leading key columns
  AlbumId   INT64 NOT NULL,    -- additional key column unique within the parent
  Title     STRING(MAX),
) PRIMARY KEY (SingerId, AlbumId),
  INTERLEAVE IN PARENT Singers ON DELETE CASCADE;

CREATE TABLE Songs (
  SingerId  INT64 NOT NULL,    -- inherits all parent key columns, in order
  AlbumId   INT64 NOT NULL,
  SongId    INT64 NOT NULL,
  Title     STRING(MAX),
) PRIMARY KEY (SingerId, AlbumId, SongId),
  INTERLEAVE IN PARENT Albums ON DELETE CASCADE;
```

Rules the parser enforces:

- The child's primary key **must start with all of the parent's primary key columns, in the same order, with the same types**.
- A row cannot exist without its parent — insert order matters: parent first, child second.
- Maximum interleaving depth: **7 levels** (Singers → Albums → Songs → ...).
- `ON DELETE CASCADE` propagates parent deletes; `ON DELETE NO ACTION` (the default) makes parent-with-children deletes fail.

## When to Interleave (vs. Foreign Key)

Interleave when **all three** are true:

1. Children almost always read with their parent (or with siblings under the same parent).
2. The parent-children combined size stays well under a split (Spanner splits aggressively, but a "hot" parent with millions of children can still cause issues).
3. You're confident this relationship is stable — you won't want to re-parent the children to a different table later.

Use a **foreign key** instead when:

- Children are read independently of the parent (different access pattern).
- Children dramatically outnumber parents and dominate the storage (the parent's split keeps growing).
- You might restructure the relationship later. Foreign keys can be added/dropped; interleaving cannot be undone.
- You need referential integrity *across* tables that have unrelated primary key shapes.

```sql
-- Foreign key alternative — relationship without locality
CREATE TABLE Reviews (
  ReviewId STRING(36) NOT NULL DEFAULT (NEW_UUID()),
  AlbumId  INT64 NOT NULL,
  Body     STRING(MAX),
  CONSTRAINT FK_AlbumReview FOREIGN KEY (AlbumId)
    REFERENCES Albums (AlbumId),
) PRIMARY KEY (ReviewId);
```

## The Irreversibility Warning

> "After you interleave a table, it's permanent. You can't undo the interleaving."

You cannot:

- Convert an interleaved table into a non-interleaved table.
- Re-parent an interleaved table under a different parent.
- Add or remove key columns to/from any existing table (interleaved or not).

The only path is: create a new table with the desired shape, copy data, drop the old table. That's a multi-hour migration on any non-trivial dataset, with downtime considerations.

**Treat interleaving as a contract you sign once.** Discuss with the team and validate access patterns *before* the table holds production data.

## Splits and Locality Limits

Spanner splits a key range automatically when:

- The range exceeds approximately a few hundred MB, or
- The range gets hot (the load-based splitter sees concentrated traffic).

Interleaved children share a split with their parent **until** the combined data exceeds the split threshold, at which point Spanner inserts a split between rows. A split between an interleaved parent and its children is allowed but undermines the locality benefit.

**Rule of thumb:** if a single parent will accumulate more than ~100 MB of children, interleaving still works but you stop benefiting from local joins (the children spill across splits). At that scale, evaluate whether the parent really needs to "own" the children physically.

## Interleaved Indexes

Indexes can also be interleaved. The leading columns of the index must match the parent's key columns:

```sql
CREATE INDEX SongsBySingerAlbumName
  ON Songs (SingerId, AlbumId, Title)
  INTERLEAVE IN Albums;
```

Use when:

- The query filters by parent key (`WHERE SingerId = @s AND AlbumId = @a AND Title LIKE ...`).
- The index would otherwise have a hotspot on the leading column.

The index entries co-locate with the parent's data, mirroring the table's locality. See [indexes.md](indexes.md) for more.

## Joining Interleaved Tables

The query optimizer recognizes parent-child joins on the shared key columns and executes them **locally** within each split:

```sql
SELECT s.LastName, a.Title
FROM Singers s
JOIN Albums a ON s.SingerId = a.SingerId
WHERE s.SingerId = @id;
```

No network fan-out, no shuffle. Compare with the same join across non-interleaved tables, which fan out across splits and merge results.

## Anti-Patterns

| Pattern | Why it's wrong |
|---|---|
| Interleaving a table whose children are queried independently | You pay locality cost without using it; a foreign key is reversible |
| Interleaving more than 7 levels deep | Schema creation fails; redesign the hierarchy |
| Interleaving when the parent has millions of children that exceed split size | Splits separate parent from children → no locality benefit |
| `ON DELETE NO ACTION` (the default) and then trying to delete a parent with children | Delete fails; either set `CASCADE` or delete children first |
| Forgetting that the child's PK must start with parent's PK columns | DDL parse error |
| Adding a non-interleaved index on a child's monotonic column | Index hotspot — interleave the index too, or shard the column |

## Worked Patterns

### Time-series with bounded child count

Sensor readings up to ~1k per device — fine to interleave:

```sql
CREATE TABLE Devices (
  DeviceId STRING(36) NOT NULL DEFAULT (NEW_UUID()),
  ...
) PRIMARY KEY (DeviceId);

CREATE TABLE DeviceReadings (
  DeviceId  STRING(36) NOT NULL,
  Timestamp TIMESTAMP NOT NULL,
  Value     FLOAT64 NOT NULL,
) PRIMARY KEY (DeviceId, Timestamp DESC),
  INTERLEAVE IN PARENT Devices ON DELETE CASCADE;
```

Per-device queries are local; deleting a device deletes its readings.

### Time-series with unbounded child count

Same shape but each device produces millions of rows. Don't interleave — the parent's split swells. Use a foreign key (or no FK) and a `ShardId`-prefixed key on the child:

```sql
CREATE TABLE DeviceReadings (
  ShardId   INT64 NOT NULL
    AS (MOD(FARM_FINGERPRINT(DeviceId), 256)) STORED,
  DeviceId  STRING(36) NOT NULL,
  Timestamp TIMESTAMP NOT NULL,
  Value     FLOAT64 NOT NULL,
) PRIMARY KEY (ShardId, DeviceId, Timestamp DESC);
```

### Multi-tenant with interleaving

```sql
CREATE TABLE Customers (
  CustomerId INT64 NOT NULL,
  ...
) PRIMARY KEY (CustomerId);

CREATE TABLE Orders (
  CustomerId INT64 NOT NULL,
  OrderId    INT64 NOT NULL,
  ...
) PRIMARY KEY (CustomerId, OrderId),
  INTERLEAVE IN PARENT Customers ON DELETE CASCADE;
```

`CustomerId` as the shared leading key gives natural per-tenant locality. Compatible with the multi-tenant pattern in [schema-design.md](schema-design.md).

## Common Pitfalls

- **"I'll interleave it now and remove the interleave later if needed."** You can't. Decide before production data exists.
- **Inserting a child before its parent.** Returns `FAILED_PRECONDITION`. Insert the parent in the same transaction.
- **`ON DELETE NO ACTION` set unintentionally.** A "delete this customer" call fails as soon as they have any orders. Choose `CASCADE` deliberately.
- **Interleaving for a relationship that's actually many-to-many.** Interleaving requires one parent. Use a join table with foreign keys instead.
- **Forgetting interleave constraints when adding columns.** You can add non-key columns freely; you cannot add key columns to either parent or child.

## Sources

- https://cloud.google.com/spanner/docs/schema-and-data-model
- https://cloud.google.com/spanner/docs/schema-design
