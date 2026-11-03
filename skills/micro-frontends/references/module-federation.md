# Module Federation setup and debugging

Module Federation lets one build (the **remote**) expose modules that another build (the **host**) loads at runtime, with shared dependencies negotiated between them.

Several implementations exist and their APIs differ:

- The plugin built into **webpack 5** (`webpack.container.ModuleFederationPlugin`), shown below.
- **Module Federation 2.0** (`@module-federation/enhanced` and related packages), which works with webpack and Rspack and adds a runtime API, manifests and type generation.
- Plugins for **Vite** and others.

Before writing config, check which package and version the project uses, and check the installed version's docs. This applies especially to the Module Federation 2.0 runtime API (how remotes are registered and loaded at runtime) and to manifest and type-generation options, which have changed between releases.

## Remote (webpack 5 core plugin)

```js
// checkout/webpack.config.js
const { ModuleFederationPlugin } = require("webpack").container;
const deps = require("./package.json").dependencies;

module.exports = {
  output: {
    publicPath: "auto",     // resolve chunk URLs relative to where remoteEntry.js was loaded from
    uniqueName: "checkout", // avoid runtime collisions between builds
  },
  plugins: [
    new ModuleFederationPlugin({
      name: "checkout",
      filename: "remoteEntry.js",
      exposes: {
        "./CheckoutPage": "./src/CheckoutPage",
      },
      shared: {
        react: { singleton: true, requiredVersion: deps.react },
        "react-dom": { singleton: true, requiredVersion: deps["react-dom"] },
      },
    }),
  ],
};
```

## Host (webpack 5 core plugin)

```js
// shell/webpack.config.js
const { ModuleFederationPlugin } = require("webpack").container;
const deps = require("./package.json").dependencies;

module.exports = {
  plugins: [
    new ModuleFederationPlugin({
      name: "shell",
      remotes: {
        checkout: "checkout@https://checkout.example.com/remoteEntry.js",
      },
      shared: {
        react: { singleton: true, requiredVersion: deps.react },
        "react-dom": { singleton: true, requiredVersion: deps["react-dom"] },
      },
    }),
  ],
};
```

Hard-coded remote URLs are fine for a first spike. For real environments, load the remote URL from a per-environment manifest at runtime (a promise-based remote, or the Module Federation 2.0 runtime API), so each MFE can be deployed and rolled back without rebuilding the host.

## The async boundary (required)

Shared modules are negotiated asynchronously, so the app's real entry must load after a dynamic import:

```js
// src/index.js
import("./bootstrap");
```

```js
// src/bootstrap.js: the real entry point
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")).render(<App />);
```

Without this, webpack fails with "Shared module is not available for eager consumption". Do this in both host and remotes. Avoid `eager: true` on shared modules as a workaround; it puts the dependency in the initial chunk and defeats sharing.

## Consuming a remote module in the host

```tsx
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

const CheckoutPage = lazy(() => import("checkout/CheckoutPage"));

export function CheckoutRoute() {
  return (
    <ErrorBoundary fallback={<p>Checkout is unavailable right now. Please try again.</p>}>
      <Suspense fallback={<p>Loading checkout…</p>}>
        <CheckoutPage />
      </Suspense>
    </ErrorBoundary>
  );
}
```

Add a timeout around remote loading if the remote can hang (a promise race against a timer that rejects), so the fallback shows instead of an endless spinner.

## TypeScript types for remotes

Minimal approach, declared in the host:

```ts
// src/remotes.d.ts
declare module "checkout/CheckoutPage" {
  import type { ComponentType } from "react";
  const CheckoutPage: ComponentType<{ cartId?: string }>;
  export default CheckoutPage;
}
```

Better: the remote publishes its exposed module types (Module Federation 2.0 can generate and download them; check the installed version's docs), or a shared contracts package defines the props, so a breaking change fails the host's type check.

## Shared dependency options

| Option | Effect |
|---|---|
| `singleton: true` | Only one copy is loaded on the page. Use for React, React DOM, the router if it holds global state, and the design system if it uses context |
| `requiredVersion` | The semver range this build accepts. With a singleton, a mismatch logs a warning and uses the loaded copy anyway |
| `strictVersion: true` | Fails instead of warning on mismatch. Use when a mismatch would definitely break |
| `eager: true` | Bundles the dependency into the initial chunk. Avoid except for special cases |

Keep the shared list short. Everything else stays bundled per MFE.

## Deployment and caching

- Deploy each remote build to a versioned path (`/checkout/1.42.0/`), with hashed chunk files cached as `immutable`.
- Serve `remoteEntry.js` (or the manifest) with `Cache-Control: no-cache`, or reference the versioned URL through a runtime manifest.
- Enable CORS on the remote's origin for the host's origin if they differ.
- Ask before changing production manifests or CDN rules.

## Common errors

| Symptom | Likely cause | Fix |
|---|---|---|
| "Shared module is not available for eager consumption" | No async boundary | Add the `import("./bootstrap")` entry |
| "Invalid hook call" or hooks behave strangely | Two copies of React on the page | Make `react` and `react-dom` singletons in host and every remote; align version ranges |
| `ScriptExternalLoadError` or remote fails to load | Wrong URL, CORS, remote not deployed, network | Check the URL in the browser, CORS headers and the deploy; make sure the fallback UI shows |
| Chunks load from the host's origin and 404 | Remote `publicPath` wrong | Set `output.publicPath: "auto"` or the remote's absolute URL |
| Shared dependency loaded twice | Version ranges don't overlap, or not marked shared in one build | Align `requiredVersion` ranges across builds; check each build's config |
| Works locally, breaks in production | Remote URL or manifest differs per environment; caching of `remoteEntry.js` | Use a per-environment manifest; set `no-cache` on the entry file |
| CSS from one MFE changes another | Global selectors | Scope CSS (modules, prefixes, layers, Shadow DOM); only the shell sets global styles |

## Local development

- Run the shell with remotes pointing at local dev servers, or at the staging versions of remotes you are not changing (configurable through the manifest or environment variables).
- Give every dev server a fixed port and document it.
- Test the integrated build, not only each remote in isolation, before merging changes to exposed modules or shared versions.
