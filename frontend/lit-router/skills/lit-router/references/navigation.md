# Navigation — Deep Dive

`Router` (the root, top-level controller) installs two global listeners on `window` in `hostConnected`: a `'click'` listener that intercepts in-app anchor clicks and rewrites them as SPA navigations, and a `'popstate'` listener that re-runs `goto(location.pathname)` on back/forward. `Routes` (nested) does neither — it relies on the root `Router` to hand it tail groups.

## Click interception

The click handler intercepts a click only when **all** of the following are true:

- Left click only (no right/middle button).
- No modifier keys held (`metaKey`, `ctrlKey`, `shiftKey`).
- `e.defaultPrevented` is not already set.
- An `<a>` element is found in `composedPath()` (so the click crosses Shadow DOM correctly).
- The anchor has no `target` attribute (literal empty string only — see pitfall below).
- The anchor has no `download` attribute.
- The anchor has no `rel="external"`.
- The anchor's `href` is non-empty and does NOT start with `mailto:`.
- The anchor's `origin === window.location.origin` (same-origin only).

When all conditions match:

```ts
e.preventDefault();
if (anchor.href !== location.href) {
  history.pushState({}, '', anchor.href);
}
this.goto(anchor.pathname);
```

**Implication:** plain `<a href="/users/123">User</a>` inside your app does the right thing automatically. No special `<lit-link>` element exists, no wrapper component is needed, and you do not need to attach event listeners.

## `popstate`

```ts
window.addEventListener('popstate', () => this.goto(location.pathname));
```

Back / forward buttons work out of the box. Note: `popstate` fires only on history navigation, not on `pushState` calls — the click handler covers that path.

## `goto()` does NOT update history

This is the most common gotcha. From source, `goto()` runs the route logic and `requestUpdate()` but does **not** call `history.pushState`. Only the click handler does. So:

- `router.goto('/x')` direct call → URL bar stays unchanged. The router will render `/x` content, but the address bar still shows the old URL, and `popstate` will see the old URL on back.
- For programmatic navigation, you almost always want:

  ```ts
  history.pushState({}, '', '/x');
  router.goto('/x');
  ```

A small helper:

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}
```

For replacement (no history entry):

```ts
private _replace(path: string) {
  history.replaceState({}, '', path);
  this._router.goto(path);
}
```

This is a known wart — see GitHub discussion #3256. Plan accordingly and prefer `<a href>` + click interception when you can.

## No `pushState` listener

The Router does **not** observe `history.pushState` / `history.replaceState` from arbitrary external callers. If you call `history.pushState` from outside the router and want the router to update, call `router.goto(...)` yourself. There is no `MutationObserver`-style hook.

If you must integrate with an external library that calls `pushState`, monkey-patch it:

```ts
const origPushState = history.pushState.bind(history);
history.pushState = (state, title, url) => {
  origPushState(state, title, url);
  if (typeof url === 'string') router.goto(new URL(url, location.href).pathname);
};
```

## Generating href values with `link()`

`link(pathname?)` resolves a string against the parent route chain. Use it when you don't want to hard-code a parent's prefix:

```html
<!-- inside a child Routes mounted under /users/* -->
<a href=${this._routes.link('new')}>New user</a>
<!-- → '/users/new' -->

<a href=${this._routes.link(`${id}/edit`)}>Edit</a>
<!-- → '/users/42/edit' -->
```

Absolute paths pass through unchanged:

```html
<a href=${this._routes.link('/about')}>About</a>
<!-- → '/about' -->
```

You can also just hard-code absolute hrefs (`<a href="/users/123">`); they work fine, since `link('/...')` returns the absolute path unchanged and the click handler doesn't care which form you used.

**Don't use leading-dot relatives.** `link('./foo')` throws `Error('Not implemented')`.

## Active-link styling

There is no built-in active-link helper and no global "route changed" event. Pattern:

```ts
render() {
  const here = location.pathname;
  const active = (path: string) => here === path ? 'active' : '';
  const startsActive = (prefix: string) => here.startsWith(prefix) ? 'active' : '';

  return html`
    <a class=${active('/')} href="/">Home</a>
    <a class=${startsActive('/users/')} href="/users/">Users</a>
    <a class=${active('/about')} href="/about">About</a>
  `;
}
```

The host re-renders on every successful `goto()` (because the router calls `host.requestUpdate()`), so reading `location.pathname` in `render()` is fine.

For matching against a child route inside a nested section, compare against `this._routes.params` or against `this._routes.link()` (no-arg returns the current matched URL).

## Cross-origin and external links

External links pass through unchanged:

```html
<a href="https://example.com/docs">Docs</a>
<!-- Skipped by the click handler because origin differs. Browser follows normally. -->

<a href="/api/raw" download>Download</a>
<!-- Skipped because of `download` attribute. -->

<a href="/legacy" rel="external">Legacy app</a>
<!-- Skipped because of `rel="external"`. -->

<a href="/foo" target="_blank">New tab</a>
<!-- Skipped because of `target`. -->
```

## Common Pitfalls

- **`router.goto()` without `history.pushState()`.** URL bar lies. Always pair them, or use `<a href>` and let the click handler do both.
- **`<a href="/foo" target="_self">` is skipped.** The click handler checks `anchor.target !== ''` (literal empty string). `_self` is the semantic default but the **attribute** is non-empty, so the handler bails. Omit `target` entirely for in-app links.
- **`href=""` is skipped.** The handler bails on empty hrefs. Use `href="/"` for "go to root".
- **`rel="external"` is skipped.** Don't use it on in-app links unless you explicitly want the browser default.
- **Modifier-clicks behave like the browser.** Cmd/Ctrl/Shift-click opens in a new tab as expected — don't try to "fix" this; it's correct behavior.
- **Multiple `Router` instances double-handle clicks.** Use `Routes` for nested routing — never `Router`.
- **No `pushState` observation.** External libraries that call `pushState` won't trigger router updates unless you monkey-patch or call `router.goto()` yourself.

See also: [api.md](api.md) for `link()` algorithm and `goto()` signature, [lifecycle.md](lifecycle.md) for what happens between click and render, [pitfalls.md](pitfalls.md) for a consolidated gotcha list.
