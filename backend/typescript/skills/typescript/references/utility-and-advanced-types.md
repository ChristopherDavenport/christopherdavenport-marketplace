# Utility & Advanced Types — Deep Dive

The standard library ships ~20 utility types, almost all built from three primitives: `keyof`, conditional types, and mapped types. Knowing what's built in saves you from re-deriving common transformations.

## The Built-In Utility Types You Will Use Constantly

### Object reshapers

| Utility | Effect | Example |
|---|---|---|
| `Partial<T>` | Every field optional | `Partial<{ a: 1; b: 2 }>` → `{ a?: 1; b?: 2 }` |
| `Required<T>` | Every field required | `Required<{ a?: 1 }>` → `{ a: 1 }` |
| `Readonly<T>` | Every field readonly | `Readonly<{ a: 1 }>` → `{ readonly a: 1 }` |
| `Pick<T, K>` | Keep only listed keys | `Pick<User, "id" \| "name">` |
| `Omit<T, K>` | Remove listed keys | `Omit<User, "password">` |
| `Record<K, V>` | Object with keys K, values V | `Record<"a" \| "b", number>` → `{ a: number; b: number }` |

### Union manipulators

| Utility | Effect | Example |
|---|---|---|
| `Exclude<T, U>` | Remove members of U from T | `Exclude<"a" \| "b" \| "c", "a">` → `"b" \| "c"` |
| `Extract<T, U>` | Keep only members of T also in U | `Extract<string \| number, string>` → `string` |
| `NonNullable<T>` | Remove `null` and `undefined` | `NonNullable<string \| null>` → `string` |

### Function inspectors

| Utility | Effect | Example |
|---|---|---|
| `Parameters<T>` | Tuple of parameter types | `Parameters<(a: string, b: number) => void>` → `[string, number]` |
| `ReturnType<T>` | Return type | `ReturnType<() => string>` → `string` |
| `Awaited<T>` | Unwraps Promise (recursively) | `Awaited<Promise<Promise<string>>>` → `string` |

### String manipulators (template literal types)

| Utility | Effect |
|---|---|
| `Uppercase<S>` | `"foo"` → `"FOO"` |
| `Lowercase<S>` | `"FOO"` → `"foo"` |
| `Capitalize<S>` | `"foo"` → `"Foo"` |
| `Uncapitalize<S>` | `"Foo"` → `"foo"` |

**Internalize this list.** When you need a transformation, check the built-ins before writing your own.

## Mapped Types — Iterating Over Keys

A mapped type creates a new object type by transforming the keys and/or values of another:

```ts
type Stringify<T> = {
  [K in keyof T]: string;
};

type X = Stringify<{ a: number; b: boolean }>;
//   ^? { a: string; b: string }
```

The `[K in keyof T]` part says "for each key K of T." The right-hand side defines the new value type.

### Modifiers: `readonly` and `?`

Mapped types can add or remove `readonly` and `?` modifiers using `+` / `-`:

```ts
type Mutable<T>      = { -readonly [K in keyof T]: T[K] };
type Required2<T>    = { [K in keyof T]-?: T[K] };
type ReadonlyDeep<T> = { readonly [K in keyof T]: T[K] extends object ? ReadonlyDeep<T[K]> : T[K] };
```

`Mutable<Readonly<X>>` strips the readonly back off. Useful at construction sites that need to build a value mutably and freeze it on the way out.

### Key Remapping with `as`

You can transform keys, not just values:

```ts
type Getters<T> = {
  [K in keyof T as `get${Capitalize<K & string>}`]: () => T[K];
};

type User    = { id: string; name: string };
type UserGet = Getters<User>;
//   ^? { getId: () => string; getName: () => string }
```

You can also *filter* keys by mapping unwanted ones to `never`:

```ts
type StringFields<T> = {
  [K in keyof T as T[K] extends string ? K : never]: T[K];
};

type User       = { id: string; name: string; age: number };
type StringOnly = StringFields<User>;
//   ^? { id: string; name: string }
```

This is the canonical pattern for "give me only the keys whose values are X."

## Conditional Types and `infer`

Conditional types and `infer` get full coverage in [generics.md](generics.md). Here, the focus is using them in *type-level* code (no functions, just types).

```ts
type If<Cond, Then, Else> = Cond extends true ? Then : Else;

type ArrayOrSelf<T> = T extends readonly unknown[] ? T : T[];

type ElementOrSelf<T> = T extends readonly (infer E)[] ? E : T;

type FirstParam<F> = F extends (first: infer P, ...rest: unknown[]) => unknown ? P : never;
```

Two patterns to know:

**1. Recursive conditional types.** Used for deep transformations:

```ts
type DeepReadonly<T> =
  T extends Function    ? T :
  T extends readonly (infer E)[] ? readonly DeepReadonly<E>[] :
  T extends object      ? { readonly [K in keyof T]: DeepReadonly<T[K]> } :
  T;
```

