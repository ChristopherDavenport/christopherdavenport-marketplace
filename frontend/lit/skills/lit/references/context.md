# @lit/context — Deep Dive

**Properties down, events up handles most cases.** Reach for context only when a value is needed by descendants 3+ levels deep AND the intermediate components have no reason to know about it (theme, current user, app config, logger). For shallow trees or when intermediates legitimately mediate the value, properties are simpler, type-safer, and don't introduce a runtime lookup.

`@lit/context` shares data across a component tree without prop drilling. It uses the W3C Community Group Context Protocol — an event-based system where consumers dispatch `context-request` events that bubble up to providers.

Install: `npm i @lit/context`

## Core API

### `createContext<T>(key)`

Creates a typed context object used as a key by providers and consumers.

```ts
import { createContext } from '@lit/context';

export interface UserData {
  id: number;
  name: string;
  email: string;
}

export const userContext = createContext<UserData>(Symbol('user'));
export const themeContext = createContext<Theme>(Symbol('theme'));
```

Use `Symbol()` for keys — strings risk collisions across packages.

### `@provide()` Decorator

Makes a property's value available to all descendant consumers of the same context.

```ts
import { LitElement } from 'lit';
import { property } from 'lit/decorators.js';
import { provide } from '@lit/context';
import { userContext, type UserData } from './contexts.js';

@customElement('app-root')
class AppRoot extends LitElement {
  @provide({ context: userContext })
  @property({ attribute: false })
  user: UserData = { id: 1, name: 'Alice', email: 'alice@co.com' };

  render() {
    return html`<slot></slot>`;
  }
}
```

When the decorated property changes (new reference), all subscribed consumers update automatically.

### `@consume()` Decorator

Receives a context value from the nearest ancestor provider.

```ts
import { LitElement, html } from 'lit';
import { property } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { userContext, type UserData } from './contexts.js';

@customElement('user-badge')
class UserBadge extends LitElement {
  @consume({ context: userContext, subscribe: true })
  @property({ attribute: false })
  user?: UserData;

  render() {
    return html`<span>${this.user?.name ?? 'Guest'}</span>`;
  }
}
```

**`subscribe: true` is critical.** Without it, the consumer gets the value once on connection and never updates when the provider changes. Default is `false`.

### `ContextProvider` Controller

Manual provider without decorators — more control over when and how values are set.

```ts
import { ContextProvider } from '@lit/context';
import { userContext, type UserData } from './contexts.js';

@customElement('app-shell')
class AppShell extends LitElement {
  private _userProvider = new ContextProvider(this, {
    context: userContext,
    initialValue: { id: 1, name: 'Alice', email: 'alice@co.com' },
  });

  updateUser(user: UserData) {
    this._userProvider.setValue(user);
  }
}
```

### `ContextConsumer` Controller

Manual consumer without decorators.

```ts
import { ContextConsumer } from '@lit/context';
import { userContext, type UserData } from './contexts.js';

@customElement('user-display')
class UserDisplay extends LitElement {
  private _user?: UserData;

  private _userConsumer = new ContextConsumer(this, {
    context: userContext,
    callback: (user) => {
      this._user = user;
      this.requestUpdate();
    },
    subscribe: true,
  });

  render() {
    return html`<p>${this._user?.name}</p>`;
  }
}
```

## How Context Flows

```
Consumer dispatches 'context-request' event
  ↓  (bubbles: true, composed: true — pierces Shadow DOM)
Event travels up the DOM tree
  ↓
Nearest ancestor Provider intercepts
  ↓
Provider calls back with its current value
  ↓
If subscribe: true, provider stores the callback
and calls it again on every setValue()
```

The event-based protocol means context works across Shadow DOM boundaries and is framework-agnostic — a Lit provider can serve a vanilla web component consumer, and vice versa.

## Context Definitions File

Keep all context definitions in a shared module:

```ts
// contexts.ts
import { createContext } from '@lit/context';

export interface UserData {
  id: number;
  name: string;
  email: string;
}

export interface AppTheme {
  primary: string;
  surface: string;
  isDark: boolean;
}

export interface AppConfig {
  apiBase: string;
  version: string;
}

export const userContext = createContext<UserData>(Symbol('user'));
export const themeContext = createContext<AppTheme>(Symbol('theme'));
export const configContext = createContext<AppConfig>(Symbol('config'));
```

Both providers and consumers import from this file, ensuring type safety and key consistency.

## Multiple Contexts per Component

A component can provide and consume any number of contexts:

```ts
@customElement('app-root')
class AppRoot extends LitElement {
  @provide({ context: userContext })
  @property({ attribute: false })
  user: UserData = { id: 1, name: 'Alice', email: 'a@co.com' };

  @provide({ context: themeContext })
  @property({ attribute: false })
  theme: AppTheme = { primary: '#0066cc', surface: '#fff', isDark: false };

  @provide({ context: configContext })
  @property({ attribute: false })
  config: AppConfig = { apiBase: '/api', version: '1.0.0' };

  render() {
    return html`<slot></slot>`;
  }
}
```

