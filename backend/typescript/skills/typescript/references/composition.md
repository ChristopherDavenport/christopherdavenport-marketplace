# Composition — Deep Dive

Composition is the act of building larger functions from smaller ones. In a functional-leaning TypeScript codebase, it replaces what OOP solves with inheritance and what procedural code solves with deeply nested calls. The two main tools: **`pipe`** (left-to-right) and **`compose`** (right-to-left). Both are 10 lines each. No library required.

## The Problem with Nested Calls

```ts
const result = capitalize(trim(toLowerCase(input)));
```

You read it inside-out: `toLowerCase`, then `trim`, then `capitalize`. Three operations, three layers of nesting. Add a fourth and the line wraps awkwardly.

```ts
const result = pipe(
  input,
  toLowerCase,
  trim,
  capitalize,
);
```

You read it top-to-bottom: input enters, each step transforms it, the result falls out the bottom. Add a step — add a line. The cognitive cost is constant.

## A Fully-Typed `pipe`

The simplest version uses **variadic tuple types** to preserve type information through arbitrarily many functions:

```ts
type AnyFn = (arg: never) => unknown;

type PipeChain<Fns extends readonly AnyFn[], Input> =
  Fns extends readonly []
    ? Input
    : Fns extends readonly [(arg: Input) => infer Next, ...infer Rest]
      ? Rest extends readonly AnyFn[]
        ? PipeChain<Rest, Next>
        : never
      : never;

function pipe<Input, Fns extends readonly [(arg: Input) => unknown, ...AnyFn[]]>(
  input: Input,
  ...fns: Fns
): PipeChain<Fns, Input> {
  return fns.reduce((acc, fn) => (fn as (x: unknown) => unknown)(acc), input as unknown) as PipeChain<Fns, Input>;
}

const result = pipe(
  "  HELLO  ",
  (s) => s.toLowerCase(),
  (s) => s.trim(),
  (s) => s.length,
);
// result: number
```

If the variadic-tuple version feels heavy, an **overload-based `pipe`** is more verbose but produces simpler error messages — and it's how popular FP libraries do it under the hood:

```ts
function pipe<A>(a: A): A;
function pipe<A, B>(a: A, ab: (a: A) => B): B;
function pipe<A, B, C>(a: A, ab: (a: A) => B, bc: (b: B) => C): C;
function pipe<A, B, C, D>(a: A, ab: (a: A) => B, bc: (b: B) => C, cd: (c: C) => D): D;
function pipe<A, B, C, D, E>(a: A, ab: (a: A) => B, bc: (b: B) => C, cd: (c: C) => D, de: (d: D) => E): E;
// ...add overloads up to whatever depth your codebase actually uses (usually 6-8)
function pipe(input: unknown, ...fns: ReadonlyArray<(x: unknown) => unknown>): unknown {
  return fns.reduce((acc, fn) => fn(acc), input);
}
```

Pick whichever fits your team's tolerance for type-level wizardry. Both work. The variadic form scales to any arity; the overload form has friendlier errors.

## `compose` — Right-to-Left

Some prefer right-to-left composition because it matches mathematical notation (`f ∘ g` means "apply g, then f"):

```ts
function compose<A, B, C>(bc: (b: B) => C, ab: (a: A) => B): (a: A) => C {
  return (a) => bc(ab(a));
}

const trimAndUpper = compose(
  (s: string) => s.toUpperCase(),
  (s: string) => s.trim(),
);

trimAndUpper("  hi  ");  // "HI"
```

`pipe` is more popular in TypeScript-land because the data-first reading order matches imperative experience. Pick one convention per codebase.

## Method Chaining — The Built-In Composition

Arrays already compose via method chaining:

```ts
const result = arr
  .filter((x) => x > 0)
  .map((x) => x * 2)
  .reduce((sum, x) => sum + x, 0);
```

This is composition under a different name. Each method returns a new array (or value) ready for the next call. Use it when:

- You're working with arrays and the methods exist
- The chain is short (3-5 calls)
- Each step is a built-in like `.map`, `.filter`, `.flatMap`

Where method chaining breaks down:

- **Custom operations** — you can't add a method to `Array` from outside. Either subclass (gross) or break out of the chain.
- **Mixed types** — chaining works only when the receiver type stays usable. Once you switch to a different shape, you've left the chain.
- **Hidden allocations** — every step allocates a new array. For large inputs, a single `for` loop is faster.

For pipelines of arbitrary functions over arbitrary types, `pipe` wins. For array-to-array, method chaining wins.

## Partial Application as a Composition Enabler

Pipelines need each step to be a **single-argument function** (input → output). Multi-argument functions need partial application to fit:

```ts
// Multi-arg — doesn't fit in a pipe directly
const replace = (pattern: RegExp, replacement: string) => (s: string) =>
  s.replace(pattern, replacement);

// Curried form fits the pipe
pipe(
  "hello world",
  replace(/world/, "TypeScript"),
  (s) => s.toUpperCase(),
);
```

The convention: **data goes last** in pipe-friendly functions. The "configuration" arguments come first, the value being transformed last. See [functions.md](functions.md) for the full picture.

```ts
// Pipe-friendly: data last
const filter = <T>(pred: (x: T) => boolean) => (arr: readonly T[]): T[] => arr.filter(pred);

// Not pipe-friendly: data first
const filterBad = <T>(arr: readonly T[], pred: (x: T) => boolean): T[] => arr.filter(pred);
```

## Composing `Result<T, E>` Pipelines

Pipes get really powerful when each step can fail. With `Result<T, E>` (from [error-handling.md](error-handling.md)), you can short-circuit on the first error without verbose `if` checks at every step:

