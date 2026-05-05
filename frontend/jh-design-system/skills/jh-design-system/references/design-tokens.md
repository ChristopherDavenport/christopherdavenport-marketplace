# Design Tokens

The mechanics of how visual choices reach your CSS. The visual *language* lives in [foundations.md](foundations.md); this file covers the **token tiers**, the **naming convention**, and **how to apply a theme**.

## URLs

| Topic | URL |
|---|---|
| Overview | `https://jackhenry.design/v2/foundations/design-tokens/overview/` |
| Themes | `https://jackhenry.design/v2/foundations/design-tokens/themes/` |
| Light theme tokens | `https://jackhenry.design/v2/foundations/design-tokens/light-theme/` |
| Dark theme tokens | `https://jackhenry.design/v2/foundations/design-tokens/dark-theme/` |

## The three tiers

| Tier | What it is | Example | Where you use it |
|---|---|---|---|
| **Global** | A raw value with a context-agnostic name. | `jh-color-blue-600` = `#085ce5` | **Inside the system** only. Not in product CSS. |
| **Alias** | A semantic pointer to a global value, scoped to a use case. | `jh-color-content-negative-enabled` | This is the layer product code consumes. |
| **Style hook** | A component-scoped CSS custom property the consumer can override. | (per-component, see Storybook docs) | Override one component without forking it. |

Always reach for the **alias** first. If you need to deviate for a single component, use its **style hook**. Bypass to a **global** only if you're authoring tokens themselves.

## Naming convention

Full pattern (levels are skipped when they don't apply):

```
[system]-[component]-[element]-[category]-[concept]-[property]-[mode]-[variant]-[state]-[scale]
```

`system` is always `jh`. So real names look like:

- `jh-color-gray-200` — system + category + property + scale
- `jh-color-content-negative-enabled` — system + category + concept + property + state
- `jh-color-content-on-primary-enabled` — system + category + concept + property + state (note `on-{surface}`)

In CSS, the same names appear with a `--` prefix and `var()`:

```css
color: var(--jh-color-content-negative-enabled);
```

## The `jh-core` package layout

Source: [`packages/jh-core`](https://github.com/Banno/jack-henry-design-system/tree/next/packages/jh-core). Outputs:

- `platforms/web/css/jh-theme-light.css` — light theme as CSS custom properties on `:root`.
- `platforms/web/css/jh-theme-dark.css` — dark theme as CSS custom properties on `:root`.
- `platforms/web/js-css/` — JS object form of the same tokens.
- `platforms/json/` — raw token JSON (consume from any platform).

Both theme CSS files target `:root`, so importing one applies that theme globally. Authoritative file:

```
https://raw.githubusercontent.com/Banno/jack-henry-design-system/next/packages/jh-core/platforms/web/css/jh-theme-light.css
```

## Applying a theme

Simplest case — one theme for the whole app:

```js
// In the app's entry CSS or via a side-effect import:
import '@jack-henry/jh-core/platforms/web/css/jh-theme-light.css';
// or
import '@jack-henry/jh-core/platforms/web/css/jh-theme-dark.css';
```

Or as a stylesheet link:

```html
<link rel="stylesheet" href="/path/to/@jack-henry/jh-core/platforms/web/css/jh-theme-light.css">
```

For **dynamic theme switching** (light/dark toggle), the published files both target `:root`. The site's themes page does not document a built-in scoping selector at the time of writing — fetch it before quoting a current pattern. Common workarounds:

- Conditionally swap which stylesheet is applied (load both, disable one).
- Re-scope the rules at build time so each theme targets `[data-jh-theme="light"]` / `[data-jh-theme="dark"]` instead of `:root`.

If the user is building a dynamic-theme product, **fetch `…/design-tokens/themes/` first** to get the current recommended pattern — don't assume the file-import approach is the only option.

## Style hooks (per-component overrides)

Each component exposes a small set of `--jh-*` custom properties that consumers can override. These are documented:

- On the component's Storybook page (the "Style hooks" section).
- In `custom-elements.json` (the `cssProperties` array on each tag entry).

Override locally with normal CSS specificity — set the custom property on a parent or on the element itself.

## When this file is the wrong place

- "What's the right *visual* color for X?" → [foundations.md](foundations.md)
- "Which props does `jh-button` expose?" → [components.md](components.md)
- "How do I install jh-core?" → [getting-started.md](getting-started.md)
