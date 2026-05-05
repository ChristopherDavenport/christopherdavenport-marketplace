# @lit-labs/signals — Deep Dive

> **Labs status:** `@lit-labs/signals` is experimental. The API may change, and it depends on the TC39 Signals proposal polyfill. Not recommended for production yet — flag this to users when recommending it.

**Properties + events handle most state.** `@property`/`@state` for component-scoped values, typed events for upward communication, and context for shared values that change infrequently. Reach for signals only when a value is shared across components AND changes frequently enough that `subscribe: true` re-fires or full re-renders become a measurable cost. For component-local state, signals are strictly extra dependency for no benefit.

Signals are observable state primitives — free-standing values that any code can read or write. Lit elements that read signals during render automatically re-render when the signal changes, with no event plumbing or context required.

## Installation

```bash
npm i @lit-labs/signals
```

The package depends on `signal-polyfill`. If multiple copies end up installed, signals from one polyfill won't notify watchers from the other:

```bash
npm ls signal-polyfill
npm dedupe
```

## Core API

All exports come from `@lit-labs/signals`:

```ts
import {
  SignalWatcher,
  signal,
  computed,
  watch,
  html,        // auto-watching html tag
  withWatch,   // factory for composing the auto-watch behavior
} from '@lit-labs/signals';
```

### `signal<T>(initial: T)`

Creates a writable signal. Read via `.get()`, write via `.set()`.

```ts
const count = signal(0);

count.get();          // 0
count.set(count.get() + 1);
count.get();          // 1
```

### `computed(fn)`

Derived signal — re-runs `fn` when any signal it reads changes. Read via `.get()`.

```ts
const count = signal(0);
const doubled = computed(() => count.get() * 2);

doubled.get();        // 0
count.set(5);
doubled.get();        // 10
```

`computed` values are cached — repeated reads without source changes are free.

### `SignalWatcher(LitElement)` mixin

Apply to any element that reads signals. Without it, signal reads in `render()` (or any lifecycle hook) won't trigger updates when the signal changes.

```ts
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { SignalWatcher, signal } from '@lit-labs/signals';

const count = signal(0);

@customElement('signal-counter')
class SignalCounter extends SignalWatcher(LitElement) {
  render() {
    return html`
      <p>Count: ${count.get()}</p>
      <button @click=${() => count.set(count.get() + 1)}>+</button>
    `;
  }
}
```

The mixin tracks signal accesses across `shouldUpdate`, `willUpdate`, `update`, `render`, `firstUpdated`, and `updated`.

### `watch(signal)` directive

Pinpoint update — only the binding wrapped in `watch()` re-renders, not the whole component.

```ts
import { watch, signal } from '@lit-labs/signals';

const count = signal(0);

render() {
  return html`
    <p>Count: ${watch(count)}</p>
    <button @click=${() => count.set(count.get() + 1)}>+</button>
  `;
}
```

`watch()` works without the `SignalWatcher` mixin, but you'll usually want both — the mixin handles signal reads outside template bindings (computed properties, lifecycle hooks).

### Auto-watching `html` tag

Import `html` from `@lit-labs/signals` instead of `lit` and any signal interpolation is wrapped in `watch()` automatically. Use the signal directly — no `.get()`, no explicit `watch()`.

```ts
import { LitElement } from 'lit';
import { SignalWatcher, html, signal } from '@lit-labs/signals';

const count = signal(0);

class Counter extends SignalWatcher(LitElement) {
  render() {
    return html`
      <p>Count: ${count}</p>
      <button @click=${() => count.set(count.get() + 1)}>+</button>
    `;
  }
}
```

Caveat: `lit-analyzer` does not yet understand the signals `html` tag. Pick one style per file — mixing `count.get()` and bare `${count}` defeats the auto-watch optimization.

### `withWatch(htmlTag)`

Composes auto-watching with other tag wrappers (e.g., `withStatic` from `lit/static-html.js`):

```ts
import { html as coreHtml } from 'lit';
import { withStatic } from 'lit/static-html.js';
import { withWatch } from '@lit-labs/signals';

const html = withWatch(withStatic(coreHtml));
```

### `.effect(callback, options?)`

Instance method on `SignalWatcher` elements. Re-runs the callback whenever any signal it reads changes, coordinated with the element's update cycle.

```ts
class Telemetry extends SignalWatcher(LitElement) {
  connectedCallback() {
    super.connectedCallback();
    this.effect(() => {
      console.log('count is now', count.get());
    });
  }
}
```

Pass `{ beforeUpdate: true }` to run the effect *before* the next render rather than after:

```ts
this.effect(() => {
  this._derived = expensiveDerivation(count.get());
}, { beforeUpdate: true });
```

For per-component derivations, `willUpdate()` is usually simpler. Reach for `.effect()` when the side effect spans multiple signals or needs lifecycle coordination.

## Three Rendering Patterns

Same counter, three ways:

### 1. Mixin + `.get()` — full re-render
```ts
class Counter extends SignalWatcher(LitElement) {
  render() {
    return html`<p>${count.get()}</p>`;
  }
}
```
Whole component re-renders on every signal change. Simplest mental model.

### 2. `watch()` directive — pinpoint update
```ts
class Counter extends LitElement {
  render() {
    return html`<p>${watch(count)}</p>`;
  }
}
```
Only the text node updates. No full render cycle. No mixin required.

