# Inventory

Phase 1 (snapshot) and Phase 2 (read what's there) of the workflow. Get them right and the rest is straightforward; get them wrong and you'll either lose work or split changes you don't understand.

## Snapshotting the baseline

The baseline is what makes recovery possible. Without it, you cannot prove the final state matches the start, and you cannot roll back if something goes wrong.

The snapshot is two artifacts:

1. A **baseline tree** — a tree-hash representing every file in the working tree at the start (tracked + untracked). Used for verification.
2. A **baseline stash** — a proper git stash entry containing tracked changes + untracked files. Used for recovery.

They are captured by different primitives because git's stash machinery and tree-hashing have different idea of "everything."

### Why not `git stash create -u`?

The obvious-looking choice would be `git stash create --include-untracked`, but it does *not* produce a single tree containing both tracked changes and untracked files. The resulting stash commit's main tree contains only tracked changes; untracked files are stashed in a separate parent commit (`stash^3`). So `git rev-parse <stash>^{tree}` and `git diff <stash>` both silently miss the untracked files.

This is a real footgun. The skill discovered it during behavioral testing: a run that committed an originally-untracked file produced a HEAD tree that didn't match the `git stash create -u` baseline tree, even though the run was correct. Use the two-artifact approach below instead.

### Capture the baseline tree (verification)

Use an alternate index file to stage everything (tracked + untracked) and write a tree from it. The real index is never touched.

```sh
TMP_INDEX=$(mktemp)
cp "$(git rev-parse --git-path index)" "$TMP_INDEX"
GIT_INDEX_FILE="$TMP_INDEX" git add -A
BASELINE_TREE=$(GIT_INDEX_FILE="$TMP_INDEX" git write-tree)
rm "$TMP_INDEX"
```

`GIT_INDEX_FILE` overrides the index location for that command's process only. After `rm`, no trace remains. The `BASELINE_TREE` SHA is reachable as long as something keeps it from being garbage-collected — wrapping it in a stash (next step) is the easiest way.

Use `git rev-parse --git-path index`, not the literal path `.git/index`. In a linked worktree, `.git` is a *file* containing a `gitdir:` pointer to a per-worktree directory under the main `.git/worktrees/<name>/`, and the index lives there — `cp .git/index` will fail with "Not a directory." `git rev-parse --git-path` resolves the right location regardless of whether you're in the main worktree, a linked worktree, or a submodule.

### Capture the baseline stash (recovery)

`git stash push --include-untracked` captures everything correctly into a proper stash, but it modifies the working tree. The trick is to push and immediately apply, restoring the working tree.

```sh
git stash push --include-untracked --quiet -m "commit-story-baseline-$(date +%s)"
git stash apply --index --quiet stash@{0} 2>/dev/null || git stash apply --quiet stash@{0}
BASELINE_STASH=$(git rev-parse stash@{0})
```

`--index` (preferred) restores the staged-vs-unstaged distinction. If it fails (some stash configurations don't support it cleanly), fall back to a plain `apply` — content is restored, just not the precise staging state. For this workflow, that's fine because Phase 6 will re-stage from scratch anyway.

There is a brief window (microseconds) between `push` and `apply` when the working tree is empty. If the process dies during that window, the user's work is in `stash@{0}` and recoverable manually — not lost.

The timestamp suffix lets you tell concurrent runs apart in `git stash list`. Side benefit: the stash entry pins both `BASELINE_TREE` (transitively reachable through the stash tree's components) and the explicit recovery state, so neither will be garbage-collected.

### Record the starting `HEAD`

```sh
START_SHA=$(git rev-parse HEAD)
```

Used by Phase 7 (`git log "$START_SHA"..HEAD`), Phase 8 (cleanup), and recovery (`git reset --soft "$START_SHA"`).

### Edge cases

- **Nothing to commit.** If `git diff HEAD` is empty *and* `git ls-files --others --exclude-standard` is empty, the working tree matches `HEAD` — stop and tell the user.
- **Detached HEAD.** Works fine for the workflow itself, but warn the user — new commits won't be on a branch and will be unreachable as soon as they `checkout` away.
- **Orphan branch / no commits.** `git rev-parse HEAD` fails. This skill assumes at least one prior commit exists. If `HEAD` doesn't resolve, tell the user to make their initial commit by hand.
- **In-progress merge / rebase / cherry-pick.** Check `git status` for `MERGE_HEAD`, `REBASE_HEAD`, `CHERRY_PICK_HEAD` files in `.git/`. If any are present, abort — the workflow is for a clean editing session, not a paused merge.

## Inventorying the diff

Once the baseline is safe, gather the full picture. Use the porcelain forms — they're stable and machine-parseable.

### `git status --porcelain=v1`

```sh
git status --porcelain=v1
```

Two-character status codes per line. The first column is the *staged* state, the second is the *unstaged* state. Both can be set on the same file.

| Code | Meaning |
|---|---|
| `M ` | Modified, staged |
| ` M` | Modified, not staged |
| `MM` | Modified and staged, then modified again |
| `A ` | Added (new file), staged |
| `??` | Untracked |
| `D ` | Deleted, staged |
| ` D` | Deleted, not staged |
| `R ` | Renamed (staged) — line shows `R  oldpath -> newpath` |
| `C ` | Copied (staged) |
| `UU` | Unmerged (conflict) — abort the workflow |

`--porcelain=v1` is fixed-format and stable across git versions. `--porcelain=v2` is more detailed (includes file mode, object IDs) but harder to parse; reach for it only if you need the extra fields.

### The four `git diff` flavors

```sh
git diff                  # working tree vs. index (unstaged changes)
git diff --cached         # index vs. HEAD (staged changes)
git diff HEAD             # working tree vs. HEAD (everything tracked, staged + unstaged)
git diff "$BASELINE_TREE" # working tree vs. baseline tree (verification)
```

For Phase 2, `git diff HEAD` plus `git ls-files --others --exclude-standard` covers everything the user is about to commit. Untracked files don't show up in `git diff HEAD` — you have to list them separately.

### Untracked files

```sh
git ls-files --others --exclude-standard
```

- `--others` = files not tracked.
- `--exclude-standard` = honor `.gitignore`, `.git/info/exclude`, and core.excludesFile.

Without `--exclude-standard`, you get every ignored file too — `node_modules/**`, build artifacts, log files. Almost never what you want.

To see what `--exclude-standard` is hiding (sometimes a user genuinely *does* want to commit something currently ignored):

```sh
git ls-files --others --ignored --exclude-standard
```

### Deletions

`git status` shows them; `git diff HEAD` shows them as removal hunks. To stage a deletion: `git rm <path>` (or `git add -A <path>`). Do not skip — a missing file in a commit is a deletion in the next.

### Renames

Git doesn't track renames; it detects them at diff time via similarity heuristics. `git status --porcelain` only shows `R` for *staged* renames; for unstaged ones, you'll see `D oldpath` + `?? newpath` (or `M newpath` if the new path was already tracked).

To get rename detection in the diff:

```sh
git diff -M HEAD          # default 50% similarity
git diff -M90% HEAD       # stricter
```

For Phase 6 execution, you can stage a rename by `git add`-ing the new path and `git rm`-ing the old path — git will detect it as a rename in the resulting commit if similarity is above the threshold. Or use `git mv` if the working tree still has the original.

### Binary files

`git diff` summarizes them as `Binary files ... differ`. You cannot meaningfully split a binary change at hunk level — it's all-or-nothing. Group binary changes with a related text change or as their own commit. Detail in [execution.md](execution.md).

## Reading for intent

The diff tells you *what* changed. To write a meaningful commit message, you need to know *why* — which usually requires reading the file (or the relevant function) in context, not just the diff.

A renamed function plus three call-site updates reads as "rename" only if you can see both ends. A new conditional reads as a feature or a fix depending on what bug it addresses. A test reads as "covers feature X" or "pins down bug Y" depending on what it asserts.

Default to reading every changed file (or the changed regions) in Phase 2. The cost is small; the cost of mis-grouping is larger.

## What the inventory output looks like

By the end of Phase 2 you should be able to produce a structured map like:

```
auth.go:
  hunk 1 (lines 12-18): require MFA assertion on /admin/* (theme: SOC2 finding)
  hunk 2 (lines 45-51): rename local var `tk` -> `token` (theme: cosmetic)
  hunk 3 (lines 89-94): require MFA assertion on /billing/* (theme: SOC2 finding)
auth_test.go:
  whole file: tests for MFA requirement (theme: SOC2 finding)
go.sum:
  whole file: dep bumps (theme: lockfile)
internal/parse/id.go:
  new file: parseRequestID helper (theme: feature prep for request-ID propagation)
```

This is the input to Phase 3 (grouping).
