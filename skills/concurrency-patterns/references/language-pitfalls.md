# Concurrency Pitfalls by Language

Each section lists the traps that cause most real bugs, the primitive to use instead, and the tooling. Check the language and library version in the project before relying on version-specific behavior.

## JavaScript / TypeScript (Node.js and browsers)

- **Missing `await`.** `async function save() { db.insert(row) }` returns before the insert finishes, and its error becomes an unhandled rejection. Enable the typescript-eslint rules `no-floating-promises` and `no-misused-promises`.
- **Unhandled rejections crash Node.** Since Node 15 the default mode is to throw on unhandled rejections, which terminates the process. Handle errors where the promise is created.
- **`forEach` with an async callback does not wait.** `items.forEach(async (i) => await send(i))` fires everything and returns immediately. Use `for (const i of items) await send(i)` for sequential work or `await Promise.all(items.map(send))` for parallel work.
- **Unbounded `Promise.all`.** Limit concurrency with a small pool (a library such as `p-limit`, or a hand-written worker loop).
- **`Promise.all` fails fast but does not cancel.** The other promises keep running. Pass an `AbortSignal` to the operations so they can stop, or use `Promise.allSettled` when you need every result.
- **State changes across `await`.**

  ```ts
  // Race: two concurrent calls both read 5 and both write 6.
  const n = await store.get("count");
  await store.set("count", n + 1);
  ```

  Use an atomic operation in the store (`INCR`, an atomic SQL update) or serialize access per key.
- **Worker threads** share memory only through `SharedArrayBuffer`; use `Atomics` for synchronization there. Everything else is copied via messages.

## Python

- **The GIL does not make your code thread-safe.** `counter += 1` is a load, add and store; threads can interleave between them. Protect shared state with `threading.Lock` or use `queue.Queue` to hand work between threads.
- **Free-threaded builds** (CPython 3.13+ built without the GIL, PEP 703) expose more of these races. Code that relied on the GIL by accident will break.
- **Blocking the asyncio event loop.** `time.sleep`, `requests.get`, synchronous database drivers and heavy CPU work inside `async def` stall every task. Use `await asyncio.sleep`, an async client, or `await asyncio.to_thread(fn, ...)` (Python 3.9+). Use processes for CPU-bound work.
- **Lost tasks.** Keep a reference to every task from `asyncio.create_task`; the event loop holds only a weak reference and an unreferenced task can disappear mid-execution. Prefer `asyncio.TaskGroup` (3.11+), which also propagates errors.
- **Timeouts**: `async with asyncio.timeout(5):` (3.11+) or `asyncio.wait_for(coro, 5)`.
- **Debug mode**: `asyncio.run(main(), debug=True)` or `PYTHONASYNCIODEBUG=1` reports slow callbacks that block the loop. A `RuntimeWarning: coroutine ... was never awaited` always means a missing `await`.
- **ORMs**: Django `select_for_update()` for row locks and `F()` expressions for atomic updates, for example `Account.objects.filter(pk=pk).update(balance=F("balance") - 10)`. SQLAlchemy has `with_for_update()` and a `version_id_col` mapper option for optimistic locking.

## Java / Kotlin

- **Use `java.util.concurrent`.** `ConcurrentHashMap` (its `compute`, `merge` and `computeIfAbsent` run atomically per key), `AtomicLong` / `LongAdder` for counters, `ExecutorService` with bounded queues. A plain `HashMap` written by several threads can corrupt itself.
- **`Collections.synchronizedMap` still needs manual synchronization when iterating.**
- **Double-checked locking** works only if the field is `volatile`. The holder-class idiom is simpler for lazy singletons.
- **`CompletableFuture` exceptions vanish** unless something calls `join()`/`get()` or attaches `exceptionally`/`handle`.
- **Always shut down executors** (`shutdown()` then `awaitTermination`) or threads leak.
- **Virtual threads (Java 21+)**: do not pool them, create one per task. In JDK 21-23, blocking inside a `synchronized` block pins the carrier thread; JEP 491 in JDK 24 removes most of that pinning. On older JDKs prefer `ReentrantLock` around blocking calls. Avoid large `ThreadLocal` values when you have millions of threads.
- **JPA**: `@Version` for optimistic locking (throws `OptimisticLockException` on conflict); `@Lock(LockModeType.PESSIMISTIC_WRITE)` for `SELECT ... FOR UPDATE`.
- **Kotlin coroutines**: use structured concurrency (`coroutineScope`, a lifecycle-bound scope) instead of `GlobalScope`; use `kotlinx.coroutines.sync.Mutex` when a lock must be held across suspension; run blocking calls on `Dispatchers.IO`.
- **Testing**: jcstress for low-level concurrency tests; `CountDownLatch` to start threads together in ordinary tests.

