# tsconfig & Strictness — Deep Dive

The `tsconfig.json` is the single most leveraged file in a TypeScript project. The right flags catch entire categories of bug at compile time; the wrong flags let real problems through. This file lists the flags that matter, explains what each one catches, and flags the few cases where you might *not* want to enable a stricter flag.

## The Non-Negotiables

These should be on in every new TypeScript project. Together they catch ~80% of the bugs that loose-typed code lets through.

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

The rest of this file walks each flag.

## `strict: true` — The Umbrella

`strict: true` enables several individual checks. As of recent TypeScript versions, this includes:

- `strictNullChecks` — `null` and `undefined` are not assignable to other types without explicit handling
- `strictFunctionTypes` — function-type parameters check contravariantly (sound variance)
- `strictBindCallApply` — `bind`/`call`/`apply` check argument types
- `strictPropertyInitialization` — class fields must be initialized or marked optional
- `noImplicitAny` — variables/parameters with no inferable type are an error
- `noImplicitThis` — implicit `this: any` in functions is an error
- `alwaysStrict` — emits `"use strict"` and parses files in strict mode
- `useUnknownInCatchVariables` — `catch (e)` types `e` as `unknown`

**Always enable `strict: true`.** Disabling individual sub-flags below to escape strict mode is a smell — fix the underlying issue instead.

The single most impactful sub-flag is `strictNullChecks`. Without it, `User` includes `null` and `undefined` silently — a `null` reference exception is one slip away. With it, you must either narrow or accept the explicit `User | null | undefined` signature.

```ts
// Without strictNullChecks
function greet(u: User) { return u.name; }   // u could be null at runtime, no warning

// With strictNullChecks
function greet(u: User | null) { return u.name; }   // ERROR: u is possibly null
function greet(u: User | null) {
  if (u === null) return "anonymous";
  return u.name;                                       // OK after narrowing
}
```

## `noUncheckedIndexedAccess: true`

By default, `arr[i]` has type `T` even though `i` might be out of bounds. With this flag, `arr[i]` has type `T | undefined`, forcing you to check.

```ts
const arr = [1, 2, 3];

// Without the flag
const x = arr[10];   // x: number  (lie — actually undefined at runtime)
console.log(x.toFixed());   // crashes at runtime, no warning

// With the flag
const x = arr[10];   // x: number | undefined
console.log(x.toFixed());   // ERROR: x is possibly undefined
console.log(x?.toFixed());  // OK
```

Same applies to objects with index signatures (`Record<string, V>`):

```ts
const m: Record<string, number> = { a: 1 };

const v = m["b"];    // v: number | undefined  (with the flag)
                     // v: number              (without — but it's actually undefined)
```

**Cost:** real existing code becomes a sea of `undefined` checks. Most are legitimate bugs you're now seeing for the first time. A few are noise — places where you genuinely know the index is in bounds. Use `arr[i]!` (the non-null assertion) sparingly and only with a comment justifying it. Or, better, refactor to use `arr.at(i)` with an explicit check, or destructure: `const [first] = arr; if (first === undefined) ...`.

## `exactOptionalPropertyTypes: true`

Without this flag, an optional field `x?: string` accepts `undefined` as a value. With it, optional means *absent* — explicitly setting `x: undefined` is a type error.

```ts
type User = { id: string; name?: string };

// Without the flag
const u: User = { id: "1", name: undefined };   // OK
// Now: does the consumer treat "name absent" the same as "name explicitly undefined"? Almost never.

// With the flag
const u: User = { id: "1", name: undefined };   // ERROR
const u2: User = { id: "1" };                    // OK — name truly absent
const u3: User = { id: "1", name: "alice" };     // OK — name set to a string
```

This matters because optional and nullable have different semantics:
- **Optional (`x?: T`)**: the property may not exist. `Object.hasOwn(obj, "x")` is false.
- **Nullable (`x: T | undefined`)**: the property exists, with value `undefined`.

These sound the same but behave differently with `JSON.stringify` (omits absent, includes `undefined` as nothing — but explicit `null` stays), object spread, structural typing, and serialization in general.

**Cost:** code that assigns `undefined` to optional fields needs to either (a) actually omit the field, or (b) declare `x: T | undefined` instead of `x?: T`. Painful migration; valuable result.

