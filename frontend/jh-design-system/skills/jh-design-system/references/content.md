# Content Guidelines

How to write the words that ship inside a jh-ui product. Microcopy, error messages, button labels, empty states, headings — anything end-users read.

## URLs

| Topic | URL |
|---|---|
| Voice and style | `https://jackhenry.design/v2/foundations/content/voice-and-style/` |
| Grammar and usage | `https://jackhenry.design/v2/foundations/content/grammar-and-usage/` |
| UX writing patterns | `https://jackhenry.design/v2/foundations/content/ux-writing-patterns/` |
| Terminology and vocabulary | `https://jackhenry.design/v2/foundations/content/terminology-and-vocabulary/` |

Trailing slashes required.

## Voice

The Jack Henry voice is **clear, confident, and human**: professional warmth that helps users navigate complex financial topics through active, direct, supportive language. Operationally:

- **Friendly and approachable** — use contractions.
- **Professional without rigidity** — no jargon for jargon's sake; explain financial/technical terms when used.
- **Confident yet humble** — direct, but acknowledge uncertainty when it exists.
- **Inclusive** — write for the full audience, not the in-group.

## Four core writing principles

1. **Active voice** for clarity and stronger messaging.
2. **One idea per sentence** — respect the reader's time.
3. **Consistent capitalization and terminology** — use the established vocabulary; don't invent synonyms.
4. **Always include a clear call to action** — tell the reader what to do next.

## When generating microcopy

Before composing copy for a jh-ui surface:

1. Fetch `…/ux-writing-patterns/` for the relevant pattern (errors, empty states, confirmations, etc.).
2. Fetch `…/terminology-and-vocabulary/` to use the canonical word for any domain term (e.g. account, transaction, transfer).
3. Apply the four principles above.

## Common jobs and where to look

| Writing job | Pages to fetch first |
|---|---|
| Button label | UX writing patterns + terminology |
| Error message | UX writing patterns (errors section) + voice and style |
| Empty state | UX writing patterns (empty states) |
| Form field label / helper text | Grammar and usage + terminology |
| Notification / toast | UX writing patterns (notifications) |
| Capitalization question (title case? sentence case?) | Grammar and usage |

## When this file is the wrong place

- "What does this component look like?" → [components.md](components.md)
- "What's the brand voice strategy / brand book?" → out of scope (this is the design-system layer, not corporate brand).
