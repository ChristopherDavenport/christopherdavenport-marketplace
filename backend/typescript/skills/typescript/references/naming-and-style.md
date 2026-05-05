# Naming & Style — Deep Dive

Naming is high-leverage. The right name communicates intent in three characters; the wrong name forces every reader to step into the implementation. This file collects the conventions that the broader TypeScript community has converged on, with reasoning for the few cases where convention is contested.

## Identifier Casing

| Kind | Convention | Examples |
|---|---|---|
| Variable, function, method, parameter | `camelCase` | `userId`, `fetchUser`, `isReady` |
| Type, interface, class, enum, namespace, type parameter | `PascalCase` | `User`, `OrderStatus`, `Result<T, E>` |
| Constants (compile-time-only literal values, never reassigned, all-caps signals "knob") | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT_MS` |
| File names | `kebab-case.ts` (most common) or `PascalCase.ts` (some teams) | `user-service.ts`, `Result.ts` |
| Boolean-returning function | `is`/`has`/`can`/`should` prefix | `isValid`, `hasAccess`, `canEdit` |
| Constructor function returning a non-class instance | `make` or `create` prefix | `makeUserId`, `createConnection` |

The `SCREAMING_SNAKE_CASE` convention has been disputed in JavaScript over the last decade; modern style guides increasingly use `camelCase` for `const` declarations. Pragmatic stance: **reserve `SCREAMING_SNAKE` for compile-time-immutable constants** that are conceptually "settings" — magic numbers, hard-coded strings, configuration. Use `camelCase` for `const`-declared variables that are values in normal program flow:

```ts
const MAX_RETRIES = 3;                  // configuration knob
const DEFAULT_TIMEOUT_MS = 5000;         // configuration knob
const userId = "u-1";                    // value in normal flow
const result = pipe(input, normalize);   // value in normal flow
```

If your team prefers `camelCase` everywhere (no `SCREAMING_SNAKE`), that's also fine — pick one and apply it consistently. The TypeScript ESLint rule `@typescript-eslint/naming-convention` will enforce whichever you pick.

## No Hungarian-Notation Type Prefixes

TypeScript style explicitly **does not** prefix types with `I`, `T`, or similar:

```ts
// Avoid
interface IUser { /* ... */ }
type TResult = /* ... */;
class CUserService { /* ... */ }

// Prefer
interface User { /* ... */ }
type Result = /* ... */;
class UserService { /* ... */ }
```

The TypeScript handbook, the Google TypeScript Style Guide, and the official ESLint rules all push against `I` prefixes. Reasons:
- The IDE/tooltip already tells you what kind of identifier it is.
- Renaming an interface to a type alias means renaming all consumers.
- It's noise that doesn't help readers; the name is the name.

The `T` prefix on type parameters (`TKey`, `TValue`) is a related debate. The community convention:
- Single-letter (`T`, `K`, `V`, `E`) is preferred for short, generic type parameters.
- Descriptive names (`Item`, `Element`, `Value`) without prefix when one letter is ambiguous.
- The `T` prefix (`TItem`, `TKey`) is used by some teams for visual distinction; not the dominant style but acceptable if consistent.

```ts
// Common
function map<T, U>(arr: readonly T[], f: (t: T) => U): U[] { /* ... */ }

// Also acceptable when descriptive helps
type Lookup<Key extends string, Value> = Record<Key, Value>;

// Avoid as default style
type Lookup<TKey extends string, TValue> = Record<TKey, TValue>;
```

## File Naming Conventions

Two camps:

**`kebab-case.ts` (most common)** — works on every filesystem, plays well with URLs, easy to type in a terminal:
```
user-service.ts
order-repository.ts
result-helpers.ts
```

**`PascalCase.ts` (React-influenced)** — the file name matches the primary export, useful when "the file is the type":
```
UserService.ts
OrderRepository.ts
Result.ts
```

Either is fine. **Pick one and enforce it across the project.** Mixed conventions are the worst outcome — readers can't predict file names.

`forceConsistentCasingInFileNames: true` in tsconfig (see [tsconfig-and-strictness.md](tsconfig-and-strictness.md)) catches drift between filename and import casing.

## Naming Functions

- **Verb phrases for actions:** `fetchUser`, `parseJson`, `normalizeEmail`.
- **Predicate prefixes (`is`/`has`/`can`/`should`) for booleans:** `isReady`, `hasPermission`, `canEdit`, `shouldRetry`. Read as a yes/no question.
- **Noun phrases for getters or constructors:** `userById`, `defaultConfig`, `makeUserId`.
- **Pure function names focus on what's returned, not how:** `sortedByDate(items)`, not `sortItemsByDate(items)`. The pure-function lens emphasizes the returned shape.

```ts
// Action
const fetchUser   = (id: string, signal: AbortSignal): Promise<User> => /* ... */;
const parseJson   = (s: string): Result<unknown, ParseError>          => /* ... */;

