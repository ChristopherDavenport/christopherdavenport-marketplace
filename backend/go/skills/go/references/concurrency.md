# Concurrency — Deep Dive

Go's concurrency primitives are goroutines (lightweight threads), channels (typed communication), `select` (multiplexing), and the `sync` package (mutexes, wait groups, atomics). The `context` package provides cancellation and deadlines — it's covered here as the canonical home.

## Goroutines

A goroutine is a function executed concurrently with its caller. Cheap (a few KB of stack), scheduled by the Go runtime onto OS threads.

```go
go func() {
    process(item)
}()
```

### The Lifetime Rule

**Every `go` statement must have a clear answer to "how does this stop?"** Goroutine leaks are unbounded memory leaks.

The three answers:

1. The function returns naturally (does its job, exits)
2. A `context.Context` is cancelled and the goroutine selects on `<-ctx.Done()`
3. A channel is closed and the goroutine selects on it

```go
// ✗ Leak risk — no exit condition if `work` blocks
go func() {
    for {
        msg := <-work
        process(msg)
    }
}()

// ✓ Tied to context cancellation
go func() {
    for {
        select {
        case <-ctx.Done():
            return
        case msg := <-work:
            process(msg)
        }
    }
}()
```

Run `pprof` against `goroutine` to spot leaks; CI should detect new ones.

## Channels

A channel is a typed conduit. `chan T` is bidirectional; `chan<- T` send-only; `<-chan T` receive-only.

```go
ch := make(chan int)        // unbuffered
ch := make(chan int, 10)    // buffered with capacity 10

ch <- 1                     // send (blocks if no receiver and no buffer space)
v := <-ch                   // receive (blocks if nothing to receive)
v, ok := <-ch               // ok=false if channel closed and drained

close(ch)                   // sender side: signals "no more values"
for v := range ch { ... }   // receive until closed
```

### Channel Direction

Restrict the direction in function signatures to make intent explicit:

```go
func produce(out chan<- int) {           // can only send
    defer close(out)
    for i := 0; i < 10; i++ { out <- i }
}

func consume(in <-chan int) {            // can only receive
    for v := range in { ... }
}

ch := make(chan int)
go produce(ch)
consume(ch)
```

### Closing Conventions

**The sender closes — never the receiver.** Closing a channel that's already closed panics. Sending to a closed channel panics.

If multiple senders exist, none of them should close. Use a separate "done" channel or `context.Context` to signal cancellation.

```go
// Pattern: producer closes when done
func produce(out chan<- Item) {
    defer close(out)
    for _, item := range source {
        out <- item
    }
}
```

### Buffered vs Unbuffered

- **Unbuffered:** synchronous handoff — sender blocks until a receiver is ready, and vice versa
- **Buffered:** sender blocks only when the buffer is full; receiver blocks only when the buffer is empty

**Default to unbuffered.** Buffering hides synchronization issues; the buffer size is rarely tuned correctly. Add buffering when you have a specific reason (rate-shaping, bursty producer, known producer/consumer ratio).

A single-element buffer (`make(chan T, 1)`) is the right size for a "slot" pattern (e.g., latest-value, debounce).

## `select`

`select` blocks until one of its cases can proceed; if multiple are ready, one is chosen at random.

```go
select {
case v := <-in:
    process(v)
case out <- result:
    // sent
case <-ctx.Done():
    return ctx.Err()
case <-time.After(5 * time.Second):
    return errors.New("timeout")
default:
    // non-blocking fallthrough
}
```

**Common patterns:**

- Cancellation: `case <-ctx.Done(): return ctx.Err()`
- Timeout: `case <-time.After(d):` (or, better, use `context.WithTimeout`)
- Non-blocking try: `select { case ch <- v: default: }` ("send if possible, else drop")

## `context.Context`

`context.Context` is the standard Go contract for carrying deadlines, cancellation, and request-scoped values across API boundaries.

### The Rules

1. **Pass `ctx` as the first parameter** to any function that does I/O, blocks, or may need to be cancelled
2. **Never store `ctx` in a struct** — it's request-scoped, not object-scoped
3. **Never pass `nil`** — use `context.TODO()` if you genuinely don't have one (mark for follow-up); `context.Background()` for top-level (`main`, tests, init)
4. **Always call `cancel()`** — even when the context completed naturally; `defer cancel()` immediately

### Construction

```go
ctx := context.Background()                              // top of the call tree
ctx := context.TODO()                                    // placeholder; replace later

ctx, cancel := context.WithCancel(parent)                // explicit cancellation
defer cancel()

ctx, cancel := context.WithTimeout(parent, 5*time.Second)
defer cancel()

ctx, cancel := context.WithDeadline(parent, deadline)
defer cancel()

ctx := context.WithValue(parent, key, val)               // request-scoped value
```

### Receiving Cancellation

```go
func work(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()                  // context.Canceled or context.DeadlineExceeded
        case work := <-queue:
            if err := process(ctx, work); err != nil {
                return err
            }
        }
    }
}
```

`ctx.Err()` returns `context.Canceled` (cancelled) or `context.DeadlineExceeded` (deadline passed). Both should propagate.

### `context.WithValue` — Use Sparingly

```go
type ctxKey int
const requestIDKey ctxKey = 0

ctx := context.WithValue(parent, requestIDKey, "abc-123")

id, _ := ctx.Value(requestIDKey).(string)
```

**Rules:**

