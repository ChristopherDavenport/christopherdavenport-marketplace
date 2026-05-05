# Project Layout — Deep Dive

Go has no enforced project structure, but strong conventions. The goal: packages with single, descriptive purposes, organized so the import graph is acyclic and easy to reason about.

## Package as the Design Unit

A package is the basic unit of API design. Choose package boundaries by *responsibility*, not by *file type*:

```
✗ Layered by file kind                  ✓ Layered by responsibility
project/                                project/
├── models/                             ├── users/
│   ├── user.go                         │   ├── user.go
│   ├── order.go                        │   ├── store.go
│   └── product.go                      │   └── store_postgres.go
├── handlers/                           ├── orders/
│   ├── user.go                         │   ├── order.go
│   ├── order.go                        │   ├── store.go
│   └── product.go                      │   └── handler.go
├── services/                           ├── products/
│   └── ...                             │   └── ...
└── stores/                             └── cmd/
    └── ...                                 └── api/
                                                └── main.go
```

**Right-hand layout:** every concept (`users`, `orders`, `products`) is a self-contained package — model + persistence + handlers all together. Imports flow inward (from `cmd/api` to domain packages); domain packages don't import each other arbitrarily.

**Why:** code that changes together lives together. Adding a field to `User` doesn't ricochet across three top-level directories.

## `cmd/` — Entry Points

Binaries go in `cmd/<name>/`. The package is `main`; the directory name becomes the binary name.

```
cmd/
├── api/
│   └── main.go        # builds to "api" binary
├── worker/
│   └── main.go        # builds to "worker" binary
└── migrate/
    └── main.go
```

Keep `main.go` small: parse flags, wire dependencies, call into your library packages, exit. Logic belongs in importable packages, not in `main`.

```go
// cmd/api/main.go
func main() {
    cfg := config.Load()
    logger := setupLogging(cfg)
    db := setupDB(cfg)

    srv := server.New(cfg, db, logger)
    if err := srv.Run(context.Background()); err != nil {
        logger.Error("server failed", "err", err)
        os.Exit(1)
    }
}
```

If `main` grows beyond a screen, factor out into `internal/<bin>/` packages.

## `internal/` — Private to the Module

Code under any `internal/` directory can only be imported by packages rooted at the parent of `internal/`. Enforced by the compiler.

```
example.com/myservice/
├── internal/
│   └── auth/                  # importable only from within example.com/myservice
└── pkg/
    └── publicutil/            # importable from anywhere
```

**Use `internal/` aggressively.** It's the only way to make a public-import-path package non-importable from outside your module. Default unexported until something needs to be public.

Multiple `internal/` directories are allowed at any level — they limit access to that subtree:

```
example.com/myservice/
├── orders/
│   └── internal/
│       └── pricing/    # only importable from example.com/myservice/orders/...
```

## `pkg/` — Public Library Code (Optional)

`pkg/` is a *convention*, not a Go-toolchain feature. Some projects put exported library code under `pkg/` to clearly separate it from `cmd/` and `internal/`. Others put domain packages at the top level.

**Both are fine.** Pick one and stay consistent. The Go stdlib doesn't use `pkg/`; many Kubernetes-influenced projects do.

## Avoid `util`/`common`/`helpers`/`misc`

These names tell you nothing and become catch-all dumping grounds. Pull contents apart by responsibility:

```
✗ util/
   ├── string.go          → strings (or strutil)
   ├── time.go            → timeutil
   ├── http.go            → httputil
   └── validate.go        → validate (or per-domain validation)

✗ common/                  → split into the actual concepts it conflates
✗ helpers/                 → same
✗ misc/                    → there is no "misc" — name it
```

If a function genuinely fits nowhere, it probably belongs *with the code that calls it*, not in a shared bag.

**Stdlib `*util` packages** (`httputil`, `iotest`, `testing/iotest`) are okay because they have a focused subject. `util` alone is not.

