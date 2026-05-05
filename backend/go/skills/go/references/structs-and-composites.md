# Structs & Composites — Deep Dive

## Composite Literals

A composite literal constructs a value of a struct, array, slice, or map type:

```go
type User struct {
    ID    int
    Email string
    Roles []string
}

u := User{ID: 1, Email: "a@b.com", Roles: []string{"admin"}}
u := User{1, "a@b.com", []string{"admin"}}        // positional — fragile
```

**Always use field names, not positional initialization.** Positional literals break silently when fields are added or reordered. The vet tool flags positional literals for stdlib types.

**Use multi-line form for clarity:**

```go
u := User{
    ID:    1,
    Email: "a@b.com",
    Roles: []string{"admin"},
}
```

The trailing comma after `Roles: []string{"admin"},` is required by `gofmt`.

### Omitting Fields

Omitted fields take the zero value:

```go
u := User{ID: 1}
// u.Email == ""
// u.Roles == nil
```

This is a feature — design types so the zero value is meaningful and you can omit the boring fields.

## `new` vs `&T{}`

```go
p := new(User)              // *User to zeroed User
p := &User{}                // *User to zeroed User — equivalent

p := &User{ID: 1}           // *User with ID set; fields not listed are zero
p := new(User); p.ID = 1    // same, two statements
```

**Prefer `&T{...}`** because it lets you initialize fields in the same expression. Use `new` only when no initialization is needed and the `T{}` form would look awkward (e.g., `*int`):

```go
p := new(int)               // *int to 0
p := &x                     // — but only if x is in scope; new() if not
```

## Useful Zero Values

The zero value should be a usable starting state when possible. Stdlib examples:

```go
var b bytes.Buffer          // ready to Write/Read
var sb strings.Builder      // ready to WriteString
var mu sync.Mutex           // ready to Lock
var wg sync.WaitGroup       // ready to Add
var m sync.Map              // ready to Load/Store
```

Design your own types this way:

```go
// ✓ Zero value usable
type Counter struct {
    mu  sync.Mutex
    val int
}

c := Counter{}              // ready to use; no NewCounter() needed
c.Inc()
```

When the zero value would be invalid (e.g., a Client that needs a connection), provide a `NewClient` constructor and document that the zero value must not be used. But ask first whether you can avoid this — many "I need a constructor" cases dissolve once you make defaults work.

## Struct Tags

Struct tags are a string after each field that tools (mostly serializers) read via reflection:

```go
type User struct {
    ID        int       `json:"id" db:"user_id"`
    Email     string    `json:"email,omitempty" db:"email"`
    Password  string    `json:"-" db:"password_hash"`
    CreatedAt time.Time `json:"created_at" db:"created_at"`
}
```

**Format rules:**

- Backticks (raw string) — avoids escaping
- Space-separated key:`"value"` pairs
- Each key's value is comma-separated options (the first is typically the name)
- `json:"-"` hides the field from JSON marshaling
- `json:",omitempty"` (note the leading comma) keeps the Go field name but omits empty values
- `json:"name,omitempty"` renames *and* omits empty
- Unknown tags are silently ignored — typos cause silent bugs

**Common tag families:**

- `json:` — `encoding/json`
- `xml:` — `encoding/xml`
- `yaml:` — gopkg.in/yaml.v3 or sigs.k8s.io/yaml
- `db:` — `sqlx`, many ORMs
- `validate:` — `go-playground/validator`
- `mapstructure:` — Viper config

`go vet` checks struct tag syntax for known formats — run it.

## Field Visibility & API Design

Exported (capitalized) fields are part of your API. Unexported fields can change without breaking clients.

```go
type Server struct {
    // Exported config — part of the API
    Addr    string
    Timeout time.Duration

    // Unexported state — internal
    listener net.Listener
    mu       sync.Mutex
}
```

**Choose exported vs unexported deliberately:**

- Exported = stable contract; changes break clients
- Unexported = free to refactor; clients must use methods

For mutable internal state with invariants (caches, counters), keep fields unexported and expose methods.

## Embedded Fields

A field declared with only a type name is *embedded* — its methods and fields are promoted to the outer struct:

```go
type ReadCloser interface {
    io.Reader
    io.Closer
}

type Server struct {
    *http.Server          // embedded — Server.ListenAndServe() comes from http.Server
    Logger *slog.Logger
}

s := &Server{Server: &http.Server{Addr: ":8080"}, Logger: logger}
s.ListenAndServe()        // promoted method
s.Server.ListenAndServe() // also works — explicit form
```

**Use embedding for behavior reuse, not for "is-a" hierarchies.** It's composition with promotion, not inheritance. See `interfaces-and-embedding.md` for the full guidance.

## Comparing Structs

Structs are comparable iff all their fields are comparable (no slices, maps, or functions):

```go
type Point struct{ X, Y int }
p1 := Point{1, 2}
p2 := Point{1, 2}
p1 == p2                    // true

type Box struct{ Items []int }
b1 := Box{[]int{1}}
b2 := Box{[]int{1}}
b1 == b2                    // ✗ compile error: cannot compare slices
```

For non-comparable structs (or any deep equality), use `reflect.DeepEqual` (slow, runtime) or hand-write a comparison function. In tests, prefer `cmp.Diff` from `github.com/google/go-cmp/cmp`.

## Conversions Between Struct Types

You can convert between structs with identical field names *and types* (tags are ignored from Go 1.8+):

```go
type A struct { X int `json:"x"` }
type B struct { X int `json:"x_field"` }

var a A
var b B = B(a)              // ✓ identical fields; tags ignored
```

This is occasionally useful when bridging between layers (DB row → API response).

## Nested vs Flat

```go
// Flat
type Order struct {
    ID         int
    UserID     int
    UserEmail  string
    UserName   string
}

// Nested
type Order struct {
    ID   int
    User User
}
type User struct {
    ID    int
    Email string
    Name  string
}
```

**Nest when** the inner type is meaningful elsewhere or the grouping clarifies the data. **Flatten when** the inner shape is incidental (e.g., a join result with no separate identity).

## `struct{}` — The Zero-Width Type

The empty struct takes zero bytes. Common uses:

```go
// Set semantics with a map
seen := map[string]struct{}{}
seen["x"] = struct{}{}
_, ok := seen["x"]

// Signaling channel
done := make(chan struct{})
go func() {
    work()
    close(done)
}()
<-done
```

Empty struct beats `bool` for set/signal usage because it makes intent explicit ("the value carries no data") and uses zero memory.

## Common Pitfalls

- **Positional struct literals** — `User{1, "a", nil}` breaks when fields shift. Always name fields.
- **Unused tag options** — `json:"name,omitempty"` requires a leading comma if you only want `omitempty`: `json:",omitempty"`. Easy typo.
- **Tag typos silently ignored** — `jsno:"name"` won't error; the field uses its Go name. `go vet` catches some, not all.
- **Forgetting that the zero value is usable** — over-engineering a `New*` constructor when `T{}` would work fine.
- **Comparing structs with slice/map fields** — compile error. Use `reflect.DeepEqual` or `cmp.Diff`.
- **Embedded pointer to nil** — `s := Server{}` with embedded `*http.Server` leaves it nil; `s.ListenAndServe()` panics.
- **Exporting fields that should be hidden** — once exported, you can't change the type without breaking clients. Keep state private; expose methods.
- **Confusion between `T{}` and `&T{}`** — the first is a value, the second is a pointer. Methods on `*T` need a pointer.
