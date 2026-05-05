# Testing — Deep Dive

The `testing` package is part of the stdlib. Tests live in files ending `_test.go` in the same directory (and either same or `package_test` package). Run with `go test ./...`.

## Test Function Shape

```go
func TestUserValidate(t *testing.T) {
    u := User{Email: ""}
    if err := u.Validate(); err == nil {
        t.Fatal("expected error for empty email")
    }
}
```

**Conventions:**

- Function name: `Test` + `<Subject>` (must start with a capital after `Test`)
- Single parameter: `*testing.T`
- `t.Fatal` / `t.Fatalf` — log and stop this test
- `t.Error` / `t.Errorf` — log and continue (other assertions in the same test will still run)
- `t.Log` / `t.Logf` — message printed only on failure (or with `-v`)

**Don't use `panic` or `os.Exit` in tests** — `t.Fatal` is the proper exit; it lets cleanup run.

## Table-Driven Tests

The dominant Go test idiom: a slice of test cases, looped with `t.Run`:

```go
func TestParseDuration(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    time.Duration
        wantErr bool
    }{
        {"zero", "0s", 0, false},
        {"seconds", "5s", 5 * time.Second, false},
        {"minutes", "2m", 2 * time.Minute, false},
        {"invalid", "fast", 0, true},
        {"empty", "", 0, true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseDuration(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("err = %v, wantErr %v", err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("got %v, want %v", got, tt.want)
            }
        })
    }
}
```

**Why this dominates:**

- Each case has a name shown in failures (`TestParseDuration/seconds`)
- Adding a case is one line
- `t.Run` lets you target a single case: `go test -run TestParseDuration/seconds`
- Failures don't stop the loop — you see all the failing cases in one run

## `t.Run` — Subtests

`t.Run(name, func(t *testing.T))` creates a nested test. Useful for table-driven tests, grouping related assertions, and parallel subtests.

```go
func TestUser(t *testing.T) {
    t.Run("Validate", func(t *testing.T) { ... })
    t.Run("Save",     func(t *testing.T) { ... })
    t.Run("Delete",   func(t *testing.T) { ... })
}
```

Run a subset: `go test -run TestUser/Save`.

## `t.Helper`

When a function fails on behalf of the test, `t.Helper` makes the failure point at the *caller*, not inside the helper:

```go
func mustOpen(t *testing.T, path string) *os.File {
    t.Helper()                  // <- crucial
    f, err := os.Open(path)
    if err != nil {
        t.Fatalf("open %s: %v", path, err)
    }
    return f
}

func TestRead(t *testing.T) {
    f := mustOpen(t, "testdata/input.txt")    // failure shows this line, not the helper
    defer f.Close()
    ...
}
```

Without `t.Helper`, failures point at the `t.Fatalf` line inside `mustOpen`, which doesn't tell you which caller broke.

## `t.Cleanup`

Register a cleanup function that runs when the test (or subtest) ends — including on failure:

```go
func TestStore(t *testing.T) {
    db := newTestDB(t)
    t.Cleanup(func() { db.Close() })
    ...
}
```

Multiple `t.Cleanup` calls run in LIFO order (like `defer`). Cleanups run after `t.Parallel` tests complete.

**Prefer `t.Cleanup` over `defer`** in test setup helpers — `defer` in the helper runs when the helper returns, which is often *before* the test body. `t.Cleanup` runs at test end.

## `t.Parallel`

Mark a test as parallel-safe. Parallel tests within the same package run concurrently:

```go
func TestThing(t *testing.T) {
    t.Parallel()
    // ... actual test
}
```

**Pitfalls:**

- All tests called from a parallel parent run concurrently with siblings (potentially with different test functions). Shared mutable state will race.
- Pre-Go-1.22 loop variable capture trap: each parallel subtest in a `for` loop sees the *same* loop variable unless you shadow it. Go 1.22+ fixes this for new code:

```go
// Pre-Go-1.22 — every parallel subtest sees the LAST tt
for _, tt := range tests {
    tt := tt    // shadow
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        ...
    })
}

// Go 1.22+ (with go.mod >= 1.22) — no shadow needed
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        ...
    })
}
```

The Go team identified this trap as a primary motivator for the 1.22 loop-variable change.

## Asserting Equality

For non-trivial values (structs, slices, maps), use `github.com/google/go-cmp/cmp`:

```go
import "github.com/google/go-cmp/cmp"

if diff := cmp.Diff(want, got); diff != "" {
    t.Errorf("mismatch (-want +got):\n%s", diff)
}
```

`cmp.Diff` produces a clear, human-readable diff — much better than `reflect.DeepEqual` + manual printing.

For simple values, direct comparison is fine: `if got != want { t.Errorf("got %v, want %v", got, want) }`.

## `testify` — Use Sparingly

