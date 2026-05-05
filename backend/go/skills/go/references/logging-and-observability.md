# Logging & Observability — Deep Dive

Go 1.21 added `log/slog` to the stdlib — a structured, leveled logger that supersedes the older `log` package for new code. Before 1.21 the community used `zap`, `logrus`, or `zerolog`; for new projects, prefer `slog` unless you have a specific reason.

## `log/slog` API

```go
import "log/slog"

slog.Info("server started", "addr", ":8080", "tls", true)
slog.Warn("retrying", "attempt", 3, "err", err)
slog.Error("request failed", "method", r.Method, "path", r.URL.Path, "err", err)
```

Key/value pairs after the message become structured attributes. The default handler renders to stderr in a key=value text format; switch to JSON for production:

```go
logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))
slog.SetDefault(logger)
```

After `SetDefault`, all package-level calls (`slog.Info`, etc.) use that logger. The stdlib `log` package also routes through `slog.Default()`.

## Levels

Standard levels are `Debug`, `Info`, `Warn`, `Error`. Configure the threshold:

```go
opts := &slog.HandlerOptions{Level: slog.LevelDebug}
logger := slog.New(slog.NewJSONHandler(os.Stderr, opts))
```

For runtime-changeable levels:

```go
var lvl slog.LevelVar             // defaults to Info
opts := &slog.HandlerOptions{Level: &lvl}
// ... later
lvl.Set(slog.LevelDebug)
```

`LevelVar` is safe for concurrent use.

## Structured Attributes

Two forms of attribute syntax:

```go
// Variadic key/value pairs (concise)
slog.Info("user login", "user_id", id, "ip", ip)

// Pre-built Attr (typed, slightly faster, lets you reuse attribute lists)
slog.Info("user login",
    slog.Int("user_id", id),
    slog.String("ip", ip),
    slog.Duration("latency", elapsed),
)
```

The variadic form is convenient but has a footgun: an odd number of args (forgotten value) silently logs an attribute with key `!BADKEY`. The `slog.X(...)` form is type-checked at compile time.

Available builders: `slog.Int`, `slog.Int64`, `slog.Uint64`, `slog.Float64`, `slog.String`, `slog.Bool`, `slog.Duration`, `slog.Time`, `slog.Any` (catch-all), `slog.Group` (nested attributes).

## `slog.Group` for Nested Structure

```go
slog.Info("request handled",
    slog.Group("request",
        slog.String("method", r.Method),
        slog.String("path", r.URL.Path),
    ),
    slog.Group("response",
        slog.Int("status", code),
        slog.Duration("duration", elapsed),
    ),
)
```

Groups become nested objects in JSON output and `request.method=...` style in text output.

## `Logger.With` — Carry Context Through a Call Tree

```go
log := slog.With("request_id", reqID, "user_id", uid)
log.Info("validated input")
log.Info("saved to database")
// Both lines include request_id and user_id
```

`With` returns a new logger with the given attributes "baked in". Use this at request entry to carry correlation IDs through subsequent calls.

## Errors in Logs

```go
slog.Error("database query failed",
    "err", err,                        // string-formatted via err.Error()
    slog.String("query", "SELECT ..."),
)
```

For richer error data, attach the error type explicitly:

```go
var pathErr *os.PathError
if errors.As(err, &pathErr) {
    slog.Error("io failed",
        "err", err,
        "path", pathErr.Path,
        "op", pathErr.Op,
    )
}
```

## Context-Aware Logging

`slog.InfoContext`, `slog.ErrorContext`, etc. accept a context. Custom handlers can extract values (request ID, trace ID):

```go
slog.InfoContext(ctx, "processing", "items", n)
```

A custom handler can pull `trace.SpanFromContext(ctx)` and emit trace correlation automatically.

## When to Log

- **Log at boundaries** — incoming requests, outgoing calls, batch starts/ends, lifecycle events
- **Log errors at the place that handles them**, not at every layer that propagates them. Logging at every layer multiplies the noise on a single failure.
- **Don't log inside tight loops** — sampling or aggregation belongs in metrics, not logs

