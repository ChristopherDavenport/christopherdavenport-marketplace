# Nested Routing — Deep Dive

Nesting in `@lit-labs/router` is **automatic by DOM containment**. You don't pass the parent router into the child. The child component instantiates its own `Routes` controller, and on `hostConnected` that controller dispatches a bubbling event that the nearest ancestor `Routes` catches and uses to register the child.

## How wiring works

From source:

1. Child component is created by a parent route's `render()`.
2. Child instantiates `new Routes(this, [...])` in its constructor or as a class field.
3. On the child's `hostConnected`, `Routes` dispatches a `RoutesConnectedEvent` (`bubbles: true, composed: true`) up the DOM tree.
4. The nearest ancestor `Routes` receives it, pushes the child into `_childRoutes`, sets `child._parentRoutes = this`, and calls `stopImmediatePropagation` so it doesn't bubble further.
5. If the parent already had a tail group, it immediately calls `childRoutes.goto(tailGroup)`.
6. On any subsequent `goto()` on the parent, after matching its own route it iterates `_childRoutes` and calls `childRoutes.goto(tailGroup)` for each.

This means:

- The child must be inside the parent's shadow/light DOM when the child's `hostConnected` fires.
- The bubbling event crosses Shadow DOM (`composed: true`), so a child rendered into a parent's shadow root still finds the parent.
- You can have any depth of nesting — each `Routes` finds its nearest ancestor.

## Path resolution

- **Parent path must end in `/*`** to produce a tail group.
- **Child paths are matched against the tail string**, not the full URL. So a child route `path: 'detail/:id'` matches when the parent's tail group is `'detail/:id'`.
- **A child's index route is `path: ''`** — empty string. This matches when the parent's wildcard captured an empty string (which happens for URLs that have a trailing slash on the parent path).

## Canonical example

```ts
import {LitElement, html} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Router, Routes} from '@lit-labs/router';

@customElement('app-shell')
class AppShell extends LitElement {
  private _router = new Router(this, [
    {path: '/',          render: () => html`<home-page></home-page>`},
    {path: '/users/*',   render: () => html`<users-section></users-section>`},
    {path: '/about',     render: () => html`<about-page></about-page>`},
  ]);

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/users/">Users</a>
        <a href="/about">About</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}

@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',         render: () => html`<user-list></user-list>`},
    {path: 'new',      render: () => html`<user-create></user-create>`},
    {path: ':id',      render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
    {path: ':id/edit', render: ({id}) => html`<user-edit .id=${id}></user-edit>`},
  ]);

  render() {
    return html`
      <h2>Users</h2>
      <nav>
        <a href=${this._routes.link('new')}>New user</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}
```

URL → matched routes:

| URL | Parent matches | Child receives | Child renders |
|---|---|---|---|
| `/users/` | `/users/*` (tail = `''`) | `''` | `<user-list>` |
| `/users/new` | `/users/*` (tail = `'new'`) | `'new'` | `<user-create>` |
| `/users/42` | `/users/*` (tail = `'42'`) | `':id'` (id = `'42'`) | `<user-detail .id="42">` |
| `/users/42/edit` | `/users/*` (tail = `'42/edit'`) | `':id/edit'` (id = `'42'`) | `<user-edit .id="42">` |
| `/users` (no slash) | **NO MATCH** — see pitfall below | — | nothing (or fallback) |

## Building child URLs with `link()`

Inside `UsersSection`, `this._routes.link('new')` returns `'/users/new'` because `link` concatenates the parent's matched pathname (`/users/`) with the local path. Use it when you don't want to hard-code the parent prefix:

```ts
render() {
  return html`
    <a href=${this._routes.link('new')}>New</a>
    <a href=${this._routes.link(`${this._routes.params.id}/edit`)}>Edit</a>
  `;
}
```

Absolute hrefs work too — `link('/foo')` returns `'/foo'` unchanged. Use whichever is clearer.

## Multiple children at one level

A parent can have multiple `Routes`-bearing children. The bubbling event registers each with the nearest ancestor, and the parent calls `goto(tailGroup)` on each on every navigation. Practical use: a layout component that renders a sidebar with its own `Routes` plus a main panel with another `Routes`.

```ts
@customElement('app-shell')
class AppShell extends LitElement {
  private _router = new Router(this, [
    {path: '/admin/*', render: () => html`
      <admin-sidebar></admin-sidebar>
      <admin-main></admin-main>
    `},
  ]);
  render() { return html`${this._router.outlet()}`; }
}
```

Both `<admin-sidebar>` and `<admin-main>` instantiate their own `Routes` and both receive the same tail group on every navigation.

## Programmatic navigation in nested routers

Inside a child, the right call is still `this._routes.goto(...)` — but the child's `goto` only re-matches its own routes against the supplied path. To navigate the whole app, walk up to the root or use absolute paths with `history.pushState`:

```ts
const navigate = (path: string) => {
  history.pushState({}, '', path);
  // Find the root Router and re-goto the full pathname.
  // Simplest: fire a popstate-equivalent.
  window.dispatchEvent(new PopStateEvent('popstate'));
};
```

Or expose a navigation helper from the root and pass it down via `@lit/context`.

## Common Pitfalls

- **Bare `/users` doesn't match `/users/*`.** `URLPattern` is strict about the literal slash before `*`. Always link to nested mounts with a trailing slash: `<a href="/users/">`. Or include both routes:
  ```ts
  {path: '/users',   render: () => html`<users-section></users-section>`},
  {path: '/users/*', render: () => html`<users-section></users-section>`},
  ```
- **Index path must be `''`, not `/`.** Inside a child, `path: '/'` does not match the empty tail. Use `path: ''`.
- **Child paths must NOT start with the parent prefix.** They're matched against the tail, not the full URL. `path: '/users/:id'` inside a `/users/*` child won't match anything.
- **Child must be inside the parent in the DOM tree when `hostConnected` fires.** A child rendered conditionally only after some delay still wires up correctly when it eventually connects — but a child outside the parent (e.g. a slotted descendant with no ancestor `Routes`) won't find a parent and won't navigate.
- **Don't put `Router` inside `Router`.** Inner `Router` instances would each install global listeners. Use `Routes` for any non-root routing.
- **Children re-mount on parent route change.** If the parent route's render returns a different element type, the child's controller is recreated and the bubbling-event handshake runs again from scratch.

See also: [api.md](api.md) for `RoutesConnectedEvent` and `link()` algorithm, [navigation.md](navigation.md) for click interception, [pitfalls.md](pitfalls.md) for the trailing-slash pitfall in detail.
