# Eval report: `typescript`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **6**
- Models: **sonnet, haiku, opus**
- Total cost: **$1.52** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 4/6 | 3 / 0 / 3 | 87% → 100% (+13%) |
| `haiku` | 5/6 | 6 / 0 / 0 | 73% → 93% (+20%) |
| `opus` ¹ | 6/6 | 5 / 0 / 1 | 87% → 87% (+0%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 4 | 2/4 | 4/4 | 4/4 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 0/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `discriminated-union-exhaustive` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `satisfies-vs-annotation` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `unknown-vs-any` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `branded-types` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `simplest-cast` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-shell-pipe` | tie | ✓ = tie | ✗ ✓ skill | ✓ = tie |

## Per-case detail

### `discriminated-union-exhaustive`

**Prompt**

```
I have a TypeScript type representing a request lifecycle:
`type Request = { kind: "pending" } | { kind: "ok", value: string } | { kind: "error", message: string }`.
Show me how to handle all variants in a function and ensure that
if I add a new variant later, the compiler will catch all the
places I forgot to update.
```

**Judge focus:** The better answer uses a switch on the discriminant with a
`default: const _: never = x` exhaustive check, not casts or
runtime assertions.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly implement the switch-on-discriminant pattern with a never-typed exhaustiveness check via assertNever, and both avoid `any` in the core handler. The minor differences are that Answer A uses a cast `(request as { kind: string }).kind` in the assertNever message (introducing a small `any`-adjacent cast), while Answer B uses `JSON.stringify(request)` cleanly. Answer B's bonus `match` helper uses a `Record<string, ...>` cast internally but is more type-safe at the call site. Overall both answers are essentially equivalent in quality and correctness for the focus criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses switch on discriminant | tie |
| uses never-typed exhaustiveness check | tie |
| avoids any | baseline |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses switch on discriminant | ✓ | `switch (request.kind` |
| uses never-typed exhaustiveness check | ✓ | `: never` |
| avoids any | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses switch on discriminant | ✓ | `switch (request.kind` |
| uses never-typed exhaustiveness check | ✓ | `: never` |
| avoids any | ✓ | |

<details><summary>sonnet: baseline answer</summary>

## Exhaustive Pattern Matching in TypeScript

The key technique is using a **never-typed exhaustive check** — if all variants are handled, the `default` branch receives type `never`. If you add a new variant and forget to handle it, the compiler errors at that branch.

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

// ─── Exhaustive check helper ───────────────────────────────────────────────
//
// If every variant is handled above this call, TypeScript infers `value` as
// `never` and the function compiles fine.  If a variant is missing, the
// unhandled type flows into `value`, causing a type error right here.

function assertNever(value: never, message?: string): never {
  throw new Error(message ?? `Unhandled variant: ${JSON.stringify(value)}`);
}

// ─── Handler ───────────────────────────────────────────────────────────────

function handleRequest(request: Request): string {
  switch (request.kind) {
    case "pending":
      return "Loading…";

    case "ok":
      return `Success: ${request.value}`; // TS knows `value` exists here

    case "error":
      return `Error: ${request.message}`; // TS knows `message` exists here

    default:
      // If all variants are covered, `request` is `never` here — good.
      // If you add a new variant and forget a case, TS errors:
      //   Argument of type '{ kind: "new" }' is not assignable to 'never'
      return assertNever(request, `Unexpected request kind: ${JSON.stringify(request)}`);
  }
}

// ─── Usage ─────────────────────────────────────────────────────────────────

const examples: Request[] = [
  { kind: "pending" },
  { kind: "ok", value: "Hello!" },
  { kind: "error", message: "Network failure" },
];

examples.forEach((r) => console.log(handleRequest(r)));
// Loading…
// Success: Hello!
// Error: Network failure
```

---

## What Happens When You Add a New Variant

```typescript
// 1. Add the new variant to the union
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string }; // 👈 new

// 2. Forget to add a case in handleRequest → compiler error:
//
//   Argument of type '{ kind: "cancelled"; reason: string }'
//   is not assignable to parameter of type 'never'.
//
// The error points exactly to `assertNever(request)` in every
// switch that is missing the new case.
```

---

## Bonus: Reusable `match` Helper (no switch needed)

For a more functional style, you can enforce exhaustiveness through the type system on the handler object itself:

```typescript
type MatchHandlers<T extends { kind: string }, R> = {
  [K in T["kind"]]: (variant: Extract<T, { kind: K }>) => R;
};

function match<T extends { kind: string }, R>(
  value: T,
  handlers: MatchHandlers<T, R>
): R {
  // The cast is safe: we know value.kind is a key of handlers
  return (handlers as Record<string, (v: T) => R>)[value.kind](value);
}

// Usage — missing any key is a compile-time error
const result = match(examples[1], {
  pending: ()      => "Loading…",
  ok:      (r)     => `Success: ${r.value}`,
  error:   (r)     => `Error: ${r.message}`,
  // Forget `cancelled` after adding it → TS error:
  // Property 'cancelled' is missing in type ...
});
```

---

## Key Takeaways

| Technique | How exhaustiveness is enforced |
|---|---|
| `switch` + `assertNever` | Unhandled variant flows into `never` parameter → type error |
| `match` helper | Object literal must have a key for every `kind` → type error |

Both approaches give you **compile-time safety with zero runtime overhead** for the check itself — `assertNever` only runs if you somehow bypass the type system (e.g., an unsafe cast).

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Exhaustive Discriminated Union Handling

The key is a `never`-typed default branch. When you add a variant, TypeScript can no longer assign it to `never`, and the function becomes a compile error at every unhandled switch.

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

// The exhaustiveness sentinel. Placing it in a shared module means
// every switch that imports it gets the same guarantee.
function assertNever(value: never, message?: string): never {
  throw new Error(message ?? `Unhandled variant: ${JSON.stringify(value)}`);
}

function describeRequest(request: Request): string {
  switch (request.kind) {
    case "pending":
      return "Loading…";
    case "ok":
      return `Success: ${request.value}`;   // request is narrowed to { kind: "ok"; value: string }
    case "error":
      return `Error: ${request.message}`;   // request is narrowed to { kind: "error"; message: string }
    default:
      // If every variant is handled above, `request` is `never` here.
      // If you add a new variant and forget this branch, the compiler
      // flags this line: "Argument of type 'NewVariant' is not assignable
      // to parameter of type 'never'."
      return assertNever(request, `Unhandled request kind: ${(request as { kind: string }).kind}`);
  }
}
```

### What happens when you add a variant

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string };  // ← new variant added
```

`describeRequest` now produces a compile error immediately:

```
Argument of type '{ kind: "cancelled"; reason: string }' is not
assignable to parameter of type 'never'.
```

The error points directly at the `assertNever` call — no runtime surprise, no silent fallthrough.

---

### Returning a value from each branch (generic helper)

When you need to map a `Request` to a value rather than just describe it, a `match` helper makes the exhaustiveness requirement part of the call site's type signature:

```typescript
type RequestHandlers<T> = {
  pending: () => T;
  ok: (value: string) => T;
  error: (message: string) => T;
};

function matchRequest<T>(request: Request, handlers: RequestHandlers<T>): T {
  switch (request.kind) {
    case "pending": return handlers.pending();
    case "ok":      return handlers.ok(request.value);
    case "error":   return handlers.error(request.message);
    default:        return assertNever(request);
  }
}

// Call site — the object literal must satisfy RequestHandlers<string>.
// Adding a variant to Request makes RequestHandlers require a new key,
// so every matchRequest call site becomes a compile error too.
const label = matchRequest(request, {
  pending: ()        => "Loading…",
  ok:      (value)   => `Success: ${value}`,
  error:   (message) => `Error: ${message}`,
});
```

`RequestHandlers<T>` is a mapped type over the union's tags, so adding `"cancelled"` to `Request` forces you to add `cancelled` to every `RequestHandlers` object — the compiler catches every call site, not just the switch.

---

### Key mechanics

| Mechanism | What it does |
|---|---|
| `switch` on the tag field | Narrows the type in each `case` branch |
| `never` in the `default` | Proves statically that all variants are covered |
| `assertNever(x: never)` | Converts the static proof into a runtime guard |
| `RequestHandlers<T>` object type | Propagates the exhaustiveness requirement to every call site |

The `assertNever` throw is a safety net for the impossible case — if the value somehow reaches it at runtime (e.g., data from an untyped boundary), you get a clear error instead of silent `undefined`.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers use a switch on the discriminant with a `never`-typed exhaustiveness check and avoid `any`. However, Answer B is more focused and idiomatic: it uses `const _exhaustive: never = req` (matching the rubric's exact pattern `const _: never = x`) as the primary recommendation without diluting it with less-safe alternatives like the `Record<Request['kind'], (req: Request & { kind: any }) => string>` pattern that Answer A includes. Answer B also explicitly warns against `as`/`as any` casts, directly addressing the rubric's 'avoids any' criterion, and keeps the presentation cleaner and more pedagogically sound.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses switch on discriminant | tie |
| uses never-typed exhaustiveness check | skill |
| avoids any | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses switch on discriminant | ✓ | `switch (req.kind` |
| uses never-typed exhaustiveness check | ✓ | `: never` |
| avoids any | ✗ | `: any` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses switch on discriminant | ✓ | `switch (req.kind` |
| uses never-typed exhaustiveness check | ✓ | `: never` |
| avoids any | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Exhaustive Pattern Matching in TypeScript

Here are several approaches to ensure the compiler catches missing cases when you add new variants:

## 1. **Switch with Exhaustiveness Check (Recommended)**

```typescript
type Request = 
  | { kind: "pending" } 
  | { kind: "ok"; value: string } 
  | { kind: "error"; message: string };

function handleRequest(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Loading...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Error: ${req.message}`;
    default:
      // This will cause a compile error if you add a new variant
      const _exhaustive: never = req;
      return _exhaustive;
  }
}
```

**How it works:** If you add a new variant, `req` won't be `never` anymore, and TypeScript will error on the assignment.

## 2. **Helper Function for Extra Safety**

```typescript
function assertNever(value: never): never {
  throw new Error(`Unhandled value: ${value}`);
}

function handleRequest(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Loading...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Error: ${req.message}`;
    default:
      return assertNever(req);
  }
}
```

## 3. **If-Else with Type Narrowing**

```typescript
function handleRequest(req: Request): string {
  if (req.kind === "pending") {
    return "Loading...";
  } else if (req.kind === "ok") {
    return `Success: ${req.value}`;
  } else if (req.kind === "error") {
    return `Error: ${req.message}`;
  } else {
    const _exhaustive: never = req;
    return _exhaustive;
  }
}
```

## 4. **Object Map Pattern (Functional)**

```typescript
const handlers: Record<Request["kind"], (req: Request & { kind: any }) => string> = {
  pending: () => "Loading...",
  ok: (req) => `Success: ${req.value}`,
  error: (req) => `Error: ${req.message}`,
};

function handleRequest(req: Request): string {
  return handlers[req.kind](req);
}
```

⚠️ **Note:** This pattern is less type-safe because `Record` doesn't enforce that all keys are handled.

## 5. **Better Object Map with Type Safety**

```typescript
type Handlers = {
  [K in Request["kind"]]: (req: Extract<Request, { kind: K }>) => string;
};

const handlers: Handlers = {
  pending: () => "Loading...",
  ok: (req) => `Success: ${req.value}`,
  error: (req) => `Error: ${req.message}`,
};

function handleRequest(req: Request): string {
  return handlers[req.kind](req);
}
```

✅ **This is fully type-safe!** Adding a new variant will cause a compile error here.

## Testing It Out

```typescript
// Add a new variant
type Request = 
  | { kind: "pending" } 
  | { kind: "ok"; value: string } 
  | { kind: "error"; message: string }
  | { kind: "loading"; progress: number }; // ← New variant

// ❌ Compile error in switch approach:
// Type 'Request' is not assignable to type 'never'

// ❌ Compile error in object map approach:
// Property 'loading' is missing in type 'Handlers'
```

## Recommendation

Use **approach #1 (switch with `never`)** or **approach #5 (typed object map)** depending on your preference:
- **Switch**: More explicit, easier to read
- **Object map**: More functional, easier to compose

Both guarantee exhaustiveness checking! 🎯

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Handling Discriminated Unions with Exhaustiveness

Your `Request` type is a **discriminated union** — the `kind` field tags each variant. Here's how to ensure the compiler catches missing cases when you add a new variant.

## Pattern: `never`-Based Exhaustive Default

Use a `switch` on the discriminant with a `default` case that assigns to `never`:

```typescript
type Request = 
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

function handleRequest(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Loading...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Error: ${req.message}`;
    default:
      const _exhaustive: never = req;
      throw new Error(`Unhandled variant: ${_exhaustive}`);
  }
}
```

**Why this works:**
- Each `case` narrows `req` to that variant's type.
- If you add a new variant (e.g., `{ kind: "timeout" }`), the `default` case receives a value that is *not* `never` — TypeScript reports: `Type '{ kind: "timeout" }' is not assignable to type 'never'`.
- The `throw` is unreachable in correct code but documents intent: "this should never happen."

---

## Adding a New Variant: Compiler Catches It

Suppose you add a timeout variant:

```typescript
type Request = 
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "timeout" };  // ← new variant
```

Now `handleRequest` fails to compile:

```
Type '{ kind: "timeout"; }' is not assignable to type 'never'.
```

You're forced to add the case:

```typescript
function handleRequest(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Loading...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Error: ${req.message}`;
    case "timeout":  // ← compiler forced this
      return "Request timed out";
    default:
      const _exhaustive: never = req;
      throw new Error(`Unhandled variant: ${_exhaustive}`);
  }
}
```

---

## Alternative: `if`/`else` with Exhaustiveness

If you prefer `if`/`else`, the same pattern works:

```typescript
function handleRequest(req: Request): string {
  if (req.kind === "pending") {
    return "Loading...";
  } else if (req.kind === "ok") {
    return `Success: ${req.value}`;
  } else if (req.kind === "error") {
    return `Error: ${req.message}`;
  } else {
    const _exhaustive: never = req;
    throw new Error(`Unhandled variant: ${_exhaustive}`);
  }
}
```

---

## Returning a Discriminated Union

If your function *produces* a `Request`, the same exhaustiveness pattern applies:

```typescript
function fetchUser(id: string): Request {
  // Simulate async work
  if (id === "1") {
    return { kind: "ok", value: "Alice" };
  } else if (id === "2") {
    return { kind: "error", message: "Not found" };
  } else {
    return { kind: "pending" };
  }
}

// Caller handles all variants:
const result = fetchUser("1");
switch (result.kind) {
  case "pending":
    console.log("Still loading...");
    break;
  case "ok":
    console.log("User:", result.value);
    break;
  case "error":
    console.log("Failed:", result.message);
    break;
  default:
    const _exhaustive: never = result;
    throw new Error(`Unhandled: ${_exhaustive}`);
}
```

---

## Why Not `as`?

You might be tempted to cast away the error:

```typescript
// ❌ DON'T DO THIS
default:
  throw new Error(`Unhandled: ${(req as never).kind}`);
```

This **silences the compiler** — adding a new variant won't produce an error. You've deleted the only guarantee the compiler was about to give you. Always use the `never` assignment instead.

---

## Key Takeaways

| Pattern | Benefit |
|---------|---------|
| `switch (x.kind)` with `default: const _: never = x` | Compiler error when you add a variant; forces update at every consumer |
| `if (x.kind === "...") ... else { const _: never = x }` | Same exhaustiveness guarantee; more verbose but sometimes clearer |
| `as` or `as any` | ❌ Silences the check; new variants slip through unnoticed |

Use the `never` default everywhere you handle a discriminated union. It's the most powerful tool TypeScript gives you for catching refactoring mistakes at compile time.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use a switch on the discriminant with a never-typed exhaustiveness check and avoid `any`. Answer A is slightly more comprehensive: it shows both the inline `const _exhaustive: never = req` pattern AND the `assertNever` helper, explicitly demonstrating the pattern the rubric focuses on (the `const _: never = x` form) before refactoring to the helper. Answer B jumps straight to `assertNever` without showing the inline form. Answer A also provides more practical guidance (noImplicitReturns tip, warning against if/else chains, avoiding `as` casts), making it more educational overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses switch on discriminant | tie |
| uses never-typed exhaustiveness check | skill |
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

<details><summary>opus: baseline answer</summary>

# Exhaustive Pattern Matching in TypeScript

The trick is to use a **`never`-typed helper** in the `default` case (or after the switch). TypeScript narrows the discriminated union as you handle each `kind`, so any unhandled variant will fail to be assignable to `never`.

## The Pattern

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

// Helper: if this is ever called, it means we missed a case.
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function describe(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Still waiting...";
    case "ok":
      return `Got value: ${req.value}`;
    case "error":
      return `Failed: ${req.message}`;
    default:
      // At this point, `req` should be narrowed to `never`.
      return assertNever(req);
  }
}
```

## How the Safety Net Works

Suppose you later add a new variant:

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "timeout"; afterMs: number }; // ← new!
```

