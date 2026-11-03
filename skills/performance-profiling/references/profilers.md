# Profiler Cheat Sheet

Commands for the most common stacks. Tools evolve: if a flag fails, check `<tool> --help` before guessing. Always profile an optimized build with realistic data.

## Python

| Need | Command |
|---|---|
| Live view of hottest functions in a running process | `py-spy top --pid <PID>` |
| Flame graph of a running process | `py-spy record -o profile.svg --pid <PID>` |
| Flame graph of a script | `py-spy record -o profile.svg -- python app.py` |
| Current stack of every thread (hang diagnosis) | `py-spy dump --pid <PID>` |
| Include waiting threads / native extensions | add `--idle` / `--native` |
| Deterministic profile (higher overhead) | `python -m cProfile -o out.prof app.py` |
| Inspect a cProfile file | `python -m pstats out.prof`, then `sort cumtime` and `stats 20`; or `snakeviz out.prof` |
| Line-by-line timing | decorate with `@profile`, run `kernprof -l -v script.py` (line_profiler) |
| CPU and memory together | `scalene app.py` |
| Memory allocations with flame graph | `memray run app.py`, then `memray flamegraph <output>.bin` |
| Built-in allocation tracking | `tracemalloc.start()`; later `tracemalloc.take_snapshot().statistics("lineno")` |

Notes: py-spy attaches with ptrace; on Linux you may need `sudo` or, in a container, the `SYS_PTRACE` capability. Python 3.12+ supports `python -X perf` so Linux `perf` can see Python function names.

## Node.js

| Need | Command |
|---|---|
| CPU profile written on exit | `node --cpu-prof app.js` (writes `*.cpuprofile`; set folder with `--cpu-prof-dir`) |
| Heap allocation profile written on exit | `node --heap-prof app.js` |
| Interactive profiling and heap snapshots | `node --inspect app.js`, open `chrome://inspect` in Chrome, use the Performance and Memory tools |
| V8 tick profiler | `node --prof app.js`, then `node --prof-process isolate-*.log > processed.txt` |
| Flame graph in one step | `npx 0x app.js` |
| Event-loop delay metric | `perf_hooks.monitorEventLoopDelay()` in code; export p99 as a metric |

Open `.cpuprofile` files in Chrome DevTools or speedscope. For leaks, take two heap snapshots a few minutes apart under load and compare "objects allocated between snapshots".

## Go

| Need | Command |
|---|---|
| Expose profiles from a service | `import _ "net/http/pprof"` and serve `http.DefaultServeMux` on an internal port |
| 30 s CPU profile | `go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30` |
| Heap / goroutines | `go tool pprof http://localhost:6060/debug/pprof/heap`, `.../debug/pprof/goroutine` |
| Mutex and blocking profiles | enable with `runtime.SetMutexProfileFraction(n)` / `runtime.SetBlockProfileRate(n)`, then fetch `/debug/pprof/mutex` or `/debug/pprof/block` |
| Web UI with flame graph | `go tool pprof -http=:8080 cpu.prof` |
| Profile a benchmark | `go test -bench=. -benchmem -cpuprofile cpu.prof -memprofile mem.prof` |
| Execution trace (scheduler, GC, latency) | `go test -trace trace.out`, then `go tool trace trace.out` |
| Compare benchmark runs | `go install golang.org/x/perf/cmd/benchstat@latest`; `benchstat old.txt new.txt` (use `-count=10` runs) |

Never expose the pprof endpoint publicly.

## Java / Kotlin (JVM)

