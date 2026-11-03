# Data inventory, retention jobs and erasure runbook

Engineering templates only. Retention periods, legal bases and exceptions come from the user's privacy or legal team.

## Data inventory template

One row per field group per location. Keep it in the repository (for example `docs/data-inventory.md`) or in a data catalog, and update it in the same change that adds a field or a new destination.

| System / location | Table or path | Fields | Class | Purpose | Lawful basis (from legal) | Retention | Deletion method | Owner | Copies sent to |
|---|---|---|---|---|---|---|---|---|---|
| Main DB | `users` | email, name, phone | Personal | Account, login, support | Contract | Account life + 30 days | Erasure job | Identity team | Search index, CRM |
| Main DB | `orders` | shipping address | Personal | Fulfilment | Contract | 7 years (invoices) | Anonymize address after 90 days | Commerce team | Warehouse |
| Object storage | `uploads/avatars/` | Profile photos | Personal | Profile | Consent | Until removed or account deleted | Delete objects by user prefix | Identity team | CDN cache |
| Logs | App logs | user_id, IP | Personal | Debugging, security | Legitimate interests | 30 days | Log retention setting | Platform team | Log vendor |
| Vendor | Email service | email, name | Personal | Transactional email | Contract | Vendor policy | Vendor deletion API | Growth team | — |

Questions that find hidden copies:

- What consumes this table's change events or exports (warehouse, search, caches, ML features)?
- Which vendors receive this data (email, CRM, support desk, analytics, payment, error tracking)?
- Where do uploaded files and generated documents (invoices, exports) live?
- Do any logs, traces or error reports include request bodies?

## Batched retention job (PostgreSQL example)

Dry run first, always:

```sql
SELECT count(*) AS would_delete
FROM events
WHERE created_at < now() - interval '400 days'
  AND NOT legal_hold;
```

Then delete in batches until no rows remain, pausing between batches and watching replication lag (see postgres-operations):

```sql
WITH batch AS (
  SELECT id
  FROM events
  WHERE created_at < now() - interval '400 days'
    AND NOT legal_hold
  ORDER BY id
  LIMIT 5000
)
DELETE FROM events AS e
USING batch
WHERE e.id = batch.id;
```

Job requirements:

- A `--dry-run` flag (default on) that only reports counts per table.
- Batch size and pause as settings; stop on error and resume safely on the next run.
- Logs and metrics with counts and duration, never the deleted values.
- An alert when the job fails, or when a run would delete far more than the previous runs (a bug in the cutoff can delete everything).
- The user's explicit confirmation before the first non-dry run in production.

For time-partitioned tables, drop whole partitions instead (after confirmation):

```sql
ALTER TABLE events DETACH PARTITION events_2024_10 CONCURRENTLY;
DROP TABLE events_2024_10;
```

On PostgreSQL 14+, `CONCURRENTLY` avoids blocking queries on the parent table, but it cannot run inside a transaction block. Without it, `DETACH PARTITION` takes a strong lock on the parent `events` table for the duration.

Anonymizing instead of deleting (when the row must stay, for example for accounting):

```sql
UPDATE orders
SET shipping_name = NULL,
    shipping_address = NULL,
    shipping_phone = NULL,
    anonymized_at = now()
WHERE created_at < now() - interval '90 days'
  AND anonymized_at IS NULL;
```

Run this in batches like the delete.

## Erasure request runbook

1. **Verify identity** of the requester through the normal account channel. Never act on an email that just claims to be the user.
2. **Check exceptions** with the privacy/legal owner: legal holds, records you must keep (invoices, fraud investigations). Kept records get restricted access.
3. **Resolve identifiers**: user ID, emails, phone numbers, customer IDs in each vendor, device IDs.
4. **Delete or anonymize in every inventory location**, in an order that doesn't recreate data:
   - stop new collection (disable the account, revoke sessions and tokens);
   - main database (replicas follow);
   - files in object storage, and purge CDN caches for them;
   - search indexes and caches;
   - warehouse, data lake, ML feature stores;
   - logs, where the logging system supports deletion; otherwise rely on short retention;
   - third-party processors through their deletion APIs, recording the request IDs they return.
5. **Backups**: don't edit them. Make sure backup retention is limited, and add the user ID to a **deletion ledger** (IDs only). Any restore procedure must re-apply the ledger before the restored data is used.
6. **Verify**: run the export for the same person; it should return nothing (or only the retained exceptions).
7. **Record** the request date, what was deleted where, exceptions applied, and completion date, without copying the deleted data into the record.

## Export (access / portability) request

- Reuse the inventory: the export must cover the same locations as erasure.
- Produce machine-readable output (JSON or CSV) grouped by category, with field names a person can understand.
- Deliver it through the authenticated account (a time-limited download link), not as an email attachment.
- Exclude other people's personal data (for example, other participants in a conversation) and internal secrets.
- Log that an export happened, not its contents.

## Tests to add

- A test user created through every feature that stores personal data, then erased: assert that every table, index and file location no longer has their data.
- The export for a fully populated test user includes every inventory location.
- Retention job: rows just older than the cutoff are deleted, rows just newer are kept, rows under legal hold are kept, and dry-run deletes nothing.
- Logging: a request containing an email and a token produces log lines without either.
