# Reactive Controllers — Deep Dive

Reactive controllers are Lit's composition primitive for encapsulating reusable behavior that hooks into a component's lifecycle. Unlike mixins or base classes, controllers use a "has-a" relationship — a component owns controller instances without modifying its prototype.

Task (`@lit/task`) is itself a reactive controller. The pattern applies broadly to any reusable logic that needs lifecycle awareness.

## Interfaces

### `ReactiveController`

All methods are optional. Implement only what you need.

```ts
interface ReactiveController {
  hostConnected?(): void;       // Host added to DOM
  hostDisconnected?(): void;    // Host removed from DOM
  hostUpdate?(): void;          // Before host's update() and render()
  hostUpdated?(): void;         // After host's update() completes
}
```

### `ReactiveControllerHost`

The host interface — `LitElement` implements this automatically.

```ts
interface ReactiveControllerHost {
  addController(controller: ReactiveController): void;
  removeController(controller: ReactiveController): void;
  requestUpdate(): void;
  readonly updateComplete: Promise<boolean>;
}
```

## Lifecycle Integration

Controllers hook into the host's update cycle at four points:

```
Host connectedCallback()
  → controller.hostConnected()

Host reactive update cycle:
  → controller.hostUpdate()       // before render
  → host.render()
  → controller.hostUpdated()      // after render
  → host.updateComplete resolves

Host disconnectedCallback()
  → controller.hostDisconnected()
```

**Key timing:** If `addController()` is called after the host is already connected, `hostConnected()` fires immediately.

## Writing a Custom Controller

Every controller follows this structure:

```ts
export class MyController implements ReactiveController {
  private _host: ReactiveControllerHost;

  constructor(host: ReactiveControllerHost) {
    this._host = host;
    host.addController(this);
  }

  hostConnected(): void {
    // Setup: listeners, timers, subscriptions, observers
  }

  hostDisconnected(): void {
    // Cleanup: remove everything set up in hostConnected
  }
}
```

### Triggering Host Re-renders

When the controller's state changes, call `this._host.requestUpdate()` to trigger the host's reactive update cycle:

```ts
export class ClockController implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _interval?: ReturnType<typeof setInterval>;
  value = new Date();

  constructor(host: ReactiveControllerHost, private _ms = 1000) {
    this._host = host;
    host.addController(this);
  }

  hostConnected(): void {
    this._interval = setInterval(() => {
      this.value = new Date();
      this._host.requestUpdate();
    }, this._ms);
  }

  hostDisconnected(): void {
    clearInterval(this._interval);
  }
}
```

Usage:

```ts
@customElement('live-clock')
class LiveClock extends LitElement {
  private _clock = new ClockController(this);

  render() {
    return html`<p>${this._clock.value.toLocaleTimeString()}</p>`;
  }
}
```

## Common Patterns

### Media Query Controller

Tracks a CSS media query and re-renders the host when the match state changes.

```ts
export class MediaQueryController implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _mql: MediaQueryList;
  matches: boolean;

  constructor(host: ReactiveControllerHost, query: string) {
    this._host = host;
    this._mql = window.matchMedia(query);
    this.matches = this._mql.matches;
    host.addController(this);
  }

  private _onChange = (e: MediaQueryListEvent) => {
    this.matches = e.matches;
    this._host.requestUpdate();
  };

  hostConnected(): void {
    this._mql.addEventListener('change', this._onChange);
  }

  hostDisconnected(): void {
    this._mql.removeEventListener('change', this._onChange);
  }
}
```

Usage:

```ts
@customElement('responsive-layout')
class ResponsiveLayout extends LitElement {
  private _mobile = new MediaQueryController(this, '(max-width: 768px)');

  render() {
    return this._mobile.matches
      ? html`<mobile-layout></mobile-layout>`
      : html`<desktop-layout></desktop-layout>`;
  }
}
```

### Mouse Position Controller

```ts
export class MouseController implements ReactiveController {
  private _host: ReactiveControllerHost;
  pos = { x: 0, y: 0 };

  constructor(host: ReactiveControllerHost) {
    this._host = host;
    host.addController(this);
  }

  private _onMouseMove = (e: MouseEvent) => {
    this.pos = { x: e.clientX, y: e.clientY };
    this._host.requestUpdate();
  };

  hostConnected(): void {
    window.addEventListener('mousemove', this._onMouseMove);
  }

  hostDisconnected(): void {
    window.removeEventListener('mousemove', this._onMouseMove);
  }
}
```

### IntersectionObserver Controller

```ts
export class IntersectionController implements ReactiveController {
  private _host: ReactiveControllerHost & Element;
  private _observer?: IntersectionObserver;
  isIntersecting = false;

  constructor(host: ReactiveControllerHost & Element, private _options?: IntersectionObserverInit) {
    this._host = host;
    host.addController(this);
  }

  hostConnected(): void {
    this._observer = new IntersectionObserver(([entry]) => {
      this.isIntersecting = entry.isIntersecting;
      this._host.requestUpdate();
    }, this._options);
    this._observer.observe(this._host);
  }

  hostDisconnected(): void {
    this._observer?.disconnect();
  }
}
```

