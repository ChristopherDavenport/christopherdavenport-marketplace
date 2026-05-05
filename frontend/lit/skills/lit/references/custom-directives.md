# Custom Directives — Deep Dive

Built-in directives (`repeat`, `classMap`, etc.) cover common cases. When you need reusable template logic that isn't covered, write a custom directive.

## When to Write a Custom Directive

| Need | Use | Why |
|------|-----|-----|
| Reusable template transformation | **Custom directive** | Runs in the template expression slot; direct DOM Part access |
| Reusable lifecycle-aware logic | **Reactive controller** | Hooks into host lifecycle; owns state |
| Simple value transformation | **Helper function** | No directive overhead; just returns a value |

Directives are the right choice when you need to:
- Interact directly with the DOM Part (the slot where the expression lives)
- Control whether the DOM updates at all (`noChange`)
- Do async work tied to a template position (`AsyncDirective`)

## Simple Directive (Synchronous)

Extend `Directive` and implement `render()`:

```ts
import { Directive, directive } from 'lit/directive.js';

class FormatDateDirective extends Directive {
  render(date: Date, locale = 'en-US', options?: Intl.DateTimeFormatOptions) {
    return new Intl.DateTimeFormat(locale, options).format(date);
  }
}

export const formatDate = directive(FormatDateDirective);
```

Usage:

```ts
html`<p>Created: ${formatDate(this.createdAt, 'en-US', { dateStyle: 'long' })}</p>`
```

`render()` returns a value that Lit renders into the template. It's called on every host render.

## Stateful Directive with `update()`

Override `update()` to access the DOM `Part` and previous state. Return `noChange` to skip the DOM update:

```ts
import { Directive, directive } from 'lit/directive.js';
import { noChange } from 'lit';
import type { Part } from 'lit/directive.js';

class ChangedDirective extends Directive {
  private _previousValue: unknown;

  update(part: Part, [value]: [unknown]) {
    if (value === this._previousValue) {
      return noChange;
    }
    this._previousValue = value;
    return this.render(value);
  }

  render(value: unknown) {
    return value;
  }
}

export const changed = directive(ChangedDirective);
```

### `update()` vs `render()`

- **`render()`** — returns the value to render. Called by `update()` by default.
- **`update(part, args)`** — called every render cycle. Has access to the `Part` (DOM position). Return `noChange` to skip DOM writes. Call `this.render()` to delegate to the render method.

Always implement `render()` even if you override `update()` — `render()` is used for SSR where `Part` is not available.

## Part Types

The `Part` passed to `update()` tells you where the directive is used:

| Part Type | Template Position | Example |
|-----------|------------------|---------|
| `ChildPart` | Child content | `html\`<div>${directive()}</div>\`` |
| `AttributePart` | Attribute value | `html\`<div attr=${directive()}>\`` |
| `BooleanAttributePart` | Boolean attribute | `html\`<div ?hidden=${directive()}>\`` |
| `PropertyPart` | Property binding | `html\`<div .prop=${directive()}>\`` |
| `EventPart` | Event listener | `html\`<div @click=${directive()}>\`` |

Import part types from `lit/directive.js` for type checking:

```ts
import { ChildPart, AttributePart } from 'lit/directive.js';

update(part: Part, args: unknown[]) {
  if (part.type === PartType.ATTRIBUTE) {
    // attribute-specific logic
  }
}
```

## AsyncDirective

For directives that do async work (fetching, observing, subscribing). Provides `setValue()` to push updates after the initial render, plus `disconnected()` / `reconnected()` lifecycle hooks.

```ts
import { AsyncDirective, directive } from 'lit/async-directive.js';
import { noChange } from 'lit';

class FetchTextDirective extends AsyncDirective {
  private _url?: string;
  private _abortController?: AbortController;

  render(url: string) {
    if (url !== this._url) {
      this._url = url;
      this._fetch(url);
    }
    return noChange;
  }

  private async _fetch(url: string) {
    this._abortController?.abort();
    this._abortController = new AbortController();
    try {
      const res = await fetch(url, { signal: this._abortController.signal });
      const text = await res.text();
      this.setValue(text);
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        this.setValue(`Error: ${(e as Error).message}`);
      }
    }
  }

  disconnected() {
    this._abortController?.abort();
  }

  reconnected() {
    if (this._url) this._fetch(this._url);
  }
}

export const fetchText = directive(FetchTextDirective);
```

Usage:

```ts
html`<pre>${fetchText(this.logUrl)}</pre>`
```

### AsyncDirective Lifecycle

| Method | When | Purpose |
|--------|------|---------|
| `render(args)` | Every host render | Return initial value or `noChange` |
| `update(part, args)` | Every host render | Access Part; call `render()` or return `noChange` |
| `setValue(value)` | Anytime after render | Push async result to the template position |
| `disconnected()` | Host disconnects from DOM | Clean up subscriptions, abort fetches |
| `reconnected()` | Host reconnects to DOM | Re-establish subscriptions |

### `setValue()` Rules

- Can only be called after the directive has rendered at least once
- Triggers a re-render of just the Part this directive occupies
- Do NOT call from within `render()` or `update()` — those return synchronously

## `noChange` vs `nothing`

| Sentinel | Import | Effect |
|----------|--------|--------|
| `noChange` | `lit` | Skip the DOM update entirely — leave previous value in place |
| `nothing` | `lit` | Render nothing (removes content / removes attribute) |

Use `noChange` in directives to avoid unnecessary DOM writes. Use `nothing` when you want to clear the output.

## Example: Conditional Permission Directive

Shows content only if the user has a required role:

```ts
import { Directive, directive } from 'lit/directive.js';
import { nothing } from 'lit';
import type { TemplateResult } from 'lit';

class WhenAllowedDirective extends Directive {
  render(userRoles: string[], requiredRole: string, content: TemplateResult) {
    return userRoles.includes(requiredRole) ? content : nothing;
  }
}

export const whenAllowed = directive(WhenAllowedDirective);
```

Usage:

```ts
html`
  ${whenAllowed(this.userRoles, 'admin', html`
    <button @click=${this._deleteAll}>Delete All</button>
  `)}
`
```

## Example: Tooltip Attribute Directive

Adds a native tooltip via the `title` attribute, with sanitization:

```ts
import { Directive, directive } from 'lit/directive.js';
import type { Part, AttributePart } from 'lit/directive.js';
import { PartType } from 'lit/directive.js';
import { noChange } from 'lit';

class TooltipDirective extends Directive {
  private _lastValue?: string;

  update(part: Part, [text]: [string]) {
    if (part.type !== PartType.ELEMENT) {
      throw new Error('tooltip directive must be used on an element');
    }
    if (text === this._lastValue) return noChange;
    this._lastValue = text;
    return this.render(text);
  }

  render(text: string) {
    return text;
  }
}

export const tooltip = directive(TooltipDirective);
```

## Best Practices

- **Always implement `render()`** — even if you override `update()`. `render()` is the SSR-compatible path.
- **Return `noChange`** when nothing changed — avoids unnecessary DOM writes
- **Clean up in `disconnected()`** for `AsyncDirective` — abort fetches, unsubscribe, clear timers
- **Re-establish in `reconnected()`** — the element may re-enter the DOM (e.g., moving nodes)
- **Keep directives focused** — one concern per directive; compose with multiple directives if needed
- **Prefer a helper function** if you don't need Part access or async lifecycle — directives have overhead
- **Prefer a reactive controller** if the logic needs host lifecycle hooks (connectedCallback, etc.) rather than template-position hooks
- **Type your directive's parameters** — `directive()` infers types from the `render()` signature
