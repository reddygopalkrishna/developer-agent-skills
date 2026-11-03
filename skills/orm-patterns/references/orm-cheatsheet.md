# ORM cheat sheet

Syntax for the patterns in the orm-patterns skill. APIs change between major versions; when something here doesn't compile, check the docs for the installed version (look at the lockfile first).

## Prisma

```ts
// SQL logging, and counting queries (useful in tests)
const prisma = new PrismaClient({ log: [{ emit: "event", level: "query" }] });
let queries = 0;
prisma.$on("query", () => { queries++; });

// Eager loading and projection
await prisma.order.findMany({
  where: { status: "open" },
  select: { id: true, total: true, customer: { select: { name: true } }, items: true },
});

// Bulk and atomic writes
await prisma.order.createMany({ data: rows });
await prisma.order.updateMany({ where: { createdAt: { lt: cutoff } }, data: { status: "archived" } });
await prisma.product.update({ where: { id }, data: { stock: { decrement: 1 } } });

// Transactions
await prisma.$transaction([op1, op2]);                    // batch, all or nothing
await prisma.$transaction(async (tx) => { /* reads and writes with tx */ });

// Parameterized raw SQL
await prisma.$queryRaw`SELECT id FROM orders WHERE customer_id = ${customerId}`;
```

- Relations never load lazily; anything not in `include`/`select` is absent.
- Connection pool settings depend on the Prisma version and whether a driver adapter is used. Check the Prisma docs for your version.

## Hibernate / JPA (Spring Data JPA)

```properties
# SQL logging and statistics (development)
logging.level.org.hibernate.SQL=DEBUG
spring.jpa.properties.hibernate.generate_statistics=true

# Batch fetching of lazy associations and collections
spring.jpa.properties.hibernate.default_batch_fetch_size=50

# JDBC batching for inserts/updates
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true

# Don't hide lazy loads in the view layer
spring.jpa.open-in-view=false

# Pool (HikariCP)
spring.datasource.hikari.maximum-pool-size=10
```

```java
@Entity
class Order {
  @ManyToOne(fetch = FetchType.LAZY)   // JPA default for to-one is EAGER: override it
  Customer customer;

  @OneToMany(mappedBy = "order")       // collections are LAZY by default
  List<Item> items;

  @Version
  long version;                        // optimistic locking
}

interface OrderRepository extends JpaRepository<Order, Long> {
  @Query("select o from Order o join fetch o.customer where o.status = :status")
  List<Order> findWithCustomer(@Param("status") String status);

  @EntityGraph(attributePaths = {"customer", "items"})
  Optional<Order> findWithDetailsById(Long id);

  @Query("select new com.example.OrderSummary(o.id, o.total) from Order o where o.status = :status")
  List<OrderSummary> findSummaries(@Param("status") String status);

  @Modifying(clearAutomatically = true)
  @Query("update Order o set o.status = 'archived' where o.createdAt < :cutoff")
  int archiveBefore(@Param("cutoff") Instant cutoff);
}
```

- `JOIN FETCH` one collection per query. Fetching two `List` collections at once fails or explodes rows; use batch fetching or a second query.
- Paginating a query with a collection `JOIN FETCH` makes Hibernate paginate in memory (it logs a warning). Page IDs first.
- `GenerationType.IDENTITY` prevents JDBC insert batching; use a sequence for bulk-insert tables.
- `@Transactional(readOnly = true)` on read services skips dirty checking.
- Query counts in tests: read `Statistics.getPrepareStatementCount()` from the `SessionFactory`, or use a JDBC proxy library that counts statements.

## Entity Framework Core

```csharp
// SQL logging (development only for sensitive data logging)
optionsBuilder.LogTo(Console.WriteLine, LogLevel.Information);

// Eager loading; split query for multiple collections
var orders = await db.Orders
    .Include(o => o.Customer)
    .Include(o => o.Items).ThenInclude(i => i.Product)
    .AsSplitQuery()
    .AsNoTracking()
    .ToListAsync();

// Projection (no Include needed; only selected columns are queried)
var rows = await db.Orders
    .Where(o => o.Status == "open")
    .Select(o => new OrderDto(o.Id, o.Total, o.Customer.Name))
    .ToListAsync();

// Set-based writes (EF Core 7+)
await db.Orders.Where(o => o.CreatedAt < cutoff)
    .ExecuteUpdateAsync(s => s.SetProperty(o => o.Status, "archived"));
await db.Sessions.Where(s => s.ExpiresAt < now).ExecuteDeleteAsync();

// Parameterized raw SQL
var list = await db.Orders.FromSql($"SELECT * FROM orders WHERE customer_id = {customerId}").ToListAsync();
```