| Need | Command |
|---|---|
| Flight recording from start | `java -XX:StartFlightRecording=duration=60s,filename=rec.jfr -jar app.jar` |
| Flight recording of a running JVM | `jcmd <PID> JFR.start duration=60s filename=rec.jfr` |
| Inspect a recording | JDK Mission Control (`jmc`), or `jfr summary rec.jfr` / `jfr print --events jdk.ExecutionSample rec.jfr` |
| CPU flame graph | `asprof -d 30 -f flame.html <PID>` (async-profiler 3.x; older versions use `profiler.sh`) |
| Allocation / lock / wall-clock profile | add `-e alloc`, `-e lock`, or `-e wall` to `asprof` |
| Thread dump | `jcmd <PID> Thread.print` (or `jstack <PID>`) |
| Heap histogram | `jcmd <PID> GC.class_histogram` |
| Heap dump (pauses the JVM, contains data) | `jcmd <PID> GC.heap_dump /path/heap.hprof`; analyze with Eclipse MAT |
| GC logging | `-Xlog:gc*:file=gc.log` |

## C# / .NET

Install the diagnostics tools once: `dotnet tool install -g dotnet-counters` (same for `dotnet-trace`, `dotnet-gcdump`, `dotnet-dump`).

| Need | Command |
|---|---|
| Live runtime counters (CPU, GC, thread pool queue, exceptions) | `dotnet-counters monitor -p <PID>` |
| CPU trace | `dotnet-trace collect -p <PID>`; open the `.nettrace` in Visual Studio or PerfView |
| Trace viewable in speedscope | `dotnet-trace collect -p <PID> --format Speedscope` |
| Other trace profiles (GC, etc.) | see `dotnet-trace collect --help`; profile names differ between tool versions |
| GC heap snapshot | `dotnet-gcdump collect -p <PID>` |
| Full process dump and analysis | `dotnet-dump collect -p <PID>`, then `dotnet-dump analyze <file>` |
| Microbenchmarks | BenchmarkDotNet with `[MemoryDiagnoser]` |

Thread-pool starvation shows as a growing thread-pool queue length with low CPU; look for `.Result`, `.Wait()` or synchronous I/O in async code.

## Rust

| Need | Command |
|---|---|
| Flame graph | `cargo install flamegraph`, then `cargo flamegraph --bin <name>` (uses perf on Linux, dtrace on macOS) |
| Sampling profiler with UI | `samply record ./target/release/<binary>` |
| Benchmarks | `criterion` with `cargo bench` |
| Symbols in release builds | in `Cargo.toml`: `[profile.release]` with `debug = true` while profiling |

## Linux system level

| Need | Command |
|---|---|
| Quick health | `top` or `htop`, `vmstat 1`, `iostat -xz 1`, `pidstat 1`, `ss -s`, `free -m`, `df -h` |
| Hot functions system-wide or per process | `perf top -p <PID>` |
| Record with call stacks | `perf record -F 99 -g -p <PID> -- sleep 30`, then `perf report` |
| Flame graph from perf | `perf script \| stackcollapse-perf.pl \| flamegraph.pl > out.svg` (Brendan Gregg's FlameGraph scripts) |
| JIT-compiled code names in perf | Node: `--perf-basic-prof`; Python 3.12+: `-X perf`; JVM: prefer async-profiler |
| Syscall summary | `strace -c -p <PID>` (high overhead; avoid on busy production processes) |

## Windows

PerfView (free, Microsoft) for CPU, GC and allocation analysis of .NET and native code. Windows Performance Recorder (`wpr`) with Windows Performance Analyzer for system-wide traces.

## Load generators

| Tool | Example |
|---|---|
| k6 | `k6 run script.js`; use the `constant-arrival-rate` executor for fixed request rates |
| wrk | `wrk -t4 -c100 -d30s http://host/path` (closed loop) |
| wrk2 | same as wrk plus `-R <rate>` for fixed throughput |
| hey | `hey -z 30s -c 50 http://host/path` |
| vegeta | `echo "GET http://host/path" \| vegeta attack -rate=200 -duration=30s \| vegeta report` |
| hyperfine (CLI commands) | `hyperfine --warmup 3 'cmd-a' 'cmd-b'` |

Only point load generators at environments the user has approved.
