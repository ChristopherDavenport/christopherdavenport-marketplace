# Functions — Deep Dive

Functions in TypeScript come in several syntactic forms with different `this` and hoisting behavior, several parameter styles (required, optional, default, rest), and several return-type idioms (single value, union, overload, generic). This file covers the practical mechanics, with a final section on functional patterns (pure functions, currying, composition) for codebases that lean that way.

## `function` vs Arrow Functions

Both produce callable values. The differences:

| | `function` declaration | Arrow function |
|---|---|---|
| `this` | Bound at call site | Lexically captured (no own `this`) |
| `arguments` | Has it | Doesn't |
| Hoisted | Yes | No (only the binding is hoisted, not initialized) |
| Constructor | Can be `new`'d | Cannot |
| `name` property | From declaration | From variable name |
| Type predicates / assertions | Required | Not allowed (use `function`) |

**Default to arrow functions** for callbacks, methods on object literals, and any function whose `this` should come from the enclosing scope.

**Use `function` declarations** for:
1. Top-level utilities — hoisting lets the use site appear above the declaration.
2. Recursive functions that reference themselves by name.
3. Type predicates (`x is T`) and assertion functions (`asserts x is T`).
4. Functions that need a typed `this` parameter.

```ts
const double = (n: number) => n * 2;

function isString(x: unknown): x is string {
  return typeof x === "string";
}

function assertString(x: unknown): asserts x is string {
  if (typeof x !== "string") throw new TypeError("not a string");
}
```

## Parameters

### Required, Optional, Default, Rest

```ts
function greet(
  name: string,                          // required
  greeting: string = "hello",            // default — implies optional
  honorific?: string,                    // optional, no default
  ...extras: ReadonlyArray<string>       // rest
): string {
  const parts = [greeting];
  if (honorific) parts.push(honorific);
  parts.push(name, ...extras);
  return parts.join(" ");
}

greet("alice");                          // "hello alice"
greet("alice", "hi", "Dr.", "PhD");      // "hi Dr. alice PhD"
greet("alice", undefined, "Dr.");        // skip-default: pass undefined explicitly
```

Rules:

- **Required parameters come first.** Optionals come after.
- **A parameter with a default is implicitly optional** — you don't (and can't) add `?`.
- **Optionals are typed as `T | undefined`** — handle accordingly.
- **Rest parameters must be the last parameter.** They collect into an array typed `T[]` (or `ReadonlyArray<T>` if you mark it).

### Parameter Order Tips

Put parameters in order of "least likely to change at the call site → most likely to change":

```ts
// Good — config first (rarely changes), data last
function search(options: SearchOptions, query: string): SearchResult[];

// Less good — data first, config buried
function search(query: string, options: SearchOptions): SearchResult[];
```

This makes partial application (and composition) natural. See the Functional Patterns section below for more.

### Object Parameters for Many Args

A function with more than ~3 parameters becomes positional-call hell. Switch to an options object:

```ts
// Hard to read at the call site
function createUser(
  id: string, name: string, email: string,
  isAdmin: boolean, createdAt: Date,
): User { /* ... */ }

createUser("u-1", "alice", "a@x", false, new Date());   // which bool is which?

// Object parameter — call sites are self-documenting
function createUser(args: {
  id: string;
  name: string;
  email: string;
  isAdmin?: boolean;
  createdAt?: Date;
}): User { /* ... */ }

createUser({
  id: "u-1",
  name: "alice",
  email: "a@x",
  isAdmin: false,
});
```

Object parameters give you:
- **Named arguments at the call site** — less guessing about positional meaning.
- **Optional fields without ordering constraints** — you can add a new optional field without breaking callers.
- **Easier to refactor** — adding/removing fields touches the type, not every call site.

The cost: a tiny allocation per call (negligible) and slightly more typing. Worth it past ~3 parameters.

## Return Types

### Annotate Return Types on Public APIs

Inferred return types are convenient inside a function body. **Annotate explicitly on exported functions** so:
- The contract is visible without reading the body.
- A change to the body that accidentally widens the return type is a compile error.

```ts
// Internal — inference is fine
const double = (n: number) => n * 2;

// Public API — annotate
export function fetchUser(id: string): Promise<User> { /* ... */ }
```

### Returning `T | undefined` vs Throwing vs `Result`

Three patterns for "operation might not produce a value":

```ts
// 1. T | undefined — caller checks
function findUser(id: string): User | undefined { /* ... */ }
const u = findUser("1");
if (u === undefined) return notFound();

// 2. Throw — caller doesn't have to think about it
function getUser(id: string): User {
  const u = findUser(id);
  if (u === undefined) throw new Error(`user ${id} not found`);
  return u;
}

// 3. Result — caller MUST branch (covered in error-handling.md)
function tryFindUser(id: string): Result<User, NotFoundError> { /* ... */ }
```

