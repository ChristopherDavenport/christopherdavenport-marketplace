# Lifecycle — Deep Dive

## Full Lifecycle Sequence

```
Element created (constructor)
        ↓
Element added to DOM (connectedCallback)
        ↓
   ┌─── Reactive Update Cycle ──────────────────┐
   │ Property changes → requestUpdate()          │
   │        ↓                                    │
   │ shouldUpdate(changedProperties) → false? STOP│
   │        ↓ true                               │
   │ willUpdate(changedProperties)               │
   │        ↓                                    │
   │ update(changedProperties)                   │
   │   └── render() → TemplateResult             │
   │        ↓                                    │
   │ firstUpdated(changedProperties) [first only]│
   │        ↓                                    │
   │ updated(changedProperties)                  │
   │        ↓                                    │
   │ updateComplete resolves                     │
   └─────────────────────────────────────────────┘
        ↓
Element removed from DOM (disconnectedCallback)
```

## Method Signatures and Rules

### `constructor()`

```ts
constructor() {
  super();
  this.count = 0;        // Initialize property defaults
  this._handler = this._onResize.bind(this);  // Bind methods for listeners
}
```

**Rules:**
- Must call `super()` first
- No attribute access (element not in DOM yet)
- No `this.renderRoot` or Shadow DOM access
- Set default property values here

### `connectedCallback()`

```ts
connectedCallback(): void {
  super.connectedCallback();
  window.addEventListener('resize', this._handler);
  this._observer = new IntersectionObserver(this._onIntersect);
  this._observer.observe(this);
}
```

**Rules:**
- Must call `super.connectedCallback()` — this triggers the first update cycle
- Fires every time the element is added to the DOM (including moves)
- Setup external event listeners, observers, timers here
- `this.renderRoot` exists but may not have rendered content yet

### `disconnectedCallback()`

```ts
disconnectedCallback(): void {
  super.disconnectedCallback();
  window.removeEventListener('resize', this._handler);
  this._observer?.disconnect();
  this._abortController?.abort();
}
```

**Rules:**
- Must call `super.disconnectedCallback()`
- Clean up everything set up in `connectedCallback`
- May fire temporarily during DOM moves (element is re-connected immediately after)

### `shouldUpdate(changedProperties)`

```ts
shouldUpdate(changedProperties: PropertyValues<this>): boolean {
  return changedProperties.has('criticalProp');
}
```

**Purpose:** Gate whether the update cycle proceeds. Returning `false` skips render.

**Use case:** Performance optimization — skip renders when only irrelevant properties changed.

**Default:** Returns `true`.

### `willUpdate(changedProperties)`

```ts
willUpdate(changedProperties: PropertyValues<this>): void {
  if (changedProperties.has('firstName') || changedProperties.has('lastName')) {
    this._fullName = `${this.firstName} ${this.lastName}`;
  }
}
```

**Purpose:** Compute derived state before rendering.

**Rules:**
- Changes to reactive properties here DO update `changedProperties` for `render()` and `updated()`
- But they do NOT trigger an additional update cycle
- No DOM access (render hasn't happened yet in this cycle)
- Preferred over `updated()` for derived state because it doesn't cause extra cycles

### `render()`

```ts
render(): TemplateResult {
  return html`<p>${this._fullName}</p>`;
}
```

**Rules:**
- Must be pure — no side effects, no property mutations
- Returns a `TemplateResult` (from `html` tag) or `nothing`
- Called by `update()` — rarely override `update()` directly

### `firstUpdated(changedProperties)`

```ts
firstUpdated(changedProperties: PropertyValues<this>): void {
  this.renderRoot.querySelector('#input')?.focus();
  this._chart = new Chart(this.renderRoot.querySelector('canvas'));
}
```

**Purpose:** One-time setup that requires rendered DOM.

**Use cases:**
- Focus management
- Initialize third-party libraries on DOM elements
- Measure DOM dimensions

**Runs:** Exactly once, after the first render.

### `updated(changedProperties)`

```ts
updated(changedProperties: PropertyValues<this>): void {
  if (changedProperties.has('selected')) {
    this.dispatchEvent(new SelectionChangedEvent(this.selected));
  }
}
```

**Purpose:** Post-render side effects.

**Rules:**
- Runs after every render (including first)
- Changing reactive properties here DOES trigger another update cycle — be careful of infinite loops
- DOM reflects the latest rendered state
- Good for: dispatching events, updating non-Lit-managed DOM, triggering animations

### `changedProperties` Map

The `changedProperties` parameter is a `Map<string, unknown>` (typed as `PropertyValues<this>`) where:
- Keys are property names that changed
- Values are the **previous** values (before the update)

```ts
updated(changedProperties: PropertyValues<this>) {
  if (changedProperties.has('userId')) {
    const previousId = changedProperties.get('userId');
    console.log(`Changed from ${previousId} to ${this.userId}`);
  }
}
```

## `updateComplete` Promise

```ts
async handleAction() {
  this.data = newData;
  await this.updateComplete;  // Wait for DOM to reflect new data
  const height = this.renderRoot.querySelector('.content')?.offsetHeight;
}
```

**Resolves:** After `updated()` completes and the DOM is stable.

**Returns:** `Promise<boolean>` — `true` if no further updates are pending.

### Extending `updateComplete` in Subclasses

```ts
protected override async getUpdateComplete(): Promise<boolean> {
  const result = await super.getUpdateComplete();
  await this._childComponent?.updateComplete;
  return result;
}
```

## Async Lifecycle Patterns

### Dispatching Events Safely

```ts
async _onSelect(item: Item) {
  this.selected = item;
  await this.updateComplete;
  this.dispatchEvent(new ItemSelectedEvent(item));
}
```

### Coordinating with Child Components

```ts
async firstUpdated() {
  const child = this.renderRoot.querySelector('child-component');
  await child?.updateComplete;
  // Child is fully rendered
}
```

### Waiting for External Resources

```ts
private _imageLoaded = new Promise<void>(resolve => {
  this._resolveImage = resolve;
});

render() {
  return html`<img @load=${() => this._resolveImage()} src=${this.src}>`;
}

protected override async getUpdateComplete() {
  const result = await super.getUpdateComplete();
  await this._imageLoaded;
  return result;
}
```