// Predicate
const isValidEmail = (s: string): boolean                              => /* ... */;
const hasAdminRole = (u: User): boolean                                => /* ... */;

// Constructor
const makeUserId   = (s: string): UserId                               => /* ... */;
const emptyUser    = (): User                                           => /* ... */;
```

## Naming Type Parameters

- **One letter when the role is generic and unambiguous:** `T` (single value), `K` (key), `V` (value), `E` (error or element), `R` (result), `A`/`B`/`C` (a sequence of types in a function signature).
- **Multi-letter when the role needs context:** `TKey extends string` if the constraint matters, `Item` instead of `T` if reading "item" makes more sense in the context.
- **Avoid one-letter names that overlap:** `T` for both "type" and "tag" in the same signature is confusing. Rename to `Tag` and `Value` for clarity.

```ts
// Idiomatic
type Mapper<T, U> = (t: T) => U;
type Predicate<T> = (t: T) => boolean;
type Reducer<T, A> = (acc: A, t: T) => A;

// More descriptive — fine when it improves readability
type Lookup<Key extends string, Value> = Record<Key, Value>;
```

## Naming Discriminant Tags

When defining discriminated unions (see [discriminated-unions.md](discriminated-unions.md)):

- `kind` — succinct, no clash with the `type` keyword
- `type` — natural-language, slightly higher chance of confusion with `typeof`
- `_tag` — common in FP libraries, signals "internal/structural"

Pick one **per project** and stick with it. Mid-codebase switching is a noise-generator.

## When JSDoc Earns Its Keep

TypeScript's types remove the need for JSDoc for parameter and return types — those are already in the signature. JSDoc is worth writing only when the type doesn't tell the whole story:

**Worth writing:**
- **Units.** `/** in milliseconds */ timeout: number`
- **Range constraints.** `/** between 0 and 1 inclusive */ ratio: number`
- **Pre/post conditions.** `/** caller must hold the lock */`
- **Side effects.** `/** mutates the input array */`
- **Surprising behavior.** `/** returns null if input contains a bare carriage return */`
- **Why, not what.** `/** Workaround for #4521 — Safari's File API doesn't expose lastModified for directory entries */`

**Not worth writing:**
- **Re-narrating the type.** `/** the user id @type {string} */ userId: string` — duplicates info.
- **Function name restatement.** `/** Fetches a user by ID */ fetchUser(id: string)` — name says it.
- **Generic descriptions.** `/** processes the data */` — meaningless.

```ts
/**
 * Returns the time elapsed since the start of the trace, in microseconds.
 * Resets when `clearTrace()` is called. Returns 0 before the first measurement.
 */
function elapsedMicros(): number { /* ... */ }
```

The JSDoc adds three things the signature doesn't: units (microseconds), reset behavior (depends on `clearTrace`), and edge case (returns 0 initially). All of these matter; none are in the type.

## Comments — When to Write Them

Same reasoning applies to inline comments. **Default: write none.** The code, the types, and the function names should explain the *what*. Comments earn their keep only for the **why**:

```ts
// Avoid: restates the code
// Increment the counter
counter += 1;

