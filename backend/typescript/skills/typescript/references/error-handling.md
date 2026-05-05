# Error Handling — Deep Dive

JavaScript's primary error-handling mechanism is `throw` and `try`/`catch`. TypeScript inherits it. This file covers how to use it well — typed errors, narrowing in `catch`, error chaining, async error handling, error boundaries — and concludes with one alternative pattern (`Result<T, E>`) that some codebases prefer for recoverable, expected failures.

## `throw new Error(...)` — The Default

The conventional pattern: throw an `Error` (or subclass) when something goes wrong, catch it where you can recover.

```ts
function parseAge(s: string): number {
  const n = Number(s);
  if (!Number.isFinite(n)) throw new Error(`Not a number: ${s}`);
  if (n < 0)               throw new Error(`Negative age: ${n}`);
  return n;
}

try {
  const age = parseAge(input);
  console.log("age:", age);
} catch (e) {
  if (e instanceof Error) console.error("parse failed:", e.message);
  else                    console.error("parse failed:", String(e));
}
```

Three rules to internalize before anything else:

1. **Always `throw new Error(...)`, never `throw "string"` or `throw { msg: "..." }`.** Non-Error values lose stack traces, defeat `instanceof Error` narrowing, and confuse logging tools.
2. **Catch the narrowest scope you can recover from.** A `try`/`catch` that wraps half a file is a maintenance burden. Wrap the call (or small block) where recovery makes sense.
3. **`catch (e: unknown)`, then narrow.** With `strict` (specifically `useUnknownInCatchVariables`), `e` is `unknown`. Don't widen to `any`; check `instanceof Error` and handle the rest.

## Custom Error Subclasses

For typed errors that callers can distinguish, subclass `Error`:

```ts
class HttpError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "HttpError";
  }
}

class ValidationError extends Error {
  constructor(public readonly field: string, message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

class TimeoutError extends Error {
  constructor(public readonly elapsedMs: number) {
    super(`Operation timed out after ${elapsedMs}ms`);
    this.name = "TimeoutError";
  }
}
```

Conventions:

- **Always set `this.name`** to the class name. Default `Error` displays name in stack traces; subclasses often display `"Error"` instead of the subclass name unless you set it explicitly.
- **Add structured fields** (`status`, `field`, `elapsedMs`) for the data callers will branch on. Don't bury it in the message.
- **Avoid deep hierarchies.** `class NotFoundError extends HttpError extends Error` is rarely worth the complexity. Flat subclasses of `Error` work for almost every case.

Callers can then narrow:

```ts
try {
  const data = await fetchUser(id);
} catch (e) {
  if (e instanceof HttpError && e.status === 404) {
    return showNotFound();
  }
  if (e instanceof TimeoutError) {
    return retryLater();
  }
  if (e instanceof ValidationError) {
    return highlightField(e.field);
  }
  throw e;   // re-throw what we don't know how to handle
}
```

The `throw e` at the end is important: catching everything and silently dropping unrecognized errors hides real bugs. Re-throw what you can't handle.

## Narrowing `catch (e: unknown)`

With `strict`, `e` is `unknown`. You **must** narrow before using it:

```ts
try {
  doThing();
} catch (e) {
  if (e instanceof Error)    return e.message;
  if (typeof e === "string") return e;        // some libraries throw strings
  return JSON.stringify(e);                    // last resort
}
```

A reusable helper:

```ts
function errorMessage(e: unknown): string {
  if (e instanceof Error)    return e.message;
  if (typeof e === "string") return e;
  return "Unknown error";
}
```

**Never write `catch (e: any)`.** The runtime can throw literally anything (string, number, plain object, `null`). `unknown` is the correct type.

## `Error.cause` — Chaining Errors

ES2022 added `Error.cause` for wrapping an error while preserving the original:

```ts
async function loadDashboard(userId: string): Promise<Dashboard> {
  try {
    return await fetchDashboardData(userId);
  } catch (e) {
    throw new Error("dashboard load failed", { cause: e });
  }
}
```

When the outer error is caught, `(e as Error).cause` gives you the original. Modern Node and browsers print the chain in stack traces:

```
Error: dashboard load failed
    at loadDashboard (...)
[cause]: HttpError: 502 Bad Gateway
    at fetchDashboardData (...)
```

Use `cause` when:
- You're translating a low-level error into a domain-level one (`HttpError` → `DashboardLoadError`) and want to preserve the underlying cause for debugging.
- You're wrapping an error to add context but the original detail is still relevant.

