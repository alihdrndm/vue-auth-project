# Eingang design export: summary

Source: `D:\repos\eingang\eingang\design\export\` (13 `*.dc.html`, `eingang-ui.js`, `support.js`; `.thumbnail` skipped), compared against `design\DESIGN-BRIEF.md`. Nothing in the repo was modified.

How the files work: every `.dc.html` is a template for a design-tool runtime. The markup sits inside `<x-dc>`, with `<helmet>` for head content, `{{ }}` bindings, `<sc-if>` / `<sc-for>` control flow, and `style-hover` / `style-focus` / `style-active` pseudo-state attributes. Logic lives in `<script type="text/x-dc" data-dc-script>` as `class Component extends DCLogic`, which is React-like (state, setState, renderVals). `data-props` on that script defines "Tweaks" (design-tool controls), for example the headline choice or reduced motion. All styling is inline. There are **no CSS custom properties anywhere**: every colour is a raw hex literal. Token names appear only as documentation text.

---

## 1. Per-file inventory

| File | Kind | What it is | Viewport(s) | States / variants shown |
|---|---|---|---|---|
| `Eingang Design System.dc.html` | Page (1461 lines) | Design system, "version 1, 09 Oct 2026". Sections: Colour, Type, Space/radius/shadow, Icons, Status labels, Components, Stamp, Drawing style. | Fluid page on `--bar` | Colour swatches. Text-on-surface contrast pairs, computed live in JS. Type scale with EN + DE samples (ä ö ü ß €). Spacing, radii, shadows. 41 icons. All B6 chips. Every component with default/hover/focus/active/disabled/loading/error rows (see §3). Stamp in 3 dates (09. OKT. 2026, 02. MÄRZ 2027, 15. SEP. 2026). Stamp sizes md/mark/chip. Proportions table. Favicon at 16/32/180. Two drawn sheets (#8 VAT ID cut off, note "cut off. which VAT ID is this?"; #5 XML, note "no buyer reference in here?") with a "Replay drawing" button. Tweaks: inkTexture, motion. |
| `Eingang Homepage.dc.html` | Page | Public homepage, desktop | 1440 (max content 1280) | Header; hero (3 headline options via Tweak, default option 1); Act 1 (4 draggable docs plus "Stamp it" buttons, inbox window with stamp drop zone; rows step Received → Processing → verdict; "Do it again"); Act 2 (taped sheet, review window for #7, note/resolve/mark reviewed, Jonas's phone with approve/approving/approved, reject hint, export row sliding into the drawn folder, "Do it again", 4-step progress list); Close (facts strip, CTA, accuracy link); footer. Tweaks: headline, motion (Full / Reduced), inkTexture. |
| `Eingang Homepage Phone.dc.html` | Page | Public homepage, phone. Also used for all widths below 1100 px (content max 680 px, centred). | 390 (and 900 fallback) | Simplified hero art (no highlighter, no plain-PDF sheet), Act 1 as a vertical stack with 44 px "Stamp it" buttons that each produce a card, Act 2 stacked with a full-width phone frame, close, footer. Same Tweaks. |
| `Eingang Homepage Board.dc.html` | Board | Desktop iframe, motion spec panel, phone iframe, tablet-fallback iframe | 1440 / 390 (392 frame) / 900 (902 frame) | The motion spec table, with all 7 brief animations (see §5). |
| `Eingang App Sign in.dc.html` | Page | Sign-in card | 1440×900 on the board; layout is fluid (`max-width:100%`) | Empty; field errors ("Enter your email address.", "Enter your password."); show/hide password; busy "Signing in…" (then redirects to Inbox after 800 ms). Link "Open the sandbox instead". Line "Free and open source. No sign-up for the sandbox." |
| `Eingang App Inbox.dc.html` | Page | Inbox, responsive, with upload | 1440, 1024 (tablet), 390 | 6 tabs with counts (7/3/1/0/0/12); search with `--hl` match marking; supplier and format filters; sort with aria-sort; row selection plus select-all (mixed); empty state per tab plus "No invoices match". Upload: `?screen=drag` (full-window overlay), `?screen=picker` (dialog with "Your system's file picker is open…"), `?screen=processing` (3 files at different StepProgress steps plus 1 rejected `.docx`); over-10-files warning. Phone: cards, 44 px controls, bottom tab bar. Tablet: icon rail, table scrolls with Supplier pinned, e-invoice shown as an icon in the Format cell. Tweak: screen. |
| `Eingang App Board.dc.html` | Board | Frames: Sign in, Inbox All, drag overlay, picker, processing, Inbox phone (All + Needs review), Inbox tablet | 1440×900, 390×844, 1024×768 | None of its own. |
| `Eingang App Review.dc.html` | Page | Invoice review, responsive. Query params `?inv=1/8/5/10`, `?tab=xml/text`, `?ev=<field>`, `?issue=open`, `?as=jonas`, `?dialog=accept/resolve/reject`, `?mtab=document/activity` | 1440, 1024, 390; #10 as a 900×460 fragment | A (#1, Jonas): Approve / Reject…, approving, approved, rejected, XML tab. B (#8, Anna): evidence popover, editing, edited, low-confidence VAT ID row, Mark reviewed disabled with reason, resolve dialog, Text tab, phone Data/Document/Activity tabs, tablet "Show document" collapsed. C (#5, Anna): issue with "Show official message" expander, "Accept anyway…" disabled for Anna; as Jonas, the accept dialog. #10: standalone DiffView card. `j` / `k` cycles #1 → #8 → #5 with a toast. Four-eyes lock after self-review. Toasts. Tweak: variant. |
| `Eingang App Review Board.dc.html` | Board | Frames: A, A-XML, B evidence open (`ev=iban`), B Text (`ev=gross`), C official message open, C accept dialog (Jonas), B phone ×3, B tablet, #10 DiffView | 1440×900, 390×844, 1024×768, 900×460 | None of its own. |
| `Eingang App Screens.dc.html` | Page | `?screen=approvals / suppliers / supplier / supplier-confirmed / exports / settings / accuracy / accuracy-public / notfound` | 1440 (Settings and Accuracy 1440×1100), approvals also 390; public accuracy 1200×900; not found 960×600 | Approvals (3 rows plus the design-only Krause four-eyes row, reject dialog, approve toast, empty state). Suppliers list (7 suppliers). Supplier detail Bürobedarf Nord (unconfirmed, plus a "State example: after the change was confirmed" variant). Exports (format radio, "1 invoice ready", exporting, exported row, design-only past export). Settings (sandbox banner, read-only org fields, four-eyes switch, duplicate window 30, reminder 3, members disabled, AI budget meters, dirty → Save). Accuracy app plus public (all values sample). Not found (404). Tweak: screen. |
| `Eingang App Screens Board.dc.html` | Board | Frames of all Screens states | as above | None of its own. |
| `Eingang States Board.dc.html` | Board (has its own content) | 6 views × Loading / Empty / Error / Success, plus special states | Wide canvas (cells 440 px) | Inbox, Invoice review, Approvals, Suppliers, Exports, Accuracy. Special states: processing and failed inbox rows; upload limit rows; expired sandbox page; 5 "Extraction unavailable" variants (including AI budget used up); toasts (success, error, rate limit); 7 permission-disabled buttons with tooltips. |
| `Eingang Handoff Notes.dc.html` | Page | "Handoff notes": Files, Decisions, Do not change, Tokens, Type, Stamp/mark/favicon, Components, Screens, Click and keyboard, Animations, Responsive, Accessibility, Placeholder vs required | Fluid, max 1040 | Static (rendered from JS arrays). Full content in §5. |

---

## 2. Design tokens actually used

**No `--*` custom properties are defined or used (`var(--` count = 0 in every file).** Colours are hard-coded hex, so the developer must map them back to token names.

The hex values used match the brief's B4 table exactly. I checked every hex in every file. All 24 token colours appear with their B4 values:

`--desk #ebe4d6`, `--paper #fdfaf4`, `--win #fffdf9`, `--bar #f7f2ea`, `--line #ebe3d6`, `--line-strong #d6cbbb`, `--soft #f6f0e6`, `--ink #1f1c18`, `--text #3f3a33`, `--muted #746c61`, `--muted-strong #5f574d`, `--ok #0f6e62`, `--ok-soft #e4f1ed`, `--warn #c47408`, `--warn-text #8a4a06`, `--warn-soft #fcefd8`, `--block #b42318`, `--block-soft #fbe9e6`, `--info #2f5d8a`, `--info-soft #e6eef7`, `--stamp #2c4a8a`, `--stamp-soft #e8edf7`, `--pen #d3241b`, `--hl #ffe53d`, `--focus #0f6e62`.

- Radii in use: 6 / 8 / 12 / 999 px, matching B4. Exceptions, all documented as illustration: the homepage phone frame uses 40 px corners; the stamp and mark use em-based radii (0.14em, 0.15em); favicon SVG `rx="3"` / `rx="6"`.
- Shadows match B4 exactly: `--shadow-window` = `0 30px 60px -34px #3a2a1480, 0 2px 8px -3px #3a2a1433`; `--shadow-sheet` = `0 1px 0 #3a2a140f, 0 30px 60px -34px #3a2a1470, 0 2px 6px -2px #3a2a1426`.
- Focus: `outline: 2.5px solid #0f6e62; outline-offset: 2px` everywhere. The handoff notes add −3 px inside scroll containers.
- Fonts match B4: Familjen Grotesk 700 (−0.025em), Instrument Sans 400/500/600, JetBrains Mono 400/500, Caveat 600, Barlow Condensed 700 (uppercase, 0.08em).
- Spacing: padding, margin and gap values are on the 4…72 scale everywhere, with three exceptions: `margin-top:168px` in Homepage.dc.html (illustration offset), and 128 / 480 / 1px values in Review.dc.html's layout object (flex basis and doc height, not true spacing).
- Type sizes: 12/13/14/16/17/21/28/42/38–66 match the scale. Off-scale values are stamp lettering (18/20/22/36/44), mark sizes (24/28/40), Caveat notes (28/30), the favicon specimen (140), and **15 px for section intros in Handoff Notes** (only real off-scale text).

Raw colours that are not B4 tokens:
- `#3a2a14` with alpha (`0b`, `0f`, `26`, `33`, `70`, `80`): used only in the two shadows and the 32 px desk grid (`#3a2a140b`). Both are defined in B4, so this is consistent.
- Named `transparent` / `none` / `currentColor`: normal.
- `support.js` (design-tool runtime, not product): `CANVAS_BG_LIGHT = "#f0eee6"`, `CANVAS_BG_DARK = "#2e2c26"`, `color-mix(...)` placeholder CSS. These never ship.

**Values that differ from B4: none.** Inconsistencies are elsewhere, in §3 and §6, for example DataTable row height and toast duration.

Documented token-usage extensions (handoff notes):
- `--ink` at 32 % opacity is the dialog backdrop.
- `--line` is also used for skeleton bars and tape.
- `--line-strong` is used for crop marks.
- `--muted` is also allowed on `--soft` and for checkbox and switch borders.
- `--block` / `--block-soft` also mark low confidence.
- `--stamp` is the sandbox banner and received-chip colour.
- `--hl` is also the evidence highlight, with a 2 px `--stamp` ring.

The XML syntax colours in CodeView:
- element names `--stamp`
- attributes `--warn-text`
- values `--ok`
- brackets `--muted`
- text `--ink`
- issue annotation row: `--block` on `--block-soft`

---

## 3. Components (B5 names) found in the export

Shown in the Design System page under these headings, and used in the screens.

| B5 component | Present? | Variants / states shown |
|---|---|---|
| AppShell | Yes | Desktop / tablet / phone. DS frame combines SandboxBanner, TopBar, Rail, PaneHeader, live Tabs and a Skeleton. |
| TopBar | Yes (inside AppShell, no own heading) | Mark + "Eingang" / org name / search with `/` kbd / "Sandbox, 23 h left" (sandbox only) / user menu with initials, name, role. |
| Rail | Yes | Default, hover, focus, active raised (`--win`, `--line` border, `0 1px 0 --line-strong`). Tablet icons only with tooltip. Phone tab bar of 5 (Inbox, Approvals, Suppliers, Exports, More), items ≥56 px tall; "More opens Accuracy and Settings". |
| PaneHeader | Yes | Title + count + action ("Approve 3"); back link + title + mono number + "More actions" IconButton. |
| Button | Yes | primary / secondary / ghost / danger × default, hover, focus, active, disabled, loading ("Approving…", "Saving…", "Loading…", "Rejecting…"). Sizes sm 28 ("Resolve check"), md 32 ("Export 7 invoices", leading icon), lg 44 (phone and dialogs). |
| IconButton | Yes | ghost and secondary × default, hover, focus, active, disabled; sizes 28/32/44; aria-label + tooltip ("More actions", "Copy IBAN"). |
| Input | Yes | Default (live), hover, focus, filled, error ("Enter all 22 characters of the IBAN."), disabled ("Viewers can't edit fields."). Mono for IBAN. |
| Textarea | Yes | Default, focus, filled, error ("Add a note before you resolve this check."), disabled. 5–500 counter in dialogs. |
| Select | Yes | Default, hover, focus, open listbox (Accountant / Approver / Admin / Viewer), error ("Choose a role before you invite someone."), disabled ("You can't change your own role."). |
| Checkbox | Yes | Off, hover, on, mixed, focus, disabled, disabled-on; live "Select all 7 in Needs review". |
| Switch | Yes | Off, on, hover, focus, disabled, disabled-on; live four-eyes switch with On/Off word. |
| SearchField | Yes | Default, hover, focus-empty (Esc hint), typed with results ("kessler" → `<mark>Kessler</mark>`). |
| Tabs | Yes | Underline (default, hover, focus, selected, empty count) and segmented (Document / XML / Text, disabled with lock + reason). |
| Badge | Yes | Count, count selected, label ("You"), Sample (dashed `--muted` border), Overdue. Also the "Design-only example" badge. |
| StatusChip | Yes | All 8 B6 statuses with code values. Icons: Received inbox, Processing spinner, Needs review eye, Awaiting approval hourglass, Approved circle-check, Rejected ban, Exported check, Failed circle-alert. |
| FormatChip | Yes | Squared corners. All B6 formats including MINIMUM / BASIC / EXTENDED / XRECHNUNG, ZUGFeRD 1, Hybrid PDF (unsupported), Plain PDF, Scanned PDF, "· credit note". ZUGFeRD tooltip "ZUGFeRD and Factur-X are the same standard". Icons: file-code (XML), paperclip (hybrid), file-text (PDF). |
| ValidationChip | Yes | E-invoice / Not an e-invoice / Valid / Valid with warnings / Invalid · 2 errors / Not applicable. In screens: "Invalid · 1 error", "Not applicable — plain PDF". |
| ConfidenceChip | Yes | High (3 bars) / Medium (2) / Low (1) / "Edited by Anna Weber" (pencil). Uses `<e-bars>`. |
| SeverityIcon | Yes | Check: Block (octagon) / Warning (triangle) / Info (circle-i). Issue: Error / Warning / Info. Icon-only variant. |
| DataTable | Yes | Sticky header, hover row, selected row, mono right-aligned amounts. **DS says 44 px rows; handoff notes say 48 px rows.** |
| DropZone | Yes | Default, dragging over ("Release to add 3 files"), error ("Angebot.docx can't be read"), disabled by role. Plus the full-window overlay in Inbox. |
| UploadProgressRow | Yes | Uploading (64 %, cancel), processing ("Step 3 of 4: extract"), received, done/needs review, failed (Retry). Plus rejected and limit rows in Inbox and the states board. |
| StepProgress | Yes | In progress (#8), complete (#1, "Extract: Not needed, data is in the XML"), stopped (#9, "No text layer, enter by hand"). Step states done / current spinner / pending / skipped / failed. |
| DocumentViewer | Yes | Tabs Document / XML / Text (disabled with reason). Zoom ±, download, page buttons "1", "2" (the DS's page thumbnails). Evidence line highlighted. The Review page has no thumbnail strip; its sample PDFs are single-page. |
| CodeView | Yes | Line numbers, token syntax colours, current line on `--soft`, search match on `--hl`, inline BR-DE-15 annotation row with no number, "Copy XML". |
| DiffView | Yes | "PDF shows" vs "XML says" (marked "Used"), line numbers 38 / 57, −/+ markers; "No differences" state. |
| IssueList | Yes | Collapsed and hover, expanded (plain explanation, official message verbatim `lang="de"`, location `/Invoice`, "Copy message", "Show in XML"). |
| CheckList | Yes | Open (#7), resolving (note form), resolved (#6, with "Reopen" and quoted note), info (#1), disabled by role. |
| FieldRow | Yes | Default, hover (Edit), editing (Save / Cancel), low (tinted `--block-soft` + hint), edited, From XML. |
| EvidencePopover | Yes | Snippet with `<mark>`, page/line, confidence sentence, "Show in document". Medium (IBAN) and Low (VAT ID) examples. |
| LinesTable | Yes | #8 lines. |
| TaxBreakdown | Yes | Net / VAT 19 % on … / Gross. |
| Timeline | Yes | #12 with rejection quote. |
| ApprovalCard | Yes | Default, approving, approved, four-eyes (design only). |
| Dialog | Yes | Reject SW-2026-77812 with reason. Screens add accept, resolve and reject dialogs with 5–500 validation and busy state. |
| Toast | Yes | Success, info ("Exporting 7 invoices…"), error with "Try again". States board adds rate limit ("Too many requests. Wait a minute and try again."). |
| EmptyState / ErrorState / Skeleton | Yes | Plus a full matrix on the states board. |
| Stamp | Yes | lg, md, mark, chip, favicon; three dates. |
| SandboxBanner | Yes | Desktop one line; phone wraps. |
| MeterBar | Yes | Under, near limit, reached. **The DS uses "3,20 € of 10,00 €"; Settings uses "$0.42 of $2.00" (brief).** |

**Missing B5 components: none.** Every B5 name is represented.

Extras not in B5: IBAN tag (as its own chip family), Mark (square "E" logo), Favicon, Overdue badge, Sample / "Design-only example" badge.

---

## 4. Screens required by the brief vs. the export

| Required (B2 / C4–C7) | Status | Where |
|---|---|---|
| Sign in | **Present** (1440 only; layout fluid, no 390 frame) | App Sign in |
| Sandbox banner | **Present** | Inbox (desktop + phone), Settings, DS. Text exact: "Sandbox · deleted in 23 h · sample data, nothing is real" |
| Inbox (1440 + 390) | **Present** (+ 1024 tablet) | App Inbox / App Board |
| Upload (drag overlay, picker, 3 processing rows, inline rejection) | **Present** | `?screen=drag / picker / processing`. Overlay text exact: "Drop invoices to stamp them in — PDF or XML, up to 4 MB each, 10 at a time". Rejection exact: "This file is not a PDF or XML. Eingang reads PDF and XML only." |
| Invoice review A | **Present** | `?inv=1` (+ XML tab) |
| Invoice review B (+390) | **Present** (+ tablet) | `?inv=8` |
| Invoice review C (+ resolve/accept dialog) | **Present** | `?inv=5&issue=open`, `?inv=5&as=jonas&dialog=accept` |
| PDF/XML mismatch DiffView (#10) | **Present**, but only as a 900×460 isolated card, not in a full review screen | `?inv=10` |
| Approvals (+390) | **Present** | `?screen=approvals` |
| Suppliers list / detail (+ confirmed variant) | **Present** | `?screen=suppliers / supplier / supplier-confirmed` |
| Exports | **Present** | `?screen=exports` |
| Accuracy | **Present** (app + extra public version) | `?screen=accuracy / accuracy-public` |
| Settings | **Present** | `?screen=settings` |
| Not found | **Present** | `?screen=notfound` ("404 / Nothing at this address / … / Go to the Inbox") |
| States board | **Present**: all 6 views × 4 states plus failed doc, expired sandbox, AI budget used up, toasts, permission-disabled | States Board |
| Homepage desktop + phone | **Present** (+ 900 fallback) | Homepage / Homepage Phone / Homepage Board |
| Motion spec | **Present** | Homepage Board (+ Handoff Notes "Animations") |
| Handoff notes | **Present** | Handoff Notes |

**Missing or partial against the brief:**
- Footer **imprint placeholder** is omitted on purpose (decision: "The footer has no imprint link.").
- The #10 mismatch is only a fragment.
- No 390 Sign in frame.
- The Review page has no page-thumbnail strip.
- The handoff "Files" table lists `uploads/kiln-*.png` reference screenshots, but **no `uploads/` folder exists in the export**.

---

## 5. "Handoff notes" page: full content

Page title "Handoff notes". Intro: "For the developer building Eingang. Every page listed here is live: open it, click it, resize it. Where this page and a design disagree, this page wins; tell the designer."

### 5.1 Files
| File | Type | What it shows |
|---|---|---|
| Eingang Design System.dc.html | Page | Tokens, type, spacing, radii, shadows, icons, every component and its states, status labels, stamp, mark, favicon, drawing style. |
| Eingang Homepage.dc.html | Page | Public homepage at 1440 px with both interactive acts. |
| Eingang Homepage Phone.dc.html | Page | Public homepage at 390 px; also the layout below 1100 px, content at most 680 px. |
| Eingang Homepage Board.dc.html | Board | Homepage desktop, phone and 900 px fallback side by side, plus the motion spec panel. |
| Eingang App Sign in.dc.html | Page | Sign-in screen. |
| Eingang App Inbox.dc.html | Page | Inbox, responsive (1440, tablet, 390). ?tab=all; ?screen=drag \| picker \| processing hold the upload states. |
| Eingang App Board.dc.html | Board | Sign in, inbox, the three upload states, inbox on phone and tablet. |
| Eingang App Review.dc.html | Page | Invoice review, responsive. ?inv=1 \| 8 \| 5 \| 10, ?tab=xml \| text, ?ev=<field>, ?issue=open, ?as=jonas, ?dialog=accept \| resolve \| reject, ?mtab=document \| activity. |
| Eingang App Review Board.dc.html | Board | Review variants A, B and C with their tabs and dialog, B on phone and tablet, and the #10 DiffView frame. |
| Eingang App Screens.dc.html | Page | Approvals (desktop and phone), suppliers, supplier detail and its confirmed state example, exports, settings, accuracy (app and public), not found. ?screen=… |
| Eingang App Screens Board.dc.html | Board | All screens of App Screens in frames. |
| Eingang States Board.dc.html | Board | Loading, empty, error and success for six data views, plus the special states. |
| Eingang Handoff Notes.dc.html | Page | This page. |
| eingang-ui.js | Script | The icon set (e-icon, 1.5 px strokes), the confidence bars (e-bars) and the shared ink filter. Loaded by every page. |
| support.js | Script | Runtime for the design pages. Not part of the product. |
| uploads/kiln-*.png | Reference | Screenshots of the Kiln reference pages. Approach only; do not ship or copy. *(Not present in the export folder.)* |

Note: "Loaded by every page" is not literally true. The board files and Handoff Notes do not load `eingang-ui.js`.

### 5.2 Decisions made during design (verbatim)
1. Headline: option 1 ("Some of our invoices are e-invoices. We couldn't tell you which.") ships. The headline options in Tweaks are for review only, not a feature.
2. Illustration sizes outside the tokens: the homepage phone frame has 40 px corners; stamp and square-mark lettering is pinned per component (see "Stamp, mark and favicon").
3. Favicon: a separate small mark, a filled --stamp square with one --win "E" in Barlow Condensed 700, at 16, 32 and 180 px.
4. Homepage stamp: the design shows 09. OKT. 2026; the live site shows the visitor's today.
5. Received chip: app date format ("07 Oct, 14:30") in stamp colours (--stamp on --stamp-soft), never the stamp lettering.
6. The overdue marker appears only on Needs review and Awaiting approval rows.
7. IBAN tags map to the API's iban_status: "Known account" = known, "Confirmed change" = confirmed, "New account" = new.
8. Inbox table: at 1440 px supplier names wrap; at 768–1279 px the table scrolls inside its container with Supplier pinned, and the e-invoice yes/no shows as an icon in the Format cell.
9. Review screen: on tablet the data panel comes first with "Show document" collapsed below; on phone the bottom tab bar is hidden and the header has a back arrow to the Inbox.
10. The footer has no imprint link.
11. Drag and drop is the browser's native drag and drop; on touch screens the "Stamp it" buttons are the primary control.
12. Error states show the API's problem title and detail. The wording on the states board is an example only.
13. Design-only content that must NOT become seed data: the Malerbetrieb Krause approvals row, the past export row (01 Oct 2026), the confirmed-IBAN state example, the homepage's phone-call note on #7.
14. Invented sample content (fine for the design): #8 invoice date 05 Oct 2026; single line items for #1 and #5; buyer reference HB-4100-EK; masked IBANs •••• 4417 and •••• 8803; Krause due date 04 Nov 2026.
15. Settings defaults: duplicate window 30 days, reminder after 3 days.
16. Homepage below 1100 px: the phone layout, centred, with content at most 680 px wide.
17. Credit notes show amounts with a minus sign ("−58,31 €", U+2212).

### 5.3 Do not change (verbatim)
1. Stamp proportions: every measure is a fraction of the stamp's lettering size; rotate only within ±5°; keep the shared ink filter.
2. Status vocabulary: the exact labels, colours and icons of B6. Status never by colour alone: always text plus icon.
3. Honesty rules: no testimonials, logos, user counts, "trusted by" or improvement percentages. Every illustrative number says "sample". Legal facts only with their source link. The homepage only links to accuracy; it never shows a number. Never claim that Eingang reads scans or images.
4. Evidence highlight: every AI-read value shows the exact text it came from, with the value marked in --hl. Selecting a field highlights the same line on the page and in the Text tab. No AI value without its evidence and confidence; XML values carry "From the XML" and no confidence chip.
5. Four-eyes: when it is on, the reviewer of an invoice can never approve it, Admins included.
6. The homepage phone-call note on #7 never appears in the app; in the app #7's check stays unresolved.

Conflicts with the "±5°" rotation rule: the homepage stamps use −7° (envelope, desktop and phone) and −8° / +6° on stamped sheets, which is outside ±5°. The DS also says "Rotation −5° to +5°".

### 5.4 Tokens (as listed on the page)
Same values as B4 (see §2), with these usage notes:
- `--bar`: also the app background.
- `--line`: borders, dividers, skeleton bars, tape.
- `--line-strong`: input and button borders, crop marks.
- `--ink`: dialog backdrop at 32 % opacity.
- `--text`: primary hover.
- `--muted`: on win, paper, bar, soft; checkbox and switch borders.
- `--block`: also low confidence.
- `--stamp`: stamp, received chip, links, sandbox banner.
- `--pen`: notes 24 px+.
- `--hl`: highlighter, search match, evidence highlight.
- `--focus`: 2.5 px outline, 2 px offset; −3 px inside scroll containers.
- Radii: sm / md / lg / pill = buttons and inputs / cards, popovers, toasts / windows, sheets, dialogs / chips, switches.
- Spacing: 4…72. "Control heights 28/32/44 are sizes. Absolute offsets of homepage drawings are illustration layout."

### 5.5 Type
"Line height 1.45 in the app, 1.6 for homepage body. Smallest size anywhere: 12 px."

| Role | Font | Size |
|---|---|---|
| Hero | Familjen Grotesk 700, −0.025em | clamp(38px, 4.6vw, 66px) |
| Homepage section heading | Familjen Grotesk 700 | clamp(28px, 2.6vw, 42px); 28 px on phone |
| Homepage body | Instrument Sans 400 | 17 px |
| Page title | Familjen Grotesk 700 | 21 px |
| Section title | Familjen Grotesk 700 | 16 px |
| Default UI | Instrument Sans 400/500/600 | 14 px; 16 px in phone inputs and 44 px buttons |
| Table, secondary | Instrument Sans | 13 px |
| Captions | Instrument Sans | 12 px |
| Numbers, IBANs, VAT IDs, rule IDs, XML | JetBrains Mono 400/500 | 12–13 px; 21 px for headline amounts |
| Red-pen notes | Caveat 600 | 24 px or more |
| Stamp | Barlow Condensed 700, uppercase, 0.08em | see stamp section |

### 5.6 Stamp, mark and favicon
W = stamp lettering size, S = side of the mark.

| Element | Measure |
|---|---|
| Stamp "EINGANG" | W. Sizes in use: lg 44 px (DS), 36 px (homepage window), md 22, 20 (stamped sheets), 18 (phone envelope). |
| Stamp date | 0.45 W, German format ("09. OKT. 2026") |
| Stamp frame | 0.07 W, corners 0.14 W |
| Stamp inner rule | 0.035 W, 0.18 W inside the outer edge |
| Stamp date rule | 0.045 W |
| Stamp padding | 0.27 W top and bottom, 0.36 W sides, 0.09 W word to date |
| Mark "E" | 0.55 S; S = 40, 28, 24 px; never below 24 |
| Mark frame / inner rule | 0.0625 S, corners 0.15 S / 0.025 S, 0.175 S inside |
| Favicon | Filled --stamp square, --win E, pixel-snapped. 16 px: E 6 × 10, stem and arms 2 px. 32 px: E 12 × 20, 4 px. 180 px: square corners. |
| Phone frame (homepage) | 8 px --ink border, 40 px corners (illustration) |

### 5.7 Components (handoff table)
Intro: "Names map one-to-one to code. Every interactive component has default, hover, focus, active and disabled states as shown in the design system."

- **AppShell**: TopBar + Rail + content on `--bar`; panes on `--win`.
- **TopBar**: mark, organisation, search with "/" hint, sandbox countdown (sandbox only), user menu with name and role.
- **Rail**: labels (≥1280), icons only (768–1279), bottom tab bar (≤767). The active item is raised. Tab bar items: Inbox, Approvals, Suppliers, Exports, More.
- **PaneHeader**: title, count, back link, actions.
- **Button** (primary / secondary / ghost / danger; sm 28, md 32, lg 44):
  - active: 1 px down
  - disabled: `--soft`, `--muted`, not-allowed cursor, real `disabled` attribute
  - loading: spinner + "…ing"
  - labels never wrap
- **IconButton** (ghost / secondary; 28/32/44): always has aria-label and tooltip; 44 px on phone.
- **Input, Textarea, Select**:
  - hover: `--muted` border
  - focus: `--ink` border + ring
  - error: `--block` border + message with octagon
  - disabled
  - notes: 5–500 characters with a counter
- **Checkbox, Switch**: off, on, mixed (checkbox), hover, focus, disabled; borders in `--muted`.
- **SearchField**: "/" focuses, Esc clears focus, matches marked in `--hl`.
- **Tabs** (underline / segmented): selected, hover, focus, empty count, disabled with lock and reason.
- **Badge** (count, selected count, label, Sample, overdue): "Sample" and "Design-only example" use a dashed `--muted` border.
- **StatusChip, FormatChip, ValidationChip, ConfidenceChip, SeverityIcon, IBAN tag**: B6 vocabulary. Format chips have squared corners and the ZUGFeRD tooltip. Long format chips wrap.
- **DataTable**: sticky header, 48 px rows, hover, selected, sortable headers with aria-sort, mono numbers right-aligned.
- **DropZone** (default, drag-over, error, disabled by role): plus the full-window overlay.
- **UploadProgressRow** (uploading, processing, received, done, failed, rejected, limit reached): rejected rows say why and offer Remove.
- **StepProgress** (detect, validate, extract, check): done, current (spinner), pending, skipped ("Not needed" / "Not applicable"), failed.
- **DocumentViewer** (Document / XML / Text): tabs disabled with a reason when they don't apply; evidence highlight in `--hl` with a `--stamp` ring.
- **CodeView**: line numbers; colours from tokens only; issues inline as an annotation row without a number.
- **DiffView**: "PDF shows" vs "XML says"; the XML side is marked Used.
- **IssueList** (collapsed, expanded): rule ID in mono, plain explanation, official message verbatim on expand, location, Show in XML.
- **CheckList** (open, resolving, resolved, info, disabled by role): block checks need a note to resolve.
- **FieldRow, EvidencePopover** (From XML, AI-read high/medium/low, edited, editing): low rows tinted `--block-soft` with a hint. The popover shows snippet, line, confidence and "Show in document".
- **LinesTable, TaxBreakdown, Timeline**: no notes.
- **ApprovalCard** (default, approving, approved, four-eyes blocked): 44 px buttons on phone.
- **Dialog**: focus moves in, Esc and Cancel close, focus returns. Backdrop `--ink` at 32 %.
- **Toast** (success, info, error, rate limit): bottom right. Success and info leave after 4–5 s; errors stay until dismissed.
- **EmptyState, ErrorState, Skeleton**: skeletons appear after 300 ms and match the layout.
- **Stamp** (lg, md, chip, mark, favicon): takes a date.
- **SandboxBanner** (desktop one line, phone wraps): Inbox and Settings only, sandbox only, not dismissible.
- **MeterBar** (under, near limit, reached): every number marked Sample in the design.

### 5.8 Screens and their states
| Screen | Viewer | States |
|---|---|---|
| Homepage | Public | Hero; Act 1 empty → stamped rows → all four done; Act 2 steps 1–4 → Do it again. Reduced motion end states. |
| Sign in | Public | Empty, field errors, signing in. |
| Inbox | Anna | 6 tabs, search, supplier/format filters, sort, selection, empty per tab, no results, loading, error. Upload: drag overlay, file picker open, processing, rejected, limits. |
| Review A, #1 | Jonas | Awaiting approval; approving; approved; rejected; XML tab. |
| Review B, #8 | Anna | Needs review; evidence open; editing; VAT ID edited or check resolved → Mark reviewed → awaiting; Text tab; phone tabs. |
| Review C, #5 | Anna (dialog: Jonas) | Official message open; Accept anyway disabled for Anna; accept dialog for Admins. |
| #10 mismatch | — | DiffView check. |
| Approvals | Jonas | 3 rows + design-only four-eyes row; approve, reject dialog, empty. |
| Suppliers / supplier detail | Anna | List; Bürobedarf Nord with New account (unconfirmed) and the confirmed state example. |
| Exports | Anna | 1 ready; exporting; exported row; nothing ready. |
| Settings | Jonas | Sandbox: banner on, members disabled; unsaved changes → Save. |
| Accuracy (app and public) | Anna / public | All numbers sample; no-results and error states. |
| Not found | — | One action: Go to the Inbox. |
| Expired sandbox | — | "This sandbox has expired. Open a new one." |

### 5.9 Click and keyboard behaviour (verbatim)
1. Everything clickable is a button or link, reachable with Tab, with a visible --focus ring. Icon-only buttons carry aria-label and the same text as tooltip.
2. "/" focuses search anywhere outside a text field. Esc closes the open popover, dialog or drag overlay.
3. Review: j = next invoice, k = previous; ignored while typing. Inbox rows open the review.
4. Tabs: arrow keys move between tabs; the selected tab has aria-selected. Sortable headers toggle ascending and descending and set aria-sort.
5. Homepage Act 1: drag a document onto the stamp (native drag and drop) or press its "Stamp it" button; each document stamps once. Act 2: type a note or use the example, Resolve check, Mark reviewed, Approve on the phone; Reject… explains it works in the sandbox.
6. Inbox upload: dragging files anywhere over the window shows the overlay; dropping uploads up to 10 files of PDF or XML, 4 MB each; others are rejected inline.
7. Review B: the pencil edits a field (Save / Cancel); the eye opens the evidence popover; picking a field highlights it in the document. Typing a full VAT ID resolves the low-confidence check.
8. Dialogs that resolve, accept or reject need a note of 5–500 characters; the confirm button validates and shows an inline error.
9. Disabled actions are real disabled buttons with the reason as visible text or tooltip, never only greyed out.

Additional details from the Design System page:
- Select opens a listbox: arrow keys move, Enter picks, Esc closes.
- Dialog focus moves to the first field and returns to the opener.
- Toasts are one at a time.

### 5.10 Animations (Handoff table + Homepage Board motion spec)
Rule: "Every motion finishes within 1.2 s. With prefers-reduced-motion nothing moves; each element shows its end state as soon as its trigger fires." The Homepage Board adds a "Reduced" Tweak that does the same.

Easing names (Homepage Board):
- `draw` = cubic-bezier(.65, 0, .35, 1): pen, highlighter, export slide.
- `out` = ease-out: direct responses to a press.
- `arrive` = cubic-bezier(.2, .8, .2, 1): things that arrive from elsewhere.

| Motion | Trigger | Duration | Easing | Reduced-motion end state |
|---|---|---|---|---|
| Stamp press | Drop on stamp or "Stamp it". Desktop: stamp moves 3 px down and scales to 96 %. Phone: impression lands on the sheet, 125 % → 100 %. | 140 ms down, 20 ms hold, 140 ms back (phone 140 ms) | out | Impression on the sheet at once |
| Document to row | Stamp press. Row fades in and slides 8 px down; Received → Processing at 400 ms → verdict at 1,100 ms. | 240 ms entry; 1,100 ms to verdict | out | Row in place with verdict; no Received or Processing steps |
| Red-pen draw-on | Hero +600 ms after load; Act 1 note when the first verdict appears; Act 2 when 30 % of the sheet is in view (20 % on phone). Strokes trace their path; notes wipe in from the left; each group plays once. | circle 600, arrow 350–400, note 400, folder 800 ms, staggered; each group ≤1,200 ms | draw | Every stroke and note drawn from the start |
| Highlighter swipe | With the hero pen (600 ms after load). Grows from the left, skewed −12°. Desktop only. | 450 ms | draw | Full swipe from the start |
| Check resolve | Resolve check with a note. Resolved line, quoted note and "Confirmed change" fade in; "New" and the form go at once. An empty note shows an inline error and nothing moves. | 200 ms | out | Resolved at once |
| Hand-off to phone | Mark reviewed. Card rises 24 px into Jonas's phone and fades in; window chip → Awaiting approval. | 320 ms | arrive | Card on the phone at once |
| Approve | Approve on the phone. Spinner + "Approving…" while the request runs (700 ms in the demo); then the status line replaces the buttons and the chip → Approved. | 700 ms wait; spinner 900 ms per turn | linear | No spinning; Approved as soon as the request returns |
| Export slide | 500 ms after approval. Export row drops into the drawn folder (−48 px → +26 px), about 30 px showing; chip → Exported. | 700 ms | draw | Row resting in the folder, number and Exported chip visible |
| Spinners (app) | Any pending request | 900 ms per turn | linear | Static icon |

Also in code:
- Act 1 hover lift: documents rise 4 px, 160 ms ease-out.
- Drop zone background: 120 ms ease-out.
- Inbox `j`/`k` toast: 2.5 s.
- App toasts: 4 s.

Inconsistency: the Design System "Drawing style" text says "Highlighter 450 ms, circle 700 ms, arrow 400 ms, note 500 ms, staggered, ease-in-out". Its JS also uses 700 / 400 / 500 with the draw curve. This differs from the motion spec's circle 600 and note 400.

### 5.11 Responsive rules
| Screen | ≥ 1280 px | 768–1279 px | ≤ 767 px |
|---|---|---|---|
| Homepage | Two-column acts, pile composition | Below 1100 px: the phone layout, centred, content at most 680 px wide; hero art, phone frame (max 358 px) and folder keep their phone sizes | Single column; simplified hero art; Act 1 vertical with Stamp it; full-width phone frame |
| App shell | Rail with labels | Rail icons only, tooltips | Bottom tab bar, 5 items |
| Inbox | Full table, no sideways scroll, Supplier wraps | Table scrolls in its container, Supplier pinned, E-invoice as icon in Format | Cards; search and filters 44 px; tabs scroll |
| Review | Document \| panel | Panel first, "Show document" collapsed below | Data / Document / Activity tabs; action bar; no bottom tab bar; back arrow |
| Approvals | Compact rows, inline actions | Same, scrolls | Stacked ApprovalCards, 44 px buttons |
| Dialogs | 480–680 px | Same | Full width minus 16 px margins |
| Tap targets | — | — | 44 px minimum everywhere |

### 5.12 Accessibility (verbatim)
1. Only the token text pairs listed in the design system; all are AA. --pen notes 24 px or larger; --muted never on --desk.
2. Focus: 2.5 px --focus outline, 2 px offset; inside scrolling or clipped containers use −3 px so the ring stays visible.
3. Status always as text plus icon; severity icons used alone carry aria-label.
4. Every drag has a button alternative (Stamp it, Choose files).
5. Live regions: toasts role=status (errors role=alert); upload progress and resolved checks announce; the counter in note fields is polite.
6. Dialogs: aria-modal, labelled by their title; focus trapped and returned.
7. German content (invoice text, official rule messages) carries lang="de"; French invoice lang="fr".
8. Tables use real table markup with header cells; sortable headers expose aria-sort; selected rows aria-selected.

Additional points from the DS:
- The `--muted` checkbox border "reads at 3:1".
- "--muted on --soft is the tightest pair. Never smaller than 12 px."
- Not allowed: `--muted` on `--desk`, `--pen` below 24 px, `--pen` or `--warn` as text on win/bar.

### 5.13 Placeholder vs required content
| Content | Status |
|---|---|
| B9 invoices, suppliers, users, amounts, dates | Required sample data for the sandbox |
| Status vocabulary, rule IDs, the official BR-DE-15 message | Required, exact |
| Legal facts and their two source links | Required, exact, always with the link |
| Homepage copy, empty-state copy, success copy | Required as designed |
| Error titles and details on the states board | Example only; the app shows the API's problem title and detail |
| Accuracy figures, AI budget figures, MeterBar values | Placeholder, always labelled Sample until measured |
| #8 invoice date, line items of #1 and #5, HB-4100-EK, •••• 4417, •••• 8803 | Invented sample content, fine for the design |
| Krause row, past export row, confirmed-IBAN example, homepage phone-call note | Design-only; never seed data |
| GitHub, sandbox and sign-in links | Placeholder hrefs (`#github`, `#sandbox`, `#sign-in`, `#accuracy`) |
| Upload filenames and timestamps in demos | Placeholder |

The Krause masked IBAN `•••• 5512` is used in the Approvals data but is not in the "invented sample content" list.

---

## 6. Copy against the honesty rules, and other content deviations

**No testimonials, customer logos, user counts, star counts, "trusted by", "10×" or improvement percentages appear anywhere.** I grepped all files.

Illustrative numbers are labelled "sample" consistently:
- Accuracy pages: "Every number on this page is a sample."; "0.00"; "95 % confidence interval 0.00–0.00 (sample)"; "— (sample)"; "$0.000 (sample)"; "Sample values" badge.
- Settings AI budget: "Sample" badge.
- DS MeterBar: "Sample".
- States board: "Results from the latest run (sample)".
- Homepage windows: "Sample data" badge and "Sample documents. Drag one onto the stamp, or press Stamp it."
- The homepage only links "How accurate is it? Measured, with the method". No number shown.

Items to flag:
1. **The legal source links to a vendor blog, not the BMF.** "Source: BMF letter, 15 Oct 2024" links to `https://www.elo.com/de-de/blog/e-rechnungspflicht-bmf-schreiben-und-faq.html` (an ELO software company blog), not to the BMF letter itself. Used in:
   - `Eingang Homepage.dc.html:254` ("BASIC WL carries too little data to count as an e-invoice.")
   - `Eingang Homepage Phone.dc.html:162` (same)
   - `Eingang App Review.dc.html:51` (#10: "PDF shows 1.190,00 € · XML says 1.200,00 € — the XML is the legally binding part." … "Eingang uses 1.200,00 €. Check with the supplier which amount they meant before anyone approves it.")
   - `Eingang Design System.dc.html:1037` (DiffView: "In a hybrid PDF the XML is the invoice, so Eingang uses 1.200,00 €.")

   The label claims a BMF source but the target is third-party.
2. **EC-sourced facts are fine.** Strip copy: "Receiving: since 1 Jan 2025 — Every German business must be able to receive structured e-invoices (EN 16931)." and "Sending: from 2027 and 2028 — Plain PDF invoices to other German businesses end: in 2027 above €800,000 turnover, in 2028 for everyone. Invoices up to €250 stay exempt." Both link "Source: European Commission" (`https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108886/eInvoicing+in+Germany`). The Review #8 check "Not an e-invoice — Plain PDFs are not e-invoices. Suppliers may still send them during the transition period." also links to the EC.
3. **Legal-ish claims without a source link:**
   - Facts strip "Checks the official EN 16931 and XRechnung rules — Every verdict names the rule it rests on and says in plain English what to do." This is a product claim; the brief lists it as a strip item without a source.
   - App validation line "Checked with the official XRechnung rules (KoSIT 2026-01-31)." (from the brief).
   - BR-DE-15 explanation "…for public bodies this is the Leitweg-ID" (brief text).

   None is a legal fact that needs a source per B7, but they assert compliance.
4. **Footer** omits the imprint placeholder (brief C2). The footer has "Not tax advice. Eingang checks published technical rules." and GitHub.
5. **IBAN tag vocabulary deviates from B6.**
   - B6 says "Same as before" / "Confirmed change" / "New". The export uses "Known account" / "Confirmed change" / "New account", recorded as a decision.
   - The Screens file adds extra labels "No changes", "Not read yet" and "New" (tooltip "First invoice from this supplier, so there is no earlier IBAN to compare with").
   - Supplier detail reads "Known account · first seen 02 Oct 2026 on BN-88102-G. Also on BN-88213." The brief had "Same as before · first seen 02 Oct 2026 on BN-88102-G".
6. **Headline choice.** The shipped hero is "Some of our invoices are e-invoices. We couldn't tell you which." (Tweak alternatives: "We checked every invoice by eye. The one with the new bank account looked fine too." / "We paid the same invoice twice. Both copies looked perfectly valid."). This fits the first-person rule.
7. **Data inconsistencies between files** (not honesty, but worth fixing):
   - Inbox row #8 shows no block check, and DS DataTable #8 shows "—". Review B, however, has Block "Low confidence: VAT ID".
   - Inbox row #5 shows no block, while Review C has Block "Validation failed".
   - DataTable row height: 44 px (DS) vs 48 px (handoff).
   - Toast auto-dismiss: 5 s (DS) vs 4–5 s (handoff) vs 4 s (code).
   - MeterBar: euros (DS, "3,20 € of 10,00 €") vs dollars (Settings, "$0.42 of $2.00").
   - Stamp rotation: −7° / −8° / +6° on the homepage vs the "±5°" do-not-change rule.
   - The DS Badge note says "No sample invoice qualifies [as overdue] on 09 Oct 2026". This matches the code: #12 is Rejected, so it is not marked.
8. **Design-only copy.** The homepage example note "Called Bürobedarf Nord on their old number — confirmed" must never appear in the app (do-not-change #6).

---

## 7. `eingang-ui.js`, `support.js`, fonts and icons

**`eingang-ui.js`** (99 lines; product-relevant helper; guarded by `window.__egUI`):
- Custom element `<e-icon name size spin>`:
  - Renders inline SVG in shadow DOM: 24-unit viewBox, `stroke="currentColor"`, round caps and joins.
  - Stroke width is `1.5*24/size`, so the rendered stroke is 1.5 px at any size.
  - `spin="true"` adds `eg-spin` (0.9 s linear infinite).
  - Without an `aria-label` it sets `aria-hidden="true"`; with one it gets `role="img"`.
  - 41 lucide-style icon paths: inbox, check, circle-check, check-check, hourglass, loader, triangle, octagon, info, x, search, upload, download, file-text, file-code, pencil, chevron-down/right/left, user, building, archive, gauge, sliders, more, plus, landmark, copy, eye, clock, ban, message, lock, refresh, external, circle, minus, circle-alert, zoom-in, zoom-out, paperclip.
  - Exposes `window.EG_ICON_NAMES`.
- Custom element `<e-bars level="1-3">`: the confidence bars. Three rects of heights 5/8/11 in a 14×12 SVG; filled bars use `currentColor`, empty ones `#d6cbbb`; `aria-hidden`.
- Shared SVG filter `#eg-ink` (appended to body): feTurbulence + feDisplacementMap (scale 3) + grain mask. This gives the uneven rubber-stamp and pen ink edge. `window.egInk(on)` toggles it (the inkTexture Tweak).

**`support.js`** (1911 lines): yes, it is only the design-tool runtime. Header: "GENERATED from dc-runtime/src/*.ts — do not edit. Rebuild with `cd dc-runtime && bun run build`."
- Parses `<x-dc>` templates, `<script data-dc-script>` logic (`DCLogic` base class) and the `data-props` Tweak schema.
- Compiles `{{ }}`, `sc-if`, `sc-for`, `style-hover/focus/active`, and `<helmet>` (→ `sc-helmet`) into React.
- Loads React 18.3.1 and ReactDOM 18.3.1 UMD, plus `@babel/standalone@7.29.0`, from unpkg.
- Has deck-stage support and a design-canvas mode (`design_doc_mode=canvas` on boards).
- Posts `__dc_booted` / `__dc_design_mode` messages to a parent frame and listens for `__dc_theme` / `__dc_probe`.
- Contains non-token canvas colours `#f0eee6` / `#2e2c26`.
- The handoff notes say: "Runtime for the design pages. Not part of the product."

**Fonts:** Google Fonts CSS2, `display=swap`.
- Familjen Grotesk 700, Instrument Sans 400;500;600 and JetBrains Mono 400;500: loaded on all pages.
- Barlow Condensed 700: all app pages, DS, homepages, states board.
- Caveat 600: DS and both homepages only.

**Icons:** only `eingang-ui.js` (no icon font, no external icon library). The DS also has inline SVG drawings (pen strokes, paper-clip, envelope, folder) and favicon SVGs.

---

