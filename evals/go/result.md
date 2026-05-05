# Eval report: `go`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **8**
- Models: **sonnet, haiku, opus**
- Total cost: **$1.84** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 8/8 | 7 / 0 / 1 | 86% → 96% (+11%) |
| `haiku` | 8/8 | 7 / 0 / 1 | 69% → 95% (+26%) |
| `opus` ¹ | 5/8 | 4 / 0 / 4 | 86% → 96% (+11%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 6 | 6/6 | 6/6 | 3/6 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `error-wrapping` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `goroutine-lifetime` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `receiver-consistency` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `interface-placement` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `slog-structured` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `generic-min` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `simplest-error` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-css-grid` | tie | ✓ = tie | ✓ = tie | ✓ = tie |

## Per-case detail

### `error-wrapping`

**Prompt**

```
I have a Go function that opens a config file and just does
`return os.Open(path)`. Callers get errors like
"open /etc/foo.yml: no such file or directory" with no hint of which
subsystem hit it. What's the right way to fix this?
```

**Judge focus:** The better answer teaches error wrapping that preserves errors.Is / errors.As
traversal (i.e. uses %w), not string concatenation or %v which break the chain.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A has a critical bug in the fmt.Errorf call — `fmt.Errorf("load config from %s: %w", err)` is missing the `path` argument, passing `err` as the `%s` argument and nothing for `%w`. However, Answer A is otherwise more thorough on the focus criteria: it explicitly calls out the %v anti-pattern with a dedicated section, explains why %v breaks the chain, and covers errors.Is/errors.As more clearly. Answer B is more correct code-wise (no argument mismatch) and adds useful structured error type coverage, but is slightly weaker on explicitly teaching the %v anti-pattern distinction. The bug in A is notable but the question focuses on teaching wrapping concepts, and A's conceptual coverage of all rubric criteria is stronger overall — though it's a close call given the code bug.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses %w directive | baseline |
| mentions errors.Is or errors.As | skill |
| uses fmt.Errorf for context | baseline |
| avoids %v wrapping anti-pattern | skill |

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
| avoids %v wrapping anti-pattern | ✗ | `fmt.Errorf("load config: %v", err` |

<details><summary>sonnet: baseline answer</summary>

## Wrapping Errors with Context in Go

The idiomatic Go solution is to wrap the error with `fmt.Errorf` and the `%w` verb, which preserves the original error for programmatic inspection while adding context.

### The Problem

```go
// Bad: caller sees "open /etc/foo.yml: no such file or directory"
// No idea which subsystem, which config type, or why it was needed
func loadConfig(path string) (*Config, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err  // naked return, context is lost
    }
    // ...
}
```

### The Fix

```go
func loadConfig(path string) (*Config, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("loadConfig: %w", err)
    }
    defer f.Close()

    var cfg Config
    if err := yaml.NewDecoder(f).Decode(&cfg); err != nil {
        return nil, fmt.Errorf("loadConfig: decode %q: %w", path, err)
    }

    return &cfg, nil
}
```

Now callers see: `"loadConfig: open /etc/foo.yml: no such file or directory"`

---

### Why `%w` and Not `%v`?

| Verb | Wraps error | `errors.Is/As` works | Use when |
|------|-------------|----------------------|----------|
| `%w` | Yes | ✅ Yes | Almost always |
| `%v` | No | ❌ No | Intentionally hiding error type |

```go
cfg, err := loadConfig("/etc/foo.yml")
if errors.Is(err, os.ErrNotExist) {
    // This still works with %w, breaks with %v
    applyDefaults()
}
```

---

### Build a Convention: Prefix with the Call Chain

Each layer adds its own name, creating a readable trace:

```go
func (s *Server) Start() error {
    if err := s.loadConfig(); err != nil {
        return fmt.Errorf("server.Start: %w", err)
    }
    return nil
}

func (s *Server) loadConfig() error {
    if _, err := loadConfig(s.configPath); err != nil {
        return fmt.Errorf("server.loadConfig: %w", err)
    }
    return nil
}
```

Error message: `"server.Start: server.loadConfig: loadConfig: open /etc/foo.yml: no such file or directory"`

---

### When You Need Structured Errors

For libraries or cases where callers need to inspect details programmatically:

```go
type ConfigError struct {
    Path string
    Op   string
    Err  error
}

func (e *ConfigError) Error() string {
    return fmt.Sprintf("config %s %q: %v", e.Op, e.Path, e.Err)
}

// Unwrap lets errors.Is/As traverse the chain
func (e *ConfigError) Unwrap() error { return e.Err }

func loadConfig(path string) (*Config, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, &ConfigError{Path: path, Op: "open", Err: err}
    }
    // ...
}

// Caller can now extract structured info:
var cfgErr *ConfigError
if errors.As(err, &cfgErr) {
    log.Printf("failed on config file: %s", cfgErr.Path)
}
```

---

### Quick Rules of Thumb

1. **Always wrap** — never return a bare `err` from a non-trivial function
2. **Use `%w`** unless you have a specific reason to use `%v`
3. **Include the path/key** in the message when it adds information the caller doesn't already have
4. **Don't include it twice** — if the path is already in `os.Open`'s error, you don't need to repeat it in your wrapper
5. **Name the operation**, not just the file — `"loadConfig:"` is more useful than `"config file:"`

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The fix is to wrap the error with `fmt.Errorf` and the `%w` verb. That adds context to the message while keeping the original error in the chain so callers can still use `errors.Is` and `errors.As`.

## The Problem

```go
// Before: callers see "open /etc/foo.yml: no such file or directory"
// No indication this came from config loading.
func loadConfig(path string) (*os.File, error) {
    return os.Open(path)
}
```

## The Fix

```go
import (
    "fmt"
    "os"
)

func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("load config from %s: %w", err)
        //                      ^^^^^^^^^^^^^^^^^^^^^^^^
        //                      operational context      |
        //                                               %w preserves the chain
    }
    return f, nil
}
```

Callers now see:

```
load config from /etc/foo.yml: open /etc/foo.yml: no such file or directory
```

And they can still match the underlying cause:

```go
err := loadConfig("/etc/foo.yml")
if errors.Is(err, os.ErrNotExist) {
    // still works — %w keeps the chain intact
}
```

## Wrapping Rules

| Situation | What to do | Why |
|---|---|---|
| Adding operational context | `fmt.Errorf("doing X: %w", err)` | Preserves `errors.Is`/`As` chain |
| The underlying error is an internal detail you don't want to expose | New sentinel or typed error, **no** `%w` | Prevents callers depending on implementation errors |
| Bare `return err` | Almost always wrong at a subsystem boundary | Loses all context about where the failure occurred |

## Wrapping Deeper Call Stacks

Each layer adds its own context, and the messages compose naturally:

```go
func (s *Server) Start(cfgPath string) error {
    f, err := loadConfig(cfgPath)
    if err != nil {
        return fmt.Errorf("server start: %w", err)
    }
    // ...
}
```

Result:

```
server start: load config from /etc/foo.yml: open /etc/foo.yml: no such file or directory
```

Read left-to-right: high-level operation → subsystem → stdlib call → OS message. No guessing which layer failed.

## Checking Errors in Tests

```go
_, err := loadConfig("/nonexistent")

// Check the sentinel — works through any number of wrapping layers
if !errors.Is(err, os.ErrNotExist) {
    t.Fatalf("expected ErrNotExist, got %v", err)
}

// Check the message contains your context
if !strings.Contains(err.Error(), "load config") {
    t.Fatalf("error missing context: %v", err)
}
```

## One Pitfall to Avoid

`%w` must appear **once** per `fmt.Errorf` call (Go 1.20+ supports multiple `%w` for wrapping several errors, but that's a different pattern). Don't use `%v` when you mean `%w` — `%v` embeds the message as a plain string and breaks `errors.Is`:

```go
// Wrong — breaks the error chain
return nil, fmt.Errorf("load config: %v", err)

// Right
return nil, fmt.Errorf("load config from %s: %w", path, err)
```

The convention for the context string is `"noun verb noun: %w"` — lowercase, no trailing punctuation, colon-space before `%w`. That way the composed message reads as a natural chain of events.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B more thoroughly addresses all rubric criteria, explicitly demonstrating errors.Is/errors.As usage with a concrete example, explaining why %w matters for chain traversal, and providing practical guidance on when to wrap vs. replace. Answer A covers the basics but the custom error type section is a distraction from the core question, and it doesn't show errors.Is/errors.As in action as clearly.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses %w directive | tie |
| mentions errors.Is or errors.As | skill |
| uses fmt.Errorf for context | tie |
| avoids %v wrapping anti-pattern | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses %w directive | ✓ | `%w` |
| mentions errors.Is or errors.As | ✓ | `errors.As` |
| uses fmt.Errorf for context | ✓ | `fmt.Errorf` |
| avoids %v wrapping anti-pattern | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses %w directive | ✓ | `%w` |
| mentions errors.Is or errors.As | ✓ | `errors.Is` |
| uses fmt.Errorf for context | ✓ | `fmt.Errorf` |
| avoids %v wrapping anti-pattern | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Adding Context to File Open Errors

The best approach is to wrap the error with context using `fmt.Errorf` with the `%w` verb (Go 1.13+):

```go
func OpenConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("failed to open config file: %w", err)
    }
    return f, nil
}
```

Now callers get: `"failed to open config file: open /etc/foo.yml: no such file or directory"`

## Better: Return a Structured Error

For more control, create a custom error type:

```go
type ConfigError struct {
    Path string
    Err  error
}

func (e *ConfigError) Error() string {
    return fmt.Sprintf("config error: failed to open %s: %v", e.Path, e.Err)
}

func (e *ConfigError) Unwrap() error {
    return e.Err
}

func OpenConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, &ConfigError{Path: path, Err: err}
    }
    return f, nil
}
```

This gives you:
- Clear error messages: `"config error: failed to open /etc/foo.yml: no such file or directory"`
- Ability to check error type: `errors.As(err, &configErr)`
- Error chain preservation with `Unwrap()`

## Quick Comparison

| Approach | Pros | Cons |
|----------|------|------|
| `fmt.Errorf` with `%w` | Simple, standard | Less structured |
| Custom error type | Structured, type-checkable | More boilerplate |

For most cases, **`fmt.Errorf` is sufficient**. Use custom types when you need callers to distinguish this error from others.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Wrapping the Error with Context

The issue is that you're returning the bare `os.Open` error, which loses operational context. The fix is to wrap it with `fmt.Errorf` using the `%w` verb:

```go
func loadConfig(path string) (*Config, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open config file: %w", err)
	}
	defer f.Close()
	// ... parse and return config
}
```

Now callers see:
```
open config file: open /etc/foo.yml: no such file or directory
```

The `%w` verb is critical — it preserves the error chain so that `errors.Is` and `errors.As` still work:

```go
// Caller can still check for specific errors
if errors.Is(err, os.ErrNotExist) {
	// Handle missing file
}
```

## When to Wrap vs. Replace

| Situation | Use `%w` | Use new error (no `%w`) |
|---|---|---|
| The underlying error is useful to callers (e.g., `os.ErrNotExist`, `io.EOF`) | ✓ | |
| You want callers to `errors.Is` or `errors.As` the original | ✓ | |
| The underlying error is an implementation detail you want to hide | | ✓ |
| You're translating between abstraction layers | | ✓ |

**Example of replacing** (when the underlying error is an implementation detail):

```go
// Bad: leaks that we use os.Open internally
return nil, fmt.Errorf("load config: %w", err)

// Good: hides the implementation, returns a domain error
if err != nil {
	return nil, ErrConfigNotFound // or a custom type
}
```

## Best Practices

1. **Add context at each layer** — each function wraps with its own perspective:
   ```go
   func (s *Server) Start(ctx context.Context) error {
       cfg, err := loadConfig("app.yml")
       if err != nil {
           return fmt.Errorf("start server: %w", err)
       }
       // ...
   }
   
   func loadConfig(path string) (*Config, error) {
       f, err := os.Open(path)
       if err != nil {
           return nil, fmt.Errorf("open config file %s: %w", path, err)
       }
       // ...
   }
   ```
   
   The final error reads: `start server: open config file /etc/foo.yml: open /etc/foo.yml: no such file or directory`

2. **Include relevant values** — add the filename, URL, or ID that failed:
   ```go
   return nil, fmt.Errorf("open config file %s: %w", path, err)
   ```

3. **Don't wrap twice** — if a function already returns a wrapped error, don't wrap it again:
   ```go
   // Bad
   cfg, err := loadConfig(path)
   if err != nil {
       return nil, fmt.Errorf("load: %w", err)  // Redundant
   }
   
   // Good: just return it, or add new context only if needed
   cfg, err := loadConfig(path)
   if err != nil {
       return nil, fmt.Errorf("initialize app: %w", err)  // New layer
   }
   ```

4. **Use `errors.Is` for sentinel checks, not string matching:**
   ```go
   // Bad
   if strings.Contains(err.Error(), "no such file") { }
   
   // Good
   if errors.Is(err, os.ErrNotExist) { }
   ```

This pattern is idiomatic Go and recommended by [Effective Go](https://golang.org/doc/effective_go#errors) and the [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments#error-strings).

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly use %w with fmt.Errorf, mention errors.Is and errors.As with working examples, and explicitly warn against %v/%s flattening. Answer A provides slightly more depth with errors.As usage and a nuanced 'when not to wrap' discussion, while Answer B offers cleaner conventions (no capitalization, wrap once per layer) and a mention of stack trace libraries. Neither is clearly superior across all criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses %w directive | tie |
| mentions errors.Is or errors.As | skill |
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

<details><summary>opus: baseline answer</summary>

# Wrap the error with context

The idiomatic Go fix is to wrap the error using `fmt.Errorf` with the `%w` verb. This adds your context while preserving the original error for inspection with `errors.Is` / `errors.As`.

```go
func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("loadConfig: opening %q: %w", path, err)
    }
    return f, nil
}
```

Now callers see something like:

```
loadConfig: opening "/etc/foo.yml": open /etc/foo.yml: no such file or directory
```

## Why `%w` and not `%v` or `%s`

- `%w` wraps the error so `errors.Is(err, os.ErrNotExist)` still works upstream.
- `%v` / `%s` flatten it to a string, losing the ability to type-check or compare sentinel errors.

## A few conventions worth following

1. **Don't capitalize or end with punctuation.** Error strings get concatenated, so `"loading config: opening file: ..."` reads naturally.
2. **Add context the caller doesn't already have.** The path is good; "error:" or "failed to" is noise — `err` already implies failure.
3. **Wrap once per layer, not at every return.** Wrapping in the function that has meaningful context (subsystem name, operation, key parameter) is enough. Re-wrapping at every level produces noisy stack-like strings.
4. **Include the dynamic value** (here, `path`) since `os.Open`'s message already includes it, but if you transform the path or compute it, log the input the caller gave you.

## If callers need to branch on the error

```go
f, err := loadConfig("/etc/foo.yml")
if errors.Is(err, os.ErrNotExist) {
    // fall back to defaults
}
```

This still works because of `%w`.

## When you want stack traces too

The standard library doesn't include them. If you find yourself wanting them, [`github.com/pkg/errors`](https://github.com/pkg/errors) or `cockroachdb/errors` add stack capture, but for most code, a couple of well-placed `fmt.Errorf("%w")` wraps are enough to identify the subsystem.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Add context with `fmt.Errorf` and `%w`

The fix is to wrap the error with operational context using `%w`, which preserves the error chain so callers can still inspect the underlying error with `errors.Is`/`errors.As`.

## The fix

```go
package config

