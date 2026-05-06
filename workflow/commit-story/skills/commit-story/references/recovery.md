# Recovery

What to do when verification fails or the user aborts mid-run. The goal is simple: leave the user exactly where they started, with no commits and no lost work.

## When to recover

- Verification (Phase 7) failed any of its three checks.
- The user said "stop" or "abort" mid-run.
- A pre-commit hook surfaced a real issue and the user wants to investigate before continuing.
- Anything unexpected: an apply that wouldn't apply even after re-derivation, a `git commit` that errored for a non-hook reason, a sudden disconnect.

The trigger is "I'm not confident the next step is safe." When in doubt, recover and report rather than push forward.

## The recovery procedure

Two operations, in this order. Both are non-destructive to the *content*; the second one explicitly re-installs the baseline.

### Step 1: Undo the new commits (preserve content)

```sh
git reset --soft "$START_SHA"
```

`--soft` moves the branch ref back to `$START_SHA` *without* touching the index or the working tree. Any commits you made since `$START_SHA` are now unreachable from the branch (they're still in the object database, recoverable via `git reflog` for ~90 days). The index and working tree are exactly what they were a moment ago — i.e., reflecting the state at the end of the (failed) run, not the baseline.

Why `--soft` and not `--hard`?

- `--hard` discards the working tree. If anything went wrong with your baseline stash, you've now lost the user's work.
- `--soft` leaves you with the option to recover by replacing the working tree with the baseline (next step), and falls back to the current state if the baseline somehow can't be restored.

`git reset --keep` and `git reset --merge` are more conservative variants but are designed for switching branches mid-edit; `--soft` is the right primitive here.

### Step 2: Restore the baseline working tree

```sh
git stash apply --index "$BASELINE_STASH" 2>/dev/null || git stash apply "$BASELINE_STASH"
```

`stash apply` restores the working tree (and, with `--index`, the staged-vs-unstaged distinction) to the state captured by the stash, *without* dropping the stash entry. After this, the working tree matches what it was at the start of Phase 1, including untracked files.

`--index` is preferred (preserves staging state). If it fails — some stash configurations don't apply cleanly with `--index` — fall back to plain `apply`. Content is restored either way; only the staging-state distinction may differ slightly.

### Step 3: Sanity-check the restoration

Compare the restored working tree to the captured baseline tree:

```sh
TMP_INDEX=$(mktemp)
cp "$(git rev-parse --git-path index)" "$TMP_INDEX"
GIT_INDEX_FILE="$TMP_INDEX" git add -A
RESTORED_TREE=$(GIT_INDEX_FILE="$TMP_INDEX" git write-tree)
rm "$TMP_INDEX"

test "$RESTORED_TREE" = "$BASELINE_TREE" && echo "recovery verified" || echo "recovery DIVERGED"
```

This rebuilds the everything-tree (tracked + untracked) the same way Phase 1 did, then compares. If they match, the working tree is byte-identical to where the user started. If they don't, the stash entry didn't fully restore — do not drop the stash; report to the user with the divergence and let them investigate manually.

You can also run the lighter `git status --porcelain` check to confirm the dirty/untracked set looks right, but tree-hash equality is the authoritative test.

### Step 4: Don't drop the baseline stash yet

After a failed run, *keep* the baseline stash. The user may want to:

- Inspect what was captured (`git stash show -p stash@{N}`).
- Re-apply it themselves to verify.
- Use it as input for a manual cleanup.

Drop it only when the user explicitly confirms recovery is good and they don't need the safety net. Or leave it indefinitely — stashes don't cost much, and `git stash list` makes it easy to find later.

### Step 5: Clean up temp files

```sh
rm -f /tmp/cs-untracked /tmp/cs-msg-* /tmp/cs-patch-*
```

Safe to do regardless of whether the run succeeded or failed.

## Reporting back to the user

Tell the user:

1. **What state they're in now.** ("Working tree restored to the state at the start of the run. The baseline stash is preserved as `stash@{N}` if you want to inspect it.")
2. **Which commits were created and discarded.** ("Commits A, B, C were created during the run; they're now unreachable from any branch but still recoverable via `git reflog` for ~90 days.")
3. **Why the run failed.** ("Verification check 3 (tree hash) failed — the baseline tree was `T1` but the new HEAD tree was `T2`. Suspect: hunk 2 of `auth.go` was duplicated across commits 1 and 2.")
4. **Suggested next step.** ("Re-run the skill with that hunk assigned to commit 1 only" / "investigate the .gitattributes settings on `path/x`" / etc.)

Be specific. "It failed, please re-run" is not actionable.

## What never to do during recovery

- **`git reset --hard`** — discards the working tree. Loses the user's work if the stash is somehow unusable.
- **`git checkout -- .`** — same problem, scoped to the current directory.
- **`git clean -fd`** — deletes untracked files. The user's untracked work is gone.
- **`git stash drop`** before recovery is verified — removes the safety net before confirming you don't need it.
- **`git push`, `git push --force`** — never. This skill doesn't push, ever.
- **`--no-verify`, `--amend`, `--force` flags** — none of these belong in the recovery path.

## If recovery itself fails

If `git stash apply "$BASELINE_STASH"` fails with conflicts (rare — the working tree should match `HEAD` after `--soft` to `START_SHA`, and the stash was created from that state, so they should be compatible), do not try to resolve them automatically.

Stop. Report to the user. Show them:

- The output of the failed `stash apply`.
- The current working tree state.
- The baseline stash SHA (`$BASELINE_STASH`) and its message (`commit-story-baseline-<timestamp>`).
- That they can manually `git stash apply` (or `git stash show -p | git apply`) at their leisure.

Their work is not lost — it's in the stash and reachable. They just need to reconcile it manually.
