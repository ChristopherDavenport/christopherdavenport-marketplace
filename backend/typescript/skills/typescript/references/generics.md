# Generics — Deep Dive

A generic is a *type-level function*. It takes types in, produces types out. The mental model that fixes most generic confusion: **generics propagate information from input types to output types so the compiler can connect the two**.

```ts
function identity<T>(x: T): T {
  return x;
}

const n = identity(1);     // n: number
const s = identity("hi");  // s: string
```

If a generic *only appears in the parameter list* and *not in the return type or another parameter*, it almost certainly shouldn't exist:

```ts
// Useless — T is just `any` in disguise
function log<T>(x: T): void { console.log(x); }

// Equivalent and clearer
function log(x: unknown): void { console.log(x); }
```

**Rule:** A type parameter must appear in at least two positions (often: a parameter and the return, or two parameters that must agree). Otherwise it's not pulling its weight.

## Type Parameters on Functions, Types, and Classes

```ts
// Generic function
function first<T>(arr: readonly T[]): T | undefined {
  return arr[0];
}

// Generic type alias
type Pair<A, B> = { first: A; second: B };

// Generic class (rare in functional code, but the syntax exists)
class Stack<T> {
  private items: T[] = [];
  push(x: T): void { this.items.push(x); }
  pop(): T | undefined { return this.items.pop(); }
}
```

Inference flows from arguments. You rarely need to specify type arguments explicitly — let the compiler figure them out:

```ts
first([1, 2, 3]);          // T inferred as number
first(["a", "b"]);         // T inferred as string
first<number>([1, 2, 3]);  // explicit; usually redundant
```

When inference fails, it's usually because the input type is too wide. Narrow the input (`as const`, `satisfies`) before calling.

## Constraints (`extends`)

By default, a type parameter can be anything — including `unknown`. To use *any* property of the type inside the function body, you must constrain it:

```ts
function lengthOf<T extends { length: number }>(x: T): number {
  return x.length;
}

lengthOf("hello");     // OK
lengthOf([1, 2, 3]);   // OK
lengthOf({ length: 5 }); // OK
lengthOf(42);          // Error: number has no length
```

The constraint says: "T can be any type, *as long as* it has a `length: number`."

A common pattern: `T extends keyof Obj` for type-safe property access:

```ts
function get<Obj, K extends keyof Obj>(obj: Obj, key: K): Obj[K] {
  return obj[key];
}

const u = { id: "1", name: "alice", age: 30 };
const a = get(u, "age");    // a: number
const x = get(u, "missing"); // Error
```

## Default Type Parameters

Type parameters can have defaults, just like value parameters:

```ts
type Result<T, E = Error> =
  | { ok: true;  value: T }
  | { ok: false; error: E };

const r1: Result<string> = { ok: false, error: new Error("nope") };       // E defaults to Error
const r2: Result<string, "NotFound"> = { ok: false, error: "NotFound" };  // E specified
```

Use defaults for the common case. Don't use them as a substitute for thinking through what the parameter means.

## Generics vs Unions vs Overloads

These three tools solve overlapping problems. Choose based on the relationship between input and output:

**Use a union parameter** when the function does the same thing regardless of input type:

```ts
function display(x: string | number): string {
  return String(x);
}
```

**Use a generic** when the input type *flows through* to the output:

```ts
function wrapInArray<T>(x: T): T[] {
  return [x];
}

const a = wrapInArray(42);    // a: number[]
const b = wrapInArray("hi");  // b: string[]
```

**Use an overload** when the output type depends on the *value* of the input in ways the type system can't express, or when the function genuinely behaves differently per type:

```ts
function parse(input: string, mode: "json"): unknown;
function parse(input: string, mode: "int"):  number;
function parse(input: string, mode: "bool"): boolean;
function parse(input: string, mode: string): unknown {
  if (mode === "json") return JSON.parse(input);
  if (mode === "int")  return parseInt(input, 10);
  if (mode === "bool") return input === "true";
  throw new Error(`unknown mode: ${mode}`);
}
```

**Often a discriminated-union return is better than overloads.** Overloads have a sharp edge: the implementation signature is *not* visible to callers, and it's easy to write an implementation that doesn't actually satisfy all the overload signatures. Reach for them only when nothing else works.

## Variance Gotchas

In TypeScript, **function parameters are bivariant** by default — which is unsound but pragmatic. With `strictFunctionTypes` on (part of `strict`), they become **contravariant** for function-type assignment, while remaining bivariant for method-type assignment. Returns are always **covariant**.

What this means in practice:

