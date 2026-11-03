# Component State Checklists

Use these when building components that load data or accept input. Every state listed must exist as a story and be covered by a test.

## Modeling state

Use one status value instead of independent booleans, so impossible combinations cannot render:

```ts
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading"; previous?: T }   // keep old data visible while refreshing
  | { status: "success"; data: T }
  | { status: "empty" }
  | { status: "error"; error: { message: string; retryable: boolean }; previous?: T };
```

Render with an exhaustive `switch` on `status` (see typescript-patterns for the `never` check).

## Async button

| State | Requirements |
| --- | --- |
| Default | Native `<button type="button">` or `type="submit"`; visible label or `aria-label` for icon-only |
| Loading / submitting | Keep width (reserve space for the spinner); keep the label or change it to "Saving..."; `aria-disabled="true"` and ignore clicks so focus stays on the button; announce completion or failure in a live region |
| Disabled | Native `disabled` if users never need to reach it; `aria-disabled="true"` plus blocked activation if a tooltip must explain why |
| Error | Return to default state and show the error next to the form or in an alert; do not leave the button stuck loading |

```html
<button type="submit" aria-disabled="true" class="btn btn--loading">
  <span class="spinner" aria-hidden="true"></span>
  Saving...
</button>
<div role="status" aria-live="polite" class="visually-hidden">Saving changes</div>
```

`aria-disabled` does not stop the browser: pressing Enter in a field still submits the form. Guard the form's submit handler too (ignore submits while a save is in flight), not only the button's click handler.

## Form field

| State | Requirements |
| --- | --- |
| Default | `<label for>` tied to the input; hint text linked with `aria-describedby` |
| Focus | Visible focus indicator meeting 3:1 contrast |
| Error | `aria-invalid="true"`; message element linked with `aria-describedby`; icon or text, not color alone; message says how to fix ("Enter a date after today") |
| Disabled | Native `disabled` (not submitted with the form); consider read-only (`readonly`) instead when users still need to read or copy the value |
| Read-only | `readonly`; still focusable and selectable |

On submit with errors: show an error summary at the top that links to each field, and move focus to it (or to the first invalid field).

## Table / list

| State | Requirements |
| --- | --- |
| Loading (first load) | Skeleton rows matching the real row height, with `aria-hidden="true"`; container `aria-busy="true"` |
| Refreshing | Keep current rows; show a small inline indicator; `aria-busy="true"` on the region |
| Empty (no data yet) | Explain what will appear here and offer the action that creates the first item |
| Empty (filtered) | Say no results match; show the active filters and a "clear filters" action |
| Error (first load) | Message plus retry; do not show an empty state, which would mislead |
| Error (refresh) | Keep old rows; inline message with retry |
| Partial | Paginated or infinite lists announce when more items load; "load more" is a real button |

## Dialog / drawer

| State | Requirements |
| --- | --- |
| Open | Focus moves into the dialog (first field or the heading); background inert; `Escape` closes unless it would lose data |
| Loading content | Dialog opens immediately with a loading region (`aria-busy="true"`), rather than delaying the open |
| Error | Error inside the dialog with retry; the dialog stays open |
| Closing | Focus returns to the element that opened it |

## Copy checklist

- Loading: say what is happening when it takes more than a moment.
- Empty: why it is empty and what to do next.
- Error: what happened, whether data was lost, and what to do (retry, fix field, contact support). No stack traces or bare codes.
- Disabled: why, when not obvious, and how to enable it.
- All copy goes through the i18n message catalog (see internationalization).

## Test checklist

- [ ] A story exists for every state in every theme.
- [ ] axe passes on every story.
- [ ] Keyboard: loading and disabled states behave as specified (focus stays or is skipped).
- [ ] Screen reader smoke test: loading start/end and errors are announced once, not repeatedly.
- [ ] No layout shift between loading and loaded states.
