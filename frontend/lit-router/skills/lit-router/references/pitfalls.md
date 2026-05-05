# Pitfalls

Consolidated list of known gotchas in `@lit-labs/router`, with workarounds. Most stem from the library being intentionally small (no redirects, no leave hooks, no named-route lookup). Several are actively discussed on the lit/lit issue tracker.

## 1. Trailing slash on nested mounts

**Symptom:** `<a href="/users">` doesn't trigger the nested user-list view; `<a href="/users/">` does.

**Why:** `URLPattern` is strict about the literal slash before `*`. A pattern `/users/*` matches `/users/` and `/users/anything`, but **not** `/users`.

**Workarounds:**

- Always link nested mounts with a trailing slash: `<a href="/users/">`.
- Or register both routes:
  ```ts
  {path: '/users',   render: () => html`<users-section></users-section>`},
  {path: '/users/*', render: () => html`<users-section></users-section>`},
  ```
- The child's index route `path: ''` only matches when the parent forwarded an empty string — i.e. when the parent matched `/users/`, not `/users`.

References: GitHub issues lit/lit#3453, #3949.

## 2. `goto()` doesn't update `history`

**Symptom:** Calling `router.goto('/x')` changes the rendered route but not the URL bar. Back button then breaks.

**Why:** `goto()` only runs route matching and `requestUpdate()`. The click handler is the only place that calls `history.pushState`.

**Workaround:**

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}
```

For replacement: `history.replaceState({}, '', path)` instead.

Reference: GitHub discussion lit/lit#3256.

## 3. Hash routing is unsupported

**Symptom:** `/#/users` doesn't route to the users page.

**Why:** The router's `getPattern` / `goto` flow only inspects `location.pathname`. `URLPattern`'s `hash` field is never consulted, and the click handler reads `anchor.pathname`.

**Workaround:** Use the History API. If you must support legacy `#` URLs, write a one-time redirect at app startup:

```ts
if (location.hash.startsWith('#/')) {
  const path = location.hash.slice(1);
  history.replaceState({}, '', path);
}
```

Reference: GitHub issue lit/lit#3517.

## 4. `link('./...')` throws

**Symptom:** `Error: Not implemented` when calling `controller.link('./detail')`.

**Why:** Source explicitly rejects any string starting with `.`:

```ts
if (pathname?.startsWith('.')) throw new Error('Not implemented');
```

**Workaround:** Use absolute (`/users/123`) or child-relative without leading dot (`detail/123`). The `link()` algorithm prepends the parent's matched pathname to non-absolute strings already.

## 5. `name` field is decorative

**Symptom:** No `linkTo('routeName', params)` API to find.

**Why:** `RouteConfig.name` exists in the type but the router never reads it. Discussion #3354 has had a request open for years.

**Workaround:** Build URLs explicitly with `link()` or template literals. If you want named routes, wrap your route definitions in a small helper that maintains a name → path map:

```ts
const routes = {
  userDetail: '/users/:id',
  userEdit:   '/users/:id/edit',
} as const;

const url = (name: keyof typeof routes, params: Record<string, string>) =>
  routes[name].replace(/:(\w+)/g, (_, k) => params[k]);
```

## 6. No leave guards / no global navigation event

**Symptom:** Can't show "Discard unsaved changes?" on navigation; can't fire analytics from a single hook.

**Why:** Library scope. Only `enter` exists.

**Workaround:** See [lifecycle.md](lifecycle.md). For leave guards, intercept clicks in capture phase before the router's bubble-phase handler. For analytics, distribute side effects across each route's `enter` or read state in `render()`.

## 7. SPA fallback must be configured on the server

**Symptom:** Hard refresh on `/users/42` returns 404.

**Why:** Like all client routers, `@lit-labs/router` only kicks in once the page (and your bundle) has loaded. The server must serve `index.html` for any unknown path.

**Workaround:** Configure your dev server (Vite: `historyApiFallback`, Web Dev Server: `appIndex`) and production host (Nginx `try_files`, Netlify `_redirects`, etc.) accordingly. The library does not address SSR.

## 8. Click handler skips any non-empty `target` attribute

**Symptom:** `<a href="/foo" target="_self">` doesn't intercept; the browser does a full reload.

**Why:** Source checks `anchor.target !== ''` (literal empty string only). `_self` is the semantic default, but the **attribute** is non-empty, so the handler bails.

**Workaround:** Omit `target` entirely on in-app links. If a third-party component sets `target="_self"`, override it or work around at the framework level.

## 9. One `Router` per page

**Symptom:** Mysterious double-firing of click handlers, race conditions during init.

**Why:** `Router.hostConnected` installs **global** listeners on `window` and unconditionally calls `goto(location.pathname)`. Multiple `Router`s would each handle every click.

**Workaround:** Use `Routes` for any non-root routing. The wiring is automatic via the `lit-routes-connected` bubbling event — see [nested-routing.md](nested-routing.md).

## 10. Cross-origin links pass through

**Symptom:** Clicking `<a href="https://other-domain.example/...">` does a full page navigation (correct behavior, but worth knowing).

**Why:** Source skips when `anchor.origin !== window.location.origin`.

**No workaround needed** — this is intentional. External links should work normally.

## 11. Labs status — pre-1.0, breaking changes possible

**Symptom:** API surface might shift between minor versions.

**Why:** `@lit-labs/router` is in Lit Labs (`0.x`). Discussion #3354 collects feedback for graduation; the package has not yet stabilised.

**Workaround:**

- Pin a known-good version in `package.json` (`"@lit-labs/router": "0.1.4"` rather than `^0.1.4`).
- Flag the experimental status to readers when introducing it in a codebase.
- Watch the lit/lit changelog for breaking changes when upgrading.

## 12. `URLPattern is not defined` on non-Chromium browsers

**Symptom:** Runtime error in Firefox / Safari (older versions).

**Why:** The router uses native `URLPattern` and does not bundle a polyfill.

**Workaround:** Install and import the polyfill **before** `@lit-labs/router`:

```bash
npm install urlpattern-polyfill
```

```ts
import 'urlpattern-polyfill';
import {Router, Routes} from '@lit-labs/router';
```

Order matters — the polyfill must define `globalThis.URLPattern` before the router's module evaluates.

## 13. Routes pushed at runtime aren't matched until the next `goto()`

**Symptom:** `this.routes.push({...})` doesn't immediately route to the new path.

**Why:** Routes are matched at `goto()` time. Pushing into the array doesn't trigger a match.

**Workaround:** After mutating `this.routes`, call `this.goto(location.pathname)` to re-match.

## 14. Initial render can be empty for async-`enter` root routes

**Symptom:** Page is blank for a moment on first load when the matched route's `enter` is async.

**Why:** `Router.hostConnected` calls `goto(location.pathname)` synchronously, but `goto` awaits `enter`. Until `enter` resolves, no route is matched and `outlet()` returns `undefined`.

**Workaround:** Render a fallback / spinner around the outlet for the initial-load case, or move the data loading into the routed component via `@lit/task`.

See also: [api.md](api.md), [navigation.md](navigation.md), [lifecycle.md](lifecycle.md), [nested-routing.md](nested-routing.md), [url-patterns.md](url-patterns.md).
