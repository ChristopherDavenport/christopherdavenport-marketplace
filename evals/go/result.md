# Eval report: `go`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **10**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.40** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 8/10 | 7 / 1 / 2 | 86% → 94% (+7%) |
| `haiku` | 10/10 | 9 / 0 / 1 | 81% → 94% (+13%) |
| `opus` ¹ | 8/10 | 7 / 0 / 3 | 86% → 97% (+11%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 8 | 6/8 | 8/8 | 6/8 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `error-wrapping` | skill_wins | ✗ ✗ baseline | ✓ ✓ skill | ✓ ✓ skill |
| `goroutine-lifetime` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `receiver-consistency` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `interface-placement` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `slog-structured` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `generic-min` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `context-timeout-cancellation` | skill_wins | ✗ = tie | ✓ ✓ skill | ✗ = tie |
| `table-driven-tests` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly use %w and explain errors.Is/errors.As traversal, but Answer A contains a notable bug: it shows the wrong fmt.Errorf call first ('fmt.Errorf("load config from %s: %w", err)' missing the path argument) before correcting it, which is confusing and unprofessional. Answer B is cleaner, correct from the start, includes a custom error type example demonstrating errors.As with Unwrap(), and provides a multi-layer wrapping example that better teaches the pattern without any errors.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses %w directive | baseline |
| mentions errors.Is or errors.As | baseline |
| uses fmt.Errorf for context | baseline |
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

<details><summary>sonnet: baseline answer</summary>

## Wrapping Errors with Context in Go

The idiomatic Go solution is to wrap the error with `fmt.Errorf` and the `%w` verb, which preserves the original error for programmatic inspection while adding context.

### The Problem

```go
// Bad: caller sees "open /etc/foo.yml: no such file or directory"
// No idea which subsystem, what the path means, or who asked for it
func loadConfig(path string) (*os.File, error) {
    return os.Open(path)
}
```

### The Fix

```go
func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("loading config: %w", err)
    }
    return f, nil
}
```

Now callers see: **`"loading config: open /etc/foo.yml: no such file or directory"`**

---

### Why `%w` and Not `%v`?

| Verb | Wraps for `errors.Is`/`errors.As`? | Use when |
|------|-------------------------------------|----------|
| `%w` | ✅ Yes | You want callers to inspect the underlying error |
| `%v` | ❌ No | You want to hide implementation details |

```go
f, err := loadConfig("/etc/foo.yml")
if err != nil {
    // This still works because %w preserves the chain
    if errors.Is(err, os.ErrNotExist) {
        // handle missing file specifically
    }
    log.Fatal(err)
}
```

---

### Add Relevant Context at Each Layer

Each layer should add what *it* knows — don't repeat what lower layers already say:

```go
// Low level: knows the path
func openConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("open config file: %w", err)
    }
    return f, nil
}

// Mid level: knows the subsystem
func initDatabase(cfgPath string) (*DB, error) {
    f, err := openConfig(cfgPath)
    if err != nil {
        return nil, fmt.Errorf("database init: %w", err)
    }
    // ...
}

// Top level: knows the user-facing operation
func Start(cfgPath string) error {
    db, err := initDatabase(cfgPath)
    if err != nil {
        return fmt.Errorf("server startup: %w", err)
    }
    // ...
}
```

This produces: **`"server startup: database init: open config file: open /etc/foo.yml: no such file or directory"`**

---

### When to Use a Custom Error Type Instead

If callers need structured data (not just a message), use `errors.As`:

```go
type ConfigError struct {
    Path string
    Err  error
}

func (e *ConfigError) Error() string {
    return fmt.Sprintf("config %q: %v", e.Path, e.Err)
}

// Unwrap lets errors.Is/As traverse the chain
func (e *ConfigError) Unwrap() error { return e.Err }

func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, &ConfigError{Path: path, Err: err}
    }
    return f, nil
}

// Caller can extract structured info:
var cfgErr *ConfigError
if errors.As(err, &cfgErr) {
    log.Printf("bad config path was: %s", cfgErr.Path)
}
```

---

### Key Rules

1. **Wrap at every layer boundary** — each layer adds what it uniquely knows
2. **Use `%w`** so the error chain stays inspectable
3. **Don't wrap if you're re-returning** the same error at the same level (avoid duplicate context)
4. **Message format**: lowercase, no punctuation at end, colon-separated — they're meant to be chained

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
        //                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^
        //                      operational context  |  %w preserves the chain
    }
    return f, nil
}
```

Wait — that's a typo in the format string. The correct call:

```go
return nil, fmt.Errorf("load config from %s: %w", path, err)
```

Now callers see:

```
load config from /etc/foo.yml: open /etc/foo.yml: no such file or directory
```

## Why `%w` and Not `%v`?

| Verb | Message | `errors.Is(err, fs.ErrNotExist)` |
|------|---------|----------------------------------|
| `%v` | ✅ has context | ❌ chain broken — callers can't inspect |
| `%w` | ✅ has context | ✅ chain intact |

`%w` calls `errors.Unwrap` under the hood, so the full chain stays navigable:

```go
cfg, err := loadConfig("/etc/foo.yml")
if errors.Is(err, fs.ErrNotExist) {
    // Still works even through the wrapping layer.
    log.Fatal("config file missing — run `myapp init` first")
}
```

## When NOT to Use `%w`

Use a plain `%v` (or a new sentinel error) when the underlying error is an **implementation detail you want to hide** — for example, a SQL driver error that callers should never match against directly:

```go
var ErrUserNotFound = errors.New("user not found")

func getUser(id int) (*User, error) {
    u, err := db.QueryRow(...)
    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrUserNotFound  // hide sql.ErrNoRows from callers
    }
    if err != nil {
        return nil, fmt.Errorf("query user %d: %w", id, err)  // wrap unexpected errors
    }
    return u, nil
}
```

## Wrapping Convention

The message fragment should read as a **lowercase phrase without a trailing period**, so the full chain reads naturally when errors are joined by `: `:

```
initialize app: load config from /etc/foo.yml: open /etc/foo.yml: no such file or directory
│               │                              └─ os error
│               └─ loadConfig wrapper
└─ caller's wrapper
```

Each layer adds one phrase describing *what it was trying to do*, not *what went wrong* — that's the innermost error's job.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use %w and mention errors.Is/errors.As, but Answer B is more focused and pedagogically stronger. B explicitly demonstrates errors.Is usage with os.ErrNotExist in a code example, provides a nuanced 'when to wrap vs replace' discussion, and shows layered wrapping across multiple functions. Answer A covers the same core points but is slightly less explicit about the errors.Is/errors.As traversal benefit in practice.

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
- Error chain preservation for debugging

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
var ErrConfigNotFound = errors.New("config file not found")

func loadConfig(path string) (*Config, error) {
	f, err := os.Open(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, ErrConfigNotFound
		}
		return nil, fmt.Errorf("read config: %w", err)
	}
	// ...
}
```

## Best Practices

1. **Add context at each layer** — each function wraps with its own perspective:
   ```go
   // In config package
   func Load(path string) (*Config, error) {
       f, err := os.Open(path)
       if err != nil {
           return nil, fmt.Errorf("open config: %w", err)
       }
       // ...
   }
   
   // In main
   cfg, err := config.Load("/etc/foo.yml")
   if err != nil {
       return fmt.Errorf("initialize app: %w", err)
   }
   ```
   
   The full chain becomes: `initialize app: open config: open /etc/foo.yml: no such file or directory`

2. **Never discard errors silently** — if you can't wrap, at least log:
   ```go
   // Only if you have a good reason to ignore it
   _ = f.Close() // error ignored; file was read-only
   ```

3. **Use typed errors for domain-specific failures** — when the caller needs to react differently:
   ```go
   type ConfigError struct {
       Path string
       Err  error
   }
   
   func (e *ConfigError) Error() string {
       return fmt.Sprintf("config %s: %v", e.Path, e.Err)
   }
   
   func (e *ConfigError) Unwrap() error { return e.Err }
   ```

See [errors.md](references/errors.md) for more on error handling patterns.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more thorough and pedagogically stronger. It explicitly explains why %w preserves the error chain for errors.Is/errors.As traversal with a concrete downstream example, uses %q for paths (better practice), and avoids the anti-pattern of redundant path inclusion that Answer B actually demonstrates in its first code example. Answer B introduces a minor anti-pattern by showing `fmt.Errorf("config: open %s: %w", path, err)` which produces the redundant 'open /etc/foo.yml: open /etc/foo.yml' message it then has to walk back, and its mention of multiple %w verbs with fmt.Errorf is actually incorrect (fmt.Errorf only supports one %w in standard Go).

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses %w directive | skill |
| mentions errors.Is or errors.As | skill |
| uses fmt.Errorf for context | tie |
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
| avoids %v wrapping anti-pattern | ✓ | |

<details><summary>opus: baseline answer</summary>

# Wrapping errors with context in Go

The idiomatic fix is to wrap the error with `fmt.Errorf` and the `%w` verb, which preserves the original error for inspection while adding context.

## The fix

```go
func loadConfig(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("config: open %s: %w", path, err)
    }
    return f, nil
}
```

Now the caller sees something like:

```
config: open /etc/foo.yml: open /etc/foo.yml: no such file or directory
```

The `os.Open` error already includes the path, so you may want to drop the redundant path from your message:

```go
return nil, fmt.Errorf("config: %w", err)
// => "config: open /etc/foo.yml: no such file or directory"
```

## Why `%w` and not `%v` or `%s`?

- `%w` *wraps* the error, so callers can still use `errors.Is` and `errors.As`:
  ```go
  if errors.Is(err, os.ErrNotExist) {
      // handle missing config specifically
  }
  ```
- `%v`/`%s` flatten it to a string, breaking those checks.

## A few conventions worth following

1. **Lowercase, no trailing punctuation.** Errors get composed, so `"config: open foo: ..."` reads better than `"Config: Open foo: ...."`.
2. **Add context, don't restate.** "failed to" / "error while" is noise — the fact that it's an error is implied.
3. **Wrap once per layer.** Each function adds its own bit of context (`config:`, `subsystem:`, etc.), forming a breadcrumb trail.
4. **Wrap only when you have something to add.** If you're just passing it through, return it unchanged.

## When you have multiple errors at one level

Since Go 1.20, `errors.Join` and `fmt.Errorf` with multiple `%w` verbs let you wrap several errors:

```go
return fmt.Errorf("config: %w (path=%s)", err, path)
// or
return errors.Join(err, otherErr)
```

For your specific case, the one-liner with `%w` and a subsystem prefix is exactly the right move.

</details>

<details><summary>opus: skill-loaded answer</summary>

# The fix: wrap with `%w` to add operational context

Your callers already get the OS-level message (`open /etc/foo.yml: no such file or directory` — that comes from `os.Open` itself), but they have no idea *which part of your program* asked for that file. Wrap the error with `fmt.Errorf` and the `%w` verb so you add context **without** breaking the error chain:

```go
package config

import (
    "fmt"
    "os"
)

func Load(path string) (*os.File, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("config: load %q: %w", path, err)
    }
    return f, nil
}
```

Now callers see:

```
config: load "/etc/foo.yml": open /etc/foo.yml: no such file or directory
```

The `config:` prefix tells you the subsystem; the rest of the chain is preserved verbatim.

## Why `%w` and not `%v` or `%s`

| Verb | Behavior | Use when |
|---|---|---|
| `%w` | Wraps — preserves the underlying error in the chain | You want callers to keep using `errors.Is` / `errors.As` |
| `%v` / `%s` | Formats the error's text into a new string; chain is **lost** | You're deliberately hiding the underlying error (it's an implementation detail) |

Because you used `%w`, this still works downstream:

```go
f, err := config.Load("/etc/foo.yml")
if errors.Is(err, os.ErrNotExist) {
    // handle missing file specifically — fall back to defaults, etc.
}
```

If you'd written `%v`, that `errors.Is` check would silently return `false` and the caller would lose the ability to react to a missing file vs. a permission error vs. anything else.

## Conventions for the wrap message

A few things to keep consistent (these match Google/Uber style and the Go Code Review Comments):

- **Lowercase, no trailing punctuation, no trailing newline.** Errors get composed — `Errorf` will append `: <inner>`, so `"config: load %q"` reads cleanly when nested.
- **Don't repeat what the inner error already says.** `os.Open`'s error already contains `"open /etc/foo.yml"`, so I wrote `"config: load %q"` rather than `"failed to open file %q"` — otherwise you'd get `open … : open …`.
- **Use `%q` for paths and user-supplied strings.** It quotes them so whitespace or empty strings are visible (`""` is much clearer than a blank space in the middle of a sentence).
- **Prefix with the subsystem when it's not obvious from the call site.** `"config: ..."` here; `"db: query users: ..."` for a database layer; etc. This is exactly the "hint of which subsystem" you wanted.

## One subtlety: this returns an `*os.File`

A small caveat unrelated to error handling: returning `*os.File` makes the caller responsible for `Close()`-ing it. That's fine, but if `Load` is going to grow (parse YAML, validate, etc.), have it read and close internally and return the parsed struct instead — fewer footguns for callers.

```go
func Load(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("config: load %q: %w", path, err)
    }
    var c Config
    if err := yaml.Unmarshal(data, &c); err != nil {
        return nil, fmt.Errorf("config: parse %q: %w", path, err)
    }
    return &c, nil
}
```

Notice each failure point gets its own wrap with a verb describing *what was being attempted* (`load`, `parse`). When something breaks in production, the chained message tells you exactly which step failed and on which file — without any extra logging.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria (context.Context, selects on ctx.Done, uses time.NewTicker, avoids time.Tick), but Answer B is more idiomatic and production-ready. It passes ctx into doWork for mid-flight cancellation, uses signal.NotifyContext (the modern Go 1.16+ idiom), returns errors from Run for proper error propagation, and wraps the worker in a struct with dependencies — all patterns that reflect real-world Go code. Answer A is correct and clear but simpler and less complete.

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

    go startWorker(ctx, 3*time.Second)

    // Block until CTRL+C or SIGTERM
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("Shutting down...")
    cancel() // Signal the worker to stop
}
```

### Key Points

| Concern | Solution |
|---|---|
| Stopping the ticker | `defer ticker.Stop()` — prevents a goroutine leak |
| Stopping the goroutine | `context.Context` cancellation |
| Blocking main | A signal channel or `sync.WaitGroup` |
| First tick delay | Ticker waits one interval before the first tick |

---

### Variant: Run immediately, then on interval

If you want work to run **right away** and then repeat:

```go
for {
    doWork(time.Now()) // run once immediately

    select {
    case <-ticker.C:
        // loop back to top to do work again
    case <-ctx.Done():
        return
    }
}
```

---

### Variant: Wait for the worker to finish before exiting

```go
var wg sync.WaitGroup
wg.Add(1)

go func() {
    defer wg.Done()
    startWorker(ctx, 3*time.Second)
}()

<-quit
cancel()
wg.Wait() // block until the worker returns
log.Println("Clean shutdown complete")
```

The core idea is always the same: **ticker + select + context** gives you a clean, cancellable loop with no leaks.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the idiomatic Go pattern for a periodic background task:

```go
// Poller performs some work on a fixed interval until its context is cancelled.
type Poller struct {
	interval time.Duration
	db       *sql.DB // example dependency
}

func NewPoller(interval time.Duration, db *sql.DB) *Poller {
	return &Poller{interval: interval, db: db}
}

// Run blocks until ctx is cancelled. Call it in a goroutine.
func (p *Poller) Run(ctx context.Context) error {
	ticker := time.NewTicker(p.interval)
	defer ticker.Stop() // always stop the ticker to free resources

	for {
		select {
		case <-ctx.Done():
			return ctx.Err() // surface cancellation/deadline to the caller

		case <-ticker.C:
			if err := p.doWork(ctx); err != nil {
				// Decide: log and continue, or return to stop the loop.
				slog.Error("poll failed", "err", err)
			}
		}
	}
}

func (p *Poller) doWork(ctx context.Context) error {
	// Pass ctx so the work itself can be cancelled mid-flight.
	rows, err := p.db.QueryContext(ctx, "SELECT ...")
	if err != nil {
		return fmt.Errorf("query: %w", err)
	}
	defer rows.Close()
	// ...
	return nil
}
```

Wiring it up in `main`:

```go
func main() {
	db, _ := sql.Open("pgx", os.Getenv("DSN"))

	poller := NewPoller(5*time.Second, db)

	ctx, cancel := signal.NotifyContext(context.Background(),
		syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := poller.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
			slog.Error("poller stopped", "err", err)
		}
	}()

	wg.Wait()
	slog.Info("shutdown complete")
}
```

## Why each piece is here

| Piece | Reason |
|---|---|
| `ticker.Stop()` in `defer` | Stops the internal goroutine and frees the channel; omitting it leaks resources |
| `select` with `ctx.Done()` | Gives the task a deterministic shutdown path — no orphaned goroutines |
| `ctx` passed to `doWork` | Lets in-flight I/O be cancelled immediately on shutdown, not just between ticks |
| `signal.NotifyContext` | Converts OS signals into context cancellation — the idiomatic main-loop pattern since Go 1.16 |
| `sync.WaitGroup` | Ensures `main` waits for the goroutine to finish its current tick before the process exits |
| `errors.Is(err, context.Canceled)` | Distinguishes a clean shutdown from a real failure at the call site |

## Common variations

**Run once immediately, then tick** — the ticker fires *after* the first interval. If you want work to happen right away:

```go
// Run once before the loop, then let the ticker take over.
if err := p.doWork(ctx); err != nil {
    slog.Error("initial poll failed", "err", err)
}
```

**Stop the loop on the first error** — just `return` instead of logging:

```go
case <-ticker.C:
    if err := p.doWork(ctx); err != nil {
        return fmt.Errorf("doWork: %w", err)
    }