import (
    "fmt"
    "os"
)

func Open(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("config: open %s: %w", path, err)
    }
    return f, nil
}
```

Now the error reads:

```
config: open /etc/foo.yml: open /etc/foo.yml: no such file or directory
```

Callers immediately see *which subsystem* failed. (If the duplicated `open /etc/foo.yml` bothers you, drop the path from your wrap message — `os.Open` already includes it. I'd keep the subsystem prefix though: `fmt.Errorf("config: %w", err)`.)

## Why `%w` and not `%v` or `%s`

`%w` wraps the error so the chain stays intact:

```go
_, err := config.Open("/etc/foo.yml")

// Still works — the underlying os.PathError is reachable:
if errors.Is(err, os.ErrNotExist) {
    // handle missing config (e.g. fall back to defaults)
}

// And you can extract the *fs.PathError if you need details:
var pathErr *fs.PathError
if errors.As(err, &pathErr) {
    log.Printf("failed op=%s path=%s", pathErr.Op, pathErr.Path)
}
```

If you'd used `%v` or `%s`, the message would look the same but `errors.Is(err, os.ErrNotExist)` would return `false` — you'd have flattened the error into a string and lost the ability to inspect it programmatically.

## Rule of thumb

- **Wrap with `%w`** when you're adding context to an error that callers might reasonably want to inspect (the common case).
- **Don't wrap** (use `%v`, or return a fresh sentinel/typed error) only when the underlying error is an implementation detail you deliberately want to hide from callers — e.g. you don't want callers coupling to the fact that you happen to use `os.Open` today and might switch to an embedded FS tomorrow.

For a config loader, wrapping with `%w` is almost certainly what you want: callers legitimately care about "file not found" vs "permission denied" vs other I/O failures.

## One more thing

Make sure callers actually use `errors.Is`/`errors.As` rather than string-matching the error message — the whole point of preserving the chain is wasted otherwise. If you find yourself or your callers writing `strings.Contains(err.Error(), "no such file")`, that's a smell pointing at either missing wrapping somewhere or a missing sentinel/typed error in your API.

</details>

---

### `goroutine-lifetime`

**Prompt**

```
Show me the basic Go pattern for running a periodic background task
(something that ticks every few seconds and does some work).
```

**Judge focus:** The better answer gives the goroutine a deterministic exit condition tied
to a context, rather than spawning an unbounded `go func()` with no way to stop.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria, but Answer B goes further by encapsulating the pattern into a reusable, testable function that passes ctx into the work function (enabling mid-task cancellation), returns errors for proper error propagation, and includes a more thorough explanation of design decisions including the note about select randomness and the importance of passing ctx to fn. Answer A is solid and practical but is more of a script-style example rather than a reusable library pattern, and its 'run immediately then tick' variation has a subtle issue where doWork is called outside the select before ctx.Done is checked.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.Context | skill |
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

<details><summary>sonnet: baseline answer</summary>

## Periodic Background Task in Go

Here's the standard pattern using `time.Ticker` with proper cleanup:

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func startWorker(ctx context.Context, interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop() // Always stop the ticker to free resources

    log.Println("Worker started")

    for {
        select {
        case t := <-ticker.C:
            doWork(t)

        case <-ctx.Done():
            log.Println("Worker stopped:", ctx.Err())
            return
        }
    }
}

func doWork(t time.Time) {
    fmt.Printf("Doing work at %s\n", t.Format(time.TimeOnly))
    // ... your logic here
}

func main() {
    // Cancel the context to stop the worker from anywhere in your program
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    // Run in background goroutine
    go startWorker(ctx, 3*time.Second)

    // Block until CTRL+C or SIGTERM
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("Shutting down...")
    cancel() // Signal the worker to stop
}
```

### Key points

| Concern | Solution |
|---|---|
| Prevent ticker leak | `defer ticker.Stop()` |
| Graceful shutdown | `context.Context` cancellation |
| Non-blocking | Run worker in a goroutine |
| OS signal handling | `signal.Notify` on a buffered channel |

---

### Common variations

**Run immediately, then tick** — the ticker waits for the first interval before firing:
```go
for {
    doWork(time.Now()) // run once right away

    select {
    case <-ticker.C:
    case <-ctx.Done():
        return
    }
}
```

**Wait for the worker to fully finish before exiting:**
```go
var wg sync.WaitGroup
wg.Add(1)

go func() {
    defer wg.Done()
    startWorker(ctx, 3*time.Second)
}()

<-quit
cancel()
wg.Wait() // block until worker returns
log.Println("Clean exit")
```

The core idea is always the same: **ticker + context + select**.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the idiomatic Go pattern for a periodic background task:

```go
// Ticker runs fn on every interval until ctx is cancelled.
// The caller controls lifetime via the context.
func Ticker(ctx context.Context, interval time.Duration, fn func(ctx context.Context) error) error {
	ticker := time.NewTicker(interval)
	defer ticker.Stop() // always release the ticker's goroutine and channel

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()

		case <-ticker.C:
			if err := fn(ctx); err != nil {
				return fmt.Errorf("ticker task: %w", err)
			}
		}
	}
}
```

**Calling it from `main` (or a server startup):**

```go
func main() {
	// A real program would wire this to SIGTERM / SIGINT.
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	err := Ticker(ctx, 5*time.Second, func(ctx context.Context) error {
		slog.InfoContext(ctx, "tick", "time", time.Now())
		// do real work here — pass ctx so it can be cancelled mid-task
		return nil
	})

	// context.DeadlineExceeded / Canceled is expected on clean shutdown.
	if err != nil && !errors.Is(err, context.DeadlineExceeded) && !errors.Is(err, context.Canceled) {
		slog.Error("ticker stopped", "err", err)
		os.Exit(1)
	}
}
```

**Running it as a background goroutine (the common server case):**

```go
func startBackgroundTask(ctx context.Context, wg *sync.WaitGroup) {
	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := Ticker(ctx, 5*time.Second, doWork); err != nil &&
			!errors.Is(err, context.Canceled) {
			slog.Error("background task failed", "err", err)
		}
	}()
}

// Somewhere in your shutdown sequence:
//   cancel()   // signal all goroutines to stop
//   wg.Wait()  // block until they've all returned
```

---

### Why each piece matters

| Decision | Reason |
|---|---|
| `time.NewTicker` + `defer ticker.Stop()` | `Stop` drains the channel and frees the internal goroutine. Forgetting it leaks. |
| `select` with `ctx.Done()` | Gives the task a clean exit path the moment the caller cancels. Without it the goroutine blocks on the next tick even after shutdown. |
| `ctx.Done()` checked **before** `ticker.C` | Go's `select` picks a ready case at random when multiple fire simultaneously. Listing `ctx.Done()` first doesn't guarantee priority — you still need the `errors.Is` check on shutdown, but it's a clear signal of intent. |
| Passing `ctx` into `fn` | Long-running work inside the tick (HTTP calls, DB queries) can respect cancellation mid-task, not just between ticks. |
| `fmt.Errorf("ticker task: %w", err)` | Wraps with context while keeping the original error inspectable via `errors.Is`/`errors.As`. |
| `sync.WaitGroup` in the goroutine case | Gives the shutdown path a way to confirm the goroutine has actually exited before the process ends. |

### One common mistake to avoid

```go
// ❌ Don't do this — fires immediately AND on every interval,
//    and there's no way to stop it cleanly.
go func() {
    for {
        doWork()
        time.Sleep(5 * time.Second)
    }
}()
```

`time.Sleep` can't be interrupted. If the program shuts down mid-sleep, the goroutine is stuck until the sleep expires (or the process is killed). `time.NewTicker` + `select` on `ctx.Done()` is the correct primitive.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A uses context.Context throughout, selects on ctx.Done(), and uses time.NewTicker — satisfying all four rubric criteria. Answer B uses a raw channel for stopping rather than context.Context, missing the ctx.Done() pattern entirely, and its first example has no exit condition at all (select{} blocks forever with an uncontrolled goroutine).

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.Context | skill |
| selects on ctx.Done | skill |
| uses time.NewTicker (preferred over time.Tick) | tie |
| avoids time.Tick (which leaks) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.Context | ✗ | |
| selects on ctx.Done | ✗ | |
| uses time.NewTicker (preferred over time.Tick) | ✓ | `time.NewTicker` |
| avoids time.Tick (which leaks) | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.Context | ✓ | `context.Context` |
| selects on ctx.Done | ✓ | `ctx.Done()` |
| uses time.NewTicker (preferred over time.Tick) | ✓ | `time.NewTicker` |
| avoids time.Tick (which leaks) | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Basic Go Pattern for Periodic Background Tasks

Here's the fundamental pattern using `time.Ticker`:

```go
package main

import (
	"fmt"
	"time"
)

func main() {
	// Create a ticker that fires every 2 seconds
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	// Run the background task
	go func() {
		for range ticker.C {
			doWork()
		}
	}()

	// Keep the program running
	select {}
}

func doWork() {
	fmt.Println("Working at", time.Now())
}
```

## With Graceful Shutdown

Here's a more production-ready version with a stop signal:

```go
package main

import (
	"fmt"
	"time"
)

func main() {
	stopChan := make(chan bool)

	// Start the background task
	go runPeriodicTask(2*time.Second, stopChan)

	// Simulate running for 10 seconds, then stop
	time.Sleep(10 * time.Second)
	stopChan <- true

	fmt.Println("Task stopped")
}

func runPeriodicTask(interval time.Duration, stop <-chan bool) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			doWork()
		case <-stop:
			return
		}
	}
}

func doWork() {
	fmt.Println("Working at", time.Now())
}
```

## Key Points

- **`time.NewTicker()`** - Creates a ticker that fires at regular intervals
- **`defer ticker.Stop()`** - Always stop the ticker to free resources
- **`for range ticker.C`** - Simple loop (no graceful shutdown)
- **`select`** - Allows listening to multiple channels (ticker + stop signal)
- **Goroutine** - Run in background with `go`

Choose the first pattern for simple cases, the second for anything that needs to stop cleanly.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Periodic Background Task Pattern

Here's the idiomatic Go approach using `time.Ticker` and `context.Context`:

```go
package main

import (
	"context"
	"log/slog"
	"time"
)

// StartPeriodicTask launches a background goroutine that runs fn every interval.
// It returns a stop function; call it to gracefully shut down the task.
func StartPeriodicTask(ctx context.Context, interval time.Duration, fn func(context.Context) error) func() {
	ctx, cancel := context.WithCancel(ctx)
	
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		
		// Run once immediately (optional; remove if you want to wait for first tick).
		if err := fn(ctx); err != nil {
			slog.Error("periodic task failed", "err", err)
		}
		
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if err := fn(ctx); err != nil {
					slog.Error("periodic task failed", "err", err)
				}
			}
		}
	}()
	
	return cancel
}

// Example usage:
func main() {
	ctx := context.Background()
	
	stop := StartPeriodicTask(ctx, 5*time.Second, func(ctx context.Context) error {
		slog.Info("doing work...")
		// Your actual work here; respect ctx.Done() for cancellation.
		return nil
	})
	
	// Let it run for a bit, then stop.
	time.Sleep(20 * time.Second)
	stop()
	
	slog.Info("task stopped")
}
```

## Key Points

1. **`time.Ticker`** — creates a channel that fires at regular intervals. Always `defer ticker.Stop()` to free resources.

2. **`select` with `<-ctx.Done()`** — the goroutine exits cleanly when the context is cancelled. This is how you stop the task.

3. **Return a `cancel` function** — lets the caller shut down the task without managing the context themselves. Alternatively, return the `cancel` directly if you want the caller to manage it.

4. **Error handling** — log errors but don't crash the loop. The task keeps running even if one iteration fails.

5. **Run-once-immediately (optional)** — the first `fn(ctx)` call before the loop lets you execute work right away instead of waiting for the first tick. Remove it if you prefer to wait.

## Variant: With a `sync.WaitGroup` (if you need to wait for completion)

```go
func StartPeriodicTask(ctx context.Context, interval time.Duration, fn func(context.Context) error) func() {
	ctx, cancel := context.WithCancel(ctx)
	var wg sync.WaitGroup
	wg.Add(1)
	
	go func() {
		defer wg.Done()
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if err := fn(ctx); err != nil {
					slog.Error("periodic task failed", "err", err)
				}
			}
		}
	}()
	
	return func() {
		cancel()
		wg.Wait() // Block until the goroutine exits.
	}
}
```

Use this if you need to ensure the task has fully shut down before proceeding (e.g., before closing a database connection).

## Variant: With a timeout per iteration

```go
case <-ticker.C:
	// Give each iteration a 10-second deadline.
	iterCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	if err := fn(iterCtx); err != nil {
		slog.Error("periodic task failed", "err", err)
	}
	cancel()
```