- Inserting many rows: `AddRange` then one `SaveChangesAsync`; EF Core batches the statements.
- Optimistic concurrency: `[ConcurrencyCheck]` on a property or a `[Timestamp]` row version (SQL Server). Other providers have their own mechanism (Npgsql can use `xmin`); check the provider docs. Catch `DbUpdateConcurrencyException`.
- Lazy loading happens only if lazy-loading proxies are enabled (`UseLazyLoadingProxies`). Prefer leaving them off.
- `AddDbContextPool` pools `DbContext` objects; database connections are pooled by the ADO.NET provider (`Max Pool Size` in the connection string).
- Query counts in tests: a `DbCommandInterceptor` that increments a counter.
- View migration SQL: `dotnet ef migrations script`.

## SQLAlchemy 2.x

```python
engine = create_engine(url, echo=True, pool_size=5, max_overflow=10, pool_pre_ping=True)

# Eager loading
stmt = (
    select(Order)
    .options(joinedload(Order.customer), selectinload(Order.items))
    .where(Order.status == "open")
)
orders = session.scalars(stmt).unique().all()   # .unique() is required with joinedload of collections

# Fail on any unexpected lazy load
stmt = select(Order).options(selectinload(Order.items), raiseload("*"))

# Projection
rows = session.execute(select(Order.id, Order.total)).all()

# Bulk and set-based writes
session.execute(insert(Order), [{"customer_id": 1, "total": 10}, {"customer_id": 2, "total": 20}])
session.execute(update(Order).where(Order.created_at < cutoff).values(status="archived"))
session.execute(update(Product).where(Product.id == pid).values(stock=Product.stock - 1))

# Large result sets
for order in session.scalars(select(Order).execution_options(yield_per=1000)):
    ...

# Parameterized raw SQL
session.execute(text("SELECT id FROM orders WHERE customer_id = :cid"), {"cid": customer_id})
```

- Optimistic locking: `__mapper_args__ = {"version_id_col": version}` on the mapped class; a conflict raises `StaleDataError`.
- Async sessions cannot lazy load (you get `MissingGreenlet`). Load relationships eagerly or use the async attribute access helpers.
- Query counts in tests: `event.listen(engine, "before_cursor_execute", count_fn)`.
- View Alembic migration SQL: `alembic upgrade head --sql`.

## Django ORM

```python
# SQL logging: set the "django.db.backends" logger to DEBUG (works when DEBUG=True)

orders = (
    Order.objects.filter(status="open")
    .select_related("customer")                      # to-one: JOIN
    .prefetch_related(
        Prefetch("items", queryset=Item.objects.filter(active=True))
    )                                                # to-many: second query
)

Order.objects.values("id", "total")                  # projection
Order.objects.only("id", "total")                    # model instances, fewer columns

Order.objects.bulk_create(objs, batch_size=1000)
Order.objects.bulk_update(objs, ["status"], batch_size=1000)
Order.objects.filter(created_at__lt=cutoff).update(status="archived")
Product.objects.filter(pk=pid).update(stock=F("stock") - 1)

for order in Order.objects.iterator(chunk_size=2000):
    ...

with transaction.atomic():
    product = Product.objects.select_for_update().get(pk=pid)
    ...
    transaction.on_commit(lambda: send_confirmation(order_id))   # side effect after commit

Order.objects.raw("SELECT * FROM shop_order WHERE customer_id = %s", [customer_id])
```

- Tests: `with self.assertNumQueries(3): ...` (or the `django_assert_num_queries` fixture with pytest-django).
- `bulk_create`, `bulk_update` and `update()` skip `save()` and signals.
- View migration SQL: `python manage.py sqlmigrate <app> <migration>`.
- Connections: `CONN_MAX_AGE` keeps connections open between requests; recent Django versions can also pool PostgreSQL connections natively. Check the docs for your version.

## ActiveRecord (Rails)

```ruby
Order.includes(:customer, :items).where(status: "open")   # Rails picks preload or eager_load
Order.preload(:items)                                    # always separate queries
Order.eager_load(:customer)                              # always LEFT OUTER JOIN

Order.strict_loading.find(id)                            # raise on lazy load for this record
# or per model: self.strict_loading_by_default = true

Order.select(:id, :total)
Order.where(status: "open").pluck(:id)

Order.insert_all(rows)                                   # skips validations and callbacks
Order.upsert_all(rows, unique_by: :external_id)
Order.where("created_at < ?", cutoff).update_all(status: "archived")
Product.update_counters(pid, stock: -1)                  # atomic

Order.find_each(batch_size: 1000) { |o| ... }

Product.transaction do
  product = Product.lock.find(pid)                       # SELECT ... FOR UPDATE
end
```

- Optimistic locking: add an integer `lock_version` column (default 0); conflicts raise `ActiveRecord::StaleObjectError`.
- N+1 detection in development and tests: the Bullet gem, or `strict_loading`.
- Pool size: `pool:` in `config/database.yml`; it must be at least the number of threads per process.