```ts
type Animal = { name: string };
type Dog    = Animal & { bark(): void };

type Take<T> = (x: T) => void;

const takeAnimal: Take<Animal> = (a) => console.log(a.name);
const takeDog:    Take<Dog>    = (d) => d.bark();

let t: Take<Dog>;
t = takeAnimal;  // OK — accepting a wider type means it accepts a Dog
t = takeDog;     // OK
```

```ts
type Make<T> = () => T;

const makeAnimal: Make<Animal> = () => ({ name: "x" });
const makeDog:    Make<Dog>    = () => ({ name: "x", bark: () => {} });

let m: Make<Animal>;
m = makeDog;     // OK — Dog is an Animal, returning a Dog is returning an Animal
m = makeAnimal;  // OK
```

You rarely need to think about variance directly. When generics misbehave around function types, mismatched variance is the usual culprit.

## Conditional Types and `infer`

A conditional type picks one type or another based on a condition:

```ts
type IsArray<T> = T extends readonly unknown[] ? true : false;

type A = IsArray<number[]>;     // true
type B = IsArray<string>;       // false
```

`infer` extracts a piece of a type during a conditional check:

```ts
type ElementOf<T> = T extends readonly (infer E)[] ? E : never;

type X = ElementOf<number[]>;       // number
type Y = ElementOf<readonly string[]>; // string
type Z = ElementOf<42>;             // never
```

The standard library uses this pervasively:

```ts
type ReturnType<T> = T extends (...args: never[]) => infer R ? R : never;
type Awaited<T>    = T extends Promise<infer U> ? Awaited<U> : T;
type Parameters<T> = T extends (...args: infer P) => unknown ? P : never;
```

When a conditional type is applied to a *generic naked type parameter*, it **distributes** over unions:

```ts
type Wrap<T> = T extends unknown ? { value: T } : never;

type W = Wrap<string | number>;
//   ^ { value: string } | { value: number }
//     (NOT { value: string | number })

// To prevent distribution, wrap in a tuple:
type WrapNoDist<T> = [T] extends [unknown] ? { value: T } : never;
type W2 = WrapNoDist<string | number>;
//   ^ { value: string | number }
```

Distribution is usually what you want. The tuple wrap is the escape hatch.

## When *Not* to Reach for Type-Level Programming

A 30-line conditional-type incantation that produces a slightly more precise return type is almost always worse than a runtime helper with a clear, simple signature. Type-level programming has costs:

- **Compile time** — deeply recursive types slow `tsc` and IDE feedback to a crawl.
- **Error messages** — when something is wrong, the error includes every step of the conditional unfurling.
- **Maintenance** — six months later, no one will remember why the type works.

Heuristic: if you can't explain the conditional type's behavior to a colleague in two sentences, it's too clever. Replace with a plain runtime function and an explicit return annotation.

## Generic Constraints with Mapped Types

The most common "I need a smarter generic" pattern is mapping over keys with constraints:

```ts
type StringKeys<T> = {
  [K in keyof T]: T[K] extends string ? K : never;
}[keyof T];

type User = { id: string; name: string; age: number };
type S = StringKeys<User>;   // "id" | "name"

function getString<T, K extends StringKeys<T>>(obj: T, key: K): string {
  return obj[key] as string;
}
```

This is the bridge between `keyof` (covered in [type-system.md](type-system.md)) and the deeper utility-type machinery (covered in [utility-and-advanced-types.md](utility-and-advanced-types.md)).

## Common Pitfalls

- **Generics that appear only once.** `function f<T>(x: T): void` is `function f(x: unknown): void` with extra steps. Delete the type parameter.
- **Constraining too late.** If you write `<T>` and then need a property of `T` inside the body, you'll have to add `T extends { ... }` later — and break every caller. Add the constraint up front when designing.
- **Specifying type arguments unnecessarily.** `identity<number>(1)` instead of `identity(1)`. Inference works; trust it. Specify arguments only when inference fails or genuinely needs steering.
- **Confusing `T extends U` (subtype) with `T extends U ? X : Y` (conditional).** Same syntax, different positions: in a constraint, it's a subtype relation; in a conditional, it's a type-level `if`.
- **Forgetting distribution.** `T extends string ? T[] : never` applied to `"a" | "b"` produces `"a"[] | "b"[]`, not `("a" | "b")[]`. If you wanted the latter, wrap: `[T] extends [string] ? T[] : never`.
- **`extends any` instead of `extends unknown`.** They behave nearly identically as constraints but `unknown` reads as "no constraint" intentionally; `any` reads as "I gave up." Use `unknown`.
- **Reaching for generics when a discriminated union would do.** If your function has a `mode` parameter and the return type depends on the mode, return a discriminated union and let the caller narrow — usually clearer than overloads or conditional return types.
- **Generic classes for things that should be free functions.** A class with one method is a function. Functional code rarely needs `class Stack<T>` — an `Array<T>` already exists.
