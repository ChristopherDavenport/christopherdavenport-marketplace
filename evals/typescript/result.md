# Eval report: `typescript`

- Backend: **SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)**
- Cases: **8**
- Models: **sonnet, haiku, opus**
- Total cost: **$2.11** (judge cost not counted)

## Per-model summary

| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |
| --- | --- | --- | --- |
| `sonnet` | 5/8 | 4 / 0 / 4 | 86% → 95% (+10%) |
| `haiku` | 8/8 | 7 / 0 / 1 | 86% → 95% (+10%) |
| `opus` ¹ | 5/8 | 4 / 0 / 4 | 90% → 95% (+5%) |

¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts).

## Expectations by kind

| Expectation kind | Total | sonnet met | haiku met | opus met |
| --- | --- | --- | --- | --- |
| `skill_wins` | 6 | 3/6 | 6/6 | 3/6 |
| `skill_wins_strict` | 1 | 1/1 | 1/1 | 1/1 |
| `tie` | 1 | 1/1 | 1/1 | 1/1 |

## Cases

| Case | Expected | sonnet | haiku | opus |
| --- | --- | --- | --- | --- |
| `discriminated-union-exhaustive` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `satisfies-vs-annotation` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `unknown-vs-any` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✗ = tie |
| `branded-types` | skill_wins | ✗ = tie | ✓ ✓ skill | ✓ ✓ skill |
| `abortsignal-cancellation` | skill_wins | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `mapped-type-validators` | skill_wins | ✗ = tie | ✓ ✓ skill | ✗ = tie |
| `simplest-cast` | skill_wins_strict | ✓ ✓ skill | ✓ ✓ skill | ✓ ✓ skill |
| `offtopic-shell-pipe` | tie | ✓ = tie | ✓ = tie | ✓ = tie |

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly implement the switch-on-discriminant pattern with a never-typed exhaustiveness check and avoid `any`. Answer A provides more practical extras (the `satisfies Record` lookup pattern, a richer return type example, and a quick-reference table) while Answer B adds a generic `match` helper that's also useful. The core focus-area requirement — `default: const _: never = x` or equivalent — is met by both via `assertNever(request)`, which is functionally identical. Neither answer uses the inline `const _: never = x` form exactly, but both use the canonical `assertNever` helper which is the standard TypeScript idiom. The quality is essentially equal on all three rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses switch on discriminant | tie |
| uses never-typed exhaustiveness check | tie |
| avoids any | tie |

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

The key technique is using a **never-typed exhaustive check** — if all variants are handled, the remaining type is `never`. If you add a new variant and forget to handle it, the compiler will error.

### The Core Pattern

```typescript
// The exhaustive check helper
function assertNever(value: never, message?: string): never {
  throw new Error(message ?? `Unhandled variant: ${JSON.stringify(value)}`);
}
```

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

function describeRequest(request: Request): string {
  switch (request.kind) {
    case "pending":
      return "Loading...";

    case "ok":
      return `Success: ${request.value}`;

    case "error":
      return `Error: ${request.message}`;

    default:
      // If all variants are handled, `request` is narrowed to `never` here.
      // If you add a new variant and forget to handle it, this line
      // becomes a compile error: "Argument of type 'X' is not assignable
      // to parameter of type 'never'."
      return assertNever(request);
  }
}
```

---

### Seeing the Compiler Catch a Missing Variant

Add a new variant to the type:

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string }; // 🆕 new variant
```

The function above now **fails to compile**:

```
Argument of type '{ kind: "cancelled"; reason: string }' is not
assignable to parameter of type 'never'.
```

TypeScript tells you exactly which variant you forgot and exactly where.

---

### Bonus: A Generic `match` Helper

For a more functional style, you can build a fully type-safe `match` function that enforces every variant is handled **without** a `default` branch:

```typescript
// Builds a Record that requires a handler for every `kind` in the union
type MatchHandlers<T extends { kind: string }, R> = {
  [K in T["kind"]]: (variant: Extract<T, { kind: K }>) => R;
};

function match<T extends { kind: string }, R>(
  value: T,
  handlers: MatchHandlers<T, R>
): R {
  // The cast is safe: we know `value.kind` is a key of `handlers`
  const handler = handlers[value.kind as T["kind"]] as (v: T) => R;
  return handler(value);
}
```

```typescript
// Usage — every variant must be handled, or it's a compile error
function describeRequest(request: Request): string {
  return match(request, {
    pending: ()        => "Loading...",
    ok:      (r)      => `Success: ${r.value}`,
    error:   (r)      => `Error: ${r.message}`,
    // cancelled: ...  ← forgetting this is a compile error
  });
}
```

If you add `cancelled` to the type and forget to add it to `match`, you get:

```
Property 'cancelled' is missing in type '{ pending: ...; ok: ...; error: ...; }'
but required in type 'MatchHandlers<Request, string>'.
```

---

### Summary

| Technique | How it catches missing variants |
|---|---|
| `switch` + `assertNever` | `default` branch receives a non-`never` type → error |
| `match` helper | Object literal must satisfy `MatchHandlers<T, R>` → missing key error |

Both approaches give you **compile-time safety** with clear error messages pointing to exactly what needs updating.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Exhaustive Discriminated Union Handling

The key is a `never`-typed default branch. When you add a variant, TypeScript can no longer assign it to `never`, and the function becomes a compile error at every unhandled switch.

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

// The exhaustiveness sentinel. Placing it here means every switch
// in the codebase can call it — one definition, many call sites.
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
      // If you add a variant and forget this function, the compiler
      // flags this line: "Argument of type 'X' is not assignable to
      // parameter of type 'never'."
      return assertNever(request, `Unhandled request kind: ${JSON.stringify(request)}`);
  }
}
```

### What happens when you add a variant

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled"; reason: string };  // ← new variant
```

Every function with an unhandled `default: assertNever(request)` now produces:

```
Argument of type '{ kind: "cancelled"; reason: string }'
is not assignable to parameter of type 'never'.
```

The compiler gives you a checklist of every site that needs updating — no grep, no runtime surprise.

### Handling variants without a switch

For inline expressions (JSX, short transforms), a lookup object with `satisfies` works well:

```typescript
const REQUEST_LABEL = {
  pending:   "Loading…",
  ok:        "Done",
  error:     "Failed",
  cancelled: "Cancelled",
} satisfies Record<Request["kind"], string>;

// `satisfies` validates the shape but preserves the narrow literal types.
// Add a variant to `Request` and forget to add it here → compile error.
const label = REQUEST_LABEL[request.kind];
```

`satisfies Record<Request["kind"], string>` forces the object to cover every key in the union. Missing a key is a compile error; adding an unknown key is also a compile error.

### Returning structured data instead of strings

The same pattern scales to richer return types:

```typescript
type RequestView =
  | { status: "loading" }
  | { status: "success"; data: string }
  | { status: "failure"; error: string }
  | { status: "cancelled"; reason: string };

function toView(request: Request): RequestView {
  switch (request.kind) {
    case "pending":
      return { status: "loading" };
    case "ok":
      return { status: "success", data: request.value };
    case "error":
      return { status: "failure", error: request.message };
    case "cancelled":
      return { status: "cancelled", reason: request.reason };
    default:
      return assertNever(request);
  }
}
```

### Quick reference

| Technique | When to use |
|---|---|
| `switch` + `assertNever` default | Functions with non-trivial per-variant logic |
| `satisfies Record<Union["kind"], V>` | Simple value lookups; inline expressions |
| Type predicate (`x is T`) | Narrowing outside a switch, e.g. in `.filter()` |

The `assertNever` function is the load-bearing piece. It does two things at once: it's a compile-time proof that the branch is unreachable (the `never` parameter), and a runtime guard that throws a descriptive error if somehow an unexpected value slips through (e.g., data from an untyped API boundary).

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use a switch on the discriminant with a `const _: never = x` exhaustive check and avoid `any`. Answer B is more thorough and idiomatic: it uses `throw` in the default branch (more correct than `return _exhaustive` in Answer A's primary example), provides clearer explanations of why the pattern works, and demonstrates the compiler error message explicitly. Answer A's Pattern 4 (object map) loses type narrowing per branch, while Answer B's equivalent pattern uses `Extract` to preserve proper narrowing. Neither answer uses casts or runtime assertions as the primary approach.

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
| avoids any | ✓ | |

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

---

## 2. **If-Else with Exhaustiveness Check**

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

---

## 3. **Helper Function for Cleaner Code**

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

---

## 4. **Object Map Pattern (Type-Safe)**

```typescript
const handlers: Record<Request["kind"], (req: Request) => string> = {
  pending: () => "Loading...",
  ok: (req) => `Success: ${req.value}`,
  error: (req) => `Error: ${req.message}`,
};

function handleRequest(req: Request): string {
  return handlers[req.kind](req);
}
```

**Advantage:** TypeScript ensures all keys are present. **Disadvantage:** Less type narrowing per branch.

---

## 5. **Testing the Exhaustiveness**

```typescript
// Add a new variant
type Request = 
  | { kind: "pending" } 
  | { kind: "ok"; value: string } 
  | { kind: "error"; message: string }
  | { kind: "timeout" };  // ← New variant

// ❌ TypeScript error: Type 'Request' is not assignable to type 'never'
function handleRequest(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Loading...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Error: ${req.message}`;
    default:
      const _exhaustive: never = req; // ← ERROR HERE
      return _exhaustive;
  }
}
```

---

## **Recommendation**

Use **approach #1 (switch + never)** or **#3 (assertNever helper)** for:
- ✅ Maximum type safety
- ✅ Clear intent
- ✅ Compiler catches all missing cases
- ✅ Works with complex nested types

The `never` type is TypeScript's way of saying "this code should be unreachable," making it perfect for exhaustiveness checking.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Handling Discriminated Unions with Exhaustiveness

Your `Request` type is a **discriminated union** — each variant has a `kind` tag that lets the compiler narrow the type. Here's how to ensure exhaustiveness:

## Pattern 1: `switch` with `never` Default (Recommended)

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
      return `Failed: ${req.message}`;
    default:
      const _exhaustive: never = req;
      throw new Error(`Unhandled variant: ${_exhaustive}`);
  }
}
```

**Why this works:**
- TypeScript narrows `req` in each `case` branch
- The `default` branch assigns `req` to `never` — if you forgot a case, `req` is still a union, and the assignment fails with a compile error
- The `throw` is unreachable in correct code but documents intent: "this should never happen"

**When you add a new variant:**
```typescript
type Request = 
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "timeout" };  // ← new variant
```

TypeScript immediately complains:
```
Type '{ kind: "timeout"; }' is not assignable to type 'never'.
```

You must add a `case "timeout":` branch.

---

## Pattern 2: Helper Function for Exhaustiveness

If you prefer a function call over the `never` assignment:

```typescript
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function handleRequest(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Loading...";
    case "ok":
      return `Success: ${req.value}`;
    case "error":
      return `Failed: ${req.message}`;
    default:
      return assertNever(req);
  }
}
```

Same compile-time guarantee; slightly more readable if you have many exhaustive switches.

---

## Pattern 3: `if`/`else` Chain with Type Predicates

For smaller unions or when you prefer imperative style:

```typescript
function handleRequest(req: Request): string {
  if (req.kind === "pending") {
    return "Loading...";
  } else if (req.kind === "ok") {
    return `Success: ${req.value}`;
  } else if (req.kind === "error") {
    return `Failed: ${req.message}`;
  } else {
    const _exhaustive: never = req;
    throw new Error(`Unhandled variant: ${_exhaustive}`);
  }
}
```

Same exhaustiveness guarantee; the final `else` is unreachable in correct code.

---

## Pattern 4: Discriminated Union as a Function Parameter

If you're dispatching to different handlers:

```typescript
type Handler<T extends Request> = (req: T) => string;

const handlers: {
  [K in Request["kind"]]: Handler<Extract<Request, { kind: K }>>;
} = {
  pending: () => "Loading...",
  ok: (req) => `Success: ${req.value}`,
  error: (req) => `Failed: ${req.message}`,
};

function handleRequest(req: Request): string {
  return handlers[req.kind](req);
}
```

**Why this works:**
- `Request["kind"]` is the union of all tag values: `"pending" | "ok" | "error"`
- `[K in Request["kind"]]` creates an object with one key per variant
- `Extract<Request, { kind: K }>` narrows to the variant with that tag
- If you forget a handler, TypeScript complains about the missing key

**When you add a new variant**, the object literal is incomplete:
```
Property 'timeout' is missing in type '{ pending: ...; ok: ...; error: ... }'
```

---

## Pattern 5: Exhaustive `match` Helper (Functional Style)

If your codebase leans functional, hand-roll a `match` helper:

```typescript
function match<T extends { kind: string }, R>(
  req: T,
  handlers: {
    [K in T["kind"]]: (req: Extract<T, { kind: K }>) => R;
  }
): R {
  return handlers[req.kind](req as any);
}

const result = match(req, {
  pending: () => "Loading...",
  ok: (req) => `Success: ${req.value}`,
  error: (req) => `Failed: ${req.message}`,
});
```

Same exhaustiveness guarantee as Pattern 4, but reads like a functional pipeline.

---

## Comparison

| Pattern | Pros | Cons |
|---------|------|------|
| **switch + never** | Explicit, familiar, no helper needed | Verbose for many variants |
| **assertNever helper** | Cleaner than inline `never` assignment | Requires a helper function |
| **if/else + never** | Imperative, readable | Verbose for many variants |
| **handlers object** | Declarative, scales well, easy to add handlers dynamically | Requires `Extract` and mapped types |
| **match helper** | Functional, composable, scales well | Requires a helper; less familiar to imperative teams |

---

## Real-World Example: Request Lifecycle

```typescript
type RequestState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: unknown }
  | { kind: "error"; error: Error };

function getDisplayMessage(state: RequestState): string {
  switch (state.kind) {
    case "idle":
      return "Ready to fetch";
    case "loading":
      return "Fetching...";
    case "success":
      return `Loaded: ${JSON.stringify(state.data)}`;
    case "error":
      return `Error: ${state.error.message}`;
    default:
      const _exhaustive: never = state;
      throw new Error(`Unhandled state: ${_exhaustive}`);
  }
}

// Later, you add a variant:
type RequestState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: unknown }
  | { kind: "error"; error: Error }
  | { kind: "retrying"; attempt: number };  // ← new

// Compiler error in getDisplayMessage:
// Type '{ kind: "retrying"; attempt: number; }' is not assignable to type 'never'.
// ✓ You must add a case for "retrying"
```