## When NOT to Log

- When the function returns an error that the caller will handle and log
- For routine flow (entry/exit of every function) — use traces for that
- For validation failures the user already sees (the API response carries the error)

## Logs vs Metrics vs Traces

The "three pillars":

- **Logs** — discrete events with rich context; high cardinality; expensive at scale; great for debugging individual cases
- **Metrics** — numeric, aggregated, low cardinality; cheap; great for dashboards and alerts (`prometheus/client_golang`, `OpenTelemetry`)
- **Traces** — request flow across services with timing; great for "why is this slow" questions (`OpenTelemetry`)

**A request's full debug story usually needs all three.** Log the unusual events; meter the rates and latencies; trace the call graph. Don't try to do alerting from logs (expensive, slow) or detailed forensics from metrics (no context).

## `log/slog` and the Old `log` Package

The legacy `log` package (`log.Printf`, `log.Fatal`) still works. After `slog.SetDefault`, those calls flow through the slog handler. New code should use `slog` directly; only `log` calls in dependencies need the bridge.

`log.Fatal` and `log.Panic` still call `os.Exit(1)` and `panic` respectively — `slog` does not have direct equivalents. For "log and crash" at startup:

```go
slog.Error("startup failed", "err", err)
os.Exit(1)
```

## Library Code: Don't Log

**Library packages should not log directly.** They should:

- Return errors with enough context to log meaningfully
- Optionally accept an `*slog.Logger` from the caller for verbose tracing
- Never call `slog.Default()` themselves — leaves no escape for the caller to control output

```go
// ✗ Library logs unconditionally
package httpclient
func Get(url string) ([]byte, error) {
    slog.Info("GET", "url", url)        // caller can't suppress this
    ...
}

// ✓ Library returns an error; or accepts a logger
package httpclient
type Client struct {
    log *slog.Logger        // optional; default to slog.Default() only if nil
}
```

Application/service code (your `cmd/` and top-level packages) is where logging happens.

## Sampling

For hot code paths where you want occasional visibility without flooding logs, sample:

```go
if rand.IntN(1000) == 0 {
    slog.Info("sampled cache miss", "key", k)
}
```

Or use a dedicated sampler from a library like `zap.SamplingConfig`. Most production apps need this somewhere.

## Sensitive Data in Logs

Never log:

- Passwords, API keys, tokens, secrets
- Full PII (full SSN, full credit card)
- Encryption keys, TLS private material

Mask or redact:

```go
slog.Info("user login", "email", maskEmail(user.Email))    // a@b.com → a***@b.com
```

Implement a custom `slog.Handler` to redact based on attribute names if your team has a strict policy.

## Common Pitfalls

- **Variadic key/value with odd arg count** — `!BADKEY` in output. Use `slog.X(...)` builders for compile-time safety in production.
- **Using `slog.Default()` inside libraries** — caller can't control output. Accept a `*slog.Logger` parameter instead.
- **Logging AND returning the same error** — duplicates lines across log layers. Pick one (usually log at the top).
- **Logging inside hot loops** — fills logs with noise. Sample or aggregate to a metric.
- **Logging secrets** — leak vector. Add a redaction policy to the handler or pre-mask values.
- **Mixing `log` and `slog`** — fine after `slog.SetDefault`, but avoid in new code; convert `log.Printf` to `slog.Info`.
- **Treating logs as the alerting source** — expensive. Promote anything you alert on to a metric.
- **No structured fields, just formatted strings** — `slog.Info(fmt.Sprintf("user %d login", id))` defeats the point. Use attributes: `slog.Info("user login", "user_id", id)`.
- **Different attribute keys for the same concept across services** — `user_id` vs `userId` vs `uid`. Agree on a schema; logs are cheap until you try to query them.
- **Missing trace correlation** — under load, you can't tie log lines to a specific request. Always carry `request_id` (or trace ID) via `slog.With` at request entry.
