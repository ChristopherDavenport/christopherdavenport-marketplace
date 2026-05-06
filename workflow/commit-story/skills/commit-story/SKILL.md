---
name: commit-story
description: >
  Take a batch of uncommitted work and split it into a sequence of meaningful
  commits with reviewer-grade messages, while guaranteeing the final tree is
  byte-identical to the starting tree. Use when the user says "split this into
  commits", "commit this in pieces", "make a PR-ready history", "break this up
  before I push", or arrives with a large mixed working tree and asks for
  commits. Plans the commit sequence, presents it for approval, executes
  whole-file or hunk-level splits via `git apply --cached`, and verifies the
  result with diff and tree-hash comparisons. Snapshots the baseline as a
  stash up front so any failure can be safely rolled back. Not for rewriting
  already-committed history (use interactive rebase), opening PRs, pushing,
  or resolving merge conflicts.
---

# Commit Story

A working tree at the moment of "I'm ready to commit" usually contains more than one logical change. Two refactors, a fix the user noticed along the way, the test for the fix, a few format tweaks the editor saved on the way past. The diff is the truth of *what* changed; a single squashed commit erases *why* it happened that way and in what order. A reviewer reading the eventual PR has to reverse-engineer the narrative from the diff itself.

This skill turns that batch into a story. It reads the diff, plans a sequence of small themed commits with messages that explain the *why*, gets the user's approval, and then executes the splits — using `git apply --cached` for hunk-level slicing when one file mixes concerns. The terminal state is byte-identical to the start: the tree-hash of the new `HEAD` equals the tree-hash of the working tree at the start, and `git diff` against the original `HEAD` is the same diff it always was. The only thing that changed is that there is now a coherent commit history a reviewer can read top-to-bottom.

## Scope

**Covers.** Splitting a batch of uncommitted work — modified, staged, untracked, deleted, renamed files — into a planned sequence of small, themed commits with messages that explain the *why*. Includes hunk-level splits when one file mixes concerns. Includes an up-front snapshot stash and an end-of-run verification that proves the final state matches the start. Includes a recovery path that restores the baseline if anything goes wrong.

**Out of scope.** Rewriting already-committed history (`git rebase -i`, `git filter-repo`), pushing, opening or updating PRs, resolving merge conflicts, pulling changes from a remote, or any operation that touches commits other than the new ones this skill creates. Those are adjacent workflows; do not let scope creep pull them in.

## When This Skill Is Triggered

- User says some variation of: "split this into commits", "commit this in pieces", "break this up before I push", "make me a PR-ready commit history", "commit this with a story", "make these into proper commits".
- User has a non-trivial working tree (multiple files, mixed concerns) and asks for commits without specifying a single message.
- User asks Claude to commit work and the diff is large enough that a single commit would obscure the change.

Do *not* trigger for: single-file trivial changes (just commit), explicit single-commit requests ("commit this as one commit"), or work that's already been committed (different workflow).

## Core Rules

These hold in every run. Internalize them before reading the workflow.

