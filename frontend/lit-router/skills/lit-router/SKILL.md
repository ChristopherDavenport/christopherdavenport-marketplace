---
name: lit-router
description: >
  Client routing for Lit via @lit-labs/router — Router and Routes
  controllers, URLPattern matching, nested routes, History API navigation.
  Use for files importing from '@lit-labs/router'. Not for the
  web-component-router skill (Banno/JH stack) or other routers.
---

# @lit-labs/router

`@lit-labs/router` is a small (~3 KB) client router for Lit. It ships two `ReactiveController` classes — `Router` (one per page; installs global `click` and `popstate` listeners) and `Routes` (any number; for nested route sections) — and matches URLs with the standard `URLPattern` API. There is no custom element and no template directive: you call `controller.outlet()` inside `render()`.

## Scope

Covers: `Router` and `Routes` reactive controllers, `URLPattern` matching, nested routing, click interception, programmatic navigation with the History API, the `enter` lifecycle hook, fallback (404) routes, and the library's known pitfalls (trailing-slash matching, `goto` doesn't `pushState`, no hash routing, no leave guards, no named-route lookup).

Status: **Lit Labs**, current version `0.1.4`, peer-deps `lit ^2 || ^3`. Pre-1.0 — flag the experimental status when introducing it.

## Quickstart

```ts
import {LitElement, html} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Router, Routes} from '@lit-labs/router';

@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/',         render: () => html`<home-page></home-page>`},
    {path: '/users/*',  render: () => html`<users-section></users-section>`},
    {
      path: '/products/:id',
      enter: async ({id}) => { await loadProduct(id!); },
      render: ({id}) => html`<product-page .id=${id}></product-page>`,
    },
  ], {fallback: {render: () => html`<not-found></not-found>`}});

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/users/">Users</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}

@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',     render: () => html`<user-list></user-list>`},
    {path: ':id',  render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);
  render() { return html`${this._routes.outlet()}`; }
}
```

## Instructions

### Setting up the root router

1. `npm install @lit-labs/router` (and `urlpattern-polyfill` if targeting non-Chromium browsers — import it before `@lit-labs/router`).
2. In your top-level `LitElement`, instantiate `new Router(this, routes, {fallback?})` as a private field.
3. Define each route as `{path, render, enter?}`. `path` is a `URLPattern` pathname string.
4. Place `${this._router.outlet()}` inside the host's `render()` template.
5. Configure the dev/prod server to serve `index.html` for unknown paths (SPA fallback).

Consult [references/api.md](references/api.md) for full constructor and method signatures, and [references/url-patterns.md](references/url-patterns.md) for pattern syntax.

### Adding a nested route section

1. In the parent router, add a route with a path ending in `/*` (e.g. `/users/*`) whose `render` returns a child component.
2. In that child component, instantiate `new Routes(this, [...])` (NOT `Router`).
3. Child paths are matched against the parent's tail group, so use `path: ''` for the index, `path: ':id'` for `/users/:id`, etc. — no leading slash, no parent prefix.
4. Render `${this._routes.outlet()}` in the child.
5. Always link to the parent with a trailing slash (`/users/`), not bare (`/users`) — see [references/pitfalls.md](references/pitfalls.md).

Consult [references/nested-routing.md](references/nested-routing.md) for the wiring mechanism (a bubbling `lit-routes-connected` event), tail-group propagation, and a complete example.

### Loading data on route entry

1. Add an `enter(params)` callback to the route — sync or async.
2. Return `false` (or `Promise<false>`) to cancel the navigation; any other value (including `undefined`) lets it proceed.
3. For full-blocking preloads, `await` the data inside `enter`. The router awaits the promise before updating params and re-rendering.
4. For component-local loading state with cancellation, prefer leaving `enter` empty and using `@lit/task` inside the routed component with the route param as an arg.
5. Be defensive against stale results — there is no built-in cancellation token if a second `goto()` fires mid-`enter`.

Consult [references/lifecycle.md](references/lifecycle.md) for `enter` semantics, race-condition handling, and `enter` vs `Task`.

### Navigating programmatically

