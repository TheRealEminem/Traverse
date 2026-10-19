# The project app: a blueprint

A project manager built as a sibling of The Lodge, so it can ship as its own app now and become part of one app
with The Lodge later, without rewriting either. This is a proposal: names, screens and tables are a starting point to
change. The rules it follows are not optional, though, because they're what make the merge free. They come from
[`02-data-and-storage.md`](02-data-and-storage.md) and [`01-ui-and-ux.md`](01-ui-and-ux.md).

**Working name: Cairn.** A cairn is the pile of stones that marks a trail, built one stone at a time, much as a
project moves milestone by milestone. It sits beside Trailmix (out on the walk) and The Lodge (where your people
are). Rename it freely: only `app.json` and the mark carry the name.

---

## 1. In one paragraph

Cairn is the family host (the same `core/` as The Lodge) plus **one module, `tasks`**: the family's existing Tasks
module, grown up to hold projects, milestones and real work items. It uses The Lodge's tokens and components
unchanged, and has its own name, mark and scene. It knows people through a small **people directory** in the host
(proposed), which People fills when it's present. Everything it stores uses random text ids, refs and prefixed
tables. So the day you want one app, **The Lodge with the new Tasks module already is that app**: merging means
copying Cairn's `tasks_*` rows into The Lodge's database.

## 2. Before you start: three things to do in The Lodge

These keep the two apps from drifting apart. Do them first. Each is small, and each is much harder later.

### 2.1 One source of truth for shared code

`core/`, `mac/`, `scripts/` and every module used by more than one app (`tasks`, `notes`) must be **one copy** that
every app takes, never edited inside an app (02 §5, the one-lineage rule). The Lodge's `core/` is already well ahead
of `_reference/Trailmix Design Family/starter` (it has backups, the scheduler, job lanes, export and structured AI).
**Start Cairn from The Lodge, not from the old starter.**

The simplest setup for one person:

```
~/Code/TrailmixFamily/        the source of truth: core/, mac/, scripts/, modules/tasks, modules/notes,
                              DESIGN.md, ARCHITECTURE.md (start it as a copy of The Lodge minus modules/crm and identity/)
~/Code/TheLodge/              app.json, identity/, modules/crm      + a synced copy of the family's shared parts
~/Code/Cairn/                 app.json, identity/                    + a synced copy of the family's shared parts
```

