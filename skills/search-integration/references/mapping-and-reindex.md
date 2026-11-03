# Mapping, Queries and Zero-Downtime Reindex

Examples use the Elasticsearch/OpenSearch REST API in the console format (`METHOD /path` followed by a JSON body). Client libraries expose the same operations. Check your engine's version docs for any setting you rely on; most of what follows has been stable for several major versions.

## Example index with an explicit mapping

Create versioned indices (`products_v1`, `products_v2`, ...) and always query through an alias (`products`).

```json
PUT /products_v1
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "analysis": {
      "normalizer": {
        "lowercase_normalizer": {
          "type": "custom",
          "filter": ["lowercase", "asciifolding"]
        }
      }
    }
  },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "id":          { "type": "keyword" },
      "tenant_id":   { "type": "keyword" },
      "title": {
        "type": "text",
        "analyzer": "english",
        "fields": { "keyword": { "type": "keyword", "ignore_above": 256 } }
      },
      "description": { "type": "text", "analyzer": "english" },
      "brand":       { "type": "keyword", "normalizer": "lowercase_normalizer" },
      "tags":        { "type": "keyword" },
      "price":       { "type": "scaled_float", "scaling_factor": 100 },
      "in_stock":    { "type": "boolean" },
      "created_at":  { "type": "date" },
      "internal_notes": { "type": "keyword", "index": false }
    }
  }
}
```

```json
POST /_aliases
{
  "actions": [
    { "add": { "index": "products_v1", "alias": "products" } }
  ]
}
```

Check analyzer output before committing to it:

```json
GET /products_v1/_analyze
{
  "field": "title",
  "text": "Running Shoes for Women"
}
```

## Indexing with external versioning

Use the database primary key as `_id` and a monotonically increasing row version (or update timestamp in milliseconds) as the external version. An older event then cannot overwrite a newer document.

```json
PUT /products/_doc/prod_123?version=1730630400123&version_type=external
{
  "id": "prod_123",
  "tenant_id": "t_42",
  "title": "Trail running shoe",
  "price": 89.99,
  "in_stock": true,
  "created_at": "2026-10-01T12:00:00Z"
}
```

A version conflict response (HTTP 409) on such a write means a newer version is already indexed. Treat it as success, not as an error to retry.

Bulk indexing (newline-delimited JSON; the body must end with a newline):

```text
POST /_bulk
{ "index": { "_index": "products", "_id": "prod_123", "version": 1730630400123, "version_type": "external" } }
{ "id": "prod_123", "tenant_id": "t_42", "title": "Trail running shoe", "price": 89.99, "in_stock": true }
{ "delete": { "_index": "products", "_id": "prod_456" } }
```

After every bulk call, check the top-level `errors` field. If it is `true`, inspect each item's `status` and `error`, retry transient failures (429, 503) with backoff, and dead-letter the rest.

## Query example: filters plus scored text

```json
GET /products/_search
{
  "size": 20,
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "running shoes",
            "fields": ["title^3", "description"],
            "fuzziness": "AUTO"
          }
        }
      ],
      "should": [
        { "match_phrase": { "title": { "query": "running shoes", "boost": 2 } } }
      ],
      "filter": [
        { "term":  { "tenant_id": "t_42" } },
        { "term":  { "in_stock": true } },
        { "range": { "price": { "lte": 100 } } }
      ]
    }
  },
  "aggs": {
    "brands": { "terms": { "field": "brand", "size": 20 } }
  }
}
```

- The tenant filter is added by the server for every query. Never accept it from the client.
- `term` queries on `keyword` fields match exactly; on `text` fields they usually match nothing because the text was analyzed.

## Deep pagination with a point in time

Open a point in time (PIT), page with `search_after`, and close the PIT when done.

```json
POST /products/_pit?keep_alive=2m
```

```json
GET /_search
{
  "size": 50,
  "pit": { "id": "<pit id from the previous call>", "keep_alive": "2m" },
  "query": { "bool": { "filter": [ { "term": { "tenant_id": "t_42" } } ] } },
  "sort": [
    { "created_at": "desc" },
    { "id": "asc" }
  ]
}
```

For the next page, repeat the request with `"search_after": [<sort values of the last hit>]`. The last sort field must be unique (here `id`) so pages never skip or repeat documents.

```json
DELETE /_pit
{ "id": "<pit id>" }
```

The PIT endpoints above are Elasticsearch's. OpenSearch uses different paths (`/_search/point_in_time`) and request fields; check its docs. Older clusters without PIT support use the scroll API for exports.

## Zero-downtime reindex runbook

Use this when changing a field type, analyzer or other mapping that can't be updated in place.

**Before you start:** confirm with the user which environment you are working in. Steps 7 and 9 change what production users see or delete data and need explicit confirmation.

1. **Create the new index** `products_v2` with the new settings and mapping. Do not attach the alias yet.
2. **Speed up the initial load** on the new index only:

   ```json
   PUT /products_v2/_settings
   { "index": { "refresh_interval": "-1", "number_of_replicas": 0 } }
   ```

3. **Note a start time `T`** (or the current outbox/CDC position), then **load all documents**. Prefer rebuilding from the database with the normal indexer code, which applies the new mapping logic. If the old index has complete `_source` and no transformation is needed, the reindex API is faster:

   ```json
   POST /_reindex?wait_for_completion=false
   {
     "source": { "index": "products_v1" },
     "dest":   { "index": "products_v2", "version_type": "external" }
   }
   ```

   Track progress with `GET /_tasks/<task id>`.

4. **Catch up** on changes made since `T`: replay outbox events or rows with `updated_at >= T` into `products_v2`. External versioning makes the replay safe to overlap. Alternatively, configure the indexer to write to both indices from `T` onward.
5. **Restore normal settings** and refresh:

   ```json
   PUT /products_v2/_settings
   { "index": { "refresh_interval": "1s", "number_of_replicas": 1 } }
   ```

   ```json
   POST /products_v2/_refresh
   ```

6. **Validate:** compare `GET /products_v1/_count` and `GET /products_v2/_count` (they should match, allowing for in-flight writes), run the judgment list against `products_v2` directly, and spot-check a few known documents. Wait for cluster health to be green with replicas assigned.
7. **Swap the alias atomically** (needs confirmation in production):

   ```json
   POST /_aliases
   {
     "actions": [
       { "remove": { "index": "products_v1", "alias": "products" } },
       { "add":    { "index": "products_v2", "alias": "products" } }
     ]
   }
   ```

   Both actions apply together, so queries never see a missing alias.

8. **Point the indexer** at the alias (or at `products_v2` only) and stop writing to `products_v1`. Watch search latency, error rates and zero-result rate.
9. **Keep `products_v1`** for a rollback window (swap the alias back if needed). Delete it later, only after explicit confirmation:

   ```json
   DELETE /products_v1
   ```

## Quick diagnostics

| Symptom | Check |
| --- | --- |
| A document doesn't match an obvious query | `_analyze` the query text and the field; check `text` vs `keyword`; check filters |
| Wrong ranking for a query | `explain: true` on the search, compare scores of the expected and actual top hits |
| Recent writes not visible | Refresh interval, indexer lag (oldest unprocessed outbox row), bulk item errors |
| Index count lower than database count | Bulk errors, missed deletes or inserts, failed catch-up after a reindex; run the rebuild |
| Writes rejected with a read-only block | Disk flood-stage watermark reached; free disk space, then clear the block per your version's docs |
| Cluster yellow | Unassigned replicas (often too few nodes for the replica count) |
| Cluster red | Unassigned primary shards: data is unavailable; investigate before changing anything |
