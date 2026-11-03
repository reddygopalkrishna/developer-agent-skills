# HTTP and CDN Caching

HTTP caching is defined in RFC 9111. This file covers what an agent needs to set headers correctly and debug them.

## Response directives (`Cache-Control`)

| Directive | Meaning |
| --- | --- |
| `max-age=N` | Fresh for N seconds in any cache |
| `s-maxage=N` | Fresh for N seconds in shared caches (CDN, proxy); overrides `max-age` there |
| `public` | Shared caches may store it, even for requests with `Authorization` |
| `private` | Only the user's browser may store it; shared caches must not |
| `no-cache` | May be stored, but must be revalidated with the origin before every use |
| `no-store` | Must not be stored anywhere |
| `must-revalidate` | Once stale, must not be served without successful revalidation |
| `proxy-revalidate` | Like `must-revalidate`, for shared caches only |
| `immutable` | The response will not change while fresh; browsers skip revalidation on reload |
| `stale-while-revalidate=N` | May serve stale for N seconds while revalidating in the background (RFC 5861) |
| `stale-if-error=N` | May serve stale for N seconds if the origin errors (RFC 5861) |
| `no-transform` | Intermediaries must not modify the body (for example recompress images) |

Notes:

- `Expires` is legacy. If both are present, `Cache-Control: max-age` wins.
- Without `Cache-Control` or `Expires`, caches may compute a heuristic lifetime from `Last-Modified`. Always set `Cache-Control` explicitly so behavior is predictable.
- Support for `stale-while-revalidate` and `stale-if-error` differs between browsers and CDNs. Check the CDN's documentation.
- Some CDNs accept their own header for CDN-only lifetimes, for example `CDN-Cache-Control` (RFC 9213) or a vendor `Surrogate-Control` header. Check which one your CDN honors.

## Recommended setups

### Static assets with content hashes

```
Cache-Control: public, max-age=31536000, immutable
```

The file name changes when the content changes (`app.3f9a1c.js`), so the URL itself is the invalidation. Never use this for un-hashed URLs.

### HTML documents

```
Cache-Control: no-cache
ETag: "v42-9f1c"
```

The browser revalidates on each navigation and gets a cheap `304` when nothing changed, so a deploy shows up immediately and the HTML always points at the newest hashed assets.

### Public API responses

```
Cache-Control: public, max-age=30, s-maxage=300, stale-while-revalidate=60
```

Browsers keep it 30 s, the CDN keeps it 5 min, and the CDN may serve stale for one more minute while it refreshes.

### Authenticated or personalized responses

```
Cache-Control: private, no-cache
```

Or, for sensitive content (account details, tokens, health or payment data):

```
Cache-Control: no-store
```

## Validators and conditional requests

- Send `ETag` (an opaque version string) and/or `Last-Modified`.
- Clients revalidate with `If-None-Match: "<etag>"` or `If-Modified-Since: <date>`.
- If the resource is unchanged, return `304 Not Modified` with no body. This saves bandwidth, not a round trip.
- Weak ETags (`W/"..."`) mean "semantically equivalent"; use strong ETags when byte-exactness matters (range requests).
- Generate ETags from a content hash or a version column, not from data that differs between servers (such as inode numbers), or every server returns a different ETag.

## `Vary` and the cache key

A shared cache stores one entry per URL plus the request headers listed in `Vary`.

| `Vary` value | Effect |
| --- | --- |
| `Accept-Encoding` | Separate entries for gzip, br, identity. Usually required |
| `Accept-Language` | One entry per language header value. High cardinality; prefer language in the URL (`/de/`) |
| `Cookie` | Effectively one entry per user. Defeats the CDN; mark the response `private` instead |
| `Origin` | Needed when CORS headers differ by origin |

Most CDNs also let you configure the cache key directly (which query parameters, headers and cookies are included). Keep it minimal, but make sure every input that changes the response is either in the key or the response is not shared-cached.

## CDN purge and invalidation

- Prefer versioned URLs over purges. Purges take time to propagate and are easy to get wrong.
- If the CDN supports tags (surrogate keys / cache tags), tag responses by entity (`product-123`) and purge by tag when the entity changes.
- Purging everything at once sends all traffic to the origin. Check origin capacity first.
- A purge is a production action. Confirm with the user before running it.

## Service workers

A service worker can serve responses from its own Cache Storage regardless of HTTP headers. If a site shows stale content that headers cannot explain, check for a registered service worker and its caching strategy, and make sure a new deploy updates it.

## Debugging with curl

```bash
# Show caching-related response headers
curl -sI https://example.com/assets/app.3f9a1c.js | grep -iE 'cache-control|etag|last-modified|age|vary|expires'

# Check revalidation returns 304
curl -sI -H 'If-None-Match: "v42-9f1c"' https://example.com/ | head -n 1

# Ask caches between you and the origin to revalidate (many CDNs ignore this request header)
curl -sI -H 'Cache-Control: no-cache' https://example.com/
```

- `Age: N` means the response came from a shared cache and has been there N seconds.
- Most CDNs add a cache status header (names vary by vendor, for example `X-Cache` or `CF-Cache-Status`) reporting HIT, MISS or similar.
- Request the same URL twice; if the second response has no `Age` and the CDN reports MISS again, the response is not being cached. Check `Cache-Control`, `Set-Cookie`, and `Vary`.

## Checklist

- [ ] Every response has an explicit `Cache-Control`.
- [ ] Hashed assets are `immutable` with a long `max-age`; HTML is `no-cache`.
- [ ] Personalized responses are `private` or `no-store`; no shared cache stores them.
- [ ] Responses that set cookies are not cached by the CDN.
- [ ] `Vary` lists every request header that changes the response, and nothing high-cardinality.
- [ ] ETags are stable across servers.
- [ ] The purge strategy is documented, and origin capacity for a full purge is known.
