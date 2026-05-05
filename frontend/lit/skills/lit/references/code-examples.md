# Code Examples — Canonical Patterns

## Basic Component

```ts
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('greeting-card')
class GreetingCard extends LitElement {
  static styles = css`
    :host { display: block; padding: 16px; border: 1px solid #ccc; border-radius: 8px; }
    h2 { margin: 0 0 8px; }
  `;

  @property() name = '';
  @property({ type: Number }) age = 0;

  render() {
    return html`
      <h2>Hello, ${this.name}!</h2>
      <p>Age: ${this.age}</p>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'greeting-card': GreetingCard;
  }
}
```

## Component with Internal State and Events

```ts
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export class CountChangedEvent extends Event {
  static readonly type = 'count-changed';
  constructor(public readonly count: number) {
    super(CountChangedEvent.type, { bubbles: true, composed: true });
  }
}

@customElement('counter-button')
class CounterButton extends LitElement {
  static styles = css`
    button { padding: 8px 16px; font-size: 16px; cursor: pointer; }
    span { margin-left: 8px; }
  `;

  @property({ type: Number }) initial = 0;
  @state() private _count = 0;

  connectedCallback() {
    super.connectedCallback();
    this._count = this.initial;
  }

  private _increment() {
    this._count++;
    this.dispatchEvent(new CountChangedEvent(this._count));
  }

  render() {
    return html`
      <button @click=${this._increment}>+</button>
      <span>${this._count}</span>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'counter-button': CounterButton;
  }
}
```

## Form Handling

```ts
import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';

export interface LoginDetail {
  email: string;
  password: string;
}

export class LoginSubmitEvent extends Event {
  static readonly type = 'login-submit';
  constructor(public readonly detail: LoginDetail) {
    super(LoginSubmitEvent.type, { bubbles: true, composed: true });
  }
}

@customElement('login-form')
class LoginForm extends LitElement {
  static styles = css`
    form { display: flex; flex-direction: column; gap: 12px; max-width: 300px; }
    input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
    button { padding: 8px; cursor: pointer; }
    .error { color: red; font-size: 14px; }
  `;

  @state() private _error = '';
  @query('#email') private _emailInput!: HTMLInputElement;

  private async _onSubmit(e: SubmitEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    this.dispatchEvent(new LoginSubmitEvent({
      email: data.get('email') as string,
      password: data.get('password') as string,
    }));
  }

  firstUpdated() {
    this._emailInput.focus();
  }

  render() {
    return html`
      <form @submit=${this._onSubmit}>
        <input id="email" name="email" type="email" placeholder="Email" required>
        <input name="password" type="password" placeholder="Password" required>
        ${this._error ? html`<p class="error">${this._error}</p>` : ''}
        <button type="submit">Log In</button>
      </form>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'login-form': LoginForm;
  }
}
```

## Data Fetching with Task

```ts
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { Task } from '@lit/task';

@customElement('user-profile')
class UserProfile extends LitElement {
  static styles = css`
    :host { display: block; }
    .loading { color: #999; }
    .error { color: red; }
    .profile { padding: 16px; border: 1px solid #eee; border-radius: 8px; }
  `;

  @property() userId = '';

  private _userTask = new Task(this, {
    task: async ([userId], { signal }) => {
      const res = await fetch(`/api/users/${userId}`, { signal });
      if (!res.ok) throw new Error(`Failed to load user: ${res.status}`);
      return res.json() as Promise<{ name: string; email: string; role: string }>;
    },
    args: () => [this.userId]
  });

  render() {
    return this._userTask.render({
      pending: () => html`<p class="loading">Loading profile...</p>`,
      complete: (user) => html`
        <div class="profile">
          <h2>${user.name}</h2>
          <p>${user.email}</p>
          <p>Role: ${user.role}</p>
        </div>
      `,
      error: (e) => html`<p class="error">${(e as Error).message}</p>`
    });
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'user-profile': UserProfile;
  }
}
```

## Slots — Default and Named

```ts
import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('card-layout')
class CardLayout extends LitElement {
  static styles = css`
    :host { display: block; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
    .header { padding: 12px 16px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
    .body { padding: 16px; }
    .footer { padding: 12px 16px; background: #fafafa; border-top: 1px solid #ddd; }
  `;

