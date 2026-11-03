# Ecosystem Command Reference

Commands for inventory, upgrade, audit and tree inspection. Run them from the project root. If a command is missing in the installed version, check `<tool> --help` rather than guessing.

## JavaScript / TypeScript

### npm

| Task | Command |
|---|---|
| List outdated | `npm outdated` |
| Update within declared ranges | `npm update` or `npm update <pkg>` |
| Install a specific version | `npm install <pkg>@<version>` |
| Audit | `npm audit` (production only: `npm audit --omit=dev`) |
| Apply non-breaking audit fixes | `npm audit fix` (avoid `--force`) |
| Why is a package installed | `npm explain <pkg>` or `npm ls <pkg>` |
| Reproducible install in CI | `npm ci` |
| Force a transitive version | `"overrides": { "<pkg>": "<version>" }` in `package.json` |
| Bump ranges to latest (third-party) | `npx npm-check-updates` to preview, `npx npm-check-updates -u` to write |

### pnpm

| Task | Command |
|---|---|
| List outdated | `pnpm outdated` |
| Update within ranges | `pnpm update` or `pnpm update <pkg>` |
| Update to latest, ignoring ranges | `pnpm update --latest <pkg>` |
| Install a specific version | `pnpm add <pkg>@<version>` |
| Audit | `pnpm audit` |
| Why is a package installed | `pnpm why <pkg>` |
| Reproducible install in CI | `pnpm install --frozen-lockfile` |
| Force a transitive version | `overrides` — in `pnpm-workspace.yaml` on recent pnpm versions, or `"pnpm": { "overrides": { ... } }` in `package.json` on older ones; check the pnpm docs for the installed version |

### Yarn

| Task | Yarn 1 (classic) | Yarn 2+ (berry) |
|---|---|---|
| List outdated | `yarn outdated` | `yarn upgrade-interactive` (built in from Yarn 4; a plugin in 2-3) |
| Upgrade a package | `yarn upgrade <pkg>@<version>` | `yarn up <pkg>@<version>` |
| Audit | `yarn audit` | `yarn npm audit` |
| Why is a package installed | `yarn why <pkg>` | `yarn why <pkg>` |
| Reproducible install in CI | `yarn install --frozen-lockfile` | `yarn install --immutable` |
| Force a transitive version | `"resolutions"` in `package.json` | `"resolutions"` in `package.json` |

## Python

### pip / pip-tools

| Task | Command |
|---|---|
| List outdated | `pip list --outdated` |
| Upgrade one package | `pip install -U <pkg>` |
| Recompile pinned requirements for one package | `pip-compile --upgrade-package <pkg> requirements.in` |
| Recompile everything | `pip-compile --upgrade requirements.in` |
| Audit | `pip-audit` (or `pip-audit -r requirements.txt`) |
| Dependency tree | `pipdeptree` (reverse lookup: `pipdeptree -r -p <pkg>`) |
| Force a transitive version | constraints file: `pip install -r requirements.txt -c constraints.txt` |

### uv

| Task | Command |
|---|---|
| Show tree with available upgrades | `uv tree --outdated` |
| Upgrade one package in the lockfile | `uv lock --upgrade-package <pkg>` |
| Upgrade everything in the lockfile | `uv lock --upgrade` |
| Add or change a requirement | `uv add "<pkg>>=2.0"` |
| Install exactly the lockfile | `uv sync --locked` |
| Audit | `uv export --format requirements-txt > /tmp/req.txt` then `pip-audit -r /tmp/req.txt` |
| Force a transitive version | `[tool.uv] override-dependencies = ["<pkg>==<version>"]` in `pyproject.toml` |

### Poetry

| Task | Command |
|---|---|
| List outdated | `poetry show --outdated` |
| Update within constraints | `poetry update <pkg>` |
| Change a constraint | `poetry add <pkg>@^2.0` |
| Dependency tree | `poetry show --tree` |

## Go

| Task | Command |
|---|---|
| List available upgrades | `go list -m -u all` |
| Upgrade one module | `go get example.com/mod@v1.4.2` (or `@latest`) |
| Patch-level upgrades of all deps | `go get -u=patch ./...` |
| Minor and patch upgrades of all deps | `go get -u ./...` (review carefully) |
| Clean up go.mod / go.sum | `go mod tidy` |
| Why is a module needed | `go mod why -m example.com/mod` |
| Full graph | `go mod graph` |
| Vulnerabilities with reachability | `go install golang.org/x/vuln/cmd/govulncheck@latest`, then `govulncheck ./...` |
| Change Go version | `go mod edit -go=<version>` |
| Major v2+ upgrade | change imports to `example.com/mod/v2` and `go get example.com/mod/v2@latest` |

## Java / Kotlin

### Maven

| Task | Command |
|---|---|
| Outdated dependencies | `mvn versions:display-dependency-updates` |
| Outdated plugins | `mvn versions:display-plugin-updates` |
| Dependency tree | `mvn dependency:tree` (filter: `-Dincludes=<groupId>:<artifactId>`) |
| Force a transitive version | declare it in `<dependencyManagement>` |
| Vulnerability scan | OWASP Dependency-Check: `mvn org.owasp:dependency-check-maven:check` |

### Gradle

| Task | Command |
|---|---|
| Dependency tree | `./gradlew dependencies --configuration runtimeClasspath` |
| Why is a version selected | `./gradlew dependencyInsight --dependency <name> --configuration runtimeClasspath` |
| Outdated (Ben Manes versions plugin) | `./gradlew dependencyUpdates` |
| Upgrade the Gradle wrapper | `./gradlew wrapper --gradle-version <version>` |
| Force a transitive version | `constraints { implementation("<group>:<name>:<version>") }` |

Versions often live in `gradle/libs.versions.toml` (version catalog); edit them there.

## C# / .NET (NuGet)

| Task | Command |
|---|---|
| List outdated | `dotnet list package --outdated` |
| List vulnerable, including transitive | `dotnet list package --vulnerable --include-transitive` |
| Full transitive list | `dotnet list package --include-transitive` |
| Add or upgrade a package | `dotnet add package <Name> --version <version>` |
| Central versions | edit `Directory.Packages.props` when the repo uses central package management |
| Force a transitive version | add a direct `PackageReference`, or enable transitive pinning with central package management |
| SDK version | `global.json` |

Recent .NET SDKs run NuGet audit during restore and report known vulnerabilities as warnings; do not suppress them without a reason.

## Rust (Cargo)

| Task | Command |
|---|---|
| Update within `Cargo.toml` ranges | `cargo update` |
| Update one crate | `cargo update -p <crate>` |
| Pin an exact version | `cargo update -p <crate> --precise <version>` |
| Who depends on a crate | `cargo tree -i <crate>` |
| Duplicate versions | `cargo tree -d` |
| Audit | `cargo install cargo-audit`, then `cargo audit` |
| Outdated | `cargo install cargo-outdated`, then `cargo outdated` |
| Policy checks (licenses, bans, advisories) | `cargo deny check` (cargo-deny) |
| Force or patch a crate | `[patch.crates-io]` in `Cargo.toml` |

## Cross-ecosystem scanners

| Tool | Command |
|---|---|
| OSV-Scanner | v1: `osv-scanner -r .`; v2: `osv-scanner scan source -r .` (check `osv-scanner --version`) |
| Trivy | `trivy fs .` |
| Grype | `grype dir:.` |
