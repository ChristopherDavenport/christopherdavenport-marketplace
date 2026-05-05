# Classes & OOP — Deep Dive

TypeScript supports the full object-oriented toolkit: classes, inheritance, abstract members, access modifiers, getters/setters, static members. They're useful tools — for entities with identity, for stateful resources that need lifecycle methods, for integrating with class-based frameworks (DOM custom elements, ORM models, NestJS controllers). They are *one* tool among several; this file covers when they fit and the conventions for writing them well.

## Class Basics

```ts
class User {
  constructor(
    public readonly id: string,
    public readonly name: string,
    public email: string,
  ) {}

  toString(): string {
    return `${this.name} <${this.email}>`;
  }
}

const u = new User("u-1", "alice", "a@x.com");
u.email = "alice@x.com";   // OK — email isn't readonly
u.name = "bob";            // ERROR — name is readonly
```

The **parameter property** shorthand (`public readonly id: string` in the constructor) declares and initializes a field in one step. Use it — it's idiomatic and removes the duplication of declaring fields and assigning them.

## Access Modifiers

| Modifier | Visibility | Compile-time? | Runtime? |
|---|---|---|---|
| `public` (default) | Anywhere | n/a | Public |
| `protected` | This class and subclasses | Yes | Public at runtime |
| `private` | This class only | Yes | Public at runtime |
| `#field` (private fields) | This class only | Yes | Hard-private at runtime |
| `readonly` | Modifier (combines with above) | Prevents reassignment | n/a |

```ts
class BankAccount {
  #balance = 0;                       // hard-private, runtime-enforced
  private deposits: number[] = [];    // soft-private, compile-only
  protected accountNumber: string;    // visible to subclasses
  public readonly id: string;          // public but immutable

  constructor(id: string, accountNumber: string) {
    this.id = id;
    this.accountNumber = accountNumber;
  }

  deposit(amount: number): void {
    this.deposits.push(amount);
    this.#balance += amount;
  }

  get balance(): number {
    return this.#balance;
  }
}
```

**`private` vs `#field`:**

- `private` is enforced by **TypeScript only** — at runtime, the field is a normal property accessible via `obj["fieldName"]` or in non-TypeScript callers.
- `#field` is **runtime-private** (ECMAScript private fields) — genuinely inaccessible from outside, even via `obj["#field"]`.

**Use `#field` for genuine encapsulation** (security boundaries, invariants you cannot afford to have bypassed). **Use `private` for everything else** — it has better tooling support, works with mocks/test doubles that need to inspect internals, and the compile-time check is usually sufficient.

## Constructors

A constructor sets up class invariants. Keep it minimal:

```ts
// Good — constructor establishes the invariant
class Connection {
  #socket: Socket;

  constructor(host: string, port: number) {
    this.#socket = openSocket(host, port);   // synchronous setup only
  }
}

// Bad — async work in a constructor
class Connection {
  #socket?: Socket;

  constructor(host: string, port: number) {
    void this.connect(host, port);   // fire-and-forget; instance is unusable until ready
  }

  async connect(host: string, port: number) { /* ... */ }
}
```

Constructors **cannot be async**. If construction requires async work, hide it behind a static factory:

```ts
class Connection {
  private constructor(private readonly socket: Socket) {}

  static async open(host: string, port: number): Promise<Connection> {
    const socket = await openSocketAsync(host, port);
    return new Connection(socket);
  }
}

const conn = await Connection.open("localhost", 8080);
```

The `private` constructor + `static` factory pattern is the cleanest way to express "this class needs work to construct that the constructor signature can't hold."

## Inheritance — Use Sparingly

Inheritance is convenient for sharing implementation, but it creates rigid coupling: the subclass depends on the parent's behavior, the parent's invariants, and the parent's choice of public methods. Refactoring the parent ripples through every subclass.

```ts
abstract class Shape {
  abstract area(): number;
  abstract perimeter(): number;

  describe(): string {
    return `area=${this.area()} perimeter=${this.perimeter()}`;
  }
}

class Circle extends Shape {
  constructor(public readonly radius: number) { super(); }
  override area():      number { return Math.PI * this.radius ** 2; }
  override perimeter(): number { return 2 * Math.PI * this.radius; }
}
```

`abstract` classes cannot be instantiated directly. Subclasses must implement abstract members. The `override` keyword is required by `noImplicitOverride` (see [tsconfig-and-strictness.md](tsconfig-and-strictness.md)) — it prevents silent renames from breaking the override relationship.

