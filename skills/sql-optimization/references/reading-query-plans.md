# Reading query plans

## PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.id, o.total
FROM   orders o
WHERE  o.customer_id = 42
ORDER  BY o.created_at DESC
LIMIT  20;
```

Example output (shortened):

```
Limit  (cost=0.43..25.10 rows=20 width=16) (actual time=0.031..0.090 rows=20 loops=1)
  Buffers: shared hit=24
  ->  Index Scan Backward using orders_customer_created_idx on orders o
        (cost=0.43..1530.22 rows=1241 width=16) (actual time=0.030..0.085 rows=20 loops=1)
        Index Cond: (customer_id = 42)
        Buffers: shared hit=24
Planning Time: 0.120 ms
Execution Time: 0.110 ms
```

### How to read it

- The plan is a tree. Indented nodes feed their parent. Read from the innermost nodes outward.
- `cost=startup..total` is the planner's estimate in arbitrary units. Use it to compare plans, not as time.
- `rows=` inside the first parentheses is the **estimate**; `rows=` inside `actual` is what happened, **per loop**.
- `actual time=first..last` is in milliseconds, **per loop**. Multiply by `loops` for the node's total. A node showing 0.05 ms with `loops=20000` costs a second.
- `Buffers: shared hit` means pages found in shared memory; `read` means pages fetched from disk or the OS cache. A large `read` count on a hot query points to IO.
- `Planning Time` vs `Execution Time`: very high planning time can come from many partitions or very complex queries.
- Time in a parent includes its children. To find the expensive node, subtract the children's time.

### Scan nodes

| Node | Meaning | Worry when |
|---|---|---|
| Seq Scan | Reads the whole table | The table is large and few rows survive the filter |
| Index Scan | Walks the index, then fetches each row from the table | Many rows are returned in random heap order (a Bitmap scan or Seq Scan may be better) |
| Index Only Scan | Answers from the index alone | `Heap Fetches` is high, meaning the visibility map is stale and the table needs VACUUM |
| Bitmap Index Scan + Bitmap Heap Scan | Collects matching row locations, then reads the pages in order | `Recheck Cond` removes many rows, or `lossy` blocks appear (work_mem too small for the bitmap) |

### Join nodes

| Node | Good for | Worry when |
|---|---|---|
| Nested Loop | Small outer side with an indexed inner side | The outer side is large (check `loops` on the inner node) |
| Hash Join | Larger unsorted inputs | `Batches` > 1 on the Hash node, meaning it spilled to disk (work_mem) |
| Merge Join | Both inputs already sorted on the join key | An explicit Sort was added just to feed it |

### Other nodes

- `Sort`: check `Sort Method`. `quicksort  Memory: ...` is fine; `external merge  Disk: ...` spilled to disk. Fix with an index that provides the order, or (carefully) a larger `work_mem` for that query.
- `HashAggregate` / `GroupAggregate`: grouping. Watch for disk spills in the details.
- `Gather` / `Gather Merge`: parallel query. `Workers Launched` lower than `Workers Planned` means the server ran out of parallel workers.
- `Memoize` (PostgreSQL 14+): caches inner lookups of a nested loop. Check its hit and miss counts.
- `Materialize`: buffers an inner input to re-scan it.
- `Limit`: stops early, but only if the node below it produces rows in the right order without sorting everything first.

### Red flags checklist

- [ ] Estimated rows differ from actual rows by 10× or more on any node. The planner chose based on wrong numbers: run `ANALYZE`, raise statistics targets, add extended statistics.
- [ ] `Rows Removed by Filter` is large compared with the rows returned. The index covers only part of the predicate.
- [ ] Seq Scan on a large table inside a Nested Loop (runs once per outer row).
- [ ] `Sort Method: external merge`.
- [ ] Hash `Batches` greater than 1.
- [ ] High `loops` on an expensive inner node.
- [ ] `Heap Fetches` close to the row count on an Index Only Scan.
- [ ] `shared read` dominates `shared hit` on a query that runs constantly.

### Useful options

- `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` shows output columns and schema-qualified names.
- `EXPLAIN (ANALYZE, BUFFERS, SETTINGS)` (PostgreSQL 12+) lists non-default planner settings that affected the plan.
- `EXPLAIN (FORMAT JSON)` output can be pasted into a plan visualiser for large plans.
- `SET track_io_timing = on;` (needs the right privileges) adds IO timing to `BUFFERS` output.

## MySQL: `EXPLAIN` and `EXPLAIN ANALYZE`

### Classic `EXPLAIN` columns (estimates only)

| Column | Read it as |
|---|---|
| `type` | Access type, best to worst: `system`, `const`, `eq_ref`, `ref`, `range`, `index`, `ALL`. `ALL` is a full table scan. `index` is a full index scan, which is often no better |
| `possible_keys` | Indexes the optimizer considered |
| `key` | The index actually chosen (NULL means none) |
| `key_len` | Bytes of the index used, showing how many columns of a composite index are used |
| `rows` | Estimated rows to examine |
| `filtered` | Estimated percent of those rows that survive the WHERE |
| `Extra` | Details; see below |

### `Extra` values

| Value | Meaning |
|---|---|
| `Using index` | Covering index: answered from the index alone. Good |
| `Using where` | Rows are filtered after being read. Fine if few are read |
| `Using index condition` | Index condition pushdown: part of the filter runs inside the index. Usually good |
| `Using filesort` | An extra sort step. Costly on large row sets; an index in the ORDER BY order avoids it |
| `Using temporary` | An internal temporary table, often for GROUP BY / DISTINCT / UNION. Costly on large sets |
| `Using join buffer (hash join)` | Hash join (8.0.18+), used when no index serves the join |

### `EXPLAIN ANALYZE` (MySQL 8.0.18+)

```sql
EXPLAIN ANALYZE
SELECT id, total FROM orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;
```

Output is a tree like:

```
-> Limit: 20 row(s)  (cost=... rows=20) (actual time=0.05..0.09 rows=20 loops=1)
    -> Index lookup on orders using orders_customer_created_idx (customer_id=42) (reverse)
         (cost=... rows=1241) (actual time=0.05..0.08 rows=20 loops=1)
```

- As in PostgreSQL, `actual time` is per loop in milliseconds (first row..all rows), and `rows` after `actual` is per loop. Multiply by `loops`.
- Compare estimated `rows` with actual `rows` to spot bad statistics. Fix with `ANALYZE TABLE` or histograms.
- `EXPLAIN ANALYZE` runs the query. Wrap data-changing statements in a transaction you roll back, and ask before running it on production.
- `EXPLAIN FORMAT=TREE` (8.0.16+) shows the same tree without running the query.

## Comparing before and after

1. Save the full plan text before the change.
2. Make one change (index, rewrite, statistics).
3. Run the same query with the same parameters several times so caches are in a similar state. Compare the warm timings and the buffer or row counts, not a single cold run.
4. Check that the node you targeted changed the way you expected. A faster total from a different, unexpected plan may not hold for other parameter values.
5. Try at least one "bad" parameter value (the most common tenant, the largest customer). Skewed data is where plans flip.