1. Whenever possible, render an `<a href>` and let the click handler do the work — `Router` intercepts same-origin clicks with no `target`, no modifier keys, and no `download`/`rel="external"`.
2. For programmatic navigation, **always** pair `history.pushState` with `router.goto`:
   ```ts
   history.pushState({}, '', path);
   this._router.goto(path);
   ```
3. `goto()` alone updates the rendered route but does NOT change the URL bar — this is a known gotcha, not your bug.
4. Use `controller.link('local-path')` to build hrefs that respect a parent route prefix.
5. Hash-based routing is not supported; `URLPattern` matching only inspects `pathname`.

Consult [references/navigation.md](references/navigation.md) for the full click-interception rule list, `popstate` handling, and `link()` resolution.

### Rendering an active-link nav

1. There is no built-in active-link helper and no global "route changed" event.
2. Read `this._router.params` and/or `location.pathname` inside `render()`; the router calls `requestUpdate()` on every successful `goto()`, so render runs again on every navigation.
3. Compute an `active` class with a small helper, e.g. `active(href) => location.pathname === href ? 'active' : ''`.
4. For hierarchical matching (any sub-route of `/users`), test `location.pathname.startsWith('/users/')`.
5. For per-route side effects on navigation, wrap the route's `enter` callback rather than waiting for an event.

Consult [references/navigation.md](references/navigation.md) for the full active-link pattern.

### Testing a routed component

1. Isolate the test in an iframe — `Router` installs listeners on `window` and reads `location.pathname`, so shared state pollutes other tests.
2. Use `iframe.contentWindow.history.pushState(...)` to position the URL before mounting the component.
3. After every navigation, `await el.updateComplete` before asserting on shadow DOM content.
4. To test the click path, query an `<a>` and call `.click()`; to test programmatic nav, call `history.pushState` + `router.goto`.
5. Restore history in `afterEach` to leave the test environment clean.

Consult [references/testing.md](references/testing.md) for sketches with `@open-wc/testing` and Vitest + happy-dom.

## When to Use Each Concept

| Scenario | Use | Why |
|----------|-----|-----|
| Top-level router on the page | `Router` | Installs global `click`/`popstate` listeners; one per app |
| Nested route section inside a child component | `Routes` | Auto-wires to the nearest ancestor `Routes` via DOM event |
| Pathname-only matching | `path: '/users/:id'` | Simplest form; compiled to `URLPattern({pathname})` |
| Match host, protocol, or full URL | `pattern: new URLPattern(...)` | Bypasses pathname-only path field |
| 404 / catch-all | `{fallback: {render: ...}}` constructor option | Internally treated as `{...fallback, path: '/*'}` |
| Async data preload before render | `enter` (async) | Router awaits before updating params |
| Component-local loading with cancellation | `@lit/task` inside the routed component | Status states, abort signal, race-safe |
| In-app link | `<a href="/...">` | Click handler intercepts and SPA-navigates |
| Build a parent-relative href in a child router | `this._routes.link('local-path')` | Prepends parent's matched pathname |
| Programmatic navigation | `history.pushState(...)` + `router.goto(...)` | `goto` alone won't update the URL |
| Active-link styling | Read `this._router.params` / `location.pathname` in `render()` | No built-in helper or event |

## Core Rules

- **One `Router` per page; `Routes` for everything else.** Multiple `Router`s would double-handle clicks and clobber each other on `popstate`.
- **No template directive — call `${controller.outlet()}` in `render()`.** A `routes()` directive does not exist.
- **`goto()` does NOT call `history.pushState`.** Always pair them for programmatic nav, or let click interception handle it.
- **Trailing slash is significant for nested mounts.** `/users/*` matches `/users/` and `/users/foo`, but NOT `/users` — link as `<a href="/users/">`.
- **`<a href>` works automatically** when the link is same-origin, has no `target`, no `download`, no `rel="external"`, and the click has no modifier keys.
- **`enter` returning `false` cancels the navigation.** There is no `leave` / `beforeUnload` hook.
- **Hash routing is unsupported.** Only `pathname` is matched. Use the History API.
- **Mark `@lit-labs/router` as Labs/experimental** when introducing it — pre-1.0, breaking changes possible.

