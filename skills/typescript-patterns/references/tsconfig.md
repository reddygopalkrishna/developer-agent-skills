# tsconfig guide

Always check the installed TypeScript version (`npx tsc -v`) and the effective config (`npx tsc --showConfig`) before editing. Option defaults change between major versions.

## Pick `module` and `moduleResolution` by how the code runs

| The code is... | `module` | `moduleResolution` | Notes |
|---|---|---|---|
| Bundled for the browser (Vite, webpack, Next.js, esbuild) | `ESNext` or `Preserve` | `Bundler` | Set `noEmit: true`; the bundler emits JS |
| Run by Node.js as ESM or CJS | `NodeNext` | `NodeNext` | Follows `"type"` in package.json; ESM relative imports need `.js` extensions |
| A library published to npm | `NodeNext` | `NodeNext` | Strictest resolution; works for both ESM and CJS consumers |
| Run by Deno or Bun | follow the runtime docs | | Both run TS directly |

Don't use the legacy `moduleResolution: "node"` (also called `node10`) in new projects.

## Baseline: bundled frontend app

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "noEmit": true,

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,

    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

Drop `jsx` if the project has no JSX. Frameworks often generate their own tsconfig (Next.js, Vite templates, Angular); extend or adjust it rather than replacing it, and keep the options the framework needs.

## Baseline: Node.js service (ESM)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": "src",
    "outDir": "dist",
    "sourceMap": true,

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,

    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

- Requires `"type": "module"` in package.json. For a CommonJS service, remove `verbatimModuleSyntax` (with CJS output it requires `import x = require("x")` syntax).
- Choose `target` to match the oldest Node version you run. Check the Node release's supported ECMAScript features if unsure.
- Install `@types/node` that matches the Node major version you run, and list it in `"types": ["node"]` (from TypeScript 6.0, `types` defaults to `[]` and `@types` packages are no longer picked up automatically).

## Baseline: npm library

Start from the Node config and add:

```json
{
  "compilerOptions": {
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  }
}
```

- Add `"exports"` and `"types"` fields to package.json, and check the published package with a tool such as `@arethetypeswrong/cli` (`npx @arethetypeswrong/cli --pack .`).
- `isolatedDeclarations` (5.5+) makes declaration output fast and parallelizable but requires explicit types on all exports. Consider it for large libraries.

## Monorepos

- Put shared options in `tsconfig.base.json` and `extends` it from each package.
- Use project references (`"composite": true` in referenced projects, `"references": [{ "path": "../core" }]` in consumers) and `tsc -b` for incremental builds across packages.
- Make sure each package's `include` covers only its own source, or files get type-checked twice.

## Option notes and tradeoffs

| Option | Recommendation |
|---|---|
| `strict` | Always on. Enables the whole strict family, including flags added in future versions |
| `noUncheckedIndexedAccess` | On for new code. For `for (const x of arr)` loops nothing changes; only index access gets `\| undefined` |
| `exactOptionalPropertyTypes` | On for new code where libraries cooperate; it distinguishes "missing" from "explicitly undefined" |
| `noPropertyAccessFromIndexSignature` | Optional. Forces `obj["key"]` for index-signature properties, which flags dynamic keys visually |
| `noImplicitReturns` | On; catches functions that forget to return in one branch |
| `noUnusedLocals`, `noUnusedParameters` | Usually leave to the linter so they don't block compiles during refactors |
| `skipLibCheck` | On in apps for speed. It also skips your own `.d.ts` files, so libraries that ship hand-written declarations may want it off in CI |
| `allowJs`, `checkJs` | Use during JS-to-TS migrations; `checkJs` with JSDoc types gives checking before renaming files |
| `erasableSyntaxOnly` (5.8+) | Turn on when running `.ts` directly with Node's built-in type stripping. It errors on `enum`, runtime `namespace`, parameter properties and `import =` |
| `paths` | Only mirrors what the bundler or runtime resolves. Configure the same aliases there (Vite `resolve.alias`, package.json `imports`), or builds break at runtime |

## Migrating an existing codebase to stricter settings

Never turn on `strict` everywhere in one PR on a large codebase. The fixes get rushed and people paper over errors with `any` and `!`.

1. **Measure.** Turn the flag on locally and count errors per directory: `npx tsc --noEmit -p tsconfig.json | grep -c "error TS"` (or `Select-String -Pattern "error TS"` in PowerShell).
2. **Create a stricter config for migrated code:**

   ```json
   {
     "extends": "./tsconfig.json",
     "compilerOptions": { "strict": true, "noUncheckedIndexedAccess": true },
     "include": ["src/billing", "src/auth"]
   }
   ```

   Save it as `tsconfig.strict.json` and run `npx tsc --noEmit -p tsconfig.strict.json` in CI alongside the normal check.
3. **Grow the `include` list** one directory or module at a time, fixing real problems rather than suppressing them.
4. **Enable flags one at a time** if the error count is large: `noImplicitAny` and `strictNullChecks` give most of the value; do them first.
5. **When everything is included,** move the flags into the main tsconfig and delete the strict config.
6. **Prevent regression** with lint rules such as `@typescript-eslint/no-explicit-any`, `no-non-null-assertion` and `ban-ts-comment` (from typescript-eslint).

## Debugging config problems

- `npx tsc --showConfig` prints the final merged config.
- `npx tsc --explainFiles` shows why each file is included.
- `npx tsc --traceResolution` explains how an import was resolved, which helps with "Cannot find module" errors.
- `npx tsc --extendedDiagnostics` reports timings when type-checking is slow.