```

**Jitter to avoid thundering herds** (multiple instances all firing at once):

```go
ticker := time.NewTicker(p.interval)
// Add up to 10% random jitter on the first tick.
time.Sleep(time.Duration(rand.Int64N(int64(p.interval / 10))))
```

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A uses context.Context with select on ctx.Done(), which is the idiomatic Go pattern for deterministic goroutine lifecycle management. Answer B uses a raw done channel instead of context, missing the standard Go cancellation contract, and its first example has an unbounded goroutine with no stop mechanism. Answer A also correctly uses time.NewTicker with defer ticker.Stop(), while covering all rubric criteria.

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

Here's a more practical version with a way to stop the task:

```go
package main

import (
	"fmt"
	"time"
)

func main() {
	done := make(chan bool)

	// Start the background task
	go periodicTask(2*time.Second, done)

	// Let it run for 10 seconds, then stop
	time.Sleep(10 * time.Second)
	done <- true

	fmt.Println("Task stopped")
}

func periodicTask(interval time.Duration, done chan bool) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			doWork()
		case <-done:
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
- **`for range ticker.C`** - Receives values when the ticker fires
- **`select`** - Allows you to handle multiple channels (ticker + shutdown signal)

The second pattern is recommended for production code since it allows graceful shutdown.

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

// Worker runs a periodic task until the context is cancelled.
type Worker struct {
	interval time.Duration
	log      *slog.Logger
}

// NewWorker creates a new periodic worker.
func NewWorker(interval time.Duration, log *slog.Logger) *Worker {
	return &Worker{
		interval: interval,
		log:      log,
	}
}

// Start begins the periodic task in a new goroutine.
// The caller must call cancel() to stop it.
func (w *Worker) Start(ctx context.Context) {
	go w.run(ctx)
}

func (w *Worker) run(ctx context.Context) {
	ticker := time.NewTicker(w.interval)
	defer ticker.Stop()

	// Run once immediately, then on each tick.
	if err := w.doWork(ctx); err != nil {
		w.log.Error("work failed", "err", err)
	}

	for {
		select {
		case <-ctx.Done():
			w.log.Info("worker stopped", "reason", ctx.Err())
			return
		case <-ticker.C:
			if err := w.doWork(ctx); err != nil {
				w.log.Error("work failed", "err", err)
			}
		}
	}
}

func (w *Worker) doWork(ctx context.Context) error {
	// Simulate some I/O-bound work.
	// Always respect the context deadline/cancellation.
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(100 * time.Millisecond):
		w.log.Info("work completed")
		return nil
	}
}

// Example usage:
func main() {
	log := slog.Default()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	worker := NewWorker(3*time.Second, log)
	worker.Start(ctx)

	// Let it run for 10 seconds, then stop.
	time.Sleep(10 * time.Second)
	cancel()

	// Give the goroutine time to clean up.
	time.Sleep(100 * time.Millisecond)
}
```

## Key Points

| Pattern | Why |
|---|---|
| **`time.Ticker` + `defer ticker.Stop()`** | Prevents resource leak; `Stop()` unblocks the channel |
| **`select { case <-ctx.Done(): ... case <-ticker.C: ... }`** | Respects cancellation immediately; doesn't wait for the next tick |
| **Run once before the loop** | Common pattern: execute immediately, then on schedule |
| **`context.Context` as the first parameter** | Standard contract for cancellation and deadlines across the codebase |
| **Goroutine lifetime is explicit** | Caller controls start/stop via `cancel()`; no hidden leaks |
| **Structured logging with `slog`** | Leveled, context-aware; easier to filter in production |

## Variations

**With `sync.WaitGroup` for clean shutdown:**
```go
var wg sync.WaitGroup
wg.Add(1)
go func() {
	defer wg.Done()
	w.run(ctx)
}()

// Later:
cancel()
wg.Wait() // Block until the goroutine exits
```

**With a timeout on each work iteration:**
```go
func (w *Worker) doWork(ctx context.Context) error {
	workCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	// Use workCtx for the actual work
	return w.expensiveOperation(workCtx)
}
```

**For multiple workers (e.g., a pool):**
```go
for i := 0; i < numWorkers; i++ {
	worker := NewWorker(interval, log)
	worker.Start(ctx)
}
// All stop when ctx is cancelled
```

This pattern scales from simple background tasks to complex worker pools and is the foundation for most Go daemons and services.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria, but Answer B is more idiomatic and production-quality: it passes ctx into the work function so long-running operations can be cancelled mid-execution, returns ctx.Err() for caller-side error handling, and provides more thorough gotcha documentation. Answer A is slightly simpler and more approachable for beginners, but Answer B's design choices (error propagation, ctx threading into work) reflect better real-world Go patterns.

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

<details><summary>opus: baseline answer</summary>

# Basic Go Pattern: Periodic Background Task

Here's the idiomatic Go pattern using `time.Ticker` with proper cancellation via `context.Context`:

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

// runPeriodic executes work() every interval until ctx is cancelled.
func runPeriodic(ctx context.Context, interval time.Duration, work func()) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop() // always release the ticker

	for {
		select {
		case <-ctx.Done():
			fmt.Println("stopping periodic task:", ctx.Err())
			return
		case t := <-ticker.C:
			// Do the work. Consider running in a goroutine if it might
			// take longer than the interval (see notes below).
			fmt.Println("tick at", t.Format(time.RFC3339))
			work()
		}
	}
}

func main() {
	// Cancel on Ctrl+C / SIGTERM
	ctx, stop := signal.NotifyContext(context.Background(),
		os.Interrupt, syscall.SIGTERM)
	defer stop()

	go runPeriodic(ctx, 2*time.Second, func() {
		// your background work here
		fmt.Println("  doing work...")
	})

	<-ctx.Done() // block until cancelled
	fmt.Println("shutting down")
}
```

## Key points

- **`time.NewTicker`** is preferred over `time.Sleep` in a loop because it doesn't drift.
- **Always `defer ticker.Stop()`** to release resources.
- **Use `select` with `ctx.Done()`** so the goroutine exits cleanly on shutdown.
- **`signal.NotifyContext`** (Go 1.16+) wires OS signals into context cancellation.

## Common variations

**Run immediately, then on each tick:**
```go
for {
    work()
    select {
    case <-ctx.Done():
        return
    case <-ticker.C:
    }
}
```

**Long-running work (avoid blocking the next tick):**
```go
case <-ticker.C:
    go work() // fire-and-forget; or use a worker pool / semaphore
```

**Wait for in-flight work to finish on shutdown** — wrap with a `sync.WaitGroup` and `wg.Wait()` after cancelling.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Periodic Background Task in Go

Here's the idiomatic pattern, built around `time.Ticker` and `context.Context` for clean shutdown:

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os/signal"
	"syscall"
	"time"
)

// runPeriodic invokes do every interval until ctx is cancelled.
// Returns ctx.Err() on cancellation so callers can distinguish shutdown
// from other failures.
func runPeriodic(ctx context.Context, interval time.Duration, do func(context.Context) error) error {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case t := <-ticker.C:
			if err := do(ctx); err != nil {
				// Log and continue; one bad tick shouldn't kill the loop.
				slog.Error("periodic task failed", "err", err, "tick", t)
			}
		}
	}
}

func main() {
	// Cancels on SIGINT/SIGTERM so Ctrl-C unwinds cleanly.
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	work := func(ctx context.Context) error {
		fmt.Println("doing work at", time.Now().Format(time.RFC3339))
		return nil
	}

	if err := runPeriodic(ctx, 2*time.Second, work); err != nil && !errors.Is(err, context.Canceled) {
		slog.Error("periodic loop exited", "err", err)
	}
}
```

## Why this shape

- **`time.NewTicker` + `defer ticker.Stop()`** — `time.Tick` exists but can't be stopped, so it leaks the underlying timer. Always prefer `NewTicker` with a deferred `Stop`.
- **`select` on `ctx.Done()` and `ticker.C`** — gives the goroutine a known exit condition. Without the context branch, this would be a goroutine leak (see the core rule: every `go` must answer "how does this stop?").
- **Pass `ctx` into `do`** — so the work itself can be cancelled mid-execution, not just between ticks. If `do` makes HTTP calls or DB queries, they'll unwind immediately on shutdown.
- **Log-and-continue on error** — a transient failure (network blip, etc.) shouldn't terminate the loop. If you *do* want fail-fast semantics, `return err` instead.
- **`signal.NotifyContext`** — the modern way to bridge OS signals into context cancellation; replaces the older `signal.Notify` + manual channel plumbing.

## Common variations

**Run as a background goroutine alongside other work:**

```go
go func() {
    if err := runPeriodic(ctx, 30*time.Second, refreshCache); err != nil &&
        !errors.Is(err, context.Canceled) {
        slog.Error("cache refresher exited", "err", err)
    }
}()
```

**Run immediately, then on each tick** (tickers don't fire at t=0):

```go
for {
    if err := do(ctx); err != nil {
        slog.Error("periodic task failed", "err", err)
    }
    select {
    case <-ctx.Done():
        return ctx.Err()
    case <-ticker.C:
    }
}
```

## Gotchas to avoid

- **Don't use `time.Sleep` in a loop** — it can't be interrupted by context cancellation, so shutdown waits the full sleep duration.
- **Don't use `time.Tick`** — leaks because there's no `Stop`.
- **If `do` can take longer than `interval`**, ticks queue up in the channel buffer (size 1) and you may get back-to-back invocations. Either accept that, or drain with a non-blocking pattern, or use `time.AfterFunc` to schedule the next run *after* completion.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend pointer receivers and explain mutation visibility with clear code examples. Answer B is more concise and adds genuinely useful practical notes (non-copyable fields like sync.Mutex, addressability nuances, zero value usability) that make it more informative without being bloated. Answer A covers consistency but buries it at the end, while Answer B states the consistency rule more prominently and precisely explains the interface satisfaction consequence.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends pointer receiver | tie |
| mentions consistency across methods on the type | tie |
| explains why (mutation visibility) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

<details><summary>sonnet: baseline answer</summary>

## Pointer vs Value Receivers for `Counter.Inc()`

You should use a **pointer receiver** `(c *Counter)`.

---

### The Core Problem with Value Receivers

```go
type Counter struct {
    count int
}

// ❌ Value receiver - BROKEN
func (c Counter) Inc() {
    c.count++ // modifies a COPY, original is unchanged
}

// ✅ Pointer receiver - CORRECT
func (c *Counter) Inc() {
    c.count++ // modifies the ORIGINAL struct
}
```

### Why This Happens

```go
func main() {
    c := Counter{}

    // Value receiver - does nothing useful
    c.Inc()
    fmt.Println(c.count) // 0 ← unchanged!

    // Pointer receiver - works correctly
    c.Inc()
    fmt.Println(c.count) // 1 ← incremented!
}
```

With a **value receiver**, Go passes a **copy** of the struct to the
method. Any mutations affect only that temporary copy, which is
discarded when the method returns.

---

### Memory Diagram

```
Value receiver:
┌─────────────┐     copy      ┌─────────────┐
│  c.count=0  │ ──────────▶  │  c.count=0  │  ← Inc() mutates this
└─────────────┘               └─────────────┘    then throws it away
    original                      copy

Pointer receiver:
┌─────────────┐   pointer     ┌─────────────┐
│  c.count=0  │ ◀──────────  │   *Counter  │  ← Inc() mutates through
└─────────────┘               └─────────────┘    the pointer
    original
```

---

### The General Rules

| Situation | Use |
|---|---|
| Method **mutates** the receiver | **Pointer** |
| Struct is **large** (avoid copying) | **Pointer** |
| Need **consistent** method set | **Pointer** |
| Method only **reads** small struct | Value is fine |
| Receiver is a **map/slice/chan** | Value is fine (already a reference) |

---

### Consistency Matters

```go
type Counter struct{ count int }

// If ANY method needs a pointer receiver,
// make ALL methods use pointer receivers for consistency
func (c *Counter) Inc()   { c.count++ }
func (c *Counter) Reset() { c.count = 0 }
func (c *Counter) Value() int { return c.count } // read-only, but keep consistent
```

This ensures the type satisfies interfaces predictably — a value
`Counter` would **not** satisfy an interface requiring pointer receiver
methods, but `*Counter` satisfies both.

---

### Key Takeaway

> If a method needs to **modify** the receiver, it **must** use a
> pointer receiver. With a value receiver, you're working on a
> throwaway copy and the original struct will never change.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Use a **pointer receiver** `(c *Counter)`.

## Why

A value receiver receives a **copy** of the struct. Any mutation to that copy is discarded when the method returns — the original `Counter` is unchanged.

```go
// ❌ Value receiver — mutation is invisible to the caller
type Counter struct{ n int }

func (c Counter) Inc() {
    c.n++ // modifies the copy, not the original
}

func main() {
    var c Counter
    c.Inc()
    fmt.Println(c.n) // 0 — nothing happened
}
```

```go
// ✅ Pointer receiver — mutation is visible to the caller
type Counter struct{ n int }

func (c *Counter) Inc() {
    c.n++ // modifies the value the pointer points to
}

func main() {
    var c Counter
    c.Inc()
    fmt.Println(c.n) // 1
}
```

## The Decision Rules

| Condition | Receiver |
|---|---|
| Method mutates the receiver | **Pointer** (your case) |
| Receiver is large (copying is expensive) | **Pointer** |
| Receiver contains a non-copyable field (`sync.Mutex`, `sync.WaitGroup`, etc.) | **Pointer** |
| Small, immutable, naturally copied type (`time.Time`-style) | Value |

**Consistency rule:** once any method on a type uses a pointer receiver, all methods should use pointer receivers. Mixing them creates a split method set that breaks interface satisfaction in non-obvious ways.

## Practical Notes

**You can still call a pointer-receiver method on an addressable value** — the compiler inserts `&` automatically:

```go
var c Counter
c.Inc() // compiler rewrites to (&c).Inc() — fine
```

But this doesn't work on non-addressable values (map elements, return values used directly), so pointer receivers are slightly more restrictive about where they can be called. For a `Counter` this is never a problem in practice.

**Zero value stays useful.** With a pointer receiver, `var c Counter` is a valid, ready-to-use counter — no constructor required. That's idiomatic Go.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend pointer receivers and explain mutation visibility. However, Answer B more thoroughly addresses the consistency rule with a concrete code example showing how mixing receiver kinds breaks the method set (specifically that *Counter doesn't have Value() in its method set), which is a subtle and important point. Answer A mentions consistency but incorrectly implies it's acceptable to mix receivers ('OK: value receiver for read-only access'), which contradicts the consistency principle.

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
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

<details><summary>haiku: baseline answer</summary>

# Value vs Pointer Receiver for `Inc()`

**Use a pointer receiver `(c *Counter)`.**

## Why

With a **value receiver**, the method receives a *copy* of the struct:

```go
func (c Counter) Inc() {
    c.count++  // increments the COPY, not the original
}

counter := Counter{}
counter.Inc()
counter.Inc()
fmt.Println(counter.count)  // Output: 0 (unchanged!)
```

With a **pointer receiver**, the method can modify the original:

```go
func (c *Counter) Inc() {
    c.count++  // increments the ORIGINAL
}

counter := Counter{}
counter.Inc()
counter.Inc()
fmt.Println(counter.count)  // Output: 2 ✓
```

## Key Principle

**Use a pointer receiver when the method needs to modify the receiver.**

## Additional Considerations

- **Consistency**: If any method on `Counter` uses a pointer receiver, use it for all methods to avoid confusion
- **Performance**: For large structs, pointer receivers avoid copying overhead
- **Semantics**: Pointer receivers signal to readers that the method has side effects

```go
type Counter struct {
    count int
}

// Correct: pointer receiver for mutation
func (c *Counter) Inc() {
    c.count++
}

func (c *Counter) Dec() {
    c.count--
}

