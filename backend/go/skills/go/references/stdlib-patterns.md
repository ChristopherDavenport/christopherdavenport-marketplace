# Stdlib Patterns — Deep Dive

The Go stdlib is large and well-designed; many third-party packages exist primarily because someone didn't know the stdlib equivalent. This reference covers the highest-leverage stdlib idioms that are easy to get wrong.

## `net/http` — Servers

### Always Set Server Timeouts

The default `http.Server` has *no timeouts*. A client can open a connection and hold it open indefinitely, exhausting your file descriptors.

```go
srv := &http.Server{
    Addr:              ":8080",
    Handler:           mux,
    ReadHeaderTimeout: 5 * time.Second,
    ReadTimeout:       10 * time.Second,
    WriteTimeout:      10 * time.Second,
    IdleTimeout:       60 * time.Second,
}
log.Fatal(srv.ListenAndServe())
```

`http.ListenAndServe(addr, handler)` (the convenience function) constructs a server with no timeouts. **Don't use it in production.**

**Timeout meanings:**

- `ReadHeaderTimeout` — time to read request headers (cheap defense against Slowloris)
- `ReadTimeout` — total time to read the request (headers + body)
- `WriteTimeout` — total time to write the response
- `IdleTimeout` — keep-alive idle timeout

### Routing (`ServeMux`, Go 1.22+)

The stdlib router got a significant upgrade in Go 1.22 — pattern matching with method, path parameters, and host matching:

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /users/{id}", getUser)
mux.HandleFunc("POST /users", createUser)
mux.HandleFunc("DELETE /users/{id}", deleteUser)

func getUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    ...
}
```

Pre-1.22, you needed a third-party router (`gorilla/mux`, `chi`, `httprouter`). For new code on 1.22+, the stdlib router covers most needs; reach for third-party only when you need middleware chaining helpers, regex paths, or route-level rate limits.

### Graceful Shutdown

```go
ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer cancel()

srv := &http.Server{...}

go func() {
    if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
        log.Fatal(err)
    }
}()

<-ctx.Done()
shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()
if err := srv.Shutdown(shutdownCtx); err != nil {
    log.Fatal("forced shutdown:", err)
}
```

`signal.NotifyContext` (Go 1.16+) cancels the context on the listed signals — cleaner than the older `make(chan os.Signal)` pattern.

`srv.Shutdown` waits for in-flight requests to finish (or the context to expire), then returns. Hand it a deadline.

## `net/http` — Clients

### Always Set a Timeout

`http.DefaultClient` has *no timeout*. A misbehaving server will hang your goroutine forever.

```go
client := &http.Client{Timeout: 10 * time.Second}
resp, err := client.Get(url)
```

For per-request control, use `http.NewRequestWithContext`:

```go
req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
if err != nil { return err }
resp, err := client.Do(req)
```

### Always Close `resp.Body`

```go
resp, err := client.Do(req)
if err != nil { return err }
defer resp.Body.Close()
```

Failing to close the body leaks the connection — it cannot be returned to the connection pool. The lint rule `bodyclose` (in `golangci-lint`) catches this.

### Drain Before Closing for Connection Reuse

If you don't read the full body, the connection won't be reused:

```go
defer func() {
    _, _ = io.Copy(io.Discard, resp.Body)
    resp.Body.Close()
}()
```

Important for high-throughput clients hitting the same endpoint.

### Reuse `http.Client`

`http.Client` is safe for concurrent use and pools connections. **Create one, share it.** A new client per request creates a new connection pool every time.

## `encoding/json`

### Struct Tags

```go
type User struct {
    ID        int       `json:"id"`
    Email     string    `json:"email,omitempty"`
    Password  string    `json:"-"`                      // never marshal
    CreatedAt time.Time `json:"created_at"`
}
```

- `json:"-"` hides the field
- `json:",omitempty"` skips when the value is the zero value (nil, "", 0, false, empty slice/map)
- Unexported fields are always skipped

### Decoding Unknown JSON

For payloads with unknown structure, use `map[string]any` or `json.RawMessage`:

```go
var raw map[string]json.RawMessage
if err := json.Unmarshal(data, &raw); err != nil { ... }

