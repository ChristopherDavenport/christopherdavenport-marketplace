# Immutability & Data — Deep Dive

TypeScript provides several tools for marking data as immutable: `readonly` field modifiers, `ReadonlyArray<T>`, `Readonly<T>`, `as const`. The runtime adds `Object.freeze` and the modern "to-" array methods (`toSorted`, `toReversed`, `toSpliced`, `with`). This file covers what each tool does, when to reach for it, and the patterns for immutable updates.

Immutability is a tool, not a religion. Use it when it earns its keep:
- **Signaling intent** — a `readonly` parameter says "I won't mutate this," which is useful documentation.
- **Catching unintended mutation** — the compiler fails when you accidentally try to write through a `readonly` reference.
- **Avoiding aliasing bugs** — when multiple references share a value, mutation through one surprises the others.
- **Predictability in shared/concurrent contexts** — immutable data is safe to pass around without defensive copying.

For purely local data (a builder accumulating into a `string[]`, a counter), mutation is fine. Reach for `readonly` when one of the four reasons above applies.

## `readonly` Field Modifier

Mark fields, parameters, and return types as `readonly` whenever they shouldn't change after construction:

```ts
type User = {
  readonly id: string;
  readonly name: string;
  readonly email: string;
};

const u: User = { id: "1", name: "alice", email: "a@x" };
u.name = "bob";   // Error: cannot assign to 'name' because it is a read-only property
```

`readonly` is **shallow**. A `readonly` field can still be a mutable nested object:

```ts
type Settings = {
  readonly options: { dark: boolean };
};
const s: Settings = { options: { dark: false } };
s.options = { dark: true };       // Error
s.options.dark = true;            // OK — the inner object is mutable
```

For "actually deeply immutable," use `Readonly<T>` recursively or define `DeepReadonly<T>` (below).

## `ReadonlyArray<T>` and `readonly T[]`

These are the same type, two syntaxes:

```ts
function sum(xs: ReadonlyArray<number>): number {
  return xs.reduce((a, b) => a + b, 0);
}

function sum2(xs: readonly number[]): number {
  return xs.reduce((a, b) => a + b, 0);
}
```

`ReadonlyArray<T>` exposes only non-mutating methods (`map`, `filter`, `reduce`, `slice`, `concat`, `find`, `findIndex`, `includes`, `indexOf`, `join`, `at`, `every`, `some`, `flat`, `flatMap`, `forEach`, plus the new `toSorted`/`toReversed`/`toSpliced`/`with`). It hides mutators (`push`, `pop`, `shift`, `unshift`, `splice`, `sort`, `reverse`, `fill`, `copyWithin`).

**Prefer `ReadonlyArray<T>` / `readonly T[]` for parameters that you don't mutate** — it documents the contract and catches accidental mutation. For internal builders or genuinely local mutation, plain `T[]` is fine.

A common surprise: `readonly T[]` is **not** assignable to `T[]`, but `T[]` *is* assignable to `readonly T[]`. The narrower (mutable) type goes into the wider (readonly) hole, not the reverse.

```ts
const mutable: number[] = [1, 2, 3];
const ro: readonly number[] = mutable;          // OK
const back: number[] = ro;                       // Error
const back2: number[] = [...ro];                 // OK — make a fresh mutable copy
```

## `ReadonlyMap<K, V>` and `ReadonlySet<T>`

Same idea for `Map` and `Set`:

```ts
function size(m: ReadonlyMap<string, number>): number {
  return m.size;
}

function has(s: ReadonlySet<string>, x: string): boolean {
  return s.has(x);
}
```

These types expose `get`, `has`, `size`, iteration, and forbid `set`, `delete`, `clear`. Use them at module boundaries to signal "I will not mutate this collection."

## `Readonly<T>`

`Readonly<T>` is a built-in mapped type that adds `readonly` to every top-level field of `T`:

```ts
type User = { id: string; name: string };
type RoUser = Readonly<User>;
//   ^? { readonly id: string; readonly name: string }

function freeze(u: User): Readonly<User> {
  return u;
}
```

Like the `readonly` modifier, `Readonly<T>` is **shallow**. It does not recurse.

## `DeepReadonly<T>`

For deep immutability at the type level, write a recursive utility:

```ts
type DeepReadonly<T> =
  T extends Function           ? T :
  T extends ReadonlyMap<infer K, infer V> ? ReadonlyMap<DeepReadonly<K>, DeepReadonly<V>> :
  T extends ReadonlySet<infer V>          ? ReadonlySet<DeepReadonly<V>> :
  T extends readonly (infer E)[]          ? readonly DeepReadonly<E>[] :
  T extends object             ? { readonly [K in keyof T]: DeepReadonly<T[K]> } :
  T;

type Config = {
  servers: { host: string; port: number }[];
  flags: { feature: { enabled: boolean } };
};

type FrozenConfig = DeepReadonly<Config>;
//   ^ readonly arrays + readonly fields all the way down
```

Reach for this on configuration objects, parser results, immutable state trees, and other "this should never change once built" structures. Skip it on small objects where a single `Readonly<T>` is enough.

## `as const` for Literal Immutability

`as const` makes an entire literal expression `readonly` and locks each literal to its narrowest type:

```ts
const direction = ["north", "south", "east", "west"] as const;
//    ^? readonly ["north", "south", "east", "west"]

type Direction = typeof direction[number];
//   ^ "north" | "south" | "east" | "west"

const config = {
  host: "localhost",
  port: 8080,
  features: ["auth", "logging"],
} as const;
//   ^ all fields readonly; "localhost" stays narrow; features is readonly tuple
```

