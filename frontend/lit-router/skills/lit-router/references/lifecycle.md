# Lifecycle & Guards — Deep Dive

`@lit-labs/router` exposes one lifecycle hook per route: `enter`. There is **no** `leave` / `beforeUnload` hook, and **no** global "route changed" event. This document covers what `enter` actually does, how to use it for async data loading, and the patterns to work around the missing hooks.

## `enter(params): boolean | Promise<boolean>`

The full source for the relevant section of `goto()`:

```ts
if (typeof route.enter === 'function') {
  const success = await route.enter(params);
  if (success === false) return;
}
// ... set current params, requestUpdate, propagate to child routes
```

Semantics:

- Return `false` (or a promise resolving to `false`) → navigation is **cancelled**. The previously matched route stays current. `requestUpdate()` is NOT called. Child routes are NOT propagated to.
- Return anything else (`true`, `undefined`, an object, a promise of any of those) → navigation proceeds.
- Async `enter` → `goto()` awaits it. The host won't re-render the new route until the promise resolves.

## Synchronous guards

Cancel based on a sync condition (e.g. auth):

```ts
{
  path: '/admin/*',
  enter: () => {
    if (!auth.isAdmin()) {
      history.replaceState({}, '', '/login');
      this._router.goto('/login');
      return false;
    }
    return true;
  },
  render: () => html`<admin-section></admin-section>`,
}
```

Note: returning `false` cancels — but the URL bar won't change unless you also push/replace history. The example above redirects to `/login` before bailing.

## Async data preload

Use `enter` to block rendering until data is ready:

```ts
{
  path: '/users/:id',
  enter: async ({id}) => {
    await store.loadUser(id!);
  },
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}
```

Trade-off: the whole router is blocked until the promise resolves. The user sees the previous route until the new data arrives. For component-local loading state with cancellation and progress UI, prefer `@lit/task` (next section).

## `enter` vs `@lit/task`

| Use `enter` when | Use `@lit/task` when |
|---|---|
| You want to gate navigation entirely on the data | You want to render the route immediately and show loading state inside the component |
| The data must be present before any render | The component can show a skeleton / spinner while loading |
| You're implementing an auth guard or redirect | You need automatic cancellation when the param changes mid-load |
| The load is fast and skeletons would flash | The load is slow and a blank page would be worse |

Combined pattern (preferred for most cases):

```ts
// Route definition: keep enter empty.
{
  path: '/users/:id',
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}
```

```ts
// Inside <user-detail>:
@customElement('user-detail')
class UserDetail extends LitElement {
  @property() id?: string;

  private _userTask = new Task(this, {
    task: async ([id], {signal}) => {
      const res = await fetch(`/api/users/${id}`, {signal});
      return res.json();
    },
    args: () => [this.id],
  });

  render() {
    return this._userTask.render({
      pending: () => html`<spinner></spinner>`,
      complete: (user) => html`<h1>${user.name}</h1>`,
      error: (e) => html`<p>Failed: ${(e as Error).message}</p>`,
    });
  }
}
```

`@lit/task` automatically cancels the previous fetch when `id` changes, so navigating quickly between users doesn't leak requests.

## No `leave` / `beforeUnload` hook

There is no built-in way to block navigation away from the currently matched route. Patterns:

### Native browser warning (closing tab, full reload)

```ts
window.addEventListener('beforeunload', (e) => {
  if (form.isDirty) {
    e.preventDefault();
    e.returnValue = '';
  }
});
```

This handles tab close and full page reload, but NOT in-app `<a>` clicks routed by `Router`.

### Click-time confirmation (in-app navigation)

Intercept clicks before the router does:

```ts
hostConnected() {
  this.shadowRoot?.addEventListener('click', this._beforeRouterClick);
}

private _beforeRouterClick = (e: Event) => {
  const a = (e.composedPath().find((n) => (n as HTMLElement).tagName === 'A')) as HTMLAnchorElement | undefined;
  if (!a) return;
  if (this._form.isDirty && !confirm('Discard changes?')) {
    e.preventDefault();
  }
};
```

Run this listener in capture phase (`addEventListener(..., true)`) if you need to win against the router's bubble-phase handler attached on `window`.

### Route-level wrapper

Wrap each protected route's `render` in a leave-confirm guard, or check in `enter` of every other route:

```ts
let dirtyForm: {isDirty: boolean} | undefined;

const guardedEnter = (next: () => void) => async () => {
  if (dirtyForm?.isDirty && !confirm('Discard?')) return false;
  next();
};
```

None of these is as clean as a real `leave` hook, and discussion #3354 has had a request open for one for years. Bake the pattern into your app's nav layer and don't fight the router.

## No global "route changed" event

There is no event you can listen for. Workarounds:

- **Read state in `render()`.** The router calls `requestUpdate()` on every successful navigation, so anything in `render()` (analytics page-view, document title, focus management) re-runs.
- **Per-route hook.** Add a side effect inside each route's `enter`:
  ```ts
  {
    path: '/about',
    enter: () => { analytics.page('/about'); },
    render: () => html`<about-page></about-page>`,
  }
  ```
- **`updated()` lifecycle.** Track `this._router.params` and detect changes there — but this only fires after re-render, so it's strictly post-navigation.

## Race conditions

If a second `goto()` fires while a previous `enter()` is still pending, both promises resolve in order but the **last** one's params win. There is no built-in cancellation token. For data loads inside `enter`, be defensive:

```ts
let lastRequestId = 0;

{
  path: '/users/:id',
  enter: async ({id}) => {
    const rid = ++lastRequestId;
    const data = await fetch(`/api/users/${id}`).then(r => r.json());
    if (rid !== lastRequestId) return false;  // stale, cancel
    store.user = data;
  },
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}
```

Or bypass the problem by moving the load into `@lit/task`, which cancels via `AbortSignal` automatically.

## Common Pitfalls

- **`enter` returning `false` doesn't update history.** If you triggered navigation by clicking a link, the URL bar already changed (the click handler called `pushState` first). Cancelling `enter` leaves the URL ahead of the rendered route. To fully rewind, push the previous URL back after returning `false`.
- **`enter` is awaited.** The whole router blocks until your async work finishes. Long fetches without `@lit/task` cause "nothing happens" UX.
- **No automatic cancellation between concurrent `enter` calls.** Track request IDs or use `@lit/task` instead.
- **No `leave` hook.** Don't promise users a clean "are you sure?" prompt without implementing it manually with one of the patterns above.
- **No global event.** Don't try to wire an analytics integration from a single listener — distribute it across `enter` callbacks or read state in `render()`.

See also: [api.md](api.md) for `goto()` source, [navigation.md](navigation.md) for click interception (which fires before `enter`), [pitfalls.md](pitfalls.md) for the full gotcha list.