- **Snapshot first, touch nothing else.** The first action of every run is to capture two things: a *baseline tree* (for verification) and a *baseline stash* (for recovery). Build the tree via an alternate index file so the real index is never modified; build the stash via `git stash push --include-untracked` followed immediately by `git stash apply --index` (which restores the working tree). Also record the starting `HEAD` SHA. Without these, there is no safe rollback. **Don't** use `git stash create -u` — despite the flag, it does not capture untracked files into a single tree, and verification will silently miss them.
- **The final tree must equal the starting tree, byte for byte.** This is the definition of correctness for this skill. Verify with both a `git diff` check (`git diff <baseline-tree>` is empty) and a tree-hash check (`git rev-parse HEAD^{tree}` equals the captured `BASELINE_TREE`). If either fails, jump to recovery.
- **Plan first, execute second. Never the other way around.** Always present the proposed commit sequence — order, files/hunks per commit, full message bodies — and wait for the user's explicit approval before running any `git add` or `git commit`. The cost of one round-trip to confirm is negligible; the cost of a wrong split is rewriting commits the user has to inspect.
- **Each commit must be independently meaningful.** A reviewer should be able to read a single commit's subject + body + diff and understand it without the surrounding context. Refactors come before the features that use them; helpers come before callers; types come before implementations; format/lint noise gets its own commit.
- **Commit messages explain the *why*, not the *what*.** The diff already shows the *what*. The body should name the constraint, motivation, prior incident, ticket, or design decision that justifies the change. "Add retry to fetchUser" is a *what*; "Add retry to fetchUser — upstream returns 503 during their nightly index rebuild and we need to be tolerant of it" is a *why*.
- **Match the repo's existing commit voice.** Read `git log --oneline -20` and `git log -5` (full bodies) before drafting. If the repo uses Conventional Commits (`feat:`/`fix:`/`refactor:`), use them. If it doesn't, don't impose them. Match imperative vs. past tense, line lengths, body conventions.
- **Forward-only operations only.** During execution, never `--amend`, never `git reset --hard`, never `git checkout --`, never `git clean -fd`. Only `git add`, `git apply --cached`, `git rm`, `git commit`. The recovery path uses `git reset --soft` (which preserves the index/working tree) plus `git stash apply`.
- **Never skip hooks or signing.** No `--no-verify`, no `--no-gpg-sign`. If a pre-commit hook fails mid-sequence, that means the partial state at that commit doesn't pass the hook — fix the cause (often a small adjustment to which hunks belong to which commit), re-stage, and create a new commit. Do not `--amend`.
- **Hunk-level splits use `git apply --cached`, never `git add -p`.** There is no TTY here. Write the desired patch to a temp file (only the hunks for this commit, valid unified diff format), then `git apply --cached <patch>`. If the patch fails to apply, re-derive it from the current working-tree state — don't paper over the failure.
- **If verification fails, stop and restore.** Don't try to "fix forward". Run the recovery procedure (reset commits, restore stash, leave the user where they started), then report exactly what diverged so the user can investigate.

## Workflow

A run proceeds in eight phases. Do not skip phases or reorder them.

### Phase 1 — Snapshot

Before reading anything substantive, capture the baseline. Two artifacts: a tree-hash for verification (built without touching the real index) and a stash for recovery (which briefly empties and immediately restores the working tree).

```sh
START_SHA=$(git rev-parse HEAD)

# 1. Baseline tree — alt-index, captures tracked + untracked, no side effects.
TMP_INDEX=$(mktemp)
cp "$(git rev-parse --git-path index)" "$TMP_INDEX"
GIT_INDEX_FILE="$TMP_INDEX" git add -A
BASELINE_TREE=$(GIT_INDEX_FILE="$TMP_INDEX" git write-tree)
rm "$TMP_INDEX"

# 2. Recovery stash — push -u captures everything, apply restores immediately.
git stash push --include-untracked --quiet -m "commit-story-baseline-$(date +%s)"
git stash apply --index --quiet stash@{0} 2>/dev/null || git stash apply --quiet stash@{0}
BASELINE_STASH=$(git rev-parse stash@{0})

git ls-files --others --exclude-standard > /tmp/cs-untracked
```

If both `git diff HEAD` is empty and `git ls-files --others --exclude-standard` is empty, there is nothing to commit — stop and tell the user. See [references/inventory.md](references/inventory.md) for why this two-step approach is needed (`git stash create -u` does not actually capture untracked files into a single tree).

### Phase 2 — Inventory

Gather the full picture.

```sh
git status --porcelain=v1
git diff HEAD                       # all unstaged changes (modifications + deletions)
git diff --cached                   # staged changes
git ls-files --others --exclude-standard   # untracked files
```

For each changed file, read it (or the relevant section of it) to understand intent. The diff alone often hides intent — a renamed function plus its three new callers reads as "rename" only if you can see both ends. Build a structured map in your head (or in a scratch note): file → hunks → semantic purpose. Detail in [references/inventory.md](references/inventory.md).

### Phase 3 — Group

Cluster the inventory into commit candidates by semantic theme. Heuristics (full list in [references/grouping.md](references/grouping.md)):

- **Dependency direction:** the helper goes before its caller; the type before its implementation; the migration before the code that uses the new column.
- **Behavior vs. mechanical:** a rename or a reformat is its own commit, separate from any behavior change in the same file. Reviewers can skim the mechanical one and focus on the behavioral one.
- **Tests with their code, unless the test surfaces an existing bug.** A new feature and its tests are one commit (or two adjacent commits if the feature is large). A test that pins down a bug *before* the fix is its own commit, then the fix.
- **Generated/lockfile changes get their own commit.** `package-lock.json`, `go.sum`, `pnpm-lock.yaml`, generated protobufs — separate, with a message that names the upstream change.
- **Renames separate from edits.** A pure file rename should not also include unrelated edits to the renamed file.