TypeScript caps recursion depth (currently around 50 nested levels). For very deep structures, the recursion will hit a `Type instantiation is excessively deep` error.

**2. Distribution over unions.** When `T` is a *naked* type parameter and appears in `T extends U ? ...`, the conditional distributes:

```ts
type Box<T> = T extends unknown ? { value: T } : never;

type B = Box<string | number>;
//   ^ { value: string } | { value: number }
```

Wrap in a tuple to suppress: `[T] extends [unknown] ? ...`.

## Template Literal Types

Template literal types let you compute string types from string literals:

```ts
type Greeting = `hello ${string}`;
const g1: Greeting = "hello world";   // OK
const g2: Greeting = "goodbye";       // Error

type CssVar  = `--${string}`;
type EventOn = `on${Capitalize<string>}`;
```

Combined with mapped types, they enable powerful key transformations:

```ts
type EventHandlers<E extends string> = {
  [K in E as `on${Capitalize<K>}`]: (event: K) => void;
};

type H = EventHandlers<"click" | "hover">;
//   ^? { onClick: (event: "click") => void; onHover: (event: "hover") => void }
```

Template literals also work for parsing string formats at the type level — splitting on delimiters, extracting prefixes, etc. Powerful but easy to overuse.

## Recursive Types

Type aliases can refer to themselves:

```ts
type Json =
  | string
  | number
  | boolean
  | null
  | Json[]
  | { [key: string]: Json };

type LinkedList<T> = { value: T; next: LinkedList<T> | null };

type Tree<T> = { value: T; children: Tree<T>[] };
```

Recursive types are how you model JSON, ASTs, file trees, expression languages — anything genuinely tree-shaped.

**Limit:** TypeScript's instantiation depth for recursive types is finite. For a parser of arbitrary nesting depth or a path-resolver of arbitrary string keys, you may hit the limit. Truncate the recursion explicitly with a depth counter:

```ts
type DeepPick<T, Path extends string, Depth extends number = 5> =
  Depth extends 0 ? unknown :
  Path extends `${infer Head}.${infer Rest}` ?
    Head extends keyof T ? DeepPick<T[Head], Rest, Decrement<Depth>> : never :
  Path extends keyof T ? T[Path] : never;
```

(`Decrement` itself is a small recursive type. Keep depth low.)

## When *Not* to Use Type-Level Programming

The same warning from [generics.md](generics.md) applies double here. A clever 40-line conditional-type chain that derives an exact-shape result type is almost always less valuable than:

- A runtime helper with a clear, plain signature, and
- An explicit `as const` annotation at the call site to lock the literal types.

Type-level programming is great for **library authors** building APIs that need to surface precise types to many callers (e.g., a query builder). It is overkill for **application code** where a `Pick<T, K>` does 90% of what an artisan-crafted mapped type does, with 10% of the cognitive overhead.

If you find yourself writing a recursive conditional type to transform application-level data, step back. There's almost certainly a simpler shape (a discriminated union, a `Record<K, V>`, a plain `Array<T>`) that solves the same problem.

## Common Pitfalls

- **Reinventing built-ins.** Writing `type MyPartial<T> = { [K in keyof T]?: T[K] }` instead of `Partial<T>`. Check the standard library first.
- **`Pick`/`Omit` with non-existent keys.** `Pick<User, "missing">` silently produces `{}`. Constrain explicitly: `Pick<User, K extends keyof User ? K : never>` if needed, but usually the type checker flags it elsewhere.
- **Distributive surprise.** `Box<string | number>` becomes `Box<string> | Box<number>`, not `Box<string | number>`. Wrap in `[T]` to suppress, but more often this is what you want — exception, not the rule.
- **Excessively deep recursion.** Conditional types deeper than ~50 levels error out. For deeply nested generic types, add a `Depth extends number` counter and decrement it at each recursion.
- **Mapped type modifiers in the wrong order.** `[K in keyof T]?: T[K]` adds `?`. `[K in keyof T]-?: T[K]` removes `?`. The `+` is implicit. Get the modifier slot wrong and you'll waste 20 minutes wondering why the optionality isn't changing.
- **`Record<string, V>` instead of `Record<K, V>` when K is known.** `Record<string, V>` lets any string in. If you know the keys, list them: `Record<"a" \| "b", V>` — much stronger guarantee.
- **Template literals matching too widely.** `` `${string}` `` matches *any* string. If you need a specific shape, narrow with literal unions: `` `${"GET" | "POST"} ${string}` ``.
- **`Omit` doesn't preserve discriminants.** `Omit<DiscriminatedUnion, "field">` collapses the union into a single intersection. For unions, use a distributive Omit: `type DistOmit<T, K> = T extends unknown ? Omit<T, K> : never`.
