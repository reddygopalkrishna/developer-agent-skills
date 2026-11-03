# Resilience Pattern Details

Language-neutral pseudo-code. Use a well-tested library for your stack when one exists, and use this file to check that the library is configured to behave this way.

## Retry with capped exponential backoff and full jitter

```text
function call_with_retry(op, deadline, max_attempts = 3, base = 100ms, cap = 2s):
    for attempt in 0 .. max_attempts - 1:
        remaining = deadline - now()
        if remaining <= 0:
            raise DeadlineExceeded

        try:
            return op(timeout = min(per_attempt_timeout, remaining))
        except error as e:
            if not is_transient(e) or attempt == max_attempts - 1:
                raise e
            if not retry_budget.try_acquire():
                raise e                                  # budget spent: don't amplify load

            delay = random_uniform(0, min(cap, base * 2^attempt))
            if e.retry_after is set:
                delay = max(delay, e.retry_after)
            if now() + delay >= deadline:
                raise e
            sleep(delay)

function is_transient(e):
    return e is ConnectionReset or ConnectTimeout
        or e.http_status in {429, 502, 503, 504}
        or e.grpc_code in {UNAVAILABLE, RESOURCE_EXHAUSTED}
        # DEADLINE_EXCEEDED / read timeout: only when the operation is idempotent
```

Notes:

- Call this only for idempotent operations, or for operations that carry an idempotency key.
- `per_attempt_timeout` is smaller than the overall deadline, so that a retry still fits.

## Retry budget (token bucket)

```text
retry_budget:
    tokens = max_tokens                 # e.g. 10
    on every successful request:   tokens = min(max_tokens, tokens + ratio)   # e.g. ratio 0.1
    on every failed request:       tokens = tokens - 1
    try_acquire():                 return tokens > max_tokens / 2
```

This permits retries while most calls succeed, and stops them automatically during an outage. gRPC's retry throttling works on the same idea.

## Circuit breaker

```text
state = CLOSED; window = sliding window of last N calls (or last T seconds)

function call(op):
    if state == OPEN:
        if now() < open_until:
            raise CircuitOpen                         # fail fast; caller uses fallback
        state = HALF_OPEN; trial_calls = 0

    if state == HALF_OPEN and trial_calls >= max_trial_calls:
        raise CircuitOpen
    if state == HALF_OPEN: trial_calls += 1

    try:
        result = op()
        record(success)
        if state == HALF_OPEN and trial_successes >= required_successes:
            state = CLOSED; window.reset()
        return result
    except error as e:
        if counts_as_failure(e):                       # timeouts, 5xx, connection errors; NOT caller 4xx
            record(failure)
            if state == HALF_OPEN:
                trip()
            elif window.calls >= minimum_calls and window.failure_rate >= threshold:
                trip()
        raise e

function trip():
    state = OPEN; open_until = now() + cool_down       # e.g. 10-60s
    emit_metric("circuit_open", dependency)
```

Typical starting settings: a window of 20-100 calls, a minimum of 10-20 calls, a 50% failure-rate threshold, and a 30 s cool-down. Tune them from real traffic. Slow calls (over a latency threshold) can also count as failures.

## Bulkhead (per-dependency concurrency limit)

```text
semaphores = { "payments": Semaphore(20), "recommendations": Semaphore(5) }

function call_dependency(name, op):
    if not semaphores[name].try_acquire(timeout = 0):     # or a very short wait
        raise Rejected                                    # fail fast instead of queueing
    try:
        return op()
    finally:
        semaphores[name].release()
```

Size each limit as roughly (target throughput x p99 latency) of that dependency, plus headroom.

## Load shedding at the entry point

```text
in_flight = AtomicCounter()

middleware(request):
    if in_flight.value >= max_concurrency:
        if request.priority == LOW or in_flight.value >= hard_limit:
            return 503 with Retry-After: 1
    in_flight.increment()
    try:     return handle(request)
    finally: in_flight.decrement()
```

Also drop requests whose deadline has already passed before you do any work on them.

## Idempotent consumer

