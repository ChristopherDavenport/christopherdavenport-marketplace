# Foundations

The visual language of the Jack Henry Design System. Each foundation page documents one axis of the system — what the available choices are and which ones to use when. The **mechanics** (how a value becomes a CSS variable, how themes are applied) live in [design-tokens.md](design-tokens.md); this file is about visual choice and intent.

## URLs

| Foundation | URL |
|---|---|
| Borders | `https://jackhenry.design/v2/foundations/borders/` |
| Colors | `https://jackhenry.design/v2/foundations/colors/` |
| Dimensions | `https://jackhenry.design/v2/foundations/dimensions/` |
| Elevation | `https://jackhenry.design/v2/foundations/elevation/` |
| Focus | `https://jackhenry.design/v2/foundations/focus/` |
| Icons | `https://jackhenry.design/v2/foundations/icons/` |
| Typography | `https://jackhenry.design/v2/foundations/typography/` |

All require the trailing slash. Always fetch the live page before quoting specific values — palette steps, spacing scales, and font sizes evolve.

## The global → alias → style hook hierarchy

Every foundation has the same shape:

1. **Global** values define the raw choices in the system (e.g. nine hues × nineteen steps for color; a fixed scale of dimensions). Naming pattern: `jh-{foundation}-{property}-{scale}` (e.g. `jh-color-blue-600`).
2. **Alias** values give global values semantic meaning (e.g. `jh-color-content-negative-enabled` for destructive text). Aliases are what you actually apply.
3. **Style hooks** let a single component override an alias for itself (e.g. a button's label color).

**Rule:** Never reference a global value directly in product CSS. Use an alias. If you need to override one component, use its style hook.

## Colors specifically

- Global palette: nine hues + grays, each with steps `50` → `950` (nineteen steps), spaced for predictable contrast pairings.
- Alias categories: container, overlay, control, divider, brand, content, interactive.
- "On" colors guarantee accessible contrast against a specific surface — pair them: `jh-color-content-on-primary-enabled` goes on `jh-color-container-primary-enabled`, etc.
- Naming pattern: `jh-color-[concept]-[property]-[state]`. Examples:
  - `jh-color-gray-200` (global — don't use in product code)
  - `jh-color-content-negative-enabled` (alias — destructive text)
  - `jh-color-content-on-primary-enabled` (alias — text drawn on top of the primary container)

## Focus

The focus foundation defines the canonical focus ring. Every interactive jh-ui component uses it. If you build a custom interactive element, mirror the same alias / style hook so the focus ring is visually consistent.

## Icons (foundation)

The icons *foundation* page describes the visual style and sizing rules. The actual icon glyphs are shipped in `@jack-henry/jh-icons` — see [getting-started.md](getting-started.md). The `<jh-icon>` component (in `@jack-henry/jh-ui`) renders them.

## Typography

Type scale, font families, and pairing rules. Components consume typography aliases; product surfaces should also consume aliases rather than hardcoding font sizes. When in doubt about which alias to apply, fetch the typography page and quote the relevant role.

## When this file is the wrong place

- "How do tokens get into my CSS?" → [design-tokens.md](design-tokens.md)
- "How do I switch to dark mode?" → [design-tokens.md](design-tokens.md) (theme application)
- "What attributes does `jh-button` accept?" → [components.md](components.md)
