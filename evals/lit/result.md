# Eval report: `lit`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **6**
- Models: **sonnet, haiku, opus**
- Total cost: **$1.44** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 4/6 | 3 / 0 / 3 | 100% → 100% (+0%) |
| `haiku` | 5/6 | 4 / 1 / 1 | 100% → 100% (+0%) |
| `opus` ¹ | 5/6 | 4 / 0 / 2 | 100% → 100% (+0%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 4 | 2/4 | 4/4 | 3/4 |
| `skill_wins_strict` | 1 | 1/1 | 0/1 | 1/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `array-mutation-no-rerender` | skill_wins | ✗ = tie | ✓ ✓ skill | ✗ = tie |
| `typed-event-cross-shadow` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `lifecycle-which-callback` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `state-vs-property` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `simplest-render-html` | skill_wins_strict | ✓ ✓ skill | ✗ ✗ baseline | ✓ ✓ skill |
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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly explain reference equality, recommend creating a new array with spread syntax, and mention requestUpdate as an escape hatch. Answer A goes deeper with additional examples (other mutation methods, objects, repeat directive) while Answer B is more concise and includes a helpful summary table with multiple new-array alternatives like concat. Both are high quality and cover all rubric criteria equally well.

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
| explains reference equality / strict equality | ✓ | `reference equal` |
| recommends creating a new array | ✓ | `[...this.items` |
| mentions requestUpdate as escape hatch | ✓ | `requestUpdate` |

<details><summary>sonnet: baseline answer</summary>

## The Problem

Lit tracks property changes by **reference equality** (`===`). When you use `push()`, you're mutating the **same array reference**, so Lit doesn't detect any change and skips re-rendering.

```javascript
// ❌ Mutating the array - Lit sees the same reference, no re-render
this.items.push(newItem);
```

---

## The Fix

You need to create a **new array reference** so Lit detects the change:

```javascript
// ✅ Option 1: Spread into a new array (most common)
this.items = [...this.items, newItem];

// ✅ Option 2: concat (returns a new array)
this.items = this.items.concat(newItem);

// ✅ Option 3: Array.from
this.items = Array.from(this.items).concat(newItem);
```

---

## If You *Must* Mutate

If you have a specific reason to mutate the array directly, you can notify Lit manually using `requestUpdate()`:

```javascript
this.items.push(newItem);
this.requestUpdate('items', previousValue); // manually trigger re-render
```

> ⚠️ This is generally discouraged — prefer immutable updates.

---

## Full Example

```javascript
import { LitElement, html } from 'lit';

class MyList extends LitElement {
  @property({ type: Array }) items = [];

  addItem(newItem) {
    this.items = [...this.items, newItem]; // ✅ new reference = re-render
  }

  render() {
    return html`
      <ul>
        ${this.items.map(item => html`<li>${item}</li>`)}
      </ul>
      <button @click=${() => this.addItem('New Item')}>Add</button>
    `;
  }
}
```

---

## Summary

| Approach | Creates New Reference | Re-renders |
|---|---|---|
| `push()` | ❌ | ❌ |
| `[...items, newItem]` | ✅ | ✅ |
| `concat()` | ✅ | ✅ |
| `push()` + `requestUpdate()` | ❌ | ✅ |

The **spread operator** (`[...this.items, newItem]`) is the cleanest and most idiomatic solution.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Lit uses **reference equality** (`!==`) to detect changes. When you call `this.items.push(newItem)`, the array reference stays the same, so Lit sees no change and skips the re-render.

## The Fix: Replace the Reference

Instead of mutating the array, assign a new one:

```typescript
// ❌ Mutates in place — Lit sees no change
this.items.push(newItem);

// ✅ New reference — Lit detects the change and re-renders
this.items = [...this.items, newItem];
```

The same rule applies to all common array mutations:

```typescript
// ❌ All of these mutate in place
this.items.push(newItem);
this.items.pop();
this.items.splice(index, 1);
this.items.sort();
this.items[0] = newItem;

// ✅ Immutable equivalents
this.items = [...this.items, newItem];           // push
this.items = this.items.slice(0, -1);            // pop
this.items = this.items.filter((_, i) => i !== index); // splice/remove
this.items = [...this.items].sort();             // sort
this.items = this.items.map((item, i) =>         // index update
  i === 0 ? newItem : item
);
```

The same principle applies to **objects** — spread instead of mutating:

```typescript
// ❌ Mutates in place
this.user.name = 'Alice';

// ✅ New reference
this.user = { ...this.user, name: 'Alice' };
```

## Escape Hatch: `requestUpdate()`

If you genuinely need to mutate in place (e.g., working with a third-party API that hands you a mutable object), you can manually notify Lit:

```typescript
this.items.push(newItem);
this.requestUpdate('items', previousItems); // pass the old reference
```

This works, but the immutable pattern is strongly preferred — it's clearer, easier to test, and avoids subtle bugs.

## Rendering Lists Efficiently

Once your array updates correctly, use the `repeat()` directive so Lit can reconcile by key instead of re-rendering the whole list:

```typescript
import { repeat } from 'lit/directives/repeat.js';

render() {
  return html`
    <ul>
      ${repeat(
        this.items,
        (item) => item.id,           // stable key
        (item) => html`<li>${item.name}</li>`
      )}
    </ul>
    <button @click=${this.addItem}>Add</button>
  `;
}

private addItem() {
  this.items = [...this.items, { id: crypto.randomUUID(), name: 'New' }];
}
```

`repeat()` with a key minimises DOM churn on reorders and insertions — without it, Lit patches nodes in place by position, which can cause issues with stateful elements like inputs.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover all three rubric criteria, but Answer B is more precise and idiomatic. It correctly uses '!==' (reference inequality) terminology rather than 'shallow equality checks', frames requestUpdate as an escape hatch to avoid rather than a primary solution, and provides cleaner code examples with explicit ❌/✅ markers. Answer A calls it 'shallow equality checks' which is slightly imprecise, and presents requestUpdate more neutrally rather than as a last resort.

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

### 3. **Use a reactive controller or state management**
For complex state, consider using a library like `lit-state` or `@lit/reactive-element`.

## Why This Happens

Lit uses **shallow equality checks** by default. It compares the old and new property values:

```javascript
oldValue === newValue  // false only if reference changes
```

When you mutate an array:
```javascript
const arr = [1, 2];
arr.push(3);
arr === arr  // still true! Same reference
```

## Best Practice

Always treat arrays as immutable in Lit:

```javascript
addItem(newItem) {
  this.items = [...this.items, newItem];
}

removeItem(index) {
  this.items = this.items.filter((_, i) => i !== index);
}

updateItem(index, updated) {
  this.items = this.items.map((item, i) => 
    i === index ? updated : item
  );
}
```

This ensures Lit detects the change and re-renders properly.

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
- [Templates & Directives](references/templates-and-directives.md) — `repeat()` directive for efficient list rendering

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria clearly. Answer A provides more comprehensive examples (remove, update, clear, objects) and explains why Lit uses reference equality, while Answer B adds a useful nuance about requestUpdate('items') and changedProperties behavior. Neither is clearly superior overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains reference equality / strict equality | tie |
| recommends creating a new array | skill |
| mentions requestUpdate as escape hatch | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains reference equality / strict equality | ✓ | `same reference` |
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

Lit uses **referential equality** (`===`) by default to detect property changes. When you call `this.items.push(newItem)`, you're mutating the existing array — the reference stays the same, so Lit doesn't see a change and doesn't trigger a re-render.

# The Fix

Replace the array with a new one instead of mutating it:

```js
// ❌ Doesn't trigger re-render
this.items.push(newItem);

// ✅ Triggers re-render
this.items = [...this.items, newItem];
```

The same applies to other mutating methods like `pop()`, `splice()`, `sort()`, etc., and to objects (`this.obj.foo = 'bar'` won't trigger an update either).

# Alternative: Manual Request

If you have a good reason to mutate in place (e.g., very large arrays where copying is expensive), you can manually tell Lit to re-render:

```js
this.items.push(newItem);
this.requestUpdate();
```

Or, if you want Lit to only check a specific property:

```js
this.items.push(newItem);
this.requestUpdate('items');
```

Note that with `requestUpdate('items')`, the `changedProperties` map passed to `updated()` / `willUpdate()` will reflect the old value as the same reference, which can break logic that compares old vs. new.

# Recommendation

Prefer the immutable approach (`this.items = [...this.items, newItem]`). It plays nicely with Lit's change detection, makes `changedProperties` meaningful, and aligns with how reactive frameworks generally expect state to be updated.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Why Your Component Isn't Re-rendering

This is one of the most common Lit pitfalls. The issue is **how Lit detects property changes**, not anything specific to arrays.

## The Cause

Lit uses **reference equality** (`!==`) to detect property changes. When you call `this.items.push(newItem)`, you're mutating the existing array in place — the reference stays the same, so Lit thinks nothing changed and skips the re-render.

```ts
// ❌ Mutates in place — same reference, no re-render
this.items.push(newItem);

// Lit's check: this.items !== this.items → false → no update
```

## The Fix

Always assign a **new** array (or object) reference:

```ts
// ✅ New array reference — triggers re-render
this.items = [...this.items, newItem];
```

The same rule applies to all array/object mutations:

```ts
// Add
this.items = [...this.items, newItem];

// Remove
this.items = this.items.filter(item => item.id !== id);

// Update one
this.items = this.items.map(item =>
  item.id === id ? { ...item, done: true } : item
);

// Clear
this.items = [];
```

And for objects:

```ts
// ❌ this.user.name = 'Alice';
// ✅
this.user = { ...this.user, name: 'Alice' };
```

## Escape Hatch (Use Sparingly)

If you have a genuine reason to mutate in place (e.g., a very large array where copying is too expensive), you can manually tell Lit to re-render:

```ts
this.items.push(newItem);
this.requestUpdate('items', this.items); // force update
```

But in 99% of cases, the immutable update pattern is cleaner and has no meaningful performance cost.

## Why Lit Works This Way

Reference equality is **fast** (a single `!==` check) and **predictable**. Deep equality would be expensive on every property set, and there's no reliable way to detect mutations to nested objects without proxies. The immutable update pattern also plays nicely with `Task` arguments, `repeat()` keys, and any future migration to signals.

---

**TL;DR:** Replace `this.items.push(x)` with `this.items = [...this.items, x]`.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify composed:true and bubbles:true as required to cross Shadow DOM boundaries, but Answer B goes further by providing the bonus content about typed Event subclasses with static readonly type, TypeScript integration with HTMLElementEventMap, and a practical debugging checklist. Answer B is more comprehensive and production-ready while still covering all the core criteria.

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
| mentions Shadow DOM boundary | ✓ | `Shadow DOM` |

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
  // composed: false    // default - does NOT cross shadow boundary
}));

