# Example Dockerfiles

These are starting points. Before using one:

- Replace the version tags with the project's runtime version, and check that the tag exists (`docker buildx imagetools inspect <image:tag>`).
- For production, pin digests (`FROM image:tag@sha256:...`) using the real digest from that command. Never invent one.
- Adjust paths, build commands, ports and entrypoints to the project.

All examples need BuildKit (the default builder in current Docker releases) for `RUN --mount`.

## Node.js (npm)

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM deps AS build
COPY . .
RUN npm run build \
 && npm prune --omit=dev

FROM node:22-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
# Files stay owned by root (read-only for the app); the image's built-in "node" user runs it.
COPY --from=build /app/package.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
USER node
EXPOSE 3000
# Node as PID 1 must handle SIGTERM itself, or run with `docker run --init` / tini.
CMD ["node", "dist/server.js"]
```

- pnpm or yarn: copy their lockfile (`pnpm-lock.yaml`, `yarn.lock`) instead and use the matching frozen-lockfile install (`pnpm install --frozen-lockfile`, `yarn install --immutable` for Yarn Berry). Enable them with Corepack if the project does.
- Apps without a build step: drop the `build` stage's `npm run build`, and copy the source directory instead of `dist`.

## Python (pip + virtual environment)

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS build
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY . .
USER 10001
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
```

- The virtual environment is copied between stages that use the same base image, so its paths stay valid.
- If dependencies need compiling (no wheel available), install build tools (`build-essential`, headers) **only in the build stage**.
- **uv** projects: install uv in the build stage (the uv docs show a pinned `COPY --from=ghcr.io/astral-sh/uv:<version> /uv /bin/` line), then run `uv sync --locked --no-dev`. Follow the uv Docker guide for the current flags.
- Poetry projects: export or install from `poetry.lock` with the dev group excluded. Check the Poetry docs for the version in use.
- ASGI apps: replace the gunicorn command with the project's server, for example `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

## Go (static binary on distroless)

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.27 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/app"]
```

- `distroless/static` includes CA certificates, time zone data and a `nonroot` user, but no libc. That is why the build uses `CGO_ENABLED=0`.
- If the binary needs cgo (for example SQLite through cgo), use `gcr.io/distroless/base-debian12:nonroot` and build without `CGO_ENABLED=0`.
- Match the `golang` tag to the `go` directive in `go.mod`.

## Java (Maven, Spring Boot style fat jar)

```dockerfile
# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 mvn -B -q dependency:go-offline
COPY src ./src
# Tests run in CI before the image build; skip them here to avoid running them twice.
RUN --mount=type=cache,target=/root/.m2 mvn -B -q package -DskipTests

FROM eclipse-temurin:21-jre
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /src/target/*.jar app.jar
USER 10001
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
```

- Make sure the `COPY --from=build /src/target/*.jar` glob matches exactly one jar. If the build produces several, name the jar explicitly.
- Modern JVMs (JDK 10+) respect container memory limits. `-XX:MaxRAMPercentage` sizes the heap as a share of the container limit; leave headroom for non-heap memory.
- Gradle: use a `gradle:<ver>-jdk<jdk>` build image, or the project's `./gradlew`, with `--mount=type=cache,target=/root/.gradle`. The output is under `build/libs/`. Spring Boot's Gradle plugin also writes a `-plain.jar`, so copy the boot jar by name.
- Spring Boot can also split the jar into layers for better caching; see the Spring Boot docs on "layered jars".

## .NET (ASP.NET Core)

```dockerfile
# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY src/MyApp/MyApp.csproj src/MyApp/
RUN --mount=type=cache,target=/root/.nuget/packages \
    dotnet restore src/MyApp/MyApp.csproj
COPY . .
RUN --mount=type=cache,target=/root/.nuget/packages \
    dotnet publish src/MyApp/MyApp.csproj -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .
# .NET 8+ images define a non-root "app" user and its UID in $APP_UID; they listen on 8080 by default.
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "MyApp.dll"]
```

- Copy every `.csproj` the app references (and `Directory.Build.props`, `Directory.Packages.props`, `NuGet.config` if present) before `dotnet restore`, so restore is cached.
- Smaller runtime images: the chiseled variants of `aspnet` (no shell or package manager). Check the available tags for your .NET version on the Microsoft Artifact Registry.
- Self-contained or Native AOT publishes can use the `runtime-deps` image instead of `aspnet`.

## Adding tini (when the platform has no `--init`)

```dockerfile
# Debian/Ubuntu-based runtime stage
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "dist/server.js"]
```

On Alpine: `RUN apk add --no-cache tini`, then `ENTRYPOINT ["/sbin/tini", "--"]`.

## Entrypoint script pattern

When the container must do setup before starting (for example rendering a config file), keep the script small and `exec` the real process, so it receives signals as PID 1 (or as tini's child):

```sh
#!/bin/sh
set -eu
# ...setup steps...
exec "$@"
```

```dockerfile
# --chmod sets the executable bit even when the file was checked out on Windows
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["node", "dist/server.js"]
```

Do not run database migrations automatically from the entrypoint of every replica. Run them as a separate, single job in the deploy pipeline.
