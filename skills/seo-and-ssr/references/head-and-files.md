# Head Tags, JSON-LD, Sitemaps and robots.txt

Copy these and replace the example values. Most frameworks have a metadata API (head components, `generateMetadata`-style functions, route `meta` exports). Prefer it over hand-written tags so tags are rendered on the server and deduplicated.

## Head tags for a typical page

```html
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Blue Running Shoes | Example Store</title>
  <meta name="description" content="Lightweight blue running shoes with free returns.">
  <link rel="canonical" href="https://www.example.com/shoes/blue-runner">

  <meta property="og:type" content="website">
  <meta property="og:title" content="Blue Running Shoes">
  <meta property="og:description" content="Lightweight blue running shoes with free returns.">
  <meta property="og:url" content="https://www.example.com/shoes/blue-runner">
  <meta property="og:image" content="https://www.example.com/images/blue-runner-og.jpg">
  <meta name="twitter:card" content="summary_large_image">
</head>
```

Pages that must not be indexed:

```html
<meta name="robots" content="noindex">
```

or, for non-HTML files such as PDFs, the response header `X-Robots-Tag: noindex`.

## hreflang

On every language version of the page, list all versions:

```html
<link rel="alternate" hreflang="en" href="https://www.example.com/en/pricing">
<link rel="alternate" hreflang="de" href="https://www.example.com/de/pricing">
<link rel="alternate" hreflang="x-default" href="https://www.example.com/pricing">
```

## JSON-LD examples

Article:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "How We Cut Build Times in Half",
  "datePublished": "2026-10-01",
  "dateModified": "2026-10-15",
  "author": { "@type": "Person", "name": "Jane Doe" },
  "image": ["https://www.example.com/images/build-times.jpg"]
}
</script>
```

Breadcrumbs:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Shoes", "item": "https://www.example.com/shoes" },
    { "@type": "ListItem", "position": 2, "name": "Blue Runner", "item": "https://www.example.com/shoes/blue-runner" }
  ]
}
</script>
```

When generating JSON-LD from data, serialize with a JSON library and escape `<` so a value can't close the script tag (see the **frontend-security** skill).

## sitemap.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.example.com/shoes/blue-runner</loc>
    <lastmod>2026-10-15</lastmod>
  </url>
</urlset>
```

Rules:

- List only canonical, indexable URLs that return 200.
- One sitemap file holds at most 50,000 URLs or 50 MB uncompressed. Use a sitemap index file to list several sitemaps.
- Keep `lastmod` accurate (when the content really changed). Google has said it ignores `priority` and `changefreq`.
- Generate the sitemap from the same source as your routes so it can't drift.

## robots.txt

```text
User-agent: *
Disallow: /cart
Disallow: /search

Sitemap: https://www.example.com/sitemap.xml
```

Rules:

- It lives at the site root (`/robots.txt`) and applies per host.
- It controls crawling, not indexing (see SKILL.md).
- Don't block CSS or JS files the page needs to render.
- Never ship `Disallow: /` to production. Add a CI check that fails if the production robots.txt contains it.

## Quick checks

```bash
# Status code and redirects
curl -sIL https://example.com/old-page | grep -iE "^HTTP|^location"

# robots meta and X-Robots-Tag
curl -sI https://example.com/page | grep -i x-robots-tag
curl -sL https://example.com/page | grep -i 'name="robots"'

# Sitemap is reachable and valid XML (requires xmllint)
curl -s https://example.com/sitemap.xml | xmllint --noout -
```
