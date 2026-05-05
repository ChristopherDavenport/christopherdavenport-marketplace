# Errors — Deep Dive

Errors are values in Go. `error` is a built-in interface:

```go
type error interface {
    Error() string
}
```

Any type with an `Error() string` method satisfies it. The conventions around how to create, wrap, inspect, and document errors are some of the most important Go idioms — get them right and most error-handling code becomes simple.

## The Foundational Rule: Errors Are Values

Errors are not exceptions, not control flow. They are return values inspected like any other:

```go
result, err := doThing()
if err != nil {
    return fmt.Errorf("doThing: %w", err)
}
// use result
```

The signature `(T, error)` is the canonical shape. The `error` is the *last* return value, always.

## Constructing Errors

```go
errors.New("something failed")               // simple message
fmt.Errorf("read %s: %w", path, err)         // formatted, with wrapping
fmt.Errorf("read %s: %v", path, err)         // formatted, without wrapping
```

The difference between `%w` and `%v`:

- `%w` — formats the error AND preserves it in the wrapped chain so `errors.Is`/`errors.As` can unwrap to find it
- `%v` — formats the error string but loses the wrapped reference; the chain is broken

**Use `%w` to add context to an underlying error you want callers to inspect. Use `%v` (or just `%s`) when you're deliberately replacing the underlying error with something abstract.**

You can wrap multiple errors at once (Go 1.20+):

```go
err := fmt.Errorf("validation failed: %w; %w", err1, err2)
errors.Is(err, err1)    // true
errors.Is(err, err2)    // true
```

## Sentinel Errors

A sentinel error is a package-level variable used as a comparison target:

```go
var (
    ErrNotFound      = errors.New("not found")
    ErrAlreadyExists = errors.New("already exists")
    ErrUnauthorized  = errors.New("unauthorized")
)
```

Callers check with `errors.Is`:

```go
u, err := store.Get(id)
if errors.Is(err, ErrNotFound) {
    return defaultUser, nil
}
if err != nil {
    return User{}, err
}
```

**Sentinels are part of your API.** Document them. Renaming or removing one breaks callers.

## Custom Error Types

When the error needs structured data — fields callers can inspect:

```go
type ValidationError struct {
    Field string
    Value any
    Msg   string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s=%v: %s", e.Field, e.Value, e.Msg)
}
```

Callers use `errors.As`:

```go
var verr *ValidationError
if errors.As(err, &verr) {
    log.Printf("validation failed on field %s", verr.Field)
}
```

**Conventions:**

- Type name ends in `Error` (`ValidationError`, `os.PathError`, `net.OpError`)
- Receiver is typically a pointer (`*ValidationError`) so the zero value isn't a usable error and so equality comparisons work the way you expect
- Implement `Unwrap() error` if you wrap an underlying error:

```go
type DBError struct {
    Query string
    Err   error
}

func (e *DBError) Error() string  { return fmt.Sprintf("query %q: %v", e.Query, e.Err) }
func (e *DBError) Unwrap() error  { return e.Err }
```

## `errors.Is` vs `errors.As`

```go
errors.Is(err, target)    // unwraps the chain looking for `target` (sentinel match)
errors.As(err, &target)   // unwraps looking for an error of target's TYPE; assigns into target
```

**Use `Is` for sentinels:**

```go
if errors.Is(err, sql.ErrNoRows) { ... }
if errors.Is(err, context.Canceled) { ... }
if errors.Is(err, io.EOF) { ... }
```

**Use `As` for typed errors with fields:**

```go
var pathErr *os.PathError
if errors.As(err, &pathErr) {
    log.Printf("path %q failed", pathErr.Path)
}
```

**Don't compare with `==`** unless you know there's no wrapping in your codebase:

```go
// ✗ Breaks the moment any caller wraps with %w
if err == sql.ErrNoRows { ... }

// ✓ Works regardless of wrapping
if errors.Is(err, sql.ErrNoRows) { ... }
```

## Custom `Is` and `As`

If your error type implements `Is(target error) bool` or `As(target any) bool`, `errors.Is`/`errors.As` will use it. Useful for custom equality (e.g., matching any HTTP 4xx error):

```go
type HTTPError struct{ Code int }
func (e *HTTPError) Error() string { return fmt.Sprintf("http %d", e.Code) }

var ErrClient = &HTTPError{}     // sentinel

func (e *HTTPError) Is(target error) bool {
    var t *HTTPError
    if !errors.As(target, &t) { return false }
    if t == ErrClient { return e.Code >= 400 && e.Code < 500 }
    return e.Code == t.Code
}

errors.Is(&HTTPError{Code: 404}, ErrClient)      // true
```

## Joining Errors

Go 1.20 added `errors.Join` for combining errors (e.g., aggregating from a batch operation):

```go
var errs []error
for _, item := range items {
    if err := process(item); err != nil {
        errs = append(errs, fmt.Errorf("item %d: %w", item.ID, err))
    }
}
return errors.Join(errs...)
```

The result is `nil` if all inputs are nil. Both `errors.Is` and `errors.As` traverse joined errors.

## Error Wrapping Strategy

When propagating an error up the stack, **add context that identifies what your function was doing**:

