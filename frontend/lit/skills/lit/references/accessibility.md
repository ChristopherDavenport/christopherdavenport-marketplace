# Accessibility in Lit & Shadow DOM

Shadow DOM provides style encapsulation but introduces specific accessibility challenges. This reference covers the patterns needed to build accessible Lit components.

## The Core Problem: ID References Don't Cross Shadow Boundaries

ARIA attributes like `aria-labelledby`, `aria-describedby`, and `aria-controls` reference other elements by ID. IDs are scoped to their root — a shadow root's IDs are invisible to the document, and vice versa.

```ts
// BROKEN — the label is in light DOM, the input is in shadow DOM
// aria-labelledby="name-label" can't find the element
render() {
  return html`<input aria-labelledby="name-label">`;
}
```

## Solution: ElementInternals AOM Properties

Use `ElementInternals` to set ARIA properties imperatively. These attach directly to the element's accessibility node — no ID references needed:

```ts
@customElement('labeled-input')
class LabeledInput extends LitElement {
  static formAssociated = true;
  private _internals = this.attachInternals();

  @property() label = '';

  willUpdate(changed: PropertyValues<this>) {
    if (changed.has('label')) {
      this._internals.ariaLabel = this.label;
    }
  }

  connectedCallback() {
    super.connectedCallback();
    this._internals.role = 'textbox';
  }

  render() {
    return html`<input>`;
  }
}
```

### Available AOM Properties

All standard ARIA properties are available on `ElementInternals`:

```ts
this._internals.role = 'button';
this._internals.ariaLabel = 'Close dialog';
this._internals.ariaDisabled = 'true';
this._internals.ariaExpanded = 'false';
this._internals.ariaSelected = 'true';
this._internals.ariaChecked = 'true';
this._internals.ariaValueNow = '50';
this._internals.ariaValueMin = '0';
this._internals.ariaValueMax = '100';
this._internals.ariaRequired = 'true';
this._internals.ariaInvalid = 'true';
this._internals.ariaHasPopup = 'listbox';
```

Note: Values are always strings (matching ARIA attribute conventions).

## Focus Management

### `delegatesFocus`

When `delegatesFocus` is set on the shadow root, clicking anywhere in the component's shadow DOM focuses the first focusable element inside:

```ts
@customElement('focus-input')
class FocusInput extends LitElement {
  static shadowRootOptions = {
    ...LitElement.shadowRootOptions,
    delegatesFocus: true,
  };

  render() {
    return html`
      <label>Name</label>
      <input type="text">
    `;
  }
}
```

Clicking the label (or any part of the shadow DOM) focuses the `<input>`.

### Manual Focus Management

For components that wrap focusable elements, forward focus explicitly:

```ts
@customElement('custom-button')
class CustomButton extends LitElement {
  @query('button') private _button!: HTMLButtonElement;

  focus(options?: FocusOptions) {
    this._button.focus(options);
  }

  render() {
    return html`<button><slot></slot></button>`;
  }
}
```

### Roving Tabindex

For composite widgets (toolbars, listboxes, tab lists), use roving tabindex: only one child is in the tab order at a time, arrow keys move between children.

```ts
@customElement('tab-list')
class TabList extends LitElement {
  @state() private _activeIndex = 0;
  @property({ type: Array }) tabs: string[] = [];

  private _onKeyDown(e: KeyboardEvent) {
    let newIndex = this._activeIndex;
    switch (e.key) {
      case 'ArrowRight': newIndex = (this._activeIndex + 1) % this.tabs.length; break;
      case 'ArrowLeft': newIndex = (this._activeIndex - 1 + this.tabs.length) % this.tabs.length; break;
      case 'Home': newIndex = 0; break;
      case 'End': newIndex = this.tabs.length - 1; break;
      default: return;
    }
    e.preventDefault();
    this._activeIndex = newIndex;
    this._focusTab(newIndex);
  }

  private _focusTab(index: number) {
    const tabs = this.shadowRoot?.querySelectorAll('[role="tab"]');
    (tabs?.[index] as HTMLElement)?.focus();
  }

  connectedCallback() {
    super.connectedCallback();
    this.setAttribute('role', 'tablist');
  }

  render() {
    return html`
      ${this.tabs.map((tab, i) => html`
        <button
          role="tab"
          tabindex=${i === this._activeIndex ? 0 : -1}
          aria-selected=${i === this._activeIndex}
          @keydown=${this._onKeyDown}
          @click=${() => { this._activeIndex = i; }}
        >${tab}</button>
      `)}
    `;
  }
}
```

**Pattern:** One element has `tabindex="0"` (in tab order), all others have `tabindex="-1"` (focusable but not in tab order). Arrow keys shift which element gets `tabindex="0"` and call `.focus()`.