Now the `describe` function fails to compile:

```
Argument of type '{ kind: "timeout"; afterMs: number; }'
is not assignable to parameter of type 'never'.
```

The error pinpoints **every** function that uses `assertNever` and forgot to handle the new case. Fix them all, and the project compiles again.

## Bonus: Returning Values Exhaustively

You can also use this with expressions, which is even cleaner because TypeScript will check the return type too:

```typescript
function statusCode(req: Request): number {
  switch (req.kind) {
    case "pending": return 102;
    case "ok":      return 200;
    case "error":   return 500;
    default:        return assertNever(req);
  }
}
```

## Why Not Just `default: throw`?

```typescript
default:
  throw new Error("unreachable"); // ❌ no compile-time check
```

Without `assertNever`, TypeScript happily ignores missing cases because the `default` branch satisfies the return type. The `never` parameter is what turns a runtime guard into a **compile-time guarantee**.

## Tip: Enforce Project-Wide

Enable these in `tsconfig.json` to make the pattern even safer:

```json
{
  "compilerOptions": {
    "strict": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

With `strict` on, TypeScript narrows discriminated unions properly, and `assertNever` becomes your compiler-enforced safety net for every variant added in the future.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Exhaustive Handling with a `never`-Based Default

The pattern: `switch` on the discriminant, then add a `default` branch that assigns the value to `never`. If a new variant is added, the value is no longer assignable to `never` and every `switch` becomes a compile error.

```ts
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

function describe(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "still working...";
    case "ok":
      return `got: ${req.value}`;
    case "error":
      return `failed: ${req.message}`;
    default: {
      // If a new variant is added to `Request`, `req` is no longer `never`
      // here, and this line becomes a compile error.
      const _exhaustive: never = req;
      throw new Error(`unhandled request kind: ${JSON.stringify(req)}`);
    }
  }
}
```

## How it works

Inside each `case`, TypeScript narrows `req` to that variant — so `req.value` is available in `"ok"` and `req.message` in `"error"`, with no casts. By the time control reaches `default`, every known variant has been excluded, so `req` is narrowed to `never`. Assigning to a `never`-typed local is the trick that turns "I forgot a case" into a type error.

The `throw` is also important: it covers the runtime case where some untyped caller passes an invalid value (e.g. data from JSON), so you get a real error instead of `undefined`.

## Reusable helper

If you do this in many places, factor the default branch into a helper:

```ts
function assertNever(x: never): never {
  throw new Error(`unhandled variant: ${JSON.stringify(x)}`);
}

function describe(req: Request): string {
  switch (req.kind) {
    case "pending": return "still working...";
    case "ok":      return `got: ${req.value}`;
    case "error":   return `failed: ${req.message}`;
    default:        return assertNever(req);
  }
}
```

`assertNever` returns `never`, which lets you use it as the `return` expression — keeping the function tidy while preserving exhaustiveness.

## Proving it catches missing cases

Add a fourth variant and watch what happens:

```ts
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string };   // new variant
```

Now `describe` fails to compile:

```
Argument of type '{ kind: "cancelled"; reason: string; }'
  is not assignable to parameter of type 'never'.
```

The error points at the `default` branch of every `switch` you forgot to update — which is exactly what you wanted.

## A couple of related tips

- **Return the result of the switch** (as above) rather than assigning to a `let` and returning it after. With `noImplicitReturns` enabled, TypeScript will additionally verify that every branch returns.
- **Avoid `if/else if` chains** for this — they don't give you the same exhaustiveness guarantee unless you end with the same `assertNever` pattern in the final `else`. `switch` on the tag is the clearest form.
- **Don't `as` your way out of it.** If a `case` body has a type error, the fix is almost never `req as SomeVariant` — the narrowing is already correct; the bug is elsewhere.

</details>

---

### `satisfies-vs-annotation`

**Prompt**

```
What's the difference between writing `const config: Config = { ... }`
and `const config = { ... } satisfies Config` in TypeScript? When
should I use `satisfies`?
```

**Judge focus:** The better answer explains that `: T` widens the inferred type to T,
while `satisfies T` validates the shape without widening — preserving
literal types for downstream inference.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core distinction well, but Answer B is more precise and idiomatic. It clearly articulates that `: T` widens the inferred type while `satisfies` validates without widening, and its examples are tighter and more illustrative of the key concept. Answer B also avoids a misleading claim in Answer A's table ('Assignable to that type: ⚠️ usually, not guaranteed' for satisfies is incorrect — satisfies does guarantee assignability to the checked type). Answer B's 'quick rule of thumb' is also more memorable and accurate.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions widening from annotation | skill |
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

<details><summary>sonnet: baseline answer</summary>

## `const config: Config = {...}` vs `const config = {...} satisfies Config`

These two approaches handle type checking differently in subtle but important ways.

---

## The Core Difference

### Type Annotation (`: Config`)
TypeScript **widens** the type to `Config` — you lose information about the specific values.

```typescript
type Config = {
  port: number;
  env: "development" | "production";
  features: string[];
};