```ts
class DashboardLoadError extends Error {
  constructor(public readonly userId: string, cause: unknown) {
    super(`Failed to load dashboard for user ${userId}`, { cause });
    this.name = "DashboardLoadError";
  }
}
```

## Async Error Handling

`async`/`await` makes async code look synchronous, including error handling:

```ts
async function loadUser(id: string, signal: AbortSignal): Promise<User> {
  try {
    const res = await fetch(`/users/${id}`, { signal });
    if (!res.ok) throw new HttpError(res.status, `failed to load user ${id}`);
    return await res.json() as User;
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw e;   // let cancellations propagate cleanly
    }
    throw new Error(`loadUser(${id}) failed`, { cause: e });
  }
}
```

A few async-specific gotchas:

**Errors in `Promise.all` come from whichever rejects first.** The other promises keep running; their failures (if any) become unhandled rejections.

```ts
// Better: surface all errors, not just the first
const results = await Promise.allSettled([loadA(), loadB(), loadC()]);
const errors  = results.filter((r) => r.status === "rejected").map((r) => r.reason);
if (errors.length > 0) throw new AggregateError(errors, "some loads failed");
```

**`AggregateError`** is the standard error type for "multiple things failed." `Promise.any` throws an `AggregateError` when all input promises reject.

**Forgetting to await `throws` after the function returns.**

```ts
// Bad — error becomes an unhandled rejection
function process() {
  loadUser("1");   // promise discarded; if it rejects, no handler
  return "done";
}

// Good — await it (or return it for the caller to await)
async function process() {
  await loadUser("1");
  return "done";
}
```

See [async-and-cancellation.md](async-and-cancellation.md) for the full async picture.

## Reserve `throw` for Genuine Errors

`throw` is for things that interrupt normal flow. Some failures aren't errors at all:

```ts
// Bad — using throw for a normal "not found" case
function findUser(id: string): User {
  const u = users.get(id);
  if (!u) throw new Error("not found");
  return u;
}

// Better — return undefined for absence
function findUser(id: string): User | undefined {
  return users.get(id);
}

// Or, when callers should be forced to handle:
function getUser(id: string): User {
  const u = users.get(id);
  if (!u) throw new Error(`User ${id} not found`);
  return u;
}
```

Convention: the **`find` prefix returns `T | undefined`** (absence is a normal outcome). The **`get` prefix throws on absence** (caller asserted the value exists). Pick a convention and document it.

The rule: `throw` should signal "the caller can't continue without handling this." If "the caller can keep going with `undefined`" is acceptable, return `undefined` instead.

## When to Throw and When to Return

A useful taxonomy:

| Failure kind | What to do | Example |
|---|---|---|
| Programmer error / invariant violation | `throw new Error(...)` | Empty array passed to `head()` |
| Configuration error at startup | `throw` and let the process exit | Missing required env var |
| Truly unreachable case | `throw new Error("unreachable")` after `_: never` | Discriminated-union default |
| Unrecoverable runtime failure | `throw` (typed subclass) | Out-of-memory, fatal IO |
| Recoverable, common failure | Return value indicating failure (`undefined`, `null`, or `Result`) | "Not found" lookup |
| Validation error in user input | Return error or throw a typed `ValidationError` (project convention) | Form field invalid |
| Network / external-system failure | Throw a typed error or return `Result` (project convention) | HTTP 500, timeout |

For the last three rows, project convention dictates the choice. Pick **one** convention per module's API surface — don't mix throw and return-error styles for the same kind of failure within one module.

## Error Boundaries

A useful pattern: a single place at the top of an operation where errors are caught, logged, and translated into a user-meaningful response. Examples:

- HTTP request handler — catch any error from the route, log it, return an HTTP error response.
- React error boundary — catch render errors in a subtree, show a fallback UI.
- Event handler — catch errors so a single event doesn't crash the listener loop.

```ts
async function handleRequest(req: Request): Promise<Response> {
  try {
    return await routeRequest(req);
  } catch (e) {
    const id = randomId();
    logger.error("request failed", { id, error: e });
    if (e instanceof HttpError) {
      return new Response(e.message, { status: e.status });
    }
    return new Response(`Internal Server Error (${id})`, { status: 500 });
  }
}
```

The error boundary is the place that turns "something threw" into an outcome the system can keep running on. Inside the boundary, code throws freely. Outside, the system has a normal value.

## Logging Errors

