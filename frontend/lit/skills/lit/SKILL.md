---
name: lit
description: >
  Lit web component library: LitElement, reactive properties, templates,
  reactive controllers, @lit/task, @lit/context, directives, Shadow DOM
  a11y. Load when authoring or reviewing any file importing from 'lit',
  'lit/decorators.js', '@lit/task', '@lit/context', or 'lit/directive.js'
  — including alongside a router or design-system skill, which cover
  different ground.
---

# Lit Web Component Library

Lit is a lightweight (~5 KB) library for building standard web components — native browser support, framework-agnostic, interoperable. Three pillars: reactive state, declarative `html` templates (no virtual DOM), and Shadow DOM style scoping.

## Scope

Covers: `LitElement`, reactive properties (`@property` / `@state`), `html` and `css` tagged templates, lifecycle, decorators, `@lit/task`, reactive controllers, `@lit/context`, form-associated elements, `ElementInternals`, custom directives, Shadow DOM accessibility (ARIA, focus management), and testing.

## Instructions

### Creating a new Lit component

1. Import `LitElement`, `html`, `css` from `lit` and decorators from `lit/decorators.js`
2. Apply `@customElement('tag-name')` — tag name must contain a dash
3. Define `static styles` using the `css` tagged template
4. Add reactive properties with `@property()` (public API) or `@state()` (internal)
5. Implement `render()` returning an `html` tagged template
6. Register the element in `HTMLElementTagNameMap` via `declare global`

Consult [references/reactive-properties.md](references/reactive-properties.md) for property options, type conversion, and decorators.
Consult [references/code-examples.md](references/code-examples.md) for full component patterns.

### Adding async data fetching

1. Install `@lit/task`: `npm i @lit/task`
2. Create a `Task` field with `task` (async function) and `args` (reactive inputs)
3. Always pass `{ signal }` to `fetch` for automatic cancellation
4. Use `this._task.render({ pending, complete, error })` in `render()`
5. Set `autoRun: false` and call `.run()` manually if the task should not run on every args change

Consult [references/task-controller.md](references/task-controller.md) for the full API, argument tracking, and advanced patterns.

### Dispatching events from a component

1. Define a concrete event class extending `Event` with a `static readonly type` and typed properties
2. Set `bubbles: true, composed: true` in the constructor so events cross Shadow DOM
3. Dispatch after `await this.updateComplete` so listeners see the rendered state
4. Export the event class so consumers can import it for type-safe listening

Consult [references/reactive-properties.md](references/reactive-properties.md) for the typed event pattern.

### Writing a reactive controller

1. Create a class implementing `ReactiveController` with a constructor that accepts `ReactiveControllerHost` and calls `host.addController(this)`
2. Implement `hostConnected()` for setup (listeners, timers, observers) and `hostDisconnected()` for cleanup
3. Expose state as public fields; call `this._host.requestUpdate()` when state changes
4. Type the host as `ReactiveControllerHost` (not `LitElement`) to keep the controller framework-agnostic
5. Use Task for request/response async; use a custom controller for ongoing resources (timers, WebSockets, observers)

Consult [references/reactive-controllers.md](references/reactive-controllers.md) for interfaces, lifecycle integration, common patterns, and composition.

### Sharing state with context

1. Install `@lit/context`: `npm i @lit/context`
2. Define contexts in a shared module using `createContext<T>(Symbol('key'))` — always use `Symbol` for uniqueness
3. Use `@provide({ context })` with `@property({ attribute: false })` on a provider component
4. Use `@consume({ context, subscribe: true })` with `@property({ attribute: false })` on consumers — `subscribe: true` is required for runtime updates
5. Add `ContextRoot` to the app shell if providers may load after consumers (lazy loading, dynamic rendering)

Consult [references/context.md](references/context.md) for the full API, nested providers, `ContextRoot`, pitfalls, and context vs signals vs properties guidance.

### Adding fine-grained reactivity with signals

1. Install `@lit-labs/signals`: `npm i @lit-labs/signals` — Labs package, flag the experimental status to the user
2. Create signals at module scope with `signal(initial)`; read via `.get()`, write via `.set()`
3. Apply `SignalWatcher(LitElement)` mixin to any element that reads signals
4. Use the `html` tag from `@lit-labs/signals` for implicit watching, or the `watch(signal)` directive for pinpoint updates
5. For shared deep-reactive state, wrap a signal in `@lit/context` instead of using `subscribe: true`