Each app gets a `scripts/sync-family` that copies the shared folders in from `TrailmixFamily`. `scripts/check` should
fail when they differ. Change shared code in `TrailmixFamily` and sync it into both apps. (A git subtree or
submodule does the same job if you'd rather.)

### 2.2 Move The Lodge's own look out of `core/`

Today The Lodge's identity lives inside the shared host. These are the only places, so it's a contained move into
an `identity/` folder at the repo root (a `@identity` alias next to `@core`):

| Now in `core/` | What's Lodge-specific | Moves to |
| --- | --- | --- |
| `web/index.css` | the palette (`:root` and Dusk values), `--grain`, `--glow-hearth` | `identity/tokens.css` (imported first) |
| `web/index.html`, `web/theme.ts` | `theme-color` hexes `#F7F4EC` / `#0E1416` | read `--bg` from the page instead |
| `web/components/illustrations.tsx` | `Logo`, `LodgeScene`, `Ambient`'s growth rings, `ContourBadge`'s rings | `identity/art.tsx` exporting `Logo`, `Scene`, `Ambient`, `Badge` |
| `web/views/Home.tsx`, `views/Login.tsx` | `LodgeScene`, "Come on in" | `Scene` from identity, `identity/copy.ts` |
| `web/views/YourData.tsx` | "Everything The Lodge holds… people, notes, the inbox" | `app.name`, and counts from modules |
| `server/backup.py` | counts `crm_entities` to label a backup | an optional `Module.count` |
| `web/public/favicon.svg`, `mac/Sources/AppHost/Mark.swift`, `mac/AppIcon.icns` | the mark | `identity/` (the build copies them in) |

After this, `core/` is byte-for-byte the same in every family app. Check The Lodge looks exactly as before.

### 2.3 Promote what a second module needs

Cairn will want these, and they live in People today. A module may not import another module, so move them to the host:

- `modules/crm/web/format.ts` (`relativeTime`, `formatDate`, `initials`) → `core/web/format.ts`
- `Avatar`, `Empty`, `Tags` from `modules/crm/web/bits.tsx` → `core/web/components/blocks.tsx`
- `normalize_tags` from `modules/crm/server/store.py` → `core/server/tags.py` (so tags normalize the same everywhere)

## 3. The big decision: projects live in the Tasks module

The family already has a Tasks module. It's in The Lodge, it receives action items from any module through the
`actions.found` contract, and it links each one back to where it came from. A project manager is mostly tasks. Three
ways to build it were considered:

| Option | What it means | Verdict |
| --- | --- | --- |
| A new `projects` module next to `tasks` | Two task lists in the merged app (to-dos and project tasks), and a contract to move things between them | ✗ "Where do my tasks live?" is the classic project-app confusion |
| `projects` for containers, `tasks` for items | Project pages need progress, counts and due dates from another module's tables, which the rules forbid | ✗ forces chatty contracts for the app's core feature |
| **Grow `tasks`** (chosen) | One module owns the whole of "work": projects, milestones, items, updates. Action items keep flowing in exactly as today | ✓ one place for work, no cross-module reads, and The Lodge simply takes the new version |

Consequences:

- The module id stays **`tasks`** (permanent: it's in table names and refs). Its display name becomes **"Projects"**,
  with "My tasks" and "Projects" in the sidebar.
- Its schema grows by **appending step 2** to its migrations: [`schema/tasks-v2-projects.sql`](schema/tasks-v2-projects.sql).
  This has been tested against a copy of The Lodge's schema: existing to-dos become work items (status follows
  `done`, action items keep their source), and the new foreign keys, cascades and checks work.
- From now on, **Cairn's repo is where `tasks` grows** (via `TrailmixFamily`). The Lodge takes each new version. When
  it does, The Lodge gains projects. Hide them with a `tasks.projects` setting if you don't want them there yet.

## 4. Data model

```
tasks_projects ──< tasks_milestones
      │                  │
      └──< tasks_items >─┘           an item belongs to at most one project and one milestone
             │  ├──< tasks_items      subtasks (parent_id)
             │  └──< tasks_blockers   what has to happen first (item ↔ item)
             └──< tasks_updates >──── projects too: comments, status updates, AI summaries
tasks_fts    search over projects and items
```

Cross-module, by ref (no foreign keys):

```
tasks_items.source_ref    ──→  crm:<meeting or doc>    where an action item came from        (+ link "action-item")
tasks_items.assignee_ref  ──→  core:me | crm:<person>  who's doing it                        (+ link "assigned")
tasks_projects.owner_ref  ──→  core:me | crm:<person>  who answers for it                    (+ link "owner")
core_links  tasks:<project> ──→ crm:<organization>      the client, or the topic              kind "about"
core_links  tasks:<project> ──→ crm:<person>            people with a stake, not doing work   kind "stakeholder"
core_links  tasks:<project> ──→ crm:<meeting>           meetings about it                     kind "discussed-in"
```

Why a column **and** a link for assignee and owner: the column lets Cairn ask "what's assigned to Ana?" quickly in
its own table. The link lets a person's profile in The Lodge show "Projects · 2 tasks" through `LinkedList` without
reading Cairn's tables. The store sets both in one function.

### Vocabularies (plain strings, listed in `modules/tasks/server/vocab.py`, served at `GET /api/tasks/meta`)

**Work item status**

| Value | Label | Tone | Meaning |
| --- | --- | --- | --- |
| `todo` | To do | neutral | not started |
| `doing` | Doing | sky | someone is working on it |
| `waiting` | Waiting | berry | it's with someone else ("Waiting on Ana") |
| `done` | Done | forest | finished; `completed_at` set, `done = 1` |
| `dropped` | Dropped | neutral, struck through | won't happen, kept for history |

**Project status:** `planned` (neutral) · `active` (sky) · `paused` (neutral) · `done` (forest) · `dropped` (neutral).

**Project health** (your judgment, set with each status update): `on_track` (forest, "On track") · `at_risk`
(sun, "At risk") · `off_track` (trail, "Off track") · `NULL` (no chip).

**Priority** (an integer so it sorts): `0` none (nothing shown) · `1` low ("Low", ink-soft) · `2` high (flag icon +
"High", ink) · `3` urgent (sun chip "Urgent").

**Worked out, never stored:** *overdue* (`due_on` before today and not done: trail, "3 days late"), *due soon*
(today or tomorrow: sun, "Due today"), *blocked* (an open blocker: trail chip "Blocked"), *progress* (done ÷ (all −
dropped), per project and milestone).

### Rules for the store

- One function changes status, and it keeps `done`, `completed_at` and `updated_at` in step.
- Every write re-feeds `tasks_fts` for that row, and publishes `tasks.changed` (with `project_id`).
- Deleting an item or project publishes `item.deleted` and calls `links.forget`. Archiving a project only sets
  `archived_at`.
- `take_actions` (the `actions.found` handler) files new items into a project when the source is linked to exactly
  one project, or when the `details` say which (see §7). Otherwise they wait, unfiled, in My tasks.
- `export()` returns `{projects, milestones, items, updates, blockers}`.

## 5. Cairn's own look

Everything shared stays shared: **The Lodge's tokens exactly**, the fonts, the components and the motion. That way,
merging changes nothing visually. Cairn makes only the things the family leaves to each app (01 §2):

| Slot | Cairn (proposed) |
| --- | --- |
| `app.json` | `{"name": "Cairn", "id": "cairn", "tagline": "what's next, and how far you've come", "bundleId": "com.cairn.app", "envPrefix": "CAIRN", "port": 8793, "updateRepo": "", "modules": ["tasks"]}` |
| Port | 8793 (8792 is already used by a local preview config in The Lodge). Add it to the table in ARCHITECTURE.md §5 (Trailmix 8765, Starter 8790, The Lodge 8791) |
| Mark | [`assets/project-app-mark.svg`](assets/project-app-mark.svg): the family tile in sky (`#4F86A8 → #285B7A`), the same hills, contours and low sun, and a cairn of three cream stones. The stones are filled rather than stroked so they stay legible at 16px. Menu bar: the same stones as 1.9pt line art |
| Hero scene (`Scene`) | A ridge trail climbing in switchbacks to a summit, a cairn at each turn (the nearest large, in the foreground), a small flag on top. Same `DAY` palette keys and layer order as `LodgeScene`, and it keeps the clock the same way |
| `Ambient` motif | A route drawn on a map: a faint dashed line wandering top right between small waypoint dots, in a warm `--route` color at the strength of The Lodge's `--grain` |
| Empty-state badge | An icon in a forest well, ringed by a short dashed route instead of growth rings |
| Live action (orange) | **None.** Keep `btn-record` for Trailmix's recording, so the merged app still has only one. If Cairn ever times work, a running timer is a sky `StatusChip` with `live` |
| Sign-in | "Pick up the trail" |
| Section icons | Lucide: `Mountain` (projects), `Flag` (milestones), `Signpost` (what's next), `ListChecks` (my tasks), `Kanban` (board) |

## 6. People: knowing who's who without People

Cairn needs people for assignees, owners and stakeholders. The Lodge's People module is the real source, but Cairn
ships without it and must still work. ARCHITECTURE.md §13 already expects "a shared people list" to be added to the
host when a second module needs one. Cairn is that module. **Proposed host addition:**

```python
# core/server/module.py: one new optional field, alongside search and describe
people: Callable[[str, int], list[dict]] | None = None
#   (q, limit) -> [{"id", "name", "email"?, "detail"?, "is_self"?}]   People implements it over crm_entities

# core/server/people.py (new): the host merges every provider, like search.py does
def find(q: str, limit: int = 8) -> list[dict]:
    """[{ref, name, email, detail, module}], best first. The owner always comes back as "core:me", never as
    "crm:<self>", so you are stored the same way in every module and every app."""
def by_email(email: str) -> str | None:
    """The one ref with this email, or None (none, or more than one)."""
# and module.describe("core:me") -> {"title": settings core.your_name or "You", "href": "#/settings"}
```

```
GET /api/people?q=ana      -> [{ref, name, email, detail, module}]     (core/server/app.py)
```

On the web, a `PersonPicker` in `core/web/components/blocks.tsx` (a field with a `Select`-style popover) gives
`{ref, name}`: "You" first, then directory matches, then "Use “Ana” as a name" for someone the app doesn't know (ref
`null`, name only). Cairn's own picker also suggests names it has used before, from its own table.

How it behaves:

| Situation | What's stored, or what happens |
| --- | --- |
| You, in standalone Cairn | `assignee_ref = "core:me"`, named from Settings → Your name |
| You, inside The Lodge | the same `core:me`. The directory returns People's "me" as `core:me` |
| Ana, in standalone Cairn | `assignee_ref = NULL`, `assignee_name = "Ana Ruiz"` |
| Ana, inside The Lodge | `assignee_ref = "crm:9a1c…"`, `assignee_name = "Ana Ruiz"`, picked from your People |
| After merging | a `tasks/match_people` job fills `NULL` refs where the name or email matches exactly one person. You confirm the rest on the task ("Is this Ana Ruiz?") |
| Ana merged into another record | Cairn hears `people.merged` and rewrites its refs |
| Ana deleted | Cairn hears `item.deleted`, keeps `assignee_name` and clears the ref |

The contracts are in [`schema/contracts-proposed.py`](schema/contracts-proposed.py). People needs two small changes to
publish them (02 §12).

## 7. How Cairn ties into The Lodge

| In The Lodge | In Cairn | Mechanism |
| --- | --- | --- |
| A meeting's action items | New work items, linked back to the meeting | `actions.found` (works today) |
| …from a meeting linked to a project | Filed straight into that project | `take_actions` checks `links.linked(source_ref)` for a `tasks:` project |
| …with "Ana to send the outline by Friday" | Assignee and due date filled in | `actions.found` `details` (proposed; People's extraction already sees owners and dates) |
| An organization (a client) | The project is "about" it | link `about`; the org's profile lists the project |
| A person | Assignee, owner or stakeholder | ref column + link; the person's profile lists them (needs `LinkedList` on profiles, 02 §12) |
| Search (⌘K) | Projects and tasks in the same box | `Module.search` over `tasks_fts` |
| Home | A "What's next" card beside People's sections | `ModuleWeb.home` |
| Granola or calendar meetings | (nothing new) | they already reach Tasks as action items via People |

## 8. Screens

All of it is built from the kit (01 §8). Nothing here needs a new color, radius, shadow or font size.

**Sidebar:** the primary button **"New task"** (Cairn's `primary`; in the merged app it's the only module with one,
so it becomes the big button), then **My tasks** (badge: due today plus overdue) and **Projects**.

| Route | View | Notes |
| --- | --- | --- |
| `#/tasks` | My tasks | `?when=today\|week\|all\|waiting` in the hash |
| `#/tasks/projects` | Projects | `?status=active\|planned\|done\|all` |
| `#/tasks/p/:id` | A project | `?view=overview\|list\|board`. The board uses `wide: true` |
| `#/tasks/t/:id` | A task | a page, not a modal, so any link (a meeting, search, the Mac menu) can open it |

**My tasks.** `PageHeader` "My tasks". A `Segmented` with Today · This week · Everything · Waiting on others. Groups
under eyebrows: Late, Today, This week, Later, No date, and "Not in a project yet" (action items, each with a
`Select` "Move to…"). Rows are `TaskRow`s in a `panel divide-y divide-line`.

**TaskRow** (one component, used everywhere): an 18px round check (forest when done, with `animate-check-pop`), the
title (`text-label`), a meta line (`text-hint ink-soft`: "Riverbend relaunch · Designs signed off"), then chips
(status when not To do, Blocked, Urgent), the assignee's 24px `Avatar` (yours on `sky-soft`), and the due label
(`text-meta`, `tabular-nums`). A done row goes `ink-soft` with a line through, then leaves open lists after a
moment. Space ticks it, Return opens it. Hover is `bg-forest/[.05]`, like People's rows. Below 640px the chips,
avatar and due date move to a line under the title, so the title is never cut to a few letters.

**Projects.** `PageHeader` "Projects" with "New project" (`btn-primary`, the one primary on the screen). Each row has
a project tile (an `Avatar` with `rounded-sm` and its initial: projects get no colors, because color is for meaning),
the name and summary line, a health chip, a progress bar with "12 of 30 done", the due date as relative time, and the
owner's avatar.

**Progress bar:** a 6px `rounded-full` track in `bg-line-strong`, filled `bg-forest` (the `.range` scrubber's look,
without the thumb), always with the words next to it. No donut charts, and no percentages on their own.

**A project.** A `page-title` with the name. Under it, one meta line: owner · due · health chip. Actions: "New task"
(primary) and a "More" icon button (Archive, Delete behind `useConfirm` with `btn-record`). A `Segmented` switches
views:

- **Overview:** the summary and brief (`prose-family`); milestones as rows with their own progress; the latest status
  update with "Write an update" and "Draft one with AI" (a job, with `JobStatus`); people (owner, stakeholders); and
  `LinkedList` (meetings, the client).
- **List:** items grouped by milestone, dragged to reorder (`sort`).
- **Board:** a column per status on `inset-surface`, headed by an eyebrow and a count. Cards are `rounded-lg
  bg-surface border border-line shadow-sm p-3.5`. They lift 1px on hover and take `shadow-lg` while dragged.
  Nothing tilts.

**A task.** The title (editable), then `ControlRow`s for Status (`Select`), Project, Milestone, Assignee
(`PersonPicker`), Due, Priority and Estimate. Below those: notes (markdown), subtasks, "Blocked by", updates and
comments, "From: Kickoff with Riverbend" (the source, described by its module) and `LinkedList`.

**Home card** (`home`, inside a panel): "What's next", with late and due-this-week items (up to five `TaskRow`s) and
projects at risk or off track. "See all" goes to `#/tasks`.

**Settings section** (`Section` with a `Mountain` well, "Projects"):
- *File action items into projects* (`SwitchRow`). "Off: action items from your meetings wait in My tasks until you
  move them."
- *Week starts on* (`Select`: Monday, Sunday).
- *Draft weekly status updates* (`SwitchRow`). "Off: write them yourself. On: each Friday a draft waits on every
  active project for you to edit or discard."

**Empty states** (`ContourBadge`, or Cairn's `Badge`):
- Projects: "No projects yet". "Your first project will appear here, with its tasks and how far along it is."
- My tasks: "Nothing due". "Tasks you add, and action items from your meetings, will appear here."
- A board column: "Nothing here".

## 9. API (`/api/tasks`)

Keeps today's routes and adds to them. Fixed paths are declared before `/{id}`.

```
GET    /api/tasks                          work items: ?project= &assignee= &status= &when= &q=
GET    /api/tasks/count                    {open, due_today, late}            (the sidebar badge)
GET    /api/tasks/meta                     statuses, project statuses, health, priorities: labels and tones
POST   /api/tasks                          {text, project_id?, due_on?, assignee_ref?, assignee_name?, …}
GET    /api/tasks/{id}                     one item: subtasks, blockers, updates, source, links
PATCH  /api/tasks/{id}                     any field (today's {done} keeps working)
DELETE /api/tasks/{id}
POST   /api/tasks/{id}/move                {project_id, milestone_id, after_id}   → sort
GET    /api/tasks/projects                 with rollups: counts by status, progress, next due, late
POST   /api/tasks/projects
GET    /api/tasks/projects/{id}
PATCH  /api/tasks/projects/{id}            including archived_at
DELETE /api/tasks/projects/{id}
POST   /api/tasks/projects/{id}/milestones · PATCH/DELETE /api/tasks/milestones/{id}
POST   /api/tasks/projects/{id}/updates    {kind, body, health?}
POST   /api/tasks/projects/{id}/draft      queue an AI status draft (a job)
```

Errors are `HTTPException` with a sentence a person can read ("A task needs some text"). Creates return `201` with
`{id}`, and deletes return `204`.

## 10. Background work and AI

| Job (`tasks/<kind>`) | What | Lane | Notes |
| --- | --- | --- | --- |
| `draft_update` | a project status draft from what changed since the last update | default | `approve=True` unless the setting is on. Shown with who wrote it |
| `break_down` | suggest subtasks for a task | interactive | `ai.structured` with a small schema. You pick which to add |
| `weekly_drafts` | queue `draft_update` for every active project | recurring (daily) | does nothing unless it's Friday and the setting is on. The host scheduler runs on intervals, not days of the week |
| `match_people` | fill `NULL` person refs that match exactly one person | default | on startup when a people provider exists, and after `core.restored` |

AI runs only in jobs, never inside a request, and anything AI wrote says so (`written_by`, "Written by Claude").

## 11. Build order

In the same chunked way as The Lodge's PLAN.md: stop at each "done when" and look.

| # | Chunk | Done when |
| --- | --- | --- |
| 0 | `TrailmixFamily` as the source of truth. The Lodge's identity moved out of `core/`. Shared helpers promoted (§2) | The Lodge passes `scripts/check` and looks the same; `core/` is identical in both repos |
| 1 | Cairn from the family: `app.json`, `identity/` (mark, scene placeholder, The Lodge's tokens) | Cairn.app launches on 8793 with an empty sidebar, in Day and Dusk |
| 2 | Tasks v2 data: migration step 2, store, vocab, API, tests (including an upgrade test from v1 rows, like People's `test_upgrade.py`) | Old to-dos survive the upgrade; the API round-trips everything |
| 3 | My tasks, quick add, the task page | Add, tick, date and open tasks from the keyboard |
| 4 | Projects list and project page (overview, list), milestones, progress | A real project, with its milestones and tasks, reads right |
| 5 | Board view and drag to reorder or move | Drag between columns updates status; order sticks |
| 6 | People directory in the host, `PersonPicker`, `core:me`, assignee and owner links, `match_people` | Assign to you or to a typed name. In The Lodge, pick from People |
| 7 | Home card, search, export, Settings | ⌘K finds projects and tasks; export includes them |
| 8 | AI: status drafts, break down; `actions.found` details | A draft appears, says who wrote it, and can be edited or discarded |
| 9 | Mac: mark, `Mark.swift`, icon, build and install | Cairn.app installs beside The Lodge, and both run at once |
| 10 | Back in The Lodge: take the new `tasks`, close the gaps in 02 §12 | A meeting's action items land in its project, and Ana's profile lists her tasks |

## 12. Becoming one app

1. Both apps are on the same `core/` and the same `tasks` version (they will be, if chunk 0 holds).
2. The Lodge's `app.json` already lists `["crm", "tasks"]`, so with the new Tasks module **it is the merged app**.
   Optionally rename it, give it a merged identity, and change its tagline.
3. Copy Cairn's rows into The Lodge's database with the merge script (02 §11): `tasks_*` tables, `core_links`, and the
   `tasks.*` settings. `match_people` then connects Cairn's names to The Lodge's people.
4. Retire Cairn.app, or keep it as a focused window onto the same module.

## 13. Checklist for every Cairn change

- [ ] Nothing imports `modules/crm`, reads `crm_*`, or calls `/api/crm` from the server.
- [ ] New tables start `tasks_`, ids come from `db.new_id()`, days are `_on`, instants are `_at`, and refs have a `_name` beside them.
- [ ] Schema changes are a new migration step, made in the family's one copy of `modules/tasks`.
- [ ] Slow work, and all AI, is a job. Jobs are safe to run twice.
- [ ] Every screen works in Day and Dusk, at 375px and 1440px, by keyboard, and with reduced motion.
- [ ] No hex colors, default Tailwind palette or sizes, bold or uppercase, and no color without a word (`scripts/check`).
- [ ] Copy is sentence case, says what happens, and has no exclamation marks.
- [ ] `scripts/check` passes.