## Examples

Example 1: User says "add a `/users/:id` route"
Actions:
1. Add `{path: '/users/:id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`}` to the `Router` config.
2. Note that `id` is typed `string | undefined` — narrow if needed.
3. Add a nav link `<a href="/users/123">`.
Result: A typed parameterised route reachable by clicking the link or visiting the URL.

Example 2: User says "my back button doesn't update the page"
Actions:
1. Confirm there is exactly one `Router` instance (not multiple).
2. Check whether they're calling `router.goto()` without `history.pushState` — that desyncs the URL bar from rendered content, which then breaks back/forward.
3. Wrap programmatic nav in a helper that does both: `history.pushState({}, '', path); this._router.goto(path);`.
Result: Back button restores the prior URL and the matching route renders.

Example 3: User says "my `/users` link doesn't show the nested user list"
Actions:
1. Identify the nested mount: parent has `/users/*`, child has `path: ''` for the index.
2. Change the link from `<a href="/users">` to `<a href="/users/">` (trailing slash).
3. Optionally add a sibling parent route `{path: '/users', render: ...}` that re-routes to `/users/`.
Result: The parent route matches, the child mounts, and the empty-path index renders.

## Troubleshooting

| Symptom | Reference |
|---------|-----------|
| Bare `/users` doesn't match `/users/*` parent route | [pitfalls.md](references/pitfalls.md) |
| `goto()` updates the page but URL bar stays the same | [navigation.md](references/navigation.md), [pitfalls.md](references/pitfalls.md) |
| `<a href="/foo" target="_self">` doesn't intercept | [navigation.md](references/navigation.md) |
| Hash-based routing (`#/foo`) doesn't work | [pitfalls.md](references/pitfalls.md) |
| `link('./foo')` throws "Not implemented" | [api.md](references/api.md), [pitfalls.md](references/pitfalls.md) |
| `params.id` is `undefined` for an optional group | [url-patterns.md](references/url-patterns.md) |
| Child router renders nothing inside a parent route | [nested-routing.md](references/nested-routing.md) |
| Need to block leaving a route (unsaved changes) | [lifecycle.md](references/lifecycle.md) |
| Need a "route changed" event for analytics | [lifecycle.md](references/lifecycle.md) |
| `URLPattern is not defined` in Firefox/Safari builds | [url-patterns.md](references/url-patterns.md) |
| Tests share state across files / break each other | [testing.md](references/testing.md) |

## Topic References

Consult these for detailed API, options, patterns, and code examples:

- [API](references/api.md) — `Router` and `Routes` classes, constructor, methods (`goto`, `outlet`, `link`, `params`), `RouteConfig` types, `link()` algorithm, `RoutesConnectedEvent`, module entry points
- [URL Patterns](references/url-patterns.md) — `URLPattern` syntax (`:name`, `:name?`, `*`, regex), `params` shape, `urlpattern-polyfill`, TypeScript narrowing
- [Nested Routing](references/nested-routing.md) — How `lit-routes-connected` wires parent and child, tail-group propagation, canonical example, index path (`path: ''`)
- [Navigation](references/navigation.md) — Click interception rules, `popstate`, `goto()` + `pushState` pairing, `link()` for parent-relative hrefs, active-link styling
- [Lifecycle](references/lifecycle.md) — `enter(params)` semantics, async preload, race conditions, missing `leave` / global hooks, `enter` vs `@lit/task`
- [Pitfalls](references/pitfalls.md) — Trailing-slash matching, `goto`/history desync, hash routing, `link('./...')`, `name` field, leave guards, SPA fallback, target attribute, multiple Routers, Labs status
- [Examples](references/examples.md) — Full runnable patterns: basic SPA, fallback/404, nested router, async data via `enter`, async data via `@lit/task`, programmatic nav, `@vaadin/router` migration cheat sheet
- [Testing](references/testing.md) — iframe isolation, `await updateComplete`, click vs programmatic drivers, `popstate` testing, `@open-wc/testing` and Vitest + happy-dom sketches
