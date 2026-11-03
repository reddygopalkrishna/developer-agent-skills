# OpenTelemetry Setup Notes

OpenTelemetry packages and APIs change often. **Before you add a dependency, check the current docs at opentelemetry.io for that language** to confirm package names and stability (some languages' logs and metrics support is newer than tracing). Match the versions the repo already uses.

## Common configuration (all languages)

The SDKs read standard environment variables. Prefer these over hard-coding:

```bash
OTEL_SERVICE_NAME=checkout
OTEL_RESOURCE_ATTRIBUTES=service.version=1.4.2,deployment.environment.name=prod
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317   # 4317 = OTLP/gRPC, 4318 = OTLP/HTTP
OTEL_EXPORTER_OTLP_PROTOCOL=grpc                         # or http/protobuf
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1                              # keep 10% of new traces
OTEL_PROPAGATORS=tracecontext,baggage                    # the default
```

- Older semantic conventions use `deployment.environment`; newer ones use `deployment.environment.name`. Use whichever your SDK and backend expect, consistently.
- Point exporters at a Collector (sidecar, agent or gateway), not at a vendor endpoint. Credentials and backend choice then live in one place.
- Shut the SDK down (flush) on process exit, or the last spans are lost.

## Java / Kotlin (JVM)

Zero-code: the Java agent instruments common frameworks, HTTP clients, JDBC and messaging.

```bash
# Download opentelemetry-javaagent.jar from the opentelemetry-java-instrumentation releases
java -javaagent:/otel/opentelemetry-javaagent.jar -jar app.jar
```

- The agent adds `trace_id` and `span_id` to the logging MDC for Logback and Log4j, so include them in the log pattern or JSON encoder.
- Manual spans: depend on `io.opentelemetry:opentelemetry-api` only and get a tracer with `GlobalOpenTelemetry.getTracer("checkout")`. Or annotate methods with `@WithSpan` (from the instrumentation annotations artifact).
- Spring Boot apps that cannot use an agent can use the OpenTelemetry Spring Boot starter. Check its docs for what it covers.

## Python

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install          # installs instrumentations for detected libraries
OTEL_SERVICE_NAME=checkout opentelemetry-instrument python app.py
```

- Log correlation: set `OTEL_PYTHON_LOG_CORRELATION=true` to add trace and span IDs to standard `logging` records, then include them in your formatter.
- Pre-fork servers (gunicorn, uWSGI) need the SDK initialized in each worker after fork. Follow the docs' pattern for your server.
- Manual spans:

```python
from opentelemetry import trace

tracer = trace.get_tracer("checkout")

def place_order(order):
    with tracer.start_as_current_span("checkout.place_order") as span:
        span.set_attribute("order.item_count", len(order.items))
        ...
```

## Node.js

```bash
npm install @opentelemetry/api @opentelemetry/auto-instrumentations-node
node --require @opentelemetry/auto-instrumentations-node/register app.js
```

- The SDK must load before any instrumented module (`http`, `express`, `pg`, ...). With the `--require` flag that happens automatically. In code-based setup, initialize the `NodeSDK` from `@opentelemetry/sdk-node` in a separate file that runs first.
- ES module apps need the loader-hook setup (`--import` plus a registration file). Check the current docs; it differs from CommonJS.
- Manual spans:

```js
const { trace, SpanStatusCode } = require('@opentelemetry/api');
const tracer = trace.getTracer('checkout');

async function placeOrder(order) {
  return tracer.startActiveSpan('checkout.place_order', async (span) => {
    try {
      return await doWork(order);
    } catch (err) {
      span.recordException(err);
      span.setStatus({ code: SpanStatusCode.ERROR });
      throw err;
    } finally {
      span.end();
    }
  });
}
```

## .NET

```bash
dotnet add package OpenTelemetry.Extensions.Hosting
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.Http
dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol
```

```csharp
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("checkout"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddSource("Checkout")            // your own ActivitySource
        .AddOtlpExporter())
    .WithMetrics(m => m
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddMeter("Checkout")             // your own Meter
        .AddOtlpExporter());

builder.Logging.AddOpenTelemetry(o => o.AddOtlpExporter());
```

- .NET uses its built-in `System.Diagnostics.ActivitySource` (spans) and `System.Diagnostics.Metrics.Meter` (metrics). Create one static `ActivitySource` per component and call `StartActivity("checkout.place_order")`. It returns null when nothing is listening, so use `?.`.
- A zero-code auto-instrumentation package for .NET also exists. Check the docs if you cannot change startup code.

## Go

```bash
go get go.opentelemetry.io/otel \
       go.opentelemetry.io/otel/sdk \
       go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc \
       go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp
```

```go
func initTracing(ctx context.Context) (func(context.Context) error, error) {
    exp, err := otlptracegrpc.New(ctx) // reads OTEL_EXPORTER_OTLP_* env vars
    if err != nil {
        return nil, err
    }
    tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exp)) // default resource reads OTEL_SERVICE_NAME
    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
        propagation.TraceContext{}, propagation.Baggage{}))
    return tp.Shutdown, nil
}

// Server: wrap the handler.   Client: wrap the transport.
handler := otelhttp.NewHandler(mux, "http.server")
client := &http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport)}
```

- Go has no implicit context. Pass `ctx` through every call and build outbound requests with `http.NewRequestWithContext(ctx, ...)`, or the trace breaks.
- Manual spans: `ctx, span := otel.Tracer("checkout").Start(ctx, "checkout.place_order"); defer span.End()`.

## Propagating context through message queues

Auto-instrumentation covers some messaging clients. Where it does not, inject on publish and extract on consume:

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("orders")

# Producer
headers = {}
inject(headers)                                   # adds traceparent (and tracestate/baggage)
producer.send("orders", value=payload, headers=[(k, v.encode()) for k, v in headers.items()])  # Kafka header values are bytes

# Consumer
ctx = extract({k: v.decode() for k, v in message.headers})
with tracer.start_as_current_span("orders process", context=ctx, kind=SpanKind.CONSUMER):
    handle(message)
```

Other languages expose the same `inject`/`extract` calls on the global propagator.

## Collector

Minimal gateway configuration:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 25
  batch: {}

exporters:
  otlp:
    endpoint: tracing-backend.example.internal:4317

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
```

- Put `memory_limiter` first in each processor list and `batch` near the end.
- Strip sensitive attributes centrally, as a safety net, with the `attributes` processor (`action: delete`) or the contrib `redaction` processor.
- Validate a configuration before you deploy it: `otelcol validate --config=config.yaml`. The binary name differs by distribution, for example `otelcol-contrib`.

### Tail sampling

Keep every error trace and slow trace, plus a baseline percentage of the rest (the `tail_sampling` processor is in the contrib distribution):

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 1000 }
      - name: baseline
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }
```

All spans of one trace must reach the same Collector instance. With several gateways, route by trace ID first (for example with the load-balancing exporter).

## Verify the setup

1. Send one request through the service and find its trace in the backend. Check that the service name is correct, not `unknown_service`.
2. Check that a downstream call appears as a child span, in the downstream service, under the same trace ID.
3. Force an error and check that the span has error status, a recorded exception, and a log line carrying the same `trace_id`.
4. Grep the exported data for tokens, passwords, emails and other secrets or PII before rolling out widely.