### Phase 4 — Draft messages

For each commit, draft subject + body following [references/commit-messages.md](references/commit-messages.md):

- Subject: imperative, ≤72 characters, no trailing period, matches the repo's prefix convention (or no prefix).
- Body: blank line after subject, then 1-3 short paragraphs explaining the *why*. Reference issues/tickets if the user mentioned them. Skip the body only for commits where the subject is genuinely self-explanatory (e.g., `Run gofmt`).
- Match the tone of `git log -5` in the current repo.

### Phase 5 — Confirm

Present the planned sequence to the user and wait for approval. Format:

```
Planned commits (against <START_SHA>):

1. <subject-1>
   Files: path/a.ts, path/b.ts
   Why: <one-line rationale>

2. <subject-2>
   Files: path/c.ts (hunks 2-3 only)
   Why: <one-line rationale>

...

Full commit messages:

--- 1 ---
<full subject + body>

--- 2 ---
<full subject + body>
```

If the user wants changes (different grouping, different messages, different order), revise and re-present. Never proceed without explicit approval.

### Phase 6 — Execute

For each planned commit in order, in the order planned:

```sh
# Whole-file commits:
git add path/a.ts path/b.ts
git commit -F /tmp/cs-msg-1

# Hunk-level commits:
# (write a unified-diff file containing only the hunks for this commit, then:)
git apply --cached /tmp/cs-patch-2
git commit -F /tmp/cs-msg-2

# Renames: git handles them via add+rm of the old path and add of the new path,
# or via `git mv` if the working tree still has the original.
```

Use `-F <file>` for messages, never `-m "..."` strings — `-F` preserves formatting and avoids any HEREDOC quoting hazards. Detail in [references/execution.md](references/execution.md).

