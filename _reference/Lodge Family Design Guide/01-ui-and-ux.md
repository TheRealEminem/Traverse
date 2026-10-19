# UI and UX

How The Lodge looks, moves and talks, written as one guide for every app in the family: The Lodge, the project app,
and Trailmix when it joins. It brings together the family guide (`DESIGN.md` in the repo), The Lodge's own palette
and artwork (DESIGN.md §17), and the patterns The Lodge's screens actually use, which DESIGN.md doesn't yet describe.
Where this guide and the code disagree, the code wins; tell me and I'll fix the guide.

Open [`design-guide.html`](design-guide.html) next to this file. It shows everything below drawn with the real tokens,
in Day and Dusk.

---

## 1. The idea

> *Where the trail ends up.*

The family looks like a well-made field notebook: warm, quiet, outdoorsy, and never cute about it. Near-white,
slightly frosted surfaces sit over a warm background with a faint linework motif. Color is rare, and when it's
there it means something.

- **Trailmix** is out on the walk: recording what happens.
- **The Lodge** is where you come back to, where your people are: a cabin by a mountain lake, with a fire going.
- **The project app** (working name Cairn) marks the way forward, one stone at a time.

There are two themes, and both are designed. **Day** is light. **Dusk** is the same place after sunset: accents get
lighter, text on accents turns dark, and shadows go black because there's no light left to tint them. Dusk is
never an inverted Day.

When something isn't covered here, ask: *would this feel at home in a good field notebook, by the fire?* Calm
before clever, warm before cool, and a few things done carefully.

## 2. What's shared and what each app makes