### AbortController Manager

Wraps `AbortController` with automatic cleanup on disconnect — useful for fetch calls outside of Task.

```ts
export class AbortControllerManager implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _controller?: AbortController;

  get signal(): AbortSignal {
    if (!this._controller) {
      this._controller = new AbortController();
    }
    return this._controller.signal;
  }

  constructor(host: ReactiveControllerHost) {
    this._host = host;
    host.addController(this);
  }

  abort(): void {
    this._controller?.abort();
    this._controller = undefined;
  }

  hostDisconnected(): void {
    this.abort();
  }
}
```

## Controller Composition

Controllers can own other controllers. Pass the host through:

```ts
export class DashboardController implements ReactiveController {
  private _host: ReactiveControllerHost;
  readonly clock: ClockController;
  readonly media: MediaQueryController;

  constructor(host: ReactiveControllerHost) {
    this._host = host;
    this.clock = new ClockController(host);
    this.media = new MediaQueryController(host, '(prefers-color-scheme: dark)');
    host.addController(this);
  }
}
```

A component can also use multiple independent controllers:

```ts
@customElement('my-dashboard')
class MyDashboard extends LitElement {
  private _clock = new ClockController(this);
  private _mobile = new MediaQueryController(this, '(max-width: 768px)');
  private _mouse = new MouseController(this);

  render() {
    return html`
      <p>Time: ${this._clock.value.toLocaleTimeString()}</p>
      <p>Mobile: ${this._mobile.matches}</p>
      <p>Mouse: ${this._mouse.pos.x}, ${this._mouse.pos.y}</p>
    `;
  }
}
```

Each controller manages its own lifecycle independently.

## Controllers with Configuration

Accept options to make controllers flexible:

```ts
interface PollingOptions<T> {
  url: string;
  interval?: number;
  transform?: (data: unknown) => T;
}

export class PollingController<T> implements ReactiveController {
  private _host: ReactiveControllerHost;
  private _timer?: ReturnType<typeof setInterval>;
  private _abortController?: AbortController;
  private _options: Required<PollingOptions<T>>;

  value?: T;
  error?: Error;
  loading = false;

  constructor(host: ReactiveControllerHost, options: PollingOptions<T>) {
    this._host = host;
    this._options = {
      interval: 30_000,
      transform: (d) => d as T,
      ...options,
    };
    host.addController(this);
  }

  hostConnected(): void {
    this._poll();
    this._timer = setInterval(() => this._poll(), this._options.interval);
  }

  hostDisconnected(): void {
    clearInterval(this._timer);
    this._abortController?.abort();
  }

  private async _poll(): Promise<void> {
    this._abortController?.abort();
    this._abortController = new AbortController();
    this.loading = true;
    this._host.requestUpdate();
    try {
      const res = await fetch(this._options.url, { signal: this._abortController.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.value = this._options.transform(await res.json());
      this.error = undefined;
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        this.error = e as Error;
      }
    } finally {
      this.loading = false;
      this._host.requestUpdate();
    }
  }
}
```

## When to Use Controllers vs Alternatives

| Need | Use | Why |
|------|-----|-----|
| Reusable lifecycle-aware logic | **Controller** | Encapsulated, composable, multiple instances per host |
| Shared properties/methods across component classes | **Mixin** | Extends the class prototype, single instance per class |
| Fundamental component behavior all subclasses inherit | **Base class** | Direct inheritance, strongest coupling |
| One-shot async operation tied to reactive inputs | **Task** | Built-in status tracking, cancellation, args watching |
| Ongoing external resource (timer, observer, listener) | **Custom controller** | Clean connect/disconnect lifecycle management |
| Cross-component shared state without prop drilling | **`@lit/context`** | Provider/consumer pattern through the DOM tree |

### Key Decision: Controller vs Task

- **Task** is the right choice when: you have a request/response pattern, the operation is triggered by reactive input changes, and you need status states (loading/error/complete) in the template.
- **Custom controller** is the right choice when: you have an ongoing resource (timer, WebSocket, observer), you need to manage setup/teardown tied to DOM connection, or Task's args-based re-execution model doesn't fit.

## Best Practices

- **Always call `addController(this)` in the constructor** — ensures lifecycle hooks fire even if the host is already connected
- **Always clean up in `hostDisconnected`** — remove listeners, clear timers, abort fetches, disconnect observers
- **Type the host as `ReactiveControllerHost`** — not `LitElement`; this keeps controllers framework-agnostic and testable
- **Expose state as public readonly fields** — the host reads `controller.value`, not via callbacks or events
- **Call `this._host.requestUpdate()`** after any state change the host needs to render
- **Don't access the host's reactive properties** — controllers should be generic; pass data in via constructor options or method arguments
- **Prefer arrow functions or bound methods** for event handlers to avoid `this` binding issues in callbacks