This ensures no single iteration hangs forever.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria, but Answer B is more idiomatic and production-quality: it wraps the pattern in a reusable function that accepts a `work func(context.Context) error`, forwards the context into the work function for proper cancellation of downstream I/O, returns an error for the caller to handle, and uses `slog` for structured logging. Answer A is correct and clear but slightly less polished—it uses a bare `time.Time` parameter for work, has a minor resource-management concern (the `time.Sleep` at shutdown instead of a WaitGroup), and doesn't propagate context into the work function.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.Context | skill |
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
| avoids time.Tick (which leaks) | ✗ | `time.Tick(` |

<details><summary>opus: baseline answer</summary>

# Basic Go Periodic Background Task Pattern

Here's the idiomatic pattern using `time.Ticker` with proper cancellation via `context.Context`:

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

func runPeriodicTask(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop() // Always stop the ticker to release resources

	for {
		select {
		case <-ctx.Done():
			fmt.Println("Stopping periodic task:", ctx.Err())
			return
		case t := <-ticker.C:
			doWork(t)
		}
	}
}

func doWork(t time.Time) {
	fmt.Println("Doing work at", t.Format(time.RFC3339))
	// ... your actual work here ...
}

func main() {
	// Cancel on Ctrl+C / SIGTERM
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go runPeriodicTask(ctx, 2*time.Second)

	<-ctx.Done() // Block until signal received
	fmt.Println("Shutting down...")
	time.Sleep(100 * time.Millisecond) // Give goroutine a moment to exit
}
```

## Key Points

1. **`time.NewTicker`** — fires on a channel at a regular interval. Use this instead of `time.Sleep` in a loop because it doesn't drift as much.

2. **`defer ticker.Stop()`** — important! A ticker is not garbage-collected until stopped.

3. **`select` with `ctx.Done()`** — gives you clean cancellation. Without this, your goroutine leaks.

4. **Run an iteration immediately?** Tickers wait one interval before the first tick. If you want to run right away:
   ```go
   for {
       doWork(time.Now())
       select {
       case <-ctx.Done():
           return
       case <-ticker.C:
       }
   }
   ```

5. **Long-running work?** If `doWork` can take longer than the interval, ticks may pile up (the channel is buffered to 1, so extras are dropped — usually what you want). For heavy jobs, consider running them in their own goroutine or using `time.AfterFunc` to schedule the next run after completion.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Periodic Background Task in Go

The idiomatic pattern uses `time.Ticker` inside a `select` loop with `context.Context` for cancellation.

```go
package worker

import (
	"context"
	"fmt"
	"log/slog"
	"time"
)

// Run executes work every interval until ctx is cancelled.
// It returns the reason it stopped (typically ctx.Err()).
func Run(ctx context.Context, interval time.Duration, work func(context.Context) error) error {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if err := work(ctx); err != nil {
				slog.ErrorContext(ctx, "periodic work failed", "err", err)
				// Continue ticking; don't kill the loop on a single failure.
				// If you want fail-fast behavior, return the error here instead.
			}
		}
	}
}
```

## Calling it

```go
func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Wire up signal handling so Ctrl-C cancels ctx (real code: signal.NotifyContext).
	go func() {
		if err := Run(ctx, 5*time.Second, doWork); err != nil {
			slog.Info("worker stopped", "reason", err)
		}
	}()

	// ... rest of program; calling cancel() shuts the worker down cleanly.
}

func doWork(ctx context.Context) error {
	// Pass ctx down so any I/O the work does is also cancellable.
	fmt.Println("tick at", time.Now())
	return nil
}
```

## Why this shape

- **`defer ticker.Stop()`** — `time.Ticker` holds a runtime resource; not stopping it leaks until GC.
- **`ctx.Done()` in the same `select` as `ticker.C`** — guarantees the goroutine has a known exit. Without this, `Run` would be the kind of unbounded `go func()` that leaks.
- **`context.Context` is the first arg** — and is forwarded into `work`, so any HTTP calls, DB queries, etc. inside `work` cancel promptly instead of finishing a 30-second request after shutdown.
- **Errors are logged, not fatal** — a periodic task that dies on the first transient failure is usually wrong. Log with `slog` and keep ticking. (Flip to `return err` if you want fail-fast.)
- **First tick fires after `interval`, not immediately.** If you want an immediate run, call `work(ctx)` once before the loop.

## Common variants

**Run once immediately, then on each tick:**

```go
for {
    if err := work(ctx); err != nil {
        slog.ErrorContext(ctx, "periodic work failed", "err", err)
    }
    select {
    case <-ctx.Done():
        return ctx.Err()
    case <-ticker.C:
    }
}
```

**Avoid overlapping runs if `work` can exceed `interval`:** the pattern above already serializes runs (next tick waits for `work` to return). If you instead want to *skip* missed ticks rather than queue them, that's the default `time.Ticker` behavior — it drops ticks when the receiver is slow. If you want concurrent runs, launch `go work(ctx)` inside the tick case (and bound concurrency with a semaphore).

## Things to avoid

- `time.Sleep(interval)` in a `for` loop — not cancellable; the goroutine sleeps through shutdown.
- `time.Tick(interval)` — convenient but the underlying ticker can never be stopped, so it leaks. Use `time.NewTicker` + `defer Stop()`.
- Storing `ctx` in a struct field on the worker — pass it as a parameter to `Run`.

</details>

---

### `receiver-consistency`

**Prompt**

```
I have a struct `Counter` with a method `Inc()` that increments an
internal field. Should the receiver be a value `(c Counter)` or a
pointer `(c *Counter)`? Why?
```

**Judge focus:** The better answer explains that mutation requires a pointer receiver AND
that receiver kind should be consistent across all methods on the type.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend a pointer receiver and explain mutation visibility, but Answer B goes significantly further by covering addressability, interface satisfaction, and mutex safety — all practically important consequences of the pointer receiver choice. Answer B also leads with the consistency rule more prominently and provides a more comprehensive decision checklist. Answer A is solid but more basic in comparison.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends pointer receiver | tie |
| mentions consistency across methods on the type | tie |
| explains why (mutation visibility) | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

<details><summary>sonnet: baseline answer</summary>

## Pointer vs Value Receiver for `Counter.Inc()`

You should use a **pointer receiver** `(c *Counter)`. Here's why:

---

### The Core Problem with Value Receivers

```go
type Counter struct {
    count int
}

// ❌ Value receiver - WRONG for mutation
func (c Counter) Inc() {
    c.count++ // modifies a COPY, original is unchanged
}

// ✅ Pointer receiver - CORRECT for mutation  
func (c *Counter) Inc() {
    c.count++ // modifies the ORIGINAL value
}
```

---

### Demonstration of the Difference

```go
func main() {
    c := Counter{}

    // With value receiver (broken)
    c.Inc()
    fmt.Println(c.count) // 0 — nothing changed!

    // With pointer receiver (correct)
    c.Inc()
    fmt.Println(c.count) // 1 — works as expected
}
```

---

### Why This Happens

| | Value Receiver `(c Counter)` | Pointer Receiver `(c *Counter)` |
|---|---|---|
| Receives | A **copy** of the struct | The **memory address** of the struct |
| Mutations affect | The copy only | The original struct |
| Caller sees changes | ❌ No | ✅ Yes |

---

### The Rules of Thumb

```
1. Method needs to MUTATE the receiver  → pointer receiver
2. Struct is LARGE (avoid copying)      → pointer receiver
3. Consistency (other methods use ptr)  → pointer receiver
4. Method only READS, struct is small   → value receiver is fine
```

---

### Practical Consistency Rule

If **any** method on a type needs a pointer receiver, it's best practice
to use pointer receivers for **all** methods on that type:

```go
type Counter struct {
    count int
}

func (c *Counter) Inc()           { c.count++ }
func (c *Counter) Reset()         { c.count = 0 }
func (c *Counter) Value() int     { return c.count } // consistent, even though read-only
```

---

### Key Takeaway

> A value receiver works on a **copy** — any changes are thrown away
> when the method returns. Since `Inc()` exists specifically to mutate
> state, a value receiver would silently do nothing, making it a
> particularly dangerous bug to have.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Use a **pointer receiver** `(c *Counter)`.

## The Rule

> If any method on a type needs a pointer receiver, **all** methods should use pointer receivers — consistency matters as much as correctness.

For `Counter`, the mutation requirement alone settles it.

## Why a Value Receiver Fails Here

```go
type Counter struct {
    count int
}

// ❌ Value receiver — operates on a COPY
func (c Counter) Inc() {
    c.count++ // mutates the copy; caller's Counter is unchanged
}

func main() {
    c := Counter{}
    c.Inc()
    fmt.Println(c.count) // 0 — the increment was lost
}
```

Go passes the receiver by value, exactly like any other function argument. `c.count++` modifies a throwaway copy.

## Pointer Receiver — Correct

```go
type Counter struct {
    count int
}

// ✅ Pointer receiver — operates on the original
func (c *Counter) Inc() {
    c.count++
}

func (c *Counter) Value() int {
    return c.count
}

func main() {
    c := Counter{}
    c.Inc()
    c.Inc()
    fmt.Println(c.Value()) // 2
}
```

## Practical Consequences

**Addressability.** You can only call a pointer-receiver method on an addressable value. A `Counter` stored in a variable is addressable; one returned directly from a function call is not.

```go
// Fine — variable is addressable; Go auto-takes its address
c := Counter{}
c.Inc() // sugar for (&c).Inc()

// Compile error — function return value is not addressable
NewCounter().Inc() // cannot take the address of NewCounter()
```

**Interface satisfaction.** `*Counter` satisfies any interface requiring `Inc()` and `Value()`. A plain `Counter` value does **not** — its method set excludes pointer-receiver methods.

```go
type Incrementer interface {
    Inc()
}

var _ Incrementer = &Counter{} // ✅ compiles
var _ Incrementer = Counter{}  // ❌ Counter does not implement Incrementer
```

This matters when you store a `Counter` in an interface variable or pass it to a function expecting `Incrementer`.

**Concurrency.** Once you have a pointer receiver, adding a mutex is straightforward and correct:

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

A value receiver would copy the mutex — which is a data race and explicitly forbidden by `go vet`.

## Decision Checklist

| Question | Answer → receiver |
|---|---|
| Does any method mutate the receiver? | Pointer |
| Does the type contain a `sync.Mutex` or similar? | Pointer (never copy) |
| Is the struct large (copying is expensive)? | Pointer |
| Is the type small, immutable, and copied intentionally (like `time.Time`)? | Value |
| Are other methods already pointer receivers? | Match them — pointer |

`Counter` hits the first criterion immediately. Use `*Counter` throughout.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B covers all three rubric criteria while Answer A only covers two. Both correctly recommend pointer receivers and explain mutation visibility with clear examples. However, Answer B explicitly addresses the consistency rule across all methods on a type, including a concrete example of how mixing receiver types breaks the method set — which is the key differentiator in the focus area.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends pointer receiver | tie |
| mentions consistency across methods on the type | skill |
| explains why (mutation visibility) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✗ | |
| explains why (mutation visibility) | ✓ | `mutat` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

<details><summary>haiku: baseline answer</summary>

# Receiver Type for `Inc()` Method

**Use a pointer receiver `(c *Counter)`.**

## Why?

### The Problem with Value Receivers

With a value receiver, `Inc()` operates on a **copy** of the struct:

```go
type Counter struct {
    count int
}

func (c Counter) Inc() {  // ❌ Value receiver
    c.count++
}

func main() {
    var counter Counter
    counter.Inc()
    fmt.Println(counter.count)  // Output: 0 (unchanged!)
}
```

The increment happens on the copy, not the original struct.

### The Solution: Pointer Receiver

With a pointer receiver, you modify the **original** struct:

```go
func (c *Counter) Inc() {  // ✅ Pointer receiver
    c.count++
}

func main() {
    var counter Counter
    counter.Inc()
    fmt.Println(counter.count)  // Output: 1 (correct!)
}
```

## Key Principles

1. **Use pointer receivers when the method modifies the receiver** (mutating methods)
2. **Use value receivers for read-only operations** (non-mutating methods)

## Bonus: Go's Convenience

Go automatically converts between values and pointers for method calls:

```go
counter.Inc()      // Go automatically passes &counter
(&counter).Inc()   // Explicit pointer (also works)
```

This works in both directions, but the receiver type you define determines the actual behavior.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Receiver Choice for `Counter.Inc()`

**Use a pointer receiver: `(c *Counter) Inc()`**

## Why

`Inc()` **mutates** the receiver. With a value receiver, you'd be incrementing a *copy* of the struct, leaving the original unchanged:

```go
// ❌ WRONG: value receiver
type Counter struct {
    count int
}

func (c Counter) Inc() {
    c.count++  // increments the copy, not the original
}

func main() {
    var counter Counter
    counter.Inc()
    fmt.Println(counter.count)  // prints 0, not 1
}
```

With a pointer receiver, you mutate the original:

```go
// ✅ CORRECT: pointer receiver
func (c *Counter) Inc() {
    c.count++  // increments the original
}

func main() {
    var counter Counter
    counter.Inc()
    fmt.Println(counter.count)  // prints 1
}
```

## The Consistency Rule

Once you choose pointer for one method, **use pointer for all methods on that type**. Mixing breaks the method set in subtle ways:

```go
// ❌ INCONSISTENT
func (c Counter) Value() int {      // value receiver
    return c.count
}

func (c *Counter) Inc() {           // pointer receiver
    c.count++
}

// Now you can't call Value() on a *Counter without dereferencing:
var p *Counter
p.Value()  // ✗ compile error: *Counter has no method Value
(*p).Value()  // ✓ works, but awkward
```

Keep it uniform:

```go
// ✅ CONSISTENT
func (c *Counter) Value() int {
    return c.count
}

func (c *Counter) Inc() {
    c.count++
}

var p *Counter
p.Value()  // ✓ works
p.Inc()    // ✓ works
```

## When Value Receivers Are Right

Use value receivers for **small, immutable types** where copying is cheap and you never mutate:

```go
// ✅ Value receiver is fine here
type Point struct {
    X, Y float64
}

func (p Point) Distance() float64 {
    return math.Sqrt(p.X*p.X + p.Y*p.Y)
}