const config: Config = {
  port: 3000,
  env: "development",
  features: ["auth", "logging"],
};

// TypeScript only knows these types:
config.port;     // number  (not 3000)
config.env;      // "development" | "production"  (not just "development")
config.features; // string[]  (not ["auth", "logging"])
```

### `satisfies` Operator
TypeScript **validates** against `Config` but **preserves** the literal/inferred type.

```typescript
const config = {
  port: 3000,
  env: "development",
  features: ["auth", "logging"],
} satisfies Config;

// TypeScript knows the narrower types:
config.port;     // 3000  (literal type!)
config.env;      // "development"  (narrower!)
config.features; // string[]
```

---

## Practical Examples

### Example 1: Catching errors while keeping narrow types

```typescript
type Routes = Record<string, { path: string; exact?: boolean }>;

const routes = {
  home: { path: "/" },
  about: { path: "/about", exact: true },
  typo: { pth: "/oops" }, // ✅ Error caught! 'pth' is not valid
} satisfies Routes;

// Still get autocomplete on specific keys:
routes.home.path;  // ✅ TypeScript knows 'home' exists
routes.xyz;        // ❌ Error: property doesn't exist
```

```typescript
// With annotation, you lose key specificity:
const routes: Routes = { ... };
routes.home; // ✅ works
routes.xyz;  // ✅ also "works" — no error! (bad)
```

### Example 2: Tuple vs Array preservation

```typescript
type Point = { coords: number[] };

// With satisfies — preserves tuple type
const p1 = {
  coords: [10, 20],
} satisfies Point;

const [x, y] = p1.coords; // ✅ Works, inferred as number[]
p1.coords[0];              // number

// With annotation — same here, but consider:
type Config = { color: [number, number, number] | string };

const c1 = { color: [255, 0, 0] } satisfies Config;
c1.color[0]; // ✅ number — TypeScript knows it's a tuple

const c2: Config = { color: [255, 0, 0] };
c2.color[0]; // ❌ Error! Could be string, no index access
```

### Example 3: Method return types

```typescript
type Handler = {
  handle: (input: string) => string | number;
};

const myHandler = {
  handle: (input: string) => input.length, // returns number
} satisfies Handler;

const result = myHandler.handle("hello");
//    ^? number  (not string | number!)

// With annotation:
const myHandler2: Handler = {
  handle: (input: string) => input.length,
};
const result2 = myHandler2.handle("hello");
//    ^? string | number  (widened — less useful)
```

---

## Decision Guide

```
Do you need the variable to BE that type
(e.g., pass it to a function expecting Config)?
│
├── YES → Use annotation: const x: Config = {...}
│         The type IS Config, assignable everywhere Config is expected.
│
└── NO → Do you just want to validate the shape
         while keeping specific types?
         │
         ├── YES → Use satisfies
         │         Validates + preserves literal/narrow types
         │
         └── BOTH → Use both!
                    const x: Config = {...} satisfies Config
```

### Using both together

```typescript
// Validates shape AND widens to Config for assignability
const config: Config = {
  port: 3000,
  env: "development",
} satisfies Config;
```

---

## Quick Reference

| Feature | `: Type` | `satisfies Type` |
|---|---|---|
| Validates shape | ✅ | ✅ |
| Catches extra properties | ✅ | ✅ |
| Preserves literal types | ❌ | ✅ |
| Preserves specific keys | ❌ | ✅ |
| Assignable to that type | ✅ | ⚠️ (usually, not guaranteed) |
| Available since | Always | TS 4.9 |

---

## Rule of Thumb

- Use **`: Type`** when the variable needs to be treated as that type downstream
- Use **`satisfies`** for config objects, lookup tables, and constants where you want **validation without losing specificity**
- Use **both** when you need validation, specificity, *and* guaranteed assignability

</details>

<details><summary>sonnet: skill-loaded answer</summary>

Both validate that your object matches `Config`, but they differ in **what type the variable gets afterward**.

## The core difference

```typescript
type Config = {
  port: number;
  host: string;
  mode: "dev" | "prod";
};

// ❌ Annotation widens the type
const config1: Config = {
  port: 3000,
  host: "localhost",
  mode: "dev",
};

config1.port; // type: number   (lost the literal 3000)
config1.mode; // type: "dev" | "prod"  (lost the literal "dev")


// ✅ satisfies validates but preserves the narrow type
const config2 = {
  port: 3000,
  host: "localhost",
  mode: "dev",
} satisfies Config;

config2.port; // type: 3000   ← literal preserved
config2.mode; // type: "dev"  ← literal preserved
```

With `: Config`, TypeScript widens the inferred type to `Config` — you get the validation, but you lose everything narrower than the annotation. With `satisfies Config`, TypeScript checks the shape against `Config` but keeps the inferred type of the expression itself.

## What satisfies catches that `: Config` doesn't

Both catch missing required fields and wrong value types. `satisfies` additionally catches errors that `: Config` would silently accept through widening:

```typescript
type Routes = {
  [path: string]: { method: "GET" | "POST"; handler: string };
};

const routes = {
  "/users": { method: "GET", handler: "getUsers" },
  "/login": { method: "PAST", handler: "login" }, // ← typo
} satisfies Routes;
//           ~~~~~~
// Type '"PAST"' is not assignable to type '"GET" | "POST"'
```

The annotation version catches this too — so for catching errors, they're equivalent. The difference is purely in what type flows forward.

## When to use each

**Use `satisfies` when** you need the narrow type downstream:

```typescript
// Autocomplete and exhaustiveness work on the literal "dev", not the union
if (config2.mode === "dev") { ... }

// Tuple positions are preserved (not widened to string[])
const palette = ["#ff0000", "#00ff00", "#0000ff"] satisfies string[];
palette[0]; // type: "#ff0000", not string

// Object keys stay as a known union, not just string
const handlers = {
  click: (e: MouseEvent) => {},
  keydown: (e: KeyboardEvent) => {},
} satisfies Record<string, (e: Event) => void>;

type HandlerKey = keyof typeof handlers; // "click" | "keydown", not string
```

**Use `: Config` when** you *want* the wider type — typically when the value will be reassigned, passed to a function expecting `Config`, or when the narrow type would cause problems:

```typescript
// You want Config, not a specific literal shape, because it will change
let activeConfig: Config = getDefaultConfig();
activeConfig = loadFromEnv(); // fine — it's typed as Config

// Function parameters: the annotation is on the parameter, not the call site
function startServer(config: Config) { ... }
```

**Combine them** when you want both validation and a named type:

```typescript
// satisfies validates the shape; "as Config" isn't needed — the type is already compatible
// Just use satisfies and let inference do the rest
const config = { port: 3000, host: "localhost", mode: "dev" } satisfies Config;

// Or if you genuinely need the wider type stored:
const config: Config = { port: 3000, host: "localhost", mode: "dev" } satisfies Config;
// This is redundant but not wrong — satisfies runs first, then the annotation widens
```

## Quick rule of thumb

> Use `satisfies` when you want the compiler to *check* the shape but *remember* the details. Use `: T` when you want the compiler to *forget* the details and treat the value as `T`.

In practice, `satisfies` is the better default for module-level constants and configuration objects. Reach for `: T` when you're working with mutable state or when the wider type is what you actually need.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A more thoroughly explains the widening behavior with `: T` annotation versus the literal-type-preserving behavior of `satisfies`, using clear discriminated union and tuple examples that directly illustrate why the distinction matters for downstream inference. It also covers the powerful `as const satisfies` pattern and provides a nuanced rule of thumb for when to use each. Answer B is correct but shallower, and its example with `Record<string, number>` actually doesn't demonstrate literal preservation well since Record values are typed as `number` anyway.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions widening from annotation | skill |
| uses satisfies keyword | tie |
| mentions preserving literal / narrow inferred type | skill |

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

<details><summary>haiku: baseline answer</summary>

# `const config: Config = {...}` vs `satisfies Config`

These look similar but have important differences in how TypeScript infers types:

## Type Annotation (`as Config`)

```typescript
const config: Config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
  retries: 3
};

// TypeScript infers: Config
config.apiUrl // string (from Config type)
```

**What happens:**
- TypeScript **widens** the type to `Config`
- Literal types are lost (`5000` becomes `number`)
- You get type safety but lose specificity

## `satisfies` Operator

```typescript
const config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
  retries: 3
} satisfies Config;

// TypeScript infers: { apiUrl: string; timeout: 5000; retries: 3 }
config.timeout // 5000 (literal type preserved!)
```

**What happens:**
- TypeScript **preserves** literal types
- Still validates against `Config`
- You get both type safety AND specificity

## Practical Example

```typescript
type Theme = {
  colors: Record<string, string>;
  spacing: Record<string, number>;
};

// ❌ Type annotation - loses literal types
const theme1: Theme = {
  colors: { primary: "#000", secondary: "#fff" },
  spacing: { small: 4, large: 16 }
};
theme1.spacing.small // number (not 4)

// ✅ satisfies - preserves literal types
const theme2 = {
  colors: { primary: "#000", secondary: "#fff" },
  spacing: { small: 4, large: 16 }
} satisfies Theme;
theme2.spacing.small // 4 (literal type!)
```

## When to Use `satisfies`

| Scenario | Use `satisfies` |
|----------|---|
| **Config objects** | ✅ Yes - preserve exact values |
| **Const assertions** | ✅ Yes - better than `as const` |
| **Route definitions** | ✅ Yes - keep literal path types |
| **API responses** | ❌ No - you want the general type |
| **Function parameters** | ❌ No - use type annotations |

## Real-World Example: Routes

```typescript
type Route = {
  path: string;
  name: string;
  component: React.ComponentType;
};

// ✅ Better - preserves literal path types
const routes = [
  { path: "/home", name: "Home", component: HomePage },
  { path: "/about", name: "About", component: AboutPage }
] satisfies Route[];

// Now you can use routes[0].path as "/home" (literal)
// instead of just string

// vs ❌ Type annotation loses specificity
const routes: Route[] = [...]; // path is just string
```

## Key Takeaway

Use `satisfies` when you want:
- ✅ Type validation (like type annotations)
- ✅ Literal type preservation (unlike type annotations)
- ✅ Better IDE autocomplete and inference

It's especially useful for **configuration objects, constants, and anything where the exact literal value matters**.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# `const config: Config = { ... }` vs `const config = { ... } satisfies Config`

The difference is **type inference width**. Both validate that the object matches `Config`, but they differ in what type the compiler infers for `config` afterward.

## The Core Difference

```typescript
type Config = {
  mode: "dev" | "prod";
  port: number;
};

// ❌ Annotation: widens to Config
const config1: Config = {
  mode: "dev",
  port: 3000,
};
// config1.mode is "dev" | "prod" (widened)

