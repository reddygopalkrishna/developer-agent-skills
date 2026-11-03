# Micro-frontend decision matrix

## Step 1: should this be micro-frontends at all?

Answer each question. Two or more "no" answers mean a modular monolith is the better choice.

| Question | Yes means |
|---|---|
| Are there at least two or three teams that ship to the same frontend? | Coordination cost is real |
| Do releases regularly wait on another team's changes or QA? | Independent deploys pay off |
| Can the product be divided into areas that one team owns end to end? | Vertical split is possible |
| Do most features stay inside one area? | Contracts between apps stay small |
| Is there a platform owner (person or team) for the shell, design system and shared tooling? | Someone keeps the whole working |
| Is the organization ready to run several pipelines and monitor several apps? | Operational cost is affordable |

Modular monolith checklist (the alternative): one app, `CODEOWNERS` per area, enforced import boundaries, a shared design system package, and build caching so CI stays fast.

## Step 2: score the composition approaches

Score each approach 1 (poor) to 3 (good) for the project's priorities, then weight the criteria that matter most.

| Criterion | Separate apps per route | Module Federation | Import maps + ESM / single-spa | Web Components | iframes | Server/edge composition |
|---|---|---|---|---|---|---|
| Independent deployment | 3 | 3 | 3 | 3 | 3 | 3 |
| Multiple teams on one page | 1 | 3 | 3 | 3 | 2 | 2 |
| Mixed frameworks | 3 | 1 | 3 | 3 | 3 | 3 |
| Runtime isolation (CSS, JS, failures) | 3 | 1 | 1 | 2 | 3 | 2 |
| Performance (no duplicate runtimes, few round trips) | 2 | 3 | 2 | 2 | 1 | 3 |
| SEO and server rendering | 3 | 2 | 1 | 1 | 1 | 3 |
| Accessibility and focus handling | 3 | 3 | 3 | 2 | 1 | 3 |
| Setup and operating simplicity | 3 | 2 | 1 | 2 | 3 | 1 |
| Debugging and local development | 3 | 2 | 1 | 2 | 2 | 1 |

These scores are typical starting points, not facts about every project. Adjust them for the team's experience and stack.

## Common choices

| Situation | Usual choice |
|---|---|
| Areas rarely appear on the same page (marketing, shop, account) | Separate apps per route behind one domain; share header and footer as a package or a small Web Component |
| One framework everywhere, several teams compose a single page | Module Federation |
| Migrating from AngularJS, Backbone or another legacy framework | single-spa or Module Federation with an adapter, using the strangler plan below |
| Widgets embedded in many host apps you don't control | Web Components with Shadow DOM, versioned and loaded from a CDN |
| Untrusted or third-party UI | iframes with `sandbox` and a `postMessage` contract that checks `event.origin` |
| SEO-heavy content pages with a few interactive islands | Server or edge composition with client-side islands |

## Strangler migration from a legacy frontend

1. **Put a proxy or shell in front of the legacy app** so every route still goes to the old app by default. Ship this with no user-visible change.
2. **Pick the first slice**: a route with clear ownership, low coupling and real business value, not the hardest page.
3. **Build it in the new stack** as its own app or MFE, behind a feature flag or for a percentage of traffic.
4. **Share session and design**: same cookie domain and auth, and a design-system bridge (shared CSS tokens) so users don't notice the seam.
5. **Switch the route** to the new implementation; keep the old route available for quick rollback.
6. **Repeat** route by route. Track the share of traffic served by the new stack.
7. **Remove the legacy app** when its last route is migrated. Delete the adapters and shims; they are not meant to stay.

Rules during migration:

- No new features in the legacy app for areas that are being migrated; otherwise the target keeps moving.
- Contracts between old and new code are URL- and event-based, never shared global state.
- Measure Core Web Vitals and error rates on both sides; the new version must not be slower.

## Questions to answer in the ADR

- Which teams own which routes and MFEs?
- Which composition approach, and why the simpler options were not enough?
- Which dependencies are shared singletons, and what is the supported version range?
- What are the contracts (mount API, events, URL parameters) and where are they versioned?
- How is each MFE deployed, versioned, cached and rolled back?
- What happens when a remote fails to load?
- Who owns the shell and the design system?
