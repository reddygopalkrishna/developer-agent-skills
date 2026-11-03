# Flaky test playbook

A flaky test passes and fails on the same code. Treat it as a bug: sometimes in the test, sometimes in the product (a real race the test happens to expose).

## 1. Confirm it is flaky

- Re-run the same commit several times locally and look at CI history for the test. Note the failure rate.
- Collect every failure message. Different messages for the same test often point at different causes.
- Make sure it is not a real, consistent failure caused by an environment difference (missing service, wrong version).

## 2. Classify the pattern

| Observation | Points to |
|---|---|
| Fails only when run with the full suite, passes alone | Shared state or order dependence |
| Fails only in parallel runs | Shared resources (ports, files, database rows, global state) |
| Fails only in CI | Slower machines and timeouts, different OS/timezone/locale, fewer CPUs, missing services |
| Fails at certain times of day or dates | Clock, timezone, DST, date boundaries |
| Fails more under load | Race conditions, timeouts, resource exhaustion |
| Fails with timeouts | Waiting on a fixed delay, slow dependency, deadlock |
| Fails only on one OS | Path separators, line endings, case-sensitive file systems, file locking |

## 3. Reproduce locally

- Repeat the single test many times (see [framework-commands.md](framework-commands.md)).
- Run the full suite in random order with the seed from the failing run (pytest-randomly, `jest --randomize --seed`, `vitest --sequence.shuffle --sequence.seed=<n>`, `go test -shuffle=<seed>`).
- Add parallelism or CPU pressure to make races more likely.
- Run inside the CI container image, with the same environment variables and resource limits.
- Run the failing test together with only the tests that ran before it in the failing order, then bisect that list.

## 4. Common causes and fixes

| Cause | Fix |
|---|---|
| Fixed `sleep` waiting for async work | Wait for a condition (poll with timeout), await the operation, or use the framework's async helpers |
| State leaking between tests | Create data per test with unique IDs; roll back transactions; reset globals, singletons, env vars and mocks in teardown |
| Order dependence | Make each test set up everything it needs; never rely on another test's side effects |
| Wall-clock time | Inject or freeze the clock; avoid assertions near midnight, month-end or DST boundaries unless that is the point of the test |
| Unseeded randomness | Seed it and print the seed on failure |
| Real external services | Replace with a fake server or emulator; keep real-service checks in a separate, clearly labeled suite |
| Port or file conflicts in parallel runs | Bind to port 0 and read the assigned port; use per-test temp directories |
| Unordered results | Sort before comparing, or compare as sets; add `ORDER BY` to queries |
| Floating-point comparisons | Compare with a tolerance (`pytest.approx`, `toBeCloseTo`, `assertEquals(expected, actual, delta)`) |
| Timeouts too tight for CI | Find out why it is slow first; raise the timeout only when the slowness is legitimate |
| Resource leaks (connections, handles) | Close resources in teardown; detect with `jest --detectOpenHandles`, pool metrics, or leak checks |
| Real product race condition | Fix the product code. The test found a bug. |

## 5. End-to-end and UI tests

- Use auto-waiting, web-first assertions instead of fixed waits. Playwright: `await expect(page.getByRole("button", { name: "Save" })).toBeVisible()`; avoid `page.waitForTimeout()`.
- Select elements by role, label or a dedicated test id, not by CSS classes or DOM position.
- Give every test its own user and data; never share accounts between parallel tests.
- Disable or shorten animations in the test environment.
- Mock or stub third-party scripts (analytics, chat widgets, ads) that load unpredictably.
- Wait for the specific network response the test depends on, not for "network idle".
- Capture traces, screenshots or videos on failure so flakes can be diagnosed after the fact.

## 6. Policy while it is being fixed

- **Quarantine, don't delete.** Mark the test as quarantined or skipped with a reason, an owner, a ticket and a date to revisit. Keep running it in a separate non-blocking job if possible, so you still collect data.
- **Retries are a temporary measure.** Automatic retries hide real races and make the suite slower. If you enable them, track how often they trigger and remove them once fixed.
- **Never "fix" by loosening the assertion** until the test no longer checks the behavior.

## 7. Verify the fix

- Run the test many more times than it took to fail before (for example, if it failed 1 in 20 runs, run it 200 times).
- Run the full suite in random order a few times.
- Watch CI for the following days before closing the ticket.