// ✅ satisfies: preserves the narrow inferred type
const config2 = {
  mode: "dev",
  port: 3000,
} satisfies Config;
// config2.mode is "dev" (narrow literal)
```

With `: Config`, the compiler validates the shape, then **widens** the inferred type to `Config`. With `satisfies Config`, the compiler validates the shape but **preserves the narrow inferred type** — `"dev"` stays `"dev"`, not `"dev" | "prod"`.

## Why This Matters

**Scenario 1: You need the narrow type downstream**

```typescript
const config = {
  mode: "dev",
  port: 3000,
} satisfies Config;

// ✅ Works: mode is "dev", so this is safe
if (config.mode === "dev") {
  console.log("Development mode");
}

// ✅ Works: TypeScript knows mode is exactly "dev"
type IsDev = typeof config.mode extends "dev" ? true : false; // true

// ❌ With `: Config`, this would be false (mode is "dev" | "prod")
```

**Scenario 2: Discriminated unions in config**

```typescript
type AppConfig =
  | { env: "dev"; debugPort: number }
  | { env: "prod"; logLevel: "error" | "warn" };

// ❌ With annotation, you lose the discriminant
const config1: AppConfig = {
  env: "dev",
  debugPort: 9229,
};
// config1.env is "dev" | "prod" — you can't narrow by it!

// ✅ With satisfies, the discriminant stays narrow
const config2 = {
  env: "dev",
  debugPort: 9229,
} satisfies AppConfig;
// config2.env is "dev" — you can narrow by it
```

**Scenario 3: Literal arrays and tuples**

```typescript
type Routes = readonly string[];

// ❌ Annotation: widens to string[]
const routes1: Routes = ["home", "about", "contact"];
// routes1[0] is string

// ✅ satisfies: preserves literal tuple
const routes2 = ["home", "about", "contact"] satisfies Routes;
// routes2[0] is "home" | "about" | "contact"
// routes2.length is 3 (not number)
```

## When to Use Each

| Use case | Use | Why |
|---|---|---|
| You need the narrow inferred type downstream | `satisfies T` | Validates shape; preserves literal types for further narrowing |
| You want to widen to the declared type | `: T` | Explicit intent; useful when you want to forget the literal values |
| Discriminated union config / state | `satisfies T` | Discriminant stays narrow; narrowing by tag works |
| Literal arrays / tuples you'll index into | `satisfies T` | Preserves tuple length and element literals |
| Simple data object with no downstream narrowing | Either (stylistic) | Both work; `satisfies` is slightly more modern |
| Function parameter or exported value | `: T` | Explicit contract; callers see the declared type, not the inferred one |
| Const assertion (`as const`) + validation | `satisfies T` | Combine: `{ ... } as const satisfies Config` locks literals *and* validates |

## Combining `as const` and `satisfies`

The most powerful pattern: lock literals with `as const`, then validate the shape:

```typescript
const config = {
  mode: "dev",
  port: 3000,
  features: ["auth", "api"],
} as const satisfies Config;

// ✓ mode is "dev" (not "dev" | "prod")
// ✓ port is 3000 (not number)
// ✓ features is readonly ["auth", "api"] (not string[])
// ✓ Validates against Config shape
```

This is the idiom for **immutable, validated, literal-preserving** config.

## Rule of Thumb

- **Default to `satisfies`** when defining a const object — it validates without throwing away type information.
- **Use `: T`** when you explicitly want to widen (e.g., a function parameter that accepts `Config` and you don't care about the literal values), or when declaring a public API (exported values should have an explicit declared type, not an inferred one).

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core distinction well, but Answer B is more thorough and precise. It explicitly explains that `: T` widens the variable's type to T while `satisfies T` preserves the narrow inferred type, includes the valuable `as const satisfies` combination, and provides a cleaner table for when to use each. Answer A is solid but slightly less precise on the widening explanation and misses the `as const` combination.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions widening from annotation | skill |
| uses satisfies keyword | tie |
| mentions preserving literal / narrow inferred type | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions widening from annotation | ✓ | `wider` |
| uses satisfies keyword | ✓ | `satisfies` |
| mentions preserving literal / narrow inferred type | ✓ | `preserv` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions widening from annotation | ✓ | `widen` |
| uses satisfies keyword | ✓ | `satisfies` |
| mentions preserving literal / narrow inferred type | ✓ | `preserv` |

<details><summary>opus: baseline answer</summary>

# Type Annotation vs `satisfies`

The key difference is **what type TypeScript infers for the variable**.

## Type Annotation: `const config: Config = { ... }`

The variable's type becomes `Config`. You lose any information about the *specific* values you wrote.

```ts
type Config = { env: string; port: number };

const config: Config = { env: "prod", port: 3000 };
// config.env is `string`, not `"prod"`
```

## `satisfies`: `const config = { ... } satisfies Config`

TypeScript **checks** that the value matches `Config`, but the variable keeps its narrow, inferred type.

```ts
const config = { env: "prod", port: 3000 } satisfies Config;
// config.env is `"prod"` (literal type preserved)
```

## A Concrete Example Where It Matters

```ts
type Routes = Record<string, { method: "GET" | "POST"; path: string }>;

// With annotation — you lose the specific keys
const routes1: Routes = {
  home: { method: "GET", path: "/" },
  login: { method: "POST", path: "/login" },
};
routes1.home;     // OK
routes1.typoo;    // Also OK ❌ (any string key is allowed)

// With satisfies — you keep the specific keys
const routes2 = {
  home: { method: "GET", path: "/" },
  login: { method: "POST", path: "/login" },
} satisfies Routes;
routes2.home;     // OK
routes2.typoo;    // ❌ Error: property doesn't exist
```

## Catching Invalid Values

Both will catch type errors:

```ts
const bad = { env: "prod", port: "3000" } satisfies Config;
// ❌ Error: string is not assignable to number
```

## When to Use `satisfies`

Use `satisfies` when you want to:

1. **Validate** a value against a type, but
2. **Preserve** the specific inferred type for downstream use.

Common cases:
- Config objects, route tables, lookup maps where you want autocomplete on specific keys
- Preserving literal types (`"GET"` instead of `string`)
- Discriminated unions where you need the narrow variant later

## When to Use `: Type`

- When you genuinely want the variable to be the wider type (e.g., function parameters, public API surface)
- When you want to rely on contextual typing inside the object literal (e.g., parameter types of inline callbacks get inferred from `Config`)

## Rule of thumb

> Use `satisfies` for **values you'll use locally and want precise types for**. Use `: Type` for **values that should behave as the abstract type**.

</details>

<details><summary>opus: skill-loaded answer</summary>

# `: T` vs `satisfies T`

Both validate that the object conforms to `Config`, but they differ in **what type the variable ends up with**.

## The key difference

```ts
type Config = {
  port: number;
  mode: "dev" | "prod";
  features: string[];
};

// Annotation: variable's type IS Config (widened)
const a: Config = {
  port: 3000,
  mode: "dev",
  features: ["auth", "logging"],
};
// a.mode is "dev" | "prod"
// a.features is string[]

// satisfies: variable keeps its narrow inferred type
const b = {
  port: 3000,
  mode: "dev",
  features: ["auth", "logging"],
} satisfies Config;
// b.mode is "dev"  ← preserved literal!
// b.features is string[]
```

With `: Config`, the variable's type *becomes* `Config`. With `satisfies Config`, the compiler **checks** the literal against `Config` but the variable keeps the narrow type it inferred from the literal.

## Why this matters

### 1. Preserves literal types

```ts
const routes = {
  home: "/",
  about: "/about",
  contact: "/contact",
} satisfies Record<string, string>;

routes.home;  // type is "/", not string
// You can use it in places that need the exact literal:
type HomeRoute = typeof routes.home;  // "/"
```

With `: Record<string, string>`, every value would just be `string`.

### 2. Preserves known keys

```ts
const handlers = {
  click: () => {},
  hover: () => {},
} satisfies Record<string, () => void>;

handlers.click;   // ✅ known to exist
handlers.scroll;  // ❌ Property 'scroll' does not exist
```

With `: Record<string, () => void>`, `handlers.scroll` would be `() => void` (since any string key is allowed), and you'd lose the closed set of known keys.

### 3. Catches excess properties and shape errors — same as `:`

```ts
const c = {
  port: 3000,
  mode: "dev",
  features: [],
  extra: true,  // ❌ caught by satisfies, just like :
} satisfies Config;
```

## When to use which

| Use | When |
|---|---|
| `satisfies T` | Object/array literals where you want both validation **and** narrow inferred types — config objects, route maps, lookup tables, enum-like records |
| `: T` on a variable | Rare. Mainly when you genuinely want to widen (e.g., declare an empty array as `string[]` rather than `never[]`) |
| `: T` on parameters / return types | Always — these are contracts, not inference sites |

## Rule of thumb

For a `const` initialized with a literal: **prefer `satisfies T`**. You get the type check without throwing away the precise type the compiler just inferred.

Often combined with `as const` for maximum narrowness:

```ts
const config = {
  port: 3000,
  mode: "dev",
  features: ["auth"],
} as const satisfies Config;
// config.features is now readonly ["auth"]
```

</details>

---

### `unknown-vs-any`

**Prompt**

```
I'm parsing JSON from an HTTP response in TypeScript. What type
should the parsed value have, and why?
```

**Judge focus:** The better answer recommends `unknown` (forces narrowing) over `any`
(silently disables typechecking), and shows a narrowing or validation
step.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend `unknown` and explain why `any` is problematic, but Answer B is more thorough and practical. It adds an assertion function pattern, explicitly warns against the `as User` type assertion anti-pattern (a common mistake), and provides a more rigorous type predicate that checks property types rather than just presence. The summary table in B is also more informative, covering more approaches with clearer tradeoffs.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends unknown | tie |
| explains why not any | tie |
| shows narrowing or validation step | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✓ | `any` silent` |
| shows narrowing or validation step | ✓ | `typeof` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✓ | `any — type checking is disable` |
| shows narrowing or validation step | ✓ | `typeof` |

<details><summary>sonnet: baseline answer</summary>

## Parsing JSON in TypeScript

The parsed value should be typed as **`unknown`**.

```typescript
const response = await fetch('https://api.example.com/data');
const parsed: unknown = await response.json();
```

---

### Why `unknown` and Not `any`?

`response.json()` returns `Promise<any>` by default, but you should **explicitly annotate or cast to `unknown`** instead.

| Type | Type-safe? | Requires validation? | Autocomplete? |
|------|-----------|----------------------|---------------|
| `any` | ❌ No | ❌ No | ❌ Unsound |
| `unknown` | ✅ Yes | ✅ Yes | ✅ After narrowing |

#### The problem with `any`
```typescript
const parsed: any = await response.json();

// TypeScript allows this — no error, but crashes at runtime
// if the shape is wrong
console.log(parsed.user.address.street.toUpperCase());
```