Consult [references/signals.md](references/signals.md) for the full API, rendering patterns, context integration, and pitfalls.

### Making a form-associated component

1. Add `static formAssociated = true` and `private _internals = this.attachInternals()`
2. Call `this._internals.setFormValue()` in every input handler and whenever the value changes
3. Implement constraint validation with `setValidity()`, providing the anchor element for validation popups
4. Implement `formResetCallback()` to clear internal state when the form resets
5. Use `this._internals.role` and `this._internals.ariaLabel` for accessible ARIA (not ID-based attributes)

Consult [references/forms-and-element-internals.md](references/forms-and-element-internals.md) for the full API, lifecycle callbacks, validation, and a complete example.
Consult [references/accessibility.md](references/accessibility.md) for focus management, keyboard interaction, and screen reader patterns.

### Testing a Lit component

1. Install `vitest` and `happy-dom`: `npm i -D vitest happy-dom`
2. Configure `vitest.config.ts` with `environment: 'happy-dom'`
3. Import the component module for side effects, then create elements with `document.createElement()` and append to the DOM
4. After any property change, `await el.updateComplete` before asserting on DOM content
5. Query shadow DOM with `el.shadowRoot!.querySelector()` — not `el.querySelector()` (that's light DOM)

Consult [references/testing.md](references/testing.md) for a reusable `fixture()` helper, event testing, context providers, Task state testing, and common pitfalls.

## When to Use Each Concept

**Default to `@property` for inputs and typed events for outputs.** Reach for context, signals, or controllers only when that pattern would force prop-drilling through 3+ intermediate components, lose reactivity across boundaries, or duplicate the same lifecycle logic in multiple components. The table below lists the escape hatches and the specific condition that justifies each.

| Scenario | Use | Why |
|----------|-----|-----|
| External component input | `@property()` | Formal API with attribute binding |
| Private render-driving state | `@state()` | No attribute; triggers updates |
| Async data (fetch, DB) | `Task` | Status tracking, cancellation, race prevention |
| Ongoing external resource (timer, observer, WebSocket) | Reactive controller | Lifecycle-aware setup/teardown, composable, reusable |
| Reusable cross-component behavior | Reactive controller | Has-a composition; multiple instances per host |
| Derived/computed values | `willUpdate()` | Computed once per cycle, before render |
| One-time DOM setup | `firstUpdated()` | DOM guaranteed to exist |
| Post-render side effects | `updated()` | DOM reflects latest state |
| Dynamic CSS classes | `classMap()` | Clean conditional class binding |
| Dynamic inline styles | `styleMap()` | Direct property binding |
| Efficient list rendering | `repeat()` with key | Minimizes DOM churn on reorder |
| External style customization | CSS custom properties | Pierce Shadow DOM cleanly |
| Parent-child data flow (any depth that's still tractable) | `@property` down, typed events up | Default Lit pattern — explicit, type-safe, no extra primitives |
| Value needed by descendants 3+ levels deep, rarely changes | `@lit/context` (no `subscribe`) | Avoids prop drilling once intermediate components have nothing to do with the value |
| Same shared value but changes at runtime | `@lit/context` with `subscribe: true` | Consumers stay in sync; tolerable when changes are infrequent |
| Shared value changes frequently AND needs fine-grained updates | `@lit-labs/signals` (often via context) | Pinpoint DOM updates without full re-render or subscribe re-fire |
| Custom element inside a `<form>` | Form-associated + `ElementInternals` | Enables form submission, validation, reset |
| Reusable template transformation | Custom directive | Direct DOM Part access, async lifecycle |
| Testing component behavior | Vitest + happy-dom + `fixture()` helper | Fast unit tests with DOM simulation |

## Core Rules

These cross-cutting rules influence which path Claude takes on most Lit tasks. API-specific guidance lives in the topic references below.

- **New references for mutations** — never mutate `@property`/`@state`/context objects or arrays in place. Lit's change detection is reference equality (`!==`), so in-place mutations don't trigger updates. Use spread/assignment, or call `requestUpdate()` if you must mutate.
- **`render()` must be pure** — no side effects, no property mutations, no DOM reads. Move derived state to `willUpdate()`, post-render side effects to `updated()`.
- **`willUpdate()` for derived state** — computed once per cycle, before render. Not `render()` (impure) and not `updated()` (causes a second cycle).
- **Dispatch events after `await this.updateComplete`** — listeners see the fully rendered state, not a stale DOM.
- **Always call `super`** in `constructor`, `connectedCallback`, and `disconnectedCallback`. Lit relies on the base class running its own setup/teardown.
- **Reach for a reactive controller** when behavior is reusable across components or owns ongoing resources (timers, observers, sockets). Reach for `Task` when it's a request/response. Reach for inline lifecycle hooks only for one-off, component-specific logic.

## Examples

Example 1: User says "create a user card component"
Actions:
1. Scaffold a `@customElement('user-card')` with `@property()` for `name`, `email`
2. Add scoped styles via `static styles`
3. Implement `render()` with property bindings
4. Add `declare global` for `HTMLElementTagNameMap`
Result: A typed, styled, self-contained web component

Example 2: User says "fetch user data in my Lit component"
Actions:
1. Add `@lit/task` import
2. Create a `Task` with `args: () => [this.userId]` and `{ signal }` in the fetch call
3. Use `_task.render({ pending, complete, error })` for loading/error states
Result: Async data fetching with automatic cancellation and status UI

Example 3: User says "my component isn't re-rendering when I push to an array"
Actions:
1. Identify the array mutation (`this.items.push(...)`)
2. Replace with immutable update: `this.items = [...this.items, newItem]`
3. Explain Lit's reference-equality change detection
Result: Component re-renders correctly on array changes

## Troubleshooting

Each reference below has a "Common Pitfalls" section covering the bugs specific to its API. Route by symptom:

| Symptom | Reference |
|---------|-----------|
| Component not re-rendering, stale DOM after mutation | [reactive-properties.md](references/reactive-properties.md) |
| Custom event not received, doesn't cross Shadow DOM | [reactive-properties.md](references/reactive-properties.md) |
| Styles leaking, missing `:host`, inline handler issues | [templates-and-directives.md](references/templates-and-directives.md) |
| Task runs every render, stale results, never runs | [task-controller.md](references/task-controller.md) |
| Form ignores component, value missing, doesn't reset | [forms-and-element-internals.md](references/forms-and-element-internals.md) |
| ARIA not announced, focus issues, `aria-labelledby` broken | [accessibility.md](references/accessibility.md) |
| Lifecycle ordering, `updateComplete` timing | [lifecycle.md](references/lifecycle.md) |
| Context value not updating, `@consume` stuck on initial | [context.md](references/context.md) |
| Signal change doesn't update DOM, polyfill mismatch | [signals.md](references/signals.md) |
| Test stale, fixture not awaiting, mocked fetch leaks | [testing.md](references/testing.md) |

## Topic References

Consult these for detailed API, options, patterns, and code examples:

- [Reactive Properties](references/reactive-properties.md) — `@property()` options, `@state()`, type conversion, custom converters, mutation rules, decorators, `HTMLElementTagNameMap`, typed events
- [Templates & Directives](references/templates-and-directives.md) — binding types (attribute, boolean, property, event), full directive catalog, conditional rendering, styles, `nothing`
- [Lifecycle](references/lifecycle.md) — complete method sequence, `updateComplete`, `changedProperties`, async patterns
- [Reactive Controllers](references/reactive-controllers.md) — `ReactiveController` interface, lifecycle hooks, custom controllers, composition, controller vs mixin vs Task
- [Context](references/context.md) — `@lit/context` API, `@provide`/`@consume`, `ContextRoot`, nested providers, context vs signals vs properties
- [Signals](references/signals.md) — `@lit-labs/signals` (Labs), `SignalWatcher` mixin, `watch()` directive, signals `html` tag, `effect()`, context integration
- [Task Controller](references/task-controller.md) — `@lit/task` API, status states, auto-run vs manual, cancellation, race conditions, argument tracking
- [Code Examples](references/code-examples.md) — canonical component patterns: basic, forms, Task fetch, slots, theming, parent-child, lists
- [Forms & ElementInternals](references/forms-and-element-internals.md) — form-associated custom elements, `setFormValue()`, constraint validation, form lifecycle callbacks, ARIA via AOM
- [Custom Directives](references/custom-directives.md) — `Directive`, `AsyncDirective`, `noChange` vs `nothing`, Part types, `setValue()`, async lifecycle
- [Accessibility](references/accessibility.md) — Shadow DOM ARIA patterns, `ElementInternals` AOM, focus management, `delegatesFocus`, roving tabindex, keyboard interaction, focus trapping
- [Testing](references/testing.md) — Vitest + happy-dom, `fixture()` helper, `updateComplete`, event testing, context providers, Task state testing
