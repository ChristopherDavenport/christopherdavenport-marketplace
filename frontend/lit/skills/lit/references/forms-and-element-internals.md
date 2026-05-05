# Form-Associated Custom Elements & ElementInternals

By default, custom elements are invisible to `<form>` — they don't participate in form submission, validation, or reset. The Form-Associated Custom Elements API and `ElementInternals` solve this.

## Making a Component Form-Associated

Two requirements:

```ts
@customElement('custom-input')
class CustomInput extends LitElement {
  static formAssociated = true;
  private _internals = this.attachInternals();

  // ...
}
```

1. **`static formAssociated = true`** — tells the browser this element participates in forms
2. **`this.attachInternals()`** — returns an `ElementInternals` object for interacting with the form

Without both, the component is invisible to its parent `<form>`.

## Setting the Form Value

Call `setFormValue()` whenever the component's value changes:

```ts
@customElement('custom-input')
class CustomInput extends LitElement {
  static formAssociated = true;
  private _internals = this.attachInternals();

  @property() name = '';
  @state() private _value = '';

  private _onInput(e: InputEvent) {
    this._value = (e.target as HTMLInputElement).value;
    this._internals.setFormValue(this._value);
  }

  render() {
    return html`<input .value=${this._value} @input=${this._onInput}>`;
  }
}
```

When the form submits, `FormData` will contain `{ [this.name]: this._value }`.

### Value Types

`setFormValue()` accepts:
- `string` — simple text value
- `File` — file upload
- `FormData` — multiple name/value pairs for complex components
- `null` — clears the value (component excluded from submission)

```ts
// Multiple values from one component
const data = new FormData();
data.append('start', this._start);
data.append('end', this._end);
this._internals.setFormValue(data);
```

## Form Lifecycle Callbacks

These optional callbacks let the component respond to form events:

```ts
@customElement('custom-input')
class CustomInput extends LitElement {
  static formAssociated = true;
  private _internals = this.attachInternals();

  @state() private _value = '';

  formAssociatedCallback(form: HTMLFormElement | null): void {
    // Called when the element is associated with (or disassociated from) a form
  }

  formResetCallback(): void {
    // Called when the form resets — restore default value
    this._value = '';
    this._internals.setFormValue('');
  }

  formDisabledCallback(disabled: boolean): void {
    // Called when the element's disabled state changes via fieldset or form
    this.requestUpdate();
  }

  formStateRestoreCallback(state: string, mode: string): void {
    // Called when the browser restores form state (back/forward navigation)
    this._value = state;
    this._internals.setFormValue(state);
  }
}
```

## Constraint Validation

Use `setValidity()` to integrate with the browser's built-in validation system:

```ts
private _validate() {
  if (!this._value) {
    this._internals.setValidity(
      { valueMissing: true },
      'This field is required',
      this.shadowRoot?.querySelector('input') ?? undefined
    );
  } else if (this._value.length < 3) {
    this._internals.setValidity(
      { tooShort: true },
      'Must be at least 3 characters',
      this.shadowRoot?.querySelector('input') ?? undefined
    );
  } else {
    this._internals.setValidity({});
  }
}

private _onInput(e: InputEvent) {
  this._value = (e.target as HTMLInputElement).value;
  this._internals.setFormValue(this._value);
  this._validate();
}
```

### `setValidity()` Parameters

```ts
setValidity(
  flags: ValidityStateFlags,   // Which constraints are violated
  message?: string,             // Custom validation message
  anchor?: HTMLElement           // Element to anchor the validation popup to
)
```

**ValidityStateFlags** mirrors the native `ValidityState` interface:
`valueMissing`, `typeMismatch`, `patternMismatch`, `tooLong`, `tooShort`, `rangeUnderflow`, `rangeOverflow`, `stepMismatch`, `badInput`, `customError`

### Checking and Reporting Validity

```ts
// Programmatic check (no UI)
const isValid = this._internals.checkValidity();

// Check and show browser validation UI
const isValid = this._internals.reportValidity();

// Read current message
const msg = this._internals.validationMessage;
```

