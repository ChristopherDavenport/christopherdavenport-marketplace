# Templates

The repo's template is the schema. This skill supplies the style. Where they disagree, the template wins on *structure* and the budget wins on *volume*.

## Discovery

```sh
ls .github/pull_request_template.md \
   .github/PULL_REQUEST_TEMPLATE.md \
   PULL_REQUEST_TEMPLATE.md \
   docs/pull_request_template.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null    # multi-template repos
```

GitHub matches case-insensitively and looks in the repo root, `.github/`, and `docs/`. If a directory form exists, the repo has several templates and the right one depends on the change type — **ask which applies** rather than picking. If nothing exists, use the default shape below.

## Reading it

The instructions are usually in HTML comments, and they are usually specific. Read them as requirements, not decoration:

```markdown
## How To Test
<!-- Testing instructions should:
  - Include tests for successful paths, unsuccessful paths, empty and loading states.
  - Formatted as a checklist.
    - Bulleted items should be actions to be attempted
    - Checkbox items should be expected outcomes of the previously listed actions.
-->
```

That comment defines a two-level grammar — bullet = action, nested checkbox = expected outcome — and getting it backwards produces a section that looks right and reads wrong. Where a template specifies a format this precisely, follow it exactly.

**Drop the comments from sections you fill. Keep them in sections you leave empty.** A filled section no longer needs its instructions; an empty one still does, for the next person.

## Section discipline

- **Never invent a section** the template does not have. If you have something important with nowhere to put it, it goes in the closest existing section or in the follow-up comment.
- **Never delete a section** the template has, even if empty. Its absence reads as a modified template; its emptiness reads as "not applicable".
- **Leave genuinely-empty sections empty.** Do not write "None" or "N/A" under *Dependencies* — an empty section is a non-assertion, the word "None" is an assertion, and it is wrong the moment someone opens a related PR.
- **Fill sections in the template's order**, not in order of importance. The reviewer knows the shape; reordering costs them the map.

The lead goes *above* the first template heading. Templates almost never provide for it, and it is not a section — it is the sentence the template forgot to ask for.

## Titles

Check for a convention before writing one:

```sh
git log --oneline -20
mcp__github__search_pull_requests  query: "repo:<owner>/<repo> is:merged"  perPage: 20
#   read the titles off the results
```

Repos vary between Conventional Commits (`feat:`, `fix:`), a product or area prefix, and free prose. Match what is there; do not impose a convention the repo does not use, and do not drop one it does.

Say what changed in terms the reader's *user* would recognise — name the behaviour, not the refactor. "Add sortable columns to the batch list" over "Refactor batch-list to use a computed property".

**Tickets.** Append a reference only if you actually know one — from the branch name, a commit trailer, or the user. Never infer one from an adjacent ticket number, and never invent one to satisfy a convention. If the repo's title format expects a ticket and the branch carries none, ask.

## Checkboxes and labels

Templates commonly end with an author-liability block: *verified the production build*, *checked accessibility compliance*, *tested in Chrome / Firefox / Safari / Edge*.

**Leave every one unchecked**, including ones you believe are satisfied. These are the author's personal attestations; ticking them asserts something you did not do and they may not have. The same applies to labels the template mentions — you cannot set them from the body, so name them in your summary to the user and let them apply them.

The distinction that matters: checkboxes *inside* a "How To Test" section are expected outcomes for the reviewer to tick as they verify, and you should write them. Checkboxes under "Author liability" are claims about the author, and you should not touch them.

## Default shape when there is no template

```markdown
<lead: 15–60 words, what changes and why>

## What changed
<the change, at the altitude of behaviour>

## How to test
- <action>
  - [ ] <expected outcome>

## Notes
<risks, caveats, anything a reviewer should look at closely — omit if there are none>
```

Three headings is enough for almost anything. If you reach for a fourth, check [placement.md](placement.md) first — it is usually a work record trying to get in.