// ✅ Also fine: time.Time, net.IP, small enums
```

**Rule of thumb:** If the type has a `Mutex`, a slice, or any field you'll ever modify, use pointer receivers everywhere.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend a pointer receiver and explain mutation visibility, but Answer A more explicitly and thoroughly addresses the consistency requirement across all methods on the type, explaining the method set implications in detail. Answer A also provides a complete, idiomatic Counter implementation showing both methods with pointer receivers, making the consistency principle concrete. Answer B mentions consistency but treats it as a secondary bullet point without the same depth of explanation about why it matters.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends pointer receiver | tie |
| mentions consistency across methods on the type | skill |
| explains why (mutation visibility) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `Pointer Receiver` |
| mentions consistency across methods on the type | ✓ | `consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `Pointer receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

<details><summary>opus: baseline answer</summary>

# Use a Pointer Receiver: `(c *Counter) Inc()`

## Why

A method with a **value receiver** operates on a *copy* of the struct. Any mutation to the field inside the method affects only that copy, which is discarded when the method returns.

```go
func (c Counter) Inc() {
    c.count++ // modifies the copy, not the original
}

var x Counter
x.Inc()
fmt.Println(x.count) // 0  — surprise!
```

A **pointer receiver** lets the method mutate the actual struct the caller holds:

```go
func (c *Counter) Inc() {
    c.count++ // modifies the original
}

var x Counter
x.Inc()
fmt.Println(x.count) // 1  ✅
```

## General Rule of Thumb

From the [Go wiki / Effective Go guidance](https://go.dev/wiki/CodeReviewComments#receiver-type):

1. **If the method mutates the receiver → pointer receiver.** ← your case
2. If the struct is large and copying is expensive → pointer receiver.
3. If the struct contains a `sync.Mutex` or similar non-copyable field → pointer receiver.
4. For consistency, if *some* methods on the type need pointer receivers, make *all* of them pointer receivers.
5. Only use value receivers for small, immutable, value-like types (e.g., `time.Time`, `image.Point`).

## Bonus: Method Set Consideration

If you want `*Counter` to satisfy an interface that includes `Inc()`, a pointer receiver works either way (both `Counter` and `*Counter` can call it, given an addressable value). But if you ever need to call `Inc()` on a value returned from a map or interface, only the pointer-receiver version is reliably callable on the *original*.

So: **`func (c *Counter) Inc()`** — because the whole point of the method is to change state.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Pointer receiver: `func (c *Counter) Inc()`

A value receiver gets a **copy** of the struct, so any mutation happens on that copy and is discarded when the method returns. Your counter would never actually increment from the caller's perspective:

```go
type Counter struct{ n int }

// WRONG: mutates a copy, caller sees nothing change
func (c Counter) Inc() { c.n++ }

// RIGHT: mutates the original through the pointer
func (c *Counter) Inc() { c.n++ }
```

## The two reasons in order of importance

1. **Mutation requires a pointer.** This is the deciding rule. If the method changes the receiver's state, the receiver must be a pointer — otherwise the change is invisible to the caller. `Inc()` is the textbook example.

2. **Consistency across the type.** Once *any* method on `Counter` needs a pointer receiver (and `Inc` does), **all** methods on `Counter` should use pointer receivers, even read-only ones like `Value()`. Mixing receiver kinds on the same type is a Go style violation because:
   - It muddles the method set: `*Counter` satisfies interfaces requiring value-receiver methods, but `Counter` does **not** satisfy interfaces requiring pointer-receiver methods. Mixing makes it hard to predict which form users need.
   - It signals confused ownership semantics to readers.

## So your `Counter` should look like

```go
type Counter struct {
    n int
}

func (c *Counter) Inc()       { c.n++ }
func (c *Counter) Value() int { return c.n }
```

And callers must hold a `*Counter`:

```go
c := &Counter{}     // or: var c Counter; c.Inc() works too — Go auto-addresses
c.Inc()
fmt.Println(c.Value()) // 1
```

## One important caveat: concurrency

If multiple goroutines will call `Inc()`, a pointer receiver alone is **not** safe — you've now got shared mutable state and need synchronization. Two idiomatic options:

```go
// Option A: mutex-guarded
type Counter struct {
    mu sync.Mutex
    n  int
}
func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}

// Option B: atomic (Go 1.19+), zero value usable, no mutex needed
type Counter struct {
    n atomic.Int64
}
func (c *Counter) Inc()         { c.n.Add(1) }
func (c *Counter) Value() int64 { return c.n.Load() }
```

Both still use pointer receivers — `sync.Mutex` and `atomic.Int64` must not be copied after first use, which reinforces the same answer.

</details>

---

### `interface-placement`

**Prompt**

```
In Go, when my function takes a parameter that is "anything that has a
Read method", where should I declare that interface — in the package
that defines the concrete reader, or in the package that consumes it?
```

**Judge focus:** The better answer says interfaces belong in the consumer package and
should be small, citing the "accept interfaces, return concrete types" rule.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the consumer package as the right place for interfaces and cite 'accept interfaces, return concrete types', but Answer A provides significantly more depth, practical guidance, and nuance. Answer A includes a decision guide table, explains testability benefits, discusses the io.Reader exception more thoroughly, and explains why producer-declared interfaces cause coupling problems with concrete examples. Answer A also gives better small interface guidance by explaining that consumer-owned interfaces naturally stay minimal.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| says consumer / caller package | tie |
| mentions accept interfaces, return concrete | tie |
| small interface guidance | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `consumer` |
| mentions accept interfaces, return concrete | ✓ | `accept interfaces` |
| small interface guidance | ✓ | `io.Reader` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `consumer` |
| mentions accept interfaces, return concrete | ✓ | `accept interfaces` |
| small interface guidance | ✓ | `one method` |

<details><summary>sonnet: baseline answer</summary>

## Interface Placement in Go

In Go, you should declare the interface in the **consuming package** (the one that uses it). This is a core Go idiom sometimes called **"accept interfaces, return concrete types"**.

---

### The Go Philosophy

> *"Don't design with interfaces, discover them."*

Interfaces in Go are **implicitly satisfied**, so the consumer declares exactly what it needs, and any concrete type that happens to match will satisfy it — with no coupling between packages.

---

### Example

```
myapp/
├── disk/
│   └── file.go        # concrete type
├── network/
│   └── conn.go        # another concrete type
└── processor/
    ├── reader.go      # declares the interface
    └── process.go     # consumes it
```

**`disk/file.go`** — concrete type, no interface knowledge
```go
package disk

type File struct { /* ... */ }

func (f *File) Read(p []byte) (n int, err error) {
    // ...
    return
}
```

**`network/conn.go`** — another concrete type, also unaware of any interface
```go
package network

type Conn struct { /* ... */ }

func (c *Conn) Read(p []byte) (n int, err error) {
    // ...
    return
}
```

**`processor/reader.go`** — the consumer owns the interface
```go
package processor

// Reader is declared HERE, in the consuming package.
// It describes only what THIS package needs.
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

**`processor/process.go`** — uses the interface
```go
package processor

func Process(r Reader) error {
    buf := make([]byte, 1024)
    n, err := r.Read(buf)
    // ...
    _ = n
    return err
}
```

Both `disk.File` and `network.Conn` satisfy `processor.Reader` **without importing `processor`**.

---

### Why This Matters

| Approach | Problem |
|---|---|
| Interface in **producer** package | Creates unnecessary coupling; producer must anticipate all consumers |
| Interface in **consumer** package ✅ | Decoupled; consumer declares only what it needs |

---

### The Standard Library Does This

`io.Reader` is a **rare, justified exception** — it lives in `io` because it's a universal primitive used everywhere. The Go team explicitly calls out that small, standard interfaces like this earn a shared home.

For your own code, the rule holds: **the consumer owns the interface**.

---

### Key Takeaway

```
Producer package  →  exports a concrete type
Consumer package  →  declares the interface it needs
```

This keeps packages loosely coupled and is idiomatic Go. The implicit satisfaction of interfaces is specifically designed to enable this pattern.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Declare the interface in the consumer package.

This is one of Go's most important design principles, and it's the opposite of what most OOP languages teach.

---

### The rule: accept interfaces, return concrete types

The package that *needs* the behavior owns the interface describing it. The package that *provides* the behavior just ships a concrete type — it doesn't know or care which interfaces that type will satisfy.

```
producer/
    file.go        // defines File with a Read method — no interface declared here

consumer/
    process.go     // declares Reader interface, accepts it as a parameter
```

```go
// consumer/process.go

package consumer

// Reader is declared here, in the package that needs it.
// File from the producer package satisfies this implicitly.
type Reader interface {
    Read(p []byte) (n int, err error)
}

func Process(r Reader) error {
    // ...
}
```

The `producer.File` type satisfies `consumer.Reader` without any explicit declaration — Go's structural typing handles it automatically.

---

### Why not declare it in the producer package?

If the producer declares the interface, every consumer must import the producer just to name the type — even if they only care about one method. That creates **unnecessary coupling**.

```go
// ❌ Producer-declared interface forces this import everywhere
import "github.com/myorg/producer"

func Process(r producer.Reader) error { ... }
```

Now your consumer depends on the producer's entire package for what is essentially a behavioral contract. Worse, the producer has to anticipate every interface its callers might want — which is impossible.

---

### The stdlib proves this works at scale

`io.Reader` is the famous exception that proves the rule: it lives in `io` because it's a *universal vocabulary type* used by both producers and consumers across the entire ecosystem. Your own packages rarely reach that level of generality.

Notice that `os.File`, `bytes.Buffer`, `strings.Reader`, and `net.Conn` all satisfy `io.Reader` without importing each other. Each is a concrete type; the interface lives in a neutral package that predates all of them.

For your own code, if you find yourself wanting to put an interface in a "shared" package so multiple consumers can use it, that's a signal to ask whether `io.Reader` (or another stdlib interface) already covers your need.

---

### Practical consequences

**Testability is free.** Because the consumer owns the interface, you can swap in a fake without touching the producer:

```go
// In your test file — no build tags, no mock framework needed
type fakeReader struct{ data []byte }

func (f *fakeReader) Read(p []byte) (int, error) {
    n := copy(p, f.data)
    return n, io.EOF
}

func TestProcess(t *testing.T) {
    err := Process(&fakeReader{data: []byte("hello")})
    // ...
}
```

**Interfaces stay minimal.** When the consumer declares the interface, it only lists the methods it actually calls. Producer-declared interfaces tend to grow to cover every method on the type, which makes them harder to satisfy and harder to test against.

**The producer can evolve freely.** Adding methods to `File` never breaks any consumer's interface — consumers only declared the methods they use.

---

### Quick decision guide

| Situation | Where to declare |
|---|---|
| Your package needs "anything with Read" | Your package |
| Two of your packages share the same behavioral contract | The lower-level one, or a small dedicated `xio`-style package |
| The interface is a universal vocabulary (like `io.Reader`) | A shared foundation package — but this is rare |
| You're tempted to put it in the producer "so callers know what to pass" | Resist; let structural typing do its job |

The concrete type in the producer package is the source of truth for *what exists*. The interface in the consumer package is the source of truth for *what's needed*. Keeping those separate is what makes Go's type system so composable.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the consumer package as the right place for interfaces and demonstrate Go's structural typing. Answer B is more thorough and useful, providing a complete working example with three separate packages showing the full picture, explicitly discussing the 'accept interfaces, return concrete types' principle through its structure, and addressing edge cases like shared interfaces and stdlib exceptions. Answer A contains a minor inaccuracy by claiming io.Reader is defined in the io package because io is a 'consumer' of abstractions, which is a stretch. Answer B also more clearly articulates small interface guidance through its use of io.Reader as the canonical example.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| says consumer / caller package | tie |
| mentions accept interfaces, return concrete | skill |
| small interface guidance | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `consumer` |
| mentions accept interfaces, return concrete | ✗ | |
| small interface guidance | ✓ | `io.Reader` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `Consumer` |
| mentions accept interfaces, return concrete | ✗ | |
| small interface guidance | ✓ | `io.Reader` |

<details><summary>haiku: baseline answer</summary>

# Interface Location in Go

**Declare the interface in the package that *consumes* it** (the package that needs the `Read` method).

This is a fundamental Go design principle. Here's why:

## The Right Way

```go
// package myapp - the consumer
package myapp

import "io"

// Define the interface you actually need
type Reader interface {
    Read(p []byte) (n int, err error)
}

func ProcessData(r Reader) {
    // use r
}
```

Or better yet, use the standard library's `io.Reader`:

```go
package myapp

import "io"

func ProcessData(r io.Reader) {
    // use r
}
```

## Why Not in the Producer's Package?

```go
// ❌ DON'T do this
package filelib

type Reader interface {
    Read(p []byte) (n int, err error)
}

type File struct { /* ... */ }
func (f *File) Read(p []byte) (n int, err error) { /* ... */ }
```

**Problems:**
- Creates unnecessary coupling between packages
- The producer doesn't know what interfaces consumers need
- Violates the Dependency Inversion Principle
- Makes the producer package depend on consumer needs

## Key Principle

> **Depend on abstractions defined as close as possible to where they're used.**

The consumer knows what behavior it needs. The concrete type automatically satisfies any interface with matching methods (structural typing), so:

- `filelib.File` will automatically satisfy `myapp.Reader`
- No explicit declaration needed
- Loose coupling achieved

This is why Go's standard library defines `io.Reader`, `io.Writer`, etc. in the `io` package—they're the *consumers* of these abstractions.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Interface Declaration: Consumer Package

**Declare the interface in the package that *consumes* it, not the producer.**

This is one of Go's most important design principles. Here's why and how:

## The Rule

```go
// ❌ WRONG: producer package defines the interface
package file

type Reader interface {
    Read(p []byte) (n int, err error)
}

type FileReader struct { /* ... */ }
func (f *FileReader) Read(p []byte) (n int, err error) { /* ... */ }

// Now consumers must import "file" just to use the interface
```

