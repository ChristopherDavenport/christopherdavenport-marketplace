# Eval report: `lit-router`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **9**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.30** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 6/9 | 6 / 1 / 2 | 80% → 91% (+10%) |
| `haiku` | 9/9 | 8 / 0 / 1 | 57% → 93% (+35%) |
| `opus` ¹ | 4/9 | 4 / 2 / 3 | 82% → 82% (+0%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 7 | 5/7 | 7/7 | 3/7 |
| `skill_wins_strict` | 1 | 0/1 | 1/1 | 0/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `goto-doesnt-update-url` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `trailing-slash-routes` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ ✗ baseline |
| `nested-routes-vs-router` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `link-helper` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `click-interception-rules` | skill_wins | ✗ ✗ baseline | ✓ ✓ skill | ✗ = tie |
| `active-link-styling` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ ✗ baseline |
| `enter-vs-task-data-loading` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify that goto() does not push history and recommend history.pushState as the fix. Answer A is more accurate about <a href> link interception, correctly stating that the router handles both pushState and goto automatically for anchor clicks, while Answer B incorrectly implies you need to manually wire up click handlers for anchors. Answer A is also more concise and idiomatic, while Answer B introduces potentially incorrect implementation details about popstate handling that may not reflect how @lit-labs/router actually works.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains goto does not push history | tie |
| recommends history.pushState | tie |
| mentions <a href> link interception | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `not** call `history` |
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

`@lit-labs/router` uses the **History API** internally, but `router.goto()` only updates the router's internal state — it does **not** call `history.pushState()` by default in all versions/configurations. You're getting client-side rendering without a real navigation entry in the browser's history stack.

---

## Root Cause

The `Routes` class in `@lit-labs/router` relies on the browser's `popstate` event and `history.pushState`, but `goto()` is essentially just:

```js
// Simplified what goto() does internally
this._currentPathname = path;
this.host.requestUpdate();
```

It **skips** pushing a new history entry unless you wire it up correctly.

---

## The Fix

You need to call `history.pushState()` **yourself** alongside `goto()`, or use the correct pattern the library expects:

### Option 1: Manually push history state (quick fix)

```js
handleClick(e) {
  e.preventDefault();
  history.pushState(null, '', '/dashboard'); // ← push the URL first
  this._router.goto('/dashboard');           // ← then update the router
}
```

### Option 2: Use an anchor tag and let the router intercept it (recommended)

The router is designed to intercept `<a>` tag clicks. Wire up a click handler on your root element:

```js
// In your top-level component
connectedCallback() {
  super.connectedCallback();
  this.addEventListener('click', (e) => {
    const anchor = e.composedPath().find(
      (el) => el instanceof HTMLAnchorElement
    );
    if (anchor) {
      e.preventDefault();
      history.pushState(null, '', anchor.href);
      this._router.goto(anchor.pathname);
    }
  });

  // Handle back/forward buttons
  window.addEventListener('popstate', () => {
    this._router.goto(window.location.pathname);
  });
}
```

Then in your template, just use normal links:

```js
html`<a href="/dashboard">Dashboard</a>`
```

### Option 3: Create a helper method to keep them in sync

```js
navigate(path) {
  history.pushState(null, '', path);
  this._router.goto(path);
}

// Usage
this.navigate('/dashboard');
```

---

## Don't Forget `popstate`

Even after fixing `goto()`, the **back button** won't work unless you listen for `popstate`:

```js
connectedCallback() {
  super.connectedCallback();
  this._popstateHandler = () => {
    this._router.goto(window.location.pathname);
  };
  window.addEventListener('popstate', this._popstateHandler);
}

disconnectedCallback() {
  super.disconnectedCallback();
  window.removeEventListener('popstate', this._popstateHandler);
}
```

---

## Summary

| Problem | Fix |
|---|---|
| URL bar not updating | Call `history.pushState()` before `goto()` |
| Back button broken | Listen for `popstate` and call `goto()` |
| Repetitive boilerplate | Wrap both in a `navigate()` helper |

The core issue is that `@lit-labs/router` is a **rendering** abstraction, not a full navigation abstraction — history management is your responsibility.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## The Problem

`goto()` updates the router's internal state and re-renders the component, but it **does not call `history.pushState`**. That's a known design quirk of `@lit-labs/router` — the two operations are intentionally separate, but the docs don't make it obvious.

So your URL bar stays on the old path, and since nothing was ever pushed to the history stack, the back button has nothing to go back to.

## The Fix

Always pair `history.pushState` with `goto()`:

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}
```

Then in your click handler:

```ts
html`<button @click=${() => this._navigate('/dashboard')}>
  Go to Dashboard
</button>`
```

## Better Yet — Use `<a href>` Instead

For in-app links, a plain anchor is the idiomatic approach. `Router` already intercepts same-origin clicks automatically, handling both `pushState` and `goto` for you:

```ts
html`<a href="/dashboard">Go to Dashboard</a>`
```

The router intercepts the click as long as the link:
- Is same-origin
- Has no `target` attribute
- Has no `download` or `rel="external"` attribute
- Is clicked without modifier keys (Ctrl, Meta, Shift, Alt)

Reserve the `history.pushState` + `goto()` pair for cases where you genuinely need programmatic navigation (e.g. after a form submission or an async operation completes).

## Why the Back Button Breaks

Each `history.pushState` call adds an entry to the browser's session history stack. Without it, navigating around your app never grows the stack, so the back button either does nothing or jumps all the way out of your app to wherever you came from before the first page load.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the root cause: goto() does not call history.pushState(), and explicitly recommends pairing them together. Answer A misdiagnoses the problem (blaming initialization or setBasePath) and never clearly states that goto() doesn't push history. Answer B also covers all three rubric criteria clearly, including <a href> link interception with a good explanation of how the router handles it automatically.

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
| mentions <a href> link interception | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `not** call `pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

<details><summary>haiku: baseline answer</summary>

# The Issue

You're likely calling `goto()` without the `replace` parameter, but the real problem is probably that **you need to use `setBasePath()` or your router isn't properly initialized**.

However, the most common cause of this specific symptom (route renders but URL doesn't update) is:

## You're not using the router's link element or the router isn't managing history

The `@lit-labs/router` needs to be set up to actually update browser history. Here are the solutions:

### Solution 1: Use `<router-link>` instead of manual `goto()`

```javascript
// Instead of:
// <button @click=${() => this._router.goto('/dashboard')}>

// Use:
<router-link href="/dashboard">
  <button>Go to Dashboard</button>
</router-link>
```

### Solution 2: If you must use `goto()`, ensure the router is initialized correctly

```javascript
import { Router } from '@lit-labs/router';

export class MyApp extends LitElement {
  private _router = new Router(this, [
    { path: '/dashboard', render: () => html`<dashboard-page></dashboard-page>` },
    // ... other routes
  ]);

  constructor() {
    super();
    // Make sure to set the base path if needed
    this._router.setBasePath('/');
  }

  handleClick() {
    // This should work if router is properly initialized
    this._router.goto('/dashboard');
  }
}
```

### Solution 3: Check your route configuration

Make sure your routes are defined **before** calling `goto()`:

```javascript
private _router = new Router(this, [
  { path: '/', render: () => html`<home-page></home-page>` },
  { path: '/dashboard', render: () => html`<dashboard-page></dashboard-page>` },
]);
```

**The key issue**: `goto()` updates the internal route state but may not update browser history if the router isn't properly wired up. Using `<router-link>` is the recommended approach.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# The Problem

You're calling `goto()` **without** `history.pushState()`. The `goto()` method updates the rendered route, but it does **not** change the URL bar or the history stack — that's a known gotcha in `@lit-labs/router`.

When you skip `pushState`, the URL bar stays at the old path while the page renders the new route. Then the back button is broken because the history stack was never updated.

## The Fix

**Always pair `history.pushState` with `router.goto`:**

```ts
private _router = new Router(this, [...]);

private handleNavigate(path: string) {
  // 1. Update the history stack
  history.pushState({}, '', path);
  // 2. Update the rendered route
  this._router.goto(path);
}

render() {
  return html`
    <button @click=${() => this.handleNavigate('/dashboard')}>
      Go to Dashboard
    </button>
  `;
}
```

## Why This Happens

- `goto(path)` is a **render-only** method — it updates `this._router.params` and calls `requestUpdate()` so the new route renders.
- `history.pushState(state, title, url)` is a **history-only** method — it changes the URL bar and adds an entry to the browser's back/forward stack.
- The router does **not** call `pushState` for you because you might want to use `goto()` without changing history (e.g., silent re-renders on data refresh).

## When You Don't Need This

If you're using **`<a href>`** links, the router's click handler does both automatically:

```ts
render() {
  return html`
    <!-- This works without manual pushState -->
    <a href="/dashboard">Go to Dashboard</a>
  `;
}
```

The router intercepts same-origin clicks on `<a>` tags (with no `target`, no modifier keys, no `download`/`rel="external"`) and internally calls both `pushState` and `goto()` for you.

## Summary

| Scenario | What to do |
|----------|-----------|
| Clicking an `<a href>` | Nothing — router handles it |
| Programmatic nav (button, event, etc.) | `history.pushState(...)` + `router.goto(...)` |
| Silent re-render (no history change) | `router.goto(...)` alone (rare) |

See [references/navigation.md](references/navigation.md) for the full click-interception rules and [references/pitfalls.md](references/pitfalls.md) for this gotcha in detail.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify that goto() does not push history and recommend history.pushState. Answer A more clearly and concisely covers all three rubric criteria, explicitly mentioning that the router's click interceptor handles <a href> links (including the pushState call), while Answer B buries the anchor interception in a 'bonus' section and incorrectly implies the user must manually implement click interception rather than noting the router already does this. Answer A's explanation that the router already installs a global click interceptor is more accurate and useful.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains goto does not push history | tie |
| recommends history.pushState | tie |
| mentions <a href> link interception | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `not** call `history` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains goto does not push history | ✓ | `does not call `history.pushState` |
| recommends history.pushState | ✓ | `history.pushState` |
| mentions <a href> link interception | ✓ | `<a href` |

<details><summary>opus: baseline answer</summary>

# The issue: `goto()` doesn't touch History

`Routes.goto()` in `@lit-labs/router` is intentionally **not** a navigation method in the browser-history sense. It only:

1. Matches the path against the route patterns,
2. Runs the matched route's `enter()` callback,
3. Triggers a re-render so the new route's `render()` runs.

It does **not** call `history.pushState()`, it doesn't update `location`, and it doesn't fire `popstate`. That's why your view changes but the URL bar and back button don't.

The library is honest about this — `goto()` is described as "for clients to navigate" in the sense of "tell the Routes object to switch", not "drive the browser." There's an open issue (lit/lit#3402 and related) tracking the fact that there's no built-in history integration yet.

# What to do instead

You have to drive History yourself and then tell the router. A small helper:

```ts
private _navigate(path: string) {
  // Update the URL bar and push a history entry
  window.history.pushState({}, '', path);
  // Tell the router to match and render the new path
  this._router.goto(path);
}
```

Use it in your click handler:

```ts
@click=${(e: Event) => {
  e.preventDefault();
  this._navigate('/dashboard');
}}
```

And handle back/forward by listening for `popstate` once (e.g. in `connectedCallback`):

```ts
connectedCallback() {
  super.connectedCallback();
  this._onPopState = () => this._router.goto(window.location.pathname);
  window.addEventListener('popstate', this._onPopState);
}

disconnectedCallback() {
  window.removeEventListener('popstate', this._onPopState);
  super.disconnectedCallback();
}
```

# Bonus: anchor clicks

If you also want `<a href="/dashboard">` to work without a full page load, intercept clicks at a top level:

```ts
this.addEventListener('click', (e) => {
  const a = (e.target as HTMLElement).closest('a');
  if (!a) return;
  const href = a.getAttribute('href');
  if (!href || href.startsWith('http') || a.target === '_blank') return;
  e.preventDefault();
  this._navigate(href);
});
```

# TL;DR

`@lit-labs/router` is still a *labs* package and deliberately leaves history management to you. `goto()` only updates the router's internal state and re-renders. Wrap it with `history.pushState` + a `popstate` listener and the URL bar and back button will behave as expected.

</details>

<details><summary>opus: skill-loaded answer</summary>

This is a known gotcha in `@lit-labs/router`: **`goto()` does not call `history.pushState`**. It updates the matched route and re-renders, but it never touches the History API, so the URL bar stays put and back/forward have nothing new to navigate to.

You have two clean fixes — pick based on whether you actually need a click handler.

## Fix 1 (preferred): Just use `<a href>`

The `Router` already installs a global click interceptor. Same-origin `<a>` clicks (no `target`, no modifier keys, no `download`, no `rel="external"`) are SPA-navigated for you — including the `pushState` call.

```ts
render() {
  return html`<a href="/dashboard">Dashboard</a>`;
}
```

No click handler, no `goto()`, no manual history calls. Back button works.

## Fix 2: Pair `pushState` with `goto` yourself

If you genuinely need a programmatic click handler (e.g. you're navigating after some logic, not from a link):

```ts
private _onClick() {
  const path = '/dashboard';
  history.pushState({}, '', path);
  this._router.goto(path);
}
```

You can wrap that in a helper so you never forget:

```ts
private _navigate(path: string) {
  history.pushState({}, '', path);
  this._router.goto(path);
}
```

`Router` also listens for `popstate`, so once the URL is in history correctly, the back button will fire `popstate` and the router will re-match against the restored `location.pathname`.

## Why it works this way

`goto(pathname)` is essentially "match this string against my routes and render the result." It's deliberately decoupled from the URL — useful for tests and edge cases, but it means *you* own the History API for programmatic navigation. The click interceptor handles `pushState` only because it's intercepting a real `<a>` click, where the user's intent to change the URL is unambiguous.

So: prefer real links, and when you can't, always pair `history.pushState(...)` with `this._router.goto(...)`.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly identify URLPattern semantics and offer the same three solutions, but Answer B is more practically oriented and better structured. Answer B prioritizes fixing links as the preferred solution (which is the most pragmatic advice), provides a cleaner summary table, and gives more accurate technical details about the wildcard behavior. Answer A incorrectly states that `*` matches 'zero or more chars' while also saying `/users/` matches — this is slightly contradictory in explanation. Answer B's ordering of recommendations (fix links first, then redirect, then raw URLPattern) is more useful for real-world scenarios.

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
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `/users` and `/users/*` |

<details><summary>sonnet: baseline answer</summary>

## The Problem

The `/*` wildcard pattern in `@lit-labs/router` uses **URLPattern** under the hood. The pattern `/users/*` requires at least one character after the slash — meaning `/users/` (empty wildcard) technically matches, but `/users` (no slash at all) does **not**, because the `/` itself is part of the pattern.

```
/users/*
       ^^
       |└─ wildcard (zero or more chars, but...)
       └─ this literal slash must be present
```

So:
| URL | Matches `/users/*`? |
|---|---|
| `/users/` | ✅ |
| `/users/profile` | ✅ |
| `/users` | ❌ |

---

## Solutions

### Option 1 — Add a second route for the exact path (simplest)

```js
new Router(this, [
  { path: '/users',   render: () => html`<users-layout />` },
  { path: '/users/*', render: () => html`<users-layout />` },
]);
```

Both routes render the same component; the component itself handles sub-routing internally.

---

### Option 2 — Use a redirect route

```js
new Router(this, [
  {
    path: '/users',
    render: () => {
      // Redirect to the canonical URL with a trailing slash
      window.history.replaceState({}, '', '/users/');
      return html`<users-layout />`;
    },
  },
  { path: '/users/*', render: () => html`<users-layout />` },
]);
```

---

### Option 3 — Match both with a single URLPattern-compatible pattern

URLPattern supports grouping with `{...}` for optional segments:

```js
new Router(this, [
  // {/}? makes the trailing slash optional, * catches the rest
  { path: '/users{/*}?', render: () => html`<users-layout />` },
]);
```

`{/*}?` means "optionally match a `/` followed by anything", so:

| URL | Matches `/users{/*}?`? |
|---|---|
| `/users` | ✅ |
| `/users/` | ✅ |
| `/users/profile` | ✅ |

This is the **most concise** solution and the one most consistent with how URLPattern is designed to handle optional trailing segments.

---

## Recommendation

Use **Option 3** (`{/*}?`) unless you need the redirect behavior. It's a single route, requires no duplication, and correctly handles all variants of the URL.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Why It Happens

`@lit-labs/router` compiles your `path` string into a `URLPattern` with **exact pathname matching**. The pattern `/users/*` expands to something like:

```
/users/<one-or-more-characters>
```

The wildcard `*` requires at least one character after the slash, so:

| URL visited | Matches `/users/*`? |
|-------------|---------------------|
| `/users/`   | ✅ (tail is `""`)   |
| `/users/42` | ✅                  |
| `/users`    | ❌ no slash, no tail |

There is no automatic redirect or normalization — the router simply finds no matching route and renders nothing (or your fallback).

---

## What To Do

You have three options, in order of preference:

### 1. Fix your links (preferred)

Always link to the trailing-slash form. The router's click interceptor will then navigate to a URL that actually matches.

```html
<!-- ❌ won't match /users/* -->
<a href="/users">Users</a>

<!-- ✅ matches /users/* -->
<a href="/users/">Users</a>
```

### 2. Add a companion redirect route

Keep `/users/*` for the nested section, and add a sibling route for the bare path that redirects:

```ts
private _router = new Router(this, [
  {
    path: '/users',
    enter: async () => {
      history.replaceState({}, '', '/users/');
      await this._router.goto('/users/');
      return false; // cancel this route; goto() handles rendering
    },
    render: () => html``, // never reached
  },
  {
    path: '/users/*',
    render: () => html`<users-section></users-section>`,
  },
]);
```

> **Note:** `return false` from `enter` cancels the navigation, so the redirect in `goto()` takes over cleanly.

### 3. Match both forms with a raw `URLPattern`

Instead of the `path` shorthand, supply a `pattern` that covers both `/users` and `/users/*`:

```ts
import {Router} from '@lit-labs/router';

private _router = new Router(this, [
  {
    pattern: new URLPattern({pathname: '/users{/*}?'}),
    render: () => html`<users-section></users-section>`,
  },
]);
```

The `{/*}?` group makes the slash-and-tail optional, so both `/users` and `/users/anything` match. The trade-off is that `params` will no longer contain a clean named group — you may need to parse `location.pathname` manually inside the component.

---

## Summary

| Approach | Best when |
|----------|-----------|
| Fix links to use trailing slash | You control all the links (most cases) |
| Redirect route | You can't control incoming URLs (external links, bookmarks) |
| Raw `URLPattern` with `{/*}?` | You need both forms to render the same component without a redirect |

The root cause is always the same: `/users/*` is a strict pattern that requires a `/` after the prefix. Option 1 is the right default; add Option 2 if you need to handle bare URLs from outside your app.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly explains URLPattern semantics — that `/users/*` requires the `/users/` prefix with a trailing slash, and the wildcard matches zero or more characters after that prefix. Answer B mischaracterizes the issue by claiming the wildcard requires 'at least one segment,' which is incorrect (it actually matches zero characters after the slash). Answer B's recommended solution of `/?*` is also dubious as a URLPattern syntax and not a standard @lit-labs/router pattern, whereas Answer A's solutions (trailing slash links and registering both paths) are accurate and practical. Answer A covers all three rubric criteria more accurately.

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
| mentions registering both paths as alternative | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✗ | |

<details><summary>haiku: baseline answer</summary>

# Route Matching Issue with `@lit-labs/router`

The route `/users/*` requires at least one segment after `/users/` to match. When you navigate to `/users` without a trailing slash, there's nothing after `users`, so the wildcard pattern doesn't match.

## Solutions

### Option 1: Make the wildcard optional (Recommended)

Use `?` to make the wildcard segment optional:

```javascript
{
  path: '/users/?*',
  component: 'users-section'
}
```

This matches:
- `/users`
- `/users/` 
- `/users/123`
- `/users/123/profile`

### Option 2: Add a separate exact route

Handle both cases explicitly:

```javascript
{
  path: '/users',
  component: 'users-list'
},
{
  path: '/users/*',
  component: 'users-section'
}
```

### Option 3: Redirect `/users` to `/users/`

In your router configuration:

```javascript
{
  path: '/users',
  action: () => {
    router.navigate('/users/');
  }
}
```

## Best Practice

**Option 1** is usually best because:
- Single route definition
- Handles all variations consistently
- No redirect overhead
- Cleaner URL handling

The `/?*` pattern means "optional slash followed by optional remaining path segments."

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Trailing-Slash Matching in `/users/*` Routes

## Why It Doesn't Match

`URLPattern` treats `/users` and `/users/` as **distinct paths**. When you define a parent route with `path: '/users/*'`, the `*` wildcard matches **zero or more characters after the `/users/` prefix** — but only if the prefix itself is present.

- `/users/` → matches (empty tail)
- `/users/123` → matches (tail is `123`)
- `/users` → **does NOT match** (no trailing slash, so no `/users/` prefix to anchor the wildcard)

## Solutions

### Option 1: Always Link with a Trailing Slash (Recommended)

Change your navigation links to include the trailing slash:

```ts
// ❌ Don't do this
<a href="/users">Users</a>

// ✅ Do this
<a href="/users/">Users</a>
```

This is the simplest fix and aligns with the library's design.

### Option 2: Add a Redirect Route

Add a sibling route that catches the bare path and redirects:

```ts
const routes = [
  {
    path: '/users',
    enter: () => {
      history.replaceState({}, '', '/users/');
      return false; // Cancel this navigation
    },
  },
  {
    path: '/users/*',
    render: () => html`<users-section></users-section>`,
  },
  // ... other routes
];
```

The `enter` hook fires before rendering. Returning `false` cancels the navigation, and `replaceState` updates the URL without adding a history entry. The router then re-evaluates and matches `/users/*`.

### Option 3: Use a Catch-All Pattern (Less Precise)

If you want `/users` and `/users/` to behave identically without redirecting, you could add both:

```ts
const routes = [
  {
    path: '/users',
    render: () => html`<users-section></users-section>`,
  },
  {
    path: '/users/*',
    render: () => html`<users-section></users-section>`,
  },
  // ... other routes
];
```

However, this duplicates the render logic and is harder to maintain. **Option 1 or 2 is preferable.**

## Best Practice

**Adopt trailing slashes consistently in your app.** Link to `/users/`, `/products/`, etc., and document this convention. It avoids confusion and keeps nested routing predictable.

See [references/pitfalls.md](references/pitfalls.md) for more on this gotcha.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly identify URLPattern semantics and recommend registering both paths. Answer A goes further by explaining the optional group syntax `/users{/*}?` as the cleanest single-route solution, provides runnable test code to verify behavior, and is more clearly structured. Answer B adds useful nuance about nested routing limitations with option 3, but Answer A's Option 3 with URLPattern groups is more idiomatic and practical than anything B offers uniquely.

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
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✓ | `Two routes` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies URLPattern matching semantics | ✓ | `URLPattern` |
| recommends adding trailing slash to links | ✓ | `trailing slash` |
| mentions registering both paths as alternative | ✗ | |

<details><summary>opus: baseline answer</summary>

# Why `/users/*` doesn't match `/users`

`@lit-labs/router` uses [URLPattern](https://developer.mozilla.org/en-US/docs/Web/API/URLPattern) syntax under the hood. In URLPattern, the `*` is a **wildcard segment that requires the preceding `/` to be present in the URL**, plus zero or more characters after it.

So `/users/*` literally means: the string `/users/` followed by anything (including empty). It matches:

- ✅ `/users/`
- ✅ `/users/123`
- ✅ `/users/123/posts`
- ❌ `/users` ← no trailing slash, no match

This is the same behavior as `path-to-regexp` and Express-style routers when you write `/users/*`.

## Fixes

### Option 1: Two routes (most explicit)

```js
this.router = new Router(this, [
  { path: '/users',   render: () => html`<users-page></users-page>` },
  { path: '/users/*', render: () => html`<users-page></users-page>` },
]);
```

### Option 2: Redirect `/users` → `/users/`

If you want canonical URLs:

```js
{ path: '/users', enter: () => { history.replaceState(null, '', '/users/'); return false; } },
{ path: '/users/*', render: () => html`<users-page></users-page>` },
```

Returning `false` from `enter` aborts rendering this route; the replaceState then triggers the wildcard match.

### Option 3: Make the slash optional with a URLPattern group

URLPattern supports `{...}?` for optional groups:

```js
{ path: '/users{/*}?', render: () => html`<users-page></users-page>` }
```

This matches `/users`, `/users/`, and `/users/anything`. This is usually the cleanest answer.

## Why it works this way

`*` in URLPattern is shorthand for the named pattern `(.*)` — it matches characters within a single "segment context," but it doesn't make the literal `/` before it optional. The pattern is matched against the full pathname, so the `/` between `users` and `*` is required text.

If you ever need to debug a pattern, you can test it directly:

```js
new URLPattern({ pathname: '/users/*' }).test({ pathname: '/users' });   // false
new URLPattern({ pathname: '/users{/*}?' }).test({ pathname: '/users' }); // true
```

I'd go with **Option 3** unless you have a reason to treat `/users` as a separate route.

</details>

<details><summary>opus: skill-loaded answer</summary>

## Why it doesn't match

`@lit-labs/router` compiles each `path` string into a `URLPattern` and matches against `location.pathname` literally. The pattern `/users/*` requires the literal `/` before the wildcard, so:

- `/users/`     ✅ matches (`*` captures `''`)
- `/users/foo`  ✅ matches (`*` captures `foo`)
- `/users`      ❌ does **not** match — there's no trailing `/`

`URLPattern` does not normalize trailing slashes, and the router does no extra fixup. This is a known sharp edge — see [references/pitfalls.md](references/pitfalls.md).

## What to do

Pick one (or combine them):

**1. Always link with the trailing slash.** This is the recommended fix.
```ts
html`<a href="/users/">Users</a>`
```
The click interceptor will SPA-navigate, and `/users/*` matches cleanly.

**2. Add a sibling route that redirects bare `/users` to `/users/`.**
```ts
new Router(this, [
  {
    path: '/users',
    enter: () => {
      history.replaceState({}, '', '/users/');
      this._router.goto('/users/');
      return false; // cancel this match; the goto above takes over
    },
    render: () => html``,
  },
  {path: '/users/*', render: () => html`<users-section></users-section>`},
  // ...
]);
```
`replaceState` (not `pushState`) avoids polluting history with the slash-less URL. Returning `false` from `enter` cancels the current navigation so the new `goto` wins.

**3. Add a second route entry that renders the same component.**
```ts
{path: '/users',   render: () => html`<users-section></users-section>`},
{path: '/users/*', render: () => html`<users-section></users-section>`},
```
Simpler, but the child `Routes` inside `<users-section>` matches against the parent's tail group — which only exists for the `/users/*` entry. The bare `/users` entry will mount the component but the child's `path: ''` index route won't match. So this only works if the child doesn't rely on nested routing for its index view.

**For your case (nested users section), use option 1 or 2.** Option 1 is the idiomatic fix; option 2 is the belt-and-braces version if users might type `/users` directly or land on it from an external link.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the key distinction between Router and Routes — that nested sections should use Routes (not Router), which is the core of the question. Answer A never mentions the Routes controller at all, instead suggesting plain conditionals or multiple Router instances, missing the idiomatic @lit-labs/router pattern entirely. Answer B also explicitly explains the global click and popstate listener mechanism and how Routes wires up via the bubbling lit-routes-connected event.

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
| identifies one Router per page | ✓ | `only one` |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global** `click` |

<details><summary>sonnet: baseline answer</summary>

## Nested Routes with `@lit-labs/router`

The short answer is **no** — you should not create multiple `new Router()` instances. Here's why and what to do instead.

---

## Why One Router Instance

`@lit-labs/router` uses the browser's History API under the hood. Multiple `Router` instances will:

- **Fight over `popstate` events** — each instance tries to handle every navigation
- **Cause double-renders** — both routers respond to the same URL change
- **Break link interception** — `<a>` clicks get processed multiple times

---

## The Right Pattern: Nested Route Matching

Use **prefix matching in the parent** and **pass remaining path segments to children**.

### Parent Router (App Shell)

```javascript
// app-shell.js
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';

class AppShell extends LitElement {
  #router = new Router(this, [
    {
      path: '/',
      render: () => html`<home-page></home-page>`,
    },
    {
      // Wildcard captures everything under /users/
      path: '/users/*',
      render: ({ rest }) => html`
        <users-section .rest=${rest}></users-section>
      `,
    },
    {
      path: '/products/*',
      render: ({ rest }) => html`
        <products-section .rest=${rest}></products-section>
      `,
    },
    {
      path: '/*',
      render: () => html`<not-found-page></not-found-page>`,
    },
  ]);

  render() {
    return this.#router.outlet();
  }
}

customElements.define('app-shell', AppShell);
```

### Child Section (No Router — Just Conditional Rendering)

```javascript
// users-section.js
import { LitElement, html } from 'lit';
import { property } from 'lit/decorators.js';

class UsersSection extends LitElement {
  // 'rest' is whatever comes after /users/
  // e.g. for /users/123/edit, rest = '123/edit'
  @property({ type: String })
  rest = '';

  get #segments() {
    // Clean and split the remaining path
    return this.rest.replace(/^\//, '').split('/').filter(Boolean);
  }

  render() {
    const [id, action] = this.#segments;

    // Route within the section using plain conditionals
    if (!id) {
      return html`<users-list></users-list>`;
    }

    if (action === 'edit') {
      return html`<user-edit .userId=${id}></user-edit>`;
    }

    return html`<user-detail .userId=${id}></user-detail>`;
  }
}

customElements.define('users-section', UsersSection);
```

---

## Alternative: Nested Router Instances (If You Must)

If sections are truly independent and loaded lazily, you *can* scope child routers — but you must **prevent event propagation**:

```javascript
// ⚠️ Only do this if sections are fully isolated lazy bundles
class UsersSection extends LitElement {
  #router = new Router(this, [
    { path: '/users/',        render: () => html`<users-list></users-list>` },
    { path: '/users/:id',     render: ({id}) => html`<user-detail .userId=${id}></user-detail>` },
    { path: '/users/:id/edit',render: ({id}) => html`<user-edit .userId=${id}></user-edit>` },
  ]);

  render() {
    return this.#router.outlet();
  }
}
```

> **Caveat:** As of `@lit-labs/router` 0.x, there is **no built-in scoping** — child routers still see the full URL. This means you must use full absolute paths in child routes, and you risk the conflicts mentioned above.

---

## Decision Guide

```
Do you need lazy loading of entire route sections?
├── No  → Use ONE router + conditional rendering in child components
│         (simplest, no conflicts)
│
└── Yes → Use ONE router with dynamic imports in render()
          ┌─────────────────────────────────────────────────┐
          │ { path: '/users/*', render: () => {             │
          │     import('./users-section.js');               │
          │     return html`<users-section></users-section>`│
          │   }                                             │
          │ }                                               │
          └─────────────────────────────────────────────────┘
          Still ONE Router instance — lazy loading is separate
          from routing
```

---

## Key Takeaways

| Concern | Answer |
|---|---|
| Number of `Router` instances | **One**, at the app root |
| Nested path matching | Use `/*` wildcard + pass `rest` down |
| Child section routing | Plain conditionals on `rest` segments |
| Lazy loading | Dynamic `import()` inside `render()` callbacks |
| Multiple routers | Avoid — causes event handling conflicts |

</details>

<details><summary>sonnet: skill-loaded answer</summary>

No — each section should create a `new Routes(...)`, not a `new Router(...)`. One `Router` per page is the rule; `Routes` is the right tool for every nested section.

## Why only one `Router`

`Router` installs **global** `click` and `popstate` listeners on `window`. A second `Router` means:

- Every click is handled twice.
- Both instances race on `popstate` (back/forward button).
- They can clobber each other's rendered output.

## The correct pattern

```
MyApp          → new Router(this, [...])   ← one, at the root
UsersSection   → new Routes(this, [...])  ← nested
ProductsSection → new Routes(this, [...]) ← nested
```

### Root component

```ts
@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    { path: '/',           render: () => html`<home-page></home-page>` },
    { path: '/users/*',    render: () => html`<users-section></users-section>` },
    { path: '/products/*', render: () => html`<products-section></products-section>` },
  ], {
    fallback: { render: () => html`<not-found></not-found>` },
  });

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

### Nested sections (both follow the same pattern)

```ts
@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    { path: '',    render: () => html`<user-list></user-list>` },
    { path: ':id', render: ({id}) => html`<user-detail .id=${id}></user-detail>` },
  ]);

  render() { return html`${this._routes.outlet()}`; }
}

@customElement('products-section')
class ProductsSection extends LitElement {
  private _routes = new Routes(this, [
    { path: '',    render: () => html`<product-list></product-list>` },
    { path: ':id', render: ({id}) => html`<product-detail .id=${id}></product-detail>` },
  ]);

  render() { return html`${this._routes.outlet()}`; }
}
```

## How the wiring works

When a `Routes` controller is created, it fires a bubbling `lit-routes-connected` event up the DOM. The nearest ancestor `Router` or `Routes` catches it and registers itself as the parent. The parent then passes its **tail group** (the `*` capture from its own matched path) down to the child as the string to match against.

That's why child paths use no leading slash and no parent prefix:

| URL | Parent matches | Tail passed to child | Child matches |
|-----|---------------|----------------------|---------------|
| `/users/` | `/users/*` | `` (empty) | `''` → user list |
| `/users/42` | `/users/*` | `42` | `:id` → user detail |
| `/products/99` | `/products/*` | `99` | `:id` → product detail |

## Key rules to remember

- **Trailing slash on nav links** — link to `/users/`, not `/users`. The pattern `/users/*` matches `/users/` and `/users/foo`, but **not** `/users` (no trailing slash, no wildcard tail).
- **`path: ''` for the section index** — an empty string matches the tail when the URL is exactly `/users/`.
- **`this._routes.link('local-path')`** — use this inside a child component to build hrefs that automatically prepend the parent's matched prefix, keeping links correct regardless of where the section is mounted.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the Routes controller as the solution for nested sections and explicitly explains that Router installs global click and popstate listeners as the reason to avoid multiple Router instances. Answer A mentions a single Router but never introduces the Routes controller or explains the global listener conflict, missing the core architectural distinction the question is asking about.

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

- ✅ **Centralized state** — easier to manage navigation
- ✅ **Consistent history** — back/forward work correctly
- ✅ **Simpler debugging** — single source of truth
- ❌ **Multiple routers** — competing navigation, state conflicts

**Check your `@lit-labs/router` version** — nested route support varies. If unsure, flat routes with a single Router is the safest approach.

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

The same flow applies to `/products/*` and its nested `ProductsSection`.

## Key Points

| Aspect | Details |
|--------|---------|
| **Parent path** | Must end in `/*` (e.g., `/users/*`) to capture the tail |
| **Child paths** | No leading slash, no parent prefix — use `path: ''` for index, `path: ':id'` for params |
| **Links** | Always use trailing slash: `<a href="/users/">` not `<a href="/users">` |
| **Wiring** | Automatic via `lit-routes-connected` event; no manual setup needed |
| **Multiple nesting** | You can nest `Routes` inside `Routes` inside `Routes` — each level gets the tail from its parent |

See [nested-routing.md](references/nested-routing.md) for the full wiring mechanism and a complete multi-level example.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies that only one Router should be created per page and that Routes (not Router) should be used for nested sections, explicitly mentioning the global click and popstate listeners as the reason. Answer B is factually wrong — it recommends creating multiple Router instances per page, which is exactly the anti-pattern the question is asking about, and it never mentions the global listener conflict.

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
| mentions global click / popstate listener as the reason | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| identifies one Router per page | ✗ | |
| recommends Routes for nesting | ✓ | `Routes` |
| mentions global click / popstate listener as the reason | ✓ | `global `click` |

<details><summary>opus: baseline answer</summary>

# Nested Routers in `@lit-labs/router`

Yes, creating a separate `Router` instance per nested section is exactly the intended pattern. `@lit-labs/router` is designed around **per-component routers** rather than one global router config.

## The Pattern

Each routing "section" is a component that owns its own `Router`. The parent matches a prefix with a trailing `/*`, and the child router handles the rest of the path.

### Root router

```js
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';

class AppRoot extends LitElement {
  private _router = new Router(this, [
    { path: '/',            render: () => html`<home-page></home-page>` },
    { path: '/users/*',     render: () => html`<users-section></users-section>` },
    { path: '/products/*',  render: () => html`<products-section></products-section>` },
  ]);

  render() {
    return this._router.outlet();
  }
}
customElements.define('app-root', AppRoot);
```

The `/*` suffix is important — it tells the parent router to match the prefix and let a child router handle the remainder.

### Child router (users section)

```js
class UsersSection extends LitElement {
  private _router = new Router(this, [
    { path: '/',        render: () => html`<users-list></users-list>` },
    { path: '/:id',     render: ({ id }) => html`<user-detail .id=${id}></user-detail>` },
    { path: '/:id/edit',render: ({ id }) => html`<user-edit .id=${id}></user-edit>` },
  ]);

  render() {
    return this._router.outlet();
  }
}
customElements.define('users-section', UsersSection);
```

The child router automatically receives the path *relative* to where the parent matched, so you write paths like `/:id` — not `/users/:id`.

The products section follows the same shape.

## Why this pattern works well

- **Encapsulation** — each section owns its own routes; you don't have to declare every leaf route in a central config.
- **Lazy loading** — you can dynamically import the child component, and its routes only get registered when that section is actually rendered.
- **Composition** — sections can be reused or moved without rewriting routes.
- **Reactive controllers** — `Router` is a `ReactiveController`, so it ties cleanly to the host's lifecycle.

## Common gotchas

1. **Don't forget the `/*`** on parent routes — without it, the parent won't match anything past the prefix and the child router won't get a chance to run.
2. **Child paths are relative** — write `/:id`, not `/users/:id`.
3. **Use `router.link()` for hrefs** if you want correctly-resolved relative links inside a section: `<a href=${this._router.link('/42')}>`.
4. **Navigation is global** — `router.goto('/users/42')` works from anywhere; you don't need a reference to the specific child router to navigate into it.

So: yes, one `new Router(...)` per section is the right call.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Use `Routes`, not `Router`, in the nested sections

Only **one `Router` per page** — at the top level. Every nested section uses `Routes`.

## Why

`new Router(...)` installs **global `click` and `popstate` listeners** on `window`. If you instantiate it more than once:

- Same-origin link clicks get handled multiple times (multiple `requestUpdate`s, possible double-navigation).
- All `Router` instances respond to every `popstate`, regardless of which section the URL belongs to.
- They clobber each other's state.

`Routes` is the nested counterpart. It has the same matching logic and the same `outlet()` / `link()` / `goto()` API as `Router`, but **without** the global listeners. Instead, on connection it dispatches a bubbling `lit-routes-connected` event that the nearest ancestor `Routes` (or the root `Router`) catches and wires up. This is how the parent forwards its tail-group match (`/users/*` → everything after `/users/`) down to the child for re-matching.

## The right pattern

**Top-level app — one `Router`:**

```ts
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

**Each nested section — `Routes`:**

```ts
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
    {path: '',     render: () => html`<product-list></product-list>`},
    {path: ':id',  render: ({id}) => html`<product-detail .id=${id}></product-detail>`},
  ]);
  render() { return html`${this._routes.outlet()}`; }
}
```

## Two things to watch out for

1. **Trailing slashes on the parent links.** `/users/*` matches `/users/` and `/users/123` but **not** bare `/users`. So link as `<a href="/users/">`, not `<a href="/users">`.

2. **Child paths are relative to the parent's tail group.** No leading slash, no parent prefix — `path: ''` for the index, `path: ':id'` for `/users/:id`. The parent's `Routes` strips its own prefix before passing the rest down.

## TL;DR

| Where | Use |
|-------|-----|
| Top-level app component (one per page) | `new Router(this, [...])` |
| Every nested section (`<users-section>`, `<products-section>`, …) | `new Routes(this, [...])` |

One `Router`, many `Routes`.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly uses the `Routes` controller (not `Router`) with `link()` to resolve paths relative to the parent route prefix, which is exactly the pattern for nested routers in @lit-labs/router. Answer B misunderstands the nested router scenario by using a top-level `Router` with hardcoded absolute paths, defeating the purpose of relative resolution. Answer A's explanation of how `link()` prepends the matched prefix is accurate and directly addresses the question's focus on relative resolution within a nested section.

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

In `@lit-labs/router`, routes are matched against the **full pathname**, and a plain relative href like `detail` will resolve relative to the **current browser URL**, not relative to the router's mount point. This often breaks in nested scenarios.

---

## The Right Way

Use the router's **`link()`** helper (available on the `Router` instance) to generate a correctly resolved path:

```js
import { Router } from '@lit-labs/router';

class MyUsersView extends LitElement {
  private router = new Router(this, [
    { path: '/users/',        render: () => html`<users-list></users-list>` },
    { path: '/users/detail', render: () => html`<user-detail></user-detail>` },
  ]);

  render() {
    return html`
      <!-- ✅ Use router.link() to get the correct absolute path -->
      <a href="${this.router.link('/users/detail')}">Go to Detail</a>

      ${this.router.outlet()}
    `;
  }
}
```

---

## Why `router.link()` Is the Right Tool

| Approach | Result | Works? |
|---|---|---|
| `href="detail"` | Resolves relative to browser URL | ❌ Fragile |
| `href="/users/detail"` | Hardcoded absolute path | ⚠️ Brittle |
| `this.router.link('/users/detail')` | Router-aware absolute path | ✅ Correct |

---

## If You Want Truly Relative Links (Nested Routers)

If you have a **nested router** mounted inside a parent, keep your routes expressed as **full absolute paths** in the route table, and use `router.link()` with the full path. `@lit-labs/router` does **not** support base-relative route resolution the way a framework like React Router does, so the safest pattern is always:

```js
// Always use full paths in route definitions
{ path: '/users/detail', render: ... }

// Always use router.link() with full paths for hrefs
html`<a href="${this.router.link('/users/detail')}">Detail</a>`
```

This keeps navigation predictable regardless of where the component is mounted in the DOM tree.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Use `this._routes.link('detail')` to build the href

Relative `<a href="detail">` won't work because the browser resolves it against the current document URL, not the router's matched prefix. The `Routes` controller exposes a `link()` method that prepends the parent's matched pathname for you.

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
      <nav>
        <!-- Resolves to "/users/detail" at runtime -->
        <a href=${this._routes.link('detail')}>Detail</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}
```

### How `link()` works

`link(localPath)` joins the parent route's matched prefix with your local path string. If the parent router matched `/users/`, the call above returns `/users/detail` — an absolute pathname the browser and the router both understand.

### Key rules to keep in mind

| Situation | What to write |
|-----------|---------------|
| Link to the index of this nested section | `this._routes.link('')` → `/users/` |
| Link to a child route | `this._routes.link('detail')` → `/users/detail` |
| Link to a parameterised child | `this._routes.link(`detail/${id}`)` → `/users/detail/42` |
| Link to a completely different top-level route | Plain `<a href="/other">` — no need for `link()` |

### Don't forget the parent mount needs a trailing slash

The parent `Router` must mount this section at `/users/*` (with the wildcard), and your nav links to the section should use `<a href="/users/">` — not `/users`. The trailing slash is what makes the `/*` pattern match and propagates the correct prefix to `link()`.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B directly recommends the `Routes.link()` helper as the correct solution, which is exactly what the question asks for and what the rubric prioritizes. Answer A only suggests hardcoding absolute paths or using `Router.go()` programmatically, completely missing the `link()` helper. Answer B also thoroughly explains why relative resolution doesn't work and how `link()` resolves paths relative to the parent route prefix.

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

The `@lit-labs/router` doesn't resolve relative paths the way you might expect in a traditional file system. The `href` attribute is interpreted by the browser as a regular URL, so `detail` would try to navigate to the current page's URL + `detail`, not relative to your router's mounted path.

## Alternative: Using Router Methods

If you want to avoid hardcoding paths, you can use the router's navigation methods programmatically:

```javascript
import { Router } from '@lit-labs/router';

// Navigate programmatically
Router.go('/users/detail');
```

Or if you have access to the router instance in your component, you could construct the path dynamically based on the current route context.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Building Parent-Relative Links in Nested Routes

When you're inside a nested `Routes` section, you **cannot** use relative `href` attributes like `<a href="detail">` — the browser will resolve them relative to the current page's `pathname`, not the parent route's matched prefix.

## The Solution: Use `Routes.link()`

Call `this._routes.link('local-path')` to build an absolute href that includes the parent's matched pathname:

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
      <!-- <a href="detail">Go to detail</a> -->

      <!-- ✅ Right: link() prepends the parent's matched pathname -->
      <a href="${this._routes.link('detail')}">Go to detail</a>
    `;
  }
}
```

If the parent `Router` matched `/users/*`, then:
- `this._routes.link('detail')` returns `'/users/detail'`
- `this._routes.link(':id')` returns `'/users/:id'` (literal; you'd interpolate the actual ID)
- `this._routes.link('')` returns `'/users/'` (the index)

## Full Example

```ts
// Parent router
@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/',        render: () => html`<home-page></home-page>`},
    {path: '/users/*', render: () => html`<users-section></users-section>`},
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

// Child with nested Routes
@customElement('users-section')
class UsersSection extends LitElement {
  private _routes = new Routes(this, [
    {path: '', render: () => html`<user-list></user-list>`},
    {path: ':id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() {
    return html`
      <nav>
        <!-- ✅ Correct: link() builds /users/... -->
        <a href="${this._routes.link('')}">List</a>
        <a href="${this._routes.link('123')}">User 123</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}

// Inside user-list component
@customElement('user-list')
class UserList extends LitElement {
  private _routes = new Routes(this, [
    {path: '', render: () => html`<div>Users</div>`},
  ]);

  render() {
    return html`
      <ul>
        <li><a href="${this._routes.link('42')}">User 42</a></li>
        <li><a href="${this._routes.link('99')}">User 99</a></li>
      </ul>
    `;
  }
}
```

## Why Not Just Use Absolute Paths?

You *can* hardcode absolute paths (`<a href="/users/detail">`), but `link()` is better because:
- **Refactoring-safe**: If you move the parent route from `/users/*` to `/admin/users/*`, only the parent changes; child links still work.
- **Composable**: Deeply nested routes can chain `link()` calls through multiple levels.
- **Explicit**: Makes it clear you're building a parent-relative path, not a global one.

## See Also

- [API: `Routes.link()`](references/api.md) — Full signature and algorithm
- [Navigation](references/navigation.md) — Active-link styling and click interception
- [Nested Routing](references/nested-routing.md) — How parent and child routes wire together

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly recommend the link() helper on the Routes controller and explain that it resolves relative to the parent route prefix. Answer A provides slightly more precise caveats (e.g., warning against './detail' paths and the 'Not implemented' error), while Answer B has a cleaner structure with headers and a TL;DR. Both are equally correct and useful for the question asked.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends link() helper | tie |
| explains relative resolution | tie |

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

# The Problem

Relative URLs in `<a href>` resolve against the current document URL, **not** the router's mount point. So `<a href="detail">` on `/users/` works, but on `/users/123` it resolves to `/users/detail` — and crucially, browsers also strip the trailing slash interpretation in unexpected ways depending on the path.

More importantly, in a **nested** router, your child router only knows about paths *relative to its mount point* (`/users/`). You need the link to produce the correct **absolute** URL.

# The Fix: use the parent router's `link()` method

`@lit-labs/router` exposes a `link(pathname)` method on the `Routes`/`Router` instance precisely for this. It resolves a path relative to the router's mount point and returns an absolute URL.

```js
import { LitElement, html } from 'lit';
import { Routes } from '@lit-labs/router';

class UsersView extends LitElement {
  // This nested Routes is mounted at /users/ by the parent router
  private _routes = new Routes(this, [
    { path: 'detail', render: () => html`<user-detail></user-detail>` },
    { path: ':id',    render: ({ id }) => html`<user-page .id=${id}></user-page>` },
  ]);

  render() {
    return html`
      <nav>
        <!-- ✅ Resolves to /users/detail regardless of current URL -->
        <a href=${this._routes.link('detail')}>Detail</a>

        <!-- ✅ You can also link to the router's own root -->
        <a href=${this._routes.link()}>Users home</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}
customElements.define('users-view', UsersView);
```

# Why this works

- `Routes#link(pathname?)` prepends the parent route's matched prefix (e.g. `/users/`) to the pathname you pass in.
- It returns a real absolute path, so the `<a href>` is unambiguous and works from any current URL.
- If you also want to intercept the click for SPA navigation (instead of a full page load), wire it through your router's navigation method — but `link()` is the canonical way to *compute* the href.

# TL;DR

Don't write `<a href="detail">`. Write:

```js
<a href=${this._routes.link('detail')}>Detail</a>
```

</details>

<details><summary>opus: skill-loaded answer</summary>

Use the child `Routes` controller's `link()` helper to build the href. It prepends the parent's matched pathname (the part before the tail group), so a relative local path resolves against the mount point rather than the current document URL.

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
      <nav>
        <a href=${this._routes.link('detail')}>Detail</a>
      </nav>
      ${this._routes.outlet()}
    `;
  }
}
```

`this._routes.link('detail')` returns `/users/detail`, which the root `Router`'s click handler will then intercept and SPA-navigate as usual.

A few notes:

- Pass a **local** path (no leading slash, no parent prefix) — `link()` adds the prefix for you.
- Calling `link()` with no argument returns just the parent prefix (useful for an "index" link back to `/users/`).
- Don't pass `'./detail'` or `'../foo'` — the current implementation throws "Not implemented" for paths starting with `.`.
- A bare `<a href="detail">` fails because the browser resolves it relative to the current document URL, not the route mount point — so from `/users/` you'd get `/users/detail` (accidentally correct), but from `/users/123` you'd get `/users/123/detail`. `link()` makes it correct from anywhere inside the section.

</details>

---

### `click-interception-rules`

**Prompt**

```
I have a @lit-labs/router app where most `<a href>` links work as
SPA navigation. But two of them aren't intercepted: one is
`<a href="/users/123" target="_blank">` and another is
`<a href="/external" rel="external">`. Why aren't they being
intercepted by the router?
```

**Judge focus:** The better answer enumerates the specific conditions Router uses
to decide *not* to intercept a click: `target` set, `rel="external"`,
`download` attribute, modifier keys held (cmd/ctrl/shift/alt),
or non-same-origin href. The router intentionally lets the browser
handle these because they're conventional opt-outs.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers cover the core criteria well, but Answer A provides a more comprehensive table of all bail-out conditions and includes a code snippet illustrating the router's internal logic, making it slightly more educational. Answer B is cleaner and more concise but covers the same rubric criteria. Both mention target, rel=external, modifier keys, and same-origin restriction, making them roughly equivalent on the rubric, though A's explicit table and internal code reference give it a slight edge.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| lists target attribute as an opt-out | tie |
| lists rel=external as an opt-out | tie |
| mentions modifier keys as a third opt-out | tie |
| mentions same-origin restriction | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| lists target attribute as an opt-out | ✓ | `target` |
| lists rel=external as an opt-out | ✓ | `rel="external"` |
| mentions modifier keys as a third opt-out | ✓ | `ctrl` |
| mentions same-origin restriction | ✓ | `external URL` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| lists target attribute as an opt-out | ✓ | `target` |
| lists rel=external as an opt-out | ✓ | `rel="external"` |
| mentions modifier keys as a third opt-out | ✓ | `modifier` |
| mentions same-origin restriction | ✓ | `Same-origin` |

<details><summary>sonnet: baseline answer</summary>

## Why Those Links Aren't Intercepted

`@lit-labs/router` uses a click handler that intentionally **skips certain links**. Looking at the source, it checks several conditions before intercepting a click and calling `History.pushState()`. Your two links each trip one of those bail-out conditions.

---

### Link 1: `target="_blank"`

```html
<a href="/users/123" target="_blank">
```

The router explicitly checks whether the anchor has a `target` attribute that is **not** `_self`:

```js
// Simplified from @lit-labs/router internals
if (anchor.target && anchor.target !== '_self') {
  return; // ← bail out, let the browser handle it
}
```

**Why?** `target="_blank"` means *"open in a new tab."* If the router intercepted it, it would do a same-page navigation instead — completely wrong behavior. So any non-`_self` target is left alone.

---

### Link 2: `rel="external"`

```html
<a href="/external" rel="external">
```

The router checks the `rel` attribute for the token `"external"`:

```js
if (anchor.rel === 'external') {
  return; // ← bail out, treat as a full page load
}
```

**Why?** `rel="external"` is a standard HTML signal meaning *"this link leads outside the current site/application."* The router respects that hint and lets the browser do a full navigation instead of a SPA transition.

---

### Full Set of Bail-Out Conditions (for reference)

The router skips interception when **any** of these are true:

| Condition | Reason |
|---|---|
| `anchor.target` is set and not `_self` | Opens in new tab/frame |
| `anchor.rel` contains `"external"` | Explicitly marked as external |
| `anchor.hasAttribute('download')` | It's a file download |
| `event.defaultPrevented` | Something else already handled it |
| `event.metaKey / ctrlKey / shiftKey` | User wants browser-native behavior (new tab, etc.) |
| Different origin (`anchor.origin !== location.origin`) | Truly external URL |

---

### Key Takeaway

Both behaviors are **intentional and correct**:

- Use `target="_blank"` → you *want* a new tab, not SPA nav ✓  
- Use `rel="external"` → you *want* a full page load ✓  

If you actually want the router to intercept these, you'd need to remove those attributes and handle the desired behavior differently (e.g., open a new tab programmatically inside a route handler).

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Both links are intentionally excluded by the router's click-interception rules.

`Router` intercepts a click only when **all** of these conditions are true:

- Same-origin URL
- No `target` attribute (or `target="_self"`)
- No modifier keys (Ctrl, Meta, Shift, Alt)
- No `download` attribute
- No `rel="external"`

Your two links each violate one of those conditions.

---

**`<a href="/users/123" target="_blank">`**

`target="_blank"` tells the browser to open the link in a new tab. The router sees a non-empty `target` and steps aside, letting the browser handle it natively. The page opens in a new tab and a full page load occurs there — the SPA in the original tab is unaffected.

Fix: remove `target="_blank"` if you want SPA navigation, or keep it if opening a new tab is the intended behaviour.

```html
<!-- SPA navigation -->
<a href="/users/123">User 123</a>

<!-- New tab (router won't intercept — intentional) -->
<a href="/users/123" target="_blank">Open in new tab</a>
```

---

**`<a href="/external" rel="external">`**

`rel="external"` is a semantic signal that the destination is outside the application, even if the URL happens to be same-origin. The router respects that signal and does not intercept the click, so the browser performs a full navigation.

Fix: remove `rel="external"` if the route is actually internal to your SPA.

```html
<!-- SPA navigation -->
<a href="/external">External-looking page</a>

<!-- Full navigation (router won't intercept — intentional) -->
<a href="/external" rel="external">Truly external page</a>
```

---

**Summary**

| Link | Why skipped | Fix |
|------|-------------|-----|
| `target="_blank"` | Non-empty `target` → browser opens new tab | Remove `target` for SPA nav |
| `rel="external"` | Explicit opt-out signal → full navigation | Remove `rel="external"` for SPA nav |

Both are deliberate escape hatches, not bugs. They give you a way to opt individual links out of SPA routing without any extra JavaScript.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B covers all four rubric criteria including modifier keys (Ctrl, Cmd, Shift, Alt) as an opt-out condition, while Answer A omits modifier keys entirely. Both answers cover target attribute, rel=external, and same-origin restriction, but B's explicit mention of modifier keys and more complete 'Full Click Interception Rules' section makes it the more thorough and accurate response.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| lists target attribute as an opt-out | tie |
| lists rel=external as an opt-out | tie |
| mentions modifier keys as a third opt-out | skill |
| mentions same-origin restriction | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| lists target attribute as an opt-out | ✓ | `target` |
| lists rel=external as an opt-out | ✓ | `rel="external"` |
| mentions modifier keys as a third opt-out | ✗ | |
| mentions same-origin restriction | ✓ | `Same origin` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| lists target attribute as an opt-out | ✓ | `target` |
| lists rel=external as an opt-out | ✓ | `rel="external"` |
| mentions modifier keys as a third opt-out | ✓ | `modifier` |
| mentions same-origin restriction | ✓ | `Same origin` |

<details><summary>haiku: baseline answer</summary>

# Why Those Links Aren't Being Intercepted

The `@lit-labs/router` doesn't intercept those links because they have explicit indicators that they should **not** be treated as SPA navigation:

## 1. `target="_blank"`

```html
<a href="/users/123" target="_blank">Open in new tab</a>
```

**Why it's not intercepted:** The `target="_blank"` attribute tells the browser to open the link in a new tab/window. The router correctly respects this and lets the browser handle it normally.

## 2. `rel="external"`

```html
<a href="/external" rel="external">External link</a>
```

**Why it's not intercepted:** The `rel="external"` attribute is a convention (often used with frameworks like Remix) that explicitly marks a link as external. The router checks for this and skips interception.

## How the Router Decides

The `@lit-labs/router` typically intercepts links based on these criteria:

- ✅ Same origin (same domain)
- ✅ No `target` attribute (or `target="_self"`)
- ✅ No `rel="external"` attribute
- ✅ No `download` attribute
- ❌ Different origin → not intercepted
- ❌ `target="_blank"`, `target="_parent"`, etc. → not intercepted
- ❌ `rel="external"` → not intercepted
- ❌ `download` attribute → not intercepted

This is the **correct behavior** — the router respects your intent when you explicitly specify these attributes.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Why Those Links Aren't Intercepted

The `Router` click handler has explicit rules for which links to intercept. Both of your links violate those rules:

## `<a href="/users/123" target="_blank">`

**Reason:** The `target="_blank"` attribute tells the browser to open the link in a new tab/window. The router **skips interception** for any link with a `target` attribute (other than `target="_self"`).

**Why:** If the user explicitly asks for a new tab, the router respects that intent and lets the browser handle the navigation natively.

**Fix:** Remove `target="_blank"` if you want SPA navigation:
```html
<a href="/users/123">User 123</a>
```

Or, if you genuinely need to open in a new tab, leave it as-is — that's the correct behavior.

---

## `<a href="/external" rel="external">`

**Reason:** The `rel="external"` attribute is a signal that this link points outside the app. The router **skips interception** for any link with `rel="external"`.

**Why:** This is a convention to mark links that should use full-page navigation (e.g., to a different domain or a truly external resource).

**Fix:** Remove `rel="external"` if you want SPA navigation:
```html
<a href="/external">External Page</a>
```

Or, if `/external` is genuinely an external URL (different origin), the `rel="external"` is correct and the browser will handle it natively.

---

## Full Click Interception Rules

The router intercepts a click **only if all** of these are true:

- ✅ Same origin (no protocol/host change)
- ✅ No `target` attribute (or `target="_self"`)
- ✅ No `download` attribute
- ✅ No `rel="external"`
- ✅ No modifier keys (Ctrl, Cmd, Shift, Alt)

If any rule is violated, the browser handles the navigation natively.

---

## Summary

| Link | Why Not Intercepted | Fix |
|------|---------------------|-----|
| `<a href="/users/123" target="_blank">` | `target="_blank"` opens a new tab | Remove `target="_blank"` for SPA nav |
| `<a href="/external" rel="external">` | `rel="external"` signals external link | Remove `rel="external"` for SPA nav |

Both behaviors are intentional — the router respects explicit user/author intent. If you want SPA navigation, remove those attributes.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly identify all four rubric criteria: target attribute, rel=external, modifier keys, and same-origin restriction. Answer A is slightly more concise and practical with its 'what to do' section, while Answer B provides better structure with headers and additional detail about non-http protocols and event.defaultPrevented. Both are equally accurate and complete on the core criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| lists target attribute as an opt-out | tie |
| lists rel=external as an opt-out | tie |
| mentions modifier keys as a third opt-out | tie |
| mentions same-origin restriction | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| lists target attribute as an opt-out | ✓ | `target` |
| lists rel=external as an opt-out | ✓ | `rel="external"` |
| mentions modifier keys as a third opt-out | ✓ | `modifier` |
| mentions same-origin restriction | ✓ | `cross-origin` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| lists target attribute as an opt-out | ✓ | `target` |
| lists rel=external as an opt-out | ✓ | `rel="external"` |
| mentions modifier keys as a third opt-out | ✓ | `modifier` |
| mentions same-origin restriction | ✓ | `Same-origin` |

<details><summary>opus: baseline answer</summary>

# Why those links aren't intercepted

`@lit-labs/router` (like most SPA routers built on top of the standard click-interception pattern) deliberately **skips** certain anchor elements so the browser's default behavior takes over. Two of the conditions it checks for are exactly the attributes you're using:

## 1. `target="_blank"` (or any non-`_self` target)

```html
<a href="/users/123" target="_blank">
```

When an anchor has a `target` attribute pointing somewhere other than the current frame (`_blank`, `_parent`, `_top`, or a named window), intercepting the click would break the user's expectation of opening a new tab/window. The router lets the browser handle it natively, which means a full page load occurs in the new tab.

## 2. `rel="external"`

```html
<a href="/external" rel="external">
```

The `rel="external"` attribute is the conventional way to tell tools (and SPA routers) "**don't treat this as an internal navigation**." Routers honor it as an explicit opt-out signal, so the click handler bails out and the browser performs a normal full-page navigation.

## Other conditions routers typically skip

For completeness, intercepted clicks are usually also skipped when:

- The link uses a different origin (cross-origin URL)
- The link uses a non-`http(s)` protocol (`mailto:`, `tel:`, etc.)
- The user held a modifier key (Ctrl/Cmd/Shift/Alt) — opens in new tab
- It's not a left-click (middle/right click)
- `event.defaultPrevented` is already true
- The anchor has `download` attribute

## How to fix it

If you actually want these to be SPA-navigated:

- **Remove `target="_blank"`** if you want in-place navigation. If you really need a new tab *and* SPA navigation, that's not possible — a new tab is a new document by definition.
- **Remove `rel="external"`** (or change it to something like `rel="noopener"` if that's what you actually wanted).

If your goal with `rel="external"` was just to add `noopener`/`noreferrer` for security, use those values instead — they don't disable router interception.

</details>

<details><summary>opus: skill-loaded answer</summary>

Both are working **as designed**. `@lit-labs/router`'s click interceptor deliberately bails out on links it considers "not in-app navigation" so the browser can do its normal thing.

The interceptor only handles a click when **all** of these are true:

- Same-origin link
- No `target` attribute (or `target=""`)
- No `download` attribute
- No `rel="external"`
- No modifier keys held (Ctrl/Cmd/Shift/Alt)
- Plain left-click

Your two links each violate one of these:

1. **`<a href="/users/123" target="_blank">`** — `target="_blank"` means "open in a new tab." If the router intercepted it and called `pushState` in the *current* tab, the user would lose their expected behavior. The browser handles it natively and opens a new tab.

2. **`<a href="/external" rel="external">`** — `rel="external"` is a conventional opt-out signaling "this is not part of the SPA, do a full page load." The router respects that hint and lets the browser navigate normally.

### What to do

**If you actually want SPA navigation for these:**

- Remove `target="_blank"` — or accept that opening in a new tab requires a full page load (the new tab has no router state anyway).
- Remove `rel="external"` — it's explicitly telling the router to stay out.

**If you want to keep `target="_blank"` AND have the new tab render the right route:**
That already works — the new tab loads your `index.html`, the `Router` boots fresh, reads `location.pathname`, and matches `/users/123`. Just make sure your server serves `index.html` for unknown paths (SPA fallback).

**If you want `rel="external"` semantics but still SPA-navigate:**
Drop `rel="external"` and use a different signal (e.g., a CSS class) for whatever styling/analytics need prompted it.

This is documented behavior, not a bug — see the click-interception rules in the navigation reference. The same list also explains why modifier-clicks (Ctrl+click to open in new tab) keep working as users expect.

</details>

---

### `active-link-styling`

**Prompt**

```
I want to highlight the current nav link in my @lit-labs/router app
based on the active route. Is there a built-in `activeLink`
directive or a route-changed event I can listen to?
```

**Judge focus:** The better answer states honestly that lit-router has NO built-in
active-link helper or route-change event — you read
`window.location.pathname` (or compare against the router's params
/ current route) at render time and apply your own active class.
It does not invent a directive that doesn't exist.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer A is more accurate and idiomatic: it correctly explains that the router's own requestUpdate() mechanism makes render() re-run automatically, so you can simply read location.pathname at render time without adding extra event listeners. Answer B introduces unnecessary complexity by adding manual popstate and click listeners on window, which duplicates what the router already handles internally. Answer A avoids inventing non-existent APIs and gives a cleaner, more correct explanation of why the pattern works.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states there is no built-in helper | tie |
| recommends reading location.pathname or router state | skill |
| applies class at render time | skill |
| avoids inventing an activeLink directive | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states there is no built-in helper | ✓ | `no built-in` |
| recommends reading location.pathname or router state | ✓ | `location.pathname` |
| applies class at render time | ✓ | `classMap` |
| avoids inventing an activeLink directive | ✗ | `activeLink` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states there is no built-in helper | ✓ | `no built-in` |
| recommends reading location.pathname or router state | ✓ | `location.pathname` |
| applies class at render time | ✓ | `class=${` |
| avoids inventing an activeLink directive | ✗ | `active-link directive` |

<details><summary>sonnet: baseline answer</summary>

## Highlighting Active Nav Links in `@lit-labs/router`

There's **no built-in `activeLink` directive or route-changed event** in `@lit-labs/router`. You'll need to implement this yourself. Here are the best approaches:

---

### Option 1: Reactive Property + `Router` Subscription (Recommended)

```typescript
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Router } from '@lit-labs/router';

@customElement('my-nav')
export class MyNav extends LitElement {
  static styles = css`
    a { color: inherit; text-decoration: none; }
    a.active { color: blue; font-weight: bold; }
  `;

  private router = new Router(this, [
    { path: '/',        render: () => html`<home-page></home-page>` },
    { path: '/about',  render: () => html`<about-page></about-page>` },
    { path: '/contact',render: () => html`<contact-page></contact-page>` },
  ]);

  // Track current path reactively
  @state() private currentPath = window.location.pathname;

  connectedCallback() {
    super.connectedCallback();
    // Listen for popstate (back/forward navigation)
    window.addEventListener('popstate', this._onPopState);
    // Intercept link clicks for client-side navigation
    window.addEventListener('click', this._onLinkClick);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('popstate', this._onPopState);
    window.removeEventListener('click', this._onLinkClick);
  }

  private _onPopState = () => {
    this.currentPath = window.location.pathname;
  };

  private _onLinkClick = (e: MouseEvent) => {
    const anchor = (e.composedPath() as Element[])
      .find((el) => el.tagName === 'A') as HTMLAnchorElement | undefined;

    if (anchor?.href && anchor.origin === window.location.origin) {
      // Update after the router has processed the click
      requestAnimationFrame(() => {
        this.currentPath = window.location.pathname;
      });
    }
  };

  private _isActive(path: string) {
    return this.currentPath === path;
  }

  render() {
    return html`
      <nav>
        <a href="/"        class=${this._isActive('/')         ? 'active' : ''}>Home</a>
        <a href="/about"   class=${this._isActive('/about')    ? 'active' : ''}>About</a>
        <a href="/contact" class=${this._isActive('/contact')  ? 'active' : ''}>Contact</a>
      </nav>
      <main>${this.router.outlet()}</main>
    `;
  }
}
```

---

### Option 2: `classMap` + Helper for Cleaner Templates

```typescript
import { classMap } from 'lit/directives/class-map.js';

// Reusable helper
private _linkClasses(path: string) {
  return classMap({
    active: this.currentPath === path,
    // Add prefix matching for nested routes:
    'active-parent': this.currentPath.startsWith(path) && path !== '/',
  });
}

render() {
  return html`
    <nav>
      <a href="/"       class=${this._linkClasses('/')}>Home</a>
      <a href="/about"  class=${this._linkClasses('/about')}>About</a>
    </nav>
    <main>${this.router.outlet()}</main>
  `;
}
```

---

### Option 3: Reusable `nav-link` Component

```typescript
@customElement('nav-link')
export class NavLink extends LitElement {
  static styles = css`
    :host { display: inline-block; }
    a { color: inherit; }
    a[aria-current='page'] { font-weight: bold; color: blue; }
  `;

  @property() href = '';
  @property() label = '';
  @state() private currentPath = window.location.pathname;

  private _onPopState = () => { this.currentPath = window.location.pathname; };

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('popstate', this._onPopState);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('popstate', this._onPopState);
  }

  render() {
    const isActive = this.currentPath === this.href;
    return html`
      <a
        href=${this.href}
        aria-current=${isActive ? 'page' : nothing}
      >${this.label}</a>
    `;
  }
}

// Usage:
html`
  <nav>
    <nav-link href="/"       label="Home"></nav-link>
    <nav-link href="/about"  label="About"></nav-link>
    <nav-link href="/contact"label="Contact"></nav-link>
  </nav>
`
```

---

### Key Points

| Concern | Solution |
|---|---|
| Back/forward buttons | Listen to `popstate` |
| Client-side link clicks | Listen to `click` on `window` |
| Nested route matching | Use `startsWith()` instead of `===` |
| Accessibility | Use `aria-current="page"` on active links |
| No built-in event | `@lit-labs/router` has no `routeChanged` event (as of v0.1.x) |

> **Tip:** Using `aria-current="page"` is the accessible standard for active links and can also be your CSS hook (`a[aria-current="page"] { ... }`), avoiding a separate `.active` class entirely.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

No — `@lit-labs/router` has no built-in active-link directive and fires no "route changed" event. But you don't need either one, because the router already calls `requestUpdate()` on the host element after every successful navigation. That means your `render()` re-runs automatically, and you can compute the active class right there.

## The pattern

```ts
import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';
import { Router } from '@lit-labs/router';

@customElement('my-app')
class MyApp extends LitElement {
  static styles = css`
    a { color: inherit; text-decoration: none; }
    a.active { font-weight: bold; border-bottom: 2px solid currentColor; }
  `;

  private _router = new Router(this, [
    { path: '/',         render: () => html`<home-page></home-page>` },
    { path: '/about',    render: () => html`<about-page></about-page>` },
    { path: '/users/*',  render: () => html`<users-section></users-section>` },
  ], { fallback: { render: () => html`<not-found-page></not-found-page>` } });

  // Exact match — use for top-level leaf routes
  private _isActive(href: string) {
    return location.pathname === href ? 'active' : '';
  }

  // Prefix match — use for routes that own a whole subtree
  private _isActiveSection(prefix: string) {
    return location.pathname.startsWith(prefix) ? 'active' : '';
  }

  render() {
    return html`
      <nav>
        <a href="/"       class=${this._isActive('/')}>Home</a>
        <a href="/about"  class=${this._isActive('/about')}>About</a>
        <a href="/users/" class=${this._isActiveSection('/users/')}>Users</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

## Why this works without any extra machinery

| What happens | Why it triggers a re-render |
|---|---|
| User clicks an `<a href>` | `Router` intercepts the click, calls `goto()`, which calls `this.host.requestUpdate()` |
| `history.pushState` + `router.goto(path)` | Same — `goto()` always calls `requestUpdate()` |
| Browser back/forward button | `Router` listens to `popstate` and calls `goto()` → `requestUpdate()` |

Because `render()` re-runs, `location.pathname` is always fresh when the helpers are called.

## A note on the trailing slash for nested routes

Notice `/users/` (with trailing slash) in both the `href` and the `startsWith` check. The `/*` wildcard in the router only matches when there is a slash after the prefix — `/users` alone won't match `/users/*`. Keep the trailing slash consistent everywhere to avoid a subtle mismatch.

## If you need this in multiple components

Extract the helpers into a small shared utility rather than duplicating them:

```ts
// nav-helpers.ts
export const isActive        = (href: string)   => location.pathname === href ? 'active' : '';
export const isActiveSection = (prefix: string) => location.pathname.startsWith(prefix) ? 'active' : '';
```

Then import and call them directly inside any component's `render()`. No event bus, no context, no extra state — the router's own `requestUpdate()` call keeps everything in sync.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly states there is no built-in activeLink directive and no route-change event, explaining that the router calls requestUpdate() automatically. Answer B invents a 'router-location-changed' event that doesn't exist in @lit-labs/router and recommends it as the 'most reliable' approach, which is factually wrong and misleading. Answer B also creates a custom activeLink directive, which the rubric explicitly penalizes.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states there is no built-in helper | skill |
| recommends reading location.pathname or router state | skill |
| applies class at render time | skill |
| avoids inventing an activeLink directive | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states there is no built-in helper | ✓ | `doesn't have` |
| recommends reading location.pathname or router state | ✓ | `location.pathname` |
| applies class at render time | ✓ | `class=${` |
| avoids inventing an activeLink directive | ✗ | `activeLink` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states there is no built-in helper | ✓ | `no built-in` |
| recommends reading location.pathname or router state | ✓ | `location.pathname` |
| applies class at render time | ✓ | `class=${` |
| avoids inventing an activeLink directive | ✗ | `activeLink` |

<details><summary>haiku: baseline answer</summary>

# Highlighting Active Links in @lit-labs/router

The `@lit-labs/router` doesn't have a built-in `activeLink` directive, but you can achieve this by listening to route changes and comparing the current route. Here are the best approaches:

## 1. Using `router-location-changed` Event (Recommended)

Listen to the `router-location-changed` event on the router element:

```typescript
import { LitElement, html, css } from 'lit';
import { Router } from '@lit-labs/router';

class MyApp extends LitElement {
  @property() currentPath = '';

  firstUpdated() {
    const router = this.shadowRoot?.querySelector('lit-router');
    router?.addEventListener('router-location-changed', (e: any) => {
      this.currentPath = e.detail.pathname;
    });
  }

  render() {
    return html`
      <nav>
        <a href="/" class=${this.isActive('/') ? 'active' : ''}>Home</a>
        <a href="/about" class=${this.isActive('/about') ? 'active' : ''}>About</a>
        <a href="/contact" class=${this.isActive('/contact') ? 'active' : ''}>Contact</a>
      </nav>
      <lit-router></lit-router>
    `;
  }

  private isActive(path: string): boolean {
    return this.currentPath === path;
  }

  static styles = css`
    a.active {
      font-weight: bold;
      color: #0066cc;
      border-bottom: 2px solid #0066cc;
    }
  `;
}
```

## 2. Using `window.location.pathname`

Simpler approach without event listeners:

```typescript
render() {
  const currentPath = window.location.pathname;
  
  return html`
    <nav>
      <a href="/" class=${currentPath === '/' ? 'active' : ''}>Home</a>
      <a href="/about" class=${currentPath === '/about' ? 'active' : ''}>About</a>
    </nav>
  `;
}
```

## 3. Create a Reusable Active Link Directive

```typescript
import { Directive, directive } from 'lit/directive.js';

class ActiveLinkDirective extends Directive {
  render(href: string) {
    const isActive = window.location.pathname === href;
    return isActive ? 'active' : '';
  }
}

export const activeLink = directive(ActiveLinkDirective);

// Usage:
html`<a href="/about" class=${activeLink('/about')}>About</a>`
```

## 4. With Route Pattern Matching

For nested routes, use pattern matching:

```typescript
private isActive(path: string): boolean {
  const current = window.location.pathname;
  return current.startsWith(path) && (path === '/' || current === path);
}
```

**The event-based approach (#1) is most reliable** as it updates whenever the router navigates, while `window.location.pathname` works but won't update reactively if you're using client-side routing without full page reloads.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Active Link Highlighting in @lit-labs/router

There is **no built-in `activeLink` directive** and **no global route-changed event**. However, active-link styling is straightforward: read `location.pathname` or `this._router.params` inside `render()`, and the router will call `requestUpdate()` on every successful navigation.

## Simple Pattern: Compare `location.pathname`

```ts
import {LitElement, html, css} from 'lit';
import {customElement} from 'lit/decorators.js';
import {Router} from '@lit-labs/router';

@customElement('my-app')
class MyApp extends LitElement {
  static styles = css`
    a.active { font-weight: bold; color: #0066cc; }
  `;

  private _router = new Router(this, [
    {path: '/', render: () => html`<home-page></home-page>`},
    {path: '/users', render: () => html`<users-page></users-page>`},
    {path: '/about', render: () => html`<about-page></about-page>`},
  ]);

  private _isActive(href: string) {
    return location.pathname === href ? 'active' : '';
  }

  render() {
    return html`
      <nav>
        <a href="/" class=${this._isActive('/')}>Home</a>
        <a href="/users" class=${this._isActive('/users')}>Users</a>
        <a href="/about" class=${this._isActive('/about')}>About</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

## Hierarchical Matching: Prefix Check

For nested routes where you want `/users` to highlight when visiting `/users/123`:

```ts
private _isActive(prefix: string) {
  const path = location.pathname;
  return path === prefix || path.startsWith(prefix + '/') ? 'active' : '';
}

render() {
  return html`
    <nav>
      <a href="/" class=${this._isActive('/')}>Home</a>
      <a href="/users" class=${this._isActive('/users')}>Users</a>
    </nav>
    ${this._router.outlet()}
  `;
}
```

## Using Route Params

If you prefer to read `this._router.params` instead of `location.pathname`:

```ts
private _router = new Router(this, [
  {path: '/', render: () => html`<home-page></home-page>`},
  {path: '/users/:id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
]);

private _isActive(routePath: string) {
  // Simple exact match on the route definition
  return location.pathname === routePath ? 'active' : '';
}
```

**Note:** `this._router.params` contains only the matched parameters (e.g. `{id: '123'}`), not the full path, so `location.pathname` is usually more convenient for active-link logic.

## Why No Built-in Helper?

- **No directive:** `@lit-labs/router` has no template directives — it uses `controller.outlet()` instead. Active-link logic is simple enough to inline.
- **No event:** The router calls `requestUpdate()` on the host after every navigation, so `render()` runs automatically. A separate event would be redundant.
- **Flexibility:** Different apps need different matching rules (exact, prefix, regex, etc.), so a one-size-fits-all helper would be limiting.

## Per-Route Side Effects

If you need to run logic *whenever* a specific route is entered (e.g., analytics, scroll-to-top), use the route's `enter` callback instead of watching for a global event:

```ts
private _router = new Router(this, [
  {
    path: '/users/:id',
    enter: async ({id}) => {
      // This runs every time this route is entered
      window.scrollTo(0, 0);
      await trackPageView(`/users/${id}`);
    },
    render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
  },
]);
```

This is more efficient and scoped than a global listener.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **baseline** — Both answers correctly state there is no built-in activeLink directive or route-change event. However, Answer B is more accurate by referencing `currentPathname` (an actual property on the Routes controller) rather than relying solely on `window.location.pathname`, making it more idiomatic to the library. Answer B also avoids inventing non-existent APIs while providing practical patterns. Answer A contains a factual error claiming `goto()` alone won't update the URL bar, which is incorrect — `goto()` does update the URL via history.pushState internally.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states there is no built-in helper | tie |
| recommends reading location.pathname or router state | baseline |
| applies class at render time | tie |
| avoids inventing an activeLink directive | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states there is no built-in helper | ✓ | `no directive` |
| recommends reading location.pathname or router state | ✓ | `currentPath` |
| applies class at render time | ✓ | `class=${` |
| avoids inventing an activeLink directive | ✗ | `activeLink` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| states there is no built-in helper | ✓ | `no built-in` |
| recommends reading location.pathname or router state | ✓ | `location.pathname` |
| applies class at render time | ✓ | `classMap` |
| avoids inventing an activeLink directive | ✗ | `activeLink` |

<details><summary>opus: baseline answer</summary>

Short answer: **No.** `@lit-labs/router` doesn't ship an `activeLink` directive, and it doesn't dispatch a `route-changed` event either. It's intentionally minimal — basically just a `Routes`/`Router` controller that resolves a pathname to a template.

Here's what you actually have to work with and the common patterns people use.

## What the router gives you

A `Routes` controller exposes:

- `routes` – the route config array
- `outlet()` – renders the matched route's template
- `goto(pathname)` – programmatic navigation
- `currentPathname` – the currently matched pathname (this is the key one for highlighting)

There's no event, no observable, no directive for active links.

## Pattern 1: Compare against `currentPathname`

Since `Routes` is a reactive controller, the host re-renders when navigation happens. You can just compare in your template:

```js
import { LitElement, html, css } from 'lit';
import { Routes } from '@lit-labs/router';

class MyNav extends LitElement {
  static styles = css`
    a.active { font-weight: bold; color: tomato; }
  `;

  #routes = new Routes(this, [
    { path: '/', render: () => html`<h1>Home</h1>` },
    { path: '/about', render: () => html`<h1>About</h1>` },
    { path: '/contact', render: () => html`<h1>Contact</h1>` },
  ]);

  #link(path, label) {
    const active = this.#routes.currentPathname === path;
    return html`
      <a href=${path}
         class=${active ? 'active' : ''}
         @click=${(e) => { e.preventDefault(); this.#routes.goto(path); }}>
        ${label}
      </a>`;
  }

  render() {
    return html`
      <nav>
        ${this.#link('/', 'Home')}
        ${this.#link('/about', 'About')}
        ${this.#link('/contact', 'Contact')}
      </nav>
      ${this.#routes.outlet()}
    `;
  }
}
customElements.define('my-nav', MyNav);
```

## Pattern 2: Listen to history changes yourself

If you need to react outside the router host (e.g., a sibling nav component), wire up `popstate` plus a wrapper around `pushState`:

```js
window.addEventListener('popstate', () => this.requestUpdate());
```

For `pushState`/`replaceState` you'd need to monkey-patch them or call `requestUpdate()` after your own `goto()` calls, since the History API doesn't fire events for programmatic changes.

## Pattern 3: A small `active-link` component

If you have lots of nav links, encapsulate the comparison:

```js
class ActiveLink extends LitElement {
  static properties = { href: {}, current: {} };
  render() {
    const active = this.current === this.href;
    return html`<a href=${this.href} class=${active ? 'active' : ''}><slot></slot></a>`;
  }
}
```

Then `<active-link href="/about" .current=${this.#routes.currentPathname}>About</active-link>`.

## TL;DR

Use `routes.currentPathname` and lean on the controller's automatic re-render. That's the idiomatic approach until/unless the labs package adds something more ergonomic.

</details>

<details><summary>opus: skill-loaded answer</summary>

Short answer: **no built-in `activeLink` directive and no route-changed event.** `@lit-labs/router` deliberately keeps its API surface tiny — it gives you `Router`/`Routes` controllers, `outlet()`, `goto()`, `link()`, and `params`. That's it.

But you don't need either, because the router calls `requestUpdate()` on the host element after every successful navigation. That means your `render()` runs again on every route change, and you can just read the current pathname (or the router's `params`) inline.

## The pattern

```ts
import {LitElement, html, css} from 'lit';
import {customElement} from 'lit/decorators.js';
import {classMap} from 'lit/directives/class-map.js';
import {Router} from '@lit-labs/router';

@customElement('my-app')
class MyApp extends LitElement {
  static styles = css`
    a.active { font-weight: bold; color: tomato; }
  `;

  private _router = new Router(this, [
    {path: '/',         render: () => html`<home-page></home-page>`},
    {path: '/users/*',  render: () => html`<users-section></users-section>`},
    {path: '/about',    render: () => html`<about-page></about-page>`},
  ]);

  // Exact match
  private _isActive(href: string) {
    return location.pathname === href;
  }

  // Hierarchical match (any sub-route of /users/)
  private _isActiveSection(prefix: string) {
    return location.pathname.startsWith(prefix);
  }

  render() {
    return html`
      <nav>
        <a href="/"        class=${classMap({active: this._isActive('/')})}>Home</a>
        <a href="/users/"  class=${classMap({active: this._isActiveSection('/users/')})}>Users</a>
        <a href="/about"   class=${classMap({active: this._isActive('/about')})}>About</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

## Why this works

- The router calls `requestUpdate()` on its host after every successful `goto()`, so `render()` re-runs on each navigation — no event subscription needed.
- Click interception on `<a href>` triggers `goto()` automatically (for same-origin links with no `target`, no modifier keys).
- `location.pathname` is the source of truth the router itself matches against.

## A couple of gotchas worth knowing

1. **Use `/users/` (trailing slash)** in both the `href` and the `startsWith` check when the parent route is `/users/*`. The pattern `/users/*` does *not* match bare `/users`.
2. **If you navigate programmatically**, always pair `history.pushState` with `router.goto` — `goto()` alone won't update the URL bar, which would leave your active-link logic out of sync:
   ```ts
   history.pushState({}, '', '/users/');
   this._router.goto('/users/');
   ```
3. **For deeply nested sections**, you can also read `this._router.params` if you'd rather match on a route param than a pathname prefix.

Note: `@lit-labs/router` is still **Lit Labs** (currently `0.1.4`), so this minimal API surface may grow before 1.0 — but for now, the inline `location.pathname` check is the idiomatic answer.

</details>

---

### `enter-vs-task-data-loading`

**Prompt**

```
My @lit-labs/router route renders a UserDetail component that needs
to fetch user data based on a route param. Should I do the fetch in
the route's `enter` callback or with `@lit/task` inside the
component? What's the tradeoff?
```

**Judge focus:** The better answer explains the two options as different shapes:
`enter` is awaited by the router and BLOCKS the route update until
it resolves (no UI until data is ready, no per-component loading
state); `@lit/task` runs inside the component, gives you status
states (pending/complete/error) for loading UI, and supports
cancellation via AbortSignal so a second navigation cancels the
first fetch. Picks based on whether the user wants a blocking
preload or a component-local loading experience.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all four rubric criteria thoroughly. Answer A provides slightly more depth on the race condition problem with `enter` and includes a concrete code example of the manual guard workaround, while Answer B's comparison table is slightly cleaner and more explicit about the AbortController/signal integration. Both explicitly name `@lit/task`, explain that `enter` blocks the route update, describe Task's status states, and address cancellation via AbortSignal. The quality is essentially equivalent.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains enter blocks the route update | tie |
| mentions Task gives status / loading state | tie |
| mentions cancellation / race-safety with Task | skill |
| names @lit/task explicitly | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains enter blocks the route update | ✓ | `block` |
| mentions Task gives status / loading state | ✓ | `pending` |
| mentions cancellation / race-safety with Task | ✓ | `cancel` |
| names @lit/task explicitly | ✓ | `@lit/task` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains enter blocks the route update | ✓ | `block` |
| mentions Task gives status / loading state | ✓ | `pending` |
| mentions cancellation / race-safety with Task | ✓ | `cancel` |
| names @lit/task explicitly | ✓ | `@lit/task` |

<details><summary>sonnet: baseline answer</summary>

## Route `enter` Callback vs `@lit/task` Inside the Component

Both approaches work, but they have meaningfully different characteristics. Here's a thorough breakdown:

---

## Option 1: Fetch in the Route's `enter` Callback

```javascript
import { Router } from '@lit-labs/router';

class MyApp extends LitElement {
  private router = new Router(this, [
    {
      path: '/users/:id',
      render: ({ id }) => html`<user-detail .user=${this._user}></user-detail>`,
      enter: async ({ id }) => {
        // Fetch BEFORE the component renders
        this._user = await fetchUser(id);
        this.requestUpdate();
        return true; // must return true to allow navigation
      },
    },
  ]);
}
```

### What you get
- Component receives data **on first render** — no loading state needed inside `UserDetail`
- Navigation is **blocked** until the fetch resolves
- `UserDetail` can be a purely presentational component with no async logic
- Easy to handle fetch failure by returning `false` to cancel navigation

### Problems
- **Navigation feels frozen** — the URL may not update and the user gets no feedback during the fetch
- Error handling lives **outside** the component that displays the error
- If the user navigates away mid-fetch, you need manual abort logic
- Harder to show a skeleton/loading UI during the transition
- The parent (`MyApp`) accumulates data-fetching concerns for every route

---

## Option 2: Fetch with `@lit/task` Inside the Component

```javascript
import { Task } from '@lit/task';

class UserDetail extends LitElement {
  @property() userId: string = '';

  private _userTask = new Task(this, {
    // Re-runs automatically when userId changes
    args: () => [this.userId] as const,
    task: async ([id], { signal }) => {
      const response = await fetch(`/api/users/${id}`, { signal });
      if (!response.ok) throw new Error('User not found');
      return response.json();
    },
  });

  render() {
    return this._userTask.render({
      pending: () => html`<loading-spinner></loading-spinner>`,
      complete: (user) => html`
        <h1>${user.name}</h1>
        <p>${user.email}</p>
      `,
      error: (e) => html`<error-message .message=${e.message}></error-message>`,
    });
  }
}
```

```javascript
// Route stays simple — just passes the param
{
  path: '/users/:id',
  render: ({ id }) => html`<user-detail .userId=${id}></user-detail>`,
}
```

### What you get
- **Navigation is instant** — the component mounts immediately and fetches in parallel
- Built-in `pending` / `complete` / `error` states with clean rendering
- The `signal` parameter gives you **automatic AbortController** integration — fetch cancels if `userId` changes or component disconnects
- Task **re-runs automatically** if `userId` changes (e.g., navigating `/users/1` → `/users/2`)
- Data-fetching logic is **colocated** with the component that uses it
- Easier to test `UserDetail` in isolation

### Problems
- Users see a loading state on every navigation (though this is often desirable)
- If you need the data to exist **before** committing to the navigation (e.g., redirect to 404 if user doesn't exist), you can't do that here without extra coordination

---

## Side-by-Side Comparison

| Concern | `enter` callback | `@lit/task` |
|---|---|---|
| First render has data | ✅ Yes | ❌ No (pending state) |
| Navigation blocked | ⚠️ Yes (feels frozen) | ✅ No |
| Loading UI | ❌ Hard | ✅ Built-in |
| Error UI | ❌ Must handle externally | ✅ Built-in |
| Auto-cancel on nav away | ❌ Manual | ✅ Via `signal` |
| Redirect on 404 | ✅ Return `false` | ❌ Needs workaround |
| Component is self-contained | ❌ No | ✅ Yes |
| Re-fetches on param change | ❌ Only on full navigation | ✅ Automatic |

---

## Recommendation

**Default to `@lit/task` inside the component.** It's more resilient, self-contained, and handles the real-world cases (loading, error, cancellation) with much less boilerplate.

**Use `enter` only when you have a specific need:**

```javascript
// Good use case for enter: guard/redirect if resource doesn't exist
enter: async ({ id }) => {
  const exists = await checkUserExists(id);
  if (!exists) {
    router.goto('/404');
    return false; // cancel navigation
  }
  return true;
}
```

You can also **combine both** — use `enter` for auth/existence guards and `@lit/task` for the actual data fetch inside the component.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Both approaches work, and the right choice depends on whether you want a **loading-free render** or **component-local loading state**. Here's the full breakdown.

---

## The two patterns

### Option A — `enter` callback (blocking preload)

```ts
// In the router config
{
  path: '/users/:id',
  enter: async ({id}) => {
    // Router awaits this before updating params and re-rendering
    currentUser = await fetchUser(id!);
    return true; // false would cancel the navigation
  },
  render: ({id}) => html`<user-detail .user=${currentUser}></user-detail>`,
}
```

The router **awaits `enter` before calling `render`**, so `<user-detail>` is never mounted with stale or missing data. The old route stays visible while the fetch runs.

### Option B — `@lit/task` inside the component

```ts
// Route config — no enter, just render
{
  path: '/users/:id',
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}

// Inside UserDetail
class UserDetail extends LitElement {
  @property() id!: string;

  private _userTask = new Task(this, {
    args: () => [this.id] as const,
    task: async ([id], {signal}) => fetchUser(id, signal),
  });

  render() {
    return this._userTask.render({
      pending: () => html`<loading-spinner></loading-spinner>`,
      complete: (user) => html`<h1>${user.name}</h1>`,
      error: (e) => html`<error-message .err=${e}></error-message>`,
    });
  }
}
```

The component mounts immediately and manages its own loading/error/complete states. The `signal` arg gives you automatic fetch cancellation when `id` changes mid-flight.

---

## Tradeoff table

| Concern | `enter` callback | `@lit/task` |
|---|---|---|
| **Loading state** | Old route stays visible (no spinner) | Component shows pending UI |
| **Error handling** | Must catch in `enter` or cancel nav | Built-in `error` render state |
| **Cancellation** | None — a second `goto()` mid-fetch is a race | `AbortSignal` passed automatically |
| **Reuse** | Data lives outside the component | Data lives inside; component is self-contained |
| **Testability** | Requires router setup to test | Component testable in isolation |
| **Stale data on back/forward** | Re-runs `enter` on every navigation | Re-runs task when `id` prop changes |
| **Skeleton / optimistic UI** | Hard — nothing renders until fetch completes | Natural — render partial UI immediately |

---

## The race condition `enter` doesn't solve

`@lit-labs/router` has no built-in cancellation token for `enter`. If the user navigates twice quickly:

```ts
enter: async ({id}) => {
  currentUser = await fetchUser(id!); // ← first fetch
  // second navigation fires here; currentUser gets overwritten
  // by whichever fetch resolves last, not whichever fired last
}
```

You'd have to roll your own guard:

```ts
let currentFetchId = 0;
enter: async ({id}) => {
  const fetchId = ++currentFetchId;
  const user = await fetchUser(id!);
  if (fetchId !== currentFetchId) return false; // stale, cancel
  currentUser = user;
}
```

`@lit/task` handles this for you via the `AbortSignal`.

---

## Recommendation

**Use `@lit/task` inside the component** as the default. It's self-contained, testable, handles errors and cancellation, and lets you show meaningful loading UI. The component works correctly whether it's reached via the router, rendered in a test, or embedded somewhere else.

**Reach for `enter`** in two specific cases:

1. **You must guarantee no flash of empty content** — e.g. a document editor where rendering an empty shell would be jarring or cause layout shift.
2. **The fetch result gates whether the navigation should happen at all** — e.g. a permission check where `return false` redirects unauthenticated users.

```ts
// enter as a guard, not a data loader
enter: async ({id}) => {
  const allowed = await checkPermission(id!);
  if (!allowed) {
    history.pushState({}, '', '/login');
    this._router.goto('/login');
    return false;
  }
  // let the component load its own data
  return true;
}
```

That keeps `enter` focused on navigation decisions and leaves data loading to the component where it belongs.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more complete and technically precise across all rubric criteria. It explicitly explains that `enter` blocks the route update (navigation doesn't proceed until the promise resolves), clearly names `@lit/task` with proper status states, and specifically calls out Task's built-in cancellation via abort signal for race safety. Answer A covers the basics but misses the cancellation/race-condition aspect entirely and is less precise about the blocking nature of `enter`.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains enter blocks the route update | skill |
| mentions Task gives status / loading state | tie |
| mentions cancellation / race-safety with Task | skill |
| names @lit/task explicitly | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains enter blocks the route update | ✓ | `before* component render` |
| mentions Task gives status / loading state | ✓ | `pending` |
| mentions cancellation / race-safety with Task | ✗ | |
| names @lit/task explicitly | ✓ | `@lit/task` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains enter blocks the route update | ✓ | `Block` |
| mentions Task gives status / loading state | ✓ | `pending` |
| mentions cancellation / race-safety with Task | ✓ | `cancel` |
| names @lit/task explicitly | ✓ | `@lit/task` |

<details><summary>haiku: baseline answer</summary>

# Route `enter` vs `@lit/task` for Data Fetching

Both approaches work, but they have different tradeoffs:

## Route `enter` Callback

```typescript
// In your router config
{
  path: '/user/:id',
  component: 'user-detail',
  enter: async (params) => {
    const data = await fetchUser(params.id);
    return { userData: data };
  }
}

// In UserDetail component
@customElement('user-detail')
class UserDetail extends LitElement {
  @property() userData?: User;
  
  render() {
    return html`<div>${this.userData?.name}</div>`;
  }
}
```

**Pros:**
- Data fetches *before* component renders (no loading state needed)
- Cleaner component code
- Can prevent navigation if fetch fails

**Cons:**
- Harder to handle refetches or user-triggered updates
- Less flexible for complex loading/error states
- Couples data fetching to routing logic

## `@lit/task` Inside Component

```typescript
@customElement('user-detail')
class UserDetail extends LitElement {
  @property() userId?: string;
  
  userTask = new Task(this, {
    task: async ([id]) => {
      if (!id) return null;
      return fetchUser(id);
    },
    args: () => [this.userId]
  });

  render() {
    return this.userTask.render({
      pending: () => html`<p>Loading...</p>`,
      complete: (user) => html`<div>${user.name}</div>`,
      error: (e) => html`<p>Error: ${e.message}</p>`
    });
  }
}
```

**Pros:**
- Handles loading/error/retry states elegantly
- Easy to refetch or update data
- Component is self-contained and reusable
- Better for complex async flows

**Cons:**
- Component renders before data arrives (need loading UI)
- More boilerplate code

## Recommendation

**Use `@lit/task`** in most cases because:
- Modern Lit pattern
- Better separation of concerns
- More flexible for real-world scenarios (refetch, polling, dependent requests)
- Loading states are expected in modern UX

Use route `enter` only if you need to **prevent navigation** on fetch failure or want a fully-loaded page before rendering.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# `enter` vs `@lit/task` for Route Data Loading

Both approaches work; the choice depends on your UX and error-handling needs.

## `enter` Callback (Full-Page Blocking)

```ts
// In Router config
{
  path: '/users/:id',
  enter: async ({id}) => {
    const res = await fetch(`/api/users/${id}`);
    if (!res.ok) throw new Error('User not found');
    // Data is now loaded; router proceeds to render
  },
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}
```

**Tradeoffs:**
- ✅ **Blocks navigation** — page doesn't render until data arrives; no loading spinner in the component
- ✅ **Centralized error handling** — throw in `enter`, catch at router level (or let it bubble)
- ✅ **Simple component** — `UserDetail` receives `id` and assumes data is ready
- ❌ **Slower perceived UX** — user sees a blank page while fetching
- ❌ **No cancellation** — if a second `goto()` fires mid-fetch, the first result still lands (race condition risk)
- ❌ **Tight coupling** — router knows about data dependencies

## `@lit/task` Inside Component (Non-Blocking)

```ts
// In Router config
{
  path: '/users/:id',
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}

// In UserDetail component
@customElement('user-detail')
class UserDetail extends LitElement {
  @property() id?: string;

  private _userTask = new Task(this, {
    task: async ([id]) => {
      const res = await fetch(`/api/users/${id}`);
      if (!res.ok) throw new Error('User not found');
      return res.json();
    },
    args: () => [this.id],
  });

  render() {
    return this._userTask.render({
      pending: () => html`<p>Loading...</p>`,
      complete: (user) => html`<h1>${user.name}</h1>...`,
      error: (e) => html`<p>Error: ${e.message}</p>`,
    });
  }
}
```

**Tradeoffs:**
- ✅ **Fast perceived UX** — page renders immediately with a loading state
- ✅ **Built-in cancellation** — `Task` aborts the fetch if `id` changes before it completes
- ✅ **Loose coupling** — router doesn't know about data; component owns its loading state
- ✅ **Flexible error UI** — component can show an error banner without blocking navigation
- ❌ **Component complexity** — `UserDetail` must handle `pending`, `complete`, `error` states
- ❌ **Slower first paint** — router renders the component shell before data arrives

## When to Use Each

| Scenario | Use | Why |
|----------|-----|-----|
| Critical data (e.g., auth check, 404 detection) | `enter` | Block navigation if data is missing or invalid |
| User expects instant feedback (e.g., search results) | `@lit/task` | Show loading spinner immediately |
| Nested routes with shared parent data | `enter` in parent | Preload once, pass to all children |
| Component-local, independent data | `@lit/task` | Isolate loading logic in the component |
| Slow network, want perceived speed | `@lit/task` | Render UI shell while fetching |
| Simple, small data (e.g., config) | `enter` | Minimal overhead, cleaner component |

## Hybrid Pattern (Recommended for Most Cases)

Use `enter` for **validation/guards**, `@lit/task` for **data**:

```ts
{
  path: '/users/:id',
  enter: async ({id}) => {
    // Validate the ID format or check permissions
    if (!id || !/^\d+$/.test(id)) return false; // Cancel navigation
    // Don't fetch here; let the component do it
  },
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}
```

Then inside `UserDetail`, use `@lit/task` to fetch and render the user. This gives you:
- Fast page render (no blank screen)
- Automatic cancellation on param change
- Clear separation of concerns (router validates, component loads)
- Graceful error UI in the component

## Race Condition Caveat

If you use `enter` for async data, be defensive:

```ts
enter: async ({id}) => {
  const user = await fetch(`/api/users/${id}`).then(r => r.json());
  // ⚠️ If goto('/users/456') fired while this was pending,
  // this result (for id=123) still lands. Store it somewhere
  // and check the current route param before using it.
  this._cachedUser = user;
}
```

`@lit/task` handles this automatically via its abort signal.

## Recommendation

**For most apps: use `@lit/task` inside the component.** It's the modern Lit pattern, handles cancellation, and gives users fast feedback. Reserve `enter` for route guards (permission checks, 404 detection) and critical preloads (shared parent data).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core tradeoffs well and explicitly name @lit/task, but Answer B is more thorough on the critical details: it explicitly calls out the race condition risk in `enter` (stale data from out-of-order resolution), explains that `enter` is awaited by the router and blocks the route update more clearly, and provides a more detailed treatment of AbortSignal cancellation with Task. The hybrid pattern section and the summary table in B also make it more actionable. Answer A is solid but slightly less precise on the race-condition/cancellation contrast.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| explains enter blocks the route update | skill |
| mentions Task gives status / loading state | tie |
| mentions cancellation / race-safety with Task | skill |
| names @lit/task explicitly | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains enter blocks the route update | ✓ | `block` |
| mentions Task gives status / loading state | ✓ | `pending` |
| mentions cancellation / race-safety with Task | ✓ | `cancel` |
| names @lit/task explicitly | ✓ | `@lit/task` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| explains enter blocks the route update | ✓ | `block` |
| mentions Task gives status / loading state | ✓ | `status` |
| mentions cancellation / race-safety with Task | ✓ | `cancel` |
| names @lit/task explicitly | ✓ | `@lit/task` |

<details><summary>opus: baseline answer</summary>

Both work, but they optimize for different things. Here's the tradeoff:

## `enter` callback (in the route)

```js
{
  path: '/users/:id',
  enter: async (params) => {
    this.user = await fetchUser(params.id);
    return true; // allow navigation
  },
  render: () => html`<user-detail .user=${this.user}></user-detail>`
}
```

**Pros:**
- Navigation is *gated* on the fetch — you don't show the route until data is ready (or you can return `false` / redirect on 404).
- Component stays dumb: it just receives data via properties.
- Easier to coordinate auth checks, redirects, and "not found" handling at the routing layer.

**Cons:**
- The previous view stays on screen while fetching (no loading state unless you build one).
- Component isn't reusable outside this route — it depends on the parent setting `.user`.
- Re-fetching on param change (`/users/1` → `/users/2`) needs care; `enter` does fire again, but you have to manage cancellation yourself.
- Mixes data-fetching concerns into your routing config.

## `@lit/task` inside the component

```js
class UserDetail extends LitElement {
  @property() userId!: string;

  private _userTask = new Task(this, {
    task: async ([id], {signal}) => fetchUser(id, {signal}),
    args: () => [this.userId],
  });

  render() {
    return this._userTask.render({
      pending:  () => html`<spinner></spinner>`,
      complete: (user) => html`<user-view .user=${user}></user-view>`,
      error:    (e) => html`<error-msg .err=${e}></error-msg>`,
    });
  }
}
```

**Pros:**
- Built-in pending/error/complete states — easy loading UX.
- Automatic re-run when `userId` changes, with `AbortSignal` for cancellation.
- Component is self-contained and reusable anywhere (storybook, other routes, embedded).
- Routing config stays purely about routing.

**Cons:**
- Navigation completes immediately, so you flash a loading state.
- 404 / auth handling has to live inside the component (or you handle it after the fetch resolves).

## My recommendation

Use **`@lit/task`** by default. It's the more idiomatic Lit approach — colocated data, automatic cancellation, built-in states, reusable component.

Use **`enter`** when you specifically need to *block* navigation: auth guards, "must redirect on 404 before showing anything," or SSR-like scenarios where you don't want a flash of loading UI.

A hybrid is also fine: do auth/permission checks in `enter` (return `false` or redirect), and let the component fetch its own data with `@lit/task`.

</details>

<details><summary>opus: skill-loaded answer</summary>

Great question — both work, and the right answer depends on whether you want **the navigation itself to wait** or **the component to render immediately and show its own loading state**.

## Quick recommendation

- **Use `enter`** when the page is meaningless without the data and you want a single, atomic navigation (URL flips → data ready → component renders).
- **Use `@lit/task`** when you want the component to mount immediately and manage its own pending/error states, especially if the user can navigate again mid-fetch.

For a `UserDetail` component, **`@lit/task` is usually the better default**, because:
- It gives you first-class `pending` / `complete` / `error` states.
- It runs again automatically when the `id` param changes (no manual refetch wiring).
- It supports cancellation via `AbortSignal`, which matters if the user clicks rapidly between users.
- The component is reusable outside the router (e.g. in tests, in a modal).

Use `enter` when you specifically want the previous page to stay on screen until the new data is ready — a "block navigation until loaded" UX.

## Side-by-side

### Option A: `enter` (block navigation)

```ts
private _router = new Router(this, [
  {
    path: '/users/:id',
    enter: async ({id}) => {
      // Router awaits this before updating params and re-rendering.
      // Return false to cancel the navigation entirely.
      await preloadUser(id!);
    },
    render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
  },
]);
```

Tradeoffs:
- ✅ When `<user-detail>` mounts, the data is guaranteed ready (assuming you cache it).
- ✅ Can cancel navigation by returning `false` (e.g. permission check fails).
- ❌ The previous page sits frozen during the fetch with no built-in spinner — you have to render a top-level loading bar yourself.
- ❌ **Race condition risk**: if the user clicks user A then quickly user B, both `enter` calls run; if A resolves last, you may render B's URL with A's data. The library gives you no cancellation token here — you have to roll your own (e.g. an "is this still the latest navigation?" check).
- ❌ Coupling: the route config knows about the component's data needs.

### Option B: `@lit/task` (component-local)

```ts
import {Task} from '@lit/task';

@customElement('user-detail')
class UserDetail extends LitElement {
  @property() id!: string;

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
      pending:  () => html`<spinner-el></spinner-el>`,
      complete: (user) => html`<h1>${user.name}</h1>`,
      error:    (e) => html`<error-el .error=${e}></error-el>`,
    });
  }
}
```

Tradeoffs:
- ✅ Navigation is instant; the component shows a spinner.
- ✅ Built-in `pending` / `complete` / `error` branches.
- ✅ `AbortSignal` cancels the in-flight fetch when `id` changes — no stale-result bugs.
- ✅ Re-runs automatically when `args` change, so the same `<user-detail>` instance updates correctly if the router reuses it across `:id` changes.
- ✅ Component works anywhere, not just under this route.
- ❌ You have to design the loading state in the component.
- ❌ Can't block/cancel the navigation itself (e.g. for auth redirects — do those in `enter`).

## Hybrid pattern (often the best of both)

Use `enter` only for things that should gate the navigation, and `@lit/task` for the actual data:

```ts
{
  path: '/users/:id',
  enter: async ({id}) => {
    // Cheap auth/permission check — cancels nav if the user can't view this page.
    if (!(await canViewUser(id!))) {
      history.replaceState({}, '', '/forbidden');
      this._router.goto('/forbidden');
      return false;
    }
  },
  render: ({id}) => html`<user-detail .id=${id}></user-detail>`,
}
```

Then let `<user-detail>` fetch its own data with `@lit/task`. This keeps navigation gating in the route config and data lifecycle in the component, where it belongs.

## TL;DR

| Want… | Use |
|---|---|
| Spinner inside the component, cancellation on rapid nav | `@lit/task` |
| Old page stays put until new data is ready | `enter` (and add a top-level progress bar) |
| Block nav for auth / permissions | `enter` returning `false` |
| Both | Hybrid: `enter` for gating, `@lit/task` for data |

For a `UserDetail`, I'd reach for `@lit/task` first.

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **skill** — Answer B correctly identifies that @lit-labs/router does not support hash routing and explains why (it matches against pathname, not hash), then offers legitimate alternatives. Answer A invents a workaround API (including a fabricated `urlPattern` constructor option that doesn't exist) and presents it as a working solution, which is misleading and incorrect per the rubric criteria.

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
    window.location.hash = url;
  };

  history.replaceState = (state, title, url) => {
    const hash = '#' + url;
    originalReplaceState(state, title, window.location.pathname + hash);
  };

  // Redirect initial load: set hash if empty
  if (!window.location.hash) {
    window.location.hash = '/';
  }

  // Make popstate fire on hashchange
  window.addEventListener('hashchange', () => {
    const path = getPathFromHash();
    // Dispatch popstate so the router picks up the change
    window.dispatchEvent(new PopStateEvent('popstate', { state: null }));
  });

  const router = new Router(host, routes, {
    // Tell the router where to read the current path from
    urlPattern: { pathname: getPathFromHash() },
  });

  return router;
}
```

### Usage in a Lit Component

```javascript
// my-app.js
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';

class MyApp extends LitElement {
  #router;

  constructor() {
    super();
    this.#router = new Router(this, [
      {
        path: '/',
        render: () => html`<h1>Home</h1>`,
      },
      {
        path: '/users',
        render: () => html`<h1>Users List</h1>`,
      },
      {
        path: '/users/:id',
        render: ({ id }) => html`<h1>User: ${id}</h1>`,
      },
      {
        path: '/*',
        render: () => html`<h1>404 Not Found</h1>`,
      },
    ]);

    this.#setupHashRouting();
  }

  #setupHashRouting() {
    // Normalize hash to path for router matching
    const syncRouterToHash = () => {
      const path = window.location.hash.slice(1) || '/';
      this.#router.goto(path);
    };

    // Listen for hash changes
    window.addEventListener('hashchange', syncRouterToHash);

    // Handle initial load
    if (!window.location.hash) {
      window.location.hash = '#/';
    } else {
      syncRouterToHash();
    }
  }

  render() {
    return html`
      <nav>
        <a href="#/">Home</a>
        <a href="#/users">Users</a>
        <a href="#/users/123">User 123</a>
      </nav>
      <main>${this.#router.outlet()}</main>
    `;
  }
}

customElements.define('my-app', MyApp);
```

### How Navigation Works

```javascript
// Use href="#/path" in templates — no special handling needed
html`<a href="#/users/456">Go to User 456</a>`

// Programmatic navigation
this.#router.goto('/users/456');          // router internal path
window.location.hash = '#/users/456';    // direct hash change (also works)
```

### Key Points

| Concern | Solution |
|---|---|
| Link format | Use `href="#/path"` instead of `href="/path"` |
| Route definitions | Define routes as `/path` (no `#`) — router sees normalized paths |
| Programmatic nav | Call `router.goto('/path')` or set `location.hash` |
| Initial load | Default to `#/` if hash is empty |
| Browser back/forward | `hashchange` event handles it automatically |

> **Note:** `@lit-labs/router` is still experimental. If hash routing is a core requirement, consider [`navigo`](https://github.com/krasimir/navigo) or [`vaadin-router`](https://vaadin.com/router) which have first-class hash routing support.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Hash routing is not supported by `@lit-labs/router`

This is a hard limitation, not a configuration gap. The router compiles every `path` string into a `URLPattern` that matches against `location.pathname` only. The fragment (`#/users/123`) is never part of `pathname` — it lives in `location.hash` — so the router never sees it, regardless of how you configure your routes.

There is no `hashRouting: true` option, no hash-aware `URLPattern` mode, and no workaround within the library itself.

---

## Your real options

### Option 1 — Use History API routing (recommended)

This is what `@lit-labs/router` is designed for. URLs look like `/users/123` instead of `/#/users/123`.

The one server-side requirement: configure your dev server (and production server) to serve `index.html` for any unknown path, so a hard refresh on `/users/123` still loads your app.

**Vite:**
```js
// vite.config.js
export default {
  server: { historyApiFallback: true },
};
```

**webpack-dev-server:**
```js
devServer: { historyApiFallback: true }
```

**Nginx:**
```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```

Once the server is configured, `@lit-labs/router` works as documented with no extra setup.

---

### Option 2 — Use a router that actually supports hash routing

If hash-based URLs are a firm requirement (e.g. a static file host with no server-side fallback config, or a GitHub Pages deployment without a custom 404 page), use a different router:

| Router | Hash routing | Notes |
|--------|-------------|-------|
| [`@vaadin/router`](https://github.com/vaadin/router) | ✅ `{baseUrl: '/#'}` option | Mature, well-documented |
| [`navigo`](https://github.com/krasimir/navigo) | ✅ built-in | Tiny, framework-agnostic |
| [`page.js`](https://github.com/visionmedia/page.js) | ✅ `{hashbang: true}` | Classic, minimal |
| [`universal-router`](https://github.com/kriasoft/universal-router) | ✅ manual | Pairs well with Lit |

---

### Option 3 — Roll a minimal hash router yourself

If you want to stay close to Lit's reactive model without a full library, a small custom controller is straightforward:

```ts
import {ReactiveController, ReactiveControllerHost, html, TemplateResult} from 'lit';

interface HashRoute {
  pattern: RegExp;
  render: (match: RegExpMatchArray) => TemplateResult;
}

class HashRouter implements ReactiveController {
  private _host: ReactiveControllerHost & EventTarget;
  private _routes: HashRoute[];
  private _fallback: () => TemplateResult;

  constructor(
    host: ReactiveControllerHost & EventTarget,
    routes: HashRoute[],
    fallback: () => TemplateResult = () => html`<p>Not found</p>`,
  ) {
    this._host = host;
    this._routes = routes;
    this._fallback = fallback;
    host.addController(this);
  }

  hostConnected() {
    window.addEventListener('hashchange', this._onHashChange);
  }

  hostDisconnected() {
    window.removeEventListener('hashchange', this._onHashChange);
  }

  private _onHashChange = () => {
    this._host.requestUpdate();
  };

  private get _currentPath() {
    // Strip the leading '#' (and optional '/')
    return location.hash.replace(/^#\/?/, '') || '';
  }

  outlet(): TemplateResult {
    for (const route of this._routes) {
      const match = this._currentPath.match(route.pattern);
      if (match) return route.render(match);
    }
    return this._fallback();
  }

  goto(path: string) {
    location.hash = '/' + path.replace(/^\//, '');
  }
}
```

Usage:

```ts
@customElement('my-app')
class MyApp extends LitElement {
  private _router = new HashRouter(this, [
    {pattern: /^$/, render: () => html`<home-page></home-page>`},
    {pattern: /^users\/(\d+)$/, render: ([, id]) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  render() {
    return html`
      <nav>
        <a href="#/">Home</a>
        <a href="#/users/123">User 123</a>
      </nav>
      <main>${this._router.outlet()}</main>
    `;
  }
}
```

This is intentionally minimal — no nested routes, no `enter` hooks — but it covers the hash-routing use case that `@lit-labs/router` cannot.

---

## Summary

| Approach | Effort | Tradeoff |
|----------|--------|----------|
| Switch to History API + server fallback | Low (server config only) | Clean URLs; requires server cooperation |
| Use `@vaadin/router` or similar | Low (swap library) | Full-featured hash routing |
| Write a small custom controller | Medium | Full control; you own the code |
| Make `@lit-labs/router` do hash routing | **Not possible** | — |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly states that @lit-labs/router does not support hash routing and explains why, then offers legitimate alternatives. Answer B invents a fictional `hashLocationProvider` API that does not exist in @lit-labs/router, which is exactly the trap the question warns about — it would mislead developers into trying a non-existent feature.

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

The simplest way is to use the `hashLocationProvider` instead of the default `pathLocationProvider`:

```typescript
import { Router } from '@lit-labs/router';
import { hashLocationProvider } from '@lit-labs/router/lib/location-providers/hash.js';

const router = new Router(element, [
  { path: '/users/:id', component: 'user-detail' },
  { path: '/users', component: 'user-list' },
], {
  locationProvider: hashLocationProvider(),
});
```

## Complete Example

```typescript
import { LitElement, html } from 'lit';
import { Router } from '@lit-labs/router';
import { hashLocationProvider } from '@lit-labs/router/lib/location-providers/hash.js';

class MyApp extends LitElement {
  router?: Router;

  firstUpdated() {
    this.router = new Router(this, [
      { path: '/users/:id', component: 'user-detail' },
      { path: '/users', component: 'user-list' },
      { path: '/', component: 'home-page' },
    ], {
      locationProvider: hashLocationProvider(),
    });
  }

  render() {
    return html`<main></main>`;
  }
}

customElements.define('my-app', MyApp);
```

Now your URLs will be:
- `http://localhost:3000/#/users`
- `http://localhost:3000/#/users/123`
- `http://localhost:3000/#/`

That's it! The `hashLocationProvider` handles all the hash-based routing automatically.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Hash Routing with @lit-labs/router

**Hash routing is not supported by `@lit-labs/router`.** The router inspects only `pathname` via the `URLPattern` API and the History API, not the hash fragment. There is no built-in option to enable it.

## Why It's Not Supported

- `URLPattern` matching operates on `pathname` only (e.g. `/users/123`), not `location.hash`.
- The router's click interception and `goto()` use `history.pushState()`, which updates `pathname`, not the hash.
- The `popstate` listener responds to History API changes, not `hashchange` events.

## Your Options

### Option 1: Use Pathname Routing (Recommended)

Switch to standard pathname-based URLs (`/users/123`). This is what `@lit-labs/router` is designed for and requires no workarounds:

```ts
const router = new Router(this, [
  {path: '/users/:id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
]);
```

**Pros:** Native support, cleaner URLs, better SEO, works with server-side rendering.  
**Cons:** Requires SPA fallback on your server (serve `index.html` for unknown paths).

### Option 2: Use a Different Router

If you need hash routing, consider:
- **`@vaadin/router`** — supports hash routing via `hashBang: true` option.
- **`lit-element-router`** — hash-based by default.
- **`wouter`** — lightweight, supports both pathname and hash modes.

### Option 3: Implement a Hash-to-Pathname Adapter (Not Recommended)

If you're locked into `@lit-labs/router` and must support hash URLs, you can manually sync the hash to `pathname` on startup and `hashchange`:

```ts
@customElement('my-app')
class MyApp extends LitElement {
  private _router = new Router(this, [
    {path: '/users/:id', render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
  ]);

  connectedCallback() {
    super.connectedCallback();
    // On startup, convert hash to pathname
    this._syncHashToPathname();
    // Listen for manual hash changes (e.g. user types in address bar)
    window.addEventListener('hashchange', () => this._syncHashToPathname());
  }

  private _syncHashToPathname() {
    const hash = location.hash.slice(1); // Remove '#'
    if (hash && location.pathname !== hash) {
      history.replaceState({}, '', hash);
      this._router.goto(hash);
    }
  }

  render() {
    return html`${this._router.outlet()}`;
  }
}
```

**Pros:** Keeps you on `@lit-labs/router`.  
**Cons:** Fragile, requires manual sync, breaks browser history semantics, not tested by the library, adds complexity.

## Recommendation

**Use pathname routing.** It's the standard for modern SPAs, works seamlessly with `@lit-labs/router`, and avoids the pitfalls of hash-based navigation. If your server doesn't support SPA fallback yet, that's a one-line fix (e.g. `try_files $uri /index.html;` in nginx, or a catch-all route in Express).

If you absolutely must have hash routing for legacy reasons, switch to `@vaadin/router` or another hash-capable router instead of fighting `@lit-labs/router`'s design.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **skill** — Answer A correctly and clearly states that @lit-labs/router does not support hash routing and explicitly avoids inventing a hash-routing API, instead offering legitimate alternatives. Answer B acknowledges the lack of built-in support but then proceeds to invent a workaround using router.goto() that fights the library's design (the router still intercepts clicks via History API, and router.goto() may internally use pushState), presenting it as a clean solution when it's actually fragile and not recommended. The rubric specifically penalizes inventing a hash-routing setup, which Answer B does.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| states hash routing is not supported | tie |
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

`@lit-labs/router` doesn't have built-in hash routing support — it uses the History API by default. But you can add hash routing with a small adapter that listens to `hashchange` and calls `router.goto()`.

## Minimal Setup

```js
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { Router } from '@lit-labs/router';

@customElement('my-app')
export class MyApp extends LitElement {
  private router = new Router(this, [
    { path: '/', render: () => html`<h1>Home</h1>` },
    { path: '/users/:id', render: ({ id }) => html`<h1>User ${id}</h1>` },
    { path: '/about', render: () => html`<h1>About</h1>` },
  ]);

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('hashchange', this.#onHashChange);
    this.#syncFromHash(); // handle initial load
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('hashchange', this.#onHashChange);
  }

  #onHashChange = () => this.#syncFromHash();

  #syncFromHash() {
    const path = location.hash.slice(1) || '/';
    this.router.goto(path);
  }

  render() {
    return html`
      <nav>
        <a href="#/">Home</a>
        <a href="#/users/123">User 123</a>
        <a href="#/about">About</a>
      </nav>
      ${this.router.outlet()}
    `;
  }
}
```

## How It Works

1. **Routes are defined normally** with paths like `/users/:id` (no `#`).
2. **Links use `href="#/..."`** — the browser updates the hash and fires `hashchange` without a page reload.
3. **The `hashchange` listener** strips the `#` and calls `router.goto()` to drive the router.
4. **`#syncFromHash()` runs on connect** so the correct route renders on initial load (and on reload).

## Optional: Programmatic Navigation

Instead of calling `router.goto()` directly, just update the hash:

```js
location.hash = '/users/456';
```

This keeps the URL and router in sync via the same `hashchange` handler.

## Why This Works

`@lit-labs/router` is intentionally minimal — `Router.goto(path)` accepts any string and matches it against your routes. By treating the hash as the source of truth instead of `location.pathname`, you get hash routing essentially for free.

The main thing you give up is the built-in link interception (`router` normally hijacks `<a>` clicks for History API navigation). With hashes, the browser handles navigation natively, so you don't need it.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Hash routing with `@lit-labs/router` — not supported

**`@lit-labs/router` does not support hash routing.** There is no `hashRouting` option, no flag, and no built-in way to make it match against `location.hash`. The router only inspects `location.pathname` via the `URLPattern` API, and it listens to `popstate` (History API) — not `hashchange`.

I want to be upfront about this rather than invent a flag that doesn't exist.

## Your real options

### 1. Use the History API instead (recommended)

This is what the library is designed for. URLs look like `/users/123` (no `#`). You need one server-side change: configure your dev/prod server to serve `index.html` for unknown paths (SPA fallback). Almost every static host (Netlify, Vercel, GitHub Pages with a workaround, Cloudflare Pages, `vite preview`, `wrangler`, etc.) supports this in one line of config.

```ts
import {Router} from '@lit-labs/router';

private _router = new Router(this, [
  {path: '/',           render: () => html`<home-page></home-page>`},
  {path: '/users/:id',  render: ({id}) => html`<user-detail .id=${id}></user-detail>`},
]);

render() {
  return html`
    <a href="/users/123">User 123</a>
    <main>${this._router.outlet()}</main>
  `;
}
```

### 2. Pick a different router that supports hash mode

If you genuinely cannot configure the server (e.g. deploying to a host that won't do SPA fallback and you can't add a `404.html` workaround), use a router that supports hash routing out of the box. `@vaadin/router` is a common pick in the Lit ecosystem and has explicit hash-routing support.

### 3. Roll your own hash → pathname adapter (not recommended)

You'd listen for `hashchange`, parse `location.hash.slice(1)`, and call `router.goto(parsedPath)`. But you'd also need to suppress the router's own click interception (which navigates via History), rewrite all your `<a href>` links to use `#/...`, and handle the initial load. At that point you're fighting the library — option 2 is less work.

## Why the constraint exists

Internally, `Router._onPopState` reads `window.location.pathname` and passes it to `Routes.goto()`, which matches it against each route's `URLPattern({pathname})`. The hash is never consulted. Adding hash support would mean a different event listener (`hashchange`), a different source string, and changes to click interception so it doesn't `pushState` for hash links — it's not a config toggle, it's a different mode.

## My recommendation

Go with option 1 (History API + SPA fallback). Tell me what you're deploying to and I'll give you the exact one-line server config. If SPA fallback truly isn't possible in your environment, say so and I'll point you at `@vaadin/router` setup instead.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in content, accuracy, and presentation. They both correctly explain the difference between git merge and git rebase, use similar visuals, and provide the same golden rule. Minor differences in wording and table content are negligible.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## Git Merge vs Git Rebase

**`git merge`** combines two branches by creating a **new merge commit** that ties their histories together. The original branch history is preserved as-is.

**`git rebase`** moves your commits to the **tip of another branch**, rewriting them as if you had started your work from there. The history is linear but rewritten.

---

### Simple visual

**Merge:**
```
A---B---C  (main)
     \     \
      D---E--M  (merge commit)
```

**Rebase:**
```
A---B---C---D'---E'  (linear history)
```

---

### Quick rule of thumb

| | Merge | Rebase |
|---|---|---|
| History | Preserved (messy) | Rewritten (clean) |
| Safe for shared branches? | ✅ Yes | ⚠️ Avoid |
| Best for | Merging finished features | Keeping a clean local history |

> **Golden rule:** Never rebase a branch that others are working on, since rewriting history causes problems for everyone else.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## `git merge` vs `git rebase`

Both integrate changes from one branch into another, but they do it differently.

**`git merge`** creates a new "merge commit" that joins the two branch histories together. The original commits from both branches are preserved as-is.

```
A---B---C  (main)
     \   \
      D---E---M  (merge commit)
```

**`git rebase`** replays your commits on top of the target branch, rewriting them as if you'd started from there. No merge commit — linear history.

```
A---B---C  (main)
             \
              D'--E'  (rebased)
```

---

### Quick rule of thumb

| | Merge | Rebase |
|---|---|---|
| History | Preserves it exactly | Rewrites it (new commit SHAs) |
| Shape | Non-linear (branchy) | Linear |
| Safe to use on shared branches? | ✅ Yes | ⚠️ Avoid — rewrites history others depend on |
| Good for | Merging feature branches into `main` | Cleaning up local commits before sharing |

**Golden rule:** never rebase commits that have already been pushed to a shared branch.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in quality and correctness. They cover the same key points: merge creates a merge commit with branching history, rebase replays commits linearly and rewrites history, and both give the same practical advice about shared vs local branches. Answer A includes a visual diagram which is a nice touch, while Answer B explicitly mentions commit hash rewriting, but neither difference is material enough to declare a winner.

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

**Simple example:**

With merge, you get:
```
A—B—C (main)
 \ \
  D—E—M (feature merged)
```

With rebase, you get:
```
A—B—C—D'—E' (feature rebased onto main)
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
- Makes the history linear (no branching).
- Rewrites commit hashes, so don't use on shared/public branches.

**When to use:**
- **Merge**: Integrating a feature branch into main; preserves history and is safe for shared branches.
- **Rebase**: Cleaning up your own local branch before pushing; keeps history tidy.

**Quick rule:** If others are using the branch, merge. If it's just yours, rebase is cleaner.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers are essentially equivalent in accuracy and usefulness. Answer A adds a useful warning about never rebasing commits others have pulled, while Answer B adds a quick analogy that some may find helpful. Neither is materially better or worse.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

**`git merge`** combines two branches by creating a new "merge commit" that ties their histories together. Your branch history is preserved as-is, including the parallel development.

**`git rebase`** moves your branch's commits on top of another branch, rewriting history so it looks like your work happened linearly after the latest changes.

**Quick analogy:**
- *Merge* = "Let's join our work and note when we combined it." (preserves history, can get messy)
- *Rebase* = "Let me replay my changes as if I started from the latest version." (cleaner, linear history)

**Rule of thumb:** Use `merge` for shared/public branches, `rebase` for cleaning up your local work before sharing.

</details>

<details><summary>opus: skill-loaded answer</summary>

**`git merge`** combines two branches by creating a new "merge commit" that ties their histories together. Both branches' histories are preserved as-is, and you end up with a branching, then re-joining, graph.

**`git rebase`** takes your branch's commits and replays them on top of another branch, as if you'd started your work from the latest version. History stays linear, but the original commits are rewritten (new SHAs).

**Rule of thumb:**
- Use **merge** for shared/public branches — it's safe and preserves history.
- Use **rebase** for your local branch before sharing — it keeps history clean and linear.
- Never rebase commits that others have already pulled.

</details>

---