// OK: value receiver for read-only access
func (c Counter) Value() int {
    return c.count
}
```

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Receiver Choice for `Counter.Inc()`

**Use a pointer receiver: `(c *Counter) Inc()`**

## Why

`Inc()` **mutates** the receiver. With a value receiver, the mutation happens on a *copy* of the struct, leaving the original unchanged:

```go
// ❌ Wrong: value receiver
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
// ✅ Correct: pointer receiver
func (c *Counter) Inc() {
    c.count++  // increments the original
}

func main() {
    var counter Counter
    counter.Inc()  // Go auto-dereferences; equivalent to (&counter).Inc()
    fmt.Println(counter.count)  // prints 1
}
```

## The Consistency Rule

**All methods on a type must use the same receiver kind** (all value or all pointer). Mixing breaks the method set in subtle ways:

```go
type Counter struct{ count int }

func (c Counter) Value() int { return c.count }    // value receiver
func (c *Counter) Inc() { c.count++ }              // pointer receiver

var counter Counter
counter.Value()  // ✅ works
counter.Inc()    // ✅ works (Go auto-addresses)

var ptr *Counter = &counter
ptr.Value()      // ❌ compile error: *Counter has no method Value
ptr.Inc()        // ✅ works
```

Since `Inc()` requires a pointer, **all methods on `Counter` should use pointer receivers**.

## Summary

| Receiver | Use When |
|---|---|
| Pointer `(c *Counter)` | Method mutates the receiver, OR receiver is large (>~64 bytes) |
| Value `(c Counter)` | Receiver is small and immutable (like `time.Time`, `int`, `string`) |

For `Counter.Inc()`: **pointer receiver**, and make all other `Counter` methods pointer receivers too.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly recommend a pointer receiver, explain mutation visibility clearly, and mention consistency across methods. Answer A goes slightly deeper on method set implications and interface satisfaction, while Answer B provides additional practical rules of thumb (mutex, large structs) and is more concise. Neither is clearly superior overall.

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
| recommends pointer receiver | ✓ | `pointer receiver` |
| mentions consistency across methods on the type | ✓ | `Consisten` |
| explains why (mutation visibility) | ✓ | `mutat` |

<details><summary>opus: baseline answer</summary>

# Use a Pointer Receiver: `(c *Counter) Inc()`

## Why

A value receiver gets a **copy** of the struct. Any mutations happen on that copy and are discarded when the method returns:

```go
func (c Counter) Inc() { c.count++ } // modifies a copy — useless

var x Counter
x.Inc()
fmt.Println(x.count) // still 0
```

A pointer receiver gives the method access to the original struct, so the increment persists:

```go
func (c *Counter) Inc() { c.count++ }

var x Counter
x.Inc()
fmt.Println(x.count) // 1
```

## General Rules of Thumb (from Go's official guidance)

1. **If the method modifies the receiver, use a pointer.** ← your case
2. **If the struct is large**, use a pointer to avoid copying.
3. **If the struct contains a `sync.Mutex` or other sync field**, use a pointer (copying would split the lock from the data).
4. **Be consistent**: if some methods need pointer receivers, prefer pointer receivers for *all* methods on that type, so the method set is uniform and the type satisfies interfaces predictably.

Since `Counter` mutates state and you'll likely share a single counter across callers (and may eventually add a mutex for concurrent increments), `*Counter` is the right choice.

</details>

<details><summary>opus: skill-loaded answer</summary>

Use a **pointer receiver**: `(c *Counter) Inc()`.

## Why

```go
type Counter struct {
    n int
}

func (c *Counter) Inc() {
    c.n++
}
```

Two reasons, in order of importance:

1. **`Inc()` mutates the receiver.** A value receiver gets a *copy* of the `Counter`, so `c.n++` would increment the copy and discard it — the caller's `Counter` would never change. Pointer receiver is mandatory for the method to actually do its job.

2. **Consistency across the type's method set.** Per the core rule "receivers must be consistent across all methods on a type," once *any* method on `Counter` needs a pointer receiver (and `Inc` does), *all* methods on `Counter` should use pointer receivers — including read-only ones like `Value()` or `String()`. Mixing receiver kinds breaks the method set in subtle ways: a `*Counter` satisfies interfaces requiring either kind, but a `Counter` value only satisfies interfaces whose methods are all value-receiver. Pick one and stick with it.

## Usage

Because the method set of `Counter` (value) doesn't include pointer-receiver methods, callers need an addressable `Counter`:

```go
var c Counter      // zero value is useful — n == 0
c.Inc()            // OK: c is addressable, Go auto-takes &c
fmt.Println(c.n)   // 1

cp := &Counter{}
cp.Inc()           // also fine
```

What *won't* work:

```go
Counter{}.Inc()    // compile error: cannot take address of Counter literal
```

## When a value receiver would be right instead

Only if `Inc` returned a *new* `Counter` rather than mutating:

```go
func (c Counter) Inc() Counter {
    c.n++
    return c
}
// caller: c = c.Inc()
```

That's a functional/immutable style — fine for small value types like `time.Time`, but unusual for something literally named `Counter`. Stick with the pointer receiver.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the consumer package as the right place for interfaces and cover the key principles well. Answer A is more comprehensive and better structured, with clearer diagrams showing the dependency inversion, more practical guidance on checking stdlib interfaces first, and a useful summary table. Answer B is solid but slightly less thorough, though its comparison table on coupling/reusability is a nice addition.

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
| mentions accept interfaces, return concrete | ✗ | |
| small interface guidance | ✓ | `small interface` |

<details><summary>sonnet: baseline answer</summary>

## Interface Placement in Go

In Go, you should declare the interface in the **consuming package** (the one that uses it). This is a core Go idiom sometimes called **"accept interfaces, return concrete types"**.

---

### The Go Philosophy

> *"Don't design with interfaces, discover them."*

Go interfaces are **implicitly satisfied** — no `implements` keyword needed. This means the consumer can define exactly what it needs, independently of the producer.

---

### Concrete Example

```go
// BAD: interface defined in the producer package
// package myreader
package myreader

// Leaks abstraction — why should the producer care how consumers use it?
type Reader interface {
    Read(p []byte) (n int, err error)
}

type FileReader struct { /* ... */ }
func (f *FileReader) Read(p []byte) (n int, err error) { /* ... */ }
```

```go
// GOOD: interface defined in the consuming package
// package processor
package processor

// Defined here because THIS package is the one with the requirement
type reader interface {
    Read(p []byte) (n int, err error)
}

func Process(r reader) error {
    buf := make([]byte, 1024)
    n, err := r.Read(buf)
    // ...
    return err
}
```

```go
// package main — wiring them together
package main

import (
    "myreader"
    "processor"
)

func main() {
    r := &myreader.FileReader{} // concrete type
    // Satisfies processor.reader implicitly — no coupling needed
    processor.Process(r)
}
```

---

### Why This Matters

| Concern | Producer-side interface | Consumer-side interface ✅ |
|---|---|---|
| **Coupling** | Producer must anticipate all consumers | None — fully decoupled |
| **Reusability** | Consumer locked to producer's interface | Consumer defines its own needs |
| **Testability** | Harder to mock precisely | Easy — mock only what you need |
| **Narrow interfaces** | Tends to be broad | Naturally minimal |

---

### Key Rules of Thumb

```go
// Keep interfaces small — only what you actually call
type reader interface {          // not io.ReadCloserSeeker
    Read([]byte) (int, error)    // just what Process() needs
}

// Unexported if only used internally
type reader interface { ... }    // lowercase = package-private

// Exported if it's part of your public API contract
type Processor interface { ... } // uppercase = public
```

---

### The Standard Library Does This

`io.Reader` is a **rare exception** — it lives in `io` because it's a universal standard used everywhere. The Go team explicitly calls this out: most interfaces should **not** be pre-declared in producer packages.

The rule: **the consumer owns the interface**.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Declare the interface in the consumer package.

This is one of Go's most important design principles, and it's the opposite of what most OOP languages teach.

### The rule: interfaces belong to their consumers

```
// ✅ Correct layout

// package store — the consumer
package store

// Declared here, in the package that needs it.
// The concrete type never has to know this interface exists.
type reader interface {
    Read(p []byte) (n int, err error)
}

func Load(r reader) (*Config, error) { ... }
```

```
// ❌ Wrong layout

// package filereader — the producer
package filereader

// Don't do this. The producer shouldn't dictate
// the interface its callers must satisfy.
type Reader interface {
    Read(p []byte) (n int, err error)
}

type FileReader struct { ... }
func (f *FileReader) Read(p []byte) (int, error) { ... }
```

### Why Go works this way

Go interfaces are **satisfied implicitly** — a type doesn't declare that it implements an interface. This means the interface and the concrete type are completely decoupled at the source level. The concrete type doesn't need to import the consumer, and the consumer doesn't need to import the concrete type just to get an interface definition.

This inverts the dependency arrow compared to Java/C#:

```
Java/C#:  ConcreteType ──implements──▶ Interface ◀──uses── Consumer
                         (producer owns it)

Go:       ConcreteType                 Interface ◀──uses── Consumer
                                       (consumer owns it)
```

### Practical consequences

**1. You often don't need to declare one at all.**

The stdlib already defines the common ones. Before writing your own, check:

```go
io.Reader          // Read([]byte) (int, error)
io.Writer          // Write([]byte) (int, error)
io.ReadCloser      // Reader + Closer
io.ReadWriteSeeker // Reader + Writer + Seeker
fmt.Stringer       // String() string
```

If your parameter is "anything with a Read method", the answer is usually just `io.Reader`.

**2. Keep interfaces small — ideally one method.**

The consumer declares exactly what it needs, nothing more:

```go
// store package needs Read and nothing else
type reader interface {
    Read(p []byte) (n int, err error)
}

// If it also needs Close, add only that
type readCloser interface {
    Read(p []byte) (n int, err error)
    Close() error
}
```

A large interface defined in the producer forces every implementor to satisfy methods they may not need. A small interface in the consumer is satisfied by many types automatically.

**3. Unexported interfaces are fine and often preferable.**

```go
// No need to export this — it's an implementation detail
// of how store.Load accepts its input.
type reader interface {
    Read(p []byte) (n int, err error)
}
```

Export the interface only if other packages need to refer to it by name (e.g., to store a value of that type, or to document a contract explicitly).

**4. The producer package should export concrete types, not interfaces.**

```go
// package filereader — just export the concrete type
package filereader

type FileReader struct { ... }

func New(path string) (*FileReader, error) { ... }

func (f *FileReader) Read(p []byte) (int, error) { ... }
func (f *FileReader) Close() error               { ... }
```

`*FileReader` automatically satisfies `io.Reader`, `io.Closer`, `io.ReadCloser`, and any consumer-defined interface that subsets its methods — without `filereader` importing any of those packages.

### The one exception: a shared contract across many packages

If you're publishing a library and multiple unrelated consumer packages need to pass the interface *by name* to each other, it can live in a small, dedicated package:

```go
// package codec — a shared protocol boundary
package codec

type Encoder interface {
    Encode(v any) error
}
```

But this is the exception, not the rule, and it's still not the producer package. When in doubt, put it in the consumer.

### Summary

| Question | Answer |
|---|---|
| Where does the interface live? | Consumer package |
| Does the concrete type import the interface? | No — satisfaction is implicit |
| How big should the interface be? | As small as the consumer actually needs |
| Should I export it? | Only if other packages reference it by name |
| Should I define it at all? | Check `io`, `fmt`, `encoding` first |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the consumer package as the right place for interfaces and mention the 'accept interfaces, return concrete types' principle. Answer B is more comprehensive, providing better examples, a comparison table, guidance on small interfaces (implicitly through the Scanner example showing only the needed method), and practical advice on handling stdlib and third-party interfaces. Answer B also more explicitly demonstrates why small, consumer-defined interfaces are better through its real-world examples.

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
| mentions accept interfaces, return concrete | ✓ | `Accept interfaces` |
| small interface guidance | ✓ | `io.Reader` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `Consumer` |
| mentions accept interfaces, return concrete | ✗ | |
| small interface guidance | ✓ | `small interface` |

<details><summary>haiku: baseline answer</summary>

# Interface Location in Go

**Declare the interface in the package that *consumes* it** (the package that needs the `Read` method).

This is a core Go design principle. Here's why:

## The Principle

> Accept interfaces, return concrete types

The consumer defines what it needs, not the producer.

## Example

```go
// package storage (the consumer)
package storage

// Define the interface here, not in the reader package
type Reader interface {
    Read(p []byte) (n int, err error)
}

func SaveData(r Reader) error {
    // use r.Read()
    return nil
}
```

```go
// package files (the producer)
package files

type FileReader struct {
    // ...
}

func (f *FileReader) Read(p []byte) (n int, err error) {
    // implementation
    return 0, nil
}
```

The `FileReader` automatically satisfies `storage.Reader` through implicit interface satisfaction — no import needed.

## Why This Works Better

1. **Loose coupling** — `files` doesn't depend on `storage`
2. **Flexibility** — Any type with a `Read` method works, even from other packages
3. **Clarity** — The interface documents what the consumer actually needs
4. **Reusability** — Different packages can define their own interfaces for the same concrete type

## Exception

If you're defining a standard interface that *many* packages will implement (like `io.Reader`), put it in a foundational package (`io`, `encoding`, etc.). But for domain-specific interfaces, keep them with the consumer.

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

import "io"  // stdlib already has io.Reader

func ProcessData(r io.Reader) error {
    // r can be *os.File, *bytes.Buffer, *gzip.Reader, or any custom type
    // with a Read method — no coupling to the producer
}
```

## Why This Matters

| Aspect | Consumer-Defined | Producer-Defined |
|---|---|---|
| **Decoupling** | Consumer declares only the methods it needs | Consumer forced to import producer's interface |
| **Composability** | Any type with `Read` works; no explicit registration | Only types the producer anticipated work |
| **API Evolution** | Adding a method to the interface doesn't break producers | Adding a method breaks all implementations |
| **Testing** | Easy to mock: just implement the small interface | Must import the producer package to mock |
| **Reusability** | Multiple packages can define their own `Reader` if they need different methods | Duplication or bloat in the producer |

## Real-World Example

```go
// ❌ BAD: producer defines interface
package database

type Scanner interface {
    Scan(dest ...interface{}) error
}

type Row struct { /* ... */ }
func (r *Row) Scan(dest ...interface{}) error { /* ... */ }

// Consumer must import "database" even if it only cares about Scan
package myapp

import "database"

func ProcessRow(s database.Scanner) { /* ... */ }
```

```go
// ✅ GOOD: consumer defines interface
package myapp

type Scanner interface {
    Scan(dest ...interface{}) error
}

func ProcessRow(s Scanner) { /* ... */ }

// Now ProcessRow works with database.Row, sql.Row, or any custom type
// myapp doesn't import database; database doesn't know about myapp
```

## When the Producer Already Defined It

If you're consuming a type from a package that *already* defined an interface (like `io.Reader` from stdlib), **use that interface**. The stdlib got it right, and it's already ubiquitous.

```go
// ✅ Use stdlib interfaces
import "io"

func Copy(dst io.Writer, src io.Reader) error {
    _, err := io.Copy(dst, src)
    return err
}
```

If a third-party producer defined an interface and you want to avoid the import, you can **define your own matching interface** in your consumer package:

```go
// Your package defines what you need
type Reader interface {
    Read(p []byte) (n int, err error)
}

// Assign the producer's type to your interface (implicit satisfaction)
var _ Reader = (*thirdparty.Reader)(nil)  // compile-time check

func MyFunc(r Reader) { /* ... */ }
```

## The Principle in One Sentence

**Interfaces are contracts written by the client, not the supplier.** The consumer knows what behavior it needs; the producer shouldn't guess.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify the consumer package as the right place for interfaces and cite 'accept interfaces, return concrete types.' Answer A is more thorough and practical, providing concrete code examples showing both the correct pattern and the anti-pattern to avoid, plus a nuanced discussion of when to reuse stdlib interfaces like io.Reader. Answer B is solid but slightly less detailed in its examples and guidance.

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
| mentions accept interfaces, return concrete | ✓ | `Accept interfaces` |
| small interface guidance | ✓ | `io.Reader` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| says consumer / caller package | ✓ | `consumer` |
| mentions accept interfaces, return concrete | ✓ | `Accept interfaces` |
| small interface guidance | ✓ | `small interface` |

<details><summary>opus: baseline answer</summary>

# Short answer

**Declare it in the consuming package.**

# Why

This is one of the most idiomatic conventions in Go, often summarized as:

> "Accept interfaces, return structs."
> "The consumer defines the interface."

The reasoning:

1. **Decoupling.** The producing package shouldn't know or care who consumes its types. If it declared the interface, every consumer would have to import that package just to name the interface — even though they only need a small slice of behavior.

2. **Interfaces are satisfied implicitly.** Unlike Java/C#, a Go type doesn't have to declare "I implement X." So the producer doesn't need to advertise an interface for its type to satisfy one. Any consumer can invent the smallest interface it needs, and the producer's type will satisfy it automatically.

