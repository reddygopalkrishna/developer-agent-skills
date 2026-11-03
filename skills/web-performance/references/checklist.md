# Web performance audit checklist

Work through the areas in order; earlier ones usually matter more. Mark each item pass, fail or not applicable, and note the evidence (a measurement, a header, a screenshot of the waterfall).

## 1. Measurement in place

- [ ] Field data exists for key templates (RUM, or CrUX via PageSpeed Insights / Search Console).
- [ ] Metrics are reported at p75, split by mobile and desktop.
- [ ] Lab tests run against a production build with CPU and network throttling.
- [ ] There is a baseline recorded before changes.

## 2. Server and network

- [ ] TTFB is under 0.8 s at p75. If not, check server timing, database calls and cache hit rate.
- [ ] HTML is served from a CDN or edge, or cached where it can be.
- [ ] No redirect chains on entry URLs (`http` → `https` → `www` → path).
- [ ] HTTP/2 or HTTP/3 is enabled.
- [ ] Text assets (HTML, CSS, JS, JSON, SVG) are compressed with Brotli or gzip.
- [ ] `preconnect` is used for the one or two critical third-party origins, and not for many.
- [ ] Consider `103 Early Hints` if the server and CDN support it and TTFB is high.

## 3. HTML and the critical path

- [ ] The main content is in the server-rendered HTML (SSR, SSG or pre-render), not built entirely by client JavaScript.
- [ ] Render-blocking CSS is small; critical CSS is inlined for above-the-fold content where it helps.
- [ ] Scripts use `defer` or `type="module"`; no synchronous scripts in `<head>` unless required.
- [ ] The LCP resource is discoverable in the initial HTML.

## 4. Images

- [ ] The LCP image has `fetchpriority="high"` and no `loading="lazy"`.
- [ ] Below-the-fold images use `loading="lazy"` and `decoding="async"`.
- [ ] Images are served in AVIF or WebP with a fallback where needed (`<picture>`).
- [ ] Responsive images use `srcset` with width descriptors and an accurate `sizes`.
- [ ] Every image has `width` and `height` (or CSS `aspect-ratio`).
- [ ] No image is much larger than its rendered size times the device pixel ratio.
- [ ] Icons are SVG or an icon font subset, not large PNG sprites.

## 5. Fonts

- [ ] At most a few font files are needed for the first view; they are preloaded with `crossorigin`.
- [ ] Fonts are WOFF2 and subset to the characters needed.
- [ ] `font-display` is set (`swap` with metric-adjusted fallbacks, or `optional`).
- [ ] Self-hosting is considered instead of a third-party font CDN, to avoid an extra connection.

## 6. JavaScript

- [ ] The bundle analyzer has been run; no duplicate libraries or full imports of large libraries.
- [ ] Code is split by route; heavy components that appear only after interaction are lazy-loaded.
- [ ] No long tasks over 50 ms during load on a throttled mid-range phone profile, or each one has a known reason.
- [ ] Event handlers give visible feedback first and defer heavy work.
- [ ] Polyfills target only the browsers in the support matrix.
- [ ] Hydration cost is understood; consider partial or progressive hydration, islands, or Server Components if supported.
- [ ] A bundle-size budget fails CI when exceeded.

## 7. CSS and rendering

- [ ] No layout thrashing (reads and writes interleaved in loops).
- [ ] Animations use `transform` and `opacity`.
- [ ] Long pages use `content-visibility: auto` for off-screen sections where safe.
- [ ] Long lists are virtualized.
- [ ] DOM size is reasonable (Lighthouse warns on very large DOMs).
- [ ] Unused CSS from frameworks or old features is removed.

## 8. Layout stability

- [ ] Space is reserved for ads, embeds, banners and late-loading widgets.
- [ ] No content is inserted above existing content after load, except in response to user input.
- [ ] Web fonts don't cause visible reflow (metric overrides or `optional`).
- [ ] Skeletons match the size of the content that replaces them.

## 9. Third-party scripts

- [ ] There is an inventory of every third-party script, its owner and its purpose.
- [ ] Unused tags are removed from the tag manager.
- [ ] Non-critical scripts load after the page is interactive or on user intent (chat widget on click).
- [ ] Third parties are measured: main-thread time and bytes per vendor.
- [ ] Facades are used for heavy embeds (video players, maps) until the user interacts.

## 10. Caching

- [ ] Fingerprinted static assets: `Cache-Control: public, max-age=31536000, immutable`.
- [ ] HTML: `no-cache` or a short `max-age` with CDN purge on deploy.
- [ ] API responses have explicit caching headers (`private` or `no-store` for user data).
- [ ] Pages are eligible for the back/forward cache (no `unload` handlers; check the DevTools Application panel's bfcache test).
- [ ] A service worker, if any, has a clear update strategy and doesn't serve stale HTML forever.

## 11. SPA navigation

- [ ] Route transitions prefetch code and data for likely next routes (on hover or viewport), within reason.
- [ ] Client-side navigations are measured (RUM soft-navigation reporting, or custom marks).
- [ ] Data fetching for a route starts in parallel with code loading, not after it (avoid waterfalls).

## 12. Guarding against regression

- [ ] Lighthouse CI or an equivalent runs on PRs with assertions for LCP, CLS and TBT.
- [ ] Bundle size is checked on PRs.
- [ ] Field metrics are on a dashboard with an alert when p75 crosses the "good" threshold.
