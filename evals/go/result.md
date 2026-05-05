# Eval report: `go`

- Cases: **8**
- Expectations met: **2/8** (skill_wins 1/6, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **1**, baseline won **0**, ties **7**
- Rubric pass-rate (over 7 scored case(s)): baseline **86%**, skill **86%** (Δ **+0%**)
- CLI cost: **$0.54** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `error-wrapping` | skill_wins | ✗ | **tie** | 100% | 100% |
| `goroutine-lifetime` | skill_wins | ✗ | **tie** | 100% | 100% |
| `receiver-consistency` | skill_wins | ✗ | **tie** | 100% | 100% |
| `interface-placement` | skill_wins | ✗ | **tie** | 100% | 100% |
| `slog-structured` | skill_wins | ✗ | **tie** | 100% | 100% |
| `generic-min` | skill_wins | ✓ | **skill** | 100% | 100% |
| `simplest-error` | skill_wins_strict | ✗ | **tie** | 0% | 0% |
| `offtopic-css-grid` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `error-wrapping`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I have a Go function that opens a config file and just does
`return os.Open(path)`. Callers get errors like
"open /etc/foo.yml: no such file or directory" with no hint of which
subsystem hit it. What's the right way to fix this?
```

**Judge:** **tie** — Both answers are excellent and cover all four rubric criteria equally well: both use %w, mention errors.Is and errors.As with concrete examples, use fmt.Errorf for context, and explicitly warn against %v/%s as the anti-pattern. The differences are stylistic — Answer A notes the message duplication issue with os.PathError and suggests a cleaner wrap, while Answer B adds errors.Join and a sentinel error example. Neither is meaningfully better on the judging criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses %w directive | tie |
| mentions errors.Is or errors.As | tie |
| uses fmt.Errorf for context | tie |
| avoids %v wrapping anti-pattern | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses %w directive | ✓ | `%w` |
| mentions errors.Is or errors.As | ✓ | `errors.Is` |
| uses fmt.Errorf for context | ✓ | `fmt.Errorf` |
| avoids %v wrapping anti-pattern | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses %w directive | ✓ | `%w` |
| mentions errors.Is or errors.As | ✓ | `errors.Is` |
| uses fmt.Errorf for context | ✓ | `fmt.Errorf` |
| avoids %v wrapping anti-pattern | ✓ | |

<details><summary>Baseline answer</summary>

# Wrap the error with context using `fmt.Errorf` and `%w`

The idiomatic Go fix is to **wrap** the error at the boundary so callers get context about *what* you were doing, while still being able to inspect the underlying error programmatically.

## The fix

```go
func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("config: open %q: %w", path, err)
    }
    return f, nil
}
```

Now the error reads:

```
config: open "/etc/foo.yml": open /etc/foo.yml: no such file or directory
```

The `config:` prefix tells you which subsystem hit it.

## Why `%w` and not `%v` or `%s`

The `%w` verb (Go 1.13+) **wraps** the original error rather than just stringifying it. That preserves two important capabilities:

```go
// 1. Sentinel checks still work
if errors.Is(err, os.ErrNotExist) {
    // create defaults, etc.
}

// 2. Type assertions still work
var pathErr *os.PathError
if errors.As(err, &pathErr) {
    log.Printf("syscall %s failed on %s", pathErr.Op, pathErr.Path)
}
```

If you used `%v`/`%s` instead, you'd flatten the chain and lose both of those.

## A few related guidelines

1. **Wrap once per layer, not at every call.** Each layer adds *its* context ("config:", "user service:", "http handler:"). Don't re-wrap the same error inside the same function.
2. **Don't include redundant words like `"failed to"` or `"error:"`** — Go errors are conventionally lowercase fragments that get joined with `:`. So `"open config %q: %w"` reads better than `"failed to open config: %w"` once nested.
3. **Include the dynamic bits** (the path, the user ID, the request ID) — those are what make a wrapped error actually useful in a log line.
4. **If you have multiple errors** to combine (e.g., a primary error plus a cleanup error), use `errors.Join` (Go 1.20+) rather than picking one to drop.
5. **Define a sentinel or typed error** if callers need to branch on this specific failure:

   ```go
   var ErrConfigMissing = errors.New("config: file missing")

   if errors.Is(err, os.ErrNotExist) {
       return nil, fmt.Errorf("%w: %s", ErrConfigMissing, path)
   }
   ```

## When *not* to wrap

- **In `main` or top-level handlers** — that's where you log/print, not wrap.
- **When the inner error already has all the context you'd add** (rare, but `*os.PathError` already has the op and path; if your subsystem name adds nothing, skip it).
- **Never** swallow the error with `fmt.Errorf("...: %s", err)` unless you've consciously decided callers should not be able to `errors.Is` it.

That single `%w` change is usually enough to make production logs go from "no idea where this came from" to "obviously the config loader."

</details>

<details><summary>Skill-loaded answer</summary>

# Wrapping Errors with Context in Go

The idiomatic fix is to use `fmt.Errorf` with the `%w` verb to wrap the error with context about *what your code was trying to do*, while preserving the original error for inspection.

## The fix

```go
func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("loadConfig: open %q: %w", path, err)
    }
    return f, nil
}
```

Now callers see:

```
loadConfig: open "/etc/foo.yml": open /etc/foo.yml: no such file or directory
```

The duplication in the message is a hint you can clean up — `os.PathError` already includes the op and path, so often you just want:

```go
return nil, fmt.Errorf("loadConfig: %w", err)
// → loadConfig: open /etc/foo.yml: no such file or directory
```

## Why `%w` and not `%v` or `%s`

- `%w` *wraps* the error — callers can still use `errors.Is` / `errors.As` to inspect it.
- `%v` / `%s` flatten it into a string and lose that ability.

So a caller can still do:

```go
f, err := loadConfig("/etc/foo.yml")
if errors.Is(err, fs.ErrNotExist) {
    // fall back to defaults
}

