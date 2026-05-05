# Modules & Tooling — Deep Dive

Go modules are the unit of versioning and distribution. A module is a tree of packages with a single `go.mod` at the root. Tooling (`go vet`, `golangci-lint`, `govulncheck`) operates per-module.

## `go.mod`

```go
module example.com/myservice

go 1.22

require (
    github.com/google/uuid v1.6.0
    go.uber.org/zap v1.27.0
)

require (
    github.com/stretchr/testify v1.8.4 // indirect
)
```

**Fields:**

- `module` — the import path callers use (`example.com/myservice`)
- `go` — the *minimum* Go version this module requires; also gates language features (loop-variable scoping changed at `go 1.22`)
- `require` — dependencies and their selected versions
- `replace` — redirect a module to a different source (local path, fork)
- `exclude` — forbid specific versions (rarely needed)
- `retract` — mark versions of *your own* module as withdrawn

## Selecting Versions

`go get` adds and updates dependencies:

```sh
go get example.com/foo                    # latest
go get example.com/foo@v1.2.3             # specific version
go get example.com/foo@latest             # latest tagged
go get -u ./...                           # update all to latest minor/patch
go get -u=patch ./...                     # update all to latest patch only
go mod tidy                               # add missing, remove unused
```

`go mod tidy` is the cleanup tool — run it before committing to ensure `go.mod` and `go.sum` reflect what's actually imported.

## `go.sum`

`go.sum` records the cryptographic hash of every module version your build depends on (directly or transitively). Commit it. The Go toolchain verifies downloads against `go.sum` to detect tampering.

```
github.com/google/uuid v1.6.0 h1:NIvaJDMOsjHA8n1jAhLSgzrAzy1Hgr+hNrb57e+94F0=
github.com/google/uuid v1.6.0/go.mod h1:TIyPZe4MgqvfeYDBFedMoGGpEw/LqOeaOT+nhxU+yHo=
```

If you see `go.sum` mismatches in CI, someone changed `go.mod` without running `go mod tidy`, or a module's content was republished (rare but possible — the toolchain protects you).

## Semantic Versioning + Semantic Import Versioning

Go enforces SemVer for module versions: `vMAJOR.MINOR.PATCH`. **And it bakes the major version into the import path for v2+.**

```go
require github.com/foo/bar v1.5.0           // import path: github.com/foo/bar

require github.com/foo/bar/v2 v2.0.0        // import path: github.com/foo/bar/v2 — note the /v2!
```