Convention: **`find` prefix returns `T | undefined`; `get` prefix throws.** See [error-handling.md](error-handling.md) for the full picture.

### `void` Return Type Semantics

`void` means **"the caller will discard the return value"** — not "must return undefined."

```ts
type Listener = () => void;

const listeners: Listener[] = [
  () => console.log("a"),
  () => 42,                    // returns 42 — fine, listener type says caller ignores it
];
```

This is why `Array.forEach` accepts callbacks that return values: `forEach` is typed `(cb: (x: T) => void) => void`, the `void` says "I don't care."

For functions that explicitly return `undefined` and where callers care:

```ts
function findFirst<T>(arr: readonly T[], pred: (x: T) => boolean): T | undefined {
  for (const x of arr) if (pred(x)) return x;
  return undefined;
}
```

## Function Overloads

Overloads let one implementation satisfy multiple call signatures:

```ts
function parse(input: string, mode: "json"): unknown;
function parse(input: string, mode: "int"):  number;
function parse(input: string, mode: "bool"): boolean;
function parse(input: string, mode: "json" | "int" | "bool"): unknown {
  if (mode === "json") return JSON.parse(input);
  if (mode === "int")  return parseInt(input, 10);
  if (mode === "bool") return input === "true";
  throw new Error(`unknown mode: ${mode}`);
}
```

Two sharp edges:

1. **The implementation signature is invisible to callers.** Only the overload signatures are part of the public type. If your implementation accepts shapes the overloads don't list, that's hidden.
2. **The compiler doesn't verify all overloads are actually satisfied** by the implementation. A wrong overload type silently produces type/runtime mismatch.

**Prefer alternatives:**
- A single signature with a discriminated-union parameter.
- A generic function that infers the right return.
- Two separate functions with descriptive names (`parseAsJson`, `parseAsInt`).

Reach for overloads only when nothing else works (typically: typing third-party APIs that genuinely behave differently per input shape).

## Generic vs Union vs Overload

Same problem ("function handles multiple shapes"), three tools. Pick based on the input/output relationship:

```ts
// Union parameter — same behavior, multiple input shapes
const length = (x: string | readonly unknown[]): number => x.length;

// Generic — input type flows to output
const wrap = <T>(x: T): { value: T } => ({ value: x });

// Overload — output is a fixed map from input value to type
function get(key: "a"): string;
function get(key: "b"): number;
function get(key: "a" | "b"): string | number {
  return key === "a" ? "hello" : 42;
}
```

Decision:
- Output doesn't depend on input type → **union parameter**
- Output type *is* (or derived from) the input type → **generic**
- Output is a small fixed set keyed by input value → **discriminated-union return** first; **overload** as a last resort

## `this` Parameter Typing

Functions can declare `this` as their (typed) first parameter. It's not a real argument — it doesn't appear at the call site:

```ts
function describe(this: { name: string }): string {
  return `name: ${this.name}`;
}

const u = { name: "alice", describe };
u.describe();                    // OK — this is the object
describe.call({ name: "bob" });  // OK — explicit this
describe();                      // Error: 'this' is not assignable
```

Use the typed `this` parameter to:
- Restrict a function to be called only as a method on a certain shape.
- Type DOM/event handlers where the runtime sets `this` (e.g., `addEventListener` callbacks).

In application code, prefer free functions that take their context as a normal argument — easier to test, easier to compose.

## Callback Signatures

When designing a function that takes a callback, **make the callback parameters as informative as possible** and the callback's return type as permissive as possible:

```ts
// Informative parameters, permissive return
function map<T, U>(
  arr: readonly T[],
  fn: (item: T, index: number, all: readonly T[]) => U,
): U[] { /* ... */ }
```

The `index` and `all` parameters are extra information — callers ignore them if they don't care. Permissive return (`U`, not `void`) lets the callback be useful.

## Defaulting Patterns

```ts
// 1. Parameter default — works for primitives
function greet(name: string, greeting = "hello"): string { /* ... */ }

// 2. Object spread default — works for option objects
type Options = { timeout?: number; retries?: number; signal?: AbortSignal };

function fetch2(url: string, options: Options = {}): Promise<Response> {
  const { timeout = 5000, retries = 3, signal } = options;
  /* ... */
}

// 3. Defaults via merging when many fields default
const DEFAULT_OPTIONS: Required<Omit<Options, "signal">> = {
  timeout: 5000,
  retries: 3,
};

function fetch3(url: string, options: Options = {}): Promise<Response> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  /* opts.timeout, opts.retries are guaranteed numbers; opts.signal stays optional */
}
```

Pattern 2 (destructuring with defaults) is usually best for option objects — defaults are visible right where the function uses them.

## Documentation via Types

The function signature carries most of the contract. JSDoc fills in what the type can't say:

