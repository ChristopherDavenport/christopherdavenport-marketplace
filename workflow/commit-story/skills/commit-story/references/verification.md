# Verification

Phase 7. The whole skill stands on this. If verification doesn't pass, the run failed — even if every individual `git commit` succeeded.

## The three checks

All three must pass. They check overlapping but not identical things, and one of them will catch a class of bugs the others miss.

### Check 1: Diff against the baseline tree is empty

```sh
git diff "$BASELINE_TREE" --
```

If output is empty, the working tree at the end of the run matches the working tree at the start (including originally-untracked files, since `BASELINE_TREE` was built to include them). Combined with `git status` being clean (Check 2), this means the new commit history reproduces the baseline tree.

If output is non-empty, content has been lost or added somewhere. The diff itself tells you what — read it carefully before deciding whether to recover.

Note: include the trailing `--` to disambiguate `$BASELINE_TREE` as a revision rather than a path. Compare against the *tree* (`BASELINE_TREE` from Phase 1's alt-index), not against the stash commit (`BASELINE_STASH`) — the stash's main tree is tracked-only and would falsely flag originally-untracked files as added.

### Check 2: Working tree is clean

```sh
git status --porcelain
```

If output is empty, no modifications, no staged-but-uncommitted, no untracked files. Pristine.

If output contains:

- **Modified or staged files** (`M `, ` M`, `MM`, `A `, `D `, ` D`, etc.) — content didn't make it into a commit. Recover.
- **Untracked files** (`??`) — content the skill failed to commit. Cross-reference against the `/tmp/cs-untracked` list captured in Phase 1: if the same files are still untracked, the skill missed them; if they're new files that weren't there at start, something else created them mid-run. Either way, investigate before declaring success.

### Check 3: Tree-hash equality

```sh
test "$(git rev-parse HEAD^{tree})" = "$BASELINE_TREE"
```

Compares the SHA-1 of the root tree object on both sides. Equal → every file in the new `HEAD`'s tree is byte-identical to every file in the baseline tree. Different → at least one file differs in content, mode, or path.

This is the strongest check. `git diff` can be silenced by certain `.gitattributes` rules (e.g., `merge=ours`); the tree hash cannot. If check 3 fails but checks 1 and 2 pass, suspect attribute-driven diff filtering — the file content actually differs even though git is hiding the diff.

## Why three checks instead of one

- **Check 1 (diff)** is the most readable. If it fails, the diff *is* the report.
- **Check 2 (status)** catches a different failure mode: content that's correct in the working tree but never made it into a commit (left staged or unstaged after the loop ended).
- **Check 3 (tree hash)** is the strongest correctness guarantee. It's the one that lets you say "byte-identical" without hedging.

In practice, all three usually agree. When they don't, the disagreement is itself the diagnostic.

## Reading divergence

Run all three even if check 1 fails — the additional checks help diagnose.

| Check 1 (diff) | Check 2 (status) | Check 3 (tree) | Diagnosis |
|---|---|---|---|
| empty | empty | equal | All good. Proceed to cleanup. |
| empty | dirty (mods) | equal | Cannot happen — if checks 1 and 3 pass, the working tree matches the baseline tree exactly, which means there are no uncommitted modifications. If you see this combination, the variables (`BASELINE_TREE` etc.) are wrong; re-derive from Phase 1 state. |
| non-empty | dirty | unequal | Content lost or added during execution. Recover. |
| non-empty | empty | unequal | A commit landed with the wrong content (e.g., a hunk was assigned to the wrong commit and duplicated). Recover. |
| empty | empty | unequal | Rare. Check `.gitattributes` for `merge=ours` or `diff` filters that hide content differences. Recover. |
| non-empty | empty | equal | Cannot happen — if check 3 passes, the diff against the baseline tree must be empty. If you see this, suspect a stale `BASELINE_TREE` variable or a comparison against the wrong tree (e.g., the stash's main tree, which excludes originally-untracked files). |

## When verification passes

Cleanup (Phase 8): drop the baseline stash, remove temp files, report the commit list.

```sh
# Find the stash entry by its message — never trust stash@{0}.
STASH_REF=$(git stash list | awk -F: '/commit-story-baseline-/ {print $1; exit}')
git stash drop "$STASH_REF"
rm -f /tmp/cs-untracked /tmp/cs-msg-* /tmp/cs-patch-* /tmp/cs-state
git log "$START_SHA"..HEAD --oneline
```

Be careful with the stash drop — match by the message you set in Phase 1 (`commit-story-baseline-<timestamp>`), not by index. Other stashes may have shifted positions if the user (or another tool) created stashes between Phase 1 and Phase 8.

## When verification fails

Stop. Do not try to fix forward by adding "correction" commits — you don't yet know what diverged or why, and stacking more commits on top makes recovery harder.

Run the recovery procedure ([recovery.md](recovery.md)) to restore the baseline state, then report to the user:

- Which check(s) failed.
- The output of `git diff "$BASELINE_TREE" --` (truncated if huge).
- The output of `git status --porcelain`.
- The list of commits that were created (`git log "$START_SHA"..HEAD --oneline` — soon to be discarded).
- Your best guess at what went wrong (mis-assigned hunk, hook auto-modification, etc.).

The user is now equipped to either:

1. Re-run the skill with a corrected plan.
2. Investigate the divergence themselves.
3. Decide the divergence is acceptable and commit some other way.

Don't make that choice for them.
