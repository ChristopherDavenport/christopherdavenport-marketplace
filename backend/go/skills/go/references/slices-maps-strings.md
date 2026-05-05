# Slices, Maps, Strings — Deep Dive

Slices, maps, and strings are the workhorses of Go. They share a common trap: they look like values but contain reference-like internal state. The bugs come from forgetting that.

## Slice Anatomy

A slice is a 3-word header: `{ptr, len, cap}` pointing at a backing array.

```
slice := []int{10, 20, 30}
              ↓
        ┌────────┐
        │ ptr ●──┼──→ [10, 20, 30, _, _, _]  (backing array)
        │ len 3  │
        │ cap 3  │
        └────────┘
```

`len(s)` is the number of valid elements; `cap(s)` is how many elements the backing array can hold before a re-allocation is needed.

## `make` vs `new` vs Composite Literal

```go
s := make([]int, 5)         // len=5, cap=5, all zeros
s := make([]int, 0, 10)     // len=0, cap=10 — pre-allocated
s := []int{1, 2, 3}         // composite literal — len=3, cap=3
s := []int{}                // empty, non-nil slice
var s []int                 // nil slice
```

`new([]int)` returns `*[]int` to a nil slice — almost never what you want.

**Pre-allocate when you know the length:** `make([]Item, 0, len(input))` then `append` avoids repeated re-allocation.

## `append` Behavior

`append` may or may not allocate, depending on capacity:

```go
s := []int{1, 2, 3}    // len=3, cap=3
s = append(s, 4)       // cap insufficient — new backing array
                       // s is now {1,2,3,4} with len=4, cap=6 (typically)

s := make([]int, 0, 10)
s = append(s, 1, 2, 3) // cap sufficient — no allocation
```

**The result must be assigned back.** `append(s, x)` does not modify `s` in place when it allocates.

### The Aliasing Trap

```go
s := []int{1, 2, 3, 4, 5}
sub := s[:3]                  // {1,2,3}, shares backing array
sub = append(sub, 99)         // cap was 5; this writes into s[3]!

// s is now {1, 2, 3, 99, 5} — surprise mutation
```

When you slice and then append, the appended write may overwrite elements of the original slice if there's spare capacity. Defenses:

```go
sub := slices.Clone(s[:3])    // explicit copy — Go 1.21+
sub := append([]int(nil), s[:3]...) // pre-1.21 idiom
sub := s[:3:3]                // 3-arg slice — caps the result at 3, forces append to reallocate
```

## Nil vs Empty Slice

A nil slice and an empty slice behave almost identically — but they're not equal:

```go
var a []int               // nil
b := []int{}              // empty, non-nil
c := make([]int, 0)       // empty, non-nil

len(a) == 0               // true for all three
cap(a) == 0               // true for all three
a == nil                  // true
b == nil                  // false

append(a, 1)              // works fine
for range a { }           // works fine
json.Marshal(a)           // → "null"
json.Marshal(b)           // → "[]"
```

**Convention:** prefer nil for the "no elements" case in your APIs; reserve empty `{}` only when you specifically want JSON to emit `[]` instead of `null`. The Go Code Review Comments explicitly recommend nil over empty.

## Iteration with Index

When iterating to modify, range with the index:

```go
// ✗ The value v is a COPY; modifying v does not affect the slice
for _, v := range users {
    v.Activated = true
}

// ✓ Index in, address out
for i := range users {
    users[i].Activated = true
}

// ✓ Or store pointers in the slice
users := []*User{...}
for _, u := range users {
    u.Activated = true
}
```

## Maps

```go
m := make(map[string]int)         // empty, ready to use
m := map[string]int{"a": 1}       // composite literal
var m map[string]int              // nil — reads work, writes panic!

m["x"] = 1                        // ✗ panics if m is nil
v := m["missing"]                 // returns zero value (0 for int)
v, ok := m["missing"]             // ok=false if key absent
delete(m, "x")                    // safe even if x absent
```

**Always initialize maps before writing.** A nil map can be read but not written.

### Map Iteration Is Randomized

```go
for k, v := range m {
    // Order is random and varies per iteration — by design
}
```

Go deliberately randomizes map iteration to prevent code from depending on order. If you need a specific order, sort the keys:

```go
keys := make([]string, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
sort.Strings(keys)
for _, k := range keys {
    fmt.Println(k, m[k])
}
```