```go
// ✅ RIGHT: consumer package defines the interface
package processor

import "io"

// Processor accepts anything with a Read method.
// io.Reader is already defined in the stdlib.
func Process(r io.Reader) error {
    // ...
}

// Your concrete type lives elsewhere:
// package file
type FileReader struct { /* ... */ }
func (f *FileReader) Read(p []byte) (n int, err error) { /* ... */ }

// FileReader satisfies io.Reader implicitly.
// processor doesn't import file; file doesn't import processor.
```

## Why This Matters

1. **Decoupling** — The consumer declares what behavior it needs. The producer doesn't need to know about every package that might use it. No circular imports, no tight coupling.

2. **Implicit satisfaction** — Go's structural typing means `FileReader` automatically satisfies `io.Reader` without an explicit declaration. The producer never needs to import the consumer's package.

3. **Reusability** — Your `FileReader` can satisfy *many* interfaces defined in different packages, all without modification.

4. **API stability** — If you own the producer, you don't have to predict every interface consumers might want. They define what they need.

## Real Example

```go
// package myapp/processor
package processor

import "io"

// ProcessFile reads from any io.Reader and does something with it.
func ProcessFile(r io.Reader) error {
    data, err := io.ReadAll(r)
    if err != nil {
        return fmt.Errorf("read: %w", err)
    }
    // ... process data
    return nil
}

// ----

// package myapp/file
package file

type FileReader struct {
    path string
}

func (f *FileReader) Read(p []byte) (n int, err error) {
    // implementation
}

// ----

// package main
package main

import (
    "myapp/file"
    "myapp/processor"
)

func main() {
    fr := &file.FileReader{path: "data.txt"}
    processor.ProcessFile(fr)  // ✅ Works! FileReader satisfies io.Reader
}
```

Notice:
- `processor` imports `io` (stdlib), not `file`.
- `file` doesn't import `processor`.
- `FileReader` satisfies `io.Reader` automatically.

## When You Own Both Packages

If you're writing both the producer and consumer in the same project:

- **Still define the interface in the consumer** — it clarifies what behavior the consumer actually needs.
- If the interface is so general it's used by many packages, consider putting it in a small, focused package (like `io` in stdlib) that both can import without creating a cycle.

## Exception: Stdlib and Well-Known Interfaces

The stdlib defines interfaces like `io.Reader`, `io.Writer`, `fmt.Stringer`, `error`, `context.Context` in their "natural" homes because they're so fundamental that *everything* depends on them. This is acceptable because:
- They're stable and rarely change.
- They're in the stdlib, not your project.
- They're designed to be depended on by many packages.

For your own code, follow the consumer rule.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly identify the consumer package as the right place to declare interfaces, cite the 'accept interfaces, return concrete types' rule, and emphasize small interfaces. Answer A provides a slightly cleaner explanation of the stdlib exception and has a more polished structure, while Answer B's rule-of-thumb summary and promotion guidance are equally useful. Neither answer is meaningfully better across all criteria.

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
| small interface guidance | ✓ | `small interface` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `consumer` |
| mentions accept interfaces, return concrete | ✓ | `accept interfaces` |
| small interface guidance | ✓ | `io.Reader` |

<details><summary>opus: baseline answer</summary>

# Short answer

**Declare it in the consuming package.**

# Why

Go interfaces are satisfied implicitly. The concrete type doesn't need to know about — or import — the interface to satisfy it. This inverts the usual OO dependency direction and lets you follow a few important conventions:

### 1. "Accept interfaces, return structs"
The consumer knows what it actually needs. If your function only calls `Read`, it should depend on the smallest possible interface describing exactly that, defined where it's used.

### 2. Keep interfaces small and local
Each consumer can declare its own minimal interface containing just the methods it uses. This avoids forcing every reader-producing package to import some shared "interfaces" package, and avoids bloated interfaces that grow over time.

```go
// in package consumer
type reader interface {
    Read(p []byte) (n int, err error)
}

func Process(r reader) error { ... }
```

### 3. Avoid import cycles and tight coupling
If the producer package declared the interface, every consumer would have to import the producer just to name the type. Defining it on the consumer side means the producer has zero knowledge of who uses it.

### 4. It matches the standard library
`io.Reader` lives in `io`, not in `os` or `bytes` or `net`. The `io` package is effectively a "consumer-style" package of abstractions that many other packages happen to satisfy. Your own small interface is the same idea at a smaller scale.

# When to put it elsewhere

- **A widely-shared abstraction** (used by many consumers across your codebase) is worth promoting to a neutral package — similar to how `io.Reader` graduated to a shared spot. But start local; promote only when duplication actually hurts.
- **Never** put it in the producer package solely because that package defines the concrete type. That's the OO instinct, and it's the wrong one in Go.

# Rule of thumb

> The package that *calls* `Read` owns the interface. The package that *implements* `Read` doesn't even need to know the interface exists.

</details>

<details><summary>opus: skill-loaded answer</summary>

Declare it in the **consuming package**, not the producing one.

This is one of Go's defining idioms — sometimes phrased as **"accept interfaces, return concrete types"** or **"the consumer defines the interface."**

## Why

1. **The consumer knows what it actually needs.** If your function only calls `Read`, it should depend on exactly that — not on whatever broader surface the producer happens to expose. Small, locally-defined interfaces minimize coupling.

2. **Producers shouldn't have to predict every consumer.** If `pkg/storage` defined a `Reader` interface for every possible client, it would either bloat or constrain its API. Letting consumers declare their own keeps the producer free to evolve.

3. **Implicit satisfaction makes it free.** Go interfaces are structural — the concrete type doesn't need to import or know about the interface. So the consumer can declare exactly what it wants, and any type with a matching method set satisfies it automatically.

4. **Testability without mocks-as-a-service.** When the interface lives next to the function that uses it, you can swap in a `bytes.Buffer`, a `strings.Reader`, or a one-off test fake without dragging in the producer package.

## The exception

`io.Reader` already exists in the standard library — and that's the *right* level for a universally-needed abstraction. The rule isn't "never put interfaces in shared packages"; it's "don't put them in the *producer* package." The stdlib's `io` package is neither producer nor consumer — it's a neutral home for a vocabulary type that everyone agrees on.

So in practice:

```go
// In your consuming package — preferred
package report

type sourceReader interface {
    Read(p []byte) (int, error)
}

func Generate(r sourceReader) error { ... }
```

Or, if the method set matches a stdlib interface exactly, just use it:

```go
func Generate(r io.Reader) error { ... }
```

What you should **not** do is define `type Reader interface { Read(...) }` inside the package that provides the concrete type and force consumers to import it.

</details>

---

### `slog-structured`

**Prompt**

```
What's the modern, idiomatic way in Go to log an error with structured
fields (e.g. user_id, request_id) so it's machine-readable in
production?
```

**Judge focus:** The better answer recommends log/slog with key-value attributes (or
typed slog.Int / slog.String builders), not log.Printf with a format
string, and isn't a third-party library when stdlib suffices.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use log/slog with structured fields and avoid log.Printf, satisfying all rubric criteria. However, Answer B is more idiomatic and production-focused: it emphasizes the *Context variants (ErrorContext, InfoContext) which are the preferred modern approach for carrying trace IDs, explicitly advises against the log-and-return antipattern, recommends slog.LogAttrs for hot paths, and gives cleaner guidance on library vs. application code. Answer A is comprehensive but slightly less opinionated and includes a table recommending third-party libraries (zerolog, zap) which slightly dilutes the stdlib-first message.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses log/slog | tie |
| shows a slog call with structured fields | tie |
| avoids recommending log.Printf for structured logging | skill |

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

<details><summary>sonnet: baseline answer</summary>

## Structured Logging in Go (Modern/Idiomatic)

### The Short Answer

Use **`log/slog`** — it's been in the standard library since **Go 1.21** and is the idiomatic choice today.

---

## Basic Setup

```go
package main

import (
    "log/slog"
    "os"
)

func main() {
    // JSON handler = machine-readable in production
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelDebug, // set minimum log level
    }))

    // Set as default so package-level functions work too
    slog.SetDefault(logger)
}
```

---

## Logging Errors with Structured Fields

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    userID := "usr_123"
    requestID := r.Header.Get("X-Request-ID")

    user, err := fetchUser(userID)
    if err != nil {
        // ✅ Idiomatic: key-value pairs after the message
        slog.Error("failed to fetch user",
            "error",      err,
            "user_id",    userID,
            "request_id", requestID,
        )
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    _ = user
}
```

**Output (JSON):**
```json
{
  "time": "2024-01-15T10:30:00.000Z",
  "level": "ERROR",
  "msg": "failed to fetch user",
  "error": "sql: no rows in result set",
  "user_id": "usr_123",
  "request_id": "req_abc456"
}
```

---

## Three Ways to Pass Fields

```go
// 1. ✅ Loose key-value pairs (simple, most common)
slog.Error("something failed",
    "error",   err,
    "user_id", userID,
)

// 2. ✅ slog.Attr (explicit typing, avoids mistakes like odd number of args)
slog.Error("something failed",
    slog.Any("error",   err),
    slog.String("user_id", userID),
    slog.Int("attempt",    3),
)

// 3. ✅ Grouped fields (useful for namespacing, e.g. "request.id")
slog.Error("something failed",
    slog.Group("request",
        slog.String("id",     requestID),
        slog.String("method", r.Method),
        slog.String("path",   r.URL.Path),
    ),
    slog.Any("error", err),
)
// → "request":{"id":"...","method":"GET","path":"/users"}
```

---

## Logger with Persistent Fields (Context)

Avoid repeating fields on every call — attach them once with `With`:

```go
// Per-request logger with fields baked in
func handleRequest(w http.ResponseWriter, r *http.Request) {
    log := slog.With(
        "request_id", r.Header.Get("X-Request-ID"),
        "user_id",    userIDFromContext(r.Context()),
        "method",     r.Method,
        "path",       r.URL.Path,
    )

    user, err := fetchUser(...)
    if err != nil {
        log.Error("failed to fetch user", "error", err)
        // ↑ request_id, user_id, method, path are automatically included
        return
    }

    log.Info("request completed", "status", 200)
}
```

---

## Passing Logger via Context (Production Pattern)

```go
// Store logger in context
type ctxKey struct{}

func WithLogger(ctx context.Context, log *slog.Logger) context.Context {
    return context.WithValue(ctx, ctxKey{}, log)
}

func FromContext(ctx context.Context) *slog.Logger {
    if log, ok := ctx.Value(ctxKey{}).(*slog.Logger); ok {
        return log
    }
    return slog.Default() // safe fallback
}

// Middleware that seeds the logger
func LoggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        log := slog.With(
            "request_id", r.Header.Get("X-Request-ID"),
            "user_id",    r.Header.Get("X-User-ID"),
        )
        ctx := WithLogger(r.Context(), log)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Deep in your call stack — no need to thread logger manually
func fetchUser(ctx context.Context, id string) (*User, error) {
    log := FromContext(ctx)

    user, err := db.QueryUser(id)
    if err != nil {
        log.Error("db query failed", "error", err, "user_id", id)
        return nil, err
    }
    return user, nil
}
```

---

## Development vs Production Config

```go
func newLogger(env string) *slog.Logger {
    if env == "production" {
        return slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
            Level:     slog.LevelInfo,
            AddSource: true, // adds "source":{"file":"...","line":42}
        }))
    }

    // Human-readable for local dev
    return slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelDebug,
    }))
    // → time=2024-01-15T10:30:00Z level=ERROR msg="failed to fetch user" error="..."
}
```

---

## Quick Reference: When to Use What

| Situation | Recommendation |
|---|---|
| Go 1.21+ project | `log/slog` — no external deps needed |
| Need high-performance logging | [`zerolog`](https://github.com/rs/zerolog) (zero-alloc) |
| Large existing codebase | [`zap`](https://github.com/uber-go/zap) (battle-tested at scale) |
| Need to wrap slog | Implement `slog.Handler` interface |

---

## Key Takeaways

- **`log/slog` is the standard** — no third-party library needed for most projects
- Always use **`NewJSONHandler`** in production for machine-readable output
- Use **`.With()`** to attach persistent fields instead of repeating them
- Pass loggers via **context** to avoid threading them through every function signature
- Prefer **`slog.Attr`** types (`slog.String`, `slog.Int`, etc.) when you want compile-time safety over loose key-value pairs

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Modern Structured Logging with `log/slog`

Since Go 1.21, the standard library includes `log/slog` — the idiomatic choice for structured, leveled, machine-readable logging. No third-party dependency required.

### Basic pattern

```go
slog.Error("failed to process payment",
    "err",        err,
    "user_id",    userID,
    "request_id", requestID,
)
```

In production, configure a **JSON handler** so every log line is a parseable object:

```go
// main.go — set up once at startup
logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
    Level: slog.LevelInfo, // or read from config/env
}))
slog.SetDefault(logger)
```

Output:
```json
{"time":"2024-11-01T12:00:00Z","level":"ERROR","msg":"failed to process payment","err":"context deadline exceeded","user_id":"u_123","request_id":"req_abc"}
```

---

### Carry fields through a request with `Logger.With`

Attach fields once and pass the enriched logger down — don't repeat them on every call:

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    log := slog.Default().With(
        "request_id", r.Header.Get("X-Request-ID"),
        "method",     r.Method,
        "path",       r.URL.Path,
    )

    userID, err := authenticate(r)
    if err != nil {
        log.Error("authentication failed", "err", err)
        http.Error(w, "unauthorized", http.StatusUnauthorized)
        return
    }

    log = log.With("user_id", userID) // enrich further as you learn more

    if err := processOrder(r.Context(), log, userID); err != nil {
        log.Error("order processing failed", "err", err)
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }
}
```

---

### Pass the logger explicitly — don't use globals in libraries

Global `slog.Error(...)` is fine in `main` and handlers. In reusable packages, accept a `*slog.Logger` parameter (or embed it in a service struct) so callers control the destination:

```go
type OrderService struct {
    db  *sql.DB
    log *slog.Logger
}

func NewOrderService(db *sql.DB, log *slog.Logger) *OrderService {
    return &OrderService{db: db, log: log}
}

func (s *OrderService) Process(ctx context.Context, orderID string) error {
    s.log.InfoContext(ctx, "processing order", "order_id", orderID)

    if err := s.db.QueryRowContext(ctx, ...).Scan(...); err != nil {
        return fmt.Errorf("fetch order %s: %w", orderID, err) // wrap, don't log here
    }
    return nil
}
```