| Shared by every app (don't change) | Each app makes its own |
| --- | --- |
| Tokens: color roles, type scale, radii, shadows, easing | Name, wordmark, lowercase tagline |
| Fonts: Geist, Fraunces, Geist Mono | Its mark (the family recipe, its own motif) |
| Day and Dusk, following the OS by default | Its hero scene, from the family's landscape palette |
| The component kit (`.btn`, `.panel`, `Select`, `StatusChip`…) | The linework motif inside `Ambient`, and the empty-state badge to match |
| Motion: hover lifts, press settles, content rises in | Which action, if any, is its one "live" action in orange |
| The shell: a 288px glass sidebar, an 872px reading column | Section icons and brand-moment copy |
| The status language (§4) and the voice (§12) | |

**For the project app, add one more shared thing: The Lodge's palette values.** The Lodge nudged Trailmix's
palette toward its own materials. The project app should not nudge it again. Same tokens means the merged app looks
identical, and the project app tells itself apart by its mark, scene and motif alone.

| | Trailmix | The Lodge | Project app (proposed) |
| --- | --- | --- | --- |
| Mark motif | a cream trail | a cream A-frame | three stacked cream stones |
| Mark tile | forest `#2F7B58 → #1B4E37` | forest `#2F7B58 → #1B4E37` | sky `#4F86A8 → #285B7A` |
| Hero scene | rolling hills, a winding trail | peaks, a lake, an A-frame, a fire; keeps the clock | a switchback trail to a summit, cairns at each turn |
| `Ambient` linework | topographic contour rings | a log's growth rings, in cedar | a dashed route between waypoints |
| Live action (orange) | Record | none | none |
| Sign-in | "See you on the trail" | "Come on in" | "Pick up the trail" |

## 3. Color

Every color is a CSS variable ([`tokens/tokens.css`](tokens/tokens.css)), exposed to Tailwind
([`tokens/tailwind.config.js`](tokens/tailwind.config.js)) and to Swift ([`tokens/Brand.swift`](tokens/Brand.swift)).
**Components never contain hex values.** Artwork in `illustrations.tsx` is the only exception.

### Surfaces and text

| Tailwind | CSS var | Day | Dusk | Use |
| --- | --- | --- | --- | --- |
| `canvas` | `--bg` | `#F7F4EC` | `#0E1416` | The page: warm linen; a spruce-blue night by the lake |
| — | `--bg-top` | `#FCFAF5` | `#121A1D` | The top of the page gradient |
| `glass` | `--surface` | `rgba(255,253,248,.72)` | `rgba(27,37,40,.62)` | Frosted panels (with blur) |
| `surface` | `--surface-solid` | `#FFFDF8` | `#172023` | Opaque cards, dialogs, menus, fields |
| `surface-subtle` | `--surface-subtle` | `#F2EEE4` | `#131B1D` | Wells, insets, segmented track, avatars |
| `ink` | `--text-primary` | `#21271F` | `#ECEAE3` | Text and headings |
| `ink-soft` | `--text-secondary` | `#666A5F` | `#A9AAA1` | Hints, metadata, secondary lines (5.0:1 · 7.9:1) |
| `ink-faint` | `--text-tertiary` | `#979A8F` | `#72776F` | **Icons, placeholders, separators only.** Too faint to read |
| `line` | `--border` | olive 11% | pale 8% | Hairlines, panel edges, dividers |
| `line-strong` | `--border-strong` | olive 17% | pale 14% | Field and soft-button edges, empty tracks |

### Accents, and the one job each does

Each accent comes in four parts: `DEFAULT` (fills, dots), `hover`, `soft` (a tinted background) and `deep` (text
on its own soft; the CSS var ends in `-ink`). **Always pair `bg-X-soft` with `text-X-deep`.**

| Family | Day | Dusk | Its job |
| --- | --- | --- | --- |
| `forest` (spruce) | `#1F5E4B` | `#52A487` | The main action, selection, focus, links, the brand; **done, healthy** |
| `trail` (ember) | `#DE5F31` | `#EC7347` | The app's **one live action**; **errors**; destructive hovers |
| `sun` (lantern) | `#F2B13C` | `#F3B955` | **Needs you**: waiting on the user, attention, flags |
| `sky` (lake) | `#457F9C` | `#7DB3CF` | **Working on it**; **You**; cloud |
| `berry` (lingonberry) | `#9A4F6B` | `#CC85A0` | **Them**, the other party. Sparingly |

`on-accent` is white in Day and near-black in Dusk, which is how Dusk's lighter accents stay readable. `btn-sun`
always uses dark text.

### Rules

- **Color is for meaning.** If it doesn't do one of the jobs above, use ink and surfaces.
- **One primary per screen.** Everything else is `btn-soft` or `btn-ghost`.
- **Tints come from opacity on family colors:** `bg-forest/[.05]` for row hover, `bg-forest/10` for counts,
  `border-trail/20` for callout edges. Never Tailwind's `gray-*`, `slate-*` or any default palette.
- **Shadows are warm olive in Day** (`rgba(40,36,22,…)`), never black. Dusk uses black.
- **Things people make don't get colors.** No colored projects, tags or labels. Tell them apart by name, initial
  tile and icon.

## 4. The status language

One vocabulary for state across every module, so "sun" means the same thing in People, Projects and Meetings. Status
is **never color alone**: every chip has a word, and every bar or glyph has a label or tooltip.

| Tone | Means | Background jobs (`JobChip`) | People (The Lodge) | Projects (proposed) |
| --- | --- | --- | --- | --- |
| `forest` | done, healthy, yours and fine | done (no chip) | known, tier bars | Done · On track |
| `sky` | working on it · You | Running ("Reading…") | — | Doing · Active · your avatar |
| `sun` | needs you | Needs you · Waiting | "needs research" | At risk · Due today · Urgent |
| `trail` | something went wrong | Failed | inbox: Failed | Off track · Late · Blocked |
| `berry` | it's with them | — | — | Waiting (on someone else) |
| `neutral` | idle, not started, set aside | Queued | — | To do · Planned · Paused · Dropped |

`trail` in a chip means "something has gone wrong". Use it as `trail-soft` with `trail-deep` text. A filled orange
button (`btn-record`) is only ever the live action, or the confirm button of a destructive dialog.

**Strength and amount** use quiet glyphs with a word, not color: The Lodge's **tier bars** (four rising bars, forest
up to the tier, with "Strong", "Working", "Light", "Indirect" or "Not linked" beside them), and a project's **progress
bar** (6px forest fill on `line-strong`, with "12 of 30 done").

