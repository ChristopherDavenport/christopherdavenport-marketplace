# Testing — Deep Dive

This file covers test patterns that apply across runners — Vitest, Jest, the Node built-in test runner, Bun's, Deno's. Examples use a generic `test`/`expect`/`describe` shape that all of these provide; the patterns transfer.

The goal: tests that are fast, focused, deterministic, easy to read, and trustworthy when they fail.

## What to Test

A useful taxonomy:

| Layer | What you test | Tools | Volume |
|---|---|---|---|
| Unit | One function or one small module in isolation | Just the test runner | Most of your tests |
| Integration | Two or more modules working together | Test runner + maybe a real DB / file system | A meaningful number |
| End-to-end | The whole system from the outside | A browser driver / HTTP client | A small, curated set |

Most "test pyramid" advice still holds: lots of fast unit tests, fewer integration tests, even fewer end-to-end. Slow tests get skipped, get flaky, get ignored. Fast tests get run.

## Anatomy of a Good Unit Test

```ts
test("normalizeEmail trims whitespace and lowercases", () => {
  const result = normalizeEmail("  Alice@Example.com  ");
  expect(result).toBe("alice@example.com");
});
```

What makes it good:

- **One thing per test.** The test name describes a single behavior.
- **Arrange / Act / Assert** — three phases, often separated by blank lines, sometimes by comments.
- **No setup that isn't relevant** to what's being tested.
- **Deterministic** — no `Date.now()`, no `Math.random()`, no time dependence.
- **Fast** — no I/O unless integration testing.

A failing test should tell you what's broken from the name and the assertion message alone, without reading the implementation.

## Naming Tests

Two common conventions:

**Behavioral, declarative:**
```ts
test("returns null for empty input", () => { /* ... */ });
test("preserves order when all items are equal", () => { /* ... */ });
test("throws when input length exceeds maxBytes", () => { /* ... */ });
```

**Given/when/then:**
```ts
test("given an empty array, returns null", () => { /* ... */ });
test("when the user is admin, allows access to settings", () => { /* ... */ });
```

Either works. Pick a style and apply it consistently. **Avoid these:**

```ts
test("test 1", () => { /* ... */ });                     // useless
test("normalizeEmail", () => { /* ... */ });             // tests what about it?
test("works", () => { /* ... */ });                      // works how?
test("should normalize email correctly", () => { /* ... */ }); // "should" + "correctly" — vague
```

The test name appears in the failure output. It should tell you, at a glance, what the test was checking — without scrolling to the implementation.

## Table-Driven Tests

When the same logic should hold across many inputs, a table avoids duplicated test bodies:

```ts
describe("normalizeEmail", () => {
  const cases: ReadonlyArray<{ input: string; expected: string }> = [
    { input: "alice@x.com",      expected: "alice@x.com" },
    { input: "  Alice@X.com  ",  expected: "alice@x.com" },
    { input: "ALICE@X.COM",      expected: "alice@x.com" },
    { input: "alice+tag@x.com",  expected: "alice+tag@x.com" },
  ];

  for (const { input, expected } of cases) {
    test(`"${input}" -> "${expected}"`, () => {
      expect(normalizeEmail(input)).toBe(expected);
    });
  }
});
```

The test name embeds the input → output, so a failure tells you exactly which case is broken.

Most runners also support a built-in parametric form (`test.each`, `it.each`); both work. The hand-rolled version is portable across runners.

## Type-Level Tests

The TypeScript type system can be tested as code. The pattern: assert that two types are equal at the type level.

```ts
type Equals<X, Y> =
  (<T>() => T extends X ? 1 : 2) extends
  (<T>() => T extends Y ? 1 : 2) ? true : false;

type Expect<T extends true> = T;

// Use:
type _t1 = Expect<Equals<ReturnType<typeof normalizeEmail>, string>>;
type _t2 = Expect<Equals<Parameters<typeof normalizeEmail>, [string]>>;
```

If `normalizeEmail` ever changes its return type to `string | null`, `_t1` becomes a compile error.

For exhaustive type tests, dedicated libraries exist (e.g., `expect-type`-shaped APIs). The hand-rolled `Equals` / `Expect` helpers are 5 lines and runner-agnostic — usually enough.

Run type tests with `tsc --noEmit` as part of CI. They don't need a test runner.

## Test Doubles: When to Mock, When to Use Real

A "test double" is a stand-in for a dependency. The vocabulary:

- **Stub** — returns canned answers. No assertions about how it's called.
- **Mock** — records calls and lets you assert on them.
- **Fake** — a working implementation, simpler than the real one (in-memory database, in-memory queue).
- **Spy** — wraps a real function and records calls without changing behavior.