- The key must be a custom type (not `string`) to prevent collisions
- Values should be request-scoped data only (request ID, user ID, trace span) — not application config or dependencies
- Don't pass functional dependencies through context; pass them explicitly as parameters

## `sync` Primitives

### `sync.Mutex`

Protects shared state. Pair `Lock` with a `defer Unlock`:

```go
type Counter struct {
    mu  sync.Mutex
    val int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.val++
}

func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.val
}
```

**Rules:**

- The mutex protects specific fields — document which (use a comment, or place the mutex above the guarded fields)
- Do not copy a `sync.Mutex` (or any struct containing one) — `go vet` flags this
- Lock as briefly as possible; never hold a lock across a network call or other long operation

### `sync.RWMutex`

Many readers, one writer. Use only when reads vastly outnumber writes — `RWMutex` has higher overhead than `Mutex`, so for balanced workloads, plain `Mutex` is faster.

```go
mu.RLock()        // many can hold simultaneously
defer mu.RUnlock()
```

### `sync.WaitGroup`

Wait for a set of goroutines to finish:

```go
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()
```

**Rules:**

- Call `Add` *before* the `go` statement (calling it inside the goroutine races with `Wait`)
- Always `defer wg.Done()` so panics don't leave the WaitGroup hung
- Pre-1.22, capture the loop variable explicitly (`func(item Item)` parameter as above)

### `sync.Once`

Run something exactly once across all callers:

```go
var (
    once   sync.Once
    config *Config
)

func GetConfig() *Config {
    once.Do(func() {
        config = loadConfig()
    })
    return config
}
```

For "init on first use" patterns. The function passed to `Do` runs exactly once even with concurrent callers.

### `sync/atomic`

Lock-free atomic operations on integers and pointers. Use for counters and flags where a mutex would be overkill:

```go
import "sync/atomic"

var n atomic.Int64
n.Add(1)
v := n.Load()
n.Store(0)

var ready atomic.Bool
ready.Store(true)
if ready.Load() { ... }
```

The Go 1.19+ generic types (`atomic.Int64`, `atomic.Pointer[T]`, etc.) are preferred over the older free functions (`atomic.AddInt64`).

## Channels vs Mutexes — Decision Guide

Both channels and mutexes solve concurrency problems. The choice:

| Use Channels When | Use Mutex When |
|---|---|
| Transferring ownership of data between goroutines | Protecting shared state read & written by many |
| Coordinating goroutine lifecycle (start/stop signals) | Maintaining invariants across multiple fields |
| Implementing a pipeline (producer → consumer) | A simple counter, cache, or registry |
| Composing with `select` (timeouts, cancellation) | Read-modify-write of a single field |

The Go proverb: *"Don't communicate by sharing memory; share memory by communicating."* But mutexes are not anti-Go — for guarded fields, they're often simpler and faster than channels.

## Race Detector

Run tests with `-race` in CI:

```sh
go test -race ./...
go run -race ./cmd/server
```

The race detector instruments memory accesses and reports concurrent unsynchronized read/write. **It only finds races that actually occur during the run** — coverage of concurrent paths in tests matters.

A race detected by `-race` is a real bug, even if it appears benign.

## Patterns

### Worker Pool

```go
func runWorkers(ctx context.Context, n int, jobs <-chan Job) {
    var wg sync.WaitGroup
    for i := 0; i < n; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case <-ctx.Done():
                    return
                case j, ok := <-jobs:
                    if !ok { return }
                    process(j)
                }
            }
        }()
    }
    wg.Wait()
}
```

### Fan-Out / Fan-In

```go
// Fan-out
out := make(chan Result, len(items))
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        out <- compute(item)
    }(item)
}
go func() { wg.Wait(); close(out) }()

// Fan-in: consume out
for r := range out {
    handle(r)
}
```

### `errgroup`

`golang.org/x/sync/errgroup` simplifies "run N tasks concurrently, fail fast on the first error":

```go
import "golang.org/x/sync/errgroup"

g, ctx := errgroup.WithContext(ctx)
for _, url := range urls {
    url := url    // pre-1.22 capture
    g.Go(func() error {
        return fetch(ctx, url)
    })
}
if err := g.Wait(); err != nil {
    return err
}
```

`g.Go` registers a task; `g.Wait` blocks until all complete. The first non-nil error cancels the shared context, which signals other tasks to abort.

## Common Pitfalls

- **Goroutine leak** — `go func()` with no exit condition. Always tie to context or a closed channel.
- **Closing a channel from the receiver** — receivers should not close. The sender closes; if multiple senders, none of them.
- **Send on closed channel** — panics. Synchronize closing with `sync.Once` or context cancellation.
- **Storing `context.Context` in a struct** — breaks the request-scoped contract; pass it as a parameter.
- **Passing `nil` context** — use `context.TODO()` or `context.Background()`.
- **Forgetting `defer cancel()`** — leaks the timer/context resources.
- **Locking and then doing I/O** — holds the lock too long. Acquire data, release lock, then do the slow thing.
- **Copying a `sync.Mutex`** — splits the lock into two unrelated locks. `go vet` flags this; pass pointers.
- **`WaitGroup.Add` inside the goroutine** — races with `Wait`. Call `Add` before `go`.
- **Reading a map concurrently with a write** — race; use a mutex or `sync.Map` (carefully).
- **Pre-1.22 loop variable capture in `go func()`** — every goroutine sees the final value. Either set `go 1.22+` in `go.mod` or capture explicitly.
- **`time.After` in a loop** — leaks a timer per iteration; use `time.NewTimer` with `Reset` if you need to.
