# Control Flow — Deep Dive

Go's control structures are deliberately spare: `if`, `for`, `switch`, `defer`, `go`, `select`. There is no `while`, no `do/while`, no ternary. Idiomatic Go leans on early returns, short-statement `if`, and `range` over manual iteration.

## `if` with a Short Statement

The `if` form `if init; cond { ... }` scopes a variable to the conditional block — the standard idiom for error checking:

```go
if err := doThing(); err != nil {
    return fmt.Errorf("doThing: %w", err)
}

// Variable err does not exist here.
```

**Use it for:**

- Error checks where the error is only used in the failure branch
- Guards that compute a single value used only inside the conditional

**Don't use it for:**

- Long expressions that hurt readability
- Cases where the value is also needed after the `if`

## Early Returns Over Deep Nesting

Idiomatic Go keeps the happy path at indent level 0 and returns early on errors:

```go
// ✗ Nested
func process(u *User) error {
    if u != nil {
        if u.Email != "" {
            if err := validate(u); err == nil {
                return save(u)
            } else {
                return err
            }
        } else {
            return ErrEmptyEmail
        }
    } else {
        return ErrNilUser
    }
}

// ✓ Early returns
func process(u *User) error {
    if u == nil {
        return ErrNilUser
    }
    if u.Email == "" {
        return ErrEmptyEmail
    }
    if err := validate(u); err != nil {
        return err
    }
    return save(u)
}
```

Avoid `else` after a `return` — the linter `revive`/`golangci-lint`'s `indent-error-flow` flags it.

## `for` Is the Only Loop

Go has one loop keyword. The three forms:

```go
for i := 0; i < 10; i++ { ... }     // C-style
for cond { ... }                     // while-style
for { ... }                          // infinite
for i, v := range slice { ... }      // range
```

### `range` Forms

```go
for i, v := range slice { ... }    // index + element
for i := range slice { ... }       // index only
for _, v := range slice { ... }    // element only

for k, v := range mp { ... }       // map
for k := range mp { ... }          // keys only
for _, v := range mp { ... }       // values only

for v := range ch { ... }          // channel — until closed
for i := range 10 { ... }          // Go 1.22+: integer range, 0..9
```

## Loop Variable Capture (Go 1.22+ Change)

**Pre-1.22:** the loop variable was reused across iterations, causing the classic closure bug:

```go
// Pre-Go-1.22 trap
for _, v := range items {
    go func() {
        process(v)   // ALL goroutines see the final v
    }()
}

// Pre-1.22 fix
for _, v := range items {
    v := v          // shadow with a new per-iteration variable
    go func() { process(v) }()
}
```

**Go 1.22+:** the loop variable is per-iteration in `for` and `for...range`. The closure trap above is gone for new code. Set `go 1.22` (or higher) in `go.mod` to opt in across the whole module.

```go
// Go 1.22+: each goroutine sees its own v
for _, v := range items {
    go func() { process(v) }()
}
```

When reviewing pre-1.22 code, the explicit `v := v` shadow is still safe and clearer; remove it only as part of a deliberate cleanup once `go 1.22+` is set in `go.mod`.

## Range-over-Func / `iter.Seq` (Go 1.23+)

Go 1.23 introduced first-class push iterators via the `iter` package. A function with the signature `func(func(V) bool)` (= `iter.Seq[V]`) is rangeable:

```go
import "iter"

func Numbers(n int) iter.Seq[int] {
    return func(yield func(int) bool) {
        for i := 0; i < n; i++ {
            if !yield(i) {
                return        // consumer broke out of range
            }
        }
    }
}

for v := range Numbers(5) {
    fmt.Println(v)            // 0 1 2 3 4
}
```

Two-value variant `iter.Seq2[K, V]` for key/value pairs:

```go
func Enumerate[V any](s []V) iter.Seq2[int, V] {
    return func(yield func(int, V) bool) {
        for i, v := range s {
            if !yield(i, v) { return }
        }
    }
}

for i, v := range Enumerate(slice) { ... }
```

**Rules:**

