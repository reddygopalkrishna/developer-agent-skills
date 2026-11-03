# ICU MessageFormat Cheat Sheet

ICU MessageFormat is supported by ICU4J/ICU4C, FormatJS (react-intl), i18next with its ICU plugin, and many translation management systems. Check your library's documentation for which argument types and options it supports.

## Simple argument

```
Hello, {name}!
```

## Plural

```
{count, plural,
  =0 {No files}
  one {# file}
  other {# files}}
```

- `#` inserts the number, formatted for the locale.
- `=N` matches an exact value and takes priority over categories.
- Categories come from CLDR plural rules: `zero`, `one`, `two`, `few`, `many`, `other`. English uses `one` and `other`; Arabic uses all six; Polish and Russian use `one`, `few`, `many`, `other`.
- `other` is required.
- Source messages need only the categories of the source language; translators add the categories their language needs. Make sure your tooling allows that.

### Offset

```
{guests, plural, offset:1
  =0 {Nobody is coming}
  =1 {{host} is coming}
  one {{host} and # other person are coming}
  other {{host} and # other people are coming}}
```

With `offset:1`, `#` shows `guests - 1`, while `=N` matches compare the original value.

## Ordinal

```
{place, selectordinal,
  one {#st}
  two {#nd}
  few {#rd}
  other {#th}} place
```

Ordinal categories differ from cardinal ones; English needs `one`, `two`, `few`, `other` for ordinals.

## Select

```
{role, select,
  admin {You can edit all projects}
  editor {You can edit your projects}
  other {You can view projects}}
```

`other` is required. Use `select` for gender or grammatical case, not for arbitrary logic.

## Nesting

Put the whole sentence inside each branch rather than nesting fragments, so translators can reorder freely:

```
{gender, select,
  female {{count, plural, one {She has # message} other {She has # messages}}}
  male {{count, plural, one {He has # message} other {He has # messages}}}
  other {{count, plural, one {They have # message} other {They have # messages}}}}
```

## Number, date and time arguments

```
Total: {amount, number}
Due {due, date, medium}
At {start, time, short}
```

Libraries also accept style options or ICU number/date skeletons (for example `{amount, number, ::currency/EUR}` in libraries that support skeletons). For currency, prefer passing an already-configured formatter or a library-specific currency option, and check that the library supports the syntax.

## Rich text

Some libraries (for example FormatJS) support tags inside messages:

```
By continuing you accept the <terms>Terms of Service</terms>.
```

The code maps `terms` to a link component, so the sentence stays whole for translators.

## Quoting and apostrophes

- Curly braces are syntax. To show a literal brace, quote it: `'{'` and `'}'`.
- In ICU4J and FormatJS, a single apostrophe only starts quoted text when it is followed by a syntax character (`{`, `}`, and `#` inside plurals). So `Don't` works as plain text.
- `''` always produces one literal apostrophe.
- Prefer the typographic apostrophe `’` in translations; it never needs escaping.

## Translator notes

Attach a description to each message, for example:

```json
{
  "inbox.unreadCount": {
    "message": "{count, plural, one {# unread message} other {# unread messages}}",
    "description": "Badge text on the inbox tab. Keep under 25 characters."
  }
}
```

The exact file format depends on the library (JSON with descriptions, XLIFF, `.po`, `.resx`). Whatever the format, include where the string appears and any length limit.

## Review checklist

- [ ] Every plural has `other`; no plural logic in code.
- [ ] Each message is one complete sentence or UI label.
- [ ] Placeholders are named and described.
- [ ] Literal braces and apostrophes are quoted correctly.
- [ ] Messages render correctly in a pseudo-locale and a complex-plural locale.