var pathErr *fs.PathError
if errors.As(err, &pathErr) {
    log.Printf("path %s failed op %s", pathErr.Path, pathErr.Op)
}
```

## Guidelines for good wrapping

1. **Add context the caller can't already infer.** Function name, subsystem, or the higher-level operation ("loading billing config", not just "open").
2. **Don't include the error's text in your prefix** — `%w` will append it. Avoid `fmt.Errorf("failed to open %s: %s: %w", path, err, err)`.
3. **Lowercase, no trailing punctuation.** Per Go convention, error strings are lowercase and don't end in `.` or `\n`, so they compose cleanly when wrapped further up the stack.
4. **Wrap at boundaries, not at every layer.** Wrapping in every function produces noisy "loadConfig: readSection: parseLine: ..." chains. Wrap when you cross a meaningful boundary (package, subsystem, RPC).
5. **Consider sentinel errors for expected cases.** If "config missing" is a normal condition, define `var ErrConfigMissing = errors.New("config missing")` and have callers branch on `errors.Is`.

## A slightly richer version

If multiple subsystems load configs, include the subsystem name so logs are greppable:

```go
func (s *BillingService) loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("billing: load config: %w", err)
    }
    return f, nil
}
```

That gives you log lines like `billing: load config: open /etc/foo.yml: no such file or directory` — which tells you both the subsystem and the underlying cause without losing programmatic access to the `fs.PathError`.

</details>

---

### `goroutine-lifetime`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Show me the basic Go pattern for running a periodic background task
(something that ticks every few seconds and does some work).
```

**Judge:** **tie** — Both answers are nearly identical in quality, correctly using context.Context, selecting on ctx.Done(), using time.NewTicker with defer ticker.Stop(), and explicitly avoiding time.Tick. Both cover the same key patterns and gotchas (immediate execution, slow work overlap, graceful shutdown with WaitGroup). Answer A provides a slightly more structured two-phase presentation (basic then production-ready), while Answer B is slightly more concise and uses atomic.Bool for the overlap guard which is more idiomatic than a mutex for that use case. The differences are minor enough to call this a tie.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.Context | tie |
| selects on ctx.Done | tie |
| uses time.NewTicker (preferred over time.Tick) | tie |
| avoids time.Tick (which leaks) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.Context | ✓ | `context.Context` |
| selects on ctx.Done | ✓ | `ctx.Done()` |
| uses time.NewTicker (preferred over time.Tick) | ✓ | `time.NewTicker` |
| avoids time.Tick (which leaks) | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.Context | ✓ | `context.Context` |
| selects on ctx.Done | ✓ | `ctx.Done()` |
| uses time.NewTicker (preferred over time.Tick) | ✓ | `time.NewTicker` |
| avoids time.Tick (which leaks) | ✓ | |

<details><summary>Baseline answer</summary>

Here's the standard Go pattern for a periodic background task using `time.Ticker`:

## Basic Pattern

```go
package main

import (
	"context"
	"log"
	"time"
)

func runPeriodic(ctx context.Context, interval time.Duration, work func()) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Println("stopping periodic task:", ctx.Err())
			return
		case t := <-ticker.C:
			log.Println("tick at", t)
			work()
		}
	}
}

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go runPeriodic(ctx, 5*time.Second, func() {
		// do some work here
		log.Println("doing work...")
	})

	// keep main alive (or wait on signals, etc.)
	time.Sleep(30 * time.Second)
	cancel()
}
```

