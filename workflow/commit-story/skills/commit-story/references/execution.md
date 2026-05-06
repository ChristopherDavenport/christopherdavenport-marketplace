# Execution

Phase 6. The plan is approved; now run it. Forward-only operations on the index and working tree, one commit at a time.

## The base loop

For each planned commit, in order:

```sh
# Stage the right subset (whole-file or hunk-level — see below).
# Commit with -F:
git commit -F /tmp/cs-msg-N
```

That's the entire shape. Everything else is variations on "stage the right subset."

## Whole-file commits

The simplest case. The commit's content is "all current changes to these files."

```sh
git add path/a.ts path/b.ts                  # adds whatever is currently in the working tree
git commit -F /tmp/cs-msg-1
```

Notes:

- `git add` on a tracked file with both staged and unstaged changes stages the working-tree state — including any earlier staged content. That's what you want.
- `git add` on an untracked file makes it tracked.
- For a file deletion, use `git rm <path>` (or `git add -u <path>`, which stages the deletion). Don't try to `git add` a missing file — it errors.
- For a rename, the cleanest path is `git mv old new` *if* the working tree still has the original. If you've already moved the file by hand, `git add new && git rm old`, then commit — git's rename detection will combine them in the commit's diff (as long as similarity is above the threshold, default 50%).

## Hunk-level commits

When one file mixes concerns and you need only a subset of its hunks in this commit.

### Step 1: Generate a patch containing the desired hunks

Start by writing the full diff for the file, then keep only the hunks you want:

```sh
git diff -- path/auth.go > /tmp/cs-full.patch
```

A unified diff has this structure:

```
diff --git a/path/auth.go b/path/auth.go
index abc1234..def5678 100644
--- a/path/auth.go
+++ b/path/auth.go
@@ -12,7 +12,11 @@ func handleAdmin(...) {       <-- hunk 1 header
 (context line)
 (context line)
-(removed line)
+(added line)
 (context line)
@@ -45,5 +49,5 @@ func someHelper(...) {        <-- hunk 2 header
 (context line)
-(old line)
+(new line)
 (context line)
@@ -89,7 +93,11 @@ func handleBilling(...) {     <-- hunk 3 header
 ...
```

To keep only hunk 2:

1. Keep the `diff --git`, `index`, `---`, `+++` header lines (the file header, four lines).
2. Delete hunk 1 (everything from its `@@` header up to but not including the next `@@`).
3. Keep hunk 2 (its `@@` header and all lines until the next `@@`).
4. Delete hunk 3 (its `@@` header through end of file).

The result is a valid unified diff containing one hunk.

For programmatic splitting, use a small filter script or `git diff -U0` (zero context) to make hunks easier to isolate, then re-add context if needed. In practice, editing the file with the Edit tool to drop the unwanted hunks is the most reliable approach.

### Step 2: Apply the patch to the index only

```sh
git apply --cached /tmp/cs-hunk2.patch
```

`--cached` stages the patch into the index without touching the working tree. The working tree still has all the original hunks; the index now has only hunk 2 staged.

```sh
git commit -F /tmp/cs-msg-1
```

### Step 3: The remaining hunks become subsequent commits

After the commit, the index is clean again, but the working tree still differs from `HEAD` by the unstaged hunks. The next commit either takes them all (`git add path/auth.go`) or another hunk-level subset (repeat steps 1-2 with the new diff).

### When `git apply --cached` fails

Most failures: the patch's line numbers don't match the current working-tree state. Causes:

- The working tree changed since you generated the patch (an earlier commit in this run staged some of the same file). Fix: re-derive the patch from the current `git diff` output.
- Line endings differ (CRLF vs. LF, or trailing whitespace). Fix: regenerate the patch with `git diff` directly into a file (don't paste through a tool that normalizes whitespace).
- The patch was hand-edited and you accidentally removed a context line or changed the `@@` header's line counts. Fix: use `git apply --check /tmp/cs-hunk2.patch` to validate before committing; the error message names the line.

Last resort: `git apply --cached --3way /tmp/cs-hunk2.patch` falls back to a 3-way merge, which can succeed when straight `apply` fails — but it's also more likely to apply something subtly wrong. Prefer re-deriving the patch.

## Special cases

### Renames

Pure rename, no content change:

```sh
git mv old/path.go new/path.go
git commit -F /tmp/cs-msg-1
```

If the rename happened in the working tree before the run started (Git sees it as `D old` + `?? new`):

```sh
git add new/path.go
git rm old/path.go
git commit -F /tmp/cs-msg-1
```

`git status` after staging should show `R old/path.go -> new/path.go` if rename detection succeeded.

Rename + edit in the same commit (avoid if possible — it complicates rename detection):

```sh
git mv old/path.go new/path.go        # or git add new + git rm old
# (edits to new/path.go are already in the working tree)
git add new/path.go                    # stage the edits
git commit -F /tmp/cs-msg-1
```

### Deletions

```sh
git rm path/dead.go
git commit -F /tmp/cs-msg-1
```

If the file is already gone from the working tree (user `rm`'d it manually), `git rm` still works. Or `git add -u path/dead.go` to stage the deletion that `git status` is showing as ` D`.

### Binary files

You cannot meaningfully split binary changes at hunk level. Stage the whole file:

```sh
git add path/icon.png
git commit -F /tmp/cs-msg-1
```

Group binary changes with a related text change (the code that uses the new asset) or in their own commit.

### New files

```sh
git add path/new.go
git commit -F /tmp/cs-msg-1
```

If you want only some of the new file's content (rare — usually a new file is one logical unit), use the hunk-level approach: generate a patch with `git diff --no-index /dev/null path/new.go` and edit it like any other patch.

## Pre-commit hook failures

When a commit fails because a pre-commit hook rejected it, the commit did not happen. The index still has the staged content; the working tree is unchanged. **Do not `--amend`** — there's nothing to amend, the prior commit is the previous commit in your sequence (or `START_SHA`).

Common causes mid-sequence:

- The partial state at this commit doesn't pass the hook (e.g., a test commit lands before the code commit it depends on, and the test runs at pre-commit time — fails because the code isn't there yet).
- Lint/format hook insists on changes that weren't part of the user's diff.

Fix the cause and create a new commit:

1. **Wrong order.** Adjust the plan — re-present to the user, then execute the corrected sequence from the failed commit forward.
2. **Hook auto-modifies files.** The hook may have written changes (e.g., `prettier --write` ran and changed something). Inspect with `git status`. Either fold those changes into the current commit (`git add` them, retry `git commit`) or, if they're unrelated, stash them temporarily and let the hook know to skip — but never `--no-verify`.
3. **Hook flags a real issue.** The user's code has a lint error or a failing test. Stop and tell the user; this is real feedback.

## Message file management

Write each commit message to its own temp file in Phase 4 before execution starts. That way Phase 6 is just `git commit -F`, with no inline string-handling in the middle of the loop.

```sh
cat > /tmp/cs-msg-1 <<'EOF'
Subject line

Body paragraph one.

Body paragraph two.
EOF
```

Use `'EOF'` (single-quoted) to disable shell expansion. After the run, clean up: `rm -f /tmp/cs-msg-* /tmp/cs-patch-* /tmp/cs-untracked`.

## What to do after each commit

After every `git commit`:

1. Check the exit code. Non-zero = hook failure or other error; do not proceed.
2. Optional: `git log -1 --stat` to confirm the commit landed with the expected files.
3. Move to the next planned commit.

After the last commit, jump to Phase 7 (verification). Do not skip — the whole point of this skill is the guarantee that the final state matches the start.
