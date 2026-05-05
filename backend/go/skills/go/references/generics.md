# Generics — Deep Dive

Generics arrived in Go 1.18. They let functions and types accept type parameters constrained by an interface. The intent: replace common patterns that previously required `interface{}` + type assertions or `reflect`, with type-safe alternatives that catch errors at compile time.

**Use generics when** the same logic operates on many types and the type parameter eliminates either runtime type checks (`v.(int)`) or duplicated code. **Don't reach for generics** as a default — much idiomatic Go code is monomorphic and clearer for it.

## Syntax

```go
func Map[T, U any](s []T, f func(T) U) []U {
    out := make([]U, len(s))
    for i, v := range s {
        out[i] = f(v)
    }
    return out
}

doubled := Map([]int{1, 2, 3}, func(x int) int { return x * 2 })
strs    := Map([]int{1, 2, 3}, strconv.Itoa)
```

`[T, U any]` declares two type parameters, both constrained to `any` (i.e., no constraint). The compiler infers `T` and `U` from the call site.

### Type Constraints

A constraint is an interface that the type argument must satisfy:

```go
import "cmp"

func Max[T cmp.Ordered](a, b T) T {
    if a > b { return a }
    return b
}
```

`cmp.Ordered` (Go 1.21+) is satisfied by all types that support `<`, `>`, `<=`, `>=` — integers, floats, strings.

Pre-1.21, the equivalent was `constraints.Ordered` from `golang.org/x/exp/constraints`. Newer code should prefer `cmp.Ordered`.

### Custom Constraints

Define a constraint as an interface that lists allowed types or required methods:

```go
type Number interface {
    ~int | ~int32 | ~int64 | ~float32 | ~float64
}

func Sum[T Number](s []T) T {
    var total T
    for _, v := range s { total += v }
    return total
}
```

The `~` (tilde) means "this underlying type, including any defined types based on it":

```go
type Celsius float64

Sum([]Celsius{1.0, 2.0, 3.0})    // works because Celsius's underlying type is float64
                                  // would NOT work without the ~ in the constraint
```

A constraint can also require methods:

```go
type Closable interface {
    Close() error
}

func CloseAll[T Closable](items []T) error {
    var errs []error
    for _, c := range items {
        if err := c.Close(); err != nil {
            errs = append(errs, err)
        }
    }
    return errors.Join(errs...)
}
```

Constraints can mix type sets and method sets:

```go
type Number interface {
    ~int | ~float64
    String() string
}
```

## `comparable`

A built-in constraint satisfied by types that support `==` and `!=`:

```go
func Index[T comparable](s []T, target T) int {
    for i, v := range s {
        if v == target { return i }
    }
    return -1
}
```

`comparable` excludes slices, maps, functions, and structs containing any of those. Go 1.20+ widened it: types like `any` or interface types now also satisfy `comparable`, with the comparison potentially panicking at runtime if the dynamic types are non-comparable.

## Type Inference

Go usually infers type parameters from the function arguments:

```go
Map([]int{1, 2, 3}, func(x int) int { return x * 2 })       // T=int, U=int inferred
Max(3, 5)                                                    // T=int inferred
```

Sometimes you must spell it out:

```go
m := Make[string, int]()        // T1=string, T2=int — when no args carry the type
```

If inference fails with a confusing message, write the type arguments explicitly to find what the compiler expects.

## Generic Types

```go
type Stack[T any] struct {
    items []T
}

func (s *Stack[T]) Push(v T)    { s.items = append(s.items, v) }
func (s *Stack[T]) Pop() (T, bool) {
    var zero T
    if len(s.items) == 0 { return zero, false }
    v := s.items[len(s.items)-1]
    s.items = s.items[:len(s.items)-1]
    return v, true
}

s := &Stack[int]{}
s.Push(1)
s.Push(2)
v, _ := s.Pop()
```

**Methods cannot introduce new type parameters** — they use the type's parameters only. To add behavior with a new type parameter, write a top-level function.

## When to Use Generics

**Reach for generics when:**

- You're writing a container type (`Stack[T]`, `Map[K, V]`, `Set[T]`) — type safety beats `any`
- You have an algorithm that works the same on multiple types (`Map`, `Filter`, `Reduce`, `Min`, `Max`)
- You're avoiding `reflect` for performance or clarity
- Multiple identical types with a different underlying type need shared behavior (use `~T`)

**Don't reach for generics when:**

- A simple interface would do: `func Sort(s sort.Interface)` is fine; you don't need `func Sort[T constraints.Ordered](s []T)` unless you specifically want type safety
- You only have one or two concrete types — write them out
- You're using generics to fake variance/inheritance — Go's type system doesn't have those
- The signature with constraints is significantly harder to read than two separate functions

## `any` Is Now `any`, Not `interface{}`

Go 1.18 introduced `any` as an alias for `interface{}`. Use `any` in new code:

```go
func Print(v any) { fmt.Println(v) }
```

Both `any` and `interface{}` mean exactly the same thing; `any` is the convention.

## Stdlib Generic Helpers (Go 1.21+)

Go 1.21 added `slices`, `maps`, and `cmp` packages built on generics:

```go
import (
    "cmp"
    "slices"
    "maps"
)

slices.Contains(s, x)
slices.Sort(s)                       // for cmp.Ordered types
slices.SortFunc(s, cmp.Compare)
slices.Index(s, x)
slices.Equal(a, b)

maps.Clone(m)
maps.Equal(a, b)
maps.Keys(m)                         // returns iter.Seq[K] in 1.23+
maps.Values(m)                       // returns iter.Seq[V] in 1.23+

cmp.Compare(a, b)                    // -1, 0, +1
cmp.Less(a, b)
```

Prefer these over hand-rolled equivalents.

## Common Pitfalls

- **Reaching for generics by default** — most Go code doesn't need them. Ask whether a simple interface works first.
- **Forgetting `~`** — without the tilde, `type Celsius float64` doesn't satisfy a `float64` constraint.
- **Methods with new type parameters** — illegal. Use a top-level function instead.
- **Confusing `comparable` with `cmp.Ordered`** — `comparable` is for `==`/`!=`; `cmp.Ordered` is for `<`/`>`.
- **Using `any` where a real interface would document intent** — `func Process(v Validator)` beats `func Process[T any](v T)` when you need a method.
- **Inference failures with unhelpful errors** — fall back to explicit type arguments to debug.
- **Generic code is harder to read than monomorphic code** — when in doubt, write it both ways and pick the clearer one.