---

## Key Takeaway

**Use the `never` default pattern** (Pattern 1 or 2) — it's the most reliable way to catch missing cases at compile time. When you add a variant, the compiler will flag every function that handles the union, forcing you to update them all.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use a switch on the discriminant with a never-typed assertNever helper and avoid `any`. Answer A is slightly better aligned with the focus area because it explicitly notes in its 'Notes' section that the `default: const _: never = x` inline pattern is an alternative and warns against using if/else chains, while Answer B actually promotes the if/else pattern as a 'bonus' which the rubric specifically disfavors. Answer A's notes section also more explicitly addresses why the switch form is preferred over if/else chains.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses switch on discriminant | skill |
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

<details><summary>opus: baseline answer</summary>

# Exhaustive Pattern Matching in TypeScript

The trick is to use a **`never`-typed helper** in the `default` (or final `else`) branch. Since `never` accepts no values, TypeScript will error if any variant isn't handled.

## The Setup

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };
```

## The Exhaustiveness Helper

```typescript
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}
```

## Using It with `switch`

```typescript
function describe(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "Still loading...";
    case "ok":
      return `Got value: ${req.value}`;
    case "error":
      return `Failed: ${req.message}`;
    default:
      return assertNever(req); // ← compile-time check
  }
}
```

## What Happens When You Add a Variant

Suppose later you extend the type:

```typescript
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled" }; // new!
```

Now the compiler complains in `describe`:

```
Argument of type '{ kind: "cancelled"; }' is not assignable to parameter of type 'never'.
```

That single error points you to every function that needs updating — fix them all and the build goes green.

## Bonus: Same Pattern with `if`/`else`

```typescript
function statusCode(req: Request): number {
  if (req.kind === "pending") return 102;
  if (req.kind === "ok") return 200;
  if (req.kind === "error") return 500;
  return assertNever(req);
}
```

## Why This Works

TypeScript's **control-flow analysis** narrows `req` after each handled case. By the `default` branch, if you've covered every variant, `req`'s type is narrowed to `never`. Adding a new variant widens it again, breaking the call to `assertNever` — turning a runtime bug into a compile-time error.

## Tip: Enforce It Project-Wide

Enable these in `tsconfig.json` to make accidental fall-throughs harder:

```json
{
  "compilerOptions": {
    "strict": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true
  }
}
```

</details>

<details><summary>opus: skill-loaded answer</summary>

# Exhaustive Handling with Discriminated Unions

The pattern is: `switch` on the discriminant tag, then add a `default` branch that assigns the value to `never`. If you add a new variant later, the assignment fails to compile in every consumer.

```ts
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string };

function describe(req: Request): string {
  switch (req.kind) {
    case "pending":
      return "still loading...";
    case "ok":
      // narrowed to { kind: "ok"; value: string }
      return `got: ${req.value}`;
    case "error":
      // narrowed to { kind: "error"; message: string }
      return `failed: ${req.message}`;
    default:
      return assertNever(req);
  }
}

// Reusable exhaustiveness helper — put this in a shared utils module.
function assertNever(x: never): never {
  throw new Error(`unexpected variant: ${JSON.stringify(x)}`);
}
```

## Why this works

In each `case`, TypeScript narrows `req` to the matching variant — so `req.value` is available in `"ok"` and `req.message` is available in `"error"`, with no casts.

In the `default`, TypeScript has eliminated every known variant, so `req` is narrowed to `never`. Passing it to `assertNever(x: never)` type-checks — but only as long as the union is fully covered.

## What happens when you add a variant

Suppose you later extend the type:

```ts
type Request =
  | { kind: "pending" }
  | { kind: "ok"; value: string }
  | { kind: "error"; message: string }
  | { kind: "cancelled" };  // new variant
```

Now in `describe`, the `default` branch sees `req` narrowed to `{ kind: "cancelled" }`, not `never`. The call `assertNever(req)` fails to compile:

```
Argument of type '{ kind: "cancelled"; }' is not assignable to parameter of type 'never'.
```

You get this error at **every** `switch` over `Request` that forgot the new case — exactly the goal.

## Notes

- **Use `switch`, not chained `if`/`else if`.** TypeScript's narrowing on `switch (req.kind)` is more reliable, and a missed case in an `if` chain falls through to whatever's after it rather than landing in a `never` check.
- **The `default` is required.** Without it, the compiler can't tell you forgot a case — it just exits the switch.
- **Don't `throw` directly in `default` without the `never` assignment.** `throw new Error("unreachable")` runs fine, but only fails at runtime. The `assertNever(req)` pattern moves the failure to compile time.
- **`assertNever` returning `never`** lets you use it in expression positions too, e.g. `const msg = req.kind === "ok" ? req.value : assertNever(req as never)` — though the `switch` form is usually clearer.

This same pattern works for state machines, parser AST nodes, message types, action reducers — anywhere you have a closed set of variants you want the compiler to police.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers cover the core distinction well, but Answer B is more precise and idiomatic. It correctly shows that `: Config` widens even literal values like `port: 3000` to `number`, while `satisfies` preserves `3000` as a literal type — a nuance Answer A misses (A incorrectly claims `theme1.mode` is `'light' | 'dark'` due to widening, which is actually correct behavior, but then muddles the explanation). Answer B also includes the valuable `as const satisfies` pattern and provides cleaner, more focused examples that directly illustrate the widening vs. preserving distinction.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| mentions widening from annotation | skill |
| uses satisfies keyword | tie |
| mentions preserving literal / narrow inferred type | skill |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions widening from annotation | ✓ | `WIDEN` |
| uses satisfies keyword | ✓ | `satisfies` |
| mentions preserving literal / narrow inferred type | ✓ | `preserv` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| mentions widening from annotation | ✓ | `Widen` |
| uses satisfies keyword | ✓ | `satisfies` |
| mentions preserving literal / narrow inferred type | ✓ | `preserv` |

<details><summary>sonnet: baseline answer</summary>

## `const config: Config = {...}` vs `const config = {...} satisfies Config`

These two approaches handle type checking differently in subtle but important ways.

---

### The Core Difference

```typescript
type Config = {
  port: number;
  host: string;
  options: Record<string, string>;
};

// Type annotation - TypeScript WIDENS the type to Config
const config1: Config = {
  port: 3000,
  host: "localhost",
  options: { timeout: "30s" }
};

// satisfies - TypeScript KEEPS the literal/narrow type
const config2 = {
  port: 3000,
  host: "localhost",
  options: { timeout: "30s" }
} satisfies Config;
```

---

### Problem 1: Loss of Literal Types

```typescript
type Theme = {
  colors: Record<string, string>;
  mode: "light" | "dark";
};

const theme1: Theme = {
  colors: { primary: "#fff" },
  mode: "light"
};

const theme2 = {
  colors: { primary: "#fff" },
  mode: "light"
} satisfies Theme;

// ❌ Error: Property 'primary' does not exist on type 'Record<string, string>'
//    TypeScript only knows colors is Record<string, string>
theme1.colors.primary;

// ✅ Works! TypeScript knows colors has a 'primary' key
theme2.colors.primary;

// Both correctly typed as "light" | "dark"... but:
type T1 = typeof theme1.mode; // "light" | "dark"  (widened to union)
type T2 = typeof theme2.mode; // "light"            (keeps literal type)
```

---

### Problem 2: Excess Property Checking Behavior

```typescript
type Config = { port: number; host: string };

// ✅ Annotation catches typos at assignment
const c1: Config = {
  port: 3000,
  host: "localhost",
  typo: "oops"  // ❌ Error: Object literal may only specify known properties
};

// ✅ satisfies ALSO catches typos
const c2 = {
  port: 3000,
  host: "localhost",
  typo: "oops"  // ❌ Error: caught here too
} satisfies Config;
```

Both catch excess properties — no difference here.

---

### Problem 3: Missing Properties

```typescript
type Config = { port: number; host: string };

// With annotation, TypeScript fills in the type as Config
// so accessing missing props gives type-level errors
const c1: Config = { port: 3000 }; // ❌ Error: missing 'host'

// satisfies also catches this
const c2 = { port: 3000 } satisfies Config; // ❌ Error: missing 'host'
```

Again, both catch this — no difference.

---

### Real-World Example: Route Config

```typescript
type Routes = Record<string, { path: string; exact?: boolean }>;

const routes = {
  home:    { path: "/" },
  about:   { path: "/about" },
  profile: { path: "/profile", exact: true }
} satisfies Routes;

// ✅ TypeScript knows these specific keys exist
routes.home.path;    // string
routes.about.path;   // string

// ❌ This would error - 'dashboard' doesn't exist
routes.dashboard;

// With annotation, you'd lose autocomplete on specific keys
const routes2: Routes = { ... };
routes2.home;        // ✅ no error, but no autocomplete either
routes2.dashboard;   // ✅ also no error! (bad)
```

---

### When to Use Each

| Scenario | Use |
|----------|-----|
| You want to **preserve narrow/literal types** | `satisfies` |
| You want **autocomplete on specific keys** | `satisfies` |
| The variable will be **reassigned** to other `Config` values | `: Config` |
| You're defining a **function parameter default** | `: Config` |
| You want the type to be **exactly `Config`**, not a subtype | `: Config` |
| Validating config/theme/route objects | `satisfies` |

---

### You Can Combine Both

```typescript
// Validate shape AND keep as Config type for reassignment
const config: Config = {
  port: 3000,
  host: "localhost"
} satisfies Config;
```

---

### Summary

- **`: Config`** — "treat this as `Config`", widening the type (you lose specificity)
- **`satisfies Config`** — "check this matches `Config`", keeping the narrow type (you keep specificity)

**Default recommendation:** Reach for `satisfies` for object literals like configs, themes, and route maps where you want both validation *and* precise inference. Use `: Type` when you explicitly need the wider type for reassignment or API compatibility.

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

// ❌ Widened to Config — you lose the specific values
const config1: Config = {
  port: 3000,
  host: "localhost",
  mode: "dev",
};

config1.port;  // type: number   (not 3000)
config1.mode;  // type: "dev" | "prod"   (not "dev")

// ✅ Validated against Config — but keeps the narrow inferred type
const config2 = {
  port: 3000,
  host: "localhost",
  mode: "dev",
} satisfies Config;

config2.port;  // type: 3000
config2.mode;  // type: "dev"   ← literal type preserved
```

With `: Config`, TypeScript widens the type to `Config` immediately. The annotation *replaces* the inferred type. With `satisfies Config`, TypeScript *checks* the shape against `Config` but keeps the narrower inferred type.

## What satisfies catches that a plain annotation doesn't

`satisfies` still catches the same structural errors:

```typescript
const bad = {
  port: "oops",   // ✗ Error: string is not assignable to number
  host: "localhost",
  mode: "staging", // ✗ Error: not assignable to "dev" | "prod"
} satisfies Config;
```

The validation is identical — you just don't lose precision afterward.

## When satisfies is the right choice

**1. You need the narrow type downstream**

```typescript
const routes = {
  home: "/",
  about: "/about",
  contact: "/contact",
} satisfies Record<string, string>;

// With `: Record<string, string>`, this would be string — not "/"
type HomeRoute = typeof routes.home; // "/"
```

**2. Discriminated unions and literal types**

```typescript
type Action =
  | { kind: "increment"; amount: number }
  | { kind: "reset" };

const defaultAction = { kind: "increment", amount: 1 } satisfies Action;

// With `: Action`, kind would be "increment" | "reset"
defaultAction.kind; // "increment" — narrows correctly in switches
```

**3. Validating `as const` objects**

```typescript
const LIMITS = {
  maxRetries: 3,
  timeout: 5000,
} as const satisfies Record<string, number>;

// Both: validated against the constraint AND fully readonly with literal types
LIMITS.maxRetries; // 3, not number
```

**4. Catching excess properties on intermediate values**

```typescript
// `: Config` would catch this too, but satisfies works even when
// the object is passed directly without a variable annotation
function start(cfg: Config) { /* ... */ }

start({ port: 3000, host: "localhost", mode: "dev", typo: true } satisfies Config);
//                                                   ^^^^ Error caught here
```

## When to stick with `: Type`

Use an explicit annotation when you *want* the wider type — typically when the variable will be reassigned or when the narrow type would cause problems:

```typescript
// You want this to be Config, not { port: 3000; host: "localhost"; mode: "dev" }
// because you'll reassign it later
let config: Config = { port: 3000, host: "localhost", mode: "dev" };
config = { port: 8080, host: "0.0.0.0", mode: "prod" }; // fine

// Function parameters and return types — always annotate these explicitly
function createConfig(port: number): Config {
  return { port, host: "localhost", mode: "dev" };
}
```

## Quick decision rule

| Situation | Use |
|---|---|
| Literal/object you want to validate *and* keep narrow | `satisfies` |
| Variable you'll reassign to a different value | `: Type` |
| Function parameter or return type | `: Type` (explicit annotation) |
| `as const` object that must match a shape | `as const satisfies Type` |
| You want autocomplete while writing the literal | Either works; `satisfies` is slightly better |

The practical default: **reach for `satisfies` on `const` object literals**. It gives you validation without the cost of widening, and you can always combine it with `as const` when you also want readonly literal types.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer A more thoroughly explains the widening behavior with concrete examples showing how `: Config` widens `mode: 'dev'` to `'dev' | 'prod'`, while `satisfies` preserves the literal `'dev'`. It also covers the `as const satisfies T` pattern and provides a comprehensive decision table. Answer B covers the basics but is less precise about the widening mechanism and uses a slightly misleading heading ('as Config') in the annotation section.

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

// config is typed as Config
config.apiUrl // string (from Config interface)
```

**What happens:**
- TypeScript assigns the type `Config` to the variable
- The object's literal types are widened to match `Config`
- You lose information about specific literal values

## `satisfies` Operator

```typescript
const config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
  retries: 3
} satisfies Config;

// config retains literal types
config.apiUrl // "https://api.example.com" (literal type)
config.timeout // 5000 (literal type)
```

**What happens:**
- TypeScript verifies the object matches `Config`
- The variable keeps its inferred literal types
- You preserve specific value information

## Practical Example

```typescript
interface Theme {
  colors: Record<string, string>;
  spacing: Record<string, number>;
}

// With type annotation - loses specificity
const theme1: Theme = {
  colors: { primary: "#000", secondary: "#fff" },
  spacing: { small: 4, large: 16 }
};
theme1.colors.primary // string (not "#000")

