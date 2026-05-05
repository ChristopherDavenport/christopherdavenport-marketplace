# API — Deep Dive

`@lit-labs/router` exports two reactive controller classes plus the supporting types and event. Both controllers attach to a `LitElement` host and call `host.requestUpdate()` whenever the matched route changes.

## Class hierarchy

- **`Routes`** — a `ReactiveController` you attach to any `LitElement` to declare routes scoped to that component. Has no global side effects.
- **`Router extends Routes`** — adds global `click` and `popstate` listeners on `window`. There must be exactly one `Router` instance on a page.

Both implement `ReactiveController` (`hostConnected` / `hostDisconnected`).

## Module entry points

```ts
import {Router, Routes, RoutesConnectedEvent} from '@lit-labs/router';
// or
import {Router} from '@lit-labs/router/router.js';
import {Routes, RoutesConnectedEvent} from '@lit-labs/router/routes.js';
```

The barrel `index.ts` is literally:

```ts
export * from './routes.js';
export {Router} from './router.js';
```

## Constructors

Identical signatures — `Router` inherits from `Routes`.

```ts
constructor(
  host: ReactiveControllerHost & HTMLElement,
  routes: Array<RouteConfig>,
  options?: { fallback?: BaseRouteConfig }
)
```

- **`host`** — the LitElement (must be both a reactive controller host AND an `HTMLElement`, because `Routes` dispatches a DOM event from it for parent-child wiring).
- **`routes`** — array of `RouteConfig`. Stored as `this.routes` and **mutable at runtime**; you can push/replace entries to add routes dynamically.
- **`options.fallback`** — a `BaseRouteConfig` matched if no other route matches. Internally treated as `{...fallback, path: '/*'}`.

The difference between `Router` and `Routes` is in `hostConnected` / `hostDisconnected`. `Router` adds global listeners on connect and immediately calls `this.goto(window.location.pathname)` so the initial render reflects the current URL.

## `RouteConfig` types

Routes can be configured one of two ways. The discriminator is which property is present (`path` for string patterns, `pattern` for pre-built `URLPattern` objects).

```ts
interface BaseRouteConfig {
  name?: string | undefined;
  render?: (params: { [key: string]: string | undefined }) => unknown;
  enter?: (params: { [key: string]: string | undefined })
    => Promise<boolean> | boolean;
}

interface PathRouteConfig extends BaseRouteConfig {
  path: string;          // becomes `new URLPattern({pathname: path})`
}

interface URLPatternRouteConfig extends BaseRouteConfig {
  pattern: URLPattern;   // pre-built URLPattern, full control
}

type RouteConfig = PathRouteConfig | URLPatternRouteConfig;
```

### Field semantics

