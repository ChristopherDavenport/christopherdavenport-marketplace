# Eval report: `lit`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **9**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.35** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 6/9 | 5 / 1 / 3 | 100% → 100% (+0%) |
| `haiku` | 8/9 | 7 / 1 / 1 | 92% → 96% (+4%) |
| `opus` ¹ | 6/9 | 5 / 1 / 3 | 92% → 96% (+4%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 7 | 4/7 | 7/7 | 5/7 |
| `skill_wins_strict` | 1 | 1/1 | 0/1 | 0/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `array-mutation-no-rerender` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `typed-event-cross-shadow` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `lifecycle-which-callback` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `state-vs-property` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `custom-directive-vs-helper` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `reactive-controller-vs-task` | skill_wins | ✗ ✗ baseline | ✓ ✓ skill | ✓ ✓ skill |
| `context-subscribe-true` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ ✗ baseline |
| `simplest-render-html` | skill_wins_strict | ✓ ✓ skill | ✗ ✗ baseline | ✗ = tie |
| `offtopic-sql-join` | tie | ✓ = tie | ✓ = tie | ✓ = tie |

## Per-case detail

### `array-mutation-no-rerender`

**Prompt**

```
I have a Lit component with a property `@property({type: Array}) items = []`.
When I push a new item with `this.items.push(newItem)`, the
component doesn't re-render. What am I doing wrong?
```

**Judge focus:** The better answer explains Lit uses reference equality (!==) for
change detection, recommends creating a new array
(`this.items = [...this.items, newItem]`), and may mention
`requestUpdate` as an alternative escape hatch.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the three rubric criteria well, but Answer A provides a more thorough and accurate explanation of reference equality, correctly notes that requestUpdate requires passing the property name explicitly (which is an important technical detail), and covers a broader range of immutable update patterns. Answer B adds a useful hasChanged approach not in the rubric, but its requestUpdate call omits the old value argument which may matter in some cases, and the table adds clarity. Overall Answer A is more technically precise and comprehensive.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains reference equality / strict equality | skill |
| recommends creating a new array | tie |
| mentions requestUpdate as escape hatch | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `!==` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `reference equal` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

<details><summary>sonnet: baseline answer</summary>

## The Problem

Lit uses **shallow equality checks** to detect property changes. When you `push()` to an array, the **reference stays the same**, so Lit sees no change and skips re-rendering.

```javascript
// ❌ Lit sees the same array reference - no re-render
this.items.push(newItem);
```

---

## Solutions

### 1. Create a New Array (Recommended)

```javascript
// ✅ New reference = Lit detects the change
this.items = [...this.items, newItem];

// Also works for other mutations:
this.items = this.items.filter(item => item.id !== id);  // remove
this.items = this.items.map(item => ({ ...item, updated: true })); // update
```

### 2. Mutate, Then Notify Manually

If you **must** mutate in place, use `requestUpdate()`:

```javascript
this.items.push(newItem);
this.requestUpdate('items'); // tell Lit the property changed
```

### 3. Use a Custom Property Hasher

Tell Lit to do a deep check instead of a reference check:

```javascript
import { deepEqual } from 'some-deep-equal-lib';

@property({
  type: Array,
  hasChanged: (newVal, oldVal) => !deepEqual(newVal, oldVal)
})
items = [];
```

> ⚠️ This can hurt performance on large arrays since it compares every element.

---

## Best Practice

| Approach | Re-renders | Mutates Original | Performance |
|---|---|---|---|
| Spread `[...arr]` | ✅ | ❌ | ✅ Good |
| `requestUpdate()` | ✅ | ✅ | ✅ Good |
| `hasChanged` deep check | ✅ | ✅ | ⚠️ Costly |

**The spread approach is the most idiomatic** — it's immutable, predictable, and works cleanly with Lit's reactive system.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Lit uses **reference equality** (`!==`) to detect changes. When you call `this.items.push(newItem)`, the array reference stays the same, so Lit sees no change and skips the re-render.

## The Fix: Always Replace the Reference

Instead of mutating the array, create a new one:

```typescript
// ❌ Mutates in place — Lit sees no change
this.items.push(newItem);

// ✅ New reference — Lit schedules a re-render
this.items = [...this.items, newItem];
```

The same rule applies to all common array operations:

```typescript
// ❌ Mutations Lit won't detect
this.items.push(newItem);
this.items.pop();
this.items.splice(index, 1);
this.items[0] = newItem;

// ✅ Immutable equivalents
this.items = [...this.items, newItem];           // push
this.items = this.items.slice(0, -1);            // pop
this.items = this.items.filter((_, i) => i !== index); // splice/remove
this.items = this.items.map((item, i) =>         // update by index
  i === 0 ? newItem : item
);
```

The same applies to **objects** — spread to replace, don't mutate:

```typescript
// ❌ Lit won't detect this
this.user.name = 'Alice';

// ✅ New reference
this.user = { ...this.user, name: 'Alice' };
```

## Escape Hatch: `requestUpdate()`

If you genuinely need to mutate in place (e.g., working with a third-party API that hands you a mutable object), you can manually notify Lit:

```typescript
this.items.push(newItem);
this.requestUpdate('items', this.items); // force re-render
```

This works, but it's fragile — Lit's `hasChanged` check will still see identical references, so you must pass the property name explicitly. Prefer immutable updates.

## Rendering the List

Pair your immutable updates with the `repeat()` directive for efficient DOM reuse when items reorder:

```typescript
import { repeat } from 'lit/directives/repeat.js';

render() {
  return html`
    <ul>
      ${repeat(
        this.items,
        (item) => item.id,          // stable key — minimises DOM churn
        (item) => html`<li>${item.name}</li>`
      )}
    </ul>
    <button @click=${this._addItem}>Add</button>
  `;
}

private _addItem() {
  this.items = [...this.items, { id: crypto.randomUUID(), name: 'New' }];
}
```

Use a plain `map()` instead of `repeat()` when the list is short and items don't reorder — `repeat()` pays off when you need to preserve DOM state (focus, animations) across reorders.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more accurate and idiomatic. It correctly explains reference equality using `!==` notation, provides a clear immutable assignment recommendation, and properly frames `requestUpdate()` as an escape hatch to avoid rather than a primary solution. Answer A contains a misleading section about 'reactive controllers/signals' that doesn't accurately represent Lit's API and could confuse readers.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains reference equality / strict equality | skill |
| recommends creating a new array | tie |
| mentions requestUpdate as escape hatch | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `same array reference` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `!==` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

<details><summary>haiku: baseline answer</summary>

# Lit Array Mutation Issue

The problem is that **Lit doesn't detect mutations to arrays** — it only detects when the array reference itself changes. When you `push()` to an array, you're mutating it in place, so Lit doesn't know to re-render.

## Solutions

### 1. **Reassign the array (Recommended)**
Create a new array reference:

```javascript
this.items = [...this.items, newItem];
// or
this.items = this.items.concat(newItem);
```

### 2. **Use `requestUpdate()`**
Manually trigger a re-render:

```javascript
this.items.push(newItem);
this.requestUpdate();
```

### 3. **Use a reactive controller or signal** (Modern approach)
For more complex state management:

```javascript
import { reactive } from '@lit/reactive-element';

items = reactive([]);

addItem(newItem) {
  this.items.push(newItem);
  // Reactive automatically detects changes
}
```

## Why This Happens

Lit uses **shallow equality checks** by default. It compares the old and new property values:

```javascript
oldValue === newValue  // true for mutations!
```

Since `push()` returns the same array reference, Lit thinks nothing changed.

## Best Practice

Always reassign arrays/objects when updating them:

```javascript
// ✅ Good
this.items = [...this.items, newItem];
this.data = { ...this.data, key: value };

// ❌ Bad
this.items.push(newItem);
this.data.key = value;
```

This is a common pattern in reactive frameworks (React, Vue, etc.) and makes change detection predictable.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Array Mutation Issue in Lit

You've hit Lit's **reference-equality change detection**. When you call `this.items.push(newItem)`, you're mutating the array in place — the reference stays the same (`===`), so Lit doesn't detect a change and doesn't trigger an update.

## The Fix

Replace the mutation with an **immutable assignment**:

```ts
// ❌ Wrong — mutates in place, no re-render
this.items.push(newItem);

// ✅ Correct — new reference, triggers update
this.items = [...this.items, newItem];
```

## Why This Happens

Lit uses `!==` (reference inequality) to detect property changes, not deep equality. This is intentional — it's fast and predictable. When you mutate an array or object in place, the reference doesn't change:

```ts
const arr = [1, 2, 3];
arr.push(4);
arr === arr;  // true — same reference, Lit sees no change
```

## Common Patterns

**Adding an item:**
```ts
this.items = [...this.items, newItem];
```

**Removing an item:**
```ts
this.items = this.items.filter(item => item.id !== idToRemove);
```

**Updating an item:**
```ts
this.items = this.items.map(item =>
  item.id === idToUpdate ? { ...item, ...updates } : item
);
```

**Clearing the array:**
```ts
this.items = [];
```

## If You Must Mutate

If you absolutely need to mutate (e.g., for performance with very large arrays), call `requestUpdate()` after the mutation to force a re-render:

```ts
this.items.push(newItem);
this.requestUpdate();  // Force update
```

However, **avoid this pattern** — immutable updates are clearer and play better with Lit's reactivity model.

## See Also

- [Reactive Properties](references/reactive-properties.md) — full mutation rules and change detection details
- [Code Examples](references/code-examples.md) — list rendering patterns with `repeat()`

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover all three rubric criteria well, but Answer A provides more comprehensive examples of immutable updates for various mutation patterns (splice, index assignment, object updates), making it more practically useful. Answer B adds a bonus `hasChanged` tip that's helpful but slightly off-focus, while Answer A's broader mutation examples and clearer TL;DR make it marginally more complete and idiomatic. The `requestUpdate` coverage is roughly equivalent, though B's mention of passing the old value for lifecycle hooks is a nice touch.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains reference equality / strict equality | tie |
| recommends creating a new array | skill |
| mentions requestUpdate as escape hatch | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✗ | |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `reference equal` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

<details><summary>opus: baseline answer</summary>

# The Problem

Lit's reactivity system detects property changes by **reference comparison** (similar to `===`). When you call `this.items.push(newItem)`, you're mutating the existing array — the reference stays the same, so Lit doesn't know anything changed and won't trigger a re-render.

# The Fix

Replace the array with a new one instead of mutating it:

```js
// ❌ Doesn't trigger re-render
this.items.push(newItem);

// ✅ Triggers re-render
this.items = [...this.items, newItem];
```

The same applies to other mutating methods (`pop`, `splice`, `sort`, `unshift`, etc.) and to objects (`this.obj.foo = 'bar'` won't trigger updates either).

# Alternatives

**1. Manually request an update** if you really need to mutate (e.g., for performance with very large arrays):

```js
this.items.push(newItem);
this.requestUpdate();
```

You can also pass the old value so `updated()` lifecycle hooks work properly:

```js
this.requestUpdate('items', this.items);
```

**2. Use a custom `hasChanged` function** if you want Lit to compare differently:

```js
@property({
  type: Array,
  hasChanged: () => true, // always consider changed
})
items = [];
```

# Recommended Approach

Stick with immutable updates (`[...this.items, newItem]`). It plays nicely with Lit's change detection, makes your code easier to reason about, and works well if you later integrate state management libraries.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Why your component isn't re-rendering

This is the **#1 most common Lit gotcha**. Lit's change detection uses **strict reference equality (`!==`)** to decide whether to re-render. When you call `this.items.push(newItem)`, you're mutating the *same array* — the reference doesn't change, so Lit thinks nothing happened.

## The fix: create a new array reference

```ts
// ❌ Mutates in place — no re-render
this.items.push(newItem);

// ✅ New array reference — triggers re-render
this.items = [...this.items, newItem];
```

The same rule applies to all array/object mutations:

```ts
// ❌ All of these mutate in place
this.items.push(item);
this.items.splice(0, 1);
this.items[0] = newValue;
this.user.name = 'Alice';

// ✅ Create new references instead
this.items = [...this.items, item];                    // append
this.items = this.items.filter((_, i) => i !== 0);     // remove
this.items = this.items.map((v, i) => i === 0 ? newValue : v);  // update
this.user = { ...this.user, name: 'Alice' };           // object update
```

## Why Lit works this way

Lit checks `oldValue !== newValue` in the property setter. This is fast (one comparison) and predictable. Deep equality checking would be expensive and ambiguous. Immutable updates also play nicely with `repeat()` directives, signals, and any future tooling that relies on reference identity.

## Escape hatch (rarely needed)

If you absolutely must mutate in place — say, for a huge array where copying is a real perf problem — manually request an update:

```ts
this.items.push(newItem);
this.requestUpdate('items');  // tell Lit to re-render
```

But prefer immutable updates as the default. They're easier to reason about and they're what every other part of the Lit ecosystem expects.

## TL;DR

> **Never mutate `@property` or `@state` values in place.** Always assign a new reference. If you can't, call `this.requestUpdate(propName)` manually.

</details>

---

### `typed-event-cross-shadow`

**Prompt**

```
I'm dispatching a CustomEvent from inside my Lit component, but
the parent component listening for it isn't receiving the event.
The parent is just outside the host element. What's wrong?
```

**Judge focus:** The better answer pinpoints `composed: true` (and bubbles: true) as
required to cross Shadow DOM boundaries. Bonus for mentioning typed
Event subclasses with static readonly type.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify composed:true and bubbles:true as required to cross Shadow DOM boundaries, but Answer B goes further by including the bonus content about typed Event subclasses with static readonly type, HTMLElementEventMap declarations, and a practical checklist of additional failure modes. Answer B is more comprehensive and production-ready while still being clear and accurate on the core issue.

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
| mentions Shadow DOM boundary | ✓ | `Shadow DOM boundary` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies composed:true is required | ✓ | `composed: true` |
| mentions bubbles:true | ✓ | `bubbles: true` |
| mentions Shadow DOM boundary | ✓ | `Shadow DOM boundary` |

<details><summary>sonnet: baseline answer</summary>

## The Problem: Custom Events and `composed`

By default, Custom Events **do not cross the Shadow DOM boundary**. They stop at the shadow root and never reach the parent component listening in the light DOM.

---

## The Fix

You need to set **both** `bubbles: true` and `composed: true` when dispatching the event:

```javascript
// ❌ Wrong - event is trapped inside the shadow root
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { message: 'hello' },
  bubbles: true,        // bubbles up through shadow DOM nodes only
  // composed is false by default!
}));

// ✅ Correct - event crosses the shadow DOM boundary
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { message: 'hello' },
  bubbles: true,   // allows the event to bubble up
  composed: true,  // allows the event to cross shadow DOM boundaries
}));
```

---

## What Each Option Does

| Option | Description |
|---|---|
| `bubbles: false` | Event stays on the dispatching element only |
| `bubbles: true` | Event bubbles up through the DOM tree |
| `composed: false` | Event is **stopped** at the shadow root (default) |
| `composed: true` | Event **crosses** shadow DOM boundaries into the light DOM |

You need **both** together to reach a parent outside the host element.

---

## Full Lit Example

```javascript
import { LitElement, html } from 'lit';

// Child component
class MyChild extends LitElement {
  _handleClick() {
    this.dispatchEvent(new CustomEvent('child-clicked', {
      detail: { value: 42 },
      bubbles: true,
      composed: true, // 👈 this is the key
    }));
  }

  render() {
    return html`<button @click=${this._handleClick}>Click me</button>`;
  }
}
customElements.define('my-child', MyChild);


// Parent component
class MyParent extends LitElement {
  render() {
    return html`
      <my-child @child-clicked=${this._onChildClicked}></my-child>
    `;
  }

  _onChildClicked(e) {
    console.log('Received event with value:', e.detail.value); // ✅ works
  }
}
customElements.define('my-parent', MyParent);
```

---

## A Note on `composed` Without `bubbles`

```javascript
// ⚠️ composed: true alone - crosses boundary but only visible
// on the host element itself, doesn't bubble further up
this.dispatchEvent(new CustomEvent('my-event', {
  composed: true,
  bubbles: false,
}));
```

In most cases you want **both flags set to `true`** to ensure the event bubbles up through the full DOM tree across shadow boundaries.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The most common cause is that the event isn't configured to cross the Shadow DOM boundary. Here's what's happening and how to fix it.

## Why Events Get Trapped

Shadow DOM creates an encapsulation boundary. A `CustomEvent` with default options stops at the shadow root — it never reaches the light DOM where your parent is listening.

Two options control this:

| Option | Default | What it does |
|--------|---------|--------------|
| `bubbles` | `false` | Event travels up the DOM tree |
| `composed` | `false` | Event crosses shadow root boundaries |

**Both must be `true`** for an event dispatched inside a shadow root to reach a parent in the light DOM.

## The Fix

```ts
// ❌ Trapped inside the shadow root
this.dispatchEvent(new CustomEvent('value-changed', {
  detail: { value: this.value },
}));

// ✅ Escapes the shadow root and bubbles up
this.dispatchEvent(new CustomEvent('value-changed', {
  detail: { value: this.value },
  bubbles: true,
  composed: true,
}));
```

## The Better Pattern: Typed Event Classes

Raw `CustomEvent` strings are error-prone. A typed event class gives you autocomplete, compile-time safety, and a single place to set `bubbles`/`composed` correctly — so you can't forget them.

**`events/value-changed-event.ts`**
```ts
export class ValueChangedEvent extends Event {
  static readonly type = 'value-changed';

  constructor(public readonly value: string) {
    super(ValueChangedEvent.type, {
      bubbles: true,   // travels up the DOM tree
      composed: true,  // crosses shadow root boundaries
    });
  }
}

// Teach TypeScript about the event on the element's interface
declare global {
  interface HTMLElementEventMap {
    'value-changed': ValueChangedEvent;
  }
}
```

**Inside your component:**
```ts
import { ValueChangedEvent } from './events/value-changed-event.js';

// Dispatch after the DOM has updated so listeners see current state
await this.updateComplete;
this.dispatchEvent(new ValueChangedEvent(this.value));
```

**In the parent (Lit template):**
```ts
// Fully typed — `e.value` is `string`, not `unknown`
html`<my-input @value-changed=${(e: ValueChangedEvent) => {
  console.log(e.value);
}}></my-input>`
```

**In the parent (vanilla JS/HTML):**
```ts
document.querySelector('my-input')
  .addEventListener('value-changed', (e: ValueChangedEvent) => {
    console.log(e.value); // typed, not e.detail.value
  });
```

## Checklist

If it's still not working after adding `bubbles: true, composed: true`, check these:

1. **`stopPropagation()` called somewhere upstream** — any ancestor calling this will swallow the event before it reaches the parent.

2. **Listener is on the wrong element** — the parent must listen on the host element (`<my-component>`) or an ancestor, not inside its own shadow root.

3. **Event dispatched before the element is connected** — events dispatched in the constructor won't bubble anywhere useful. Use `firstUpdated()` or a user interaction handler instead.

4. **`composed: false` on a built-in event** — some native events (like `change` on an `<input>` inside a shadow root) are not composed by default. Re-dispatch them as a new composed event if you need them to escape.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify composed:true and bubbles:true as required to cross Shadow DOM boundaries. Answer A goes further by providing the bonus content of typed Event subclasses with static readonly type, HTMLElementEventMap augmentation, and a complete type-safe pattern, making it more comprehensive and idiomatic for TypeScript/Lit development.

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
| mentions Shadow DOM boundary | ✓ | `Shadow DOM boundary` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies composed:true is required | ✓ | `composed: true` |
| mentions bubbles:true | ✓ | `bubbles: true` |
| mentions Shadow DOM boundary | ✓ | `Shadow DOM Boundary` |

<details><summary>haiku: baseline answer</summary>

# CustomEvent Not Reaching Parent in Lit

The issue is likely that your CustomEvent is **not crossing the Shadow DOM boundary**. By default, events created in Shadow DOM don't bubble out to the light DOM.

## Solution: Set `composed: true`

When dispatching the event, add the `composed` option:

```javascript
// ❌ Won't reach parent (stops at Shadow DOM boundary)
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { message: 'hello' }
}));

// ✅ Will reach parent (crosses Shadow DOM boundary)
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { message: 'hello' },
  composed: true,  // <-- Add this
  bubbles: true    // <-- Also add this for safety
}));
```

## Complete Example

**Child Component (Lit):**
```javascript
import { LitElement, html } from 'lit';

export class MyChild extends LitElement {
  render() {
    return html`<button @click=${this.handleClick}>Click me</button>`;
  }

  handleClick() {
    this.dispatchEvent(new CustomEvent('child-event', {
      detail: { message: 'Event from child' },
      composed: true,
      bubbles: true
    }));
  }
}
```

**Parent Component:**
```javascript
export class MyParent extends LitElement {
  render() {
    return html`
      <my-child @child-event=${this.handleChildEvent}></my-child>
    `;
  }

  handleChildEvent(event) {
    console.log(event.detail.message); // Works! ✅
  }
}
```

## Key Options Explained

| Option | Purpose |
|--------|---------|
| `composed: true` | **Required** - allows event to cross Shadow DOM boundary |
| `bubbles: true` | Allows event to bubble up through parent elements |
| `detail` | Passes data with the event |

Without `composed: true`, the event stops at the Shadow DOM boundary and never reaches the parent.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Custom Event Not Crossing Shadow DOM Boundary

The issue is that your event isn't configured to bubble through the Shadow DOM. By default, events created with `new CustomEvent()` have `bubbles: false` and `composed: false`, which means they stop at the Shadow DOM boundary.

## The Fix

When you create and dispatch the event, set both `bubbles: true` and `composed: true`:

```typescript
// ❌ Wrong — stops at Shadow DOM boundary
this.dispatchEvent(new CustomEvent('my-event'));

// ✅ Correct — crosses Shadow DOM
this.dispatchEvent(
  new CustomEvent('my-event', {
    bubbles: true,
    composed: true,
  })
);
```

## Best Practice: Typed Event Class

Define a concrete event class in your component module so consumers can import it for type-safe listening:

```typescript
// my-component.ts
export class MyEventDetail {
  constructor(public value: string) {}
}

export class MyEvent extends Event {
  static readonly type = 'my-event';

  constructor(public detail: MyEventDetail) {
    super(MyEvent.type, {
      bubbles: true,
      composed: true,
    });
  }
}

@customElement('my-component')
export class MyComponent extends LitElement {
  private _handleClick() {
    this.dispatchEvent(new MyEvent(new MyEventDetail('hello')));
  }

  render() {
    return html`<button @click=${this._handleClick}>Click me</button>`;
  }
}

declare global {
  interface HTMLElementEventMap {
    'my-event': MyEvent;
  }
}
```

## Parent Listening (Type-Safe)

```typescript
// parent-component.ts
import { MyEvent } from './my-component.js';

@customElement('parent-component')
export class ParentComponent extends LitElement {
  render() {
    return html`
      <my-component @my-event=${this._onMyEvent}></my-component>
    `;
  }

  private _onMyEvent(event: MyEvent) {
    console.log('Received:', event.detail.value); // "hello"
  }
}
```

## Key Points

- **`bubbles: true`** — event propagates up the DOM tree
- **`composed: true`** — event crosses the Shadow DOM boundary (critical!)
- **`static readonly type`** — standardizes the event name and enables `HTMLElementEventMap` typing
- **Dispatch after `await this.updateComplete`** — listeners see the fully rendered state

See [reactive-properties.md](references/reactive-properties.md) for the full typed event pattern and more examples.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify composed:true and bubbles:true as required to cross Shadow DOM boundaries, but Answer B goes further by including the bonus criterion of typed Event subclasses with a static readonly type property, which is explicitly mentioned in the focus area. Answer B also provides a practical checklist and dispatch timing advice, making it more comprehensive and useful overall.

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
| mentions Shadow DOM boundary | ✓ | `Shadow DOM` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies composed:true is required | ✓ | `composed: true` |
| mentions bubbles:true | ✓ | `bubbles: true` |
| mentions Shadow DOM boundary | ✓ | `Shadow DOM boundary` |

<details><summary>opus: baseline answer</summary>

# The Issue: CustomEvents Don't Bubble Through Shadow DOM by Default

By default, `CustomEvent` instances have two properties that prevent them from reaching listeners outside your Lit component's shadow DOM:

1. **`bubbles: false`** – the event won't bubble up the DOM tree
2. **`composed: false`** – the event won't cross the shadow DOM boundary

Even if you set `bubbles: true`, the event will bubble *within* the shadow root but stop at the shadow boundary. To escape the shadow DOM, you need **both** `bubbles` and `composed` set to `true`.

## The Fix

```js
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { someData: 123 },
  bubbles: true,
  composed: true,
}));
```

## Quick Reference

| `bubbles` | `composed` | Behavior |
|-----------|------------|----------|
| `false` | `false` | Only listeners on the dispatching element fire |
| `true` | `false` | Bubbles inside shadow root, stops at boundary |
| `false` | `true` | No bubbling, but can be caught at exact retarget point |
| `true` | `true` | ✅ Bubbles all the way up through shadow DOM |

## A Couple of Caveats

- **Event retargeting**: When the event crosses the shadow boundary, `event.target` will be retargeted to your host element (the custom element itself), not the inner element that dispatched it. If you need the original target, use `event.composedPath()[0]`.
- **Naming**: Prefer kebab-case event names (e.g., `'item-selected'`), and avoid names that collide with native DOM events.
- **Lit convention**: Some teams reserve `composed: true` only for events that are genuinely meant to be public API of the component, since composed events can leak implementation details.

If it still doesn't work after this change, double-check that the parent's listener is attached to an ancestor of the host element (or the host itself), and that it's listening for the exact same event name.

</details>

<details><summary>opus: skill-loaded answer</summary>

Short answer: your event almost certainly isn't crossing the Shadow DOM boundary. Events fired from inside a shadow root **do not** bubble out to ancestors unless you set `composed: true`. And to bubble at all, you also need `bubbles: true`.

## The fix

```ts
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { value: 42 },
  bubbles: true,
  composed: true,
}));
```

Both flags are required:
- `bubbles: true` — lets the event bubble up the DOM
- `composed: true` — lets it cross Shadow DOM boundaries

Without `composed`, the parent (which lives outside your component's shadow root) will never see it.

## Recommended pattern: typed event class

Rather than ad-hoc `CustomEvent`s, define a concrete event class. This gives you type-safe `detail`, a stable event name, and consumers can import it for typed listeners:

```ts
export class ValueChangeEvent extends Event {
  static readonly type = 'value-change' as const;
  constructor(public readonly value: number) {
    super(ValueChangeEvent.type, { bubbles: true, composed: true });
  }
}

// In your component:
this.dispatchEvent(new ValueChangeEvent(42));
```

## One more gotcha: dispatch timing

If the listener inspects DOM state when handling the event, dispatch *after* the update has flushed, otherwise the parent may read stale DOM:

```ts
this.value = 42;
await this.updateComplete;
this.dispatchEvent(new ValueChangeEvent(this.value));
```

## Quick checklist

1. ✅ `bubbles: true`
2. ✅ `composed: true`
3. ✅ Listener attached to an actual ancestor (not a sibling)
4. ✅ Event name matches exactly (case-sensitive, no typos)
5. ✅ Dispatched *after* `await this.updateComplete` if the handler reads DOM

99% of the time, adding `composed: true` solves it. If it still doesn't work after that, double-check that the listener is on an ancestor element and the event name matches.

</details>

---

### `lifecycle-which-callback`

**Prompt**

```
In a Lit component, where should I put each kind of work:
(a) compute a derived property from this.someInput before render,
(b) one-time DOM measurement of a child element after first render,
(c) calling an external API after every render that changed an input.
Which lifecycle method for each, and why?
```

**Judge focus:** The better answer maps the three tasks to willUpdate, firstUpdated,
and updated, and explains the ordering and "changed properties"
parameter where relevant.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly map all three tasks to willUpdate, firstUpdated, and updated, explain the ordering, and use the changedProperties parameter with guards. Answer A is slightly more concise and includes a helpful summary table, while Answer B provides more detailed TypeScript examples, a lifecycle flow diagram, and comparison tables for alternatives. Both are equally strong on all rubric criteria.

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

<details><summary>sonnet: baseline answer</summary>

# Lit Component Lifecycle Placement

## (a) Derived Property from `this.someInput` Before Render

**→ `willUpdate(changedProperties)`**

```javascript
willUpdate(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.derivedValue = expensiveComputation(this.someInput);
  }
}
```

**Why:**
- Runs **before** `render()`, so the derived value is ready when the template is evaluated
- Guaranteed to run on both client and server (SSR-safe)
- `update()` would also work but `willUpdate` is the semantic fit — it exists specifically for pre-render derivation
- Do **not** use `updated()` — that runs after render, causing a wasted paint with stale data
- Do **not** set reactive properties here (use plain class fields) — setting a reactive property would trigger another update cycle

---

## (b) One-Time DOM Measurement After First Render

**→ `firstUpdated(changedProperties)`**

```javascript
firstUpdated() {
  const rect = this.shadowRoot
    .querySelector('.target')
    .getBoundingClientRect();
  this.initialHeight = rect.height;
}
```

**Why:**
- Runs **once**, after the component's first `update()` completes and the DOM is committed
- The element is guaranteed to be in the DOM and measurable at this point
- `connectedCallback` is too early — shadow DOM children may not be rendered yet
- `updated()` would re-run on every change — wasteful and potentially incorrect for a "snapshot" measurement
- If you need to wait for layout/paint (e.g., for accurate `getBoundingClientRect`), wrap in `await this.updateComplete` or `requestAnimationFrame`

```javascript
async firstUpdated() {
  await this.updateComplete; // ensure children are also settled
  const rect = this.shadowRoot.querySelector('.target').getBoundingClientRect();
}
```

---

## (c) Call External API After Every Render That Changed an Input

**→ `updated(changedProperties)`**

```javascript
updated(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.fetchData(this.someInput).then(result => {
      this.result = result; // reactive property triggers re-render
    });
  }
}
```

**Why:**
- Runs **after** every update, with access to both current and previous values via `changedProperties`
- The `changedProperties.has('someInput')` guard is **critical** — without it you get infinite loops (setting `this.result` triggers `updated` again)
- Runs after DOM is committed, so any DOM side effects from the API response are safe
- Do **not** use `willUpdate` — the DOM isn't ready and you'd be calling the API before the render it corresponds to
- Consider cancelling in-flight requests (AbortController) to handle rapid input changes

---

## Summary Table

| Task | Method | Timing | Key Reason |
|---|---|---|---|
| Derive from input | `willUpdate` | Before render | Value ready when template runs |
| One-time DOM measure | `firstUpdated` | After first render | DOM exists, runs only once |
| API call on input change | `updated` | After every render | Post-DOM, guarded by `changedProperties` |

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Lifecycle Placement for Each Kind of Work

### (a) Derived property — `willUpdate()`

```typescript
@customElement('my-component')
export class MyComponent extends LitElement {
  @property({ type: Number }) price = 0;
  @property({ type: Number }) quantity = 0;

  // Derived state: plain fields, not @state() — no extra update cycle
  protected total = 0;
  protected formattedTotal = '';

  protected willUpdate(changed: PropertyValues<this>): void {
    // Runs before render(), so derived values are ready when render() reads them.
    // Only recompute when the inputs actually changed — important for expensive derivations.
    if (changed.has('price') || changed.has('quantity')) {
      this.total = this.price * this.quantity;
      this.formattedTotal = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
      }).format(this.total);
    }
  }

  render() {
    // Reads already-computed values — render() stays pure
    return html`<p>Total: ${this.formattedTotal}</p>`;
  }
}
```

**Why `willUpdate()` and not somewhere else:**

| Alternative | Problem |
|-------------|---------|
| Inside `render()` | Makes render impure — side effects in render break the contract and make testing harder |
| `@state()` field set in `updated()` | Triggers a *second* update cycle — wasteful and can cause loops |
| `updated()` | Runs *after* render, so the first paint shows stale derived values |

`willUpdate()` is the one place guaranteed to run before render, after new property values are set, with access to `changedProperties` for conditional recomputation.

---

### (b) One-time DOM measurement — `firstUpdated()`

```typescript
@customElement('my-component')
export class MyComponent extends LitElement {
  @query('canvas') private _canvas!: HTMLCanvasElement;

  private _chart: Chart | null = null;

  protected firstUpdated(): void {
    // Shadow DOM is fully rendered exactly once here.
    // Safe to measure, query, or hand off to a third-party library.
    const { width, height } = this._canvas.getBoundingClientRect();

    this._chart = new Chart(this._canvas, {
      initialWidth: width,
      initialHeight: height,
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._chart?.destroy(); // Clean up what firstUpdated() set up
  }
}
```

**Why `firstUpdated()` and not somewhere else:**

| Alternative | Problem |
|-------------|---------|
| `constructor()` | Shadow DOM doesn't exist yet — `querySelector` returns null, `getBoundingClientRect()` returns zeros |
| `connectedCallback()` | Runs before the first render — same problem as constructor for DOM queries |
| `updated()` | Works, but fires on *every* update — you'd need a manual `_initialized` flag to guard it, which is exactly what `firstUpdated()` already does for you |

---

### (c) External API call after every relevant render — `updated()`

```typescript
@customElement('my-component')
export class MyComponent extends LitElement {
  @property() userId = '';

  protected updated(changed: PropertyValues<this>): void {
    // Guard on the specific property — don't call the API for unrelated updates
    if (changed.has('userId') && this.userId) {
      this._syncToAnalytics(this.userId);
    }
  }

  private _syncToAnalytics(id: string): void {
    // DOM reflects the latest state here, so the external system
    // sees what the user actually sees
    externalAnalytics.track('user-viewed', { id });
  }
}
```

**Why `updated()` and not somewhere else:**

| Alternative | Problem |
|-------------|---------|
| `willUpdate()` | DOM hasn't updated yet — the external system would see stale rendered state |
| `render()` | Impure; may run more than once per logical update in some scenarios |
| Inline in a property setter | Fires before Lit's update cycle, so DOM is still stale; also bypasses `changedProperties` batching |

The `changed.has('userId')` guard is load-bearing — without it, every unrelated state change (a CSS class toggle, an internal `@state()` flip) would fire the API call.

---

### Summary

```
Property values set
        ↓
  willUpdate()   ← (a) derive computed state from new inputs
        ↓
    render()     ← pure: read properties and derived fields, return template
        ↓
   DOM updated
        ↓
firstUpdated()   ← (b) one-time: measure, initialize third-party libs  [first render only]
    updated()    ← (c) every relevant render: sync external systems, measure post-render DOM
```

The common thread: **read `changedProperties` in both `willUpdate()` and `updated()`** to avoid doing work when the relevant inputs haven't changed. Unconditional work in `updated()` is a frequent source of unnecessary API calls and infinite update loops.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly map the three tasks to willUpdate, firstUpdated, and updated, and both mention the changedProperties parameter. Answer B is more thorough in explaining *why* each lifecycle is chosen (e.g., explaining why computing in render() or updated() would be wrong for case (a)), and adds valuable extras like the Task controller for async work and race condition handling. Answer B also more explicitly discusses the ordering rationale and the 'pure render' principle, making it more educational and complete.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions willUpdate | tie |
| mentions firstUpdated | tie |
| mentions updated | tie |
| mentions changedProperties parameter | skill |

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

<details><summary>haiku: baseline answer</summary>

# Lit Lifecycle Placement Guide

## (a) Compute derived property from `this.someInput` before render

**Use: `willUpdate()` or a getter**

```typescript
class MyElement extends LitElement {
  @property() someInput: string = '';
  derivedProperty: string = '';

  willUpdate(changedProperties: PropertyValues) {
    if (changedProperties.has('someInput')) {
      this.derivedProperty = this.someInput.toUpperCase();
    }
  }

  render() {
    return html`${this.derivedProperty}`;
  }
}
```

**Why:** `willUpdate()` runs after property changes are detected but *before* `render()`, ensuring derived data is ready. Alternatively, use a getter for simple transformations (it recalculates on every access, which is fine for render).

---

## (b) One-time DOM measurement of child element after first render

**Use: `firstUpdated()`**

```typescript
class MyElement extends LitElement {
  @query('#child') childElement!: HTMLElement;

  firstUpdated() {
    const height = this.childElement.offsetHeight;
    console.log('Child height:', height);
  }

  render() {
    return html`<div id="child">Content</div>`;
  }
}
```

**Why:** `firstUpdated()` runs once after the initial render completes and the DOM is painted. The element is guaranteed to exist and be measurable. Using `@query` ensures the element reference is available.

---

## (c) Call external API after every render that changed an input

**Use: `updated()`**

```typescript
class MyElement extends LitElement {
  @property() userId: string = '';

  updated(changedProperties: PropertyValues) {
    if (changedProperties.has('userId')) {
      this.fetchUserData(this.userId);
    }
  }

  private async fetchUserData(id: string) {
    const response = await fetch(`/api/users/${id}`);
    // handle response
  }

  render() {
    return html`<p>User: ${this.userId}</p>`;
  }
}
```

**Why:** `updated()` runs *after* render completes, so the DOM is stable. Checking `changedProperties` ensures you only fetch when relevant inputs change, avoiding unnecessary API calls.

---

## Quick Reference Table

| Task | Method | Timing |
|------|--------|--------|
| Derive data from inputs | `willUpdate()` / getter | Before render |
| One-time DOM setup | `firstUpdated()` | After first render |
| Side effects on input change | `updated()` | After every render |

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Lifecycle Placement Guide

## (a) Compute a derived property from `this.someInput` before render

**Use `willUpdate(changedProperties)`**

```typescript
willUpdate(changedProperties: PropertyValues) {
  if (changedProperties.has('someInput')) {
    this.derivedValue = expensiveCompute(this.someInput);
  }
}

render() {
  return html`<div>${this.derivedValue}</div>`;
}
```

**Why:**
- Runs once per update cycle, *before* `render()` — so `render()` sees the computed value
- `render()` must be pure (no side effects, no mutations); `willUpdate()` is the right place for derived state
- If you compute in `render()`, you recompute on every call (wasteful) and risk impure side effects
- If you compute in `updated()`, you've already rendered with stale data, forcing a second cycle

**Key detail:** Check `changedProperties.has('someInput')` to avoid recomputing when unrelated properties change.

---

## (b) One-time DOM measurement of a child element after first render

**Use `firstUpdated(changedProperties)`**

```typescript
firstUpdated(changedProperties: PropertyValues) {
  const child = this.shadowRoot!.querySelector('.my-child');
  this.childHeight = child!.offsetHeight;
  // Now you can use this.childHeight in subsequent renders
}

render() {
  return html`
    <div class="my-child" style="height: ${this.childHeight}px">...</div>
  `;
}
```

**Why:**
- Runs exactly once, after the first `render()` completes and the DOM is stable
- The element and its children are guaranteed to exist and be laid out
- Perfect for one-time measurements, focus, or initialization that depends on the rendered DOM
- Cheaper than `updated()` if you only need to run once

**Key detail:** If you need to measure *every* time the DOM changes, use `updated()` instead. But if it's truly one-time (e.g., initial scroll position, initial focus), `firstUpdated()` is cleaner.

---

## (c) Call an external API after every render that changed an input

**Use `updated(changedProperties)` with a guard**

```typescript
@state() private _apiResult: Data | null = null;

updated(changedProperties: PropertyValues) {
  if (changedProperties.has('userId')) {
    this._fetchUser(this.userId);
  }
}

private async _fetchUser(userId: string) {
  try {
    this._apiResult = await fetch(`/api/users/${userId}`).then(r => r.json());
  } catch (e) {
    console.error(e);
  }
}

render() {
  return html`<div>${this._apiResult?.name}</div>`;
}
```

**Why:**
- Runs after `render()` completes, so the DOM is stable and listeners can see the rendered state
- `changedProperties.has('userId')` ensures you only fetch when the input actually changed
- Avoids the "stale render" problem: you don't block render waiting for the API; you render immediately, then fetch

**Better alternative: Use `Task` from `@lit/task`**

```typescript
private _userTask = new Task(this, {
  task: async ([userId], { signal }) => {
    const res = await fetch(`/api/users/${userId}`, { signal });
    return res.json();
  },
  args: () => [this.userId],
});

render() {
  return this._userTask.render({
    pending: () => html`<p>Loading...</p>`,
    complete: (data) => html`<div>${data.name}</div>`,
    error: (e) => html`<p>Error: ${e.message}</p>`,
  });
}
```

**Why Task is better:**
- Automatic cancellation if `userId` changes before the fetch completes (no race conditions)
- Built-in status tracking (pending, complete, error) — no manual state management
- Cleaner separation of async logic from render
- Handles argument tracking for you

See [task-controller.md](references/task-controller.md) for the full API.

---

## Summary Table

| Work | Method | Runs | Why |
|------|--------|------|-----|
| Derive state from inputs | `willUpdate()` | Before render, once per cycle | Computed value ready for `render()`, pure |
| One-time DOM setup | `firstUpdated()` | After first render only | DOM guaranteed to exist, cheap |
| Post-render side effects (API, analytics, DOM mutation) | `updated()` | After every render | DOM is stable; listeners see rendered state |
| Async data fetching | `Task` (preferred) or `updated()` | On arg change | Cancellation, status tracking, race prevention |

**Golden rule:** `render()` is pure. Everything else (derived state, side effects, DOM access) goes in a lifecycle hook.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly map the three tasks to willUpdate, firstUpdated, and updated, and both mention the changedProperties parameter. Answer A is more thorough in its explanations, explicitly addresses why alternative lifecycle methods are wrong for each case, includes a practical caveat about @lit/task for data-fetching scenarios, and provides a cleaner summary table. Answer B is accurate and concise but lacks the depth and nuance that makes Answer A more educational and useful.

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

<details><summary>opus: baseline answer</summary>

# Lit Lifecycle Method Placement

## (a) Compute a derived property from `this.someInput` before render

**Use `willUpdate(changedProperties)`**

```js
willUpdate(changed) {
  if (changed.has('someInput')) {
    this.derived = expensiveCompute(this.someInput);
  }
}
```

**Why:** `willUpdate` runs before `render()` during the update cycle. Setting properties here is folded into the same render pass — no extra re-render is triggered. It's the official hook for computing derived state. (Avoid doing this in `update()` unless you need to call `super.update()` yourself, and avoid `updated()` because that runs *after* render and would force a second update.)

## (b) One-time DOM measurement after first render

**Use `firstUpdated(changedProperties)`**

```js
firstUpdated() {
  const rect = this.renderRoot
    .querySelector('.target')
    .getBoundingClientRect();
  this._height = rect.height;
}
```

**Why:** `firstUpdated` is called exactly once, after the component's DOM has been rendered for the first time. The shadow DOM exists and is laid out, so measurements are valid. Doing this in `connectedCallback` would be too early (no rendered DOM yet); doing it in `updated` would re-measure on every change.

## (c) Call an external API after every render that changed an input

**Use `updated(changedProperties)`**

```js
updated(changed) {
  if (changed.has('query')) {
    this.fetchResults(this.query);
  }
}
```

**Why:** `updated` runs after every render (including the first). Guarding with `changedProperties.has(...)` ensures you only fire the API call when the relevant input actually changed, not on every unrelated re-render. You shouldn't do side effects with external systems in `willUpdate`/`update` because those run before the DOM reflects the new state, and the work could be wasted if the update is interrupted.

---

### Quick mental model

| Phase | Method | Use for |
|---|---|---|
| Before render | `willUpdate` | derived state from props |
| After first render only | `firstUpdated` | initial DOM measurement / setup |
| After every render | `updated` | side effects, external calls, post-render DOM work |

</details>

<details><summary>opus: skill-loaded answer</summary>

Great question — these three cases map cleanly onto three different Lit lifecycle hooks. Picking the right one matters because they run at different phases relative to rendering and reactive-property updates.

## (a) Derived property from `this.someInput` → `willUpdate(changedProperties)`

```ts
willUpdate(changed: PropertyValues<this>) {
  if (changed.has('someInput')) {
    this.derived = expensiveCompute(this.someInput);
  }
}
```

**Why `willUpdate` and not `render()` or `updated()`:**

- **Not `render()`** — `render()` must be pure. Side effects there (including assigning to reactive properties) violate Lit's contract and can trigger warnings or extra render cycles.
- **Not `updated()`** — that runs *after* render. If you set `this.derived` there, you've already rendered with the stale value, and setting it then schedules a *second* update cycle. Wasteful and visibly flickery.
- **`willUpdate` runs before `render()`**, after reactive properties have settled but before the template is built. Anything you assign to `this.derived` here is visible to `render()` in the same cycle. It's also the place to gate work with `changedProperties.has('someInput')` so you don't recompute when unrelated properties change.

## (b) One-time DOM measurement of a child → `firstUpdated(changedProperties)`

```ts
firstUpdated() {
  const child = this.renderRoot.querySelector('.target')!;
  this._initialHeight = child.getBoundingClientRect().height;
}
```

**Why `firstUpdated`:**

- It runs exactly once, after the first render completes and the shadow DOM is populated. The child element is guaranteed to exist.
- **Not `connectedCallback`** — the element is in the document, but `render()` hasn't run yet, so `this.renderRoot` is empty. Querying for `.target` returns `null`.
- **Not `constructor`** — same problem, plus no DOM at all.
- **Not `updated()`** — that runs on *every* update, so you'd re-measure unnecessarily (and pay layout cost each time). `firstUpdated` is purpose-built for one-shot post-render setup.

If you need the measurement to reflect later layout changes too, use a `ResizeObserver` set up in `firstUpdated` (or better, in a reactive controller) rather than measuring in `updated()`.

## (c) External API call when an input changed → `updated(changedProperties)`

```ts
updated(changed: PropertyValues<this>) {
  if (changed.has('userId')) {
    this._sendAnalytics(this.userId);
  }
}
```

**Why `updated`:**

- It runs after every render, with `changedProperties` telling you what actually changed. Gate the side effect with `changed.has('userId')` so you only call the API when the relevant input changed, not on every render.
- The DOM reflects the latest state at this point, which matters if the API call needs to read rendered DOM (measurements, computed styles, etc.).
- **Not `willUpdate`** — that's for synchronous, pure derivations of state. Doing async I/O there is wrong: it runs before render, and if the API response sets a property, you'd kick off another update mid-cycle.
- **Not `render()`** — never put side effects in `render()`.

**Important caveat for case (c):** if the "external API" is really a fetch to load data that drives the UI, don't hand-roll it in `updated()`. Use `@lit/task` with `args: () => [this.userId]` — you get cancellation, race-condition handling, and pending/error states for free. `updated()` is the right place for *fire-and-forget* side effects (analytics, logging, imperative DOM commands on a third-party library) that don't feed back into render state.

## Summary table

| Work | Hook | Runs | Key reason |
|------|------|------|------------|
| Derive state before render | `willUpdate` | Before every render | Visible to `render()` same cycle; no second pass |
| One-time DOM setup | `firstUpdated` | Once, after first render | DOM exists; runs exactly once |
| Side effect on input change | `updated` | After every render | DOM is current; gate with `changedProperties.has(...)` |

</details>

---

### `state-vs-property`

**Prompt**

```
In Lit, when should I use @state() versus @property() on a class
field? I'm a bit unclear on the distinction.
```

**Judge focus:** The better answer explains @property is the public reactive API
(synced with HTML attribute by default), @state is internal-only
(no attribute), and gives concrete examples of each.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A adds a useful note about reference equality and mutation detection, while Answer B includes a helpful clarification that @state() is essentially shorthand for @property({ attribute: false }), which is a concrete technical detail. Both provide clear examples, comparison tables, and decision rules at roughly the same quality level.

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
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `Triggers re-render` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `triggers re-render` |

<details><summary>sonnet: baseline answer</summary>

## `@state()` vs `@property()` in Lit

The core distinction is about **public API vs internal state**.

---

### `@property()` — Public API
Use when the value should be **configurable from outside** the component.

```javascript
class MyButton extends LitElement {
  @property({ type: String }) label = 'Click me';
  @property({ type: Boolean }) disabled = false;
}
```

```html
<!-- Consumers can set these as HTML attributes or JS properties -->
<my-button label="Submit" disabled></my-button>
```

**Characteristics:**
- Reflected to/from HTML attributes (by default)
- Shows up in your component's public interface
- Triggers re-render on change
- Can be set by parent components or plain HTML

---

### `@state()` — Internal/Private State
Use when the value is **implementation detail** that outsiders shouldn't touch.

```javascript
class MyDropdown extends LitElement {
  @property({ type: Array }) options = [];  // public input

  @state() private isOpen = false;          // internal state
  @state() private selectedIndex = -1;      // internal state
}
```

**Characteristics:**
- **Not** reflected to HTML attributes
- No attribute observation
- Triggers re-render on change
- Signals "don't touch this from outside"

---

### Side-by-Side Comparison

| Feature | `@property()` | `@state()` |
|---|---|---|
| Triggers re-render | ✅ | ✅ |
| Reflected to attribute | ✅ (configurable) | ❌ |
| Observed from attribute | ✅ | ❌ |
| Public API | ✅ | ❌ |
| Typical visibility | `public` | `private` / `protected` |

---

### `@state()` is essentially a shorthand

```javascript
// These two are equivalent:
@state()
private isOpen = false;

@property({ state: true, attribute: false })
private isOpen = false;
```

---

### Quick Decision Rule

```
Does a parent component or HTML author need to set this value?
├── YES → @property()
└── NO  → @state()
```

A common pattern is using both together — `@property()` for inputs, `@state()` for derived or UI-only values that change as the user interacts with the component.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## `@property()` vs `@state()`

Both decorators make a field **reactive** — Lit schedules a re-render whenever the value changes. The difference is entirely about **visibility**: who is allowed to set the value, and whether it maps to an HTML attribute.

---

### `@property()` — public API

Use this when the field is part of the component's **external interface**: something a parent component, framework, or HTML author should be able to set.

```typescript
@customElement('user-card')
class UserCard extends LitElement {
  @property() name = '';
  @property({ type: Number }) age = 0;
  @property({ type: Boolean, reflect: true }) disabled = false;
}
```

What you get:
- **Attribute binding** — Lit auto-converts between the HTML attribute (`name="Alice"`) and the JS property (`el.name = 'Alice'`). The `type` option controls that conversion.
- **`reflect: true`** — writes the property value back to the attribute, useful for CSS attribute selectors like `[disabled]`.
- **Public contract** — signals to consumers "this is a knob you're meant to turn."

### `@state()` — private internal state

Use this when the field drives rendering but is **nobody else's business** — things like whether a dropdown is open, a loading flag, or a locally computed value.

```typescript
@customElement('search-box')
class SearchBox extends LitElement {
  @property() placeholder = 'Search…'; // public input

  @state() private _isOpen = false;    // internal toggle
  @state() private _inputValue = '';   // tracks the live input
}
```

What you get:
- **Reactive** — still triggers re-renders on change.
- **No attribute** — never serialized to or from HTML.
- **No public surface** — TypeScript's `private` keyword (or the `#` prefix) enforces this at compile time; `@state()` signals the intent at the Lit level.

---

### Side-by-side comparison

| | `@property()` | `@state()` |
|---|---|---|
| Triggers re-render | ✅ | ✅ |
| Maps to HTML attribute | ✅ (by default) | ❌ |
| Reflects to attribute | Optional (`reflect: true`) | ❌ |
| Intended audience | External callers | The component itself |
| Conventional visibility | `public` | `private` / `#` |

---

### The mutation rule applies to both

Lit uses **reference equality** (`!==`) to detect changes. Mutating an object or array in place won't trigger a re-render regardless of which decorator you used:

```typescript
// ❌ No re-render — same array reference
this._items.push(newItem);

// ✅ New reference — re-render scheduled
this._items = [...this._items, newItem];
```

---

### Quick decision rule

> **Will anything outside this component ever read or write this field?**
> - Yes → `@property()`
> - No → `@state()`

If you find yourself reaching for `@property()` on something that's clearly internal (a hover flag, a toggle, a cached computation), switch to `@state()`. It keeps the public API surface small and prevents accidental coupling.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more comprehensive and concrete, providing a practical modal dialog example that clearly shows both decorators used together in a realistic scenario. It more explicitly explains that @property() fields are synced with HTML attributes by default (showing actual HTML attribute usage), while @state() has no attribute binding, and it uses TypeScript's private keyword to reinforce the internal-only nature of @state(). Both answers cover all rubric criteria, but B does so with greater depth and clarity.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies @property as public API / attribute-synced | skill |
| identifies @state as internal / no attribute | skill |
| mentions reactive trigger / re-render | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `triggers re-render` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `Public` |
| identifies @state as internal / no attribute | ✓ | `Internal` |
| mentions reactive trigger / re-render | ✓ | `Triggers update` |

<details><summary>haiku: baseline answer</summary>

# @state() vs @property() in Lit

The key distinction is about **reactivity** and **what triggers re-renders**:

## @state()
Use this for **internal component state** that should trigger re-renders when changed.

```javascript
import { LitElement, html } from 'lit';
import { state } from 'lit/decorators.js';

class MyComponent extends LitElement {
  @state()
  count = 0;

  render() {
    return html`
      <p>Count: ${this.count}</p>
      <button @click=${() => this.count++}>Increment</button>
    `;
  }
}
```

**Characteristics:**
- Private to the component (by convention, prefix with `_`)
- Changes trigger a re-render
- Not exposed to parent components
- Not reflected in HTML attributes

## @property()
Use this for **public properties** that can be set by parent components and should trigger re-renders.

```javascript
import { LitElement, html } from 'lit';
import { property } from 'lit/decorators.js';

class MyComponent extends LitElement {
  @property()
  name = 'World';

  render() {
    return html`<p>Hello, ${this.name}!</p>`;
  }
}
```

**Characteristics:**
- Public API for the component
- Changes trigger a re-render
- Can be set by parent components
- Can be reflected to HTML attributes (with `reflect: true`)
- Supports type conversion

## Quick Comparison

| Feature | @state() | @property() |
|---------|----------|------------|
| Triggers re-render | ✅ | ✅ |
| Public API | ❌ | ✅ |
| Set by parent | ❌ | ✅ |
| Reflect to attribute | ❌ | ✅ (optional) |
| Internal only | ✅ | ❌ |

**Rule of thumb:** Use `@state()` for internal data, `@property()` for component inputs.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# @state() vs @property() in Lit

The distinction is about **API surface and reactivity scope**:

## @property() — Public API, Attribute Binding

Use `@property()` for inputs that:
- Are part of your component's **public contract** — consumers set them
- Should be **settable via HTML attributes** (with optional type conversion)
- Represent **external data flowing in** from a parent or attribute

```typescript
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('user-card')
export class UserCard extends LitElement {
  @property() name: string = '';
  @property() email: string = '';
  @property({ type: Number }) age: number = 0;

  render() {
    return html`<h1>${this.name}</h1><p>${this.email}</p>`;
  }
}
```

**Consumers use it like this:**
```html
<user-card name="Alice" email="alice@example.com" age="30"></user-card>
```

Or via JavaScript:
```javascript
const card = document.querySelector('user-card');
card.name = 'Bob';
card.email = 'bob@example.com';
```

---

## @state() — Private Internal State, No Attributes

Use `@state()` for state that:
- Is **internal to the component** — consumers don't set it
- Should **not** be reflected to an HTML attribute
- Drives rendering but is **not part of the public API**

```typescript
@customElement('counter-button')
export class CounterButton extends LitElement {
  @state() private count = 0;

  render() {
    return html`<button @click=${this.increment}>Count: ${this.count}</button>`;
  }

  private increment() {
    this.count++;
  }
}
```

**Key difference:** `@state()` fields are typically `private` and never set from outside the component.

---

## Side-by-Side Comparison

| Aspect | `@property()` | `@state()` |
|--------|--------------|-----------|
| **Visibility** | Public API | Private/internal |
| **Set from outside?** | Yes (attribute or JS) | No |
| **HTML attribute?** | Yes (if `attribute: true`, the default) | No |
| **Type conversion?** | Yes (via `type` or `converter`) | No |
| **Typical access** | `public` | `private` |
| **Triggers update?** | Yes | Yes |
| **Use case** | Inputs, configuration | Derived state, UI toggles, counters |

---

## Practical Example: Modal Dialog

```typescript
@customElement('my-modal')
export class MyModal extends LitElement {
  // Public API: consumers control whether modal is shown
  @property({ type: Boolean }) open = false;

  // Internal state: tracks which tab is active
  @state() private activeTab = 'general';

  render() {
    if (!this.open) return nothing;
    return html`
      <div class="modal">
        <button @click=${() => (this.activeTab = 'general')}>General</button>
        <button @click=${() => (this.activeTab = 'advanced')}>Advanced</button>
        ${this.activeTab === 'general' ? html`<p>General content</p>` : html`<p>Advanced content</p>`}
      </div>
    `;
  }
}
```

**Usage:**
```html
<!-- Parent controls open/close via property -->
<my-modal open></my-modal>

<script>
  const modal = document.querySelector('my-modal');
  modal.open = false; // Parent can toggle this
  // But modal.activeTab is private — parent doesn't touch it
</script>
```

---

## When in Doubt

- **Does a parent component or HTML attribute need to set this?** → `@property()`
- **Is this only used internally to drive rendering?** → `@state()`

Both trigger re-renders when they change. The distinction is about **encapsulation and API clarity**, not reactivity.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers are excellent and cover all three rubric criteria well. Answer A edges out B by providing more depth: it explains the `@property({ attribute: false })` edge case which clarifies the boundary between the two decorators, includes a concrete `willUpdate()` derived-state example, and gives a cleaner narrative flow. Answer B's decision table is a nice touch but overall A provides more actionable nuance without being verbose.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies @property as public API / attribute-synced | tie |
| identifies @state as internal / no attribute | tie |
| mentions reactive trigger / re-render | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `triggers re-render` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `triggers a re-render` |

<details><summary>opus: baseline answer</summary>

# `@property()` vs `@state()` in Lit

The core distinction is **public API vs. internal state**.

## `@property()` — Public, reactive, exposed to HTML

Use when the field is part of your component's public interface:

- Should be settable from outside (HTML attributes or parent components)
- Reflects to/from an HTML attribute by default
- Shows up in TypeScript's element interface for consumers

```ts
@property({ type: String })
name = 'World';

@property({ type: Boolean, reflect: true })
disabled = false;
```

Then consumers can do:
```html
<my-element name="Alice" disabled></my-element>
```

## `@state()` — Private, reactive, internal only

Use when the field is internal implementation detail:

- Not exposed as an attribute
- Not part of the public API (won't appear in generated manifests, etc.)
- Still triggers re-renders when changed

```ts
@state()
private _isOpen = false;

@state()
private _fetchedData: User[] = [];
```

## Quick decision guide

| Question | Use |
|---|---|
| Should a parent set this via attribute or property? | `@property()` |
| Is this derived/fetched/computed internally? | `@state()` |
| Is it a UI toggle like "is the menu open"? | `@state()` |
| Is it config the user provides? | `@property()` |

## Common pitfall

Don't use `@property()` for everything just to get reactivity. If you do, you're leaking internals into your public API, and tools like custom-element manifests will document them as if users should set them.

A good rule: **if it starts with `_` or feels private, it's probably `@state()`.**

</details>

<details><summary>opus: skill-loaded answer</summary>

## `@property()` vs `@state()`

Both make a class field **reactive** — changing the field triggers a re-render. The difference is whether the field is part of your component's **public API**.

### `@property()` — public, external input

Use when the value is set by **whoever uses your component** (parent template, framework, plain HTML).

- Reflects to/from an HTML **attribute** by default, so it works from markup: `<user-card name="Ada">`
- Has type conversion (String, Number, Boolean, Object, Array)
- Shows up in your component's documented API

```ts
@property() name = '';
@property({ type: Number }) age = 0;
@property({ type: Boolean }) disabled = false;
```

### `@state()` — private, internal

Use when the value is **managed inside the component** and consumers shouldn't know or care about it.

- No attribute, no type conversion, no public API surface
- Triggers re-renders just like `@property()`
- Signals "this is an implementation detail"

```ts
@state() private _isOpen = false;
@state() private _hoveredIndex = -1;
@state() private _fetchedData: User[] = [];
```

### Rule of thumb

Ask: *"Should someone be able to set this from outside the component?"*

- **Yes** → `@property()`
- **No** → `@state()`

### Common case: derived state

If a value is computed from properties, it's internal — use `@state()` (or just compute it in `willUpdate()` without a decorator at all):

```ts
@property() firstName = '';
@property() lastName = '';
@state() private _fullName = '';

willUpdate(changed: PropertyValues) {
  if (changed.has('firstName') || changed.has('lastName')) {
    this._fullName = `${this.firstName} ${this.lastName}`;
  }
}
```

### Edge case: `@property({ attribute: false })`

This is a `@property()` with no attribute binding — useful for public API values that **can't** be expressed as a string attribute (objects, functions, complex data passed only from JS/templates). Still public, just not settable from HTML markup.

```ts
@property({ attribute: false }) user?: User;  // public, but JS-only
```

If you find yourself reaching for this **and** the value is internal, you probably want `@state()` instead.

</details>

---

### `custom-directive-vs-helper`

**Prompt**

```
I have a small piece of templating logic I'm reusing across three
Lit components — it formats a list of items with some conditional
rendering. Should I extract it into a custom Lit directive (extends
Directive) or just a helper function that returns a TemplateResult?
What's the difference?
```

**Judge focus:** The better answer explains that a plain helper function returning
a TemplateResult is the right tool for "compose a sub-template" —
custom directives only earn their weight when you need access to
the underlying Part (DOM node), want noChange to skip work, or
need persistent state between renders. Custom directives are
overkill for "I want to reuse some markup."

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend a helper function and explain when directives are justified, but Answer B is more focused and pedagogically cleaner. B's decision rule at the end is particularly crisp, its directive justification section is more precise (mentioning AsyncDirective and the 'push updates outside render cycle' case), and it avoids the slightly misleading noChange example in A where the directive still computes a result before checking reference equality. B also better emphasizes that Lit's diffing handles TemplateResult efficiently regardless of extraction, which directly addresses a common concern.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends helper function for the simple case | tie |
| explains when a Directive is justified | skill |
| mentions Directive class or directive() factory | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends helper function for the simple case | ✓ | `Helper` |
| explains when a Directive is justified | ✓ | `noChange` |
| mentions Directive class or directive() factory | ✓ | `class HighlightListDirective extends Directive` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends helper function for the simple case | ✓ | `Helper` |
| explains when a Directive is justified | ✓ | `Part` |
| mentions Directive class or directive() factory | ✓ | `class CountUpDirective extends Directive` |

<details><summary>sonnet: baseline answer</summary>

## Helper Function vs Custom Directive

Great question — this is a common decision point in Lit development. The short answer is: **use a helper function** for your case. Here's why, and when each actually makes sense.

---

## Helper Function (Returns `TemplateResult`)

```typescript
// helpers/format-list.ts
import { html, TemplateResult, nothing } from 'lit';

interface ListItem {
  id: string;
  label: string;
  disabled?: boolean;
}

export function formatList(
  items: ListItem[],
  selectedId?: string
): TemplateResult | typeof nothing {
  if (!items.length) {
    return html`<p class="empty">No items found.</p>`;
  }

  return html`
    <ul class="item-list">
      ${items.map(
        (item) => html`
          <li
            class=${item.disabled ? 'disabled' : ''}
            aria-selected=${item.id === selectedId}
          >
            ${item.label}
          </li>
        `
      )}
    </ul>
  `;
}
```

```typescript
// my-component.ts
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { formatList } from './helpers/format-list.js';

@customElement('my-component')
class MyComponent extends LitElement {
  @property({ type: Array }) items = [];
  @property() selectedId?: string;

  render() {
    return html`
      <div class="wrapper">
        ${formatList(this.items, this.selectedId)}
      </div>
    `;
  }
}
```

**This is the right choice when:**
- You're composing/returning markup
- Logic is stateless (no need to track previous renders)
- You just need reusable template fragments
- Straightforward conditional rendering

---

## Custom Directive (Extends `Directive`)

```typescript
// directives/highlight-list.ts
import { Directive, directive, PartInfo, PartType } from 'lit/directive.js';
import { html, noChange, nothing } from 'lit';
import type { ChildPart } from 'lit';

class HighlightListDirective extends Directive {
  // Directives can hold STATE between renders
  private previousItems: string[] = [];
  private renderCount = 0;

  constructor(partInfo: PartInfo) {
    super(partInfo);
    // Can validate WHERE the directive is used
    if (partInfo.type !== PartType.CHILD) {
      throw new Error('highlight-list must be used in child position');
    }
  }

  render(items: string[], highlightNew: boolean) {
    this.renderCount++;

    const newItems = items.filter(
      (item) => !this.previousItems.includes(item)
    );

    // KEY FEATURE: return noChange to skip DOM update entirely
    if (items === this.previousItems) {
      return noChange;
    }

    const result = html`
      <ul>
        ${items.map(
          (item) => html`
            <li class=${highlightNew && newItems.includes(item) ? 'new' : ''}>
              ${item}
            </li>
          `
        )}
      </ul>
    `;

    // Mutate state AFTER computing result
    this.previousItems = [...items];
    return result;
  }
}

export const highlightList = directive(HighlightListDirective);
```

```typescript
// usage
render() {
  return html`
    ${highlightList(this.items, true)}
  `;
}
```

**This is the right choice when:**
- You need **state that persists between renders** (previous values, timers, subscriptions)
- You need **direct DOM access** via `update()` instead of `render()`
- You need to return `noChange` to **bail out of rendering** for performance
- You need to **validate placement** (child vs attribute vs property position)
- You're building something like `repeat()`, `until()`, `animate()` — behavior, not just markup

---

## The Core Difference

| | Helper Function | Custom Directive |
|---|---|---|
| **Returns** | `TemplateResult` | `TemplateResult`, `noChange`, or DOM values |
| **Has state** | ❌ No | ✅ Yes (instance persists) |
| **DOM access** | ❌ No | ✅ Via `update()` |
| **Complexity** | Low | Medium-High |
| **Use for** | Markup composition | Behavior / optimization |
| **Lit internals** | Unaware | Integrated |

---

## Your Specific Case

```
formatting a list with conditional rendering → Helper Function ✅
```

Directives exist to hook into Lit's **rendering lifecycle** for things that can't be expressed as markup alone. Your use case is purely about **what to render**, not **how rendering behaves** — that's exactly what helper functions are for.

A good rule of thumb: **reach for a directive only when you find yourself wishing a helper function could remember something between renders, or skip rendering altogether.**

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Helper Function vs Custom Directive

For formatting a list with conditional rendering, **a helper function returning `TemplateResult` is almost certainly the right choice**. Custom directives solve a different class of problem.

Here's the core distinction:

| | Helper function | Custom directive |
|---|---|---|
| Returns | `TemplateResult` | Controls a DOM `Part` directly |
| Statefulness | Stateless (pure) | Can hold instance state across renders |
| DOM access | None | Direct, low-level |
| Complexity | Trivial | Meaningful boilerplate |
| Right for | Reusable templates | DOM manipulation Lit can't express declaratively |

---

### Helper function — what you actually want

```typescript
// list-helpers.ts
import { html, nothing, TemplateResult } from 'lit';

export interface ListItem {
  id: string;
  label: string;
  disabled?: boolean;
}

export function renderItemList(
  items: ListItem[],
  selectedId: string | null
): TemplateResult {
  if (items.length === 0) {
    return html`<p class="empty">No items found.</p>`;
  }

  return html`
    <ul>
      ${items.map(item => html`
        <li
          class=${item.disabled ? 'disabled' : nothing}
          aria-selected=${item.id === selectedId}
        >
          ${item.label}
          ${item.disabled ? html`<span class="badge">Unavailable</span>` : nothing}
        </li>
      `)}
    </ul>
  `;
}
```

```typescript
// any-component.ts
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { renderItemList } from './list-helpers.js';

@customElement('my-component')
class MyComponent extends LitElement {
  @state() private items: ListItem[] = [];
  @state() private selectedId: string | null = null;

  render() {
    return html`
      <h2>Items</h2>
      ${renderItemList(this.items, this.selectedId)}
    `;
  }
}
```

Lit's template engine handles efficient diffing of the returned `TemplateResult` — you get the same update performance as inline templates. There's no overhead to extracting it this way.

---

### When a directive is actually justified

A directive is the right tool when you need something a `TemplateResult` **cannot express**:

- **Instance state that persists across renders** — e.g., a directive that animates between old and new values needs to remember the previous value
- **Direct DOM Part manipulation** — e.g., `ref()`, `live()`, `unsafeHTML()` all need to reach into the DOM node itself
- **Async rendering with external push** — `AsyncDirective` lets you call `setValue()` from outside the render cycle (think a directive that subscribes to an observable)
- **Bypassing Lit's diffing intentionally** — e.g., `unsafeHTML` sets `innerHTML` directly

The built-in directives (`repeat`, `classMap`, `styleMap`, `ref`, `until`) are good examples of things that *genuinely* need the directive API. Your list formatting doesn't need any of that.

```typescript
// A directive IS warranted here: stateful animation between values
import { Directive, directive, PartInfo, PartType } from 'lit/directive.js';

class CountUpDirective extends Directive {
  private _previousValue = 0; // state that survives re-renders

  render(newValue: number) {
    // animate from _previousValue → newValue, then update
    this._previousValue = newValue;
    return newValue;
  }
}
export const countUp = directive(CountUpDirective);
```

A helper function has no `this` — it can't hold that previous value between calls.

---

### Decision rule

```
Does the logic need to:
  - remember state between renders?          → directive
  - directly manipulate a DOM node/Part?     → directive
  - push updates outside the render cycle?   → AsyncDirective
  - just produce HTML from inputs?           → helper function
```

Your case — formatting a list with conditional rendering — is pure input-to-template transformation. Use a helper function. Save directives for when you're fighting against what `TemplateResult` can express, not working within it.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend the helper function for the simple case, but Answer B is more precise and idiomatic in its explanation of when directives are justified — specifically calling out `noChange` to skip work, Part access, and persistent state between renders, which aligns directly with the focus area. Answer B also includes a decision tree, mentions `AsyncDirective`, and explicitly shows `noChange` as a key directive benefit, while Answer A's directive example is somewhat misleading (storing items as instance variables in a way that doesn't demonstrate real directive value). Answer B's 'even here you could use a helper + updated()' section reinforces the core message more effectively.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends helper function for the simple case | tie |
| explains when a Directive is justified | skill |
| mentions Directive class or directive() factory | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends helper function for the simple case | ✓ | `Helper` |
| explains when a Directive is justified | ✓ | `part` |
| mentions Directive class or directive() factory | ✓ | `class FormatItemListDirective extends Directive` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends helper function for the simple case | ✓ | `Helper` |
| explains when a Directive is justified | ✓ | `Part` |
| mentions Directive class or directive() factory | ✓ | `class FormatItemListDirective extends Directive` |

<details><summary>haiku: baseline answer</summary>

# Directive vs Helper Function in Lit

Both work, but they have different strengths. Here's how to choose:

## Helper Function (Simpler)

```typescript
function formatItemList(items: Item[], showPrice: boolean) {
  return html`
    <ul>
      ${items.map(item => html`
        <li>
          ${item.name}
          ${showPrice ? html`<span class="price">${item.price}</span>` : ''}
        </li>
      `)}
    </ul>
  `;
}

// Usage
class MyComponent extends LitElement {
  render() {
    return html`
      <div>${formatItemList(this.items, true)}</div>
    `;
  }
}
```

**Use this when:**
- Logic is purely presentational
- You just need to return a `TemplateResult`
- No need to interact with the DOM after rendering
- Simpler to test and reason about

## Custom Directive (More Powerful)

```typescript
class FormatItemListDirective extends Directive {
  items: Item[] = [];
  showPrice = false;

  render(items: Item[], showPrice: boolean) {
    this.items = items;
    this.showPrice = showPrice;
    return html`
      <ul>
        ${items.map(item => html`
          <li>
            ${item.name}
            ${showPrice ? html`<span class="price">${item.price}</span>` : ''}
          </li>
        `)}
      </ul>
    `;
  }

  update(part: Part, [items, showPrice]: Parameters<this['render']>) {
    // Called when inputs change
    if (items !== this.items) {
      console.log('Items changed, could do cleanup');
    }
    return this.render(items, showPrice);
  }
}

export const formatItemList = directive(FormatItemListDirective);

// Usage
class MyComponent extends LitElement {
  render() {
    return html`
      <div>${formatItemList(this.items, true)}</div>
    `;
  }
}
```

**Use this when:**
- You need lifecycle hooks (`update`, `disconnect`)
- You need to manage DOM references or side effects
- You want to optimize re-renders (e.g., only update when specific props change)
- You need to clean up resources

## Key Differences

| Aspect | Helper Function | Directive |
|--------|-----------------|-----------|
| **Lifecycle** | None | `render()`, `update()`, `disconnect()` |
| **DOM Access** | No | Yes (via `Part`) |
| **Side Effects** | Not ideal | Built for this |
| **Complexity** | Low | Higher |
| **Performance** | Good for simple cases | Better for complex updates |
| **Testing** | Easier | Requires more setup |

## Practical Example: When Directive Shines

```typescript
// Directive that manages focus or event listeners
class FocusItemDirective extends Directive {
  private focusedIndex = 0;

  render(items: Item[]) {
    return html`
      <ul>
        ${items.map((item, i) => html`
          <li ?autofocus=${i === this.focusedIndex}>
            ${item.name}
          </li>
        `)}
      </ul>
    `;
  }

  update(part: Part, [items]: Parameters<this['render']>) {
    // Can access the actual DOM element via part.element
    const ul = part.element as HTMLUListElement;
    const focused = ul.querySelector('[autofocus]') as HTMLLIElement;
    focused?.focus();
    
    return this.render(items);
  }

  disconnect() {
    // Cleanup if needed
  }
}
```

## Recommendation

**Start with a helper function.** Only upgrade to a directive if you need:
- DOM manipulation after rendering
- Lifecycle management
- Performance optimization for complex updates

For your reusable templating logic, a helper function is probably the right choice unless you have specific DOM interaction needs.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Custom Directive vs. Helper Function

**Use a helper function** unless you need direct DOM Part access, async lifecycle, or stateful DOM manipulation. For pure template logic, a helper is simpler and sufficient.

## Quick Comparison

| Aspect | Helper Function | Custom Directive |
|--------|-----------------|------------------|
| **Complexity** | Simple: `(items) => html\`...\`` | More boilerplate: class + `render()` |
| **When to use** | Pure template transformation, no DOM side effects | DOM Part manipulation, async setup, stateful DOM nodes |
| **Lifecycle** | None — just returns `TemplateResult` | Full: `update()`, `render()`, async hooks |
| **Performance** | Identical for pure templates | Slightly better if you avoid re-rendering the same Part |
| **Testing** | Trivial: call the function, check output | Requires directive test harness |

## Helper Function (Recommended for Your Case)

```typescript
// shared-templates.ts
import { html, TemplateResult } from 'lit';

export function formatItemList(
  items: Array<{ id: string; label: string; hidden?: boolean }>
): TemplateResult {
  return html`
    <ul>
      ${items
        .filter(item => !item.hidden)
        .map(item => html`<li key=${item.id}>${item.label}</li>`)}
    </ul>
  `;
}
```

```typescript
// my-component.ts
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { formatItemList } from './shared-templates.js';

@customElement('my-component')
export class MyComponent extends LitElement {
  @property() items: Array<{ id: string; label: string; hidden?: boolean }> = [];

  render() {
    return html`
      <div class="container">
        ${formatItemList(this.items)}
      </div>
    `;
  }
}
```

**Pros:**
- Zero boilerplate — just a function
- Easy to test: call it, assert the returned `TemplateResult`
- Composable: nest helpers, pass them around
- No lifecycle overhead

**Cons:**
- Can't intercept DOM updates or manage stateful DOM nodes
- No async setup (but you can use `Task` in the component instead)

---

## Custom Directive (Only If You Need DOM Access)

Use a directive **only** if you need to:
- Directly manipulate DOM nodes (e.g., focus, scroll, measure)
- Manage async setup/teardown tied to a specific Part
- Avoid re-rendering the same Part when inputs haven't changed

```typescript
// format-item-list.directive.ts
import { Directive, PartType, noChange } from 'lit';
import { directive } from 'lit/directive.js';
import { html } from 'lit';

class FormatItemListDirective extends Directive {
  render(
    items: Array<{ id: string; label: string; hidden?: boolean }>
  ) {
    return html`
      <ul>
        ${items
          .filter(item => !item.hidden)
          .map(item => html`<li key=${item.id}>${item.label}</li>`)}
      </ul>
    `;
  }
}

export const formatItemList = directive(FormatItemListDirective);
```

```typescript
// my-component.ts
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { formatItemList } from './format-item-list.directive.js';

@customElement('my-component')
export class MyComponent extends LitElement {
  @property() items: Array<{ id: string; label: string; hidden?: boolean }> = [];

  render() {
    return html`
      <div class="container">
        ${formatItemList(this.items)}
      </div>
    `;
  }
}
```

**Pros:**
- Can intercept DOM updates via `update()` and `render()`
- Can manage async setup/teardown
- Can skip re-render if inputs haven't changed (return `noChange`)

**Cons:**
- More boilerplate
- Harder to test (requires directive test harness)
- Overkill for pure template logic

---

## Real-World Example: When a Directive Shines

You'd reach for a directive if your "formatting" involved **DOM side effects**:

```typescript
// Example: auto-focus the first item, measure list height
class FormatItemListDirective extends Directive {
  private _listElement: HTMLUListElement | null = null;

  render(items: Array<{ id: string; label: string; hidden?: boolean }>) {
    return html`
      <ul>
        ${items
          .filter(item => !item.hidden)
          .map((item, idx) => html`
            <li 
              key=${item.id}
              ${idx === 0 ? 'autofocus' : ''}
            >
              ${item.label}
            </li>
          `)}
      </ul>
    `;
  }

  update(part: Part, [items]: Parameters<this['render']>) {
    // Measure the list after render
    const result = super.update(part, [items]);
    
    // Access the DOM node after Lit updates it
    if (part.type === PartType.CHILD) {
      this._listElement = (part as ChildPart).parentNode?.querySelector('ul') ?? null;
      if (this._listElement) {
        console.log('List height:', this._listElement.offsetHeight);
      }
    }
    
    return result;
  }
}
```

But even here, you could achieve the same with a helper + `updated()` in the component:

```typescript
// Simpler: helper + component lifecycle
export function formatItemList(items: Array<...>) {
  return html`...`;
}

@customElement('my-component')
export class MyComponent extends LitElement {
  @property() items = [];

  updated() {
    const list = this.shadowRoot?.querySelector('ul');
    if (list) console.log('List height:', list.offsetHeight);
  }

  render() {
    return html`<div>${formatItemList(this.items)}</div>`;
  }
}
```

---

## Decision Tree

```
Does your template logic need to:
  ├─ Directly manipulate DOM nodes (focus, scroll, measure)?
  │  └─ YES → Custom Directive
  ├─ Manage async setup/teardown tied to a specific Part?
  │  └─ YES → Custom Directive (or AsyncDirective)
  ├─ Skip re-render if inputs haven't changed?
  │  └─ YES → Custom Directive (return noChange)
  └─ Just transform data into HTML?
     └─ NO → Helper Function ✓
```

---

## Recommendation for Your Case

**Use a helper function.** You're reusing template logic across three components — that's a perfect fit for a simple function that returns `TemplateResult`. No DOM manipulation, no async setup, no stateful nodes. Keep it simple.

```typescript
// shared-templates.ts
export function formatItemList(items: ItemType[]): TemplateResult {
  return html`
    <ul>
      ${items
        .filter(item => !item.hidden)
        .map(item => html`<li key=${item.id}>${item.label}</li>`)}
    </ul>
  `;
}
```

Then import and call it in each component's `render()`. If you later need DOM access or async setup, you can always refactor to a directive — but start with the simpler tool.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A provides a more detailed table and TypeScript examples, while Answer B adds a useful practical tip about using Lit's built-in `repeat` directive as an alternative to custom directives for keyed list reconciliation. Both correctly recommend helper functions, explain directive justification well, and mention the Directive class/factory.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends helper function for the simple case | tie |
| explains when a Directive is justified | tie |
| mentions Directive class or directive() factory | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends helper function for the simple case | ✓ | `helper` |
| explains when a Directive is justified | ✓ | `Part` |
| mentions Directive class or directive() factory | ✓ | `extends Directive` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends helper function for the simple case | ✓ | `helper` |
| explains when a Directive is justified | ✓ | `Part` |
| mentions Directive class or directive() factory | ✓ | `extends Directive` |

<details><summary>opus: baseline answer</summary>

Short answer: use a plain helper function that returns a `TemplateResult`. Custom directives are overkill for what you're describing.

## The difference

**Helper function returning `TemplateResult`:**
- Just a function. Called every render. Returns html`...`.
- Lit diffs the result like any other template.
- Zero ceremony, fully composable, easy to test.

```js
const renderItems = (items, opts = {}) => html`
  <ul>
    ${items.map(item => html`
      <li class=${item.active ? 'active' : ''}>
        ${item.label}
        ${opts.showCount ? html`<span>(${item.count})</span>` : ''}
      </li>
    `)}
  </ul>
`;
```

**Custom directive (`extends Directive` / `AsyncDirective`):**
- A class with `update()`/`render()` lifecycle, access to the `Part` it's bound to, and persistent state across renders.
- Can do things templates can't: imperatively read/write the DOM node, hold subscriptions, schedule async updates, short-circuit re-renders, etc.
- More boilerplate, harder to compose, and you opt out of some of Lit's normal flow.

## When you actually need a directive

Reach for `Directive` only when you need at least one of:

1. **Persistent state tied to a Part** across renders (e.g. caching, memoization keyed to a DOM location).
2. **Direct access to the DOM element/attribute** (like `ref`, `classMap`, `styleMap`, `live`).
3. **Async updates** that push new values into a part without the host re-rendering (`AsyncDirective.setValue`).
4. **Short-circuiting** — returning `noChange` to skip an update.

"Format a list with some conditionals" hits none of these. It's pure value → template, which is exactly what functions are for.

## Rules of thumb

- Pure transformation of inputs to markup → **helper function**.
- Need to interact with the DOM node, hold state, or push async values → **directive**.
- Built-ins like `repeat`, `when`, `map`, `classMap` cover most "smart rendering" cases without writing your own directive.

Stick with the function. If later you discover you need keyed reconciliation for the list, swap `items.map(...)` for Lit's `repeat` directive — still no custom directive needed.

</details>

<details><summary>opus: skill-loaded answer</summary>

Use a **helper function returning `TemplateResult`**. That's almost certainly the right answer for your case.

## Why

A helper function is just:

```ts
import { html, nothing } from 'lit';

export function renderItemList(items: Item[], options?: { showCount?: boolean }) {
  if (items.length === 0) return html`<p>No items</p>`;
  return html`
    ${options?.showCount ? html`<span>${items.length} items</span>` : nothing}
    <ul>
      ${items.map((item) => html`<li>${item.name}</li>`)}
    </ul>
  `;
}
```

Then in each component:

```ts
render() {
  return html`<div>${renderItemList(this.items, { showCount: true })}</div>`;
}
```

This works perfectly because `html` returns a `TemplateResult` value — composable, cacheable by Lit's template system, and efficient. Lit's diffing handles nested templates natively; there's no performance cost to splitting templates across functions.

## When you'd actually need a custom Directive

Custom directives (`extends Directive`) exist for things templates **can't express**:

- **Direct DOM Part access** — you need to read/write the actual attribute, node, or property Part imperatively (e.g., `classMap`, `styleMap`, `ref`)
- **Stateful rendering across renders** — the directive needs to remember something between calls (e.g., `cache`, `repeat`'s key tracking)
- **Async lifecycle** — `AsyncDirective` for things like subscribing to an observable and calling `setValue()` outside the normal render cycle (e.g., `until`, `asyncAppend`)
- **Disconnection callbacks** — cleanup when the directive's part is removed from the DOM

Your case — "format a list with conditional rendering" — needs none of these. It's pure template composition.

## Rule of thumb

| Need | Use |
|------|-----|
| Reusable template fragment | **Helper function returning `TemplateResult`** |
| Conditional/loop rendering | Helper function (or inline `map`/ternary) |
| Imperative DOM manipulation | Custom directive |
| Subscribe to async source | `AsyncDirective` |
| State that persists across renders for the same DOM location | Custom directive |

Custom directives are powerful but add real complexity (Part API, lifecycle, `update` vs `render`, `noChange` vs `nothing`). Don't reach for them when a function call composes templates just as well.

</details>

---

### `reactive-controller-vs-task`

**Prompt**

```
I want to add a persistent WebSocket connection to my Lit component
— open on mount, close on unmount, and re-render the host when a
message arrives. Should I write a ReactiveController or use
@lit/task? What's the difference?
```

**Judge focus:** The better answer recommends a ReactiveController for this case
(long-lived resource with hostConnected / hostDisconnected
lifecycle hooks and requestUpdate to drive re-renders), and
contrasts it with @lit/task which is for request-shaped async
work tied to inputs (fetch-style, with status states).

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly recommend ReactiveController and cover all four rubric criteria, but Answer B is more practical and complete: it includes auto-reconnect logic, proper cleanup (nulling out handlers before close), a public API (send/disconnect/reconnect), and cleaner patterns for accumulating messages. Answer A has a garbled 'mental model' section with a broken ASCII diagram that runs on for thousands of characters, which significantly hurts readability and professionalism. Answer B's contrast table and lifecycle diagram are cleaner and more informative.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends ReactiveController for this scenario | tie |
| mentions hostConnected / hostDisconnected | tie |
| contrasts with Task as request-shaped async | baseline |
| mentions requestUpdate or host re-render | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends ReactiveController for this scenario | ✓ | `ReactiveController` |
| mentions hostConnected / hostDisconnected | ✓ | `hostConnected` |
| contrasts with Task as request-shaped async | ✓ | `@lit/task` |
| mentions requestUpdate or host re-render | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends ReactiveController for this scenario | ✓ | `ReactiveController` |
| mentions hostConnected / hostDisconnected | ✓ | `hostConnected` |
| contrasts with Task as request-shaped async | ✓ | `@lit/task` |
| mentions requestUpdate or host re-render | ✓ | `requestUpdate` |

<details><summary>sonnet: baseline answer</summary>

## ReactiveController vs `@lit/task` for WebSockets

**Short answer: Write a `ReactiveController`.** `@lit/task` is designed for one-shot async operations (like fetch), not persistent connections. Here's why, and how to do it properly.

---

## Why Not `@lit/task`?

```javascript
// ❌ @lit/task is built around a single Promise that resolves/rejects
const task = new Task(this, {
  task: async ([url]) => {
    const ws = new WebSocket(url);
    // Task expects you to return a value — but WebSocket never "completes"
    // You'd have to hack around it with manual Promise chains
    return new Promise((resolve) => {
      ws.onmessage = (e) => resolve(e.data); // Only gets FIRST message, then done
    });
  },
  args: () => [this.url]
});
```

| Concern | `@lit/task` | `ReactiveController` |
|---|---|---|
| Lifecycle hooks | ❌ No `hostConnected`/`hostDisconnected` | ✅ Built-in |
| Persistent connections | ❌ Awkward, fights the API | ✅ Natural fit |
| Multiple events over time | ❌ One promise = one value | ✅ Call `requestUpdate()` anytime |
| Cleanup on unmount | ❌ No teardown hook | ✅ `hostDisconnected()` |
| Reconnection logic | ❌ Very messy | ✅ Clean |

---

## The Right Way: ReactiveController

```javascript
// websocket-controller.js
export class WebSocketController {
  #host;
  #url;
  #ws = null;
  #reconnectTimer = null;
  #intentionalClose = false;

  // Public state the host component can read
  lastMessage = null;
  status = 'disconnected'; // 'connecting' | 'connected' | 'disconnected' | 'error'
  error = null;

  constructor(host, url) {
    this.#host = host;
    this.#url = url;
    // Register with the host — this is what makes it a ReactiveController
    host.addController(this);
  }

  // ── Lifecycle hooks called by Lit automatically ──────────────────────

  hostConnected() {
    this.#connect();
  }

  hostDisconnected() {
    this.#intentionalClose = true;
    this.#cleanup();
  }

  // ── Public API ───────────────────────────────────────────────────────

  send(data) {
    if (this.#ws?.readyState === WebSocket.OPEN) {
      this.#ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    } else {
      console.warn('WebSocket is not open. Current status:', this.status);
    }
  }

  disconnect() {
    this.#intentionalClose = true;
    this.#cleanup();
  }

  reconnect() {
    this.#intentionalClose = false;
    this.#cleanup();
    this.#connect();
  }

  // ── Private internals ────────────────────────────────────────────────

  #connect() {
    this.#intentionalClose = false;
    this.#setStatus('connecting');

    try {
      this.#ws = new WebSocket(this.#url);
    } catch (err) {
      this.#setError(err);
      return;
    }

    this.#ws.onopen = () => {
      this.error = null;
      this.#setStatus('connected');
    };

    this.#ws.onmessage = (event) => {
      // Parse JSON automatically, fall back to raw string
      try {
        this.lastMessage = JSON.parse(event.data);
      } catch {
        this.lastMessage = event.data;
      }
      // This is the key call — tells Lit to re-render the host
      this.#host.requestUpdate();
    };

    this.#ws.onerror = (event) => {
      this.#setError(new Error('WebSocket error'));
    };

    this.#ws.onclose = (event) => {
      this.#setStatus('disconnected');
      // Auto-reconnect unless we closed intentionally
      if (!this.#intentionalClose) {
        this.#scheduleReconnect();
      }
    };
  }

  #cleanup() {
    clearTimeout(this.#reconnectTimer);
    if (this.#ws) {
      // Remove handlers before closing to prevent onclose triggering reconnect
      this.#ws.onopen = null;
      this.#ws.onmessage = null;
      this.#ws.onerror = null;
      this.#ws.onclose = null;
      this.#ws.close();
      this.#ws = null;
    }
  }

  #scheduleReconnect(delay = 3000) {
    this.#reconnectTimer = setTimeout(() => {
      if (!this.#intentionalClose) {
        console.log('Attempting WebSocket reconnect...');
        this.#connect();
      }
    }, delay);
  }

  #setStatus(status) {
    this.status = status;
    this.#host.requestUpdate(); // Re-render on every status change
  }

  #setError(err) {
    this.error = err;
    this.status = 'error';
    this.#host.requestUpdate();
  }
}
```

---

## Using It in a Component

```javascript
// my-chat.js
import { LitElement, html, css } from 'lit';
import { WebSocketController } from './websocket-controller.js';

class MyChat extends LitElement {
  static styles = css`
    .status { font-size: 0.8rem; padding: 4px 8px; border-radius: 4px; }
    .connected    { background: #d4edda; color: #155724; }
    .connecting   { background: #fff3cd; color: #856404; }
    .disconnected { background: #f8d7da; color: #721c24; }
    .error        { background: #f8d7da; color: #721c24; }
    .messages     { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 8px; }
  `;

  // Controller is instantiated once — Lit handles the rest
  #ws = new WebSocketController(this, 'wss://echo.websocket.org');

  #messages = [];

  render() {
    // Read directly from controller — no extra state needed
    const { status, lastMessage, error } = this.#ws;

    // Accumulate messages (you'd normally do this in onmessage callback)
    if (lastMessage && !this.#messages.includes(lastMessage)) {
      this.#messages = [...this.#messages, lastMessage];
    }

    return html`
      <span class="status ${status}">${status}</span>

      ${error ? html`<p class="error">Error: ${error.message}</p>` : ''}

      <div class="messages">
        ${this.#messages.map(msg => html`
          <div class="message">${JSON.stringify(msg)}</div>
        `)}
      </div>

      <div class="controls">
        <input id="input" type="text" placeholder="Type a message..." />
        <button @click=${this.#sendMessage}
                ?disabled=${status !== 'connected'}>
          Send
        </button>
        <button @click=${() => this.#ws.reconnect()}>Reconnect</button>
      </div>
    `;
  }

  #sendMessage() {
    const input = this.shadowRoot.querySelector('#input');
    if (input.value.trim()) {
      this.#ws.send(input.value);
      input.value = '';
    }
  }
}

customElements.define('my-chat', MyChat);
```

---

## Accumulating Messages Cleanly

The example above has a subtle bug (message dedup by reference). Here's the cleaner pattern — keep message history *in the controller*:

```javascript
// In WebSocketController
#messageHistory = [];

get messages() {
  return this.#messageHistory;
}

// In onmessage handler:
this.#ws.onmessage = (event) => {
  const parsed = (() => {
    try { return JSON.parse(event.data); } catch { return event.data; }
  })();

  this.lastMessage = parsed;
  this.#messageHistory = [...this.#messageHistory, parsed]; // immutable update
  this.#host.requestUpdate();
};

// Clear history on reconnect if desired
#connect() {
  this.#messageHistory = [];
  // ...rest of connect
}
```

```javascript
// In component — now trivially simple
render() {
  return html`
    ${this.#ws.messages.map(msg => html`<div>${JSON.stringify(msg)}</div>`)}
  `;
}
```

---

## Key Takeaways

```
ReactiveController lifecycle:
  addController() → hostConnected() → [requestUpdate() × N] → hostDisconnected()
       ↑                  ↑                    ↑                       ↑
  constructor         ws.open()           ws.onmessage()          ws.close()
```

1. **`hostConnected`** = open the socket (not the constructor — the element may not be in the DOM yet)
2. **`hostDisconnected`** = close the socket and cancel reconnect timers
3. **`requestUpdate()`** = the bridge between async WebSocket events and Lit's render cycle
4. **`@lit/task`** is for fetch-style request/response — don't fight it into a persistent connection shape

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Controller vs Task for WebSocket

**Use a Reactive Controller.** `@lit/task` is designed for request/response async (fetch a URL, get a result, done). A WebSocket is an *ongoing resource* — it has its own lifecycle that must be tied to the component's lifecycle, and it emits an unbounded stream of messages over time. That's exactly what reactive controllers exist for.

The decision table from the skill captures this directly:

| Pattern | Use when |
|---|---|
| `Task` | Request → response → done (fetch, DB query) |
| Reactive Controller | Ongoing resource with setup/teardown (timers, observers, **WebSockets**) |

---

## The Reactive Controller

```typescript
// ws-controller.ts
import type { ReactiveController, ReactiveControllerHost } from 'lit';

export class WebSocketController<T = unknown> implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _url: string;
  private _socket: WebSocket | null = null;

  /** Latest parsed message payload — read this in render() */
  lastMessage: T | null = null;
  readyState: number = WebSocket.CLOSED;
  error: Event | null = null;

  constructor(host: ReactiveControllerHost, url: string) {
    this._host = host;
    this._url = url;
    host.addController(this);   // register with the host
  }

  // Called when the host connects to the DOM
  hostConnected() {
    this._open();
  }

  // Called when the host disconnects from the DOM
  hostDisconnected() {
    this._close();
  }

  send(data: string | ArrayBufferLike | Blob) {
    if (this._socket?.readyState === WebSocket.OPEN) {
      this._socket.send(data);
    }
  }

  private _open() {
    this._socket = new WebSocket(this._url);

    this._socket.addEventListener('open', () => {
      this.readyState = WebSocket.OPEN;
      this.error = null;
      this._host.requestUpdate();   // re-render the host
    });

    this._socket.addEventListener('message', (event: MessageEvent) => {
      try {
        this.lastMessage = JSON.parse(event.data) as T;
      } catch {
        this.lastMessage = event.data as T;
      }
      this._host.requestUpdate();   // re-render on every message
    });

    this._socket.addEventListener('error', (event) => {
      this.error = event;
      this.readyState = this._socket?.readyState ?? WebSocket.CLOSED;
      this._host.requestUpdate();
    });

    this._socket.addEventListener('close', () => {
      this.readyState = WebSocket.CLOSED;
      this._host.requestUpdate();
    });
  }

  private _close() {
    this._socket?.close();
    this._socket = null;
  }
}
```

Key points:
- The host type is `ReactiveControllerHost`, not `LitElement` — keeps the controller usable with any compatible host
- `requestUpdate()` is the only way the controller drives re-renders; it never touches the DOM directly
- `_close()` in `hostDisconnected()` guarantees no leaked sockets or ghost message handlers

---

## Using It in a Component

```typescript
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { WebSocketController } from './ws-controller.js';

interface StockTick {
  symbol: string;
  price: number;
}

@customElement('stock-ticker')
export class StockTicker extends LitElement {
  static styles = css`
    :host { display: block; font-family: monospace; }
    .error { color: red; }
    .connecting { color: grey; }
  `;

  // Controller is instantiated once; it self-registers via addController()
  private _ws = new WebSocketController<StockTick>(
    this,
    'wss://example.com/stocks'
  );

  render() {
    const { readyState, lastMessage, error } = this._ws;

    if (error) {
      return html`<p class="error">Connection error.</p>`;
    }

    if (readyState !== WebSocket.OPEN) {
      return html`<p class="connecting">Connecting…</p>`;
    }

    return html`
      <p>Status: connected</p>
      ${lastMessage
        ? html`<p>${lastMessage.symbol}: $${lastMessage.price.toFixed(2)}</p>`
        : html`<p>Waiting for data…</p>`}
      <button @click=${() => this._ws.send(JSON.stringify({ sub: 'AAPL' }))}>
        Subscribe AAPL
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'stock-ticker': StockTicker;
  }
}
```

The component's `render()` is pure — it just reads controller state. All the socket logic lives in the controller.

---

## Why Not Task?

If you tried to model this with `@lit/task`, you'd immediately hit its design assumptions:

```typescript
// ❌ This doesn't work — Task expects a Promise that resolves once
private _ws = new Task(this, {
  task: async ([url]) => {
    const socket = new WebSocket(url);
    // What do you return here? The socket? The first message?
    // Task has no model for "keep running and emit values over time"
  },
  args: () => [this.url],
});
```

Task gives you one `pending → complete | error` cycle per run. A WebSocket needs:
- Persistent state across many messages
- Cleanup tied to component unmount
- The ability to call `send()` imperatively

None of those fit Task's model.

---

## The Mental Model

```
Task:           open → [one result] → close
                ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend ReactiveController and cover the key criteria, but Answer A is more thorough and complete. It provides a more detailed contrast with Task (explaining why Task is wrong for WebSocket — it expects a promise that resolves, not a stream), explicitly mentions all four rubric criteria with greater depth, and includes additional practical guidance like reconnection logic, type safety, and public API design. Answer B is correct but more superficial.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends ReactiveController for this scenario | tie |
| mentions hostConnected / hostDisconnected | tie |
| contrasts with Task as request-shaped async | skill |
| mentions requestUpdate or host re-render | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends ReactiveController for this scenario | ✓ | `ReactiveController` |
| mentions hostConnected / hostDisconnected | ✓ | `hostConnected` |
| contrasts with Task as request-shaped async | ✓ | `@lit/task` |
| mentions requestUpdate or host re-render | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends ReactiveController for this scenario | ✓ | `ReactiveController` |
| mentions hostConnected / hostDisconnected | ✓ | `hostConnected` |
| contrasts with Task as request-shaped async | ✓ | `Task is for request/response (fetch` |
| mentions requestUpdate or host re-render | ✓ | `requestUpdate` |

<details><summary>haiku: baseline answer</summary>

# WebSocket in Lit: ReactiveController vs @lit/task

For a persistent WebSocket connection, **ReactiveController is the better choice**. Here's why:

## ReactiveController (Recommended)

Use this for **stateful, long-lived connections** that need lifecycle management.

```typescript
import { ReactiveController, ReactiveControllerHost } from 'lit';

class WebSocketController implements ReactiveController {
  private ws?: WebSocket;
  private host: ReactiveControllerHost;

  constructor(host: ReactiveControllerHost, private url: string) {
    this.host = host;
    host.addController(this);
  }

  hostConnected() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (event) => {
      this.onMessage(event.data);
      this.host.requestUpdate(); // Re-render on message
    };
  }

  hostDisconnected() {
    this.ws?.close();
  }

  private onMessage(data: string) {
    // Handle message
  }

  send(data: string) {
    this.ws?.send(data);
  }
}
```

**Usage in component:**

```typescript
import { LitElement, html } from 'lit';

class MyComponent extends LitElement {
  private wsController = new WebSocketController(this, 'ws://localhost:8080');

  render() {
    return html`<p>Connected</p>`;
  }
}
```

## @lit/task (Not ideal for this)

`@lit/task` is designed for **async operations with clear start/end points** (like API calls).

```typescript
import { task } from '@lit/task';

class MyComponent extends LitElement {
  private wsTask = new Task(this, {
    task: async () => {
      // ❌ Problem: task() expects a Promise that resolves
      // WebSocket is never "done"
      return new Promise(() => {}); // Never resolves!
    }
  });
}
```

## Key Differences

| Aspect | ReactiveController | @lit/task |
|--------|-------------------|-----------|
| **Lifecycle** | `hostConnected/Disconnected` | Task-based (start/end) |
| **Best for** | Persistent connections | One-off async operations |
| **State management** | Manual | Built-in (pending/complete/error) |
| **Re-render trigger** | `requestUpdate()` | Automatic on completion |

## Complete Example

```typescript
import { LitElement, html } from 'lit';
import { ReactiveController, ReactiveControllerHost } from 'lit';

class WebSocketController implements ReactiveController {
  private ws?: WebSocket;
  private host: ReactiveControllerHost;
  data: string = '';

  constructor(host: ReactiveControllerHost, private url: string) {
    this.host = host;
    host.addController(this);
  }

  hostConnected() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (event) => {
      this.data = event.data;
      this.host.requestUpdate();
    };
    this.ws.onerror = () => console.error('WebSocket error');
  }

  hostDisconnected() {
    this.ws?.close();
  }

  send(message: string) {
    this.ws?.send(message);
  }
}

class MyComponent extends LitElement {
  private ws = new WebSocketController(this, 'ws://localhost:8080');

  render() {
    return html`
      <div>${this.ws.data}</div>
      <button @click=${() => this.ws.send('hello')}>Send</button>
    `;
  }
}
```

**Use ReactiveController** — it's purpose-built for this pattern! 🎯

</details>

<details><summary>haiku: skill-loaded answer</summary>

# WebSocket Connection: ReactiveController vs Task

**Use a ReactiveController.** Task is for request/response (fetch, DB query). WebSocket is an ongoing resource that needs lifecycle-aware setup/teardown and should trigger re-renders on incoming messages.

## Why ReactiveController, Not Task

| Aspect | Task | ReactiveController |
|--------|------|-------------------|
| **Lifecycle** | Runs when args change; completes | Runs once on `hostConnected()`; lives until `hostDisconnected()` |
| **Resource type** | Request/response (fetch, DB) | Ongoing (WebSocket, timer, observer, event listener) |
| **Cleanup** | Automatic (abort signal) | Manual in `hostDisconnected()` |
| **Re-render trigger** | Status change (pending → complete) | Call `host.requestUpdate()` on message |
| **Multiple instances** | One per component | One per component, reusable across many |

A WebSocket stays open for the lifetime of the component. Task would re-run every time its args changed, which is wasteful and wrong for a persistent connection.

## Complete Example

```typescript
import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ReactiveController, ReactiveControllerHost } from 'lit';

// 1. Define the controller
class WebSocketController implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _ws: WebSocket | null = null;
  private _reconnectAttempts = 0;
  private _maxReconnectAttempts = 5;
  private _reconnectDelay = 1000;

  @state() isConnected = false;
  @state() lastMessage: string | null = null;
  @state() error: string | null = null;

  constructor(
    host: ReactiveControllerHost,
    private _url: string,
    private _onMessage?: (data: unknown) => void
  ) {
    this._host = host;
    host.addController(this);
  }

  hostConnected() {
    this._connect();
  }

  hostDisconnected() {
    this._disconnect();
  }

  private _connect() {
    try {
      this._ws = new WebSocket(this._url);

      this._ws.addEventListener('open', () => {
        this.isConnected = true;
        this._reconnectAttempts = 0;
        this._host.requestUpdate();
      });

      this._ws.addEventListener('message', (event) => {
        this.lastMessage = event.data;
        this.error = null;
        this._onMessage?.(JSON.parse(event.data));
        this._host.requestUpdate();
      });

      this._ws.addEventListener('error', () => {
        this.error = 'WebSocket error';
        this._host.requestUpdate();
      });

      this._ws.addEventListener('close', () => {
        this.isConnected = false;
        this._host.requestUpdate();
        this._attemptReconnect();
      });
    } catch (err) {
      this.error = `Failed to connect: ${err}`;
      this._host.requestUpdate();
    }
  }

  private _attemptReconnect() {
    if (this._reconnectAttempts < this._maxReconnectAttempts) {
      this._reconnectAttempts++;
      const delay = this._reconnectDelay * Math.pow(2, this._reconnectAttempts - 1);
      setTimeout(() => this._connect(), delay);
    }
  }

  private _disconnect() {
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }

  send(data: unknown) {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(data));
    }
  }

  getStatus() {
    return {
      isConnected: this.isConnected,
      lastMessage: this.lastMessage,
      error: this.error,
    };
  }
}

// 2. Use the controller in your component
@customElement('chat-app')
export class ChatApp extends LitElement {
  private _ws = new WebSocketController(
    this,
    'wss://echo.websocket.org',
    (data) => {
      // Optional callback when message arrives
      console.log('Received:', data);
    }
  );

  @state() messages: string[] = [];

  render() {
    const { isConnected, error } = this._ws.getStatus();

    return html`
      <div>
        <p>Status: ${isConnected ? '🟢 Connected' : '🔴 Disconnected'}</p>
        ${error ? html`<p style="color: red">${error}</p>` : ''}
        <button @click=${() => this._sendMessage()}>Send</button>
        <ul>
          ${this.messages.map((msg) => html`<li>${msg}</li>`)}
        </ul>
      </div>
    `;
  }

  private _sendMessage() {
    this._ws.send({ text: 'Hello' });
  }
}
```

## Key Points

1. **`hostConnected()` / `hostDisconnected()`** — Lit calls these automatically. Open the socket on connect, close on disconnect.

2. **`requestUpdate()` on message** — When a message arrives, call `this._host.requestUpdate()` to trigger a re-render. The component sees the new state.

3. **Expose a public API** — `send()`, `getStatus()` let the component interact with the WebSocket without exposing internals.

4. **Type the host as `ReactiveControllerHost`** — Not `LitElement`. This keeps the controller framework-agnostic and reusable.

5. **Cleanup in `hostDisconnected()`** — Close the socket, cancel timers, remove listeners. Prevents memory leaks.

6. **Reconnection logic** — Exponential backoff with a max attempt limit. Adjust `_maxReconnectAttempts` and `_reconnectDelay` as needed.

## Accessing Controller State in the Component

If you want the component to read controller state directly (not via a callback), expose it as public fields:

```typescript
class WebSocketController implements ReactiveController {
  isConnected = false;
  lastMessage: string | null = null;
  error: string | null = null;
  // ...
}

// In the component:
render() {
  return html`
    <p>Status: ${this._ws.isConnected ? '🟢' : '🔴'}</p>
    ${this._ws.error ? html`<p>${this._ws.error}</p>` : ''}
  `;
}
```

The controller calls `this._host.requestUpdate()` whenever state changes, so the component re-renders automatically.

## When to Use Task Instead

Use Task **only** if you're fetching data once per component lifecycle or when args change:

```typescript
// ❌ Wrong for WebSocket
private _task = new Task(this, {
  task: async ({ signal }) => {
    const ws = new WebSocket('wss://...');
    // Task completes when the promise resolves
    // But WebSocket never resolves — it's a stream
  },
});
```

Task is designed for async operations that have a clear end state (pending → complete/error). WebSocket is a stream that lives for the component's lifetime.

---

**Summary:** ReactiveController for WebSocket, timers, observers, event listeners, and other ongoing resources. Task for fetch, DB queries, and other request/response patterns.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend ReactiveController and cover all four rubric criteria well. Answer A is more comprehensive with a richer comparison table, additional gotchas section, and more complete status tracking in the controller implementation. However, Answer B is cleaner and more concise while still hitting every criterion, and its 'when you'd combine the two' section adds a nice nuance. Answer A edges out B due to the explicit comparison table and the gotchas section that add practical depth, plus slightly more thorough coverage of the contrast with Task.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends ReactiveController for this scenario | tie |
| mentions hostConnected / hostDisconnected | tie |
| contrasts with Task as request-shaped async | skill |
| mentions requestUpdate or host re-render | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends ReactiveController for this scenario | ✓ | `ReactiveController` |
| mentions hostConnected / hostDisconnected | ✓ | `hostConnected` |
| contrasts with Task as request-shaped async | ✓ | `@lit/task` |
| mentions requestUpdate or host re-render | ✓ | `requestUpdate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends ReactiveController for this scenario | ✓ | `ReactiveController` |
| mentions hostConnected / hostDisconnected | ✓ | `hostConnected` |
| contrasts with Task as request-shaped async | ✓ | `@lit/task` |
| mentions requestUpdate or host re-render | ✓ | `requestUpdate` |

<details><summary>opus: baseline answer</summary>

# ReactiveController is the right choice here

For a persistent WebSocket lifecycle tied to a host element, use a **ReactiveController**. `@lit/task` is for something different.

## The distinction

**`Task`** models an *async operation* with discrete states (`initial` → `pending` → `complete`/`error`) that runs in response to changing inputs. It's built around a single promise that resolves once. Think: "fetch this user when the `userId` property changes."

**`ReactiveController`** is a reusable bundle of state + lifecycle hooks (`hostConnected`, `hostDisconnected`, `hostUpdate`, `hostUpdated`) attached to a host. It's the right primitive for anything stream-like, subscription-based, or tied to mount/unmount — exactly your case.

A WebSocket isn't a one-shot promise; it's a long-lived connection emitting many messages. Forcing that into `Task` would be awkward.

## Example controller

```ts
import { ReactiveController, ReactiveControllerHost } from 'lit';

export class WebSocketController implements ReactiveController {
  host: ReactiveControllerHost;
  private url: string;
  private ws?: WebSocket;
  lastMessage?: unknown;

  constructor(host: ReactiveControllerHost, url: string) {
    (this.host = host).addController(this);
    this.url = url;
  }

  hostConnected() {
    this.ws = new WebSocket(this.url);
    this.ws.addEventListener('message', this.onMessage);
  }

  hostDisconnected() {
    this.ws?.removeEventListener('message', this.onMessage);
    this.ws?.close();
    this.ws = undefined;
  }

  send(data: string) {
    this.ws?.send(data);
  }

  private onMessage = (e: MessageEvent) => {
    this.lastMessage = e.data;
    this.host.requestUpdate(); // triggers re-render
  };
}
```

## Using it

```ts
@customElement('my-element')
class MyElement extends LitElement {
  private socket = new WebSocketController(this, 'wss://example.com');

  render() {
    return html`<p>Last: ${this.socket.lastMessage ?? '—'}</p>`;
  }
}
```

`addController(this)` wires it up; `host.requestUpdate()` is the bridge that schedules a re-render when a message arrives. Open/close happen automatically with `hostConnected`/`hostDisconnected`, which align with the element being added to / removed from the DOM.

## When you'd combine the two

If a particular message triggers a one-shot async operation (e.g., a request/response RPC over the socket), that *inner* operation could be modeled with `Task`. But the connection itself belongs in a controller.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Use a ReactiveController, not Task

Short answer: **write a `ReactiveController`**. `@lit/task` is the wrong tool here.

## Why not Task?

`@lit/task` is designed for **request/response async** — you give it args, it runs an async function, you get back `{ pending, complete, error }`. It's modeled around a single async operation that resolves (or errors) once per arg change. Cancellation works via `AbortSignal` tied to arg changes.

A WebSocket is the opposite shape:
- It's an **ongoing resource**, not a one-shot promise
- It pushes **many messages over time**, not a single result
- Its lifecycle is tied to **mount/unmount**, not to argument changes
- You need explicit **setup and teardown** symmetry

Trying to force this into Task means fighting the abstraction the whole way.

## Why a ReactiveController fits

`ReactiveController` exists exactly for this: lifecycle-aware resources that need `hostConnected` / `hostDisconnected` symmetry, and that call `host.requestUpdate()` when their internal state changes.

```ts
import type { ReactiveController, ReactiveControllerHost } from 'lit';

export class WebSocketController<T = unknown> implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _url: string;
  private _socket?: WebSocket;

  message?: T;
  status: 'connecting' | 'open' | 'closed' | 'error' = 'closed';

  constructor(host: ReactiveControllerHost, url: string) {
    this._host = host;
    this._url = url;
    host.addController(this);
  }

  hostConnected() {
    this.status = 'connecting';
    this._socket = new WebSocket(this._url);

    this._socket.addEventListener('open', () => {
      this.status = 'open';
      this._host.requestUpdate();
    });

    this._socket.addEventListener('message', (e) => {
      this.message = JSON.parse(e.data);
      this._host.requestUpdate();
    });

    this._socket.addEventListener('close', () => {
      this.status = 'closed';
      this._host.requestUpdate();
    });

    this._socket.addEventListener('error', () => {
      this.status = 'error';
      this._host.requestUpdate();
    });
  }

  hostDisconnected() {
    this._socket?.close();
    this._socket = undefined;
  }

  send(data: unknown) {
    this._socket?.send(JSON.stringify(data));
  }
}
```

Usage:

```ts
@customElement('live-feed')
export class LiveFeed extends LitElement {
  private _ws = new WebSocketController<{ text: string }>(
    this,
    'wss://example.com/feed'
  );

  render() {
    if (this._ws.status !== 'open') {
      return html`<p>Status: ${this._ws.status}</p>`;
    }
    return html`<p>Latest: ${this._ws.message?.text ?? '(waiting…)'}</p>`;
  }
}
```

## The mental model

| | Task | ReactiveController |
|---|---|---|
| Shape | one-shot async (request → response) | ongoing resource |
| Lifecycle trigger | argument changes | `hostConnected`/`hostDisconnected` |
| Cancellation | `AbortSignal` via args | manual cleanup in `hostDisconnected` |
| Re-render trigger | status transitions | you call `host.requestUpdate()` |
| Examples | `fetch`, DB query, expensive computation | WebSocket, timer, ResizeObserver, mouse tracker |

A useful rule: **if the work has a single resolution, use Task. If it has a connection that lives across many updates, use a controller.**

## A couple of gotchas

- **Reconnection on URL change.** The example above only opens the socket on mount. If `url` is a reactive property that can change at runtime, add a `hostUpdate()` hook that compares the new URL and reconnects — or expose a `reconnect(newUrl)` method the host calls explicitly.
- **`hostConnected` runs on every connection.** If the host element is moved in the DOM, it disconnects and reconnects. Your controller will tear down and re-open the socket — which is usually what you want, but be aware.
- **Don't forget `requestUpdate()`.** The controller's fields aren't reactive properties; Lit doesn't know they changed unless you say so.

For more on the controller interface, lifecycle integration, and composition patterns, see `references/reactive-controllers.md`.

</details>

---

### `context-subscribe-true`

**Prompt**

```
I'm using @lit/context to share a theme object from a top-level
provider. The provider's value changes at runtime when the user
toggles dark mode, but the consumer components don't update.
The initial value is read fine, just not subsequent changes.
What's missing?
```

**Judge focus:** The better answer pinpoints `subscribe: true` on the consumer
side as the missing piece — without it, @lit/context fetches the
value once and never re-subscribes to provider updates. It may
also mention setting the provider's value via setValue (or
re-assigning the @provide property) so the change actually fires.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify `subscribe: true` as the missing piece and explain the one-shot default behavior. Answer A is slightly more focused and better structured, leading with the core fix immediately and providing a cleaner explanation of why each piece matters. Answer B initially misdirects by suggesting the root cause is about replacing vs mutating the context value rather than leading with `subscribe: true`, which is the primary missing piece per the rubric.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies subscribe option | skill |
| explains default is one-shot / no resubscription | tie |
| mentions @consume or ContextConsumer | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies subscribe option | ✓ | `subscribe: true` |
| explains default is one-shot / no resubscription | ✓ | `one-shot` |
| mentions @consume or ContextConsumer | ✓ | `@consume` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies subscribe option | ✓ | `subscribe: true` |
| explains default is one-shot / no resubscription | ✓ | `one-shot` |
| mentions @consume or ContextConsumer | ✓ | `@consume` |

<details><summary>sonnet: baseline answer</summary>

## The Problem: Context Value Updates Not Propagating

This is a very common `@lit/context` gotcha. The issue is almost certainly that you're **replacing the context value object** rather than mutating it, or you're not calling the right method to notify consumers of changes.

---

## Root Cause

`@lit/context` consumers only re-render when the provider **explicitly notifies them**. This happens automatically *only* when you use the `@provide` decorator correctly — specifically, the value must be set through the decorated property's **setter**, not by mutating a nested property.

### ❌ Common Mistakes

```javascript
// MISTAKE 1: Mutating the object directly — setter is never called,
// consumers are never notified
this.theme.mode = 'dark';
this.theme.colors.background = '#000';

// MISTAKE 2: Reassigning but on a nested ref the decorator doesn't watch
this.theme = { ...this.theme, mode: 'dark' }; // OK only if wired up right
```

```javascript
// MISTAKE 3: Using ContextProvider imperatively but forgetting to
// set .value through the instance
this._provider = new ContextProvider(this, { context: themeContext });
this._provider.value.mode = 'dark'; // ❌ mutation, no notification
```

---

## The Fix

### Option A — Declarative `@provide` (Recommended)

Always **reassign the whole property** so the decorated setter fires:

```javascript
import { LitElement, html } from 'lit';
import { provide } from '@lit/context';
import { themeContext } from './theme-context.js';

class ThemeProvider extends LitElement {

  @provide({ context: themeContext })
  theme = { mode: 'light', colors: { bg: '#fff', fg: '#000' } };

  toggleDarkMode() {
    // ✅ Reassign the property — triggers the @provide setter,
    //    which calls setValue() on all registered consumers
    this.theme = {
      ...this.theme,
      mode: 'dark',
      colors: { bg: '#111', fg: '#eee' },
    };
  }

  render() {
    return html`
      <button @click=${this.toggleDarkMode}>Toggle</button>
      <slot></slot>
    `;
  }
}
```

---

### Option B — Imperative `ContextProvider`

If you're using the class directly, set `.value` on the **provider instance** (not the object it holds):

```javascript
import { ContextProvider } from '@lit/context';
import { themeContext } from './theme-context.js';

class ThemeProvider extends LitElement {

  connectedCallback() {
    super.connectedCallback();
    this._provider = new ContextProvider(this, {
      context: themeContext,
      initialValue: { mode: 'light', colors: { bg: '#fff', fg: '#000' } },
    });
  }

  toggleDarkMode() {
    // ✅ Set through the provider instance's .value setter —
    //    this internally calls updateObservers() for all consumers
    this._provider.value = {
      ...this._provider.value,
      mode: 'dark',
      colors: { bg: '#111', fg: '#eee' },
    };
  }
}
```

---

### Consumer Side — Ensure `subscribe: true`

The consumer must opt into updates, otherwise it only reads the value **once**:

```javascript
import { LitElement, html } from 'lit';
import { consume } from '@lit/context';
import { themeContext } from './theme-context.js';

class ThemedButton extends LitElement {

  @consume({ context: themeContext, subscribe: true }) // ✅ subscribe!
  theme;

  render() {
    return html`
      <button style="background:${this.theme.colors.bg}">
        Click me
      </button>
    `;
  }
}
```

> Without `subscribe: true`, the consumer fires a one-shot context request and **never listens for updates**.

---

## Summary Checklist

| Check | Why it matters |
|---|---|
| Provider **reassigns** the property (not mutates) | Triggers the `@provide` setter which notifies consumers |
| Imperative users set `provider.value = ...` | Same reason — uses the notifying setter |
| Consumer has `subscribe: true` | Without it, only the initial value is ever received |
| Context object identity is stable where needed | Avoid unnecessary re-renders by not recreating if nothing changed |

The single most common fix is adding **`subscribe: true`** to `@consume` — that alone solves the problem in the majority of cases.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The most common cause is a missing `subscribe: true` on the `@consume` decorator. Without it, `@lit/context` does a one-shot lookup at connect time and never listens for updates.

## The Fix

**Consumer — add `subscribe: true`**

```ts
import { consume } from '@lit/context';
import { themeContext, type Theme } from './theme-context.js';

@customElement('my-consumer')
class MyConsumer extends LitElement {
  @consume({ context: themeContext, subscribe: true }) // ← required for updates
  @property({ attribute: false })
  theme?: Theme;

  render() {
    return html`
      <div class=${this.theme?.mode ?? 'light'}>...</div>
    `;
  }
}
```

**Provider — value must be reassigned, not mutated**

```ts
import { provide } from '@lit/context';
import { themeContext, type Theme } from './theme-context.js';

@customElement('my-provider')
class MyProvider extends LitElement {
  @provide({ context: themeContext })
  @property({ attribute: false })
  theme: Theme = { mode: 'light', accent: '#0057b8' };

  toggleDarkMode() {
    // ✅ New reference — context notifies all subscribers
    this.theme = { ...this.theme, mode: 'dark' };

    // ❌ In-place mutation — subscribers never notified
    // this.theme.mode = 'dark';
  }
}
```

**Shared context definition**

```ts
// theme-context.ts
import { createContext } from '@lit/context';

export interface Theme {
  mode: 'light' | 'dark';
  accent: string;
}

// Symbol key guarantees uniqueness across module reloads
export const themeContext = createContext<Theme>(Symbol('theme'));
```

---

## Why Each Piece Matters

| Requirement | What breaks without it |
|---|---|
| `subscribe: true` on `@consume` | One-shot lookup only; consumer never hears about updates |
| New object reference on the provider | `@lit/context` compares by reference; mutation is invisible |
| `@property({ attribute: false })` on both sides | Lit won't schedule a re-render when the context value arrives |
| `Symbol` key in `createContext` | String keys can collide across packages or module reloads |

---

## If Consumers Still Don't Update After This

**Consumers connect before the provider renders** — this is the lazy-loading / dynamic-rendering problem. Add `ContextRoot` to your app shell once:

```ts
import { ContextRoot } from '@lit/context';

// In your app shell's constructor or connectedCallback
const root = new ContextRoot();
root.attach(document.body); // intercepts requests that find no provider yet
```

Without `ContextRoot`, a consumer that fires its context request event before the provider element exists in the DOM gets no response and stays on the default value permanently.

**Check the provider is actually an ancestor.** Context travels up the DOM tree via events. If the provider and consumer are siblings, or the consumer is outside the provider's subtree, the request never reaches it.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies `subscribe: true` on the `@consume` decorator as the primary missing piece, which is exactly what the question asks about. Answer A focuses almost entirely on `setValue()` on the provider side and never mentions `subscribe: true`, missing the core issue entirely. Answer B also explains the default one-shot behavior and demonstrates proper use of `@consume` with the subscribe option.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies subscribe option | skill |
| explains default is one-shot / no resubscription | skill |
| mentions @consume or ContextConsumer | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies subscribe option | ✗ | |
| explains default is one-shot / no resubscription | ✗ | |
| mentions @consume or ContextConsumer | ✓ | `@consume` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies subscribe option | ✓ | `subscribe: true` |
| explains default is one-shot / no resubscription | ✗ | |
| mentions @consume or ContextConsumer | ✓ | `@consume` |

<details><summary>haiku: baseline answer</summary>

# The Issue

When you update the context value in the provider, you need to **explicitly notify consumers** that the value has changed. Simply reassigning the value won't trigger updates.

# Solution

Use the **`ContextProvider.setValue()`** method to notify all consumers:

```typescript
import { ContextProvider } from '@lit/context';
import { LitElement, html } from 'lit';
import { property } from 'lit/decorators.js';
import { themeContext } from './theme-context.js';

export class ThemeProvider extends LitElement {
  @property({ attribute: false })
  theme = { mode: 'light' };

  private contextProvider = new ContextProvider(this, {
    context: themeContext,
    initialValue: this.theme,
  });

  toggleDarkMode() {
    this.theme = { mode: this.theme.mode === 'light' ? 'dark' : 'light' };
    
    // ✅ Notify consumers of the change
    this.contextProvider.setValue(this.theme);
  }

  render() {
    return html`
      <button @click=${this.toggleDarkMode}>Toggle Dark Mode</button>
      <slot></slot>
    `;
  }
}
```

# Key Points

- **`setValue()`** is required to trigger reactivity in consumers
- Simply mutating or reassigning the value won't work
- Consumers using `@consume(themeContext)` will automatically re-render when `setValue()` is called

# Alternative: Reactive Property Pattern

If you want automatic updates, make the context value reactive:

```typescript
@property({ attribute: false })
set theme(value) {
  this._theme = value;
  this.contextProvider.setValue(value);
}
get theme() {
  return this._theme;
}
private _theme = { mode: 'light' };
```

This way, any property change automatically notifies consumers.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Missing `subscribe: true` on `@consume`

The issue is that your consumer components are **not subscribing to context updates**. By default, `@consume` reads the context value once at connection time and never listens for changes.

## The Fix

Add `subscribe: true` to every `@consume` decorator:

```ts
import { consume } from '@lit/context';
import { themeContext } from './theme-context.js';

@customElement('my-component')
export class MyComponent extends LitElement {
  @consume({ context: themeContext, subscribe: true })
  @property({ attribute: false })
  theme?: Theme;

  render() {
    return html`<div class="theme-${this.theme?.mode}">...</div>`;
  }
}
```

## Why This Happens

- **Without `subscribe: true`**: The consumer reads the context value once when it connects to the DOM. If the provider's value changes later, the consumer never hears about it.
- **With `subscribe: true`**: The consumer registers itself as a listener. When the provider calls `this.requestUpdate()` after changing its value, all subscribed consumers are notified and re-render.

## Complete Example

**Provider:**
```ts
import { provide } from '@lit/context';
import { themeContext } from './theme-context.js';

@customElement('app-shell')
export class AppShell extends LitElement {
  @provide({ context: themeContext })
  @property({ attribute: false })
  theme: Theme = { mode: 'light' };

  toggleDarkMode() {
    this.theme = { ...this.theme, mode: this.theme.mode === 'light' ? 'dark' : 'light' };
    // requestUpdate() is automatic after @property assignment
  }

  render() {
    return html`
      <button @click=${this.toggleDarkMode}>Toggle Dark Mode</button>
      <my-component></my-component>
    `;
  }
}
```

**Consumer:**
```ts
@customElement('my-component')
export class MyComponent extends LitElement {
  @consume({ context: themeContext, subscribe: true })
  @property({ attribute: false })
  theme?: Theme;

  render() {
    return html`<p>Current mode: ${this.theme?.mode}</p>`;
  }
}
```

**Context definition:**
```ts
import { createContext } from '@lit/context';

export interface Theme {
  mode: 'light' | 'dark';
}

export const themeContext = createContext<Theme>(Symbol('theme'));
```

## When to Use `subscribe: true`

| Scenario | Use `subscribe` |
|----------|-----------------|
| Value rarely or never changes (e.g., app config, feature flags) | `false` (default) — saves memory |
| Value changes at runtime (e.g., theme, user, locale) | `true` — consumers stay in sync |
| Value changes frequently AND you need fine-grained updates | Consider `@lit-labs/signals` instead — avoids re-firing all subscribers on every change |

See [context.md](references/context.md) for nested providers, `ContextRoot`, and context vs signals guidance.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly identify `subscribe: true` as the missing piece and explain the one-shot default behavior. Answer A is more comprehensive with a clear checklist, code examples for both consumer and provider sides, and explicit coverage of the `ContextProvider.setValue()` API. Answer B adds a useful tip about `ContextRoot` for late-mounting consumers but contains a slightly inaccurate claim that `@property({ attribute: false })` is 'required' and that 'without it, Lit tries to reflect to an attribute and the context wiring breaks' — this overstates the issue. Answer A's structured format and accuracy across all rubric criteria make it the stronger response.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies subscribe option | tie |
| explains default is one-shot / no resubscription | tie |
| mentions @consume or ContextConsumer | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies subscribe option | ✓ | `subscribe: true` |
| explains default is one-shot / no resubscription | ✗ | |
| mentions @consume or ContextConsumer | ✓ | `@consume` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies subscribe option | ✓ | `subscribe: true` |
| explains default is one-shot / no resubscription | ✗ | |
| mentions @consume or ContextConsumer | ✓ | `@consume` |

<details><summary>opus: baseline answer</summary>

# The Missing Piece: `subscribe: true`

By default, `@lit/context` consumers only read the value **once** when they connect. To receive updates when the provider's value changes, you need to opt into subscription.

## Consumer side

```ts
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { themeContext, Theme } from './theme-context.js';

@customElement('my-button')
export class MyButton extends LitElement {
  @consume({ context: themeContext, subscribe: true })
  @property({ attribute: false })
  theme!: Theme;

  render() {
    return html`<button style="background:${this.theme.bg}">Click</button>`;
  }
}
```

The two important bits:

1. **`subscribe: true`** – tells the context protocol to keep the callback alive so the consumer is notified on every change.
2. **`@property({ attribute: false })`** – ensures Lit treats the field as reactive, so assignment from the context triggers a re-render.

## Provider side

You also need to make sure the provider actually pushes a *new value*. Mutating the existing object will not notify subscribers — the provider compares by reference (or whatever your custom equality is).

```ts
import { provide } from '@lit/context';

@customElement('app-root')
export class AppRoot extends LitElement {
  @provide({ context: themeContext })
  @property({ attribute: false })
  theme: Theme = lightTheme;

  toggleDark() {
    // ❌ this won't notify consumers
    // this.theme.bg = '#000';

    // ✅ assign a new object
    this.theme = this.theme === lightTheme ? darkTheme : lightTheme;
  }
}
```

If you're using a `ContextProvider` controller directly instead of the decorator, call `setValue` with the new object:

```ts
this.themeProvider.setValue({ ...this.theme, mode: 'dark' });
```

## Summary checklist

- [ ] Consumer uses `subscribe: true`
- [ ] Consumer field is reactive (`@property` / `@state`)
- [ ] Provider assigns a **new** object/value rather than mutating in place
- [ ] If using `ContextProvider` directly, call `setValue(...)` (not just field mutation)

Nine times out of ten with this symptom, it's the missing `subscribe: true`.

</details>

<details><summary>opus: skill-loaded answer</summary>

You need `subscribe: true` on the consumer:

```ts
@consume({ context: themeContext, subscribe: true })
@property({ attribute: false })
theme!: Theme;
```

Without `subscribe: true`, the consumer reads the context value once (on connect) and never re-reads it. With `subscribe: true`, the consumer registers with the provider and gets re-notified whenever the provider's value changes — which then triggers a re-render.

A couple of related things worth checking while you're in there:

1. **Set a new reference on the provider, don't mutate.** If you're doing `this.theme.mode = 'dark'`, the provider sees the same object reference and won't notify subscribers. Do `this.theme = { ...this.theme, mode: 'dark' }` instead.

2. **`@property({ attribute: false })` on the consumer field is required** (which you have). Without it, Lit tries to reflect to an attribute and the context wiring breaks.

3. **If consumers might mount before the provider** (lazy loading, dynamic rendering), add `ContextRoot` at the app shell — it buffers context requests until a provider appears.

See [references/context.md](references/context.md) for the full pitfall list. If the theme changes very frequently and you want to avoid re-rendering the whole subtree on every toggle, that reference also covers wrapping a signal in context for fine-grained updates.

</details>

---

### `simplest-render-html`

**Prompt**

```
Inside my Lit component's render() method, I want to insert some
user-controlled HTML I just received from an API as a string.
What's the simplest way to render it?
```

**Judge focus:** The naive answer reaches for innerHTML or unsafeHTML. The right
answer either uses the unsafeHTML directive WITH a strong warning
about XSS and sanitization, or refuses the bare string injection
and recommends parsing into a structured form first. innerHTML
inside Lit defeats the templating system entirely.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend unsafeHTML with XSS warnings and DOMPurify, but Answer B is slightly superior in depth and nuance. It explicitly explains why Lit's html template escapes strings by default (making unsafeHTML's purpose clearer), recommends server-side sanitization as the primary defense, mentions the native Sanitizer API as an alternative, and adds a nuanced caveat about when sanitization might be skippable. Answer A is solid but less comprehensive in its security guidance.

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

