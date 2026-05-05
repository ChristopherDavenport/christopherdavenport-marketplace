# Components

`@jack-henry/jh-ui` ships **21 web component tags**, all prefixed `jh-`. The site documents **30 component pages** — the extras are usage variants (input by type, table sub-cells) that don't have their own tag.

## The 21 jh-ui tags

Source of truth: [`packages/jh-ui/custom-elements.json`](https://raw.githubusercontent.com/Banno/jack-henry-design-system/next/packages/jh-ui/custom-elements.json) (default branch is `next`). Always read this file for attributes, properties, slots, events, and CSS custom properties of a component before answering API questions.

| Tag | Site doc page | Source dir |
|---|---|---|
| `jh-badge` | `/v2/components/badge/` | `packages/jh-ui/components/badge/` |
| `jh-button` | `/v2/components/button/` | `packages/jh-ui/components/button/` |
| `jh-card` | `/v2/components/card/` | `packages/jh-ui/components/card/` |
| `jh-checkbox` | `/v2/components/checkbox/` | `packages/jh-ui/components/checkbox/` |
| `jh-checkbox-group` | `/v2/components/checkbox-group/` | `packages/jh-ui/components/checkbox-group/` |
| `jh-divider` | `/v2/components/divider/` | `packages/jh-ui/components/divider/` |
| `jh-icon` | `/v2/components/icon/` | `packages/jh-ui/components/icon/` |
| `jh-input` | `/v2/components/input/` (and the input-* variant pages) | `packages/jh-ui/components/input/` |
| `jh-list-group` | `/v2/components/list-group/` | `packages/jh-ui/components/list-group/` |
| `jh-list-item` | `/v2/components/list-item/` | `packages/jh-ui/components/list-item/` |
| `jh-menu` | `/v2/components/menu/` | `packages/jh-ui/components/menu/` |
| `jh-notification` | `/v2/components/notification/` | `packages/jh-ui/components/notification/` |
| `jh-progress` | `/v2/components/progress/` | `packages/jh-ui/components/progress/` |
| `jh-radio` | `/v2/components/radio/` | `packages/jh-ui/components/radio/` |
| `jh-radio-group` | `/v2/components/radio-group/` | `packages/jh-ui/components/radio-group/` |
| `jh-switch` | `/v2/components/switch/` | `packages/jh-ui/components/switch/` |
| `jh-tag` | `/v2/components/tag/` | `packages/jh-ui/components/tag/` |
| `jh-tag-group` | `/v2/components/tag-group/` | `packages/jh-ui/components/tag-group/` |
| `jh-toast` | `/v2/components/toast/` | `packages/jh-ui/components/toast/` |
| `jh-toast-controller` | (no dedicated site page — see toast docs) | `packages/jh-ui/components/toast-controller/` |
| `jh-tooltip` | `/v2/components/tooltip/` | `packages/jh-ui/components/tooltip/` |

## Site pages with no dedicated jh-ui tag

These render as documentation pages but use one of the tags above (or are not yet implemented):

| Site doc page | What it actually is |
|---|---|
| `/v2/components/input-email/` | `<jh-input type="email">` |
| `/v2/components/input-password/` | `<jh-input type="password">` |
| `/v2/components/input-search/` | `<jh-input type="search">` |
| `/v2/components/input-telephone/` | `<jh-input type="tel">` |
| `/v2/components/input-textarea/` | `<jh-input>` (multiline variant) |
| `/v2/components/input-url/` | `<jh-input type="url">` |
| `/v2/components/table/` | **Documented but not yet in `packages/jh-ui` source.** Surface this to the user. |
| `/v2/components/table-data-cell/` | Same — not yet implemented as a tag. |
| `/v2/components/table-header-cell/` | Same. |
| `/v2/components/table-row/` | Same. |

If a user asks for a `<jh-table>` etc., check `packages/jh-ui/components/` again — it may have landed since this reference was written.

## Slug normalization

Map free-text component names to URL slugs:

| User says | Slug |
|---|---|
| "button" | `button` |
| "password input" / "password field" | `input-password` |
| "search field" | `input-search` |
| "phone input" | `input-telephone` |
| "textarea" | `input-textarea` |
| "checkbox group" / "checkboxes" | `checkbox-group` for the group, `checkbox` for one |
| "tag group" / "chips" | `tag-group` |
| "table row" | `table-row` |
| "toast" / "snackbar" | `toast` (use `toast-controller` to manage queueing) |
| "tooltip" | `tooltip` |

Always **kebab-case**, no `jh-` prefix in the URL.

## Component page anatomy (jackhenry.design)

Every component page on `/v2/components/{slug}/` is structured the same way:

1. **Overview** — one-sentence purpose.
2. **Code Documentation** — link to the Storybook page (props, code).
3. **Anatomy** — labeled parts diagram (container, label, icon, etc.).
4. **Variants** — appearance/size/state options with examples.
5. **Behavior** — interaction states (enabled, hover, focus, active, disabled, pending).
6. **Design Tool Guidance** — Figma instructions.

When a user asks "how does X look / when do I use it?", quote from sections 1, 3, 4, 5. When they ask "what props does X take?", go to Storybook or `custom-elements.json`.

## Where to look for what

| Question | Source |
|---|---|
| "When do I use this? What does it look like?" | Site `/v2/components/{slug}/` page |
| "What attributes / properties / slots / events does it have?" | Storybook docs page **or** `custom-elements.json` (preferred for accuracy) |
| "Show me a code example" | Storybook (the `--docs` page renders a live example) |
| "What CSS custom properties can I override?" | `custom-elements.json` (`cssProperties` array) |
| "Why does it behave like X? Is there a bug?" | `gh issue list -R Banno/jack-henry-design-system` and the source `.js` file |
| "What version is shipped?" | `gh api repos/Banno/jack-henry-design-system/contents/packages/jh-ui/package.json` → `version` |

## Importing a component

```js
// Side-effect import registers the custom element.
import '@jack-henry/jh-ui/components/button/button.js';
```

The package's `files` allowlist exposes `components/**/!(*.stories).js`, so you import the bare component file. There is no barrel export — register only what you use.
