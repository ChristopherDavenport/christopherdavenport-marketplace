# Type System — Deep Dive

TypeScript's type system is **structural** (not nominal). Two types with the same shape are interchangeable, regardless of their declared name. This is the single most important fact to internalize: it shapes how you model data, how you build APIs, and how you cross module boundaries.

```ts
type Point = { x: number; y: number };
type Vec   = { x: number; y: number };

const p: Point = { x: 1, y: 2 };
const v: Vec   = p;  // OK — same shape, same type to TS
```

Once you accept this, the language stops being "Java with `let`" and starts behaving like a value-oriented language with a powerful proof system over data shapes.

## `type` vs `interface`

Both declare named shapes. The differences matter:

| | `type` | `interface` |
|---|---|---|
| Unions, intersections | ✅ `type X = A \| B` | ❌ |
| Mapped types, conditionals, template literals | ✅ | ❌ |
| Declaration merging | ❌ | ✅ |
| Implements / extends in classes | ✅ | ✅ |
| Tooltip readability | Sometimes worse for very large objects | Often better |

**Default to `type`.** It composes with everything else in the type system. Reach for `interface` only when:

1. You need declaration merging (extending a third-party type, augmenting a global, exposing an extension point to consumers).
2. You're writing a class contract that you expect to be `implements`'d in many places and want the nicer tooltip.

Whichever you pick, **stay consistent within a file**. Mixing them confuses readers more than the choice itself matters.

```ts
type User = { id: string; name: string };           // good default
interface Plugin { activate(): void }                // open for extension
```

## Literal Types and `as const`

A *literal type* is a type whose only inhabitant is a single value:

```ts
type Method = "GET" | "POST" | "PUT" | "DELETE";
let m: Method = "GET";  // OK
m = "PATCH";            // Error: not a Method
```

By default, TypeScript widens literal values when assigning to a `let` or storing in an object:

```ts
const direction = "north";          // type: "north"  (narrow)
let   wind      = "north";          // type: string   (wide)
const config    = { dir: "north" }; // dir: string    (wide)
```

`as const` opts every literal in an expression *into* its narrowest type:

```ts
const config = { dir: "north" } as const;
//    ^? { readonly dir: "north" }

const palette = ["red", "green", "blue"] as const;
//    ^? readonly ["red", "green", "blue"]

type Color = typeof palette[number];  // "red" | "green" | "blue"
```

Use `as const` whenever you want a literal value to *also* serve as a source of truth for a type.

## `satisfies`

`: T` annotation **widens** the value to `T`. `satisfies T` **validates** the value matches `T` while preserving the narrow inferred type.

```ts
type Config = Record<string, string | number>;

const wide: Config = { host: "localhost", port: 8080 };
//    wide.host has type string | number — lost the narrowing

const narrow = { host: "localhost", port: 8080 } satisfies Config;
//    narrow.host has type string, narrow.port has type number — preserved
```

Rule of thumb: use `satisfies` for object literals that must conform to a shape *and* be used downstream with their precise types. Use `: T` only when widening is what you want (parameters, public API surfaces).

## The `unknown` / `never` / `void` / `any` Family

These four types are constantly confused. They are not interchangeable.

| Type | Meaning | When to use |
|---|---|---|
| `unknown` | "Could be anything; you must narrow before use" | Boundary inputs (JSON, `catch`, untyped library returns) |
| `never` | "No value can exist here" | Exhaustiveness checks, function that always throws / never returns |
| `void` | "Caller will ignore the return value" | Callbacks where the return is discarded; `setTimeout` handlers |
| `any` | "Disable type checking for this expression" | Almost never. Possibly during a migration. |

```ts
function parse(input: unknown) {
  if (typeof input === "string") {
    return input.toUpperCase();   // narrowed
  }
  return null;
}

function unreachable(x: never): never {
  throw new Error(`Unreachable: ${JSON.stringify(x)}`);
}

const handlers: Array<() => void> = [
  () => console.log("a"),
  () => 42,           // returning 42 is fine — `void` says caller ignores it
];
```

**Never write `any`.** If you reach for it, write `unknown` and narrow, or fix the underlying type. The one place `any` legitimately appears is in the *constraint* position of a generic (`T extends any[]`) where TS doesn't accept `unknown[]` for variance reasons.

## Type Narrowing

Narrowing is how you take a wide type and make it specific based on runtime checks. The compiler tracks the narrowing through control flow.

```ts
function len(x: string | string[]): number {
  if (typeof x === "string") return x.length;       // narrowed to string
  return x.length;                                   // narrowed to string[]
}

function first(x: { kind: "list"; items: number[] } | { kind: "single"; value: number }) {
  if (x.kind === "list") return x.items[0];          // narrowed by tag
  return x.value;
}

class HttpError {}
class NetworkError {}
function handle(e: HttpError | NetworkError) {
  if (e instanceof HttpError) return "http";         // narrowed by class
  return "network";
}

function take(o: { a: string } | { b: number }) {
  if ("a" in o) return o.a;                           // narrowed by `in`
  return o.b;
}
```

