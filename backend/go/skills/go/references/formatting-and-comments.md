# Formatting & Comments — Deep Dive

## `gofmt` Is the Spec

Go has one canonical formatting, enforced by `gofmt`. There are no debates about brace placement, indentation, or alignment. Run `gofmt -w .` before committing; configure your editor to format on save; configure CI to fail on `gofmt -l .` returning anything.

```sh
gofmt -w .          # Rewrite all .go files in place
gofmt -l .          # List files that would be changed (non-empty exit on diff)
gofmt -d file.go    # Show the diff that would be applied
```

**Key invariants `gofmt` enforces:**

- Tabs for indentation (not spaces)
- Opening brace on the same line as the keyword
- One statement per line
- Blank line between top-level declarations
- Aligned struct field tags within a block
- Removed trailing whitespace, normalized line endings

**Never reformat by hand.** If `gofmt` rewrites your code in a way you dislike, restructure the code — don't fight the formatter.

## `goimports` for Import Hygiene

`goimports` is `gofmt` plus import management: it adds missing imports, removes unused ones, and groups them.

```sh
goimports -w .
```

**Standard import grouping** (separated by blank lines):

```go
import (
    "context"
    "fmt"
    "io"

    "github.com/google/uuid"
    "go.uber.org/zap"

    "example.com/internal/users"
)
```

Order: stdlib → third-party → local. `goimports` does not enforce the local-vs-third-party split automatically; add the `-local example.com/` flag (or use `gci`/`golangci-lint`'s `goimports` integration) to get the third group.

## Doc Comments — Godoc Conventions

Every exported identifier must have a doc comment that begins with the identifier's name.

```go
// Reader is the interface that wraps the basic Read method.
//
// Read reads up to len(p) bytes into p. It returns the number of bytes
// read (0 <= n <= len(p)) and any error encountered.
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

**Rules:**

- Use complete sentences, capitalized, terminated with a period
- The first sentence is the summary that appears in `go doc` listings
- Begin with the identifier name (`Reader is...`, `Read reads...`) so the rendered doc reads naturally
- Use `//` comments, not `/* */`, for doc comments
- Blank `//` lines separate paragraphs in rendered output
- Indent code examples with a tab (or use `[Go]` doc-link syntax in Go 1.19+)

**Don't:**

- ❌ `// Reader.` — too terse, no behavior described
- ❌ `// This function reads...` — should be `// Read reads...`
- ❌ Multiple sentences crammed into one line — break across lines, `gofmt` won't reflow

## Package Comments

Each package must have a package comment, on the `package` declaration of one file (conventionally `doc.go` for multi-file packages):

```go
// Package users manages user accounts and authentication.
//
// The package exposes a Store interface backed by either an in-memory
// map (for testing) or a Postgres database. All operations are safe
// for concurrent use.
package users
```

For `main` packages, document what the binary does:

```go
// Command migrate applies database migrations from a directory of .sql files.
//
// Usage:
//
//     migrate --dir=./migrations --dsn=postgres://...
package main
```

## Doc-Link Syntax (Go 1.19+)

Reference other identifiers with bracketed syntax:

```go
// Validate checks the user against [User.Validate]. It returns
// [ErrInvalid] when the address is malformed.
```

Renders as hyperlinks in `go doc` and pkg.go.dev.

## When to Comment Unexported Code

The exported API needs doc comments. Unexported code needs comments only when:

- The *why* is non-obvious (a workaround, a hidden invariant, a deliberate inefficiency)
- A subtle correctness invariant must be preserved
- Behavior would surprise a reader (intentional ordering, locking required by callers)

**Don't write comments that just restate the code.** `i++ // increment i` is noise.

```go
// Bad — restates the code
// Loop through users
for _, u := range users {
    ...
}

// Good — explains the why
// Process oldest users first so that retries from the prior batch
// see the freshest state when they re-enqueue.
sort.Slice(users, func(i, j int) bool { return users[i].CreatedAt.Before(users[j].CreatedAt) })
```

## Comment Style Conventions

- Use `// TODO(username): description` for tracked work; assign an owner
- Use `// FIXME` sparingly — prefer fixing
- Use `// Deprecated:` (note the colon and capitalization) on the line *before* the doc comment so tooling recognizes it:

```go
// Deprecated: use [NewClientWithOptions] instead.
func NewClient(addr string) *Client { ... }
```

- `// nolint:linter1,linter2` directives must include the linter name; bare `nolint` is rejected by `golangci-lint`

## Build Tags / Constraints

Use `//go:build` (Go 1.17+), not the legacy `// +build`:

```go
//go:build linux && amd64

package osutil
```

Must appear at the top of the file, before the package clause, with a blank line separating it from `package`. `gofmt` (Go 1.17+) writes both forms during the transition window; new code should use only `//go:build`.

## Common Pitfalls

- **Editor not running `gofmt` on save** — diffs will fight you; configure once.
- **Doc comment doesn't start with the identifier name** — godoc still renders it but the leading sentence reads awkwardly. Lint rule: `golint`/`revive`'s `exported` check.
- **Stale doc comments after refactor** — when you rename, search for the old name in comments. Tooling won't catch this.
- **Package comment in the wrong file** — only one file per package needs the package comment; duplicates are a compile error in some toolchains. Conventionally put it in `doc.go`.
- **`//go:build` placement** — must precede `package` with a blank line between. Misplaced constraints are silently ignored.
- **Tabs-to-spaces in editor settings** — Go uses tabs; if your editor inserts spaces you'll fight `gofmt` forever.
- **`nolint` without linter name** — rejected by `golangci-lint`; use `//nolint:errcheck` not `//nolint`.
