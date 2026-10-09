# Design map

Where each part of the design export (`design/export/`) lives in the code, and every place where the code deliberately differs from the design. The design is the source of truth for how things look and read; `HANDOFF.md` is the source of truth for behaviour and data.

First draft, written with the base components and the app shell. Screens are added as they are built.

## Tokens and global styles

| Design | Code | Notes |
|---|---|---|
| Colour tokens (`--desk` … `--focus`) | `frontend/src/styles/tokens.css` | Same names and values as the design system. The only file allowed to hold raw hex values (`scripts/check-hex.mjs`). |
| Fonts (`--font-head`, `--font-sans`, `--font-mono`, `--font-hand`, `--font-stamp`) | `frontend/src/styles/tokens.css`, `frontend/src/styles/fonts.ts` | Self-hosted from `@fontsource`: Familjen Grotesk 700, Instrument Sans 400/500/600, JetBrains Mono 400/500, Barlow Condensed 700, Caveat 600. |
| Radii (`--r-sm`, `--r-md`, `--r-lg`, `--r-pill`) | `frontend/src/styles/tokens.css` | 6 / 8 / 12 / 999 px. |
| Shadows (`--shadow-window`, `--shadow-sheet`) | `frontend/src/styles/tokens.css` | Plus `--shadow-raised` (`0 1px 0 --line-strong`), the raised look of the active rail item and the selected segmented tab. |
| Spacing scale 4 … 72 | `frontend/src/styles/tokens.css` (`--space-4` … `--space-72`) | The design gives the steps as numbers only; the token names are ours. |
| Type scale 12 / 13 / 14 / 16 / 17 / 21 px, section and hero clamps | `frontend/src/styles/tokens.css` (`--fs-*`, `--lh-*`) | Names are ours, values are the design's. |
| Control and layout sizes (28 / 32 / 44 px controls, 48 px rows and top bar, rail 88 / 64 px, dialog 480 / 520 / 680 px, …) | `frontend/src/styles/tokens.css` (`--size-*`) | Names are ours, values are the design's. |
| Motion (easings `draw`, `out`, `arrive`; 900 ms spinner turn) | `frontend/src/styles/tokens.css` (`--ease-*`, `--dur-*`) | |
| Dialog backdrop "`--ink` at 32 %" | `--backdrop` in `tokens.css` | `color-mix()` of `--ink`. |
| Page base (body font, focus ring, selection, reduced motion) | `frontend/src/styles/base.css` | Light theme only. With `prefers-reduced-motion` all animations and transitions end at once; spinners stand still. Adds the `.sr-only` utility. |

## Components