When you log an error, log the full thing — not just the message. The stack trace is critical:

```ts
// Bad
logger.error("failed: " + e.message);

// Good
logger.error("failed", { error: e });

// Or with structured fields:
logger.error("user fetch failed", {
  userId: id,
  error: e instanceof Error ? { name: e.name, message: e.message, stack: e.stack } : e,
});
```

Modern structured loggers handle `Error` instances natively — pass the error itself, don't stringify it.

## An Alternative: `Result<T, E>` for Recoverable Failures

Some codebases — particularly those leaning toward functional patterns — prefer to return errors as values rather than throw them. The pattern:

```ts
type Result<T, E> =
  | { ok: true;  value: T }
  | { ok: false; error: E };

const ok  = <T, E = never>(value: T): Result<T, E> => ({ ok: true,  value });
const err = <E, T = never>(error: E): Result<T, E> => ({ ok: false, error });

async function fetchUser(id: string, signal: AbortSignal): Promise<Result<User, FetchError>> {
  try {
    const res = await fetch(`/users/${id}`, { signal });
    if (!res.ok) return err({ kind: "http", status: res.status });
    return ok(await res.json() as User);
  } catch (e) {
    return err({ kind: "network", message: errorMessage(e) });
  }
}
```

Callers branch on `.ok`:

```ts
const r = await fetchUser("u-1", signal);
if (!r.ok) {
  switch (r.error.kind) {
    case "http":    return showHttpError(r.error.status);
    case "network": return retryLater();
  }
}
showUser(r.value);
```

**Tradeoffs vs throw/catch:**

Pros:
- Errors appear in the function signature — callers know what can go wrong without reading the implementation.
- The compiler enforces handling: `r.value` is unreachable until you check `r.ok`.
- Cleaner pipelines when chaining many operations that can each fail (see [composition.md](composition.md)).

Cons:
- Verbose for code that doesn't actually want to handle errors (most of the time, you want to bail out).
- Doesn't compose naturally with throw-based libraries — every call needs a `try`/`catch` wrapper to lift into `Result`.
- Less familiar to colleagues coming from throw-based codebases.

**When `Result` fits well:**
- Pipelines where many steps can each fail and you want short-circuit + typed errors.
- Public API surfaces where the contract benefits from making error cases explicit.
- Codebases that have committed to the functional style end-to-end.

**When `throw` is simpler:**
- One-off failures that propagate up to a single error boundary.
- Most application code that doesn't need fine-grained per-step error handling.
- Integration with throw-based ecosystems.

Most TypeScript codebases use throw/catch as the default and reach for `Result` only in specific places. A few go the other way. **Pick one as the default per module/package** and stay consistent — mixing both styles in one API forces callers to handle both.

If you adopt `Result`, define it once in a shared utility module (the 5 lines above) and import from there. No library is required.

## Common Pitfalls

- **`throw "string"` or `throw { msg: ... }`.** Always `throw new Error(...)`. Stack traces matter.
- **`catch (e: any)`.** With `strict`, `e` is `unknown`. Narrow with `instanceof Error` and other checks.
- **Catching errors and silently dropping them.** A `catch (e) {}` block hides bugs. Either log + re-throw, or convert to a meaningful return value.
- **Catching `Error` and accessing `e.message` without checking `instanceof Error` first.** With `useUnknownInCatchVariables`, this is a compile error — but it's also semantically wrong.
- **`throw` for normal control flow.** "User not found" is not an exception; it's a result. Return `undefined` or a `Result`.
- **Deep `try`/`catch` nesting.** Catch at meaningful boundaries (one per request, one per top-level operation). Don't wrap every line.
- **Custom Error subclasses without setting `this.name`.** Stack traces will display "Error" instead of your subclass name.
- **Using `throw` from inside an `async` function and not handling the promise rejection.** The error becomes an unhandled rejection. Always `await` async functions or attach `.catch`.
- **`Promise.all` when partial failure should be tolerated.** Use `Promise.allSettled` and partition.
- **Re-throwing without preserving the original.** If you wrap an error, use `Error.cause` so debug context isn't lost.
- **Mixing `throw` and `Result` for the same kind of failure in one API.** Callers have to defend against both. Pick one.
- **Logging errors as strings (`logger.error(e.message)`).** Strips the stack trace. Pass the whole error so the logger can serialize it properly.
- **`Promise<Result<T, E>>` that also rejects.** Defeats the purpose. If you adopt `Result`, never `throw` from a function that returns one — convert internally.
