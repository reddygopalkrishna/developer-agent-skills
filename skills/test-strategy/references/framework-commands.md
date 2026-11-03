# Test framework commands

Commands for the most common frameworks. Prefer the project's own scripts (`npm test`, `make test`, `./gradlew check`) when they exist, because they may set environment variables or flags. Check `--help` for your installed version; flags marked "plugin" need an extra package.

## pytest (Python)

| Task | Command |
|---|---|
| One file / one test | `pytest tests/test_orders.py` / `pytest tests/test_orders.py::test_refund` |
| Filter by name | `pytest -k "refund and not slow"` |
| Stop at first failure | `pytest -x` |
| Rerun last failures / failures first | `pytest --lf` / `pytest --ff` |
| Verbose, show prints | `pytest -vv -s` |
| Debugger on failure | `pytest --pdb` |
| Slowest tests | `pytest --durations=10` |
| Parallel (plugin: pytest-xdist) | `pytest -n auto` |
| Random order (plugin: pytest-randomly) | On automatically once installed; reuse a seed with `pytest --randomly-seed=<seed>` (or `--randomly-seed=last`); disable with `-p no:randomly` |
| Repeat (plugin: pytest-repeat) | `pytest --count=50 tests/test_orders.py::test_refund` |
| Coverage (plugin: pytest-cov) | `pytest --cov=src --cov-report=term-missing` |
| Markers | `pytest -m "not integration"` (register markers in config) |

## Jest (JavaScript / TypeScript)

| Task | Command |
|---|---|
| One file | `npx jest src/cart.test.ts` |
| Filter by test name | `npx jest -t "applies discount"` |
| Watch mode | `npx jest --watch` |
| Only previously failed | `npx jest --onlyFailures` |
| Stop after first failing suite | `npx jest --bail` |
| Serial (no workers) | `npx jest --runInBand` |
| Random order (Jest 29.5+) | `npx jest --randomize` (prints the seed; reuse with `--seed=<n>`) |
| Find leaked handles | `npx jest --detectOpenHandles` |
| Coverage | `npx jest --coverage` |

## Vitest (JavaScript / TypeScript)

| Task | Command |
|---|---|
| Run once (no watch) | `npx vitest run` |
| One file | `npx vitest run src/cart.test.ts` |
| Filter by test name | `npx vitest run -t "applies discount"` |
| Watch mode | `npx vitest` |
| Stop after N failures | `npx vitest run --bail 1` |
| Shuffle order | `npx vitest run --sequence.shuffle` |
| Verbose | `npx vitest run --reporter=verbose` |
| Coverage | `npx vitest run --coverage` (needs `@vitest/coverage-v8` or `@vitest/coverage-istanbul`) |

## go test

| Task | Command |
|---|---|
| All packages | `go test ./...` |
| One test (regex) | `go test -run '^TestRefund$' ./orders` |
| One subtest | `go test -run '^TestRefund$/expired_card$' ./orders` |
| Verbose, no cache | `go test -v -count=1 ./orders` |
| Repeat | `go test -run '^TestRefund$' -count=100 ./orders` |
| Race detector | `go test -race ./...` |
| Random order | `go test -shuffle=on ./...` (prints the seed; reuse with `-shuffle=<seed>`) |
| Stop at first failure | `go test -failfast ./...` |
| Timeout | `go test -timeout 60s ./...` |
| Coverage | `go test -coverprofile=cover.out ./... && go tool cover -html=cover.out` |
| Fuzzing | `go test -fuzz=FuzzParse -fuzztime=30s ./parser` |

## JUnit 5 with Maven

| Task | Command |
|---|---|
| All unit tests | `mvn test` |
| Unit + integration tests (Failsafe) | `mvn verify` |
| One class | `mvn test -Dtest=OrderServiceTest` |
| One method | `mvn test -Dtest='OrderServiceTest#refundsOnlyOnce'` |
| Pattern | `mvn test -Dtest='*ServiceTest'` |

## JUnit 5 with Gradle

| Task | Command |
|---|---|
| All tests | `./gradlew test` |
| One class | `./gradlew test --tests 'com.acme.orders.OrderServiceTest'` |
| One method | `./gradlew test --tests 'com.acme.orders.OrderServiceTest.refundsOnlyOnce'` |
| Force rerun (no up-to-date skip) | `./gradlew test --rerun` (Gradle 7.6+) or `./gradlew cleanTest test` |
| Stop at first failure | `./gradlew test --fail-fast` |

JUnit 5 features: `@ParameterizedTest` with `@ValueSource`/`@CsvSource`/`@MethodSource`; `@RepeatedTest(50)` to repeat; random method order via `junit.jupiter.testmethod.order.default=org.junit.jupiter.api.MethodOrderer$Random` in `src/test/resources/junit-platform.properties`. Coverage is usually JaCoCo (configured as a build plugin).

## .NET (xUnit, NUnit, MSTest) with dotnet test

These options are for the classic VSTest runner. Projects on Microsoft.Testing.Platform (for example xUnit v3 or MSTest runner mode) use different flags, so check `dotnet test --help` in the project first.

| Task | Command |
|---|---|
| All tests | `dotnet test` |
| Filter by name | `dotnet test --filter "FullyQualifiedName~OrderServiceTests"` |
| One test | `dotnet test --filter "FullyQualifiedName=Acme.Orders.Tests.OrderServiceTests.RefundsOnlyOnce"` |
| By category / trait | `dotnet test --filter "Category=Integration"` |
| Detailed output | `dotnet test --logger "console;verbosity=detailed"` |
| Dump on hang | `dotnet test --blame-hang-timeout 60s` |
| Coverage (coverlet.collector package) | `dotnet test --collect:"XPlat Code Coverage"` |

Parameterized tests: xUnit `[Theory]` + `[InlineData]`/`[MemberData]`; NUnit `[TestCase]`; MSTest `[TestMethod]` + `[DataRow]` (`[DataTestMethod]` is deprecated from MSTest 3.10).

## Rust (cargo)

| Task | Command |
|---|---|
| All tests | `cargo test` |
| Filter by name (substring) | `cargo test refund` |
| Exact name | `cargo test -- --exact orders::tests::refund_once` |
| Show output | `cargo test -- --nocapture` |
| Serial | `cargo test -- --test-threads=1` |
| Doc tests only | `cargo test --doc` |
| nextest runner (separate install) | `cargo nextest run` |
| Coverage (cargo-llvm-cov, separate install) | `cargo llvm-cov` |

## Repeating a test to expose flakiness

Use the framework's repeat option when it has one. Otherwise loop until failure.

Bash:

```bash
for i in $(seq 1 50); do
  <test command> || { echo "failed on run $i"; break; }
done
```

PowerShell:

```powershell
for ($i = 1; $i -le 50; $i++) {
  <test command>
  if ($LASTEXITCODE -ne 0) { "failed on run $i"; break }
}
```
