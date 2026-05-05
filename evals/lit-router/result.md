# Eval report: `lit-router`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **6**
- Models: **sonnet, haiku, opus**
- Total cost: **$1.41** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 4/6 | 4 / 1 / 1 | 80% → 83% (+3%) |
| `haiku` | 6/6 | 5 / 0 / 1 | 60% → 100% (+40%) |
| `opus` ¹ | 4/6 | 4 / 1 / 1 | 83% → 83% (+0%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 4 | 3/4 | 4/4 | 3/4 |
| `skill_wins_strict` | 1 | 0/1 | 1/1 | 0/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `goto-doesnt-update-url` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `trailing-slash-routes` | skill_wins | ✗ ✗ baseline | ✓ ✓ skill | ✗ ✗ baseline |
| `nested-routes-vs-router` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `link-helper` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `simplest-hash-routing` | skill_wins_strict | ✗ ✓ skill | ✓ ✓ skill | ✗ ✓ skill |
| `offtopic-git-rebase` | tie | ✓ = tie | ✓ = tie | ✓ = tie |

## Per-case detail

### `goto-doesnt-update-url`

**Prompt**

```
I'm using @lit-labs/router. I call `this._router.goto('/dashboard')`
inside a click handler, and the new route renders, but the URL
bar doesn't change and the browser back button is broken. What's
going on?
```

**Judge focus:** The better answer pinpoints that goto() does NOT update history,
and tells the user to call history.pushState (or use a regular
<a href> link, which the router intercepts).

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify that goto() does not push history and recommend history.pushState and <a href> links. Answer B adds some extra content (popstate handling, custom events) that goes slightly beyond the question but is still useful. However, Answer A is more concise, better organized, and includes a practical helper function pattern. The popstate listener in Answer B is actually somewhat misleading since @lit-labs/router handles popstate internally. Both answers cover all three rubric criteria equally well, making this very close, but Answer A's clarity and accuracy give it a slight edge.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains goto does not push history | tie |
| recommends history.pushState | tie |
| mentions <a href> link interception | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `history.pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `does not call `history.pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

<details><summary>sonnet: baseline answer</summary>

## The Problem

`@lit-labs/router` uses the **History API** internally, but `goto()` only updates the router's internal state — it does **not** automatically call `history.pushState()` to update the browser's URL bar or create a history entry.

---

## The Fix

You need to call `window.history.pushState()` yourself **before or alongside** `goto()`, or use the router's built-in link handling instead.

### Option 1: Push state manually alongside `goto()`

```javascript
handleClick(path) {
  window.history.pushState({}, '', path); // ← updates URL bar + history stack
  this._router.goto(path);               // ← updates router state
}
```

```javascript
// Example in a LitElement
_handleNavClick(e) {
  e.preventDefault();
  const path = '/dashboard';
  window.history.pushState({}, '', path);
  this._router.goto(path);
}
```

---

### Option 2: Use anchor tags (recommended)

The router installs a **click interceptor** on `<a>` tags automatically. Let it do the work:

```javascript
// In your render() method — no click handler needed
render() {
  return html`
    <a href="/dashboard">Dashboard</a>
  `;
}
```

The router intercepts the click, calls `pushState`, and updates itself. This is the idiomatic approach.

---

### Option 3: Dispatch a custom event and handle centrally

Keep navigation logic in one place:

```javascript
// In any component
this.dispatchEvent(new CustomEvent('navigate', {
  bubbles: true,
  composed: true,
  detail: { path: '/dashboard' }
}));

// In your root app component
this.addEventListener('navigate', (e) => {
  window.history.pushState({}, '', e.detail.path);
  this._router.goto(e.detail.path);
});
```

---

## Also Handle the Back Button

The back button fires `popstate`, which `goto()` alone won't respond to. Make sure you handle it:

```javascript
connectedCallback() {
  super.connectedCallback();
  this._onPopState = () => this._router.goto(window.location.pathname);
  window.addEventListener('popstate', this._onPopState);
}

disconnectedCallback() {
  super.disconnectedCallback();
  window.removeEventListener('popstate', this._onPopState);
}
```

---

## Summary

| What you did | What was missing |
|---|---|
| `router.goto('/dashboard')` | Updates router state only |
| `history.pushState(...)` | Updates URL bar + back/forward stack |
| `popstate` listener | Syncs router when user hits back/forward |

**The root cause:** `goto()` is a *state* update, not a *navigation* action. Full navigation requires both the router state and the browser history to be updated together.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## The Problem

`goto()` updates the router's internal state and re-renders the component, but it **does not call `history.pushState`**. That's a known design quirk of `@lit-labs/router` — the two are intentionally separate, but this means you have to pair them yourself.

## The Fix

Call `history.pushState` **before** `goto()`:

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}
```

Then in your click handler:

```ts
html`<button @click=${() => this._navigate('/dashboard')}>
  Dashboard
</button>`
```

## Why This Order Matters

| Step | What it does |
|------|-------------|
| `history.pushState({}, '', path)` | Updates the URL bar and adds an entry to the browser history stack |
| `this._router.goto(path)` | Matches the path against your routes and triggers a re-render |

If you only call `goto()`, the page renders correctly but the URL bar is stale. When the user hits **Back**, the browser pops to the previous URL — but since that URL was never pushed, the history stack is broken.

## Prefer `<a href>` When You Can

The router's built-in click interceptor handles this pairing automatically for standard links — no manual `pushState` needed:

```ts
html`<a href="/dashboard">Dashboard</a>`
```

The interceptor fires for same-origin links with no `target`, no `download`, no `rel="external"`, and no modifier keys held. If your use case fits, this is the simpler and less error-prone path.

## If You Navigate in Many Places

Extract the helper so the pairing is never accidentally split:

```ts
// navigation.ts
export function navigate(router: Router, path: string) {
  history.pushState({}, '', path);
  router.goto(path);
}
```

This also makes it easy to add extras later (analytics, scroll reset, etc.) in one place.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the root cause: goto() does not update browser history or the URL bar, and recommends pairing it with history.pushState(). Answer A incorrectly diagnoses the problem as a missing await, which is not the actual issue described, and its explanation of why awaiting fixes history is factually wrong. Answer B covers all three rubric criteria accurately and thoroughly.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains goto does not push history | skill |
| recommends history.pushState | skill |
| mentions <a href> link interception | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✗ | |
| recommends history.pushState | ✗ | |
| mentions <a href> link interception | ✓ | `<a href` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `NOT touch history` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

<details><summary>haiku: baseline answer</summary>

# The Issue

You're likely calling `goto()` without awaiting it. The `@lit-labs/router` `goto()` method is **asynchronous**, and you need to wait for it to complete before the URL updates.

## Solution

**Await the `goto()` call:**

```typescript
async handleClick() {
  await this._router.goto('/dashboard');
}
```

Or in your click handler:

```typescript
@query('a')
link!: HTMLAnchorElement;

render() {
  return html`
    <button @click=${async () => await this._router.goto('/dashboard')}>
      Go to Dashboard
    </button>
  `;
}
```

## Why This Matters

Without awaiting:
- The route change starts but doesn't complete before the handler finishes
- The view updates (because Lit re-renders), but the URL bar and history don't sync
- Browser history is broken

With `await`:
- The router completes the full navigation cycle
- URL bar updates
- Browser history is properly maintained
- Back button works correctly

## Alternative: Use Links

If you're navigating on click, consider using standard `<a>` tags instead, which the router handles automatically:

```typescript
render() {
  return html`<a href="/dashboard">Go to Dashboard</a>`;
}
```

The router intercepts link clicks and handles navigation properly without manual `goto()` calls.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# The Problem

You're calling `goto()` without `history.pushState()`. The `goto()` method updates the *rendered* route, but it does **not** change the URL bar or the browser history — that's a known gotcha in `@lit-labs/router`.

When you skip `pushState`, the URL bar stays at the old path while the page renders the new route. Then the back button is broken because the history stack was never updated.

## The Fix

**Always pair `history.pushState` with `router.goto`:**

```ts
private _router = new Router(this, [/* routes */]);

private handleNavigate(path: string) {
  // 1. Update the history stack
  history.pushState({}, '', path);
  // 2. Update the rendered route
  this._router.goto(path);
}
```

Then call it from your click handler:

```ts
render() {
  return html`
    <button @click=${() => this.handleNavigate('/dashboard')}>
      Go to Dashboard
    </button>
  `;
}
```

## Why This Happens

- **`goto(path)`** — Updates `this._router.params` and calls `requestUpdate()`, so the new route renders. Does NOT touch history or the URL bar.
- **`history.pushState(state, unused, url)`** — Updates the URL bar and the history stack. Does NOT tell the router to re-render.

You need both.

## Automatic Click Interception (Preferred)

If you use **`<a href>`** instead, the router intercepts the click automatically and does both for you:

```ts
render() {
  return html`
    <a href="/dashboard">Go to Dashboard</a>
  `;
}
```

This works because `Router` installs a global `click` listener that:
1. Detects same-origin `<a>` clicks (no `target`, no modifier keys, no `download`/`rel="external"`)
2. Calls `history.pushState()`
3. Calls `goto()`

**Recommendation:** Use `<a href>` whenever possible. Reserve `goto()` + `pushState` for cases where you can't use a link (e.g., form submission, programmatic navigation from a non-link element).

See [references/navigation.md](references/navigation.md) for the full click-interception rule list and [references/pitfalls.md](references/pitfalls.md) for why this design exists.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify that goto() does not push history and recommend history.pushState as the fix. Answer A is slightly more accurate and idiomatic: it correctly explains that the router's global click listener handles both pushState and goto automatically when using <a href> links, which is the proper description of how @lit-labs/router works. Answer B's Option 3 is vague ('Most apps end up writing a tiny helper') and doesn't clearly state that the router itself intercepts link clicks. Answer B also includes a potentially misleading Option 2 (dispatching popstate manually) which is a less clean pattern. Answer A's explanation of why goto() is designed this way (it's also used by the popstate handler) is particularly insightful.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains goto does not push history | tie |
| recommends history.pushState | tie |
| mentions <a href> link interception | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `does not call `history.pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `does NOT call `history.pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

<details><summary>opus: baseline answer</summary>

# The Issue: `goto()` Doesn't Update the URL

This is a known limitation (and source of confusion) with `@lit-labs/router`. The `goto()` method **only updates the router's internal state and triggers a re-render** — it does not call `history.pushState()` or otherwise touch the URL bar.

From the package docs:

> `goto()` is mostly intended for use in tests and for programmatic navigation that doesn't need to update the URL.

That's why your view changes but the address bar stays put and the back button has nothing to navigate back to.

## The Fix

You need to update browser history yourself, then let the router pick up the change. There are a couple of ways to do this:

### Option 1: pushState + goto

```js
_navigate(path) {
  window.history.pushState({}, '', path);
  this._router.goto(path);
}

// in your click handler
this._navigate('/dashboard');
```

### Option 2: pushState + dispatch a popstate-like event

If you've wired the router to listen to `popstate` (which is the typical setup), you can do:

```js
_navigate(path) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}
```

### Option 3: Use a link and let the router intercept it

If the navigation originates from a user click, the cleanest pattern is just to render an `<a href="/dashboard">` and have a global click handler that intercepts same-origin clicks, calls `pushState`, and triggers the router. Most apps using `@lit-labs/router` end up writing a tiny helper for this.

## Why It's Designed This Way

`@lit-labs/router` is intentionally minimal and unopinionated about history management — it leaves URL/history concerns to you so it works in tests, embedded contexts, and apps that use hash routing, memory routing, etc. The trade-off is that `goto()` looks like a navigation API but really isn't one in the browser-history sense.

## TL;DR

`goto()` ≠ navigation. Always pair it with `history.pushState()` (or use `<a>` tags with a click interceptor) when you want the URL bar and back button to work.

</details>

<details><summary>opus: skill-loaded answer</summary>

## What's happening

This is a known gotcha in `@lit-labs/router`: **`router.goto()` does NOT call `history.pushState`.** It only matches the path against your routes, runs `enter`, updates `params`, and re-renders the outlet. It never touches the History API.

So when you call `goto('/dashboard')` from a click handler:

1. The router matches `/dashboard`, renders the dashboard component ✅
2. The URL bar still shows the old URL ❌
3. No new history entry is pushed, so back/forward have nothing to navigate to ❌

## The fix

Always pair `history.pushState` with `goto()`:

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}

// in your click handler:
this._navigate('/dashboard');
```

A small helper like this is worth adding once and reusing everywhere you navigate programmatically.

## Better: just use a link

If your click handler is on a button purely to navigate, prefer an `<a href="/dashboard">`. The `Router` installs a global click listener that intercepts same-origin link clicks and handles both the `pushState` and the `goto` for you — no manual wiring needed. The interception applies as long as the link has no `target`, no `download`, no `rel="external"`, and the click has no modifier keys (Ctrl/Cmd/Shift/Alt).

```html
<a href="/dashboard">Dashboard</a>
```

That's the idiomatic path and it gets back/forward right automatically.

## Why it's designed this way

`goto()` is the low-level "render this route now" primitive — it's also what the internal `popstate` handler calls when the user hits back/forward (where you specifically *don't* want to push a new entry). Pushing history is left to the caller so the same method serves both directions. The tradeoff is that it's easy to forget when navigating programmatically, which is exactly what bit you.

</details>

---

### `trailing-slash-routes`

**Prompt**

```
I have a `@lit-labs/router` route with path `/users/*` for a
nested users section. When I navigate to `/users` (no trailing
slash), the route doesn't match. Why, and what do I do?
```

**Judge focus:** The better answer explains URLPattern semantics — `/users/*`
requires the slash and one of: link with trailing slash, or
register both `/users` and `/users/*`.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly identify URLPattern semantics as the root cause and cover registering both paths. Answer A adds a valuable third option — the `{/*}?` optional group syntax — which is arguably the most elegant single-route solution and directly addresses the URLPattern semantics criterion in depth. Answer B's strength is emphasizing the trailing-slash link fix as the primary recommendation, but it lacks the optional-group pattern. Overall Answer A covers more ground with higher technical depth.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies URLPattern matching semantics | baseline |
| recommends adding trailing slash to links | skill |
| mentions registering both paths as alternative | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `/users/` |
| mentions registering both paths as alternative | ✓ | `two routes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `both path` |

<details><summary>sonnet: baseline answer</summary>

## The Problem

The `/*` wildcard pattern in `@lit-labs/router` uses **URLPattern** under the hood. The pattern `/users/*` requires at least one character after the slash — meaning `/users/` (empty wildcard) may match, but `/users` (no slash at all) does **not**.

```js
// This pattern...
{ path: '/users/*' }

// Matches:  /users/        ✅
// Matches:  /users/123     ✅
// Matches:  /users/foo/bar ✅
// Does NOT match: /users   ❌
```

---

## Solutions

### 1. Define Both Routes (Recommended)

Add a second route entry for the exact `/users` path, pointing to the same component or a redirect:

```js
import { Router } from '@lit-labs/router';

this._router = new Router(this, [
  { path: '/users',   render: () => html`<users-section></users-section>` },
  { path: '/users/*', render: () => html`<users-section></users-section>` },
]);
```

This is the clearest and most explicit approach.

---

### 2. Use an Optional Group with URLPattern Syntax

URLPattern supports optional groups using `{/}?`, letting you express "slash and wildcard are both optional":

```js
this._router = new Router(this, [
  {
    path: '/users{/*}?',
    render: ({ pathname }) => html`<users-section></users-section>`,
  },
]);
```

| Pattern      | Matches `/users` | Matches `/users/` | Matches `/users/123` |
|--------------|:---:|:---:|:---:|
| `/users/*`   | ❌  | ✅  | ✅  |
| `/users{/*}?`| ✅  | ✅  | ✅  |

> `{...}?` is a URLPattern **optional non-capturing group** — the entire `/*` segment becomes optional.

---

### 3. Redirect `/users` → `/users/` at the App Level

If you control navigation, normalize the URL before the router sees it:

```js
// Intercept clicks or navigation and normalize
if (location.pathname === '/users') {
  history.replaceState({}, '', '/users/');
}
```

This is fragile and not recommended unless you need it for other reasons.

---

## Recommendation

Use **option 2** (`/users{/*}?`) — it's a single route, uses standard URLPattern syntax, and handles all cases cleanly. Fall back to **option 1** (two routes) if you need different behavior for the index vs. sub-pages.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Why It Happens

`@lit-labs/router` compiles your `path` string into a `URLPattern` with `pathname` matching. The pattern `/users/*` expands to something like:

```
/users/<zero-or-more characters>
```

The `*` wildcard requires the literal `/` after `users` to be present — so `/users/` and `/users/foo` match, but `/users` (no slash, no wildcard segment at all) does **not**. This is standard `URLPattern` behaviour, not a bug in the router.

## Your Options

### Option 1 — Fix the link (preferred for simple cases)

If you control the nav link, just add the trailing slash:

```ts
// ❌ doesn't match /users/*
html`<a href="/users">Users</a>`

// ✅ matches /users/*
html`<a href="/users/">Users</a>`
```

That's often all you need.

---

### Option 2 — Add a redirect route for the bare path

Add a sibling route above the wildcard one that catches `/users` and redirects:

```ts
private _router = new Router(this, [
  {
    path: '/users',
    enter: async () => {
      history.replaceState({}, '', '/users/');
      await this._router.goto('/users/');
      return false; // cancel this route — goto() handles rendering
    },
  },
  {
    path: '/users/*',
    render: () => html`<users-section></users-section>`,
  },
]);
```

`return false` from `enter` cancels the current navigation, and `goto('/users/')` takes over. `replaceState` (not `pushState`) keeps the back button clean.

---

### Option 3 — Match both paths explicitly

If you don't want a redirect, add a second route that renders the same component for the bare path:

```ts
private _router = new Router(this, [
  {
    path: '/users',
    render: () => html`<users-section></users-section>`,
  },
  {
    path: '/users/*',
    render: () => html`<users-section></users-section>`,
  },
]);
```

This works but means the child `Routes` controller inside `<users-section>` won't receive a tail group when matched via `/users` — so its index route (`path: ''`) may not render correctly. Option 1 or 2 is safer.

---

## The Rule to Remember

> **Always link to a nested route mount with a trailing slash.**  
> `/users/*` → link as `<a href="/users/">`, never `<a href="/users">`.

This is called out as a known pitfall in the library — the trailing slash is load-bearing.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly explains URLPattern semantics — that `/users/*` requires a literal slash before the wildcard, so `/users/` matches but `/users` does not. Answer B incorrectly states that `*` requires 'at least one segment' (it actually matches zero or more characters), and its solutions use APIs like `router.goto()` and `children` that don't exist in `@lit-labs/router`. Answer A provides accurate, actionable solutions including linking with trailing slash and registering both paths.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies URLPattern matching semantics | skill |
| recommends adding trailing slash to links | skill |
| mentions registering both paths as alternative | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `pattern doesn't match` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `/users` and `/users/*` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `/users` and `/users/*` |

<details><summary>haiku: baseline answer</summary>

# Route Matching Issue with `@lit-labs/router`

The route `/users/*` requires at least one segment after `/users/` to match. When you navigate to `/users` without a trailing slash, there's nothing after `users`, so the pattern doesn't match.

## Solutions

### Option 1: Make the nested segment optional (Recommended)

Use a pattern that matches both `/users` and `/users/*`:

```javascript
{
  path: '/users',
  component: 'users-section',
  children: [
    // your nested routes
  ]
}
```

Then handle both cases in your component, or redirect:

```javascript
{
  path: '/users',
  action: () => router.goto('/users/list') // or your default route
}
```

### Option 2: Add a redirect route

```javascript
{
  path: '/users',
  action: () => router.goto('/users/list')
},
{
  path: '/users/*',
  component: 'users-section'
}
```

### Option 3: Use a catch-all with default handling

If using `@lit-labs/router` with a parent route:

```javascript
{
  path: '/users',
  component: 'users-layout',
  children: [
    {
      path: '/',
      component: 'users-default' // matches /users/
    },
    {
      path: '/:id',
      component: 'user-detail'
    }
  ]
}
```

Then ensure your server/router redirects `/users` → `/users/` if needed.

**The key**: `*` patterns need content to match. Use redirects or optional segments to handle the base path.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Trailing-Slash Matching in `/users/*` Routes

## Why It Doesn't Match

`URLPattern` treats `/users` and `/users/` as **distinct paths**. When you define a parent route with `path: '/users/*'`, the `*` wildcard matches **zero or more characters after the `/`**, but only if the path **starts with `/users/`** (with the slash).

- `/users/` → matches `/users/*` (tail is empty string)
- `/users/123` → matches `/users/*` (tail is `123`)
- `/users` → does **not** match `/users/*` (no trailing slash)

This is a known pitfall of the library.

## Solutions

### 1. **Always Link with a Trailing Slash** (Recommended)

Change your navigation links to include the trailing slash:

```ts
// ❌ Don't do this
<a href="/users">Users</a>

// ✅ Do this
<a href="/users/">Users</a>
```

This is the simplest fix and aligns with REST conventions for collection endpoints.

### 2. **Add a Redirect Route**

Add a sibling route that catches the bare path and re-routes:

```ts
const routes = [
  {
    path: '/users',
    render: () => {
      // Redirect to /users/
      history.replaceState({}, '', '/users/');
      return html`<users-section></users-section>`;
    },
  },
  {
    path: '/users/*',
    render: () => html`<users-section></users-section>`,
  },
  // ... other routes
];
```

Or use `enter` to redirect before rendering:

```ts
{
  path: '/users',
  enter: () => {
    history.replaceState({}, '', '/users/');
    // Return false to cancel this route and let the next one match
    return false;
  },
},
```

### 3. **Use a Catch-All Pattern** (Less Ideal)

If you need both `/users` and `/users/*` to work identically, you could match both explicitly:

```ts
{
  path: '/users',
  render: () => html`<users-section></users-section>`,
},
{
  path: '/users/*',
  render: () => html`<users-section></users-section>`,
},
```

But this duplicates logic and is harder to maintain.

## Best Practice

**Use option 1**: always link with a trailing slash (`/users/`). This is:
- The clearest intent (collection endpoint)
- The least code
- Consistent with REST conventions
- What the library expects

If you're migrating from another router that was lenient about trailing slashes, add a server-side or client-side redirect layer to normalize incoming URLs to the trailing-slash form.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly identify URLPattern semantics and offer similar solutions. Answer A introduces the elegant `/users{/*}?` optional group syntax which is a genuinely useful URLPattern feature that Answer B misses entirely. Answer B's analysis of Option 3's limitations (child routes not being reachable) is a nice touch, but Answer A's Option 2 with the optional group is arguably the cleanest solution overall and demonstrates deeper URLPattern knowledge.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies URLPattern matching semantics | tie |
| recommends adding trailing slash to links | skill |
| mentions registering both paths as alternative | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `/users/` |
| mentions registering both paths as alternative | ✓ | `two routes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `two routes` |

<details><summary>opus: baseline answer</summary>

# Why `/users/*` doesn't match `/users`

`@lit-labs/router` uses [`URLPattern`](https://developer.mozilla.org/en-US/docs/Web/API/URLPattern) under the hood for path matching. In `URLPattern` syntax, `*` is a wildcard that matches **zero or more characters**, but the `/` before it is a **literal character that must be present**.

So the pattern `/users/*` actually requires:
- The literal string `/users/`
- Followed by zero or more characters

That means:
- ✅ `/users/` matches (wildcard matches empty string)
- ✅ `/users/profile` matches
- ❌ `/users` does **not** match (missing the trailing `/`)

## Solutions

### Option 1: Add two routes

```js
this.router = new Router(this, [
  { path: '/users',   render: () => this.renderUsers() },
  { path: '/users/*', render: () => this.renderUsers() },
]);
```

### Option 2: Make the slash + suffix optional with a group

Wrap the `/` and wildcard in a group and mark it optional with `?`:

```js
{ path: '/users{/*}?', render: () => this.renderUsers() }
```

This matches `/users`, `/users/`, and `/users/anything`.

### Option 3: Redirect to the canonical form

If you'd rather have a single canonical URL, redirect `/users` to `/users/`:

```js
{
  path: '/users',
  enter: () => {
    history.replaceState(null, '', '/users/');
    this.router.goto('/users/');
    return false;
  },
},
{ path: '/users/*', render: () => this.renderUsers() },
```

## Recommendation

For nested sections that should behave as a single area, **Option 2** (`/users{/*}?`) is usually cleanest — it keeps a single route handler and matches all the variants users might type or link to.

</details>

<details><summary>opus: skill-loaded answer</summary>

## Why it doesn't match

`@lit-labs/router` compiles your `path` into a `URLPattern({pathname: '/users/*'})`. The `*` is a wildcard *segment* that matches zero or more characters **after** the literal `/users/`. The pattern requires the trailing slash to be present in the URL — so:

- `/users/` ✅ matches (the `*` captures `''`)
- `/users/foo` ✅ matches (the `*` captures `'foo'`)
- `/users` ❌ does **not** match — there's no `/` after `users`

This is `URLPattern` behavior, not a bug in the router.

## What to do

You have three good options, in rough order of preference:

### 1. Always link with the trailing slash (simplest)

```html
<a href="/users/">Users</a>
```

Inside the nested `Routes`, the index uses `path: ''`:

```ts
new Routes(this, [
  {path: '',     render: () => html`<user-list></user-list>`},
  {path: ':id',  render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
]);
```

This is the canonical pattern and what the library expects.

### 2. Add a sibling route that redirects bare `/users` to `/users/`

```ts
new Router(this, [
  {
    path: '/users',
    enter: () => {
      history.replaceState({}, '', '/users/');
      this._router.goto('/users/');
      return false; // cancel this navigation; goto handles the real one
    },
    render: () => html``,
  },
  {path: '/users/*', render: () => html`<users-section></users-section>`},
  // ...
]);
```

Use this if external links or bookmarks to `/users` are out in the wild.

### 3. Add `/users` as a second matching route alongside `/users/*`

```ts
{path: '/users', render: () => html`<users-section></users-section>`},
{path: '/users/*', render: () => html`<users-section></users-section>`},
```

Works, but you now have two routes pointing at the same component, and the bare-`/users` case won't have a tail group for the nested `Routes` to match against — the child's `path: ''` index will render but `path: ':id'` won't be reachable from there. Generally inferior to option 2.

## Recommendation

Go with **option 1**. Fix your nav links to use `/users/` and you're done. If you can't control all inbound links, add the **option 2** redirect on top.

</details>

---

### `nested-routes-vs-router`

**Prompt**

```
My @lit-labs/router app has nested route sections — one for
`/users/...` and one for `/products/...`. Should each section
create its own `new Router(...)`? What's the right pattern?
```

**Judge focus:** The better answer says NO — only one Router per page (it installs
global click + popstate listeners; multiples conflict). Use Routes
(the other controller) for nested sections.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the `Routes` controller as the proper tool for nested sections, which is the core of the question and the focus area. Answer A says 'no multiple Routers' correctly but never mentions `Routes` at all — it instead suggests manual path matching with regex or flattening all routes, missing the actual API designed for this use case. Answer B also explicitly mentions the global click and popstate listeners as the reason to avoid multiple Routers, satisfying all three rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies one Router per page | tie |
| recommends Routes for nesting | skill |
| mentions global click / popstate listener as the reason | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✓ | `One Router` |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `popstate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✗ | |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global** `click` |

<details><summary>sonnet: baseline answer</summary>

## Nested Routes with `@lit-labs/router`

The short answer is **no** — you should not create multiple `new Router()` instances. Here's why and what to do instead.

---

## The Problem with Multiple Routers

```javascript
// ❌ Wrong — multiple Router instances fight over popstate/click events
class AppShell extends LitElement {
  router = new Router(this, [...]);
}

class UsersSection extends LitElement {
  router = new Router(this, [...]);  // conflicts with parent router
}

class ProductsSection extends LitElement {
  router = new Router(this, [...]);  // conflicts with parent router
}
```

Multiple routers will:
- Each intercept **all** link clicks and `popstate` events
- Race to handle the same URL changes
- Produce unpredictable rendering behavior

---

## The Right Pattern: One Router, Nested Route Definitions

### 1. Top-Level Router (Entry Point)

```javascript
// app-shell.js
import { Router } from '@lit-labs/router';
import { LitElement, html } from 'lit';

class AppShell extends LitElement {
  router = new Router(this, [
    {
      path: '/',
      render: () => html`<home-page></home-page>`,
    },
    {
      // Wildcard captures all /users/* routes
      path: '/users/*',
      render: ({ rest }) => html`
        <users-section .subroute=${rest}></users-section>
      `,
    },
    {
      // Wildcard captures all /products/* routes
      path: '/products/*',
      render: ({ rest }) => html`
        <products-section .subroute=${rest}></products-section>
      `,
    },
    {
      path: '/*',
      render: () => html`<not-found-page></not-found-page>`,
    },
  ]);

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/users">Users</a>
        <a href="/products">Products</a>
      </nav>
      <main>${this.router.outlet()}</main>
    `;
  }
}
customElements.define('app-shell', AppShell);
```

---

### 2. Child Section — Handles Its Own Sub-Routes via Property

```javascript
// users-section.js
import { LitElement, html } from 'lit';
import { property } from 'lit/decorators.js';

class UsersSection extends LitElement {
  // Receives the remaining path from the parent router
  @property({ type: String })
  subroute = '';

  // Derive the view from the subroute prop — no Router needed
  get currentView() {
    const path = this.subroute ?? '';

    if (path === '' || path === '/') {
      return html`<users-list></users-list>`;
    }

    // Match /users/:id
    const idMatch = path.match(/^\/(\w+)$/);
    if (idMatch) {
      return html`<user-detail .userId=${idMatch[1]}></user-detail>`;
    }

    // Match /users/:id/edit
    const editMatch = path.match(/^\/(\w+)\/edit$/);
    if (editMatch) {
      return html`<user-edit .userId=${editMatch[1]}></user-edit>`;
    }

    return html`<not-found-page></not-found-page>`;
  }

  render() {
    return html`
      <aside>Users Sidebar</aside>
      <section>${this.currentView}</section>
    `;
  }
}
customElements.define('users-section', UsersSection);
```

---

### 3. Alternative: Flatten All Routes at the Top Level

For simpler apps, just define everything in one place:

```javascript
// ✅ Simple and explicit — no nesting needed
router = new Router(this, [
  { path: '/',                  render: () => html`<home-page></home-page>` },
  { path: '/users',             render: () => html`<users-list></users-list>` },
  { path: '/users/:id',         render: ({id}) => html`<user-detail .userId=${id}></user-detail>` },
  { path: '/users/:id/edit',    render: ({id}) => html`<user-edit .userId=${id}></user-edit>` },
  { path: '/products',          render: () => html`<products-list></products-list>` },
  { path: '/products/:id',      render: ({id}) => html`<product-detail .productId=${id}></product-detail>` },
]);
```

---

## Decision Guide

| Situation | Pattern |
|---|---|
| Simple app, few routes | Flat routes in one Router |
| Sections with shared layout/sidebar | Wildcard + `rest` prop to child |
| Section routing is complex | Child component does its own `path.match()` |
| Truly independent micro-frontends | Separate Router **only** if they're in separate shadow DOM trees with no shared navigation |

---

## Key Takeaway

```
One Router → owns URL changes
Child components → receive path remainder as a prop
                → render sub-views with plain conditional logic
```

The `rest` parameter from a wildcard route (`/users/*`) is the escape hatch that lets child components handle their own sub-routing without needing their own `Router` instance.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

No — each section should create a `new Routes(...)`, not a `new Router(...)`. One `Router` per page; `Routes` for every nested section.

## Why it matters

`Router` installs **global** `click` and `popstate` listeners on `window`. A second `Router` means every click is handled twice and every `popstate` fires twice — they'll clobber each other. `Routes` is the same matching/rendering logic without those global side-effects; it wires itself to the nearest ancestor router automatically.

## The right pattern

```
MyApp          ← new Router(this, [...])   (one, at the top)
├── UsersSection   ← new Routes(this, [...])
└── ProductsSection ← new Routes(this, [...])
```

### Top-level app

```ts
@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    { path: '/',          render: () => html`<home-page></home-page>` },
    { path: '/users/*',   render: () => html`<users-section></users-section>` },
    { path: '/products/*',render: () => html`<products-section></products-section>` },
  ], { fallback: { render: () => html`<not-found></not-found>` } });

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/users/">Users</a>
        <a href="/products/">Products</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

### Each nested section uses `Routes`

```ts
@customElement('users-section')
class UsersSection extends LitElement {
  // Routes, not Router
  private _routes = new Routes(this, [
    { path: '',    render: ()     => html`<user-list></user-list>` },
    { path: ':id', render: ({id}) => html`<user-detail .id=${id}></user-detail>` },
  ]);

  render() { return html`${this._routes.outlet()}`; }
}

@customElement('products-section')
class ProductsSection extends LitElement {
  private _routes = new Routes(this, [
    { path: '',    render: ()     => html`<product-list></product-list>` },
    { path: ':id', render: ({id}) => html`<product-detail .id=${id}></product-detail>` },
  ]);

  render() { return html`${this._routes.outlet()}`; }
}
```

## How the wiring works

When a `Routes` controller is created, it dispatches a bubbling `lit-routes-connected` event up the DOM. The nearest ancestor `Router` (or `Routes`) catches it and registers the child as a sub-router. After that, the parent passes its **tail group** — the `*` portion of `/users/*` — down to the child for matching. So:

| URL | Parent matches | Tail passed to child | Child matches |
|-----|---------------|----------------------|---------------|
| `/users/` | `/users/*` | `` (empty) | `''` → user list |
| `/users/42` | `/users/*` | `42` | `:id` → user detail |
| `/products/99` | `/products/*` | `99` | `:id` → product detail |

## Key rules to remember

- **Trailing slash on nav links** — link to `/users/`, not `/users`. The pattern `/users/*` matches `/users/` and `/users/foo` but **not** `/users` (no trailing slash, no wildcard tail).
- **Child paths have no leading slash and no parent prefix** — write `':id'`, not `'/users/:id'`.
- **`path: ''`** is the index route for a section (matches when the tail is empty).
- **`goto()` alone doesn't update the URL bar** — for programmatic navigation always pair it: `history.pushState({}, '', path); this._router.goto(path);`.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B directly addresses all three rubric criteria: it explicitly states only one Router per page, recommends Routes for nested sections, and explains that Router installs global click and popstate listeners as the reason multiples conflict. Answer A mentions avoiding multiple routers but never mentions the Routes controller or the global listener mechanism, which are the core of the correct answer.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies one Router per page | skill |
| recommends Routes for nesting | skill |
| mentions global click / popstate listener as the reason | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✓ | `Single Router` |
| recommends Routes for nesting | ✓ | `routes` |
| mentions global click / popstate listener as the reason | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✓ | `One Router` |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global listener` |

<details><summary>haiku: baseline answer</summary>

# Router Pattern for Nested Route Sections

**No, you should not create separate `Router` instances for each section.** Instead, use a **single root Router** with nested route definitions.

## Recommended Pattern

```typescript
import { Router } from '@lit-labs/router';

const router = new Router(document.body, [
  { path: '/users/:id', component: 'user-detail' },
  { path: '/users', component: 'user-list' },
  { path: '/products/:id', component: 'product-detail' },
  { path: '/products', component: 'product-list' },
  { path: '/', component: 'home' },
]);
```

## If You Need Nested Routing Structure

If you want logical separation, use **nested route objects** (if supported by your version):

```typescript
const router = new Router(document.body, [
  {
    path: '/users',
    component: 'users-layout',
    children: [
      { path: '/:id', component: 'user-detail' },
      { path: '/', component: 'user-list' },
    ],
  },
  {
    path: '/products',
    component: 'products-layout',
    children: [
      { path: '/:id', component: 'product-detail' },
      { path: '/', component: 'product-list' },
    ],
  },
]);
```

## Why Single Router?

- ✅ **Centralized navigation** — one source of truth
- ✅ **Simpler state management** — avoid router conflicts
- ✅ **Cleaner history handling** — single history stack
- ❌ Multiple routers can cause navigation conflicts and duplicate listeners

**Check your `@lit-labs/router` version** — nested route support varies. If unsure, flat routes with prefixes is the safest approach.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Nested Route Sections: Use `Routes`, Not Multiple `Router`s

**No — do NOT create multiple `Router` instances.** There should be exactly **one `Router`** at the top level of your app. Each nested section should use `new Routes(...)` instead.

## Why One Router, Many Routes

- **`Router` installs global listeners** on `window` for `click` and `popstate`. Multiple routers would double-handle clicks and clobber each other on back/forward.
- **`Routes` is the nested controller** — it auto-wires to the nearest ancestor `Router` (or `Routes`) via a bubbling `lit-routes-connected` event and inherits the matched tail group from its parent.

## The Right Pattern

```ts
import {LitElement, html} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Router, Routes} from '@lit-labs/router';

// Top level: one Router
@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/',           render: () => html`<home-page></home-page>`},
    {path: '/users/*',    render: () => html`<users-section></users-section>`},
    {path: '/products/*', render: () => html`<products-section></products-section>`},
  ], {fallback: {render: () => html`<not-found></not-found>`}});

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/users/">Users</a>
        <a href="/products/">Products</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}

// Nested section 1: Routes, not Router
@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',    render: () => html`<user-list></user-list>`},
    {path: ':id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() {
    return html`
      <section>
        <h2>Users</h2>
        ${this._routes.outlet()}
      </section>
    `;
  }
}

// Nested section 2: Routes, not Router
@customElement('products-section')
class ProductsSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',    render: () => html`<product-list></product-list>`},
    {path: ':id', render: ({id}) => html`<product-detail .id=${id}></product-detail>`},
  ]);

  render() {
    return html`
      <section>
        <h2>Products</h2>
        ${this._routes.outlet()}
      </section>
    `;
  }
}
```

## How It Works

1. **Parent `Router` matches `/users/*`** → renders `<users-section>`.
2. **`UsersSection` mounts** and creates `new Routes(this, [...])`.
3. **`Routes` fires `lit-routes-connected`** (bubbles up to the `Router`).
4. **`Router` receives the event** and propagates the **tail group** (the `*` part) to the child `Routes`.
5. **Child `Routes` matches against the tail** — e.g., `/users/123` → tail is `123` → matches `path: ':id'` → renders `<user-detail .id="123">`.

The same wiring happens for `/products/*` and its nested `Routes`.

## Key Points

| Aspect | Details |
|--------|---------|
| **Paths in child `Routes`** | No leading slash, no parent prefix. Use `path: ''` for index, `path: ':id'` for params. |
| **Links** | Always include the trailing slash: `<a href="/users/">` not `<a href="/users">`. |
| **Parent route pattern** | Must end in `/*` to enable nesting: `/users/*`, `/products/*`. |
| **`Routes` vs `Router`** | `Routes` = nested; `Router` = top-level only. One per app. |

See [nested-routing.md](references/nested-routing.md) for the full wiring mechanism and [pitfalls.md](references/pitfalls.md) for the trailing-slash gotcha.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies that only one Router should be created per page and that Routes (not Router) should be used for nested sections, explaining that Router installs global click and popstate listeners which would conflict if duplicated. Answer B is factually wrong on the core question — it recommends creating multiple Router instances per section, which is exactly the anti-pattern the question asks about, and incorrectly claims they 'cooperate' when in reality they conflict.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| identifies one Router per page | skill |
| recommends Routes for nesting | skill |
| mentions global click / popstate listener as the reason | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✗ | |
| recommends Routes for nesting | ✓ | `routes` |
| mentions global click / popstate listener as the reason | ✓ | `popstate` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✗ | |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global* listener` |

<details><summary>opus: baseline answer</summary>

# Nested Routers in `@lit-labs/router`

Yes — creating a separate `Router` per section is exactly the intended pattern. `@lit-labs/router` is designed around **per-component routers** that compose hierarchically, not a single global route table.

## The pattern

Each component that owns a route section instantiates its own `Router` as a reactive controller, and uses a wildcard (`/*`) in the parent to delegate the rest of the path to a child component that has its own router.

### Parent (app shell)

```js
import {LitElement, html} from 'lit';
import {Router} from '@lit-labs/router';

class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/',           render: () => html`<h1>Home</h1>`},
    {path: '/users/*',    render: () => html`<users-page></users-page>`},
    {path: '/products/*', render: () => html`<products-page></products-page>`},
  ]);

  render() {
    return this._router.outlet();
  }
}
customElements.define('my-app', MyApp);
```

The trailing `/*` is important — it tells the parent router "match this prefix and let a child handle the rest."

### Child router (e.g. users section)

```js
class UsersPage extends LitElement {
  private _router = new Router(this, [
    {path: '/',         render: () => html`<users-list></users-list>`},
    {path: '/:id',      render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
    {path: '/:id/edit', render: ({id}) => html`<user-edit .id=${id}></user-edit>`},
  ]);

  render() {
    return this._router.outlet();
  }
}
customElements.define('users-page', UsersPage);
```

The child router automatically sees paths *relative to its mount point*, so `/users/42` matches `/:id` here.

## Why this pattern is good

1. **Encapsulation** — each section owns its own routes; the shell doesn't need to know about `/users/:id/edit`.
2. **Code-splitting friendly** — you can dynamically import `users-page` only when `/users/*` matches.
3. **Local fallbacks** — each child router can define its own `fallback` for unknown sub-paths.
4. **Reactive controllers** — routers tie into the host's lifecycle automatically; no manual subscribe/unsubscribe.

## Things to watch out for

- **Don't forget the `/*`** on the parent route, or the child router will receive an empty path and nothing will match.
- **Link generation**: `router.link(...)` returns paths relative to that router. If you need an absolute URL across sections, build it from the root or use plain `href` attributes.
- **Navigation** via `router.goto(path)` on a child router is also relative to that child. To navigate cross-section, call `goto` on the root router (or just set `window.location`).
- Each router installs a `click` / `popstate` listener on the host, but they cooperate — clicks bubble until a router claims them.

So: one `Router` per route-owning component, parents delegate via `/*`, children define routes relative to their mount point. That's idiomatic `@lit-labs/router`.

</details>

<details><summary>opus: skill-loaded answer</summary>

## Short answer

**No.** Use exactly **one `Router`** at the top of your app, and use **`Routes`** (not `Router`) inside each nested section like `/users/...` and `/products/...`.

## Why

`Router` installs *global* listeners on `window` — a `click` interceptor for `<a href>` and a `popstate` handler for back/forward. If you create a second `Router` inside a child section, you get:

- Duplicate click handling (both routers try to intercept the same `<a>` click).
- Both routers responding to `popstate`, fighting over what to render.
- Each `Router` independently reading `location.pathname`, with no awareness of the parent's matched prefix.

`Routes` is the controller designed for nested sections. It auto-wires itself to the nearest ancestor `Routes`/`Router` via a bubbling `lit-routes-connected` DOM event, and its child paths are matched against the *tail* of the parent's match — so you write child paths relative to the mount point, not the full URL.

## The pattern

**Top-level app** — one `Router`, with parent routes ending in `/*` to delegate to children:

```ts
import {Router} from '@lit-labs/router';

@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/',           render: () => html`<home-page></home-page>`},
    {path: '/users/*',    render: () => html`<users-section></users-section>`},
    {path: '/products/*', render: () => html`<products-section></products-section>`},
  ], {fallback: {render: () => html`<not-found></not-found>`}});

  render() {
    return html`
      <nav>
        <a href="/">Home</a>
        <a href="/users/">Users</a>
        <a href="/products/">Products</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

**Each nested section** — `Routes`, with paths relative to the parent mount (no leading slash, no `/users` prefix):

```ts
import {Routes} from '@lit-labs/router';

@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',     render: () => html`<user-list></user-list>`},
    {path: ':id',  render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() { return html`${this._routes.outlet()}`; }
}

@customElement('products-section')
class ProductsSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',          render: () => html`<product-list></product-list>`},
    {path: ':id',       render: ({id}) => html`<product-detail .id=${id}></product-detail>`},
    {path: ':id/edit',  render: ({id}) => html`<product-edit .id=${id}></product-edit>`},
  ]);

  render() { return html`${this._routes.outlet()}`; }
}
```

## Two things that will bite you

1. **Trailing slash on the nav links.** `path: '/users/*'` matches `/users/` and `/users/foo` but **not** bare `/users`. Always link as `<a href="/users/">`, not `<a href="/users">`.

2. **Building hrefs inside a section.** Inside `users-section`, use `this._routes.link('123')` instead of hand-building `/users/123` — it prepends the parent's matched pathname for you, so the section stays relocatable.

## Summary

| Where | Use | Path style |
|---|---|---|
| Top-level app component | `new Router(this, [...])` | Full paths, parent routes end in `/*` |
| `users-section`, `products-section`, etc. | `new Routes(this, [...])` | Relative: `''`, `':id'`, `':id/edit'` |

One `Router`, many `Routes`. ⚠️ Note that `@lit-labs/router` is a Lit Labs package (currently 0.1.4, pre-1.0) — APIs may still change.

</details>

---

### `link-helper`

**Prompt**

```
Inside a nested @lit-labs/router section mounted at `/users/`,
I want to render a link to a child route at `detail`. If I write
`<a href="detail">`, it won't work. What's the right way?
```

**Judge focus:** The better answer reaches for the link() helper on the Routes
controller, which resolves relative to the parent route prefix.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly focuses on the `Routes` controller's `link()` helper (not the top-level `Router`), which is the idiomatic solution for nested route sections mounted at a prefix. It accurately explains that `link()` prepends the parent's matched pathname prefix, which is exactly the relative resolution mechanism the question asks about. Answer B mentions `link()` but applies it to a flat `Router` instance with absolute paths, missing the key point about nested `Routes` controllers resolving relative to their parent prefix.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends link() helper | skill |
| explains relative resolution | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `relative` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `Relative` |

<details><summary>sonnet: baseline answer</summary>

## The Problem

In `@lit-labs/router`, routes are matched against the **full pathname**, and a plain relative href like `detail` will resolve relative to the **current document URL** in the browser — which may not behave as you expect inside a nested router context. The router doesn't automatically prepend the parent prefix.

---

## The Right Way

### 1. Use an absolute path (simplest & most reliable)

```html
<a href="/users/detail">Detail</a>
```

This always works because it's unambiguous.

---

### 2. Use the router's `link()` helper (idiomatic Lit Router approach)

`@lit-labs/router` exposes a `link()` utility that resolves a path **relative to the router's base**, so you don't have to hardcode the prefix everywhere.

```ts
import { Router } from '@lit-labs/router';

class MyElement extends LitElement {
  private router = new Router(this, [
    { path: '/users/',       render: () => html`<user-list></user-list>` },
    { path: '/users/detail', render: () => html`<user-detail></user-detail>` },
  ]);

  render() {
    return this.router.outlet();
  }
}
```

Inside a child component that has access to the router instance, use:

```ts
html`<a href=${this.router.link('/users/detail')}>Detail</a>`
```

`router.link()` returns a properly resolved pathname string.

---

### 3. Nested router — pass the prefix down via context

If you have a **nested** `Router` mounted at `/users/`, pass the prefix via [Lit Context](https://lit.dev/docs/data/context/) or a property so child components can build links without hardcoding:

```ts
// parent
const BASE = '/users/';

html`<a href="${BASE}detail">Detail</a>`
```

Or more robustly:

```ts
// In the component that owns the nested router
get base() { return '/users/'; }

render() {
  return html`
    <a href="${this.base}detail">Go to Detail</a>
    ${this.router.outlet()}
  `;
}
```

---

## Why `href="detail"` Fails

| Href style | Resolves to | Works? |
|---|---|---|
| `detail` | relative to browser URL (unpredictable) | ❌ |
| `./detail` | same as above | ❌ |
| `/users/detail` | absolute path | ✅ |
| `router.link('/users/detail')` | router-resolved | ✅ |

---

## Summary

**Use absolute paths** (`/users/detail`) or **`router.link('/users/detail')`** — never bare relative hrefs inside a Lit router, because the router intercepts navigation based on full pathnames and relative hrefs resolve against the browser's location, not the router's logical base.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Use `this._routes.link('detail')` to build the href

Relative `<a href="detail">` is a plain HTML relative URL — the browser resolves it against the current document URL, not the router's matched prefix. Inside a nested `Routes` controller you need to ask the controller to prepend the parent's matched pathname for you.

```ts
import {LitElement, html} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Routes} from '@lit-labs/router';

@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',       render: () => html`<user-list></user-list>`},
    {path: 'detail', render: () => html`<user-detail></user-detail>`},
  ]);

  render() {
    return html`
      <!-- ✅ resolves to /users/detail -->
      <a href=${this._routes.link('detail')}>Go to detail</a>

      <!-- ❌ browser resolves relative to the document, not the route prefix -->
      <a href="detail">Broken</a>

      ${this._routes.outlet()}
    `;
  }
}
```

### What `link()` does

`link('detail')` prepends the pathname that the parent `Router` matched for this `Routes` instance. If the parent mounted this component at `/users/*`, the tail group is everything after `/users/`, so `link('detail')` returns `/users/detail`.

### The trailing-slash rule still applies

The parent route **must** be mounted with a trailing slash in the link you use to reach it:

```ts
// In the root Router:
{path: '/users/*', render: () => html`<users-section></users-section>`}

// Nav link — note the trailing slash:
html`<a href="/users/">Users</a>`   // ✅ matches /users/*
html`<a href="/users">Users</a>`    // ❌ does NOT match /users/*
```

Without the trailing slash the parent route never matches, so `Routes` never mounts and `link()` has no prefix to prepend.

### Passing a param

If the child path includes a segment, just include it in the string you pass:

```ts
// path: ':id'  →  /users/42
html`<a href=${this._routes.link('42')}>User 42</a>`
```

`link()` only does string concatenation — it does not accept a named-params object — so build the segment yourself before passing it in.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly recommends the `Routes.link()` helper, which is the idiomatic solution in `@lit-labs/router` for resolving paths relative to a parent route prefix. Answer A only suggests hardcoding absolute paths or using `router.goto()`, missing the key `link()` API entirely. Answer B also clearly explains how `link()` resolves relative to the parent's matched pathname, satisfying both rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends link() helper | skill |
| explains relative resolution | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✗ | |
| explains relative resolution | ✓ | `relative` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `Relative` |

<details><summary>haiku: baseline answer</summary>

# Using Absolute Paths in Nested Routes

When you're inside a nested router section mounted at `/users/`, you need to use an **absolute path** from the root, not a relative path.

Instead of:
```html
<a href="detail">Link</a>
```

Use:
```html
<a href="/users/detail">Link</a>
```

## Why Relative Paths Don't Work

The `@lit-labs/router` doesn't resolve relative paths the way you might expect from a file system. The `href` attribute is interpreted by the browser as a regular URL, so `detail` would try to navigate to the current page's URL + `detail`, not relative to your router's mount point.

## Alternative: Using Router Methods

If you want to avoid hardcoding paths, you can use the router's navigation methods programmatically:

```javascript
import { Router } from '@lit-labs/router';

// In your component
this.router.goto('/users/detail');
```

Or if you have access to the router instance, you could create a helper that constructs paths relative to the current route context.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Building Parent-Relative Links in Nested Routes

When you're inside a nested `Routes` section, you **cannot** use relative `href` attributes like `<a href="detail">` — the browser will resolve them relative to the current document's base URL, not your route prefix.

## The Solution: Use `Routes.link()`

Call `this._routes.link('local-path')` to build an absolute href that includes the parent route's matched pathname:

```ts
@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',     render: () => html`<user-list></user-list>`},
    {path: ':id',  render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() {
    return html`
      ${this._routes.outlet()}
      <!-- ❌ Wrong: resolves to /detail, not /users/detail -->
      <!-- <a href="detail">User Detail</a> -->
      
      <!-- ✅ Right: link() prepends the parent's matched pathname -->
      <a href="${this._routes.link('detail')}">User Detail</a>
    `;
  }
}
```

## How `link()` Works

`link(path)` returns an absolute pathname by prepending the parent `Router`'s matched pathname to your local path:

- Parent route: `/users/*` matches `/users/123`
- Child calls: `this._routes.link('detail')` → `/users/detail`
- Child calls: `this._routes.link(':id')` → `/users/:id` (literal string, not interpolated)

## Full Example

```ts
@customElement('user-list')
class UserList extends LitElement {
  render() {
    return html`
      <ul>
        <li><a href="/users/1">User 1</a></li>
        <li><a href="/users/2">User 2</a></li>
      </ul>
    `;
  }
}

@customElement('user-detail')
class UserDetail extends LitElement {
  @property() id?: string;
  
  private _routes = new Routes(this, [
    {path: '', render: () => html`<user-list></user-list>`},
    {path: ':id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() {
    return html`
      <h2>User ${this.id}</h2>
      <!-- Link back to the list using link() -->
      <a href="${this._routes.link('')}">Back to list</a>
    `;
  }
}
```

## Key Points

- **`link()` is only on `Routes`**, not `Router` (the root router doesn't need it — use absolute paths).
- **Always use `link()` for child-to-child navigation** within a nested section.
- **For parent-level links, use absolute paths** (e.g. `<a href="/users/">`).
- **`link()` does NOT interpolate route params** — pass the literal string you want appended.

See [references/navigation.md](references/navigation.md) for the full `link()` algorithm and more examples.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend the link() helper and explain relative resolution. Answer A is slightly more precise and useful: it correctly notes that link() prepends the parent's matched pathname, warns against paths starting with '.', advises against hardcoding the parent mount point, and provides accurate programmatic navigation guidance. Answer B's explanation of why bare relative links fail is somewhat muddled (the browser behavior description is inconsistent), and its programmatic navigation example using goto() alone on the nested Routes instance is less accurate than A's guidance.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends link() helper | tie |
| explains relative resolution | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `Relative` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends link() helper | ✓ | `.link(` |
| explains relative resolution | ✓ | `relative` |

<details><summary>opus: baseline answer</summary>

# The Issue with Relative Links in Nested Routers

When you're inside a nested router mounted at `/users/`, writing `<a href="detail">` doesn't work the way you'd expect because the browser resolves relative URLs against the **current page URL**, not against the router's mount point.

For example, if the user is currently at `/users/list`, then `<a href="detail">` will resolve to `/users/detail` — which might be fine. But if they're at `/users/`, it resolves to `/users/detail` too, and if they're at `/users/list/something`, it breaks entirely.

## The Right Way: Use `router.link()`

`@lit-labs/router` gives each `Routes`/`Router` instance a `link()` method specifically for this. It resolves a path *relative to where that router is mounted*, producing an absolute URL that's stable regardless of the current location.

```js
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { Routes } from '@lit-labs/router';

@customElement('users-view')
export class UsersView extends LitElement {
  // This Routes instance is mounted at /users/ by the parent router
  private _routes = new Routes(this, [
    { path: 'detail', render: () => html`<user-detail></user-detail>` },
    { path: 'list',   render: () => html`<user-list></user-list>` },
  ]);

  render() {
    return html`
      <nav>
        <a href=${this._routes.link('detail')}>Detail</a>
        <a href=${this._routes.link('list')}>List</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}
```

## Why this works

- `this._routes.link('detail')` walks up through any parent `Routes` instances and prepends their mount paths.
- The resulting `href` is a fully qualified path like `/users/detail`, so it's correct no matter what the current URL is.
- You can still pass it to a normal `<a href>` — combined with a click handler (or the router's built-in navigation handling) it will perform client-side navigation.

## Bonus: navigating programmatically

For programmatic navigation use `goto()` on the *root* router, with the absolute URL you got from `link()`:

```js
this._routes.goto(this._routes.link('detail'));
```

So the rule of thumb: **never write bare relative paths in `href` inside a nested router — always pipe them through `routes.link()`.**

</details>

<details><summary>opus: skill-loaded answer</summary>

Use the `Routes` controller's `link()` method to build the href. It prepends the parent's matched pathname (the part of the URL the parent router consumed before delegating to this nested `Routes`), so a relative child path resolves to a correct absolute URL that the click interceptor will handle.

```ts
@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '',       render: () => html`<user-list></user-list>`},
    {path: 'detail', render: () => html`<user-detail></user-detail>`},
  ]);

  render() {
    return html`
      <a href=${this._routes.link('detail')}>Detail</a>
      ${this._routes.outlet()}
    `;
  }
}
```

Mounted at `/users/`, `this._routes.link('detail')` returns `/users/detail`, which the `Router`'s global click handler will intercept and SPA-navigate (no full page reload).

Two caveats worth knowing:

- **Pass a plain child-relative path** like `'detail'` or `'123/edit'` — not `'./detail'`. The `link()` implementation throws "Not implemented" on paths starting with `.`.
- **Don't hand-write `<a href="/users/detail">`.** It works, but it hardcodes the parent mount point; if you ever remount `UsersSection` under a different prefix, every link breaks. `link()` keeps the child decoupled from where the parent mounts it.

For programmatic navigation from the same component, remember `goto()` alone won't update the URL bar — pair it with `history.pushState`:

```ts
const href = this._routes.link('detail');
history.pushState({}, '', href);
this._routes.goto(href);
```

</details>

---

### `simplest-hash-routing`

**Prompt**

```
I want hash routing (URLs like /#/users/123 instead of
/users/123) using @lit-labs/router. What's the simplest way to
set this up?
```

**Judge focus:** The trap: invent a hash-routing setup. @lit-labs/router does NOT
support hash routing — the router inspects pathname, not hash.
The correct answer is to say so and offer alternatives (use a
different router, or pre-process URLs to map hash -> pathname).

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **skill** — Answer B correctly states that hash routing is not supported by @lit-labs/router and explains why (the router matches against pathname, not hash), then offers legitimate alternatives. Answer A invents a fake hash-routing API with fabricated constructor options like `urlPattern` and subclass overrides that don't exist in the library, directly violating both rubric criteria by failing to clearly state the limitation and by inventing a non-existent API.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states hash routing is not supported | skill |
| avoids inventing a hash-routing API | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states hash routing is not supported | ✗ | |
| avoids inventing a hash-routing API | ✗ | `HashRouter` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states hash routing is not supported | ✓ | `not support` |
| avoids inventing a hash-routing API | ✗ | `hashRouting` |

<details><summary>sonnet: baseline answer</summary>

## Hash Routing with @lit-labs/router

`@lit-labs/router` doesn't have built-in hash routing support, but you can implement it cleanly by creating a custom history adapter.

### Setup

```bash
npm install @lit-labs/router
```

### Custom Hash Router Implementation

```javascript
// hash-router.js
import { Router } from '@lit-labs/router';

/**
 * Patches the router to use hash-based URLs
 * Converts /#/path → /path for route matching
 */
export function createHashRouter(host, routes) {
  // Normalize hash URL to pathname for the router
  const getPathFromHash = () => {
    const hash = window.location.hash;
    return hash ? hash.slice(1) || '/' : '/';
  };

  // Override history methods to use hash
  const originalPushState = history.pushState.bind(history);
  const originalReplaceState = history.replaceState.bind(history);

  history.pushState = (state, title, url) => {
    if (url && !url.startsWith('http')) {
      window.location.hash = url;
    } else {
      originalPushState(state, title, url);
    }
  };

  history.replaceState = (state, title, url) => {
    if (url && !url.startsWith('http')) {
      window.location.hash = url;
    } else {
      originalReplaceState(state, title, url);
    }
  };

  // Sync hash changes → popstate (router listens to popstate)
  window.addEventListener('hashchange', () => {
    const path = getPathFromHash();
    window.dispatchEvent(new PopStateEvent('popstate', { state: null }));
  });

  // Set initial hash if missing
  if (!window.location.hash) {
    window.location.hash = '/';
  }

  // Temporarily rewrite location.pathname for router initialization
  const router = new Router(host, routes, {
    // Provide custom URL for route matching
    urlPattern: {
      pathname: getPathFromHash(),
    },
  });

  return router;
}
```

### Simpler, More Reliable Approach

A cleaner solution — subclass and override the URL the router sees:

```javascript
// hash-router.js
import { Router } from '@lit-labs/router';

export class HashRouter extends Router {
  // Override the URL used for route matching
  get currentRoute() {
    return this._getHashPath();
  }

  _getHashPath() {
    const hash = window.location.hash;
    return hash.replace(/^#/, '') || '/';
  }

  async goto(path) {
    window.location.hash = path;
  }
}
```

### Recommended Practical Approach

The most reliable method — intercept at the component level:

```javascript
// my-app.js
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';

class MyApp extends LitElement {
  constructor() {
    super();
    this._setupHashRouting();
    this._router = this._createRouter();
  }

  _setupHashRouting() {
    // Convert hashchange → popstate so the router reacts
    window.addEventListener('hashchange', () => {
      const path = window.location.hash.slice(1) || '/';

      // Fake the URL the router will read
      history.replaceState(
        null,
        '',
        path  // temporarily set real path
      );

      window.dispatchEvent(new PopStateEvent('popstate'));
    });

    // On load, redirect hash path into real path for router init
    const initialPath = window.location.hash.slice(1) || '/';
    history.replaceState(null, '', initialPath);
  }

  _createRouter() {
    return new Router(this, [
      {
        path: '/',
        render: () => html`<home-page></home-page>`,
      },
      {
        path: '/users/:id',
        render: ({ id }) => html`<user-page .userId=${id}></user-page>`,
      },
      {
        path: '/about',
        render: () => html`<about-page></about-page>`,
      },
    ]);
  }

  // Navigation helper — always use hash links
  navigate(path) {
    window.location.hash = path;
  }

  render() {
    return html`
      <nav>
        <a href="#/">Home</a>
        <a href="#/users/123">User 123</a>
        <a href="#/about">About</a>
      </nav>

      <main>${this._router.outlet()}</main>
    `;
  }
}

customElements.define('my-app', MyApp);
```

### How It Works

```
User clicks  ──→  hashchange fires  ──→  path extracted from hash
  #/users/123         │                      /users/123
                      ↓
              history.replaceState()    ←── router reads window.location
              sets real path            ←── matches route
                      │
              popstate dispatched  ──→  router.goto() called internally
```

### Key Points

| Concern | Solution |
|---|---|
| Link format | Use `href="#/path"` in all anchors |
| Programmatic nav | `window.location.hash = '/path'` |
| Route patterns | Define normally (`/users/:id`) |
| Browser back/forward | Works automatically via `hashchange` |
| Page refresh | Works — hash is client-side only |
| No server config needed | ✅ Hash never sent to server |

The core trick is **syncing `hashchange` → `popstate`** and keeping `history.replaceState` updated so the router always sees a clean pathname to match against.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Hash routing is not supported by `@lit-labs/router`

This is a hard limitation, not a configuration gap. The router compiles every `path` string into a `URLPattern` that matches against `location.pathname` only. The fragment (`#/users/123`) is never part of `pathname` — it lives in `location.hash` — so the router never sees it, regardless of how you configure your routes.

There is no `hashRouting: true` option, no hash-aware `URLPattern` mode, and no workaround within the library itself.

---

## Your real options

### Option 1 — Use History API routing (recommended)

This is what `@lit-labs/router` is designed for. URLs look like `/users/123` instead of `/#/users/123`.

The one server-side requirement: configure your dev server (and production server) to serve `index.html` for all unknown paths so that a hard refresh on `/users/123` doesn't 404.

**Vite** (`vite.config.ts`):
```ts
export default {
  server: { historyApiFallback: true },
};
```

**webpack-dev-server** (`webpack.config.js`):
```js
devServer: { historyApiFallback: true }
```

**Nginx** (`nginx.conf`):
```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```

Then use `@lit-labs/router` normally — no changes to your route definitions.

---

### Option 2 — Use a router that actually supports hash routing

If hash-based URLs are a firm requirement (e.g. a static file host with no server-side rewrite support), use a different router:

| Router | Hash routing |
|--------|-------------|
| [`@vaadin/router`](https://github.com/vaadin/router) | ✅ built-in |
| [`universal-router`](https://github.com/kriasoft/universal-router) | ✅ bring your own history |
| [`navigo`](https://github.com/krasimir/navigo) | ✅ built-in |

These all work fine with Lit web components — you call their APIs from a `LitElement` just as you would any other JS.

---

## Bottom line

| Goal | Answer |
|------|--------|
| Hash routing with `@lit-labs/router` | ❌ Not possible |
| History API routing with `@lit-labs/router` | ✅ Fully supported — configure server SPA fallback |
| Hash routing with a different router + Lit | ✅ Use `@vaadin/router` or similar |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly states that hash routing is not supported by @lit-labs/router and explains why, while Answer A invents a fictional `hashLocation()` API that does not exist in the library. Answer B provides accurate information and useful alternatives, while Answer A would mislead developers into trying a non-existent feature.

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
| states hash routing is not supported | ✓ | `not support` |
| avoids inventing a hash-routing API | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Hash Routing with @lit-labs/router

The simplest way is to use the `hashLocation()` function instead of the default `pathLocation()`:

```typescript
import { Router } from '@lit-labs/router';
import { hashLocation } from '@lit-labs/router';

const router = new Router(this, [
  { path: '/users/:id', render: () => html`<user-detail></user-detail>` },
  { path: '/about', render: () => html`<about-page></about-page>` }
], {
  location: hashLocation()
});
```

## Complete Example

```typescript
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';
import { hashLocation } from '@lit-labs/router';

class MyApp extends LitElement {
  private router = new Router(this, [
    { path: '/users/:id', render: () => html`<user-detail></user-detail>` },
    { path: '/about', render: () => html`<about-page></about-page>` },
    { path: '/', render: () => html`<home-page></home-page>` }
  ], {
    location: hashLocation()
  });

  render() {
    return html`
      <nav>
        <a href="/#/">Home</a>
        <a href="/#/users/123">User 123</a>
        <a href="/#/about">About</a>
      </nav>
      ${this.router.outlet()}
    `;
  }
}
```

Now your URLs will be:
- `/#/` (home)
- `/#/users/123` (user detail)
- `/#/about` (about page)

That's it! The `hashLocation()` function handles all the hash-based routing logic for you.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Hash Routing with @lit-labs/router

**Hash routing is not supported by `@lit-labs/router`.** The router inspects only `pathname` via `URLPattern` matching, not the hash fragment. There is no built-in option to enable it.

## Why It's Not Supported

`@lit-labs/router` uses the standard `URLPattern` API, which matches against:
- `pathname` (e.g. `/users/123`)
- `hostname`, `protocol`, `port`, `search`, etc.

It does **not** match the hash (`#/users/123`). The router's click interception and `goto()` method both work with the History API (`pushState`/`replaceState`), not hash-based navigation.

## Your Options

### Option 1: Use the History API (Recommended)

Switch to pathname-based routing — it's the modern standard and what `@lit-labs/router` is designed for:

```ts
// Instead of /#/users/123
// Use /users/123

const router = new Router(this, [
  {path: '/users/:id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
]);
```

**Pros:**
- Native support in `@lit-labs/router`
- Cleaner URLs
- Better SEO
- Works with server-side rendering

**Cons:**
- Requires SPA fallback on your server (serve `index.html` for unknown paths)

### Option 2: Use a Different Router

If you need hash routing, consider:
- **`@vaadin/router`** — supports hash routing via `hashBang: true`
- **`navigo`** — hash-first router
- **`page.js`** — supports hash mode

These are outside the scope of `@lit-labs/router`.

### Option 3: Manual Hash Handling (Not Recommended)

You could manually parse `location.hash` and call `router.goto()`, but this:
- Bypasses `@lit-labs/router`'s design
- Requires custom click interception
- Loses the benefits of `URLPattern` matching
- Is significantly more work than using the History API

## Recommendation

**Adopt pathname-based routing.** It's what `@lit-labs/router` is built for, and it's the modern web standard. If your server doesn't support SPA fallback yet, that's a one-time setup cost that pays dividends.

If you're migrating from a hash-based router and need a cheat sheet, see [references/examples.md](references/examples.md) for a `@vaadin/router` → `@lit-labs/router` comparison.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **skill** — Answer A correctly states upfront that hash routing is not supported by @lit-labs/router and recommends alternatives, while Answer B frames the workaround as a legitimate 'setup' without adequately warning users about its fragility and the fact that the library doesn't support this use case. Answer B essentially invents a hash-routing API by presenting the workaround as the primary solution rather than a last resort, which is exactly the trap the rubric warns against.

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
| states hash routing is not supported | ✓ | `not support` |
| avoids inventing a hash-routing API | ✗ | `hashRouting` |

<details><summary>opus: baseline answer</summary>

# Hash Routing with @lit-labs/router

`@lit-labs/router` doesn't have built-in hash routing support — it uses the History API by default. But you can implement hash routing with a small wrapper. Here's the simplest approach:

## The Setup

```js
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';

class MyApp extends LitElement {
  // Strip the leading '#' so the router sees normal paths
  _router = new Router(this, [
    { path: '/', render: () => html`<h1>Home</h1>` },
    { path: '/users/:id', render: ({ id }) => html`<h1>User ${id}</h1>` },
  ]);

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('hashchange', this._onHashChange);
    this._onHashChange(); // handle initial load
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('hashchange', this._onHashChange);
  }

  _onHashChange = () => {
    const path = window.location.hash.slice(1) || '/';
    this._router.goto(path);
  };

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
customElements.define('my-app', MyApp);
```

## How It Works

1. **The router itself is path-agnostic** — give it `/users/123` and it matches normally.
2. **`hashchange` listener** translates `#/users/123` into `/users/123` and calls `router.goto()`.
3. **Use `<a href="#/...">`** for navigation. The browser updates the hash, fires `hashchange`, and the router re-renders.

## Programmatic Navigation

Instead of calling `router.goto()` directly (which would bypass the hash), update the hash:

```js
window.location.hash = '/users/456';
```

That's it — no need to override `goto()` or intercept link clicks. The hash is the single source of truth, and the router just follows along.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Hash routing with `@lit-labs/router` is not supported

`@lit-labs/router` matches exclusively against `location.pathname`. There is no `hashRouting: true` option, no `hashbang` mode, and no documented way to make `URLPattern` match against the fragment. The router also installs `popstate` and intercepts `<a href>` clicks for History API navigation — the hash never enters the matching pipeline.

So there is no "simple" answer here, only choices:

## Option 1 (recommended): use real History API URLs

Switch from `/#/users/123` to `/users/123`. This is what the library is designed for.

```ts
private _router = new Router(this, [
  {path: '/users/:id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
]);
```

You'll need your dev/prod server to serve `index.html` for unknown paths (SPA fallback). Vite, Wrangler, Netlify, Vercel, etc. all do this with one line of config. This is almost always the right answer in 2025 — hash routing is a workaround for static hosts that can't do SPA fallback, and that situation is rare now.

## Option 2: pick a router that actually does hash routing

If you genuinely need hash URLs (e.g. you're hosting on something like raw GitHub Pages without a 404→index rewrite, or embedding inside another app's path), use a router that supports it natively:

- **`@vaadin/router`** — supports hash routing via `new Router(outlet, {baseUrl: ''})` plus listening on `hashchange`, and has a documented hash-routing recipe.
- **`urlpattern-router`** or other community Lit routers — check their docs.

Don't try to bolt hash routing onto `@lit-labs/router` — you'd end up reimplementing click interception, `hashchange` handling, and pathname rewriting, at which point you've replaced the library.

## Option 3 (only if you must stay on `@lit-labs/router`): rewrite hash → pathname at the edges

The idea: keep the hash in the URL bar for the user, but feed the pathname-shaped string to the router. This is fragile and I'd push back on it, but for completeness:

```ts
// On startup and on hashchange, mirror the hash into the router.
const hashToPath = () => location.hash.slice(1) || '/';

window.addEventListener('hashchange', () => {
  this._router.goto(hashToPath());
});

// Initial sync
this._router.goto(hashToPath());
```

You then have to:
- intercept your own `<a href="#/users/123">` clicks (the library's click handler ignores hash-only links),
- avoid calling `history.pushState` (it would fight the hash),
- accept that `this._router.params` and `location.pathname` are now out of sync, which will bite you any time you read `location` directly.

I don't recommend this. If you're at the point of writing this glue, switch to Option 1 or 2.

---

**My recommendation:** go with Option 1. If you tell me what's blocking you from using real pathname URLs (static host? embedded app? something else?), I can give you a more targeted answer — including the one-line SPA-fallback config for your hosting setup.

</details>

---

### `offtopic-git-rebase`

**Prompt**

```
What's the difference between `git merge` and `git rebase`?
Just a short, plain explanation.
```

**Judge focus:** This question has nothing to do with lit-router. Both answers
should be essentially equivalent. Pick "tie" unless one is
materially wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in content, accuracy, and usefulness. They both explain the core difference between merge and rebase, include ASCII diagrams, and provide a comparison table with the same key points. Neither is materially wrong or superior.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## `git merge` vs `git rebase`

Both integrate changes from one branch into another, but differently:

---

### `git merge`
- **Combines** two branches by creating a new "merge commit"
- **Preserves** the full history of both branches
- History looks like branches diverging and reconnecting

```
A---B---C  (main)
     \   \
      D---E  (merge commit)
```

---

### `git rebase`
- **Replants** your commits on top of another branch
- **Rewrites** history to look linear (no merge commit)
- History looks like everything happened in a straight line

```
A---B---C---D  (main, after rebase)
```

---

### Simple rule of thumb

| | `merge` | `rebase` |
|---|---|---|
| History | Preserved as-is | Rewritten, linear |
| Merge commit | Yes | No |
| Safe for shared branches | ✅ Yes | ⚠️ Avoid |

> **Avoid rebasing branches others are working on** — rewriting shared history causes problems for teammates.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## `git merge` vs `git rebase`

Both integrate changes from one branch into another, but they do it differently.

**`git merge`** creates a new "merge commit" that joins the two branch histories together. The original commits from both branches are preserved as-is.

```
A---B---C  (main)
     \   \
      D---E  (merge commit)
       \
        (feature)
```

**`git rebase`** replays your branch's commits on top of the target branch, rewriting them as if you'd started from there. The result is a straight, linear history — but the commits are new copies.

```
Before:          After rebase onto main:
A---B  (main)    A---B---D'---E'  (feature)
     \
      D---E  (feature)
```

---

### Quick rule of thumb

| | `merge` | `rebase` |
|---|---|---|
| History | Preserves exact history | Rewrites history (linear) |
| Safe to use on shared branches? | ✅ Yes | ⚠️ Avoid — rewrites commits others may have |
| Merge commit added? | Yes | No |

**Use `merge`** for shared/public branches (like `main`).  
**Use `rebase`** to clean up your local feature branch before merging.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in content and accuracy. Answer B adds a visual diagram which some may find helpful, while Answer A has slightly more prose explanation. Neither is materially better or worse than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# `git merge` vs `git rebase`

**`git merge`**
- Combines two branches by creating a new "merge commit"
- Keeps the full history of both branches
- Results in a branched history (non-linear)
- Safer for shared/public branches

**`git rebase`**
- Replays your commits on top of another branch
- Rewrites commit history to be linear
- Cleaner, simpler history
- Don't use on shared/public branches (rewrites history)

**Quick example:**

With merge, you get:
```
A—B—C (main)
 \ /
  D—E (feature)
```

With rebase, you get:
```
A—B—C—D'—E' (main)
```

**Rule of thumb:** Use `merge` for shared branches, `rebase` for local branches before pushing.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# `git merge` vs `git rebase`

**`git merge`**
- Combines two branches by creating a new "merge commit" that has both branches as parents.
- Keeps the full history of both branches intact.
- Results in a branching history graph.

**`git rebase`**
- Replays one branch's commits on top of another branch, rewriting history.
- Creates a linear history (no merge commit).
- Cleaner timeline, but rewrites commit hashes — don't use on shared/public branches.

**When to use:**
- **Merge**: Integrating a feature branch into main; preserves history and is safe for shared branches.
- **Rebase**: Cleaning up local commits before pushing; keeping a linear history on feature branches.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in accuracy, completeness, and usefulness. They cover the same core concepts (merge creates a merge commit preserving history, rebase replays commits linearly rewriting history) and both include practical guidance about avoiding rebase on shared branches. Neither is materially better or worse than the other.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

**`git merge`** combines two branches by creating a new "merge commit" that ties their histories together. Both branches' histories are preserved as-is.

**`git rebase`** moves your branch's commits on top of another branch, rewriting history to make it look like you started your work from the latest point.

**Quick analogy:**
- *Merge* = "Let's join our work and record that we did."
- *Rebase* = "Let me replay my changes as if I started from your latest version."

**Result:**
- Merge → preserves history, but can look messy with many branches.
- Rebase → cleaner, linear history, but rewrites commits (avoid on shared branches).

</details>

<details><summary>opus: skill-loaded answer</summary>

**Merge** combines two branches by creating a new "merge commit" that ties their histories together. Both branches' histories are preserved exactly as they happened, including the divergence and the join point.

**Rebase** takes your branch's commits and replays them on top of another branch, as if you'd started your work from that branch's latest commit. The result is a straight, linear history — but the commits are technically new ones (different hashes).

**Rule of thumb:**
- Use **merge** for shared/public branches — it's safe and preserves true history.
- Use **rebase** for your own local branches before sharing — it keeps history tidy.
- Never rebase commits that others have already pulled.

</details>

---