// ✅ Correct - event escapes the shadow root
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { message: 'hello' },
  bubbles: true,   // bubbles up through the DOM
  composed: true   // crosses the shadow DOM boundary ✅
}));
```

---

## What Each Option Does

| Option | Description |
|---|---|
| `bubbles: false` | Event stays on the dispatching element only |
| `bubbles: true` | Event bubbles up through the DOM tree |
| `composed: false` | Event is **blocked** at the shadow root (default) |
| `composed: true` | Event **crosses** shadow DOM boundaries into the light DOM |

---

## Full Lit Example

```javascript
// child-component.js
import { LitElement, html } from 'lit';

class ChildComponent extends LitElement {
  _handleClick() {
    this.dispatchEvent(new CustomEvent('child-clicked', {
      detail: { value: 42 },
      bubbles: true,
      composed: true  // 👈 key option
    }));
  }

  render() {
    return html`<button @click=${this._handleClick}>Click me</button>`;
  }
}
customElements.define('child-component', ChildComponent);
```

```javascript
// parent-component.js
import { LitElement, html } from 'lit';

class ParentComponent extends LitElement {
  _onChildClicked(e) {
    console.log('Received event:', e.detail.value); // 42 ✅
  }

  render() {
    return html`
      <child-component
        @child-clicked=${this._onChildClicked}>
      </child-component>
    `;
  }
}
customElements.define('parent-component', ParentComponent);
```

---

## Important Caveat: `e.target` Will Be Retargeted

When `composed: true` is used, the browser **retargets** `e.target` to the host element (`<child-component>`) as the event crosses the boundary — the internal element that originally fired it is hidden. This is expected Shadow DOM behavior.

```javascript
_onChildClicked(e) {
  console.log(e.target); // <child-component> not the internal <button>
}
```

---

## Quick Rule of Thumb

> If you want a parent **outside** your Lit component to hear your event, always use `bubbles: true, composed: true`.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## The Problem: Shadow DOM Event Retargeting

Custom events don't cross Shadow DOM boundaries by default. When you dispatch an event inside a shadow root, it stops there — the parent component never sees it.

The fix requires **two flags** in the event constructor:

```typescript
// ❌ Stays trapped inside the shadow root
this.dispatchEvent(new CustomEvent('user-selected', { detail: { id: 42 } }));

// ✅ Crosses shadow boundaries and bubbles up the DOM tree
this.dispatchEvent(new CustomEvent('user-selected', {
  detail: { id: 42 },
  bubbles: true,   // travels up the DOM tree
  composed: true,  // crosses shadow root boundaries
}));
```

Both flags are required together:

| Flag | What it does | Without it |
|------|-------------|------------|
| `bubbles` | Travels up the DOM tree | Event stays on the dispatching element |
| `composed` | Crosses shadow root boundaries | Event stops at the shadow root edge |

---

## The Recommended Pattern: Typed Event Classes

Rather than raw `CustomEvent`, define a concrete event class. This gives you type safety on both the dispatching and listening sides, and makes the `bubbles`/`composed` defaults impossible to forget.

**`events/user-selected-event.ts`** — define once, import everywhere:

```typescript
export class UserSelectedEvent extends Event {
  static readonly type = 'user-selected';

  constructor(public readonly userId: number) {
    super(UserSelectedEvent.type, {
      bubbles: true,
      composed: true,
    });
  }
}

// Teach TypeScript about the event on the element's interface
declare global {
  interface HTMLElementEventMap {
    'user-selected': UserSelectedEvent;
  }
}
```

**Dispatching component** — dispatch after `updateComplete` so listeners see the rendered state:

```typescript
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { UserSelectedEvent } from './events/user-selected-event.js';

@customElement('user-list')
export class UserList extends LitElement {
  private async _handleClick(userId: number) {
    // Do any async work first, then dispatch after render is settled
    await this.updateComplete;
    this.dispatchEvent(new UserSelectedEvent(userId));
  }

  render() {
    return html`
      <button @click=${() => this._handleClick(42)}>Select user</button>
    `;
  }
}
```

**Listening component** — the event type is fully inferred from `HTMLElementEventMap`:

```typescript
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { UserSelectedEvent } from './events/user-selected-event.js';

@customElement('app-shell')
export class AppShell extends LitElement {
  render() {
    return html`
      <user-list
        @user-selected=${this._onUserSelected}
      ></user-list>
    `;
  }

  // userId is typed as number — no casting needed
  private _onUserSelected(e: UserSelectedEvent) {
    console.log(e.userId);
  }
}
```

---

## Quick Checklist

If the event still isn't arriving, run through these:

- [ ] **Both `bubbles: true` and `composed: true` are set** — one alone isn't enough
- [ ] **The listener is on the host element or an ancestor**, not inside the shadow root of the dispatching component
- [ ] **`e.stopPropagation()` isn't called** somewhere between the dispatch point and the listener
- [ ] **The event name matches exactly** — `'user-selected'` vs `'userSelected'` are different strings
- [ ] **The listener is attached before the event fires** — especially relevant with `firstUpdated` timing

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify composed:true and bubbles:true as required to cross Shadow DOM boundaries, but Answer A goes further by including the bonus content about typed Event subclasses with static readonly type, which is explicitly mentioned in the focus area. Answer A also provides a comparison table, updateComplete timing guidance, and more comprehensive TypeScript examples, making it more complete and useful overall.

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
// ❌ Won't reach parent (default)
this.dispatchEvent(new CustomEvent('my-event'));

// ✅ Will reach parent
this.dispatchEvent(new CustomEvent('my-event', {
  bubbles: true,
  composed: true
}));
```

## Complete Example

**Child Component (Lit):**
```javascript
import { LitElement, html } from 'lit';

export class MyChild extends LitElement {
  handleClick() {
    this.dispatchEvent(new CustomEvent('child-event', {
      detail: { message: 'Hello from child' },
      bubbles: true,
      composed: true  // ← This is the key!
    }));
  }

  render() {
    return html`<button @click=${this.handleClick}>Click me</button>`;
  }
}
```

**Parent Component:**
```javascript
export class MyParent extends LitElement {
  handleChildEvent(e) {
    console.log('Received:', e.detail.message);
  }

  render() {
    return html`
      <my-child @child-event=${this.handleChildEvent}></my-child>
    `;
  }
}
```

## Key Options Explained

| Option | Purpose |
|--------|---------|
| `bubbles: true` | Allows event to bubble up the DOM tree |
| `composed: true` | **Allows event to cross Shadow DOM boundary** |
| `detail` | Optional data to pass with the event |

Both `bubbles` and `composed` are typically needed for events to reach parents outside the Shadow DOM.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# CustomEvent Not Crossing Shadow DOM Boundary

