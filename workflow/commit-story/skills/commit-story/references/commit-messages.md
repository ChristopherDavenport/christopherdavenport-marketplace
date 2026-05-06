# Commit Messages

Phase 4. The whole point of this skill is the message. The diff is the *what*; the message is the *why*. A reviewer reading the PR three months from now (or `git blame` two years from now) only has the message.

## The shape of a good message

```
<subject — imperative, ≤72 chars, no trailing period>
<blank line>
<body — 1 to 3 short paragraphs explaining the why>
<blank line, only if needed>
<footers — issue refs, Co-Authored-By, etc.>
```

The subject is what shows up in `git log --oneline`, GitHub's PR commit list, and `git shortlog`. It has to stand alone.

The body is what shows up in `git log` (full), `git show`, and any reviewer who clicks the commit. It explains the motivation, names the constraint, points at the ticket.

## Subject line

### Imperative mood

`Add request-ID propagation`, not `Added request-ID propagation` or `Adding request-ID propagation` or `Adds request-ID propagation`.

The convention comes from completing the sentence: "If applied, this commit will __________." The imperative form ("Add ...") fits naturally; past/gerund/third-person forms don't.

This is git's own convention (`git commit --help` examples) and matches the format git uses for its own auto-generated messages ("Merge branch ...", "Revert ...").

### ≤72 characters

GitHub truncates at 72; `git log --oneline` reads better short. Aim for 50 if you can; cap at 72.

If you can't fit the *what* in 72 characters, the commit is probably doing too much — re-split.

### No trailing period

`Add request-ID propagation`, not `Add request-ID propagation.`

The subject is a title, not a sentence.

### Match the repo's prefix convention

Read `git log --oneline -20` first. If you see prefixes like:

- `feat: ...`, `fix: ...`, `refactor: ...` → Conventional Commits. Use them, with the same scopes (`feat(api): ...`).
- `[area] ...` → bracketed area prefixes. Match.
- `area: ...` → colon-separated area prefixes. Match.
- No prefixes, just plain subjects → no prefixes.

Do not impose a convention the repo doesn't use. Conventional Commits are nice for tooling, but if the repo doesn't already use them, adding them now creates inconsistency that future tooling can't rely on either.

### What the subject should say

The subject is the *headline*. It says what changed and (if it fits) the most important reason.

Good:

- `Require MFA on /admin and /billing endpoints`
- `Fix loadUser null-deref on archived rows`
- `Extract parseRequestID helper`
- `Run gofmt`
- `Update lockfile after axios 1.6 bump`

Bad (vague, narrating):