```ts
/**
 * Returns the elapsed time since the start of the trace, in microseconds.
 * Returns 0 before the first measurement.
 */
function elapsedMicros(): number { /* ... */ }
```

The signature says it returns a number. The doc adds units and edge case. Both are necessary; neither is redundant.

Don't write docs that re-narrate the type:

```ts
// Useless
/** Returns the user. @returns {User} */
function getUser(id: string): User { /* ... */ }
```

See [naming-and-style.md](naming-and-style.md) for when JSDoc is worth the keystroke.

## Functional Patterns

The patterns in this section are widely useful but less central than the conventions above. Codebases that lean toward functional style use them heavily; others use them selectively.

### Higher-Order Functions

Functions that take or return functions:

```ts
const map = <T, U>(arr: readonly T[], fn: (x: T) => U): U[] =>
  arr.map(fn);

const greaterThan = (n: number) => (x: number): boolean => x > n;
const isPositive = greaterThan(0);
```

`Array.prototype.map`, `filter`, `reduce` are the everyday HOFs. Custom HOFs are useful when the same control flow recurs (retries, memoization, throttling).

### Pure Functions

A pure function:
1. Returns the same output for the same inputs (no `Date.now()`, no globals, no I/O).
2. Doesn't mutate its inputs or any reachable state.
3. Has no side effects.

Pure functions are trivially testable, cacheable, and concurrent-safe. Push impure work (I/O, time, randomness) to the **edges** of your code; keep the data-transformation core pure.

```ts
// Impure — entangled with I/O and time
async function processOrder(orderId: string): Promise<void> {
  const order = await db.getOrder(orderId);
  order.processedAt = new Date();
  await db.save(order);
  await emailQueue.send({ to: order.email, body: "thanks!" });
}

// Pure core, impure shell
type ProcessedOrder = Order & { processedAt: Date };

const markProcessed = (order: Order, now: Date): ProcessedOrder =>
  ({ ...order, processedAt: now });

const buildReceiptEmail = (order: ProcessedOrder): EmailMsg =>
  ({ to: order.email, body: "thanks!" });

async function processOrder(orderId: string): Promise<void> {
  const order = await db.getOrder(orderId);
  const processed = markProcessed(order, new Date());
  await db.save(processed);
  await emailQueue.send(buildReceiptEmail(processed));
}
```

`markProcessed` and `buildReceiptEmail` are testable in isolation, no database mocks required.

You don't have to make every function pure — but when a function naturally would be pure, *keep* it pure. Don't reach for `Date.now()` or shared mutable state inside what could otherwise be a clean transformation.

### Partial Application via Closures

Fixing some arguments and getting back a function of the remaining arguments:

```ts
const fetchFrom = (baseUrl: string) => (path: string, signal: AbortSignal) =>
  fetch(`${baseUrl}${path}`, { signal });

const apiCall = fetchFrom("https://api.example.com");
apiCall("/users/1", signal);
```

Closures handle this cleanly. **Avoid `Function.prototype.bind`** — closures preserve generic types better and read more naturally.

### Currying and Data-Last

Currying turns a multi-arg function into a chain of single-arg functions. Useful when the function will frequently be partially applied or fed into a `pipe`:

```ts
// Curried, data-last — pipes naturally
const filter = <T>(pred: (x: T) => boolean) => (arr: readonly T[]): T[] =>
  arr.filter(pred);

const isEven = (n: number) => n % 2 === 0;
filter(isEven)([1, 2, 3, 4]);   // [2, 4]
```

The "data goes last" convention is what makes curried functions composable — see [composition.md](composition.md) for the full picture. Don't curry every function; curry the ones that participate in pipelines.

## Common Pitfalls

- **Long positional parameter lists.** Past ~3 parameters, switch to an options object so call sites are readable.
- **Missing return-type annotations on exported functions.** A typo or refactor accidentally widens the type; callers see surprising results.
- **Overloads when a discriminated-union return would do.** Try the simpler tool first.
- **Reaching for `function` everywhere out of habit.** Default to arrows; use `function` for the specific cases that need it.
- **Using `.bind()` for partial application.** Closures do the same thing with better type inference.
- **`void` confused with `undefined`.** `void` means "discarded by caller"; `undefined` requires the value. Use `T | undefined` when the caller checks.
- **Mutating arguments.** A function that mutates its inputs is a hidden side effect. Mark parameters `readonly` to prevent it.
- **Currying functions that won't be partially applied.** Adds call indirection for no benefit. Curry only the functions that participate in pipelines.
- **Putting data first in curried functions.** `filter(arr, pred)` doesn't compose; `filter(pred)(arr)` does.
- **`this`-using functions in domain code.** `this` couples a function to a calling context. Prefer plain functions taking the data as an argument.
- **Inline default values that shadow real type information.** `function f(x = 0)` infers `x: number` from the default — fine for primitives. For complex defaults, declare the type explicitly to prevent inference surprises.