```go
// ✗ Bare propagation — caller has no idea where it came from
func loadConfig(path string) (*Config, error) {
    f, err := os.Open(path)
    if err != nil { return nil, err }
    defer f.Close()
    return parse(f)
}

// ✓ Each layer adds operational context
func loadConfig(path string) (*Config, error) {
    f, err := os.Open(path)
    if err != nil { return nil, fmt.Errorf("open config %s: %w", path, err) }
    defer f.Close()
    cfg, err := parse(f)
    if err != nil { return nil, fmt.Errorf("parse config %s: %w", path, err) }
    return cfg, nil
}
```

**Context to add:** what your function was doing, the inputs that mattered (path, ID, URL). **Context to leave out:** redundant labels (don't prefix with the function name — the chain already shows the call path) and sensitive data (passwords, tokens, PII).

**Don't double-wrap with the same info** — if the inner error already says "open foo.txt", don't wrap with "open foo.txt: open foo.txt: permission denied".

## When to Replace, Not Wrap

Wrap with `%w` to expose the underlying error. Replace (no `%w`) when the underlying error is an *implementation detail* you don't want callers to depend on:

```go
// ✗ Leaks the storage backend through the API
func (u *UserStore) Get(id int) (User, error) {
    err := u.db.QueryRow(...).Scan(&user)
    if errors.Is(err, sql.ErrNoRows) {
        return User{}, fmt.Errorf("user %d: %w", id, sql.ErrNoRows)  // callers now depend on database/sql
    }
    return user, err
}

// ✓ Translate to your own sentinel — callers see your domain only
func (u *UserStore) Get(id int) (User, error) {
    err := u.db.QueryRow(...).Scan(&user)
    if errors.Is(err, sql.ErrNoRows) {
        return User{}, ErrUserNotFound
    }
    if err != nil {
        return User{}, fmt.Errorf("get user %d: %w", id, err)        // unexpected — wrap as-is for ops
    }
    return user, nil
}
```

The principle: callers should not need to import your dependencies' error types to handle your errors.

## Documenting Errors

For exported functions that return errors, document:

- Which sentinel errors they may return (`returns [ErrNotFound] if no user matches`)
- Which custom error types they may return (`returns *[ValidationError] if input is malformed`)
- Whether wrapping is preserved across layers

```go
// Get returns the user with the given ID.
// It returns [ErrNotFound] if no user with that ID exists.
// All other errors are wrapped from the underlying storage layer.
func (s *Store) Get(id int) (User, error) { ... }
```

## When to Panic

Panic for *programmer error* — situations callers can't reasonably recover from and that indicate a bug:

- Indexing past the end of a slice (the runtime panics)
- Calling a method on a nil receiver where the contract said you must call `New*` first
- A switch hitting a `default` case for an exhaustive enum

Library code should not panic across API boundaries. Return an error instead.

```go
// ✓ Programmer-error panic
func (c *Client) Send(msg Message) error {
    if c == nil {
        panic("Client.Send called on nil Client")
    }
    ...
}

// ✗ Should be an error return
func ParseURL(s string) *URL {
    u, err := url.Parse(s)
    if err != nil { panic(err) }    // callers can't handle this!
    return u
}
```

## `recover` at Boundaries

`recover` only works inside a deferred function and only catches panics in the same goroutine. Use it to prevent a single bug from killing a long-lived process:

```go
func safeHandle(w http.ResponseWriter, r *http.Request, h http.Handler) {
    defer func() {
        if rcv := recover(); rcv != nil {
            slog.Error("panic", "panic", rcv, "stack", string(debug.Stack()))
            http.Error(w, "internal error", http.StatusInternalServerError)
        }
    }()
    h.ServeHTTP(w, r)
}
```

**Rules:**

- Recover only at process/request boundaries (HTTP middleware, top-level worker goroutines)
- Always log the recovered value AND the stack trace
- Never use recover as control flow inside business logic
- Recover does not cross goroutine boundaries — every `go func()` needs its own recover if it can panic

## Common Pitfalls

- **`fmt.Errorf` with `%v` instead of `%w`** — breaks the wrapped chain; `errors.Is`/`As` won't work.
- **Comparing errors with `==`** — `err == sql.ErrNoRows` fails as soon as someone wraps. Use `errors.Is`.
- **Returning `*MyError(nil)` as `error`** — yields a non-nil interface holding a nil concrete value. Return untyped nil explicitly.
- **Wrapping a sentinel without translation when leaking the dependency** — e.g., wrapping `sql.ErrNoRows` in your domain API forces callers to import `database/sql`.
- **`if err != nil { return err }` everywhere** — sometimes correct, but most layers should add context.
- **Bare `panic(err)` in library code** — callers can't recover; return errors instead.
- **`recover` in business logic** — masks bugs and makes them harder to find. Fix the panic.
- **Discarding errors with `_`** — almost always wrong. If you genuinely don't care, write a comment explaining why.
- **Logging the error AND returning it** — typically only one layer should log; the rest propagate. Otherwise you get duplicate log lines.
- **Joined errors lost via `%w` of a single error** — `fmt.Errorf("...: %w", errors.Join(a, b))` only formats the first; use multiple `%w` directives in 1.20+ or accept the chain semantics.
