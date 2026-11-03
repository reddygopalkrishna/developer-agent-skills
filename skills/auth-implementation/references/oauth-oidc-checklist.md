# OAuth 2.0 / OpenID Connect checklist

Use this when implementing or reviewing a login integration. Check items against the IdP's own documentation: endpoint names, supported parameters and token formats differ by provider.

## 1. Registration and configuration

- [ ] One client registration per application and per environment (dev, staging, prod). Don't share clients across apps.
- [ ] Client type is correct: **confidential** (has a backend that can keep a secret) or **public** (SPA without backend, mobile, desktop, CLI).
- [ ] Redirect URIs are registered **exactly** (scheme, host, port, path). No wildcards. Native apps use a claimed HTTPS link or loopback redirect per RFC 8252.
- [ ] Post-logout redirect URIs are registered exactly too.
- [ ] Only the grant types you use are enabled. Implicit and password grants are disabled.
- [ ] Endpoints come from the discovery document (`/.well-known/openid-configuration`), not hard-coded.
- [ ] Client secret (confidential clients only) lives in a secret manager, is rotated, and never appears in code, logs or front-end bundles. Prefer private-key JWT or mTLS client authentication when the IdP supports it.

## 2. Authorization request

- [ ] `response_type=code`.
- [ ] PKCE: generate a high-entropy `code_verifier`, send `code_challenge` with `code_challenge_method=S256`. Store the verifier server-side (or in the client's memory for public clients) keyed to this login attempt.
- [ ] `state`: random, single-use, bound to the user's browser session; verify on callback.
- [ ] `nonce` (OIDC): random, single-use; verify in the ID token.
- [ ] `scope` includes `openid` for OIDC plus the minimum needed. Request `offline_access` (or the IdP's equivalent) only if you need refresh tokens.
- [ ] Any `returnTo` / deep-link target is stored server-side or validated against an allowlist of relative paths.

## 3. Callback and token exchange

- [ ] Reject the callback if `state` is missing, unknown, expired or already used.
- [ ] Handle `error` responses from the IdP without leaking details to the user.
- [ ] Exchange the code at the token endpoint over the back channel, sending the `code_verifier` (and client authentication if confidential).
- [ ] Treat the code as single-use; don't retry the exchange with the same code after a failure that might have succeeded.

## 4. ID token validation (OIDC)

- [ ] Signature verified with a key from the IdP's JWKS; the key's `kid` matches; algorithm is on your allowlist.
- [ ] `iss` exactly equals the expected issuer.
- [ ] `aud` contains your client ID. If there are multiple audiences, `azp` equals your client ID.
- [ ] `exp` in the future, `iat` reasonable; allow only small clock skew (seconds to a couple of minutes).
- [ ] `nonce` equals the one you sent.
- [ ] Identify the user by `iss` + `sub`, not by email. Email can change and may be unverified; check `email_verified` before trusting it for account linking.

## 5. Establishing the session

- [ ] Create a server-side session (or BFF session) and set an HttpOnly, Secure, SameSite cookie. Regenerate the session ID.
- [ ] Store access and refresh tokens server-side, encrypted at rest, keyed to the session.
- [ ] For public clients without a backend: keep the access token in memory only; never in `localStorage` or URLs.
- [ ] Set idle and absolute session timeouts.

## 6. Calling APIs

- [ ] Send access tokens only to the API they are issued for (`aud`), over TLS, in the `Authorization: Bearer` header.
- [ ] APIs validate signature, algorithm, `iss`, `aud`, `exp`, and scopes/roles on every request, or introspect opaque tokens.
- [ ] APIs perform object-level authorization using the token's subject and tenant.

## 7. Refresh

- [ ] Refresh on expiry (or shortly before), not on every request.
- [ ] Refresh token rotation is enabled at the IdP; on reuse detection the whole family is revoked.
- [ ] Concurrent refreshes are serialized so two requests don't both use the same refresh token (which looks like reuse).
- [ ] Refresh failures end the session cleanly and send the user to log in again.

## 8. Logout

- [ ] Local session destroyed server-side and cookie cleared.
- [ ] Refresh tokens revoked at the IdP's revocation endpoint (RFC 7009) if supported.
- [ ] Optional RP-initiated logout to the IdP's `end_session_endpoint` with `id_token_hint` and a registered `post_logout_redirect_uri`.
- [ ] Back-channel logout handled if multiple apps share the IdP session and must end together.

## 9. Operations

- [ ] JWKS keys cached with refresh on unknown `kid`, so IdP key rotation doesn't cause an outage.
- [ ] Login, token and refresh failures are logged with a correlation ID but **without** tokens, codes or secrets.
- [ ] Alerts on spikes in login failures, refresh-token reuse and invalid-signature errors.
- [ ] Tests cover: tampered `state`, replayed code, wrong `aud`, expired token, wrong issuer, unsigned token, cross-tenant access, logout then reuse of the old session cookie.

## Red flags in code review

- Decoding a JWT (`jwt.decode`, `base64` parsing) and reading claims without verifying the signature.
- Accepting the algorithm from the token header without an allowlist.
- Comparing `aud` or `iss` with `startsWith` or `includes`.
- Building redirect URLs from request parameters.
- `client_secret` in a front-end bundle, mobile app, or public repository.
- Long-lived tokens (days or more) with no refresh or revocation path.
- User identity or tenant read from a request body or header the client controls.
