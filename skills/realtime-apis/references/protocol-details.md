# Protocol Details

## Message envelope

Use one envelope for every message in both directions:

```json
{
  "v": 1,
  "type": "order.updated",
  "id": "1730650000123-42",
  "ts": "2026-11-03T14:20:00.123Z",
  "data": { "orderId": "ord_123", "status": "shipped" }
}
```

- `v`: schema version. Add fields freely; bump only for breaking changes and support both versions during rollout.
- `type`: what happened, in past tense for events.
- `id`: unique and increasing within a stream, so clients can resume and deduplicate.
- `ts`: server time, used to measure delivery lag.
- Client-to-server messages also carry a client-generated `requestId` so the server can send an acknowledgement or error that refers to it.

## SSE wire format

```text
id: 1730650000123-42
event: order.updated
data: {"orderId":"ord_123","status":"shipped"}

: ping

retry: 5000
```

- Each event ends with a blank line.
- Multi-line data uses several `data:` lines.
- Lines starting with `:` are comments, which are useful as heartbeats.

## WebSocket close codes

| Code | Meaning | Client action |
| --- | --- | --- |
| 1000 | Normal closure | Don't reconnect unless the app still needs the stream |
| 1001 | Going away (server shutting down, page leaving) | Reconnect with jitter |
| 1006 | Abnormal closure (no close frame; set by the client library, never sent) | Reconnect with backoff |
| 1008 | Policy violation (for example auth expired or revoked) | Re-authenticate before reconnecting |
| 1009 | Message too big | Fix the client; don't retry the same message |
| 1011 | Server error | Reconnect with backoff |
| 1012 | Service restart | Reconnect with jitter |
| 1013 | Try again later | Reconnect with a longer backoff |
| 4000-4999 | Reserved for application use | Define and document your own |

## Client reconnect logic (browser, WebSocket)

```js
function connect({ url, getTicket, onMessage }) {
  let attempt = 0;
  let lastId = null;
  let socket;

  async function open() {
    const ticket = await getTicket(); // short-lived, from an authenticated HTTP call
    const params = new URLSearchParams({ ticket });
    if (lastId) params.set("lastId", lastId);
    socket = new WebSocket(`${url}?${params}`);

    socket.onopen = () => { attempt = 0; };
    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (lastId !== null && msg.id <= lastId) return; // already applied
      lastId = msg.id;
      onMessage(msg);
    };
    socket.onclose = (event) => {
      if (event.code === 1000) return;
      const base = Math.min(30000, 1000 * 2 ** attempt++);
      const delay = Math.random() * base; // full jitter
      setTimeout(open, delay);
    };
  }

  open();
  return () => socket && socket.close(1000);
}
```

Notes:

- The `msg.id <= lastId` comparison assumes IDs sort correctly as strings or numbers. Use fixed-width or numeric IDs, or compare a separate sequence number.
- On close code 1008, refresh the session before calling `open()` again.
- Pause reconnecting while the page is hidden or offline (`document.visibilityState`, the `online` event) if battery or server load matters.

## Server-side resume

- Keep a per-stream replay buffer of recent messages (for example the last N messages or last M minutes) in a store all instances can read.
- On connect with `lastId` (or the SSE `Last-Event-ID` header):
  - If `lastId` is still in the buffer, send everything after it, then switch to live messages.
  - If it is older than the buffer, send a `resync` message telling the client to refetch full state over HTTP.
- Subscribe to live messages **before** reading the buffer, then drop duplicates by ID, so nothing published in between is lost.

## Load testing

- Test the target number of concurrent connections, not only requests per second.
- Include reconnect storms: drop all connections at once and watch CPU, memory, auth endpoint load and recovery time.
- Use a tool that supports WebSockets or SSE (for example k6, Artillery or Gatling) and check its docs for the current protocol support.