  render() {
    return html`
      <div class="header"><slot name="header"></slot></div>
      <div class="body"><slot></slot></div>
      <div class="footer"><slot name="footer"></slot></div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'card-layout': CardLayout;
  }
}
```

Usage:
```html
<card-layout>
  <h2 slot="header">Title</h2>
  <p>Default slot content goes here.</p>
  <button slot="footer">Action</button>
</card-layout>
```

## CSS Custom Property Theming

```ts
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('theme-button')
class ThemeButton extends LitElement {
  static styles = css`
    :host {
      --btn-bg: #0066cc;
      --btn-color: white;
      --btn-radius: 4px;
      --btn-padding: 8px 16px;
    }
    button {
      background: var(--btn-bg);
      color: var(--btn-color);
      border: none;
      border-radius: var(--btn-radius);
      padding: var(--btn-padding);
      cursor: pointer;
      font-size: inherit;
    }
    button:hover { filter: brightness(1.1); }
    button:active { filter: brightness(0.9); }
  `;

  @property() label = '';

  render() {
    return html`<button><slot>${this.label}</slot></button>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'theme-button': ThemeButton;
  }
}
```

Usage:
```html
<theme-button label="Default"></theme-button>
<theme-button label="Danger" style="--btn-bg: #cc0000;"></theme-button>
<theme-button label="Rounded" style="--btn-radius: 20px;"></theme-button>
```

## Parent-Child Communication

```ts
// events.ts — shared event definitions
export class ItemSelectedEvent extends Event {
  static readonly type = 'item-selected';
  constructor(public readonly item: string) {
    super(ItemSelectedEvent.type, { bubbles: true, composed: true });
  }
}
```

```ts
// parent-list.ts
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { ItemSelectedEvent } from './events.js';
import './list-item.js';

@customElement('parent-list')
class ParentList extends LitElement {
  @state() private _items = ['Apple', 'Banana', 'Cherry'];
  @state() private _selected = '';

  private _onItemSelected(e: ItemSelectedEvent) {
    this._selected = e.item;
  }

  render() {
    return html`
      <p>Selected: ${this._selected || 'none'}</p>
      ${this._items.map(item => html`
        <list-item
          .name=${item}
          ?selected=${item === this._selected}
          @item-selected=${this._onItemSelected}
        ></list-item>
      `)}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'parent-list': ParentList;
  }
}
```

```ts
// list-item.ts
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { ItemSelectedEvent } from './events.js';

@customElement('list-item')
class ListItem extends LitElement {
  static styles = css`
    :host { display: block; padding: 8px; cursor: pointer; }
    :host([selected]) { background: #e3f2fd; }
  `;

  @property() name = '';
  @property({ type: Boolean, reflect: true }) selected = false;

  private _onClick() {
    this.dispatchEvent(new ItemSelectedEvent(this.name));
  }

  render() {
    return html`<div @click=${this._onClick}>${this.name}</div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'list-item': ListItem;
  }
}
```

## List Rendering with `repeat()`

```ts
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

interface TodoItem {
  id: string;
  text: string;
  done: boolean;
}

@customElement('todo-list')
class TodoList extends LitElement {
  static styles = css`
    .done { text-decoration: line-through; color: #999; }
    li { padding: 4px 0; cursor: pointer; }
  `;

  @state() private _todos: TodoItem[] = [];

  private _addTodo(text: string) {
    this._todos = [...this._todos, { id: crypto.randomUUID(), text, done: false }];
  }

  private _toggleTodo(id: string) {
    this._todos = this._todos.map(t =>
      t.id === id ? { ...t, done: !t.done } : t
    );
  }

  private _removeTodo(id: string) {
    this._todos = this._todos.filter(t => t.id !== id);
  }

  render() {
    return html`
      <ul>
        ${repeat(this._todos, (t) => t.id, (t) => html`
          <li class=${t.done ? 'done' : ''} @click=${() => this._toggleTodo(t.id)}>
            ${t.text}
          </li>
        `)}
      </ul>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'todo-list': TodoList;
  }
}
```
