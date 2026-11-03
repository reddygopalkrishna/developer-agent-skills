# Debugging tools by stack

Use the lightest tool that answers the current question. Check that a tool is installed (`<tool> --version`) before relying on it, and check `--help` for flags, which change between versions.

## Python

| Need | Tool / command |
|---|---|
| Breakpoint | Put `breakpoint()` in the code; run normally. `python -m pdb script.py` to start under the debugger. |
| Debug a failing test | `pytest path::test -x --pdb` (drops into pdb on failure), `pytest --lf` (rerun last failures), `-s` (show prints) |
| Hard crash / hang | `python -X faulthandler script.py` dumps tracebacks on fatal errors; `faulthandler.dump_traceback_later(30)` for hangs |
| Stack of a running process | `py-spy dump --pid <pid>` (no code changes; may need elevated permissions) |
| CPU hot spots | `py-spy top --pid <pid>`, `python -m cProfile -s cumtime script.py` |
| Memory growth | `tracemalloc` (snapshot and compare), `memray` |
| Asyncio problems | `python -X dev` (enables asyncio debug mode, warnings for never-awaited coroutines and slow callbacks) |
| Logging | `logging` with `%(asctime)s %(name)s %(levelname)s %(message)s`; raise one logger to DEBUG instead of everything |

## JavaScript / TypeScript (Node.js)

| Need | Tool / command |
|---|---|
| Breakpoint | `node --inspect-brk app.js`, then open `chrome://inspect` or attach the editor debugger. `debugger;` statement in code. |
| Tests under debugger | `node --inspect-brk node_modules/.bin/jest --runInBand <file>`; Vitest: `vitest --inspect-brk --no-file-parallelism` |
| Readable TS stack traces | `node --enable-source-maps` |
| Warnings and unhandled errors | `node --trace-warnings`, `node --trace-uncaught` |
| Core module internals | `NODE_DEBUG=http,net,tls node app.js` |
| Libraries using the `debug` package | `DEBUG=express:*,my-lib:* node app.js` |
| Open handles keeping Jest alive | `jest --detectOpenHandles` |
| CPU / heap | `node --cpu-prof app.js` (writes `.cpuprofile`), `node --heap-prof`, heap snapshots in DevTools |

## Browser front-end

- DevTools **Sources**: breakpoints, conditional breakpoints, logpoints (log without editing code), "Pause on caught/uncaught exceptions", XHR/fetch breakpoints, DOM-change breakpoints.
- **Network**: status, timing, request/response bodies, "Disable cache", throttling, "Preserve log" across navigations.
- **Console**: `console.table`, `console.trace()` for call stacks, `$0` for the selected element.
- **Performance** panel for long tasks and layout thrashing; **Memory** panel heap snapshots for leaks (compare two snapshots).
- Framework devtools (React, Vue, Angular) for component state and re-render causes.
- Service workers and caches: Application panel, "Update on reload", clear site data.

## Java / Kotlin (JVM)

| Need | Tool / command |
|---|---|
| Remote debugging | Start JVM with `-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005`, attach the IDE |
| Thread dump (deadlocks, hangs) | `jcmd <pid> Thread.print` or `jstack <pid>`; take 3 dumps a few seconds apart and compare |
| Heap dump | `jcmd <pid> GC.heap_dump /tmp/heap.hprof`; automatic: `-XX:+HeapDumpOnOutOfMemoryError` |
| Low-overhead profiling | Java Flight Recorder: `jcmd <pid> JFR.start duration=60s filename=rec.jfr`, open in JDK Mission Control |
| List JVMs | `jcmd` with no arguments |
| GC behavior | `-Xlog:gc*` (JDK 9+) |

## Go

| Need | Tool / command |
|---|---|
| Debugger | Delve: `dlv debug ./cmd/app`, `dlv test ./pkg -- -test.run '^TestX$'`, `dlv attach <pid>` |
| Data races | `go test -race ./...`, `go run -race .` |
| Goroutine dump of a running process | Send SIGQUIT (`kill -QUIT <pid>`), or set `GOTRACEBACK=all` for full dumps on panic |
| Profiling | `import _ "net/http/pprof"` and serve it, then `go tool pprof http://localhost:6060/debug/pprof/profile` (CPU), `.../heap`, `.../goroutine` |
| Tests | `go test -run '^TestX$' -v -count=1 ./pkg` (`-count=1` disables the test cache) |
| Execution trace | `go test -trace trace.out`, then `go tool trace trace.out` |