> **Rule of thumb:** libraries should *return* errors with context (`%w`); only the *call site* that decides what to do with an error should log it. Logging and returning is almost always a mistake — it produces duplicate log lines.

---

### Use `*Context` variants to respect cancellation and carry trace IDs

Prefer `InfoContext`/`ErrorContext`/etc. over the bare versions — handlers can extract trace IDs from the context (e.g. OpenTelemetry):

```go
slog.ErrorContext(ctx, "cache miss", "key", cacheKey, "err", err)
```

---

### Group related fields with `slog.Group`

```go
slog.InfoContext(ctx, "request complete",
    slog.Group("http",
        "method",      r.Method,
        "path",        r.URL.Path,
        "status_code", status,
        "duration_ms", duration.Milliseconds(),
    ),
    "user_id", userID,
)
```

JSON output nests cleanly:
```json
{"level":"INFO","msg":"request complete","http":{"method":"POST","path":"/orders","status_code":200,"duration_ms":42},"user_id":"u_123"}
```

---

### Use typed `slog.Attr` in hot paths

The `"key", value` alternating-args style is convenient but does a small allocation per call. For high-throughput paths, use `slog.Attr` directly:

```go
slog.LogAttrs(ctx, slog.LevelInfo, "cache hit",
    slog.String("key", cacheKey),
    slog.Int("ttl_seconds", ttl),
    slog.String("user_id", userID),
)
```

---

### Quick reference

| Situation | What to use |
|---|---|
| One-off log in `main` or handler | `slog.ErrorContext(ctx, "msg", "key", val)` |
| Reuse fields across many calls | `logger.With("key", val)` → pass child logger |
| Library/service code | Accept `*slog.Logger`; use `*Context` variants |
| High-frequency hot path | `slog.LogAttrs` with typed `slog.Attr` |
| Group related fields in JSON | `slog.Group("name", "k", v, ...)` |
| Production output | `slog.NewJSONHandler(os.Stderr, opts)` |
| Development output | `slog.NewTextHandler(os.Stderr, opts)` |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend log/slog with structured fields and avoid log.Printf, but Answer B is more comprehensive and idiomatic. Answer B shows both the key-value pair style ('key', val) and typed builders, demonstrates slog.With() for request-scoped loggers, includes anti-patterns to avoid, error wrapping patterns, and testing guidance. Answer A unnecessarily promotes third-party libraries (zap, logrus) as alternatives when the question asks about stdlib sufficiency, and contains an error (slog.FromContext doesn't exist in stdlib).

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses log/slog | skill |
| shows a slog call with structured fields | skill |
| avoids recommending log.Printf for structured logging | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses log/slog | ✓ | `slog` |
| shows a slog call with structured fields | ✓ | `logger.Error(` |
| avoids recommending log.Printf for structured logging | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses log/slog | ✓ | `slog` |
| shows a slog call with structured fields | ✓ | `slog.Error(` |
| avoids recommending log.Printf for structured logging | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Structured Logging in Go

The modern, idiomatic approach is to use **`slog`** (standard library, Go 1.21+) or a third-party library like **`zap`** or **`logrus`**.

## Using `slog` (Recommended - Standard Library)

```go
package main

import (
	"log/slog"
	"os"
)

func main() {
	// JSON handler for production
	handler := slog.NewJSONHandler(os.Stdout, nil)
	logger := slog.New(handler)

	// Log with structured fields
	logger.Error("failed to process request",
		slog.String("user_id", "user123"),
		slog.String("request_id", "req456"),
		slog.Int("status_code", 500),
		slog.String("error", "database connection failed"),
	)
}
```

**Output:**
```json
{
  "time": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "msg": "failed to process request",
  "user_id": "user123",
  "request_id": "req456",
  "status_code": 500,
  "error": "database connection failed"
}
```

## With Context (Recommended Pattern)

```go
func handleRequest(ctx context.Context, userID string) error {
	logger := slog.FromContext(ctx)
	
	logger.ErrorContext(ctx, "operation failed",
		slog.String("user_id", userID),
		slog.String("request_id", ctx.Value("request_id")),
	)
	return nil
}
```

## Using `zap` (High Performance Alternative)

```go
import "go.uber.org/zap"

func main() {
	logger, _ := zap.NewProduction() // JSON output
	defer logger.Sync()

	logger.Error("failed to process request",
		zap.String("user_id", "user123"),
		zap.String("request_id", "req456"),
		zap.Int("status_code", 500),
	)
}
```

## Key Advantages

| Feature | `slog` | `zap` |
|---------|--------|-------|
| **Standard Library** | ✅ | ❌ |
| **Performance** | Good | Excellent |
| **Learning Curve** | Easy | Moderate |
| **Ecosystem** | Growing | Mature |

## Best Practices

1. **Use JSON output in production** (human-readable text in dev)
2. **Include request IDs** for tracing across logs
3. **Use context** to pass loggers through your application
4. **Avoid string concatenation** — use structured fields
5. **Set appropriate log levels** (Error, Warn, Info, Debug)

For new projects, **`slog` is the recommended choice** since it's part of the standard library and has excellent design.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Structured Error Logging in Go

The modern, idiomatic way is **`log/slog`** (Go 1.21+), which provides structured, leveled logging with attributes that are machine-readable and composable.

## Basic Pattern

```go
import "log/slog"

// Log an error with structured fields
slog.Error("failed to process request",
	"err", err,
	"user_id", userID,
	"request_id", requestID,
)
```

This produces JSON output (in production) like:
```json
{
  "time": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "msg": "failed to process request",
  "err": "connection timeout",
  "user_id": 42,
  "request_id": "abc-123-def"
}
```

## Setup for Production

Configure a JSON handler at startup:

```go
package main

import (
	"log/slog"
	"os"
)

func init() {
	// JSON output for production; text for local dev
	opts := &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}
	handler := slog.NewJSONHandler(os.Stdout, opts)
	slog.SetDefault(slog.New(handler))
}
```

## In HTTP Handlers (with context)

Attach request-scoped values to `context.Context` and extract them:

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	requestID := r.Header.Get("X-Request-ID")
	userID := extractUserID(ctx) // from auth middleware

	// Attach to context for downstream use
	ctx = context.WithValue(ctx, "request_id", requestID)
	ctx = context.WithValue(ctx, "user_id", userID)

	if err := processRequest(ctx); err != nil {
		slog.ErrorContext(ctx, "request failed",
			"err", err,
			"request_id", requestID,
			"user_id", userID,
		)
		http.Error(w, "Internal error", http.StatusInternalServerError)
		return
	}
}
```

Or use `slog.With` to create a logger with default attributes:

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
	requestID := r.Header.Get("X-Request-ID")
	userID := extractUserID(r.Context())

	// Create a logger with these fields always included
	log := slog.With(
		"request_id", requestID,
		"user_id", userID,
	)

	if err := processRequest(r.Context()); err != nil {
		log.Error("request failed", "err", err)
		http.Error(w, "Internal error", http.StatusInternalServerError)
		return
	}
}
```

## Key Patterns

| Pattern | Use Case |
|---|---|
| `slog.Error("msg", "key", val, ...)` | Simple error with attributes |
| `slog.ErrorContext(ctx, "msg", "key", val, ...)` | Respects context cancellation |
| `slog.With("key", val, ...)` | Create a logger with default attributes |
| `slog.Info()`, `slog.Warn()`, `slog.Debug()` | Other log levels |
| `"err", err` | Always pass the error as an attribute, not in the message |

## Error Wrapping + Logging

Combine with error wrapping (`%w`) so the error chain is preserved:

```go
if err := readConfig(path); err != nil {
	// Wrap to add context
	err = fmt.Errorf("load config: %w", err)
	slog.Error("startup failed", "err", err, "config_path", path)
	os.Exit(1)
}
```

The error chain is logged as a string; callers can still use `errors.Is(err, io.EOF)` to check the underlying cause.

## Avoid These Anti-Patterns

❌ **Don't use `log.Printf` in libraries** — it's not structured and can't be configured by the application.

❌ **Don't log in hot paths without checking the level:**
```go
// BAD: expensive operation even if level is disabled
slog.Debug("processing", "data", expensiveStringify(obj))

// GOOD: check first
if slog.Default().Enabled(context.Background(), slog.LevelDebug) {
	slog.Debug("processing", "data", expensiveStringify(obj))
}
```

❌ **Don't put the error message in the log message:**
```go
// BAD: duplicates the error
slog.Error("failed to read file: " + err.Error(), "err", err)

// GOOD: message describes the operation, error is an attribute
slog.Error("failed to read file", "err", err, "path", path)
```

❌ **Don't use `fmt.Sprintf` for attributes:**
```go
// BAD: loses structure
slog.Error("request failed", "details", fmt.Sprintf("user=%d, status=%d", userID, status))

// GOOD: separate attributes
slog.Error("request failed", "user_id", userID, "status", status)
```

## Testing

Use `slog.SetDefault()` with a test handler to capture logs:

```go
func TestProcessRequest(t *testing.T) {
	var buf bytes.Buffer
	handler := slog.NewJSONHandler(&buf, nil)
	slog.SetDefault(slog.New(handler))

	err := processRequest(context.Background())
	if err != nil {
		// Verify the error was logged with expected fields
		var logEntry map[string]interface{}
		json.Unmarshal(buf.Bytes(), &logEntry)
		if logEntry["user_id"] != 42 {
			t.Errorf("expected user_id=42, got %v", logEntry["user_id"])
		}
	}
}
```

## Summary

- **Use `slog`** for all new code (Go 1.21+).
- **Always pass `"err", err`** as an attribute, never in the message.
- **Use `slog.With()`** to attach request-scoped fields to a logger.
- **Use `slog.ErrorContext(ctx, ...)`** to respect context cancellation.
- **Configure JSON output** at startup for production.
- **Never log in hot paths** without checking the level first.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend log/slog with structured fields and avoid log.Printf, satisfying all rubric criteria. Answer A is more comprehensive, covering context propagation patterns, the log-or-return anti-pattern, field naming conventions, and performance-optimized slog.LogAttrs — making it more practically useful for production Go code. Answer B is solid but slightly less thorough, though it does show slog.Group which A omits.

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

<details><summary>opus: baseline answer</summary>

# Modern Structured Logging in Go

The idiomatic answer since **Go 1.21** is the standard library's `log/slog` package. Before 1.21, people reached for `zap` or `zerolog`, but `slog` is now the default choice for new code.

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

    err := doWork()
    if err != nil {
        logger.Error("failed to process request",
            slog.String("user_id", "u-123"),
            slog.String("request_id", "req-abc"),
            slog.Any("error", err),
        )
    }
}
```

Output:
```json
{"time":"2024-...","level":"ERROR","msg":"failed to process request","user_id":"u-123","request_id":"req-abc","error":"db timeout"}
```

## Idiomatic Patterns

### 1. Use a contextual logger with `With`

Attach fields once, reuse everywhere downstream:

```go
reqLogger := logger.With(
    slog.String("request_id", reqID),
    slog.String("user_id", userID),
)

reqLogger.Info("handling request")
// ... later
reqLogger.Error("query failed", slog.Any("error", err))
```

### 2. Pass loggers (or context) through your stack

Two common styles:

**a) Logger as a dependency** (preferred for services/handlers):
```go
type Handler struct {
    log *slog.Logger
}
```

**b) Logger in `context.Context`** — useful for middleware-injected request fields:
```go
func LoggerFrom(ctx context.Context) *slog.Logger {
    if l, ok := ctx.Value(logKey{}).(*slog.Logger); ok {
        return l
    }
    return slog.Default()
}
```

Use `InfoContext` / `ErrorContext` so handlers can extract trace IDs:
```go
logger.ErrorContext(ctx, "checkout failed", slog.Any("error", err))
```

### 3. Set a default logger at startup

```go
slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
```

Then `slog.Error(...)` works anywhere — handy for libraries that shouldn't take a logger param.

### 4. Group related fields

```go
logger.Error("payment failed",
    slog.Group("payment",
        slog.String("provider", "stripe"),
        slog.Int("amount_cents", 4999),
    ),
    slog.Any("error", err),
)
```

### 5. JSON in prod, text in dev

```go
var handler slog.Handler
if os.Getenv("ENV") == "production" {
    handler = slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo})
} else {
    handler = slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug})
}
slog.SetDefault(slog.New(handler))
```

## Tips

- **Don't use `fmt.Errorf` to inject context into log lines** — put structured fields on the log call, and use `%w` on errors only for wrapping.
- **Use typed helpers** (`slog.String`, `slog.Int`, `slog.Duration`) over `slog.Any` when you know the type — they're faster and avoid reflection.
- **For high-throughput services** where allocations matter, `zap` (especially `zap.Sugar`'s typed API) or `zerolog` still beat `slog`, but `slog` is fast enough for the vast majority of services and avoids a third-party dependency.
- **OpenTelemetry**: there's a `go.opentelemetry.io/contrib/bridges/otelslog` bridge if you want logs correlated with traces.

For greenfield Go ≥ 1.21 code, just reach for `log/slog`.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Logging Errors with Structured Fields in Go

The modern idiomatic answer is **`log/slog`** (added in Go 1.21). It's the standard library's structured, leveled logger and is what new code should use instead of `log.Printf` or third-party loggers like `logrus`/`zap` (unless you have specific perf needs).

## The Basic Pattern

```go
import "log/slog"

