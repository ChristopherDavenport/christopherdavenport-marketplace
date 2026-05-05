# Async & Cancellation — Deep Dive

`Promise` and `async`/`await` are the foundation. `AsyncIterable` handles streaming. `AbortSignal` handles cancellation as a first-class concern. Together they cover ~all of what async TypeScript needs — without runtime-specific APIs.

## `async`/`await` Over `.then` Chains

Both work; `async`/`await` reads better and produces clearer stack traces.

```ts
// .then chain — flow is harder to follow, errors split across .catch
function loadUser(id: string): Promise<User> {
  return fetch(`/users/${id}`)
    .then((res) => res.json())
    .then((data) => parseUser(data));
}

// async/await — linear, errors go to one catch
async function loadUser(id: string): Promise<User> {
  const res  = await fetch(`/users/${id}`);
  const data = await res.json();
  return parseUser(data);
}
```

The two cases where `.then` still wins:

1. **Simple value transformation in a single expression** — `myPromise.then(JSON.stringify)` is shorter than wrapping in an arrow.
2. **`.catch` for ergonomic fallback** — `risky().catch(() => fallback)` is one line; the `try`/`catch` equivalent is four. But for anything beyond a single line, switch to `try`/`catch`.

## Sequential vs Parallel Execution

The most common async performance bug: awaiting in a loop when the operations could be parallel.

```ts
// Sequential — each awaits the previous (slow)
const results: User[] = [];
for (const id of ids) {
  results.push(await fetchUser(id));
}

// Parallel — fire all at once, await all (fast)
const results = await Promise.all(ids.map((id) => fetchUser(id)));
```