The issue is that your event isn't configured to bubble through the Shadow DOM. By default, events created with `new CustomEvent()` have `bubbles: false` and `composed: false`, which means they stop at the Shadow DOM boundary.

## Solution

When dispatching a custom event from a Lit component, **always set `bubbles: true` and `composed: true`**:

```typescript
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('my-button')
export class MyButton extends LitElement {
  private handleClick() {
    // ✅ Correct: event crosses Shadow DOM
    this.dispatchEvent(
      new CustomEvent('my-event', {
        detail: { message: 'Hello from shadow!' },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`<button @click=${this.handleClick}>Click me</button>`;
  }
}
```

Parent listening outside the component:

```typescript
const button = document.querySelector('my-button');
button.addEventListener('my-event', (e: Event) => {
  const event = e as CustomEvent;
  console.log(event.detail.message); // "Hello from shadow!"
});
```

## Why This Matters

| Property | Effect |
|----------|--------|
| `bubbles: true` | Event propagates up the DOM tree (parent, grandparent, etc.) |
| `composed: true` | Event crosses the Shadow DOM boundary; without this, it stops at the host element |
| `bubbles: false` (default) | Event only fires on the exact target; doesn't propagate |
| `composed: false` (default) | Event cannot cross Shadow DOM; invisible to light DOM listeners |

## Best Practice: Typed Event Classes

For type safety and reusability, define a concrete event class:

```typescript
// events.ts
export class MyEventDetail {
  constructor(public message: string) {}
}

export class MyEvent extends Event {
  static readonly type = 'my-event';

  constructor(public detail: MyEventDetail) {
    super(MyEvent.type, { bubbles: true, composed: true });
  }
}

// my-button.ts
import { MyEvent, MyEventDetail } from './events.js';

@customElement('my-button')
export class MyButton extends LitElement {
  private handleClick() {
    this.dispatchEvent(new MyEvent(new MyEventDetail('Hello!')));
  }

  render() {
    return html`<button @click=${this.handleClick}>Click me</button>`;
  }
}

// parent.ts
import { MyEvent } from './events.js';

const button = document.querySelector('my-button')!;
button.addEventListener(MyEvent.type, (e: Event) => {
  const event = e as MyEvent;
  console.log(event.detail.message); // Fully typed!
});
```

## Dispatch After `updateComplete`

For events that reflect the rendered state, dispatch after the DOM has updated:

```typescript
private async handleChange() {
  this.value = 'new value';
  await this.updateComplete; // Wait for render
  this.dispatchEvent(
    new CustomEvent('value-changed', {
      detail: { value: this.value },
      bubbles: true,
      composed: true,
    })
  );
}
```

See [reactive-properties.md](references/reactive-properties.md) for the full typed event pattern and [lifecycle.md](references/lifecycle.md) for `updateComplete` timing.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify composed:true, bubbles:true, and Shadow DOM boundaries as the core issue. However, Answer B goes further by including the bonus criterion of typed Event subclasses with static readonly type, complete TypeScript examples, HTMLElementEventMap augmentation, and practical debugging tips. Answer A is solid but lacks the typed event class pattern that the rubric specifically rewards.

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

# The Issue: Event Propagation Across Shadow DOM

By default, `CustomEvent`s **don't cross shadow DOM boundaries**. Since Lit components use shadow DOM, an event dispatched from inside your component will be trapped unless you configure it properly.

## The Fix

You need to set both `bubbles: true` and `composed: true`:

```js
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { someData: 123 },
  bubbles: true,
  composed: true  // 👈 This is the key — allows the event to escape shadow DOM
}));
```

## What Each Option Does

| Option | Purpose |
|--------|---------|
| `bubbles: true` | Lets the event bubble up the DOM tree (instead of firing only on the target) |
| `composed: true` | Lets the event cross shadow DOM boundaries into the light DOM |

Without `composed: true`, the event will bubble *within* your component's shadow root, but will stop at the shadow boundary and never reach the parent.

## A Note on `event.target`

Once the event crosses the shadow boundary, `event.target` will be **retargeted** to your custom element (the host), not the inner element that originally dispatched it. If you need access to the original target, use `event.composedPath()[0]`.

## Bonus: Lit Convention

Lit's docs recommend dispatching events from a method so consumers can override behavior, and naming events with a hyphen (e.g., `item-selected`):

```js
private _notify() {
  this.dispatchEvent(new CustomEvent('item-selected', {
    detail: { id: this.itemId },
    bubbles: true,
    composed: true,
  }));
}
```

That should get your parent listener firing correctly.

</details>

<details><summary>opus: skill-loaded answer</summary>

Almost certainly your event isn't crossing the Shadow DOM boundary. By default, events dispatched from inside a shadow root are **retargeted** and don't bubble out unless you explicitly opt in.

## The fix

Set both `bubbles: true` and `composed: true` on the event:

```ts
this.dispatchEvent(new CustomEvent('my-event', {
  detail: { value: 42 },
  bubbles: true,
  composed: true,  // <-- required to cross Shadow DOM
}));
```

- `bubbles: true` — event walks up the DOM tree
- `composed: true` — event crosses Shadow DOM boundaries

Without `composed: true`, the event bubbles only within your component's shadow root and stops at the host. The parent never sees it.

## Recommended pattern: typed event class

For a more robust, type-safe approach, define a concrete event class and export it so consumers get autocomplete and type checking:

```ts
// my-component.ts
export class ValueChangeEvent extends Event {
  static readonly type = 'value-change' as const;
  constructor(public readonly value: number) {
    super(ValueChangeEvent.type, { bubbles: true, composed: true });
  }
}

@customElement('my-component')
export class MyComponent extends LitElement {
  private async _onClick() {
    this.value = 42;
    await this.updateComplete;  // ensure DOM reflects state before listeners run
    this.dispatchEvent(new ValueChangeEvent(this.value));
  }
  // ...
}

declare global {
  interface HTMLElementEventMap {
    'value-change': ValueChangeEvent;
  }
}
```

Then in the parent:

```ts
import { ValueChangeEvent } from './my-component.js';

el.addEventListener(ValueChangeEvent.type, (e) => {
  console.log(e.value);  // fully typed
});
```

## Other things to check if it still doesn't work

1. **Listener attached too early?** If the parent attaches the listener before the child upgrades, that's fine — `addEventListener` doesn't care about element upgrade order. But if you're using inline `@event` bindings in a Lit template, make sure the parent itself has rendered.
2. **Wrong event name** — check for typos; event names are case-sensitive.
3. **`stopPropagation()` somewhere in between** — an intermediate component may be swallowing it.
4. **Dispatching before render** — if you dispatch in `connectedCallback` before `firstUpdated`, the parent listener may not be wired up yet. Dispatch after `await this.updateComplete` to be safe.

The 90% answer is `composed: true`. Add it and the event will reach your parent.

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly map all three tasks to willUpdate, firstUpdated, and updated, explain the changedProperties parameter with guards, and provide clear rationale. Answer A is slightly more concise and readable, while Answer B provides more detailed TypeScript examples, comparison tables for alternatives, and a useful note about @lit/task for data fetching. Both are essentially equivalent in correctness and coverage of all rubric criteria.

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
- Do **not** use `updated()` — that runs after render, causing a wasted paint cycle
- Do **not** set reactive properties here (use plain class fields), otherwise you trigger another update cycle

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
- If you need to wait for sub-element rendering, `await this.updateComplete` inside here is valid

---

## (c) External API Call After Every Render That Changed an Input

**→ `updated(changedProperties)`**

```javascript
updated(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.fetchData(this.someInput).then(result => {
      this.result = result; // reactive property, triggers re-render
    });
  }
}
```

**Why:**
- Runs **after every update**, with access to what actually changed via `changedProperties`
- The guard `changedProperties.has('someInput')` prevents unnecessary API calls on unrelated re-renders
- Runs after DOM is committed, so any DOM side effects from the API response are safe
- Do **not** do this in `willUpdate` — the DOM isn't ready and you'd be firing async work before the render it corresponds to is even painted
- Be careful: setting a reactive property in `updated()` triggers another update cycle — that's intentional here but must be guarded to avoid infinite loops

---

## Summary Table

| Task | Method | Timing | Runs |
|---|---|---|---|
| Derive from input | `willUpdate()` | Before render | Every relevant change |
| Measure DOM once | `firstUpdated()` | After first render | Once |
| Call API on input change | `updated()` | After every render | Every relevant change |

