# CSP Rollout Guide

A Content Security Policy only helps if it is strict, and only survives if it doesn't break the site. Roll it out in report-only mode, fix what it reports, then enforce.

## 1. Pick nonce or hash

| Site type | Use | Why |
| --- | --- | --- |
| Server-rendered HTML (SSR, templates) | **Nonce** | The server can add a fresh random value to every response |
| Static HTML (SSG, CDN-cached pages) | **Hash** | The HTML doesn't change per request, so a nonce would be reused |

Nonce rules:

- Generate a new nonce for every response, from a CSPRNG, at least 128 bits, base64-encoded.
- Put the same value in the header and on every `<script nonce="...">` you trust.
- Never cache HTML that carries a nonce in a shared cache. A cached nonce becomes a fixed, public value.

## 2. Start from a strict policy

Nonce-based:

```http
Content-Security-Policy-Report-Only:
  script-src 'nonce-RANDOM' 'strict-dynamic';
  object-src 'none';
  base-uri 'none';
  frame-ancestors 'none';
  report-to csp-endpoint
Reporting-Endpoints: csp-endpoint="https://example.com/csp-reports"
```

(Shown on several lines for reading; send it as one header line.)

Hash-based: replace `'nonce-RANDOM'` with one `'sha256-...'` source per inline script, computed over the exact script text.

What each part does:

- `'strict-dynamic'`: scripts loaded by a trusted (nonced or hashed) script are trusted too, so tag managers and bundler chunks keep working without host allowlists. Browsers that support it ignore host allowlists and `'self'` in `script-src`.
- `object-src 'none'`: blocks plugins.
- `base-uri 'none'`: stops an injected `<base>` tag from redirecting relative script URLs.
- `frame-ancestors`: clickjacking protection. It does not work in a `<meta>` CSP; send it as a header.

For older browsers, the commonly recommended strict policy also adds `'unsafe-inline' https:` to `script-src` as a fallback. Browsers that support nonces ignore `'unsafe-inline'` when a nonce or hash is present. Check your target browsers before relying on this.

## 3. Collect reports

- `report-to` with the `Reporting-Endpoints` header is the current mechanism. `report-to` only became Baseline in 2026, so also add the older `report-uri https://example.com/csp-reports` for older browsers; browsers that support `report-to` ignore `report-uri`.
- Reports contain page URLs. Treat them as logs that may hold personal data.
- Expect noise from browser extensions and injected scripts. Group reports by directive and blocked source, and ignore sources like `chrome-extension`.

## 4. Fix common violations

| Violation | Fix |
| --- | --- |
| Inline event handlers (`onclick="..."`) | Move to `addEventListener` in a script file. Nonces can't be applied to attributes |
| `javascript:` URLs in links | Replace with buttons and event listeners |
| Inline `<script>` without a nonce | Add the nonce in the template, or move the code to a file |
| `eval` / `new Function` from a library | Upgrade or replace the library; avoid adding `'unsafe-eval'` |
| Third-party snippet that injects scripts | Load the snippet with a nonce; `'strict-dynamic'` covers what it loads |
| Inline styles | Start with `style-src` out of the policy, or allow `'unsafe-inline'` for styles only; tighten later. Style injection is lower risk than script injection |

Framework support: several frameworks document how to generate and pass a nonce (often through middleware or a server hook). Check your framework's security or CSP docs for the current API rather than hand-patching rendered HTML.

## 5. Enforce

1. Run report-only in production long enough to cover real traffic (all major pages, logged-in and logged-out).
2. When reports show only noise, ask the user to approve switching the header from `Content-Security-Policy-Report-Only` to `Content-Security-Policy`.
3. Keep a report-only header alongside the enforced one to test the next tightening step (for example adding Trusted Types).
4. Add a test that fails if the CSP header disappears or gains `'unsafe-eval'`, or `'unsafe-inline'` without a nonce or hash, in `script-src`.

## Checking a policy

- Load the page with browser devtools open: CSP violations appear in the console.
- Check the response header with `curl -sI https://example.com | grep -i content-security-policy`.
- Paste the policy into a CSP evaluator tool to spot bypassable allowlists.