**When inheritance fits:**
- Framework integration (React class components, NestJS controllers, web components) where the framework expects a class hierarchy.
- A small, stable hierarchy (3-5 classes) with genuine "is-a" relationships.
- Sharing behavior across implementations of an interface, where the abstract base provides the template method.

**When to avoid inheritance:**
- More than 2 levels deep — the chain becomes hard to reason about.
- Sharing utility methods — use a free function or a mixin instead.
- Modeling variants that differ in shape — a discriminated union (see [discriminated-unions.md](discriminated-unions.md)) is usually clearer.
- Code reuse for its own sake — composition (`class Foo { #helper: Helper }`) almost always beats inheritance for sharing.

## Interfaces and `implements`

```ts
interface Logger {
  log(level: "info" | "warn" | "error", message: string): void;
}

class ConsoleLogger implements Logger {
  log(level: "info" | "warn" | "error", message: string): void {
    console.log(`[${level}] ${message}`);
  }
}

function setup(logger: Logger): void { /* ... */ }
setup(new ConsoleLogger());
```

`implements` is a **compile-time check** — the class must satisfy the interface, but it doesn't gain anything at runtime. Use it to:

1. Document the contract a class is meant to satisfy.
2. Get errors when the interface evolves and the class hasn't kept up.

Note: `implements` is one-way. The class doesn't carry the interface as a runtime tag. Consumers should depend on the interface, not the class — so the class can be swapped for any other implementation:

```ts
// Good — depends on the interface
function setup(logger: Logger): void { /* ... */ }

// Bad — depends on the concrete class; can't substitute
function setup(logger: ConsoleLogger): void { /* ... */ }
```

## Getters and Setters

Property accessors look like fields but run code:

```ts
class Temperature {
  #celsius: number;

  constructor(celsius: number) {
    this.#celsius = celsius;
  }

  get celsius(): number {
    return this.#celsius;
  }

  set celsius(value: number) {
    if (!Number.isFinite(value)) throw new Error("not finite");
    this.#celsius = value;
  }

  get fahrenheit(): number {
    return this.#celsius * 9 / 5 + 32;
  }
}

const t = new Temperature(20);
t.celsius;             // 20
t.fahrenheit;          // 68
t.celsius = 100;
t.celsius = NaN;       // throws
```

**Use getters** for derived values that look like properties (`fahrenheit` from `celsius`).

**Use setters sparingly.** They hide work behind what looks like a field assignment. A method (`setCelsius(value)`) is more honest. The case for a setter: parity with a getter, or framework conventions that expect property-shaped access (DOM custom elements, frameworks that reflect attributes).

## Static Members

Static members belong to the class itself, not an instance:

```ts
class HttpStatus {
  static readonly OK = 200;
  static readonly NOT_FOUND = 404;
  static readonly INTERNAL_SERVER_ERROR = 500;

  static isSuccess(status: number): boolean {
    return status >= 200 && status < 300;
  }
}

HttpStatus.OK;                   // 200
HttpStatus.isSuccess(200);       // true
```

Static members are useful for:
- **Factory methods** (`Connection.open(...)`).
- **Constants tied to the type** (`HttpStatus.OK`).
- **Stateless utilities related to the type** (`Date.now()`, `Math.max()`).

**Caveat:** a class consisting entirely of static members is a namespace pretending to be a class. Use a plain `const` object or a module of free functions:

```ts
// Avoid — class as namespace
class StringUtils {
  static reverse(s: string): string { /* ... */ }
  static capitalize(s: string): string { /* ... */ }
}

// Prefer — module
export const reverse = (s: string): string => /* ... */;
export const capitalize = (s: string): string => /* ... */;
```

## When to Use a Class

Use a class when **at least one** of these is true:

1. **Identity matters.** Two `User` instances with the same fields are still different users. The instance has identity beyond its data.
2. **Lifecycle matters.** The object goes through states (`open` → `closed`, `loading` → `ready` → `disposed`) and you need methods to drive transitions while protecting invariants.
3. **Invariants need protection.** You want to guarantee that `BankAccount.balance` is never directly assignable from outside; only `deposit`/`withdraw` can change it.
4. **Framework expects it.** React class components (legacy), NestJS, Lit, Angular, custom elements — all expect classes.
5. **Resource ownership.** The instance owns a connection, a file handle, a subscription that needs explicit cleanup.

## When to Use a Plain Object Instead

Use a plain object (with `type` or `interface`) when **all** of these are true:

1. The data is **just data** — no methods, or methods that could equally be free functions.
2. There's no lifecycle — the value is constructed once and used.
3. Equality is structural — two values with the same fields are interchangeable.
4. You don't need to protect any invariant after construction.

