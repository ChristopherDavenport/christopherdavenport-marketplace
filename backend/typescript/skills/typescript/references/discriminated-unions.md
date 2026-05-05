# Discriminated Unions — Deep Dive

A discriminated union (also: tagged union, sum type, ADT) is a union of object types that share a literal-typed **tag field**. The tag tells the compiler — and the reader — which variant a value is. The pattern is one of the most useful data-modeling tools TypeScript offers, especially for values that come in a fixed set of variants (state machines, parser results, request lifecycles, message types).

Used well, discriminated unions make entire categories of bugs impossible: forgetting to handle a state, using the wrong field for the variant you have, drifting consumer code out of sync with producer code.

## The Anatomy

```ts
type Result =
  | { kind: "ok";    value: number }
  | { kind: "error"; message: string };
```

The `kind` field is the **discriminant** (also called the *tag* or *discriminator*). Each variant has a unique literal value for it. Each variant can carry whatever data is appropriate for its case.

Consumers narrow by checking the tag:

```ts
function describe(r: Result): string {
  if (r.kind === "ok")    return `value: ${r.value}`;
  if (r.kind === "error") return `error: ${r.message}`;
  // unreachable
  throw new Error("impossible");
}
```

Inside each branch, the type is narrowed:
- In the `kind === "ok"` branch, TS knows `r.value` exists (and `r.message` does not).
- In the `kind === "error"` branch, TS knows `r.message` exists (and `r.value` does not).

This narrowing is the entire point. Without the tag, you'd be reaching for `as` casts or property-existence checks (`"value" in r`).

## Discriminated Unions vs Class Hierarchies

For a value that comes in a fixed set of variants, you can model it with either a class hierarchy or a discriminated union:

```ts
// Class hierarchy
abstract class Result { /* ... */ }
class Ok    extends Result { constructor(public value: number) { super(); } }
class Err_  extends Result { constructor(public message: string) { super(); } }

// Discriminated union
type Result =
  | { kind: "ok";  value: number }
  | { kind: "err"; message: string };
```

Each has tradeoffs:

| | Class hierarchy | Discriminated union |
|---|---|---|
| Adding a new variant | Add a subclass; consumer code may silently miss it | New variant breaks every consumer's exhaustive switch (compile error) |
| Adding a new operation | Add a method to every subclass | Add a free function over the union (no class changes) |
| Identity / lifecycle | Natural — `new`, `instanceof`, methods | Awkward — values are plain data |
| Serialization | Bespoke `toJSON`/`fromJSON` | Already JSON-shaped |
| Cross-module / cross-package | Nominal — instances of "the same" class from two modules differ | Structural — any matching shape works |
| Pairs with framework | Frameworks often expect classes (React, Lit, NestJS) | Frameworks expecting plain data |

**Use a class hierarchy when:**
- The value has identity, lifecycle, or invariants that need protection (see [classes-and-oop.md](classes-and-oop.md)).
- A framework or external API expects classes.
- You need shared implementation across variants via the template-method pattern.

**Use a discriminated union when:**
- The value is essentially data — variants differ in shape, not behavior.
- You add operations more often than variants.
- Exhaustiveness matters and you want compile errors on missing cases.
- The value crosses module/package boundaries or gets serialized.

Both are valid; pick based on what the data is doing in your system.

## Exhaustiveness with `never`

The killer feature: ensure every consumer handles every variant, **enforced at compile time**.

```ts
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "square"; side: number }
  | { kind: "rectangle"; width: number; height: number };

function area(s: Shape): number {
  switch (s.kind) {
    case "circle":    return Math.PI * s.radius ** 2;
    case "square":    return s.side ** 2;
    case "rectangle": return s.width * s.height;
    default:
      // If a new variant is added to Shape and not handled above,
      // `s` here will not be `never` — it'll be the missing variant —
      // and assignment to `_exhaustive: never` will be a compile error.
      const _exhaustive: never = s;
      throw new Error(`Unhandled shape: ${JSON.stringify(_exhaustive)}`);
  }
}
```

**Add a new variant to `Shape`.** The compiler immediately flags every `area`-style function in the codebase. No runtime testing required to find the missing cases. This is the type system doing the work that test coverage would otherwise have to.

The pattern, distilled:

```ts
function unreachable(x: never): never {
  throw new Error(`Unreachable case: ${JSON.stringify(x)}`);
}

switch (value.kind) {
  case "a": /* ... */ break;
  case "b": /* ... */ break;
  default:  unreachable(value);
}
```

## Choosing the Tag Field Name

Conventions vary. The tag must be a **single, agreed-upon name** within a project:

- `kind` — succinct, no built-in collision risk, common in TypeScript-native code
- `type` — natural-language, but collides with the `type` keyword in some contexts and overlaps with the JS `typeof`
- `_tag` — leading underscore signals "internal/structural," common in FP libraries (and convenient if you ever migrate to one)
- `discriminator` — explicit, verbose, less common

Pick one and stick with it project-wide. Readers should never wonder which field is the discriminant.

## Modeling State Machines

A state machine is the canonical use of discriminated unions:

```ts
type FetchState<T> =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: T }
  | { kind: "error"; error: Error };

function render<T>(state: FetchState<T>, view: (data: T) => string): string {
  switch (state.kind) {
    case "idle":    return "(not started)";
    case "loading": return "loading…";
    case "success": return view(state.data);
    case "error":   return `error: ${state.error.message}`;
  }
}
```

The compiler enforces that:
- `data` is only accessed in the `success` branch
- `error` is only accessed in the `error` branch
- Every state is handled

Add `{ kind: "retrying"; attempt: number }` to `FetchState`, and `render` (and every other consumer) must be updated.