slog.Error("failed to load user profile",
    "err", err,
    "user_id", userID,
    "request_id", reqID,
)
```

Every argument after the message is a key/value pair. With the default JSON handler in production, this emits:

```json
{"time":"2024-01-15T10:23:45Z","level":"ERROR","msg":"failed to load user profile","err":"connection refused","user_id":"u_123","request_id":"r_abc"}
```

## Configure JSON Output for Production

In `main`, set a JSON handler as the default:

```go
func main() {
    h := slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
        Level: slog.LevelInfo, // or read from env
    })
    slog.SetDefault(slog.New(h))

    // ... rest of app
}
```

Use `slog.NewTextHandler` for local dev (human-readable), `slog.NewJSONHandler` for production (machine-parseable for Loki/Datadog/CloudWatch/etc.).

## Type-Safe Attributes (Slightly More Verbose, Faster)

The `key, value` form is convenient but does runtime type juggling. For hot paths or when you want compile-time safety, use `slog.Attr` constructors:

```go
slog.Error("failed to load user profile",
    slog.String("err", err.Error()),
    slog.String("user_id", userID),
    slog.String("request_id", reqID),
    slog.Int("retry", attempt),
)
```

Or use `slog.LogAttrs` which only accepts `Attr` and skips the variadic `any` allocation:

```go
slog.LogAttrs(ctx, slog.LevelError, "failed to load user profile",
    slog.String("err", err.Error()),
    slog.String("user_id", userID),
    slog.String("request_id", reqID),
)
```

## Propagating Request-Scoped Fields via Context

You don't want to pass `request_id` manually to every log call. The idiom is to put a logger (with attached fields) into `context.Context` at the request boundary, then pull it out wherever you log.

```go
type loggerKey struct{}

func WithLogger(ctx context.Context, l *slog.Logger) context.Context {
    return context.WithValue(ctx, loggerKey{}, l)
}