**Caveat:** sometimes friction with third-party libraries that explicitly accept `undefined` for optional fields. In those rare cases, broaden the type to `T | undefined` rather than disabling the flag.

## `noImplicitOverride: true`

When overriding a method in a subclass, requires the `override` keyword:

```ts
class Base {
  greet(): string { return "hi"; }
}

class Derived extends Base {
  greet() { return "hello"; }            // ERROR: missing 'override'
  override greet() { return "hello"; }    // OK
}
```

This prevents two bugs:
1. Renaming the base method without renaming the derived one — the derived method silently stops overriding (becomes its own method) without warning.
2. Adding a new method to the base that conflicts with an unrelated method in the derived — accidentally overriding.

Cheap to enable; valuable wherever you use class inheritance. (If your codebase doesn't override methods often, the flag is mostly a no-op — but turn it on for when it matters.)

## `noFallthroughCasesInSwitch: true`

Forbids accidental case fallthrough in `switch`:

```ts
switch (x.kind) {
  case "a":
    doA();
    // ERROR: fallthrough to "b" is not explicit
  case "b":
    doB();
    break;
}
```

Either add `break` (or `return`, or `throw`) to terminate, or annotate intentional fallthrough with `// fallthrough` (or just structure differently). Catches a real class of bug.

## `noImplicitReturns: true`

Requires every code path in a function to return a value (or all paths to be `void`):

```ts
function classify(n: number): string {
  if (n > 0) return "positive";
  if (n < 0) return "negative";
  // ERROR: not all paths return a value (forgot zero)
}
```

Forces you to handle every case. Combined with discriminated-union exhaustiveness, this is a powerful safety net.

## `noUnusedLocals: true` and `noUnusedParameters: true`

Errors on unused local variables and unused function parameters:

```ts
function f(a: number, b: number) {
  return a;   // ERROR: 'b' is declared but never used
}
```

Unused parameters can be silenced by prefixing with underscore:

```ts
function f(a: number, _b: number) {
  return a;   // OK
}
```

Catches dead code, leftover debugging variables, accidentally renamed parameters.

## `isolatedModules: true`

Ensures every file can be compiled in isolation — no cross-file type information needed at the per-file level. Required for fast bundlers (esbuild, swc) that compile files in parallel.

Effects:
- Const enums require `preserveConstEnums` or replacement with literal unions.
- Re-exports of types must use `export type { ... }` (otherwise the bundler can't tell they're erased).
- A few other corner cases.

**Always enable.** Even if your build tool doesn't strictly require it, the constraints are healthy and let you switch tools later without refactoring.

## `verbatimModuleSyntax: true`

Builds on `isolatedModules`. Requires that every import/export be either:
- A value reference (kept in emit), or
- Explicitly marked `type` (erased from emit)

```ts
import { type User, fetchUser } from "./user";   // OK — explicit
import { User, fetchUser } from "./user";         // ERROR if User is only a type
```

Why it matters:
- **No surprise emit.** What you write in source is what ends up in JS (modulo TS-syntax stripping). No compiler magic about which imports survive.
- **Faster compilation.** Tools don't need cross-file type information to determine whether to emit a given import.
- **Required by `module: "preserve"`** for some workflows.

Painful day-one migration; correct long-term default.

## `forceConsistentCasingInFileNames: true`

Errors when import casing doesn't match the actual filename:

```ts
// File: ./user-service.ts
import { fetchUser } from "./User-Service";   // ERROR
import { fetchUser } from "./user-service";    // OK
```

Catches bugs that bite when moving from a case-insensitive filesystem (macOS default, Windows) to case-sensitive (Linux, often CI). Prevent at compile time, not in production.

## Module / Target / ModuleResolution

The trio that controls compilation output and import resolution.

```json
{
  "module": "NodeNext",            // or "ESNext", or "Preserve" (with bundler)
  "moduleResolution": "NodeNext",  // must match module strategy
  "target": "ES2022"               // or "ESNext"; align to your runtime baseline
}
```

**`module`** — what kind of module syntax is emitted:
- `NodeNext` / `Node16` — Node.js native ESM/CJS dual-mode resolution
- `ESNext` — pure ESM, output as ESM
- `Preserve` — TypeScript-syntax-stripping only, leaves your imports alone (for bundlers like esbuild)
- `CommonJS` — legacy CJS output

**`moduleResolution`** — how `import "./foo"` resolves:
- `NodeNext` / `Node16` — Node.js modern resolution (file extensions in imports, `package.json` `exports`)
- `Bundler` — relaxed resolution for bundler use (no `.js` extension required)
- `Node` (legacy) — Node.js classic resolution

**`target`** — what JS version the emitted code targets:
- `ES2022` — modern syntax, supported in Node 18+ and current evergreen browsers
- `ESNext` — latest stable spec; check that your runtime supports it
- Older targets (`ES2020`, `ES2019`, etc.) only when you genuinely target older runtimes

**Pick one strategy and align all three flags.** The most common mistake: `module: "ESNext"` with `moduleResolution: "Node"` — works but doesn't match how your runtime actually resolves at runtime, leading to "works in TypeScript, broken at runtime" surprises.

## Other Flags Worth Knowing

| Flag | What it does | Recommendation |
|---|---|---|
| `skipLibCheck: true` | Skip type-checking declaration files in `node_modules` | Enable — drastic speedup, downside is rare |
| `resolveJsonModule: true` | Allow `import data from "./foo.json"` | Enable if you import JSON |
| `allowSyntheticDefaultImports: true` | Allow `import x from "cjs-module"` | Enable for CJS interop; `esModuleInterop` implies this |
| `esModuleInterop: true` | Make CJS interop "just work" | Enable unless you're sure you don't need it |
| `declaration: true` | Emit `.d.ts` files | Enable for libraries; not for app code |
| `declarationMap: true` | Source maps for `.d.ts` | Enable when `declaration: true` |
| `sourceMap: true` | Source maps for `.js` | Enable in development; choose per-build for production |
| `incremental: true` | Faster repeat builds via cache | Enable for development |
| `noEmit: true` | Don't emit JS — just type-check | Enable when a separate tool (esbuild, swc) emits |
| `lib` | Which built-in lib types to include | `["ES2022", "DOM"]` for browser; `["ES2022"]` for server |

## When *Not* to Enable a Strict Flag

The honest cases:

- **`exactOptionalPropertyTypes`** in a project that interops heavily with libraries that pass `undefined` for optional fields. The friction is real. Workaround: enable it, and use `T | undefined` (instead of `?: T`) at interop boundaries.
- **`noUncheckedIndexedAccess`** in a project that does heavy index-based access on guaranteed-fixed-length tuples or matrices. Workaround: enable it, and use destructuring or non-null assertion (`!`) only at the genuinely-safe sites.
- **`noUnusedParameters`** in a project where many functions accept positional callbacks with unused args. Workaround: prefix with `_`.

Disabling a flag should be the last resort, with a comment in the `tsconfig.json` explaining why. Most "this flag is too strict" reactions become "this flag found a real bug" two days later.

## Common Pitfalls

- **`"strict": false` because turning it on flags too many issues.** Most of those issues are bugs. Schedule the migration; don't permanently disable.
- **Enabling `strict` on individual sub-flags but not `strict` itself.** New strict sub-flags get added in TS releases; you miss them. Use the umbrella.
- **`any` everywhere because `noImplicitAny` is annoying.** `unknown` is the right escape hatch for "I don't know what this is yet."
- **Forgetting `noUncheckedIndexedAccess` and writing `arr[0].name` confidently.** Production crashes from out-of-bounds indexing are entirely preventable.
- **Mixing `module` strategies in one repo.** Pick one. The interop story for mixed CJS/ESM is full of corner cases.
- **Targeting old JS to "support" old Node versions you don't actually run.** Set `target` to what your *actual* runtime supports. Older targets emit larger code with worse performance.
- **`skipLibCheck: false` in a large project.** Rebuilding type-checks every dependency on every change. Just enable it.
- **No `tsconfig.json` for tests.** A separate `tsconfig.test.json` extending the main config lets you relax `noUnusedLocals` (helpful for partial setup) without affecting source code.
- **`include`/`exclude` that misses files.** Run `tsc --listFiles` to see what's actually being checked. Often surprising.
- **`paths` aliases that work at compile but break at runtime.** TypeScript resolves `paths` for type-checking; the runtime doesn't know about them. Use a bundler or runtime-side path mapping (`tsx`, `tsconfig-paths`) to keep them aligned.