if val, ok := raw["typed_field"]; ok {
    var typed MyType
    if err := json.Unmarshal(val, &typed); err != nil { ... }
}
```

`json.RawMessage` defers parsing — useful for polymorphic shapes ("if `type` is `'foo'`, parse `payload` as `Foo`").

### Streaming with `Decoder` / `Encoder`

For large or streamed input/output, `json.NewDecoder(r)` and `json.NewEncoder(w)` work directly with `io.Reader`/`io.Writer`:

```go
dec := json.NewDecoder(r.Body)
dec.DisallowUnknownFields()       // strict mode — fail on extras
var req CreateUserRequest
if err := dec.Decode(&req); err != nil { ... }
```

`DisallowUnknownFields` is a great defense for API request parsing — surface schema mismatches as errors rather than silently dropping data.

### `json.Number` for Numeric Precision

JavaScript treats all numbers as float64; Go does too unless you ask. For large integers (IDs, monetary values) where precision matters:

```go
dec := json.NewDecoder(r.Body)
dec.UseNumber()                   // numbers decoded as json.Number, not float64

var v map[string]any
dec.Decode(&v)
n := v["id"].(json.Number)
i, _ := n.Int64()
```

## `io.Reader` / `io.Writer` Composition

The stdlib's `io` interfaces compose. Most stdlib functions that consume bytes accept `io.Reader`; most that produce bytes accept `io.Writer`. Lean into this.

```go
// Compose: read a gzip'd file
f, _ := os.Open("data.gz")
defer f.Close()
gz, _ := gzip.NewReader(f)
defer gz.Close()
data, _ := io.ReadAll(gz)
```

**Useful helpers:**

- `io.Copy(dst, src)` — stream from a reader to a writer
- `io.ReadAll(r)` — slurp into `[]byte`
- `io.Discard` — `/dev/null` writer
- `io.MultiReader(r1, r2, ...)` — concatenate readers
- `io.TeeReader(r, w)` — read from r, also write to w (logging, hashing)
- `io.LimitReader(r, n)` — read at most n bytes
- `io.Pipe()` — in-memory reader/writer pair, useful for streaming between goroutines

### `bufio` Wrappers

Wrap raw `io.Reader`/`io.Writer` in `bufio.NewReader` / `bufio.NewWriter` to amortize syscalls when doing many small reads/writes.

```go
r := bufio.NewReader(conn)
line, err := r.ReadString('\n')
```

`bufio.Scanner` for line-by-line input:

```go
scanner := bufio.NewScanner(r)
for scanner.Scan() {
    line := scanner.Text()
    ...
}
if err := scanner.Err(); err != nil { ... }
```

Default scanner buffer is 64KB — increase with `scanner.Buffer(buf, max)` if your lines exceed that.

## `crypto/rand` — Use for Security

`math/rand` (and `math/rand/v2`) is **not cryptographically secure**. Never use it for tokens, session IDs, password salts, or anything an attacker shouldn't predict.

```go
import "crypto/rand"

token := make([]byte, 32)
if _, err := rand.Read(token); err != nil {
    return fmt.Errorf("rand: %w", err)
}
encoded := base64.RawURLEncoding.EncodeToString(token)
```

Use `math/rand` only for non-security randomness (jitter, sampling, fuzz inputs).

## `database/sql` — Parameterized Queries

**Never concatenate user input into SQL.** Use placeholders:

```go
// ✗ SQL injection
q := fmt.Sprintf("SELECT * FROM users WHERE email = '%s'", email)

