# Codemod Tooling Guide

A codemod is a program that rewrites code using its syntax tree instead of text matching. Use one whenever the same change repeats across many files.

## Workflow

1. **Write fixtures first:** a few input files and the exact expected output, including edge cases (comments, aliases, multi-line calls, generated code).
2. **Run on fixtures** until output matches exactly.
3. **Dry run on the real codebase** and read the diff for a sample of files from different directories.
4. **Exclude** generated code, vendored code, build output and lockfiles.
5. **Apply, then run the project's formatter** so only meaningful changes remain.
6. **Build and run the tests.**
7. **Commit the codemod output separately** from manual fixes, with the exact command in the commit message, so reviewers can review the transform and reproduce it instead of reading thousands of lines.

## Choosing a tool

| Language | Tool | Best for |
|---|---|---|
| JS/TS | jscodeshift | Classic AST transforms; large ecosystem of existing transforms |
| TS | ts-morph | Changes that need type information (rename a symbol and all its references) |
| Many languages | ast-grep | Pattern-based search and rewrite with readable patterns |
| Java/Kotlin | OpenRewrite | Framework and Java version migrations with ready-made recipes |
| Python | LibCST | Transforms that preserve formatting and comments |
| Python | pyupgrade / Ruff `UP` rules | Modernizing syntax to a newer Python version |
| C#/.NET | Roslyn analyzers and code fixes | Organization-specific patterns; built-in fixes via `dotnet format` |
| Go | `gofmt -r`, `go fix` | Simple expression rewrites; Go API updates |
| Rust | `cargo fix`, `cargo clippy --fix` | Edition migrations and lint fixes |
| Any | Comby | Structural search and replace across languages without a full parser |

Use `sed` or plain regex only for trivial, unambiguous text changes.

## JavaScript / TypeScript

### jscodeshift

```bash
# Preview without writing files
npx jscodeshift -t transform.js src --extensions=ts,tsx --parser=tsx --dry --print

# Apply
npx jscodeshift -t transform.js src --extensions=ts,tsx --parser=tsx
```

Transform skeleton:

```js
// transform.js: rename calls of oldApi(...) to newApi(...)
export default function transformer(file, api) {
  const j = api.jscodeshift;
  return j(file.source)
    .find(j.CallExpression, { callee: { name: "oldApi" } })
    .forEach((path) => {
      path.node.callee.name = "newApi";
    })
    .toSource();
}
```

Test transforms with fixture pairs using the `defineTest` helper from `jscodeshift/dist/testUtils`.

### ts-morph

Use when the change depends on types or must update every reference:

```ts
import { Project } from "ts-morph";

const project = new Project({ tsConfigFilePath: "tsconfig.json" });
const file = project.getSourceFileOrThrow("src/services/user.ts");
file.getFunctionOrThrow("getUser").rename("fetchUser"); // updates all references
await project.save();
```

### ast-grep

```bash
# Search
ast-grep run --pattern 'console.log($$$ARGS)' --lang ts

# Rewrite interactively
ast-grep run --pattern 'console.log($$$ARGS)' --rewrite 'logger.debug($$$ARGS)' --lang ts --interactive

# Rewrite all matches
ast-grep run --pattern 'console.log($$$ARGS)' --rewrite 'logger.debug($$$ARGS)' --lang ts --update-all
```

`$VAR` matches one node; `$$$VAR` matches zero or more. For repeatable migrations, put rules in YAML files and run `ast-grep scan`.

### Framework codemods

Many frameworks ship official codemods with their upgrade guides (for example `ng update` for Angular and `npx @next/codemod` for Next.js). Always check the framework's migration guide first; an official transform beats a custom one.

## Java / Kotlin: OpenRewrite

Maven, without changing the POM:

```bash
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-migrate-java:RELEASE \
  -Drewrite.activeRecipes=org.openrewrite.java.migrate.UpgradeToJava21
```

Use the `dryRun` goal instead of `run` to produce a patch file under `target/rewrite/` for review. Gradle uses the `org.openrewrite.rewrite` plugin with `rewriteDryRun` and `rewriteRun` tasks. Recipes exist for Java version upgrades, Spring Boot upgrades, `javax` to `jakarta`, JUnit 4 to 5 and more; check the OpenRewrite recipe catalog for exact names.

## Python

### LibCST

```bash
python -m libcst.tool initialize .            # creates .libcst.codemod.yaml
python -m libcst.tool codemod mymodule.MyCommand src/
```

A codemod is a `VisitorBasedCodemodCommand` (or a plain `cst.CSTTransformer`) that overrides `leave_*` methods, for example `leave_Call`, and returns the updated node. LibCST keeps comments and formatting intact.

### Syntax modernization

```bash
pyupgrade --py311-plus $(git ls-files '*.py')
ruff check --select UP --fix .
```

## C# / .NET

- Apply fixes for a specific diagnostic across a solution: `dotnet format analyzers --diagnostics <ID>` (for example a CA or IDE rule ID). Add `--verify-no-changes` in CI to enforce it.
- For organization-specific migrations, write a Roslyn `DiagnosticAnalyzer` plus a `CodeFixProvider`, test it with the Roslyn analyzer testing packages, and ship it as a NuGet package so the fix also works in IDEs.

## Go

```bash
# Expression rewrite (pattern -> replacement), applied in place
gofmt -r 'bytes.Compare(a, b) == 0 -> bytes.Equal(a, b)' -w .

# Apply Go's own API fixers
go fix ./...
```

In `gofmt -r`, single lowercase letters act as wildcards.

## Rust

```bash
cargo fix --edition          # prepare code for the next edition
cargo clippy --fix           # apply machine-applicable lint suggestions
```

## Comby (language-agnostic)

```bash
comby 'oldFn(:[args])' 'newFn(:[args])' .go -i   # -i writes changes in place
```

Omit `-i` to preview the diff.

## Reviewing codemod output

- Read a sample of changed files from every top-level directory, not just the first few.
- Grep for leftovers the codemod missed (dynamic calls, string-based references, reflection, templates).
- Check that generated and vendored files were not touched.
- Confirm the formatter ran and the diff contains only intended changes.