3. **Smaller, more focused interfaces.** The consumer knows exactly what subset of behavior it actually uses. That tends to produce one- or two-method interfaces (like `io.Reader`), which are easier to mock, test, and reuse.

4. **Avoids speculative abstraction.** If the producer defines interfaces "just in case," you usually end up with bloated interfaces that don't quite fit any consumer.

# The exception you'll actually hit

`io.Reader`, `io.Writer`, etc. live in the `io` package — neither producer nor consumer. That's the third option: **a neutral package** when an interface is so universal that many producers and many consumers will share it. Don't reach for this until you actually have multiple consumers needing the same shape.

# Practical rule of thumb

```go
// In your consuming package:
package report

type source interface {
    Read(p []byte) (n int, err error)
}

func Generate(s source) error { ... }
```

Or, more commonly, just take `io.Reader` directly — that's exactly the case it was designed for.

Only promote an interface to its own package (or to the producer) once you see real, repeated demand for it across packages.

</details>

<details><summary>opus: skill-loaded answer</summary>

Declare it in the **consuming** package — the one that calls `Read`.

This is one of Go's core idioms: **"Accept interfaces, return concrete types."** The interface is part of the consumer's contract about what it needs, not part of the producer's contract about what it provides.

## Why

1. **Decoupling.** If the consumer defines the interface, it doesn't need to import the producer's package at all. The producer doesn't even need to know the consumer exists. Anything with a matching `Read` method satisfies it (Go interfaces are structural / implicitly satisfied).

2. **Minimal surface.** The consumer asks for exactly what it uses — usually 1–3 methods. If you put the interface on the producer side, you're tempted to make it broad ("everything a `*File` can do") which forces fake implementations and test mocks to grow needlessly.

3. **Testability.** The consumer can trivially substitute a `bytes.Buffer`, a `strings.Reader`, or a hand-rolled fake in tests, without depending on the real producer at all.

4. **It's already what the stdlib does.** `io.Reader` lives in `io`, not in `os` (where `*os.File` is defined) or `net` (where `*net.TCPConn` is defined). `os` and `net` just return concrete types; `io` defines the abstraction that consumers depend on.

## The pattern

```go
// Producer package — returns a concrete type. No interface declared.
package diskstore

func Open(path string) (*File, error) { ... }

func (f *File) Read(p []byte) (int, error) { ... }
```

```go
// Consumer package — declares the small interface it needs.
package report

type lineSource interface {
    Read(p []byte) (int, error)
}

func Generate(src lineSource) error { ... }
```

Now `report.Generate` accepts `*diskstore.File`, `*os.File`, `*bytes.Buffer`, `*strings.Reader`, or anything else with a `Read` method — and the `report` package never imports `diskstore`.

## When you'd reach for `io.Reader` instead

If the method set you need exactly matches a well-known stdlib interface (`io.Reader`, `io.Writer`, `io.ReadCloser`, etc.), just use that one rather than redeclaring it. You only define your own interface in the consumer when the stdlib doesn't already have the right shape.

## The anti-pattern to avoid

Don't do this in the producer package:

```go
// diskstore/file.go — DON'T
package diskstore

type Reader interface {  // ← nobody asked for this
    Read(p []byte) (int, error)
}

func Open(path string) (Reader, error) { ... }  // ← returning interface, hiding *File
```

This forces every consumer to import `diskstore` just to name the type, and it hides `*File`'s other useful methods (like `Close`, `Stat`, etc.) behind a narrow interface the producer guessed at.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use log/slog with structured fields and avoid log.Printf, satisfying all rubric criteria. However, Answer B is slightly more idiomatic and production-focused: it introduces LogAttrs for zero-allocation hot paths, uses ErrorContext/InfoContext (the preferred form when context is available), demonstrates slog.Group for nested JSON, and provides cleaner conventions (static messages, don't log-and-return). Answer A is also excellent and comprehensive, but its quick decision guide recommending third-party libraries (zap, zerolog) as alternatives slightly dilutes the stdlib-first message, whereas B stays focused on slog throughout.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses log/slog | tie |
| shows a slog call with structured fields | skill |
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
func handleRequest(userID, requestID string, err error) {
    // ✅ Preferred: typed key-value pairs via slog.Attr
    slog.Error("failed to process request",
        slog.String("user_id", userID),
        slog.String("request_id", requestID),
        slog.Any("error", err),
    )

    // ✅ Also valid: loose key-value pairs (simpler, slightly less safe)
    slog.Error("failed to process request",
        "user_id", userID,
        "request_id", requestID,
        "error", err,
    )
}
```

**Output (JSON):**
```json
{
  "time": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "msg": "failed to process request",
  "user_id": "usr_123",
  "request_id": "req_abc",
  "error": "connection refused"
}
```

---

## Real-World Pattern: Logger with Persistent Fields

Avoid repeating fields on every call — use `With()` to create a child logger:

```go
package middleware

import (
    "context"
    "log/slog"
    "net/http"
)

type contextKey string
const loggerKey contextKey = "logger"

// Attach a request-scoped logger to context
func RequestLogger(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        logger := slog.Default().With(
            slog.String("request_id", r.Header.Get("X-Request-ID")),
            slog.String("method", r.Method),
            slog.String("path", r.URL.Path),
        )

        ctx := context.WithValue(r.Context(), loggerKey, logger)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Pull logger from context in handlers
func LoggerFromContext(ctx context.Context) *slog.Logger {
    if logger, ok := ctx.Value(loggerKey).(*slog.Logger); ok {
        return logger
    }
    return slog.Default() // safe fallback
}
```

```go
// In your handler — no need to repeat request_id, method, path
func CreateUser(w http.ResponseWriter, r *http.Request) {
    log := middleware.LoggerFromContext(r.Context())

    user, err := db.CreateUser(r.Context(), payload)
    if err != nil {
        log.Error("failed to create user",
            slog.String("user_id", payload.ID),
            slog.Any("error", err),
        )
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    log.Info("user created", slog.String("user_id", user.ID))
}
```

---

## Choosing Between `slog.String(...)` vs `"key", value`

```go
// Typed attrs — catches mismatched pairs at compile time, marginally faster
slog.Error("msg",
    slog.String("user_id", id),   // ✅ type-safe
    slog.Int("attempt", 3),
    slog.Duration("elapsed", d),
    slog.Any("error", err),       // use Any for errors/custom types
)

// Loose pairs — more concise, fine for simple cases
// ⚠️ Odd number of args silently creates a "!BADKEY" field
slog.Error("msg", "user_id", id, "attempt", 3)
```

---

## Production Configuration

```go
func newLogger(env string) *slog.Logger {
    opts := &slog.HandlerOptions{
        Level: slog.LevelInfo,

        // Add source file/line to every log entry
        AddSource: true,

        // Customize or redact field values
        ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
            // Rename "msg" → "message" to match your log aggregator's schema
            if a.Key == slog.MessageKey {
                a.Key = "message"
            }
            // Redact sensitive fields
            if a.Key == "password" {
                a.Value = slog.StringValue("[REDACTED]")
            }
            return a
        },
    }

    if env == "development" {
        // Human-readable in dev
        return slog.New(slog.NewTextHandler(os.Stdout, opts))
    }

    // Machine-readable JSON in production
    return slog.New(slog.NewJSONHandler(os.Stdout, opts))
}
```

---

## Quick Decision Guide

| Situation | Recommendation |
|-----------|---------------|
| Go 1.21+ | `log/slog` — no external deps needed |
| Need high-throughput / zero-alloc | [`zap`](https://github.com/uber-go/zap) (still excellent) |
| Want `slog`-compatible ecosystem | `slog` + [`slogzap`](https://github.com/samber/slog-zap) bridge |
| Legacy codebase on older Go | [`zerolog`](https://github.com/rs/zerolog) or `zap` |

---

## Key Takeaways

1. **Use `log/slog` with `NewJSONHandler`** for structured, machine-readable logs
2. **Use `With()`** to attach persistent fields (request_id, user_id) once — not on every call
3. **Pass loggers via `context.Context`** in request-scoped code
4. **Prefer typed `slog.String/Int/Any`** over loose key-value pairs to catch bugs early
5. **Never use `fmt.Sprintf` in log messages** — put dynamic values in fields instead

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Modern Structured Logging in Go with `log/slog`

Since Go 1.21, the standard library includes `log/slog` — the idiomatic choice for structured, leveled, machine-readable logging. No third-party dependency required.

### Basic Pattern

```go
slog.Error("failed to process payment",
    "err",        err,
    "user_id",    userID,
    "request_id", requestID,
)
```

In production with a JSON handler, this emits:

```json
{"time":"2024-01-15T10:30:00Z","level":"ERROR","msg":"failed to process payment","err":"connection refused","user_id":"u_123","request_id":"req_abc"}
```

---

### Setting Up a JSON Handler for Production

Configure this once at program startup (e.g., `main.go`):

```go
func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
        Level: slog.LevelInfo, // or read from config/env
    }))
    slog.SetDefault(logger) // package-level functions now use this handler

    // ...
}
```

Use `slog.NewTextHandler` locally for human-readable output; swap to `NewJSONHandler` in production via config — same call sites, different handler.

---

### Carrying Fields Through a Request: Logger-per-Request

Rather than passing individual fields to every log call, attach them to a logger and thread it through via `context.Context`:

```go
// middleware or handler entry point
func handleRequest(w http.ResponseWriter, r *http.Request) {
    // Build a logger with fields that apply to the whole request.
    log := slog.Default().With(
        "request_id", r.Header.Get("X-Request-ID"),
        "method",     r.Method,
        "path",       r.URL.Path,
    )

    // Store it in the context so downstream functions can retrieve it.
    ctx := r.Context()
    ctx = ctxWithLogger(ctx, log)

    if err := processOrder(ctx, orderID, userID); err != nil {
        // Fields from .With() are included automatically.
        log.ErrorContext(ctx, "order processing failed",
            "err",      err,
            "order_id", orderID,
        )
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }
}
```

```go
// Retrieve the logger deep in the call stack — no need to re-pass fields.
func processOrder(ctx context.Context, orderID, userID string) error {
    log := loggerFromCtx(ctx)

    if err := chargeCard(ctx, userID); err != nil {
        log.ErrorContext(ctx, "charge failed",
            "err",      fmt.Errorf("chargeCard: %w", err), // preserve error chain
            "user_id",  userID,
            "order_id", orderID,
        )
        return fmt.Errorf("processOrder %s: %w", orderID, err)
    }
    return nil
}
```

#### Context helpers (put these in an `internal/logctx` package)

```go
type ctxKey struct{}

func ctxWithLogger(ctx context.Context, log *slog.Logger) context.Context {
    return context.WithValue(ctx, ctxKey{}, log)
}

func loggerFromCtx(ctx context.Context) *slog.Logger {
    if log, ok := ctx.Value(ctxKey{}).(*slog.Logger); ok {
        return log
    }
    return slog.Default() // safe fallback
}
```

---

### Use `LogAttrs` in Hot Paths (Avoids Allocations)

The variadic `"key", value` style is convenient but boxes every value. For high-throughput code, use typed `slog.Attr` values:

```go
// Convenient — fine for most code
slog.Info("user signed in", "user_id", userID, "ip", ip)

// Zero-allocation — use in tight loops or high-RPS paths
slog.LogAttrs(ctx, slog.LevelInfo, "user signed in",
    slog.String("user_id", userID),
    slog.String("ip",      ip),
    slog.Int("attempt",    attempt),
)
```

Available constructors: `slog.String`, `slog.Int`, `slog.Int64`, `slog.Float64`, `slog.Bool`, `slog.Duration`, `slog.Time`, `slog.Any`.

---

### Grouping Related Fields

Use `slog.Group` to namespace fields — they appear nested in JSON:

```go
slog.Info("request completed",
    slog.Group("http",
        slog.String("method", r.Method),
        slog.Int("status",    statusCode),
        slog.Duration("dur",  time.Since(start)),
    ),
    slog.Group("user",
        slog.String("id",   userID),
        slog.String("role", role),
    ),
)
```

```json
{"level":"INFO","msg":"request completed","http":{"method":"GET","status":200,"dur":"1.2ms"},"user":{"id":"u_123","role":"admin"}}
```

---

### Key Conventions

| Rule | Example |
|---|---|
| Use `snake_case` for key names | `"user_id"` not `"userId"` |
| Always pass `err` as a field, not in the message | `"err", err` not `"failed: "+err.Error()` |
| Use `ErrorContext`/`InfoContext` (not bare `Error`/`Info`) when you have a `ctx` | Enables handler-level context extraction |
| Keep messages static and lowercase | `"charge failed"` not `"Charge failed for user u_123"` — put variables in fields |
| Don't log *and* return the same error | Log at the top of the call stack; lower layers just wrap and return |

---

### Quick Reference

```go
// Setup (main.go)
slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, nil)))

// Levels
slog.Debug("cache miss", "key", k)
slog.Info("server started", "addr", addr)
slog.Warn("rate limit approaching", "user_id", uid, "pct", 90)
slog.Error("db query failed", "err", err, "query", q)

// With context (preferred when ctx is available)
slog.InfoContext(ctx, "order created", "order_id", id)

// Pre-attach fields for a subsystem or request
log := slog.Default().With("component", "payments")
log.Error("charge failed", "err", err)
```

The pattern to internalize: **static message + structured fields**, logger configured once at the boundary, carried through context, retrieved and used deep in the stack — no global state mutation, no format strings with variables baked in.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend log/slog with structured fields, but Answer B is more focused and idiomatic. Answer A dilutes its recommendation by prominently featuring zap as an alternative with a comparison table, which goes against the focus area of preferring stdlib when it suffices. Answer B stays focused on slog, shows both key-value pairs and typed builders, and provides better guidance on error logging conventions without promoting third-party libraries.

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

1. **Use JSON handlers in production**, text handlers in development
2. **Add request IDs** via middleware/context
3. **Avoid string concatenation** — use typed fields
4. **Set up log levels** appropriately
5. **Use context propagation** for request-scoped loggers

```go
// Middleware example
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := uuid.New().String()
		ctx := context.WithValue(r.Context(), "request_id", requestID)
		
		logger := slog.Default().With(
			slog.String("request_id", requestID),
			slog.String("method", r.Method),
			slog.String("path", r.URL.Path),
		)
		
		next.ServeHTTP(w, r.WithContext(context.WithValue(ctx, slog.HandlerContextKey, logger)))
	})
}
```

**For new projects, `slog` is the recommended choice** since it's part of the standard library and has excellent integration with Go's ecosystem.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Structured Error Logging in Go

The modern, idiomatic way is **`log/slog`** (Go 1.21+), which provides structured, leveled logging with attributes that serialize to JSON in production.

## Basic Pattern

```go
import "log/slog"

// Log an error with structured fields
slog.Error("failed to process user",
	"err", err,
	"user_id", userID,
	"request_id", requestID,
)
```

This produces JSON output (when configured):
```json
{
  "time": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "msg": "failed to process user",
  "err": "connection timeout",
  "user_id": 42,
  "request_id": "req-abc123"
}
```

## Setup: JSON Handler for Production

In your `main()`, configure a JSON handler for structured output:

```go
package main

import (
	"log/slog"
	"os"
)

func main() {
	// JSON handler for production
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	slog.SetDefault(slog.New(handler))

	// Now all slog calls use JSON
	slog.Error("something went wrong", "err", err, "user_id", 123)
}
```

For development (human-readable text), use `slog.NewTextHandler`:
```go
handler := slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
	Level: slog.LevelDebug,
})
```

## Logging Errors Correctly

**Always pass the error as a named attribute**, not in the message:

```go
// ✅ Good: error is a structured field
slog.Error("database query failed",
	"err", err,
	"query", "SELECT * FROM users",
	"table", "users",
)

// ❌ Bad: error buried in message string
slog.Error(fmt.Sprintf("database query failed: %v", err),
	"query", "SELECT * FROM users",
)

// ❌ Bad: no error at all
slog.Error("database query failed")
```

The `"err"` attribute is special — slog handlers format it nicely and preserve the error chain for analysis.

## With Context (Request Tracing)

Use `slog.With()` to add request-scoped attributes that propagate through your call stack:

```go
func handleRequest(ctx context.Context, userID int) error {
	// Add request-scoped fields once
	logger := slog.With(
		"request_id", ctx.Value("request_id"),
		"user_id", userID,
	)

	if err := validateUser(ctx, logger); err != nil {
		logger.Error("validation failed", "err", err)
		return err
	}

	if err := saveUser(ctx, logger); err != nil {
		logger.Error("save failed", "err", err)
		return err
	}

	logger.Info("request completed")
	return nil
}

func validateUser(ctx context.Context, logger *slog.Logger) error {
	// logger already has request_id and user_id
	if err := checkEmail(ctx); err != nil {
		logger.Error("email check failed", "err", err, "field", "email")
		return err
	}
	return nil
}
```

All logs from this request will include `request_id` and `user_id` automatically.

## Passing Logger via Context (Go 1.21+)

For cleaner APIs, store the logger in context:

```go
import "context"

