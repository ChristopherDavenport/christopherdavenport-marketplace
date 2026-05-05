# Reactive Properties — Deep Dive

## Property Options Reference

```ts
@property({
  type: String,              // Converter hint for attribute ↔ property
  attribute: true,           // true (auto-name) | false (no attribute) | 'custom-name'
  reflect: false,            // true = write property back to attribute on change
  hasChanged: (newVal, oldVal) => newVal !== oldVal,  // Custom change detection
  converter: {               // Custom attribute ↔ property conversion
    fromAttribute: (value: string, type?) => parsed,
    toAttribute: (value: any, type?) => string | null
  },
  noAccessor: false          // true = skip getter/setter generation (rare)
})
```

## Built-in Type Conversion (attribute → property)

When an HTML attribute string needs to become a JS property value:

| `type` | Attribute `"hello"` becomes | Notes |
|--------|---------------------------|-------|
| `String` | `"hello"` | Default if no type set |
| `Number` | `NaN` (would be `42` for `"42"`) | Uses `Number()` |
| `Boolean` | `true` | Attribute presence = true, absence = false |
| `Object` | `JSON.parse("hello")` → error | Attribute must be valid JSON |
| `Array` | `JSON.parse("hello")` → error | Attribute must be valid JSON |

### Boolean Attribute Behavior

Boolean attributes follow HTML semantics — presence means `true`, absence means `false`:

```html
<my-el disabled></my-el>     <!-- disabled = true -->
<my-el></my-el>              <!-- disabled = false -->
<my-el disabled="false"></my-el>  <!-- disabled = true! (attribute exists) -->
```

With `reflect: true`, setting the property to `false` removes the attribute entirely.

## Custom Converter

For types that don't map cleanly to JSON:

```ts
@property({
  converter: {
    fromAttribute(value: string | null): Date | null {
      return value ? new Date(value) : null;
    },
    toAttribute(value: Date | null): string | null {
      return value?.toISOString() ?? null;
    }
  },
  reflect: true
})
date: Date | null = null;
```

## Custom `hasChanged`

Default comparison is strict inequality (`!==`). Override for deep comparison or tolerance:

```ts
@property({
  hasChanged(newVal: number, oldVal: number) {
    return Math.abs(newVal - oldVal) > 0.01;
  }
})
temperature = 0;
```

## `@state()` Behavior

`@state()` is equivalent to `@property({ state: true })`:
- Triggers reactive updates like `@property`
- No HTML attribute generated
- Not part of the component's public API
- Same mutation rules apply (new references for objects/arrays)

## Triggering Updates Manually

When you must mutate in place:

```ts
this.items.push(newItem);
this.requestUpdate();           // Schedule update with no specific property
this.requestUpdate('items');    // Schedule update for a named property
```

`requestUpdate()` is batched — multiple calls in the same microtask produce one update cycle.

## `getUpdateComplete()` for Subclasses

If your component renders child components that also update asynchronously:

```ts
protected override async getUpdateComplete(): Promise<boolean> {
  const result = await super.getUpdateComplete();
  await this._childEl?.updateComplete;
  return result;
}
```

This ensures `await this.updateComplete` waits for the full subtree.

## Common Pitfalls

**1. Class field initializers and decorator ordering:**
```ts
// Safe — decorator sets up the accessor before the initializer runs
@property() name = 'default';
```
In standard decorators (TC39), this works correctly. In legacy decorators (TypeScript experimental), initialize in the constructor if you see issues.

**2. Reflecting complex types:**
Don't reflect `Object` or `Array` — it serializes to `[object Object]` in the attribute. Reflect only primitive types (String, Number, Boolean).

**3. Attribute name casing:**
HTML attributes are case-insensitive. Lit auto-lowercases: `@property() myProp` → attribute `myprop`. Use the `attribute` option for custom names:
```ts
@property({ attribute: 'my-prop' }) myProp = '';
```

**4. Setting properties before element is defined:**
Properties set before `customElements.define()` runs will be overwritten by the class field initializer. Use `connectedCallback` or defer property setting.

**5. Component not re-rendering after array/object mutation:**
Lit detects changes by reference equality (`!==`). In-place mutations like `this.items.push(x)` keep the same reference, so no update fires.
```ts
// BROKEN
this.items.push(newItem);

// FIX — new reference
this.items = [...this.items, newItem];

// OR — explicit request
this.items.push(newItem);
this.requestUpdate('items');
```

**6. Custom event not received by parent across Shadow DOM:**
Events stop at shadow boundaries by default. Without `composed: true`, the event never escapes the component's shadow root.
```ts
// BROKEN — stays inside shadow DOM
this.dispatchEvent(new CustomEvent('change'));

// FIX — crosses shadow boundary
this.dispatchEvent(new CustomEvent('change', { bubbles: true, composed: true }));
```
The typed event class pattern (below) bakes this into the constructor so it can't be forgotten.

## Decorators Reference

All decorators are imported from `lit/decorators.js`.

| Decorator | Purpose |
|-----------|---------|
| `@customElement('tag-name')` | Register custom element (equivalent to `customElements.define`) |
| `@property({...})` | Reactive public property with optional attribute binding |
| `@state()` | Reactive internal state (no attribute) |
| `@query('#id')` | Lazy `this.renderRoot.querySelector('#id')` — caches result |
| `@queryAll('.cls')` | `this.renderRoot.querySelectorAll('.cls')` |
| `@queryAsync('#id')` | Waits for `updateComplete` then queries — returns `Promise<Element>` |
| `@eventOptions({...})` | Set `addEventListener` options (capture, passive, once) on event handlers |

### `@query` vs `@queryAsync`

Use `@query` when the element is always in the template. Use `@queryAsync` when the element may not exist until after an async update (e.g., conditionally rendered content).

## Global Tag Name Registration

Always register your component in `HTMLElementTagNameMap` so that `document.querySelector`, `createElement`, and framework type-checking can infer the element type from its tag name:

```ts
@customElement('my-element')
class MyElement extends LitElement { /* ... */ }

declare global {
  interface HTMLElementTagNameMap {
    'my-element': MyElement;
  }
}
```

This enables:
- `document.querySelector('my-element')` returns `MyElement` instead of `Element`
- `document.createElement('my-element')` returns `MyElement`
- Framework template type-checking (Angular, Vue, etc.) recognizes the element

Place the `declare global` block at the bottom of the same file that defines the component.

## Typed Custom Events

Define concrete event classes instead of using inline `new CustomEvent(...)`. This gives consumers type-safe access to event data without casting:

```ts
export class CountChangedEvent extends Event {
  static readonly type = 'count-changed';
  constructor(public readonly count: number) {
    super(CountChangedEvent.type, { bubbles: true, composed: true });
  }
}

// Dispatching:
this.dispatchEvent(new CountChangedEvent(this._count));

// Listening (typed — no casting needed):
el.addEventListener(CountChangedEvent.type, (e: CountChangedEvent) => {
  console.log(e.count);
});
```

**Why concrete event classes over inline `new CustomEvent`:**
- Event name is a single `static readonly type` — no string typos across files
- Payload is typed properties — no `e.detail` casting
- Importable by consumers — auto-complete and refactoring work
- Co-locate event definition with or near the component that dispatches it