#### The benefit of `unknown`
```typescript
const parsed: unknown = await response.json();

// TypeScript FORCES you to narrow the type before using it
console.log(parsed.user); // ❌ Error: Object is of type 'unknown'
```

---

### Validating After Parsing

You must **narrow** the type before use. Common approaches:

#### 1. Type Guard (manual)
```typescript
interface User {
  id: number;
  name: string;
}

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value
  );
}

const parsed: unknown = await response.json();

if (isUser(parsed)) {
  console.log(parsed.name); // ✅ Safe
}
```

#### 2. Runtime Validation Library (recommended for complex schemas)
```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
});

const parsed: unknown = await response.json();
const user = UserSchema.parse(parsed); // throws if invalid
console.log(user.name); // ✅ Fully typed and validated
```

---

### Key Takeaway

> Use **`unknown`** because JSON can be *anything* at runtime — a string, number, array, object, or `null`. Using `unknown` forces you to **prove the shape** before accessing it, preventing entire classes of runtime errors that `any` silently allows.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Use `unknown`, not `any`

```typescript
const response = await fetch(url);
const data: unknown = await response.json();
```

### Why not `any`?

`response.json()` returns `Promise<any>` in the standard lib. If you accept that `any` and pass it around, TypeScript stops checking every downstream use — silently. One typo in a property name, one wrong assumption about shape, and you get a runtime crash with no compile-time warning.

```typescript
// ❌ any — type checking is disabled from here on
const data: any = await response.json();
console.log(data.user.nmae); // typo — compiles fine, crashes at runtime
```

`unknown` forces you to prove the shape before using it.

```typescript
// ✅ unknown — compiler won't let you touch it without narrowing first
const data: unknown = await response.json();
console.log(data.user.name); // Error: 'data' is of type 'unknown'
```

---

## Narrowing the value

You have three good options depending on how much rigor you need.

### 1. Type predicate (lightweight, no dependencies)

Write a guard function that checks the shape at runtime and tells the compiler what you've verified:

```typescript
type User = { id: number; name: string };

function isUser(value: unknown): value is User {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof (value as Record<string, unknown>).id === "number" &&
    "name" in value &&
    typeof (value as Record<string, unknown>).name === "string"
  );
}

const data: unknown = await response.json();

if (!isUser(data)) {
  throw new Error("Unexpected response shape");
}

// data is User from here on
console.log(data.name);
```

### 2. Assertion function (throws instead of returning false)

Useful when an unexpected shape is always a hard error:

```typescript
function assertIsUser(value: unknown): asserts value is User {
  if (!isUser(value)) {
    throw new Error(`Expected User, got: ${JSON.stringify(value)}`);
  }
}

const data: unknown = await response.json();
assertIsUser(data);
// data is User — no if-branch needed
console.log(data.name);
```

### 3. Validation library (recommended for production)

For complex or evolving schemas, hand-written guards become fragile. Libraries like [Zod](https://zod.dev), [Valibot](https://valibot.dev), or [ArkType](https://arktype.io) generate both the runtime check and the TypeScript type from a single schema definition:

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
});

type User = z.infer<typeof UserSchema>; // { id: number; name: string }

const data: unknown = await response.json();
const user = UserSchema.parse(data); // throws ZodError with field-level detail if invalid
console.log(user.name);
```

---

## The one thing to avoid

```typescript
// ❌ type assertion — skips all runtime checking
const data = await response.json() as User;
```

`as User` is a compile-time lie. It tells the compiler "trust me, this is a `User`" without verifying anything at runtime. If the server returns a different shape, you get silent corruption or a crash, not a useful error.

---

## Summary

| Approach | Type safety | Runtime check | Effort |
|---|---|---|---|
| Accept `any` | ❌ None | ❌ None | None |
| `as User` assertion | ✅ Compile-time only | ❌ None | Minimal |
| `unknown` + type predicate | ✅ Both | ✅ Yes | Low |
| `unknown` + assertion function | ✅ Both | ✅ Yes | Low |
| `unknown` + validation library | ✅ Both + error detail | ✅ Yes | Schema definition |

Start with `unknown`. Narrow it with a type predicate for simple shapes, or a validation library for anything you'd put in production.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend `unknown` over `any` and show narrowing/validation steps, but Answer B is more thorough and practical. It introduces assertion functions as an additional pattern, includes a comparison table that clearly illustrates the tradeoffs, and uses `Record<string, unknown>` casts in the type guard which is more idiomatic than using `in` operator alone for property access. Answer B also more explicitly frames JSON as 'untrusted input' and explains where failures should occur ('at the boundary, not deep in your business logic').

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends unknown | tie |
| explains why not any | skill |
| shows narrowing or validation step | skill |

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
| shows narrowing or validation step | ✓ | `typeof` |

<details><summary>haiku: baseline answer</summary>

# Typing Parsed JSON in TypeScript

The parsed value should have type **`unknown`**, and here's why:

## The Problem with `any`

```typescript
// ❌ Avoid this
const data: any = JSON.parse(response);
data.user.name.toUpperCase(); // No type checking!
```

`any` disables all type checking, defeating TypeScript's purpose.

## The Correct Approach

```typescript
// ✅ Use unknown
const data: unknown = JSON.parse(response);

// TypeScript forces you to narrow the type before using it
if (typeof data === 'object' && data !== null && 'user' in data) {
  console.log(data.user); // Still unknown here
}
```

## Why `unknown`?

1. **Type Safety**: You must validate/narrow the type before using it
2. **Honest**: JSON.parse returns unpredictable data from external sources
3. **Forces Validation**: Prevents runtime errors from unexpected structures

## Practical Pattern: Type Guards

```typescript
interface User {
  name: string;
  age: number;
}

function isUser(obj: unknown): obj is User {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'name' in obj &&
    typeof obj.name === 'string' &&
    'age' in obj &&
    typeof obj.age === 'number'
  );
}

const data: unknown = JSON.parse(response);
if (isUser(data)) {
  console.log(data.name.toUpperCase()); // ✅ Safe!
}
```

## With Libraries

For complex schemas, use validation libraries:

```typescript
import { z } from 'zod';

const userSchema = z.object({
  name: z.string(),
  age: z.number(),
});

const data = userSchema.parse(JSON.parse(response));
// data is now properly typed as { name: string; age: number }
```

**Bottom line**: Start with `unknown`, then validate to your actual type.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Parsing JSON: Use `unknown`

The parsed value should have type **`unknown`**, not `any`. Here's why and how:

## The Problem with `any`

```typescript
// ❌ Don't do this
const data: any = JSON.parse(response);
data.user.name.toUpperCase(); // No error, but crashes at runtime if shape is wrong
```

`any` disables *all* type checking downstream. If the JSON is malformed or the server changed its schema, you won't know until runtime.

## The Right Approach: `unknown`

```typescript
// ✅ Do this
const data: unknown = JSON.parse(response);

// Now you must narrow before use
if (typeof data === "object" && data !== null && "user" in data) {
  const user = data.user;
  // Still unknown here; narrow further
}
```

`unknown` forces you to validate the shape *before* using it. This is the whole point: **JSON from the network is untrusted input**.

## Practical Pattern: Type Predicate + Assertion Function

For real code, combine a **type predicate** with a **type guard**:

```typescript
// Define the expected shape
type User = {
  readonly id: number;
  readonly name: string;
  readonly email: string;
};

// Type predicate: narrows `unknown` to `User`
function isUser(x: unknown): x is User {
  return (
    typeof x === "object" &&
    x !== null &&
    typeof (x as Record<string, unknown>).id === "number" &&
    typeof (x as Record<string, unknown>).name === "string" &&
    typeof (x as Record<string, unknown>).email === "string"
  );
}

// Parse and validate in one step
const data: unknown = JSON.parse(response);
if (!isUser(data)) {
  throw new Error("Invalid user shape from server");
}

// Now `data` is narrowed to `User`
console.log(data.name.toUpperCase()); // ✅ Safe
```

Or use an **assertion function** if you want to throw on failure:

```typescript
function assertIsUser(x: unknown): asserts x is User {
  if (
    typeof x !== "object" ||
    x === null ||
    typeof (x as Record<string, unknown>).id !== "number" ||
    typeof (x as Record<string, unknown>).name !== "string" ||
    typeof (x as Record<string, unknown>).email !== "string"
  ) {
    throw new Error("Invalid user shape from server");
  }
}

const data: unknown = JSON.parse(response);
assertIsUser(data); // Throws if invalid
// Now `data` is narrowed to `User`
```

## Why This Matters

| Approach | Catches Schema Changes? | Catches Typos? | Crashes at Runtime? |
|---|---|---|---|
| `any` | ❌ No | ❌ No | ✅ Yes |
| `unknown` + predicate | ✅ Yes | ✅ Yes | ❌ No |

The predicate/assertion function is your **runtime contract** with the server. When the API changes, your code fails *at the boundary*, not deep in your business logic.

## For Larger Schemas: Use a Validation Library

If your JSON is complex, hand-rolled predicates get tedious. Consider a lightweight validator:

```typescript
import { z } from "zod"; // or io-ts, valibot, etc.

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
});

type User = z.infer<typeof UserSchema>;

const data = UserSchema.parse(JSON.parse(response));
// `data` is now `User`, validated at runtime
```

But the principle is the same: **`unknown` at the boundary, narrowed via validation before use**.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers are excellent and cover all three rubric criteria well. Answer A edges out Answer B by providing more depth: it explicitly shows the compiler error from using `any`, covers assertion functions as a third narrowing option, and includes a dedicated 'What to avoid' section warning against `as`-casting. Answer B is also strong and includes a useful summary table, but Answer A's coverage is slightly more comprehensive and pedagogically thorough.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends unknown | tie |
| explains why not any | skill |
| shows narrowing or validation step | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✓ | `any` — silent` |
| shows narrowing or validation step | ✓ | `typeof` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✗ | |
| shows narrowing or validation step | ✓ | `typeof` |

<details><summary>opus: baseline answer</summary>

# The Correct Type: `unknown`

When you parse JSON from an HTTP response, the result should be typed as **`unknown`**, not `any`.

```ts
const response = await fetch('/api/data');
const data: unknown = await response.json();
```

## Why `unknown`?

### 1. JSON could be literally anything
A JSON response could be an object, array, string, number, boolean, or `null`. The TypeScript compiler has no way to know what shape the server actually returned.

### 2. The server is outside your type system
Your TypeScript types describe what you *expect*. They can't enforce what an external server *actually sends*. The network is an untrusted boundary.

### 3. `unknown` forces validation; `any` doesn't
This is the key difference:

```ts
// With `any` — silently broken at runtime
const data: any = await response.json();
data.user.name.toUpperCase(); // compiles fine, may crash

// With `unknown` — compiler forces you to check
const data: unknown = await response.json();
data.user.name.toUpperCase(); // ❌ Error: 'data' is of type 'unknown'
```

`unknown` is the type-safe counterpart of `any`: you can assign anything *to* it, but you can't do anything *with* it until you've narrowed it.

