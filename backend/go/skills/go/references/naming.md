# Naming — Deep Dive

Names are part of the API surface. They show up in import paths, doc comments, error messages, and IDE completion lists. The Go idiom rewards short, lowercase, single-purpose names — the further from declaration a name is used, the more descriptive it should be.

## Package Names

```go
package users        // ✓ short, lowercase, single word
package httputil     // ✓ short, no underscore
package userpkg      // ✗ stutter — every name will be users.UserStore
package user_utils   // ✗ underscores not idiomatic
package utils        // ✗ meaningless; says nothing about contents
package common       // ✗ same; what's "common" about it?
```

**Rules:**

- Lowercase, single word, no underscores or mixed case
- Should be the same as the directory name (or a meaningful subset)
- Avoid plurals: `package users` not `package usersutil`; the package itself is the noun
- Avoid generic names: `util`, `common`, `helpers`, `misc`, `lib` are anti-patterns
- The package name is part of every exported identifier's qualified name — short package names + descriptive identifiers reads best: `bytes.Buffer`, not `bytespackage.BytesBuffer`

## Avoiding Stutter

The package name prefixes everything you export. Don't repeat it in identifiers:

```go
// In package users
type User struct{...}            // ✓ users.User reads naturally
type Store interface{...}        // ✓ users.Store
type UserStore interface{...}    // ✗ users.UserStore stutters

func New() *Store { ... }        // ✓ users.New()
func NewUserStore() *Store { ... } // ✗ users.NewUserStore() stutters
```

Exception: when an identifier would be ambiguous on its own (e.g., `errors.Error` would clash with the `error` type), let the stutter stand — clarity wins.

## Exported vs Unexported

Capitalization is the access modifier. Capitalize the first letter of an identifier to export it; leave it lowercase to keep it package-private. There's no `private` or `public` keyword.

```go
type User struct {
    ID    int    // exported field
    Email string // exported field
    salt  string // package-private
}
```

## MixedCaps, Not snake_case

```go
var ErrNotFound = errors.New("not found")    // ✓
var maxRetries = 3                           // ✓
var max_retries = 3                          // ✗ underscores
const HTTPTimeoutSeconds = 30                // ✓ acronyms stay capitalized
const HttpTimeoutSeconds = 30                // ✗ acronym should be all-caps
```

**Acronyms** are all uppercase or all lowercase, never camelcase: `URL`, `HTTP`, `JSON`, `userID`, `parseURL`. The whole acronym shifts case together.

## Getter Conventions

Go does not use `Get` prefixes on getters. The field name (capitalized) is the getter:

```go
// ✗ Java-style
func (u *User) GetName() string { return u.name }
func (u *User) SetName(n string) { u.name = n }

// ✓ Go style
func (u *User) Name() string { return u.name }
func (u *User) SetName(n string)        // Set* prefix IS idiomatic for setters
```

`Get` prefixes on getters are discouraged because they add no information — the method name is the property. Setters keep `Set` because they have side effects worth flagging.

## Interface Names

Single-method interfaces typically end in `-er`:

```go
type Reader interface { Read(p []byte) (n int, err error) }
type Writer interface { Write(p []byte) (n int, err error) }
type Closer interface { Close() error }
type Stringer interface { String() string }
```

Multi-method interfaces are named for the abstraction they describe: `http.Handler`, `sort.Interface`, `fs.FS`. The `-er` suffix becomes awkward; use a noun.

## Receiver Names

Receivers should be 1–2 characters, consistent across all methods on the type, and reflect the type:

```go
func (u *User) Validate() error { ... }      // ✓ u for User
func (u *User) Save(ctx context.Context)     // ✓ same receiver name
func (this *User) Validate() error { ... }   // ✗ no `this` or `self`
func (user *User) Validate() error { ... }   // ✗ too long
func (u User) Validate() error { ... }       // ✗ if other methods use *User, mixing breaks method set consistency
```

**Pick the receiver name from the type:** `User → u`, `Server → s`, `httpClient → c`, `Buffer → b`. If two types in a file would clash (`User` and `UserStore` both want `u`), use a longer prefix: `us` for `UserStore`.

## Variable Names — Scope-Sized

Short variable names for short scopes, longer names for longer scopes:

```go
for i, v := range users {           // ✓ i, v are fine in a 3-line loop
    ...
}

func processOrders(ctx context.Context, orders []Order) error {
    for _, o := range orders {
        if err := o.Validate(); err != nil {
            return fmt.Errorf("order %d: %w", o.ID, err)
        }
    }
    return nil
}
```

**Conventions:**

- Loop indices: `i`, `j`, `k`
- Range value: `v` (or a meaningful single letter for the type)
- Receiver: as above
- Error: `err` (always — never `e`, never `error`)
- Context: `ctx`
- A buffered reader: `r` or `br`; a writer: `w` or `bw`
- Functions/parameters with broader scope: full descriptive names

**Don't:**

- Use `data`, `info`, `value`, `result` — these say nothing
- Use `i` for anything but a loop index
- Match Java conventions like `numUsers` or `userList` — prefer `users`

## Error Variable Names

Sentinel errors use the `Err` prefix:

```go
var ErrNotFound = errors.New("not found")
var ErrInvalidInput = errors.New("invalid input")
```

Custom error types use the `Error` suffix:

```go
type ValidationError struct {
    Field string
    Msg   string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Msg)
}
```

## Constants

Constants follow MixedCaps with the same export rules:

```go
const (
    DefaultTimeout = 30 * time.Second  // exported
    maxRetries     = 5                 // unexported
)
```

Avoid SCREAMING_SNAKE_CASE — that's a C convention. `MaxRetries`, not `MAX_RETRIES`.

## Test Names

Test functions: `TestXxx` where `Xxx` does not start with a lowercase letter. Subtests via `t.Run` should be valid Go identifiers (use `_` to spell readable names; Go test will replace with hyphens in the subtest name):

```go
func TestUser_Validate(t *testing.T) {
    t.Run("rejects_blank_email", func(t *testing.T) { ... })
    t.Run("accepts_valid_email", func(t *testing.T) { ... })
}
```

Underscores in test names are an explicit exception to MixedCaps — they're widely used to separate the type from the method (`TestUser_Validate`).

## Common Pitfalls

- **`utils`/`common`/`misc` packages** — pull contents apart by responsibility: HTTP helpers → `httputil`, time helpers → `timeutil`, etc.
- **Stuttering exports** — `users.UserStore` should be `users.Store`. The package name is half the qualified name; use it.
- **Camelcased acronyms** — `parseUrl` should be `parseURL`. `Json` should be `JSON`.
- **`Get` prefixes** — drop them. `u.Name()` not `u.GetName()`.
- **Long receiver names** — use 1–2 chars. `this`/`self` are not idiomatic.
- **Inconsistent receiver kinds** — if any method on `*User` exists, every method should be on `*User`; never mix value and pointer receivers on the same type unless there's a strong reason and you've documented it.
- **`error` shadowed** — never name a local variable `error`; use `err`.
- **Single-letter names with broad scope** — `c` is fine for a `Client` in a 5-line method; not for a package-level variable.