## Modeling Parser Results

```ts
type Parsed<T> =
  | { kind: "ok"; value: T; rest: string }
  | { kind: "fail"; reason: string; pos: number };

function parseInt2(input: string): Parsed<number> {
  const m = input.match(/^(-?\d+)/);
  if (!m) return { kind: "fail", reason: "expected digits", pos: 0 };
  return { kind: "ok", value: Number(m[1]), rest: input.slice(m[0].length) };
}
```

This generalizes to combinator-style parsers, AST builders, and validation pipelines.

## Modeling Request Lifecycles

```ts
type Request =
  | { kind: "queued";    id: string }
  | { kind: "running";   id: string; startedAt: Date }
  | { kind: "done";      id: string; result: unknown; durationMs: number }
  | { kind: "failed";    id: string; error: { code: string; message: string } }
  | { kind: "cancelled"; id: string; reason: string };
```

Every transition produces a fresh value of the right variant — no mutation, no "is this field set yet?" guessing. Persistence is JSON-direct.

## Building `Option` and `Either` from Discriminated Unions

Two patterns from FP that are just discriminated unions wearing fancy hats:

### `Option<T>` / `Maybe<T>`

```ts
type Option<T> = { kind: "some"; value: T } | { kind: "none" };

const some = <T>(value: T): Option<T> => ({ kind: "some", value });
const none = <T>(): Option<T>         => ({ kind: "none" });

const map = <T, U>(o: Option<T>, f: (t: T) => U): Option<U> =>
  o.kind === "some" ? some(f(o.value)) : none();

const getOrElse = <T>(o: Option<T>, fallback: T): T =>
  o.kind === "some" ? o.value : fallback;
```

`Option<T>` is a typed alternative to `T | undefined` that's harder to mishandle: the only way to get the value is to check the tag.

### `Either<L, R>`

```ts
type Either<L, R> =
  | { kind: "left";  left:  L }
  | { kind: "right"; right: R };

const left  = <L, R>(left:  L): Either<L, R> => ({ kind: "left",  left  });
const right = <L, R>(right: R): Either<L, R> => ({ kind: "right", right });
```

`Either<L, R>` is the foundation of `Result<T, E>` (covered in [error-handling.md](error-handling.md)). Convention: errors on the `left`, success on the `right` (mnemonic: "right is right").

These are often called "monadic" — the structure supports `map` and `flatMap`/`chain` operations that compose nicely. You can write the helpers in 5 lines each. No library needed.

## Combining Discriminated Unions and Generics

Discriminated unions can be generic:

```ts
type AsyncResult<T, E> =
  | { kind: "loading" }
  | { kind: "success"; value: T }
  | { kind: "failure"; error: E };
```

Multiple discriminants are also legal and useful:

```ts
type Event =
  | { kind: "click";    target: "button" | "link"; x: number; y: number }
  | { kind: "keypress"; key: string; modifiers: ReadonlyArray<"shift" | "ctrl" | "alt"> }
  | { kind: "scroll";   delta: number };
```

The compiler narrows by *all* discriminants. Inside `if (e.kind === "click" && e.target === "button")`, you have a button-click event with both fields available.

## Comparison to Enums

TypeScript `enum` exists but is generally avoided in modern functional TypeScript:

- `enum` produces runtime objects, not just types — they don't tree-shake well.
- They invent nominal typing where the rest of the language is structural.
- `const enum` works around the runtime cost but has incompatibilities with `isolatedModules` and `verbatimModuleSyntax`.

**Use string literal unions instead:**

```ts
// Avoid
enum Status { Idle, Loading, Done }

// Prefer
type Status = "idle" | "loading" | "done";

// Or, if you want runtime-accessible values:
const StatusValues = ["idle", "loading", "done"] as const;
type Status = typeof StatusValues[number];
```

The literal-union form has zero runtime cost, plays nicely with serialization, and composes with the rest of the type system.

## Common Pitfalls

- **Forgetting the `never` exhaustive default.** Without it, adding a variant doesn't break consumers — it silently falls through. Always include `default: const _: never = x; throw ...`.
- **Inconsistent tag field names.** Half the codebase uses `kind`, half uses `type`. Readers waste time figuring out which is the discriminant. Pick one.
- **Tag field with `string` type instead of literal types.** `{ kind: string }` defeats narrowing — TS can't tell which variant you have. Always use literal types: `{ kind: "ok" }` not `{ kind: string }`.
- **Sharing fields across variants instead of putting them in each variant.** This:
  ```ts
  type Bad = { id: string } & ({ kind: "a"; v: 1 } | { kind: "b"; v: 2 });
  ```
  works but is harder to extend. Put shared fields directly in each variant, or use a generic helper. Intersection-with-union types are a refactoring trap.
- **Class hierarchies for pure-data variants with no methods.** If the abstract base has only data fields and consumers `dispatch` on subclass identity via a switch-like construct, a discriminated union is usually clearer. Conversely, if the base has meaningful shared behavior or lifecycle, a class hierarchy fits — see [classes-and-oop.md](classes-and-oop.md).
- **Reaching for `Either` / `Option` from a library when a hand-rolled discriminated union would do.** A `Result<T, E>` or `Option<T>` is 5-10 lines of stdlib TypeScript. Add a library only if you'll use the surrounding ecosystem of operators heavily.
- **Using `enum` reflexively.** Literal unions are cheaper, simpler, and play better with type-level features. `enum` exists for legacy reasons.
- **Putting the discriminant inside a nested object.** `{ outer: { kind: "..."; ... } }` requires `value.outer.kind === "..."` — narrowing works, but readability suffers. Hoist the tag to the top level.
