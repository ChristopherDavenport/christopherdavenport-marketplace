# Templates & Directives — Deep Dive

## Expression Binding Types

### Text / Child Content
```ts
html`<p>${this.message}</p>`
html`<p>Hello ${this.firstName} ${this.lastName}</p>`
```
Values are escaped by default — HTML entities are rendered as text, not markup.

### Attribute Binding
```ts
html`<div id=${this.id} class=${this.cls}></div>`
```
Sets the attribute value. If the expression is `undefined` or `null`, the attribute is removed.

### Boolean Attribute
```ts
html`<input ?disabled=${this.isDisabled}>`
html`<details ?open=${this.expanded}>`
```
Truthy → attribute present. Falsy → attribute removed. Follows HTML boolean attribute semantics.

### Property Binding
```ts
html`<my-child .userData=${this.user}></my-child>`
html`<input .value=${this.inputValue}>`
```
Sets the JavaScript property directly (not the HTML attribute). Use for complex objects, arrays, or when the property and attribute behave differently (e.g., `input.value`).

### Event Listener
```ts
html`<button @click=${this._handleClick}>OK</button>`
html`<input @input=${(e) => this._onInput(e)}>`
```
Adds an event listener. Lit automatically binds `this` for method references. Inline arrows work but create a new function each render — use method references for performance.

## The `nothing` Sentinel

```ts
import { nothing } from 'lit';

render() {
  return this.showContent ? html`<div>Content</div>` : nothing;
}
```
Renders no DOM node at all. Better than empty string `''` which leaves an empty text node.

## Directive Reference

### `repeat(items, keyFn, template)`

Efficient keyed list rendering. Maintains DOM identity when items reorder.

```ts
import { repeat } from 'lit/directives/repeat.js';

render() {
  return html`
    <ul>
      ${repeat(this.items, (item) => item.id, (item) => html`
        <li>${item.name}</li>
      `)}
    </ul>
  `;
}
```

**When to use `repeat` vs `.map()`:**
- Use `repeat` when items have stable keys AND reorder, insert, or remove frequently
- Use `.map()` for simple static lists or when items always fully re-render anyway

### `classMap(classInfo)`

```ts
import { classMap } from 'lit/directives/class-map.js';

render() {
  const classes = { active: this.isActive, disabled: this.isDisabled, highlight: true };
  return html`<div class=${classMap(classes)}>Content</div>`;
}
```
Keys are class names, values are booleans. Only truthy classes are applied.

### `styleMap(styleInfo)`

```ts
import { styleMap } from 'lit/directives/style-map.js';

render() {
  const styles = { color: this.textColor, '--custom-prop': this.customVal };
  return html`<div style=${styleMap(styles)}>Content</div>`;
}
```
Keys are CSS property names (camelCase or kebab-case). Handles CSS custom properties.

### `ifDefined(value)`

```ts
import { ifDefined } from 'lit/directives/if-defined.js';

html`<img src=${ifDefined(this.src)} alt=${ifDefined(this.alt)}>`
```
If value is `undefined`, the attribute is not set. If defined (including `null`, `''`, `0`), the attribute is set.

### `cache(templateResult)`

```ts
import { cache } from 'lit/directives/cache.js';

render() {
  return cache(this.view === 'detail'
    ? html`<detail-view .item=${this.item}></detail-view>`
    : html`<list-view .items=${this.items}></list-view>`
  );
}
```
Preserves the DOM of the inactive template instead of destroying it. Useful for tab-like UIs where switching back should maintain scroll position, input state, etc.

### `guard(deps, valueFn)`

```ts
import { guard } from 'lit/directives/guard.js';

render() {
  return html`
    ${guard([this.items], () => repeat(this.items, (i) => i.id, (i) => html`<li>${i.name}</li>`))}
  `;
}
```
Only re-evaluates the value function when dependencies change. Useful for expensive template computations.

### `live(value)`

```ts
import { live } from 'lit/directives/live.js';

html`<input .value=${live(this.inputValue)}>`
```
Checks the live DOM value before setting. Use when external code (e.g., a library) may mutate the DOM value between renders.

### `ref(refObject)`

```ts
import { ref, createRef } from 'lit/directives/ref.js';

private _inputRef = createRef<HTMLInputElement>();

render() {
  return html`<input ${ref(this._inputRef)}>`;
}

firstUpdated() {
  this._inputRef.value?.focus();
}
```
Alternative to `@query` — stores element references that track across renders.

### `unsafeHTML(string)` / `unsafeSVG(string)`

```ts
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import DOMPurify from 'dompurify';

render() {
  return html`<div>${unsafeHTML(DOMPurify.sanitize(this.htmlContent))}</div>`;
}
```
Renders raw HTML/SVG markup. **Always sanitize user-provided content** — this is a direct XSS vector if used with untrusted input.

### `templateContent(templateEl)`

```ts
import { templateContent } from 'lit/directives/template-content.js';

const tpl = document.querySelector('#my-template') as HTMLTemplateElement;
html`${templateContent(tpl)}`
```
Stamps an HTML `<template>` element's content. Useful for server-rendered templates.

## Conditional Rendering

```ts
render() {
  return html`
    ${this.loading
      ? html`<spinner-el></spinner-el>`
      : html`<div>${this.content}</div>`}
  `;
}
```

Use ternaries for two-branch conditionals. For "render or nothing", use the `nothing` sentinel instead of an empty string.

## Styles

Styles are scoped to the component via Shadow DOM. External styles do not leak in; component styles do not leak out.

```ts
static styles = css`
  :host { display: block; }
  :host([hidden]) { display: none; }
  .container { padding: 16px; }
`;
```

### Style Composition

Combine multiple style sheets with arrays:

```ts
static styles = [resetStyles, sharedStyles, css`/* component-specific */`];
```

### Theming with CSS Custom Properties

CSS custom properties pierce the Shadow DOM — use them to expose customization points:

```ts
static styles = css`
  :host { --button-bg: blue; }
  button { background: var(--button-bg); }
`;
```

Consumers override: `<my-button style="--button-bg: red;"></my-button>`

### Key Selectors

| Selector | Purpose |
|----------|---------|
| `:host` | The component element itself |
| `:host([attr])` | Component when it has an attribute |
| `:host(.class)` | Component when it has a class |
| `::slotted(selector)` | Slotted light DOM children (top-level only) |

## Rendering Behavior

- `render()` is called synchronously during the update cycle
- Multiple property changes in the same microtask are batched into one render
- Template expressions are compared by identity — only changed parts update the DOM
- Static template structure (tags, attributes) is parsed once and cached
- Dynamic values (expressions) are the only parts that update on re-render

## Common Pitfalls

### Styles leaking or not applying
**Cause:** Forgetting `:host` for the component itself, or expecting external styles to penetrate the Shadow DOM.
**Fix:** Use `:host { display: block; }` (or `inline-block`) — custom elements are `display: inline` by default, which often surprises. For external customization, expose CSS custom properties (they pierce shadow DOM); never rely on parent styles cascading in.

### Inline arrow handlers re-bind every render
**Cause:** `@click=${() => this._foo()}` creates a new function each render, defeating identity-based event binding.
**Fix:** Use a method reference: `@click=${this._foo}`. Lit auto-binds `this`. Reserve inline arrows for closures that genuinely need per-render state.

### Conditional rendering leaves empty text nodes
**Cause:** Returning `''` (empty string) from a conditional branch creates an empty text node in the DOM.
**Fix:** Return the `nothing` sentinel instead — it renders no node at all.