## 5. Surfaces and depth

Three layers: the `Ambient` background, frosted chrome (sidebar and narrow top bar), then content panels.

| Class | Looks like | Use for |
| --- | --- | --- |
| `.panel` | solid surface at 88%, `rounded-xl`, hairline, panel shadow, a 1px highlight on the top edge | The default container: lists, settings groups, cards |
| `.glass` | `--surface` + 20px blur, otherwise like `.panel` | Panels floating over artwork |
| `.inset-surface` | `surface-subtle` at 70%, inset hairline, `rounded-lg` | Empty states, recessed areas, board columns |
| `.chrome` | `--sidebar-bg` + 18px blur | The sidebar and the narrow-window top bar |
| `.well` / `.well-forest` | 32px `rounded-sm` square | The icon at the start of rows and section headings |
| `.art-frame` | hairline, `rounded-hero`, fades out at the bottom | Hero scenes |

**Radii** (Tailwind's are replaced, not extended): `xs 5` (code, key caps) · `sm 8` (small buttons, fields, wells,
icon buttons) · `md 12` (buttons, menus, nav items) · `lg 16` (callouts, toasts, cards) · `xl 22` (panels, dialogs)
· `hero 28` (artwork) · `full` (chips, switches, avatars).

**Shadows:** `sm` (resting controls), `md` (tooltips, hover lift), `lg` (menus, dialogs, toasts, a dragged card),
`panel` (two very soft layers), `chrome` (the sidebar edge), `focus` (the field ring).

Every raised surface has `inset 0 1px 0 var(--highlight)`, a faint light line along its top. It's a large part of why
surfaces look made rather than flat.

## 6. Type

- **Geist** (`font-sans`) for everything in the interface.
- **Fraunces** (`font-display`) for page titles, hero titles and the wordmark only, always with
  `"opsz" 144, "SOFT" 30, "WONK" 0`, semibold, tight negative tracking. Import `@fontsource-variable/fraunces/full.css`
  (the plain import lacks the SOFT axis).
- **Geist Mono** (`font-mono`) for timers, keys, paths and code. Numbers that change use `tabular-nums`.

| Class | Size | For |
| --- | --- | --- |
| `text-caption` | 11px | Chips, badges, key caps |
| `text-meta` | 12px | Timestamps, eyebrows, tooltips, right-hand row details |
| `text-hint` | 12.5px | Hints under labels, the second line of a row |
| `text-ui` | 13.5px | Controls, navigation, small buttons, fields, blurbs |
| `text-label` | 14px | Row titles, buttons, the body default |
| `text-body` | 15px | Reading text, line-height 1.7 |
| `text-heading` | 16px | Section headings: semibold, `tracking-[-0.01em]` |
| `text-lead` | 17px | Dialog titles |
| `text-wordmark` | 21px | The app's name in the sidebar (Fraunces) |
| `.page-title` | 26–32px | One per page (Fraunces) |
| `.hero-title` | 32–46px | One per hero: Home's greeting (Fraunces) |
| `.hero-sub` | 15.5–17.5px | The line under a hero |

Weights: 400 for text, 500 (`font-medium`) for labels and buttons, 600 (`font-semibold`) for headings and the
primary button. **Never 700, never uppercase.** An eyebrow (`.eyebrow`) is meta size, medium weight, `ink-soft`,
in sentence case.

## 7. Layout

- **The shell:** `Ambient` fixed behind everything. A 288px `.chrome` sidebar at 1024px and wider. Below that, a
  drawer behind a 56px frosted top bar with a scrim.
- **The content column:** `max-w-[872px]`, `px-5 sm:px-8 lg:px-10`, `pt-7 lg:pt-12`, `pb-24`. A route marked
  `wide: true` gets `max-w-[1400px]` instead: The Lodge's network canvas, and the project board.