## ARIA via Accessibility Object Model (AOM)

`ElementInternals` provides imperative ARIA properties that avoid the ID-reference problem in Shadow DOM:

```ts
constructor() {
  super();
  this._internals = this.attachInternals();
  this._internals.role = 'textbox';
  this._internals.ariaLabel = 'Email address';
  this._internals.ariaRequired = 'true';
}

updated() {
  this._internals.ariaInvalid = String(!this._internals.checkValidity());
}
```

This is superior to attribute-based ARIA in Shadow DOM because:
- No ID references needed — `aria-labelledby` requires IDs that don't cross shadow boundaries
- Properties are set on the element's accessibility node directly
- Works consistently across shadow roots

See [references/accessibility.md](accessibility.md) for comprehensive Shadow DOM accessibility patterns.

## Complete Example: Custom Text Input

```ts
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('text-field')
class TextField extends LitElement {
  static formAssociated = true;
  private _internals = this.attachInternals();

  static styles = css`
    :host { display: inline-block; }
    :host([internals-invalid]) input { border-color: red; }
    input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font: inherit; }
    .error { color: red; font-size: 12px; margin-top: 4px; }
  `;

  @property() name = '';
  @property() label = '';
  @property({ type: Boolean }) required = false;
  @property({ type: Number }) minlength = 0;
  @state() private _value = '';
  @state() private _touched = false;

  connectedCallback() {
    super.connectedCallback();
    this._internals.role = 'textbox';
    if (this.label) this._internals.ariaLabel = this.label;
  }

  private _onInput(e: InputEvent) {
    this._value = (e.target as HTMLInputElement).value;
    this._internals.setFormValue(this._value);
    this._validate();
  }

  private _onBlur() {
    this._touched = true;
  }

  private _validate() {
    if (this.required && !this._value) {
      this._internals.setValidity({ valueMissing: true }, 'Required');
    } else if (this.minlength && this._value.length < this.minlength) {
      this._internals.setValidity({ tooShort: true }, `Min ${this.minlength} chars`);
    } else {
      this._internals.setValidity({});
    }
  }

  formResetCallback() {
    this._value = '';
    this._touched = false;
    this._internals.setFormValue('');
    this._internals.setValidity({});
  }

  render() {
    const showError = this._touched && !this._internals.checkValidity();
    return html`
      ${this.label ? html`<label>${this.label}</label>` : nothing}
      <input
        .value=${this._value}
        @input=${this._onInput}
        @blur=${this._onBlur}
        ?required=${this.required}
      >
      ${showError ? html`<div class="error">${this._internals.validationMessage}</div>` : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'text-field': TextField;
  }
}
```

Usage:
```html
<form @submit=${this._onSubmit}>
  <text-field name="email" label="Email" required></text-field>
  <text-field name="name" label="Name" minlength="2"></text-field>
  <button type="submit">Submit</button>
</form>
```

## Common Pitfalls

### Form submission ignores the component
**Cause:** Missing `static formAssociated = true`.
**Fix:** Add the static field. Without it, the browser doesn't know the element participates in forms.

### Value not in FormData
**Cause:** Never calling `this._internals.setFormValue()`.
**Fix:** Call it in every input handler and whenever the value changes programmatically.

### Validation popup anchored to wrong element
**Cause:** Missing the third `anchor` argument in `setValidity()`.
**Fix:** Pass the inner input element: `this._internals.setValidity(flags, msg, this.shadowRoot.querySelector('input'))`.

### Component doesn't reset with the form
**Cause:** Missing `formResetCallback()`.
**Fix:** Implement the callback and clear internal state + call `setFormValue(null)` or `setFormValue('')`.

### ARIA attributes not reflected to assistive technology
**Cause:** Using `aria-*` HTML attributes on elements inside Shadow DOM instead of `ElementInternals` AOM properties.
**Fix:** Use `this._internals.role`, `this._internals.ariaLabel`, etc.