## Key Points

1. **Always `defer ticker.Stop()`** — otherwise the ticker leaks resources until GC.
2. **Use `context.Context` for cancellation** — never rely on `time.Sleep` in a loop, since you can't interrupt it cleanly.
3. **`select` on both `ctx.Done()` and `ticker.C`** — this is what makes shutdown responsive.
4. **`time.NewTicker` (not `time.Tick`)** — `time.Tick` cannot be stopped and leaks.

## Production-Ready Variant (with graceful shutdown on signals)

```go
package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(),
		os.Interrupt, syscall.SIGTERM)
	defer stop()

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		runPeriodic(ctx, 5*time.Second, doWork)
	}()

	<-ctx.Done()
	log.Println("shutdown signal received")
	wg.Wait()
	log.Println("clean exit")
}

func doWork() {
	// your periodic work
}
```

## A Couple of Gotchas

- **Slow work**: if `work()` takes longer than `interval`, ticks will queue up to a small buffer, then drop. If you need to skip overlapping runs, guard with a `sync.Mutex` or a `chan struct{}` semaphore.
- **First tick is delayed by `interval`**: if you want immediate execution, call `work()` once before entering the loop.
- **Jitter**: for many workers hitting the same downstream, add a small random offset to avoid thundering herds.

</details>

<details><summary>Skill-loaded answer</summary>

# Periodic Background Task in Go

Here's the canonical pattern using `time.Ticker` with proper cancellation via `context.Context`:

```go
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func runPeriodic(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop() // always release the ticker

	for {
		select {
		case <-ctx.Done():
			fmt.Println("stopping:", ctx.Err())
			return
		case t := <-ticker.C:
			doWork(t)
		}
	}
}

func doWork(t time.Time) {
	fmt.Println("tick at", t.Format(time.RFC3339))
	// ... your work here ...
}

func main() {
	// Cancel on Ctrl-C / SIGTERM
	ctx, stop := signal.NotifyContext(
		context.Background(),
		os.Interrupt, syscall.SIGTERM,
	)
	defer stop()

	go runPeriodic(ctx, 5*time.Second)

	<-ctx.Done() // wait for shutdown signal
}
```

## Key points

1. **`time.NewTicker` over `time.Sleep`** — a ticker fires on a steady cadence and won't drift if your work occasionally takes longer than expected (it just drops ticks).
2. **Always `defer ticker.Stop()`** — frees the underlying timer resources.
3. **Drive cancellation with a `context.Context`** — the `select` lets the goroutine exit promptly when the context is cancelled.
4. **`signal.NotifyContext`** (Go 1.16+) ties graceful shutdown to OS signals in one line.

## Common variations