// With satisfies - keeps specificity
const theme2 = {
  colors: { primary: "#000", secondary: "#fff" },
  spacing: { small: 4, large: 16 }
} satisfies Theme;
theme2.colors.primary // "#000" (literal type)
```

## When to Use `satisfies`

✅ **Use `satisfies` when you want to:**

1. **Validate against a type while preserving literal types**
   ```typescript
   const routes = {
     home: "/",
     about: "/about",
     contact: "/contact"
   } satisfies Record<string, string>;
   
   // routes.home is "/" not string
   ```

2. **Enable better autocomplete and type narrowing**
   ```typescript
   const config = {
     env: "production" as const,
     debug: false
   } satisfies Config;
   
   if (config.env === "production") { } // works great
   ```

3. **Catch type errors without widening types**
   ```typescript
   const settings = {
     theme: "dark",
     fontSize: 14
   } satisfies Settings; // Error if doesn't match, but keeps literal types
   ```

✅ **Use type annotation when you want to:**

1. **Explicitly declare the type for clarity**
   ```typescript
   const config: Config = getConfigFromFile();
   ```

2. **Allow the type to be more general**
   ```typescript
   const value: string | number = getValue();
   ```

## Summary Table

| Aspect | Type Annotation | `satisfies` |
|--------|-----------------|-------------|
| Type checking | ✅ | ✅ |
| Preserves literals | ❌ | ✅ |
| Explicit intent | ✅ | ✅ |
| Best for config objects | ❌ | ✅ |
| Best for function params | ✅ | ❌ |

**Rule of thumb:** Use `satisfies` for object literals where you want to keep specific values, use type annotations for function parameters and when you want intentional type widening.

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

After the annotation, `config1.mode` has type `"dev" | "prod"` — the full union. After `satisfies`, `config2.mode` has type `"dev"` — the literal you wrote. The compiler **validates the shape against `Config`** but **preserves the narrower inferred type**.

## Why This Matters

### Example 1: Discriminated Union Narrowing

```typescript
type Request = 
  | { method: "GET"; url: string }
  | { method: "POST"; url: string; body: string };

// ❌ With annotation: method widens to "GET" | "POST"
const req1: Request = {
  method: "GET",
  url: "/api/users",
};
// req1.method is "GET" | "POST" — you lose the literal

// ✅ With satisfies: method stays "GET"
const req2 = {
  method: "GET",
  url: "/api/users",
} satisfies Request;
// req2.method is "GET" — the compiler knows it's GET-only

// Now this works without a type guard:
if (req2.method === "GET") {
  // req2 is narrowed to { method: "GET"; url: string }
  // (though the narrowing is redundant — we already knew)
}
```

More importantly, if you pass `req2` to a function that expects a discriminated union:

```typescript
function handle(req: Request) {
  switch (req.method) {
    case "GET":
      console.log("Fetching", req.url);
      break;
    case "POST":
      console.log("Posting to", req.url, "with", req.body);
      break;
  }
}

handle(req2); // Works; compiler knows req2 is a valid Request
```

### Example 2: Literal Types in Maps/Lookups

```typescript
type Colors = "red" | "green" | "blue";

const colorMap: Record<Colors, string> = {
  red: "#ff0000",
  green: "#00ff00",
  blue: "#0000ff",
};
// colorMap["red"] is string (widened)

const colorMap2 = {
  red: "#ff0000",
  green: "#00ff00",
  blue: "#0000ff",
} satisfies Record<Colors, string>;
// colorMap2["red"] is "#ff0000" (narrow literal)

// Useful if you want to extract the value as a constant:
const RED = colorMap2.red; // type: "#ff0000", not string
```

### Example 3: Tuple Narrowing

```typescript
type Pair = readonly [number, number];

// ❌ Annotation: widens to number[]
const point1: Pair = [10, 20];
// point1[0] is number

// ✅ satisfies: stays readonly [10, 20]
const point2 = [10, 20] as const satisfies Pair;
// point2[0] is 10 (literal)
```

## When to Use Each

| Scenario | Use | Why |
|---|---|---|
| You want the **narrowest inferred type** and need to validate shape | `satisfies T` | Preserves literals; compiler still checks the shape |
| You want to **widen to the full type** (e.g., for reassignment) | `: T` annotation | Explicit intent; the type is what you'll work with |
| You're building a **lookup table / map** and want to preserve literal keys | `satisfies Record<K, V>` | Keys stay narrow; useful for extracting constants |
| You're building a **discriminated union** and want the tag to stay literal | `satisfies Union` | Tag narrowing works without extra type guards |
| You're **reassigning** the variable later | `: T` annotation | Reassignment to a different variant should be allowed |
| You're **exporting** a constant | `as const satisfies T` | Locks the type; consumers see the narrow type |

## Best Practice: Combine with `as const`

For maximum narrowness + validation:

```typescript
const config = {
  mode: "dev",
  port: 3000,
  retries: 3,
} as const satisfies Config;

// config.mode is "dev" (not "dev" | "prod")
// config.port is 3000 (not number)
// config.retries is 3 (not number)
// But the shape is validated against Config
```

This is especially useful for **exported constants** that other modules will use:

```typescript
// config.ts
export const DEFAULT_CONFIG = {
  timeout: 5000,
  retries: 3,
  env: "production",
} as const satisfies Config;

// consumer.ts
import { DEFAULT_CONFIG } from "./config";
// DEFAULT_CONFIG.timeout is 5000 (literal), not number
// Can use it as a discriminant or in a switch without widening
```

## The Rule of Thumb

- **Use `satisfies` by default** when you want to validate shape but keep the inferred type narrow.
- **Use `: T` annotation** when you explicitly want to widen to the full type (e.g., for reassignment or when the narrowness doesn't matter).
- **Combine `as const satisfies T`** for exported constants that need both narrowness and validation.

In modern TypeScript, `satisfies` is the more precise tool. It lets the compiler infer the tightest type while still catching shape errors.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria clearly. Answer A uses a cleaner RouteMap example that vividly shows key widening, while Answer B's concrete Config example with Record<string, boolean> more precisely illustrates the widening/narrowing distinction for values. Both explain satisfies preserving literal types, both mention widening from annotation, and both cover the satisfies keyword thoroughly. The quality is essentially equivalent.

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

<details><summary>opus: baseline answer</summary>

# Type Annotation vs `satisfies`

These two approaches look similar but behave very differently when it comes to type inference.

## Type Annotation: `const config: Config = { ... }`

The variable's type **becomes** `Config`. TypeScript widens the value to match the annotation, and you lose information about the specific shape of what you wrote.

```ts
type Config = { mode: string; tags: string[] };

const config: Config = { mode: "dark", tags: ["a", "b"] };

config.mode; // string (not "dark")
```

## `satisfies`: `const config = { ... } satisfies Config`

The value is **checked against** `Config`, but the variable keeps its narrow, inferred type.

```ts
const config = { mode: "dark", tags: ["a", "b"] } satisfies Config;

config.mode; // "dark" (literal type preserved)
```

## A More Telling Example

```ts
type RouteMap = Record<string, { path: string; auth: boolean }>;

// With annotation — keys are just `string`
const routes1: RouteMap = {
  home: { path: "/", auth: false },
  admin: { path: "/admin", auth: true },
};
routes1.dashboard; // ✅ allowed (typed as the value type), but undefined at runtime!

// With satisfies — keys are preserved
const routes2 = {
  home: { path: "/", auth: false },
  admin: { path: "/admin", auth: true },
} satisfies RouteMap;
routes2.dashboard; // ❌ error: no such property
routes2.home.path; // "/" (literal)
```

## When to Use `satisfies`

Use `satisfies` when you want **both**:
1. Validation that your value conforms to a type
2. The narrowest possible inferred type for downstream use

Common cases:
- **Config objects** where you want literal key/value types preserved
- **Discriminated union literals** (`{ kind: "circle", radius: 1 } satisfies Shape`) so the specific variant is kept
- **`as const`-style data** where you still want a contract checked
- **Lookup maps** where you want autocomplete on the actual keys

## When to Use a Type Annotation

- When you genuinely want the variable to have the wider type (e.g., it's reassigned later, or passed to APIs that expect the abstract type)
- When you want the type to be the source of truth and the value to be interchangeable
- For function parameters and return types (where `satisfies` doesn't apply)

## Rule of Thumb

> Use `satisfies` for **constants and data**; use `: Type` for **variables that should be treated as the abstract type**.

You can also combine them: `const x = { ... } as const satisfies Config` gives you readonly + literal types + validation.

</details>

<details><summary>opus: skill-loaded answer</summary>

# `: Config` vs `satisfies Config`

These look similar but do opposite things to inference. The difference matters whenever you want to *both* validate a shape *and* keep the precise types of what you wrote.

## What each one does

**`const config: Config = { ... }`** — type annotation. The variable's type *becomes* `Config`. The literal is checked against `Config`, then widened to it. You lose any information narrower than `Config`.

**`const config = { ... } satisfies Config`** — constraint check. The literal is validated against `Config`, but the variable keeps its *inferred* type, which is typically narrower.

## A concrete example

```ts
type Config = {
  env: string;
  port: number;
  features: Record<string, boolean>;
};

// With annotation
const a: Config = {
  env: "prod",
  port: 8080,
  features: { auth: true, beta: false },
};

a.env;             // string
a.features.auth;   // boolean | undefined  (it's a Record, key may not exist)
a.features.foo;    // boolean | undefined  (no error — Record allows any key)

// With satisfies
const b = {
  env: "prod",
  port: 8080,
  features: { auth: true, beta: false },
} satisfies Config;

b.env;             // "prod"  (literal type preserved!)
b.features.auth;   // boolean (known to exist)
b.features.foo;    // Error: property 'foo' does not exist
```

Both reject `port: "8080"`. Both reject a missing `env`. The difference is what you can do with `a` vs `b` *after* the check.

## When to use `satisfies`

- **Literals you'll read narrowly later** — config objects, route tables, lookup maps. You want autocomplete on the actual keys, not on `Record<string, ...>`.
- **`as const` objects validated against a shape** — `{ ... } as const satisfies Config` validates structure while locking every value to its literal type.
- **Discriminated-union builders** — declare each entry's `kind` as a literal, then `satisfies` against the union, and downstream code can narrow on the actual `kind`.
- **When you'd otherwise reach for `as Config`** — `satisfies` is almost always the right tool. `as` silences errors; `satisfies` checks them.

```ts
const routes = {
  home:    { path: "/",        method: "GET"  },
  create:  { path: "/items",   method: "POST" },
} as const satisfies Record<string, { path: string; method: "GET" | "POST" }>;

routes.home.method;  // "GET" — not just string
```

## When to use `: Type`

- **Function parameters and return types** — these are contracts, not inferred values. Annotate them.
- **You genuinely want widening** — e.g., a `let` that will be reassigned with other valid `Config` values. Without the annotation, the inferred type is too narrow to accept the reassignment.
- **Public API surface** — explicit annotations document intent and stabilize the type against refactors of the literal.

## Rule of thumb

For `const` literals: prefer `satisfies`. For function signatures and mutable bindings: prefer `:`. If you find yourself writing `as SomeType` on a literal to make an error go away, switch to `satisfies SomeType` — you'll get the same validation without throwing away inference.

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

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend `unknown` over `any` and show narrowing steps, but Answer B is more thorough and practical. It adds an assertion function pattern, mentions `any` being contagious (a key insight), shows more complete type predicate validation with field-level type checks, includes a full end-to-end `fetchUser` function example, and mentions Valibot as an alternative to Zod. Answer B's type predicate is also more rigorous, checking the types of individual fields rather than just their presence.

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
| explains why not any | ✗ | |
| shows narrowing or validation step | ✓ | `typeof` |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| recommends unknown | ✓ | `unknown` |
| explains why not any | ✓ | `any` \| ❌ \| Disable` |
| shows narrowing or validation step | ✓ | `typeof` |

<details><summary>sonnet: baseline answer</summary>

## Parsing JSON in TypeScript

The parsed value should have the type **`unknown`**.

```typescript
const response = await fetch('https://api.example.com/data');
const parsed: unknown = await response.json();
```

### Why `unknown` and not `any`?

`response.json()` actually returns `Promise<any>` in the TypeScript standard library, but you should **explicitly annotate it as `unknown`** instead.

Here's why the distinction matters:

```typescript
// ❌ any — unsound, skips type checking entirely
const parsed: any = await response.json();
parsed.foo.bar.baz;        // No error, but may crash at runtime
parsed.toUpperCase();      // No error, but may crash at runtime

// ✅ unknown — forces you to verify the shape before using it
const parsed: unknown = await response.json();
parsed.foo;                // Error: Object is of type 'unknown'
parsed.toUpperCase();      // Error: Object is of type 'unknown'
```

### The right approach: narrow before use

You must validate/narrow the type before TypeScript will let you use the value:

```typescript
// Option 1: Type guard (manual validation)
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
  console.log(parsed.name); // ✅ Safe — TypeScript knows it's a User
}

// Option 2: Validation library (recommended for production)
import { z } from 'zod';

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
});

const user = UserSchema.parse(parsed); // throws if invalid
console.log(user.name); // ✅ Fully typed and runtime-validated
```

### Summary

| Type | Type-safe? | Requires narrowing? | Recommended? |
|------|-----------|-------------------|--------------|
| `any` | ❌ No | No | ❌ No |
| `unknown` | ✅ Yes | Yes | ✅ Yes |
| `MyType` (assertion) | ⚠️ Partial | No | ⚠️ Risky |

**The core reason:** JSON comes from outside your program — it could be *anything*. `unknown` honestly represents that uncertainty and forces you to prove the shape is what you expect before using it, preventing entire classes of runtime errors.

</details>

<details><summary>sonnet: skill-loaded answer</summary>

## Use `unknown`, not `any`

```typescript
const response = await fetch(url);
const data: unknown = await response.json();
```

### Why not `any`?

`response.json()` returns `Promise<any>` in the standard lib. If you accept that `any` and pass it around, TypeScript stops checking every downstream use — silently, with no error:

```typescript
const data: any = await response.json();
console.log(data.user.name.trim()); // No error. Crashes at runtime if shape is wrong.
```

`any` is contagious: it flows into every variable and return type that touches it, disabling inference along the way.

### Why `unknown`?

`unknown` forces you to prove the shape before using the value:

```typescript
const data: unknown = await response.json();

// TypeScript won't let you do this:
console.log(data.user.name); // Error: 'data' is of type 'unknown'
```

You must narrow first — which is exactly the right behavior for untrusted external data.

---

## Narrowing strategies

