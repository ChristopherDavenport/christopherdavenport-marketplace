---
name: go
description: >
  Idiomatic Go: error wrapping with %w, context propagation, slog, generics,
  goroutines/channels, table-driven tests. Use when writing, reviewing, or
  refactoring .go files or projects with go.mod.
---

# Go Best Practices

Go's design rewards simplicity, composition, explicit error handling, and small interfaces. This skill steers Claude toward code that satisfies the major community style guides — Effective Go, Google's Go Style, Uber's Go Style, and the Go Code Review Comments — while incorporating modern stdlib idioms (`errors.Is`/`As` wrapping, `context.Context`, `log/slog`, generics, fuzz tests).

## Scope

Covers: error wrapping (`errors.Is`/`As`, `%w`), `context.Context` propagation, `log/slog` structured logging, generics with type parameters and constraints, `iter.Seq` range-over-func, goroutines / channels / `select`, `defer`, embedding, interfaces, struct tags, JSON marshaling, `net/http` patterns, project layout, internal packages, build tags, table-driven tests, `t.Run` / `t.Cleanup`, fuzz testing, `go vet`, `golangci-lint`, `govulncheck`, go workspaces.

## Core Rules

These rules cross-cut most Go tasks. Internalize them before reaching for an API-specific reference.

- **Handle every error explicitly** — never assign with `_` to discard an error without a comment justifying why. Wrap with `fmt.Errorf("...: %w", err)` to add context while preserving the chain; replace (no `%w`) only when the underlying error is an implementation detail you want to hide.
- **Accept interfaces, return concrete types** — declare interfaces in the *consumer* package, not the producer. Keep them small (1–3 methods); prefer `io.Reader` over `FileLike`.
- **Receivers: pointer for mutation or large structs, value for small immutable types — and consistent across all methods on a type.** Mixing receiver kinds breaks the method set in subtle ways.
- **Goroutines need a known lifetime** — every `go` statement must have a clear answer to "how does this stop?" (context cancellation, channel close, `sync.WaitGroup`). Unbounded `go func()` is a leak.
- **Pass `context.Context` as the first parameter** to anything that does I/O, blocks, or may be cancelled. Never store it in a struct. Never pass `nil` — use `context.TODO()` if you genuinely have nothing.
- **Prefer composition over embedding-as-inheritance** — embed for behavior reuse, not to fake type hierarchies. Don't embed types just to expose their methods as your API.
- **Zero values should be useful** — design types so `var x T` is a valid starting state. `sync.Mutex{}`, `bytes.Buffer{}`, and `strings.Builder{}` are the canonical examples. Don't require a `New*` constructor when a literal works.
- **Concurrent access requires synchronization** — channel for ownership transfer, `sync.Mutex` for guarded shared state, `sync/atomic` for counters and flags. Always run `go test -race` in CI.
- **`gofmt` is non-negotiable** — never argue with it, never reformat by hand. `goimports` for import grouping. CI must fail on unformatted code.
- **Package names: short, lowercase, single-word, no underscores or plurals** — `users` not `user_utils`, `httputil` not `HTTPUtil`. Importers will type the name often; respect their fingers.

## When to Use Each Concept

