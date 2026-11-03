# Event Schema Evolution

Producers and consumers deploy independently, and old events stay in topics and archives. A schema change is safe only if every combination of old/new producer and old/new consumer that can occur still works.

## Compatibility vocabulary

These are the modes used by schema registries such as Confluent Schema Registry (other registries use similar terms; check yours):

| Mode | Guarantee | Deploy order |
| --- | --- | --- |
| BACKWARD | Consumers on the new schema can read data written with the previous schema | Upgrade consumers first, then producers |
| FORWARD | Consumers on the previous schema can read data written with the new schema | Upgrade producers first, then consumers |
| FULL | Both backward and forward | Any order |
| `*_TRANSITIVE` | The guarantee holds against all earlier versions, not just the last one | Same as the base mode |
| NONE | No checks | Avoid for shared topics |

Recommendation: use FULL_TRANSITIVE (or at least BACKWARD_TRANSITIVE) for integration events, because replays and slow consumers read old data long after the schema changed.

## Change safety table

| Change | Typically safe? | Notes |
| --- | --- | --- |
| Add an optional field with a default | Yes | The standard way to evolve. Consumers must ignore fields they don't know |
| Add a required field with no default | No | Consumers on the new schema can't read old events |
| Remove a field | Only if no consumer reads it, and (Avro) it had a default | Deprecate first; remove after all consumers stopped reading it |
| Rename a field | No | Add the new field, populate both, migrate consumers, then remove the old one |
| Change a field's type | No (assume breaking) | Some formats allow specific widenings; don't rely on it for shared contracts |
| Change units or meaning (cents to dollars, local time to UTC) | **No, even though the schema check passes** | Registries can't detect semantic changes; use a new field name |
| Add an enum value | Only if consumers handle unknown values | Old consumers may crash on an unexpected value; define a fallback |
| Change the partition/ordering key | No | Breaks per-key ordering for in-flight data |
| Change the event type name or topic | No | It's a new contract; run both during migration |

## Format-specific rules

### Avro

- Every field that may be added or removed needs a `default`.
- Optional fields are unions with `null` first and `"default": null`.
- Readers resolve by field name; aliases can support renames but are easy to get wrong. Prefer add-new-field-then-remove.

### Protobuf

- Never change a field's number. Never reuse a removed field's number or name: mark them `reserved`.
  ```proto
  message OrderPlaced {
    reserved 4;
    reserved "legacy_total";
    string order_id = 1;
    int64 total_cents = 2;
    string currency = 3;
  }
  ```
- Adding fields is safe; old readers skip unknown fields.
- Renaming a field is wire-compatible for binary encoding but breaks the JSON mapping and generated code; treat it as breaking for shared contracts.
- For enums, keep a zero value meaning "unspecified" (proto3 convention) and handle unknown values.

### JSON Schema

- Consumers must tolerate unknown properties ("tolerant reader"). A consumer schema with `additionalProperties: false` turns every added field into a breaking change.
- Registry compatibility checks for JSON Schema are subtler than for Avro/Protobuf (open vs closed content models); read your registry's docs before relying on them.

## Procedure for a breaking change

When a change can't be made compatible:

1. Create a new event version or type (`OrderPlaced` v2, or a new topic).
2. Producers publish both old and new versions (from the outbox) during the migration.
3. Migrate consumers one by one to the new version; track who still consumes the old one.
4. Stop publishing the old version only after all consumers moved and the replay/retention window you care about has passed.
5. Announce the timeline to consuming teams in advance. Sending such announcements is outward-facing; draft them for the user to send.

## CI checks

- Store schemas in the repo (or a registry) and check compatibility in CI before merge: registries expose compatibility-check APIs, and Protobuf linters/breaking-change detectors (for example `buf breaking`) catch field-number and type changes.
- Keep sample events (old versions) as test fixtures and run consumer tests against them, so replays of old data stay covered.