### 3. Auto-watching `html` tag — pinpoint, implicit
```ts
import { html } from '@lit-labs/signals';

class Counter extends LitElement {
  render() {
    return html`<p>${count}</p>`;
  }
}
```
Same behavior as `watch()` but cleaner syntax. Tradeoff: lit-analyzer support gap.

**Default:** start with the mixin + `.get()` for clarity. Reach for `watch()` or the auto-watching tag when you measure unnecessary re-renders.

## Combining with `@lit/context`

For deep-reactive state shared across the tree, provide a signal through context. Consumers read the signal directly — no `subscribe: true` re-firing on every change, because the signal handles its own observation.

```ts
// shared/cart.ts
import { signal } from '@lit-labs/signals';
import { createContext } from '@lit/context';

export interface CartItem { id: string; qty: number; }

export const cartSignal = signal<CartItem[]>([]);
export const cartContext = createContext<typeof cartSignal>(Symbol('cart'));
```

```ts
// app-root.ts — provides the signal once
@customElement('app-root')
class AppRoot extends LitElement {
  @provide({ context: cartContext })
  cart = cartSignal;

  render() { return html`<slot></slot>`; }
}
```

```ts
// cart-badge.ts — consumes and reads
@customElement('cart-badge')
class CartBadge extends SignalWatcher(LitElement) {
  @consume({ context: cartContext })
  cart!: typeof cartSignal;

  render() {
    return html`<span>${this.cart.get().length} items</span>`;
  }
}
```

Why this beats raw context: the context value is a stable signal reference, so context plumbing fires once at connection. Subsequent updates flow through the signal's own change tracking — finer-grained and cheaper than `subscribe: true`.

## Signal Collections

The companion package `signal-utils` (separate npm install) provides observable collections:

```ts
import { SignalArray } from 'signal-utils/array';
import { SignalMap } from 'signal-utils/map';

const items = new SignalArray<string>(['a', 'b']);
items.push('c');  // notifies watchers
```

Reach for these when you need a signal-aware list/map/set without manual `signal.set([...signal.get(), x])` ceremony. Decorator helpers for class fields are also available.

## When to Reach for Signals

| Need | Use | Why |
|------|-----|-----|
| State scoped to one component | `@property` / `@state` | No extra dependency, integrates with attributes |
| Cross-tree value, rarely changes | `@lit/context` (no `subscribe`) | Lightweight one-time delivery |
| Cross-tree value, changes frequently | `@lit/context` + signal | Fine-grained updates without subscribe re-fire |
| Free-standing module-scope state | Bare signal + `SignalWatcher` | No context needed; any element can read |
| Derived value from one component | `willUpdate()` | Lifecycle-integrated, no extra primitive |
| Derived value from multiple signals | `computed()` | Auto-tracks dependencies, cached |

## Common Pitfalls

### Signal change doesn't update the DOM
**Cause:** Forgot the `SignalWatcher` mixin. Signal reads in `render()` are tracked, but the element only knows to re-render if it's wrapped.
**Fix:** `class MyEl extends SignalWatcher(LitElement)`. Or use `watch(signal)` in the template, which works without the mixin.

### Updates from one signal don't reach watchers of another
**Cause:** Multiple copies of `signal-polyfill` installed. Signals created against one polyfill are invisible to watchers from another.
**Fix:** `npm ls signal-polyfill` — if you see duplicates, run `npm dedupe` or pin a single version.

### `repeat()` doesn't re-run when a signal-collection mutates
**Cause:** No signal-aware `repeat()` directive yet. The directive doesn't subscribe to the collection's change notifications.
**Fix:** Use `signal-utils` collections and wrap the list in `watch()`, or compute a fresh array in a `computed()` and pass that to `repeat()`.

### Auto-watching `html` tag is mixed with `.get()`
**Cause:** Importing `html` from `@lit-labs/signals` but still calling `signal.get()` in interpolations.
**Fix:** Pick one style per file. With the auto-watching tag, pass the signal directly: `${mySignal}`, not `${mySignal.get()}`.

### Signals used for component-local state
**Cause:** Reaching for signals when `@state` would do.
**Fix:** Default to `@state` for state owned by one component. Signals earn their keep when state crosses component boundaries or needs fine-grained updates.

### Effect callback never re-runs
**Cause:** Calling `.effect()` outside a `SignalWatcher` element, or never reading a signal inside the callback.
**Fix:** `.effect()` is an instance method — only available on `SignalWatcher(LitElement)` subclasses. The callback must read at least one signal for the dependency tracker to wire up.

## Best Practices

- **Default to `@state`/`@property`** for component-local state — only reach for signals when the value crosses components or needs fine-grained reactivity.
- **Apply `SignalWatcher` once per element** that reads signals in lifecycle hooks; templates can use `watch()` without the mixin.
- **Pick one `html` style per file** — either core `lit` `html` + explicit `watch()`, or `@lit-labs/signals` `html` with bare interpolations. Don't mix.
- **Use `computed()` for derived values from multiple signals** — cached and dependency-tracked. Use `willUpdate()` for derivations from a single component's properties.
- **Wrap a signal in context for shared deep-reactive state** — beats `subscribe: true` for frequently-changing values.
- **Run `npm dedupe`** if signal updates seem inconsistent — polyfill duplication is a silent failure mode.
- **Flag Labs status to users** when recommending this package — API breaks are possible until it graduates.
