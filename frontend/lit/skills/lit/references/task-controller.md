# @lit/task Controller — Deep Dive

## Installation

```bash
npm install @lit/task
```

## Constructor API

```ts
import { Task } from '@lit/task';

new Task(host, {
  task: async (args: T[], options: { signal: AbortSignal }) => Promise<R>,
  args: () => T[],           // Returns array of arguments; task re-runs when these change
  autoRun: true,             // true (default): run on args change. false: manual only.
  argsEqual: shallowArrayEquals,  // Comparison function for args
  onComplete: (value: R) => void,  // Callback on success (optional)
  onError: (error: Error) => void   // Callback on failure (optional)
});
```

## Status Enum

```ts
import { TaskStatus } from '@lit/task';

TaskStatus.INITIAL   // 0 — Task has never run
TaskStatus.PENDING   // 1 — Task is currently executing
TaskStatus.COMPLETE  // 2 — Task finished successfully
TaskStatus.ERROR     // 3 — Task threw an error
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `status` | `TaskStatus` | Current execution state |
| `value` | `R \| undefined` | Result of last successful execution |
| `error` | `unknown` | Error from last failed execution |

## Methods

### `.render(handlers)`

Primary API for rendering task state in templates:

```ts
this._task.render({
  initial:  () => TemplateResult,           // Optional — shown before first run
  pending:  () => TemplateResult,           // Shown during execution
  complete: (value: R) => TemplateResult,   // Shown on success
  error:    (error: unknown) => TemplateResult  // Shown on failure
})
```

All handlers are optional. If a handler is missing for the current status, nothing renders for that state.

### `.run(args?)`

Manually trigger execution:

```ts
await this._task.run();           // Uses args from args()
await this._task.run([customArg]); // Override args for this run
```

Returns a `Promise` that resolves with the task result or rejects with the error.

## Argument Tracking

### Default: Shallow Array Equality

```ts
import { shallowArrayEquals } from '@lit/task';

// Task won't re-run if args() returns the same values:
args: () => [this.userId, this.page]  // Only re-runs when userId or page changes
```

Compares each element with `===`. Objects/arrays compared by reference.

### Deep Equality

```ts
import { deepArrayEquals } from '@lit/task';

private _task = new Task(this, {
  task: async ([filter]) => search(filter),
  args: () => [this.filterObject],
  argsEqual: deepArrayEquals  // Deep comparison of filter object
});
```

### Custom Equality

```ts
private _task = new Task(this, {
  task: async ([query]) => search(query),
  args: () => [this.query],
  argsEqual: (newArgs, oldArgs) => {
    return newArgs[0].trim().toLowerCase() === oldArgs?.[0]?.trim().toLowerCase();
  }
});
```

## Cancellation & Race Conditions

### How It Works

When `args` change while a task is running:
1. The running task's `AbortSignal` is aborted
2. A new task execution starts with the new args
3. The old task's result is discarded even if it completes

### Passing Signal to Fetch

```ts
private _task = new Task(this, {
  task: async ([id], { signal }) => {
    const res = await fetch(`/api/items/${id}`, { signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
  args: () => [this.itemId]
});
```

### Checking Signal in Long-Running Work

```ts
private _task = new Task(this, {
  task: async ([data], { signal }) => {
    const results = [];
    for (const chunk of splitIntoChunks(data)) {
      if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
      results.push(await processChunk(chunk));
    }
    return results;
  },
  args: () => [this.largeDataset]
});
```

## Error Handling

### Errors in Task Function

Any thrown error sets `status` to `ERROR` and is available via `.error`:

```ts
private _task = new Task(this, {
  task: async ([id], { signal }) => {
    const res = await fetch(`/api/${id}`, { signal });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    return res.json();
  },
  args: () => [this.id]
});
```

### Using `onComplete` and `onError` Callbacks

```ts
private _task = new Task(this, {
  task: async ([id]) => fetchItem(id),
  args: () => [this.id],
  onComplete: (item) => {
    this.dispatchEvent(new ItemLoadedEvent(item));
  },
  onError: (error) => {
    console.error('Failed to load item:', error);
  }
});
```

## Multiple Tasks in One Component

```ts
class DashboardElement extends LitElement {
  @property() userId = '';

  private _userTask = new Task(this, {
    task: async ([id], { signal }) => {
      const res = await fetch(`/api/users/${id}`, { signal });
      return res.json();
    },
    args: () => [this.userId]
  });

  private _postsTask = new Task(this, {
    task: async ([id], { signal }) => {
      const res = await fetch(`/api/users/${id}/posts`, { signal });
      return res.json();
    },
    args: () => [this.userId]
  });

  render() {
    return html`
      <div class="user">
        ${this._userTask.render({
          pending: () => html`<p>Loading user...</p>`,
          complete: (user) => html`<h1>${user.name}</h1>`,
          error: (e) => html`<p>Error: ${e}</p>`
        })}
      </div>
      <div class="posts">
        ${this._postsTask.render({
          pending: () => html`<p>Loading posts...</p>`,
          complete: (posts) => html`
            <ul>${posts.map(p => html`<li>${p.title}</li>`)}</ul>
          `,
          error: (e) => html`<p>Error: ${e}</p>`
        })}
      </div>
    `;
  }
}
```

Both tasks run independently. Changing `userId` re-triggers both.

## Common Pitfalls

### Task runs on every render
**Cause:** `args()` returns a new object or array reference each call. Default `shallowArrayEquals` compares by `===`, so a fresh `{...}` or `[...this.items]` every render makes the task think the args changed.
**Fix:** Reference stable values directly — `args: () => [this.userId, this.page]`. If the input genuinely is an object, switch to `argsEqual: deepArrayEquals` or supply a custom comparator (see "Argument Tracking" above).

### Stale results from a previous request
**Cause:** Not passing `signal` to `fetch`. When args change mid-flight, the old request still resolves and may overwrite the newer one.
**Fix:** Always destructure `signal` from the second arg and pass it to `fetch({ signal })`. The Task wires up the abort plumbing; you just have to forward it.

### Task never runs
**Cause:** `autoRun: false` is set but `.run()` is never called.
**Fix:** Either flip `autoRun` back to its default of `true`, or call `await this._task.run()` explicitly from a handler (see "Manual Mode Pattern" above).

## Manual Mode Pattern

```ts
class SearchElement extends LitElement {
  @state() private _query = '';

  private _searchTask = new Task(this, {
    task: async ([query], { signal }) => {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal });
      return res.json();
    },
    args: () => [this._query],
    autoRun: false
  });

  private _onSubmit = async (e: Event) => {
    e.preventDefault();
    await this._searchTask.run();
  };

  render() {
    return html`
      <form @submit=${this._onSubmit}>
        <input @input=${(e: InputEvent) => this._query = (e.target as HTMLInputElement).value}>
        <button type="submit">Search</button>
      </form>
      ${this._searchTask.render({
        initial: () => html`<p>Enter a search term</p>`,
        pending: () => html`<p>Searching...</p>`,
        complete: (results) => html`
          <ul>${results.map(r => html`<li>${r.title}</li>`)}</ul>
        `,
        error: (e) => html`<p>Search failed: ${e}</p>`
      })}
    `;
  }
}
```