- `Update auth.go`               (what changed about it?)
- `Various fixes`                (which fixes?)
- `WIP`                          (you're not committing WIP through this skill)
- `Refactor`                     (refactor what? to what?)
- `Address review feedback`      (which feedback? OK in a follow-up commit on a PR, never in initial commits)

## Body

### When to include one

Always, unless the subject is genuinely self-explanatory. `Run gofmt` doesn't need a body. `Require MFA on /admin and /billing endpoints` does — the body says *why now*.

### Structure

A body has three possible sections, in this order:

1. **Motivation** (always). What problem is this solving? What constraint, ticket, incident, or design decision drove it?
2. **Approach** (sometimes). If the *how* isn't obvious from the diff, briefly explain the choice — especially if you considered and rejected an alternative.
3. **Tradeoffs / followups** (sometimes). What's not addressed here, what's the known limitation, what comes next.

Keep each section to 1-3 short paragraphs. Wrap at 72 characters. Use blank lines between paragraphs.

### Example: motivation only

```
Require MFA on /admin and /billing endpoints

SOC2 audit (Q2-2026) flagged that privileged endpoints accept any
valid session token, including ones older than the MFA grace window.
Adding requireMFA() forces a re-assertion within the last 15 minutes
for these routes specifically. Other routes are unaffected.
```

### Example: motivation + approach

```
Switch loadUser to return ErrNotFound on archived rows

Production logs (ticket #842) show `loadUser` panicking on a nil row
deref when the user_id is valid but the row was archived. The caller
already handles ErrNotFound for the unknown-id case; extending that
to "row archived" is the smallest behavior change.

Considered returning a typed `ErrArchived` so callers can distinguish
"never existed" from "archived". Decided against — every existing
caller treats both as "not available" and adding a new error type
forces churn at every call site for no observable benefit.
```

### Example: motivation + followup

```
Add request-ID propagation through API handlers

Distributed tracing (ticket #1023) needs a stable request ID across
the auth -> api -> billing service boundary. This commit threads
X-Request-ID through the three handler entrypoints and falls back
to a generated UUID when the header is missing.

Followup: the billing client (in vendor/billing-go) doesn't yet
forward the header — that's tracked in #1041 and needs an upstream
PR. For now, billing traces show a fresh request ID at the boundary.
```

## Issue / ticket references

If the user mentions an issue or ticket number, reference it in the body, not the subject (subjects need to read standalone). Match the repo's existing reference style:

- `ticket #842`, `(#842)`, `Refs: #842`, `Fixes: #842` (be careful with `Fixes:` / `Closes:` — they'll auto-close the issue on merge in many forges).

If the repo uses an external tracker (Linear, Jira), match that: `LIN-1234`, `PROJ-456`.

## Footers

Standard footers go at the end, separated by a blank line:

- `Co-Authored-By: Name <email>` — if appropriate. Claude Code's harness adds its own attribution; don't duplicate.
- `Refs: #123`, `Fixes: #456` — if not already in the body.
- `Reviewed-by:`, `Tested-by:`, `Reported-by:` — kernel-style trailers, only if the repo uses them.

Don't add footers the repo doesn't already use. They're noise otherwise.

## What *not* to include

- **"and also"**. If you find yourself writing "and also" in the subject or body, the commit is doing two things — re-split.
- **Diff narration**. "Removes the if statement on line 42." The diff already shows this. Explain *why* the if statement is gone, not that it is.
- **References to the current task / fix / caller**. `// added for the X flow`, "called by the new Y handler". These rot the moment the calling code is restructured, and they belong in the PR description, not the commit body.
- **Filenames in the body** (usually). The diff shows them. Mention a filename only when it carries meaning ("Move retry logic out of `client.go` and into the new `retry.go` since two clients now need it.").
- **Half-truths to make the commit look cleaner**. If a commit does two things because they couldn't be split, say so honestly: "This commit also reformats the surrounding function — gofmt insisted." Better than pretending it doesn't.

## Drafting workflow

For each planned commit:

1. Look at the hunks/files assigned to it.
2. Write a one-sentence answer to "why are we doing this *at all*?" That's the seed of the body.
3. Write a one-sentence answer to "what changed?" That's the seed of the subject.
4. Compress the *what* sentence into ≤72 chars, imperative.
5. Expand the *why* sentence into 1-3 paragraphs of body.
6. Read it back. Would a reviewer understand the commit from this alone?

## Writing it to disk

Use `-F <file>` to commit, never `-m "..."`:

```sh
cat > /tmp/cs-msg-1 <<'EOF'
Require MFA on /admin and /billing endpoints

SOC2 audit (Q2-2026) flagged that privileged endpoints accept any
valid session token, including ones older than the MFA grace window.
Adding requireMFA() forces a re-assertion within the last 15 minutes
for these routes specifically. Other routes are unaffected.
EOF

git commit -F /tmp/cs-msg-1
```

`-F` reads the file verbatim — no shell escaping, no `\n` quoting hazards, no truncation at the first newline. `-m` works for one-line messages but is fragile for multi-paragraph bodies.

Use a HEREDOC with single-quoted `'EOF'` to disable shell expansion in the body. Backticks, `$variables`, and `!history` get literal-interpreted, which is what you want.