- **The sidebar, top to bottom:** mark and wordmark with the tagline, the primary button (the first module that has
  one), search with a `⌘K` key cap, Home (when there's more than one module), each module's nav items with count
  badges, then Settings.
- **Rhythm:** sections are `mb-10`. A section heading is a `.well-forest`, a heading and a one-line blurb, `gap-3`.
  Panels are `divide-y divide-line` rows, `px-5 sm:px-6`. Rows are `py-3` to `py-3.5`, with `gap-3.5`.
- **Stagger:** blocks enter with `animate-enter`, 60ms apart (`animationDelay`).
- The smallest window is 420×560. Everything works at 375px wide with no sideways scrolling.

## 8. The kit: what exists, and where

Use these before writing anything new. If something's missing, add it to the kit, not to one screen.

| Need | Use | From |
| --- | --- | --- |
| A page title, subtitle and actions | `PageHeader` | `@core/components/ui` |
| A choice between a few views or filters | `Segmented` (sliding thumb) | `ui` |
| A dropdown | `Select` (never the native `<select>`) | `ui` |
| A setting | `ControlRow`, `SwitchRow`, `Switch` | `ui` |
| A group of settings | `Section` (well, heading, blurb, panel) | `@core/components/blocks` |
| A text or secret setting | `TextSetting`, `SecretSetting` | `blocks` |
| A state | `StatusChip tone label live?` | `ui` |
| A background job | `JobChip` (in rows), `JobStatus` (with Start, Go ahead anyway, Try again) | `blocks` |
| Things linked from other modules | `LinkedList of="<ref>"` | `blocks` |
| Confirm | `useShell().confirm({title, body, confirmLabel, tone})` | `@core/shell` |
| A message | `useShell().toast(text, "success" or "error")` | `shell` |
| A tooltip | `data-tip="…"` on any element | (one `TooltipLayer` for the app) |
| Loading | `Skeleton`, `Spinner`, `Pulse` | `ui` |
| Collapse and expand | `Collapse` | `ui` |
| Copy to clipboard | `CopyButton` | `ui` |
| Icons | the `icon()` wrapper and named icons | `@core/components/icons` |
| Data that stays fresh | `useLive(load, deps)` | `@core/live` |
| Filters in the URL | `useQueryParams()` | `@core/router` |
| Settings, live | `useSettings()` | `shell` |
| An empty state | `Empty` (`ContourBadge` + line + sentence) | People's `bits.tsx` today, promote to `blocks` |
| A person or org initial | `Avatar` (round for people, `rounded-sm` for organizations and projects) | `bits.tsx`, promote |
| Tags | `Tags` (`chip bg-surface-subtle`, `#tag`) | `bits.tsx`, promote |
| Dates | `relativeTime`, `formatDate` | People's `format.ts`, promote |

**Buttons** are `.btn` + a size (`btn-sm` 32px, `btn-md` 40px, `btn-lg` 44px, `btn-hero` 52px) + a variant:
`btn-primary` (forest), `btn-soft` (the default secondary), `btn-ghost`, `btn-danger-ghost` (Delete), `btn-sun`
("needs you" calls to action), `btn-record` (the live action, and destructive confirms). All lift 1px on hover and
settle to `scale(.98)` on press. **Icon buttons** are `.icon-btn` (36px, a bigger invisible hit area) and always have
`aria-label`, usually `data-tip` too. **Fields** are `.field`. **Key caps** are `.kbd`.

## 9. Patterns from The Lodge's screens

These are how The Lodge's real screens are built. New modules follow the same patterns, so the merged app reads as
one piece.

**List rows.** A `panel divide-y divide-line overflow-hidden`. Each row is a link (`<a href="#/…">`) laid out as a grid:
an avatar or tile, then two lines (title `text-label font-medium`, detail `text-hint text-ink-soft`, both
`truncate`), then a fixed-width status column, then right-aligned metadata in `text-meta` that hides below `sm`.
Rows are `px-5 py-3`, with `hover:bg-forest/[.05]`. (`PersonLine` in People, `TaskRow` in the project app.)

**Lists with filters.** `PageHeader`, then a `Segmented` filter with counts (`All 412`, `Strong 38`…), then sort as
a `Select`, then the panel. **Filters and sort live in the hash query** (`#/crm/people?tier=strong&sort=recent`)
through `useQueryParams`, so every filtered view can be linked and survives a reload. Load 100 at a time.

**Detail pages.** A `page-title` with the name, one meta line under it, actions on the right, then a `Segmented`
for the page's views, then sections. Everything is a page with its own route, never a modal, so links from search,
other modules and the Mac menu can open it.

**Home.** The scene in an `.art-frame` with a soft forest glow behind it, the date as an eyebrow, a `hero-title`
greeting ("Good morning"), and the app's name and tagline as `hero-sub`. Then each module's block: in a `panel` card
by default, or full width (`homeWide`) for a module that lays out its own sections. A Home section is a forest well,
a heading and blurb, and a "See all" link on the right.

**Settings.** One `Section` per module, made of `ControlRow`s: well, label and hint on the left, control on the
right. **A hint says what happens:** "Off: action items from your meetings wait in My tasks until you move them."

**Background work and AI.** Slow work is never a spinner on a frozen screen. It's a job, shown where the thing is:
`JobChip` in a row, `JobStatus` on the page, with "Needs you" (sun) and a button when it waits for approval.
**Anything AI wrote says who wrote it** ("Written by Claude"). AI never runs without the person knowing, and cloud AI
is only ever a choice in Settings.

**Review before it lands.** The Lodge's inbox reads a document, proposes what to add (each person as Same as, New
or Skip), and waits for you. Imports and AI changes follow that rule: propose, show, then apply, and record the
`source` so they can be taken back.

