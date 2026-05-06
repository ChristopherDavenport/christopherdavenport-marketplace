# Grouping

Phase 3. You have an inventory of files and hunks with their semantic purposes. Now cluster them into commits a reviewer will thank you for.

## The reviewer's perspective

A reviewer reads commits in order. Each one is a fresh context switch. The cost of switching is non-zero, so the value of the next commit has to be worth that cost. Two principles fall out of this:

1. **A commit should do one thing.** "Rename and extract a helper and add the feature" requires the reviewer to hold three independent concerns in their head while reading one diff.
2. **The sequence should tell a story.** Helpers before callers; types before implementations; tests after the code (usually); refactors before the feature that uses them. The reviewer's mental model should grow monotonically — each commit adds something on top of what's already understood.

Optimize for the reviewer who knows nothing about the change yet.

## Heuristics

These are heuristics, not laws. Apply them with judgment, and revise the plan if the user pushes back.

### Dependency direction

If commit B depends on something introduced in commit A, A goes first. Examples:

- A new helper function lands before the commits that call it.
- A new type lands before the implementations of that type.
- A schema migration lands before the code that reads the new column.
- A configuration option lands before the code that consumes it.

This makes each commit independently buildable — `git checkout <commit>` and the project compiles. Most CI bisects assume this.

### Mechanical vs. behavioral

A pure refactor (rename, extract, format, move) should not share a commit with a behavior change. Reviewers can skim the mechanical commit (no logic changed, just shuffling) and focus their attention on the behavioral one.

If a single file mixes both, that's a hunk-level split candidate. See [execution.md](execution.md).

### Tests with code, except when the test is the point

Default: a new feature and its tests go in one commit. The tests document the intended behavior; reading them next to the code is helpful.

Exception: when the test is *pinning down a bug* before the fix. In that case, the test commit goes first (failing), then the fix commit (which makes it pass). This is the executable specification of the bug — a future revert of the fix is caught by CI.

Exception: when the feature is large enough that the diff is overwhelming. Then split the implementation and the tests into adjacent commits, in that order.

### Generated artifacts and lockfiles get their own commit

`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `go.sum`, `Cargo.lock`, generated protobufs, generated docs — separate commit. The diff is mechanical, often huge, and a reviewer who sees a code commit also showing 2,000 lines of lockfile churn cannot tell the two apart.

Subject convention: `Update lockfile after <upstream-change>` or `Regenerate protobufs for <change>`.

### Renames in their own commit

A pure rename (file or symbol) should not also include unrelated edits. Rename detection across diffs is fragile; mixing renames with content changes makes git's similarity heuristic fail and the diff becomes a delete + add, which is much harder to review.

If you do need to both rename and edit, do the rename first as its own commit (so git's heuristic catches it), then the edit on the new path.

### Format/lint noise as its own commit

If the editor reformatted unrelated files on save, those go in one commit by themselves: `Run gofmt` / `Apply prettier --write` / etc. No body needed; the subject is self-explanatory.

If you find yourself with many small format-only changes scattered across many files, do the format commit *first* — that way subsequent feature commits don't carry incidental whitespace churn.

### One concern per file is rare; one concern per commit is the goal

A file with two concerns gets split at the hunk level. A concern that spans many files becomes one commit. Don't let "one file per commit" or "one commit per file" be a default; both are wrong as often as they're right.

## When to split a candidate further

If a commit candidate is getting large, ask: would a reviewer reading just this commit have to mentally separate two concerns? If yes, split. Common sub-splits:

- "Add feature" candidate is large → split into "Extract helper X" + "Add feature using X".
- "Rename and edit" candidate → split into "Rename X to Y" + "Edit Y".
- "Migration + reads + writes" candidate → split into "Add column" + "Backfill" + "Switch reads to new column" + "Stop writing to old column" + "Drop old column" (the textbook expand/contract sequence).

## When to merge candidates

The opposite trap is splitting too aggressively. If two candidates always appear together (e.g., a new endpoint and the route registration that exposes it), merging is fine — they're a single logical unit.

Also merge when:

- Both candidates are tiny (1-2 lines each) and tightly related.
- Splitting would force one to be temporarily broken (one half doesn't compile without the other).
- The user explicitly asks for a coarser split.

## Order within the sequence

Once you have N commit candidates, decide their order. The default heuristic:

1. Format/lint noise (clears the deck).
2. Pure refactors and renames (no behavior change).
3. Helper / type / scaffold additions (used by later commits).
4. The behavioral changes themselves, in dependency order.
5. Tests (unless they're the bug-pinning kind, which go just before the fix).
6. Generated artifacts and lockfiles (they're consequences of the above).

Adjust freely — this is a default, not a rule.

## Sanity-check the plan before Phase 4

Read the proposed list back to yourself. Ask:

- Could a reviewer understand commit N from its subject + body + diff alone?
- Does the sequence build monotonically — each commit adds something coherent on top of the previous?
- Is any commit doing two unrelated things?
- Is any commit so trivial it could be merged into its neighbor without loss?
- Does the order respect dependencies (no commit refers to something only added later)?

If any answer is uncomfortable, revise before drafting messages. Re-grouping is cheap; re-executing isn't.