## What `fetch` actually gives you

Note that `Response.json()` in the DOM lib is typed as `Promise<any>` for historical/ergonomic reasons. You should explicitly annotate to `unknown` to opt into safety:

```ts
const data: unknown = await response.json();
```

## How to use the value

You then need to validate the shape before using it. Options:

**1. Manual type guards:**
```ts
function isUser(x: unknown): x is { name: string } {
  return typeof x === 'object' && x !== null
    && 'name' in x && typeof (x as any).name === 'string';
}

if (isUser(data)) {
  console.log(data.name.toUpperCase()); // ✅ safe
}
```

**2. A schema validation library** (recommended for non-trivial shapes) like **Zod**, **Valibot**, **ArkType**, or **io-ts**:

```ts
import { z } from 'zod';

const User = z.object({ name: z.string() });
const data = User.parse(await response.json()); // throws if invalid
data.name.toUpperCase(); // ✅ typed and validated
```

## Summary

| Type | Safe? | Why |
|------|-------|-----|
| `any` | ❌ | Disables type checking entirely |
| `SomeInterface` | ❌ | A lie — TS trusts you, but the server might not comply |
| `unknown` | ✅ | Honest about uncertainty; forces runtime validation |

Use `unknown` and validate at the boundary. Once validated, you have a properly typed value you can trust everywhere downstream.

</details>

<details><summary>opus: skill-loaded answer</summary>

# `unknown`, not `any`

`JSON.parse` is typed to return `any` in the standard lib, but you should immediately narrow it to `unknown`:

```ts
const data: unknown = JSON.parse(responseText);
```

## Why `unknown` and not `any`

`any` opts out of type checking entirely. This compiles with no error:

```ts
const data = JSON.parse(responseText);  // any
const name: string = data.user.profile.name;  // no check, no error
data.foo.bar.baz();                            // no check, no error
```

If the response shape is wrong, you get a runtime `TypeError` (or worse, a silent bug downstream when `name` is actually `undefined`). The compiler had no chance to help.

`unknown` flips this. The value is "some value, shape not yet proven," and the compiler refuses every operation until you prove the shape:

```ts
const data: unknown = JSON.parse(responseText);
const name: string = data.user.profile.name;
//                   ~~~~ Object is of type 'unknown'.
```

## Narrowing the `unknown`

You have a few options depending on how much you trust the source:

**1. A user-defined type predicate** — cheap, no dependency, good for small shapes:

```ts
type User = { id: string; name: string };

function isUser(x: unknown): x is User {
  return (
    typeof x === "object" && x !== null &&
    "id" in x && typeof x.id === "string" &&
    "name" in x && typeof x.name === "string"
  );
}

const data: unknown = JSON.parse(responseText);
if (!isUser(data)) throw new Error("invalid user response");
// data is User from here on
```

**2. An assertion function** — same idea, but throws instead of returning a boolean, so the narrowing flows through the rest of the function:

```ts
function assertUser(x: unknown): asserts x is User {
  if (!isUser(x)) throw new Error("invalid user response");
}

const data: unknown = JSON.parse(responseText);
assertUser(data);
// data is User from here on, no if-block needed
```

**3. A schema validator** (Zod, Valibot, ArkType, etc.) — for non-trivial shapes, where hand-written predicates become tedious and error-prone:

```ts
const User = z.object({ id: z.string(), name: z.string() });
const data = User.parse(JSON.parse(responseText));  // typed as User, throws on mismatch
```

## What to avoid

```ts
const data = JSON.parse(responseText) as User;  // ❌
```

`as` is a type assertion: you're telling the compiler "trust me, this is a `User`" with no runtime check. If the server returns `{ "id": 42 }` (number, not string), the compiler stays silent and you get a runtime error somewhere far away from the parse site. Assertions delete the very check the compiler was about to give you. The cost of a one-line type predicate or schema is almost always worth paying at an I/O boundary.

## Summary

- Type the result of `JSON.parse` as `unknown`.
- Narrow it with a type predicate, assertion function, or schema validator before using it.
- Never `as`-cast parsed JSON to your domain type — that's the trap `unknown` exists to prevent.

</details>

---

### `branded-types`

**Prompt**

```
In my TypeScript codebase I have UserId and OrderId, both currently
just `string`. We have a bug where someone passed an OrderId to a
function expecting a UserId and TypeScript didn't catch it. How do
I prevent this kind of mistake?
```

**Judge focus:** The better answer reaches for branded (nominal) types using a
phantom `__brand` property to make the types structurally distinct.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A uses a string-literal tag approach with `__brand` which is slightly more readable, while Answer B uses `unique symbol` which is technically more robust against accidental brand collisions. Both explain structural typing as the root cause, show phantom `__brand` properties, and recommend branded types with constructor functions. The differences are stylistic rather than substantive.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends branded types | tie |
| shows __brand or similar phantom property | tie |
| explains structural typing as the cause | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `Brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✓ | `structural` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✓ | `structural` |

<details><summary>sonnet: baseline answer</summary>

## Branded Types

This is a classic problem solved with **branded (nominal) types** — making structurally identical types distinct to TypeScript.

### The Pattern

```typescript
// brands.ts
declare const __brand: unique symbol;

type Brand<T, B> = T & { readonly [__brand]: B };

export type UserId  = Brand<string, 'UserId'>;
export type OrderId = Brand<string, 'OrderId'>;
```

`unique symbol` is the key — each declaration is a type-level singleton, so no two brands can accidentally match.

---

### Constructor Functions (The Safe Entry Point)

Never cast directly at call sites. Centralise the cast in one place:

```typescript
// Unsafe — avoid spreading this pattern everywhere
const id = "abc" as UserId;

// Safe — cast once, in a controlled location
export const UserId  = (id: string): UserId  => id as UserId;
export const OrderId = (id: string): OrderId => id as OrderId;
```

---

### Usage

```typescript
function getUserById(id: UserId): User { ... }
function getOrderById(id: OrderId): Order { ... }

const userId  = UserId("user-123");
const orderId = OrderId("order-456");

getUserById(userId);   // ✅
getUserById(orderId);  // ❌ Argument of type 'OrderId' is not assignable
                       //    to parameter of type 'UserId'
getUserById("raw");    // ❌ string is not assignable to UserId
```

---

### Validation at System Boundaries

Combine with runtime validation (e.g. from an API or database):

```typescript
export function parseUserId(raw: string): UserId {
  if (!raw.startsWith("user-")) {
    throw new Error(`Invalid UserId: ${raw}`);
  }
  return raw as UserId;
}

export function parseOrderId(raw: string): OrderId {
  if (!raw.startsWith("order-")) {
    throw new Error(`Invalid OrderId: ${raw}`);
  }
  return raw as OrderId;
}
```

Parse at the boundary (HTTP handler, DB read), then the rest of your codebase is type-safe without any casts.

---

### Reusable Helper

```typescript
// Generic factory — avoids repeating the cast pattern
function makeBrandedConstructor<T extends Brand<string, any>>() {
  return (value: string): T => value as T;
}

export const UserId  = makeBrandedConstructor<UserId>();
export const OrderId = makeBrandedConstructor<OrderId>();
```

---

### Key Points

| Concern | Answer |
|---|---|
| Runtime cost | Zero — brands are erased at compile time |
| Where to cast | Only inside constructor/parser functions |
| Serialisation | Works fine — it's still a `string` at runtime |
| Libraries (zod, etc.) | `.transform(s => s as UserId)` or use `z.string().brand<'UserId'>()` |

The single rule: **raw strings enter through constructors/parsers, branded types flow everywhere else.**

</details>

<details><summary>sonnet: skill-loaded answer</summary>

This is the classic "stringly-typed" problem. The fix is **branded types** — you keep the runtime representation as `string` but attach a phantom type tag that makes `UserId` and `OrderId` structurally incompatible.

## The Pattern

```typescript
// brands.ts
type Brand<Base, Tag extends string> = Base & { readonly __brand: Tag };

export type UserId  = Brand<string, "UserId">;
export type OrderId = Brand<string, "OrderId">;
```

The `__brand` field never exists at runtime — it's purely a compile-time marker. Because the tags differ, TypeScript treats the two types as incompatible even though both are `string` underneath.

## Constructor Functions (the Only Place You Cast)

```typescript
// Centralise the unsafe cast here so nowhere else needs `as`.
export function toUserId(id: string): UserId {
  // Add validation if you have invariants (non-empty, UUID format, etc.)
  if (!id) throw new Error("UserId cannot be empty");
  return id as UserId;
}

export function toOrderId(id: string): OrderId {
  if (!id) throw new Error("OrderId cannot be empty");
  return id as OrderId;
}
```

Every other file uses these constructors. The `as` cast is quarantined to one place per brand.

## What You Get

```typescript
function getUser(id: UserId): User { /* ... */ }

const userId  = toUserId("usr_123");
const orderId = toOrderId("ord_456");

getUser(userId);   // ✅
getUser(orderId);  // ✅ Compile error: Argument of type 'OrderId' is not
                   //    assignable to parameter of type 'UserId'.
getUser("usr_123"); // ✅ Compile error: plain string not accepted either
```

The bug you described is now a compile error.

## Practical Tips

**Brands are still strings at runtime.** You can pass them anywhere a `string` is expected (e.g. `console.log`, template literals, JSON serialisation) without any conversion. The brand only blocks the *wrong* branded type.

**Parse at the boundary, use freely inside.** Validate and brand at I/O edges (HTTP handlers, DB queries, form inputs), then pass branded values through your domain code without re-checking.

```typescript
// In your HTTP handler — one cast, at the edge
const userId = toUserId(req.params.userId);

// Everything downstream is type-safe with no further ceremony
const user = await getUser(userId);
await createOrder(userId, ...);  // createOrder(id: UserId, ...) — safe
```

**Use `satisfies` to validate config objects that contain branded IDs** without losing the narrow type:

```typescript
const TEST_IDS = {
  user:  toUserId("usr_test"),
  order: toOrderId("ord_test"),
} satisfies { user: UserId; order: OrderId };
```

**Extend the `Brand` helper for non-string primitives** — the same pattern works for `number`, `bigint`, etc.:

```typescript
type Milliseconds = Brand<number, "Milliseconds">;
type Pixels       = Brand<number, "Pixels">;
```

## Migrating an Existing Codebase

1. Define the brands and constructors.
2. Add the branded types to function signatures one module at a time.
3. Let the compiler guide you to every call site that needs a constructor call.
4. The migration is mechanical and safe — no runtime behaviour changes.

The key insight: **one `as` cast in the constructor, zero `as` casts everywhere else.** The compiler does the rest.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend branded types with a `__brand` phantom property and explain structural typing as the root cause. However, Answer B is significantly more comprehensive and practical: it explains *why* the pattern works (structural distinctness, phantom types, zero runtime cost), provides a reusable generic `Brand<T, B>` helper for scaling, covers common pitfalls, and shows how to combine brands with validation. Answer A is correct but shallower, and its 'class-based' alternative actually uses structural typing which can still be fooled by duck typing.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends branded types | tie |
| shows __brand or similar phantom property | tie |
| explains structural typing as the cause | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✗ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `Brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✓ | `structural` |

