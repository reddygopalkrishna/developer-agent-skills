# Component patterns (based on the WAI-ARIA Authoring Practices Guide)

These follow the W3C WAI-ARIA Authoring Practices Guide (APG). When a pattern here is not enough, read the matching APG pattern page and its example. Before building any of these, check whether a native element or the project's design system already provides an accessible version.

Notation: **Tab** moves between widgets; **arrows** move inside a widget.

## Button

- Use `<button type="button">`. If you must use another element: `role="button"`, `tabindex="0"`, activate on Enter and Space.
- Toggle button: `aria-pressed="true|false"`, and the label stays the same ("Mute", not "Muted"/"Unmuted").
- Disabled: prefer the `disabled` attribute. If the button must stay focusable to explain why it is unavailable, use `aria-disabled="true"` and block the action in code.

## Disclosure (show/hide)

```html
<button type="button" aria-expanded="false" aria-controls="faq-1">Shipping options</button>
<div id="faq-1" hidden>...</div>
```

- Toggle `aria-expanded` and the `hidden` attribute together.
- Native alternative: `<details><summary>Shipping options</summary>...</details>`.
- Use this, not a menu, for site navigation submenus.

## Accordion

- A set of disclosures, each heading wrapping a button: `<h3><button aria-expanded="false" aria-controls="panel-1">Title</button></h3>`.
- Panels can use `role="region"` with `aria-labelledby` pointing at the button when there are few panels (avoid many landmarks).
- Optional: Up/Down arrows move between headers, Home/End to first/last.

## Dialog (modal)

- Prefer `<dialog>` with `showModal()` (see the main skill).
- Custom implementation: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` (title) and optionally `aria-describedby`.
- On open: move focus to the first focusable element, or to the dialog heading for long content, or to the least destructive action for confirmations.
- While open: Tab and Shift+Tab stay inside; background is `inert`; Esc closes.
- On close: return focus to the element that opened it (or the next logical place if that element is gone).
- Alert dialog (requires a response): `role="alertdialog"`.

## Menu button (application-style actions menu)

Use only for menus of actions (Edit, Duplicate, Delete), like a desktop app menu. Not for navigation links.

```html
<button type="button" id="actions-btn" aria-haspopup="menu" aria-expanded="false" aria-controls="actions-menu">Actions</button>
<ul id="actions-menu" role="menu" aria-labelledby="actions-btn" hidden>
  <li role="menuitem" tabindex="-1">Edit</li>
  <li role="menuitem" tabindex="-1">Duplicate</li>
  <li role="menuitem" tabindex="-1">Delete</li>
</ul>
```

- Enter, Space or Down on the button opens the menu and focuses the first item; Up opens and focuses the last.
- In the menu: Up/Down move (wrapping is optional), Home/End jump, Enter activates, Esc closes and returns focus to the button, Tab closes the menu.
- Typing a character moves to the next item starting with it.
- Only one item is focused at a time (roving `tabindex` or `aria-activedescendant`).

## Tabs

```html
<div role="tablist" aria-label="Account settings">
  <button role="tab" id="tab-profile" aria-selected="true" aria-controls="panel-profile">Profile</button>
  <button role="tab" id="tab-security" aria-selected="false" aria-controls="panel-security" tabindex="-1">Security</button>
</div>
<div role="tabpanel" id="panel-profile" aria-labelledby="tab-profile" tabindex="0">...</div>
<div role="tabpanel" id="panel-security" aria-labelledby="tab-security" tabindex="0" hidden>...</div>
```

- Roving tabindex: only the selected tab has `tabindex="0"`; others have `-1`.
- Left/Right arrows move between tabs (Up/Down for vertical tablists, with `aria-orientation="vertical"`); Home/End jump to first/last.
- Automatic activation (panel switches on arrow) when panels load instantly; manual activation (arrow moves focus, Enter/Space selects) when switching is slow.
- Tab from the tablist moves into the active panel.
- If tabs change the URL and act like navigation, consider plain links styled as tabs instead.

## Combobox (autocomplete)

```html
<label for="city">City</label>
<input id="city" type="text" role="combobox" aria-autocomplete="list"
       aria-expanded="false" aria-controls="city-options">
<ul id="city-options" role="listbox" hidden>
  <li role="option" id="city-opt-1">Amsterdam</li>
  <li role="option" id="city-opt-2">Athens</li>
</ul>
```

- Focus stays in the input. Down opens the list and highlights an option; Up/Down move the highlight using `aria-activedescendant` set to the highlighted option's id; Enter selects; Esc closes (and may clear).
- Mark the highlighted option with `aria-selected="true"` and a visible style.
- Announce the number of results with a polite live region ("5 results available").
- Use a native `<select>` if the user only picks from a short fixed list, or `<input list>` with `<datalist>` for simple suggestions. Custom comboboxes are hard; prefer a well-tested library component.

## Tooltip

- Only for short supplementary text about a focusable element. Never put interactive content or essential information only in a tooltip.
- Show on hover and on keyboard focus; hide on Esc, blur and mouse leave. It must stay visible while the pointer is over the tooltip itself (WCAG Content on Hover or Focus).
- Link with `aria-describedby` pointing at the element with `role="tooltip"`.
- For icon-only buttons, the accessible name still comes from `aria-label`; the tooltip supplements it.

## Toast / snackbar notifications

- Render into a live region that exists before the toast appears: `role="status"` for information, `role="alert"` for errors.
- Don't auto-dismiss toasts that contain actions, or give enough time and a way to reach them (keyboard shortcut or a notifications area). Pause timers on hover and focus.
- Don't move focus to a toast unless the user must act on it.

## Carousel

- Provide previous/next buttons with names, and a pause button if it auto-rotates. Auto-rotation stops on hover and on keyboard focus within the carousel.
- Each slide: `role="group"` with `aria-roledescription="slide"` and `aria-label="2 of 5"`; the container has `aria-roledescription="carousel"` and a label.
- Better default: no auto-rotation at all.

## Data table with sorting

- Use `<table>` with `<th scope="col">`. Put sort controls as `<button>`s inside the header cells.
- Set `aria-sort="ascending|descending"` on the sorted `<th>` only.
- Announce result changes for filtering with a polite live region.
- Interactive grid behavior (`role="grid"` with arrow-key cell navigation) is only for spreadsheet-like widgets; most data tables should stay plain tables.

## Testing each pattern

1. Keyboard: every key in the pattern's list works, and Tab enters and leaves the widget once.
2. Screen reader: role, name and state (expanded, selected, pressed, checked) are announced and update on change.
3. axe: no violations in each state (closed, open, item selected, error).