The core principle: **before the DOM → `willUpdate`, after the DOM → `updated`/`firstUpdated`**, and always guard with `changedProperties.has()` to avoid unnecessary work.

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
    // Runs before render(), so the template sees fresh values immediately
    if (changed.has('price') || changed.has('quantity')) {
      this.total = this.price * this.quantity;
      this.formattedTotal = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
      }).format(this.total);
    }
  }

  render() {
    // formattedTotal is always current — no stale-value risk
    return html`<p>Total: ${this.formattedTotal}</p>`;
  }
}
```

**Why `willUpdate()` and not somewhere else:**

| Alternative | Problem |
|-------------|---------|
| Inside `render()` | Makes `render()` impure — it should be a pure projection of state to DOM |
| `@state()` field set in `updated()` | Triggers a *second* update cycle — wasteful and can cause loops |
| Constructor / `connectedCallback` | Doesn't re-run when inputs change |

`willUpdate()` is the one place guaranteed to run before every render, after properties are set, with access to `changedProperties` so you can guard the computation.

---

### (b) One-time DOM measurement — `firstUpdated()`

```typescript
@customElement('my-component')
export class MyComponent extends LitElement {
  @query('canvas') private _canvas!: HTMLCanvasElement;

  private _chart: Chart | null = null;

  protected firstUpdated(): void {
    // Shadow DOM is fully rendered exactly once here
    const { width, height } = this._canvas.getBoundingClientRect();

    this._chart = new Chart(this._canvas, {
      initialWidth: width,
      initialHeight: height,
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._chart?.destroy(); // clean up the external resource
  }

  render() {
    return html`<canvas></canvas>`;
  }
}
```

**Why `firstUpdated()` and not somewhere else:**

| Alternative | Problem |
|-------------|---------|
| `constructor` | Shadow DOM doesn't exist yet — `querySelector` returns `null` |
| `connectedCallback` | Lit hasn't rendered yet at this point |
| `updated()` | Runs after *every* update — you'd re-initialize the chart on every property change |

`firstUpdated()` fires once, after the initial render, with the DOM present. It's the right place for "set up an external thing that owns a DOM node."

---

### (c) External API call after relevant input changes — `updated()`

```typescript
@customElement('my-component')
export class MyComponent extends LitElement {
  @property() userId = '';

  protected updated(changed: PropertyValues<this>): void {
    if (changed.has('userId') && this.userId) {
      // Guard is critical — updated() runs after every update cycle
      this._syncToAnalytics(this.userId);
    }
  }

  private _syncToAnalytics(id: string): void {
    // Fire-and-forget side effect; not data fetching (use Task for that)
    navigator.sendBeacon('/api/analytics', JSON.stringify({ userId: id }));
  }

  render() {
    return html`<p>Viewing user: ${this.userId}</p>`;
  }
}
```

**Why `updated()` and not somewhere else:**

| Alternative | Problem |
|-------------|---------|
| `willUpdate()` | DOM hasn't rendered yet — the "after render" guarantee is missing |
| `render()` | Impure; may be called speculatively by Lit |
| Unconditional `updated()` | Fires on *every* update, not just when `userId` changed — causes runaway calls |

The `changed.has('key')` guard is non-negotiable. Without it, every unrelated property change (a CSS class toggle, a loading flag) triggers the API call.

> **Note:** If this were *fetching* data rather than pushing a side effect, use `@lit/task` instead — it handles cancellation, race conditions, and loading states that `updated()` doesn't.

---

### Summary

```
Property change
      │
      ▼
 willUpdate()  ← (a) derive computed state from new inputs
      │
      ▼
   render()    ← pure: reads this.* and returns html``
      │
      ▼
  updated()    ← (c) side effects that react to specific changes
      │
      ▼  (first render only)
firstUpdated() ← (b) one-time DOM measurement / external lib init
```

The underlying principle is the same in each case: **match the method to when the DOM and data are in the state your work requires**, and always guard `updated()` with `changed.has()` to avoid runaway effects.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly map the three tasks to willUpdate, firstUpdated, and updated, and both mention the changedProperties parameter. Answer B is more thorough in its explanations, explicitly explaining why each alternative placement would be wrong, and adds the Task pattern as a modern best practice for async API calls. Answer A is solid but slightly less detailed in its reasoning and doesn't explain the pitfalls of alternative approaches as clearly.

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

<details><summary>haiku: baseline answer</summary>

# Lit Lifecycle Methods by Use Case

## (a) Compute derived property from `this.someInput` before render
**→ Use a getter or `willUpdate()`**

```typescript
// Option 1: Simple getter (preferred for most cases)
get derivedProperty() {
  return this.someInput?.toUpperCase();
}

render() {
  return html`<p>${this.derivedProperty}</p>`;
}

// Option 2: willUpdate() if computation is expensive
willUpdate(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.derivedProperty = expensiveComputation(this.someInput);
  }
}
```

**Why:** Getters are reactive and re-compute on every render. `willUpdate()` runs *before* render, so derived state is ready when `render()` executes. Avoids stale values.

---

## (b) One-time DOM measurement of child element after first render
**→ Use `firstUpdated()`**

```typescript
firstUpdated() {
  const child = this.shadowRoot?.querySelector('.my-child');
  this.childHeight = child?.offsetHeight;
}

render() {
  return html`<div class="my-child"></div>`;
}
```

**Why:** `firstUpdated()` runs once after the first render completes and DOM is painted. Perfect for measurements that require layout information. Using `updated()` would re-measure unnecessarily on every change.

---

## (c) Call external API after every render that changed an input
**→ Use `updated()`**

```typescript
updated(changedProperties) {
  if (changedProperties.has('userId')) {
    this.fetchUserData(this.userId);
  }
}

async fetchUserData(id) {
  const response = await fetch(`/api/users/${id}`);
  this.userData = await response.json();
}
```

**Why:** `updated()` runs *after* render completes and DOM is committed. You can check `changedProperties` to avoid unnecessary API calls. This is the right place for side effects that depend on rendered state.

---

## Quick Reference Table

| Task | Method | Timing | Why |
|------|--------|--------|-----|
| Derived properties | Getter or `willUpdate()` | Before render | Ensures values ready for template |
| First-time DOM measurement | `firstUpdated()` | After first render | DOM is painted; runs once |
| Side effects (API calls) | `updated()` | After every render | Can check what changed; DOM committed |

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
- `render()` must be pure (no side effects, no mutations); `willUpdate()` is the designated place for derived state
- If you compute in `render()`, you recompute on every render call (wasteful) and risk impure side effects
- If you compute in `updated()`, you've already rendered with stale data, forcing a second cycle

---

## (b) One-time DOM measurement of a child element after first render

**Use `firstUpdated(changedProperties)`**

```typescript
firstUpdated(changedProperties: PropertyValues) {
  const child = this.shadowRoot!.querySelector('.my-child');
  this.childHeight = child!.offsetHeight;
  // or: this.childWidth = child!.getBoundingClientRect().width
}

render() {
  return html`<div class="my-child">Content</div>`;
}
```

**Why:**
- Runs exactly once, after the first `render()` completes and the DOM is stable
- DOM is guaranteed to exist and be laid out (no `offsetHeight` of 0)
- Cleaner than `updated()` because you don't need to check `changedProperties` or guard against re-running
- If you measure in `render()`, the DOM hasn't been painted yet (measurements are unreliable)
- If you measure in `updated()` without a guard, you measure on every property change (wasteful and may trigger layout thrashing)

---

## (c) Calling an external API after every render that changed an input

**Use `updated(changedProperties)` with a guard, OR use `Task` (preferred)**

### Option 1: `updated()` with a guard (simple case)

```typescript
updated(changedProperties: PropertyValues) {
  if (changedProperties.has('userId')) {
    this.fetchUserData(this.userId);
  }
}

private async fetchUserData(id: string) {
  const response = await fetch(`/api/users/${id}`);
  this.userData = await response.json();
}
```

**Why:**
- Runs after every render, so you can check which properties changed
- Guard with `changedProperties.has()` to avoid redundant API calls
- Simple, one-off logic; no need for a full Task

### Option 2: `Task` (recommended for most cases)

```typescript
private _userTask = new Task(this, {
  task: async ([userId], { signal }) => {
    const response = await fetch(`/api/users/${userId}`, { signal });
    return response.json();
  },
  args: () => [this.userId],
});

render() {
  return this._userTask.render({
    pending: () => html`<p>Loading...</p>`,
    complete: (data) => html`<p>${data.name}</p>`,
    error: (e) => html`<p>Error: ${e.message}</p>`,
  });
}
```

**Why:**
- Automatic cancellation if `userId` changes before the fetch completes (prevents race conditions)
- Built-in status tracking (pending, complete, error) — no separate state variables
- Cleaner than `updated()` + manual state management
- Handles argument tracking automatically; re-runs only when `args()` changes
- Use `Task` whenever the work is request/response (fetch, DB query, etc.)

---

## Summary Table

| Work | Method | Why |
|------|--------|-----|
| Derived state (compute before render) | `willUpdate()` | Runs before render; pure; computed once per cycle |
| One-time DOM measurement | `firstUpdated()` | Runs once after first render; DOM is stable and laid out |
| API call on input change | `Task` (preferred) or `updated()` with guard | Task: auto-cancellation, status tracking, race prevention. `updated()`: simpler for one-off logic |

**Golden rule:** `render()` is pure (no side effects). Everything else goes in the lifecycle hooks that match the timing and frequency you need.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly map all three tasks to willUpdate, firstUpdated, and updated with good explanations. Answer A is more thorough in explaining the changedProperties parameter with concrete gating examples, adds important nuance about async data fetching with @lit/task, and provides richer 'why not' explanations for alternative approaches. Answer B is more concise but covers all the required criteria adequately. The depth and practical caveats in Answer A make it the stronger response overall.

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

<details><summary>opus: baseline answer</summary>

# Lit Lifecycle Method Placement

## (a) Compute derived property from `this.someInput` before render
**Use `willUpdate(changedProperties)`**

```js
willUpdate(changedProperties) {
  if (changedProperties.has('someInput')) {
    this.derived = expensiveCompute(this.someInput);
  }
}
```

**Why:** `willUpdate` runs *before* `render()` but after reactive properties have settled. Setting properties here is safe and won't trigger another update cycle. `render()` should stay pure — just return a template based on existing state — so derivation belongs in `willUpdate`.

(Avoid `update()` for this unless you need to control whether the update proceeds; `willUpdate` is the idiomatic hook.)

## (b) One-time DOM measurement after first render
**Use `firstUpdated(changedProperties)`**

```js
firstUpdated() {
  const rect = this.renderRoot
    .querySelector('#child')
    .getBoundingClientRect();
  this.childWidth = rect.width;
}
```

**Why:** `firstUpdated` fires exactly once, after the component's DOM has been rendered and is queryable via `this.renderRoot`. It's the canonical place for one-time DOM setup (measurements, third-party widget initialization, focus management on mount).

## (c) Call external API after every render that changed an input
**Use `updated(changedProperties)`**

```js
updated(changedProperties) {
  if (changedProperties.has('someInput')) {
    fetch(`/api/data?q=${this.someInput}`)
      .then(r => r.json())
      .then(data => { this.data = data; });
  }
}
```

**Why:** `updated` runs after every render (including the first), and `changedProperties` lets you gate side effects on what actually changed. Side effects like network calls, dispatching events, or imperatively poking other DOM belong here — never in `render()` (which must be pure) or `willUpdate` (which runs before DOM is committed).

---

### Quick mental model
| Phase | Method | Purpose |
|---|---|---|
| Before render | `willUpdate` | Compute derived state |
| Render | `render` | Pure template only |
| After first render | `firstUpdated` | One-time DOM setup |
| After every render | `updated` | Side effects, post-DOM work |

</details>

<details><summary>opus: skill-loaded answer</summary>

Great question — Lit's lifecycle is designed so each of these has a clear, distinct home. Here's the mapping:

## (a) Compute a derived property from `this.someInput` before render → `willUpdate(changedProperties)`

```ts
willUpdate(changed: PropertyValues<this>) {
  if (changed.has('someInput')) {
    this._derived = expensiveCompute(this.someInput);
  }
}
```

**Why:**
- Runs *before* `render()`, so `render()` can read `this._derived` and the DOM reflects it on the first paint.
- Runs *once per update cycle*, even if multiple properties changed.
- Setting properties here does **not** trigger another update (Lit batches it into the in-flight cycle).
- `render()` must stay pure — no derivation logic there.
- Doing this in `updated()` would cause a second render cycle (wasteful, can cause flicker).

Gate the work on `changedProperties.has('someInput')` so it only recomputes when the relevant input actually changed.

## (b) One-time DOM measurement of a child after first render → `firstUpdated(changedProperties)`

```ts
@query('#child') private _child!: HTMLElement;

firstUpdated() {
  const rect = this._child.getBoundingClientRect();
  this._initialWidth = rect.width;
}
```

**Why:**
- Called exactly once, after the first `render()` has produced real DOM.
- The shadow DOM is guaranteed to exist, so `this.shadowRoot`, `@query`, and `getBoundingClientRect()` all work.
- Doing it in `connectedCallback()` is too early — the element is in the tree but hasn't rendered yet.
- Doing it in `constructor()` is way too early — no DOM at all.
- Doing it in `updated()` would re-run on every change (wasteful for one-time setup).

If you need to *react* to size changes over time, that's a different job — use a `ResizeObserver` in a reactive controller, set up in `hostConnected()`.

## (c) Call an external API after every render where an input changed → `updated(changedProperties)`

```ts
updated(changed: PropertyValues<this>) {
  if (changed.has('userId')) {
    this._analytics.track('view', { userId: this.userId });
  }
}
```

**Why:**
- Runs after the DOM is updated, so it's safe for side effects that shouldn't block rendering.
- Receives `changedProperties`, so you can gate on the specific inputs that should trigger the call.
- `render()` must be pure — no `fetch()` or analytics calls there.
- `willUpdate()` runs *before* render, so side effects there happen before the user sees the new state — wrong order for "post-update notification."

**Important caveat:** if "external API" means async data fetching (request/response), `updated()` is the wrong tool. Use `@lit/task` instead:

```ts
private _userTask = new Task(this, {
  task: async ([userId], { signal }) => {
    const res = await fetch(`/api/users/${userId}`, { signal });
    return res.json();
  },
  args: () => [this.userId],
});
```

Task handles cancellation, race conditions, and pending/error/complete states. Use raw `updated()` for fire-and-forget side effects (analytics, logging, imperative third-party library calls).

## Summary table

| Work | Method | Runs | Purpose |
|------|--------|------|---------|
| Derive state for render | `willUpdate()` | Before every render | Computed values consumed by `render()` |
| One-time DOM setup | `firstUpdated()` | Once, after first render | Measure/wire up real DOM |
| Post-render side effects | `updated()` | After every render | Notify the outside world; gate on `changedProperties` |
| Async data fetching | `Task` (not a lifecycle method) | When args change | Cancellable request/response with status |

The mental model: **`willUpdate` prepares → `render` describes → `updated` reacts.** And `firstUpdated` is the one-shot variant of `updated` for setup that only makes sense once.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover all three rubric criteria well, but Answer A provides more concrete, realistic examples (SearchBox with multiple properties and states) and includes the important mutation/reference equality rule that helps developers avoid common pitfalls. Answer A's decision table and richer code examples make it more practically useful, though Answer B is also solid and slightly more concise.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies @property as public API / attribute-synced | tie |
| identifies @state as internal / no attribute | tie |
| mentions reactive trigger / re-render | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `Public` |
| identifies @state as internal / no attribute | ✓ | `Internal` |
| mentions reactive trigger / re-render | ✓ | `trigger re-render` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies @property as public API / attribute-synced | ✓ | `public` |
| identifies @state as internal / no attribute | ✓ | `internal` |
| mentions reactive trigger / re-render | ✓ | `triggers re-render` |

<details><summary>sonnet: baseline answer</summary>

## `@state()` vs `@property()` in Lit

Both decorators trigger re-renders when their values change, but they serve different purposes.

---

### `@property()` — Public API

Use this for values that should be **exposed to the outside world**.

```javascript
class MyButton extends LitElement {
  @property({ type: String }) label = 'Click me';
  @property({ type: Boolean }) disabled = false;
}
```

```html
<!-- These can be set from outside the component -->
<my-button label="Submit" disabled></my-button>
```

**Characteristics:**
- Reflected to/from HTML attributes (configurable)
- Shows up in the element's public API
- Can be set by parent components or plain HTML
- Included in `observedAttributes`

---

### `@state()` — Private Internal State

Use this for values that are **internal implementation details**.

```javascript
class MyDropdown extends LitElement {
  @property({ type: Array }) items = [];  // public input

