# Effects decision guide

An effect is an escape hatch for synchronizing a component with something outside React. Ask: "Which external system does this effect keep in sync?" If there is no answer, the effect should not exist.

## "I want to..." → "Do this"

| I want to... | Do this instead of an effect |
|---|---|
| Compute a value from props or state | Calculate it during render. `useMemo` only if measured as slow |
| Filter or sort a list for display | Calculate during render |
| Reset all state when a prop changes (a different user, item or route) | Give the component `key={id}` |
| Adjust one piece of state when a prop changes | Usually derive it instead. If you truly must, store the previous prop in state and compare during render, not in an effect |
| Respond to a click, submit or other user action (POST, navigate, toast, analytics event) | Do it in the event handler |
| Tell the parent something changed | Call the parent's callback in the same event handler that changed the state, or lift the state up |
| Share logic between two handlers | Extract a plain function and call it from both |
| Initialize something once for the whole app | Run it at module level, or guard with a module-level flag (effects run twice in Strict Mode in development) |
| Subscribe to an external store or browser API | `useSyncExternalStore` |
| Fetch data | A data library or framework loader. Only fall back to an effect with race handling (below) |
| Read layout (size, position) before the browser paints | `useLayoutEffect`, sparingly |

## Legitimate effects

- Connecting to a chat room, WebSocket or event source and disconnecting in cleanup.
- Adding and removing browser event listeners (`resize`, `keydown` on `window`, `visibilitychange`).
- Controlling a non-React widget (a map, a chart library, a video player) via a ref.
- Starting and clearing timers or intervals.
- Logging an "impression" when a screen is shown, if the analytics needs it on display rather than on a user action.

## Fetching in an effect (only when no library or loader is available)

Handle races and unmounts, or responses arrive out of order and overwrite newer data:

```tsx
function useUser(userId: string) {
  const [state, setState] = useState<
    { status: "loading" } | { status: "success"; user: User } | { status: "error"; error: Error }
  >({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    fetch(`/api/users/${encodeURIComponent(userId)}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((user: User) => setState({ status: "success", user }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return; // superseded or unmounted
        setState({ status: "error", error: error instanceof Error ? error : new Error(String(error)) });
      });
    return () => controller.abort();
  }, [userId]);

  return state;
}
```

This still lacks caching, deduplication, retries and background refresh. That is why a data library is the default.

## Subscribing to external stores

```ts
import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

export function useOnlineStatus() {
  return useSyncExternalStore(
    subscribe,             // stable function defined outside the component
    () => navigator.onLine, // client snapshot
    () => true              // server snapshot, used during SSR and hydration
  );
}
```

The snapshot function must return the same value (or the same object reference) when nothing changed, or React re-renders forever.

## Fixing dependency problems

Never silence `react-hooks/exhaustive-deps`. Change the code so the dependencies are honest:

| Symptom | Fix |
|---|---|
| Effect re-runs every render because an object or array dependency is recreated | Create the object inside the effect, or depend on its primitive fields (`options.serverUrl`, not `options`) |
| A function dependency changes every render | Move the function inside the effect, or outside the component if it uses no props or state |
| Effect needs the latest value of a prop but should not re-run when it changes (for example, a theme used when logging a connect event) | Read it through an "effect event": `useEffectEvent` (stable since React 19.2; needs a recent `eslint-plugin-react-hooks`), or a ref updated in a layout effect on older versions |
| `setCount(count + 1)` inside an interval makes `count` a dependency | Use the updater form `setCount((c) => c + 1)` and remove the dependency |
| An effect runs, sets state, and runs again forever | The effect depends on state it sets. Usually the computation belongs in render |

## Cleanup checklist

Every effect that starts something returns a function that stops it:

- `addEventListener` → `removeEventListener` with the same function reference.
- `setInterval`/`setTimeout` → `clearInterval`/`clearTimeout`.
- Subscriptions and connections → unsubscribe or close.
- `fetch` → `AbortController.abort()`.
- Third-party widget instances → their `destroy()` or equivalent.

Test cleanup by keeping Strict Mode on in development: if the UI breaks when the effect runs, cleans up and runs again, the cleanup is incomplete.

## `useLayoutEffect`

Use it only to measure layout and synchronously apply a correction before paint (tooltip positioning, scroll restoration). It blocks painting, so keep it short. It does not run during server rendering; components that must render on the server should measure on the client after hydration.
