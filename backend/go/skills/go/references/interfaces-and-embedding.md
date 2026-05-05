# Interfaces & Embedding — Deep Dive

Interfaces are Go's primary abstraction. They are *implicit* (no `implements` keyword), *structural* (a type satisfies an interface if it has the required methods), and *small* (one or two methods is the norm).

## Accept Interfaces, Return Concrete Types

The defining idiom of Go API design.

```go
// ✓ Accept an interface — caller can pass anything that fits
func Save(w io.Writer, data []byte) error {
    _, err := w.Write(data)
    return err
}

// ✓ Return a concrete type — caller can use any of its methods
func NewClient(addr string) *Client {
    return &Client{addr: addr}
}

// ✗ Return an interface — limits what the caller can do
func NewClient(addr string) Pinger {
    return &Client{addr: addr}
}
```

**Why:** the consumer best knows which behaviors it depends on. Returning a concrete type lets callers assert to the interfaces *they* care about. Returning an interface forces them through your chosen abstraction.

**Exceptions** (when returning an interface is correct):

- The factory genuinely returns one of several types based on input (`io.NewReader` style — but even then, return `*os.File` if you have one).
- The interface is the documented contract and the concrete type is an implementation detail (`http.Handler` from middleware).
- Decorating: `io.LimitReader` returns `io.Reader` because the wrapped type is irrelevant.

## Define Interfaces in the Consumer Package

The package that *uses* the interface should define it. Not the package that *implements* it.

```go
// ✗ The provider package declares the interface
package db

type DB interface {
    Query(q string) ([]Row, error)
}

func NewPostgres() *Postgres { ... }       // *Postgres implements DB

// Consumer must import db.DB just to type the parameter
package users
import "example.com/db"
func List(d db.DB) []*User { ... }
```

```go
// ✓ The consumer package declares the interface it needs
package users

type Querier interface {
    Query(q string) ([]Row, error)         // Just what users needs
}

func List(q Querier) []*User { ... }

// Provider doesn't need to know about Querier
package db
func NewPostgres() *Postgres { ... }       // Has Query method; satisfies Querier implicitly
```

This works because Go interfaces are implicit. The `Postgres` type doesn't have to "declare" it implements `Querier` — having the right methods is enough.

**Benefits:**

- Consumers depend only on the methods they actually use (interface segregation)
- Providers don't grow a "things that depend on me" list
- Tests in the consumer package can mock without importing the provider

## Keep Interfaces Small

The stdlib's most successful interfaces have one method:

```go
type Reader interface { Read(p []byte) (n int, err error) }
type Writer interface { Write(p []byte) (n int, err error) }
type Closer interface { Close() error }
type Stringer interface { String() string }
type Error interface { Error() string }
```

Composition assembles bigger interfaces:

```go
type ReadCloser interface {
    Reader
    Closer
}
```

**Rule of thumb:** if your interface has more than ~3 methods, ask whether the abstraction is too coarse. Big interfaces are hard to satisfy in tests and signal that the consumer wants too much from the provider.

## Type Assertions

Recover the concrete type from an interface value:

```go
var i interface{} = "hello"

s := i.(string)             // panics if i is not a string
s, ok := i.(string)         // comma-ok form: ok=false instead of panic
```

**Use the comma-ok form.** Bare assertions panic at runtime.

For type-switching by type:

```go
switch v := i.(type) {
case string:
    return strconv.Atoi(v)
case int:
    return v, nil
case fmt.Stringer:
    return strconv.Atoi(v.String())
default:
    return 0, fmt.Errorf("unsupported type %T", i)
}
```

## Compile-Time Interface Satisfaction Check

When you want to assert that a type implements an interface — and get a compile error if it ever stops:

```go
var _ http.Handler = (*MyHandler)(nil)
```

This declares an unused variable of interface type, assigning a typed nil pointer. Costs nothing at runtime; gives you a build error if `*MyHandler` ever loses a method or `http.Handler` changes.

Place this near the type definition or at package init.

## Empty Interface — `interface{}` and `any`

`interface{}` (or `any`, the Go 1.18+ alias) is satisfied by any type. Used when you genuinely don't care about the type — `fmt.Println`, `json.Marshal`, generic containers (pre-generics).

```go
func Log(v any) { fmt.Println(v) }
```

**Avoid `any` when generics, an interface, or a concrete type would do.** `any` discards type information and pushes type checks to runtime.

```go
// ✗ Pre-generics era
func First(s []any) any { ... }

// ✓ With generics
func First[T any](s []T) T { ... }
```