```sql
CREATE TABLE processed_messages (
    consumer     text        NOT NULL,
    message_id   text        NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer, message_id)
);
```

```text
function handle(message):
    begin transaction
        inserted = INSERT INTO processed_messages (consumer, message_id)
                   VALUES ('billing', message.id)
                   ON CONFLICT DO NOTHING          -- dialect-specific; use your DB's equivalent
        if inserted == 0:
            commit; ack(message); return           -- duplicate: already applied
        apply_side_effects(message)                -- same transaction, same database
    commit
    ack(message)                                   -- ack only after commit
```

If the side effect is in another system (an external API), pass `message.id` to that system as its idempotency key instead.

Clean up old rows on a schedule, keeping them longer than the broker's maximum redelivery window.

## Transactional outbox

```sql
CREATE TABLE outbox (
    id           uuid PRIMARY KEY,
    aggregate_id text NOT NULL,
    event_type   text NOT NULL,
    payload      jsonb NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz
);
CREATE INDEX outbox_unpublished ON outbox (created_at) WHERE published_at IS NULL;
```

```text
# Write path: one local transaction
begin transaction
    UPDATE orders SET status = 'paid' WHERE id = :id
    INSERT INTO outbox (id, aggregate_id, event_type, payload)
           VALUES (new_uuid(), :id, 'order.paid', :payload)
commit

# Relay (polling variant); several relays can run safely with SKIP LOCKED
loop:
    begin transaction
        rows = SELECT * FROM outbox
               WHERE published_at IS NULL
               ORDER BY created_at
               LIMIT 100
               FOR UPDATE SKIP LOCKED              -- PostgreSQL 9.5+, MySQL 8.0+
        for row in rows:
            broker.publish(topic_for(row.event_type), key = row.aggregate_id,
                           value = row.payload, headers = { "message-id": row.id })
        UPDATE outbox SET published_at = now() WHERE id IN (rows.ids)
    commit
    sleep(poll_interval) if rows is empty
```

- Publishing happens before the commit, so a crash can publish an event twice. That is expected; consumers dedupe on `message-id`.
- Use the aggregate ID as the partition key so events for one entity stay in order.
- The change-data-capture variant (for example Debezium reading the database log) avoids polling, but you run more infrastructure.

## Saga (orchestrated)

```text
steps = [
    (reserve_inventory, release_inventory),
    (charge_payment,    refund_payment),
    (create_shipment,   cancel_shipment),
]

function run_saga(saga_id, order):
    completed = load_completed_steps(saga_id)          # persisted so the saga survives restarts
    for (action, compensate) in steps:
        if action in completed: continue
        try:
            action(order, idempotency_key = saga_id + action.name)
            persist_step_done(saga_id, action)
        except PermanentFailure:
            for (done_action, done_compensate) in reversed(completed_steps(saga_id)):
                retry_until_success(done_compensate, order,
                                    idempotency_key = saga_id + done_compensate.name)
            mark_saga(saga_id, "compensated")
            return
        # transient failures: retry the step with backoff; don't compensate yet
    mark_saga(saga_id, "completed")
```

- Persist saga state. An in-memory saga is lost on deploy.
- Every action and compensation is idempotent and keyed.
- Some steps cannot be undone (an email sent). Put them last, after the pivot step that decides success.

## Graceful shutdown

```text
on SIGTERM:
    readiness = FAILING                    # load balancer starts removing this instance
    sleep(drain_delay)                     # e.g. 5-10s; endpoint removal is asynchronous
    server.stop_accepting()
    consumers.stop_polling()
    wait_for(in_flight == 0, timeout = shutdown_timeout)   # must fit inside the grace period
    consumers.commit_offsets_or_nack_unfinished()
    flush(telemetry); close(pools)
    exit(0)
```

In Kubernetes: the `preStop` hook (or the app's own sleep) + drain + cleanup must finish within `terminationGracePeriodSeconds` (default 30), or the process is killed with SIGKILL.

Make sure the process actually receives SIGTERM. In containers, a shell-form `CMD` or a wrapper script may not forward signals. Use exec-form `CMD`, `exec` in scripts, or a minimal init (for example tini or `docker run --init`).