The five narrowing operators: `typeof`, `instanceof`, `in`, equality (`===`/`!==`/`==`/`!=`), and discriminated-union tag comparison.

## User-Defined Type Predicates

When a check is too complex for the built-in operators, write a **type predicate**:

```ts
type User = { id: string; name: string };

function isUser(x: unknown): x is User {
  return (
    typeof x === "object" && x !== null &&
    "id" in x && typeof (x as Record<string, unknown>).id === "string" &&
    "name" in x && typeof (x as Record<string, unknown>).name === "string"
  );
}

function greet(x: unknown): string {
  if (isUser(x)) return `hello ${x.name}`;            // narrowed to User
  return "hello stranger";
}
```

The `is` clause tells the compiler: "if this returns `true`, narrow the argument to that type." **The compiler trusts you** — if your runtime check is wrong, the narrowing is wrong. Keep predicates tight and well-tested.

## Assertion Functions

Like a predicate, but throws instead of returning a boolean:

```ts
function assertString(x: unknown): asserts x is string {
  if (typeof x !== "string") throw new TypeError("expected string");
}

function shout(x: unknown): string {
  assertString(x);     // throws if not a string
  return x.toUpperCase();   // narrowed to string after the call
}
```

Use assertion functions at I/O boundaries where failure is genuinely fatal and you want a one-liner instead of an `if`.

**Caveat:** assertion functions and predicates trip the compiler if not declared with `function` syntax. Arrow-function expressions cannot carry `is` / `asserts`.

## Branded (Nominal) Types

Structural typing means a `UserId` and an `OrderId` — both `string` underneath — are interchangeable. Often you don't want that. **Branding** simulates nominal typing using a phantom property:

```ts
type UserId  = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

function makeUserId(s: string): UserId  { return s as UserId; }
function makeOrderId(s: string): OrderId { return s as OrderId; }

function loadUser(id: UserId)  { /* ... */ }

const u = makeUserId("u-1");
const o = makeOrderId("o-1");
loadUser(u);   // OK
loadUser(o);   // Error: OrderId is not assignable to UserId
loadUser("u-1"); // Error: string is not assignable to UserId
```

The cast inside the constructor function is the **only** place `as` is acceptable in branded code — it's the boundary where validation happens. Concentrate the unsafety in one place; the rest of the codebase becomes type-safe.

The brand property is purely compile-time — it never exists at runtime. Use a `unique symbol` brand for stronger isolation if you want to prevent any other module from constructing the brand:

```ts
declare const userIdBrand: unique symbol;
type UserId = string & { readonly [userIdBrand]: true };
```

## `keyof` and Indexed Access

`keyof T` is the union of `T`'s keys as string literals. `T[K]` is the type at key `K`.

```ts
type User = { id: string; name: string; age: number };

type UserKey   = keyof User;       // "id" | "name" | "age"
type UserName  = User["name"];     // string
type UserField = User[keyof User]; // string | number

function get<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

const u: User = { id: "1", name: "alice", age: 30 };
const a = get(u, "age");  // type: number
```

This is the basis of every advanced utility type. Master it.

## Common Pitfalls

- **Reaching for `as` to silence the compiler.** Every `as` is a manual override of the type system. The honest fix is usually to fix the type or add a predicate. The two legitimate uses: branded-type constructors and `as const`.
- **Confusing `unknown` and `any`.** `any` makes downstream code unsafe; `unknown` makes it require narrowing. Always prefer `unknown`.
- **Annotating where inference would suffice.** `const x: number = 1` is noise. `const x = 1` infers `number`. Annotate at *boundaries* (function signatures, public API), let inference do the rest.
- **Using `: T` when you wanted `satisfies T`.** The annotation widens, the operator validates without widening. If you want to keep narrow inference, use `satisfies`.
- **Forgetting that `interface` doesn't accept unions.** `interface X = A | B` is a syntax error; you need `type X = A | B`. This is the single most common reason to switch from `interface` to `type` mid-file.
- **Brand-property name collisions.** If two modules both use `__brand: "Foo"`, their brands are interchangeable. Use a `unique symbol` if you need true isolation.
- **Type predicates that lie.** The compiler trusts the `is T` clause unconditionally. A buggy predicate produces narrowed types that don't match runtime reality — among the worst class of TypeScript bugs.
- **Declaring class instances as the type.** `function f(d: Date)` accepts anything with `Date`'s structural shape. If you need a real `Date` (e.g., to call `.getTime()` and trust it works), the structural check passes for plain objects with the right method shapes too. Use `instanceof` checks at boundaries when identity matters.