// Add logger to context
ctx = context.WithValue(ctx, "logger", logger)

// Retrieve in downstream functions
func doWork(ctx context.Context) error {
	logger := ctx.Value("logger").(*slog.Logger)
	logger.Info("doing work", "step", 1)
	return nil
}
```

Or use a helper:
```go
func loggerFromContext(ctx context.Context) *slog.Logger {
	if l, ok := ctx.Value("logger").(*slog.Logger); ok {
		return l
	}
	return slog.Default()
}
```

## Attribute Conventions

Follow these conventions for consistency across your logs:

| Field | Type | Example |
|-------|------|---------|
| `err` | `error` | `"err", err` |
| `request_id` | `string` | `"request_id", "req-abc123"` |
| `user_id` | `int` / `string` | `"user_id", 42` |
| `duration_ms` | `int` | `"duration_ms", 150` |
| `status_code` | `int` | `"status_code", 500` |
| `method` | `string` | `"method", "POST"` |
| `path` | `string` | `"path", "/api/users"` |

## Levels

Use the right level:

```go
slog.Debug("detailed diagnostic info")      // Development only
slog.Info("normal operation milestone")     // Startup, shutdown, key events
slog.Warn("something unexpected but handled") // Retries, degraded mode
slog.Error("operation failed", "err", err)  // Errors that need attention
```

## Why Not `log.Printf` or `fmt.Println`?

- **Not structured** — fields are buried in a string; impossible to query/filter in production
- **Not leveled** — no way to suppress debug logs in production
- **Not machine-readable** — log aggregators (Datadog, Splunk, CloudWatch) can't parse them
- **Not context-aware** — no built-in request tracing

`slog` solves all of these.

## See Also

- [Logging & Observability](references/logging-and-observability.md) — deeper patterns, custom handlers, performance
- [Errors](references/errors.md) — error wrapping with `%w` to preserve chains
- [Concurrency](references/concurrency.md) — passing context through goroutines

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend log/slog with structured fields and avoid log.Printf, satisfying all rubric criteria. Answer A is more comprehensive and idiomatic, covering ErrorContext with context propagation, LogAttrs for zero-allocation hot paths, slog.Group for nested fields, and important conventions like logging at call stack boundaries and library code patterns. Answer B is solid but slightly less complete, though it does cover all the core requirements cleanly.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses log/slog | tie |
| shows a slog call with structured fields | skill |
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

Since **Go 1.21**, the standard library includes `log/slog`, which is now the idiomatic choice. No third-party library needed.

## Basic Usage

```go
import "log/slog"

slog.Error("failed to process payment",
    "user_id", userID,
    "request_id", reqID,
    "err", err,
)
```

## Production Setup (JSON Output)

In `main()`, set a JSON handler as the default:

```go
func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)

    // ... rest of app
}
```

Output:
```json
{"time":"2024-01-15T10:30:00Z","level":"ERROR","msg":"failed to process payment","user_id":"u_123","request_id":"r_abc","err":"insufficient funds"}
```

## Type-Safe Attributes (Slightly Faster)

Use `slog.String`, `slog.Int`, `slog.Any` to avoid runtime type inspection:

```go
slog.Error("failed to process payment",
    slog.String("user_id", userID),
    slog.String("request_id", reqID),
    slog.Any("err", err),
)
```

## Carrying Context Across Calls

Build a child logger with persistent fields and pass it down (or stash in `context.Context`):

```go
func handleRequest(ctx context.Context, reqID, userID string) {
    log := slog.With(
        "request_id", reqID,
        "user_id", userID,
    )

    log.Info("starting request")

    if err := doWork(); err != nil {
        log.Error("work failed", "err", err)
        return
    }
}
```

## Context-Aware Logging

`slog.ErrorContext` (and `InfoContext`, etc.) pass a `context.Context` to the handler — useful if you write a custom handler that extracts trace IDs from context:

```go
slog.ErrorContext(ctx, "db query failed",
    "query", "SELECT ...",
    "err", err,
)
```

## Tips

- **Use a consistent key for errors** — `"err"` or `"error"`. Pick one team-wide.
- **Don't log secrets**; implement `slog.LogValuer` on sensitive types to redact them.
- **Group related fields** with `slog.Group("http", slog.Int("status", 500), ...)`.
- For very hot paths, prefer the typed helpers (`slog.String`, etc.) over the `key, value` variadic form.

Before Go 1.21, `zap` and `zerolog` were the go-to choices and remain great if you need extreme performance, but for most services `slog` is now the idiomatic default.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Modern Idiomatic Structured Error Logging in Go

Since Go 1.21, the answer is **`log/slog`** — it's in the standard library, structured/leveled, and context-aware. No third-party logger needed for most cases.

## The Basic Pattern

```go
import "log/slog"

slog.ErrorContext(ctx, "failed to charge customer",
    "err", err,
    "user_id", userID,
    "request_id", reqID,
)
```

Key points:
- **`ErrorContext`** (not plain `Error`) — passes `ctx` so handlers can extract trace IDs, deadlines, etc.
- **First arg is a constant message**, not a formatted string. Variable data goes in attributes so log aggregators can group/filter.
- **Key-value pairs** after the message become structured fields.

## Production Setup: JSON Handler

In `main`, install a JSON handler once so all output is machine-parseable:

```go
func main() {
    h := slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
        Level:     slog.LevelInfo,
        AddSource: true, // includes file:line
    })
    slog.SetDefault(slog.New(h))

    // ... rest of program
}
```

Output looks like:
```json
{"time":"2025-01-15T10:23:45Z","level":"ERROR","source":{...},"msg":"failed to charge customer","err":"card declined: insufficient_funds","user_id":"u_123","request_id":"r_abc"}
```

For local development, swap in `slog.NewTextHandler` for human-readable output.

## Typed Attributes (Faster, Type-Safe)

The `key, value` form is convenient but allocates and isn't type-checked. For hot paths or shared helpers, use typed `slog.Attr`:

```go
slog.LogAttrs(ctx, slog.LevelError, "failed to charge customer",
    slog.String("err", err.Error()),
    slog.String("user_id", userID),
    slog.String("request_id", reqID),
    slog.Int("amount_cents", amount),
)
```

`LogAttrs` is the lowest-allocation entry point.

## Carrying Request-Scoped Fields

Don't pass `request_id` and `user_id` into every call site. Build a child logger once per request and propagate it:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    log := slog.Default().With(
        "request_id", r.Header.Get("X-Request-ID"),
        "user_id", currentUserID(r),
    )
    ctx := withLogger(r.Context(), log) // your own helper

    if err := chargeCustomer(ctx, ...); err != nil {
        log.ErrorContext(ctx, "failed to charge customer", "err", err)
        http.Error(w, "internal error", 500)
        return
    }
}
```

Now every log line in that request automatically carries `request_id` and `user_id`.

## Group Related Fields

Use `slog.Group` to nest related attributes:

```go
slog.ErrorContext(ctx, "payment failed",
    "err", err,
    slog.Group("payment",
        "amount_cents", 1999,
        "currency", "USD",
        "processor", "stripe",
    ),
)
```

JSON output: `"payment": {"amount_cents": 1999, "currency": "USD", ...}`.

## Important Conventions

- **Log errors at the top of the call stack, not at every layer.** Lower layers should `return fmt.Errorf("charge customer %s: %w", id, err)` to add context. Only the handler/main loop logs.
- **Don't log AND return** the same error — pick one. Double-logging clutters output.
- **Library code should never call `slog.Default()`** directly. Accept a `*slog.Logger` (or pull one from `ctx`) so the application controls output.
- **`"err"` is the conventional key** for error values. Some teams use `"error"` — pick one and be consistent.
- **Constant `msg`, variable attrs.** Bad: `slog.Error(fmt.Sprintf("user %s failed", id))`. Good: `slog.Error("user operation failed", "user_id", id)`.

## Putting It Together

```go
func ChargeCustomer(ctx context.Context, log *slog.Logger, userID string, cents int) error {
    if err := stripe.Charge(ctx, userID, cents); err != nil {
        // Wrap with context, return — don't log here.
        return fmt.Errorf("stripe charge user=%s amount=%d: %w", userID, cents, err)
    }
    log.InfoContext(ctx, "charge succeeded", "user_id", userID, "amount_cents", cents)
    return nil
}

// At the edge (HTTP handler, worker loop, main):
if err := ChargeCustomer(ctx, log, uid, 1999); err != nil {
    log.ErrorContext(ctx, "charge failed", "err", err, "user_id", uid)
    // ... return error response
}
```

This gives you wrapped errors with full call-chain context (via `%w`) plus a single structured log entry at the boundary — the modern Go idiom.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer A uses the standard library's `cmp.Ordered` constraint (available since Go 1.21), which is the most idiomatic modern approach and avoids the need to manually enumerate types. Both answers correctly use generics syntax and avoid interface{}/reflect, but Answer A's use of `cmp.Ordered` is cleaner and more maintainable than Answer B's manual union constraint. Answer A also provides more useful context about the built-in `min` function.

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

<details><summary>sonnet: baseline answer</summary>

## Generic Min Function in Go

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

// Min returns the smaller of two values for any numeric type
func Min[T Number](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(3, 5))           // int:     3
	fmt.Println(Min(3.14, 2.72))     // float64: 2.72
	fmt.Println(Min(int64(10), 20))  // int64:   10
	fmt.Println(Min(uint(7), 2))     // uint:    2
}
```

### Key Points

| Feature | Description |
|---|---|
| `[T Number]` | Declares a type parameter `T` constrained to `Number` |
| `~int` | The `~` allows custom types with underlying type `int` (e.g. `type MyInt int`) |
| Type inference | Go infers `T` from the arguments, so no explicit type needed at call site |

### Using `golang.org/x/exp/constraints` (Alternative)

Instead of defining your own constraint, you can use the official experimental package:

```go
import "golang.org/x/exp/constraints"

func Min[T constraints.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

> **Note:** As of Go 1.21, `min` and `max` are built-in functions, so you may not need to define this yourself in newer projects.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's an idiomatic generic `Min` using a type constraint:

```go
package mathutil

import "cmp"

// Min returns the smaller of a and b.
func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

**How it works:**

- `cmp.Ordered` is a constraint from the standard library (Go 1.21+) that covers all integer types, float types, and `string` — anything that supports `<`, `>`, `<=`, `>=`.
- The type parameter `[T cmp.Ordered]` lets the compiler infer `T` from the arguments, so call sites are clean.

**Usage:**

```go
Min(3, 5)        // 3  (int)
Min(3.14, 2.72)  // 2.72  (float64)
Min("b", "a")    // "a"  (string)
```

**Before you write this yourself — check the stdlib first:**

- Go 1.21+ ships [`min` and `max` as built-in functions](https://go.dev/ref/spec#Min_and_max), so in most cases you don't need to write this at all:
  ```go
  min(3, 5)       // built-in, no import needed
  min(3.14, 2.72) // works for any cmp.Ordered type
  ```
- The `cmp` package also provides [`cmp.Compare`](https://pkg.go.dev/cmp#Compare) for three-way comparison, and [`slices.Min`](https://pkg.go.dev/slices#Min) / [`slices.Max`](https://pkg.go.dev/slices#Max) for slices.

Write the generic version above when you need it in an older codebase (pre-1.21), or as a building block for a more complex generic utility.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use generics with an Ordered constraint and avoid interface{}/reflect. Answer A is slightly better because it leads with the stdlib `cmp.Ordered` (Go 1.21+) which requires no external dependency, then falls back to `golang.org/x/exp/constraints` for older versions — a more complete and modern recommendation. Answer B leads with the external dependency and only shows the custom constraint as an alternative, missing the opportunity to highlight the now-standard `cmp.Ordered`.

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

Here's a solution using **generics** (Go 1.18+):

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

## Usage Example

```go
package main

import (
	"fmt"
	"golang.org/x/exp/constraints"
)

func Min[T constraints.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(5, 3))           // 3
	fmt.Println(Min(3.14, 2.71))     // 2.71
	fmt.Println(Min(int64(100), int64(50))) // 50
	fmt.Println(Min("apple", "zebra")) // apple
}
```

## Alternative: Without External Dependencies

If you want to avoid the `golang.org/x/exp/constraints` import, you can define your own constraint:

```go
package main

import "fmt"

// Ordered is a constraint for types that support comparison operators
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

func main() {
	fmt.Println(Min(5, 3))           // 3
	fmt.Println(Min(3.14, 2.71))     // 2.71
	fmt.Println(Min("apple", "zebra")) // apple
}
```

## Key Points

- **Generics** (Go 1.18+) allow a single function to work with any numeric type
- `constraints.Ordered` includes all comparable numeric types and strings
- The `~` operator in the custom constraint allows both the base type and any type derived from it
- Simple and efficient with no runtime overhead

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

- **`cmp.Ordered` constraint** (stdlib, Go 1.21+) — permits any type that supports `<`, `>`, `==` comparisons: `int`, `int64`, `float64`, `string`, `uint`, etc.
- **Type parameter `[T cmp.Ordered]`** — the compiler infers `T` from the arguments, so you don't write `Min[int](3, 5)`.
- **No `interface{}`** — type-safe, no reflection, zero runtime overhead.
- **Consistent with stdlib** — `slices.Min`, `maps.Min` use the same pattern.

## If You Need Go < 1.21

Use `constraints.Ordered` from `golang.org/x/exp/constraints`:

```go
import "golang.org/x/exp/constraints"

