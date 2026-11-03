# Database test setup examples

Testcontainers APIs change between releases. These examples show the shape; check the Testcontainers documentation for your language and installed version before copying. Use an image tag that matches the production database's major version.

## Java (JUnit 5, Spring Boot)

```java
@Testcontainers
@SpringBootTest
class OrderRepositoryTest {

  @Container
  @ServiceConnection   // Spring Boot 3.1+: wires the datasource from the container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

  @Autowired OrderRepository orders;

  @Test
  void findsOpenOrders() { /* ... */ }
}
```

Without `@ServiceConnection`, register the connection details with `@DynamicPropertySource` using `postgres.getJdbcUrl()`, `getUsername()` and `getPassword()`. A `static` container is shared by all tests in the class; share it across classes with a common base class or the singleton pattern described in the Testcontainers docs.

## Python (pytest)

```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

@pytest.fixture(scope="session")
def engine():
    with PostgresContainer("postgres:16-alpine") as pg:
        engine = create_engine(pg.get_connection_url())
        run_migrations(engine)          # your Alembic/Django migration call
        yield engine

@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    # SQLAlchemy 2.x: code under test may call commit(); it commits a savepoint only
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()              # rollback-per-test isolation
    connection.close()
```

Django projects can let the test runner create the test database on the container's server by pointing `DATABASES` at it; `TestCase` then wraps each test in a transaction, and `TransactionTestCase` truncates instead.

## Node (Vitest or Jest)

```ts
import { PostgreSqlContainer, type StartedPostgreSqlContainer } from "@testcontainers/postgresql";

let container: StartedPostgreSqlContainer;

beforeAll(async () => {
  container = await new PostgreSqlContainer("postgres:16-alpine").start();
  process.env.DATABASE_URL = container.getConnectionUri();
  await runMigrations(process.env.DATABASE_URL);
}, 60_000);

afterAll(async () => {
  await container.stop();
});

afterEach(async () => {
  await truncateAll(); // see the truncate helper below
});
```

For parallel workers, start the container once in a global setup file and give each worker its own database (template clone) using the worker id from the test runner.

## .NET (xUnit)

```csharp
using Testcontainers.PostgreSql;

public sealed class DatabaseFixture : IAsyncLifetime
{
    public PostgreSqlContainer Container { get; } = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine")
        .Build();

    public async Task InitializeAsync()
    {
        await Container.StartAsync();
        // apply migrations, e.g. dbContext.Database.MigrateAsync()
    }

    public Task DisposeAsync() => Container.DisposeAsync().AsTask();
}

public class OrderTests : IClassFixture<DatabaseFixture>
{
    private readonly string _connectionString;
    public OrderTests(DatabaseFixture db) => _connectionString = db.Container.GetConnectionString();
}
```

Newer Testcontainers for .NET releases may expect the image in the builder's constructor; follow the version's docs. Use `Database.MigrateAsync()`, not `EnsureCreated()`, so migrations are exercised.

## Go

```go
import (
    "context"
    "os"
    "testing"

    "github.com/testcontainers/testcontainers-go/modules/postgres"
)

func TestMain(m *testing.M) {
    ctx := context.Background()
    ctr, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("app_test"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        postgres.BasicWaitStrategies(),
    )
    if err != nil { panic(err) }
    dsn, _ := ctr.ConnectionString(ctx, "sslmode=disable")
    // run migrations with dsn, store it for tests
    code := m.Run()
    _ = ctr.Terminate(ctx)
    os.Exit(code)
}
```

Older module versions use a different constructor; check the module docs for your version.

## GitHub Actions service container

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: app_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      DATABASE_URL: postgres://test:test@localhost:5432/app_test
      APP_ENV: test
    steps:
      - uses: actions/checkout@v4
      # install dependencies, run migrations, run tests
```

## PostgreSQL helpers

Template database (migrate once, clone per worker or test):

```sql
-- once, after running migrations into app_template:
-- (no other sessions may be connected to app_template while cloning)
CREATE DATABASE app_test_w1 TEMPLATE app_template;
-- after the run:
DROP DATABASE IF EXISTS app_test_w1;
```

Truncate every application table in a schema (skip the migration tool's own table, whose name depends on the tool):

```sql
DO $$
DECLARE tables text;
BEGIN
  SELECT string_agg(format('%I.%I', schemaname, tablename), ', ')
    INTO tables
  FROM pg_tables
  WHERE schemaname = 'public'
    AND tablename NOT IN ('schema_migrations', 'flyway_schema_history', 'alembic_version', '__EFMigrationsHistory', '_prisma_migrations', 'django_migrations');
  IF tables IS NOT NULL THEN
    EXECUTE 'TRUNCATE ' || tables || ' RESTART IDENTITY CASCADE';
  END IF;
END $$;
```

Run these helpers only against test databases created for the run; the safety guard in the skill applies.
