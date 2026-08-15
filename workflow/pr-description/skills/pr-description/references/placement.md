# Placement

Most over-dense PR descriptions do not contain bad writing. They contain good writing in the wrong place. This is the sorting rule.

## The three piles

Before drafting, sort everything you know into exactly one of these.

**Body — what the reviewer needs to decide.** What changed and why. The behaviour a user will notice. The risk that would make someone say no. The thing to look at closely. How to check it works. Anything that changes the *approve / request-changes* decision.

**Comment — the record of the work.** How you found the problem. What you ruled out and why. Investigation that would save the next person time. Confirmation that a failure is pre-existing. Benchmark tables. Phase plans. Dead ends. Post it as the first comment on the PR, immediately after opening.

**Neither — true but inert.** Restating the diff in prose. Narrating your own process ("I first looked at X, then realised Y"). Describing the codebase as it already exists, at length, to set up a two-line change. Explaining a well-known library. Listing every file you touched when the file list is right there.

## The test

For each fact, ask: **would a reviewer who already agreed with this change still need it?**

- Yes → body.
- No, but a future maintainer would → comment.
- No to both → cut it.

Most of what an agent produces answers *no* to the first question. That is not a flaw in the investigation; it is a flaw in the destination.

## Why a comment and not a wiki page

The comment sits on the artifact it describes, it is searchable from the PR, it survives the branch being deleted, and it costs one `gh pr comment` call. A wiki page needs a home, a link, and someone to maintain it. If the material outgrows a comment, it has become a document and should be written as one — but that is a separate decision, made deliberately, not something a PR body should drift into.

State the split in one line so it does not look like the body is hiding something:

> Investigation notes are in the first comment.

## Failure modes this catches

**The long-running branch.** An integration PR for a multi-phase migration accumulates a phase checklist, per-phase findings, and revised estimates. All of it is real project management and none of it is review material. Keep a single "what changes" body; let the phase log live in a comment you edit as you go, or in the tracking issue.

**The confirmed non-issue.** You spent an hour proving three failing tests also fail on the base branch. That hour was well spent and the conclusion belongs in the body as *one sentence* — "three pre-existing failures on this branch also fail on the base" — with the evidence in the comment. The proof is not the point; the reassurance is.

**The setup that ate the change.** A two-line fix preceded by four paragraphs explaining the subsystem. If the reviewer owns that subsystem they do not need it. If they do not own it, they need a link, not a lecture.

**The findings-as-body.** A body organised around what the author discovered rather than what the reader must decide. The tell is a heading like "Findings" or "Notes from investigation", or a body whose section order recapitulates the order the work happened in. Reorder around the decision.

**The apology.** Explaining why the diff is larger than intended, or why an approach was abandoned mid-branch. If the diff needs defending, either split the PR or say the one sentence that defends it. Do not litigate it in the body.

## What never goes anywhere

- Assertions you did not verify — "all tests pass", "no performance impact", "backwards compatible".
- Invented ticket numbers.
- Ticks on the author's attestation checkboxes.
- Attribution footers or any note about how the description was written.