## Keyboard Interaction

Interactive custom elements must handle keyboard events. The WAI-ARIA Authoring Practices define expected keys per widget role:

### Buttons

```ts
private _onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    this._activate();
  }
}

render() {
  return html`
    <div role="button" tabindex="0" @click=${this._activate} @keydown=${this._onKeyDown}>
      <slot></slot>
    </div>
  `;
}
```

### Listboxes

| Key | Action |
|-----|--------|
| `ArrowDown` | Move focus to next option |
| `ArrowUp` | Move focus to previous option |
| `Home` | Move focus to first option |
| `End` | Move focus to last option |
| `Enter` / `Space` | Select focused option |
| Type-ahead | Focus option matching typed characters |

### Dialogs

| Key | Action |
|-----|--------|
| `Escape` | Close dialog |
| `Tab` | Cycle focus within dialog (trap focus) |
| `Shift+Tab` | Cycle focus backward within dialog |

## Focus Trapping for Dialogs

Modal dialogs must trap focus — Tab/Shift+Tab should cycle within the dialog, not escape to the page behind:

```ts
private _trapFocus(e: KeyboardEvent) {
  if (e.key !== 'Tab') return;

  const focusable = this.shadowRoot?.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );
  if (!focusable?.length) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}
```

## Slots and Accessibility

Slotted content (light DOM projected into shadow DOM) retains its position in the accessibility tree at its **original light DOM location**, not where the `<slot>` appears in the shadow tree.

This means:
- ARIA attributes on slotted elements work normally
- IDs on slotted elements are in the document scope (not shadow scope)
- Screen readers see slotted content in its light DOM order

```ts
// The <button> is in light DOM — its ARIA attributes work normally
html`
  <card-layout>
    <button slot="actions" aria-label="Delete item">X</button>
  </card-layout>
`
```

## Screen Reader Considerations

### Expose Role, Name, State

Every interactive component needs:
1. **Role** — what the component is (`button`, `textbox`, `listbox`, `dialog`, etc.)
2. **Accessible name** — what to announce (`ariaLabel` or text content)
3. **State** — current status (`ariaExpanded`, `ariaChecked`, `ariaSelected`, etc.)

```ts
connectedCallback() {
  super.connectedCallback();
  this._internals.role = 'checkbox';
  this._internals.ariaLabel = this.label;
}

updated() {
  this._internals.ariaChecked = String(this.checked);
}
```

### Live Regions

For dynamic content updates that screen readers should announce:

```ts
render() {
  return html`
    <div aria-live="polite" aria-atomic="true">
      ${this._statusMessage}
    </div>
  `;
}
```

Use `aria-live="polite"` for non-urgent updates, `"assertive"` for urgent ones.

## Common Pitfalls

### Using `aria-labelledby` with IDs across shadow boundaries
**Problem:** The ID can't be resolved across shadow roots.
**Fix:** Use `this._internals.ariaLabel` instead of `aria-labelledby`. For associations within the same shadow root, ID references work fine.

### Missing keyboard handlers on custom interactive elements
**Problem:** A `<div>` with `role="button"` doesn't respond to Enter/Space.
**Fix:** Add `@keydown` handler for expected keys. Or use a native `<button>` inside the shadow DOM — it gets keyboard support for free.

### Forgetting `tabindex="0"` on custom interactive elements
**Problem:** Custom interactive element can't be reached via Tab.
**Fix:** Add `tabindex="0"` to the interactive element. If it wraps a native focusable element, use `delegatesFocus` instead.

### Focus escaping a modal dialog
**Problem:** Tab key moves focus outside the dialog.
**Fix:** Implement focus trapping (see pattern above). Consider using the native `<dialog>` element with `showModal()` which handles this automatically.

### Not updating ARIA state on property changes
**Problem:** Screen reader announces stale state.
**Fix:** Update `this._internals.ariaChecked`, `ariaExpanded`, etc. in `updated()` or `willUpdate()` whenever the corresponding property changes.

## Best Practices

- **Use native elements when possible** — `<button>`, `<input>`, `<dialog>`, `<details>` come with built-in accessibility
- **Use `ElementInternals` AOM** over `aria-*` attributes for anything on the host element
- **Test with a screen reader** — VoiceOver (Mac), NVDA (Windows), or Orca (Linux)
- **Follow WAI-ARIA Authoring Practices** — defines expected keyboard interactions per widget role
- **Provide visible focus indicators** — never remove `:focus` outlines without a replacement; use `:focus-visible` for keyboard-only indicators
- **Use `delegatesFocus`** on components that wrap a single focusable element
- **Roving tabindex** for composite widgets — one Tab stop, arrow keys within
- **Trap focus in modals** — or use native `<dialog>` with `showModal()`
