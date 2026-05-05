# Functions & Methods — Deep Dive

## Multiple Return Values

Go functions can return multiple values. The dominant idiom is `(result, error)`:

```go
func ReadFile(path string) ([]byte, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("open %s: %w", path, err)
    }
    defer f.Close()
    return io.ReadAll(f)
}
```

**Conventions:**

- `error` is the *last* return value, always
- On error, return the zero value for other returns: `return nil, err` (slice/map/pointer), `return 0, err` (numeric), `return "", err` (string), `return User{}, err` (struct)
- Never return a usable result *and* a non-nil error — callers shouldn't have to inspect both
- The "comma ok" idiom for type assertions, map lookups, channel receives:

```go
v, ok := mp[key]            // ok=false if key missing
v, ok := i.(string)         // ok=false if type assertion fails
v, ok := <-ch               // ok=false if channel closed and drained
```

## Named Returns — Use Sparingly

Named returns let you declare return variables in the signature:

```go
func split(s, sep string) (before, after string, found bool) {
    i := strings.Index(s, sep)
    if i < 0 {
        return s, "", false
    }
    return s[:i], s[i+len(sep):], true
}
```

**When they earn their keep:**

- Documenting what each return represents (`(width, height int)`)
- Modifying the return value in a deferred function (the `defer ... { err = ... }` pattern):

```go
func write(w io.Writer, src io.Reader) (err error) {
    defer func() {
        if cerr := flush(w); err == nil {
            err = cerr
        }
    }()
    _, err = io.Copy(w, src)
    return
}
```

**When they hurt:**

- Long functions where naked `return` makes the actual return value invisible
- Hides bugs where you assigned to the named variable but forgot to update it before returning

**Rule of thumb:** name returns when they aid documentation or you need the deferred-modification pattern. Otherwise prefer explicit returns.

**Avoid naked `return` in functions longer than ~5 lines** — readers shouldn't have to scroll up to find what's being returned.

## Receivers — Value vs Pointer

Choose a pointer receiver when:

- The method mutates the receiver
- The receiver is large (rule of thumb: bigger than ~64 bytes; benchmark when it matters)
- The receiver contains a `sync.Mutex` or other field that must not be copied
- Consistency: any other method on the type uses a pointer receiver

Choose a value receiver when:

- The type is small and immutable (`time.Time`, `net.IP`, primitives wrapped in a `type X string`)
- You want call sites to be safe even with copies (no aliasing surprises)
- The receiver is a map, slice, or channel — these are already reference-like

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

// ✓ Pointer receiver — mutates count, contains a mutex
func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

// ✓ Value receiver — small, immutable
type Color uint32

func (c Color) RGB() (r, g, b uint8) { ... }
```

### Consistency Across Methods

**Mixing receiver kinds on the same type breaks the method set in subtle ways.** A `*T` has access to both pointer-receiver and value-receiver methods; a `T` only has access to value-receiver methods. Mixing means addressable values implement different interfaces than non-addressable copies:

```go
// Map values are NOT addressable
m := map[string]Counter{}
m["x"].Inc()        // ✗ compile error — can't call pointer method on map value
```

**Pick one receiver kind per type and stick to it.**

## Method Sets

The method set determines which interfaces a type satisfies:

- `T` includes all methods with a `T` receiver
- `*T` includes all methods with a `T` *or* `*T` receiver

```go
type Validator interface { Validate() error }

type User struct { ... }
func (u *User) Validate() error { ... }

var u User = ...
var v Validator = u    // ✗ User does not satisfy Validator (only *User does)
var v Validator = &u   // ✓
```

## Functional Options Pattern

For constructors with many optional parameters, the canonical Go idiom is functional options:

```go
type Server struct {
    addr        string
    timeout     time.Duration
    maxConns    int
    logger      *slog.Logger
}

type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

func WithMaxConns(n int) Option {
    return func(s *Server) { s.maxConns = n }
}

func WithLogger(l *slog.Logger) Option {
    return func(s *Server) { s.logger = l }
}

func NewServer(addr string, opts ...Option) *Server {
    s := &Server{
        addr:     addr,
        timeout:  30 * time.Second,
        maxConns: 100,
        logger:   slog.Default(),
    }
    for _, opt := range opts {
        opt(s)
    }
    return s
}