**Use a real implementation when:**
- The dependency is fast and side-effect-free (a pure helper).
- A fake exists that's faithful to the contract (in-memory store).
- Wiring the real thing in a test takes the same effort as a mock.

**Use a fake when:**
- The dependency is slow, networked, or has side effects.
- A faithful in-memory version is straightforward.
- You want integration-level confidence without integration-level cost.

**Use a stub when:**
- The dependency's behavior isn't relevant to what you're testing — you just need *some* answer.
- Setting up a real or faked version costs more than the test value.

**Use a mock when:**
- You're specifically testing that a side effect happened (e.g., "the email service was called with these arguments").
- The dependency is the *thing under test* and you need to observe interactions.

```ts
// Real — it's pure, no need for a double
test("formatPrice", () => {
  expect(formatPrice(1234, "USD")).toBe("$1,234.00");
});

// Fake — in-memory store as a stand-in for a database
test("UserRepository.save then find", async () => {
  const store = new InMemoryUserStore();
  const repo  = new UserRepository(store);
  await repo.save({ id: "1", name: "alice" });
  expect(await repo.find("1")).toEqual({ id: "1", name: "alice" });
});

// Stub — return a canned response; we don't care how it's called
test("loads user with default config", async () => {
  const stubFetch = (): Promise<Response> =>
    Promise.resolve(new Response(JSON.stringify({ id: "1", name: "alice" })));
  const result = await loadUser("1", { fetch: stubFetch });
  expect(result.name).toBe("alice");
});

// Mock — we ARE testing that the call happens
test("notifies the audit log when a user is deleted", async () => {
  const calls: Array<{ event: string; userId: string }> = [];
  const audit = (event: string, userId: string) => { calls.push({ event, userId }); };
  await deleteUser("u-1", { audit });
  expect(calls).toEqual([{ event: "user.deleted", userId: "u-1" }]);
});
```

**Avoid mocking what you don't own.** Mocking third-party libraries directly couples your tests to their internals. Wrap them in a thin interface you control, mock the interface.

**Avoid over-mocking.** A test that mocks every dependency tests that the function calls its mocks — it doesn't test that the function does anything useful. Mock at the boundaries; use real implementations for the interior.

## Async Tests

```ts
test("fetchUser returns the user", async () => {
  const user = await fetchUser("u-1", new AbortController().signal);
  expect(user.id).toBe("u-1");
});
```

The runner awaits the test function's returned promise. **Always `await`** any promise inside the test — a forgotten `await` makes the assertion run after the test has already finished, the failure reports as an unhandled rejection, and you'll waste time hunting it.

For testing rejections:

```ts
test("fetchUser throws on 404", async () => {
  await expect(fetchUser("missing", signal)).rejects.toThrow("404");
});
```

For testing values inside a `.catch`:

```ts
test("fetchUser surfaces the response status", async () => {
  let caught: unknown;
  try {
    await fetchUser("missing", signal);
  } catch (e) {
    caught = e;
  }
  expect(caught).toBeInstanceOf(HttpError);
  expect((caught as HttpError).status).toBe(404);
});
```

## Time, Randomness, and Other Sources of Non-Determinism

A test that passes today and fails tomorrow because the calendar rolled over is a worse-than-no-test test.

**Inject** sources of non-determinism rather than reading them directly:

```ts
// Bad — depends on Date.now() at test time
function isExpired(token: { exp: number }): boolean {
  return token.exp < Date.now();
}

// Good — caller injects the time
function isExpired(token: { exp: number }, now: number): boolean {
  return token.exp < now;
}

test("isExpired", () => {
  expect(isExpired({ exp: 1000 }, 2000)).toBe(true);
  expect(isExpired({ exp: 2000 }, 1000)).toBe(false);
});
```

Same pattern for randomness, IDs, file paths, environment variables. The test passes a known value; the production code passes the real one.

If injection isn't practical, most runners have time-mocking primitives (`vi.useFakeTimers()`, `jest.useFakeTimers()`, `MockTimers` in `node:test`). They work but they're heavier than a parameter.

## Test Isolation

Tests should not depend on the order they run in. The runner may parallelize, randomize, or run subsets. A test that passes only after another test runs first is broken.

```ts
// Bad — state leaks between tests
let counter = 0;

test("increments", () => {
  counter += 1;
  expect(counter).toBe(1);   // breaks if "starts at zero" runs second
});

test("starts at zero", () => {
  expect(counter).toBe(0);
});

// Good — each test sets up its own state
test("increments from zero", () => {
  let counter = 0;
  counter += 1;
  expect(counter).toBe(1);
});
```