**Run immediately, then on each tick** (tickers don't fire at t=0):

```go
doWork(time.Now())
for {
    select {
    case <-ctx.Done():
        return
    case t := <-ticker.C:
        doWork(t)
    }
}
```

**Don't let slow work overlap** — wrap `doWork` in a guard or skip if a previous run is still in flight:

```go
var running atomic.Bool
case <-ticker.C:
    if !running.CompareAndSwap(false, true) {
        continue // previous tick still running, skip
    }
    go func() {
        defer running.Store(false)
        doWork(time.Now())
    }()
```

**Wait for the goroutine on shutdown** — use a `sync.WaitGroup` if `main` needs to know the worker has finished cleanly:

```go
var wg sync.WaitGroup
wg.Add(1)
go func() {
    defer wg.Done()
    runPeriodic(ctx, 5*time.Second)
}()
<-ctx.Done()
wg.Wait()
```

That's the whole pattern — ticker + context + select is the idiomatic backbone for nearly any periodic worker in Go.

</details>

---

### `receiver-consistency`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I have a struct `Counter` with a method `Inc()` that increments an
internal field. Should the receiver be a value `(c Counter)` or a
pointer `(c *Counter)`? Why?
```

**Judge:** **tie** — Both answers are excellent and cover all three rubric criteria: recommending a pointer receiver, explaining mutation visibility, and emphasizing consistency across methods. The differences are minor stylistic choices—Answer A mentions interface satisfaction more prominently while Answer B emphasizes the 'identity vs value' conceptual distinction and the sync.Mutex vet warning. Neither answer is meaningfully better than the other on the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends pointer receiver | tie |
| mentions consistency across methods on the type | tie |
| explains why (mutation visibility) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `Pointer Receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `Mutat` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `Pointer Receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `Mutat` |

<details><summary>Baseline answer</summary>

# Pointer Receiver: `(c *Counter)`

You should use a **pointer receiver** for `Inc()`. Here's why:

## The Core Reason: Mutation

In Go, value receivers operate on a **copy** of the struct. So if you wrote:

```go
func (c Counter) Inc() {
    c.count++ // modifies the local copy, lost when method returns
}
```

The increment would happen on the copy and be discarded when the method returns. The original `Counter` would never change.

With a pointer receiver:

```go
func (c *Counter) Inc() {
    c.count++ // modifies the actual Counter the caller holds
}
```

You're modifying the value the caller actually cares about.

## Supporting Reasons

Beyond correctness, pointer receivers are preferred here for several conventional reasons:

1. **Consistency**: Go's style guide recommends that if *any* method on a type needs a pointer receiver, *all* methods should use pointer receivers. A `Counter` with mutating methods like `Inc()`, `Reset()`, `Add(n)` should consistently be `*Counter`.

2. **Avoids accidental copies**: A `Counter` is conceptually an identity (a thing that holds state over time), not a value (like an `int` or a `time.Time`). Copying it is almost always a bug — you'd end up with two counters drifting apart.

3. **Concurrency safety**: If you later add a `sync.Mutex` to `Counter` (very likely for a counter!), it *must* not be copied. Pointer receivers prevent this. In fact, `go vet` will flag copies of structs containing a `sync.Mutex`.

4. **Interface satisfaction**: Only `*Counter` will satisfy an interface like `Incrementer { Inc() }` in a way that lets the same instance be incremented through the interface. With a value receiver, the interface would still work but each call through it might involve copies.

## Quick Demo

```go
type Counter struct{ n int }

func (c Counter) IncVal()  { c.n++ }   // BUG: no effect
func (c *Counter) IncPtr() { c.n++ }   // works

func main() {
    c := Counter{}
    c.IncVal(); c.IncVal()
    fmt.Println(c.n) // 0  ❌

    c.IncPtr(); c.IncPtr()
    fmt.Println(c.n) // 2  ✅
}
```

## Rule of Thumb

> Use a **value receiver** when the type is small, immutable, and behaves like a value (e.g., `time.Time`, `image.Point`).
>
> Use a **pointer receiver** when the method **mutates state**, the struct is **large**, or the type represents an **identity with lifecycle** (e.g., a counter, a connection, a buffer).

`Counter.Inc()` hits the first criterion outright — it must be a pointer receiver.

</details>

<details><summary>Skill-loaded answer</summary>

# Pointer Receiver: `(c *Counter)`

You should use a **pointer receiver**. Here's why:

## The Core Reason: Mutation

In Go, value receivers operate on a **copy** of the struct. Any modifications made inside the method affect only that local copy and are discarded when the method returns.

```go
type Counter struct {
    n int
}

// ❌ Wrong: modifies a copy, original is unchanged
func (c Counter) Inc() {
    c.n++ // mutates local copy only
}

// ✅ Correct: modifies the original via pointer
func (c *Counter) Inc() {
    c.n++ // mutates the actual Counter
}
```

If you used a value receiver, calling `counter.Inc()` would do nothing observable — the increment would be lost.

## Demonstration

```go
c := Counter{}
c.Inc()
c.Inc()
fmt.Println(c.n) // With value receiver: 0  | With pointer receiver: 2
```

## Supporting Reasons

1. **Consistency**: Go's style guide recommends that if *any* method on a type uses a pointer receiver, *all* methods should — to keep the method set consistent. Since `Inc()` must use a pointer, other methods on `Counter` should too.

2. **Interface satisfaction**: Only `*Counter` will satisfy an interface like `interface{ Inc() }` when the method has a pointer receiver. This is usually what you want for mutable types.

3. **Avoiding bugs**: Value receivers on types meant to be mutated are a classic Go footgun — the code compiles and runs silently while doing the wrong thing.

4. **Concurrency safety hints**: Pointer receivers signal to readers that the type has identity and shouldn't be casually copied (relevant if you later add a `sync.Mutex`, which *must* not be copied).

## Rule of Thumb

> **If a method needs to modify the receiver, use a pointer receiver. Period.**

Value receivers are appropriate for small, immutable, value-like types (e.g., `time.Time`, small structs used as map keys, or pure "getter"-style methods on tiny structs).

</details>

---

### `interface-placement`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
In Go, when my function takes a parameter that is "anything that has a
Read method", where should I declare that interface — in the package
that defines the concrete reader, or in the package that consumes it?
```

**Judge:** **tie** — Both answers correctly identify the consumer package as the right place to declare interfaces, cite the 'accept interfaces, return concrete types' rule, and emphasize small interfaces. Answer A adds useful nuance about exported vs unexported interfaces and the plugin pattern exception, while Answer B provides a cleaner code example showing both producer and consumer packages side by side and explicitly mentions testability. Neither answer is clearly superior overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| says consumer / caller package | tie |
| mentions accept interfaces, return concrete | tie |
| small interface guidance | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `consumer` |
| mentions accept interfaces, return concrete | ✓ | `Accept interfaces` |
| small interface guidance | ✓ | `one method` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `Consumer` |
| mentions accept interfaces, return concrete | ✓ | `Accept interfaces` |
| small interface guidance | ✓ | `one method` |

<details><summary>Baseline answer</summary>

# Where to Declare Interfaces in Go

**Declare it in the consuming package**, not the package that defines the concrete reader.

This is one of Go's most important idioms, often summarized as:

> "Accept interfaces, return structs."
> "The bigger the interface, the weaker the abstraction."
> — Rob Pike

## Why the consumer side?

1. **The consumer knows what it needs.** Only the function calling `Read` knows it needs *just* a `Read` method. The producer of a concrete type (say, a `*os.File`) shouldn't have to anticipate every possible subset of its behavior.

2. **Avoids unnecessary coupling.** If interfaces lived with the concrete type, every consumer would have to import that package just to name the interface — defeating the point of decoupling.

3. **Structural typing makes it free.** Go interfaces are satisfied implicitly. The concrete type doesn't need to know the interface exists; it just needs to have the right methods. So there's no benefit to co-locating them.

4. **Keeps interfaces small and focused.** Consumer-defined interfaces tend to be tiny (often one method), which is exactly what Go encourages. The standard library's `io.Reader` is the canonical example — a single-method interface defined where it's *used*, not where readers live.

## A practical pattern

```go
// package mypkg (the consumer)

type reader interface {
    Read(p []byte) (n int, err error)
}

func Process(r reader) error {
    // ...
}
```

Note it's often lowercase (unexported) — you only need to export it if callers need to name the type themselves.

## When to break the rule

- **Reuse an existing interface if one fits.** Don't redeclare `Read(p []byte) (n int, err error)` — just use `io.Reader`. That's why `io` exists: to host shared, fundamental interfaces consumed widely.
- **Plugin/strategy patterns** where the producing package defines the contract and many implementations plug in (e.g., `database/sql/driver.Driver`) are a legitimate exception.

## TL;DR

For your "anything with a `Read` method" case: **just use `io.Reader`**. If it were a more domain-specific method, declare the interface in the package that calls it.

</details>

<details><summary>Skill-loaded answer</summary>

# Go Interface Declaration: Define at the Consumer

In Go, the idiomatic answer is: **declare the interface in the package that consumes it**, not the package that provides the concrete implementation.

This is often summarized as:

> "Accept interfaces, return structs."
> — and define those interfaces where they're used.

## Why?

### 1. Interfaces describe what the consumer needs
The consumer knows exactly which methods it depends on. A producer can't know in advance every possible way its type might be used, so any interface it declares is just a guess.

### 2. Avoids unnecessary coupling
If `package a` defines `Reader` and `package b` consumes it, then `package c` (which also has a `Read` method) would have to import `package a` just to "implement" the interface — even though Go interfaces are structurally satisfied. Declaring the interface in the consumer means no one needs to import anyone extra.

### 3. Keeps interfaces small
Consumer-defined interfaces tend to be tiny (often one method), which matches Go's preference: "The bigger the interface, the weaker the abstraction."

### 4. Makes testing trivial
Your tests can supply any type with a `Read` method — no need to import or mock the concrete producer.

## Example

```go
// package store -- the producer
package store

type FileReader struct { /* ... */ }

func (f *FileReader) Read(p []byte) (int, error) { /* ... */ }
// Note: no interface declared here.
```

```go
// package report -- the consumer
package report

type reader interface {
    Read(p []byte) (int, error)
}

func Summarize(r reader) (string, error) {
    // ...
}
```

Now `report` doesn't import `store`, and `store` doesn't import `report`. Any type with a `Read` method works.

## The standard library exception

`io.Reader` lives in `io` because it's a *universal* abstraction used everywhere. If — and only if — your interface is genuinely shared by many unrelated consumers, it can make sense to put it in a neutral package (often a small `…/iface` or shared package). Otherwise, default to the consumer.

## Rule of thumb

- **Defining a type with a `Read` method?** Just export the struct. Don't ship an interface alongside it.
- **Writing a function that needs "something that can Read"?** Declare the minimal interface right there in your package — and if `io.Reader` already fits, just use that.

</details>

---

### `slog-structured`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
What's the modern, idiomatic way in Go to log an error with structured
fields (e.g. user_id, request_id) so it's machine-readable in
production?
```

**Judge:** **tie** — Both answers are nearly identical in quality, correctly recommending log/slog with structured fields and typed attribute helpers, avoiding log.Printf, and covering the same idiomatic patterns (With, context variants, groups, LogValuer). Answer A is slightly more opinionated against third-party libraries, while Answer B provides a more balanced view on when zap/zerolog might still be appropriate. Neither has a meaningful advantage over the other for the stated focus area.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses log/slog | tie |
| shows a slog call with structured fields | tie |
| avoids recommending log.Printf for structured logging | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses log/slog | ✓ | `slog` |
| shows a slog call with structured fields | ✓ | `slog.Error(` |
| avoids recommending log.Printf for structured logging | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses log/slog | ✓ | `slog` |
| shows a slog call with structured fields | ✓ | `slog.Error(` |
| avoids recommending log.Printf for structured logging | ✓ | |

<details><summary>Baseline answer</summary>

# Structured Logging in Go (2026)

The modern, idiomatic way is to use **`log/slog`** from the standard library (added in Go 1.21, now the default choice).

## Basic usage

```go
import (
    "log/slog"
    "os"
)

logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

logger.Error("failed to process payment",
    slog.String("user_id", userID),
    slog.String("request_id", reqID),
    slog.Any("err", err),
)
```

This produces machine-readable JSON like:

```json
{"time":"2026-05-05T10:14:22Z","level":"ERROR","msg":"failed to process payment","user_id":"u_123","request_id":"req_abc","err":"connection refused"}
```

## Idiomatic patterns

### 1. Set a global default once at startup

```go
func main() {
    h := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level:     slog.LevelInfo,
        AddSource: true, // includes file:line
    })
    slog.SetDefault(slog.New(h))
}
```

Then anywhere:
```go
slog.Error("db query failed", "user_id", uid, "err", err)
```

### 2. Carry context with `With` (request-scoped loggers)

Attach common fields once per request rather than repeating them:

```go
reqLogger := slog.Default().With(
    "request_id", reqID,
    "user_id", userID,
)

reqLogger.Info("starting handler")
// ... later ...
reqLogger.Error("validation failed", "field", "email", "err", err)
```

### 3. Pass the logger via `context.Context`

Use `slog.InfoContext` / `slog.ErrorContext` so handlers (e.g. tracing handlers) can pull trace IDs out of the context automatically:

```go
slog.ErrorContext(ctx, "operation failed",
    "request_id", reqID,
    "err", err,
)
```

A common pattern is to stash a request logger in context:

```go
type ctxKey struct{}

func WithLogger(ctx context.Context, l *slog.Logger) context.Context {
    return context.WithValue(ctx, ctxKey{}, l)
}

func FromContext(ctx context.Context) *slog.Logger {
    if l, ok := ctx.Value(ctxKey{}).(*slog.Logger); ok {
        return l
    }
    return slog.Default()
}
```

### 4. Group related fields

```go
logger.Error("payment failed",
    slog.Group("user",
        slog.String("id", userID),
        slog.String("tier", "pro"),
    ),
    slog.String("request_id", reqID),
    slog.Any("err", err),
)
```

### 5. Make your own types loggable with `LogValuer`

Avoid leaking PII or formatting in every call site:

```go
type User struct {
    ID    string
    Email string
}

func (u User) LogValue() slog.Value {
    return slog.GroupValue(
        slog.String("id", u.ID),
        // intentionally omit email
    )
}

logger.Info("user signed in", "user", user)
```

## A few practical tips

- **Prefer typed attrs** (`slog.String`, `slog.Int`, `slog.Any`) in hot paths — they avoid the reflection cost of the loose `key, value` form.
- **Use stable, snake_case keys** (`user_id`, `request_id`, `trace_id`) so log aggregators (Loki, Datadog, Cloud Logging, etc.) can index reliably.
- **Use `"err"` (or `"error"`) consistently** for error values — pick one and stick to it across the codebase.
- **JSON handler in prod, Text handler in dev** — switch via env var.
- **Don't reach for `zap` or `zerolog` by default anymore.** They're still faster, but `slog` is the standard, integrates with the ecosystem (including pluggable handlers that wrap zap/zerolog), and is fast enough for the vast majority of services.

## TL;DR

```go
slog.ErrorContext(ctx, "checkout failed",
    "user_id", userID,
    "request_id", reqID,
    "err", err,
)
```

That single line — using `log/slog` with a JSON handler set as the default — is the canonical 2026 answer.

</details>

<details><summary>Skill-loaded answer</summary>

# Structured Logging in Go (Modern, Idiomatic Approach)

The modern, idiomatic way is to use **`log/slog`**, which was added to the standard library in **Go 1.21** (August 2023). Before `slog`, the community relied on third-party libraries like `zap` or `zerolog`, but `slog` is now the standard choice for new code.

## Basic Usage

```go
package main

import (
    "log/slog"
    "os"
)

func main() {
    // JSON handler for production (machine-readable)
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)

    err := doWork()
    if err != nil {
        slog.Error("failed to process request",
            slog.String("user_id", "u-123"),
            slog.String("request_id", "req-abc"),
            slog.Any("error", err),
        )
    }
}
```

This produces a JSON line like:

```json
{"time":"2026-05-05T10:00:00Z","level":"ERROR","msg":"failed to process request","user_id":"u-123","request_id":"req-abc","error":"db timeout"}
```

## Idiomatic Tips

### 1. Use typed attribute helpers (faster, allocation-free)

Prefer `slog.String`, `slog.Int`, `slog.Duration`, etc. over the loose key-value form, as they avoid reflection:

```go
slog.Error("payment failed",
    slog.String("user_id", userID),
    slog.String("request_id", reqID),
    slog.Int("amount_cents", amount),
    slog.Any("error", err),
)
```

### 2. Carry context with `logger.With(...)`

Bind common fields once per request rather than repeating them:

```go
reqLogger := slog.Default().With(
    slog.String("request_id", reqID),
    slog.String("user_id", userID),
)

