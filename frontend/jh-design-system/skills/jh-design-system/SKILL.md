---
name: jh-design-system
description: >
  Jack Henry Design System (jackhenry.design/v2): the @jack-henry/jh-ui
  Lit components (jh-* tags), @jack-henry/jh-core design tokens, and
  @jack-henry/jh-icons. Load when authoring or reviewing any file
  importing from a @jack-henry/jh-* package — including alongside the lit
  skill, which covers the underlying LitElement patterns.
---

# Jack Henry Design System

## Scope

Covers all of `https://jackhenry.design/v2`: the 21 `jh-*` web-component tags (`jh-badge`, `jh-button`, `jh-card`, `jh-checkbox`, `jh-checkbox-group`, `jh-divider`, `jh-icon`, `jh-input`, `jh-list-group`, `jh-list-item`, `jh-menu`, `jh-notification`, `jh-progress`, `jh-radio`, `jh-radio-group`, `jh-switch`, `jh-tag`, `jh-tag-group`, `jh-toast`, `jh-toast-controller`, `jh-tooltip`); visual foundations (borders, colors, dimensions, elevation, focus, icons, typography); the global / alias / style-hook token tiers; the `jh-theme-light.css` and `jh-theme-dark.css` themes; content guidelines (voice and style, grammar and usage, UX writing patterns, terminology and vocabulary); the Figma kit setup flow (designing) and the npm install / Storybook flow (developing); and the `Banno/jack-henry-design-system` GitHub repo (default branch `next`, not `main`).

The Jack Henry Design System (`https://jackhenry.design/v2`) is an open-source design system for community financial institutions. Three npm packages, all under `@jack-henry/`:

