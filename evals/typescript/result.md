# Eval report: `typescript`

- Cases: **6**
- Expectations met: **2/6** (skill_wins 1/4, skill_wins_strict 0/1, tie 1/1)
- Judge: skill won **1**, baseline won **0**, ties **5**
- Rubric pass-rate (over 5 scored case(s)): baseline **87%**, skill **87%** (Δ **+0%**)
- CLI cost: **$0.39** (judge cost not counted)

## Cases

| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |
| --- | --- | --- | --- | --- | --- |
| `discriminated-union-exhaustive` | skill_wins | ✗ | **tie** | 100% | 100% |
| `satisfies-vs-annotation` | skill_wins | ✗ | **tie** | 100% | 100% |
| `unknown-vs-any` | skill_wins | ✗ | **tie** | 100% | 100% |
| `branded-types` | skill_wins | ✓ | **skill** | 100% | 100% |
| `simplest-cast` | skill_wins_strict | ✗ | **tie** | 33% | 33% |
| `offtopic-shell-pipe` | tie | ✓ | **tie** | 0% | 0% |

## Per-case detail

### `discriminated-union-exhaustive`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I have a TypeScript type representing a request lifecycle:
`type Request = { kind: "pending" } | { kind: "ok", value: string } | { kind: "error", message: string }`.
Show me how to handle all variants in a function and ensure that
if I add a new variant later, the compiler will catch all the
places I forgot to update.
```

**Judge:** **tie** — Both answers correctly implement the switch-on-discriminant pattern with an assertNever exhaustiveness check and avoid any casts. Answer A provides slightly more tips and a match helper, while Answer B includes a useful bonus section on noImplicitReturns. Both are essentially equivalent in correctness and idiomaticity for the core criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses switch on discriminant | tie |
| uses never-typed exhaustiveness check | tie |
| avoids any | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses switch on discriminant | ✓ | `switch (req.kind` |
| uses never-typed exhaustiveness check | ✓ | `: never` |
| avoids any | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses switch on discriminant | ✓ | `switch (req.kind` |
| uses never-typed exhaustiveness check | ✓ | `: never` |
| avoids any | ✓ | |

<details><summary>Baseline answer</summary>

# Exhaustive Handling with a `never` Helper

The trick is to add a default branch that assigns the value to `never`. Since `never` accepts no values, the compiler will reject any code that reaches it with an unhandled variant.

```ts
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

// Helper that crashes at runtime AND fails to type-check
// if `x` could be anything other than `never`.
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function describe(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Still working...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Failed: ${req.message}`;
    default:
      // If every case above is handled, `req` is narrowed to `never` here.
      return assertNever(req);
  }
}
```

## Why this works

Inside each `case`, TypeScript narrows `req` based on the `kind` discriminant. After all known cases are handled, the only type left for `req` is `never`. Passing it to `assertNever(x: never)` type-checks fine — *until* you add a new variant.

## What happens when you add a variant

Suppose later you extend the type:

```ts
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string };   // 👈 new
```

Now in `describe`, the `default` branch sees `req` narrowed to `{ kind: "cancelled"; reason: string }`, not `never`. The compiler errors:

```
Argument of type '{ kind: "cancelled"; reason: string; }'
is not assignable to parameter of type 'never'.
```

Every `switch` that uses `assertNever` will light up across your codebase, pointing you to exactly the spots that need updating.

## Bonus: enforce return-type exhaustiveness without a default

If your function has a non-`void` return type, you can also rely on TypeScript's "not all code paths return a value" check by omitting the `default`:

```ts
function describe(req: Request): string {
  switch (req.kind) {
    case "pending": return "Still working...";
    case "ok":      return `Success: ${req.value}`;
    case "error":   return `Failed: ${req.message}`;
  }
  // No return here — adding a new variant makes this a compile error.
}
```

This works as long as `noImplicitReturns` is enabled in `tsconfig.json`. The `assertNever` pattern is more robust though — it works for `void`-returning functions and gives a clear runtime error if a bad value sneaks in from untyped code (e.g. JSON from the network).

</details>

<details><summary>Skill-loaded answer</summary>

# Exhaustive Handling with the `never` Trick

The idiomatic pattern in TypeScript is to use a **discriminated union** (which you already have, via the `kind` field) combined with an **exhaustiveness check** using the `never` type. Here's how:

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

// Helper that asserts a value is `never`. If a new variant is added
// to `Request`, the compiler will reject the call to this function.
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function describe(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Still waiting...";
    case "ok":
      // TypeScript narrows `req` to { kind: "ok"; value: string } here
      return `Success: ${req.value}`;
    case "error":
      return `Failed: ${req.message}`;
    default:
      // If every case above is handled, `req` is narrowed to `never`.
      return assertNever(req);
  }
}
```

## Why this works

In each `case` branch, TypeScript narrows the type of `req` based on the `kind` literal. After all known variants are handled, the only type remaining for `req` in the `default` branch is `never` — meaning "this can't happen."

## What happens when you add a variant

Suppose you later extend the type:

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string }; // <-- new!
```

Now in `describe`, the `default` branch will see `req` as `{ kind: "cancelled"; reason: string }` instead of `never`. The call `assertNever(req)` will fail to compile with:

```
Argument of type '{ kind: "cancelled"; reason: string; }'
is not assignable to parameter of type 'never'.
```

The compiler error will fire at **every** `switch` (or `if/else` chain) where you forgot to add a `case "cancelled"` — exactly what you wanted.

## Tips for stronger guarantees

1. **Enable `strict` mode** in `tsconfig.json` (especially `strictNullChecks`) so narrowing works reliably.
2. **Turn on `noFallthroughCasesInSwitch`** to prevent accidentally falling through a case without a `return`/`break`.
3. **Prefer `switch` over `if`/`else if`** for unions — TypeScript's narrowing on `switch` over a literal discriminant is the most reliable.
4. If you want exhaustiveness without throwing at runtime, you can use the assertion in a type-only position:

   ```typescript
   const _exhaustive: never = req; // compile-time only
   ```

5. For expression-style code, you can use a small helper to avoid the `default` boilerplate:

   ```typescript
   function match<R>(
     req: Request,
     handlers: {
       pending: () => R;
       ok: (v: string) => R;
       error: (m: string) => R;
     }
   ): R {
     switch (req.kind) {
       case "pending": return handlers.pending();
       case "ok":      return handlers.ok(req.value);
       case "error":   return handlers.error(req.message);
     }
   }
   ```

   Adding a new variant to `Request` will force you to update the `handlers` object's type, again giving compile-time errors at every call site.

This pattern — discriminated unions + `assertNever` — is the TypeScript equivalent of exhaustive pattern matching in languages like Rust, Haskell, or OCaml.

</details>

---

### `satisfies-vs-annotation`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
What's the difference between writing `const config: Config = { ... }`
and `const config = { ... } satisfies Config` in TypeScript? When
should I use `satisfies`?
```

**Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A uses a slightly more concrete example with `features` and route maps, while Answer B adds a discriminated union example and a cleaner 'check vs declare' rule of thumb. Both explain widening, satisfies, and literal type preservation with equal clarity and correctness.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions widening from annotation | tie |
| uses satisfies keyword | tie |
| mentions preserving literal / narrow inferred type | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions widening from annotation | ✓ | `widen` |
| uses satisfies keyword | ✓ | `satisfies` |
| mentions preserving literal / narrow inferred type | ✓ | `preserv` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions widening from annotation | ✓ | `widen` |
| uses satisfies keyword | ✓ | `satisfies` |
| mentions preserving literal / narrow inferred type | ✓ | `preserv` |

<details><summary>Baseline answer</summary>

# Type Annotation vs `satisfies` in TypeScript

These two approaches look similar but behave very differently. The key difference is **how the type of `config` is inferred**.

## Type Annotation: `const config: Config = { ... }`

This **widens** the type of `config` to `Config`. The variable loses any information about its specific literal values.

```typescript
type Config = {
  mode: "dev" | "prod";
  features: Record<string, boolean>;
};

const config: Config = {
  mode: "dev",
  features: { darkMode: true, beta: false },
};

config.mode;            // type: "dev" | "prod"
config.features.beta;   // type: boolean | undefined
config.features.foo;    // type: boolean | undefined  (no error!)
```

## `satisfies`: `const config = { ... } satisfies Config`

This **validates** the object against `Config` without widening. You get the benefits of type-checking *and* keep the precise inferred type.

```typescript
const config = {
  mode: "dev",
  features: { darkMode: true, beta: false },
} satisfies Config;

config.mode;            // type: "dev"  (literal preserved!)
config.features.beta;   // type: boolean (not undefined)
config.features.foo;    // ❌ Error: Property 'foo' does not exist
```

## When to Use Each

**Use `satisfies` when you want to:**
- Preserve literal types and exact keys for downstream inference
- Catch typos/extra properties on `Record`-style types
- Build a value that must conform to a contract but is also consumed elsewhere with stronger guarantees (e.g., route maps, config objects, discriminated lookups)
- Get autocomplete for keys without losing the actual subset you defined

**Use `: Type` annotation when you want to:**
- Allow the variable to later be reassigned to any valid `Config`
- Intentionally widen (e.g., a mutable container that may grow)
- Document the contract at the binding site, and you don't care about narrower inference

## A Concrete Example

```typescript
type Routes = Record<string, { path: string }>;

// With annotation — keys are lost
const routesA: Routes = {
  home: { path: "/" },
  about: { path: "/about" },
};
routesA.hme;  // type: { path: string } | undefined  (typo not caught!)

// With satisfies — keys preserved, typos caught at use sites
const routesB = {
  home: { path: "/" },
  about: { path: "/about" },
} satisfies Routes;
routesB.hme;  // ❌ Error: Property 'hme' does not exist
type RouteName = keyof typeof routesB;  // "home" | "about"
```

## Rule of Thumb

> Reach for `satisfies` by default for constants and configuration. Reach for `: Type` only when you genuinely need the broader type — typically for variables that will be reassigned or passed through APIs that expect the wider shape.

</details>

<details><summary>Skill-loaded answer</summary>

# Type Annotation vs `satisfies` in TypeScript

Both approaches validate that your value conforms to `Config`, but they preserve type information differently.

## `const config: Config = { ... }`

This **widens** the value to the declared type. The variable's type becomes exactly `Config` — you lose information about the specific literal values you wrote.

```ts
type Config = {
  env: "dev" | "prod";
  features: Record<string, boolean>;
};

const config: Config = {
  env: "dev",
  features: { darkMode: true, beta: false },
};

config.env;              // type: "dev" | "prod"
config.features.darkMode; // type: boolean | undefined  ❌
config.features.unknown;  // type: boolean | undefined  (no error)
```

## `const config = { ... } satisfies Config`

This **validates** the value against `Config` *without widening it*. The variable keeps its narrow, inferred type.

```ts
const config = {
  env: "dev",
  features: { darkMode: true, beta: false },
} satisfies Config;

config.env;              // type: "dev"  ✅ (literal preserved)
config.features.darkMode; // type: boolean  ✅ (key known to exist)
config.features.unknown;  // ❌ Property 'unknown' does not exist
```

You still get an error if the object doesn't match `Config`:

```ts
const bad = {
  env: "staging",  // ❌ not assignable to "dev" | "prod"
  features: {},
} satisfies Config;
```

## When to use `satisfies`

Reach for `satisfies` when you want **type checking without losing precision**:

1. **Const-like config objects** where you want to preserve literal types and known keys.
2. **Discriminated union members** where you want the narrower variant retained:
   ```ts
   const action = { type: "increment", by: 1 } satisfies Action;
   // action.type stays "increment", not the full union
   ```
3. **Records with known keys** — you constrain to `Record<string, T>` while keeping autocomplete on actual keys.
4. **Lookup tables / route maps** where you want both validation *and* `keyof typeof` to work usefully.
5. **Returning literals from functions** while ensuring they conform to a contract.

## When to use a type annotation instead

- **Mutable variables** (`let`) where the variable should accept any valid `Config` later.
- **Public API surfaces** where you deliberately want callers to see the wide type, not implementation details.
- **Function parameters and return type signatures** — `satisfies` doesn't apply here; use annotations.
- When you actually want the value widened (e.g., to allow reassignment to other valid shapes).

## Rule of thumb

> Use `satisfies` to **check** a value against a type. Use `: Type` to **declare** that a binding *is* that type.

If you're writing a const literal and want both safety and the most precise inferred type, `satisfies` is almost always the better tool.

</details>

---

### `unknown-vs-any`

**Expected:** `skill_wins` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I'm parsing JSON from an HTTP response in TypeScript. What type
should the parsed value have, and why?
```

**Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A provides a richer explanation of why `any` is dangerous with concrete crash examples and a summary table, while Answer B shows a more detailed manual narrowing example with type guards before introducing Zod. Both recommend `unknown`, explain why `any` is problematic, and demonstrate validation/narrowing steps.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends unknown | tie |
| explains why not any | skill |
| shows narrowing or validation step | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✓ | `any` disable` |
| shows narrowing or validation step | ✓ | `typeof` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✓ | `any` disable` |
| shows narrowing or validation step | ✓ | `narrow` |

<details><summary>Baseline answer</summary>

# Parsing JSON in TypeScript: The Right Type

The parsed value should be typed as **`unknown`**, not `any`.

## Why `unknown`?

When you call `JSON.parse()`, TypeScript types the result as `any` by default. This is unsafe because `any` disables all type checking — you can access any property, call it as a function, or assign it anywhere without errors, even though the actual runtime value could be anything.

`unknown` is the type-safe counterpart to `any`: it represents "a value whose type we don't know yet," but TypeScript forces you to **narrow it** (via type guards, schema validation, etc.) before you can use it.

## Example

```ts
async function fetchUser(id: string) {
  const res = await fetch(`/api/users/${id}`);
  const data: unknown = await res.json(); // 👈 force unknown

  // ❌ TS error — can't access properties on unknown
  // return data.name;

  // ✅ Narrow first
  if (
    typeof data === "object" &&
    data !== null &&
    "name" in data &&
    typeof data.name === "string"
  ) {
    return data.name; // now typed as string
  }

  throw new Error("Invalid user response");
}
```

## In practice: use a validator

Hand-written type guards get tedious, so most teams use a runtime schema library that produces a properly typed value from `unknown`:

```ts
import { z } from "zod";

const User = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
});

const data: unknown = await res.json();
const user = User.parse(data); // typed as { id: string; name: string; email: string }
```

Other popular options: **Valibot**, **ArkType**, **io-ts**, **TypeBox**, or `@effect/schema`.

## The key principle

**Data crossing a trust boundary** (network, disk, user input, `eval`) should enter your program as `unknown` and only become a concrete type after validation. This prevents runtime shape mismatches from silently corrupting your code — exactly the class of bug TypeScript is supposed to catch.

</details>

<details><summary>Skill-loaded answer</summary>

# Parsing JSON in TypeScript: The Right Type

The parsed value should be typed as **`unknown`**, not `any`.

## Why `unknown`?

When you call `JSON.parse()` or `await response.json()`, TypeScript actually types the result as `any` by default — but that's a footgun, not a feature. Here's why `unknown` is the correct choice:

### 1. `any` disables type checking entirely
```ts
const data: any = await response.json();
data.user.name.toUpperCase(); // ✅ Compiles, 💥 crashes at runtime
data.foo.bar.baz();           // ✅ Compiles, 💥 crashes at runtime
```
`any` silently propagates through your codebase, infecting every value it touches.

### 2. `unknown` forces you to validate
```ts
const data: unknown = await response.json();
data.user.name; // ❌ Compile error: Object is of type 'unknown'
```
You're forced to narrow the type before using it, which matches reality: **you don't actually know what the server sent you.**

### 3. The server's contract is not a guarantee
Even if your API "should" return `{ user: { name: string } }`, the response could be:
- An error payload with a different shape
- A newer/older API version
- HTML from a misconfigured proxy
- Malformed data from a bug

The TypeScript compiler can't verify what crosses the network boundary, so the type system shouldn't pretend it can.

## The recommended pattern

Validate at the boundary using a schema library like **Zod**, **Valibot**, or **ArkType**:

```ts
import { z } from "zod";

const UserSchema = z.object({
  user: z.object({ name: z.string() }),
});

const response = await fetch("/api/user");
const raw: unknown = await response.json();
const data = UserSchema.parse(raw); // typed as { user: { name: string } }
```

Now `data` has a precise, *trustworthy* type — earned through runtime validation, not assumed through wishful typing.

## Summary

| Type | Use it? | Why |
|------|---------|-----|
| `any` | ❌ | Silently disables type safety |
| `unknown` | ✅ | Forces validation before use |
| `MyInterface` | ⚠️ | Only after runtime validation |

**Rule of thumb:** treat every value crossing a trust boundary (network, disk, user input) as `unknown` until proven otherwise.

</details>

---

### `branded-types`

**Expected:** `skill_wins` · **Met:** ✓

**Prompt**

```
In my TypeScript codebase I have UserId and OrderId, both currently
just `string`. We have a bug where someone passed an OrderId to a
function expecting a UserId and TypeScript didn't catch it. How do
I prevent this kind of mistake?
```

**Judge:** **skill** — Both answers are excellent and cover all three rubric criteria well, but Answer B edges out Answer A by including an additional practical section explaining why class wrappers are inferior to branded types, which adds useful context for the reader's decision-making. Answer B also explicitly notes that raw strings are rejected (must go through constructor), which is a subtle but important point. Both use `unique symbol` with `__brand`-style phantom properties and explain structural typing as the root cause.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends branded types | tie |
| shows __brand or similar phantom property | tie |
| explains structural typing as the cause | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✓ | `structural` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `Brand` |
| shows __brand or similar phantom property | ✓ | `unique symbol` |
| explains structural typing as the cause | ✓ | `structural` |

<details><summary>Baseline answer</summary>

Great question — this is a classic case of **primitive obsession**, and the fix in TypeScript is to use **branded (a.k.a. nominal/opaque) types**. TypeScript uses structural typing by default, so any two `string` aliases are interchangeable. You need to add a "phantom" property to make them distinct at the type level.

## The pattern

```ts
declare const brand: unique symbol;
type Brand<T, B> = T & { readonly [brand]: B };

export type UserId  = Brand<string, "UserId">;
export type OrderId = Brand<string, "OrderId">;
```

Now `UserId` and `OrderId` are *not* assignable to each other, even though both are still `string` at runtime (zero cost).

## Constructing values

You can't just assign a raw string anymore, which is the whole point. Provide smart constructors that do validation:

```ts
export const UserId = (s: string): UserId => {
  if (!/^usr_/.test(s)) throw new Error(`Invalid UserId: ${s}`);
  return s as UserId;
};

export const OrderId = (s: string): OrderId => {
  if (!/^ord_/.test(s)) throw new Error(`Invalid OrderId: ${s}`);
  return s as OrderId;
};
```

The `as` cast is isolated to one place, so the rest of your code stays honest.

## What this catches

```ts
function getUser(id: UserId) { /* ... */ }

const orderId: OrderId = OrderId("ord_123");
getUser(orderId);
// ❌ Argument of type 'OrderId' is not assignable to parameter of type 'UserId'.
```

## Tips

1. **Use a single shared `Brand` helper** — don't redefine the pattern per ID type.
2. **Use `unique symbol`** (rather than a string property like `__brand`) so the brand can't be accidentally constructed from a plain object.
3. **Brand at boundaries** — when data enters your system (HTTP, DB, JSON), validate and brand it once. Inside your code, just pass the branded type around.
4. **Pair with a parser like Zod / Valibot / Effect Schema** if you want runtime validation and the branded type for free:
   ```ts
   const UserIdSchema = z.string().startsWith("usr_").brand<"UserId">();
   type UserId = z.infer<typeof UserIdSchema>;
   ```
5. **Apply liberally** — it's also great for `Email`, `Url`, `PositiveInt`, `IsoDateString`, currency amounts, etc. Anywhere a primitive carries domain meaning.

The runtime cost is zero; it's purely a compile-time guard. After you introduce it, the compiler will surface every existing place where IDs are getting crossed — exactly the bug you just hit.

</details>

<details><summary>Skill-loaded answer</summary>

# Preventing ID Mix-ups with Branded Types

This is a classic TypeScript pitfall. Since `type UserId = string` and `type OrderId = string` are just aliases, TypeScript treats them as structurally identical. The fix is **branded (or "nominal") types**.

## The Pattern

```typescript
declare const brand: unique symbol;
type Brand<T, B> = T & { readonly [brand]: B };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
```

Now `UserId` and `OrderId` are *not* assignable to each other, even though both are `string` at runtime.

## Constructing Branded Values

You need a controlled way to create them. A common approach is a small "smart constructor":

```typescript
function UserId(raw: string): UserId {
  // optional runtime validation
  if (!/^u_[a-z0-9]+$/.test(raw)) {
    throw new Error(`Invalid UserId: ${raw}`);
  }
  return raw as UserId;
}

function OrderId(raw: string): OrderId {
  if (!/^o_[a-z0-9]+$/.test(raw)) {
    throw new Error(`Invalid OrderId: ${raw}`);
  }
  return raw as OrderId;
}
```

## Using Them

```typescript
function getUser(id: UserId) { /* ... */ }

const u = UserId('u_abc');
const o = OrderId('o_123');

getUser(u); // ✅ ok
getUser(o); // ❌ Argument of type 'OrderId' is not assignable to parameter of type 'UserId'
getUser('u_abc'); // ❌ raw string also rejected — must go through constructor
```

## Practical Tips

1. **Centralize the brand helper.** Put `Brand<T, B>` in one shared module (e.g. `src/types/brand.ts`) and import it everywhere.
2. **Force construction through smart constructors.** Don't sprinkle `as UserId` casts around the codebase — restrict the cast to one file per ID type. You can even enforce this with an ESLint rule banning `as UserId`/`as OrderId` outside that file.
3. **Parse at the boundary.** When IDs come from JSON, the database, or HTTP params, validate and brand them once at the edge (e.g. inside your API layer or with a Zod schema using `.brand<'UserId'>()`). Internal code then trusts the type.
4. **Zod shortcut** if you already use Zod:
   ```typescript
   const UserIdSchema = z.string().regex(/^u_/).brand<'UserId'>();
   type UserId = z.infer<typeof UserIdSchema>;
   ```
5. **Zero runtime cost.** The brand only exists in the type system; at runtime these are still plain strings, so JSON serialization, logging, and DB drivers work unchanged.
6. **Apply broadly.** The same trick is great for `Email`, `Url`, `IsoDateString`, `PositiveInt`, `Cents` vs `Dollars`, etc. — anywhere the underlying primitive hides a domain distinction.

## Why Not a Class Wrapper?

You *could* do `class UserId { constructor(public value: string) {} }`, which gives nominal typing for free. But it costs you:
- allocations and `.value` access everywhere,
- awkward serialization,
- harder interop with libraries expecting strings.

Branded types give you the same compile-time safety with none of those costs, which is why they're the idiomatic solution in modern TypeScript.

</details>

---

### `simplest-cast`

**Expected:** `skill_wins_strict` · **Met:** ✗ — **[FAILED EXPECTATION]**

**Prompt**

```
I have a TypeScript error: `Type 'unknown' is not assignable to
type 'string'`. The value definitely is a string at runtime. Just
give me the simplest, fewest-character fix to make this compile.
```

**Judge:** **tie** — Both answers are identical — they both recommend the bare `as string` cast without any warning, explanation of unsafety, or mention of type predicates or assertion functions. Neither answer meets the rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses or recommends a type predicate / assertion function | tie |
| warns against bare as cast | tie |
| avoids recommending bare as cast as the answer | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✗ | |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✗ | |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

<details><summary>Baseline answer</summary>

Use `as string`:

```ts
value as string
```

</details>

<details><summary>Skill-loaded answer</summary>

Use `as string`:

```ts
value as string
```

</details>

---

### `offtopic-shell-pipe`

**Expected:** `tie` · **Met:** ✓

**Prompt**

```
What's the simplest one-liner in bash to count the number of
files in the current directory (not recursively, hidden files
excluded)?
```

**Judge:** **tie** — Both answers are identical, providing the same one-liner `ls | wc -l` which correctly counts non-hidden files in the current directory non-recursively.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>Baseline answer</summary>

```bash
ls | wc -l
```

</details>

<details><summary>Skill-loaded answer</summary>

```bash
ls | wc -l
```

</details>

---
