# Eval report: `lit-router`

- Cases: **6**
- Expectations met: **1/6** (skill_wins 0/4, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **1**, baseline won **1**, ties **4**
- Rubric pass-rate (over 5 scored case(s)): baseline **90%**, skill **90%** (Δ **+0%**)
- CLI cost: **$0.95** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `goto-doesnt-update-url` | skill_wins | ✗ | **baseline** | 100% | 100% |
| `trailing-slash-routes` | skill_wins | ✗ | **tie** | 100% | 100% |
| `nested-routes-vs-router` | skill_wins | ✗ | **tie** | 100% | 100% |
| `link-helper` | skill_wins | ✗ | **tie** | 100% | 100% |
| `simplest-hash-routing` | skill_wins_strict | ✗ | **skill** | 50% | 50% |
| `offtopic-git-rebase` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `goto-doesnt-update-url`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I'm using @lit-labs/router. I call `this._router.goto('/dashboard')`
inside a click handler, and the new route renders, but the URL
bar doesn't change and the browser back button is broken. What's
going on?
```

**Judge:** **baseline** — Both answers correctly explain that goto() does not push history and recommend both history.pushState and <a href> links. Answer B is more complete and idiomatic, adding the crucial popstate listener for back/forward button support, a clear rule of thumb for when to use each approach, and better explanation of why link interception handles edge cases like modifier-key clicks. Answer A has a useful but somewhat tangential note about multiple Router instances.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains goto does not push history | tie |
| recommends history.pushState | baseline |
| mentions <a href> link interception | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `no history` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `history.pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

<details><summary>Baseline answer</summary>

# Why `goto()` doesn't change the URL

This is a common gotcha with `@lit-labs/router`. The `goto()` method is **not** a navigation method — it's a *route resolver*. It only:

1. Matches the path against the router's routes
2. Runs the matched route's `render` (and `enter`) callbacks
3. Triggers a re-render of the host element

It deliberately does **not** touch `window.history` or `window.location`. That's why the address bar is stale and the back button has nothing to pop — no history entry was ever pushed.

## The fix: push history yourself

You need to update the History API and *then* tell the router to resolve the new path:

```ts
private _navigate(path: string) {
  window.history.pushState({}, '', path);
  this._router.goto(path);
}

private _onClick(e: Event) {
  e.preventDefault();
  this._navigate('/dashboard');
}
```

And to keep the back/forward buttons working, listen for `popstate` and re-resolve:

```ts
connectedCallback() {
  super.connectedCallback();
  window.addEventListener('popstate', this._onPopState);
}

disconnectedCallback() {
  window.removeEventListener('popstate', this._onPopState);
  super.disconnectedCallback();
}

private _onPopState = () => {
  this._router.goto(window.location.pathname);
};
```

## The more idiomatic approach: just use `<a>`

`@lit-labs/router` ships with link interception when you use real anchor tags inside the routed element:

```ts
render() {
  return html`<a href="/dashboard">Dashboard</a>`;
}
```

The router intercepts same-origin link clicks, calls `pushState`, and resolves the route for you — no manual `goto()` needed. This handles modifier-key clicks (cmd/ctrl-click to open in a new tab), middle-clicks, and external links correctly, which is annoying to reproduce by hand.

## Rule of thumb

- **User-initiated navigation** (clicks, menu items) → render an `<a href>` and let the router intercept it.
- **Programmatic navigation** (after a form submit, redirect, auth flow) → `history.pushState()` + `router.goto()`, and make sure you have a `popstate` listener wired up.

`goto()` alone is essentially "show me this route's UI without navigating" — useful for things like a 404 fallback or `enter()` redirects, but not what you want from a click handler.

</details>

<details><summary>Skill-loaded answer</summary>

## Why this happens

`Router.goto()` is intentionally a "render only" operation — it matches the path against your routes and updates the rendered outlet, but it **does not push (or replace) anything on `window.history`**. So the URL bar is whatever it was before, and the browser's back/forward stack has no entry for the navigation, which is exactly why the back button does nothing useful.

This trips a lot of people up because the name `goto` sounds like a full navigation, but it's really `setRoute` under the hood.

## Two ways to fix it

### 1. The cleanest fix: use a real link

The `Router` (the top-level one you instantiate once per page) installs a global click listener that intercepts same-origin `<a href>` clicks, calls `history.pushState` for you, and then runs `goto()` internally. So this just works:

```html
<a href="/dashboard">Dashboard</a>
```

Back button, URL bar, deep-linking — all correct, no JS in your click handler at all. Prefer this whenever the click target is semantically a link.

### 2. If you really need an imperative call

Push the history entry yourself, then call `goto`:

```ts
private _onClick(e: Event) {
  e.preventDefault();
  history.pushState({}, '', '/dashboard');
  this._router.goto('/dashboard');
}
```

Use `history.replaceState` instead of `pushState` if you don't want the navigation to land in the back stack (e.g. a redirect after login).

## Quick gotcha to double-check

Make sure you only have **one** `new Router(...)` on the page. If you've created additional `Router` instances for nested sections (instead of using the `Routes` controller), their global click/popstate listeners will fight each other and you can see symptoms that look a lot like "URL doesn't update."

</details>

---

### `trailing-slash-routes`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I have a `@lit-labs/router` route with path `/users/*` for a
nested users section. When I navigate to `/users` (no trailing
slash), the route doesn't match. Why, and what do I do?
```

**Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A provides a slightly cleaner explanation of the URLPattern semantics with the bullet-point breakdown, and adds a useful 'what not to do' warning about `/users*`. Answer B provides a clearer explanation of why `/users/` does match (the wildcard can be empty, but the slash is required) and presents three options more cleanly. Both are essentially equivalent in quality and correctness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies URLPattern matching semantics | tie |
| recommends adding trailing slash to links | tie |
| mentions registering both paths as alternative | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `both path` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `both path` |

<details><summary>Baseline answer</summary>

## Why `/users` doesn't match `/users/*`

`@lit-labs/router` builds its patterns on top of **URLPattern** semantics. In a pattern like `/users/*`, every character is significant — including the literal `/` between `users` and `*`. The `*` matches a wildcard segment, but the `/` *before* it is required.

So when the URL is `/users` (no trailing slash), URLPattern sees:

- Pattern: `/users/*` → expects `/users` + `/` + (anything, including empty)
- URL: `/users` → missing the required `/`

→ no match. `/users/` and `/users/anything` both match; bare `/users` does not.

## What to do

You have two clean fixes — pick whichever fits your app.

### 1. Always link with the trailing slash (simplest)

Make sure every link, redirect, and `goto()` call uses `/users/`:

```html
<a href="/users/">Users</a>
```

```ts
this._routes.goto('/users/');
```

This is the easiest fix and keeps your route table small.

### 2. Register both paths

If you can't control every inbound link (e.g. external links, bookmarks, server-rendered URLs), register `/users` and `/users/*` as two routes pointing at the same render:

```ts
this._routes = new Routes(this, [
  { path: '/users',   render: () => this._renderUsers() },
  { path: '/users/*', render: () => this._renderUsers() },
]);
```

Or normalize on entry by redirecting the bare form:

```ts
{ path: '/users', enter: async () => { this._routes.goto('/users/'); return false; } },
{ path: '/users/*', render: () => this._renderUsers() },
```

### What *not* to do

Don't try to make `*` match the missing slash by writing `/users*` — that pattern matches `/usersanything` (e.g. `/usersettings`), which is almost never what you want for a nested section.

### TL;DR

URLPattern requires the literal `/` in `/users/*`, so `/users` is a non-match by design. Either always link to `/users/`, or register `/users` alongside `/users/*`.

</details>

<details><summary>Skill-loaded answer</summary>

## Why it doesn't match

`@lit-labs/router` compiles each `path` string into a [`URLPattern`](https://developer.mozilla.org/en-US/docs/Web/API/URLPattern), and **`URLPattern` matching is literal, character-for-character**. The pattern `/users/*` is parsed as:

- the literal text `/users/`
- followed by `*`, which is a wildcard group meaning "zero or more characters"

The wildcard is **after** the second `/`, so the pattern requires that slash to be present in the URL. `/users` has no trailing slash, so it never even gets to the wildcard part — the literal prefix fails to match. (`*` matches zero characters, which is why `/users/` does match — the wildcard part is allowed to be empty, but the slash before it is not.)

This is just standard URLPattern / path-to-regexp semantics; lit-labs/router isn't doing anything special here.

## What to do

You have three reasonable fixes; pick based on intent.

**1. Make sure links/navigation include the trailing slash.** This is the simplest fix if `/users/` is really the canonical URL of the section:

```html
<a href="/users/">Users</a>
```

Since the router intercepts same-origin clicks, this Just Works.

**2. Register both paths.** If you want both `/users` and `/users/anything` to hit the same view, declare two routes:

```ts
this._routes = new Routes(this, [
  { path: '/users',   render: () => html`<x-users></x-users>` },
  { path: '/users/*', render: () => html`<x-users></x-users>` },
]);
```

**3. Redirect `/users` → `/users/`.** If you want a single canonical URL, give `/users` an `enter` hook that rewrites:

```ts
{
  path: '/users',
  enter: async () => {
    history.replaceState(null, '', '/users/');
    return false; // don't render this route; let the next match handle it
  },
}
```

For most apps, option 1 (just write the slash in your links) is the cleanest, and option 2 is the most forgiving if users might type or bookmark the URL by hand.

</details>

---

### `nested-routes-vs-router`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
My @lit-labs/router app has nested route sections — one for
`/users/...` and one for `/products/...`. Should each section
create its own `new Router(...)`? What's the right pattern?
```

**Judge:** **tie** — Both answers correctly identify that only one Router should be used per page, recommend Routes for nested sections, and explain that the reason is the global click and popstate listeners installed by Router. The answers are nearly identical in quality, structure, and technical accuracy. Answer A includes a slightly more detailed table and mentions routes.link() for child links, while Answer B mentions that Router extends Routes which is a useful technical detail. Neither has a meaningful advantage over the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies one Router per page | tie |
| recommends Routes for nesting | tie |
| mentions global click / popstate listener as the reason | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✓ | `ONE Router` |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global **`click` listener` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✓ | `ONE Router` |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global** listener` |

<details><summary>Baseline answer</summary>

Short answer: **No — don't create multiple `Router`s. Use one `Router` at the top, and a `Routes` controller for each nested section.**

## Why only one `Router`

`Router` extends `Routes`, but it adds a couple of *global, page‑level* side effects when it's installed:

- A global **`click` listener** on `window` that intercepts `<a href>` navigations.
- A global **`popstate` listener** on `window` that handles back/forward.

If you `new Router(...)` in two different components, you end up with two sets of those listeners fighting over the same navigation event — duplicated renders, double goto's, weird back‑button behavior, and whichever instance happens to win the race "captures" the URL. That's exactly the kind of bug this is designed to avoid.

So the rule is: **one `Router` per page**, almost always at your top‑level app shell.

## The right pattern: `Router` at the top, `Routes` underneath

`Routes` is the same controller as `Router` minus the global listeners. It's specifically designed for nested sections and it cooperates with the parent `Router` — when the parent matches a route ending in `/*`, it hands the tail off to the child `Routes`.

```ts
// app-shell.ts — the ONE Router on the page
import {LitElement, html} from 'lit';
import {Router} from '@lit-labs/router';

class AppShell extends LitElement {
  private _router = new Router(this, [
    {path: '/',           render: () => html`<home-page></home-page>`},
    {path: '/users/*',    render: () => html`<users-section></users-section>`},
    {path: '/products/*', render: () => html`<products-section></products-section>`},
  ]);

  render() { return this._router.outlet(); }
}
```

```ts
// users-section.ts — a nested section uses Routes, NOT Router
import {LitElement, html} from 'lit';
import {Routes} from '@lit-labs/router';

class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '/',       render: () => html`<users-list></users-list>`},
    {path: '/:id',    render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
    {path: '/:id/edit', render: ({id}) => html`<user-edit .id=${id}></user-edit>`},
  ]);

  render() { return this._routes.outlet(); }
}
```

`products-section.ts` looks identical — also a `Routes`, not another `Router`.

## Two related gotchas worth knowing

1. **Trailing slash on the parent.** The parent path needs to end in `/*` (e.g. `/users/*`) so the tail is forwarded to the child. URLPattern is strict about this — `/users` (no slash) won't match `/users/foo`.
2. **Linking between sections.** Use plain `<a href="/users/123">` — the top‑level `Router`'s click listener intercepts it. Don't reach for `goto()` for normal navigation; `goto()` doesn't push history.

TL;DR: one `Router` at the app shell, one `Routes` controller per nested section. Don't stack `Router`s.

</details>

<details><summary>Skill-loaded answer</summary>

# Short answer: No — one `Router` per page, `Routes` for nested sections

`@lit-labs/router` exports two reactive controllers:

| Controller | Where it goes |
|---|---|
| `Router`  | **Exactly one** per page — the top-level/root |
| `Routes`  | One per nested section (users, products, etc.) |

## Why only one `Router`

When you instantiate `Router`, it installs **global** listeners on the document/window:

- a global **click** listener that intercepts `<a href>` navigations
- a global **`popstate`** listener for back/forward
- it claims responsibility for reading `location.pathname`

If you `new Router(...)` again for `/users/...` and a third time for `/products/...`, you end up with three controllers all responding to the same click and popstate events, all trying to render based on the full pathname. They fight each other — you'll see double renders, the wrong section "winning," or back-button glitches.

`Routes` deliberately does **not** install those global listeners. It only resolves whatever path the parent `Router` (or parent `Routes`) hands down to it.

## The right pattern

```ts
// app-root.ts — the ONE Router
import {Router} from '@lit-labs/router';

class AppRoot extends LitElement {
  private _router = new Router(this, [
    {path: '/',            render: () => html`<app-home></app-home>`},
    {path: '/users/*',     render: () => html`<users-section></users-section>`},
    {path: '/products/*',  render: () => html`<products-section></products-section>`},
  ]);

  render() { return this._router.outlet(); }
}
```

```ts
// users-section.ts — nested Routes, NOT a new Router
import {Routes} from '@lit-labs/router';

class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '/',          render: () => html`<users-list></users-list>`},
    {path: ':id',        render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
    {path: ':id/edit',   render: ({id}) => html`<user-edit   .id=${id}></user-edit>`},
  ]);

  render() { return this._routes.outlet(); }
}
```

`products-section` follows the same shape with its own `Routes` controller.

## A couple of related gotchas while you're here

1. **Trailing slash on the parent path.** `/users/*` won't match a bare `/users` — link to `/users/` (or register both `/users` and `/users/*`).
2. **Use `routes.link('detail')` for child links** inside a nested section so the href is resolved against the parent prefix (`/users/`), not the document root.
3. **`router.goto()` doesn't push history.** Prefer plain `<a href>` (the root `Router`'s click handler intercepts it) or call `history.pushState` yourself.

So: one `Router` at the root, one `Routes` per nested section, and let the nested controllers compose.

</details>

---

### `link-helper`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
Inside a nested @lit-labs/router section mounted at `/users/`,
I want to render a link to a child route at `detail`. If I write
`<a href="detail">`, it won't work. What's the right way?
```

**Judge:** **tie** — Both answers correctly recommend the link() helper on the Routes controller and explain relative resolution well. Answer A provides more practical tips (click interception, programmatic navigation) but contains a minor inaccuracy claiming the router doesn't auto-intercept anchor clicks, while Answer B correctly notes the global click interceptor handles navigation. Answer B's explanation of why relative hrefs fail is slightly more precise (walking up the chain of parent Routes instances), but both answers satisfy the rubric criteria equally well.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends link() helper | tie |
| explains relative resolution | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `relative` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `relative` |

<details><summary>Baseline answer</summary>

# Use the child `Routes` instance's `link()` helper

`@lit-labs/router` is designed for exactly this situation. The child `Routes` (or `Router`) instance you instantiated for the nested section knows the path prefix it was mounted under (`/users/`), and it exposes a `link()` method that prepends that prefix for you.

```ts
import {Routes} from '@lit-labs/router';

class UsersView extends LitElement {
  // Mounted by the parent at `/users/*`
  private _routes = new Routes(this, [
    {path: 'detail', render: () => html`<user-detail></user-detail>`},
    // ...
  ]);

  render() {
    return html`
      <a href=${this._routes.link('detail')}>Detail</a>
      ${this._routes.outlet()}
    `;
  }
}
```

`this._routes.link('detail')` will produce `/users/detail` (and `this._routes.link()` with no argument gives you the prefix itself, useful for an "index" link).

## Why `<a href="detail">` doesn't work

A bare relative href is resolved by the **browser**, against the current document URL — and crucially, browsers treat the last path segment as a "file" unless the URL ends in a slash:

- On `/users/` → `detail` resolves to `/users/detail` ✅
- On `/users` (no trailing slash) → `detail` resolves to `/detail` ❌
- On `/users/123` → `detail` resolves to `/users/detail` (replaces `123`) — often not what you want either.

`Routes.link()` sidesteps all of that by always producing the correct absolute path based on where the nested router is mounted, regardless of the current URL within it.

## A couple of related tips

1. **Intercept clicks for client-side navigation.** A plain `<a>` will still cause a full page load. Either use a tiny click handler that calls `router.goto(href)` and `event.preventDefault()`, or wrap the anchor in a small component that does this. The router doesn't auto-intercept anchor clicks.

2. **Going up to a parent route** (e.g. back to `/users/`): use the parent `Routes` instance's `link()`, or pass the absolute path explicitly. Child `Routes` only knows about paths *within* its own prefix.

3. **For programmatic navigation,** prefer `this._routes.goto('detail')` — it uses the same prefix logic as `link()`.

</details>

<details><summary>Skill-loaded answer</summary>

Use the `link()` helper on the nested `Routes` controller — that's exactly what it's there for.

```ts
import {Routes} from '@lit-labs/router/routes.js';

class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: 'detail', render: () => html`<user-detail></user-detail>`},
    // ...
  ]);

  render() {
    return html`
      <a href=${this._routes.link('detail')}>Detail</a>
    `;
  }
}
```

### Why a bare `<a href="detail">` doesn't work

A relative href like `"detail"` is resolved by the browser against the **current document URL**, not against your nested route's mount point. So if the user is sitting at `/users/`, the link works by accident; but at `/users/42` the browser resolves `"detail"` to `/users/detail` relative to the *last path segment*, and at `/users/42/edit` it goes somewhere else again. The router has no chance to fix this — by the time it sees the click, the href has already been resolved to a final URL.

`Routes#link(pathTail?)` does the right thing: it walks up the chain of parent `Routes`/`Router` instances and prepends each parent's matched prefix, so `this._routes.link('detail')` always produces `/users/detail` regardless of where inside the section you currently are. Calling it with no argument (`this._routes.link()`) gives you the URL of the section's mount point itself, which is handy for "back to list" links.

Once the href is an absolute path produced by `link()`, the `Router`'s global click interceptor handles the navigation client-side as usual — no `goto()` / `pushState` plumbing needed in your click handler.

</details>

---

### `simplest-hash-routing`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I want hash routing (URLs like /#/users/123 instead of
/users/123) using @lit-labs/router. What's the simplest way to
set this up?
```

**Judge:** **skill** — Answer B correctly states that @lit-labs/router does not support hash routing and avoids inventing a hash-routing API by clearly explaining the limitation upfront and recommending alternatives. Answer A, while technically creative, invents a hash-routing setup using @lit-labs/router's internal goto() method as if it were a supported pattern, which is exactly the trap the rubric warns against. Answer B satisfies both rubric criteria by being honest about the limitation and steering users toward proper solutions.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states hash routing is not supported | skill |
| avoids inventing a hash-routing API | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states hash routing is not supported | ✗ | |
| avoids inventing a hash-routing API | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states hash routing is not supported | ✓ | `doesn't support` |
| avoids inventing a hash-routing API | ✗ | `hash: true` |

<details><summary>Baseline answer</summary>

Short answer: `@lit-labs/router` doesn't ship a hash-mode out of the box — it's built around `URLPattern` + `popstate` + click interception on real paths. But you can bridge it to the hash with very little code.

The simplest setup is a tiny "hash adapter" that:

1. Tells the `Router` to read its current path from `location.hash`.
2. Calls `router.goto(...)` whenever `hashchange` fires.
3. Intercepts your `<a href="#/...">` clicks (or just lets the browser update the hash naturally — no `pushState` needed).

```ts
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { Router } from '@lit-labs/router';

// Read "/users/123" out of "#/users/123" (default to "/")
const hashPath = () => '/' + (location.hash.replace(/^#\/?/, ''));

@customElement('my-app')
export class MyApp extends LitElement {
  private _router = new Router(this, [
    { path: '/',            render: () => html`<h1>Home</h1>` },
    { path: '/users/:id',   render: ({ id }) => html`<user-page .id=${id}></user-page>` },
    { path: '/*',           render: () => html`<h1>Not found</h1>` },
  ]);

  connectedCallback() {
    super.connectedCallback();
    // Initial route
    this._router.goto(hashPath());
    // Subsequent hash changes (back/forward, link clicks, manual edits)
    window.addEventListener('hashchange', this._onHashChange);
  }

  disconnectedCallback() {
    window.removeEventListener('hashchange', this._onHashChange);
    super.disconnectedCallback();
  }

  private _onHashChange = () => this._router.goto(hashPath());

  render() {
    return html`
      <nav>
        <a href="#/">Home</a>
        <a href="#/users/123">User 123</a>
      </nav>
      ${this._router.outlet()}
    `;
  }
}
```

A few important gotchas worth knowing, since they trip people up:

- **Use `<a href="#/...">` for navigation, not `router.goto(...)` alone.** `goto()` doesn't update history (that's a known pitfall), and with hash routing you specifically *want* the browser to update `location.hash` so back/forward works. Setting the hash via a link (or `location.hash = '/users/123'`) automatically fires `hashchange` and pushes a history entry for free — no `pushState` needed.
- **Only one `Router` per page.** It installs global click + `popstate` listeners; if you have nested route sections, use the `Routes` controller for them, not another `Router`.
- **Trailing slashes still matter** because routes are matched with `URLPattern`. If you register `/users/*`, link to `#/users/` (with the slash) or also register `/users` — the hash adapter doesn't change `URLPattern` semantics.
- The router's built-in click interception is geared toward same-origin path links. With hash links you don't really need it — the browser's native hash behavior is doing the work, and your `hashchange` listener feeds the router.

If you ever want to switch back to real path routing later, you delete the `hashPath()` helper and the `hashchange` listener, and the same routes table keeps working.

</details>

<details><summary>Skill-loaded answer</summary>

Short answer: you can't, really — at least not out of the box. `@lit-labs/router` doesn't support hash routing. It inspects `location.pathname` (and listens for `popstate` + intercepts `<a>` clicks), and it has no `hash: true` option, no `HashRouter` class, and no hook to swap the location source. So there isn't a one-line "turn on hash mode" setup to give you.

You have basically three options, in order of simplicity:

### 1. Use a different router (simplest)
If hash routing is a hard requirement (e.g. you're deploying to static hosting that can't do SPA fallbacks), pick a router that supports it natively — `vaadin-router` has `setRoutes` plus a `useHash`-style pattern, and `navigo` supports hash mode directly. That's far less work than bending `@lit-labs/router` into a shape it wasn't built for.

### 2. Configure your host for pathname routing
Most "I need hash routing" cases are really "my host 404s on deep links." If you control the server (or are on Netlify/Vercel/Cloudflare Pages/etc.), add an SPA fallback that rewrites unknown paths to `index.html`. Then plain `@lit-labs/router` works as designed and your URLs stay clean.

### 3. Bridge hash → pathname yourself (only if you must)
If you really need `/#/users/123` *and* `@lit-labs/router`, you'd have to translate between the two yourself — something like:

```js
// On load and on hashchange, mirror the hash into the pathname
// the router sees, then ask the router to re-resolve.
window.addEventListener('hashchange', () => {
  const path = location.hash.replace(/^#/, '') || '/';
  history.replaceState(null, '', path);
  this._router.goto(path); // re-render the matched route
});
```

This works but it's a hack: you're fighting the library, every navigation has to be funneled through your shim, and `<a href="#/...">` link interception won't behave the way it does with normal paths. I'd only reach for this if options 1 and 2 are off the table.

My recommendation: do (2) if you can, otherwise (1). Don't invent a hash mode for `@lit-labs/router` — it doesn't have one.

</details>

---

### `offtopic-git-rebase`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the difference between `git merge` and `git rebase`?
Just a short, plain explanation.
```

**Judge:** **tie** — Both answers are essentially equivalent in accuracy, clarity, and usefulness. They cover the same core concepts (merge commit vs. linear history rewrite) and offer the same practical rule of thumb. Answer B adds a small detail about 'replaying commits one by one' and 'non-linear' labeling, but neither is materially better than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

**git merge** combines two branches by creating a new "merge commit" that ties their histories together. Both branches' histories are preserved as-is, including the point where they diverged and rejoined.

**git rebase** moves your branch's commits on top of another branch, replaying them one by one. This rewrites history to make it look like your work happened linearly after the other branch, with no merge commit.

In short:
- **Merge** = preserves history, adds a merge commit (non-linear).
- **Rebase** = rewrites history, keeps it clean and linear.

Rule of thumb: merge for shared/public branches, rebase for cleaning up your local work before sharing.

</details>

<details><summary>Skill-loaded answer</summary>

**git merge** combines two branches by creating a new "merge commit" that ties their histories together. Both branches' histories are preserved as-is.

**git rebase** moves your branch's commits on top of another branch, rewriting them as if you'd started from there. The result is a clean, linear history with no merge commit.

Quick rule of thumb:
- Use **merge** to preserve history (good for shared branches).
- Use **rebase** to keep history tidy (good for your own local work before sharing).

</details>

---
