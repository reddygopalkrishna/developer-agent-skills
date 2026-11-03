# Modeling for document, key-value and wide-column stores

Relational modeling starts from the entities. NoSQL modeling starts from the **queries**. Before designing anything, write the access-pattern table with the user:

| # | Access pattern | Inputs | Returns | Frequency | Consistency needed |
|---|---|---|---|---|---|
| 1 | Get order with its lines | order id | 1 order + lines | High | Strong |
| 2 | List a customer's recent orders | customer id, date range | up to 50 orders | High | Eventual OK |
| 3 | ... | | | | |

If the list is long, changes often, or is dominated by ad-hoc analytical queries, question whether a relational database (possibly with a `jsonb` column) is the better fit. Say so to the user.

## Document stores (MongoDB and similar)

### Embed or reference

| Embed when | Reference when |
|---|---|
| Read together almost every time | Read independently |
| Owned by the parent (deleted with it) | Shared by many parents |
| Bounded and small (a few addresses, an order's lines) | Unbounded (comments, events, log entries) |
| Updated together with the parent | Updated often on its own, by different writers |

- MongoDB documents have a 16 MB maximum size. Long before that, large documents make every read and update expensive.
- **Never let an array grow without bound** inside a document (all comments on a post, all events for a device). Put those in their own collection, keyed by the parent id, or use the bucket pattern.

### Useful patterns

- **Subset:** embed the most recent or most important N children (the last 10 reviews) and keep the full set in a separate collection.
- **Extended reference:** copy the few fields you always display (a customer's name) next to the reference, and accept updating them when the source changes. Decide whether the copy is a snapshot (keep the old value) or must follow changes (needs an update path).
- **Bucket:** group time-series points into one document per entity per time window (per device per hour) instead of one document per point.
- **Computed:** maintain totals and counters on write when they are read far more often than written.
- **Schema versioning:** store a `schemaVersion` field and migrate documents lazily on read or in batches.

### Integrity

- Use schema validation (`$jsonSchema` validators on the collection) for required fields and types. Without it, every document shape the code has ever written lives forever.
- Create unique indexes for business uniqueness; the database will not infer it.
- Multi-document transactions exist, but they cost more and have limits. Prefer designs where one business operation updates one document.
- Create an index for every query pattern in the table, and check with `explain()` that queries use them.

## DynamoDB

### Core rules

- Every access pattern must be served by a `GetItem`, or a `Query` on the table or a secondary index. A `Scan` reads the whole table: avoid it outside of rare batch jobs.
- **Partition key:** high cardinality and evenly accessed (customer id, order id). A low-cardinality key (status, date) creates hot partitions.
- **Sort key:** enables range queries and ordering within a partition (`ORDER#2026-01-15#1234`).
- The maximum item size is 400 KB. Large blobs belong in object storage, with a pointer in the item.
- Global secondary indexes (GSIs) are eventually consistent, and each one adds write cost. Local secondary indexes must be created with the table.

### Single-table design (when it fits)

Store several entity types in one table with generic key attributes, so related items share a partition and one `Query` fetches them together:

| PK | SK | Entity | Other attributes |
|---|---|---|---|
| `CUSTOMER#42` | `PROFILE` | Customer | name, email |
| `CUSTOMER#42` | `ORDER#2026-01-15#1001` | Order | total, status |
| `CUSTOMER#42` | `ORDER#2026-02-03#1002` | Order | total, status |
| `ORDER#1001` | `LINE#1` | Order line | sku, qty |

- "Customer with recent orders" becomes one `Query` on `PK = CUSTOMER#42`, with `SK` `begins_with ORDER#` and a descending scan order.
- Add GSIs with overloaded keys (`GSI1PK`, `GSI1SK`) for alternate access patterns, such as orders by status.
- Store an explicit `type` attribute on every item, for readability and for streams consumers.

Single-table design is worth it when access patterns are known, stable and latency-critical. **Several tables are fine** when access patterns are few, when entities are rarely fetched together, when the team is new to DynamoDB, or when analytics needs a clean export. Do not force single-table design just because it is fashionable.

### Practices

- Model one-to-many relationships with the parent id as the partition key and the child id in the sort key.
- Use conditional writes (`attribute_not_exists(PK)`) for uniqueness and optimistic locking (a `version` attribute).
- Use TTL attributes for expiring data (sessions, temporary tokens). Deletion by TTL is not immediate.
- Use DynamoDB Streams (or a change data capture equivalent) to maintain derived views, instead of writing to several places from the application.
- Check the current DynamoDB documentation for limits (transaction size, GSI count, throughput) before relying on a specific number.

## Wide-column stores (Cassandra, ScyllaDB)

- Design **one table per query**. Duplicating data across tables is normal and expected.
- The partition key decides which node holds the data. Keep partitions bounded in size: add a time bucket to the partition key for time series (`(sensor_id, day)`).
- Clustering columns define the sort order inside a partition. Queries must follow the key order.
- Avoid `ALLOW FILTERING` in production queries; it means the table does not fit the query.
- Deletes create tombstones; heavy delete patterns (queues) perform badly. Use TTLs and time-bucketed tables instead.

## Key-value stores and caches (Redis and similar)

- Treat them as a cache or for ephemeral data (sessions, rate limits, locks with expiry) unless persistence and failover have been deliberately configured and tested.
- Namespace keys (`app:tenant:42:user:7`), set a TTL on everything that is a cache, and plan for the cache being empty (a cold start must not overload the database).
- Keep the source of truth in a durable database.

## Checklist

- [ ] The access-pattern table exists, and every row maps to a key lookup or an indexed query.
- [ ] No unbounded arrays or partitions.
- [ ] Partition keys are high-cardinality and evenly accessed.
- [ ] Every duplicated field has an owner and an update path.
- [ ] Uniqueness and required fields are enforced by the store (unique indexes, conditional writes, schema validation).
- [ ] Item and document sizes stay well below the store's limits.
- [ ] There is a plan for schema evolution (version field, lazy or batched migration).