- Always check `yield`'s return value and stop on `false`. Failure to do so means `break` in the consumer doesn't actually stop your iterator.
- Push iterators compose with `slices.All`, `maps.All`, `slices.Collect`, `maps.Collect` (Go 1.23 stdlib).
- Reach for `iter.Seq` when you have a custom sequence (tree traversal, DB rows) that callers will want to `range` over. Don't write iterators for things that are already slices.

## `switch`

Go's `switch` does not fall through by default. Each case is its own block:

```go
switch level {
case "debug", "info":
    return Verbose
case "warn":
    return Quiet
default:
    return Normal
}
```

**Forms:**

- Tag-less: `switch { case cond1: ...; case cond2: ... }` — works as an `if/else if` chain
- With short statement: `switch x := f(); x { case ...: }`
- Type switch: `switch v := x.(type) { case Foo: ...; case Bar: ... }`

**Fallthrough** is opt-in with the `fallthrough` keyword (rarely needed; usually a smell):

```go
switch x {
case 1:
    doA()
    fallthrough
case 2:
    doB()
}
```

## Type Switch

```go
switch v := i.(type) {
case nil:
    return ErrNil
case string:
    return strconv.Atoi(v)            // v is string
case int:
    return v, nil                     // v is int
case fmt.Stringer:
    return strconv.Atoi(v.String())   // v is fmt.Stringer
default:
    return 0, fmt.Errorf("unsupported type %T", i)
}
```

**Rules:**

- `case nil:` matches a nil interface
- Multiple types in one case: `case int, int32, int64:` — but then `v` has the static type of the original interface, not the matched type
- Order matters when types overlap (e.g., concrete type before interface)
- `default` is conventional but not required

## `defer`

`defer` schedules a call to run when the surrounding function returns (whether by normal return, panic, or `runtime.Goexit`). Calls run in LIFO order:

```go
func processFile(path string) error {
    f, err := os.Open(path)
    if err != nil { return err }
    defer f.Close()                  // runs at function return

    return parse(f)
}
```

### Defer Pitfalls

**Arguments evaluated at the `defer` statement, not at execution:**

```go
i := 0
defer fmt.Println(i)    // prints 0
i = 1
return                  // 0 is printed, NOT 1
```

To capture the *current* value at defer time, use a closure:

```go
i := 0
defer func() { fmt.Println(i) }()    // prints 1 (closure reads i later)
i = 1
return
```

**Defer in a loop accumulates:**

```go
// ✗ All file handles open until function returns
for _, path := range paths {
    f, _ := os.Open(path)
    defer f.Close()      // doesn't run until processAll returns
    process(f)
}

// ✓ Wrap the body so defer runs per-iteration
for _, path := range paths {
    func() {
        f, _ := os.Open(path)
        defer f.Close()
        process(f)
    }()
}
```

**Defer + named returns to capture errors:**

```go
func write(w io.Writer) (err error) {
    defer func() {
        if cerr := closer.Close(); err == nil {
            err = cerr   // surface close error if write succeeded
        }
    }()
    _, err = io.Copy(w, src)
    return
}
```

**Defer the unlock immediately after the lock:**

```go
mu.Lock()
defer mu.Unlock()      // ✓ pair them visually
// ...
```

## `goto` and Labels

`goto` exists but is rarely used. Labeled `break` and `continue` *are* idiomatic for breaking outer loops:

```go
outer:
for _, row := range matrix {
    for _, cell := range row {
        if cell.Bad() {
            break outer
        }
    }
}
```

## Common Pitfalls

- **`else` after `return`** — flatten the structure. Linters flag this as `indent-error-flow`.
- **Pre-1.22 loop-variable capture** — until `go.mod` says `go 1.22+`, every closure capturing a loop variable is suspect. Add `v := v` explicitly.
- **Defer in a tight loop** — accumulates allocations and delays cleanup; wrap in an inner closure or extract a function.
- **Defer arguments evaluated immediately** — wrap in a closure to capture the latest value.
- **`switch` without `default`** — sometimes intentional, sometimes a missing case. Reviewers should ask.
- **Forgetting `yield` return value in `iter.Seq`** — consumer's `break` becomes a no-op.
- **`break` inside `select` inside `for`** — `break` breaks the `select`, not the `for`. Use a labeled `break` or a `done` flag.