reqLogger.Error("checkout failed", slog.Any("error", err))
```

### 3. Use the context-aware variants

`slog.ErrorContext(ctx, ...)` lets handlers pull values (like trace IDs) out of `context.Context`:

```go
slog.ErrorContext(ctx, "db query failed",
    slog.String("query", "SELECT ..."),
    slog.Any("error", err),
)
```

### 4. Group related fields

```go
slog.Error("request failed",
    slog.Group("http",
        slog.String("method", "POST"),
        slog.String("path", "/checkout"),
        slog.Int("status", 500),
    ),
    slog.Any("error", err),
)
```

### 5. Make custom types log nicely

Implement `slog.LogValuer` to control how a type is logged (e.g., redact secrets):

```go
type User struct {
    ID    string
    Email string
}

func (u User) LogValue() slog.Value {
    return slog.GroupValue(
        slog.String("id", u.ID),
        // omit email
    )
}
```

## Production vs. Development

A common pattern is to switch handlers based on environment:

```go
var handler slog.Handler
if os.Getenv("ENV") == "production" {
    handler = slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo})
} else {
    handler = slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug})
}
slog.SetDefault(slog.New(handler))
```

## When to Reach for Third-Party Libraries

- **`zap`** (Uber) or **`zerolog`** — still excellent if you need maximum throughput or you're already on them. Both can be used as `slog.Handler` backends now (e.g., `go.uber.org/zap/exp/zapslog`), so you can write `slog`-style code and keep `zap`'s performance.
- **`slog-multi`**, **`samber/slog-*`** — useful for fan-out, sampling, or sending to platforms like Datadog/Sentry.

## TL;DR

Use `log/slog` with a `JSONHandler` in production, attach request-scoped fields via `logger.With(...)`, and prefer the typed `slog.String`/`slog.Int`/`slog.Any` helpers for both performance and clarity.

</details>

---

### `generic-min`

**Expected:** `skill_wins` · **Met:** ✓

**Prompt**

```
Write me a Go `Min` function that returns the smaller of two values
and works for any numeric type (int, int64, float64, etc).
```

**Judge:** **skill** — Both answers are nearly identical in quality, using the same generic syntax, the same Number constraint with tilde-prefixed types, and the same implementation. Answer A is slightly better because it mentions the standard library's `cmp.Ordered` constraint (available since Go 1.21 in the stdlib, not just golang.org/x/exp) with a concrete code example, which is more accurate and up-to-date than Answer B's reference to the experimental `golang.org/x/exp/constraints` package.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses generics syntax with type parameter | tie |
| uses an Ordered or numeric union constraint | skill |
| avoids interface{} + reflect | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses generics syntax with type parameter | ✓ | `[T ` |
| uses an Ordered or numeric union constraint | ✓ | `constraints.Ordered` |
| avoids interface{} + reflect | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses generics syntax with type parameter | ✓ | `[T ` |
| uses an Ordered or numeric union constraint | ✓ | `cmp.Ordered` |
| avoids interface{} + reflect | ✓ | |

<details><summary>Baseline answer</summary>

Here's a generic `Min` function in Go that works with any numeric type using type parameters (generics, available since Go 1.18):

```go
package main

import "fmt"

// Number is a constraint that permits any integer or floating-point type.
type Number interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64
}

// Min returns the smaller of a and b.
func Min[T Number](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(3, 7))            // 3
	fmt.Println(Min(int64(10), 4))    // 4
	fmt.Println(Min(2.5, 1.75))       // 1.75
	fmt.Println(Min[float32](9, 12))  // 9
}
```

### Notes

- **`~` in the constraint** allows named types whose underlying type is one of the listed types (e.g., `type Celsius float64` will still work).
- **`constraints.Ordered`**: If you don't mind pulling in `golang.org/x/exp/constraints`, you can replace the `Number` interface with `constraints.Ordered`, which also includes `string`. Use that if you'd like to compare strings as well:

  ```go
  import "golang.org/x/exp/constraints"

  func Min[T constraints.Ordered](a, b T) T {
      if a < b {
          return a
      }
      return b
  }
  ```

- **Standard library**: Since Go 1.21, the standard library actually provides `min` (and `max`) as built-ins that work on any ordered type, so unless you're on an older version or need custom behavior, you can just write `min(a, b)` directly.

</details>

<details><summary>Skill-loaded answer</summary>

Here's a generic `Min` function in Go that works for any numeric type:

```go
package main