## `testdata/` — Test Fixtures

The Go toolchain ignores any directory named `testdata` for compilation, so you can put any file there:

```
users/
├── store.go
├── store_test.go
└── testdata/
    ├── valid_user.json
    └── invalid_user.json
```

Test code reads from `testdata/` with relative paths — `go test` runs in the package directory.

## `doc.go` — Package Documentation

For packages with many files, put the package comment in a `doc.go` so it's easy to find:

```go
// Package users manages user accounts and authentication.
//
// The package exposes a Store interface backed by either an in-memory
// map (for testing) or a Postgres database. All operations are safe
// for concurrent use.
package users
```

Single-file packages can put the comment on any file, but `doc.go` is the convention in multi-file packages.

## Avoid Circular Imports

Go forbids import cycles. If `package a` imports `b` and `b` imports `a`, the compiler refuses. Cycles indicate that the abstraction is wrong — usually two packages that should be one, or a missing third package that both depend on.

**Resolution patterns:**

- Move shared types to a new lower-level package both depend on
- Use an interface in the consumer to break the dependency
- Combine the two packages

## Layered Design

Imports should flow downward through layers:

```
cmd/<bin>/          ← top: wires dependencies
  ↓
internal/server/    ← HTTP routing, middleware
  ↓
internal/users/     ← domain logic
  ↓
internal/storage/   ← persistence
```

Lower layers don't import upper layers. The `users` package never imports `server`. `storage` never imports `users` (instead, `users` defines a `Storage` interface that `storage` satisfies — see `interfaces-and-embedding.md` for the "interfaces in the consumer" rule).

This layering is enforceable with `golangci-lint`'s `depguard` linter or the simpler `go-cleanarch`.

## Domain Package Shape

A typical domain package contains:

```go
package users

// types.go — domain types
type User struct { ... }

// errors.go — sentinel errors
var (
    ErrNotFound = errors.New("user not found")
)

// store.go — persistence interface
type Store interface { ... }

// service.go — business logic
type Service struct { store Store }
func (s *Service) Register(...) error { ... }

// handler.go — HTTP transport (optional, sometimes its own subpackage)
func RegisterHandlers(mux *http.ServeMux, s *Service) { ... }
```

Test files (`*_test.go`) live alongside, plus `testdata/` for fixtures.

## Multi-Module vs Single-Module

For most projects, **one `go.mod` per repo** is the right answer. Multiple modules complicate versioning, releases, and CI.

Reasons to split into multiple modules:

- A reusable library that should be versioned independently
- A sub-tree with very different release cadence or compatibility needs
- A migration path away from a monorepo

If you do split, use `go.work` for local cross-module development.

## File Organization Within a Package

Common layouts inside one package:

- One file per type (`user.go`, `order.go`)
- One file per concept (`validation.go`, `parsing.go`)
- Group small related types in a single file (`errors.go`, `types.go`)

There's no enforced rule. The bias should be toward small files — when a file gets past ~500 lines, ask if there's a natural split.

## Common Pitfalls

- **`utils`, `common`, `helpers`, `misc` packages** — refactor by responsibility.
- **Layered-by-kind layout** (`models/`, `handlers/`, `services/`) — works at small scale, ossifies at large scale. Prefer domain-grouped layout.
- **Logic in `main`** — keep `main` thin (parse, wire, run). Real code goes in importable packages.
- **Not using `internal/`** — exposing packages publicly that should be private. Default everything to `internal/`; promote when needed.
- **Circular imports** — almost always means the package boundary is wrong. Don't paper over with `interface{}` indirection; redesign.
- **`pkg/` cargo-culted** — adopt `pkg/` if it helps your team, skip it if not. The stdlib does without.
- **Over-splitting into many tiny packages** — each package is overhead (its own doc, its own README of methods). Don't make a package per type.
- **Putting tests under a parallel `tests/` directory** — test files belong next to the code; `_test.go` is the marker.