  @state() private isOpen = false;        // internal state
  @state() private selectedIndex = -1;   // internal state
}
```

**Characteristics:**
- No attribute reflection
- Not part of the public API
- Signals to other developers "don't touch this from outside"
- Slightly more efficient (skips attribute handling)

---

### Side-by-Side Comparison

| Feature | `@property()` | `@state()` |
|---|---|---|
| Triggers re-render | ✅ | ✅ |
| Attribute reflection | ✅ (by default) | ❌ |
| Public API | ✅ | ❌ |
| Set via HTML attribute | ✅ | ❌ |
| TypeScript convention | `public` | `private` / `protected` |

---

### `@state()` is essentially shorthand

```javascript
// These are equivalent:
@state()
private isOpen = false;

@property({ state: true, attribute: false })
private isOpen = false;
```

---

### Quick Decision Rule

> **"Does anything outside this component need to set or read this value?"**
> - **Yes** → `@property()`
> - **No** → `@state()`

Think of it like class visibility: `@property()` is `public`, `@state()` is `private`.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## `@property()` vs `@state()` in Lit

Both decorators make a field **reactive** — Lit re-renders when the value changes — but they differ in visibility and how they interact with HTML attributes.

### `@property()` — public API

Use this for data the **outside world sets**, either via HTML attributes or JavaScript.

```typescript
@customElement('user-card')
class UserCard extends LitElement {
  @property() name = '';
  @property({ type: Number }) age = 0;
  @property({ type: Boolean }) disabled = false;
}
```

This gives you:
- An **HTML attribute** (`<user-card name="Alice">`)
- A **JavaScript property** (`el.name = 'Alice'`)
- Automatic string↔type conversion via the `type` option

### `@state()` — private internal state

Use this for data that **only the component itself manages**. It triggers re-renders but creates no attribute and signals to consumers that the field is an implementation detail.

```typescript
@customElement('toggle-button')
class ToggleButton extends LitElement {
  @property() label = 'Click me';  // public: callers set this