If a hook fails on a commit, the commit did not happen. Investigate the failure (often the partial state at that commit doesn't pass — e.g., the test commit lands before the code commit it depends on). Adjust the plan, present the change to the user, then continue.

### Phase 7 — Verify

Three independent checks, all must pass:

```sh
# 1. Diff vs. baseline tree is empty (working tree matches captured everything-tree):
git diff "$BASELINE_TREE" --

# 2. Working tree is clean (no leftover modifications, no leftover untracked):
git status --porcelain

# 3. Tree-hash matches the captured baseline tree-hash:
test "$(git rev-parse HEAD^{tree})" = "$BASELINE_TREE"
```

Detail in [references/verification.md](references/verification.md). If any check fails, jump to recovery.

### Phase 8 — Cleanup

Only after verification passes, drop the baseline stash:

```sh
# Find the stash entry by its message (don't trust stash@{0} — other stashes may have shifted positions).
STASH_REF=$(git stash list | awk -F: '/commit-story-baseline-/ {print $1; exit}')
git stash drop "$STASH_REF"
rm -f /tmp/cs-untracked /tmp/cs-msg-* /tmp/cs-patch-* /tmp/cs-state
```

Report the new commit list to the user (`git log "$START_SHA"..HEAD --oneline`).

## Examples

### Example 1 — Refactor + bugfix + test (3 commits, file-level)

User's working tree: 6 files modified. Reading them shows: 4 files are a mechanical rename of `fetchUser` → `loadUser` (the rename + every call site), 1 file fixes a null-deref in `loadUser` itself, and 1 file is a new test pinning the null-deref behavior.

Plan:

1. **Rename `fetchUser` → `loadUser`** — mechanical rename across 4 files, no behavior change. Why: `loadUser` matches the verb conventions used elsewhere in the data layer (`loadAccount`, `loadSession`).
2. **Fix null-deref in `loadUser` when row is missing** — 1 file. Why: production logs (ticket #842) show the deref happening when the user_id is valid but the row was archived; we should return a typed Not-Found, not panic.
3. **Add test for `loadUser` returning Not-Found on missing row** — 1 file. Why: pin the new behavior so a future revert of the fix is caught.

Execute with `git add` per file group, commit with `-F` for each message. Verify. Done.

### Example 2 — Feature + format noise (4 commits, mixed)

User's working tree: a new feature plus the editor reformatted two unrelated files on save.

Plan:

1. **Run gofmt on `internal/x/y.go` and `internal/p/q.go`** — pure formatting, no behavior change. (No body — subject is self-explanatory.)
2. **Extract `parseRequestID` helper** — refactor in preparation for the feature; new helper, no caller yet. Why: the feature commit needs a single function it can call from multiple paths; extracting first keeps the feature commit focused on the new behavior.
3. **Add request-ID propagation through the API handlers** — the actual feature, calling `parseRequestID`. Why: ticket #1023 — distributed traces need a stable request ID across our service boundary.
4. **Add tests for request-ID propagation** — Why: cover the three handler entrypoints and the missing-header case.

### Example 3 — One file mixes two concerns (hunk-level split)

User's working tree: `auth.go` has 3 hunks. Hunks 1 and 3 add a new `requireMFA` check; hunk 2 is an unrelated rename of an internal variable.

Plan:

1. **Rename `tk` → `token` in `auth.go`** — pure rename of a local. (Hunk 2 only.)
2. **Require MFA on privileged endpoints** — Hunks 1 and 3. Why: SOC2 finding from this quarter; privileged endpoints must require a fresh MFA assertion.

Execution for commit 1:

```sh
# Synthesize a patch containing only hunk 2:
git diff -- auth.go > /tmp/cs-full.patch
# Edit /tmp/cs-full.patch to keep only hunk 2 (or use `git diff -U0` and a hunk-extracting script).
git apply --cached /tmp/cs-hunk2.patch
git commit -F /tmp/cs-msg-1
```

For commit 2: `git add auth.go` (the remaining unstaged hunks) → `git commit -F /tmp/cs-msg-2`.

Detail in [references/execution.md](references/execution.md).

## Troubleshooting

| Symptom | Reference |
|---|---|
| Verification fails — `git diff <baseline-stash>` is non-empty after all commits | [references/verification.md](references/verification.md) + [references/recovery.md](references/recovery.md) |
| Pre-commit hook rejects a commit mid-sequence | [references/execution.md](references/execution.md) (the "fix and new commit, never `--amend`" rule) |
| Untracked files accidentally pulled in (or excluded when they shouldn't be) | [references/inventory.md](references/inventory.md) (the `--others --exclude-standard` distinction; `.gitignore` interactions) |
| Two changes in the same hunk that need to be in different commits | [references/execution.md](references/execution.md) (synthesizing a patch with only the desired hunk; splitting a hunk by editing the patch file directly) |
| User aborts mid-execution | [references/recovery.md](references/recovery.md) (`git reset --soft` + `git stash apply`) |
| `git apply --cached` fails with "patch does not apply" | [references/execution.md](references/execution.md) (re-derive the patch from current working-tree state; check for line-ending or whitespace mismatches; use `--3way` as a last resort) |
| Repo has no prior commits / unusual `HEAD` (detached, orphan branch) | [references/inventory.md](references/inventory.md) (the `START_SHA` capture caveats; abort cleanly if `HEAD` doesn't exist) |

## Topic References

- [Inventory](references/inventory.md) — capturing the baseline (alt-index tree for verification + `git stash push -u --apply` for recovery, *not* `git stash create -u`); parsing `git status --porcelain=v1`; modified vs. staged vs. untracked vs. deleted vs. renamed; reading files (not just the diff) to understand intent.
- [Grouping](references/grouping.md) — heuristics for clustering hunks into commits: dependency direction, mechanical vs. behavioral, test bundling, generated/lockfile isolation, rename isolation, when to split vs. merge candidates.
- [Commit Messages](references/commit-messages.md) — subject conventions (imperative, ≤72 chars, no period, repo-matching prefixes); body structure (motivation → approach → tradeoffs); referencing issues/tickets; what *not* to include.
- [Execution](references/execution.md) — exact git command sequence for whole-file commits and for hunk-level splits; synthesizing a hunk-only patch from `git diff`; `git apply --cached`; `-F` for messages; handling renames, deletions, and binary files; recovering from a failed hook.
- [Verification](references/verification.md) — the three checks (`git diff`, `git status`, tree-hash equality) that prove the final state matches the starting state; what each kind of divergence means.
- [Recovery](references/recovery.md) — restoring the baseline if verification fails or the user aborts: `git reset --soft <START_SHA>` then `git stash apply <baseline-stash>`, with `--index` if needed; cleaning up temp files; reporting the rollback to the user.