- **`jh-ui`** — native web components (built on `lit` 2.x). Tag pattern: `<jh-{name}>`. Authoritative API contract: [`packages/jh-ui/custom-elements.json`](https://github.com/Banno/jack-henry-design-system/blob/next/packages/jh-ui/custom-elements.json) in the repo.
- **`jh-core`** — design tokens emitted as CSS custom properties (`--jh-*`) and JSON. Ships pre-built `jh-theme-light.css` and `jh-theme-dark.css` that target the `:root` selector — apply a theme by importing the corresponding CSS file.
- **`jh-icons`** — SVG and web-component icons.

Token tiers, every project must respect them: **global** (raw value, e.g. `jh-color-blue-600` = `#085ce5`) → **alias** (semantic context, e.g. `jh-color-content-negative-enabled`) → **style hook** (per-component override). Components consume aliases; consumers override style hooks. Never wire a global token into a component.

The system is **framework-agnostic** (native custom elements). The repo's default branch is **`next`**, not `main`.

## Handling a Query

1. Identify the section using the routing table below.
2. Read the matching reference file for URLs, structure, and stable conventions.
3. Fetch the live page (site / Storybook / repo) — do not answer from training data; the system is versioned and changes.
4. Cross-check against `custom-elements.json` whenever the question is about a component's API surface (attributes, properties, slots, events, CSS custom properties).
5. Cite the canonical URL in the response.

## Dynamic Fetching Protocol

Always fetch rather than recall. Prefer these sources:

### jackhenry.design/v2 (design + usage guidance)

- Section page: `https://jackhenry.design/v2/{section}/{topic}/` (the **trailing slash is required** — pages 404 without it).
- Component page: `https://jackhenry.design/v2/components/{slug}/` where `slug` is the kebab-case name (e.g. `button`, `input-password`, `tag-group`). See [references/components.md](references/components.md) for slug normalization.
- Use `WebFetch`.

### Storybook (live demos, props, code examples)

- Canonical Storybook (built from `main`): `https://main--68f8e6a25b256d0ef89b13e6.chromatic.com/`
- Direct doc page for a component: `https://main--68f8e6a25b256d0ef89b13e6.chromatic.com/?path=/docs/components-{name}--docs`
- The site's "Code Documentation" link points to `release-v2--…chromatic.com` — that's the staging build. Prefer the `main--…` URL above.

### GitHub repo: `Banno/jack-henry-design-system`

- Use `gh` CLI, not WebFetch.
- Default branch is `next`.
- Source for a jh-ui component: `mcp__github__get_file_contents` with `owner: Banno`, `repo: jack-henry-design-system`, `path: packages/jh-ui/components/{name}` (entries: `{name}.js`, `{name}.mdx`, `{name}.stories.js`).
- Authoritative component API: `https://raw.githubusercontent.com/Banno/jack-henry-design-system/next/packages/jh-ui/custom-elements.json`
- Theme CSS source: `https://raw.githubusercontent.com/Banno/jack-henry-design-system/next/packages/jh-core/platforms/web/css/jh-theme-light.css` (and `…/jh-theme-dark.css`).
- Issues: `mcp__github__list_issues` with `owner: Banno`, `repo: jack-henry-design-system`.

If a fetch fails, say so and fall back to the structural information in the relevant reference file rather than guessing.

## Routing Table

| Topic Keywords | Section | Reference File |
|---|---|---|
| A specific component (jh-button, button, jh-input, password input, table cell, …); component API, attributes, slots, events, anatomy, variants, behavior states | Components | [references/components.md](references/components.md) |
| Borders, colors (visual language), dimensions / spacing, elevation / shadow, focus rings, icon foundation, typography / type scale | Foundations | [references/foundations.md](references/foundations.md) |
| Design tokens, token tiers, alias tokens, style hooks, `--jh-*` CSS variables, `jh-color-*`, theme application, light vs. dark theme, naming convention | Design tokens | [references/design-tokens.md](references/design-tokens.md) |
| Voice, tone, microcopy, grammar, capitalization, UX writing patterns, error messages, button labels, terminology, vocabulary | Content guidelines | [references/content.md](references/content.md) |
| Install, npm packages, project bootstrap, importing components, Figma kit / community library, Storybook lookup, designer vs developer onboarding | Getting started | [references/getting-started.md](references/getting-started.md) |
| Multi-section question (e.g. "build a themed button using design tokens with the right voice") | Multiple | Read each relevant reference; combine |

## Response Format

- Lead with the canonical URL (site page, Storybook page, or repo file).
- Distinguish **design guidance** (anatomy, when-to-use, accessibility) from **dev contract** (tag name, attributes, slots, events, CSS custom property names).
- Quote attribute / property names exactly from `custom-elements.json` — do not invent API.
- For tokens, always recommend the **alias** (or a **style hook** when overriding a single component); never recommend a raw global token in product code.
- When the site documents a component that doesn't exist in the source yet (e.g. table sub-cells at the time of writing), say so explicitly — site docs can be ahead of implementation.
- Surface accessibility notes when the source page provides them.
- **Brevity does not override correctness.** When asked for a "quick", "simplest", or "shortest" answer about a JH component or token, do not invent tag names, attributes, or token names to satisfy the request faster. If a component (e.g. `<jh-table>` with sortable columns and pagination) cannot be verified in `custom-elements.json` because the source does not yet implement it, say that explicitly and point at the gap — never fabricate a code example that looks plausible. Inventing API to look helpful is the worst failure mode this skill can have.

## Out of Scope

- Generic Lit authoring questions → defer to the `lit` skill.
- Routing / navigation in jh-ui apps → defer to `web-component-router` or `lit-router`.
- Other design systems (Material, Carbon, Lightning, Polaris).
- The legacy `/pages/` version of jackhenry.design — only `/v2/` is in scope.
- Securities, mortgage, or banking regulations → defer to `financial-regs`.

## Topic References

- [Components](references/components.md) — the 21 jh-* tags, the 30 site doc pages and how they collapse onto components, slug normalization, component-page anatomy, where to look for what (site vs Storybook vs repo).
- [Foundations](references/foundations.md) — borders, colors, dimensions, elevation, focus, icons, typography. Visual-language guidance, with pointers to design-tokens.md for the mechanics.
- [Design Tokens](references/design-tokens.md) — global / alias / style-hook tiers, naming convention, theme application (`:root` import of `jh-theme-light.css` / `jh-theme-dark.css`), `--jh-*` custom properties, jh-core layout.
- [Content Guidelines](references/content.md) — voice and style, grammar and usage, UX writing patterns, terminology and vocabulary; how to compose microcopy for jh-ui components.
- [Getting Started](references/getting-started.md) — the three packages, install, importing components, Figma flow (designing), npm + Storybook flow (developing), repo layout.
