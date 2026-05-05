# Modules — Deep Dive

Modules are how TypeScript code is organized, shared, and consumed. The choices you make about module syntax, export style, and project layout have outsized effects on refactor-friendliness, build size, and the unfortunate frequency of circular-import bugs.

## ESM as the Default

ECMAScript Modules (ESM, `import`/`export`) are the default in modern TypeScript. CommonJS (`require`/`module.exports`) is a legacy compatibility target — write new code as ESM.

```ts
// foo.ts
export const greet = (name: string) => `hello, ${name}`;
export type Greeting = string;

// bar.ts
import { greet } from "./foo";
import type { Greeting } from "./foo";
```

Configure your `tsconfig.json` for ESM:
```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "verbatimModuleSyntax": true,
    "isolatedModules": true
  }
}
```

(Or `module: "ESNext"` / `moduleResolution: "Bundler"` if a bundler handles resolution.) See [tsconfig-and-strictness.md](tsconfig-and-strictness.md) for what each flag does.

## Named Exports Over Default Exports

Default exports (`export default`) are seductive in their brevity but cause subtle pain at scale.

```ts
// Default export — what you wrote
export default class UserService { /* ... */ }

// Default export — what consumers can write
import UserService    from "./user-service";  // expected
import US             from "./user-service";  // also valid
import WhateverIWant  from "./user-service";  // also valid
```

The import name is **not** required to match. This breaks:

- **Tooling:** auto-import, refactor-rename, find-references.
- **Code search:** grepping for `UserService` doesn't find consumers using a different alias.
- **Tree-shaking:** less granular than named exports.

**Always prefer named exports:**

```ts
// Module
export class UserService { /* ... */ }
export const DEFAULT_TIMEOUT_MS = 5000;
export type UserOptions = { /* ... */ };

// Consumer
import { UserService, DEFAULT_TIMEOUT_MS } from "./user-service";
import type { UserOptions } from "./user-service";
```

Named exports give the importer one canonical name. Refactoring is a real find-replace, not a guess.

The legitimate uses of default export:
- Frameworks that mandate it (some bundler entry points, some legacy APIs).
- Single-export modules where the file *is* the export and you genuinely don't want to bikeshed the name (rare in practice).

When in doubt, named.

## `import type` and `export type`

A type-only import declares that the binding is *only* used as a type, never as a runtime value. The compiler erases it from the emitted JavaScript.

```ts
import type { User } from "./user";          // erased at compile
import { fetchUser } from "./user";          // kept

import { type Result, ok, err } from "./result";   // mixed inline
```

Why this matters:

1. **Avoids unnecessary runtime imports.** If `./user` does work at module-load time (registers a hook, runs a side effect), `import type` lets you reference its types without paying that cost.
2. **Breaks circular import deadlocks.** If module A imports a type from B and B imports a type from A, type-only imports avoid the runtime cycle while preserving the type relationships.
3. **Required by `verbatimModuleSyntax`.** That flag refuses to emit imports that are only used as types — you must mark them `type` explicitly.

The same applies to exports:

```ts
export type { User, UserId } from "./user";   // re-export types only
export { fetchUser } from "./user";            // re-export value
```

**Convention:** mark every type-only import/export as `type` from day one. Once `verbatimModuleSyntax` is enabled, the compiler enforces it.

## Barrel Files (`index.ts`) — When They Help, When They Hurt

A barrel file re-exports from multiple modules, presenting a single import surface:

```ts
// services/index.ts
export { UserService } from "./user-service";
export { OrderService } from "./order-service";
export { PaymentService } from "./payment-service";

// consumer
import { UserService, OrderService } from "./services";
```

**When barrels help:**
- Public package boundaries — you genuinely want consumers to write `import { x } from "your-pkg"` without thinking about internal structure.
- A small, stable set of related exports.

**When barrels hurt:**
- **Circular imports.** Barrel imports the modules; the modules each import from the barrel; you have a cycle. Symptom: `Cannot read properties of undefined` at module-load time.
- **Tree-shaking.** A barrel that re-exports 50 modules pulls all of them into the build, even if the consumer used one. Some bundlers handle this; many don't.
- **Build performance.** Every consumer of the barrel triggers re-resolution of every barrel entry.
- **Discoverability.** Code search finds `import from "./services"` everywhere, not the actual source file.

**Rule of thumb:** use barrels at *package boundaries* (the public API of a library or major subpackage). Avoid them inside a project — import from the source file directly.

If you do use a barrel:
- Re-export only types and "always-needed" runtime entries.
- Avoid side-effecting imports through barrels.
- Audit for cycles after each addition.

## Import-Time Side Effects Are an Anti-Pattern

A module that does work at import time — registering a global, mutating shared state, starting a timer — is fragile:

```ts
// Bad: side effect at import
console.log("module loaded");
GlobalRegistry.register("foo", handler);
setInterval(poll, 1000);
```

Problems:
- The order of imports starts to matter. Refactoring imports can break behavior.
- Tree-shaking can't remove "unused" modules — they ran.
- Tests can't isolate; importing the module runs the side effect.
- Server-side rendering / pre-rendering hits the side effect at build time, often unexpectedly.

**Convention:** modules export functions and types. Calling them is what runs the side effect. The module itself is inert.