## Nil Interface vs Interface Holding Nil

A classic Go gotcha:

```go
var p *MyError = nil
var e error = p
e == nil      // false ! ! !
```

An interface value is `nil` only when *both* its type and value are nil. Wrapping a typed nil pointer in an interface gives a non-nil interface containing a nil concrete value.

**Defense:** return `error` directly, not via a typed variable:

```go
// ✗
func doThing() error {
    var err *MyError
    if cond { err = &MyError{...} }
    return err              // returns non-nil error even when err is nil pointer
}

// ✓
func doThing() error {
    if cond { return &MyError{...} }
    return nil              // explicit untyped nil
}
```

## Embedding

Embedding promotes the methods (and fields) of an embedded type to the outer type:

```go
type Logger struct{ slog.Logger }       // value embed

func (l *Logger) WithRequestID(id string) *Logger {
    return &Logger{Logger: *l.Logger.With("request_id", id)}
}
```

```go
type Server struct{ *http.Server }       // pointer embed

s := &Server{Server: &http.Server{Addr: ":8080"}}
s.ListenAndServe()                       // promoted from *http.Server
```

### Embedding for Behavior, Not Hierarchy

**Use embedding when:**

- You want to reuse another type's methods without manually delegating each one
- You're building a thin wrapper that adds one or two methods
- You're composing interfaces (`io.ReadCloser`)

**Do not use embedding when:**

- You're trying to fake inheritance — Go has no inheritance and pretending it does leads to brittle hierarchies
- You want to restrict which methods are exposed — embedding promotes everything (use a regular field and delegate selectively)
- The embedded type's methods don't make sense on the outer type — `Server` embedding `bytes.Buffer` because both happen to have a Read method is a coincidence, not a design

### Method Resolution with Embedding

Outer methods shadow inner methods of the same name:

```go
type Logger struct{ slog.Logger }
func (l *Logger) Info(msg string, args ...any) { ... }   // shadows slog.Logger.Info
```

If two embedded types have the same method name, neither is promoted — calling it on the outer type is a compile error. You must qualify: `outer.EmbeddedA.Method()`.

### Pointer vs Value Embedding

```go
type Wrapper struct {
    Inner            // value embed — Wrapper contains an Inner
    *OtherInner      // pointer embed — Wrapper contains *OtherInner; nil if not set
}
```

Pointer embedding is fine but the embedded pointer can be nil — calling promoted methods on a nil embed panics. Initialize it.

## Interface Polymorphism Patterns

### Strategy via Interface

```go
type Notifier interface {
    Notify(msg string) error
}

type EmailNotifier struct{ ... }
func (e *EmailNotifier) Notify(msg string) error { ... }

type SlackNotifier struct{ ... }
func (s *SlackNotifier) Notify(msg string) error { ... }

func Alert(n Notifier, msg string) { _ = n.Notify(msg) }
```

### Decorator via Interface

```go
type Handler interface {
    Handle(req Request) Response
}

func Logging(next Handler) Handler {
    return HandlerFunc(func(req Request) Response {
        log.Printf("req: %v", req)
        return next.Handle(req)
    })
}
```

The `HandlerFunc` adapter (a function type with a method) is the canonical Go pattern for satisfying single-method interfaces with a plain function:

```go
type HandlerFunc func(Request) Response
func (f HandlerFunc) Handle(req Request) Response { return f(req) }
```

Stdlib does this for `http.HandlerFunc`, `sort.SliceStable`, and many others.

## Common Pitfalls

- **Returning interfaces from constructors** — limits callers. Return concrete types unless you have a specific reason.
- **Defining interfaces in the producer package** — couples consumers to your abstraction. Define them in the consumer.
- **Big interfaces** — `Database` with 30 methods is a smell. Break into `Querier`, `Execer`, etc.
- **Bare type assertion without comma-ok** — panics on type mismatch. Always use `v, ok := i.(T)`.
- **Returning a typed nil pointer as `error`** — yields a non-nil interface. Return untyped `nil` explicitly.
- **`any`/`interface{}` everywhere** — discards type safety. Reach for generics or a real interface.
- **Embedding for inheritance** — Go has no inheritance. Embedding is composition with promotion; don't pretend otherwise.
- **Embedded pointer left nil** — promoted method calls panic. Initialize embedded pointers in your constructor.
- **Forgetting compile-time satisfaction check** — easy to silently lose interface satisfaction during refactoring. Add `var _ Iface = (*Type)(nil)`.