## C# / .NET

- **Never block on async code** with `.Result`, `.Wait()` or `.GetAwaiter().GetResult()`. With a `SynchronizationContext` (UI apps, classic ASP.NET) it deadlocks; in ASP.NET Core it causes thread-pool starvation under load. Use `async` all the way up.
- **`ConfigureAwait(false)`** in library code that does not need the caller's context.
- **`async void`** only for event handlers. Its exceptions cannot be caught by the caller and can crash the process.
- **No `await` inside `lock`** (the compiler forbids it). Use `SemaphoreSlim(1, 1)` with `await sem.WaitAsync()` and `Release()` in a `finally` block.
- **`ConcurrentDictionary.GetOrAdd(key, factory)`** may call the factory more than once under contention. If creation must happen once, store `Lazy<T>` values.
- **Atomic counters**: `Interlocked.Increment`, `Interlocked.CompareExchange`.
- **Producer/consumer**: `System.Threading.Channels`. Bounded parallel async work: `Parallel.ForEachAsync` with `MaxDegreeOfParallelism`.
- **EF Core**: mark a property with `[ConcurrencyCheck]` or a `[Timestamp]` row-version column; conflicts throw `DbUpdateConcurrencyException`.
- **Testing**: Microsoft Coyote explores interleavings systematically.

## Go

- **Run the race detector** in tests and in a race-enabled staging build: `go test -race ./...`, `go build -race`.
- **Maps are not safe for concurrent writes.** The runtime may abort with `fatal error: concurrent map writes`. Guard with `sync.Mutex`/`sync.RWMutex`; `sync.Map` fits only specific patterns (keys written once, read many times, or disjoint keys per goroutine).
- **Goroutine leaks**: a goroutine blocked forever on a channel send or receive never exits. Give every goroutine an exit path through `ctx.Done()`; use a buffered channel of size 1 for a result the caller might stop waiting for. Detect leaks in tests with `go.uber.org/goleak`.
- **Do not copy values containing a `sync.Mutex`** (pass pointers). `go vet` reports this (copylocks).
- **Close channels only from the sending side**; sending on a closed channel panics.
- **Fan-out with errors**: `golang.org/x/sync/errgroup` with `g.SetLimit(n)` bounds concurrency and returns the first error; use `errgroup.WithContext` to cancel the rest.
- **Deadlines**: `ctx, cancel := context.WithTimeout(ctx, 2*time.Second)` and always `defer cancel()`.
- **Loop variables**: since Go 1.22 each iteration has its own variable, so capturing it in a goroutine is safe; in older modules (go directive below 1.22) it is shared. Check `go.mod`.

## Rust

- **Safe Rust prevents data races** through `Send` and `Sync`, but not deadlocks or logical races (check-then-act across two lock acquisitions is still a race).
- **Shared state**: `Arc<Mutex<T>>` or `Arc<RwLock<T>>`; atomics in `std::sync::atomic` for counters. A `std::sync::Mutex` is poisoned if a holder panics, so `lock()` returns a `Result`.
- **Do not hold a `std::sync::MutexGuard` across `.await`.** The future becomes `!Send` (it cannot be spawned on a multi-threaded runtime) and it can deadlock. Drop the guard before awaiting, or use `tokio::sync::Mutex` when the lock really must span an await.
- **Blocking work in async code** goes to `tokio::task::spawn_blocking` (or the runtime's equivalent).
- **Spawned tasks**: dropping a `JoinHandle` detaches the task and its panic or error is lost unless you join it. `tokio::task::JoinSet` manages groups of tasks.
- **Channels**: prefer message passing (`tokio::sync::mpsc`, `std::sync::mpsc`, or crossbeam) over shared locks for pipelines.
- **Testing**: `loom` model-checks concurrent code by exploring interleavings; Miri detects undefined behavior, including some data races, in `unsafe` code.
