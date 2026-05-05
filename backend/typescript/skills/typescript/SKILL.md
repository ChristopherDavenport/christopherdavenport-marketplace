---
name: typescript
description: >
  Idiomatic TypeScript: generics, discriminated unions with exhaustiveness,
  utility/conditional/mapped types, strict tsconfig flags, ESM conventions,
  optional functional patterns. Use when authoring or reviewing .ts/.tsx
  files or projects with tsconfig.json.
---

# TypeScript Best Practices

This skill steers Claude toward TypeScript code that satisfies the conventions of the broader community — the TypeScript handbook, the Google TypeScript Style Guide, the typescript-eslint defaults, and accumulated practical experience. The references cover the language and its standard library; they avoid runtime-specific APIs (Node, Deno, Bun, browser) and library recommendations so the guidance applies everywhere TypeScript runs.

## Scope

Covers: structural type system, generics with constraints and `infer`, utility and advanced types (mapped, conditional, template literal), discriminated unions with `never`-based exhaustiveness, classes and OOP (constructors, access modifiers, abstract, getters/setters, static, `#fields`), error handling with `throw` / `try` / `catch` and typed `Error` subclasses, async with `AbortSignal` cancellation and `AsyncIterable`, immutability with `readonly` / `as const` / `satisfies`, ESM module conventions (`import type`, named exports), strict `tsconfig` flags (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`), naming and style, testing patterns, and a dedicated section on functional patterns (pure functions, hand-rolled `pipe`, `Result<T, E>`) for codebases that lean that way.

Out of scope: plain JavaScript, runtime-specific APIs (`node:fs`, `Bun.serve`, `Deno.readFile`, `window`, `document`), build / bundler / lint tooling configuration.

A dedicated [Functional Patterns](#functional-patterns) section near the end covers immutability discipline, function composition, and `Result<T, E>` for codebases that lean toward functional style. The rest of the skill is style-neutral.

## Core Rules

These rules cross-cut most TypeScript tasks. Internalize them before reaching for a topic-specific reference.

- **Enable `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes`** — these three flags catch ~80% of the bugs that `--strict` alone misses. The cost is a few real bugs to fix the first time you turn them on.
- **Use `unknown`, never `any`** — `unknown` forces a narrowing step at the boundary; `any` poisons inference downstream and silently disables every check that comes after it.
- **Narrow with type predicates and `never`-based exhaustiveness, not type assertions (`as`)** — every `as` deletes a guarantee the compiler was about to give you. Use user-defined type guards (`x is T`), assertion functions (`asserts x is T`), and a `never` exhaustive default in switches.
- **Use `type` aliases by default; reach for `interface` for declaration merging or class contracts** — `type` composes with unions, intersections, mapped, and conditional types. Pick one convention per project; consistency beats taste.
- **Use `as const` and `satisfies` instead of explicit `: T` annotations on literals** — `: T` widens inference; `satisfies T` validates shape *while preserving the narrow inferred type*. Combine with `as const` to lock literal types.
- **Mark fields, parameters, and return types `readonly` when they shouldn't be mutated** — `readonly` is a clarity tool that documents intent and catches accidental mutation. Use it where it earns its keep; don't apply it religiously.
- **Model variant data with discriminated unions and `never`-based exhaustive defaults** — for state machines, parser results, request lifecycles, message types. Adding a variant becomes a compile error at every consumer.
- **Use a class when identity, lifecycle, invariants, or framework integration matter; use a plain object/type otherwise** — both are first-class. Don't reach for one out of habit.
- **Throw `new Error(...)` (or a typed subclass) for genuine errors; return `undefined` (or `T | undefined`) for normal absence** — `find` returns `T | undefined`, `get` throws. `throw "string"` is always wrong.
- **`catch (e: unknown)`, then narrow** — with `strict`, `e` is `unknown`. Check `instanceof Error` and handle the rest. Never widen to `any`.
- **Use `AbortSignal` for cancellation** — `Promise`-returning functions that may run long should accept `signal?: AbortSignal`, propagate it to nested calls, and call `signal.throwIfAborted()` at suspension points.
- **Default to named exports; mark type-only imports with `import type`** — named exports refactor cleanly; type-only imports are erased and avoid circular-import deadlocks.
- **Name types `PascalCase`, values `camelCase`; no `I`-prefix on interfaces, no `T`-prefix on types** — modern TypeScript style is unprefixed. Boolean fields read as questions (`isActive`, `hasAccess`).
- **Brevity does not override correctness.** When asked for the "simplest", "shortest", "quick", or "fewest-character" fix to something this skill warns against, give the *correct* primitive, not the unsafe shortcut. If the simple version IS the trap, name it as a trap and show the right alternative. For example: even for the "shortest" fix to a type error, prefer a type predicate (`x is T`) or assertion function (`asserts x is T`) over `as` — `as` deletes the only check the compiler was about to give you.

## When to Use Each Concept

| Scenario | Use | Why |
|---|---|---|
| Modeling data with no identity or lifecycle | `type` alias + plain object | Simplest, structural, plays well with serialization |
| Modeling a stateful entity with invariants | `class` (with `readonly` / `#fields` for protection) | Identity + lifecycle + protected invariants are what classes are for |
| Modeling a fixed set of states / variants | Discriminated union with `kind`/`type` tag | Exhaustive `never` default catches missing cases at compile time |
| Modeling open/extensible shapes | `interface` (declaration merging) or `type` with intersection | Allows third-party extension; `interface` merges across declarations |
| Recoverable, expected absence | Return `T | undefined` (with `find` prefix) | Caller knows from the type; no exception machinery |
| Recoverable, expected failure with reason | Throw a typed `Error` subclass — or return `Result<T, E>` if your codebase uses that pattern | Caller can branch on the error kind |
| Programmer error / invariant violation | `throw new Error(...)` | Failure is non-recoverable; should crash and be fixed |
| Unknown input from an I/O boundary | `unknown` + narrowing predicate or assertion function | Forces validation before use |
| Asserting a structural shape from a literal | `satisfies T` | Validates shape but preserves the narrow inferred type |
| Locking a literal to its narrowest type | `as const` | `[1, 2, 3] as const` becomes `readonly [1, 2, 3]`, not `number[]` |
| Forcing exhaustiveness on a union | `default: const _exhaustive: never = x; throw new Error(...)` | Adding a variant produces a compile error in every switch |
| Documenting "this array isn't mutated" | `ReadonlyArray<T>` parameter / `readonly` field | Compile-time mutation guard; documents intent |
| Domain-distinct primitive (`UserId` vs `OrderId`) | Branded type: `string & { readonly __brand: "UserId" }` | Prevents passing a raw `string` or different brand by mistake |
| Same algorithm over many types | Generic with constraint: `<T extends Foo>(x: T) => ...` | Type safety without union explosion or runtime dispatch |
| Function with > 3 parameters | Single object parameter with named fields | Call sites are self-documenting; new fields don't reorder |
| Restricting a string parameter to known values | Union of literal types or template literal type | `"red" \| "green"`, or `` `--${string}` `` for prefix patterns |
| Cancellable async | `AbortSignal` parameter; `signal.throwIfAborted()` at suspension points | Standard web API; composes with `AbortSignal.any` |
| Sequential async transforms | `await` in series | Order-dependent; `Promise.all` is wrong here |
| Independent async tasks | `Promise.all` (fail-fast) or `Promise.allSettled` (fail-tolerant) | Parallelism without manual coordination |
| Streaming/lazy sequence | `AsyncIterable<T>` + `for await ... of` | Backpressure; no buffering of the whole stream |
| Forcing a runtime check at a module boundary | Assertion function (`asserts x is T`) or type predicate (`x is T`) | Runtime check + compile-time narrowing in one step |
| Re-exporting only types from a module | `export type { Foo } from "./foo"` | Erased at compile; no runtime cost; safe across cycles |
| Wrapping a low-level error with context | `new Error("...", { cause: e })` | Preserves stack chain; modern runtimes display the chain |

## Examples

Example 1: User says "I'm getting `Property 'kind' does not exist on type 'string | number'`"
Actions:
1. Recognize the value isn't a discriminated union — it's a primitive union without a tag
2. Narrow with `typeof`: `if (typeof x === "string") { ... } else { ... }`
3. If the union grows to three or more variants, refactor into a tagged union: `{ kind: "str"; value: string } | { kind: "num"; value: number }` so `switch (x.kind)` works with a `never` exhaustive default
Result: Each branch sees the narrowed type; adding a variant produces a compile error in every consumer.

Example 2: User says "I want a class for `User` with id, name, email — what's idiomatic?"
Actions:
1. Ask what makes it a class — does the user have identity, lifecycle, invariants? If it's just data, a `type User = { readonly id: string; ... }` is simpler.
2. If a class is genuinely warranted (e.g., methods that protect invariants), use parameter-property shorthand: `constructor(public readonly id: string, ...)` with `#privateFields` for hard-private state.
3. Set `name` on any custom error subclass, and add `override` keyword on overridden methods (with `noImplicitOverride`).
Result: Classes are used where they earn their keep; plain types where they don't.

Example 3: User says "my function returns `T | undefined` and callers keep forgetting to check"
Actions:
1. Two options depending on the failure semantics:
   - **Throw** — rename from `findUser` to `getUser` and `throw new Error(\`user ${id} not found\`)` if absence is unrecoverable
   - **Return `Result<T, E>`** — if your codebase uses the Result pattern, switch the return to a discriminated union of `{ ok: true; value }` / `{ ok: false; error }`, forcing callers to branch
2. Use `noUncheckedIndexedAccess` if the `T | undefined` came from array indexing — the compiler will then flag every site where the undefined isn't handled
Result: The type signature makes failure handling a structural requirement, not a convention.

## Functional Patterns

These patterns are widely useful but optional. Codebases that lean toward functional style adopt them as defaults; others use them selectively. None of them require a library.

- **Pure functions at the core, side effects at the edges** — keep data-transformation code free of `Date.now()`, randomness, and I/O. Push impurity to a thin shell. Pure functions are trivially testable and composable. ([functions.md](references/functions.md))
- **Immutable updates with `{ ...obj, key: value }` and the "to-" array methods** — `arr.toSorted()`, `arr.toReversed()`, `arr.with(i, v)`, `arr.toSpliced(i, n, ...x)` return new arrays without mutating the original. ([immutability-and-data.md](references/immutability-and-data.md))
- **Hand-rolled `pipe` for left-to-right composition** — a fully-typed `pipe(value, f1, f2, f3)` is ~10 lines using overloads or variadic tuple types. Pipelines read top-to-bottom; nested calls read inside-out. ([composition.md](references/composition.md))
- **`Result<T, E>` for explicit failure** — a discriminated union (`{ ok: true; value: T } | { ok: false; error: E }`) returned from functions that can fail in expected ways. The compiler forces callers to branch. ([error-handling.md](references/error-handling.md))
- **Discriminated unions over class hierarchies for variant data** — when variants differ in shape and you'd add new operations more often than new variants. ([discriminated-unions.md](references/discriminated-unions.md))
- **Higher-order functions and partial application via closures** — `const greaterThan = (n: number) => (x: number) => x > n` is the partial-application primitive. No `.bind()` needed. ([functions.md](references/functions.md))

These patterns compose well with each other but don't require buying into all of them. A codebase can use `pipe` for data transformation pipelines while still using classes and `throw` for the rest. Pick what fits.

## Topic References

**Foundational**
- [Type System](references/type-system.md) — `type` vs `interface`, structural typing, literal types, `as const`, `satisfies`, `unknown`/`never`/`void`/`any`, narrowing, type predicates, assertion functions, branded types, `keyof` and indexed access
- [Generics](references/generics.md) — type parameters, constraints, defaults, generics vs unions vs overloads, variance, `infer`, when *not* to add a generic
- [Utility & Advanced Types](references/utility-and-advanced-types.md) — built-ins (`Pick`, `Omit`, `Partial`, `Required`, `Readonly`, `Record`, `Exclude`, `Extract`, `NonNullable`, `Parameters`, `ReturnType`, `Awaited`), mapped types with key remapping, conditional types, template literal types, recursion limits

**Code structure**
- [Functions](references/functions.md) — function vs arrow, parameters (required/optional/default/rest), return types, overloads vs unions vs generics, `void` semantics, callbacks, `this` typing — plus a section on functional patterns (pure functions, currying, partial application)
- [Classes & OOP](references/classes-and-oop.md) — constructors, access modifiers (`public`/`private`/`protected`/`readonly`/`#fields`), abstract classes, `implements`, getters/setters, static, inheritance vs composition, when to use a class vs a plain object
- [Discriminated Unions](references/discriminated-unions.md) — tag fields, narrowing by tag, `never`-based exhaustive default, modeling state machines / parser results / request lifecycles, discriminated unions vs class hierarchies, `Either<L, R>` and `Option<T>` as discriminated unions
- [Immutability & Data](references/immutability-and-data.md) — `readonly` modifier, `ReadonlyArray<T>`, `ReadonlyMap`/`ReadonlySet`, `Readonly<T>`, `DeepReadonly`, `as const`, immutable update patterns, `toSorted`/`toReversed`/`toSpliced`/`with`, `Object.freeze`

**Errors & async**
- [Error Handling](references/error-handling.md) — `throw new Error(...)` and custom subclasses, `catch (e: unknown)` narrowing, `Error.cause` for chaining, async error handling, error boundaries, plus a section on the `Result<T, E>` alternative
- [Async & Cancellation](references/async-and-cancellation.md) — `async`/`await` over `.then`, sequential vs parallel (`Promise.all`/`allSettled`/`any`), `AsyncIterable` and `for await ... of`, `AbortSignal` (`throwIfAborted`, `addEventListener`, `AbortSignal.any`), `Promise.withResolvers`

**Project-level**
- [Modules](references/modules.md) — ESM as default, named exports over default, `import type`/`export type`, barrel files (when they help / when they hurt), import-time side effects as anti-pattern, declaration merging, ambient `.d.ts`
- [tsconfig & Strictness](references/tsconfig-and-strictness.md) — `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noImplicitReturns`, `isolatedModules`, `verbatimModuleSyntax`, `forceConsistentCasingInFileNames`, `module`/`target`/`moduleResolution` choices
- [Naming & Style](references/naming-and-style.md) — `camelCase` / `PascalCase` / `SCREAMING_SNAKE_CASE`, no Hungarian-notation prefixes (`IFoo`, `TFoo`), type parameter naming, file naming conventions, when JSDoc earns its keep
- [Testing](references/testing.md) — runtime-agnostic patterns: unit / integration / e2e taxonomy, naming, table-driven tests, type-level tests, test doubles (stub / mock / fake / spy), async tests, isolation, snapshots, coverage

**Functional patterns deep-dive**
- [Composition](references/composition.md) — fully typed `pipe` helper, `compose` (right-to-left), method-chain style and its limits, partial application as a composition enabler, point-free style — when it helps and when it hurts