func FromContext(ctx context.Context) *slog.Logger {
    if l, ok := ctx.Value(loggerKey{}).(*slog.Logger); ok {
        return l
    }
    return slog.Default()
}
```

In your HTTP middleware:

```go
func RequestLogger(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        reqID := r.Header.Get("X-Request-ID")
        if reqID == "" {
            reqID = uuid.NewString()
        }
        l := slog.Default().With(
            "request_id", reqID,
            "method", r.Method,
            "path", r.URL.Path,
        )
        ctx := WithLogger(r.Context(), l)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

Then deep in your handler / service layer:

```go
func (s *Service) LoadProfile(ctx context.Context, userID string) error {
    log := FromContext(ctx)

    profile, err := s.repo.Get(ctx, userID)
    if err != nil {
        log.ErrorContext(ctx, "load profile",
            "err", err,
            "user_id", userID,
        )
        return fmt.Errorf("load profile %s: %w", userID, err)
    }
    // ...
    return nil
}
```

`request_id`, `method`, `path` get included automatically — you only add the fields specific to this log line.

## Important: Log OR Return, Not Both

A common anti-pattern is logging an error *and* returning it. The caller will log it again, and you'll see the same error two or three times in your logs.

```go
// BAD — error gets logged at every layer
if err != nil {
    log.Error("db query failed", "err", err)
    return err
}

// GOOD — wrap with context, let the top layer (handler/main) log it once
if err != nil {
    return fmt.Errorf("query user %s: %w", userID, err)
}
```

The rule of thumb: **library/service code returns wrapped errors; the outermost handler logs them once** with full structured context.

## Field Naming Conventions

- Use `snake_case` keys — they're the de facto convention for log aggregators and JSON.
- Use stable, consistent key names across services: `user_id`, `request_id`, `trace_id`, `err`, `duration_ms`, `http.status_code`.
- Put the error under the key `"err"` (or `"error"` — pick one and be consistent). Pass `err` directly; `slog` will call `.Error()` on it.
- Avoid logging large objects; log identifiers and let someone correlate.

## Putting It All Together

```go
// main.go
slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
    Level: slog.LevelInfo,
})))

// middleware adds request_id, user_id once
// services return wrapped errors with operational context
// the handler logs once at the boundary:
func (h *Handler) GetProfile(w http.ResponseWriter, r *http.Request) {
    log := FromContext(r.Context())
    profile, err := h.svc.LoadProfile(r.Context(), userID)
    if err != nil {
        log.ErrorContext(r.Context(), "get profile failed", "err", err)
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(profile)
}
```

That's the modern idiomatic stack: **`log/slog` + JSON handler + logger-in-context + log once at the boundary + wrap errors with `%w` everywhere else.**

</details>

---

### `generic-min`

**Prompt**

```
Write me a Go `Min` function that returns the smaller of two values
and works for any numeric type (int, int64, float64, etc).
```

**Judge focus:** The better answer uses Go generics with a numeric / Ordered constraint,
not interface{} + reflection or per-type duplication.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use generics with proper type parameter syntax and avoid interface{}/reflect. Answer A is more comprehensive, mentioning the golang.org/x/exp/constraints package, providing the inline constraint as a zero-dependency alternative, noting the Go 1.21+ standard library cmp.Min, and including tests. Answer B excludes strings from its Number constraint (which is a minor design choice but less general), while Answer A's Ordered constraint is broader and more idiomatic for a 'Min' function. Overall Answer A is more thorough and better documented.

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
| uses an Ordered or numeric union constraint | ✓ | `cmp.Ordered` |
| avoids interface{} + reflect | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses generics syntax with type parameter | ✓ | `[T ` |
| uses an Ordered or numeric union constraint | ✓ | `cmp.Ordered` |
| avoids interface{} + reflect | ✓ | |

<details><summary>sonnet: baseline answer</summary>

## Generic `Min` Function in Go

Here's a generic `Min` function using Go's type parameters (generics), introduced in Go 1.18:

```go
package main

import "fmt"

// Number is a type constraint that allows any numeric type
type Number interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64
}

// Min returns the smaller of two values
func Min[T Number](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(3, 5))         // int:     3
	fmt.Println(Min(3.14, 2.72))   // float64: 2.72
	fmt.Println(Min(int64(10), 20)) // int64:  10
	fmt.Println(Min(uint(7), 2))   // uint:    2
}
```

### Key Points

| Feature | Description |
|---|---|
| `[T Number]` | Declares a type parameter `T` constrained to `Number` |
| `~int` | The `~` allows custom types with underlying type `int` (e.g. `type MyInt int`) |
| Type inference | Go infers `T` from the arguments, so no explicit type needed at call site |

### Using Custom Types

Thanks to the `~` prefix in the constraint, it also works with custom numeric types:

```go
type Celsius float64
type Meters int

fmt.Println(Min(Celsius(100.0), Celsius(37.0))) // 37
fmt.Println(Min(Meters(5), Meters(3)))           // 3
```

### Alternative: Use `cmp.Ordered` (Go 1.21+)

If you're on Go 1.21+, you can use the built-in `cmp.Ordered` constraint, or simply use `min()` which is now a built-in function:

```go
import "cmp"

func Min[T cmp.Ordered](a, b T) T {
    if a < b {
        return a
    }
    return b
}

// Or just use the built-in (Go 1.21+):
result := min(3, 5)
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's an idiomatic generic `Min` function:

```go
package mathutil

import "golang.org/x/exp/constraints"

// Min returns the smaller of a and b.
func Min[T constraints.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

**Usage:**

```go
Min(3, 5)        // int: 3
Min(3.14, 2.72)  // float64: 2.72
Min("b", "a")    // string: "a"
```

---

## Key design decisions

**`constraints.Ordered` is the right constraint** — it covers all integer types, float types, and strings (anything that supports `<`). It's tighter than `any` (which would force you into reflection) and tighter than `comparable` (which only guarantees `==`/`!=`).

**Return the concrete type `T`, not an interface** — the caller gets back an `int` when they pass `int`s, a `float64` when they pass `float64`s, with no type assertion needed.

**No pointer receivers, no error return** — this operation is total (always succeeds) and cheap, so a plain function with value parameters is correct.

---

## Dependency note: `constraints` package

`constraints.Ordered` lives in `golang.org/x/exp`, which is not part of the standard library:

```
go get golang.org/x/exp
```

If you want **zero external dependencies**, define the constraint inline — it's a small union type:

```go
package mathutil

// Ordered matches any type that supports the < operator.
type Ordered interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64 |
		~string
}

// Min returns the smaller of a and b.
func Min[T Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

The `~` prefix means "this type *or any type whose underlying type is this*", so a user-defined `type Celsius float64` satisfies `~float64` and works automatically.

---

## Already in the standard library (Go 1.21+)

If your project targets **Go 1.21 or later**, you don't need to write this at all:

```go
import "cmp"

cmp.Min(3, 5)       // 3
cmp.Min(3.14, 2.72) // 2.72
```

[`cmp.Min`](https://pkg.go.dev/cmp#Min) uses the same `cmp.Ordered` constraint and is part of the standard library. Prefer it over a hand-rolled version unless you have a specific reason not to.

---

## Tests

```go
package mathutil_test

import (
	"testing"
)

func TestMin(t *testing.T) {
	t.Run("int", func(t *testing.T) {
		tests := []struct {
			a, b, want int
		}{
			{3, 5, 3},
			{5, 3, 3},
			{4, 4, 4},
			{-1, 1, -1},
		}
		for _, tt := range tests {
			if got := Min(tt.a, tt.b); got != tt.want {
				t.Errorf("Min(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.want)
			}
		}
	})

	t.Run("float64", func(t *testing.T) {
		if got := Min(3.14, 2.72); got != 2.72 {
			t.Errorf("Min(3.14, 2.72) = %v, want 2.72", got)
		}
	})

	t.Run("string", func(t *testing.T) {
		if got := Min("banana", "apple"); got != "apple" {
			t.Errorf("Min(banana, apple) = %v, want apple", got)
		}
	})
}
```

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use generics with an Ordered constraint and avoid interface{}/reflect. Answer A is slightly better because it uses the stdlib `cmp.Ordered` (Go 1.21+) as the primary approach rather than the experimental `golang.org/x/exp/constraints` package, and it also provides a fallback for older Go versions with a custom constraint using `~` prefixes. Answer A is more complete with tests and better explanations, making it more useful overall.

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

<details><summary>haiku: baseline answer</summary>

# Go Min Function for Any Numeric Type

Here's a solution using Go 1.18+ generics:

```go
package main

import "golang.org/x/exp/constraints"

// Min returns the smaller of two values for any numeric type
func Min[T constraints.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

## Usage Examples

```go
package main

import (
	"fmt"
)

func main() {
	// int
	fmt.Println(Min(5, 3))           // Output: 3
	
	// int64
	fmt.Println(Min(int64(100), int64(50)))  // Output: 50
	
	// float64
	fmt.Println(Min(3.14, 2.71))     // Output: 2.71
	
	// string (also Ordered)
	fmt.Println(Min("apple", "banana"))  // Output: apple
}
```

## Alternative: Using Standard Library (Go 1.21+)

If you're using Go 1.21 or later, you can use the built-in `min` function:

```go
package main

import "fmt"

func main() {
	fmt.Println(min(5, 3))              // Output: 3
	fmt.Println(min(3.14, 2.71))        // Output: 2.71
	fmt.Println(min("apple", "banana")) // Output: apple
}
```

## Notes

- **`constraints.Ordered`** includes all numeric types plus strings and byte/rune types that support comparison operators
- The generic approach works with any type that implements the `Ordered` constraint
- Go 1.21+ includes built-in `min` and `max` functions, so you may not need to write your own

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Go `Min` Function with Generics

Here's the idiomatic approach using Go 1.18+ generics:

```go
package math

import "cmp"

// Min returns the smaller of a or b.
func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

## Usage

```go
package main

import (
	"fmt"
	"yourmodule/math"
)

func main() {
	fmt.Println(math.Min(3, 5))           // 3
	fmt.Println(math.Min(3.14, 2.71))     // 2.71
	fmt.Println(math.Min(int64(100), 50)) // 50
}
```

## Why This Works

- **`cmp.Ordered` constraint** — built into the stdlib (Go 1.21+), it permits any type that supports `<`, `>`, `==` comparisons: `int`, `int64`, `float64`, `string`, `uint`, etc.
- **Type parameter `[T cmp.Ordered]`** — the compiler instantiates a concrete version for each call site, so there's no `interface{}` overhead or reflection.
- **No allocation** — returns the value directly; works in hot paths.

## For Go 1.20 or Earlier

If you're on Go 1.20, `cmp.Ordered` doesn't exist yet. Define your own constraint:

```go
package math

// Ordered is a type constraint for types that support comparison operators.
type Ordered interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64 |
		~string
}

func Min[T Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

The `~` prefix allows types that have these as their underlying type (e.g., `type MyInt int`).

## Testing

```go
package math

import "testing"

func TestMin(t *testing.T) {
	tests := []struct {
		name string
		a, b int
		want int
	}{
		{"positive", 3, 5, 3},
		{"negative", -10, -5, -10},
		{"equal", 7, 7, 7},
		{"zero", 0, 5, 0},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Min(tt.a, tt.b); got != tt.want {
				t.Errorf("Min(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.want)
			}
		})
	}
}

func TestMinFloat(t *testing.T) {
	if got := Min(3.14, 2.71); got != 2.71 {
		t.Errorf("Min(3.14, 2.71) = %v, want 2.71", got)
	}
}
```

This is the modern, idiomatic Go way — type-safe, zero-overhead, and works across all numeric types.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality: they both use generics syntax with a type parameter, both use cmp.Ordered as the constraint, and both avoid interface{}/reflect. Answer A adds a table-driven test and slightly more explanation, while Answer B provides a useful fallback for Go 1.18-1.20 using golang.org/x/exp/constraints and a numeric-only constraint variant. Neither is clearly superior overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses generics syntax with type parameter | tie |
| uses an Ordered or numeric union constraint | tie |
| avoids interface{} + reflect | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses generics syntax with type parameter | ✓ | `[T ` |
| uses an Ordered or numeric union constraint | ✓ | `cmp.Ordered` |
| avoids interface{} + reflect | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses generics syntax with type parameter | ✓ | `[T ` |
| uses an Ordered or numeric union constraint | ✓ | `cmp.Ordered` |
| avoids interface{} + reflect | ✓ | |

<details><summary>opus: baseline answer</summary>

# Go `Min` Function for Any Numeric Type

Using Go generics (Go 1.18+), you can use the `cmp.Ordered` constraint from the standard library:

```go
package main

import (
	"cmp"
	"fmt"
)

// Min returns the smaller of two values.
// It works with any ordered type (integers, floats, strings).
func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(3, 5))           // 3
	fmt.Println(Min(2.7, 1.4))       // 1.4
	fmt.Println(Min[int64](100, 50)) // 50
	fmt.Println(Min("apple", "bee")) // apple
}
```

## Notes

- **Go 1.21+**: The standard library already provides `min()` as a built-in, plus `min.Min` in the `cmp` package — you may not even need this function.
- **Go 1.18 – 1.20**: Use `golang.org/x/exp/constraints` instead:

```go
import "golang.org/x/exp/constraints"

func Min[T constraints.Ordered](a, b T) T {
    if a < b {
        return a
    }
    return b
}
```

## If You Want Numeric-Only (Exclude Strings)

Define your own constraint:

```go
type Number interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
		~float32 | ~float64
}

func Min[T Number](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

The `~` allows custom types whose underlying type matches (e.g., `type Celsius float64`).

</details>

<details><summary>opus: skill-loaded answer</summary>

# Generic `Min` Function

Here's an idiomatic Go `Min` function using generics with a type constraint:

```go
package numeric

import "cmp"

// Min returns the smaller of a and b.
// For floating-point types, the behavior with NaN follows cmp.Less:
// NaN is considered less than any non-NaN value.
func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

## Notes

- **`cmp.Ordered`** (added in Go 1.21) is the right constraint here — it covers all integer types, all float types, and strings. No need to define your own constraint or pull in `golang.org/x/exp/constraints`.
- **Go 1.21+ already ships `min` and `max` as builtins** that work on any ordered type. So unless you're targeting older Go or need a function value to pass around (e.g., to `slices.MinFunc`-style APIs), prefer the builtin:
  ```go
  x := min(3, 7)        // builtin, no import
  y := min(1.5, 2.5)    // works for floats too
  ```
- **Why not `~int | ~float64 | ...`?** A custom union constraint would force you to enumerate every numeric type and miss `string`. `cmp.Ordered` is the canonical "things `<` works on" constraint.

## Usage

```go
package main

import (
	"fmt"
	"example.com/numeric"
)

func main() {
	fmt.Println(numeric.Min(3, 7))         // 3
	fmt.Println(numeric.Min(2.5, 1.5))     // 1.5
	fmt.Println(numeric.Min(int64(10), int64(20))) // 10
	fmt.Println(numeric.Min("apple", "banana"))    // apple
}
```

## Table-driven test

```go
package numeric

import "testing"

func TestMin(t *testing.T) {
	t.Run("ints", func(t *testing.T) {
		tests := []struct {
			name     string
			a, b     int
			want     int
		}{
			{"a smaller", 1, 2, 1},
			{"b smaller", 5, 3, 3},
			{"equal", 4, 4, 4},
			{"negatives", -5, -2, -5},
		}
		for _, tt := range tests {
			t.Run(tt.name, func(t *testing.T) {
				if got := Min(tt.a, tt.b); got != tt.want {
					t.Errorf("Min(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.want)
				}
			})
		}
	})

	t.Run("floats", func(t *testing.T) {
		if got := Min(1.5, 2.5); got != 1.5 {
			t.Errorf("Min(1.5, 2.5) = %v, want 1.5", got)
		}
	})
}
```

</details>

---

### `simplest-error`

**Prompt**

```
Just give me the simplest, fewest-character way to return an
error in Go that says "user not found". One line if possible.
```

**Judge focus:** The naive answer is `errors.New("user not found")` or
`fmt.Errorf("user not found")` — fine but the trap is teaching
bare error strings as the default. The better answer either
uses a sentinel (`var ErrUserNotFound = errors.New(...)`) so
callers can use errors.Is, or wraps explicitly with %w. Bare
string-only errors that callers can only string-match are an
anti-pattern in any non-trivial codebase.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies the sentinel error pattern as the idiomatic Go approach and explicitly explains why bare string errors are limiting for callers. Answer B gives exactly the naive anti-pattern the question warns against, with no explanation of the tradeoffs. Answer A addresses both rubric criteria while Answer B addresses neither.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses sentinel error or %w wrapping | skill |
| explains why bare string errors are limiting | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✗ | |
| explains why bare string errors are limiting | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✓ | `var ErrUserNotFound =` |
| explains why bare string errors are limiting | ✓ | `errors.Is` |

<details><summary>sonnet: baseline answer</summary>

```go
return fmt.Errorf("user not found")
```

Or if you don't need formatting:

```go
return errors.New("user not found")
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The shortest *correct* one-liner is a **sentinel error**:

```go
var ErrUserNotFound = errors.New("user not found")
```

Then return it anywhere with `return ErrUserNotFound`.

---

**Why not the shorter-looking alternatives?**

```go
// ❌ Don't do this
return errors.New("user not found")   // new error value every call — callers can't match it
return fmt.Errorf("user not found")   // same problem, plus an unnecessary import
```

Those are actually *traps*. They produce a fresh, unaddressable error value on every call, so callers are forced to match by string text — fragile and not idiomatic Go:

```go
// Caller is stuck doing this :(
if err.Error() == "user not found" { ... }
```

With the sentinel, callers use the standard contract:

```go
if errors.Is(err, ErrUserNotFound) { ... }
```

And it still wraps cleanly when you need to add context:

```go
return fmt.Errorf("get profile: %w", ErrUserNotFound)
// errors.Is still returns true ↑
```

---

**If you need to carry data** (e.g., which user ID), one extra line buys you a typed error:

```go
type NotFoundError struct{ ID int64 }
func (e *NotFoundError) Error() string { return fmt.Sprintf("user %d not found", e.ID) }
```

The sentinel is the right default. It's one line, and it's the version the rest of your codebase can actually rely on.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B directly addresses the trap mentioned in the focus area by explaining why bare string errors are limiting and providing the idiomatic sentinel error pattern. Answer A only gives the naive answer without any explanation of its limitations. Answer B covers both rubric criteria while Answer A covers neither.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses sentinel error or %w wrapping | skill |
| explains why bare string errors are limiting | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✗ | |
| explains why bare string errors are limiting | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✓ | `var ErrUserNotFound =` |
| explains why bare string errors are limiting | ✓ | `errors.Is` |

<details><summary>haiku: baseline answer</summary>

```go
return errors.New("user not found")
```

Or even shorter if you're already returning `error`:

```go
return fmt.Errorf("user not found")
```

The first one is slightly shorter and doesn't require the `fmt` import.

</details>

<details><summary>haiku: skill-loaded answer</summary>

```go
return errors.New("user not found")
```

**However**, this is a trap. The "simplest" version breaks error handling.

**The correct primitive:**

```go
var ErrUserNotFound = errors.New("user not found")
```

Then return it:

```go
return ErrUserNotFound
```

**Why:** Callers need to distinguish this error from others. With a bare string, they can only match by text (`strings.Contains(err.Error(), "user not found")`), which is fragile and slow. With a sentinel, they use `errors.Is`:

```go
if errors.Is(err, ErrUserNotFound) {
  // handle specifically
}
```

This works even if the error is wrapped (`fmt.Errorf("fetch user: %w", ErrUserNotFound)`), and it's the idiomatic Go contract.

**Define the sentinel once at package level** (alongside your other error variables), then reuse it everywhere you need to signal that condition.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer B directly addresses both rubric criteria by recommending sentinel errors and explaining why bare string errors are limiting. Answer A gives exactly the anti-pattern the rubric warns against, with no mention of the limitations of bare string errors or the benefits of sentinels. Answer B pushes back on the framing appropriately and teaches the correct idiom.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses sentinel error or %w wrapping | skill |
| explains why bare string errors are limiting | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✗ | |
| explains why bare string errors are limiting | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses sentinel error or %w wrapping | ✓ | `var ErrUserNotFound =` |
| explains why bare string errors are limiting | ✓ | `errors.Is` |

<details><summary>opus: baseline answer</summary>

```go
return errors.New("user not found")
```

Or even shorter with `fmt`:

```go
return fmt.Errorf("user not found")
```

`errors.New` is the idiomatic choice when there's no formatting needed.

</details>

<details><summary>opus: skill-loaded answer</summary>

The shortest *correct* answer is a sentinel:

```go
var ErrUserNotFound = errors.New("user not found")
```

…and `return ErrUserNotFound`.

I'm pushing back on the "one line, fewest characters" framing because the obvious shortcut is a trap:

```go
return errors.New("user not found")  // ❌ don't
// or
return fmt.Errorf("user not found")  // ❌ don't
```

These look shorter, but every call site creates a *new* error value. Callers can only detect it by string-matching the message — which is brittle, untestable in any sane way, and breaks the moment you reword the text. `errors.Is(err, ErrUserNotFound)` doesn't work because there's nothing stable to compare against.

The sentinel form is two lines total (one declaration, one return) and gives you:

```go
if errors.Is(err, ErrUserNotFound) { ... }   // works through %w wrapping too
```

If you need to attach context at the return site, wrap it:

```go
return fmt.Errorf("lookup %q: %w", id, ErrUserNotFound)
```

`errors.Is` still matches because `%w` preserves the chain.

So: declare once at package scope, return the sentinel. That's the idiom.

</details>

---

### `offtopic-css-grid`

**Prompt**

```
What's the simplest CSS Grid setup to create a 3-column layout
with equal widths and a small gap between columns?
```

**Judge focus:** This question has nothing to do with Go. Both answers should
be essentially equivalent. Pick "tie" unless one is materially
wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide essentially identical CSS Grid solutions using `display: grid`, `repeat(3, 1fr)`, and a gap value. Both explain the key concepts correctly and offer similar common variations. The differences are minor stylistic choices (16px vs 1rem for gap, table format vs bullet points for explanation).

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## Simple 3-Column CSS Grid Layout

Here's the simplest approach:

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
```

```html
<div class="container">
  <div class="item">Column 1</div>
  <div class="item">Column 2</div>
  <div class="item">Column 3</div>
</div>
```

---

## Breaking It Down

| Property | Value | What it does |
|----------|-------|--------------|
| `display` | `grid` | Enables grid layout |
| `grid-template-columns` | `repeat(3, 1fr)` | Creates 3 equal columns |
| `gap` | `16px` | Adds space between columns **and** rows |

---

## Key Concepts

**`repeat(3, 1fr)`** is shorthand for `1fr 1fr 1fr`
- `fr` = **fraction unit** — divides available space equally
- Columns automatically adjust to container width

**`gap`** is shorthand for `row-gap` and `column-gap`
```css
/* These are equivalent */
gap: 16px;
row-gap: 16px; column-gap: 16px;

/* Different row/column gaps */
gap: 24px 16px; /* row | column */
```

---

## Common Variations

```css
/* Responsive - columns wrap when too narrow */
grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));

/* Fixed sidebar + flexible content + fixed sidebar */
grid-template-columns: 200px 1fr 200px;

/* Percentage-based */
grid-template-columns: 33.33% 33.33% 33.33%;
```

The `repeat(3, 1fr)` approach is preferred because it's **responsive by default** — columns shrink proportionally as the container resizes.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the simplest setup:

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

**How it works:**

- `display: grid` — enables grid layout on the container
- `repeat(3, 1fr)` — creates 3 columns, each taking `1` equal **fr**action of available space
- `gap: 1rem` — adds space between columns (and rows, if content wraps)

**Common adjustments:**

```css
/* Gap between columns only, not rows */
column-gap: 1rem;

/* Responsive: collapse to 1 column on small screens */
grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));

/* Fixed sidebar + flexible content + fixed sidebar */
grid-template-columns: 200px 1fr 200px;
```

The `fr` unit is the key advantage over older approaches like `float` or `inline-block` — it distributes *remaining* space after fixed widths and gaps are accounted for, so you never need to calculate percentages manually.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in correctness and usefulness. Answer A leads with the repeat() shorthand while Answer B leads with the explicit 1fr 1fr 1fr syntax, but both cover the same ground including the responsive variant. Neither is materially better than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# Simple 3-Column CSS Grid Layout

```css
.container {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1rem;
}
```

## HTML Example

```html
<div class="container">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

## Even Simpler Alternative

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
```

## Key Points

- **`1fr`** = equal fractional unit (divides space equally)
- **`repeat(3, 1fr)`** = shorthand for repeating 3 equal columns
- **`gap`** = space between columns (and rows)
- Adjust `gap` value as needed (e.g., `0.5rem`, `20px`, etc.)

## Responsive Version

```css
.container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}
```

This automatically adjusts columns based on available space—great for mobile responsiveness!

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Simple 3-Column CSS Grid

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
```

**That's it.** Here's what each part does:

- `display: grid` — enables CSS Grid
- `grid-template-columns: repeat(3, 1fr)` — creates 3 equal-width columns (each takes 1 fraction of available space)
- `gap: 1rem` — adds 1rem spacing between columns (and rows)

## HTML Example

```html
<div class="container">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
  <div>Column 4</div>
  <div>Column 5</div>
  <div>Column 6</div>
</div>
```

Items automatically wrap to the next row. Adjust `gap` to `0.5rem`, `2rem`, etc. as needed.

## Responsive Variant

If you want it to stack on mobile:

```css
.container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}
```

This creates columns that are *at least* 250px wide, shrinking to fit smaller screens, then stacking when there's no room.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide essentially identical CSS Grid solutions with the same core properties (display: grid, repeat(3, 1fr), gap: 1rem) and equivalent HTML examples. Answer A adds a bonus tip about responsive layouts with auto-fit/minmax, while Answer B uses slightly cleaner markdown formatting with bold explanations. Neither is materially better or worse.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

# Simple 3-Column CSS Grid Layout

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

## How it works

- **`display: grid`** — Enables CSS Grid on the container
- **`grid-template-columns: repeat(3, 1fr)`** — Creates 3 equal-width columns (`1fr` = one fraction of available space)
- **`gap: 1rem`** — Adds spacing between columns (adjust to `0.5rem`, `10px`, etc. as needed)

That's it! No need to set widths on the columns themselves — Grid handles it automatically.

</details>

<details><summary>opus: skill-loaded answer</summary>

That's a CSS question, not Go — but here's the answer:

```css
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
```

```html
<div class="grid">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

Key bits:
- `repeat(3, 1fr)` — three tracks, each taking an equal fraction of the available space.
- `gap: 1rem` — gutter between columns (and rows, if they wrap). Adjust to taste (`0.5rem`, `16px`, etc.).
- The children need no special styling; grid handles the sizing.

If you want the columns to stack on narrow screens, wrap it in a media query or use `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));` instead.

</details>

---