### 1. Type predicate (manual, zero dependencies)

```typescript
interface User {
  id: number;
  name: string;
  email: string;
}

function isUser(value: unknown): value is User {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value && typeof (value as Record<string, unknown>).id === "number" &&
    "name" in value && typeof (value as Record<string, unknown>).name === "string" &&
    "email" in value && typeof (value as Record<string, unknown>).email === "string"
  );
}

const data: unknown = await response.json();

if (!isUser(data)) {
  throw new Error("Unexpected response shape", { cause: data });
}

// data is now User — fully typed, runtime-verified
console.log(data.name.trim());
```

### 2. Assertion function (throws instead of returning false)

```typescript
function assertIsUser(value: unknown): asserts value is User {
  if (!isUser(value)) {
    throw new Error("Invalid user payload", { cause: value });
  }
}

const data: unknown = await response.json();
assertIsUser(data);
// data is User from here down
```

### 3. Validation library (for complex schemas)

Libraries like [Zod](https://zod.dev) or [Valibot](https://valibot.dev) derive the TypeScript type *from* the schema, keeping the two in sync automatically:

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
});

type User = z.infer<typeof UserSchema>; // derived — never drifts

const data: unknown = await response.json();
const user = UserSchema.parse(data); // throws ZodError with field-level detail if invalid
```

---

## The pattern in one place

```typescript
async function fetchUser(id: number): Promise<User> {
  const response = await fetch(`/api/users/${id}`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} fetching user ${id}`);
  }

  const data: unknown = await response.json();
  assertIsUser(data); // or UserSchema.parse(data)
  return data;
}
```

---

## Summary

| Type | Safe? | Why |
|------|-------|-----|
| `any` | ❌ | Disables all checks; errors surface at runtime |
| `unknown` | ✅ | Forces narrowing before use; errors surface at compile time |

The rule: **annotate I/O boundaries as `unknown`, then narrow immediately.** The rest of your codebase can work with fully-typed values.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers recommend `unknown`, explain why `any` is problematic, and show narrowing/validation steps. Answer B is slightly superior because it introduces the `asserts x is User` assertion function pattern (a more complete TypeScript idiom), uses `Record<string, unknown>` instead of `any` in the type guard internals (more type-safe), and includes a comparison table that clearly illustrates the tradeoffs. These additions make Answer B more thorough and idiomatic.

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

## The Solution: `unknown`

```typescript
// ✅ Correct approach
const data: unknown = JSON.parse(response);

// TypeScript forces you to narrow the type
if (typeof data === 'object' && data !== null && 'user' in data) {
  console.log(data.user); // Still typed as unknown
}
```

## Why `unknown`?

1. **Type-safe by default** — You must validate before using
2. **Reflects reality** — You don't know the structure until runtime
3. **Prevents bugs** — Catches assumptions about the data

## Practical Pattern: Type Guards

```typescript
interface User {
  name: string;
  age: number;
}

function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'name' in data &&
    typeof (data as any).name === 'string' &&
    'age' in data &&
    typeof (data as any).age === 'number'
  );
}

const data: unknown = JSON.parse(response);
if (isUser(data)) {
  console.log(data.name); // Now safely typed as User
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

**Bottom line:** Use `unknown` for JSON parsing, then validate/narrow to your actual type.

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

// Usage
const data: unknown = JSON.parse(response);
if (isUser(data)) {
  console.log(data.name); // ✅ data is now User
} else {
  throw new Error("Invalid user shape");
}
```

Or use an **assertion function** to throw on failure:

```typescript
function assertIsUser(x: unknown): asserts x is User {
  if (!isUser(x)) {
    throw new Error("Expected User shape");
  }
}

const data: unknown = JSON.parse(response);
assertIsUser(data);
console.log(data.name); // ✅ data is now User
```

## Why This Matters

| Approach | Catches Schema Errors? | Requires Validation? | Type-Safe? |
|---|---|---|---|
| `any` | ❌ No | ❌ No | ❌ No |
| `unknown` + no narrowing | ❌ No | ❌ No | ❌ No |
| `unknown` + type predicate | ✅ Yes | ✅ Yes | ✅ Yes |

The validation code looks verbose, but it's **the cost of safety**. You're explicitly saying: "I don't trust this JSON; here's what I expect." If the server changes the schema, your code fails loudly at the boundary, not deep in your business logic.

## Library Alternative

If you're parsing a lot of JSON, consider a schema validation library like **Zod** or **io-ts**, which generate both runtime validators and TypeScript types:

```typescript
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string(),
});

type User = z.infer<typeof UserSchema>;

const data = UserSchema.parse(JSON.parse(response)); // Throws if invalid
```

But the hand-rolled predicate is the idiomatic TypeScript primitive and works everywhere.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A provides a more detailed hand-rolled type predicate example and explicitly lists anti-patterns to avoid, while Answer B includes a helpful summary table and uses the more modern fetch/response.json() pattern. Both recommend unknown, explain why not any, and show narrowing/validation steps with schema validators.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends unknown | tie |
| explains why not any | tie |
| shows narrowing or validation step | tie |

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
| explains why not any | ✓ | `any` silently disable` |
| shows narrowing or validation step | ✓ | `typeof` |

<details><summary>opus: baseline answer</summary>

# The Correct Type: `unknown`

When you parse JSON from an HTTP response, the result should be typed as **`unknown`**.

```typescript
const response = await fetch('/api/data');
const data: unknown = await response.json();
```

## Why `unknown` and not `any`?

### The problem with `any`
`Response.json()` is typed as `Promise<any>` in the standard lib, which is unsound. `any` disables type checking entirely, so you can do `data.foo.bar.baz()` and TypeScript won't complain — until it explodes at runtime.

### The problem with asserting a specific type
```typescript
const data = await response.json() as User; // 🚨 lying to the compiler
```
You have no actual guarantee the server returned a `User`. This assertion is just a promise to the type system that you can't keep — networks fail, APIs change, attackers send malicious payloads.

### Why `unknown` is right
`unknown` is the type-safe counterpart to `any`. It means "I don't know what this is yet," and TypeScript forces you to **narrow it** before using it:

```typescript
const data: unknown = await response.json();

// ❌ Error: 'data' is of type 'unknown'
console.log(data.name);

// ✅ Must validate first
if (typeof data === 'object' && data !== null && 'name' in data) {
  console.log(data.name);
}
```

## The practical pattern: validate at the boundary

Use a runtime validator (Zod, Valibot, ArkType, io-ts) to convert `unknown` into a trusted, typed value:

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
});
type User = z.infer<typeof UserSchema>;

const raw: unknown = await response.json();
const user: User = UserSchema.parse(raw); // throws if invalid
```

## Summary

| Type | Safety | Recommendation |
|------|--------|----------------|
| `any` | None — silently unsafe | Avoid |
| `User` (asserted) | False sense of safety | Avoid |
| `unknown` | Forces validation | ✅ Use this |

The core principle: **data crossing a trust boundary (network, disk, user input) is `unknown` until proven otherwise.**

</details>

<details><summary>opus: skill-loaded answer</summary>

# Parsed JSON should be `unknown`

```ts
const data: unknown = JSON.parse(text);
```

## Why not `any`?

`JSON.parse` is declared to return `any` in the standard lib, which is the worst possible default: `any` silently disables type checking everywhere it flows. You can write `data.user.name.toUpperCase()` and the compiler won't say a word — until production throws `TypeError: Cannot read properties of undefined`.

## Why `unknown`?

`unknown` is the type-safe counterpart to `any`. It accepts any value (so the assignment from `JSON.parse` works) but the compiler refuses to let you *use* it until you've narrowed it. That forces a validation step at the boundary, which is exactly where validation belongs — JSON from an HTTP response is untrusted input, regardless of what your API contract says.

## Narrowing it

For small ad-hoc shapes, write a type predicate:

```ts
type User = { id: string; name: string };

function isUser(x: unknown): x is User {
  return (
    typeof x === "object" && x !== null &&
    "id" in x && typeof x.id === "string" &&
    "name" in x && typeof x.name === "string"
  );
}

const data: unknown = JSON.parse(text);
if (!isUser(data)) {
  throw new Error("response did not match User shape");
}
// data is User here
```

For anything non-trivial, reach for a schema validator (Zod, Valibot, ArkType, etc.) — they generate the predicate and the type from one declaration and produce far better error messages than hand-rolled checks.

## What to avoid

```ts
const data = JSON.parse(text) as User;        // ❌ lies to the compiler
const data: User = JSON.parse(text);          // ❌ same lie, different syntax
const data: any = JSON.parse(text);           // ❌ poisons everything downstream
```

All three claim a guarantee the runtime hasn't verified. The first two are type assertions that the compiler can't check; the third turns off checking entirely. If the server sends `{ "id": 42, "name": null }` one day, none of these will catch it — but `unknown` + a predicate will.

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

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers are excellent and cover all three rubric criteria thoroughly. Answer A is more comprehensive with migration guidance, scaling examples, and non-string branding examples. Answer B introduces the `unique symbol` approach which is technically superior for avoiding brand collisions, and presents information more concisely with a useful practical tips table. The tradeoff between A's depth and B's technical precision makes this essentially a tie.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends branded types | tie |
| shows __brand or similar phantom property | baseline |
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

This is a classic problem solved with **branded (nominal) types**. TypeScript's type system is structural, so two `string` aliases are identical to it — you need to make them structurally distinct.

### The Pattern

```typescript
// brands.ts
declare const __brand: unique symbol;

type Brand<BaseType, BrandName> = BaseType & {
  readonly [__brand]: BrandName;
};

export type UserId  = Brand<string, "UserId">;
export type OrderId = Brand<string, "OrderId">;
```

The `unique symbol` ensures each brand is truly distinct — even two brands named `"UserId"` in different files won't collide.

---

### Constructor Functions (the only place you cast)

```typescript
// You cast ONCE here, then the type system enforces everywhere else
export const UserId  = (id: string): UserId  => id as UserId;
export const OrderId = (id: string): OrderId => id as OrderId;
```

---

### Usage

```typescript
function getUserById(id: UserId): User { ... }

const userId  = UserId("user-123");
const orderId = OrderId("order-456");

getUserById(userId);   // ✅ OK
getUserById(orderId);  // ❌ Compile error: OrderId is not assignable to UserId
getUserById("raw");    // ❌ Compile error: string is not assignable to UserId
```

---

### With Validation (recommended for untrusted input)

```typescript
// Return the brand only if the value is actually valid
export function parseUserId(raw: string): UserId {
  if (!raw.startsWith("user-")) {
    throw new Error(`Invalid UserId: ${raw}`);
  }
  return raw as UserId;
}

// Or with a Result type if you prefer not to throw
export function tryParseUserId(raw: string): UserId | null {
  return raw.startsWith("user-") ? (raw as UserId) : null;
}
```

---

### Practical Tips

| Situation | Recommendation |
|---|---|
| Database layer | Cast at the query boundary, return branded types |
| API input | Parse/validate at the controller, brand immediately |
| Tests | Use the constructor functions, not raw `as` casts |
| Serialization | Branded types serialize normally — no runtime cost |

---

### Key Properties

- **Zero runtime cost** — brands are purely compile-time
- **Assignability is one-way** — `UserId` can't be used as `OrderId` or plain `string` without an explicit cast
- **Plain `string` is rejected** — you can't accidentally pass an unbranded string either
- **`as` casts are your seam** — grep for `as UserId` / `as OrderId` to audit all trust boundaries

The core idea: **cast once at the boundary, let the type system enforce everywhere else.**

</details>

<details><summary>sonnet: skill-loaded answer</summary>

This is the classic "stringly-typed" problem. The fix is **branded types** (also called nominal types or opaque types) — you add a phantom property to the type so that `UserId` and `OrderId` are structurally distinct, even though they're both `string` at runtime.

## The Pattern

```typescript
type Brand<Base, Tag extends string> = Base & { readonly __brand: Tag };

type UserId  = Brand<string, "UserId">;
type OrderId = Brand<string, "OrderId">;
```

The `__brand` property never exists at runtime — it's purely a compile-time fiction. But it's enough to make the two types incompatible:

```typescript
function getUser(id: UserId): User { ... }

declare const orderId: OrderId;
getUser(orderId);
// ❌ Argument of type 'OrderId' is not assignable to parameter of type 'UserId'.
//    Types of property '__brand' are incompatible.
```

## Creating Values: Smart Constructors

You can't write `"abc" as UserId` everywhere — that defeats the purpose. Instead, create values through constructor functions that validate (or at least assert) the input:

```typescript
function toUserId(raw: string): UserId {
  if (!raw.startsWith("usr_")) {
    throw new Error(`Invalid UserId: ${raw}`);
  }
  return raw as UserId; // the ONE place the cast lives
}

function toOrderId(raw: string): OrderId {
  if (!raw.startsWith("ord_")) {
    throw new Error(`Invalid OrderId: ${raw}`);
  }
  return raw as OrderId;
}
```

The `as` cast is intentionally confined to these constructors. Every other call site uses the typed value directly — no casting needed.

If you don't have a meaningful validation rule yet, a simple assertion constructor is still worth it to centralize the cast:

```typescript
const toUserId  = (raw: string) => raw as UserId;
const toOrderId = (raw: string) => raw as OrderId;
```

## Putting It Together

```typescript
type Brand<Base, Tag extends string> = Base & { readonly __brand: Tag };

type UserId  = Brand<string, "UserId">;
type OrderId = Brand<string, "OrderId">;

const toUserId  = (raw: string): UserId  => raw as UserId;
const toOrderId = (raw: string): OrderId => raw as OrderId;

function getUser(id: UserId): string {
  return `user:${id}`;
}

const uid = toUserId("usr_123");
const oid = toOrderId("ord_456");

getUser(uid); // ✅
getUser(oid); // ❌ compile error — caught!
getUser("usr_123"); // ❌ also caught — raw strings don't pass either
```

That last line is a bonus: raw `string` literals are also rejected, so you can't accidentally skip the constructor.

## Scaling Up

Once you have the `Brand` helper, new ID types are one-liners:

```typescript
type ProductId  = Brand<string, "ProductId">;
type CustomerId = Brand<string, "CustomerId">;
```

You can also brand non-string types — a `PositiveNumber`, a `NonEmptyArray<T>`, a `ValidatedEmail`:

```typescript
type PositiveNumber = Brand<number, "PositiveNumber">;

function toPositiveNumber(n: number): PositiveNumber {
  if (n <= 0) throw new Error(`Expected positive number, got ${n}`);
  return n as PositiveNumber;
}
```

## Migration Path

You don't have to change everything at once. The types are still `string` at runtime, so you can:

1. Define the branded types and constructors.
2. Update function signatures to use `UserId` / `OrderId`.
3. Fix call sites one file at a time — the compiler will point you to every mismatch.

The existing bug you described would have been a compile error from step 2 onward.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend branded types with a `__brand` phantom property and explain structural typing as the root cause. Answer B is more thorough and educational: it explains *why* the intersection type works (phantom property never exists at runtime), covers validation at boundaries, extraction of raw values, additional use cases like units of measurement, and includes guidance on when not to overuse the pattern. Answer A is solid but more surface-level, while B provides deeper understanding and practical guidance.

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

```typescript
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

// Helper functions to create branded types safely
const UserId = (id: string): UserId => id as UserId;
const OrderId = (id: string): OrderId => id as OrderId;

// Now TypeScript catches the error
function processUser(userId: UserId) {
  console.log(userId);
}

const orderId = OrderId("order-123");
const userId = UserId("user-456");

processUser(userId);        // ✅ OK
processUser(orderId);       // ❌ Type error!
```

## 2. **Opaque Types (More Robust)**

```typescript
declare const __brand: unique symbol;

type UserId = string & { [__brand]: "UserId" };
type OrderId = string & { [__brand]: "OrderId" };

const UserId = (id: string): UserId => id as UserId;
const OrderId = (id: string): OrderId => id as OrderId;
```

## 3. **Class-Based (Most Explicit)**

```typescript
class UserId {
  constructor(readonly value: string) {}
}

class OrderId {
  constructor(readonly value: string) {}
}

function processUser(userId: UserId) {
  console.log(userId.value);
}

processUser(new OrderId("order-123")); // ❌ Type error!
processUser(new UserId("user-456"));   // ✅ OK
```

## Comparison

| Approach | Runtime Overhead | Ergonomics | Type Safety |
|----------|------------------|-----------|-------------|
| Branded | None | Good | Excellent |
| Opaque | None | Good | Excellent |
| Class | Small | Verbose | Excellent |

**I'd recommend branded types** — they're zero-cost abstractions with great ergonomics.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Branded Types for Distinct Primitives

You need **branded types** (also called "opaque types" or "nominal types"). They let you create distinct types from the same primitive while staying structurally sound.

## The Solution

```typescript
// Define the brands
type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

// Helper functions to create branded values safely
function createUserId(value: string): UserId {
  return value as UserId;
}

function createOrderId(value: string): OrderId {
  return value as OrderId;
}

// Now the function signature is type-safe
function getUser(id: UserId): User {
  // ...
}

function getOrder(id: OrderId): Order {
  // ...
}

// ✅ This works
const userId = createUserId("user-123");
getUser(userId);

// ❌ This is a compile error
const orderId = createOrderId("order-456");
getUser(orderId); // Type 'OrderId' is not assignable to type 'UserId'
```

## Why This Works

- **`string & { readonly __brand: "UserId" }`** is an intersection type. At runtime, it's just a string (the `__brand` property is never actually added). At compile time, TypeScript treats `UserId` and `OrderId` as distinct types.
- **The `__brand` field is `readonly`** so you can't accidentally construct it by hand.
- **The helper functions (`createUserId`, `createOrderId`)** are the only safe way to create branded values. They document intent and are where you'd add validation if needed.

## Validation at Boundaries

If you're parsing IDs from JSON or a database, add validation:

```typescript
function createUserIdFromString(value: unknown): UserId {
  if (typeof value !== "string" || !value.startsWith("user-")) {
    throw new Error(`Invalid UserId: ${value}`);
  }
  return value as UserId;
}

function createOrderIdFromString(value: unknown): OrderId {
  if (typeof value !== "string" || !value.startsWith("order-")) {
    throw new Error(`Invalid OrderId: ${value}`);
  }
  return value as OrderId;
}
```

## Extracting the Raw Value

When you need to pass the ID to an API or database, extract the raw string:

```typescript
function sendToDatabase(userId: UserId) {
  const rawId: string = userId; // Branded types are assignable to their base
  db.query("SELECT * FROM users WHERE id = ?", [rawId]);
}
```

## Multiple Brands on the Same Primitive

You can brand `number`, `bigint`, or any primitive:

```typescript
type Milliseconds = number & { readonly __brand: "Milliseconds" };
type Seconds = number & { readonly __brand: "Seconds" };

function sleep(ms: Milliseconds): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ❌ Compile error: Seconds is not assignable to Milliseconds
sleep(5 as Seconds);

// ✅ Correct
sleep(5000 as Milliseconds);
```

## When to Use Branded Types

- **Domain-distinct IDs** (`UserId`, `OrderId`, `ProductId`) — the most common case
- **Units of measurement** (`Milliseconds`, `Pixels`, `Kilobytes`) — prevents mixing incompatible units
- **Validated strings** (`Email`, `PhoneNumber`, `Slug`) — the brand documents that validation has happened
- **Semantic distinctions** (`Percentage` vs `Ratio`, `Absolute` vs `Relative`) — prevents subtle logic errors

**Don't overuse them.** If you have 20 different ID types, the overhead of helper functions becomes tedious. But for the high-risk ones (user/order/product IDs), the safety is worth it.

## Alternative: Nominal Classes

If you prefer a more explicit approach, use a class:

```typescript
class UserId {
  constructor(readonly value: string) {}
}

class OrderId {
  constructor(readonly value: string) {}
}

// Now they're genuinely distinct types
getUser(new UserId("user-123")); // ✅
getUser(new OrderId("order-456")); // ❌ Compile error
```

This is heavier (you create objects at runtime) but more explicit. Pick whichever fits your codebase's style.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly recommend branded types with a __brand phantom property and explain structural typing as the root cause. Answer A is more thorough and practical, covering validation at boundaries, ESLint enforcement, a reusable Brand helper, runtime behavior, and concrete guidance on when to brand. Answer B introduces a nice touch with `unique symbol` for the brand field but is otherwise less comprehensive. Overall A provides more actionable depth.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| recommends branded types | tie |
| shows __brand or similar phantom property | baseline |
| explains structural typing as the cause | skill |

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

<details><summary>opus: baseline answer</summary>

# Branded Types: Preventing ID Mix-ups

This is a classic problem with "stringly-typed" code. The solution is **branded types** (also called nominal types or opaque types). They let you make TypeScript treat two structurally identical types as distinct.

## The Pattern

```typescript
type Brand<T, B> = T & { readonly __brand: B };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
```

The `__brand` field doesn't actually exist at runtime — it's a phantom property used purely for compile-time type checking. At runtime, these are still just strings.

## Constructors

Since you can't directly assign a `string` to a `UserId` anymore, you need constructor functions:

```typescript
function UserId(id: string): UserId {
  // optionally validate here
  return id as UserId;
}

function OrderId(id: string): OrderId {
  return id as OrderId;
}
```

## Usage

```typescript
function getUser(id: UserId) { /* ... */ }

const userId = UserId('user-123');
const orderId = OrderId('order-456');

getUser(userId);  // ✅ ok
getUser(orderId); // ❌ Argument of type 'OrderId' is not assignable to 'UserId'
getUser('user-123'); // ❌ also blocked — must go through constructor
```

## A Reusable Helper

You can generalize this so you don't repeat yourself:

```typescript
declare const __brand: unique symbol;
type Brand<T, B> = T & { readonly [__brand]: B };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
```

Using `unique symbol` makes the brand field essentially unforgeable.

## Where to Apply It

Practical advice:

- **Boundaries matter most.** Brand IDs at the point they enter your system (DB layer, API parsing). Once branded, they flow through the rest of the codebase safely.
- **Validate in the constructor.** Since you're already wrapping the value, you can also enforce format (e.g. UUID, prefix check) in one place.
- **Apply to other primitives too.** `Email`, `Cents`, `Milliseconds`, `SafeHtml` — anywhere a raw `string` or `number` could be confused with another.

## Trade-offs

- **Zero runtime cost** — the brand disappears in compiled JS.
- You'll need `as UserId` casts at the boundaries; concentrate them in constructors.
- Third-party libraries returning `string` will need a wrap call to enter your branded world.

If you want stricter ergonomics (e.g. forbidding accidental implicit casts even within your own code), libraries like [`ts-brand`](https://github.com/kourge/ts-brand) or zod's `.brand()` API give you the same pattern with a bit more polish.

</details>

<details><summary>opus: skill-loaded answer</summary>

You want **branded types** (also called nominal types or opaque types). They make `UserId` and `OrderId` structurally distinct even though both are `string` at runtime.

## The pattern

```ts
// Define the brands
export type UserId = string & { readonly __brand: "UserId" };
export type OrderId = string & { readonly __brand: "OrderId" };

// Constructors (the only way to create one)
export const UserId = (s: string): UserId => s as UserId;
export const OrderId = (s: string): OrderId => s as OrderId;
```

The `& { readonly __brand: "..." }` intersection adds a phantom property that exists only in the type system — at runtime these are still plain strings, zero overhead. Because the brand strings differ, `UserId` and `OrderId` are no longer assignable to each other.

## How it catches your bug

```ts
function getUser(id: UserId) { /* ... */ }

const orderId = OrderId("ord_123");
getUser(orderId);
// ✗ Argument of type 'OrderId' is not assignable to parameter of type 'UserId'.
//   Type '"OrderId"' is not assignable to type '"UserId"'.

const userId = UserId("usr_456");
getUser(userId); // ✓
```

Raw strings are also rejected:

```ts
getUser("usr_456");
// ✗ Argument of type 'string' is not assignable to parameter of type 'UserId'.
```

This is the key win — you can no longer accidentally pass a plain string from `req.params.id` or a database row without going through the constructor, which is your one chokepoint for validation.

## Validating at the boundary

The constructor is where you parse/validate untrusted input once, then trust the type everywhere downstream:

```ts
export const UserId = (s: string): UserId => {
  if (!/^usr_[a-z0-9]+$/.test(s)) {
    throw new Error(`invalid UserId: ${s}`);
  }
  return s as UserId;
};
```

Now anywhere a `UserId` appears in a type signature, you know it has been validated. The `as` cast is contained to this one function — that's the trade. Outside the constructor, no `as UserId` should appear in your codebase (consider an ESLint rule).

## A reusable helper

If you have many branded types, factor it:

```ts
type Brand<T, B extends string> = T & { readonly __brand: B };

export type UserId   = Brand<string, "UserId">;
export type OrderId  = Brand<string, "OrderId">;
export type Email    = Brand<string, "Email">;
export type Cents    = Brand<number, "Cents">; // works for numbers too
```

## Things to know

- **Runtime cost: zero.** The brand is erased; serialization (`JSON.stringify`) treats them as their underlying type.
- **Deserialization re-validates.** When data comes back from JSON/DB, run it through the constructor again — the type was lost on the wire.
- **Pick one brand-property name and stick with it** (`__brand`, `_tag`, whatever) so different branded types don't accidentally become assignable through structural matching on a different property.
- **Don't over-brand.** Brand things that are genuinely confusable (different ID kinds, validated vs unvalidated strings, units like `Cents` vs `Dollars`). Branding every string is noise.

Drop this in and the OrderId-to-UserId bug becomes a compile error.

</details>

---

### `abortsignal-cancellation`

**Prompt**

```
I have an async TypeScript function that fetches data in chunks
and may take a few minutes. I want callers to be able to cancel
it mid-flight. What's the modern, idiomatic way to expose this?
```

**Judge focus:** The better answer accepts an AbortSignal parameter, propagates
it into inner awaitable calls (fetch, child operations), and
checks for abort at suspension points (signal.throwIfAborted()
or by listening to 'abort'). It does not invent a custom
cancellation token type or rely on a boolean flag.

#### `sonnet`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use AbortSignal, propagate it into inner calls, and check at suspension points. However, Answer B demonstrates more sophisticated patterns like AbortSignal.any() for composing multiple signals, uses optional signal parameters (more ergonomic), shows an AsyncGenerator pattern that more naturally represents chunked streaming, includes the ASCII diagram showing signal flow, and covers the already-aborted fast-path check on entry. Answer B is slightly more idiomatic and complete in its treatment of real-world usage patterns.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| accepts an AbortSignal parameter | tie |
| forwards signal into inner async calls | tie |
| checks for abort at suspension points | skill |
| avoids inventing a custom cancellation token | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| accepts an AbortSignal parameter | ✓ | `signal: AbortSignal` |
| forwards signal into inner async calls | ✓ | `fetch(url, { signal` |
| checks for abort at suspension points | ✓ | `throwIfAborted` |
| avoids inventing a custom cancellation token | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| accepts an AbortSignal parameter | ✓ | `signal?: AbortSignal` |
| forwards signal into inner async calls | ✓ | `fetch(url, { signal` |
| checks for abort at suspension points | ✓ | `throwIfAborted` |
| avoids inventing a custom cancellation token | ✓ | |

<details><summary>sonnet: baseline answer</summary>

## Cancellable Async Functions in TypeScript

The modern, idiomatic approach is to use the **Web API's `AbortController` / `AbortSignal`**. This is the same mechanism used by `fetch()`, Node.js streams, and most modern browser/Node APIs.

---

### Basic Pattern

```typescript
async function fetchInChunks(
  url: string,
  signal: AbortSignal,          // caller passes this in
): Promise<string[]> {
  const results: string[] = [];

  while (true) {
    // 1. Check before each unit of work
    signal.throwIfAborted();    // throws AbortError if cancelled

    const chunk = await fetchNextChunk(url, signal); // pass down too
    if (!chunk) break;

    results.push(chunk);
  }

  return results;
}
```

```typescript
// Caller
const controller = new AbortController();

// Cancel after 30 seconds
const timeout = setTimeout(() => controller.abort("Timed out"), 30_000);

try {
  const data = await fetchInChunks("https://example.com/data", controller.signal);
  console.log(data);
} catch (err) {
  if (err instanceof Error && err.name === "AbortError") {
    console.log("Cancelled:", err.message);
  } else {
    throw err; // re-throw unexpected errors
  }
} finally {
  clearTimeout(timeout);
}

// Cancel manually at any time:
controller.abort("User cancelled");
```

---

### Real-World Example with `fetch`

```typescript
async function fetchInChunks(
  baseUrl: string,
  signal: AbortSignal,
): Promise<string[]> {
  const results: string[] = [];
  let cursor: string | null = null;

  do {
    signal.throwIfAborted();

    const url = cursor ? `${baseUrl}?cursor=${cursor}` : baseUrl;

    // fetch() natively respects AbortSignal
    const response = await fetch(url, { signal });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const { data, nextCursor } = await response.json();
    results.push(...data);
    cursor = nextCursor ?? null;

  } while (cursor !== null);

  return results;
}
```

---

### Handling Cancellation During Non-`fetch` Async Work

If you're doing CPU work or using APIs that **don't** accept a signal, use `signal.throwIfAborted()` as a checkpoint, or wrap with a race:

```typescript
// Helper: makes any promise cancellable
function withAbort<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted(); // fast-path if already aborted

    signal.addEventListener("abort", () => {
      reject(signal.reason); // signal.reason is what was passed to abort()
    }, { once: true });

    promise.then(resolve, reject);
  });
}

// Usage inside your chunked function
const chunk = await withAbort(someThirdPartyAsyncCall(), signal);
```

---

### Exposing a Clean Public API

If you want to **hide** the controller from callers and return a handle:

```typescript
interface FetchHandle {
  result: Promise<string[]>;
  cancel: (reason?: string) => void;
}

function startFetchInChunks(url: string): FetchHandle {
  const controller = new AbortController();

  return {
    result: fetchInChunks(url, controller.signal),
    cancel: (reason) => controller.abort(reason ?? "Cancelled"),
  };
}

// Caller
const handle = startFetchInChunks("https://example.com/data");
const data = await handle.result;

// Or cancel:
handle.cancel("User navigated away");
```

---

### Key Rules

| Rule | Why |
|---|---|
| Accept `signal`, don't create it | Callers compose multiple signals (timeout + manual) |
| Use `signal.throwIfAborted()` at loop boundaries | Ensures prompt cancellation between awaits |
| Pass `signal` to every nested `fetch`/API call | Cancels I/O immediately, not just between chunks |
| Check `err.name === "AbortError"` not `instanceof` | `AbortError` can come from different realms |
| Use `AbortSignal.timeout(ms)` for simple timeouts | Built-in, no manual `setTimeout` cleanup needed |

```typescript
// Built-in timeout signal (no cleanup needed)
const signal = AbortSignal.timeout(30_000);
const data = await fetchInChunks(url, signal);
```

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The modern, idiomatic answer is **`AbortSignal`** — the same primitive browsers and Node.js use for `fetch`, `setTimeout`, streams, and everything else. You don't invent a cancellation protocol; you plug into the one that already exists.

## The core pattern

```typescript
async function fetchInChunks(
  url: string,
  signal?: AbortSignal,   // optional so callers who don't need cancellation aren't burdened
): Promise<Chunk[]> {
  const results: Chunk[] = [];

  for await (const chunk of streamChunks(url, signal)) {
    signal?.throwIfAborted();   // ← check at every suspension point
    results.push(chunk);
  }

  return results;
}
```

`signal.throwIfAborted()` throws an `AbortError` if the signal has already fired. Call it at the top of every loop iteration — right after the `await` that just resumed — so cancellation is noticed promptly rather than after the next network round-trip completes.

## Wiring up the caller

```typescript
const controller = new AbortController();

// Cancel after 30 s, or on user action
const timeoutSignal = AbortSignal.timeout(30_000);
const signal = AbortSignal.any([controller.signal, timeoutSignal]);

// Start the work
const promise = fetchInChunks("https://example.com/data", signal);

// Cancel from elsewhere (button click, route change, etc.)
cancelButton.addEventListener("click", () => controller.abort("user cancelled"));

try {
  const chunks = await promise;
  // ...
} catch (e) {
  if (e instanceof Error && e.name === "AbortError") {
    console.log("Cancelled:", controller.signal.reason);
  } else {
    throw e;   // re-throw genuine errors
  }
}
```

`AbortSignal.any([...])` merges multiple signals — the combined signal fires as soon as *any* of them does. This is how you compose "user cancel OR timeout OR parent cancelled" without any extra machinery.

## Propagating the signal to nested I/O

Pass `signal` to every async call that accepts one. Most modern APIs do:

```typescript
async function* streamChunks(
  url: string,
  signal?: AbortSignal,
): AsyncGenerator<Chunk> {
  const response = await fetch(url, { signal });   // fetch respects AbortSignal natively

  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();

  try {
    while (true) {
      signal?.throwIfAborted();                    // check before each read
      const { done, value } = await reader.read(); // also interrupted by signal via fetch
      if (done) break;
      yield parseChunk(value);
    }
  } finally {
    reader.releaseLock();                          // always clean up, even on cancellation
  }
}
```

The `finally` block is your cleanup guarantee — it runs whether the function returns normally, throws, or is aborted.

## Handling already-aborted signals

If a caller passes in a signal that's *already* fired (e.g., they cancelled before calling you), you want to fail immediately rather than start work:

```typescript
async function fetchInChunks(
  url: string,
  signal?: AbortSignal,
): Promise<Chunk[]> {
  signal?.throwIfAborted();   // ← fail fast if cancelled before we even start

  const results: Chunk[] = [];
  for await (const chunk of streamChunks(url, signal)) {
    signal?.throwIfAborted();
    results.push(chunk);
  }
  return results;
}
```

## The complete picture

```
Caller
  │  creates AbortController
  │  AbortSignal.any([controller.signal, AbortSignal.timeout(30_000)])
  │
  ▼
fetchInChunks(url, signal)
  │  signal?.throwIfAborted()          ← check on entry
  │
  └─► streamChunks(url, signal)
        │  fetch(url, { signal })      ← propagate to I/O
        │  signal?.throwIfAborted()    ← check before each read
        │  yield chunk
        │  finally: reader.releaseLock()
        ▼
  │  signal?.throwIfAborted()          ← check after each yield resumes
  │  results.push(chunk)
  ▼
return results  (or AbortError propagates up)
```

## Why not a custom `isCancelled` flag or a `CancellationToken`?

- `AbortSignal` composes with `fetch`, `addEventListener`, `setTimeout` (via `AbortSignal.timeout`), streams, and any other API that accepts it — a custom flag doesn't.
- `AbortSignal.any` lets you merge signals from multiple sources for free.
- Callers already know how to use it; it's the platform standard.
- `throwIfAborted()` gives you a real `AbortError` with a `.reason`, not a boolean you have to check and convert yourself.

The only time you'd reach for something else is if you need *cooperative* cancellation with cleanup steps that must complete before the function returns — in that case, you'd still use `AbortSignal` to *detect* cancellation, but you'd catch the `AbortError` internally, run cleanup, then re-throw.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B is more idiomatic and complete: it uses `signal?.throwIfAborted()` (the modern, preferred API) rather than manually checking `signal.aborted` and throwing a DOMException, it demonstrates `AbortSignal.timeout()` and `AbortSignal.any()` for advanced composition, and it consistently propagates the signal through nested async calls. Answer A checks `signal.aborted` manually and throws a DOMException by hand, which is the older pattern that `throwIfAborted()` was designed to replace.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| accepts an AbortSignal parameter | tie |
| forwards signal into inner async calls | tie |
| checks for abort at suspension points | skill |
| avoids inventing a custom cancellation token | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| accepts an AbortSignal parameter | ✓ | `signal: AbortSignal` |
| forwards signal into inner async calls | ✓ | `fetch(`/api/chunk/${index}`, { signal` |
| checks for abort at suspension points | ✓ | `signal.aborted` |
| avoids inventing a custom cancellation token | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| accepts an AbortSignal parameter | ✓ | `signal?: AbortSignal` |
| forwards signal into inner async calls | ✓ | `fetch(`${url}?offset=${offset}`, { signal` |
| checks for abort at suspension points | ✓ | `throwIfAborted` |
| avoids inventing a custom cancellation token | ✓ | |

<details><summary>haiku: baseline answer</summary>

# Cancellation with AbortController

The modern, idiomatic way is to use **AbortController** and **AbortSignal**:

```typescript
async function fetchDataInChunks(signal: AbortSignal): Promise<Data[]> {
  const results: Data[] = [];
  
  for (let i = 0; i < totalChunks; i++) {
    // Check if cancellation was requested
    if (signal.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }
    
    const chunk = await fetchChunk(i, signal);
    results.push(...chunk);
  }
  
  return results;
}

// Usage
const controller = new AbortController();

// Start the operation
const promise = fetchDataInChunks(controller.signal);

// Cancel it later
controller.abort();

try {
  await promise;
} catch (error) {
  if (error instanceof DOMException && error.name === 'AbortError') {
    console.log('Operation was cancelled');
  }
}
```

## Key Points

**Pass the signal to nested operations:**
```typescript
async function fetchChunk(index: number, signal: AbortSignal): Promise<Data[]> {
  const response = await fetch(`/api/chunk/${index}`, { signal });
  return response.json();
}
```

**Listen for abort events:**
```typescript
signal.addEventListener('abort', () => {
  console.log('Cancellation requested');
});
```

**Check before long operations:**
```typescript
if (signal.aborted) {
  throw new DOMException('Aborted', 'AbortError');
}
```

## Why AbortController?

- ✅ Standard Web API (works in Node.js 15+, all modern browsers)
- ✅ Works with `fetch()`, streams, and custom code
- ✅ Composable (can pass same signal to multiple operations)
- ✅ Automatic cleanup (no manual listener removal needed)
- ✅ Better than custom callbacks or Promise rejection patterns

This is what the Fetch API, Node.js streams, and most modern libraries use.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Cancellation with `AbortSignal`

Use `AbortSignal` as a parameter. It's the standard web API for cancellation and composes cleanly with other async operations.

## Basic Pattern

```typescript
async function fetchDataInChunks(
  url: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const chunks: string[] = [];
  let offset = 0;

  while (offset < totalSize) {
    // Check for cancellation at suspension points
    signal?.throwIfAborted();

    const chunk = await fetch(`${url}?offset=${offset}`, { signal });
    chunks.push(await chunk.text());
    offset += chunkSize;
  }

  return chunks;
}
```

**Key points:**
- Accept `signal?: AbortSignal` as a parameter
- Pass it to any nested async operations (`fetch`, `setTimeout`, etc.)
- Call `signal?.throwIfAborted()` at suspension points (before `await`, in loops)
- When the signal is aborted, `throwIfAborted()` throws an `AbortError`

## Caller Usage

```typescript
// Create an AbortController
const controller = new AbortController();

// Start the fetch
const promise = fetchDataInChunks("https://api.example.com/data", controller.signal);

// Cancel after 30 seconds
const timeout = setTimeout(() => controller.abort(), 30_000);

try {
  const data = await promise;
  console.log("Done:", data);
} catch (e) {
  if (e instanceof DOMException && e.name === "AbortError") {
    console.log("Cancelled");
  } else {
    throw e;
  }
} finally {
  clearTimeout(timeout);
}
```

Or with a timeout helper:

```typescript
const controller = AbortSignal.timeout(30_000); // Aborts after 30s
try {
  const data = await fetchDataInChunks("https://api.example.com/data", controller);
} catch (e) {
  if (e instanceof DOMException && e.name === "AbortError") {
    console.log("Timed out");
  }
}
```

## Propagating Through Nested Calls

If your function calls other async functions, pass the signal through:

```typescript
async function fetchDataInChunks(
  url: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const chunks: string[] = [];

  for (let i = 0; i < numChunks; i++) {
    signal?.throwIfAborted();

    // Pass signal to nested fetch
    const response = await fetch(`${url}?chunk=${i}`, { signal });
    
    // Pass signal to nested async function
    const processed = await processChunk(response, signal);
    chunks.push(processed);
  }

  return chunks;
}

async function processChunk(response: Response, signal?: AbortSignal): Promise<string> {
  signal?.throwIfAborted();
  const text = await response.text();
  // ... processing ...
  return text;
}
```

## Combining Multiple Signals

If you have multiple cancellation sources (user abort + timeout), use `AbortSignal.any`:

```typescript
const userController = new AbortController();
const timeoutSignal = AbortSignal.timeout(30_000);

const combinedSignal = AbortSignal.any([
  userController.signal,
  timeoutSignal,
]);

try {
  const data = await fetchDataInChunks("https://api.example.com/data", combinedSignal);
} catch (e) {
  if (e instanceof DOMException && e.name === "AbortError") {
    console.log("Cancelled or timed out");
  }
}
```

## Handling Abort in Event Listeners

If you're using event listeners (not just `await`), listen for the abort event:

```typescript
async function fetchDataInChunks(
  url: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const chunks: string[] = [];

  return new Promise((resolve, reject) => {
    const onAbort = () => {
      reject(new DOMException("Aborted", "AbortError"));
    };

    signal?.addEventListener("abort", onAbort);

    // ... async work ...

    signal?.removeEventListener("abort", onAbort);
    resolve(chunks);
  });
}
```

## Why `AbortSignal`?

- **Standard API** — works across `fetch`, `setTimeout`, `AbortController`, and custom async code
- **Composable** — `AbortSignal.any` combines multiple sources
- **No callback hell** — integrates cleanly with `async`/`await`
- **Timeout built-in** — `AbortSignal.timeout(ms)` is simpler than manual `setTimeout`
- **Works everywhere** — Node.js, browsers, Deno, Bun all support it

See [Async & Cancellation](references/async-and-cancellation.md) for more patterns.

</details>

#### `opus`

**Met:** ✓  ·  **Judge:** **skill** — Both answers are excellent and cover all four rubric criteria well. Answer A edges out B with its more thorough treatment of signal propagation (explicitly mentioning not re-implementing cancellation on top of existing APIs), its clear guidance on not swallowing AbortErrors in retry logic, and its use of AbortSignal.timeout() as a convenience constructor. Answer A also provides a slightly more complete and polished explanation of the AbortSignal.any() composition pattern with concrete code.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| accepts an AbortSignal parameter | tie |
| forwards signal into inner async calls | skill |
| checks for abort at suspension points | tie |
| avoids inventing a custom cancellation token | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| accepts an AbortSignal parameter | ✓ | `signal?: AbortSignal` |
| forwards signal into inner async calls | ✓ | `fetch(`${url}?page=${page}`, { signal` |
| checks for abort at suspension points | ✓ | `throwIfAborted` |
| avoids inventing a custom cancellation token | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| accepts an AbortSignal parameter | ✓ | `signal?: AbortSignal` |
| forwards signal into inner async calls | ✓ | `fetch(`${url}?cursor=${cursor ?? ""}`, { signal` |
| checks for abort at suspension points | ✓ | `throwIfAborted` |
| avoids inventing a custom cancellation token | ✓ | |

<details><summary>opus: baseline answer</summary>

# Cancellation in Async TypeScript: Use `AbortSignal`

The modern, idiomatic pattern is to accept an `AbortSignal` parameter, mirroring the Web Platform conventions used by `fetch`, `setTimeout`, streams, etc.

## Basic Shape

```ts
interface FetchOptions {
  signal?: AbortSignal;
}

async function fetchInChunks<T>(
  url: string,
  opts: FetchOptions = {}
): Promise<T[]> {
  const { signal } = opts;
  const results: T[] = [];

  for (let page = 0; ; page++) {
    // 1. Throw early if already cancelled
    signal?.throwIfAborted();

    // 2. Forward the signal to anything that supports it
    const res = await fetch(`${url}?page=${page}`, { signal });
    const chunk = (await res.json()) as { items: T[]; done: boolean };

    results.push(...chunk.items);
    if (chunk.done) break;
  }

  return results;
}
```

## Caller Side

```ts
const ac = new AbortController();

// Cancel after 30 seconds, or on a button click, etc.
setTimeout(() => ac.abort(new Error("User gave up")), 30_000);

try {
  const data = await fetchInChunks("/api/things", { signal: ac.signal });
} catch (err) {
  if (ac.signal.aborted) {
    // handled cancellation
  } else {
    throw err;
  }
}
```

## Key Points

1. **Accept `AbortSignal`, don’t invent your own API.** Every modern Node and browser API understands it (`fetch`, `setTimeout`, `events.on`, streams, etc.).

2. **Use `signal.throwIfAborted()`** at chunk boundaries. It throws an `AbortError` (a `DOMException` whose `.name === "AbortError"`) — the standard contract callers expect.

3. **Forward the signal downstream** to `fetch` and any other cancellable operation. Don’t just check it; let underlying I/O actually stop.

4. **For cleanup, use `signal.addEventListener("abort", …)`** — useful if you need to close a stream, release a lock, or reject a manually-constructed promise:

   ```ts
   await new Promise<void>((resolve, reject) => {
     const onAbort = () => reject(signal!.reason);
     signal?.addEventListener("abort", onAbort, { once: true });
     doWork().then(resolve, reject).finally(() =>
       signal?.removeEventListener("abort", onAbort)
     );
   });
   ```

5. **Combine signals** with `AbortSignal.any([sig1, sig2])` (Node ≥20, modern browsers) when you want both a timeout *and* a user-cancel:

   ```ts
   const signal = AbortSignal.any([userSignal, AbortSignal.timeout(60_000)]);
   ```

6. **Detecting cancellation in catch blocks**: prefer `signal.aborted` or `err?.name === "AbortError"` over instanceof checks (the class differs between Node and browsers).

## What to avoid

- A custom `cancel()` method on a returned object — non-standard and doesn’t compose.
- A boolean `cancelled` flag the caller mutates — racy and can’t interrupt in-flight I/O.
- Returning a `CancelablePromise` library type — was popular pre-`AbortController`, now obsolete.

`AbortSignal` is the lingua franca; use it and your function will compose cleanly with everything else in the ecosystem.

</details>

<details><summary>opus: skill-loaded answer</summary>

# Cancellation with `AbortSignal`

The modern, idiomatic way is to accept an optional `AbortSignal` parameter, propagate it to nested async work, and check for cancellation at every suspension point. This is the same primitive `fetch`, `setTimeout` (Node 16+), and the streams APIs all use — so your function composes naturally with the rest of the ecosystem.

## The pattern

```typescript
async function fetchAllChunks(
  url: string,
  options: { signal?: AbortSignal } = {},
): Promise<Chunk[]> {
  const { signal } = options;
  signal?.throwIfAborted(); // fail fast if already aborted

  const chunks: Chunk[] = [];
  let cursor: string | undefined;

  do {
    // Propagate signal to fetch — it will reject with AbortError on abort
    const response = await fetch(`${url}?cursor=${cursor ?? ""}`, { signal });
    const page = (await response.json()) as { items: Chunk[]; next?: string };

    chunks.push(...page.items);
    cursor = page.next;

    // Check between iterations in case the inner work doesn't accept a signal
    signal?.throwIfAborted();
  } while (cursor);

  return chunks;
}
```

## Caller side

```typescript
const controller = new AbortController();

// Cancel after 30s, or on a button click, or on shutdown, etc.
const timeoutId = setTimeout(() => controller.abort(), 30_000);

try {
  const chunks = await fetchAllChunks("https://api.example.com/data", {
    signal: controller.signal,
  });
  // use chunks
} catch (e: unknown) {
  if (e instanceof Error && e.name === "AbortError") {
    // expected — caller cancelled
    return;
  }
  throw e;
} finally {
  clearTimeout(timeoutId);
}
```

## Key rules

- **Accept `signal?: AbortSignal` as part of an options object**, not a positional parameter — it's almost always optional, and an options bag keeps the call site readable as more options accrete.
- **Call `signal?.throwIfAborted()` at every `await` boundary** where the inner call doesn't natively accept a signal. For loops, check once per iteration. The cost is negligible; the alternative is a function that "cancels" but keeps running for another minute.
- **Propagate the signal to every nested async call that accepts one** — `fetch`, `setTimeout` (with `{ signal }`), `ReadableStream`, child processes, etc. Don't re-implement cancellation on top of these; pass the signal through.
- **Throw on abort, don't return a sentinel.** `throwIfAborted()` throws a `DOMException` with `name === "AbortError"`. This is the convention every web/Node API follows; callers know to check for it.
- **Don't swallow the abort in your own `catch`.** If you have a `try`/`catch` for retry logic, re-throw aborts immediately:
  ```typescript
  catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") throw e;
    // ...retry logic
  }
  ```

## Composing multiple signals

If your function has its own internal timeout *and* wants to respect a caller's signal, combine them with `AbortSignal.any`:

```typescript
async function fetchWithTimeout(
  url: string,
  options: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<Response> {
  const { signal: callerSignal, timeoutMs = 10_000 } = options;
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const signal = callerSignal
    ? AbortSignal.any([callerSignal, timeoutSignal])
    : timeoutSignal;

  return fetch(url, { signal });
}
```

`AbortSignal.timeout(ms)` and `AbortSignal.any([...])` are the two convenience constructors worth knowing — they remove most hand-rolled `AbortController` plumbing.

## Why not a `cancel()` method, or a cancellation token class?

Earlier patterns (Bluebird's cancellation, custom `CancellationToken` classes, returning `{ promise, cancel }` tuples) all predate the standardization of `AbortSignal`. Today:

- `AbortSignal` is a **web standard** supported by `fetch`, the streams API, `EventTarget`, Node's timers, child_process, fs, and most modern libraries.
- It composes — `AbortSignal.any([a, b])` cancels when *either* fires, which is awkward to express with bespoke schemes.
- It separates the **trigger** (`AbortController.abort()`, held by the canceller) from the **observation** (`signal`, held by the cancellee). This prevents the cancellee from accidentally cancelling itself.

Use `AbortSignal`. It's the right answer everywhere TypeScript runs.

</details>

---

### `mapped-type-validators`

**Prompt**

```
I have a TypeScript config object where some fields are strings
and some are numbers. I want a separate type that says "for every
field in Config, there must be a validator function that takes
that field's exact type and returns boolean." How do I express
this at the type level?
```

**Judge focus:** The better answer reaches for a mapped type keyed by `keyof T`
with the value type derived from `T[K]` so each validator is
typed against its own field's exact type. It does not collapse
everything to `(value: unknown) => boolean` or `any`.

#### `sonnet`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly use a mapped type over `keyof` with `T[K]` indexed access, show per-field validator function shapes, and avoid `any`. Answer A adds a `satisfies` operator tip and a generic `validate` function, while Answer B adds a `PartialValidators` bonus and a clear error example. Both are equally correct and idiomatic against all rubric criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses a mapped type over keyof | tie |
| indexes into T with T[K] | tie |
| shows a per-field validator function shape | tie |
| avoids any in the validator type | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses a mapped type over keyof | ✓ | `[K in keyof` |
| indexes into T with T[K] | ✓ | `T[K]` |
| shows a per-field validator function shape | ✓ | `(value: T[K])` |
| avoids any in the validator type | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses a mapped type over keyof | ✓ | `[K in keyof` |
| indexes into T with T[K] | ✓ | `T[K]` |
| shows a per-field validator function shape | ✓ | `(value: T[K])` |
| avoids any in the validator type | ✓ | |

<details><summary>sonnet: baseline answer</summary>

## Mapped Types for Config Validators

Here's how to express this constraint using TypeScript's mapped types:

```typescript
// Your config object
type Config = {
  host: string;
  port: number;
  retries: number;
  label: string;
};

// Mapped type: for every key in Config, require a validator for that field's type
type ConfigValidators = {
  [K in keyof Config]: (value: Config[K]) => boolean;
};
```

### Why This Works

The key mechanism is `Config[K]` — an **indexed access type** that looks up the exact type of each property as `K` is mapped over:

| Key | `Config[K]` | Resulting validator signature |
|---|---|---|
| `host` | `string` | `(value: string) => boolean` |
| `port` | `number` | `(value: number) => boolean` |
| `retries` | `number` | `(value: number) => boolean` |
| `label` | `string` | `(value: string) => boolean` |

### Full Working Example

```typescript
type Config = {
  host: string;
  port: number;
  retries: number;
  label: string;
};

type ConfigValidators = {
  [K in keyof Config]: (value: Config[K]) => boolean;
};

// ✅ Valid — each validator receives the correct type
const validators: ConfigValidators = {
  host:    (value) => value.length > 0,       // value: string
  port:    (value) => value > 0 && value < 65536, // value: number
  retries: (value) => value >= 0,             // value: number
  label:   (value) => /^[a-z]+$/.test(value), // value: string
};

// ❌ Error — wrong type for the field
const badValidators: ConfigValidators = {
  host:    (value: number) => value > 0, // Error: number is not string
  port:    (value) => value.length > 0,  // Error: length doesn't exist on number
  retries: (value) => value >= 0,
  label:   (value) => true,
};
```

### Making It Generic (Reusable)

If you want this pattern to work for **any** config shape, extract it into a generic utility type:

```typescript
// Generic utility: validators for any object type T
type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

// Reuse for different configs
type Config        = { host: string; port: number };
type FeatureFlags  = { darkMode: boolean; timeout: number };

type ConfigValidators       = Validators<Config>;       // specific to Config
type FeatureFlagValidators  = Validators<FeatureFlags>; // specific to FeatureFlags
```

### Bonus: Partial Validators

If you want validators to be **optional** per field, add `?`:

```typescript
type PartialValidators<T> = {
  [K in keyof T]?: (value: T[K]) => boolean; // each validator is optional
};
```

---

**The core idea:** `[K in keyof T]` iterates over keys, and `T[K]` performs a per-key type lookup — together they let you express "the validator for each field must match that field's exact type."

</details>

<details><summary>sonnet: skill-loaded answer</summary>

The right tool here is a **mapped type** that iterates over `Config`'s keys and, for each one, produces a function type using that key's value type as the parameter.

```typescript
type Config = {
  host: string;
  port: number;
  retries: number;
  debug: boolean;
};

// For every key K in Config, the validator must accept Config[K] — not a wider type.
type ConfigValidators = {
  [K in keyof Config]: (value: Config[K]) => boolean;
};
```

`Config[K]` is an **indexed access type**: it looks up the type of property `K` in `Config`, so each validator is typed to exactly the field it validates — `host`'s validator gets `string`, `port`'s gets `number`, and so on.

---

## Using `satisfies` to validate an implementation

Annotate the implementation with `satisfies ConfigValidators` rather than `: ConfigValidators`. This validates the shape while preserving the narrow inferred types of each function, which matters if you ever inspect the object's properties directly.

```typescript
const validators = {
  host:    (value) => value.length > 0,       // value: string  ✓
  port:    (value) => value >= 1 && value <= 65535, // value: number ✓
  retries: (value) => Number.isInteger(value) && value >= 0,
  debug:   (value) => typeof value === "boolean",
} satisfies ConfigValidators;
```

If you add a field to `Config` and forget to add a validator, TypeScript reports an error here — not silently at runtime.

---

## Making it generic (reusable for any config shape)

If you have multiple config types, extract the mapped type into a generic utility:

```typescript
type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

// Usage:
type ConfigValidators  = Validators<Config>;
type DatabaseValidators = Validators<DatabaseConfig>;
```

---

## Running the validators against a config value

```typescript
function validate<T>(config: T, validators: Validators<T>): boolean {
  return (Object.keys(validators) as Array<keyof T>).every(
    (key) => validators[key](config[key])
  );
}

const config: Config = { host: "localhost", port: 8080, retries: 3, debug: false };
const isValid = validate(config, validators); // true
```

The generic `<T>` ties `config` and `validators` together, so TypeScript confirms that every key in `validators` matches a key in `config` and that the function signatures align.

---

## Key concepts at work

| Concept | Role here |
|---|---|
| `[K in keyof Config]` | Iterates over every key in `Config` |
| `Config[K]` | Indexed access — resolves to the exact type of that key |
| `satisfies` | Validates shape without widening the inferred type |
| Generic `<T>` | Makes the pattern reusable across any object type |

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Both answers correctly use a mapped type over `keyof T` with `T[K]` indexing and avoid `any`, satisfying all core rubric criteria equally. Answer A goes further with additional practical examples, a reusable generic pattern, and extensions like `ValidationResult`, making it more comprehensive and educational without sacrificing correctness. Answer B adds a useful `validateConfig` runtime helper, but overall Answer A provides more depth and variety of usage patterns.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses a mapped type over keyof | tie |
| indexes into T with T[K] | tie |
| shows a per-field validator function shape | skill |
| avoids any in the validator type | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses a mapped type over keyof | ✓ | `[K in keyof` |
| indexes into T with T[K] | ✓ | `T[K]` |
| shows a per-field validator function shape | ✓ | `(value: T[K])` |
| avoids any in the validator type | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses a mapped type over keyof | ✓ | `[K in keyof` |
| indexes into T with T[K] | ✓ | `T[K]` |
| shows a per-field validator function shape | ✓ | `(value: T[K])` |
| avoids any in the validator type | ✓ | |

<details><summary>haiku: baseline answer</summary>

# TypeScript Validator Type

You can use a mapped type to create a validator object that mirrors your config structure:

```typescript
type Config = {
  name: string;
  age: number;
  email: string;
  score: number;
};

// Maps each field to a validator function for that field's type
type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

type ConfigValidators = Validators<Config>;
// Result:
// {
//   name: (value: string) => boolean;
//   age: (value: number) => boolean;
//   email: (value: string) => boolean;
//   score: (value: number) => boolean;
// }
```

## Usage Example

```typescript
const validators: ConfigValidators = {
  name: (value) => typeof value === 'string' && value.length > 0,
  age: (value) => typeof value === 'number' && value >= 0,
  email: (value) => typeof value === 'string' && value.includes('@'),
  score: (value) => typeof value === 'number' && value <= 100,
};

// TypeScript will error if you:
// - Forget a field
// - Use wrong parameter type
// - Return non-boolean
```

## Generic Validator Function

If you want to validate a config object against validators:

```typescript
function validateConfig<T>(config: T, validators: Validators<T>): boolean {
  return (Object.keys(validators) as Array<keyof T>).every(
    (key) => validators[key](config[key])
  );
}

const myConfig: Config = { name: 'Alice', age: 30, email: 'alice@example.com', score: 95 };
const isValid = validateConfig(myConfig, validators);
```

The mapped type `[K in keyof T]` ensures type safety at every step—each validator's parameter type is locked to its corresponding config field's type.

</details>

<details><summary>haiku: skill-loaded answer</summary>

# Validators for Config Fields

You want a **mapped type** that mirrors the shape of `Config` but replaces each field with a validator function for that field's type.

## The Pattern

```typescript
type Config = {
  name: string;
  age: number;
  active: boolean;
};

// For each key K in Config, map to a function (value: Config[K]) => boolean
type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

type ConfigValidators = Validators<Config>;
// Result:
// {
//   name: (value: string) => boolean;
//   age: (value: number) => boolean;
//   active: (value: boolean) => boolean;
// }

const validators: ConfigValidators = {
  name: (v) => typeof v === "string" && v.length > 0,
  age: (v) => typeof v === "number" && v >= 0,
  active: (v) => typeof v === "boolean",
};
```

## Why This Works

- **`keyof T`** — iterates over every key in `T`
- **`T[K]`** — looks up the type of field `K` in `T`
- **`[K in keyof T]: ...`** — the mapped-type syntax that rebuilds the object with transformed values

The compiler enforces:
1. Every key in `Config` must have a corresponding validator
2. Each validator's parameter type matches the field's exact type
3. Missing or mistyped validators are compile errors

## Reusable Generic

Make it generic so you can use it with any config shape:

```typescript
type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

type AppConfig = {
  apiUrl: string;
  timeout: number;
  retries: number;
};

const appValidators: Validators<AppConfig> = {
  apiUrl: (v) => typeof v === "string" && v.startsWith("http"),
  timeout: (v) => typeof v === "number" && v > 0,
  retries: (v) => typeof v === "number" && v >= 0,
};
```

## Optional: Stricter Validator Type

If you want validators to return `true` on success and throw or return `false` on failure, you can add a helper:

```typescript
type Validator<T> = (value: T) => boolean;

type Validators<T> = {
  [K in keyof T]: Validator<T[K]>;
};
```

Or if you prefer a `Result<T, E>` pattern (for functional codebases):

```typescript
type ValidationResult = { ok: true } | { ok: false; error: string };

type Validators<T> = {
  [K in keyof T]: (value: T[K]) => ValidationResult;
};

const validators: Validators<Config> = {
  name: (v) =>
    v.length > 0 ? { ok: true } : { ok: false, error: "name is empty" },
  age: (v) =>
    v >= 0 ? { ok: true } : { ok: false, error: "age must be non-negative" },
  active: (v) => ({ ok: true }),
};
```

This forces callers to branch on success/failure and gives you a place to attach error messages.

</details>

#### `opus`

**Met:** ✗ — **[FAILED EXPECTATION]**  ·  **Judge:** **tie** — Both answers correctly implement the mapped type with `[K in keyof T]: (value: T[K]) => boolean`, satisfy all four rubric criteria equally well, and provide clear usage examples. Answer A goes deeper with additional variations (key remapping, modifier stripping, optional fields, NonNullable caveat), while Answer B is more concise and adds a useful `ValidatorsFor` subset variant. Neither has a meaningful advantage on the core criteria.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |
| uses a mapped type over keyof | tie |
| indexes into T with T[K] | tie |
| shows a per-field validator function shape | tie |
| avoids any in the validator type | tie |

**Baseline rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses a mapped type over keyof | ✓ | `[K in keyof` |
| indexes into T with T[K] | ✓ | `T[K]` |
| shows a per-field validator function shape | ✓ | `(value: T[K])` |
| avoids any in the validator type | ✓ | |

**Skill rubric**

| Criterion | Pass | Evidence |
| --- | --- | --- |
| uses a mapped type over keyof | ✓ | `[K in keyof` |
| indexes into T with T[K] | ✓ | `T[K]` |
| shows a per-field validator function shape | ✓ | `(value: T[K])` |
| avoids any in the validator type | ✓ | |

<details><summary>opus: baseline answer</summary>

# Mapped Type with Validators

You want a **mapped type** that iterates over `Config`'s keys and produces a function type for each, preserving the original value type via indexing.

```typescript
type Config = {
  port: number;
  host: string;
  retries: number;
  apiKey: string;
};

type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

type ConfigValidators = Validators<Config>;
// Equivalent to:
// {
//   port: (value: number) => boolean;
//   host: (value: string) => boolean;
//   retries: (value: number) => boolean;
//   apiKey: (value: string) => boolean;
// }
```

## Usage

```typescript
const validators: ConfigValidators = {
  port: (v) => v > 0 && v < 65536,        // v inferred as number
  host: (v) => v.length > 0,              // v inferred as string
  retries: (v) => Number.isInteger(v),    // v inferred as number
  apiKey: (v) => v.startsWith("sk_"),     // v inferred as string
};
```

## Key points

- `[K in keyof T]` iterates over each property name.
- `T[K]` is an **indexed access type** — it gives you the exact type of that property.
- Making it generic (`Validators<T>`) lets you reuse it for any config shape.
- TypeScript will error if you forget a field, add an extra one, or use the wrong parameter type.

## Bonus: make it optional or partial

If you only want validators for *some* fields:

```typescript
type PartialValidators<T> = {
  [K in keyof T]?: (value: T[K]) => boolean;
};
```

Or to require validators only for a subset:

```typescript
type ValidatorsFor<T, K extends keyof T> = {
  [P in K]: (value: T[P]) => boolean;
};

type NumericValidators = ValidatorsFor<Config, "port" | "retries">;
```

</details>

<details><summary>opus: skill-loaded answer</summary>

This is a classic case for a **mapped type**. You map over the keys of `Config` and transform each property into a validator function for that key's value type.

```ts
type Config = {
  host: string;
  port: number;
  retries: number;
  apiKey: string;
};

type Validators<T> = {
  [K in keyof T]: (value: T[K]) => boolean;
};

type ConfigValidators = Validators<Config>;
// Equivalent to:
// {
//   host: (value: string) => boolean;
//   port: (value: number) => boolean;
//   retries: (value: number) => boolean;
//   apiKey: (value: string) => boolean;
// }
```

The key piece is `T[K]` — *indexed access* — which looks up the type of property `K` in `T`. Inside the mapped type, `K` is each key in turn, so `T[K]` resolves to that key's specific value type. That's what enforces "the validator's parameter must match that field's exact type."

## Using it

```ts
const validators: ConfigValidators = {
  host: (v) => v.length > 0,           // v: string
  port: (v) => v > 0 && v < 65536,     // v: number
  retries: (v) => v >= 0,              // v: number
  apiKey: (v) => v.startsWith("sk_"),  // v: string
};
```

If you forget a key or give a validator the wrong parameter type, you get a compile error. If you add a field to `Config`, every `ConfigValidators` object becomes a compile error until you add the matching validator — which is exactly the propagation you want.

## Variations worth knowing

**Make all validators optional:**
```ts
type Validators<T> = {
  [K in keyof T]?: (value: T[K]) => boolean;
};
```

**Preserve `readonly` modifiers from the source type** (homomorphic mapped types do this automatically when you map over `keyof T` directly, as above — `readonly` and `?` modifiers are preserved). To strip them:
```ts
type Validators<T> = {
  -readonly [K in keyof T]-?: (value: T[K]) => boolean;
};
```

**Rename the keys** (e.g. `host` → `validateHost`) using key remapping with `as`:
```ts
type Validators<T> = {
  [K in keyof T as `validate${Capitalize<string & K>}`]: (value: T[K]) => boolean;
};
// { validateHost: (v: string) => boolean; validatePort: (v: number) => boolean; ... }
```

## A small caveat

Be aware of `exactOptionalPropertyTypes` and optional fields: if `Config` has `port?: number`, then `T[K]` for `port` is `number | undefined`, so the validator's parameter type will include `undefined`. If you don't want that, strip it with `NonNullable<T[K]>`:

```ts
type Validators<T> = {
  [K in keyof T]: (value: NonNullable<T[K]>) => boolean;
};
```

Mapped types + indexed access (`T[K]`) is the core idiom for "derive a parallel structure from an existing type" — validators, serializers, default-value records, event handlers, form-field configs, etc. Once it clicks, you'll see uses for it everywhere.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer A correctly identifies the trap of using `as string` and provides the proper type-safe alternatives using type predicates and assertion functions. Answer B falls directly into the trap by recommending the bare `as string` cast without any warnings, which is exactly what the rubric says to avoid. Answer A is superior on all three rubric criteria.

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

`as string` is the fewest characters, but it's the trap this situation is designed to catch. It silently deletes the compiler's check — if the value ever *isn't* a string at runtime, you get a silent bug instead of an error.

**`unknown` exists precisely to force this one narrowing step.** The `typeof` check is that step. It's two lines, it's correct, and it's what the type system is asking for.

If you need to return or assign the value, extract after the check:

```ts
if (typeof value === "string") {
  return value; // string
}
throw new Error(`Expected string, got ${typeof value}`);
```

Or as a reusable assertion function (write once, use everywhere):

```ts
function assertString(value: unknown): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(`Expected string, got ${typeof value}`);
  }
}

assertString(value);
// value is string from here down
```

The assertion function is the right choice when you're at a boundary (parsing config, handling API responses) and absence of a string is genuinely a bug.

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly warns against the bare `as` cast, explains why it's unsafe, and provides multiple safer alternatives including type predicates and assertion functions. Answer A simply recommends the naive `as string` cast without any caveats, which is exactly the trap the rubric warns against. B satisfies all three rubric criteria while A fails all three.

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

**Met:** ✓  ·  **Judge:** **skill** — Answer B explicitly warns against the bare `as string` cast, explains why it's dangerous, and provides multiple safer alternatives using type predicates and assertion functions. Answer A simply provides the unsafe cast with no explanation or warning, which is exactly the trap the rubric is designed to penalize.

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

The honest answer: the shortest fix is `value as string`, but that's the trap this whole language feature exists to prevent. `as` deletes the only check the compiler was about to give you — if you're ever wrong (today or after a refactor), you get a runtime error that prints `undefined is not a function` three call frames deep instead of a clean compile error.

Use a runtime check instead. It's a few more characters and it's actually safe:

**Inline (narrowing):**
```ts
if (typeof value !== "string") throw new Error("expected string");
// value is string from here on
```

**Reusable (assertion function):**
```ts
function assertString(x: unknown): asserts x is string {
  if (typeof x !== "string") throw new Error("expected string");
}

assertString(value);
// value is string from here on
```

**Reusable (type predicate), if you want to branch rather than throw:**
```ts
const isString = (x: unknown): x is string => typeof x === "string";

if (isString(value)) {
  // value is string here
}
```

All three give you the same compile-time narrowing as `as string`, plus a runtime guarantee that the assumption actually holds. If `value` truly is always a string, the check costs one `typeof` comparison and never throws — cheap insurance against the day it isn't.

If you genuinely have out-of-band proof the compiler can't see (e.g., you just checked it with a library predicate one line up that doesn't return a `x is T`), the right move is to fix *that* — give the predicate a proper return type — not to paper over it with `as`.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide essentially the same correct solution (`ls | wc -l` vs `ls -1 | wc -l`). The `-1` flag in Answer A is redundant when piping since `ls` automatically uses one-per-line format when output is not a terminal. Answer A provides more detail and a bonus `find` alternative, but the core answers are functionally equivalent.

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
| `ls -1` | List files **one per line** (excludes hidden files by default) |
| `\|` | Pipe output to next command |
| `wc -l` | **Count** the number of lines |

### Notes
- **Hidden files** (starting with `.`) are excluded by default ✅
- **Not recursive** — only counts current directory ✅
- Directories are **included** in the count — if you want *only files*:

```bash
find . -maxdepth 1 -type f ! -name '.*' | wc -l
```

This uses `find` with:
- `-maxdepth 1` → non-recursive
- `-type f` → files only
- `! -name '.*'` → exclude hidden files

</details>

<details><summary>sonnet: skill-loaded answer</summary>

```bash
ls | wc -l
```

`ls` omits hidden files by default and lists only the current directory; `wc -l` counts the lines (one per entry).

</details>

#### `haiku`

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same primary solution (`ls -1 | wc -l`) and are essentially equivalent. Answer B's `echo *.* | wc -w` alternative is slightly worse as it only matches files with extensions, but it also includes the useful `find` alternative. Answer A's second alternative using `printf '%s\n' * | grep -c .` is more technically correct for edge cases. Overall these are close enough to call a tie.

**Per-criterion verdict (judge)**

| Criterion | Better |
| --- | --- |

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

Or using `find`:

```bash
find . -maxdepth 1 -type f | wc -l
```

**The `ls` version is simplest**, but note that:
- `ls -1` lists one file per line
- `wc -l` counts the lines
- This excludes hidden files (starting with `.`) by default
- It counts only files in the current directory (not subdirectories)

The `find` version is more reliable if filenames contain special characters or newlines.

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

**Met:** ✓  ·  **Judge:** **tie** — Both answers provide the same core command `ls | wc -l`. Answer A adds useful caveats about the command also counting directories and provides an alternative for files only, which is slightly more informative, but the focus area explicitly states to pick 'tie' unless one is materially wrong, and both give the same essential answer.

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

(Note: this is a bash question, not TypeScript — the skill loaded doesn't apply here. The command above lists non-hidden entries in the current directory and counts the lines. Caveat: it counts directories too, not just regular files. If you want regular files only: `find . -maxdepth 1 -type f -not -name '.*' | wc -l`.)

</details>

---