```ts
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

const ok    = <T, E = never>(value: T): Result<T, E> => ({ ok: true,  value });
const err   = <E, T = never>(error: E): Result<T, E> => ({ ok: false, error });

const map = <T, U, E>(f: (t: T) => U) => (r: Result<T, E>): Result<U, E> =>
  r.ok ? ok(f(r.value)) : r;

const flatMap = <T, U, E>(f: (t: T) => Result<U, E>) => (r: Result<T, E>): Result<U, E> =>
  r.ok ? f(r.value) : r;

// Pipeline
const parseAndValidate = (input: string): Result<User, ParseError | ValidateError> =>
  pipe(
    parse(input),                         // Result<Raw, ParseError>
    flatMap((raw) => validate(raw)),      // Result<User, ParseError | ValidateError>
    map((user) => normalize(user)),       // Result<User, ParseError | ValidateError>
  );
```

`map` transforms the `value` if `ok`, leaves `err` untouched. `flatMap` (also called `chain`) lets a step *return* a new `Result`, threading the error union forward. Together they form a "railway" — happy track on top, error track on the bottom, automatic switching.

## Composing `Promise<Result<T, E>>`

Async + Result composes the same way with async helpers:

```ts
const mapP = <T, U, E>(f: (t: T) => U | Promise<U>) =>
  async (r: Promise<Result<T, E>>): Promise<Result<U, E>> => {
    const v = await r;
    return v.ok ? ok(await f(v.value)) : v;
  };

const flatMapP = <T, U, E>(f: (t: T) => Promise<Result<U, E>>) =>
  async (r: Promise<Result<T, E>>): Promise<Result<U, E>> => {
    const v = await r;
    return v.ok ? f(v.value) : v;
  };

const result = await pipe(
  fetchUser(id, signal),                 // Promise<Result<User, FetchError>>
  flatMapP((user) => fetchOrders(user.id, signal)),
  mapP((orders) => orders.length),
);
```

Once you have `map`/`flatMap`/`mapP`/`flatMapP`, almost any async pipeline becomes a `pipe` chain. ~30 lines of helpers replace most of what FP libraries provide.

## Point-Free Style — When to Use, When to Avoid

Point-free (or "tacit") style means writing functions without naming their arguments:

```ts
// Pointful
const double = (x: number) => x * 2;
const incrementAll = (arr: readonly number[]) => arr.map((x) => x + 1);

// Point-free
const double = multiply(2);
const incrementAll = map(add(1));
```

The point-free form is shorter and emphasizes the *transformation* over the *value being transformed*. It composes beautifully:

```ts
const process = pipe(
  trim,
  toLowerCase,
  split(" "),
  map(capitalize),
  join(" "),
);
```

But it has costs:

- **Type errors get harder** — when one step's output doesn't match the next step's input, the error message names types in the chain rather than a specific argument.
- **Debugging is harder** — there's no `x` to `console.log` mid-chain.
- **It's unfamiliar to many readers** — colleagues coming from imperative or OOP backgrounds will read pointful code faster.

**Heuristic:** use point-free when each step is a named, well-understood function. Drop into pointful (`(x) => ...`) when the step is bespoke, complex, or benefits from a named argument for readability.

## Composition Beats Inheritance

A common refactor when introducing functional style: **replace base classes with composed functions**.

```ts
// Inheritance
abstract class Validator {
  validate(input: unknown): boolean { /* template method */ }
  protected abstract check(input: unknown): boolean;
  protected normalize(input: unknown): unknown { return input; }
}

class EmailValidator extends Validator {
  protected check(input: unknown) { return /@/.test(String(input)); }
}

// Composition
const validateEmail = pipe(
  parseString,                          // unknown -> Result<string, ParseError>
  flatMap(normalizeEmail),              // string  -> Result<string, NormalizeError>
  flatMap(checkEmailFormat),            // string  -> Result<Email, FormatError>
);
```

The composed version:
- Each step is independently testable
- The error type at each step is precise
- Adding a new validator is adding a function, not a class hierarchy
- No "what does the base class default behavior do" mystery

Use composition for behavior that varies; use shared functions for behavior that's identical.

## Common Pitfalls

- **A 50-step `pipe` chain.** Composition makes pipelines easy to grow; it doesn't mean every pipeline should be giant. If a pipe is hard to follow, name intermediate functions or break it up.
- **Mixing `pipe` and `compose` in one codebase.** Pick a direction. Mixing is a recipe for confusion.
- **Functions that aren't pipe-friendly because data isn't last.** A multi-arg function with the value first can't drop into a pipe without an arrow wrapper. Curry it (data-last) once, then it's reusable.
- **Building a `pipe` helper from scratch in every project, repeatedly.** Add the 10-line helper to a shared utility module and import it. Don't paste it.
- **Point-free style applied to functions with confusing types.** If the type errors are unreadable, drop back to a named-argument form.
- **Method chaining that switches types mid-chain.** `arr.map(...).filter(...).reduce(...)` is fine; `arr.map(...).then(...)` (turning a value into a promise mid-chain) breaks the pattern. Switch to `pipe` once the receiver type changes.
- **Composing without thinking about `Result` early.** A pipe of throwing functions short-circuits on uncaught exceptions — but the exception type is invisible in the signature. Lift to `Result` early so the error path is part of the type.
- **Forgetting that `pipe(value, fn)` and `compose(fn)(value)` are equivalent.** They produce the same thing, just written in different orders. The choice is purely stylistic; argue about it once and move on.
- **Excessive intermediate variables that defeat the pipe.** `const a = ...; const b = pipe(a, ...); const c = pipe(b, ...);` — usually those should all be one pipe. Or, if they're conceptually distinct steps, give them distinct names but skip the pipe boilerplate.