// Call site
srv := NewServer("0.0.0.0:8080",
    WithTimeout(5*time.Second),
    WithLogger(logger),
)
```

**Why this beats alternatives:**

- Adding a new option doesn't change the constructor signature (backwards-compatible)
- Defaults live in one place
- Each option is self-documenting at the call site (compare to `NewServer("0.0.0.0:8080", 5*time.Second, 0, logger)`)

**Alternatives:**

- **Config struct**: `NewServer(Config{Addr: "...", Timeout: ...})` — simpler when there are few fields and you don't need callable defaults; downside is required-vs-optional gets fuzzy
- **Builder**: rarely idiomatic in Go; functional options are the preferred shape

## Variadic Functions

```go
func Sum(vals ...int) int {
    total := 0
    for _, v := range vals {
        total += v
    }
    return total
}

Sum(1, 2, 3)
Sum([]int{1, 2, 3}...)    // unpack a slice with ...
```

**Variadic is just sugar for a slice parameter.** Inside the function, `vals` is `[]int`. Callers can unpack a slice with `...`.

**When to use:**

- Genuinely variable-arity APIs (`fmt.Printf`, `slices.Concat`)
- Optional argument lists (functional options pattern)

**When not to use:**

- Avoiding overloads — Go has no overloads, but you don't need variadic for this; named functions are clearer
- Faking optional parameters — variadic with 0-or-1 elements is a code smell; prefer functional options

## Function Values and Closures

Functions are first-class values. Closures capture variables from the enclosing scope:

```go
func counter() func() int {
    n := 0
    return func() int {
        n++
        return n
    }
}

c := counter()
c() // 1
c() // 2
```

Captured variables live as long as any closure referencing them — not as long as the enclosing function. This is the source of the loop-variable trap (pre-1.22) and goroutine leaks (a closure can keep large objects alive).

## `init()`

Each file can have one or more `init()` functions, called after package-level variables are initialized, before `main`:

```go
var registry = map[string]Driver{}

func init() {
    registry["pg"] = pgDriver{}
}
```

**Use sparingly.** `init` runs implicitly, can fail at import time, complicates testing, and creates ordering dependencies. Prefer explicit registration:

```go
func RegisterDriver(name string, d Driver) {
    registry[name] = d
}
```

Only use `init` for things that genuinely must happen at program start and have no caller — e.g., registering an `image.Decoder` for `image/png` so `image.Decode` works without explicit setup.

## `panic` and `recover`

`panic` is for *programmer error* — invariant violations that callers can't reasonably recover from. Library code should not panic across API boundaries.

```go
// ✓ panic on programmer error: nil where it makes no sense
func mustOpen(path string) *os.File {
    f, err := os.Open(path)
    if err != nil {
        panic(fmt.Sprintf("open %s: %v", path, err))
    }
    return f
}
```

`recover` works only inside a deferred function, and only catches panics in the same goroutine. Use it at process boundaries (HTTP handlers, top-level goroutines) to avoid crashing the whole process:

```go
func safeHandle(w http.ResponseWriter, r *http.Request) {
    defer func() {
        if rcv := recover(); rcv != nil {
            slog.Error("panic in handler", "panic", rcv)
            http.Error(w, "internal error", http.StatusInternalServerError)
        }
    }()
    handle(w, r)
}
```

Don't use panic for ordinary errors — return them.

## Common Pitfalls

- **Naked `return` in long functions** — readers can't tell what's returned without scrolling.
- **Mixed receiver kinds** — pick pointer or value per type, not per method.
- **Calling a `*T` method on a map value** — map values are not addressable; assign to a local first or store `*T` in the map.
- **Variadic 0-or-1 to fake an optional parameter** — use functional options or two named functions.
- **Returning a usable value alongside a non-nil error** — the contract is one or the other.
- **`init()` doing real work** — moves errors out of the call graph and complicates testing. Prefer explicit setup functions.
- **`recover` in business logic** — `recover` is for boundaries, not control flow. Treat panics as bugs to fix.
- **Closure capturing a large value** — keeps it alive for the closure's lifetime; copy only what you need.
