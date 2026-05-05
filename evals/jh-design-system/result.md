# Eval report: `jh-design-system`

- Cases: **6**
- Expectations met: **1/6** (skill_wins 0/4, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **0**, baseline won **0**, ties **6**
- Rubric pass-rate (over 5 scored case(s)): baseline **93%**, skill **90%** (Δ **-3%**)
- CLI cost: **$1.04** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `tag-prefix-and-import` | skill_wins | ✗ | **tie** | 100% | 100% |
| `token-tier-discipline` | skill_wins | ✗ | **tie** | 67% | 100% |
| `password-input-variant` | skill_wins | ✗ | **tie** | 100% | 100% |
| `dark-mode-switch` | skill_wins | ✗ | **tie** | 100% | 100% |
| `invent-component` | skill_wins_strict | ✗ | **tie** | 100% | 50% |
| `offtopic-python-async` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `tag-prefix-and-import`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I want to use the Jack Henry Design System button component
(`@jack-henry/jh-ui`) in a Lit app. What's the import path,
what tag do I render, and is there anything I need to set up
before it'll look right?
```

**Judge:** **tie** — Both answers are essentially identical in quality, covering all three rubric criteria: the jh-button tag, the components-subpath import path, and the theme CSS requirement. The structure, code examples, and explanations are nearly equivalent, with only minor stylistic differences between them.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| names jh-button tag | tie |
| shows components-subpath import (no barrel) | tie |
| requires theme CSS import | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names jh-button tag | ✓ | `jh-button` |
| shows components-subpath import (no barrel) | ✓ | `@jack-henry/jh-ui/components/` |
| requires theme CSS import | ✓ | `jh-theme-light` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| names jh-button tag | ✓ | `jh-button` |
| shows components-subpath import (no barrel) | ✓ | `@jack-henry/jh-ui/components/` |
| requires theme CSS import | ✓ | `jh-theme-light` |

<details><summary>Baseline answer</summary>

Here's the quick version for `@jack-henry/jh-ui` in a Lit app:

## 1. Import path (no barrel)

`jh-ui` doesn't expose a top-level barrel — you import each component from its own subpath so you only register what you use:

```js
import '@jack-henry/jh-ui/components/button/button.js';
```

Not `import '@jack-henry/jh-ui'`. That won't side-effect-register the element.

## 2. Tag

The component self-registers as a custom element:

```html
<jh-button variant="primary">Save</jh-button>
```

So in your Lit template:

```js
import { LitElement, html } from 'lit';
import '@jack-henry/jh-ui/components/button/button.js';

class MyView extends LitElement {
  render() {
    return html`<jh-button variant="primary">Save</jh-button>`;
  }
}
customElements.define('my-view', MyView);
```

## 3. The setup gotcha — theme CSS

This is the one that bites people: `jh-button` (and every other `jh-*` component) styles itself with CSS custom properties like `--jh-color-container-primary-enabled`. Those variables don't exist by default. You have to load a theme stylesheet that defines them on `:root`, or the button will render unstyled / transparent.

Pick one of:

```js
import '@jack-henry/jh-ui/themes/jh-theme-light.css';
// or
import '@jack-henry/jh-ui/themes/jh-theme-dark.css';
```

Load it once at your app entry (e.g. `main.ts`/`index.ts`), before your first render. Because the theme defines variables on `:root`, they cascade through Shadow DOM into the components automatically — you don't need to re-import it inside each Lit element.

### TL;DR

| What | Value |
|---|---|
| Tag | `<jh-button>` |
| Import | `@jack-henry/jh-ui/components/button/button.js` |
| One-time setup | import `jh-theme-light.css` (or `-dark.css`) at app entry |

If your button shows up but looks like an unstyled `<button>` with no brand color, it's almost always a missing theme import.

</details>

<details><summary>Skill-loaded answer</summary>

Here's the rundown for dropping a JH button into a Lit app:

## 1. The tag

```html
<jh-button>Save</jh-button>
```

All JH components are custom elements with the `jh-` prefix, so it's `<jh-button>` — not `<JhButton>` or anything React-flavored.

## 2. The import path

Import the component file directly — there is **no barrel export** off the package root, so `import '@jack-henry/jh-ui'` won't work. Reach into the component subpath:

```js
// somewhere in your app's entry / the Lit component that uses it
import '@jack-henry/jh-ui/components/button/button.js';
```

That side-effect import registers the `jh-button` custom element with `customElements.define`. You don't need to name an export — just importing the file is enough.

In a Lit component it looks like:

```js
import { LitElement, html } from 'lit';
import '@jack-henry/jh-ui/components/button/button.js';

class MyForm extends LitElement {
  render() {
    return html`<jh-button variant="primary">Save</jh-button>`;
  }
}
customElements.define('my-form', MyForm);
```

## 3. The thing people forget: load a theme

`jh-ui` components style themselves with CSS custom properties like `--jh-color-container-primary-enabled`, `--jh-space-*`, `--jh-radius-*`, etc. Those variables are **not** shipped inside the component files — if you skip this step the button will render but look unstyled / wrong colors.

You need to load a theme stylesheet once at the app level so the tokens resolve on `:root`:

```js
// in your app entry (e.g. main.ts / index.ts), once
import '@jack-henry/jh-ui/themes/jh-theme-light.css';
// or '@jack-henry/jh-ui/themes/jh-theme-dark.css'
```

A few notes on that:

- Pick **one** theme to start. Both light and dark target `:root`, so importing both at once just lets the second one win — you'd need scoping (e.g. `data-theme="dark"` on `<html>`) or a dynamic swap to actually toggle.
- The theme provides the *alias* tokens (`--jh-color-container-*`, `--jh-color-content-*`, etc.) that the components consume internally. If you ever style your own product CSS, prefer those alias tokens over the raw global palette.
- Because Lit components use shadow DOM, custom properties inherit through the shadow boundary, so a single global theme import is enough — you don't have to re-import it inside each Lit component.

## TL;DR

| Question | Answer |
|---|---|
| Tag | `<jh-button>` |
| Import | `import '@jack-henry/jh-ui/components/button/button.js'` |
| Setup | Also import `@jack-henry/jh-ui/themes/jh-theme-light.css` (or `-dark`) once at the app entry so the design tokens are defined |

</details>

---

### `token-tier-discipline`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I'm styling some product CSS that uses the Jack Henry Design
System. I want a "primary" background color that matches the
JH brand. Can I just write `background: var(--jh-color-blue-600)`?
What's the right pattern?
```

**Judge:** **tie** — Both answers are nearly identical in quality, covering all three tiers clearly, steering away from raw global tokens, and recommending alias tokens with concrete examples. Answer A provides slightly more detail on state coverage and style hook usage with a concrete CSS example for component overrides, while Answer B is marginally more concise and equally complete. Neither has a meaningful advantage across the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| steers away from raw global token | tie |
| recommends alias token | tie |
| mentions all three tiers | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| steers away from raw global token | ✗ | |
| recommends alias token | ✓ | `Alias` |
| mentions all three tiers | ✓ | `global \| Alias \| style hook` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| steers away from raw global token | ✓ | `global = internal` |
| recommends alias token | ✓ | `alias` |
| mentions all three tiers | ✓ | `global \| alias \| Style hook` |

<details><summary>Baseline answer</summary>

Short answer: **no, don't reach for `--jh-color-blue-600` directly.** That's a *global* token — it's effectively internal to the design system, and wiring it into product CSS bypasses the layer that's allowed to change brand decisions for you.

## The three-tier model

The JH Design System tokens are layered. You should pick the most specific tier that fits your use case:

1. **Global tokens** — raw palette / scale values like `--jh-color-blue-600`, `--jh-space-4`, `--jh-font-size-300`. These are the *source* values. Treat them as internal to the DS; do not consume them from product code.
2. **Alias (semantic) tokens** — intent-based names like `--jh-color-container-primary-enabled`, `--jh-color-content-on-primary`, `--jh-color-border-subtle`. These are what product CSS should consume. They re-point to the right global token per theme (light/dark) and per state.
3. **Component style hooks** — per-component overrides exposed by a specific element, e.g. `--jh-button-background-color`. Use these when you need to tweak one component instance, not to define your own surfaces.

## What to write instead

For a "primary" surface in your own component:

```css
.my-hero {
  background: var(--jh-color-container-primary-enabled);
  color: var(--jh-color-content-on-primary);
}
```

If you're styling a JH component instance, prefer its style hook:

```css
jh-button[variant="primary"] {
  --jh-button-background-color: var(--jh-color-container-primary-enabled);
}
```

## Why this matters

- **Theming works for free.** Alias tokens resolve differently under `jh-theme-light.css` vs `jh-theme-dark.css`. Hard-coding `--jh-color-blue-600` will look wrong (or unreadable) in dark mode.
- **Brand changes don't break you.** If JH re-points "primary" from blue-600 to blue-700, alias consumers update; global consumers drift.
- **State coverage.** Alias tokens come in `-enabled` / `-hover` / `-pressed` / `-disabled` flavors, so you get the whole interaction set without re-deriving it from the palette.

Rule of thumb: **product code → alias tokens; component-instance tweaks → style hooks; globals → leave to the DS.**

</details>

<details><summary>Skill-loaded answer</summary>

Short answer: **no, don't reach for `--jh-color-blue-600` directly.** That's a *global* token and product code shouldn't wire to it. Use an **alias** token instead.

## The three tiers

The JH Design System uses a three-tier token model, and the tier you pick matters:

1. **Global tokens** — e.g. `--jh-color-blue-600`, `--jh-color-gray-100`. The raw palette. These are considered **internal** to the design system. They're the primitives the alias tier is built on; they can be renumbered or repurposed without warning. **Don't consume these from product code.**

2. **Alias tokens** — e.g. `--jh-color-container-primary-enabled`, `--jh-color-content-primary`, `--jh-color-border-subtle`. These are *semantic*: they describe the role (container vs. content vs. border, primary vs. secondary, enabled vs. hover vs. disabled). This is the tier product CSS should use. When the brand re-tunes which blue maps to "primary," your UI follows automatically.

3. **Style hooks** — per-component custom properties that a JH component exposes for targeted overrides (e.g. something like `--jh-button-background`). Reach for these when you specifically need to tweak one component instance, not for general layout color.

## What to write

For a "primary" brand background on your own element:

```css
.my-callout {
  background: var(--jh-color-container-primary-enabled);
  color: var(--jh-color-content-on-primary);
}
```

Pick the alias whose *name describes the role* you want — container vs. content (text/icon) vs. border, and the state (enabled/hover/disabled). If you're overriding a JH component's background, prefer that component's style hook.

## Why it matters

- The global → alias indirection is what lets light/dark themes and brand re-skins work. If you bind to `--jh-color-blue-600`, you'll punch through the theme and your "primary" won't follow dark mode or rebrand changes.
- It also means your component will look fine even on themes where "primary" isn't blue at all.

Rule of thumb: **global = internal, alias = product code, style hook = per-component override.**

</details>

---

### `password-input-variant`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
The Jack Henry design site has a "password input" component
page (`/v2/components/input-password/`). What tag do I actually
use, and what attribute makes it a password field?
```

**Judge:** **tie** — Both answers correctly identify that `<jh-input type="password">` is the right approach and that there is no separate `<jh-password-input>` element. Both explain the doc-page-to-variant mapping clearly. The differences are minor: Answer A mentions theme stylesheets while Answer B suggests checking `custom-elements.json` for verification — both are useful additions but neither is clearly superior overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses jh-input not a separate tag | tie |
| shows type="password" attribute | tie |
| distinguishes site doc from tag | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses jh-input not a separate tag | ✓ | `<jh-input` |
| shows type="password" attribute | ✓ | `type="password` |
| distinguishes site doc from tag | ✓ | `variant` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses jh-input not a separate tag | ✓ | `<jh-input` |
| shows type="password" attribute | ✓ | `type="password` |
| distinguishes site doc from tag | ✓ | `variant` |

<details><summary>Baseline answer</summary>

You actually use the **`<jh-input>`** tag with the **`type="password"`** attribute — there is no separate `<jh-password-input>` element.

```html
<jh-input type="password" label="Password"></jh-input>
```

A common point of confusion: the design site's `/v2/components/input-password/` page documents a **variant** of the base input component, not a distinct custom element. Many of JH's component doc pages map this way — one underlying tag (`jh-input`) with different `type` values (`text`, `password`, `email`, `number`, etc.) producing the documented variants. So when you see a doc page like `input-password`, `input-email`, or similar, reach for `<jh-input type="...">` rather than hunting for a dedicated tag.

Import is still the usual subpath (no barrel):

```js
import '@jack-henry/jh-ui/components/input/input.js';
```

If you want to verify which variants the element actually accepts, check `custom-elements.json` in `@jack-henry/jh-ui` — it'll list the supported `type` values on `jh-input` directly.

</details>

<details><summary>Skill-loaded answer</summary>

You use the base `<jh-input>` tag with the `type="password"` attribute — there is no separate `<jh-password-input>` element.

```html
<jh-input type="password" label="Password" name="password"></jh-input>
```

Why the confusion: the design site's `/v2/components/input-password/` page documents a **variant** of the base input component, not a distinct custom element. The JH UI library exposes a single `jh-input` tag whose behavior (password masking, reveal toggle, etc.) is selected via the standard `type` attribute, mirroring the native `<input type="...">` pattern. So site doc pages like `input-password`, `input-email`, `input-search`, etc. all map back to the same underlying tag.

Import it from the components subpath (no barrel):

```js
import '@jack-henry/jh-ui/components/input/input.js';
```

And make sure a theme stylesheet (`jh-theme-light.css` or `jh-theme-dark.css`) is loaded so the token CSS variables resolve.

</details>

---

### `dark-mode-switch`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
My Jack Henry Design System app currently imports
`jh-theme-light.css`. I want to add dark mode support so users
can toggle. What's the recommended approach?
```

**Judge:** **tie** — Both answers correctly identify that both themes target :root and explain why naive dual-import fails, and both recommend the same two solutions (dynamic swap and build-time re-scope). Answer A uses adoptedStyleSheets while Answer B uses a <link> element swap — both valid. Answer B adds useful extras like alias vs global token guidance and color-scheme property, while Answer A has a cleaner comparison table. Neither is clearly superior on the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies both themes target :root | tie |
| recommends scoping or swapping | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies both themes target :root | ✓ | `:root` |
| recommends scoping or swapping | ✓ | `swap` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies both themes target :root | ✓ | `:root` |
| recommends scoping or swapping | ✓ | `swap` |

<details><summary>Baseline answer</summary>

# Adding dark mode to a Jack Henry Design System app

## The gotcha first

Both `jh-theme-light.css` and `jh-theme-dark.css` define their custom properties on the **same selector — `:root`**. That means if you naively import both, whichever loads second simply overwrites the first, and a `prefers-color-scheme` media query inside your own CSS won't help because the token files don't ship that wrapper themselves.

So you can't just do:

```js
// ❌ doesn't work — second import wins, no toggle
import '@jack-henry/jh-core/jh-theme-light.css';
import '@jack-henry/jh-core/jh-theme-dark.css';
```

You need to either **swap** the active theme stylesheet at runtime, or **re-scope** the token declarations to a theme attribute/class.

---

## Recommended approach: dynamic stylesheet swap

This is the simplest pattern and keeps the JH-shipped CSS untouched.

```js
// theme-controller.js
const themes = {
  light: () => import('@jack-henry/jh-core/jh-theme-light.css?inline'),
  dark:  () => import('@jack-henry/jh-core/jh-theme-dark.css?inline'),
};

let currentSheet;

export async function setTheme(name) {
  const css = (await themes[name]()).default;
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(css);

  document.adoptedStyleSheets = [
    ...document.adoptedStyleSheets.filter(s => s !== currentSheet),
    sheet,
  ];
  currentSheet = sheet;
  document.documentElement.setAttribute('data-theme', name);
  localStorage.setItem('jh-theme', name);
}

setTheme(localStorage.getItem('jh-theme') ?? 'light');
```

Wire a toggle button to `setTheme('dark')` / `setTheme('light')`. Because both files target `:root`, replacing the adopted sheet cleanly swaps the entire alias-token layer — every `jh-button`, `jh-input`, etc. updates in place.

---

## Alternative: re-scope at build time

If you'd rather have both themes live in the document at once (e.g. for an embedded widget that mounts in a `data-theme="dark"` subtree), do a small build-time transform that rewrites the selector:

```css
/* jh-theme-dark.css after re-scope */
:root[data-theme='dark'],
[data-theme='dark'] {
  --jh-color-container-primary-enabled: …;
  /* … */
}
```

Then ship light as the default `:root` declaration and dark as the scoped override. A toggle just flips `document.documentElement.dataset.theme`. PostCSS's `postcss-prefix-selector` or a tiny custom plugin handles this in a few lines.

---

## What I'd avoid

- **`@media (prefers-color-scheme: dark)` inside your own CSS** — the JH token files don't gate themselves on it, so user preference can't override the imported `:root` block.
- **Editing the JH theme files directly** — you lose forward-compat when `@jack-henry/jh-core` updates.
- **Re-declaring alias tokens yourself** — you'd be re-implementing the design system; let the shipped theme files own the values.

---

## Quick recap

| Need | Pick |
|---|---|
| Single app, user toggle | Dynamic swap of adopted stylesheets |
| Both themes coexisting in one DOM | Build-time re-scope to `[data-theme]` |
| Follow OS preference only | Dynamic swap driven by a `matchMedia('(prefers-color-scheme: dark)')` listener |

The dynamic swap is what I'd reach for first — it's a dozen lines and survives JH updates cleanly.

</details>

<details><summary>Skill-loaded answer</summary>

# Adding dark mode to a Jack Henry Design System app

The key thing to know up front: **`jh-theme-light.css` and `jh-theme-dark.css` both define their tokens on `:root`**. That means the "obvious" approach — importing both and gating one with `prefers-color-scheme` — won't work cleanly, because whichever stylesheet loads last wins for everyone, all the time. You can't toggle by adding/removing a class on `<html>` either, because nothing in the shipped CSS is scoped to a class or attribute.

You have two solid options.

## Option 1 — Dynamic stylesheet swap (simplest)

Load exactly one theme at a time and replace it when the user toggles. This works well because the two files declare the same custom property names with different values, so swapping the sheet re-resolves every `var(--jh-color-*)` reference instantly.

```ts
// theme.ts
const THEMES = {
  light: () => import('@jack-henry/jh-ui/themes/jh-theme-light.css?url'),
  dark:  () => import('@jack-henry/jh-ui/themes/jh-theme-dark.css?url'),
};

let linkEl: HTMLLinkElement | null = null;

export async function setTheme(name: 'light' | 'dark') {
  const { default: href } = await THEMES[name]();
  if (!linkEl) {
    linkEl = document.createElement('link');
    linkEl.rel = 'stylesheet';
    document.head.appendChild(linkEl);
  }
  linkEl.href = href;
  document.documentElement.dataset.theme = name;     // for your own CSS
  localStorage.setItem('jh-theme', name);
}

// boot
const initial =
  (localStorage.getItem('jh-theme') as 'light' | 'dark') ??
  (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
setTheme(initial);
```

Pros: no build tweaks, themes stay independently cacheable, FOUC is minimal if you preload the initial theme in `index.html`.

## Option 2 — Re-scope the themes at build time

If you want both themes resident in one bundle (e.g. for instant toggling with no network), copy the two files and rewrite the `:root` selector so they coexist:

```css
/* jh-theme-scoped.css — generated */
[data-theme="light"] { /* ...contents of jh-theme-light.css... */ }
[data-theme="dark"]  { /* ...contents of jh-theme-dark.css...  */ }
```

Then toggle with:

```ts
document.documentElement.dataset.theme = 'dark'; // or 'light'
```

A tiny PostCSS plugin or a 10-line build script (`replace(/:root\b/g, '[data-theme="dark"]')`) is enough. Just remember to redo it whenever you bump `@jack-henry/jh-ui`, since global tokens occasionally change.

## Recommendation

For most apps, **go with Option 1** — it's a few lines, doesn't fork the vendor CSS, and survives package upgrades without intervention. Reach for Option 2 only if you need synchronous, no-flash toggling (e.g. inside a settings preview where the user flips back and forth rapidly), or if your CSP forbids dynamic `<link>` injection.

A few extra tips either way:

- Make sure your **product CSS** uses **alias tokens** (`--jh-color-container-primary-enabled`, `--jh-color-content-primary`, etc.), not global ones (`--jh-color-blue-600`). The alias layer is what actually changes between light and dark; if you've hard-coded globals, dark mode will look broken in those spots.
- Set `color-scheme: light dark` on `:root` so native form controls and scrollbars follow along.
- Persist the user's choice (localStorage) and respect `prefers-color-scheme` only as the initial default.

</details>

---

### `invent-component`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I need a Jack Henry Design System table with sortable columns
and pagination. What component do I use and how do I configure
sorting? Show me a small example.
```

**Judge:** **tie** — Both answers correctly state that jh-table is documented but not implemented, avoid inventing fake API like jh-table-row/jh-table-cell, and provide the same verification approach via custom-elements.json. Both recommend TanStack Table with JH alias tokens as the practical alternative. The differences are cosmetic — Answer A is slightly more detailed in its recommendations while Answer B is slightly more concise — but neither is meaningfully better on the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states table is documented but not implemented | tie |
| avoids inventing jh-table-row / jh-table-cell API | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states table is documented but not implemented | ✓ | `not yet implement` |
| avoids inventing jh-table-row / jh-table-cell API | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states table is documented but not implemented | ✓ | `not yet implement` |
| avoids inventing jh-table-row / jh-table-cell API | ✗ | `jh-table-row sortable="` |

<details><summary>Baseline answer</summary>

Short answer: **don't ship this yet** — and I'd push back on the premise of the question before writing any markup.

## What's actually shippable

The Jack Henry design site does have table-related documentation pages (under the data display section), but as of the current `@jack-henry/jh-ui` package, **a `jh-table` component is not yet implemented in source**. The site is ahead of the code here. So:

- There is no shipped `<jh-table>` tag.
- There is no shipped sort API, no `sortable` attribute, no `sort-direction` event, no pagination element — and I'm not going to invent one for you, because anything I wrote here would be fiction that compiles but doesn't render.
- It's not exported from `@jack-henry/jh-ui/components/...`, and you won't find it in the package's `custom-elements.json`.

## How to verify before you build

Don't trust me, don't trust the design site — check the manifest:

```bash
# In your app or in a scratch dir with @jack-henry/jh-ui installed
cat node_modules/@jack-henry/jh-ui/custom-elements.json \
  | jq '.modules[].declarations[]?.tagName' | sort -u
```

If `jh-table` (or `jh-table-row`, `jh-table-cell`, `jh-pagination`, etc.) doesn't show up there, it doesn't exist as a custom element in that release. You can also grep the Banno monorepo where the components live for the tag name; absence there is the definitive answer.

## What I'd actually recommend

Pick one of these three, in order of preference:

1. **Ask the JH DS team** what the planned tag name and API will be, and whether there's a target release. If something is in flight you want to align to it, not paint yourself into a corner.
2. **Build a local table** using primitives that *do* exist — semantic `<table>` markup styled with JH **alias** tokens (e.g. `--jh-color-container-primary-enabled`, `--jh-color-content-primary`, spacing aliases), and `jh-button` / `jh-icon-button` for header sort affordances and pager controls. Keep it isolated behind your own `<app-data-table>` wrapper so you can swap it out for `jh-table` later without touching call sites.
3. **Use a headless table library** (TanStack Table is the usual pick) for the sort/paginate logic, and render with the same JH-token-styled markup from option 2. This is what I'd do for anything non-trivial — sorting, multi-column sort, and pagination state are easy to get subtly wrong.

I'd rather hand you a wrapper that's honest about being a stopgap than a `<jh-table sortable …>` snippet that looks authoritative and isn't real. If you want, point me at your column shape and I'll sketch the `<app-data-table>` wrapper using only currently-shipped JH pieces.

</details>

<details><summary>Skill-loaded answer</summary>

Short answer: **don't ship this yet.** There's a gap you should know about before you write any code.

## The situation with `jh-table`

The Jack Henry Design System **documentation site shows table components**, but as of today they are **not yet implemented in the published `@jack-henry/jh-ui` package**. The site is running ahead of the source. There is no `jh-table` custom element you can import, render, and configure — so any "small example" I gave you with sortable columns and pagination would be invented API, and your build would fail (or worse, look like it works in a snippet but reference tags that don't exist at runtime).

I'd rather flag that than make something up.

## How to verify before you commit to an approach

Two quick checks so you don't have to take my word for it:

1. **`custom-elements.json` in `@jack-henry/jh-ui`** — this is the manifest of every element actually shipped. If `jh-table` isn't in there, it isn't real yet. From your app:
   ```bash
   cat node_modules/@jack-henry/jh-ui/custom-elements.json | jq '.modules[].declarations[]?.tagName' | grep -i table
   ```
2. **The Banno consumer repo** — if the largest internal consumer hasn't adopted it, that's a strong signal it isn't ready. Search there for `jh-table` usage.

## What to do in the meantime

Pick one of these, depending on how much you need it to "feel JH":

- **Build it locally** using JH **alias tokens** for surface, border, and text (e.g. `--jh-color-container-primary-enabled`, `--jh-color-border-subtle`, `--jh-color-content-primary`) so it's drop-in replaceable later. Avoid raw global tokens like `--jh-color-blue-600` — those are internal to the alias layer.
- **Use a headless table library** (TanStack Table, for example) for sort + pagination logic, and style the markup with JH alias tokens. Headless keeps the API surface yours, so swapping to `jh-table` later is a render-layer change, not a logic rewrite.
- **Ask the DS team for an ETA / RFC link** before you invest. If `jh-table` lands in the next minor, it's worth waiting; if not, the headless route is safer.

## What I would *not* recommend

Writing something like `<jh-table-row sortable="true">` or `<jh-table-column field="name" sort-direction="asc">` based on the doc site. Those attributes aren't contractually defined anywhere you can verify, and you'd be locking in guesses.

Want me to sketch the headless + JH-alias-tokens version instead? That one I can write honestly.

</details>

---

### `offtopic-python-async`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the difference between asyncio.gather and
asyncio.wait in Python? A short example would help.
```

**Judge:** **tie** — Both answers are essentially equivalent in correctness, structure, and usefulness. They cover the same key differences, use nearly identical examples, and provide the same rule-of-thumb guidance. Minor differences (Answer A mentions cancellation behavior explicitly; Answer B notes coroutines deprecated since 3.8) are negligible.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

# `asyncio.gather` vs `asyncio.wait`

Both run awaitables concurrently, but they differ in how you interact with the results.

## Key Differences

| Feature | `asyncio.gather` | `asyncio.wait` |
|---|---|---|
| **Returns** | A list of results in the order tasks were passed | Two sets: `(done, pending)` of `Task` objects |
| **Result access** | Direct (`results = await gather(...)`) | Manual (`task.result()` on each) |
| **Error handling** | Raises first exception (or returns it if `return_exceptions=True`) | Never raises — exceptions stay inside tasks |
| **Partial completion** | Always waits for all (unless cancelled) | Supports `FIRST_COMPLETED`, `FIRST_EXCEPTION`, `ALL_COMPLETED` |
| **Input** | Accepts coroutines or tasks | Requires `Task`/`Future` objects (coroutines deprecated since 3.8) |

## Short Example

```python
import asyncio

async def work(name, delay):
    await asyncio.sleep(delay)
    return f"{name} done"

async def main():
    # gather: simple, ordered results
    results = await asyncio.gather(
        work("A", 1),
        work("B", 2),
    )
    print(results)  # ['A done', 'B done']

    # wait: more control, e.g. stop as soon as one finishes
    tasks = [asyncio.create_task(work("C", 1)),
             asyncio.create_task(work("D", 3))]
    done, pending = await asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED
    )
    for t in done:
        print(t.result())  # 'C done'
    for t in pending:
        t.cancel()

asyncio.run(main())
```

## Rule of Thumb

- Use **`gather`** when you want all results back in order and want exceptions to propagate.
- Use **`wait`** when you need fine-grained control — e.g., reacting to the first completed task, timeouts without cancellation, or inspecting task state manually.

For most everyday concurrency, `gather` (or the newer `asyncio.TaskGroup` in Python 3.11+) is the cleaner choice.

</details>

<details><summary>Skill-loaded answer</summary>

# `asyncio.gather` vs `asyncio.wait`

Both run awaitables concurrently, but they differ in their return values and error handling.

## Key differences

| Feature | `asyncio.gather` | `asyncio.wait` |
|---|---|---|
| **Returns** | List of results in the order tasks were passed | Two sets: `(done, pending)` of `Task` objects |
| **Result access** | Direct values | Must call `task.result()` yourself |
| **Errors** | Raises immediately (or collects them with `return_exceptions=True`) | Never raises — exceptions stay on the tasks |
| **Cancellation** | Cancels remaining tasks if one fails (when `return_exceptions=False`) | Doesn't touch other tasks |
| **Control** | All-or-nothing | Supports `return_when=FIRST_COMPLETED` / `FIRST_EXCEPTION` |
| **Input** | Accepts coroutines or tasks | Requires tasks (in 3.11+ coroutines are deprecated) |

## Example

```python
import asyncio

async def work(name, delay):
    await asyncio.sleep(delay)
    return f"{name} done"

async def main():
    # gather: ordered results, easy to use
    results = await asyncio.gather(
        work("A", 1),
        work("B", 2),
    )
    print(results)
    # ['A done', 'B done']

    # wait: more control, returns task sets
    tasks = [asyncio.create_task(work("C", 1)),
             asyncio.create_task(work("D", 3))]

    done, pending = await asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED
    )
    for t in done:
        print(t.result())   # 'C done'
    for t in pending:
        t.cancel()          # clean up the rest

asyncio.run(main())
```

## Rule of thumb

- Reach for **`gather`** when you want all results back together (the common case).
- Reach for **`wait`** when you need fine-grained control — e.g., react as soon as the first task finishes, or inspect tasks without raising on failure.
- For newer code, also consider **`asyncio.TaskGroup`** (Python 3.11+), which is the modern, structured-concurrency replacement for `gather`.

</details>

---