  @state() private _isOpen = false; // private: component manages this
  @state() private _count = 0;

  render() {
    return html`
      <button @click=${this._handleClick}>
        ${this.label} (${this._count})
      </button>
    `;
  }

  private _handleClick() {
    this._isOpen = !this._isOpen;
    this._count++;
  }
}
```

`@state()` is essentially shorthand for `@property({ state: true, attribute: false })`.

---

### Decision guide

| Question | Answer | Use |
|---|---|---|
| Should a parent component or HTML author set this? | Yes | `@property()` |
| Should it be settable as an HTML attribute? | Yes | `@property()` |
| Is it purely internal (UI state, derived data, flags)? | Yes | `@state()` |
| Should it appear in the element's public TypeScript API? | No | `@state()` |

---

### Common examples

```typescript
class SearchBox extends LitElement {
  // Public API — callers provide these
  @property() placeholder = 'Search…';
  @property({ type: Number }) maxResults = 10;

  // Internal state — component owns these
  @state() private _query = '';
  @state() private _isLoading = false;
  @state() private _results: Result[] = [];

  render() {
    return html`
      <input
        .value=${this._query}
        @input=${(e: InputEvent) =>
          this._query = (e.target as HTMLInputElement).value}
        placeholder=${this.placeholder}
      />
      ${this._isLoading ? html`<span>Loading…</span>` : nothing}
    `;
  }
}
```

---

### The mutation rule (applies to both)

Lit detects changes by **reference equality** (`!==`). Mutating an object or array in place won't trigger a re-render:

```typescript
// ❌ No re-render — same array reference
this._results.push(newItem);

// ✅ New reference — re-render triggered
this._results = [...this._results, newItem];
```

---

**Short version:** `@property()` is your component's public interface; `@state()` is its private memory. When in doubt, start with `@state()` and promote to `@property()` only if an external caller needs to set it.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core distinction well, but Answer B is more thorough and idiomatic. It explicitly notes that @state properties don't respond to HTML attributes (with a concrete example showing the attribute being ignored), covers type conversion for @property, includes the mutation rules for triggering re-renders, and uses TypeScript with proper access modifiers which is more idiomatic for Lit. Answer A is solid but slightly less complete on the attribute-binding nuances.

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
| mentions reactive trigger / re-render | ✓ | `trigger re-render` |

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
- Not exposed as HTML attributes
- Not reflected to attributes

## @property()
Use this for **public properties** that can be set from outside and should trigger re-renders.

```javascript
import { LitElement, html } from 'lit';
import { property } from 'lit/decorators.js';

class MyComponent extends LitElement {
  @property()
  name = 'World';

  render() {
    return html`<p>Hello ${this.name}!</p>`;
  }
}
```

**Characteristics:**
- Public API for your component
- Can be set as HTML attributes: `<my-component name="Alice"></my-component>`
- Changes trigger a re-render
- Can be configured to reflect back to attributes

## Quick Comparison

| Feature | @state() | @property() |
|---------|----------|------------|
| **Purpose** | Internal state | Public API |
| **Triggers re-render** | ✅ Yes | ✅ Yes |
| **Set from outside** | ❌ No | ✅ Yes |
| **HTML attribute** | ❌ No | ✅ Yes (by default) |
| **Convention** | `_privateState` | `publicProp` |

## Real-world example

```javascript
class UserCard extends LitElement {
  @property()
  userId = '';  // Set by parent: <user-card userId="123"></user-card>

  @state()
  _loading = false;  // Internal state

  @state()
  _userData = null;  // Internal state

  async connectedCallback() {
    super.connectedCallback();
    this._loading = true;
    this._userData = await fetchUser(this.userId);
    this._loading = false;
  }

  render() {
    return this._loading 
      ? html`<p>Loading...</p>`
      : html`<p>${this._userData.name}</p>`;
  }
}
```

**Rule of thumb:** Use `@property()` for anything the parent component needs to control, and `@state()` for everything else.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# @state() vs @property() in Lit

The distinction is about **API surface and reactivity scope**:

## @property() — Public API, Attribute Binding

Use `@property()` for inputs that:
- Are part of your component's **public contract** — consumers set them
- Should be **settable via HTML attributes** (with optional type conversion)
- Represent **external data flowing in** from a parent or attribute

```ts
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
```ts
const card = document.querySelector('user-card');
card.name = 'Bob';
```

## @state() — Private Internal State, No Attributes

Use `@state()` for state that:
- Is **internal to the component** — consumers don't set it
- Drives rendering but **doesn't need attribute binding**
- Changes in response to user interaction, async operations, or internal logic

```ts
@customElement('counter-button')
export class CounterButton extends LitElement {
  @state() private count = 0;

  render() {
    return html`<button @click=${this._increment}>Count: ${this.count}</button>`;
  }

  private _increment() {
    this.count++;
  }
}
```

**Consumers can't set it via attributes:**
```html
<!-- This does nothing; count is not an attribute -->
<counter-button count="5"></counter-button>
```

They *can* read it via JavaScript, but it's not part of the intended API:
```ts
const btn = document.querySelector('counter-button');
console.log(btn.count); // 0 (initial value)
```

## Key Differences

| Aspect | `@property()` | `@state()` |
|--------|--------------|-----------|
| **Attribute binding** | ✅ Yes (by default) | ❌ No |
| **Public API** | ✅ Yes | ❌ No (private by convention) |
| **Type conversion** | ✅ Configurable | ❌ N/A |
| **Reflection** | ✅ Optional (reflects to attribute) | ❌ No |
| **Use case** | External inputs | Internal state |

## Practical Example: Form Input Component

```ts
@customElement('my-input')
export class MyInput extends LitElement {
  // Public API: consumers set the label via attribute or property
  @property() label: string = '';

  // Internal state: tracks whether the input is focused
  @state() private isFocused = false;

  render() {
    return html`
      <label>${this.label}</label>
      <input
        @focus=${() => (this.isFocused = true)}
        @blur=${() => (this.isFocused = false)}
      />
      ${this.isFocused ? html`<p>Focused!</p>` : nothing}
    `;
  }
}
```

- `label` is `@property()` because the parent sets it
- `isFocused` is `@state()` because it's internal and changes on user interaction

## Mutation Rules Apply to Both

Both trigger re-renders on **reference change** (`!==`), not mutation:

```ts
// ❌ Won't trigger update
this.items.push(newItem);

// ✅ Triggers update
this.items = [...this.items, newItem];
```

This applies equally to `@property()` and `@state()`.

## When in Doubt

- **Can a parent/consumer reasonably set this?** → `@property()`
- **Is this only for internal bookkeeping?** → `@state()`

Most components have a mix: a few `@property()` inputs and several `@state()` fields tracking UI state, async progress, or derived values.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers are excellent and cover all three rubric criteria well. Answer A edges out B by providing the additional nuance of `@property({ attribute: false })` as a middle ground between fully public attribute-synced properties and fully private state, which is genuinely useful and often overlooked. Answer A also provides a more comprehensive comparison table and the 'full hierarchy' framing adds clarity. Answer B is slightly more concise and has a clean example, but A's extra depth on the attribute:false option makes it more complete.

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
| mentions reactive trigger / re-render | ✓ | `trigger re-render` |

<details><summary>opus: baseline answer</summary>

# `@property()` vs `@state()` in Lit

The core distinction is **public API vs. internal state**.

## `@property()` — Public, reactive API

Use this when the value should be settable from **outside** the component, typically as an HTML attribute or DOM property.

```ts
@property({ type: String })
name = 'world';
```

- Creates a corresponding **HTML attribute** (e.g., `<my-el name="Alice">`)
- Part of your component's public contract
- Triggers re-render on change
- Supports type conversion, attribute name customization, etc.

## `@state()` — Private, reactive internal state

Use this for values that are **internal** to the component and shouldn't be set by consumers.

```ts
@state()
private _isOpen = false;
```

- **No** corresponding HTML attribute
- Not part of the public API (often paired with `private`)
- Still triggers re-render on change
- Excluded from tooling that introspects public properties

## Quick decision guide

| Question | Use |
|---|---|
| Should a parent set this via attribute or property? | `@property()` |
| Is this derived from user interaction or async work inside the component? | `@state()` |
| Does it need to be reflected to/from an attribute? | `@property()` |
| Is it implementation detail that could change without breaking consumers? | `@state()` |

## Common example

```ts
@customElement('user-card')
class UserCard extends LitElement {
  // Public input — caller provides this
  @property() userId = '';

  // Internal — fetched data, not for callers to set
  @state() private _user?: User;
  @state() private _loading = false;

  async updated(changed: PropertyValues) {
    if (changed.has('userId')) {
      this._loading = true;
      this._user = await fetchUser(this.userId);
      this._loading = false;
    }
  }
}
```

**Rule of thumb:** if you'd document it in your component's README, it's `@property()`. If it's an implementation detail, it's `@state()`.

</details>

<details><summary>opus: skill-loaded answer</summary>

Great question — the distinction is about **API surface**, not behavior. Both trigger re-renders the same way; they differ in whether the field is part of your component's public contract.

## `@property()` — public input

Use when the field is part of how external code (HTML, parents, frameworks) configures your component:

- **Reflected to/from an HTML attribute** by default, so it can be set in markup: `<user-card name="Ada">`
- **Documented as part of your component's API**
- Type-converted from the attribute string (string, number, boolean, object via JSON)

```ts
@customElement('user-card')
export class UserCard extends LitElement {
  @property() name = '';
  @property({ type: Number }) age = 0;
  @property({ type: Boolean }) active = false;
}
```

## `@state()` — private internal state

Use when the field drives rendering but is an implementation detail:

- **Not associated with an attribute** — can't be set from HTML
- **Not part of the public API** — safe to rename/remove without breaking consumers
- Triggers re-renders identically to `@property`

```ts
@customElement('user-card')
export class UserCard extends LitElement {
  @property() userId = '';

  // Internal: fetched data, UI mode, hover state, etc.
  @state() private _expanded = false;
  @state() private _loadedUser: User | null = null;
}
```

## Quick decision rule

Ask: *"Should someone be able to set this from HTML or from a parent component?"*

- **Yes** → `@property()`
- **No, it's internal bookkeeping** → `@state()`

## Common cases

| Field | Decorator |
|---|---|
| `name`, `value`, `disabled`, `placeholder` | `@property()` |
| `_isOpen`, `_hoverIndex`, `_fetchedData` | `@state()` |
| Result of a `Task` you store on the instance | `@state()` |
| Anything prefixed with `_` (convention for private) | usually `@state()` |

## One subtle gotcha

Don't use `@property()` for objects you don't want serialized to attributes. If you have a complex object input from a parent, use `@property({ attribute: false })` — that keeps it as a public reactive input but disables the attribute machinery. It's the right choice for context providers/consumers and for object/array props that only ever come from JS, not HTML.

```ts
@property({ attribute: false }) user!: User;  // public, JS-only
```

So the full hierarchy is:
1. `@property()` — public, attribute-bindable
2. `@property({ attribute: false })` — public, JS-only
3. `@state()` — private, internal

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend unsafeHTML with XSS warnings and DOMPurify sanitization, but Answer B goes further with a practical trust-level table that helps developers make informed decisions, mentions server-side sanitization as an option, and includes a note about Markdown-to-HTML conversion. Answer B also avoids the slightly misleading claim in A that 'dropping a raw string into a template won't work' (it works, it just gets escaped), and provides more complete guidance overall.

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