import "fmt"

// Number is a constraint that permits any numeric type.
type Number interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64
}

// Min returns the smaller of a and b.
func Min[T Number](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(3, 7))           // 3
	fmt.Println(Min(int64(10), 4))   // 4
	fmt.Println(Min(2.71, 3.14))     // 2.71
	fmt.Println(Min[uint](5, 9))     // 5
}
```

### How it works
- **`Number` constraint**: A type set listing all of Go's built-in numeric types. The `~` prefix means "any type whose underlying type is this," so it also accepts named types like `type Celsius float64`.
- **`Min[T Number](a, b T) T`**: A generic function parameterized by `T`, which must satisfy the `Number` constraint. Both arguments and the return value share the same type.
- **`<` works** because every type in the constraint supports the ordering operator.

### Alternative: use the standard library
Since Go 1.21, the standard library provides this for you via the built-in `min` function:

```go
fmt.Println(min(3, 7))      // 3
fmt.Println(min(2.71, 3.14)) // 2.71
```

And for ordered types more broadly, `cmp.Ordered` (in the `cmp` package) is the canonical constraint:

```go
import "cmp"

func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

Note that `cmp.Ordered` also includes `string`, so use the custom `Number` constraint above if you want to restrict to numeric types only.

</details>

---

### `simplest-error`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Just give me the simplest, fewest-character way to return an
error in Go that says "user not found". One line if possible.
```

**Judge:** **tie** — Both answers are identical, providing the bare `errors.New("user not found")` approach without using sentinel errors or %w wrapping, and neither explains why bare string errors are limiting. Neither answer meets the rubric criteria for best practices in Go error handling.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses sentinel error or %w wrapping | tie |
| explains why bare string errors are limiting | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✗ | |
| explains why bare string errors are limiting | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✗ | |
| explains why bare string errors are limiting | ✗ | |

<details><summary>Baseline answer</summary>

```go
return errors.New("user not found")
```

</details>

<details><summary>Skill-loaded answer</summary>

```go
return errors.New("user not found")
```

</details>

---

### `offtopic-css-grid`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the simplest CSS Grid setup to create a 3-column layout
with equal widths and a small gap between columns?
```