// ✓ Parameterized
row := db.QueryRowContext(ctx, "SELECT * FROM users WHERE email = $1", email)
```

Driver-specific placeholder syntax: `?` for MySQL/SQLite, `$1`, `$2`, ... for Postgres.

### Always Pass `context.Context`

`*sql.DB` methods come in two flavors: `Query`/`Exec` (no context) and `QueryContext`/`ExecContext` (with context). **Use the context variants** — they enable per-query timeouts and cancellation.

### Always Close `Rows`

```go
rows, err := db.QueryContext(ctx, "...")
if err != nil { return err }
defer rows.Close()                  // critical — leaks connection otherwise

for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Email); err != nil { return err }
    users = append(users, u)
}
return rows.Err()                   // surface iteration errors
```

`rows.Err()` returns errors that occurred *during* iteration (e.g., the connection dropped). Easy to forget.

### `sql.DB` Connection Pool Settings

`sql.DB` is a connection pool, not a single connection. Tune it:

```go
db.SetMaxOpenConns(25)              // limit concurrent connections
db.SetMaxIdleConns(5)               // keep-alive pool size
db.SetConnMaxLifetime(5 * time.Minute)  // recycle connections
```

Defaults are unlimited — easy to overwhelm your database.

## `time`

### Avoid `time.Sleep` for "Wait Until X"

`time.Sleep` blocks unconditionally. For waiting on cancellation:

```go
select {
case <-ctx.Done():
    return ctx.Err()
case <-time.After(d):
    // proceed
}
```

`time.After` allocates a timer per call; in tight loops use `time.NewTimer` and `Reset`.

### Prefer `time.Time` Comparisons Over Subtraction

```go
if t1.Before(t2) { ... }
if t1.After(t2) { ... }
if t1.Equal(t2) { ... }                     // handles different time zones correctly

dur := t2.Sub(t1)                           // duration
```

### `time.Now()` in Tests Is a Smell

Inject a clock:

```go
type Clock interface { Now() time.Time }

type realClock struct{}
func (realClock) Now() time.Time { return time.Now() }

type Service struct { clock Clock }
```

In tests, swap in a mock clock. `github.com/jonboulle/clockwork` is a popular helper.

## `os.Exec`, Subprocesses

Use `exec.CommandContext`, not `exec.Command`, so the subprocess is killed when the context is cancelled:

```go
cmd := exec.CommandContext(ctx, "git", "status", "--porcelain")
cmd.Dir = repoDir
out, err := cmd.Output()
```

For stdout + stderr in one buffer: `cmd.CombinedOutput()`.

## Common Pitfalls

- **HTTP server with no timeouts** — `http.ListenAndServe` is fine for demos, dangerous in production. Set timeouts on `&http.Server{}` explicitly.
- **HTTP client with no timeout** — `http.DefaultClient` blocks forever on a hung server. Always set `Timeout`.
- **Forgetting `resp.Body.Close()`** — leaks connections. The `bodyclose` linter catches it.
- **Not draining `resp.Body` before closing** — connection isn't reused.
- **Creating a new `http.Client` per request** — destroys connection pooling.
- **Positional struct literals in `http.Server{}`** — `gofmt` doesn't catch this; use field names.
- **`json:"-omitempty"` instead of `json:",omitempty"`** — the leading comma is required when omitting the name.
- **`math/rand` for security tokens** — predictable. Use `crypto/rand`.
- **String concatenation into SQL** — injection. Always use placeholders.
- **Forgetting `rows.Close()` and `rows.Err()`** — `Close` leaks connections; `Err` hides iteration errors.
- **`time.After` in a hot loop** — allocates a timer each call. Use `time.NewTimer` with `Reset`.
- **`exec.Command` with no context** — orphan subprocesses on cancellation. Use `exec.CommandContext`.
- **Reading entire HTTP body with `io.ReadAll` for large responses** — load into memory unboundedly. Stream with `io.Copy` or set a size limit with `io.LimitReader`.