For shared setup that's expensive but isolated, use the runner's `beforeEach` (resets per test) — **not** `beforeAll` (shared across tests, which is where state-leak bugs live).

## Snapshot Tests — Use With Caution

Snapshot tests record an output and compare future runs against it:

```ts
test("renders the user card", () => {
  expect(renderUserCard(user)).toMatchSnapshot();
});
```

Useful for:
- Catching unintended changes to large outputs.
- Locking in the shape of a complex value during refactoring.

Anti-pattern:
- Snapshots become stale, no one reads them, every change updates them blindly.
- A snapshot of a 200-line JSON blob that nobody can review meaningfully.

**Rule of thumb:** if the snapshot is small enough to read at a glance and you'd notice a wrong change, it's useful. Otherwise prefer targeted assertions on the specific properties that matter.

## Test File Layout

- **Co-locate tests with source.** `user-service.ts` → `user-service.test.ts` in the same directory. Refactoring moves both together.
- **Mirror the source structure.** Don't invent a separate organization for tests.
- **One test file per source file** is a good default; split if a single file grows past ~500 lines of tests.
- **Group related tests with `describe`.** One `describe` per public function or behavior is usually right; nesting describes more than one level deep is a smell.

```ts
describe("normalizeEmail", () => {
  test("lowercases", () => { /* ... */ });
  test("trims whitespace", () => { /* ... */ });
  test("preserves the local-part case after the @ if explicitly opted out", () => { /* ... */ });
});
```

## Coverage — Measure but Don't Worship

Coverage tells you which lines were *executed* by tests, not whether they were *meaningfully tested*. A test that calls a function but asserts nothing produces full coverage and zero value.

Use coverage to **find untested code** (low coverage = not exercised), not as a quality target (high coverage doesn't mean the tests are good).

100% line coverage as a hard requirement produces tests that exist only to hit lines — useless tests that slow CI, make refactoring painful, and obscure the meaningful tests. Aim for "the things that matter are tested" first; coverage is a diagnostic, not a goal.

## What *Not* to Test

- **Trivial getters and setters.** A test that `user.name === "alice"` after `new User("alice")` tests nothing about your code; it tests the constructor of TypeScript itself.
- **Third-party library internals.** Test that *your* code uses the library correctly, not that the library works.
- **Implementation details.** A test that asserts "the function calls `internalHelperFunction` 3 times" breaks every refactor and tests nothing the user cares about.
- **Compiler guarantees.** TypeScript already ensures `user.id` is a `string`. You don't need a test for that.
- **`console.log` output.** Logs are diagnostics, not contracts. Test the behavior the log describes, not the log itself.

## Common Pitfalls

- **Tests that depend on order.** Symptom: passes locally, fails in CI. Cause: shared state between tests. Reset state in `beforeEach`, not `beforeAll`.
- **Forgotten `await`.** The test "passes" because the assertion runs after the test ends; the failure shows up as an unhandled rejection. Use ESLint's `no-floating-promises` and the runner's "did the test return a settled promise?" detection.
- **Mocking everything.** A test where the function calls 5 mocked dependencies tests that mocks were called, not that anything happened. Use real implementations whenever practical.
- **Fragile assertions.** `expect(result).toEqual(largeObject)` where most fields don't matter — every change to `largeObject` breaks the test. Assert on the specific fields that actually matter.
- **Tests that read the implementation.** If you change the implementation without changing behavior and the test breaks, the test was over-coupled. Test outcomes, not internals.
- **Time-dependent tests.** `expect(getCurrentDay()).toBe("Monday")` will fail every other day. Inject time, mock it, or rewrite the function to take time as a parameter.
- **`expect(x).toBeTruthy()` when you mean `toBe(true)`.** `toBeTruthy` matches `1`, `"hello"`, `{}`, anything. If you actually mean `true`, say so.
- **Snapshot of everything.** Snapshots of large blobs become noise that no one reads. Targeted assertions for the fields that matter.
- **No type tests on tricky types.** A complex utility type can break silently. Add a few `Expect<Equals<X, Y>>` lines as type-only tests.
- **`console.log` in tests as a debug technique left in.** Polluting test output. Remove before committing, or use the runner's debug mode.
- **`describe` nesting more than 2 levels.** Tests become hard to find. Flatten with descriptive `test` names.
- **Treating coverage % as the goal.** 100% coverage with bad assertions is worse than 70% with good ones.