**Judge:** **tie** — Both answers provide essentially identical CSS solutions with the same three properties and equivalent explanations. Answer B adds a minor bonus tip about responsive behavior with auto-fit/minmax, but this is a small addition that doesn't materially change the quality of the core answer.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

The simplest CSS Grid setup for a 3-column layout with equal widths and a small gap:

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
```

```html
<div class="container">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

**Breakdown:**
- `display: grid` — turns the container into a grid.
- `grid-template-columns: repeat(3, 1fr)` — creates 3 columns that each take an equal fraction (`1fr`) of the available space.
- `gap: 1rem` — adds spacing between columns (and rows, if there are any). Adjust to `0.5rem`, `8px`, etc., to taste.

That's it — three lines of CSS for a clean, equal-width 3-column layout.

</details>

<details><summary>Skill-loaded answer</summary>

The simplest CSS Grid setup for a 3-column layout with equal widths and a small gap:

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
```

**Breakdown:**

- `display: grid` — Turns the element into a grid container.
- `grid-template-columns: repeat(3, 1fr)` — Creates 3 columns, each taking an equal fraction (`1fr`) of the available space.
- `gap: 1rem` — Adds a small space between columns (and rows, if any). Adjust to taste (`8px`, `0.5rem`, etc.).

**HTML:**

```html
<div class="container">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

That's it — no media queries or extra wrappers needed for the basic case. If you want it to gracefully collapse on small screens, you can swap in:

```css
grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
```

</details>

---
