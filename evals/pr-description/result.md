# pr-description — assertion eval

**24/24 cases** (11 failure, 13 pass). Mutation check passes.

Deterministic and free: PR bodies in, verdicts and failure sets out. No model,
no tokens, no network — so this runs on every change rather than on a funded
sweep.

```
./evals/pr-description/run.sh              # the suite
./evals/pr-description/run.sh --mutate     # prove the suite can fail
```

## What is under test

`workflow/pr-description/skills/pr-description/scripts/density.py` — the scorer
the skill runs on its own draft before presenting it. It turns a body plus a
diff size into a decision: within budget, or not, with a named set of metrics
that tripped.

The suite asserts **the failure set, not just the exit code.** A body that
breaks the paragraph cap when the case meant to test the bold cap still exits
non-zero, and under exit-code-only assertion would read as covered. Each
failure case declares exactly which metrics must trip, and a mismatch is a
failure even when the verdict is right.

Two cases were written with incomplete expectations during development and the
set-matching caught both — they tripped `max_para_words` in addition to the
metric under test. That is the check earning its place on the first run.

## Coverage

| Group | Cases | What they pin |
|---|---|---|
| Lead | 5 | absent, too short, too long, and both boundaries (15 and 60) |
| Word budget | 4 | over-cap in each of the three tiers, plus the empty body |
| Tier selection | 2 | 50 changed lines is small, 51 is normal |
| Emphasis | 1 | bold per 100 words, isolated from other caps |
| Paragraph | 2 | 81 words fails, 80 passes |
| Scaffolding exclusion | 4 | checkboxes, HTML comments, code fences, table rows |
| Structure | 2 | bullets are not paragraphs; absent diff size defaults to normal |
| Whole bodies | 4 | proportionate small, normal and large drafts, plus multi-failure |

**13 of the 24 cases assert pass**, and they carry as much weight as the
failures: *a scorer that rejects every body satisfies every failure case and is
useless.* Boundary cases sit on both sides of each cap, since an off-by-one in
a comparison is the likeliest bug in a budget check.

### One case documents a blind spot

`table-rows-excluded` asserts **pass** for a body whose prose has been moved
into a table. That is the scorer working as designed — table rows are excluded
so that a template's tables do not count against the author — and it is also a
loophole: relocating paragraphs into a table ducks the word cap while making
the body denser to read.

The scorer structurally cannot catch this, so the skill forbids the tactic in
prose instead. The case exists so the gap is asserted and visible rather than
discovered later and mistaken for a bug.

## The mutation requirement

`--mutate` replaces the scorer with one that always reports "within budget" —
still emitting parseable JSON, because the interesting mutation is a scorer
that *runs and approves*, not one that crashes. A crash is caught by any case;
a permissive scorer is caught only here.

Verified in both directions. Under mutation all 11 failure cases correctly
invert. With the stub write disabled as a negative control, exactly those 11
go red and the suite exits 1 — so the mutation mode is itself exercised, not
merely present.

## Not covered

Stated rather than implied, because an eval's silence reads as coverage:

- **The skill's prose is unscored.** Only the scorer it ships is asserted.
  Whether the workflow produces better descriptions is a judge-shaped question
  and this suite does not answer it.
- **The budget values themselves are not validated here.** That 500 words is
  the right large-tier cap is a calibration claim, evidenced in
  `references/density.md`, not something a test can settle.
- **No end-to-end run.** The suite exercises the scorer, not the skill driving
  it. The closest thing to an integration test is that PR #4's own description
  was written with the skill and scores within budget.