  constructor() {
    super();
    this.apiContent = '<p>Hello from the <strong>API</strong>!</p>';
  }

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

The directive is called **`unsafe`** HTML for a reason. Since the content comes from a user-controlled API, you **must sanitize it first** to prevent **XSS attacks**. Use a library like [DOMPurify](https://github.com/cure53/DOMPurify) before passing it to the directive:

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

### Why not just use `innerHTML`?

Lit's `html` template tag **escapes strings by default** to prevent XSS, so dropping a raw string into a template won't work — `unsafeHTML` is the intended escape hatch for this use case.

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

  render() {
    return html`
      <div class="content">
        ${unsafeHTML(this._content)}
      </div>
    `;
  }
}
```

The name `unsafeHTML` is intentional — Lit's `html` template tag escapes interpolated strings by design to prevent XSS. This directive bypasses that protection entirely.

## ⚠️ Security Warning

**Never use `unsafeHTML` with user-controlled content without sanitizing it first.** An attacker can inject `<script>` tags, event handlers (`onerror`, `onload`), and other malicious markup.

Sanitize on the server before the API returns the content, or sanitize on the client using a library like [DOMPurify](https://github.com/cure53/DOMPurify):

```typescript
import DOMPurify from 'dompurify';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

render() {
  const clean = DOMPurify.sanitize(this._content);
  return html`<div>${unsafeHTML(clean)}</div>`;
}
```

## When `unsafeHTML` Is Appropriate

| Content source | Safe to use `unsafeHTML`? |
|---|---|
| Your own CMS / trusted backend | ✅ Yes, but still consider sanitizing |
| Third-party API you don't control | ⚠️ Only after sanitizing |
| User-submitted content | ❌ Never without sanitizing |
| Static strings in your own code | ✅ Yes |

If the API returns Markdown instead of HTML, convert it with a library (e.g. `marked`) and then sanitize the resulting HTML before passing it to `unsafeHTML`.

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Answer A correctly recommends the `unsafeHTML` directive (the idiomatic Lit approach) with strong XSS warnings and a DOMPurify sanitization example, while also suggesting structured data as the best practice. Answer B incorrectly steers users away from `unsafeHTML` toward raw `innerHTML` in `updated()`, which actually defeats Lit's templating system and is the anti-pattern the rubric explicitly warns against — Shadow DOM does NOT prevent script execution from innerHTML, making B's 'Why this works' explanation factually wrong.

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

The name `unsafeHTML` is intentional—it's **unsafe** because it bypasses Lit's built-in XSS protection. Only use this if:

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

Only use `unsafeHTML` when you have a legitimate need for dynamic HTML and can guarantee its safety.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Rendering User-Controlled HTML in Lit

**Do not use `unsafeHTML()`** for user-controlled content. It creates an XSS vulnerability.

## The Safe Approach: Use a `<div>` with `innerHTML`

The simplest safe way is to render an empty container and set its `innerHTML` after the element updates:

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
- The `<div>` is in Shadow DOM, so styles and scripts in the HTML won't leak out

## If You Must Sanitize First

If the API content might contain malicious scripts, sanitize it before setting `innerHTML`:

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
// ❌ NEVER do this with user content
render() {
  return html`${unsafeHTML(this.userContent)}`;
}
```

`unsafeHTML()` bypasses Lit's escaping entirely. If `userContent` contains `<img src=x onerror="alert('hacked')">`, it will execute.

## Summary

| Approach | Use When | Security |
|----------|----------|----------|
| `innerHTML` in `updated()` | Content is from your own API | Safe if you trust the source |
| `innerHTML` + `DOMPurify` | Content is from untrusted sources | Safe; removes scripts/dangerous attrs |
| `unsafeHTML()` | Never with user content | ❌ XSS risk |

**Recommendation:** Use `innerHTML` in `updated()` + `DOMPurify` if there's any doubt about the source.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the key criteria well, but Answer A is more thorough and better structured. It leads with a strong XSS warning, explicitly avoids recommending innerHTML, correctly names and demonstrates the unsafeHTML directive, and provides clearer guidance on when sanitization is required versus optional. Answer A also adds useful context like the 'text vs HTML' question and the Markdown alternative, making it more practically helpful for someone who may not fully understand the risk.

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

<details><summary>opus: baseline answer</summary>

# Rendering User-Controlled HTML in Lit

**Short answer:** Use Lit's `unsafeHTML` directive — but be very careful, because the name is a literal warning.

```js
import { LitElement, html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class MyElement extends LitElement {
  static properties = { apiHtml: { type: String } };

  render() {
    return html`<div>${unsafeHTML(this.apiHtml)}</div>`;
  }
}
customElements.define('my-element', MyElement);
```

By default, Lit escapes interpolated strings to prevent XSS. `unsafeHTML` bypasses that escaping and parses the string as HTML.

## ⚠️ Security warning

You said the HTML is **user-controlled** and comes from an API. That's exactly the scenario where `unsafeHTML` is dangerous: a malicious user could inject `<script>` tags, `<img onerror=...>`, or other XSS payloads.

**You should sanitize it first.** The standard choice is [DOMPurify](https://github.com/cure53/DOMPurify):

```js
import { html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import DOMPurify from 'dompurify';

render() {
  const clean = DOMPurify.sanitize(this.apiHtml);
  return html`<div>${unsafeHTML(clean)}</div>`;
}
```

## Note on Shadow DOM

If your component uses Shadow DOM (the Lit default), the injected HTML is somewhat isolated from the rest of the page's styles and scripts — but this is **not** a security boundary. Inline event handlers and `<script>` still execute in the same JS realm. Always sanitize.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Don't render user-controlled HTML strings — this is an XSS vulnerability

Before I answer the "how," I have to flag the security issue: **rendering user-controlled HTML from an API directly into your DOM is a cross-site scripting (XSS) vulnerability.** An attacker can inject `<script>` tags, `<img onerror=...>` handlers, event handlers, `<iframe>` elements, etc., that run with your site's privileges (steal cookies, session tokens, make authenticated requests, etc.).

Lit deliberately makes this hard. By design, Lit's `html` template tag escapes all interpolated string values:

```ts
render() {
  // This is SAFE — the string is rendered as text, tags are escaped
  return html`<div>${this.apiHtml}</div>`;
}
```

If `apiHtml` is `<script>alert(1)</script>`, the user sees the literal text, not an executed script. **In the vast majority of cases, this is what you want.** Ask yourself first: do you actually need HTML, or do you just need text? If text, you're already done.

## If you genuinely need to render HTML

You have two options, in order of preference:

### 1. Sanitize first, then use `unsafeHTML` (the right choice for user content)

Use a vetted sanitizer like [DOMPurify](https://github.com/cure53/DOMPurify) to strip dangerous content, then render with the `unsafeHTML` directive:

```ts
import { html } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import DOMPurify from 'dompurify';

render() {
  const clean = DOMPurify.sanitize(this.apiHtml);
  return html`<div>${unsafeHTML(clean)}</div>`;
}
```

DOMPurify removes scripts, event handlers, `javascript:` URLs, and other vectors while preserving safe markup like `<p>`, `<strong>`, `<a href>`, etc. You can configure allowed tags/attributes if you want to be stricter.

### 2. `unsafeHTML` alone (only for HTML you fully trust and control)

```ts
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

render() {
  return html`<div>${unsafeHTML(this.trustedHtml)}</div>`;
}
```

The directive is named `unsafeHTML` precisely because it bypasses Lit's escaping. **Only use it without sanitization if the HTML originates from a source you control end-to-end** (e.g., your own CMS where authors are trusted, server-rendered markup you generated yourself). API responses generally do not qualify, even from your own backend, unless that backend itself sanitizes.

## Recommendation

For your case (HTML from an API): **install DOMPurify and use option 1.** It's the simplest *safe* approach and adds maybe 20 KB. If the API content is actually plain text or has only a few formatting needs (bold, links), consider rendering it as text or parsing a restricted format like Markdown instead — both avoid the HTML-injection surface entirely.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality, correctness, and usefulness. They both explain INNER JOIN vs LEFT JOIN clearly with similar table examples and SQL queries. Answer A includes a slightly more detailed quick reference table (including the unmatched records pattern), while Answer B adds a useful note about RIGHT JOIN. Neither is materially better than the other.

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

**customers**
| id | name  |
|----|-------|
| 1  | Alice |
| 2  | Bob   |
| 3  | Carol |

**orders**
| id | customer_id | item    |
|----|-------------|---------|
| 1  | 1           | Laptop  |
| 2  | 1           | Mouse   |
| 3  | 2           | Monitor |

*(Carol has no orders)*

---

### INNER JOIN
```sql
SELECT customers.name, orders.item
FROM customers
INNER JOIN orders ON customers.id = orders.customer_id;
```
| name  | item    |
|-------|---------|
| Alice | Laptop  |
| Alice | Mouse   |
| Bob   | Monitor |

❌ Carol is **excluded** (no matching order)

---

### LEFT JOIN
```sql
SELECT customers.name, orders.item
FROM customers
LEFT JOIN orders ON customers.id = orders.customer_id;
```
| name  | item    |
|-------|---------|
| Alice | Laptop  |
| Alice | Mouse   |
| Bob   | Monitor |
| Carol | NULL    |

✅ Carol is **included** with NULL

---

### Quick Rule of Thumb

| Use case | Join type |
|----------|-----------|
| Only want records with matches on both sides | `INNER JOIN` |
| Want all records from left table, even without a match | `LEFT JOIN` |

> **Note:** A `RIGHT JOIN` is just a `LEFT JOIN` with the tables flipped — most developers stick with `LEFT JOIN` for consistency.

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
| 1  | 1           | Book    |
| 2  | 1           | Pen     |
| 3  | 2           | Notebook|

---

```sql
-- INNER JOIN: only customers WHO HAVE orders
SELECT customers.name, orders.item
FROM customers
INNER JOIN orders ON customers.id = orders.customer_id;
```
| name  | item     |
|-------|----------|
| Alice | Book     |
| Alice | Pen      |
| Bob   | Notebook |

> Charlie is **excluded** — no matching order.

---

```sql
-- LEFT JOIN: ALL customers, with orders if they exist
SELECT customers.name, orders.item
FROM customers
LEFT JOIN orders ON customers.id = orders.customer_id;
```
| name    | item     |
|---------|----------|
| Alice   | Book     |
| Alice   | Pen      |
| Bob     | Notebook |
| Charlie | NULL     |

> Charlie is **included** with `NULL` for the item.

---

### Quick Rule of Thumb

| Goal | Use |
|------|-----|
| Only matched records | `INNER JOIN` |
| All left records + matches | `LEFT JOIN` |
| Find unmatched left records | `LEFT JOIN` + `WHERE right.id IS NULL` |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality, correctness, and usefulness. They both clearly explain the difference between INNER JOIN and LEFT JOIN with appropriate table examples and SQL queries. Answer A includes a minor note about Lit scope which is slightly unnecessary, while Answer B uses slightly cleaner table aliases in the SQL, but neither difference is material.

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

Carol appears because `LEFT JOIN` keeps all rows from the left table (`users`), with `NULL` for the missing order.

---

**Note:** This is outside the Lit web component library scope, but happy to help with SQL questions!

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in content, accuracy, and usefulness. They use the same example data and queries, explain the same concepts, and include the same tip about using LEFT JOIN with IS NULL to find missing relationships. Minor differences like table aliases, column naming (item vs product), and formatting are cosmetic and do not materially affect quality.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

# INNER JOIN vs LEFT JOIN

**INNER JOIN**: Returns only rows that have matching values in *both* tables.

**LEFT JOIN**: Returns *all* rows from the left table, plus matched rows from the right table. Unmatched rows get `NULL` for right-table columns.

## Example

**users table:**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Charlie |

**orders table:**
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

**Result:**
| name  | product |
|-------|---------|
| Alice | Book    |
| Alice | Pen     |
| Bob   | Laptop  |

Charlie is excluded because he has no orders.

### LEFT JOIN
```sql
SELECT u.name, o.product
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

**Result:**
| name    | product |
|---------|---------|
| Alice   | Book    |
| Alice   | Pen     |
| Bob     | Laptop  |
| Charlie | NULL    |

Charlie appears with `NULL` since he has no matching orders.

**Tip**: Use `LEFT JOIN ... WHERE right_table.id IS NULL` to find rows that *don't* have a match (e.g., users with no orders).

</details>

<details><summary>opus: skill-loaded answer</summary>

# INNER JOIN vs LEFT JOIN

**INNER JOIN** returns only rows where there's a match in *both* tables.

**LEFT JOIN** returns *all* rows from the left table, plus matching rows from the right table. Where no match exists, columns from the right table are `NULL`.

## Example

Given these tables:

**users**
| id | name    |
|----|---------|
| 1  | Alice   |
| 2  | Bob     |
| 3  | Charlie |

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

Result — Charlie is excluded (no orders):

| name  | item   |
|-------|--------|
| Alice | Book   |
| Alice | Pen    |
| Bob   | Laptop |

### LEFT JOIN

```sql
SELECT users.name, orders.item
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```

Result — Charlie appears with `NULL`:

| name    | item   |
|---------|--------|
| Alice   | Book   |
| Alice   | Pen    |
| Bob     | Laptop |
| Charlie | NULL   |

## When to use which

- **INNER JOIN**: You only care about records that have related data in both tables (e.g., "show users who placed orders").
- **LEFT JOIN**: You want all records from the primary table even if related data is missing (e.g., "show all users and their orders, if any"). Useful for finding missing relationships with `WHERE right_table.id IS NULL`.

</details>

---