## Nested Providers (Overriding Context)

A provider lower in the tree shadows the one above it for its subtree:

```ts
@customElement('admin-section')
class AdminSection extends LitElement {
  @provide({ context: themeContext })
  @property({ attribute: false })
  theme: AppTheme = { primary: '#cc0000', surface: '#fff3f3', isDark: false };

  render() {
    return html`<slot></slot>`;
  }
}
```

```html
<app-root>
  <!-- children here get blue theme from app-root -->
  <user-badge></user-badge>

  <admin-section>
    <!-- children here get red theme from admin-section -->
    <user-badge></user-badge>
  </admin-section>
</app-root>
```

Consumers always receive from the **closest ancestor provider**.

## Late-Arriving Providers with `ContextRoot`

If consumers connect to the DOM before their provider exists (lazy loading, dynamic rendering), the context request has no handler.

`ContextRoot` solves this by capturing unfulfilled requests and replaying them when a provider appears:

```ts
import { ContextRoot } from '@lit/context';

@customElement('app-shell')
class AppShell extends LitElement {
  private _contextRoot = new ContextRoot(this);

  render() {
    return html`
      <!-- consumer renders immediately -->
      <user-badge></user-badge>

      <!-- provider loads lazily -->
      ${this._showApp ? html`<app-root></app-root>` : nothing}
    `;
  }
}
```

Attach `ContextRoot` to a common ancestor (usually the app shell). It handles:
- Consumers that upgrade before providers
- Providers added dynamically after consumers
- Providers that are conditionally rendered

## When to Use Context vs Alternatives

| Need | Use | Why |
|------|-----|-----|
| App-wide services (user, theme, config, logger) | **Context** | Avoids drilling through every intermediate component |
| Direct parent-child data binding | **Properties** | Simpler, no overhead, explicit API |
| Shared mutable state many components read and write | **Signals** | Deep reactivity, automatic invalidation |
| Request/response async tied to component inputs | **Task** | Status tracking, cancellation |
| State that rarely changes after initialization | **Context without `subscribe`** | One-time delivery, minimal overhead |
| State that changes frequently at runtime | **Context with `subscribe: true`** | Consumers stay in sync |

### Context + Signals

For deep-reactive state shared across the component tree, provide a signal through context. Consumers read `signal.get()` and update via the `SignalWatcher` mixin or `watch()` directive — no `subscribe: true` round-trip per change, because the signal handles its own observation.

See [signals.md](signals.md) for the integration pattern and the full signals API.

## Common Pitfalls

### Consumer never receives a value

**Cause:** No provider ancestor exists, or provider connects after consumer.
**Fix:** Add `ContextRoot` to a common ancestor. Provide a fallback default on the consumer property.

### Consumer doesn't update when provider value changes

**Cause:** `subscribe` defaults to `false`.
**Fix:** Set `subscribe: true`:
```ts
@consume({ context: userContext, subscribe: true })
```

### Provider update doesn't reach consumers

**Cause:** Mutating the existing object instead of creating a new reference.
**Fix:** Same immutability rule as reactive properties:
```ts
// WRONG
this.user.name = 'Bob';

// CORRECT
this.user = { ...this.user, name: 'Bob' };
```

### Context key collision across packages

**Cause:** Using string keys that match by coincidence.
**Fix:** Always use `Symbol()`:
```ts
createContext<User>(Symbol('user'));  // unique per call
```

### Provider in a closed Shadow DOM

**Cause:** `context-request` events have `composed: true` and bubble out of shadow roots. This is not the issue. But if a provider uses a non-standard event listener setup, it may miss requests.
**Fix:** Use `@provide` or `ContextProvider` — they handle the event plumbing correctly.

## Best Practices

- **Use `Symbol()` for context keys** — guarantees uniqueness; strings risk collisions
- **Define contexts in a shared module** — single source of truth for types and keys
- **Set `subscribe: true`** on consumers of data that changes at runtime
- **Use `attribute: false`** on context-provided properties — context values should not come from HTML attributes
- **Provide at the highest reasonable level** — usually the app root or shell
- **Use `ContextRoot`** if providers may load dynamically or lazily
- **Never mutate context values in place** — create new references so subscribers are notified
- **Handle missing providers gracefully** — default values or optional types on consumer properties
- **Prefer decorators** (`@provide`/`@consume`) for simplicity; use controllers (`ContextProvider`/`ContextConsumer`) when you need programmatic control (conditional subscription, dynamic setValue)
- **Keep context values serializable** when possible — makes testing and debugging easier
