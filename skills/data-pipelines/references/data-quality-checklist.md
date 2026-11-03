# Data Quality Checklist

Run these checks against the staging data before publishing. Each query below should return zero rows (or a value inside the threshold) for the check to pass. SQL dialects vary; adjust date arithmetic and parameter syntax for your warehouse.

## Volume

Compare today's row count with recent runs:

```sql
SELECT
  (SELECT COUNT(*) FROM staging_orders) AS today_rows,
  (SELECT AVG(n) FROM (
     SELECT COUNT(*) AS n
     FROM orders
     WHERE order_date >= :run_date - INTERVAL '7' DAY
       AND order_date <  :run_date
     GROUP BY order_date
   ) recent) AS avg_recent_rows;
```

Fail if `today_rows` is zero or outside an agreed band around `avg_recent_rows`. Set the band from observed history (weekday/weekend patterns differ), not a guess.

## Completeness

```sql
SELECT COUNT(*) AS missing_customer
FROM staging_orders
WHERE customer_id IS NULL;
```

Required columns: block on any null. Optional columns: warn when the null rate jumps compared with history.

## Uniqueness of the grain

```sql
SELECT order_id, COUNT(*) AS copies
FROM staging_orders
GROUP BY order_id
HAVING COUNT(*) > 1;
```

Always blocking. Duplicates at the grain double-count every downstream metric.

## Validity

```sql
SELECT status, COUNT(*)
FROM staging_orders
WHERE status NOT IN ('placed', 'shipped', 'delivered', 'returned', 'cancelled')
GROUP BY status;

SELECT COUNT(*) AS bad_amounts
FROM staging_orders
WHERE amount < 0 OR amount > 1000000;
```

## Referential integrity

```sql
SELECT o.order_id
FROM staging_orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;
```

If dimensions load later than facts, either order the tasks so dimensions finish first, or route orphan rows to a quarantine table and reprocess them.

## Freshness

```sql
SELECT MAX(event_time) AS newest_event
FROM staging_events;
```

Fail if `newest_event` is older than the SLA (for example more than 2 hours behind the interval end). Freshness checks on sources catch silent upstream outages before your pipeline publishes stale data.

## Reconciliation with the source

```sql
-- In the warehouse
SELECT SUM(amount) FROM staging_orders WHERE order_date = :run_date;
-- In the source system, for the same interval
SELECT SUM(amount) FROM orders WHERE created_at >= :start AND created_at < :end;
```

Small, explained differences (late data, time-zone boundaries) can be a warning; unexplained differences block.

## dbt example

```yaml
models:
  - name: orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: status
        tests:
          - accepted_values:
              values: ['placed', 'shipped', 'delivered', 'returned', 'cancelled']
      - name: customer_id
        tests:
          - relationships:
              to: ref('customers')
              field: customer_id
```

Newer dbt versions also accept `data_tests:` in place of `tests:` and have changed how test arguments are written. Check the docs for the installed version. Use the `severity` config (`error` or `warn`) to decide which tests block.

## Severity and alerting

| Check | Default severity |
| --- | --- |
| Grain uniqueness | Block |
| Required column nulls | Block |
| Zero rows | Block |
| Volume outside band | Block for critical tables, warn otherwise |
| Referential integrity | Block or quarantine |
| Validity (unknown enum value) | Warn, then block once the list is stable |
| Freshness | Block publishing; alert the source owner |
| Reconciliation drift | Warn below an agreed tolerance, block above it |

An alert should say: which table and partition, which check, observed vs expected values, a sample of failing rows (without PII), the owner, and a runbook link.

## Ownership

- Every check has an owner who is paged or notified.
- Every warning is reviewed periodically; a warning nobody reads should be removed or promoted to blocking.
- When a check fires because expectations changed (a new status value, real growth), update the check in the same change that explains why.
