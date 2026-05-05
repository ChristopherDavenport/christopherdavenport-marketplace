# Getting Started

Onboarding for designers and developers. Start here for "how do I install it" and "where's the Figma kit" type questions.

## URLs

| Topic | URL |
|---|---|
| Designing (Figma) | `https://jackhenry.design/v2/about/getting-started/designing/` |
| Developing (npm + Storybook) | `https://jackhenry.design/v2/about/getting-started/developing/` |
| About / overview | `https://jackhenry.design/v2/about/` |
| License | `https://jackhenry.design/v2/about/license/` |
| Releases | `https://jackhenry.design/v2/about/releases/` |
| Storybook (canonical) | `https://main--68f8e6a25b256d0ef89b13e6.chromatic.com/` |
| GitHub repo | `https://github.com/Banno/jack-henry-design-system` (default branch: `next`) |
| Figma community profile | `https://www.figma.com/@jack_henry` |

## The three packages

| Package | What it provides | When you need it |
|---|---|---|
| `@jack-henry/jh-ui` | 21 web components (`<jh-button>`, `<jh-input>`, etc.). Built on **Lit 2.x**. | Anything UI. |
| `@jack-henry/jh-core` | Design tokens — CSS custom properties, JSON, JS-CSS. Includes pre-built `jh-theme-light.css` and `jh-theme-dark.css`. | Always — you need a theme stylesheet for jh-ui to look right. |
| `@jack-henry/jh-icons` | SVG and web-component icons. | When using `<jh-icon>` or any icon glyph. |

`jh-ui` lists `jh-core` and `jh-icons` as workspace dependencies, so installing `jh-ui` brings them along — but install all three explicitly if you import from each.

## Install

```sh
npm install @jack-henry/jh-ui @jack-henry/jh-core @jack-henry/jh-icons
```

## Minimal usage

```js
// Apply a theme (sets the --jh-* custom properties on :root).
import '@jack-henry/jh-core/platforms/web/css/jh-theme-light.css';

// Register only the components you use.
import '@jack-henry/jh-ui/components/button/button.js';
```

```html
<jh-button>Save</jh-button>
```

That's it — native custom elements, no framework wrapper required. The same import works in plain HTML, Lit, Vue, Svelte, or React (with React's custom-element support / `@lit-labs/react` wrappers).

## Designer flow (Figma)

The designing page walks through four phases:

1. **Set up** — duplicate the base design kit locally and publish it within the appropriate team permissions.
2. **Extend** — build product-specific libraries using components from the base kit.
3. **Update** — manage version transitions by branching and swapping variables to newer base kits.
4. **Theme** — connect custom theme libraries to the base kit to define product-specific variables.

The shared library URL listed on the designing page is internal-only. The public surface is the [Figma community profile](https://www.figma.com/@jack_henry).

## Developer flow

1. Read `.../v2/about/getting-started/developing/` for orientation.
2. Install the three packages.
3. Import a theme CSS from `jh-core` to populate `--jh-*` custom properties.
4. Side-effect-import each component you use from `@jack-henry/jh-ui/components/{name}/{name}.js`.
5. Use Storybook (`https://main--68f8e6a25b256d0ef89b13e6.chromatic.com/`) for live demos and the props table.
6. For source / issues, go to [`Banno/jack-henry-design-system`](https://github.com/Banno/jack-henry-design-system) (default branch `next`).

## Repo layout (top of `packages/`)

```
packages/
  jh-core/    # tokens
    platforms/
      web/css/jh-theme-light.css
      web/css/jh-theme-dark.css
      web/js-css/
      json/
    tokens/
  jh-icons/   # icons
  jh-ui/      # web components
    components/{name}/{name}.js
    custom-elements.json   # authoritative API contract
    package.json
```

## License

Apache-2.0. The system is open source and accepts external contribution issues at the GitHub repo.