## C# / .NET

| Need | Tool / command |
|---|---|
| Debugger | Visual Studio, Rider, or VS Code with the C# extension; `System.Diagnostics.Debugger.Break()` |
| Live counters (CPU, GC, thread pool, exceptions) | `dotnet-counters monitor -p <pid>` |
| Trace | `dotnet-trace collect -p <pid>` |
| Dump and analyze | `dotnet-dump collect -p <pid>`, then `dotnet-dump analyze <file>` (`clrstack`, `dumpheap -stat`) |
| Hanging tests | `dotnet test --blame-hang-timeout 60s` collects a dump when a test hangs |

Install the diagnostic tools with `dotnet tool install --global dotnet-counters` (and `dotnet-trace`, `dotnet-dump`).

## Rust

| Need | Tool / command |
|---|---|
| Backtraces | `RUST_BACKTRACE=1` (or `full`) |
| Quick value inspection | `dbg!(expr)` (prints file, line and value; remove afterwards) |
| Debugger | `rust-gdb` / `rust-lldb`, or the editor's CodeLLDB integration |
| See test output | `cargo test <name> -- --nocapture`; serialize: `-- --test-threads=1` |
| Undefined behavior in `unsafe` code | Miri: `cargo +nightly miri test` |
| Async runtime | `tokio-console` (requires enabling instrumentation in the app) |
| Logging | `tracing` or `log` crates with `RUST_LOG=my_crate=debug` (with `env_logger` or `tracing-subscriber`'s env filter) |

## C / C++

- `gdb` / `lldb`; compile with `-g -O0` for debugging.
- AddressSanitizer `-fsanitize=address`, UndefinedBehaviorSanitizer `-fsanitize=undefined`, ThreadSanitizer `-fsanitize=thread` (do not combine ASan and TSan in one build).
- Valgrind (`valgrind --leak-check=full ./app`) on Linux.

## Operating system and process level

| Need | Linux | macOS | Windows |
|---|---|---|---|
| System calls / file and network activity | `strace -f -e trace=file,network -p <pid>` | `dtruss` (limited by SIP) | Process Monitor (Sysinternals) |
| Open files and sockets | `lsof -p <pid>`, `ss -tanp` | `lsof -p <pid>` | `Get-NetTCPConnection`, Resource Monitor, Process Explorer |
| Resource usage | `top`, `htop`, `pidstat` | Activity Monitor, `top` | Task Manager, `Get-Process` |
| System logs | `journalctl -u <service>`, `dmesg` (OOM killer) | `log show --last 10m` | Event Viewer |

## Network and HTTP

- `curl -v https://host/path` shows DNS, TLS and headers; add `-w '%{http_code} %{time_total}\n'` for timing.
- DNS: `dig host`, `nslookup host`.
- TLS: `openssl s_client -connect host:443 -servername host` shows the certificate chain and expiry.
- Inspect traffic: browser Network tab, an intercepting proxy such as mitmproxy, or `tcpdump`/Wireshark for lower levels.

## Databases

- Turn on query logging for the session or ORM (for example the ORM's SQL echo setting) to see the SQL actually sent.
- `EXPLAIN` / `EXPLAIN ANALYZE` for unexpected slowness.
- Locks and blocked queries: PostgreSQL `pg_stat_activity` and `pg_locks`; MySQL `SHOW ENGINE INNODB STATUS` and `performance_schema.data_locks` (8.0+); SQL Server `sys.dm_exec_requests`.
- Check the transaction isolation level and whether the code runs inside the transaction you think it does.

## Distributed systems

- Follow one request through all services with a correlation or trace ID (OpenTelemetry traces if available).
- Compare timestamps carefully: hosts' clocks can differ; prefer trace spans over wall-clock comparisons across machines.
- Check retries and timeouts at every hop; a timeout in one service often shows up as a different error in its caller.

## Logging technique for debugging

- Use a unique prefix (`DBG-refund:`) so temporary logs are easy to find and delete.
- Log at boundaries: function inputs and outputs, before and after external calls.
- Log type and length, not just value: `repr(x)`, `typeof x`, `%T` in Go, `x.GetType()` in C#. Many bugs are `"1"` vs `1`, `None` vs `""`, trailing whitespace.
- Never log secrets, tokens, passwords or personal data, even temporarily.