### Maps Are Not Safe for Concurrent Use

```go
// ✗ data race — concurrent map writes detected
go func() { m["a"] = 1 }()
go func() { m["b"] = 2 }()
```

Options:

- `sync.Mutex` around all access (the simplest)
- `sync.RWMutex` if reads dominate writes
- `sync.Map` *only* if your access pattern matches its sweet spot: keys written once and read many times, or disjoint key sets per goroutine. For most workloads, `Mutex + map` is faster.

### Map Values Are Not Addressable

```go
type Counter struct{ n int }

m := map[string]Counter{"x": {}}
m["x"].n++             // ✗ compile error: cannot assign to struct field

// Workarounds:
v := m["x"]; v.n++; m["x"] = v       // copy, mutate, store
m := map[string]*Counter{"x": {}}    // store pointers — m["x"].n++ works
```

## Strings

Strings in Go are immutable byte sequences (typically UTF-8 but the type doesn't enforce it). A `string` is a 2-word header: `{ptr, len}` to a read-only backing array.

### Range Iterates Runes

```go
s := "héllo"
for i, r := range s {
    fmt.Printf("%d: %c\n", i, r)
}
// 0: h
// 1: é          ← byte index 1, but the rune occupies 2 bytes
// 3: l          ← so the next index is 3, not 2
// 4: l
// 5: o

len(s)             // 6 — bytes, not runes
utf8.RuneCountInString(s) // 5 — actual rune count
```

**`len(s)` is byte count, not character count.** Use `utf8.RuneCountInString` for runes; use `range` to iterate by rune.

### `[]byte` and `string` Conversion

```go
b := []byte("hello")        // allocates and copies
s := string(b)              // allocates and copies
```

Conversion is a copy because `string` is immutable and `[]byte` is mutable. The compiler optimizes some cases (e.g., `string(b)` as a map key) to avoid the allocation.

For high-throughput byte-to-string-to-byte work, hold onto `[]byte` if you can.

### Building Strings — `strings.Builder`

```go
// ✗ Quadratic allocation
s := ""
for _, w := range words {
    s += w + " "
}

// ✓ Linear with strings.Builder
var sb strings.Builder
for _, w := range words {
    sb.WriteString(w)
    sb.WriteByte(' ')
}
s := sb.String()
```

For known-size building, `sb.Grow(n)` pre-allocates. For very simple cases, `strings.Join` is often clearer:

```go
s := strings.Join(words, " ")
```

### `bytes.Buffer` vs `strings.Builder`

- `strings.Builder` — string output only; cheaper because no `[]byte` ↔ `string` round-trip
- `bytes.Buffer` — both `Write` and `Read`; use when you need an `io.Reader`/`io.Writer`

## Slice Modern Helpers (`slices`, `maps`)

Go 1.21 added `slices` and `maps` packages with type-safe generic helpers:

```go
import "slices"

slices.Contains(s, x)
slices.Index(s, x)
slices.Sort(s)                       // for ordered types
slices.SortFunc(s, cmp)              // custom compare
slices.Clone(s)                      // shallow copy
slices.Equal(a, b)
slices.Concat(a, b, c)               // 1.22+
slices.Delete(s, i, j)               // remove range
```

Prefer these over hand-rolled loops or `reflect`-based helpers.

## Common Pitfalls

- **`append` aliasing** — slicing and then appending can mutate the original. Use `slices.Clone` or 3-arg slicing `s[:n:n]` to be safe.
- **Modifying range value** — `for _, v := range slice { v.X = ... }` mutates a copy. Use the index or a slice of pointers.
- **Nil map writes** — `var m map[K]V; m[k]=v` panics. Initialize with `make` or a literal.
- **Map iteration order** — never depend on it; sort keys when needed.
- **`len(string)` for "character count"** — it's byte count. Use `utf8.RuneCountInString`.
- **Concurrent map access** — guard with a mutex; `sync.Map` only when its specific patterns apply.
- **Converting `[]byte` to `string` in a hot path** — every conversion copies. Stay in `[]byte` when you can.
- **String concatenation in a loop** — quadratic. Use `strings.Builder` or `strings.Join`.
- **Forgetting to assign `append` result** — `append(s, x)` returns a possibly-new slice; you must reassign.
- **`s := make([]int, n)` when you meant `make([]int, 0, n)`** — the first creates `n` zero elements; subsequent `append` adds to position `n`, not `0`.