<details><summary>sonnet: baseline answer</summary>

## Rendering Raw HTML in Lit

In Lit, you can use the **`unsafeHTML`** directive from `lit/directives/unsafe-html.js` to render a raw HTML string.

### Example

```javascript
import { LitElement, html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class MyElement extends LitElement {
  static properties = {
    apiContent: { type: String },
  };

  render() {
    return html`
      <div>
        ${unsafeHTML(this.apiContent)}
      </div>
    `;
  }
}

customElements.define('my-element', MyElement);
```

---

### ⚠️ Security Warning

The directive is called **`unsafe`** HTML for a reason. Since the content comes from an API and is **user-controlled**, you **must sanitize it first** to prevent **XSS (Cross-Site Scripting) attacks**.

Use a library like [**DOMPurify**](https://github.com/cure53/DOMPurify) before rendering:

```javascript
import DOMPurify from 'dompurify';

render() {
  const sanitized = DOMPurify.sanitize(this.apiContent);
  return html`
    <div>
      ${unsafeHTML(sanitized)}
    </div>
  `;
}
```

---

### Summary

| Approach | Safe? |
|---|---|
| `unsafeHTML(rawString)` | ❌ Not without sanitization |
| `unsafeHTML(DOMPurify.sanitize(rawString))` | ✅ Yes |

Never skip sanitization when the HTML originates from user input or external APIs.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Rendering Raw HTML in Lit

Use the `unsafeHTML` directive from `lit/directives/unsafe-html.js`:

```typescript
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

@customElement('my-article')
export class MyArticle extends LitElement {
  @state() private _content = '';

  async fetchContent() {
    const res = await fetch('/api/content');
    this._content = await res.text();
  }

  render() {
    return html`<div>${unsafeHTML(this._content)}</div>`;
  }
}
```

The `html` tagged template escapes interpolated strings by default — `unsafeHTML` bypasses that to inject raw markup.

---

## ⚠️ Security Warning — Read Before Using

The directive is named **unsafe** for a reason. Injecting user-controlled HTML directly creates an **XSS vulnerability**. If the string contains `<script>` tags or event handler attributes (`onclick`, `onerror`, etc.), they will execute.

**Sanitize the string on the server before it reaches the API response.** If you need client-side sanitization as a second layer, use the [Sanitizer API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Sanitizer_API) (where available) or a library like [DOMPurify](https://github.com/cure53/DOMPurify):

```typescript
import DOMPurify from 'dompurify';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

render() {
  const clean = DOMPurify.sanitize(this._content);
  return html`<div>${unsafeHTML(clean)}</div>`;
}
```

**Only skip sanitization if the HTML is generated entirely by your own trusted backend and never includes user-supplied input.**

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer B correctly identifies unsafeHTML as the Lit-idiomatic solution while providing a strong XSS warning and recommending DOMPurify sanitization. Answer A's 'safe approach' of using innerHTML in updated() is actually worse — it defeats Lit's templating system entirely, which the rubric explicitly flags as problematic, and its claim that 'innerHTML is safe when you control the assignment' is misleading for user-controlled API content. Answer B hits all three rubric criteria: warns about XSS, mentions unsafeHTML with proper context, and while it doesn't avoid recommending innerHTML entirely, it uses it only as part of a sanitization pattern rather than as the primary approach.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| warns about XSS / sanitization | baseline |
| avoids recommending raw innerHTML | baseline |
| mentions unsafeHTML directive (if recommending it) | baseline |

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

<details><summary>haiku: baseline answer</summary>

# Rendering User-Controlled HTML in Lit

The simplest way is to use the **`unsafeHTML`** directive:

```javascript
import { LitElement, html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class MyComponent extends LitElement {
  render() {
    return html`
      <div>${unsafeHTML(this.apiContent)}</div>
    `;
  }
}
```

## ⚠️ Important Security Warning

The name `unsafeHTML` is intentional—it's **unsafe** because it bypasses Lit's built-in XSS protections. Only use this if:

1. **You trust the source completely** (e.g., your own backend)
2. **You've sanitized the HTML** on the server side

## Safer Alternative: Sanitize First

If the HTML comes from untrusted sources, sanitize it before rendering:

```javascript
import DOMPurify from 'dompurify';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

render() {
  const cleanHTML = DOMPurify.sanitize(this.apiContent);
  return html`<div>${unsafeHTML(cleanHTML)}</div>`;
}
```

## Best Practice

If possible, **avoid rendering raw HTML entirely**:
- Parse the API response into structured data
- Use Lit templates to render components instead
- This is safer and more maintainable

Only use `unsafeHTML` when you have no other choice and can guarantee the content is safe.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Rendering User-Controlled HTML in Lit

**Do not use `unsafeHTML()`** for user-controlled content. It creates an XSS vulnerability.

## The Safe Approach: Use a `<div>` with `innerHTML`

The simplest safe way is to render a container element and set its `innerHTML` after the component updates:

```typescript
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('my-component')
export class MyComponent extends LitElement {
  @property() userContent = '';

  render() {
    return html`<div id="content"></div>`;
  }

  updated() {
    const container = this.shadowRoot?.querySelector('#content');
    if (container) {
      container.innerHTML = this.userContent;
    }
  }
}
```

**Why this works:**
- `innerHTML` is safe when you control the assignment (not user input directly in the template)
- `updated()` runs after the DOM is rendered, so the element exists
- The content is inserted into Shadow DOM, isolated from the rest of your page

## If You Must Sanitize First

If the API content might contain malicious scripts, sanitize it before assignment:

```typescript
import DOMPurify from 'dompurify';

updated() {
  const container = this.shadowRoot?.querySelector('#content');
  if (container) {
    container.innerHTML = DOMPurify.sanitize(this.userContent);
  }
}
```

Install: `npm i dompurify`

## Why Not `unsafeHTML()`?

```typescript
// ❌ DO NOT DO THIS
render() {
  return html`${unsafeHTML(this.userContent)}`;
}
```

`unsafeHTML()` bypasses Lit's escaping entirely. If `userContent` comes from an untrusted API, an attacker can inject `<script>` tags or event handlers. It's only safe for content you control (e.g., your own markdown renderer output).

## Summary

| Scenario | Approach |
|----------|----------|
| User-controlled HTML from API | `innerHTML` in `updated()` |
| User-controlled HTML + need sanitization | `innerHTML` + `DOMPurify` in `updated()` |
| Your own generated HTML (trusted) | `unsafeHTML()` in `render()` |
| Plain text from user | Regular property binding (safe by default) |

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers cover all three rubric criteria well: they warn about XSS/sanitization, avoid recommending raw innerHTML, and mention the unsafeHTML directive with appropriate caveats. Answer A is more comprehensive with its decision tree and stronger framing of the safe default first, while Answer B adds a useful note about Shadow DOM not protecting against XSS. Neither has a clear advantage across all criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| warns about XSS / sanitization | tie |
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

<details><summary>opus: baseline answer</summary>

# Rendering HTML Strings in Lit

The simplest way is to use Lit's `unsafeHTML` directive:

```js
import { LitElement, html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class MyComponent extends LitElement {
  render() {
    return html`<div>${unsafeHTML(this.apiHtml)}</div>`;
  }
}
```

## ⚠️ Important Security Warning

You said the HTML is **user-controlled**, which makes this dangerous. The directive is literally called `unsafeHTML` for a reason — it will execute any `<script>` tags, event handlers (`onclick`, `onerror`, etc.), and other XSS vectors contained in the string.

**Don't use `unsafeHTML` directly with user-controlled content.** You should sanitize it first. The standard choice is [DOMPurify](https://github.com/cure53/DOMPurify):

```js
import { LitElement, html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import DOMPurify from 'dompurify';

class MyComponent extends LitElement {
  render() {
    const clean = DOMPurify.sanitize(this.apiHtml);
    return html`<div>${unsafeHTML(clean)}</div>`;
  }
}
```

### A note about Shadow DOM

Lit components use Shadow DOM by default, which provides some isolation (styles and DOM are encapsulated), but it does **not** protect against XSS — scripts injected into shadow roots still execute with full page privileges. So sanitization is still required.

### Alternatives to consider

- If the API returns structured data (e.g., Markdown or JSON), render it through a parser (`marked` + DOMPurify, or build the template from data) instead of injecting raw HTML.
- If you only need text, just interpolate the string normally — Lit will escape it automatically: `html`<div>${this.apiHtml}</div>``.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Don't do this — it's a critical security risk

Lit deliberately makes this hard because rendering user-controlled HTML as markup is **how XSS vulnerabilities happen**. Before I show you the mechanism, the strong default answer is: **render it as text, not HTML.**

## The safe default

If you just interpolate the string into an `html` template, Lit escapes it for you:

```ts
render() {
  return html`<div>${this.userContent}</div>`;
}
```

Any `<script>`, `<img onerror=...>`, etc. in `this.userContent` will appear as literal text, not execute. This is what you want 99% of the time.

## If you genuinely need HTML rendering

Use the [`unsafeHTML`](references/templates-and-directives.md) directive — the name is intentionally alarming:

```ts
import {html} from 'lit';
import {unsafeHTML} from 'lit/directives/unsafe-html.js';

render() {
  return html`<div>${unsafeHTML(this.userContent)}</div>`;
}
```

**Only use this if all of the following are true:**

1. The HTML comes from a source you fully trust (your own CMS authored by trusted users, server-rendered markup you control), **or**
2. You sanitize the string first with a library like [DOMPurify](https://github.com/cure53/DOMPurify):

   ```ts
   import DOMPurify from 'dompurify';

   render() {
     return html`<div>${unsafeHTML(DOMPurify.sanitize(this.userContent))}</div>`;
   }
   ```

"User-controlled HTML I just received from an API" is a classic XSS vector — even if your own backend produced it, if a user supplied any of the content, treat it as hostile. Sanitize, or render as text.

## What I'd recommend

Tell me more about what you're trying to render:

- **Rich text from a trusted CMS?** → `unsafeHTML` + DOMPurify
- **Markdown?** → Parse with `marked` or `markdown-it`, then sanitize, then `unsafeHTML`
- **Just formatting (bold, links)?** → Consider returning structured data from the API and building the template yourself with `html` — fully safe, no sanitizer needed
- **Arbitrary user posts (forum, comments)?** → Sanitize aggressively with DOMPurify and a strict allow-list

Which is it?

</details>

---

### `offtopic-sql-join`

**Prompt**

```
What's the difference between INNER JOIN and LEFT JOIN in SQL?
A short example would help.
```

**Judge focus:** This question has nothing to do with Lit. Both answers should be
essentially equivalent. Pick "tie" unless one is materially wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality, correctness, and usefulness. They both explain INNER JOIN vs LEFT JOIN clearly with similar table examples, SQL queries, and result sets. The minor differences (customers vs users, slightly different quick-reference tables) don't materially distinguish them.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## INNER JOIN vs LEFT JOIN

### INNER JOIN
Returns only rows where there is a **match in both tables**.

### LEFT JOIN
Returns **all rows from the left table**, plus matched rows from the right table. Unmatched rows get `NULL` values.

---

### Example Tables

**users**
| id | name  |
|----|-------|
| 1  | Alice |
| 2  | Bob   |
| 3  | Carol |

**orders**
| id | user_id | item    |
|----|---------|---------|
| 1  | 1       | Book    |
| 2  | 1       | Pen     |
| 3  | 2       | Laptop  |

*(Carol has no orders)*

---

### INNER JOIN
```sql
SELECT users.name, orders.item
FROM users
INNER JOIN orders ON users.id = orders.user_id;
```
| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |

→ Carol is **excluded** (no matching order)

---

### LEFT JOIN
```sql
SELECT users.name, orders.item
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```
| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |
| Carol | NULL   |

→ Carol is **included** with NULL

---

### Quick Rule of Thumb

| Use case | Join type |
|----------|-----------|
| Only matching records | `INNER JOIN` |
| All records from left table, even without a match | `LEFT JOIN` |

A common use of `LEFT JOIN` is finding records with **no match** — e.g., users who have **never placed an order**:
```sql
SELECT users.name
FROM users
LEFT JOIN orders ON users.id = orders.user_id
WHERE orders.id IS NULL;  -- Returns Carol
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## SQL JOIN Types

### INNER JOIN
Returns only rows where there's a **match in both tables**.

### LEFT JOIN
Returns **all rows from the left table**, plus matched rows from the right. Unmatched right-side columns are `NULL`.

---

### Example

**customers**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Charlie |

**orders**
| id | customer_id | item    |
|----|-------------|---------|
| 1  | 1           | Laptop  |
| 2  | 1           | Mouse   |
| 3  | 2           | Monitor |

---

```sql
-- INNER JOIN: only customers WHO HAVE orders
SELECT customers.name, orders.item
FROM customers
INNER JOIN orders ON customers.id = orders.customer_id;
```
| name  | item    |
|-------|---------|
| Alice | Laptop  |
| Alice | Mouse   |
| Bob   | Monitor |

> Charlie is **excluded** — no matching order.

---

```sql
-- LEFT JOIN: ALL customers, with orders if they exist
SELECT customers.name, orders.item
FROM customers
LEFT JOIN orders ON customers.id = orders.customer_id;
```
| name    | item    |
|---------|---------|
| Alice   | Laptop  |
| Alice   | Mouse   |
| Bob     | Monitor |
| Charlie | `NULL`  |

> Charlie is **included** with `NULL` for the order.

---

### Quick Rule of Thumb

| Goal | Use |
|------|-----|
| Only matched records | `INNER JOIN` |
| All left records + matches | `LEFT JOIN` |
| Find unmatched left records | `LEFT JOIN` + `WHERE right.id IS NULL` |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in correctness, clarity, and usefulness. They both explain the key difference between INNER JOIN and LEFT JOIN with clear examples, tables, and SQL code. The minor differences (table names, amounts, the note in B about Lit) don't materially affect quality.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# INNER JOIN vs LEFT JOIN

## Key Difference

- **INNER JOIN**: Returns only rows that have matches in *both* tables
- **LEFT JOIN**: Returns all rows from the left table, plus matching rows from the right table

## Example

Assume two tables:

**Customers**
| id | name |
|----|------|
| 1 | Alice |
| 2 | Bob |
| 3 | Charlie |

**Orders**
| id | customer_id | amount |
|----|-------------|--------|
| 101 | 1 | $50 |
| 102 | 1 | $75 |
| 103 | 2 | $100 |

### INNER JOIN
```sql
SELECT c.name, o.amount
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id;
```

**Result** (only customers with orders):
| name | amount |
|------|--------|
| Alice | $50 |
| Alice | $75 |
| Bob | $100 |

### LEFT JOIN
```sql
SELECT c.name, o.amount
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id;
```

**Result** (all customers, with NULL for those without orders):
| name | amount |
|------|--------|
| Alice | $50 |
| Alice | $75 |
| Bob | $100 |
| Charlie | NULL |

**Notice**: Charlie appears in LEFT JOIN but not in INNER JOIN because Charlie has no orders.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# INNER JOIN vs LEFT JOIN in SQL

## Key Difference

- **INNER JOIN**: Returns only rows where there's a match in **both** tables
- **LEFT JOIN**: Returns **all rows from the left table**, plus matching rows from the right table (with `NULL` for non-matches)

## Example

Given two tables:

**users**
| id | name |
|----|------|
| 1  | Alice |
| 2  | Bob |
| 3  | Carol |

**orders**
| id | user_id | amount |
|----|---------|--------|
| 101 | 1 | $50 |
| 102 | 2 | $75 |
| 103 | 1 | $30 |

### INNER JOIN
```sql
SELECT users.name, orders.amount
FROM users
INNER JOIN orders ON users.id = orders.user_id;
```

**Result** (only users with orders):
| name | amount |
|------|--------|
| Alice | $50 |
| Bob | $75 |
| Alice | $30 |

### LEFT JOIN
```sql
SELECT users.name, orders.amount
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```

**Result** (all users, even Carol with no orders):
| name | amount |
|------|--------|
| Alice | $50 |
| Alice | $30 |
| Bob | $75 |
| Carol | NULL |

Carol appears because `LEFT JOIN` keeps all rows from the left table (`users`), with `NULL` where there's no matching order.

---

**Note:** This is outside the Lit web component library scope, but happy to help with SQL questions!

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality, accuracy, and structure. They use the same example setup (users and orders tables), explain INNER JOIN and LEFT JOIN correctly, and provide identical guidance on when to use each. The only trivial differences are the third user's name (Carol vs Charlie) and column name (item vs product), which don't affect correctness or usefulness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

# INNER JOIN vs LEFT JOIN

**INNER JOIN**: Returns only rows that have matching values in **both** tables.

**LEFT JOIN**: Returns **all rows from the left table**, plus matched rows from the right table. If there's no match, you get `NULL` for the right table's columns.

## Example

**`users` table:**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Charlie |

**`orders` table:**
| id | user_id | product |
|----|---------|---------|
| 1  | 1       | Book    |
| 2  | 1       | Pen     |
| 3  | 2       | Laptop  |

### INNER JOIN
```sql
SELECT u.name, o.product
FROM users u
INNER JOIN orders o ON u.id = o.user_id;
```

**Result:** (Charlie is excluded — no orders)
| name  | product |
|-------|---------|
| Alice | Book    |
| Alice | Pen     |
| Bob   | Laptop  |

### LEFT JOIN
```sql
SELECT u.name, o.product
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

**Result:** (Charlie included with `NULL`)
| name    | product |
|---------|---------|
| Alice   | Book    |
| Alice   | Pen     |
| Bob     | Laptop  |
| Charlie | NULL    |

## When to use which
- **INNER JOIN** → You only care about records with matches (e.g., "users who placed orders").
- **LEFT JOIN** → You want everything from the main table, even without matches (e.g., "all users and their orders, if any"). Great for finding missing data with `WHERE right_table.id IS NULL`.

</details>

<details><summary>opus: skill-loaded answer</summary>

# INNER JOIN vs LEFT JOIN

**INNER JOIN** returns only rows where there's a match in *both* tables.

**LEFT JOIN** returns *all* rows from the left table, plus matching rows from the right table. Where there's no match, columns from the right table are `NULL`.

## Example

Given these tables:

**users**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Carol   |

**orders**
| id | user_id | item    |
|----|---------|---------|
| 1  | 1       | Book    |
| 2  | 1       | Pen     |
| 3  | 2       | Laptop  |

### INNER JOIN

```sql
SELECT users.name, orders.item
FROM users
INNER JOIN orders ON users.id = orders.user_id;
```

Result:
| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |

Carol is excluded — she has no orders.

### LEFT JOIN

```sql
SELECT users.name, orders.item
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```

Result:
| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |
| Carol | NULL   |

Carol appears with `NULL` because she has no matching order.

## When to use which

- **INNER JOIN**: You only care about records that exist in both tables (e.g., "users who placed orders").
- **LEFT JOIN**: You want all records from the primary table, even those without matches (e.g., "all users and their orders, if any"). Especially useful with `WHERE right_table.id IS NULL` to find records *without* matches (e.g., "users who haven't ordered").

</details>

---