// Worth it: explains a non-obvious decision
// Use Math.fround instead of plain assignment to ensure 32-bit precision
// matches the WebGL shader's float behavior. Otherwise positions drift in long sessions.
position[0] = Math.fround(x);
```

Avoid:
- "Used by X" / "Called from Y" — comments rot when callers change. Find-references tells you.
- "TODO: refactor this" without a ticket — becomes ambient noise.
- "Added for issue #1234" — the commit message has this.
- Restating identifier names.

Write when:
- A future reader will be confused by the *why*.
- A subtle invariant needs to be preserved.
- A workaround references an external bug or surprising behavior.

## Avoid Abbreviation Jargon in Public APIs

Internal abbreviations (`req`, `res`, `cfg`, `db`, `cb`) are fine inside a function body. **Public API surfaces — exported function and type names, parameter names, field names — should spell out words.**

```ts
// Internal: fine
function handle(req: Request): Response { /* ... */ }

// Public API: spell it out
export function handleRequest(request: Request): Response { /* ... */ }
export type UserConfig = { /* ... */ };   // not UserCfg

// Public API parameters: spell out names readers will see in autocomplete
export function setTimeout2(callback: () => void, delayMs: number): TimerId {
  // ^^^^^^^^                ^^^^^^^^^                ^^^^^^^
  //   not setTo                not cb                  not d
}
```

The asymmetry: in a body, you read the abbreviation while looking at its definition (one line up). In a public API, callers see only the abbreviation in autocomplete.

## Module Naming

Files contain related code. The file name should tell readers what's inside without opening it:

- **Specific:** `user-service.ts`, `order-validation.ts`, `parse-csv.ts`
- **Avoid:** `utils.ts`, `helpers.ts`, `common.ts`, `misc.ts` — these become dumping grounds. Once a file is named `utils`, every utility goes in, and the file balloons. Split by concern: `string-utils.ts`, `date-formatting.ts`.

## Boolean Field Names

Booleans should read as predicates:

```ts
// Good — reads as a question
type User = {
  isActive: boolean;
  hasVerifiedEmail: boolean;
  canEditOthers: boolean;
};

// Avoid — ambiguous
type User = {
  active: boolean;          // active what? as in "currently online" or "not deleted"?
  emailVerified: boolean;   // OK, but isVerifiedEmail or hasVerifiedEmail is clearer
  permissions: boolean;     // "permissions" isn't a yes/no
};
```

The `is`/`has`/`can`/`should` prefix removes ambiguity at the call site:

```ts
if (user.isActive) { /* ... */ }      // reads correctly
if (user.active)   { /* ... */ }       // reads less naturally
```

## Avoid Negative Boolean Names

`isNotReady`, `disableValidation`, `hideField` — reading these requires double-negation.

```ts
// Avoid
if (!user.isNotActive) { /* ... */ }   // double negative
if (!disableValidation) { /* ... */ }   // double negative

// Prefer
if (user.isActive) { /* ... */ }
if (validationEnabled) { /* ... */ }
```

When you must invert at the call site, that's fine — but the field/variable name itself stays positive.

## Common Pitfalls

- **`I`-prefixed interfaces and `T`-prefixed types.** Strip them. Modern TypeScript style is unprefixed.
- **`utils.ts`, `helpers.ts`, `common.ts`.** Become dumping grounds. Split by concern as you go.
- **Single-letter parameters in a multi-arg function.** `function f(a, b, c, d)` is unreadable. Single letters are fine for `(x) => x * 2`-style one-liners and well-known parameter conventions (mathematical functions, callbacks).
- **Boolean fields without `is`/`has`/`can`/`should` prefix.** `user.admin` could be a boolean, an enum, an object — the name doesn't say. `user.isAdmin` is unambiguous.
- **Negative boolean names.** Double-negation at every read site. Invert the variable instead.
- **`T` in two unrelated roles in the same signature.** Rename to specific names — the resulting clarity is worth the extra letters.
- **Mixed file-name casing.** Some files `kebab-case`, others `PascalCase`. Pick one. Enforce with lint.
- **JSDoc that re-narrates the type.** Adds noise without adding information. Either say something the type doesn't, or say nothing.
- **Comment-as-tracking-info.** "Added by Alice for ticket-1234." Belongs in the commit message, not the code. Comments rot.
- **Abbreviations exported in public APIs.** `cfg`, `req`, `cb`, `db` make sense in a function body. They make autocomplete cryptic in a public surface.
- **Inconsistent constant casing.** `MAX_RETRIES` here, `maxRetries` there. Pick a rule (compile-time literals get `SCREAMING_SNAKE`; everything else `camelCase`) and lint for it.