func Min[T constraints.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

## Avoid

❌ **Don't use `interface{}`** — loses type safety and requires reflection:
```go
func Min(a, b interface{}) interface{} { /* ... */ } // No.
```

❌ **Don't write separate functions** — generics exist for this:
```go
func MinInt(a, b int) int { /* ... */ }
func MinFloat64(a, b float64) float64 { /* ... */ } // Repetitive.
```

The generic version is the modern, idiomatic Go solution.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use generics with an Ordered constraint and avoid interface{}/reflect. Answer A is slightly more idiomatic for modern Go by using the stdlib `cmp.Ordered` (Go 1.21+) rather than the external `golang.org/x/exp/constraints` package, avoiding an unnecessary dependency. Answer A also includes a table-driven test and more thorough documentation including the NaN caveat, making it more complete and production-ready.

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

<details><summary>opus: baseline answer</summary>

# Generic Min Function in Go

Here's a generic `Min` function using Go's type constraints (Go 1.18+):

```go
package main

import (
	"fmt"
	"golang.org/x/exp/constraints"
)

// Min returns the smaller of two values of any ordered type.
func Min[T constraints.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Min(3, 5))           // 3
	fmt.Println(Min(3.14, 2.71))     // 2.71
	fmt.Println(Min(int64(100), int64(50))) // 50
	fmt.Println(Min("apple", "banana"))     // apple (also works for strings!)
}
```

## If you don't want the external dependency

You can define the constraint yourself:

```go
package main

import "fmt"

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

func main() {
	fmt.Println(Min(3, 5))       // 3
	fmt.Println(Min(3.14, 2.71)) // 2.71
}
```

## Note: Go 1.21+ Built-in

If you're on **Go 1.21 or later**, you don't need to write this yourself — the standard library already provides [`min`](https://pkg.go.dev/builtin#min) as a built-in:

```go
fmt.Println(min(3, 5))       // 3
fmt.Println(min(3.14, 2.71)) // 2.71
fmt.Println(min(1, 2, 3, 4)) // 1 (variadic!)
```

The `~` in the custom constraint means "any type whose underlying type is this," so it also works with custom types like `type MyInt int`.

</details>

<details><summary>opus: skill-loaded answer</summary>

Here's an idiomatic generic `Min` function:

```go
package numeric

import "cmp"

// Min returns the smaller of a and b.
// For floating-point types, the result is unspecified if either argument is NaN.
func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}
```

## Notes

- **Use `cmp.Ordered`** (Go 1.21+) as the constraint. It covers all integer, float, and string types — anything that supports `<`. This is preferable to defining your own constraint or pulling in `golang.org/x/exp/constraints`.
- **Stdlib already has this**: as of Go 1.21, `min(a, b)` is a built-in that works on any ordered type, and `cmp.Or` / `min` cover most cases. Prefer the built-in unless you need a function value (e.g., to pass to `slices.Reduce`-style code) or a named export for your API.
- **NaN caveat**: any comparison with NaN is false, so `Min(NaN, 1.0)` returns `1.0` and `Min(1.0, NaN)` returns `NaN`. The doc comment flags this. If you need NaN-aware behavior, use `math.Min` for `float64`.
- **Value receiver / no pointer**: `T` may be a small numeric type; copying is cheaper than indirection.

### If you need it as a callable value

```go
var MinInt = Min[int]  // func(int, int) int
```

### Test (table-driven)

```go
func TestMin(t *testing.T) {
	tests := []struct {
		name     string
		a, b, want int
	}{
		{"a smaller", 1, 2, 1},
		{"b smaller", 5, 3, 3},
		{"equal", 4, 4, 4},
		{"negatives", -2, -1, -2},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Min(tt.a, tt.b); got != tt.want {
				t.Errorf("Min(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.want)
			}
		})
	}
}
```

</details>

---

### `context-timeout-cancellation`

**Prompt**

```
I have a Go handler that does two things in sequence: an HTTP call
to an upstream API, then a database query. If the whole handler
takes more than 5 seconds I want to give up and return an error,
and I don't want either of those calls to keep running after that.
What's the right way to set this up?
```

**Judge focus:** The better answer derives a single deadline-bearing context with
context.WithTimeout and threads it into BOTH the HTTP request and
the DB call so cancellation propagates to each. It does not rely
on time.After races or per-call ad-hoc timeouts.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly implement all four rubric criteria: context.WithTimeout with defer cancel, threading ctx into the HTTP request via http.NewRequestWithContext, and threading ctx into the DB call via QueryRowContext. Both derive from r.Context(), explain the shared budget concept, and warn against http.DefaultClient. The differences are stylistic — Answer A uses a cleaner separation with a process() helper and slightly cleaner error handling at the handler level, while Answer B includes a helpful ASCII diagram and a summary table, but also has a minor issue of checking errors.Is for context errors inside callUpstream where the HTTP client wraps the error in url.Error (making the check unreliable there). Neither answer has a clear overall advantage.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.WithTimeout (or WithDeadline) | tie |
| defers cancel | tie |
| threads ctx into the HTTP request | tie |
| threads ctx into the DB call | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.WithTimeout (or WithDeadline) | ✓ | `context.WithTimeout` |
| defers cancel | ✓ | `defer cancel(` |
| threads ctx into the HTTP request | ✓ | `http.NewRequestWithContext` |
| threads ctx into the DB call | ✓ | `QueryRowContext` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.WithTimeout (or WithDeadline) | ✓ | `context.WithTimeout` |
| defers cancel | ✓ | `defer cancel(` |
| threads ctx into the HTTP request | ✓ | `http.NewRequestWithContext` |
| threads ctx into the DB call | ✓ | `QueryContext` |

<details><summary>sonnet: baseline answer</summary>

## Context-Based Timeout in Go

The right approach is to use `context.WithTimeout` and pass that context through to both the HTTP client and the database query. Both the standard `net/http` client and `database/sql` respect context cancellation natively.

### Complete Example

```go
package main

import (
    "context"
    "database/sql"
    "encoding/json"
    "errors"
    "fmt"
    "net/http"
    "time"

    _ "github.com/lib/pq"
)

type Server struct {
    db         *sql.DB
    httpClient *http.Client
}

func NewServer(db *sql.DB) *Server {
    return &Server{
        db: db,
        // Do NOT use http.DefaultClient — it has no timeout.
        // This transport timeout is a per-attempt safety net,
        // but the context will still cancel it early if needed.
        httpClient: &http.Client{
            Timeout: 10 * time.Second,
        },
    }
}

func (s *Server) Handler(w http.ResponseWriter, r *http.Request) {
    // Derive a child context from the request context.
    // This means the timeout also fires if the *client* disconnects early.
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel() // Always call cancel to free resources, even on success.

    // --- Step 1: upstream HTTP call ---
    result, err := s.callUpstream(ctx)
    if err != nil {
        writeError(w, err)
        return
    }

    // --- Step 2: database query ---
    row, err := s.queryDB(ctx, result.ID)
    if err != nil {
        writeError(w, err)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(row)
}

// callUpstream makes a context-aware HTTP request.
// The request is cancelled automatically when ctx is done.
func (s *Server) callUpstream(ctx context.Context) (*UpstreamResult, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet,
        "https://api.example.com/data", nil)
    if err != nil {
        return nil, fmt.Errorf("building upstream request: %w", err)
    }

    resp, err := s.httpClient.Do(req)
    if err != nil {
        // Distinguish a timeout/cancellation from other errors.
        if errors.Is(err, context.DeadlineExceeded) ||
            errors.Is(err, context.Canceled) {
            return nil, fmt.Errorf("upstream call timed out: %w", err)
        }
        return nil, fmt.Errorf("upstream call failed: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("upstream returned status %d", resp.StatusCode)
    }

    var result UpstreamResult
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("decoding upstream response: %w", err)
    }
    return &result, nil
}

// queryDB runs a context-aware database query.
// The query is cancelled automatically when ctx is done.
func (s *Server) queryDB(ctx context.Context, id string) (*DBRow, error) {
    var row DBRow
    err := s.db.QueryRowContext(ctx,
        `SELECT id, value FROM items WHERE id = $1`, id,
    ).Scan(&row.ID, &row.Value)

    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) ||
            errors.Is(err, context.Canceled) {
            return nil, fmt.Errorf("db query timed out: %w", err)
        }
        if errors.Is(err, sql.ErrNoRows) {
            return nil, fmt.Errorf("item not found: %w", err)
        }
        return nil, fmt.Errorf("db query failed: %w", err)
    }
    return &row, nil
}

func writeError(w http.ResponseWriter, err error) {
    if errors.Is(err, context.DeadlineExceeded) ||
        errors.Is(err, context.Canceled) {
        http.Error(w, "request timed out", http.StatusGatewayTimeout)
        return
    }
    http.Error(w, err.Error(), http.StatusInternalServerError)
}

type UpstreamResult struct {
    ID string `json:"id"`
}

type DBRow struct {
    ID    string
    Value string
}
```

### How Cancellation Actually Works

```
r.Context()  ←── cancelled if client disconnects
     │
     ▼
context.WithTimeout(5s)  ←── cancelled after 5s OR if parent cancels
     │
     ├──▶ http.NewRequestWithContext(ctx)
     │         The HTTP client aborts the in-flight TCP connection
     │
     └──▶ db.QueryRowContext(ctx)
               The db driver cancels the in-flight query
```

### Key Rules to Follow

| Rule | Why |
|---|---|
| Always `defer cancel()` | Prevents a context leak even on the happy path |
| Use `r.Context()` as the parent | Handler also stops if the client disconnects |
| Use `http.NewRequestWithContext`, not `req.WithContext` | The former is the modern API (Go 1.13+) |
| Never use `http.DefaultClient` without a timeout | It will hang forever independently of your context |
| Check `errors.Is(err, context.DeadlineExceeded)` | Gives you accurate 504 vs 500 responses |

### What "cancelled" means for each call

- **HTTP client** — the underlying TCP connection is aborted; the goroutine inside the transport unblocks and returns an error
- **`database/sql`** — sends a cancellation to the database server (e.g. PostgreSQL `CancelRequest`); the query stops executing server-side, not just client-side

The 5-second budget is **shared** across both calls, which is exactly what you want — there's no way for the two steps together to exceed it.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The standard approach is a single `context.WithTimeout` at the handler boundary. Both the HTTP client and the database driver honour `context.Context` cancellation, so the same context threads through both calls and cancels them automatically when the deadline fires.

## The pattern

```go
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel() // always release resources, even on the happy path

    result, err := h.process(ctx)
    if err != nil {
        // Distinguish a timeout/cancellation from other errors.
        if errors.Is(err, context.DeadlineExceeded) ||
            errors.Is(err, context.Canceled) {
            http.Error(w, "request timed out", http.StatusGatewayTimeout)
            return
        }
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(result)
}

func (h *Handler) process(ctx context.Context) (*Result, error) {
    // Step 1: upstream HTTP call — uses the same deadline.
    apiData, err := h.callUpstream(ctx)
    if err != nil {
        return nil, fmt.Errorf("upstream call: %w", err)
    }

    // Step 2: database query — uses whatever time is left.
    row, err := h.db.QueryRowContext(ctx, "SELECT ...", apiData.ID)
    if err != nil {
        return nil, fmt.Errorf("db query: %w", err)
    }
    // ...scan row...
    return result, nil
}

func (h *Handler) callUpstream(ctx context.Context) (*APIData, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, h.upstreamURL, nil)
    if err != nil {
        return nil, fmt.Errorf("build request: %w", err)
    }

    resp, err := h.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("do request: %w", err) // wraps url.Error which wraps ctx.Err()
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("upstream status %d", resp.StatusCode)
    }

    var data APIData
    if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
        return nil, fmt.Errorf("decode response: %w", err)
    }
    return &data, nil
}
```

## Why each piece matters

**`context.WithTimeout` at the handler boundary, not inside the helpers**  
The 5-second clock starts once and is shared. If the HTTP call takes 4.9 s, the database query gets only 0.1 s — which is exactly what you want. Creating separate timeouts per call would allow 5 + 5 = 10 s of total wall time.

**`defer cancel()`**  
`WithTimeout` allocates a timer goroutine. `cancel()` releases it immediately on the happy path instead of waiting for the deadline to fire. Forgetting this is a goroutine/resource leak that `go vet` and `golangci-lint` (the `contextcheck` linter) will flag.

**`http.NewRequestWithContext` instead of `http.NewRequest`**  
This is the only way to attach a context to an outbound HTTP request. The client will abort the in-flight TCP connection as soon as the context is cancelled — no lingering goroutine waiting on a read.

**`db.QueryRowContext` / `db.QueryContext`**  
The `database/sql` package's `*Context` variants cancel the query at the driver level. Without them the query runs to completion regardless of your deadline.

**`fmt.Errorf("...: %w", err)` at each layer**  
Wrapping with `%w` preserves the error chain so `errors.Is(err, context.DeadlineExceeded)` still returns `true` even after the error has been annotated with call-site context. A bare `return err` would work too, but you'd lose the "where did this fail?" information in logs.

## One thing to watch: the incoming request's context

`context.WithTimeout(r.Context(), ...)` derives from the request's own context, which the HTTP server cancels when the client disconnects. That means:

- If the client drops the connection before your 5 s are up, both calls are cancelled immediately — no wasted work.
- If your load balancer has its own timeout shorter than 5 s, that fires first.

This is almost always what you want. If you ever need the work to *outlive* the request (e.g. fire-and-forget background jobs), you'd derive from `context.Background()` instead — but then you need a different mechanism to bound that work's lifetime.

## Injecting the HTTP client

Notice `h.httpClient` is a field rather than `http.DefaultClient`. This matters for two reasons:

1. `http.DefaultClient` has no timeout of its own; a misbehaving server can hold a connection open indefinitely even with a context (the context cancels the *request*, but a pre-existing idle connection can still tie up resources).
2. In tests you can swap in a `*http.Client` backed by `httptest` without any monkey-patching.

```go
type Handler struct {
    httpClient  *http.Client
    db          *sql.DB
    upstreamURL string
}

func NewHandler(db *sql.DB, upstreamURL string) *Handler {
    return &Handler{
        httpClient: &http.Client{
            // Transport-level timeout as a safety net beneath the context.
            Timeout: 10 * time.Second,
        },
        db:          db,
        upstreamURL: upstreamURL,
    }
}
```

The transport `Timeout` is a belt-and-suspenders guard; your context deadline is still the primary control.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A has a critical bug: it calls `http.NewRequestWithContext` but never actually executes the request with an HTTP client (missing `client.Do(req)`), making the code non-functional. Answer B correctly structures the HTTP call with `h.client.Do(req)` and also provides better overall code organization, error handling with `errors.Is(err, context.DeadlineExceeded)`, and more thorough explanation of the shared deadline behavior.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.WithTimeout (or WithDeadline) | tie |
| defers cancel | tie |
| threads ctx into the HTTP request | skill |
| threads ctx into the DB call | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.WithTimeout (or WithDeadline) | ✓ | `context.WithTimeout` |
| defers cancel | ✓ | `defer cancel(` |
| threads ctx into the HTTP request | ✓ | `http.NewRequestWithContext` |
| threads ctx into the DB call | ✓ | `QueryRowContext` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.WithTimeout (or WithDeadline) | ✓ | `context.WithTimeout` |
| defers cancel | ✓ | `defer cancel(` |
| threads ctx into the HTTP request | ✓ | `http.NewRequestWithContext` |
| threads ctx into the DB call | ✓ | `QueryContext` |

<details><summary>haiku: baseline answer</summary>

# Using Context with Timeout

The right way is to use a **context with a timeout** and pass it through both calls. Here's the pattern:

```go
func MyHandler(w http.ResponseWriter, r *http.Request) {
    // Create a context with a 5-second timeout
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel()
    
    // Make HTTP call with the context
    resp, err := http.NewRequestWithContext(ctx, "GET", "https://api.example.com/data", nil)
    if err != nil {
        http.Error(w, "Upstream call failed", http.StatusGatewayTimeout)
        return
    }
    defer resp.Body.Close()
    
    // Parse response...
    
    // Make database query with the same context
    var result string
    err = db.QueryRowContext(ctx, "SELECT data FROM table WHERE id = ?", id).Scan(&result)
    if err != nil {
        http.Error(w, "Database query failed", http.StatusGatewayTimeout)
        return
    }
    
    // Return success
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(result)
}
```

## Key Points

1. **`context.WithTimeout()`** - Creates a context that cancels after 5 seconds
2. **Pass `ctx` to both calls** - Both `http.NewRequestWithContext()` and `db.QueryRowContext()` respect the timeout
3. **`defer cancel()`** - Cleans up resources (good practice, though not strictly necessary with timeout)
4. **Error handling** - Both calls will return a context deadline exceeded error if timeout is hit

## What Happens

- If the HTTP call takes >5 seconds, it's cancelled and returns an error
- If the HTTP call succeeds but the DB query would exceed 5 seconds total, it's cancelled
- The context automatically cancels any in-flight operations when the deadline passes

This is the idiomatic Go way to handle timeouts across multiple operations.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Timeout with Context Cancellation

Use `context.WithTimeout` to create a deadline, and pass that context to both the HTTP client and database query. Both will respect the cancellation and stop early.

## The Pattern

```go
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Create a context with a 5-second deadline from now.
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	// Pass ctx to both operations.
	data, err := h.fetchUpstream(ctx)
	if err != nil {
		h.handleError(w, err)
		return
	}

	err = h.storeInDB(ctx, data)
	if err != nil {
		h.handleError(w, err)
		return
	}

	w.WriteHeader(http.StatusOK)
}

func (h *Handler) fetchUpstream(ctx context.Context) (interface{}, error) {
	req, _ := http.NewRequestWithContext(ctx, "GET", "https://api.example.com/data", nil)
	resp, err := h.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("upstream call: %w", err)
	}
	defer resp.Body.Close()
	// ... parse response
	return data, nil
}

func (h *Handler) storeInDB(ctx context.Context, data interface{}) error {
	// Pass ctx to the query; it will be cancelled if the deadline expires.
	err := h.db.QueryRowContext(ctx, "INSERT INTO ...").Scan(...)
	if err != nil {
		return fmt.Errorf("store in db: %w", err)
	}
	return nil
}
```

## Why This Works

1. **`context.WithTimeout(parent, duration)`** wraps the request context and adds a deadline. When the deadline passes, the context is automatically cancelled.
2. **`defer cancel()`** stops the timer early if the handler finishes before the deadline (good practice; prevents resource leak).
3. **Both `http.Client.Do` and `database/sql` methods accept `Context`** — they check `ctx.Done()` and abort if the deadline has passed or the context is cancelled.
4. **Errors propagate cleanly** — if either call times out, you get `context.DeadlineExceeded`, which you can check with `errors.Is(err, context.DeadlineExceeded)` if you need special handling.

## Error Handling

```go
func (h *Handler) handleError(w http.ResponseWriter, err error) {
	if errors.Is(err, context.DeadlineExceeded) {
		http.Error(w, "Request timeout", http.StatusRequestTimeout)
		return
	}
	// ... other error cases
	http.Error(w, "Internal error", http.StatusInternalServerError)
}
```

## Key Points

- **Always pass `context.Context` as the first parameter** to I/O functions (`Do`, `QueryRowContext`, `QueryContext`, etc.).
- **Never store context in a struct** — it's a request-scoped value.
- **The deadline is shared** — if the upstream call takes 3 seconds, the database query has only 2 seconds left. This is the intended behavior for a total timeout.
- **Use `context.WithCancel`** if you need to cancel independently of a deadline (e.g., user closes the connection).
- **HTTP clients should have their own timeout too** — set `client.Timeout` as a safety net, but context deadlines are the primary control mechanism in handlers.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are essentially equivalent in correctness and completeness, satisfying all four rubric criteria: context.WithTimeout, defer cancel, threading ctx into the HTTP request via NewRequestWithContext, and threading ctx into the DB call via QueryRowContext. Both derive from r.Context(), explain the shared budget concept, and provide clear working code examples. Answer B is marginally more concise and adds the useful 'http.Client.Timeout as backstop' tip, while Answer A provides slightly more detailed explanation of error handling nuances. Neither has a meaningful advantage over the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses context.WithTimeout (or WithDeadline) | tie |
| defers cancel | tie |
| threads ctx into the HTTP request | tie |
| threads ctx into the DB call | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.WithTimeout (or WithDeadline) | ✓ | `context.WithTimeout` |
| defers cancel | ✓ | `defer cancel(` |
| threads ctx into the HTTP request | ✓ | `http.NewRequestWithContext` |
| threads ctx into the DB call | ✓ | `QueryContext` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses context.WithTimeout (or WithDeadline) | ✓ | `context.WithTimeout` |
| defers cancel | ✓ | `defer cancel(` |
| threads ctx into the HTTP request | ✓ | `http.NewRequestWithContext` |
| threads ctx into the DB call | ✓ | `QueryContext` |

<details><summary>opus: baseline answer</summary>

# Setting Up a Handler-Wide Timeout in Go

The idiomatic approach is to derive a `context.Context` with a timeout from the request's context, then thread that context through both calls. When the timeout fires (or the client disconnects), both operations get cancelled.

## Basic structure

```go
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel()

    apiResult, err := h.callUpstream(ctx)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            http.Error(w, "request timed out", http.StatusGatewayTimeout)
            return
        }
        http.Error(w, "upstream failed", http.StatusBadGateway)
        return
    }

    dbResult, err := h.queryDB(ctx, apiResult)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            http.Error(w, "request timed out", http.StatusGatewayTimeout)
            return
        }
        http.Error(w, "db failed", http.StatusInternalServerError)
        return
    }

    writeResponse(w, dbResult)
}
```

The `defer cancel()` is important — it releases the timer resources even if you return early due to an error, and signals downstream goroutines to stop.

## Making sure the calls actually respect the context

A timeout only helps if both calls honor cancellation. Two things to check:

**HTTP call** — use `http.NewRequestWithContext`, not `http.NewRequest`:

```go
func (h *Handler) callUpstream(ctx context.Context) (Result, error) {
    req, err := http.NewRequestWithContext(ctx, "GET", h.upstreamURL, nil)
    if err != nil {
        return Result{}, err
    }
    resp, err := h.httpClient.Do(req)
    if err != nil {
        return Result{}, err
    }
    defer resp.Body.Close()
    // ... decode
}
```

When the context is cancelled, the in-flight request is aborted and `Do` returns an error.

**DB call** — use the `Context` variants of `database/sql` methods (`QueryContext`, `ExecContext`, `QueryRowContext`):

```go
func (h *Handler) queryDB(ctx context.Context, in Result) (DBResult, error) {
    var out DBResult
    err := h.db.QueryRowContext(ctx, "SELECT ...", in.ID).Scan(&out.X)
    return out, err
}
```

Most drivers (pgx, the standard `database/sql` with a context-aware driver) will cancel the in-flight query when the context is done.

## A couple of things to be aware of

- **The 5s budget is shared.** If the HTTP call takes 4.5s, the DB call only has 500ms before it's cancelled. That's usually what you want, but if you'd rather give each step its own budget, derive a fresh `WithTimeout` per call instead.
- **Don't use `http.TimeoutHandler` for this.** It enforces a wall-clock limit on the response but doesn't cancel the request context, so your goroutines keep running. Context-based cancellation is what stops the work.
- **Distinguishing client-cancel from timeout:** both surface as `context.Canceled` / `context.DeadlineExceeded`. If you need to tell them apart for logging, check `ctx.Err()` after the call returns — `DeadlineExceeded` means your 5s fired, `Canceled` typically means the client went away.

</details>

<details><summary>opus: skill-loaded answer</summary>

Use `context.WithTimeout` derived from the request context, and pass that context through to both calls. Both `net/http` and `database/sql` honor context cancellation, so when the timeout fires (or the client disconnects), the in-flight HTTP call and DB query are cancelled too.

```go
func (h *Handler) handle(w http.ResponseWriter, r *http.Request) {
    // Derive from r.Context() so client disconnects also cancel.
    // 5s budget covers BOTH calls combined.
    ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
    defer cancel() // always; releases resources even on early return

    user, err := h.fetchUpstream(ctx, r.URL.Query().Get("id"))
    if err != nil {
        // Distinguish "we ran out of time" from other failures.
        if errors.Is(err, context.DeadlineExceeded) {
            http.Error(w, "upstream timeout", http.StatusGatewayTimeout)
            return
        }
        http.Error(w, "upstream failed", http.StatusBadGateway)
        return
    }

    record, err := h.lookupDB(ctx, user.ID)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            http.Error(w, "db timeout", http.StatusGatewayTimeout)
            return
        }
        http.Error(w, "db failed", http.StatusInternalServerError)
        return
    }

    writeJSON(w, record)
}

func (h *Handler) fetchUpstream(ctx context.Context, id string) (*User, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, h.upstreamURL+"/users/"+id, nil)
    if err != nil {
        return nil, fmt.Errorf("build upstream request: %w", err)
    }
    resp, err := h.client.Do(req) // h.client also has its own Timeout as a backstop
    if err != nil {
        return nil, fmt.Errorf("upstream call: %w", err)
    }
    defer resp.Body.Close()
    // ... decode ...
}

func (h *Handler) lookupDB(ctx context.Context, userID string) (*Record, error) {
    var rec Record
    err := h.db.QueryRowContext(ctx, "SELECT ... WHERE user_id = $1", userID).Scan(&rec.Foo, &rec.Bar)
    if err != nil {
        return nil, fmt.Errorf("db lookup for %s: %w", userID, err)
    }
    return &rec, nil
}
```

Key points:

1. **Derive from `r.Context()`, not `context.Background()`** — that way a client disconnect also cancels both calls, not just the 5s timeout.
2. **`defer cancel()` immediately** after `WithTimeout`. Even if you return early, this releases the timer. Not deferring it is a leak `go vet` will flag.
3. **One context, both calls** — the 5s is a budget for the whole handler. If the HTTP call takes 4.5s, the DB call only gets 0.5s before being cancelled. That's usually what you want.
4. **`http.NewRequestWithContext`, not `http.NewRequest`** — the latter ignores context. Same idea for `db.QueryRowContext` / `ExecContext` / `QueryContext` — never use the non-`Context` variants in a server.
5. **Check `errors.Is(err, context.DeadlineExceeded)`** to distinguish timeout from other errors. `context.Canceled` is the other one (fires on client disconnect).
6. **Keep `http.Client.Timeout` set too** as a backstop — it covers cases where context plumbing is missed somewhere down the stack. Belt and suspenders.

If you wanted independent per-call budgets instead of one shared budget (e.g., "HTTP gets 3s, DB gets 2s"), you'd derive a second `WithTimeout` from `ctx` for each call — but the shared-budget pattern above is the more common starting point.

</details>

---

### `table-driven-tests`

**Prompt**

```
I have a Go validation function `Validate(s string) error` that
rejects strings on a few different rules. I want to test it against
many inputs without copy-pasting the same setup code per test.
What's the idiomatic way to write this test?
```

**Judge focus:** The better answer shows a slice of test-case structs (a "table"),
iterated with t.Run for named subtests, rather than a sequence of
independent TestFoo functions or repeated setup blocks.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria equally well, but Answer B is more idiomatic and complete: it correctly notes that `tt := tt` is no longer needed in Go 1.22+, uses `errors.Is` as the primary approach, includes the concise `(err != nil) != tt.wantErr` idiom, and adds a valuable fuzz testing bonus. Answer A also captures the range variable with `tc := tc` as a comment but still includes it, and presents the `wantErr bool` pattern first before the more idiomatic sentinel error approach. Answer B's overall quality, correctness notes about Go versions, and additional practical content make it the stronger answer.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses t.Run for subtests | tie |
| uses a slice of structs as the table | tie |
| each case has a name field | tie |
| iterates with range | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses t.Run for subtests | ✓ | `t.Run(` |
| uses a slice of structs as the table | ✓ | `[]struct {` |
| each case has a name field | ✓ | `name    string` |
| iterates with range | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses t.Run for subtests | ✓ | `t.Run(` |
| uses a slice of structs as the table | ✓ | `[]struct {` |
| each case has a name field | ✓ | `name    string` |
| iterates with range | ✗ | |

<details><summary>sonnet: baseline answer</summary>

## Table-Driven Tests in Go

The idiomatic Go approach is **table-driven tests** — define a slice of test cases, then loop over them with `t.Run`.

### Example

```go
package mypkg_test

import (
    "testing"

    "github.com/you/mypkg"
)

func TestValidate(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        wantErr bool
    }{
        // valid inputs
        {name: "simple valid string",  input: "hello",   wantErr: false},
        {name: "empty string",         input: "",         wantErr: false},

        // invalid inputs
        {name: "too long",             input: "aaaaaaaaaaaaaaaaaaaaaaaaa", wantErr: true},
        {name: "contains digit",       input: "abc123",  wantErr: true},
        {name: "special characters",   input: "foo@bar", wantErr: true},
    }

    for _, tc := range tests {
        tc := tc // capture range variable (unnecessary in Go 1.22+)
        t.Run(tc.name, func(t *testing.T) {
            t.Parallel() // optional: run subtests concurrently

            err := mypkg.Validate(tc.input)

            if tc.wantErr && err == nil {
                t.Errorf("Validate(%q) = nil, want error", tc.input)
            }
            if !tc.wantErr && err != nil {
                t.Errorf("Validate(%q) = %v, want nil", tc.input, err)
            }
        })
    }
}
```

### Checking for a *specific* error

If your function returns distinct sentinel errors or error types, test for those explicitly rather than just `wantErr bool`:

```go
tests := []struct {
    name    string
    input   string
    wantErr error // nil means no error expected
}{
    {name: "too long",        input: "aaaaaaaaaa", wantErr: mypkg.ErrTooLong},
    {name: "invalid char",    input: "foo@bar",    wantErr: mypkg.ErrInvalidChar},
    {name: "valid",           input: "hello",      wantErr: nil},
}

for _, tc := range tests {
    t.Run(tc.name, func(t *testing.T) {
        err := mypkg.Validate(tc.input)
        if !errors.Is(err, tc.wantErr) {
            t.Errorf("Validate(%q) = %v, want %v", tc.input, err, tc.wantErr)
        }
    })
}
```

### Key points

| Practice | Reason |
|---|---|
| `t.Run(name, func)` | Each case gets its own named subtest, visible in output |
| `tc := tc` before goroutine | Avoids loop-variable capture bug (Go < 1.22) |
| `t.Parallel()` | Speeds up large test tables |
| `errors.Is` over `==` | Correctly handles wrapped errors |
| Descriptive `name` field | `go test -run TestValidate/too_long` lets you target one case |

### Running a single case

```bash
go test -run TestValidate/too_long -v
```

This pattern scales cleanly — adding a new rule means adding one struct literal to the slice, with no duplicated setup code.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The idiomatic Go approach is a **table-driven test**: define a slice of test cases as an anonymous struct, then loop over them with `t.Run` to get a named sub-test per case.

## Basic structure

```go
func TestValidate(t *testing.T) {
    t.Parallel()

    tests := []struct {
        name    string
        input   string
        wantErr error // nil means we expect success
    }{
        {
            name:    "valid input",
            input:   "hello",
            wantErr: nil,
        },
        {
            name:    "empty string",
            input:   "",
            wantErr: ErrEmpty,
        },
        {
            name:    "too long",
            input:   strings.Repeat("a", 256),
            wantErr: ErrTooLong,
        },
        {
            name:    "invalid character",
            input:   "hello!",
            wantErr: ErrInvalidChar,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel() // each sub-test runs concurrently

            err := Validate(tt.input)

            if tt.wantErr != nil {
                if !errors.Is(err, tt.wantErr) {
                    t.Errorf("Validate(%q) error = %v, want %v", tt.input, err, tt.wantErr)
                }
            } else {
                if err != nil {
                    t.Errorf("Validate(%q) unexpected error: %v", tt.input, err)
                }
            }
        })
    }
}
```

## Why each piece matters

**`tt := tt` is no longer needed (Go 1.22+).** The loop variable capture bug was fixed — each iteration gets its own `tt`. If you're on an older version, add `tt := tt` before the `t.Run` call.

**`errors.Is` instead of `==` or string matching.** This works correctly when your function wraps errors with `%w`, and it's the only way to match sentinel errors through a chain.

**`t.Parallel()` on both the outer test and each sub-test.** The outer call lets this test run concurrently with other top-level tests. The inner call lets sub-tests run concurrently with each other. If `Validate` touches shared state, drop the inner one.

**Named sub-tests via `t.Run`.** Failures are reported as `TestValidate/empty_string`, which is unambiguous and runnable in isolation:
```
go test -run TestValidate/empty_string
```

## When you only care "error or not"

If your rules produce a single error type and you just need pass/fail, simplify the case struct:

```go
tests := []struct {
    name    string
    input   string
    wantErr bool
}{
    {"valid", "hello", false},
    {"empty", "", true},
    {"too long", strings.Repeat("a", 256), true},
}

for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        err := Validate(tt.input)
        if (err != nil) != tt.wantErr {
            t.Errorf("Validate(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
        }
    })
}
```

## Bonus: fuzz testing for free

Once you have the table, you can add a fuzz test that explores inputs beyond what you thought of:

```go
func FuzzValidate(f *testing.F) {
    // Seed corpus from your table-driven cases
    for _, seed := range []string{"hello", "", "hello!", strings.Repeat("a", 256)} {
        f.Add(seed)
    }

    f.Fuzz(func(t *testing.T, s string) {
        // The contract: Validate must never panic, regardless of input.
        // If it returns an error, it must be one of the known sentinels.
        err := Validate(s)
        if err != nil &&
            !errors.Is(err, ErrEmpty) &&
            !errors.Is(err, ErrTooLong) &&
            !errors.Is(err, ErrInvalidChar) {
            t.Errorf("Validate(%q) returned unexpected error: %v", s, err)
        }
    })
}
```

Run with `go test -fuzz=FuzzValidate`. The fuzzer will find edge cases (Unicode boundaries, null bytes, etc.) that manual tables rarely cover.

## Quick reference

| Need | Tool |
|---|---|
| Many inputs, same logic | Table-driven test with `t.Run` |
| Specific error identity | `errors.Is(err, ErrSentinel)` |
| Specific error fields | `errors.As(err, &target)` |
| Unknown-unknown inputs | `f.Fuzz` seeded from your table |
| Isolate one failing case | `go test -run TestValidate/case_name` |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria equally well, but Answer A provides a more thorough and educational response with additional context like the `(err != nil) != wantErr` idiom explanation, parallel test guidance, `errors.Is` usage, and explicit anti-patterns to avoid. Answer B is cleaner and more concise, which has merit, but Answer A is more comprehensive without being incorrect.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses t.Run for subtests | tie |
| uses a slice of structs as the table | tie |
| each case has a name field | tie |
| iterates with range | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses t.Run for subtests | ✓ | `t.Run(` |
| uses a slice of structs as the table | ✓ | `[]struct {` |
| each case has a name field | ✓ | `name    string` |
| iterates with range | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses t.Run for subtests | ✓ | `t.Run(` |
| uses a slice of structs as the table | ✓ | `[]struct {` |
| each case has a name field | ✓ | `name    string` |
| iterates with range | ✗ | |

<details><summary>haiku: baseline answer</summary>

# Idiomatic Go Table-Driven Tests

The idiomatic way is to use **table-driven tests**. Here's the pattern:

```go
func TestValidate(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		wantErr bool
	}{
		{
			name:    "valid input",
			input:   "hello",
			wantErr: false,
		},
		{
			name:    "empty string",
			input:   "",
			wantErr: true,
		},
		{
			name:    "too long",
			input:   strings.Repeat("a", 1000),
			wantErr: true,
		},
		{
			name:    "invalid characters",
			input:   "hello@world",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := Validate(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
```

## Key Benefits

- **No copy-paste**: Single test loop handles all cases
- **Clear organization**: Each test case is a struct with descriptive names
- **Better output**: `t.Run()` creates subtests with individual pass/fail reporting
- **Easy to add cases**: Just add another struct to the slice
- **Readable failures**: Test names appear in output (e.g., `TestValidate/empty_string`)

## If You Need Error Messages

If you want to verify specific error messages:

```go
tests := []struct {
	name      string
	input     string
	wantErr   bool
	errString string // optional
}{
	{
		name:      "empty string",
		input:     "",
		wantErr:   true,
		errString: "cannot be empty",
	},
	// ...
}

for _, tt := range tests {
	t.Run(tt.name, func(t *testing.T) {
		err := Validate(tt.input)
		if (err != nil) != tt.wantErr {
			t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
		}
		if tt.wantErr && !strings.Contains(err.Error(), tt.errString) {
			t.Errorf("Validate() error = %v, want substring %q", err, tt.errString)
		}
	})
}
```

This is the standard Go testing pattern used throughout the standard library.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Table-Driven Tests with `t.Run`

The idiomatic Go pattern is a **table-driven test** combined with `t.Run` for clarity and parallelism. Here's the structure:

```go
func TestValidate(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		wantErr bool
		errType error // optional: for errors.Is checks
	}{
		{
			name:    "valid lowercase",
			input:   "hello",
			wantErr: false,
		},
		{
			name:    "valid with numbers",
			input:   "hello123",
			wantErr: false,
		},
		{
			name:    "empty string rejected",
			input:   "",
			wantErr: true,
			errType: ErrEmpty, // if you have a sentinel
		},
		{
			name:    "uppercase rejected",
			input:   "HELLO",
			wantErr: true,
			errType: ErrUppercase,
		},
		{
			name:    "special chars rejected",
			input:   "hello!",
			wantErr: true,
			errType: ErrInvalidChar,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := Validate(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			}
			if tt.errType != nil && !errors.Is(err, tt.errType) {
				t.Errorf("Validate(%q) error = %v, want %v", tt.input, err, tt.errType)
			}
		})
	}
}
```

## Why This Pattern

| Benefit | How |
|---|---|
| **No copy-paste setup** | Single loop; each case is just data |
| **Clear test names** | `TestValidate/valid_lowercase` in output; `-run` filters easily |
| **Parallelizable** | Add `t.Parallel()` at the top of the inner function; tests run concurrently |
| **Easy to add cases** | Append a row; no new function needed |
| **Readable failure output** | Test name + `t.Errorf` message pinpoints the exact case |

## Key Patterns

**1. Use `t.Run` for subtests** — each row becomes a named subtest:
```go
t.Run(tt.name, func(t *testing.T) {
	// test body
})
```

**2. Parallel execution** — add this if your test has no shared state:
```go
t.Run(tt.name, func(t *testing.T) {
	t.Parallel() // safe if Validate is pure
	// ...
})
```

**3. Check error presence with `(err != nil) != wantErr`** — this idiom handles both "want error" and "want no error":
- If `wantErr=true` and `err != nil`: `(true) != true` → `false` → pass ✓
- If `wantErr=true` and `err == nil`: `(false) != true` → `true` → fail ✗
- If `wantErr=false` and `err == nil`: `(false) != false` → `false` → pass ✓
- If `wantErr=false` and `err != nil`: `(true) != false` → `true` → fail ✗

**4. Use `errors.Is` for sentinel checks** — if your function returns typed errors:
```go
if tt.errType != nil && !errors.Is(err, tt.errType) {
	t.Errorf("...")
}
```

## Variant: Inline Error Checking

If you want to be more explicit about error types without a separate field:

```go
func TestValidate(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		checkErr  func(error) bool
	}{
		{
			name:  "valid",
			input: "hello",
			checkErr: func(err error) bool { return err == nil },
		},
		{
			name:  "empty rejected",
			input: "",
			checkErr: func(err error) bool { return errors.Is(err, ErrEmpty) },
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := Validate(tt.input)
			if !tt.checkErr(err) {
				t.Errorf("Validate(%q) error = %v, check failed", tt.input, err)
			}
		})
	}
}
```

This is more verbose but lets you express complex error conditions (e.g., "error wraps both X and Y").

## Avoid

❌ **Don't** create a separate test function per case — defeats the purpose:
```go
// Bad: repetitive, hard to add cases
func TestValidateEmpty(t *testing.T) { ... }
func TestValidateUppercase(t *testing.T) { ... }
func TestValidateLowercase(t *testing.T) { ... }
```

❌ **Don't** use `t.Fatal` in a loop — stops the whole test on first failure:
```go
// Bad: one failure stops all remaining cases
for _, tt := range tests {
	if err := Validate(tt.input); err != nil {
		t.Fatal(err) // ✗
	}
}
```
Use `t.Errorf` instead so all cases run.

---

**Run with `-v` to see subtest names:**
```bash
go test -v
# TestValidate/valid_lowercase
# TestValidate/empty_string_rejected
# TestValidate/uppercase_rejected
# ...
```

**Run a single subtest:**
```bash
go test -run TestValidate/empty
```

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers satisfy all four rubric criteria, but Answer A is more complete and idiomatic overall. It uses `errors.Is` as the primary comparison approach (rather than a boolean flag), includes both happy-path and error cases, and provides more thorough guidance on edge cases and variants. Answer B's basic pattern uses a `wantErr bool` which is less precise, though it does show the sentinel approach as a secondary option.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses t.Run for subtests | tie |
| uses a slice of structs as the table | tie |
| each case has a name field | tie |
| iterates with range | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses t.Run for subtests | ✓ | `t.Run(` |
| uses a slice of structs as the table | ✓ | `[]struct {` |
| each case has a name field | ✓ | `name    string` |
| iterates with range | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses t.Run for subtests | ✓ | `t.Run(` |
| uses a slice of structs as the table | ✓ | `[]struct {` |
| each case has a name field | ✓ | `name    string` |
| iterates with range | ✗ | |

<details><summary>opus: baseline answer</summary>

# Table-Driven Tests in Go

The idiomatic Go approach is **table-driven tests** combined with `t.Run` for subtests. This gives you one setup, many cases, and clear failure output.

## Basic Pattern

```go
func TestValidate(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        wantErr bool
    }{
        {"empty string", "", true},
        {"too short", "ab", true},
        {"valid input", "hello", false},
        {"contains spaces", "hi there", true},
        {"too long", strings.Repeat("a", 1000), true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := Validate(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("Validate(%q) error = %v, wantErr %v",
                    tt.input, err, tt.wantErr)
            }
        })
    }
}
```

## Why This Is Idiomatic

- **One setup, many cases**: All inputs and expectations live in one slice.
- **Subtests via `t.Run`**: Each case shows up as `TestValidate/empty_string` in output, and you can run a single case with `go test -run TestValidate/empty_string`.
- **Easy to extend**: Adding a case is one line.
- **Parallel-friendly**: You can add `t.Parallel()` inside the subtest.

## Checking Specific Errors

If you care *which* error is returned (recommended), use sentinel errors and `errors.Is`:

```go
var (
    ErrTooShort   = errors.New("too short")
    ErrBadChars   = errors.New("invalid characters")
)

tests := []struct {
    name    string
    input   string
    wantErr error // nil means no error expected
}{
    {"too short", "ab", ErrTooShort},
    {"bad chars", "hi!", ErrBadChars},
    {"valid",     "hello", nil},
}

for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        err := Validate(tt.input)
        if !errors.Is(err, tt.wantErr) {
            t.Errorf("Validate(%q) = %v, want %v", tt.input, err, tt.wantErr)
        }
    })
}
```

## Optional: Parallel Execution

```go
for _, tt := range tests {
    tt := tt // capture range variable (not needed in Go 1.22+)
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        // ...
    })
}
```

This pattern scales from 3 cases to 300 without changing structure, which is why you'll see it throughout the Go standard library (e.g., `net/url`, `strconv`).

</details>

<details><summary>opus: skill-loaded answer</summary>

# Table-Driven Tests

This is the canonical Go testing pattern. Define a slice of test cases, then loop with `t.Run` to get one subtest per case.

```go
func TestValidate(t *testing.T) {
    t.Parallel()

    tests := []struct {
        name    string
        input   string
        wantErr error // sentinel to match with errors.Is, or nil
    }{
        {"empty string", "", ErrEmpty},
        {"too long", strings.Repeat("a", 101), ErrTooLong},
        {"contains null byte", "hi\x00there", ErrInvalidChar},
        {"valid simple", "hello", nil},
        {"valid unicode", "héllo", nil},
        {"valid max length", strings.Repeat("a", 100), nil},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()

            err := Validate(tt.input)

            if tt.wantErr == nil {
                if err != nil {
                    t.Errorf("Validate(%q) = %v, want nil", tt.input, err)
                }
                return
            }
            if !errors.Is(err, tt.wantErr) {
                t.Errorf("Validate(%q) = %v, want %v", tt.input, err, tt.wantErr)
            }
        })
    }
}
```

## Key points

- **Anonymous struct slice with a `name` field.** The name becomes the subtest name visible in `go test -v` output and lets you target one case with `go test -run TestValidate/empty_string`.
- **`t.Run(tt.name, ...)`** isolates each case: one failure doesn't stop the others, and the failure message tells you exactly which case broke.
- **`t.Parallel()` at both levels** — outer for the whole test, inner for each subtest — runs cases concurrently. Safe here because `Validate` is pure. Skip the inner one if your subject mutates shared state.
- **`errors.Is` for sentinel comparison**, not `==`. This works whether `Validate` returns the sentinel directly or wraps it with `fmt.Errorf("...: %w", ErrEmpty)`. Assumes your validation errors are defined like:
  ```go
  var (
      ErrEmpty       = errors.New("validate: empty string")
      ErrTooLong     = errors.New("validate: too long")
      ErrInvalidChar = errors.New("validate: invalid character")
  )
  ```
- **Include the input in the failure message** (`%q` quotes it so whitespace/control chars are visible). Future-you debugging a regression will thank present-you.
- **Cover happy paths AND each rejection rule.** One row per branch is the minimum; add edge cases (boundary lengths, empty, max-size) liberally — rows are cheap.

## When to reach for variants

- **Custom error types with fields?** Use `errors.As` instead of `errors.Is`, and assert on the extracted value.
- **Comparing complex outputs (structs, slices)?** Use `github.com/google/go-cmp/cmp` with `cmp.Diff` — its diff output is far more readable than `reflect.DeepEqual` + `%v`.
- **Loop-variable capture?** On Go 1.22+ this is fixed; on older versions add `tt := tt` inside the loop before `t.Run`.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies the sentinel error pattern as the idiomatic Go approach and explains why bare string errors are limiting for callers using errors.Is. Answer B gives exactly the naive anti-pattern the question warns against, with no explanation of its limitations. Answer A addresses both rubric criteria while Answer B addresses neither.

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

Then return it anywhere with:

```go
return ErrUserNotFound
```

---

**Why not the shorter-looking alternatives?**

```go
// ❌ errors.New("user not found") inline at the return site
return errors.New("user not found")
```
This creates a *new, distinct error value every call*, so callers can never do:
```go
errors.Is(err, ErrUserNotFound) // always false — different pointer
```
They're forced to match by string, which is fragile and not idiomatic Go.

```go
// ❌ fmt.Errorf("user not found")
```
Same problem, plus an unnecessary allocation and format parse on every call.

---

**The sentinel is the right primitive here.** One declaration, one return statement, and callers get a stable value they can check reliably. That's the idiomatic Go "simplest" — not fewest characters, but fewest moving parts.

If you need to carry extra data (e.g., which user ID was missing), the next step up is a small error type:

```go
type NotFoundError struct{ ID string }
func (e *NotFoundError) Error() string { return "user not found: " + e.ID }
```

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B directly addresses the trap mentioned in the focus area by explaining why bare string errors are limiting and providing the idiomatic Go solution using sentinel errors with errors.Is. Answer A simply gives the naive answer without any explanation of its limitations, missing both rubric criteria entirely. Answer B satisfies both criteria by demonstrating sentinel error usage and explaining why string-only errors are an anti-pattern.

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
| explains why bare string errors are limiting | ✓ | `string match` |

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

**However**, this is a trap. The "simplest" one-liner breaks error handling:

```go
if err != nil && err.Error() == "user not found" { }  // ❌ fragile string matching
```

**The correct primitive** (still one line, barely longer):

```go
var ErrUserNotFound = errors.New("user not found")
```

Then return it:

```go
return ErrUserNotFound
```

Now callers use the robust sentinel check:

```go
if errors.Is(err, ErrUserNotFound) { }  // ✓ safe, refactorable
```

**Why it matters:** Bare strings are unmaintainable. If you later change the message, all callers matching by text break silently. Sentinels are the Go idiom — define them once at package scope, reuse everywhere.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A directly addresses the trap mentioned in the focus area by explaining why bare string errors are limiting and providing the idiomatic sentinel pattern with `errors.Is` usage. Answer B falls directly into the trap by recommending `errors.New` inline as the idiomatic choice without any mention of the limitations of bare string errors or sentinel patterns.

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
| explains why bare string errors are limiting | ✓ | `string match` |

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

The shortest *correct* answer isn't `errors.New("user not found")` inline at the return site — that's the trap. Callers can only match it by string comparison, which is fragile and breaks `errors.Is`.

The idiomatic one-liner is a **package-level sentinel**:

```go
var ErrUserNotFound = errors.New("user not found")
```

Then return it:

```go
return ErrUserNotFound
```

Callers check it cleanly:

```go
if errors.Is(err, ErrUserNotFound) { ... }
```

### Why not `errors.New("user not found")` at the return site?

```go
return errors.New("user not found") // ← the trap
```

It looks shorter, but:
- Every call allocates a new error.
- Callers have no way to detect it except `err.Error() == "user not found"`, which breaks the moment you wrap it (`fmt.Errorf("lookup: %w", err)`) or tweak the message.
- It violates the "errors are values" idiom — sentinels exist precisely so this comparison is a typed identity check, not a string match.

### If you need to add context at the call site

Wrap with `%w` so `errors.Is` still finds the sentinel:

```go
return fmt.Errorf("get user %q: %w", id, ErrUserNotFound)
```

So: **two lines total** (one `var` declaration, one `return`) — and that's the real minimum for code you won't regret.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide essentially identical CSS Grid solutions using `display: grid`, `repeat(3, 1fr)`, and a gap value. Both explain the key concepts clearly and include practical examples. The differences are purely stylistic — Answer B uses a table and more formatting, while Answer A uses prose — but neither is materially better or worse.

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
| `gap` | `16px` | Adds space between columns AND rows |

---

## Key Concepts

**`repeat(3, 1fr)`** is shorthand for `1fr 1fr 1fr`
- `fr` = **fraction unit** — divides available space equally
- Columns automatically adjust to container width

**`gap`** controls spacing:
```css
gap: 16px;           /* same gap for rows and columns */
gap: 8px 16px;       /* row-gap | column-gap */
column-gap: 16px;    /* columns only */
```

---

## Practical Example with Styling

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 16px;
}

.item {
  background: #f0f0f0;
  padding: 20px;
  border-radius: 8px;
}
```

> **Tip:** Add `@media (max-width: 768px) { grid-template-columns: 1fr; }` 
> to stack columns on mobile.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Here's the simplest CSS Grid setup for that:

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

- `display: grid` — enables Grid on the container
- `repeat(3, 1fr)` — creates 3 columns, each taking **1 fraction** of available space (so they're always equal width)
- `gap: 1rem` — adds space between columns *and* rows without affecting outer edges

**Common adjustments:**

```css
/* Gap between columns only (no row gap) */
column-gap: 1rem;

/* Fixed gap size */
gap: 16px;

/* Responsive: collapse to 1 column on small screens */
grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
```

The `1fr` unit is the key — it distributes remaining space equally after gaps are accounted for, so you never need to calculate percentages manually.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in correctness and usefulness. Answer A shows both the explicit `1fr 1fr 1fr` and the `repeat(3, 1fr)` shorthand, while Answer B leads with the shorthand and includes a more realistic HTML example with 6 items showing wrapping behavior. Neither is materially better than the other.

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

This creates columns that are *at least* 250px wide, shrinking to fit smaller screens, and automatically reduces to fewer columns when space is tight.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same core CSS solution with identical code and equivalent explanations. Answer A adds a responsive auto-fit variation while Answer B adds shorthand alternatives and gap variations — both are useful extras but neither is materially better than the other.

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

## Breakdown

- **`display: grid`** — Activates grid layout
- **`grid-template-columns: repeat(3, 1fr)`** — Creates 3 equal columns (`1fr` = 1 fraction of available space)
- **`gap: 1rem`** — Adds spacing between columns (and rows, if any)

## Variations

**Even shorter** (without `repeat`):
```css
grid-template-columns: 1fr 1fr 1fr;
```

**Custom gap size**:
```css
gap: 8px;        /* small */
gap: 20px;       /* medium */
gap: 2rem;       /* large */
```

**Different row/column gaps**:
```css
row-gap: 0;
column-gap: 1rem;
```

That's it — no media queries or extra rules needed for a basic equal-width layout. 🎯

</details>

<details><summary>opus: skill-loaded answer</summary>

That's a CSS question, not Go — happy to answer it directly:

```css
.container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
```

That's it. Breakdown:

- `display: grid` — turn the element into a grid container
- `grid-template-columns: repeat(3, 1fr)` — three columns, each taking an equal fraction (`1fr`) of the available space
- `gap: 1rem` — space between columns (and rows, if you add any); adjust the value to taste (`8px`, `0.5rem`, `16px`, etc.)

Any direct children of `.container` will automatically flow into the three columns:

```html
<div class="container">
  <div>Column 1</div>
  <div>Column 2</div>
  <div>Column 3</div>
</div>
```

If you want it to collapse to one column on narrow screens, the most modern way is:

```css
.container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}
```

That gives as many columns as fit, each at least 250px wide.

</details>

---