| Scenario | Use | Why |
|---|---|---|
| Allocating a slice, map, or channel | `make` | Initializes the internal structure; `new` returns a zeroed pointer that's unusable for these |
| Allocating a struct you need a pointer to | `&T{...}` | Lets you initialize fields; `new(T)` only gives the zero value |
| Method mutates receiver, or receiver > ~64 bytes | Pointer receiver | Avoids copy; required for mutation visibility |
| Small immutable type (`time.Time`-style) | Value receiver | Cheap copy, no aliasing surprises, safe in maps |
| Function returns a domain type | Concrete type | Caller can assert to the interfaces they need; preserves API evolution |
| Function parameter describes behavior | Interface (smallest possible) | Decouples caller; testability without mocks |
| Adding context to a returned error | `fmt.Errorf("...: %w", err)` | Preserves `errors.Is`/`As` chain |
| Hiding the underlying error (it's an implementation detail) | New sentinel/typed error, no `%w` | Don't leak internal abstractions |
| Coordinating goroutines on a result | Channel | Ownership transfer; composes with `select` and context |
| Protecting mutable shared state | `sync.Mutex` | Lower overhead than channels for guarded fields |
| Cancellation/deadline across boundaries | `context.Context` + `select { case <-ctx.Done(): }` | Standard contract throughout stdlib |
| Same algorithm over multiple types | Generic function with a constraint | Type safety without `interface{}` + reflection |
| Logging an error with structured fields | `slog.Error("msg", "err", err, "key", v)` | Structured, leveled, context-aware |
| Optional configuration for a constructor | Functional options (`func(*T)`) | Backwards-compatible API growth |
| Iterating a custom sequence (Go 1.23+) | `iter.Seq` / `iter.Seq2` + `range` | First-class push iterators; composes with stdlib |

## Examples

Example 1: User says "this error message just says `EOF`, I can't tell where it came from"
Actions:
1. Identify the bare `return err`
2. Replace with `return fmt.Errorf("read config from %s: %w", path, err)`
3. Confirm callers using `errors.Is(err, io.EOF)` still work because of `%w`
Result: Error chain carries operational context without breaking sentinel checks.

Example 2: User says "my goroutine is leaking — pprof shows them piling up"
Actions:
1. Find every `go func()` and trace its exit condition
2. Add `ctx context.Context` plumbing if missing; replace blocking sends/receives with `select { case ...: case <-ctx.Done(): return }`
3. Ensure the parent calls `cancel()` (defer it) so children unwind
Result: Each goroutine has a deterministic lifetime tied to a context.

Example 3: User says "I want to add validation to my User struct, what's idiomatic?"
Actions:
1. Avoid forcing a `NewUser` constructor — keep the zero value usable if possible
2. Add a `(u User) Validate() error` method returning a typed error so callers can `errors.As`
3. If validation requires non-trivial setup, use functional options (`UserOption func(*User)`)
Result: Consumers can use `User{}` literals; complex configurations remain extensible.

## Troubleshooting

| Symptom | Reference |
|---|---|
| `gofmt` keeps reformatting your code; doc comments missing on exported names | [formatting-and-comments.md](references/formatting-and-comments.md) |
| Linter flags name (Get prefix, stutter, ALL_CAPS, package name underscore) | [naming.md](references/naming.md) |
| `defer` running in unexpected order; `for` loop variable captured wrong | [control-flow.md](references/control-flow.md) |
| Mixed value/pointer receivers; named returns hiding bugs; variadic edge cases | [functions-and-methods.md](references/functions-and-methods.md) |
| `append` "shared backing array" surprise; nil vs empty slice; map iteration order | [slices-maps-strings.md](references/slices-maps-strings.md) |
| `new` vs `&T{}` confusion; struct tag syntax errors; zero value not usable | [structs-and-composites.md](references/structs-and-composites.md) |
| Interface defined in wrong package; type assertion panics; embedding leaking methods | [interfaces-and-embedding.md](references/interfaces-and-embedding.md) |
| `errors.Is` returns false; bare `return err`; panic that should be an error | [errors.md](references/errors.md) |
| Data race detected; goroutine leak; channel deadlock; `context.Context` misuse | [concurrency.md](references/concurrency.md) |
| Generic function won't compile; `comparable` constraint surprise; reflection overuse | [generics.md](references/generics.md) |
| Test ordering bugs with `t.Parallel`; missing `t.Helper`; flaky benchmarks | [testing.md](references/testing.md) |
| `go.mod` confusion; v2+ import path; `replace` for local dev; vulnerability check | [modules-and-tooling.md](references/modules-and-tooling.md) |
| Cyclic imports; `util`/`common` packages; where does `internal/` go | [project-layout.md](references/project-layout.md) |
| HTTP client missing timeout; response body not closed; JSON tag wrong; `math/rand` for security | [stdlib-patterns.md](references/stdlib-patterns.md) |
| `log.Printf` in library code; logging in a hot path; structured fields missing | [logging-and-observability.md](references/logging-and-observability.md) |

## Topic References

- [Formatting & Comments](references/formatting-and-comments.md) — `gofmt`/`goimports` invariants, godoc-style doc comments, package comments
- [Naming](references/naming.md) — packages, exported identifiers, getters/setters, interface names, receivers, error variables
- [Control Flow](references/control-flow.md) — `if`/`for`/`switch`/type switch, range, range-over-func/`iter.Seq`, `defer`, early-return
- [Functions & Methods](references/functions-and-methods.md) — multiple/named returns, receivers, method sets, functional options, variadic
- [Slices, Maps, Strings](references/slices-maps-strings.md) — `make`/`append`/`copy`, capacity gotchas, nil-vs-empty, map iteration, `strings.Builder`
- [Structs & Composites](references/structs-and-composites.md) — composite literals, struct tags, `new` vs `&T{}`, useful zero values
- [Interfaces & Embedding](references/interfaces-and-embedding.md) — accept interfaces / return concrete, small interfaces, type assertions, embedding
- [Errors](references/errors.md) — error as value, sentinel errors, `%w` wrapping, `errors.Is`/`As`/`Unwrap`, custom types, panic/recover
- [Concurrency](references/concurrency.md) — goroutines, channels, `select`, `context.Context`, `sync` primitives, race detector, channel-vs-mutex
- [Generics](references/generics.md) — type parameters, constraints (`comparable`, `constraints.Ordered`, custom unions), when to use generics
- [Testing](references/testing.md) — table-driven tests, `t.Run`/`t.Helper`/`t.Cleanup`/`t.Parallel`, golden files, fuzz, benchmarks, examples
- [Modules & Tooling](references/modules-and-tooling.md) — `go.mod`/`go.sum`, SemVer + import versioning, `go vet`, `golangci-lint`, `govulncheck`, workspaces
- [Project Layout](references/project-layout.md) — package as design unit, `internal/`, `cmd/`, anti-patterns, layering
- [Stdlib Patterns](references/stdlib-patterns.md) — `net/http` (server + client), `encoding/json`, `io.Reader`/`Writer`, `crypto/rand`, `database/sql`
- [Logging & Observability](references/logging-and-observability.md) — `log/slog`, structured/leveled logging, attribute conventions, when to log vs return
