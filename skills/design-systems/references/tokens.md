# Design Tokens

## Naming scheme

Use `category.property.variant.state`, dropping parts that don't apply.

| Category | Examples |
| --- | --- |
| `color.text` | `primary`, `secondary`, `muted`, `inverse`, `danger`, `success`, `link`, `link.hover` |
| `color.bg` | `canvas`, `surface`, `surface.raised`, `surface.hover`, `danger`, `danger.subtle`, `selected` |
| `color.border` | `default`, `strong`, `focus`, `danger` |
| `color.icon` | `primary`, `muted`, `danger` |
| `font.family` | `sans`, `mono` |
| `font.size` | `xs`, `sm`, `md`, `lg`, `xl`, `2xl` |
| `font.weight` | `regular`, `medium`, `bold` |
| `line.height` | `tight`, `normal`, `relaxed` |
| `space` | `1`...`12` on a 4 px or 8 px base; semantic aliases such as `space.inset.md`, `space.stack.lg` |
| `radius` | `sm`, `md`, `lg`, `full` |
| `shadow` / `elevation` | `1`, `2`, `3` |
| `motion.duration` | `fast`, `normal`, `slow` |
| `motion.easing` | `standard`, `enter`, `exit` |
| `z` | `dropdown`, `sticky`, `overlay`, `modal`, `toast` |

Guidelines:

- Semantic names describe the role ("danger background"), never the value ("red background").
- Use a small number of steps. If designers ask for a step between `md` and `lg`, first check whether an existing step works.
- Use named z-index layers instead of ad-hoc numbers like `9999`.

## Source format

Keep tokens in JSON in the repository. The W3C Design Tokens Community Group (DTCG) format uses `$value` and `$type`, with aliases in braces. In the stable 2025.10 version a `color` `$value` is an object (`colorSpace`, `components`, optional `hex`); the hex strings below are the older draft form that many tools still accept:

```json
{
  "color": {
    "blue": {
      "600": { "$value": "#2563eb", "$type": "color" },
      "400": { "$value": "#60a5fa", "$type": "color" }
    },
    "gray": {
      "50":  { "$value": "#f9fafb", "$type": "color" },
      "900": { "$value": "#111827", "$type": "color" }
    }
  },
  "semantic": {
    "color": {
      "text": {
        "primary": { "$value": "{color.gray.900}", "$type": "color" }
      },
      "border": {
        "focus": { "$value": "{color.blue.600}", "$type": "color" }
      }
    }
  }
}
```

Build tools (for example Style Dictionary) read this and emit CSS custom properties, JS/TS constants, and native platform files. Check which token format version your build tool supports before adopting new syntax.

## Generated CSS

```css
:root {
  --color-text-primary: #111827;
  --color-border-focus: #2563eb;
  --space-4: 16px;
  --radius-md: 6px;
}
```

App and component code reference only the variables, never the raw values.

## Themes

A theme overrides the semantic layer only:

```json
{
  "semantic": {
    "color": {
      "text":   { "primary": { "$value": "{color.gray.50}",  "$type": "color" } },
      "border": { "focus":   { "$value": "{color.blue.400}", "$type": "color" } }
    }
  }
}
```

Generate one CSS block per theme (`:root` for the default, `[data-theme="dark"]` for dark). Brands work the same way: same semantic names, different primitive palette.

For every theme, verify contrast of each semantic pair you actually use:

| Pair | Minimum (WCAG 2.2 AA) |
| --- | --- |
| Body text on its background | 4.5:1 |
| Large text (at least 24 px regular or about 18.7 px bold) | 3:1 |
| Focus indicator, input borders, icons that carry meaning | 3:1 against adjacent colors |

## Typography and spacing scales

- Pick a type scale with a fixed ratio or a hand-tuned list, and pair each size with a line height.
- Use `rem` for font sizes so user font-size settings apply.
- Spacing: one base unit (4 px or 8 px) and a short scale (4, 8, 12, 16, 24, 32, 48, 64). Layout components use these tokens for gaps.

## Changing tokens safely

- Adding a token is a minor change. Renaming or removing one is breaking.
- To rename, add the new token, alias the old one to it, mark the old one deprecated, and remove it in the next major.
- Changing a value (for example a brand color) is not an API break, but it is a visual change: run visual regression tests and announce it.
- Lint for raw values in app code (for example stylelint rules that disallow hex colors outside token files) so new hard-coded values do not creep back in.