When a library bumps to v2, its import path *changes*. Both v1 and v2 can coexist in the same build (they're different modules to Go). This is the "semantic import versioning" rule — major version mismatches are visible at the import statement.

**v0 and v1 share the path.** Pre-v1 (`v0.x.y`) is treated as unstable; the path is `github.com/foo/bar` for both v0 and v1.

## `replace` for Local Development

To work on a dependency in tandem with your module:

```go
require example.com/dep v0.0.0-00010101000000-000000000000

replace example.com/dep => ../dep
```

The fake `v0.0.0-...` version satisfies the require; `replace` redirects to the local checkout.

**Use `replace` for development only.** Don't ship a `go.mod` with a `replace` pointing at a local path — downstream consumers will choke. Most teams strip `replace` directives in CI.

## Workspaces (`go.work`)

For developing across multiple modules at once (e.g., a monorepo with several modules):

```go
// go.work
go 1.22

use (
    ./moduleA
    ./moduleB
    ./internal/sharedlib
)
```

`go.work` overrides the per-module `go.mod` for resolution: edits to `moduleB` are seen by `moduleA` immediately, no `replace` needed. **Don't commit `go.work`** unless your repo is a true workspace; it's a developer-machine artifact in most cases. Add it to `.gitignore` (and `go.work.sum`).

## `go vet`

Static analyzer that catches a curated set of likely bugs: shadowed variables, struct tag typos, lock copies, printf format mismatches, unreachable code. Always run in CI:

```sh
go vet ./...
```

Most Go editors run `vet` on save. CI should fail on any vet finding.

## `golangci-lint`

The dominant Go meta-linter — runs many linters in parallel with shared parsing. Configure with `.golangci.yml`:

```yaml
linters:
  enable:
    - errcheck         # find unchecked errors
    - gosimple         # suggest simplifications
    - govet            # the stdlib analyzer
    - ineffassign      # detect ineffective assignments
    - staticcheck      # comprehensive linting
    - unused           # find unused code
    - gofmt            # ensure gofmt-clean
    - goimports        # ensure imports grouped
```

Run: `golangci-lint run ./...`. Useful flags: `--new-from-rev=origin/main` to lint only changed code, `--fix` to auto-apply fixes.

`staticcheck` is the standout — it finds many real bugs and is usually the first linter teams add.

## `govulncheck`

Scans your code for usage of known-vulnerable Go modules. Different from `go list -m -u` (which just shows updates) — `govulncheck` cross-references CVEs against the Go vulnerability database.

```sh
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...
```

Reports only vulnerabilities that *your code path actually reaches*, reducing noise. Run it in CI on every PR and on a schedule against `main`.

## Build Tags

Conditionally compile files:

```go
//go:build linux && amd64

package osutil
```

Common tags:

- `linux`, `darwin`, `windows`, `freebsd` — `runtime.GOOS`
- `amd64`, `arm64`, `386` — `runtime.GOARCH`
- `cgo` / `!cgo` — whether cgo is enabled
- Custom: `//go:build integration` — enabled with `go test -tags=integration`

Build tag rules:

- `//go:build` (Go 1.17+) is the modern syntax; the old `// +build` is deprecated
- Must appear before `package`, with a blank line between
- File-name suffixes also work: `os_linux.go`, `os_darwin.go` — implicit `linux`/`darwin` tags

## File Name Conventions

- `*_test.go` — test files (`go test` only compiles these in test builds)
- `*_linux.go`, `*_darwin.go`, etc. — implicit OS build tag
- `*_amd64.go`, `*_arm64.go` — implicit arch build tag
- `*_unix.go` — Unix-family build tag (Go 1.19+)
- `doc.go` — by convention, holds the package comment
- `main.go` — by convention, the file with `func main` in `package main`

## `go generate`

Run code generators based on `//go:generate` directives in source files:

```go
//go:generate stringer -type=Color
type Color int
const (
    Red Color = iota
    Green
    Blue
)
```

Run with `go generate ./...`. Common uses: `stringer`, `mockgen`, `protoc`. **Commit the generated files** — `go build` does not run `go generate` automatically.

## `go test` Flags

```sh
go test ./...                      # all packages
go test -run TestUser ./...        # only matching tests
go test -race ./...                # race detector
go test -cover ./...               # coverage summary
go test -coverprofile=c.out ./...  # coverage profile
go tool cover -html=c.out          # render coverage HTML
go test -bench=. ./...             # benchmarks
go test -count=10 ./...            # run each test 10 times (catch flakes)
go test -short ./...               # tests that respect testing.Short() can skip
```

## `go install` vs `go build` vs `go run`

- `go build` — compile to a binary in the current directory
- `go install` — compile and place the binary in `$GOBIN` (defaults to `$GOPATH/bin`)
- `go run` — compile and run, no binary kept

For installing tools: `go install github.com/foo/tool@latest`. Pin the version in CI to ensure reproducible builds: `go install github.com/foo/tool@v1.2.3`.

## Reproducible Builds with `tools.go`

To pin the versions of tools you use during development (linters, generators), declare them in a `tools.go` file with a build tag that excludes it from normal builds:

```go
//go:build tools

package tools

import (
    _ "github.com/golangci/golangci-lint/cmd/golangci-lint"
    _ "golang.org/x/vuln/cmd/govulncheck"
)
```

Then `go.mod` tracks them like any other dependency. Install with `go install <path>`.

Go 1.24 added a more direct `tool` directive in `go.mod` that supersedes the `tools.go` pattern; check `go help mod edit` for current syntax.

## Common Pitfalls

- **Forgetting `go mod tidy`** — `go.mod`/`go.sum` drift; CI breaks. Add `go mod tidy && git diff --exit-code go.mod go.sum` to CI.
- **`replace` in committed `go.mod`** — breaks downstream consumers. Use `go.work` for local cross-module dev instead.
- **v2+ without `/v2` in import path** — the module won't be importable; consumers get confusing errors.
- **Skipping `govulncheck` in CI** — known vulnerabilities sit in production. Cheap to add; high value.
- **Pinning `go.mod` `go` version too low** — modern features (generics, `slog`, loop variable fix) require recent Go. Set this honestly.
- **Editing `go.sum` by hand** — never. Always `go mod tidy`.
- **Running `golangci-lint` without `--new-from-rev`** — every PR re-lints the whole codebase; flagging old code in unrelated PRs is noise. Lint diffs.
- **Build tag placement** — `//go:build` must precede `package` with a blank line. Misplaced tags are silently ignored.
- **`go install` from `main`** — installing `@latest` may pick a fast-moving unstable build. Pin a version.