<details><summary>haiku: baseline answer</summary>

# Nominal Types in TypeScript

You need **nominal typing** (also called "branded types"). Here are the best approaches:

## 1. **Branded Types (Recommended)**

Create distinct types that TypeScript treats as different, even though they're both strings:

```typescript
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

// Helper functions to create branded types safely
const userId = (id: string): UserId => id as UserId;
const orderId = (id: string): OrderId => id as OrderId;

// Now TypeScript catches the error
function processUser(id: UserId) {
  console.log(id);
}

const myOrderId = orderId("order-123");
processUser(myOrderId); // ❌ Type error!
processUser(userId("user-456")); // ✅ OK
```

## 2. **Opaque Types (More Robust)**

Use a class-based approach for stronger guarantees:

```typescript
class UserId {
  constructor(readonly value: string) {}
}

class OrderId {
  constructor(readonly value: string) {}
}

function processUser(id: UserId) {
  console.log(id.value);
}

const myOrderId = new OrderId("order-123");
processUser(myOrderId); // ❌ Type error!
processUser(new UserId("user-456")); // ✅ OK
```

## 3. **Enum-based (Lightweight)**

```typescript
enum UserIdBrand {}
enum OrderIdBrand {}

type UserId = string & { readonly __brand: UserIdBrand };
type OrderId = string & { readonly __brand: OrderIdBrand };

const userId = (id: string): UserId => id as UserId;
const orderId = (id: string): OrderId => id as OrderId;
```

## Comparison

| Approach | Runtime Cost | Type Safety | Ergonomics |
|----------|-------------|-------------|-----------|
| Branded types | None | Good | Good |
| Classes | Small | Excellent | Requires `new` |
| Enums | None | Good | Good |

**I'd recommend branded types** for most cases—they're zero-cost abstractions with excellent type safety.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Branded Types for Distinct Primitives

You need **branded types** (also called "opaque types" or "nominal types"). They let you create distinct types from the same primitive without runtime overhead.

## The Pattern

```typescript
// Define each brand as a unique type
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

// Helper to create branded values safely
const userId = (id: string): UserId => id as UserId;
const orderId = (id: string): OrderId => id as OrderId;

// Now the function signature is type-safe
function getUser(id: UserId): User {
  // ...
}

function getOrder(id: OrderId): Order {
  // ...
}

// ✅ Type-safe
const user = getUser(userId("user-123"));
const order = getOrder(orderId("order-456"));

// ❌ Compile error: Argument of type 'OrderId' is not assignable to parameter of type 'UserId'
getUser(orderId("order-456"));

// ❌ Compile error: Argument of type 'string' is not assignable to parameter of type 'UserId'
getUser("user-123");
```

## Why This Works

- **Intersection with a unique object type** — `string & { readonly __brand: "UserId" }` is structurally distinct from `string & { readonly __brand: "OrderId" }`, even though both are strings at runtime.
- **`as` only at the boundary** — the helper functions (`userId`, `orderId`) are the *only* place you cast. Everywhere else, the type system enforces the distinction.
- **Zero runtime cost** — the `__brand` property is never actually created. It's a compile-time-only phantom type.

## Scaling to Many IDs

If you have many branded types, create a reusable helper:

```typescript
// Generic brand helper
type Brand<T, B extends string> = T & { readonly __brand: B };

type UserId = Brand<string, "UserId">;
type OrderId = Brand<string, "OrderId">;
type ProductId = Brand<string, "ProductId">;

// Generic constructor
const createBrand = <T, B extends string>(value: T): Brand<T, B> => value as Brand<T, B>;

const userId = (id: string) => createBrand<string, "UserId">(id);
const orderId = (id: string) => createBrand<string, "OrderId">(id);
const productId = (id: string) => createBrand<string, "ProductId">(id);
```

## Extracting the Raw Value

When you need the underlying string (e.g., to serialize or log):

```typescript
function logUser(id: UserId) {
  // Cast back to string when you need the raw value
  console.log("User ID:", id as string);
}

// Or use a helper
const unwrap = <T, B extends string>(branded: Brand<T, B>): T => branded as T;
```

## Common Pitfalls

**Don't skip the helper:**
```typescript
// ❌ Bad: anyone can cast
getUser("user-123" as UserId);

// ✅ Good: only the helper can create a UserId
getUser(userId("user-123"));
```

**Don't use `__brand` at runtime:**
```typescript
// ❌ This will fail at runtime
if (id.__brand === "UserId") { ... }

// ✅ Use a type predicate instead
const isUserId = (id: unknown): id is UserId => typeof id === "string";
```

**Brands don't prevent accidental mixing in plain objects:**
```typescript
type User = { id: UserId; name: string };

// ❌ Still compiles (structural typing)
const user: User = { id: "raw-string" as UserId, name: "Alice" };

// ✅ Use a constructor or factory to enforce
const createUser = (id: UserId, name: string): User => ({ id, name });
```

## When to Use Branded Types

| Scenario | Use Branded | Why |
|---|---|---|
| Distinct IDs (UserId, OrderId, ProductId) | ✅ Yes | Prevents accidental swaps; common source of bugs |
| Validated strings (Email, URL, Slug) | ✅ Yes | Signals that the string has been validated |
| Numeric units (Milliseconds, Pixels, Kilobytes) | ✅ Yes | Prevents mixing `1000` (ms) with `1000` (px) |
| Generic "string" or "number" | ❌ No | Overhead without benefit |
| Internal-only types | ❌ Maybe | If the type never crosses a module boundary, a plain `type` alias is simpler |

## Combining with Validation

For validated strings, pair the brand with a validation function:

```typescript
type Email = Brand<string, "Email">;

const createEmail = (input: string): Email | null => {
  // Simple regex; use a real email validator in production
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input)) {
    return null;
  }
  return input as Email;
};

function sendEmail(to: Email, subject: string) {
  // Guaranteed to be a valid email
}

const email = createEmail("user@example.com");
if (email) {
  sendEmail(email, "Hello");
}
```

This catches the bug at the source: you can't create an invalid `Email` in the first place.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend branded types and explain structural typing as the root cause. Answer A uses the `__brand` property pattern explicitly (matching the rubric's focus), provides a reusable `Brand<T, B>` helper, covers constructors, parse boundaries, caveats, and file organization in greater depth. Answer B uses `unique symbol` which is a valid alternative but diverges from the `__brand` phantom property the rubric specifically calls for, and is less comprehensive overall.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends branded types | tie |
| shows __brand or similar phantom property | skill |
| explains structural typing as the cause | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `Brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✓ | `structural` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends branded types | ✓ | `Brand` |
| shows __brand or similar phantom property | ✓ | `__brand` |
| explains structural typing as the cause | ✓ | `structural` |

<details><summary>opus: baseline answer</summary>

# Branded Types: The Fix You Want

This is a classic case for **branded (or "nominal") types**. TypeScript uses structural typing by default, so `type UserId = string` and `type OrderId = string` are completely interchangeable. You need to add a "brand" that exists only at the type level.

## The Pattern

```typescript
declare const brand: unique symbol;

type Brand<T, TBrand> = T & { [brand]: TBrand };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
```

Now `UserId` and `OrderId` are distinct types, even though both are still just strings at runtime.

## Constructing Branded Values

You need explicit constructors since you can't just assign a `string` to a `UserId`:

```typescript
function UserId(id: string): UserId {
  // optionally validate here
  return id as UserId;
}

function OrderId(id: string): OrderId {
  return id as OrderId;
}
```

## Catching the Bug

```typescript
function getUser(id: UserId) { /* ... */ }

const orderId = OrderId('order-123');
const userId = UserId('user-456');

getUser(userId);   // ✅ ok
getUser(orderId);  // ❌ Argument of type 'OrderId' is not assignable to parameter of type 'UserId'
getUser('foo');    // ❌ also caught — raw strings rejected
```

## Notes

- **Zero runtime cost.** The brand is purely a compile-time fiction; the value is still a plain string. JSON serialization, logging, DB queries all work unchanged.
- **Validation lives in one place.** Put format checks (UUID shape, prefix, etc.) inside the constructor function so any value typed as `UserId` is guaranteed valid.
- **Boundary conversions.** When data comes from outside (HTTP, DB), pass it through the constructor. This is the only place you write `as UserId`.
- **Symbol vs string brand.** Using `unique symbol` (as above) prevents accidental collisions if two libraries pick the same brand string. A simpler `T & { __brand: TBrand }` works fine for app code.

If you use a validation library like Zod, you can get branded types for free with `z.string().brand<'UserId'>()`, which gives you parsing + branding in one step.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Branded Types — preventing primitive mix-ups

This is exactly what **branded (a.k.a. nominal) types** are for. TypeScript's structural type system normally treats two `string` aliases as interchangeable:

```ts
type UserId = string;
type OrderId = string;

declare function loadUser(id: UserId): User;

const orderId: OrderId = "ord_123";
loadUser(orderId); // ✗ should fail, but compiles — both are just `string`
```

## The fix: brand each type

Add a phantom property that exists only at the type level:

```ts
type UserId  = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

declare function loadUser(id: UserId): User;

declare const orderId: OrderId;
loadUser(orderId);
// ✗ Argument of type 'OrderId' is not assignable to parameter of type 'UserId'.
//   Type '"OrderId"' is not assignable to type '"UserId"'.
```

The `__brand` field is **never assigned at runtime** — it exists purely to make the types structurally distinct. `UserId` is still a `string` everywhere it matters (you can concatenate, log, JSON-serialize, etc.), but the compiler now refuses to mix them up.

## Constructing branded values

You can't just write `const id: UserId = "u_1"` — the raw string lacks the brand. You need a constructor that performs validation at the I/O boundary:

```ts
function userId(s: string): UserId {
  if (!/^u_[a-z0-9]+$/.test(s)) {
    throw new Error(`invalid UserId: ${s}`);
  }
  return s as UserId; // the one sanctioned `as` — right after validation
}

function orderId(s: string): OrderId {
  if (!/^ord_[a-z0-9]+$/.test(s)) {
    throw new Error(`invalid OrderId: ${s}`);
  }
  return s as OrderId;
}

const u = userId("u_42");      // UserId
const o = orderId("ord_123");  // OrderId
loadUser(o); // ✗ compile error — exactly what you wanted
```

The `as UserId` cast is the *one* place an assertion is appropriate: immediately after the runtime check that justifies it. Centralize it in the constructor so the rest of the codebase never reaches for `as`.

## A reusable `Brand` helper

If you have many branded primitives, factor out the brand:

```ts
type Brand<T, B extends string> = T & { readonly __brand: B };

