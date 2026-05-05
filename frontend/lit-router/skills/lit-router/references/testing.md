# Testing — Deep Dive

`@lit-labs/router` ships no library-specific test helpers. The package's own tests (in `packages/labs/router/src/test/router_test.ts`) follow a simple pattern that you can mirror:

1. **Isolate via iframe** — `Router` installs listeners on `window` and reads `location.pathname`. Tests that share a `window` pollute each other. Either run inside an iframe with its own contentWindow, or carefully restore history in `afterEach`.
2. **`await el.updateComplete`** after every navigation before asserting on shadow DOM content.
3. **For nested routers**, query through each shadow root: `el.shadowRoot!.querySelector('users-section')!.shadowRoot!.querySelector(...)`.
4. **Drive navigation two ways** — clicking an `<a>` exercises the click interception path; `history.pushState` + `router.goto` exercises the programmatic path. Test both.
5. **For `popstate`**, call `history.back()` and wait for the next microtask plus `updateComplete`.

## With `@open-wc/testing`

```ts
import {fixture, html, expect} from '@open-wc/testing';
import './my-app.js';
import type {MyApp} from './my-app.js';

describe('<my-app>', () => {
  let originalPath: string;

  beforeEach(() => {
    originalPath = location.pathname;
    history.pushState({}, '', '/');
  });

  afterEach(() => {
    history.pushState({}, '', originalPath);
  });

  it('renders the home route initially', async () => {
    const el = await fixture<MyApp>(html`<my-app></my-app>`);
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).to.contain('Home');
  });

  it('navigates to /about on link click', async () => {
    const el = await fixture<MyApp>(html`<my-app></my-app>`);
    await el.updateComplete;

    const link = el.shadowRoot!.querySelector('a[href="/about"]') as HTMLAnchorElement;
    link.click();
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).to.contain('About');
    expect(location.pathname).to.equal('/about');
  });

  it('navigates programmatically when paired with pushState', async () => {
    const el = await fixture<MyApp>(html`<my-app></my-app>`);
    await el.updateComplete;

    history.pushState({}, '', '/users/42');
    // Access the router through whatever public hook the component exposes,
    // or test via a public method.
    el.navigate('/users/42');
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).to.contain('User 42');
  });
});
```

## With Vitest + happy-dom (consistent with `lit`)

`vitest.config.ts`:

```ts
import {defineConfig} from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'happy-dom',
  },
});
```

```ts
import {describe, it, beforeEach, afterEach, expect} from 'vitest';
import './my-app.js';
import type {MyApp} from './my-app.js';

const fixture = async <T extends HTMLElement>(tag: string): Promise<T> => {
  const el = document.createElement(tag) as T;
  document.body.appendChild(el);
  await (el as any).updateComplete;
  return el;
};

describe('<my-app>', () => {
  let originalPath: string;

  beforeEach(() => {
    originalPath = location.pathname;
    history.pushState({}, '', '/');
  });

  afterEach(() => {
    document.body.innerHTML = '';
    history.pushState({}, '', originalPath);
  });

  it('renders the home route initially', async () => {
    const el = await fixture<MyApp>('my-app');
    expect(el.shadowRoot!.textContent).toContain('Home');
  });

  it('intercepts in-app links', async () => {
    const el = await fixture<MyApp>('my-app');
    const link = el.shadowRoot!.querySelector('a[href="/about"]') as HTMLAnchorElement;
    link.click();
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).toContain('About');
  });
});
```

**happy-dom caveat:** `URLPattern` is not implemented in happy-dom (or jsdom). Import the polyfill in your test setup:

```ts
// test-setup.ts
import 'urlpattern-polyfill';
```

```ts
// vitest.config.ts
export default defineConfig({
  test: {
    environment: 'happy-dom',
    setupFiles: ['./test-setup.ts'],
  },
});
```

## Testing nested routers

```ts
it('renders nested user list under /users/', async () => {
  history.pushState({}, '', '/users/');
  const el = await fixture<MyApp>('my-app');
  await el.updateComplete;

  const section = el.shadowRoot!.querySelector('users-section')!;
  await (section as any).updateComplete;

  expect(section.shadowRoot!.querySelector('user-list')).to.exist;
});

it('renders user detail at /users/42', async () => {
  history.pushState({}, '', '/users/42');
  const el = await fixture<MyApp>('my-app');
  await el.updateComplete;

  const section = el.shadowRoot!.querySelector('users-section')!;
  await (section as any).updateComplete;
  const detail = section.shadowRoot!.querySelector('user-detail') as any;
  expect(detail.id).to.equal('42');
});
```

Two `updateComplete` awaits — once for the parent (which mounts `<users-section>`), once for the section (which renders the matched child route).

## Testing `popstate`

```ts
it('handles back button', async () => {
  const el = await fixture<MyApp>('my-app');
  await el.updateComplete;

  // Navigate forward via click.
  (el.shadowRoot!.querySelector('a[href="/about"]') as HTMLAnchorElement).click();
  await el.updateComplete;
  expect(el.shadowRoot!.textContent).to.contain('About');

  // Back button.
  history.back();
  await new Promise((r) => setTimeout(r, 0));  // let popstate fire
  await el.updateComplete;
  expect(el.shadowRoot!.textContent).to.contain('Home');
});
```

`popstate` fires asynchronously, so wait one microtask before `updateComplete`.

## Testing async `enter`

```ts
it('blocks render until enter resolves', async () => {
  const el = await fixture<MyApp>('my-app');
  await el.updateComplete;

  // The router is on '/'. Trigger nav to a route with async enter.
  history.pushState({}, '', '/products/42');
  await el.navigate('/products/42');   // your test helper that calls router.goto
  await el.updateComplete;

  expect(el.shadowRoot!.querySelector('product-page')).to.exist;
});
```

If `enter` rejects or returns `false`, the route does NOT update. Assert that the old content is still visible.

## Avoiding cross-test pollution

`Router` is a singleton in the sense that it installs listeners on `window`. Across tests:

- Restore `history` in `afterEach` (push the original pathname back).
- Tear down components: `document.body.innerHTML = ''`. This calls `disconnectedCallback`, which removes the global listeners.
- If you instantiate multiple test apps within one file, ensure each is removed before the next is mounted.

Real-world tip: keep router tests in a single file (or run with `--no-isolate` if your runner has it) so the listener install/teardown stays predictable.

## Common Pitfalls

- **`URLPattern is not defined` in tests.** Add `urlpattern-polyfill` to your test setup. Native happy-dom and jsdom don't implement it.
- **Missing `await updateComplete`.** Asserting immediately after `goto()` reads stale DOM.
- **Two-level nesting needs two `updateComplete` awaits.** Parent and child each have their own update cycle.
- **`Router` listeners leak across tests.** Always remove the host element in `afterEach`.
- **`location.pathname` from the previous test.** Push back to a known path in `beforeEach` and `afterEach`.
- **Click `dispatchEvent(new MouseEvent('click', {...}))` may bypass interception** if you don't construct the event correctly (`bubbles: true, composed: true, button: 0`). Prefer calling `link.click()` directly for the click-interception code path.

See also: [api.md](api.md) for `goto()` semantics, [navigation.md](navigation.md) for which clicks are intercepted, [pitfalls.md](pitfalls.md) for the full gotcha list.