`github.com/stretchr/testify` provides `assert` and `require` packages with familiar `assertEquals`-style helpers. It's widely used but not idiomatic in stdlib-style Go.

**Stdlib-style preferred:**

- Bare `if got != want { t.Errorf(...) }` is the Go convention; the message is yours to write
- `cmp.Diff` for complex equality
- `t.Helper` to make custom helpers fail at the call site

**If you adopt testify:**

- Prefer `require` (which calls `t.Fatal`) over `assert` for setup steps where continuing is meaningless
- Be aware that testify's failure messages can obscure what's compared
- Be consistent — pick one style per package

## Golden Files

For tests of large output (formatted text, generated code, JSON), store the expected output in a file and compare:

```go
func TestRender(t *testing.T) {
    got := Render(input)
    goldenPath := "testdata/render.golden"

    if *update {
        if err := os.WriteFile(goldenPath, []byte(got), 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(goldenPath)
    if err != nil { t.Fatal(err) }
    if string(want) != got {
        t.Errorf("output differs from %s; rerun with -update to regenerate", goldenPath)
    }
}

var update = flag.Bool("update", false, "update golden files")
```

`testdata/` is special — `go test` ignores it for compilation, so any file extension works.

## Fuzz Tests (Go 1.18+)

Fuzz tests automatically generate inputs to find edge-case bugs:

```go
func FuzzReverse(f *testing.F) {
    f.Add("hello")           // seed corpus
    f.Add("")
    f.Add("a")
    f.Fuzz(func(t *testing.T, in string) {
        out := Reverse(in)
        if Reverse(out) != in {
            t.Errorf("Reverse(Reverse(%q)) = %q", in, Reverse(out))
        }
    })
}
```

Run as `go test -fuzz=FuzzReverse` — runs forever (or with `-fuzztime=30s`). Crashes are added to `testdata/fuzz/FuzzReverse/`. Future test runs include the regression cases automatically.

## Benchmarks

```go
func BenchmarkReverse(b *testing.B) {
    s := "the quick brown fox jumps over the lazy dog"
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _ = Reverse(s)
    }
}
```

Run: `go test -bench=. -benchmem`. The framework chooses `b.N` to get a meaningful runtime.

**Conventions:**

- Use `b.ResetTimer()` if setup before the loop took time
- `b.ReportAllocs()` (or `-benchmem` flag) shows allocations
- For sub-benchmarks: `b.Run(name, func(b *testing.B) { ... })`
- Compare benchmarks with `benchstat`: `go test -bench=. -count=10 > new.txt; benchstat old.txt new.txt`

## Testable Examples

Functions named `Example*` in `_test.go` files are compiled and run as tests, with output compared to `// Output:` comments:

```go
func ExampleReverse() {
    fmt.Println(Reverse("hello"))
    // Output: olleh
}
```

These appear on pkg.go.dev as documentation examples. They're a great way to document an API and ensure the docs stay correct.

`// Unordered output:` is a variant for output where order doesn't matter (map iteration).

## `_test` Package Variant

A test file's package can be either the package under test (white-box, access to unexported) or `<pkg>_test` (black-box, only exported API):

```go
// users.go
package users

// users_test.go
package users         // can access unexported

// users_external_test.go
package users_test    // can only use exported API; tests the user-facing contract
```

Use `<pkg>_test` for tests that should only depend on the exported API. Useful for catching accidental private-API leakage.

## Test Layout

- Place tests in the same directory as the code they test
- Use `testdata/` for fixtures and golden files
- Use `internal/testutil/` for shared test helpers across packages within a module

## Common Pitfalls

- **Pre-1.22 `t.Parallel` + table-driven loop variable** — every parallel subtest sees the last case. Either set `go 1.22+` in `go.mod` or shadow `tt := tt`.
- **`defer` in a test helper** — runs when the helper returns, often before the test body. Use `t.Cleanup`.
- **Forgetting `t.Helper()`** — failures point inside the helper, not at the caller, making bugs hard to locate.
- **`t.Run` inside `t.Run` deeply nested** — fine in moderation, but at 4+ levels the names become unreadable.
- **Calling `t.Fatal` from a goroutine** — unsafe; only the main test goroutine can call `Fatal`. Use a channel or `t.Errorf` from goroutines.
- **`reflect.DeepEqual` for diffs** — gives no diff output. Use `cmp.Diff`.
- **Reading `testdata/` with relative paths** — fine; `go test` runs in the package directory. Don't try to walk up to find it.
- **Flaky tests due to timing** — never sleep to "wait for" something; poll with a deadline, or use channels.
- **Missing `b.ResetTimer()` after expensive setup** — benchmark numbers include setup, distorting results.
- **Fuzz tests in CI** — short runs find regressions but won't find new bugs without a long fuzz budget. Schedule a separate long-running fuzz job.