- **`path`** — pathname pattern (URLPattern syntax). Cached internally per route via `WeakMap`. Compiled lazily on first match.
- **`pattern`** — full `URLPattern` if you need things like host/protocol matching. The router only ever calls `pattern.exec({pathname})`, so non-pathname components are matched against the current URL.
- **`render(params)`** — returns the template (`unknown`, since Lit's `TemplateResult` flows through `outlet()`). Optional; if omitted, the matched route renders nothing.
- **`enter(params)`** — guard / data loader. Return `false` (or `Promise<false>`) to **cancel** navigation. Any other return value (including `undefined`) lets it proceed. The router awaits async `enter` before updating params and re-rendering.
- **`name`** — declared in the type but **not used by the router itself**. There is no `linkTo('routeName', params)` API today. Treat `name` as informational / forward-compatible.

## Methods

Both `Router` and `Routes` expose:

| Member | Signature | Behavior |
|---|---|---|
| `goto(pathname)` | `(pathname: string) => Promise<void>` | Programmatic navigation. Finds matching route, runs `enter`, sets current params, calls `host.requestUpdate()`, and recursively dispatches the tail-group portion to child `Routes`. Throws `Error("No route found for ${pathname}")` if no route matches AND no fallback is configured AND `routes` is non-empty. **Does NOT call `history.pushState`.** |
| `outlet()` | `() => unknown` | Returns the template from the currently matched route's `render`, or `undefined`. Call inside your `render()` template. |
| `link(pathname?)` | `(pathname?: string) => string` | Resolves a path string against the parent chain. See algorithm below. |
| `params` (getter) | `{[key: string]: string \| undefined}` | The currently matched route's params (URLPattern `pathname.groups`). |
| `routes` (field) | `Array<RouteConfig>` | The mutable route table. Push/splice to alter at runtime. |
| `fallback` (field) | `BaseRouteConfig \| undefined` | Mutable fallback. |
| `hostConnected()` / `hostDisconnected()` | — | Reactive controller lifecycle. `Router` overrides these to manage global listeners. |

## The `link()` algorithm

From source:

```ts
link(pathname?: string): string {
  if (pathname?.startsWith('/')) return pathname;        // absolute, no resolution
  if (pathname?.startsWith('.')) throw new Error('Not implemented');
  pathname ??= this._currentPathname;
  return (this._parentRoutes?.link() ?? '') + pathname;
}
```

Implications:

- `link('/foo')` → `'/foo'` (treats leading `/` as absolute, returns as-is).
- `link('foo')` → parent's currently matched pathname + `'foo'`. Useful for child routes to build URLs without hard-coding the parent prefix.
- `link()` (no arg) → the parent chain's matched pathname + this controller's matched pathname. Effectively the current URL of this nested router.
- `link('./foo')` or any leading-dot relative form → throws **"Not implemented"**.

## `outlet()` — there is no template directive

Despite plausible guesses, **there is no Lit directive in this package**. You call `this._routes.outlet()` inside your `render()`. The matched route's template is rendered into wherever you place `${this._routes.outlet()}`.

```ts
render() {
  return html`
    <header>...</header>
    <main>${this._router.outlet()}</main>
    <footer>...</footer>
  `;
}
```

If no route is matched and no fallback is configured, `outlet()` returns `undefined` and Lit renders nothing in that slot.

## `RoutesConnectedEvent`

The internal mechanism for parent-child wiring:

```ts
class RoutesConnectedEvent extends Event {
  static readonly eventName = 'lit-routes-connected';
  readonly routes: Routes;
  onDisconnect?: () => void;
}
```

When a `Routes` controller's host connects, it dispatches a `bubbles: true, composed: true` event up the DOM tree. The nearest ancestor `Routes` catches it (via `stopImmediatePropagation`), registers the child, and stops propagation.

Authors of routed components don't usually interact with this directly, but it is exported and the `HTMLElementEventMap` is augmented so listeners are typed:

```ts
declare global {
  interface HTMLElementEventMap {
    'lit-routes-connected': RoutesConnectedEvent;
  }
}
```

Listening manually:

```ts
this.addEventListener('lit-routes-connected', (e) => {
  console.log('child Routes connected:', e.routes);
  e.onDisconnect = () => console.log('child disconnected');
});
```

## Common Pitfalls

- **`goto()` doesn't update `history`.** It only updates the matched route and re-renders. For programmatic navigation, pair with `history.pushState({}, '', path)`. See [navigation.md](navigation.md).
- **`link('./foo')` throws.** Use absolute (`/foo`) or child-relative without leading dot (`foo`).
- **`name` field is decorative.** No named-route lookup exists. Build URLs with `link()` or by hand.
- **Routes mutability.** Pushing into `this.routes` after construction works, but the new routes are only matched on the next `goto()`. If you need them active immediately, call `goto(location.pathname)` after pushing.
- **`Router` self-initialises.** On `hostConnected` it calls `this.goto(window.location.pathname)`. If your initial route's `enter` is async, the first render will be `undefined` until the promise resolves.
- **Constructor expects `HTMLElement`.** A bare `ReactiveControllerHost` (e.g. a non-element host) won't satisfy the type — `Routes` needs to dispatch DOM events from it.

See also: [url-patterns.md](url-patterns.md) for `path` syntax, [nested-routing.md](nested-routing.md) for how `RoutesConnectedEvent` is used in practice, [lifecycle.md](lifecycle.md) for `enter` semantics.
