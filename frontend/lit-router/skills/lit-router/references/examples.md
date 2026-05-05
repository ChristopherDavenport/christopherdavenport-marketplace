# Examples

Canonical, runnable patterns. Lift these into your project and adjust the route paths and components.

## Basic single-page app

```ts
import {LitElement, html} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Router} from '@lit-labs/router';

@customElement('my-app')
export class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/',          render: () => html`<h1>Home</h1>`},
    {path: '/about',     render: () => html`<h1>About</h1>`},
    {path: '/users/:id', render: ({id}) => html`<h1>User ${id}</h1>`},
  ]);

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/users/42">User 42</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

## Fallback (404) route

```ts
new Router(
  this,
  [
    {path: '/',      render: () => html`<home-page></home-page>`},
    {path: '/about', render: () => html`<about-page></about-page>`},
  ],
  {fallback: {render: () => html`<not-found></not-found>`}}
);
```

The fallback is internally treated as `{...fallback, path: '/*'}`, so it matches anything no other route does. You can also use it to install routes on demand: have its `render` push new entries into `this.routes` and call `goto()` again.

## Nested router (full)

```ts
import {LitElement, html} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Router, Routes} from '@lit-labs/router';

@customElement('app-shell')
class AppShell extends LitElement {
  private _router = new Router(this, [
    {path: '/',         render: () => html`<home-page></home-page>`},
    {path: '/users/*',  render: () => html`<users-section></users-section>`},
  ]);

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
    {path: 'new',  render: () => html`<user-create></user-create>`},
    {path: ':id',  render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() {
    return html`
      <h2>Users</h2>
      <nav>
        <a href=${this._routes.link('')}>List</a>
        <a href=${this._routes.link('new')}>New</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}
```

The `<a href="/users/">` (trailing slash) matters — see [pitfalls.md](pitfalls.md).

## Async data loading via `enter`

Block render until data is ready:

```ts
{
  path: '/products/:id',
  enter: async ({id}) => {
    await store.loadProduct(id!);
  },
  render: ({id}) => html`<product-page .id=${id}></product-page>`,
}
```

To redirect-on-failure, push the new URL and return `false`:

```ts
{
  path: '/admin/*',
  enter: async () => {
    const ok = await auth.isAdmin();
    if (!ok) {
      history.replaceState({}, '', '/login');
      this._router.goto('/login');
      return false;
    }
  },
  render: () => html`<admin-section></admin-section>`,
}
```

## Async data loading via `@lit/task` (preferred for component-local UI)

Keep `enter` empty; do the work inside the routed component with cancellation and loading state:

```ts
import {Task} from '@lit/task';

@customElement('user-detail')
class UserDetail extends LitElement {
  @property() id?: string;

  private _userTask = new Task(this, {
    task: async ([id], {signal}) => {
      const res = await fetch(`/api/users/${id}`, {signal});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    args: () => [this.id],
  });

  render() {
    return this._userTask.render({
      pending:  () => html`<spinner></spinner>`,
      complete: (user) => html`<h1>${user.name}</h1>`,
      error:    (e) => html`<p>Failed: ${(e as Error).message}</p>`,
    });
  }
}
```

`@lit/task` automatically aborts the previous fetch when `id` changes — so navigating quickly between users doesn't leak requests.

## Programmatic navigation with history sync

`goto()` alone does NOT update the URL bar. Always pair with `history.pushState`:

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}

private _replace(path: string) {
  history.replaceState({}, '', path);
  this._router.goto(path);
}
```

Use `_navigate` from event handlers, form submissions, etc.:

```ts
private _onSubmit = async (e: SubmitEvent) => {
  e.preventDefault();
  const id = await store.createUser();
  this._navigate(`/users/${id}`);
};
```

## Active-link styling

No built-in helper. Read `location.pathname` in `render()`:

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

The host re-renders on every successful navigation, so this stays in sync.

## Dynamic route registration (lazy modules)

Use `fallback` to load a module on first hit, register its routes, and re-match:

```ts
private _router = new Router(this, [
  {path: '/',      render: () => html`<home-page></home-page>`},
  {path: '/about', render: () => html`<about-page></about-page>`},
], {
  fallback: {
    enter: async () => {
      const path = location.pathname;
      if (path.startsWith('/admin')) {
        await import('./admin-section.js');
        this._router.routes.push(
          {path: '/admin/*', render: () => html`<admin-section></admin-section>`},
        );
        await this._router.goto(path);
        return false;
      }
    },
    render: () => html`<not-found></not-found>`,
  },
});
```

## Migration cheat sheet from `@vaadin/router`

| `@vaadin/router` | `@lit-labs/router` equivalent |
|---|---|
| `new Router(outlet)` | `new Router(this, routes)` and place `${this._router.outlet()}` in `render()` |
| `setRoutes([...])` | Pass routes in the constructor or mutate `this.routes` then `goto(location.pathname)` |
| `children: [...]` (config tree) | Parent path ending `/*` + child component with its own `Routes` (composition, not config) |
| `redirect: '/login'` | `enter: () => { history.replaceState(...); router.goto('/login'); return false; }` |
| `before` / `after` lifecycle | `enter` only (no `before`/`after`/`leave`) |
| `Router.urlForName('routeName', params)` | Not supported — build URLs by hand or with `link()` |
| `<a router-ignore>` to bypass interception | `<a rel="external">` or `<a target="_blank">` (anything non-default `target`) |
| Built-in `Router.go(path)` | `history.pushState({}, '', path); router.goto(path);` |
| Animations on route change | Not built in — use Web Animations API in `render()` or component `firstUpdated` |
| Outlet auto-discovers from DOM | You must place `${controller.outlet()}` explicitly |

## Polyfilled, complete app entry

```ts
import 'urlpattern-polyfill';   // omit if targeting Chromium-only
import './my-app.js';

document.body.appendChild(document.createElement('my-app'));
```

`my-app.js` is the `MyApp` component from the first example. The `urlpattern-polyfill` import must come before any module that imports `@lit-labs/router`.

See also: [api.md](api.md), [nested-routing.md](nested-routing.md), [navigation.md](navigation.md), [lifecycle.md](lifecycle.md).