| Design component | Code | Notes |
|---|---|---|
| Icons (`<e-icon>`, `eingang-ui.js`) | `frontend/src/components/ui/Icon.vue`, `frontend/src/components/ui/icons.ts` | All 41 design icon names map to `lucide-vue-next` icons with a 1.5 px absolute stroke. Hidden from assistive tech unless given a `label`. |
| Button | `frontend/src/components/ui/Button.vue` | primary / secondary / ghost / danger; sm 28, md 32, lg 44; leading icon; loading (spinner, label set by the caller, e.g. "Approving…"); real `disabled`. `disabledReason` adds the lock icon and a tooltip linked with `aria-describedby` (states board "permission-disabled buttons"). |
| Input | `frontend/src/components/ui/TextInput.vue` | Named `TextInput` in code. Label above, hint or error below (error with the octagon icon), `mono` for IBANs and numbers, `lg` for phone. |
| Textarea | `frontend/src/components/ui/TextArea.vue` | Named `TextArea` in code. Optional `<length> / <max>` counter (polite live region) as in the review dialogs; error and hint together. |
| Select | `frontend/src/components/ui/Select.vue` | See deviation 1. `inline` gives the inbox filter-bar look ("Supplier [select]"). Disabled shows the lock icon. |
| Badge | `frontend/src/components/ui/Badge.vue` | count, selected count, label, Sample (dashed), overdue. |
| StatusChip | `frontend/src/components/ui/StatusChip.vue` | All eight document statuses with the design's label, icon and colour pair; the Processing icon spins. Typed from the generated OpenAPI `DocumentStatusEnum`. |
| SeverityIcon | `frontend/src/components/ui/SeverityChip.vue` | Named `SeverityChip` in code. Checks: Block / Warning / Info; validation issues: Error / Warning / Info. `iconOnly` labels the icon. |
| FormatChip | `frontend/src/components/ui/FormatChip.vue` | Squared corners; icon chosen from the API's format label (XML → file-code, ZUGFeRD and hybrid → paperclip, plain and scanned PDF → file-text); ZUGFeRD tooltip; "· credit note"; long labels wrap. |
| `<e-bars>` (inside ConfidenceChip) | `frontend/src/components/ui/ConfidenceBars.vue` | Bars are `aria-hidden`; a screen-reader text says "High/Medium/Low confidence" unless the caller passes an empty label because a visible word is next to it. The full ConfidenceChip belongs to the fields form and is not built yet. |
| DataTable | `frontend/src/components/ui/DataTable.vue` | Real `<table>` with caption and `th scope="col"`; sticky header on `--bar`; 48 px rows (see deviation 2); sortable header buttons with `aria-sort`; rows open on click, Enter or Space; `aria-selected` on selected rows; mono right-aligned amounts; cells through `cell-<key>` slots. Sorting itself is the caller's (the API sorts). |
| Tabs | `frontend/src/components/ui/Tabs.vue` | underline and segmented; WAI-ARIA tabs (roving tabindex, ←/→/Home/End, automatic activation, disabled tabs skipped); count badges; disabled with lock icon and reason. |
| Dialog | `frontend/src/components/ui/Dialog.vue` | Native `<dialog>` opened with `showModal()` (falls back to the `open` attribute). Labelled by its title; focus moves to the first field, stays inside, returns to the opener; Esc, Close and backdrop click close it. Sizes 480 / 520 / 680 px; full width minus 16 px margins on phones. |
| Toast | `frontend/src/components/ui/Toast.vue`, `frontend/src/components/ui/useToast.ts` | One at a time, bottom right. Success and info: `role=status`, polite, leave after 4 s (see deviation 3); errors and rate limit: `role=alert`, stay until dismissed; optional action such as "Try again". `useToast().show()` from anywhere. Mount `<Toast />` once in the app layout. |
| Skeleton | `frontend/src/components/ui/Skeleton.vue` | Static `--line` bars laid out by grid tracks so they match the content; optional pane-header bar; `aria-busy` with a label; appears only after 300 ms. |
| EmptyState | `frontend/src/components/ui/EmptyState.vue` | Icon disc, title, what it means, one action slot. |
| ErrorState | `frontend/src/components/ui/ErrorState.vue` | Shows the API problem's `title` and `detail` and a "Try again" button that emits `retry`; `role=alert`. |
| Stamp (lg, md, mark, chip) | `frontend/src/components/ui/Stamp.vue`, `frontend/src/components/ui/ink.ts` | lg 44 px and md 22 px lettering with every measure as a fraction of it (em); German date "09. OKT. 2026"; `role=img` named "Eingang stamp, 9 October 2026". `mark` is the square "E" (24 / 28 / 40 px). `chip` is the received chip ("07 Oct, 14:30"). The shared ink filter is added to the page once. Used by the top bar (mark) and the inbox drag overlay (lg). See deviation 4. |
| AppShell, TopBar, Rail | `frontend/src/components/shell/AppShell.vue` | Top bar: mark + "Eingang" / organisation / search with "/" hint (Esc hint while focused) / "Sandbox, <n> h left" / user-menu slot. Rail: Inbox, Approvals, Suppliers, Exports, Accuracy, Settings as `RouterLink`s to `/app/…`, active item raised with `aria-current="page"` (invoice and supplier detail pages count as their section). ≥ 1280 px labels; 768–1279 px icons only with tooltips; ≤ 767 px phone header (mark, page title, phone-actions slot, user menu) and bottom tab bar of five with More. Slots: page (default), `banner` (SandboxBanner), `user-menu`, `phone-actions`. No data fetching. See deviations 5 and 6. |

### Not built yet

PaneHeader, IconButton, Checkbox, Switch, SearchField (as a standalone component; the top-bar search lives in AppShell), ValidationChip, ConfidenceChip, IBAN tag, DropZone, UploadProgressRow, StepProgress, DocumentViewer, CodeView, DiffView, IssueList, CheckList, FieldRow, EvidencePopover, LinesTable, TaxBreakdown, Timeline, ApprovalCard, SandboxBanner, MeterBar, favicon.

## Screens

| Design screen | Code | Notes |
|---|---|---|
| App shell (Inbox and Screens pages) | `frontend/src/components/shell/AppShell.vue` | |

## Deliberate differences from the design

1. **Select uses the native `<select>`.** The design system shows a custom listbox when open; the inbox screens themselves use a styled native select. The native control keeps keyboard and screen-reader behaviour for free; the closed state matches the design, the open list is the browser's.
2. **DataTable rows are 48 px.** The design system page says 44 px, the handoff notes say 48 px; the handoff notes win by their own rule.
3. **Toasts leave after 4 s.** The design system says 5 s, the handoff notes 4–5 s, the design's code 4 s.
4. **Stamp months.** The design shows only OKT., MÄRZ and SEP.; the other months follow the same style: JAN., FEB., MÄRZ, APR., MAI, JUNI, JULI, AUG., SEP., OKT., NOV., DEZ. The received chip shows the time in the viewer's time zone.
5. **Nav counts.** The design's rail has no counts. AppShell accepts optional counts per item and shows them as a count badge on the item's icon; nothing shows when no count is passed.
6. **More menu on phones.** The design says "More opens Accuracy and Settings" without drawing it. It opens a small list above the tab bar in the popover style of the design (`--win`, `--line` border, `--shadow-window`); Esc closes it and returns focus. The phone header shows the page title as text; the page keeps its own `h1`.
7. **Disabled buttons with a reason** keep the real `disabled` attribute (handoff notes) rather than the states board's focusable `aria-disabled` span; the reason is the tooltip and the button's description.

## Screens not in the design

To be filled in as screens are built.
