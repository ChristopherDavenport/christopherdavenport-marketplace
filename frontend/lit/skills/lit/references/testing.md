# Testing Lit Components

Vitest with happy-dom provides a fast, modern test environment for Lit web components. Vitest has native TypeScript support and watch mode, while happy-dom is a lightweight browser simulation with custom element and Shadow DOM support.

## Setup

```bash
npm i -D vitest happy-dom
```

**`vitest.config.ts`:**
```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'happy-dom',
  },
});
```

**`package.json`:**
```json
{
  "scripts": {
    "test": "vitest"
  }
}
```

## Fixture Helper

A reusable helper that creates an element, appends it to the DOM, awaits `updateComplete`, and tracks elements for automatic cleanup:

```ts
import { afterEach } from 'vitest';

const fixtureElements: HTMLElement[] = [];

async function fixture<T extends HTMLElement>(tag: string, props?: Partial<T>): Promise<T> {
  const el = document.createElement(tag) as T;
  if (props) Object.assign(el, props);
  document.body.appendChild(el);
  fixtureElements.push(el);
  await (el as any).updateComplete;
  return el;
}

afterEach(() => {
  fixtureElements.forEach(el => el.remove());
  fixtureElements.length = 0;
});
```

Place this in a shared test utility file (e.g., `test/utils.ts`) and import where needed.

## Basic Test Structure

```ts
import { describe, it, expect } from 'vitest';
import '../src/my-element.js';
import type { MyElement } from '../src/my-element.js';

describe('my-element', () => {
  it('renders with default values', async () => {
    const el = await fixture<MyElement>('my-element');

    expect(el.shadowRoot).toBeTruthy();
    expect(el.shadowRoot!.querySelector('h1')?.textContent).toBe('Default');
  });
});
```

The component module must be imported for its side effect (registering the custom element). Without it, `document.createElement('my-element')` returns a generic `HTMLElement`.

## Testing Reactive Properties

Set properties via the fixture helper or programmatically, then await `updateComplete`:

```ts
it('renders the name property', async () => {
  const el = await fixture<MyElement>('my-element', { name: 'Alice' });

  expect(el.name).toBe('Alice');
  expect(el.shadowRoot!.querySelector('h1')?.textContent).toBe('Alice');
});

it('updates when property changes', async () => {
  const el = await fixture<MyElement>('my-element', { name: 'Alice' });

  el.name = 'Bob';
  await el.updateComplete;

  expect(el.shadowRoot!.querySelector('h1')?.textContent).toBe('Bob');
});
```

**Critical:** Always `await el.updateComplete` after changing a reactive property before asserting on DOM content. Without it, you're reading stale DOM.

## Testing Shadow DOM Content

Query inside `el.shadowRoot`:

```ts
it('renders a list of items', async () => {
  const el = await fixture<MyList>('my-list', { items: ['A', 'B', 'C'] });

  const items = el.shadowRoot!.querySelectorAll('li');
  expect(items).toHaveLength(3);
  expect(items[0].textContent).toBe('A');
});
```

For complex queries, use helper functions:

```ts
function getShadow(el: LitElement, selector: string) {
  return el.shadowRoot!.querySelector(selector);
}

function getAllShadow(el: LitElement, selector: string) {
  return el.shadowRoot!.querySelectorAll(selector);
}
```

## Testing Events

### Dispatched Events

```ts
it('fires count-changed on increment', async () => {
  const el = await fixture<Counter>('my-counter');
  const button = el.shadowRoot!.querySelector('button')!;

  const eventPromise = new Promise<CountChangedEvent>(resolve => {
    el.addEventListener('count-changed', resolve as EventListener, { once: true });
  });
  button.click();
  const event = await eventPromise;

  expect(event).toBeTruthy();
  expect(event.count).toBe(1);
});
```

Set up the event listener *before* triggering the action so the event is always caught.

### Multiple Events

```ts
it('fires events in sequence', async () => {
  const el = await fixture<MyElement>('my-element');
  const events: Event[] = [];

  el.addEventListener('my-event', (e) => events.push(e));

  el.trigger();
  el.trigger();
  await el.updateComplete;

  expect(events).toHaveLength(2);
});
```

## Testing User Interaction

```ts
it('toggles on click', async () => {
  const el = await fixture<Toggle>('my-toggle');
  const button = el.shadowRoot!.querySelector('button')!;

  expect(el.active).toBe(false);

  button.click();
  await el.updateComplete;

  expect(el.active).toBe(true);
  expect(button.getAttribute('aria-pressed')).toBe('true');
});

it('handles keyboard interaction', async () => {
  const el = await fixture<MyButton>('my-button');
  const target = el.shadowRoot!.querySelector('[role="button"]')!;

  target.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
  await el.updateComplete;

  expect(el.activated).toBe(true);
});
```

## Testing with Context Providers

Wrap the consumer in a provider element using manual DOM construction:

```ts
import { provide } from '@lit/context';
import { userContext, type UserData } from '../src/contexts.js';

@customElement('test-provider')
class TestProvider extends LitElement {
  @provide({ context: userContext })
  @property({ attribute: false })
  user: UserData = { id: 1, name: 'Test User', email: 'test@test.com' };

  render() { return html`<slot></slot>`; }
}

describe('user-badge', () => {
  it('renders user from context', async () => {
    const provider = document.createElement('test-provider') as TestProvider;
    const badge = document.createElement('user-badge') as UserBadge;
    provider.appendChild(badge);
    document.body.appendChild(provider);
    fixtureElements.push(provider);
    await provider.updateComplete;
    await badge.updateComplete;

    expect(badge.shadowRoot!.textContent).toContain('Test User');
  });

  it('updates when context value changes', async () => {
    const provider = document.createElement('test-provider') as TestProvider;
    const badge = document.createElement('user-badge') as UserBadge;
    provider.appendChild(badge);
    document.body.appendChild(provider);
    fixtureElements.push(provider);
    await provider.updateComplete;
    await badge.updateComplete;

    provider.user = { id: 2, name: 'Updated', email: 'u@test.com' };
    await provider.updateComplete;
    await badge.updateComplete;

    expect(badge.shadowRoot!.textContent).toContain('Updated');
  });
});
```

For nested element tests, construct the DOM manually and push the outermost element to `fixtureElements` for cleanup.

## Testing Task States

Test each task status by controlling when the fetch resolves:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('user-profile', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('shows loading state', async () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {})); // never resolves

    const el = await fixture<UserProfile>('user-profile', { userId: '1' });

    expect(el.shadowRoot!.textContent).toContain('Loading');
  });

  it('renders user on success', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ name: 'Alice' })));

    const el = await fixture<UserProfile>('user-profile', { userId: '1' });

    await el.updateComplete;
    // May need an extra microtask for the Task to settle
    await new Promise(r => setTimeout(r, 0));
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).toContain('Alice');
  });

  it('shows error state', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('', { status: 500 }));

    const el = await fixture<UserProfile>('user-profile', { userId: '1' });

    await el.updateComplete;
    await new Promise(r => setTimeout(r, 0));
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).toContain('Error');
  });
});
```

**Note:** Task settles asynchronously after the initial render. You may need an extra microtask (`setTimeout(r, 0)`) followed by another `await updateComplete` to see the final state.

## Testing Form-Associated Components

```ts
it('participates in form submission', async () => {
  const form = document.createElement('form');
  const field = document.createElement('text-field') as TextField;
  field.setAttribute('name', 'email');
  field.value = 'test@example.com';
  form.appendChild(field);
  document.body.appendChild(form);
  fixtureElements.push(form);
  await field.updateComplete;

  const formData = new FormData(form);
  expect(formData.get('email')).toBe('test@example.com');
});

it('validates correctly', async () => {
  const el = await fixture<TextField>('text-field');
  el.setAttribute('required', '');
  await el.updateComplete;

  expect(el.internals.checkValidity()).toBe(false);

  el.value = 'hello';
  await el.updateComplete;

  expect(el.internals.checkValidity()).toBe(true);
});
```

## Common Pitfalls

### Not awaiting `updateComplete`
**Problem:** Assertions run before the DOM reflects the property change.
**Fix:** Always `await el.updateComplete` after any property change before asserting on DOM.

### Querying light DOM instead of shadow DOM
**Problem:** `el.querySelector()` searches light DOM. Shadow DOM content won't be found.
**Fix:** Use `el.shadowRoot!.querySelector()` for shadow DOM content.

### Stale Task state
**Problem:** Task is still PENDING when you assert COMPLETE.
**Fix:** After `await updateComplete`, add `await new Promise(r => setTimeout(r, 0))` then `await updateComplete` again. Task settles on a separate microtask.

### Custom element not defined in test
**Problem:** `document.createElement('my-element')` returns a generic `HTMLElement` because the component file was never imported.
**Fix:** Import the component's side-effect module (e.g., `import '../src/my-element.js'`) at the top of the test file before creating elements.

### Event listener registered after the event fires
**Problem:** The event fires before the listener Promise is set up, so the test hangs.
**Fix:** Always create the `addEventListener` Promise before triggering the action that dispatches the event.

### happy-dom limitation with computed styles
**Problem:** A test relies on `getComputedStyle` with CSS custom properties or pseudo-elements, which happy-dom does not fully support.
**Fix:** Add `// @vitest-environment jsdom` at the top of that test file to switch environments per-file, or move CSS-dependent assertions to Vitest Browser Mode tests with Playwright.

## Best Practices

- **One assertion focus per test** — test one behavior, not the entire component
- **Await `updateComplete` after every mutation** — properties, method calls, event dispatches
- **Use the `fixture()` helper for clean test setup** — creates, appends, awaits, and auto-cleans up elements
- **Clean up mocks in `afterEach`** — use `vi.restoreAllMocks()` and `vi.unstubAllGlobals()`
- **Test accessibility** — check `role`, `aria-*` attributes, keyboard interaction, focus management
- **Test edge cases** — empty data, error states, rapid property changes, disconnection/reconnection
- **Set up event listeners before triggering actions** — use `{ once: true }` for single events, collect into an array for multiple
- **Avoid testing Lit internals** — test the component's public API (properties, events, rendered output), not implementation details
- **Use `// @vitest-environment jsdom` as an escape hatch** — for any test file that hits a happy-dom limitation, switch environments per-file