**Destructive actions.** `btn-danger-ghost` to start, then a confirm with a plain title, a body that says what will
happen and how to undo it, and `btn-record` to go ahead. Focus starts on Cancel.

**Errors.** A callout: `rounded-lg border border-trail/20 bg-trail-soft/70 p-4 text-label text-trail-deep`, with a
semibold first line ("That didn't go through"), the reason under it, and "Try again".

**Avatars.** Initials on `surface-subtle`, `ink-soft`, semibold. Round for people, `rounded-sm` for organizations
and projects. No photos yet (planned), and no colored avatars. The project app's own avatar for you sits on
`sky-soft` (You = sky).

**Dates.** Relative in lists ("3 days ago", "in 2 weeks", "yesterday", "today"), absolute on detail pages
("Oct 20, 2026"). Day-only values are parsed at noon. *New:* give a relative date a `data-tip` with the absolute one.

**Counts in the sidebar.** `NavCount`: a small `bg-forest/10` pill with `text-forest-deep`, `tabular-nums`. Count what's waiting on you (items to review, open tasks), and show nothing at zero.

## 10. Icons

One family: **Lucide**, at **1.8 stroke**, in `currentColor`. Use 16px for everyday UI, 18px for important controls,
and 20px in dialog wells and primary actions. Wrap new icons with `icon()` in `icons.tsx`, so the defaults and
`aria-hidden` apply. Icons are `ink-soft` at rest, `ink` on hover and forest when active. Outdoor icons (`Compass`,
`Leaf`, `Signpost`, `TreePine`, `Mountain`, `Flag`, `Backpack`) are welcome for section headings, but never in place of
a clearer functional icon.

## 11. Motion

Calm and physical: things lift when you point at them, settle when pressed, and rise gently into place.

- **Easing:** `--ease-out` `cubic-bezier(.2,.8,.2,1)` for nearly everything. `--ease-spring`
  `cubic-bezier(.34,1.56,.64,1)` only for small moments: the switch thumb, the check pop.
- **Durations:** 140–180ms for hovers and color, 80ms for a press, 200–300ms for menus, thumbs and collapses, 480ms
  for content entering.
- **Entrances:** `animate-enter` (fade and rise 8px), staggered 60ms. Menus use `animate-pop`, dialogs
  `animate-dialog-in`, scrims `animate-fade-in`.