Use sequential `await` when:
- Each step depends on the previous
- You need to short-circuit on the first error
- Backpressure matters (don't fire 10,000 requests at once)

Use parallel `Promise.all` when:
- Operations are independent
- Total time = max(individual times), not sum
- Failure of any → failure of the whole (acceptable)

## `Promise.all` / `allSettled` / `any` / `race`

Four combinators, each for a different shape of "I have N promises, what do I want?":

| Combinator | Resolves when | Rejects when | Use when |
|---|---|---|---|
| `Promise.all` | All resolve | First rejects | All-or-nothing parallelism (N requests, one missing → fail) |
| `Promise.allSettled` | All settle | Never | Best-effort parallelism (collect results and errors per-item) |
| `Promise.any` | First resolves | All reject | Race for any successful result (fallbacks, redundant servers) |
| `Promise.race` | First settles | First settles (if rejection) | Time-boxed wait, generic race |

```ts
// Fail-fast parallel
const users = await Promise.all(ids.map(fetchUser));

// Best-effort parallel — never throws
const settled = await Promise.allSettled(ids.map(fetchUser));
const ok    = settled.filter((s) => s.status === "fulfilled").map((s) => s.value);
const errs  = settled.filter((s) => s.status === "rejected").map((s) => s.reason);

// First success wins
const fastest = await Promise.any([primary(), backup1(), backup2()]);

// Generic race
const winner = await Promise.race([slowOp(), timeout(5000)]);
```

`Promise.race` rejects on the first rejection — usually `Promise.any` is what you want.

## `AsyncIterable<T>` and `for await ... of`

For streams of values produced over time, `AsyncIterable<T>` is the standard interface. `for await ... of` consumes them with backpressure — each iteration awaits the next value.

```ts
async function* paginate(start: string): AsyncIterable<Page> {
  let cursor: string | undefined = start;
  while (cursor !== undefined) {
    const page = await fetchPage(cursor);
    yield page;
    cursor = page.nextCursor;
  }
}

for await (const page of paginate("first")) {
  process(page);  // each iteration awaits the producer
}
```

`async function*` defines an **async generator** — a function that produces an `AsyncIterable<T>`. `yield` produces a value; the consumer pulls it via `for await`.

The mental model: a synchronous generator is `Iterable<T>`; an async generator is `AsyncIterable<T>`. Same shape, just async.

Use cases:
- Pagination (fetch a page, yield it, fetch the next)
- Server-sent events
- File chunks
- Long-running computations producing intermediate results
- Anywhere you want a stream without buffering the whole thing

## Cancellation: `AbortSignal` as a First-Class Concern

Long-running async work needs to be cancelable. The standard mechanism is `AbortSignal` — a web-platform API that's universally available across runtimes.

### The pattern

Every long-running async function takes a `signal?: AbortSignal`:

```ts
async function fetchUser(id: string, signal?: AbortSignal): Promise<User> {
  const res = await fetch(`/users/${id}`, { signal });
  return parseUser(await res.json());
}
```

The signal:
- Is created via `const controller = new AbortController(); controller.signal`
- Is **aborted** by calling `controller.abort(reason?)`
- Carries the abort reason (defaults to a `DOMException` named `"AbortError"`)
- Has a `.aborted` boolean and an `addEventListener("abort", ...)` for callbacks
- Has `.throwIfAborted()` to imperatively bail at suspension points

```ts
const controller = new AbortController();
// abort after 5 seconds
setTimeout(() => controller.abort(new Error("timeout")), 5000);

try {
  const user = await fetchUser("u-1", controller.signal);
} catch (e) {
  if (controller.signal.aborted) {
    // handle cancellation
  } else {
    // handle other error
  }
}
```

### `signal.throwIfAborted()`

Call at suspension points in your own async code:

```ts
async function process(items: readonly string[], signal: AbortSignal): Promise<void> {
  for (const item of items) {
    signal.throwIfAborted();      // bail if cancelled
    await doWork(item, signal);    // pass signal to nested calls
  }
}
```

This makes cancellation observable mid-loop without writing `if (signal.aborted) throw signal.reason` by hand at every step.

### `signal.addEventListener("abort", ...)`

For cleanup that needs to run when the signal aborts (closing a connection, removing a subscription):

```ts
function watchValue(signal: AbortSignal): Promise<Value> {
  return new Promise((resolve, reject) => {
    const subscription = subscribe((v) => resolve(v));
    signal.addEventListener("abort", () => {
      subscription.unsubscribe();
      reject(signal.reason);
    });
  });
}
```

### Propagating signals

**Always pass the signal through to nested async calls.** A function that takes a signal and doesn't propagate it to its async children is broken — cancellation will only affect the current await, not what it kicked off.

```ts
async function loadDashboard(userId: string, signal: AbortSignal): Promise<Dashboard> {
  // GOOD — both calls receive the signal
  const [user, prefs] = await Promise.all([
    fetchUser(userId, signal),
    fetchPrefs(userId, signal),
  ]);
  return { user, prefs };
}
```

### Combining signals: `AbortSignal.any`

Combine multiple signals into one — aborts when any of them aborts:

```ts
const userCancel = controller.signal;
const timeout    = AbortSignal.timeout(5000);

const combined = AbortSignal.any([userCancel, timeout]);
await fetchUser("u-1", combined);
// Aborts on whichever fires first.
```

`AbortSignal.timeout(ms)` returns a signal that auto-aborts after `ms` milliseconds — much cleaner than `setTimeout`.

## Never Swallow Rejections

```ts
// Bug: ignored promise — rejection becomes an unhandled rejection
fetchUser("u-1", signal);

// Bug: returned but caller doesn't await — same problem
function process() {
  doAsync();
  return "done";
}
```

Every promise must either be `await`'d, returned to a caller that will await it, or have an explicit `.catch` (or `.then(..., onRejected)`).

For "fire and forget" intentionally:

```ts
void fetchUser("u-1", signal).catch((e) => {
  console.error("background fetch failed", e);
});
```

The `void` operator declares "I'm intentionally discarding this." The `.catch` ensures rejections aren't unhandled.

In an editor with `@typescript-eslint/no-floating-promises` enabled, the bare `fetchUser()` call would be flagged. Recommended.

## `unhandledRejection` is a Bug

When a promise rejects with no handler attached, the runtime fires an `unhandledRejection` event. Treat this as a bug — somewhere a promise is being created without an error path.

To find unhandled rejections in your own code: enable strict ESLint rules (`no-floating-promises`, `no-misused-promises`) and the TypeScript flag `noUnusedLocals`. Together they catch most cases at lint time.

## `Promise.withResolvers`

For deferred-creation patterns (you need the promise before the producer of its value is wired up):

```ts
const { promise, resolve, reject } = Promise.withResolvers<User>();

setupCallback((user) => resolve(user));
setupErrorCallback((err) => reject(err));

const result = await promise;
```

Equivalent to the older `new Promise((res, rej) => { /* capture res/rej */ })` pattern, without the closure dance.

Use when integrating with callback-based APIs that fire once. For multi-fire (event streams), use `AsyncIterable` instead.

## Composing Async with `Result`

`Result<T, E>` from [error-handling.md](error-handling.md) and `Promise` compose. Helpers like `mapResult` work the same on `Result<T, E>` whether wrapped in a `Promise` or not:

```ts
const map = <T, U, E>(r: Result<T, E>, f: (t: T) => U): Result<U, E> =>
  r.ok ? { ok: true, value: f(r.value) } : r;

const mapAsync = async <T, U, E>(
  r: Promise<Result<T, E>>,
  f: (t: T) => U | Promise<U>,
): Promise<Result<U, E>> => {
  const v = await r;
  return v.ok ? { ok: true, value: await f(v.value) } : v;
};
```

This is how a Result-based codebase composes pipelines — see [composition.md](composition.md).

## Common Pitfalls

- **`for ... of` with `await` when independent calls could be parallel.** Convert to `Promise.all(arr.map(...))` whenever the operations don't depend on each other.
- **`Promise.all` when one failure shouldn't fail the rest.** Use `Promise.allSettled` and partition the results.
- **Forgetting to pass `signal` through to nested calls.** Cancellation aborts only what's actively awaiting at the top level; the dispatched work keeps running.
- **`new Promise((res, rej) => { ... })` for things that can be done with `async function`.** The constructor form is for genuinely async, non-promise APIs (callbacks, events). For `await` chains, just write `async function`.
- **Floating promises.** A function call returning a promise that's not awaited or `.catch`'d is a bug waiting to happen. Lint for it.
- **`async` functions that don't `await` anything.** A function declared `async () => { return 42 }` returns `Promise<number>`, but the work isn't async. Just return `42` from a plain function.
- **`try`/`catch` around `await` of a `Promise<Result<T, E>>`.** The Result form already encodes the error. Catching defeats the design.
- **`Promise.race` to time out without canceling.** The race resolves but the slow operation keeps running in the background. Use `AbortSignal.timeout` instead so the slow op gets cancelled.
- **Passing `AbortSignal` only at the top — not into helpers.** Cancellation half-works. Audit nested calls; every async helper should accept an optional signal.
- **Catching `AbortError` and proceeding as if successful.** If the work was cancelled, downstream code should *also* abort. Re-check `signal.aborted` after the catch, or rethrow.
- **Async generators that ignore the `return()` signal.** When a `for await` loop breaks, the generator's `return()` is called. Long-running generators should respect this — wrap producer code in `try`/`finally` to clean up.