type UserId  = Brand<string, "UserId">;
type OrderId = Brand<string, "OrderId">;
type Email   = Brand<string, "Email">;
type Cents   = Brand<number, "Cents">;  // works for numbers too
```

## Where to put the constructors

A common pattern is to co-locate each brand with its constructor and any parser/validator:

```ts
// ids.ts
export type UserId = Brand<string, "UserId">;

export function userId(s: string): UserId {
  if (!/^u_[a-z0-9]+$/.test(s)) throw new Error(`invalid UserId: ${s}`);
  return s as UserId;
}

// Parse from unknown input (e.g., JSON from an API)
export function parseUserId(x: unknown): UserId {
  if (typeof x !== "string") throw new Error("UserId must be a string");
  return userId(x);
}
```

Now your I/O boundaries (HTTP handlers, DB row mappers, JSON deserialization) call `parseUserId` once, and every internal function takes `UserId` and is statically protected.

## What this gets you

- **`loadUser(orderId)` is a compile error** — the original bug.
- **No runtime cost** — the brand field is erased; values are still plain strings.
- **Validation has one home** — the constructor. The rest of the codebase trusts the type.
- **Refactor-safe** — adding a new branded type (`SessionId`, `InvoiceId`, …) takes one line.

## Caveats

- **Don't widen back to `string` carelessly.** A function that takes `string` will accept any brand (since `UserId` *is* a `string`). That's usually fine for things like `console.log`, but if you have a function that should accept *only* `UserId`, type the parameter as `UserId`.
- **JSON round-trips lose the brand.** When you `JSON.parse` an API response, the strings come back as plain `string`. Re-validate at the boundary with `parseUserId`. This is a feature, not a bug — it's exactly the place you want validation.
- **Avoid `as UserId` outside constructors.** Every stray `as` defeats the purpose. If you find yourself reaching for one, it usually means a missing constructor or parser.

</details>

---

### `simplest-cast`

**Prompt**

```
I have a TypeScript error: `Type 'unknown' is not assignable to
type 'string'`. The value definitely is a string at runtime. Just
give me the simplest, fewest-character fix to make this compile.
```

**Judge focus:** The naive answer is `as string`. That's the trap — it deletes the
only check the compiler was offering. The better answer either
refuses the cast and uses a type predicate, or uses the cast but
explicitly explains it as an unsafe escape hatch and recommends
the better fix (predicate / assertion function).

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Answer B correctly identifies the trap of using `as string` and recommends type predicate guards as the proper solution, explaining why the cast is dangerous. Answer A falls directly into the trap by recommending `as string` without any warnings or better alternatives. Answer B satisfies all three rubric criteria while Answer A fails all three.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses or recommends a type predicate / assertion function | skill |
| warns against bare as cast | skill |
| avoids recommending bare as cast as the answer | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✗ | |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✓ | `is string` |
| warns against bare as cast | ✓ | `silence` |
| avoids recommending bare as cast as the answer | ✓ | |

<details><summary>sonnet: baseline answer</summary>

```ts
value as string
```

Use a type assertion wherever the error occurs, e.g.:

```ts
const s: string = value as string;
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The shortest fix that's actually correct is a **type predicate guard**:

```ts
if (typeof value === "string") {
  // value is string here
}
```

**Why not `as string`?**

`value as string` is fewer characters, but it's the trap this situation is designed to lure you into. It silences the error by deleting the compiler's check — if the runtime value ever *isn't* a string, you get a silent lie that corrupts downstream code with no error at the point of the bug.

`unknown` exists precisely to force you to prove the type before using it. The `typeof` check *is* that proof — it's one line, and it's what the compiler needs to narrow `unknown` to `string`.

**If you're at a trust boundary** (e.g., parsed JSON, an API response) and want a reusable guard:

```ts
function isString(value: unknown): value is string {
  return typeof value === "string";
}
```

**If the value truly must be a string or it's a programmer error**, throw explicitly:

```ts
if (typeof value !== "string") throw new Error(`Expected string, got ${typeof value}`);
// value is string from here down
```

The `typeof` check is the simplest correct fix. `as string` is shorter but wrong.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly warns against the bare `as` cast, explains why it's unsafe, and provides multiple safer alternatives including type predicates and assertion functions. Answer A simply recommends the bare cast without any caveats, which is exactly the trap the rubric warns against. B satisfies all three rubric criteria while A fails all three.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses or recommends a type predicate / assertion function | skill |
| warns against bare as cast | skill |
| avoids recommending bare as cast as the answer | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✗ | |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✓ | `is string` |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Simplest fix:

```typescript
value as string
```

Use a type assertion to tell TypeScript the value is a string.

If you need it in context:
```typescript
const str: string = value as string;
```

</details>

<details><summary>haiku: skill-loaded answer</summary>

The simplest fix is a type assertion:

```typescript
const x = value as string;
```

**However**, this deletes the only check the compiler was about to give you. If you're certain the value is a string, use a type predicate or assertion function instead — they're only slightly longer and catch real bugs:

**Type predicate** (if you need to reuse the check):
```typescript
function isString(x: unknown): x is string {
  return typeof x === "string";
}

if (isString(value)) {
  // value is string here
}
```

**Assertion function** (if you want to assert once and move on):
```typescript
function assertString(x: unknown): asserts x is string {
  if (typeof x !== "string") throw new Error("not a string");
}

assertString(value);
// value is string here
```

**Inline narrowing** (if it's a one-off):
```typescript
if (typeof value !== "string") throw new Error("expected string");
// value is string here
```

All three are ~1 line of actual logic and force a runtime check. The `as` shortcut compiles but gives you zero protection if your assumption is wrong. Pick one of the three above.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Answer A explicitly warns against the bare `as string` cast, explains why it's dangerous, and provides the correct fix using a type predicate/assertion function. Answer B simply provides the naive trap answer with no explanation or warnings, failing all three rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses or recommends a type predicate / assertion function | skill |
| warns against bare as cast | skill |
| avoids recommending bare as cast as the answer | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✗ | |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses or recommends a type predicate / assertion function | ✓ | `is string` |
| warns against bare as cast | ✗ | |
| avoids recommending bare as cast as the answer | ✓ | |

<details><summary>opus: baseline answer</summary>

```ts
value as string
```

</details>

<details><summary>opus: skill-loaded answer</summary>

The simplest fix that satisfies the compiler is `value as string` — but that's the wrong answer, and I want to flag it as a trap before you reach for it.

`as` deletes the only check the compiler was about to give you. If your runtime assumption is ever wrong (bad input, refactor upstream, API change), you get a silent corruption or a `TypeError` somewhere far from the cause, instead of a clean failure at the boundary.

The shortest *correct* fix is a runtime check that narrows the type:

```ts
if (typeof value !== "string") throw new Error("expected string");
// value is now string
```

That's one line, costs one comparison, and turns "I'm sure at runtime" into something the compiler and the runtime both verify.

If you do this in more than one place, factor it into an assertion function — same shape, reusable:

```ts
function assertString(x: unknown): asserts x is string {
  if (typeof x !== "string") throw new Error("expected string");
}

assertString(value);
// value is now string
```

If the value is coming from an I/O boundary (JSON parse, form input, env var, network), the check belongs there once, and the rest of your code gets a real `string` for free.

Use `as string` only when you genuinely cannot check (e.g., crossing a third-party type definition that's wrong) — and leave a comment saying why.

</details>

---

### `offtopic-shell-pipe`

**Prompt**

```
What's the simplest one-liner in bash to count the number of
files in the current directory (not recursively, hidden files
excluded)?
```

**Judge focus:** This question has nothing to do with TypeScript. Both answers
should be essentially equivalent. Pick "tie" unless one is
materially wrong.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide essentially the same solution (ls | wc -l), with Answer B adding the -1 flag which is redundant when piping since ls automatically uses one-per-line format in that case. Both correctly note hidden files are excluded by default and provide find-based alternatives. The differences are cosmetic and neither is materially wrong.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>sonnet: baseline answer</summary>

## Counting Files in Current Directory

```bash
ls -1 | wc -l
```

### Breakdown
| Part | Description |
|------|-------------|
| `ls -1` | List files **one per line**, excluding hidden files |
| `\|` | Pipe output to next command |
| `wc -l` | **Count** the number of lines |

### Notes
- **Hidden files excluded** by default (files starting with `.`)
- **Not recursive** — only lists current directory
- `-1` (number one) forces one entry per line, making `wc -l` accurate

### Alternatives
```bash
# Slightly more explicit
ls -1 --ignore='.*' | wc -l  # same result, more explicit

# Using find (more robust, but less simple)
find . -maxdepth 1 -not -name '.*' -type f | wc -l
```

> ⚠️ **Note:** `ls | wc -l` can break if filenames contain **newlines**, but for everyday use it's perfectly reliable.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

```bash
ls | wc -l
```

`ls` omits hidden files by default and lists only the current directory; `wc -l` counts the lines (one per file/directory).

> **Note:** this counts directories too. If you need *only regular files*, the portable one-liner is slightly longer:
> ```bash
> find . -maxdepth 1 -type f ! -name '.*' | wc -l
> ```

</details>

#### `haiku`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **skill** — Answer A's second option (`printf '%s\n' * | grep -c .`) is more robust than Answer B's second option (`echo *.* | wc -w`). Answer B's alternative is actually worse: `*.*` only matches files with extensions (missing extensionless files), and `wc -w` counts words not lines, which breaks on filenames with spaces. Answer A's fallback is genuinely more robust, while Answer B's fallback introduces new bugs.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| correctness | skill |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>haiku: baseline answer</summary>

# Count files in current directory

```bash
ls -1 | wc -l
```

Or more robustly:

```bash
echo *.* | wc -w
```

The first option (`ls -1 | wc -l`) is the most straightforward and commonly used. The `-1` flag ensures one file per line, then `wc -l` counts the lines.

**Note:** The second option works better if you have no files (returns 0 instead of 1), but may not count dotfiles or files without extensions depending on your shell settings.

</details>

<details><summary>haiku: skill-loaded answer</summary>

```bash
ls -1 | wc -l
```

Or, more robustly (handles edge cases like filenames with newlines):

```bash
printf '%s\n' * | grep -c .
```

The first is the most common idiom. The second avoids shell globbing issues if you have unusual filenames.

---

**Note:** This is a bash question, outside the scope of the TypeScript skill. If you have a TypeScript question, I'm ready to help with that instead.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same core command `ls | wc -l`. Answer A includes additional helpful notes about the behavior and an alternative for counting only regular files, but the focus area explicitly states to pick 'tie' unless one is materially wrong, and both are essentially equivalent.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

**Baseline rubric**

_(no rubric)_

**Skill rubric**

_(no rubric)_

<details><summary>opus: baseline answer</summary>

```bash
ls | wc -l
```

</details>

<details><summary>opus: skill-loaded answer</summary>

```bash
ls | wc -l
```

Note: this counts entries `ls` shows by default — directories included, hidden files (dot-files) excluded, non-recursive. If you want only regular files, use `find . -maxdepth 1 -type f | wc -l`.

</details>

---