`as const` is the **single most useful immutability tool** for compile-time data: configuration constants, enum-like value sets, lookup tables. Combined with `typeof X[number]` you derive a union type from the data — one source of truth.

## Immutable Update Patterns

Mutation is easy. Immutable updates require a tiny bit of syntax. The patterns:

### Object update — spread + override

```ts
type User = { id: string; name: string; age: number };

const u: User = { id: "1", name: "alice", age: 30 };

const renamed = { ...u, name: "bob" };          // change one field
const aged    = { ...u, age: u.age + 1 };       // increment a field
const merged  = { ...u, ...partialUpdate };     // merge in a partial
```

The spread copies one level. For nested updates, spread at each level:

```ts
type Doc = { meta: { title: string; tags: string[] }; body: string };

const updated: Doc = {
  ...doc,
  meta: { ...doc.meta, title: "new title" },
};
```

### Object key delete — destructure

```ts
const { password, ...withoutPassword } = user;   // omit a key without mutating
```

### Array prepend / append

```ts
const prepended = [x, ...arr];
const appended  = [...arr, x];
const inserted  = [...arr.slice(0, i), x, ...arr.slice(i)];
```

### Array update at index

```ts
const updated = arr.map((v, idx) => idx === i ? newValue : v);
// or, modern:
const updated2 = arr.with(i, newValue);
```

### Array filter / remove

```ts
const removed = arr.filter((_, idx) => idx !== i);
const without = arr.filter((v) => v.id !== targetId);
```

## The "to-" Methods (ES2023)

Modern JavaScript shipped immutable counterparts to the mutating array methods:

| Mutating | Immutable | Returns |
|---|---|---|
| `arr.sort()` | `arr.toSorted()` | new sorted array |
| `arr.reverse()` | `arr.toReversed()` | new reversed array |
| `arr.splice(i, n, ...items)` | `arr.toSpliced(i, n, ...items)` | new array with splice applied |
| `arr[i] = v` | `arr.with(i, v)` | new array with index `i` replaced |

```ts
const original = [3, 1, 2];
const sorted   = original.toSorted();   // [1, 2, 3]
// original is still [3, 1, 2]

const arr = [1, 2, 3];
const updated = arr.with(1, 99);        // [1, 99, 3]
```

Use these instead of copy-then-mutate (`[...arr].sort()`). Cleaner and the intent is explicit.

## `Object.freeze` vs `readonly`

`readonly` is **compile-time** — it disappears at runtime, doesn't prevent mutation by anything that ignores types (e.g., `(x as any).field = ...`, JSON deserializers, other JS code).

`Object.freeze(x)` is **runtime** — it actually prevents writes. In strict mode, writes throw; in sloppy mode, they fail silently.

```ts
const ro: Readonly<{ a: number }> = { a: 1 };
(ro as { a: number }).a = 2;     // No compile error (we cast). Runtime: succeeds.

const frozen = Object.freeze({ a: 1 });
(frozen as { a: number }).a = 2; // Runtime: TypeError (strict mode)
```

For configuration values, security-sensitive constants, or anything you genuinely want to prevent any code (including third parties) from mutating, combine both:

```ts
const config = Object.freeze({
  host: "localhost",
  port: 8080,
} as const);
```

`as const` gives compile-time readonly + narrow types; `Object.freeze` gives runtime immutability.

`Object.freeze` is **shallow**. For deep freezing, recurse:

```ts
function deepFreeze<T extends object>(o: T): Readonly<T> {
  for (const v of Object.values(o)) {
    if (v && typeof v === "object" && !Object.isFrozen(v)) {
      deepFreeze(v);
    }
  }
  return Object.freeze(o);
}
```

## Common Pitfalls

- **Forgetting that `readonly` is shallow.** `readonly meta: { title: string }` lets you reassign `meta.title`. Use `DeepReadonly<T>` or per-field `readonly` markers when nesting matters.
- **`readonly T[]` ↔ `T[]` assignability surprise.** Mutable arrays are assignable to `readonly` (widening). The reverse requires a copy: `[...readOnlyArr]`.
- **Using `Object.assign({}, x, update)` instead of `{ ...x, ...update }`.** They do the same thing, but the spread form is more idiomatic and reads better.
- **Annotating constants without `as const`.** `const config: Config = { host: "a" }` widens `host` to `string`. `const config = { host: "a" } as const satisfies Config` keeps it narrow *and* validates.
- **Calling mutating methods on a `readonly T[]` via `as`.** Don't escape the type system. If you genuinely need to mutate, copy first: `const mutable = [...ro]`.
- **Deep clone via `JSON.parse(JSON.stringify(x))`.** Loses Dates, Maps, Sets, Symbols, undefined fields, and class instances. Use `structuredClone(x)` if you need a runtime deep copy of a structured-cloneable value.
- **Building immutability into class fields with `readonly` instead of using plain objects.** Classes work, but a `type` + `readonly` is simpler and composes with mapped/conditional types. Reach for classes only when you need methods, identity, or interop with class-based APIs.
- **Freezing the object but not the arrays inside it.** `Object.freeze` is shallow. Either `deepFreeze` or be intentional about which level matters.
- **Mutating a returned value that the producer didn't expect to be mutated.** If the producer returns the same instance to multiple callers, mutation surprises them. When in doubt, copy first or use a `readonly` return type to make the contract explicit.
- **Copying arrays with `Array.from(arr)` when `[...arr]` would do.** Both work. The spread form is shorter and more idiomatic for arrays.