- **Live things:** `animate-soft-pulse` for a chip's dot, `animate-ring-pulse` for `Pulse`.
- **Atmosphere:** The Lodge's hero drifts up to about 5px with the pointer, and the stove smoke sways on Home.
- **Reduced motion is always honored.** A global rule in `index.css` stops all animation, and artwork checks
  `prefers-reduced-motion` itself.

## 12. Voice and copy

Plain, warm and brief, like a capable friend who also hikes.

- **Sentence case everywhere:** buttons, headings, menu items, chips.
- **Labels say what happens:** "New task", "Summarize", "Add to your people", "Move to…", "Delete". Outdoor flavor is
  for brand moments only: hero titles, sign-in, the tagline. Never in a functional label.
- **Hints explain consequences:** "Off: …".
- **Errors say what happened, then what to do,** without blame: "The summary didn't come through." Then the reason
  and the fix.
- **Empty states say what will appear:** "Your first project will appear here, with its tasks and how far along it is."
- **People are named, not "users".** "You" and "Them", or the person's name ("Waiting on Ana").
- Curly quotes (“ ” ’), a real ellipsis (`Saving…`), `·` between items of metadata. **No exclamation marks, no
  "Oops", no emoji.**

## 13. Accessibility

- Reuse the kit: its primitives already have roles, keyboard handling and labels.
- Icon-only buttons need `aria-label`. Decorative SVG gets `aria-hidden`. Illustrations get `role="img"` and a short
  description.
- Visible focus (`:focus-visible`, a 2px forest outline) on everything.
- Never use `ink-faint` for text someone has to read. Status is never color alone.
- Pointer targets are at least 28px.
- Everything should work from the keyboard: `⌘K` for search, Return to open, Escape to close, and in the project
  app Space to tick.

## 14. Native (macOS) parts

Native parts use the same palette through `Brand` ([`tokens/Brand.swift`](tokens/Brand.swift), with The Lodge's values
and a light/dark `Color`). The system font (SF) is used: titles 13pt semibold, details 11pt `.secondary`.
`.tint(Brand.forest)`. Menu bar icons are template line art of the app's mark, 18×18, with a 1.9pt main stroke and
1.3pt detail. Build with the Command Line Tools only: no `@State`, `@Entry` or `#Preview` macros.

## 15. Do and don't

**Do:** use the kit first · design Day and Dusk together and look at both · keep one primary per screen and one live
action per app · pair `soft` with `deep` · stagger entrances and honor reduced motion · put filters in the hash ·
show who wrote anything AI wrote · keep copy short and in sentence case.

**Don't:** hex, `rgb()` or named colors in components · Tailwind's default palette or sizes (`gray-500`, `text-sm`)
· new radii, shadows or easing curves (add a token instead) · black shadows in Day, pure white backgrounds, pure
black text · orange except for the live action, errors and destructive confirms · bold, uppercase eyebrows, or
Fraunces below page-title size · the native `<select>`, `window.confirm` or `title=` tooltips · emoji, stock photos,
gradient blobs · color as the only signal.

## 16. Before calling UI work done

`scripts/check` runs the tests, the type check, the build, and these style rules (each should print nothing):

```bash
grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' core/web modules --include='*.tsx' --include='*.ts' | grep -vE 'illustrations\.tsx|components/ui\.tsx|web/theme\.ts'
grep -rnE '\b(gray|slate|zinc|neutral|stone|red|blue|green|amber|emerald)-[0-9]{2,3}\b' core/web modules
grep -rnE '\btext-(xs|sm|base|lg|xl|[2-9]xl)\b' core/web modules
grep -rnE '\bfont-bold\b|\buppercase\b' core/web modules
grep -rnE '<select\b|window\.confirm\(' core/web modules
```

Then look: both themes (Settings → Appearance, or `localStorage["<app id>.theme"] = "dusk"`) · 375px and 1440px
wide · keyboard only · reduced motion on · next to The Lodge: does it look like a sibling?

After editing `tailwind.config.js`, restart the Vite dev server. It doesn't hot-reload that file.