```ts
// Just data — use a plain object
type User = {
  readonly id: string;
  readonly name: string;
  readonly email: string;
};

const buildUser = (id: string, name: string, email: string): User =>
  ({ id, name, email });
```

The plain-object approach plays better with serialization (`JSON.stringify` is direct), structural typing across module boundaries, and immutable-update patterns. Reach for a class when one of the criteria above (identity, lifecycle, invariants, framework, resource) actually applies.

## Mixins (Use With Care)

Mixins compose behavior without inheritance. They use the constructor function pattern:

```ts
type Constructor<T = object> = new (...args: any[]) => T;

function Timestamped<T extends Constructor>(Base: T) {
  return class extends Base {
    timestamp = Date.now();
  };
}

class User {
  constructor(public name: string) {}
}

const TimestampedUser = Timestamped(User);
const u = new TimestampedUser("alice");
u.name;        // "alice"
u.timestamp;   // 1234567890
```

Mixins are powerful but the resulting types and class hierarchies become hard to reason about. Use **composition** (a field holding a helper instance) instead unless you have a specific framework requirement that wants mixins.

## Method Bindings and `this`

Methods on a class are not auto-bound. Passing them as callbacks loses `this`:

```ts
class Counter {
  count = 0;
  increment() { this.count++; }
}

const c = new Counter();
const fn = c.increment;
fn();   // TypeError: Cannot read 'count' of undefined
```

Three solutions:

```ts
// 1. Arrow-function field — bound at construction
class Counter {
  count = 0;
  increment = () => { this.count++; };
}

// 2. Bind at the call site
const fn = c.increment.bind(c);

// 3. Wrap in an arrow at the call site
const fn = () => c.increment();
```

Arrow-function fields work but allocate a new function per instance and aren't shared across instances (memory cost). For most cases, prefer wrapping at the call site — explicit and zero per-instance overhead.

## Abstract Classes vs Interfaces

An **interface** describes a shape with no implementation. An **abstract class** describes a shape and may provide partial implementation.

```ts
// Interface — no implementation
interface Repository<T> {
  find(id: string): Promise<T | null>;
  save(entity: T): Promise<void>;
}

// Abstract class — partial implementation
abstract class CachedRepository<T> implements Repository<T> {
  #cache = new Map<string, T>();

  abstract fetchFromBackend(id: string): Promise<T | null>;
  abstract persistToBackend(entity: T): Promise<void>;

  async find(id: string): Promise<T | null> {
    if (this.#cache.has(id)) return this.#cache.get(id)!;
    const result = await this.fetchFromBackend(id);
    if (result !== null) this.#cache.set(id, result);
    return result;
  }

  async save(entity: T): Promise<void> {
    await this.persistToBackend(entity);
  }
}
```

**Default to interfaces.** They impose no implementation constraints and play well with composition. Reach for an abstract class only when there's genuine shared implementation that would otherwise be duplicated across subclasses (the template method pattern).

## Common Pitfalls

- **Using a class for what is just data.** A `User` with `id` / `name` / `email` and no methods doesn't need to be a class. A plain object is simpler.
- **Long inheritance chains.** Two levels works; three is suspicious; four is hard to maintain. Refactor toward composition.
- **`private` when you need real privacy.** TypeScript's `private` is compile-time only. For runtime privacy, use `#fields`.
- **Async work in constructors.** Constructors can't be async. Use a `private constructor` + `static async create()` factory.
- **Class with all static methods.** That's a module. Use `export function` instead.
- **Passing methods as callbacks without binding.** Loses `this`. Bind at the call site or use arrow-function fields.
- **Setters that hide complex work.** `obj.thing = value` looks free but might trigger a network call or recompute everything. Use a method.
- **`implements` on every class out of habit.** Only useful when the contract evolves separately from implementations. For an interface used by exactly one class, the class itself is the contract.
- **`override` missing.** Without `noImplicitOverride`, renaming the base method silently breaks the override. Enable the flag and use the keyword.
- **Mutable public fields.** Direct field access skips invariant checks. Make fields `readonly` or `private`/`#`, expose mutation through methods.
- **Constructor parameter properties + extra constructor logic.** The shorthand is great when the constructor is only assignment. Once you have non-trivial logic, declare fields explicitly to keep the constructor readable.
- **Returning `this` for chaining without thinking through immutability.** Method chaining mutates by default. If you want a fluent API on an immutable type, return a new instance from each method instead.