```ts
// Good: side effect is explicit
export function startPolling(intervalMs: number): () => void {
  const id = setInterval(poll, intervalMs);
  return () => clearInterval(id);
}

// Caller decides when:
const stop = startPolling(1000);
```

## Circular Imports

A cycle exists when module A's import graph reaches back to A. ESM handles cycles in some cases — bindings are live references — but the failure modes are nasty:

- A `const` from a not-yet-evaluated module is `undefined` at the moment you try to use it.
- A class hoisted as `class X {}` is initialized too early; methods called on it fail.
- Module-load order changes after refactors, breaking previously-working code.

**Detection:** most modern bundlers warn on cycles. ESLint plugin `eslint-plugin-import` has `import/no-cycle`. Turn these on.

**Resolution patterns:**

1. **Extract the shared bit to a third module.** A imports C, B imports C, no cycle.
2. **Make the offending import a type-only import.** Type imports are erased; they don't participate in the runtime cycle.
3. **Use lazy imports.** Move the import inside the function where it's used (`const { x } = await import("./b")`). Adds latency on first call but breaks the cycle.

Most cycles are accidental — two modules grew shared concerns without a shared home. The first fix (extract a third module) is almost always right.

## Declaration Merging via `interface`

`interface` supports declaration merging — two `interface X { ... }` declarations in the same scope are merged into one:

```ts
// In one file
interface Config {
  host: string;
}

// In another file (or same file)
interface Config {
  port: number;
}

// Effective:
const c: Config = { host: "localhost", port: 8080 };
```

This is the legitimate use case for `interface` over `type`. Common applications:
- Augmenting a third-party library's type with your additions.
- Adding fields to global types (`Window`, `globalThis`).
- Extending a framework's request/context object.

**Use sparingly.** Declaration merging makes types depend on import order in subtle ways. When in doubt, prefer composition (intersect types in a new alias) over augmentation.

```ts
// Augmentation
declare global {
  interface Window {
    myAppVersion: string;
  }
}
```

## Ambient `.d.ts` Declarations

`.d.ts` files contain *only* type declarations — no runtime code. They describe the shapes of:

- Untyped JavaScript libraries (`@types/*` packages, but you can write your own).
- Module-shaped values created at runtime (assets, env vars).
- Globals injected by the build environment.

```ts
// types/env.d.ts
declare module "*.css" {
  const styles: Record<string, string>;
  export default styles;
}

declare const __VERSION__: string;
declare const __DEV__: boolean;
```

Convention: keep `.d.ts` files in a `types/` directory and reference them via `tsconfig.json` `include`. Don't sprinkle them throughout the source tree.

For library code, **prefer typed source over a separate `.d.ts`.** TypeScript can emit declaration files (`declaration: true`) — the source *is* the declaration. Hand-written `.d.ts` companions get out of sync.

## File and Module Naming

- **One module per file.** Don't put two unrelated exports in one file just because they're small.
- **File name reflects the primary export.** A file with `export class UserService` should be named `user-service.ts` (or `UserService.ts` — see [naming-and-style.md](naming-and-style.md) for the case-convention discussion).
- **Avoid `utils.ts` and `helpers.ts`.** They become dumping grounds. Put utilities into named files (`string-utils.ts`, `date-formatting.ts`, `result-helpers.ts`) so the file name says what's inside.
- **Tests live next to source.** `user-service.ts` + `user-service.test.ts` in the same directory beats parallel `src/` and `tests/` trees for refactor-friendliness. (Consult your project convention.)

## `import` vs `import type` vs `import { type ... }`

```ts
import { Foo, type Bar } from "./mod";  // mixed — runtime + type
import type { Baz } from "./mod";        // entire import is type-only
import { Foo, Bar } from "./mod";        // both runtime — even if Bar is a type
```

With `verbatimModuleSyntax`:

- `import { Bar }` where `Bar` is only a type — **error**. Mark it `type`.
- `import type { Bar }` is correct.
- `import { Foo, type Bar }` is correct for the mixed case.

This flag is annoying for the first hour and a load-bearing improvement after that. Enable it.

## Common Pitfalls

- **Default exports because they're shorter to type.** The cost is paid forever in refactor pain. Always named.
- **Barrel files everywhere.** Internal imports should hit the source file directly. Barrels at the package boundary only.
- **`import { type X }` vs `import type { X }`.** Both work; pick a convention. The latter is cleaner when *all* imports from a module are types.
- **Forgetting `import type` for cycle-causing type imports.** If A imports a type from B and B does any runtime work, an `import type` instead of `import` may break the cycle.
- **Module-load side effects.** Set up a registry function and call it explicitly from an entry point. Don't run it at import time.
- **Tons of tiny modules.** A 1-line module per function is overkill. Group related functions into a module ~10-200 lines. Bigger files are fine if the contents are cohesive.
- **One giant module.** A 2000-line module is a maintenance trap. Split when concerns diverge.
- **Mixing `.cjs` and `.mjs` in the same package without a strategy.** Pick ESM-only and stick with it. CJS-ESM interop works but is full of corner cases.
- **Re-exporting types without `export type`.** Without `verbatimModuleSyntax`, this works; with it, the compiler errors. The fix is one keyword.
- **Augmenting third-party types globally without scoping.** `declare global { ... }` modifies everything in the project. Use it intentionally; prefer module-scoped augmentation when possible.
