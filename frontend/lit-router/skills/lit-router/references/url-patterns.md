# URL Patterns — Deep Dive

`@lit-labs/router` matches routes using the standard [`URLPattern`](https://developer.mozilla.org/docs/Web/API/URLPattern) API. A route's `path` string is compiled to `new URLPattern({pathname: path})` lazily on first match and cached per route via a `WeakMap`. For full control over host/protocol/search/hash matching, supply a pre-built `pattern: URLPattern` instead of `path`.

## Pattern syntax

| Syntax | Meaning |
|---|---|
| `/users` | Literal match |
| `/users/:id` | Named group → `params.id` |
| `/users/:id?` | Optional named group → `params.id` is `string \| undefined` |
| `/files/*` | Wildcard tail group → `params['0']` holds the captured tail |
| `/users/:id(\\d+)` | Named group with regex constraint (only digits) |
| `/a/:b/c/:d` | Multiple named groups |
| `/items/:type(books\|movies)` | Named group with regex alternation |
| `/users/*` | Nested-mount wildcard — see [nested-routing.md](nested-routing.md) |

Per recent CHANGELOG, unmatched optional groups now resolve to `undefined` (not empty string), so always treat `params[name]` as `string | undefined`.

## `params` shape

`params` is the `pathname.groups` object produced by `URLPattern.exec`:

```ts
type Params = { [key: string]: string | undefined };
```

Inside a route's `render` and `enter`, params are passed as the first argument:

```ts
{
  path: '/users/:id',
  render: ({id}) => html`<user-page .id=${id}></user-page>`,
}
```

Outside (from elsewhere on the host), read them via the controller:

```ts
const id = this._routes.params.id;   // string | undefined
```

## Wildcards and tail groups

A trailing `/*` produces a numbered group (string keys `'0'`, `'1'`, …). The router's internal `getTailGroup` helper picks the highest-numbered numeric key and treats that string as the path forwarded to child controllers. This is the mechanism that powers nested routing:

```ts
{path: '/users/*', render: () => html`<users-section></users-section>`}
// At /users/42 — params = {'0': '42'}
// Child Routes inside <users-section> receives '42' as its pathname.
```

You can also read the wildcard group directly if you need it:

```ts
{
  path: '/files/*',
  render: ({0: filePath}) => html`<file-viewer path=${filePath ?? ''}></file-viewer>`,
}
```

## Pre-built `URLPattern` (host/protocol matching)

If you need to match more than `pathname`, build the pattern yourself:

```ts
{
  pattern: new URLPattern({
    protocol: 'https',
    hostname: 'admin.example.com',
    pathname: '/dashboard/:section',
  }),
  render: ({section}) => html`<admin-dashboard section=${section ?? ''}></admin-dashboard>`,
}
```

The router calls `pattern.exec({pathname})` internally, but a multi-component `URLPattern` matches against the current URL as a whole. Useful for subdomain-aware routing in single-bundle apps.

## Browser support and the polyfill

`URLPattern` is implemented in Chrome / Edge / Chromium-based browsers natively, and Firefox and Safari are catching up (approaching Baseline 2025). For older targets, install and import the polyfill **before** `@lit-labs/router`:

```bash
npm install urlpattern-polyfill
```

```ts
import 'urlpattern-polyfill';
import {Router, Routes} from '@lit-labs/router';
```

The package source contains a triple-slash directive `/// <reference types="urlpattern-polyfill" />`, so even if your TS lib doesn't include `URLPattern`, installing `urlpattern-polyfill` as a devDependency provides the types.

## TypeScript narrowing

The router types `params` as `{[key: string]: string | undefined}`. Two patterns to narrow:

### Inline cast

```ts
const userRoute: PathRouteConfig = {
  path: '/users/:id',
  render: (params) => {
    const {id} = params as {id: string};
    return html`<user-detail .id=${id}></user-detail>`;
  },
};
```

### Generic helper

```ts
import type {PathRouteConfig} from '@lit-labs/router';

const route = <P extends Record<string, string>>(
  path: string,
  render: (params: P) => unknown
): PathRouteConfig => ({path, render: (p) => render(p as P)});

const r = route<{id: string}>('/users/:id', ({id}) => html`<user-detail .id=${id}></user-detail>`);
```

For optional groups, type the field as optional:

```ts
type EditParams = {id: string; section?: string};
{path: '/users/:id/:section?', render: (p) => render(p as EditParams)}
```

## Common Pitfalls

- **All param values are `string | undefined`.** Coerce to numbers explicitly (`Number(id)`) and validate.
- **Optional groups resolve to `undefined`, not `''`.** Old code that `.length`-checked params will break — use `id ?? ''` or explicit `undefined` checks.
- **Trailing slashes are literal.** `/users/*` does not match `/users` — see [pitfalls.md](pitfalls.md) and [nested-routing.md](nested-routing.md).
- **Regex constraints use string-escaped backslashes.** In a JS string, write `'/users/:id(\\d+)'` (double-backslash). In a template literal, `` `/users/:id(\\d+)` ``.
- **`URLPattern` only matches `pathname` via the `path` field.** To match search params, hash, or origin, use `pattern: new URLPattern({...})` — and note that **hash routing is not supported** because the router never inspects `location.hash` (see [pitfalls.md](pitfalls.md)).
- **`URLPattern is not defined`.** You're on a browser without native support and forgot to import `urlpattern-polyfill` before `@lit-labs/router`. Order matters.

See also: [api.md](api.md) for `RouteConfig` shapes, [nested-routing.md](nested-routing.md) for how the wildcard tail group flows into child routers.
