# Traverse: implementation plan

_Planning document, written 2026-10-18. Tick the boxes as chunks close. Work one chunk at a time and stop at its
"done when" so Mark can look before the next one starts._

Traverse is Mark's own workspace for Cold Connect's work: the project app from the Lodge design guide's blueprint
(working name Cairn, `_reference/Lodge Family Design Guide/03-project-app-blueprint.md`), built as a Trailmix family
app, plus a connection to **Plane**, which stays the team's database and the place everyone else works. Traverse is
where Mark plans, captures and drafts with AI; Plane is where the shared result lives. Nothing reaches Plane until
Mark sends it, and nothing Traverse does can delete or overwrite a teammate's work.

## Progress

| # | Chunk | Size | Status |
| --- | --- | --- | --- |
| 0 | Family source of truth: `TrailmixFamily`, The Lodge's look out of `core/`, shared helpers promoted | M | ◐ 2026-10-18: committed on The Lodge's `family/source-of-truth` (a48764e, 00644eb) and TrailmixFamily (up to 84ea14d); The Lodge's main untouched |
| 1 | Traverse from the family: repo, `app.json`, `identity/`, an empty app that launches | S | ☑ 2026-10-18 on `chunk-1/traverse-from-family` |
| 2 | Tasks v2 data: projects, milestones, items, updates (migration step 2) | M | ☑ 2026-10-19 (family 842c525) on `chunk-2/tasks-v2` |
| 3 | My tasks, quick add, the task page | M | ☑ 2026-10-19 (family 1584a3a) on `chunk-3/my-tasks` |
| 4 | Projects list and project page, milestones, progress | M | ☑ 2026-10-19 on `chunk-4/projects` |
| 5 | Plane connection and a read-only mirror; Team view; the people directory | M–L | ☑ 2026-10-20: live check against Cold Connect's Plane passed |
| 6 | Linking: Traverse projects ↔ Plane projects, bringing Plane items in, "Changed in Plane" | M | ◐ 2026-10-20 (family ca89799) on `chunk-6/linking`: Mark's 23 items are linked tasks; following a Plane edit is tested against the fake Plane, not yet with a real edit |
| 7 | **Push to Plane**: previews, changed fields only, conflict stops, log and undo | L | ◐ 2026-10-20 on `chunk-7/push`: every §3.3 rule tested against the fake Plane; live, a dry run only (dry run is on until Mark turns it off) |
| 8 | Board view and drag | M | ◐ 2026-10-19 (family bf6d30a) on `chunk-8/board`; cards say "1 change to send" since chunk 7 |
| 9 | Inbox: capture anything, AI proposes work items, you review | L | ☑ 2026-10-19 on `claude/chunk-9-inbox-362a27` |
| 10 | Meetings from Trailmix | S–M | ☑ 2026-10-19 on `claude/chunk-9-inbox-362a27` |
| 11 | MCP server in the host: Claude Desktop and Claude Code can use Traverse | M | ☑ 2026-10-20 on `chunk-11/mcp`: Claude Code answered from the dev server, left 4 proposals in the inbox and a push waiting in the Outbox; Claude Desktop's config tried over stdin, not in the app |
| 12 | AI in the app: status drafts, break a task down | M | ☑ 2026-10-21 on `claude/chunk-12-ai-c80a35` (from `chunk-11/mcp`): drafts and breakdowns tried live on Ollama; a status update waits in the Outbox as a comment, never sent (dry run) |
| 13 | Home card, search, export, Settings, the auto-sync switch | M | ☐ |
| 14 | Mac: mark, menu, build and install beside The Lodge | M | ☐ |

Milestones: **A** "it runs" = 0–1 · **B** "my work, locally" = 2–4 · **C** "sees the team" = 5–6 ·
**D** "shares with the team" = 7–8 · **E** "AI does the typing" = 9–12 · **F** "shipped" = 13–14.

Sizes are relative effort (S ≈ one sitting, M ≈ a few, L ≈ many), not calendar time.

**Merged 2026-10-19** on `merge/plane-inbox-updater` (from `chunk-8/board`): chunk 5 (`claude/chunk-5-plane-mirror-ebcfba`),
chunks 9-10 (`claude/chunk-9-inbox-362a27`) and F4 (`claude/family-f4-updater-8da213`), which were built in parallel
sessions. `app.json` now runs `tasks`, `plane` and `inbox`; the shared parts (the people directory, the updater and
release flow) are in the family at 44da03f, and sync-family shares the three new release files. One conflict (the
progress table in this file) and one test that still read a task's origin as `source` rather than `came_from`. All 198
tests pass, the Mac app builds, the update checks pass, and Home, Team, Inbox and Settings → Plane load in a browser.
**Live check, 2026-10-20:** with Mark's key, Traverse connected to `cold-connect` ("8 projects to choose from"), read
the 7 real projects (49 items, 31 requests; the demo project left off), and the Team view matched Plane exactly: 34
open, Mark 23, Mickey 5, Elijah 2, 4 with no one (6 past due now). Item links use Plane's own keys (SOFTWARE-5 is
"Share Github repo's with Mark"). Found by it: the Plane server field had `https://app.plane.so`, Plane's website,
whose answer isn't JSON; the module now reads Plane Cloud's web address as its API address (`api.plane.so`).
Still open: the Mac menu's Inbox item opens The Lodge's People inbox,
which Traverse doesn't have; the release workflows haven't run on GitHub yet; and updates stay off until `updateRepo`
names a repository the installed app can read.

**Family track** (§6b): work on the shared host in `TrailmixFamily`, done from Traverse and taken by The Lodge when
Mark chooses. Asked for 2026-10-18: the Trailmix adoptions from `TRAILMIX-COMPARISON.md`, and family apps on one
Mac sharing data, keys and basic preferences.

| # | Family chunk | Size | When | Status |
| --- | --- | --- | --- | --- |
| F1 | A backup before an update migrates the database | S | with chunk 1 | ☑ 2026-10-18 (family 5166181) |
| F2 | Gemini's default model (`gemini-2.5-flash` is closed to new accounts) | S | with chunk 1 | ☑ 2026-10-18 (family 5166181) |
| F3 | **Family link:** shared keys and preferences, a registry of installed apps, app-to-app data calls | M–L | after chunk 1 | ☑ 2026-10-18 (family 3a26cf7); The Lodge has it on its `family/link` branch |
| F4 | Updater: beta channel, Go back, skip a version; CI publishes a pre-release and promotes it later | M | before chunk 14 | ☑ 2026-10-19 (family 44da03f); its workflows haven't run on GitHub yet |
| F5 | Lockdown: one switch that stops every cloud call, shared across the family | M | after F3 | ☐ |
| F6 | AI pricing and usage: what each AI call costs, and a running total | M | before chunk 9 | ☐ |
| F7 | Trailmix joins the family link (reads shared keys and preferences, offers its meetings) | S–M | Mark's call | ☐ a change in Trailmix's own repo |

---

## 1. The idea in five lines

1. Traverse is the family host (The Lodge's `core/`, via `TrailmixFamily`) plus three modules: **`tasks`** (the
   family's Tasks module, grown to hold projects; Traverse is where it grows), **`plane`** (the connection to Plane)
   and **`inbox`** (capture and AI triage).
2. Work is made and shaped in `tasks`. `plane` mirrors the team's Plane workspace read-only and sends your changes
   to Plane only when you say so.
3. AI does the typing: it turns meetings, pasted threads and notes into proposed work items, drafts status updates,
   and breaks tasks down. You approve; then you choose what goes to Plane.
4. Claude Desktop and Claude Code can reach Traverse through an MCP server in the host, under the same rules.
5. It shares The Lodge's structure but not its pace: the same host (each app pinned to its own family version),
   tokens, prefixed tables, random ids and refs, so the two can share data later. Each stays its own app.

## 2. Decisions

| # | Decision | Why |
| --- | --- | --- |
| D1 | Traverse is the blueprint's project app (Cairn), renamed, with Plane added | Mark's answer, 2026-10-18. The blueprint already keeps it compatible with The Lodge |
| D2 | **Plane is the team's database.** Traverse is Mark's personal workspace on top of it | Everyone else uses Plane. Traverse is for Mark alone for now |
| D3 | **Push only, and explicit.** Every change to Plane is a job that waits for Mark's approval, with a preview of exactly what will change | "Don't want any random deletes or rewrites of anyone's work" |
| D4 | **Auto-sync is a switch, off by default, per project** (chunk 13). Even on, it never deletes and still stops on conflicts | Mark asked for it as a later, toggleable feature |
| D5 | Plane integration is its own module, `plane`, owned by Traverse. `tasks` stays Plane-free | `tasks` is shared with The Lodge, which doesn't need Plane. If the apps ever combine, `plane` is an add-on |
| D6 | Start from The Lodge's `core/` through a new `~/Code/TrailmixFamily`, doing the blueprint's §2 first (chunk 0). **Each app pins a family version** (`family.lock`) and takes updates when it chooses | Mark's answers, 2026-10-18: one copy of shared code, but The Lodge stays an independently developed app. Only the structure is normalized |
| D7 | The priority scale follows Plane's five levels (none, low, medium, high, urgent), not the blueprint's four | Plane is the database; a scale without "medium" would lose information on every round trip. Must be settled before migration step 2 ships |
| D8 | Plane members become people through the host's people directory (blueprint §6), with `plane` as a provider | Assignees then work the same way with or without The Lodge's People |
| D9 | MCP lives in the host (`core/server/mcp.py`), and modules contribute tools | A shared host feature: any family app (The Lodge too) can expose its modules' tools the same way |

## 3. Plane: what syncs, and the rules that protect the team's work

### 3.1 The direction of each thing

| Thing | Plane → Traverse | Traverse → Plane |
| --- | --- | --- |
| Projects, states, members, labels, cycles | Mirrored, read-only, for linked projects | Never. Traverse doesn't create or edit Plane projects, states, members or settings |
| Work items in linked projects | Mirrored. Items you bring in become linked local tasks | Only fields you changed, on approval |
| New work items | Shown in Team view; "Bring into Traverse" makes a linked copy | Created in Plane on approval, in a linked project |
| Comments | Shown on linked tasks | Your Traverse updates can be posted as new comments on approval (append only) |
| Deletes | A deleted Plane item shows "Removed in Plane" on its local copy; nothing local is deleted | **Never.** Deleting in Traverse only unlinks |
| Private notes, inbox, AI drafts, estimates, blockers | — | Never leave Traverse |

### 3.2 Field map (work items)

| Traverse (`tasks_items`) | Plane | Notes |
| --- | --- | --- |
| `text` | `name` | |
| `notes` (markdown) | `description_html` | Converted on push. Whole-field write, so the conflict check matters most here |
| `status` | `state` | Mapped by state group: to do → unstarted, doing → started, waiting → started, done → completed, dropped → cancelled. Each linked project picks which of its states to use for each, preset to the group's default |
| `priority` | `priority` | Same five values (D7) |
| `due_on` | `target_date` | |
| `start_on` | `start_date` | (added in chunk 6: the same thing on both sides) |
| `assignee_ref` | `assignees` | Through the people directory: `plane:<member id>`, and `core:me` ↔ Mark's Plane member |
| project | `project` | Only Traverse projects linked to a Plane project can push |
| milestone | (later) | Plane modules or milestones; see §8 |
| subtasks (`parent_id`) | `parent` | Later chunk; only when both are in Plane |

### 3.3 The rules

1. **Traverse never deletes anything in Plane,** in any mode. There is no code path for it, and a test checks that
   the Plane client has no delete method.
2. **Nothing is sent without approval.** Each push is a job parked as **Needs you**, showing field by field what
   Plane has now and what it will have. "Send" sends it; "Discard" forgets it.
3. **Only changed fields are sent.** Traverse remembers, for each linked item, the Plane version it last saw (its
   `updated_at` and field values, the "base"). A push sends the fields you edited since then, never the whole item.
   Fields you didn't touch are never written, so others' edits to them are safe.
4. **Check before writing.** Right before sending, Traverse reads the item from Plane again. If a field it is about
   to send has changed in Plane since the base, it stops and shows both versions, and you choose: keep Plane's,
   send yours, or edit. It never overwrites a teammate's change silently.
5. **Lists are merged, not replaced.** Assignees and labels are sent as Plane's current list plus your additions minus
   your removals, so nobody added in Plane is dropped.
6. **Only linked projects.** A Traverse project is private until you link it to a Plane project. Items in private
   projects can't be pushed.
7. **Everything sent is logged** (`plane_pushes`: the item, each field before and after, when, and that you approved
   it). Each entry has **Undo**, which is itself a push of the "before" values, with the same preview and check.
8. **Dry run** (a setting) prepares and previews pushes but never sends, for trying it out.
9. Traverse signs in to Plane with **your personal API key**, so everything it does shows in Plane as you. The key is
   a write-only secret in Settings → Plane, never sent back to the page.

### 3.4 Pull: the read-only mirror

A recurring job (`plane/pull`, every few minutes while the app is open, and on demand) reads the linked projects'
items, states, members, labels and cycles into `plane_*` tables. The mirror is only ever written by pulls. It feeds:

- **Team view:** who's on what, by person, state and project (the dashboard from this conversation, rebuilt natively,
  plus past-due and unassigned items).
- **The conflict check** in rule 4.
- **Linked tasks follow Plane.** When Plane changes a field you haven't edited locally, the local copy takes Plane's
  value (it changes only your copy). When you have edited it too, the task shows "Changed in Plane" with both values.
- **People:** Plane members feed the people directory (D8).

### 3.5 How the modules meet

`tasks` and `plane` never import each other or read each other's tables:

- A linked task is a link `tasks:<id>` ↔ `plane:<item id>` (kind `synced`) in `core_links`.
- "Send to Plane" on a task publishes a contract **`work.share_requested`** `{ref, local_ref, fields, base,
  project_ref}` with only the fields changed since the base, and their base values. `plane` receives it, parks the
  push for approval and links the task to it (kind `share`) while it waits, so the task can say where. A task not
  linked yet, in a linked project, asks to be made there (`ref` is then the task itself, `base` empty), and comes back
  as `work.arrived` with `local_ref`, which makes it the linked copy. `tasks` doesn't know Plane exists; any future
  sharing module (Linear, GitHub Issues) could listen to the same contract.
- After a pull or a push, `plane` publishes **`work.updated_elsewhere`** `{ref, fields, source, url, take?}` for linked
  items (`take`: fields you chose Plane's value for in the outbox, which follow even though you'd changed them), and
  **`work.removed_elsewhere`** `{ref, source}` for ones gone from Plane. `tasks` applies untouched fields and flags
  the rest.
- "Bring into Traverse" publishes **`work.arrived`** `{ref, fields, project_ref, source, url}` (chunk 6 made this its
  own contract rather than `actions.found`, whose items replace each other and aren't linked), after
  **`work.project_arrived`** `{ref, name, summary, source}` for a Plane project with no Traverse project yet. The
  fields are already named as tasks' own (`contracts.WORK_FIELDS`), so `tasks` never learns Plane's shapes.
- "Post it in Plane too" on an update publishes **`work.comment_requested`** `{ref, local_ref, update_ref, body,
  written_by}` (chunk 12): a linked task's comment, or a project's status update put on one of the project's linked
  tasks, since Plane's API has no project updates. `plane` parks it in the outbox as a comment (append only: Plane's
  comments are never edited or deleted) and links `update_ref` → it, kind `share` while it waits and `posted` once it's
  there, so the update can say which.
- `tasks` keeps each linked task's base and flags in `tasks_synced` (migration step 3); `plane` keeps each project's
  link and state map in `plane_links`. The Linking screen lists Traverse projects through `GET /api/tasks/projects`
  (a page reading another module's public API; the servers still never talk).

Contracts are written down in `core/server/contracts.py` (in `TrailmixFamily`, since they're shared).

## 4. AI tie-ins

| Tie-in | What it does | Where |
| --- | --- | --- |
| **In the app** | Status drafts for projects, breaking a task into subtasks, and the inbox's extraction. Uses the host's providers (Claude, Ollama, others) from Settings → AI, always in jobs, and shows who wrote what | `tasks`, `inbox`, chunk 9 and 12 |
| **Inbox capture** | Paste an email, a Slack thread, notes or a file. AI proposes work items with an assignee, due date and project; you accept, edit or drop each one. Accepted items become tasks; sending them to Plane is a separate, explicit step | `inbox`, chunk 9 |
| **Meetings from Trailmix** | A recurring job reads newly summarized meetings from Trailmix's local API (`127.0.0.1:8765/api/meetings`) and puts their action items in the inbox for review | `inbox`, chunk 10 |
| **MCP server** | `http://127.0.0.1:8793/mcp`, with a local token. Tools: what's on my plate, team workload (from the mirror), find, add a task, capture to inbox, and *propose* a push. Claude can never send to Plane itself: a proposed push waits in Traverse for your approval | host + each module's tools, chunk 11 |

Why an MCP server when Plane already has one: Plane's MCP writes straight to Plane with no guardrails. Traverse's
gives Claude your local context (private notes, inbox, drafts) and keeps every Plane write behind §3.3.

## 5. Traverse's own look

Everything shared stays shared: The Lodge's tokens, fonts, components and motion, unchanged. Traverse makes only
what each app makes (Lodge guide 01 §2, blueprint §5):

| Slot | Traverse (proposed) |
| --- | --- |
| `app.json` | `{"name": "Traverse", "id": "traverse", "tagline": "what's next, and who's on it", "bundleId": "com.traverse.app", "envPrefix": "TRAVERSE", "port": 8793, "updateRepo": "", "modules": ["tasks", "plane", "inbox"]}` |
| Mark | The family's sky tile, the same hills and low sun, and a trail cutting across the slope with a small cairn where it turns. Filled shapes so it reads at 16px |
| Scene | A path traversing a mountainside toward a saddle, cairns along it, the nearest one large |
| Ambient motif | The blueprint's route on a map: a faint dashed line between waypoint dots |
| Live action (orange) | None (kept for Trailmix's recording) |
| Sign-in | "Pick up the trail" |
| Section icons | Lucide: `Mountain` (projects), `Flag` (milestones), `ListChecks` (my tasks), `Kanban` (board), `Users` (team), `Inbox` (inbox), `Send` (sent to Plane) |

## 6. Chunks

### Chunk 0 · Family source of truth (M)

The blueprint's §2, done in The Lodge (which is in daily use, so back up its data first; the change is code only).

- Create `~/Code/TrailmixFamily` from The Lodge minus `modules/crm` and its identity: `core/`, `mac/`, `scripts/`,
  `modules/tasks`, `modules/notes`, `DESIGN.md`, `ARCHITECTURE.md`. Make it a git repo.
- Move The Lodge's look out of `core/` into `identity/` (blueprint §2.2 table) with an `@identity` alias.
- Promote `format.ts`, `Avatar`/`Empty`/`Tags` and `normalize_tags` to the host (§2.3).
- `scripts/sync-family` in The Lodge copies the shared folders in; `scripts/check` fails when they differ.

**Done when:** The Lodge passes `scripts/check`, looks exactly as before in Day and Dusk, and its `core/` is
identical to `TrailmixFamily/core/`.

**Result (2026-10-18).**
- **Backup first:** "Back up now" through the running Lodge (`lodge-20261019-012146-manual.db`, integrity ok,
  381 records), with a second copy in `~/Documents/The Lodge backups/before-family-chunk0/`. No data was touched.
- **The Lodge's look is in `identity/`** (with an `@identity` alias): `tokens.css` (every color, shadow and the
  atmosphere, Day and Dusk; `core/web/index.css` keeps the type scale, radii, motion and focus ring), `art.tsx`
  (`Logo`, `Scene`, `Ambient`, `Badge`; `core/web/components/illustrations.tsx` now only re-exports them, keeping
  `ContourBadge` as the name modules import), `copy.ts` (sign-in title, Your data wording), `public/favicon.svg`,
  `mac/` (`Mark.swift`, `AppIcon.icns`, `make-icon.swift`; the build copies the mark in) and `DESIGN.md` (the old
  DESIGN.md §17). The window color now reads `--bg` instead of two hard-coded hexes.
- **The host no longer knows about People:** backups are labelled through a new optional `Module.count` (People
  counts its people), and the host's backup tests use stand-in modules and the app's own id. People's backup checks
  moved to `modules/crm/tests/test_backups.py`. The Dockerfile copies `identity/`; `check-app.py` names its temp
  folder after the app.
- **Promoted to the host:** `core/web/format.ts` (`relativeTime`, `formatDate`, `initials`), `Avatar`, `Tags` and
  `Empty` in `core/web/components/blocks.tsx` (People's `bits.tsx` re-exports them, so its screens are unchanged),
  and `core/server/tags.py` (`normalize_tags`).
- **`~/Code/TrailmixFamily`** holds the one copy of the shared code (98 files: `core/`, `mac/`, `tasks`, `notes`,
  the shared scripts, the build setup, `ARCHITECTURE.md`, `DESIGN.md`) plus a README. `scripts/sync-family` pulls
  it into an app, `--push` sends a deliberate change back, and `--check` (now a step of `scripts/check`) fails when
  an app's copy differs. The list of shared paths is at the top of that script. ARCHITECTURE.md has a new rule 9
  and an `identity/` entry in its folder map.
- **Verified:** `scripts/check` passes (202 tests, the 197 from before plus 5 new; types; build; family code the
  same; style rules). Ten pages captured before the change (Home, People, Groups, Inbox, Organizations, Meetings,
  Tasks, Settings, Your data, a profile) have identical markup afterwards in Day and Dusk, apart from the scene's
  minute-by-minute sky, React's generated ids and the overview count the preview's sweep moved on. All 122 theme
  variables have the same computed values in both themes, and the built CSS holds the same 114 token
  declarations with the same values. The Mac app builds and signs with the icon and favicon in place.
- **Pinned versions (asked for 2026-10-18):** each app records the family commit it's built on in `family.lock`
  and moves only when `scripts/sync-family` is run there (`<commit>` picks one). `--check` compares with the pinned
  version, warns instead of failing (`--strict` fails), and says when the family has newer commits. Tried: a
  Lodge-only change warns and fails only with `--strict`; a newer family commit (in a throwaway clone) is reported
  and not applied.
- **Committed:** The Lodge's `family/source-of-truth` at a48764e and 00644eb (pinned to family 84ea14d), and
  TrailmixFamily c3ad509, 6f551ba and 84ea14d.
- **Not done yet:** merging the branch into The Lodge's main (Mark's call). The installed Lodge in /Applications is
  unchanged; nothing about it needs reinstalling, since the change is code-only and looks the same.

### Chunk 1 · Traverse from the family (S)

- `git init` here. The two design guides move to `_reference/` (as The Lodge keeps its).
- Sync the family in (`scripts/sync-family`, which pins its version in `family.lock`), write `app.json` (§5), and `identity/` with the mark, a placeholder scene and The Lodge's
  tokens. Add port 8793 to the port table in `ARCHITECTURE.md`.

**Done when:** Traverse launches on 8793 with an empty sidebar in Day and Dusk, and The Lodge still runs beside it.

**Result (2026-10-18).**
- **Git and GitHub:** Traverse is a git repository with private GitHub repos for it
  (`TheRealEminem/Traverse`) and for the family (`TheRealEminem/TrailmixFamily`); The Lodge's was already private
  and now has the `family/source-of-truth` branch too. The design guides are tracked in `_reference/`.
- **From the family:** `scripts/sync-family` pulled the shared code in and pinned it (`family.lock`, now d2f4765).
  `app.json` as in §5 with `tasks` as its one module so far (the sidebar has Home and Tasks), `VERSION` 0.1.0,
  `package.json` and `package-lock.json` from The Lodge without its network canvas, and a `requirements.txt` of the
  host's four packages. Port 8793 is in ARCHITECTURE.md's table.
- **`identity/`:** The Lodge's tokens, value for value; the mark (the sky tile, a low sun, a trail crossing a slope
  to a cairn); a first scene (a trail across a mountainside toward a saddle, cairns along it, the nearest large;
  Day by day, sunset at Dusk, pointer parallax unless motion is reduced); the route motif for `Ambient`; the dashed
  route badge; "Pick up the trail"; the favicon; the menu bar mark; `AppIcon.icns`, drawn from the favicon by
  `mac/make-icon.swift`; and `identity/DESIGN.md`.
- **Found on the way:** `scripts/dev` used whatever `python3` was first on the PATH, which can be macOS's 3.9; it now
  picks 3.11 or newer (in the family). AppKit's SVG reader ignores `stroke-opacity`, so the mark's faint lines use
  `opacity`.
- **Verified:** `scripts/check` passes (75 tests, types, build, family code the same as d2f4765, style rules). In a
  browser on 8793 while The Lodge ran on 8791: Home with the scene, the Tasks page with the new badge, Day and Dusk.
- **Not done:** the Mac app isn't built yet (chunk 14); the scene is a first version.

### Chunk 2 · Tasks v2 data (M)

Blueprint chunk 2: migration step 2 from `schema/tasks-v2-projects.sql`, adjusted for D7 (five priorities), plus
`notes` on items and the fields §3.2 needs. Store, vocab (`GET /api/tasks/meta`), API (blueprint §9), tests,
including an upgrade test from The Lodge's v1 rows. Made in `TrailmixFamily/modules/tasks`, never in an app.

**Done when:** v1 to-dos survive the upgrade, and the API round-trips projects, milestones, items and updates.

**Result (2026-10-19, family 842c525).**
- **Migration step 2** is the guide's `tasks-v2-projects.sql` with one change: `priority` is 0 none, 1 low, 2 medium,
  3 high, 4 urgent (D7, Plane's scale).
- **The store** is split by job: `store.py` (the migrations and the checks every write uses, each raising a sentence a
  person can read), `items.py`, `projects.py`, `vocab.py` (served at `GET /api/tasks/meta`) and `hooks.py` (contracts,
  describe, search, export, backup count). As the blueprint asks, one function changes status and keeps `done` and
  `completed_at` in step, every write re-indexes search and says `tasks.changed`, and deleting says `item.deleted`
  (for an item's subtasks too) and forgets its links.
- **Decided along the way:**
  - subtasks live wherever their parent does and move with it;
  - a milestone decides its item's project;
  - blockers refuse loops;
  - progress counts top-level items only;
  - assignees and owners are a column and a link, except `core:me`, which has no profile to show it on;
  - deleting a project leaves its items in no project (archiving keeps it whole);
  - links to a task or project open `#/tasks` until chunk 3 adds their pages.
- **Action items** (`actions.found`) now go into the project their source is linked to when there's exactly one, accept
  `{text, due_on, assignee_ref, assignee_name, priority}` as well as plain text, and **replace only the earlier items
  you haven't touched**: anything you edited, ticked, filed or wrote notes on stays (before, every open one was
  replaced). A deleted person or source leaves its name on items and projects and clears the ref.
- **The API** is the blueprint's §9 (without the AI draft, chunk 12), plus blockers and item updates; the current Tasks
  page works unchanged.
- **Verified:** 25 tests in the module (114 in Traverse), including step 1 to step 2 on a database of v1 to-dos (ticked,
  open, from a source), the new tables' constraints and cascades, and every API path and error. Step 2 also ran cleanly
  on a copy of The Lodge's real database (integrity and foreign keys fine), though The Lodge has no to-dos yet.
- **Worth knowing:** the update backup (F1) runs when the app's version changes, so a release that adds a migration
  step should also bump `VERSION`, as every installed update does.

### Chunk 3 · My tasks, quick add, the task page (M)

Blueprint chunk 3 and §8: `TaskRow`, My tasks with Today · This week · Everything · Waiting, the task page.

**Done when:** add, tick, date and open tasks from the keyboard, at 375px and 1440px.

**Result (2026-10-19, family 1584a3a).**
- **My tasks** (`#/tasks?when=today|week|all|waiting`): "mine" means nobody's or yours, still to do or doing. Today
  shows Late and Today; This week adds the next seven days; Everything adds Later, No date and "Not in a project yet"
  (meeting action items, each with Move to…); Waiting on others is anything marked Waiting or given to someone else.
  Tabs carry counts (and short names on a phone). Recently done tasks wait behind Show done.
- **TaskRow and TaskList** for every task list: a round check, the title, a meta line (project, where it came from,
  subtasks done), chips (status, Blocked, Urgent; High as a flag), someone else's avatar, and the due label (late in
  trail, today and tomorrow in sun). ↑ ↓ move across every list on the page, Space ticks, Return opens. A ticked task
  shows done for a moment before it leaves the list (tick again to take it back) and saves when it leaves, or at once
  if you go elsewhere. Rows show nothing for Low and Medium priority, to keep lists calm.
- **Quick add:** Return adds and keeps you in the field; "n" goes to it; the sidebar's **New task** opens it. On Today
  it adds a task due today; on Waiting, one marked Waiting.
- **The task page** (`#/tasks/t/<id>`): editable title, status, project, milestone, assignee (a name for now; the
  PersonPicker arrives with chunk 5), due and start days, priority, estimate ("45", "2h", "1h30"), notes, subtasks,
  "Waiting on" (blockers), comments, where it came from, linked things, and Delete behind a confirm.
- **Sidebar and Home:** My tasks with a count of late and due-today tasks; Home's card is "What's next" this week.
- **API:** `assignee=mine|others`, status lists (`todo,doing`), and `when=waiting` also takes someone else's open
  tasks. Found while building: the API had replaced each task's `source` (its kind) with where it came from; that's
  now `came_from`. Task links from other modules open the task page.
- **Verified:** 26 module tests (115 in Traverse). In a browser with example tasks in the development database: the
  groups and counts; ↓ across lists, Space ticking a task and the save reaching the server, Return opening it; on the
  task page, priority, a subtask and a comment saved from the page; Day and Dusk at 1440px and 375px (where the chips
  drop under the title). Fixed on the way: the title's size on the task page, tabs overflowing on a phone, and the
  tab highlight measuring before the counts arrived.

### Chunk 4 · Projects (M)

Blueprint chunk 4: projects list with health and progress, the project page (overview, list), milestones.

**Done when:** a real Cold Connect project, with milestones and tasks, reads right.

**Result (2026-10-19).**
- **Projects** (`#/tasks/projects?status=…`): Active, Planned, Done, All and Archived. Each row has the project's tile
  (its initial: projects get no colors), name and summary, health, a progress bar with the words beside it, its due
  date (late in trail) and owner. A new project starts from its name and opens straight away.
- **A project** (`#/tasks/projects/<id>?view=overview|list`): an editable name and summary, a meta line (status when
  not Active, health, owner, due), and New task, Archive and Delete. **Overview:** progress with what's doing, waiting
  and late; status, owner, start and due; the brief in Markdown (shown formatted, with an edit button); milestones
  with their own progress and due dates, ticked, renamed or deleted in place; "How it's going": the latest status
  update, a form whose health ("Just a note", On track, At risk, Off track) sets the project's, and earlier updates;
  linked things. **List:** the project's tasks grouped by milestone, each group with its progress, due date and an add
  field, then "No milestone". New task opens the List with its add field ready.
- **Decided:** the project page lives at `#/tasks/projects/<id>` rather than the blueprint's `#/tasks/p/<id>`, so the
  sidebar knows it belongs to Projects; the module now shows as "Projects". Reordering by drag waits for chunk 8.
- **Fixed on the way (shared):** the sidebar lit up every entry the page's address started with (My tasks as well as
  Projects); it now marks only the most specific one.
- **Verified:** 115 tests, types and build. In a browser with example projects: the list in every filter; a project's
  overview and list; ticking a milestone, posting an "At risk" update (the project's health followed), and New task
  focusing the add field; Day and Dusk at 1440px and 375px.
- **For The Lodge:** taking this family version adds Projects to its sidebar too. A setting to hide projects in an app
  that doesn't want them (the blueprint's `tasks.projects`) belongs with chunk 13's settings.
- **Not done:** the "real Cold Connect project" part of done-when needs Plane (chunks 5 and 6), which brings real
  projects in; until then it was checked with example projects.

### Chunk 5 · Plane connection, mirror, Team view, people (M–L)

- `plane` module: settings (API key as a secret, workspace slug, base URL preset to Plane Cloud), a connection
  test, and which Plane projects to mirror.
- A small Plane client (`modules/plane/server/client.py`) over Plane's REST API with read methods only in this
  chunk. Rate limits and paging handled.
- `plane/pull` recurring job into `plane_projects`, `plane_states`, `plane_members`, `plane_labels`, `plane_items`.
- **Team view** (`#/plane/team`): open items by person, state and project, past-due and unassigned, each item
  opening in Plane.
- The host's people directory (blueprint §6): `Module.people`, `core/server/people.py`, `GET /api/people`,
  `PersonPicker`, with `plane` as a provider and `core:me` matched to Mark's Plane member by email.

**Done when:** Team view matches Plane: on 2026-10-18 that was 34 open items, Mark 23, Mickey 5, Elijah 2, 4 with no
one. Assigning a task offers Elijah and Mickey from Plane.

**Result (2026-10-19, branch `claude/chunk-5-plane-mirror-ebcfba`, not yet live-checked).**
- **`modules/plane`:** settings (`plane.personal_api_key`, write-only; plain `api_key` wouldn't be a secret to the
  host, which only hides names ending in `_api_key`), workspace slug, base URL (Plane Cloud), projects to mirror,
  `plane.me`, pull interval; `POST /api/plane/test`; a GET-only client (paging, 429/5xx backoff, readable errors);
  `plane/pull` writing a whole snapshot in one transaction, touching only changed rows (gone items get `removed_at`).
- **Team view** `#/plane/team` (wide): totals, per-person cards with a state split, by state, by project, and a
  searchable item table filtered by person, project, past due and no one (filters in the hash); items open in Plane.
- **People directory:** `Module.people`, `core/server/people.py` (merges modules and `family.call("people.search")`,
  you first as `core:me`, same email shown once, a note when the other app is closed), `GET /api/people`,
  `PersonPicker` in blocks.tsx. Plane members are `plane:<id>`; the key's owner (or `plane.me`) is `core:me`.
- **Verified:** 169 tests with `TRAVERSE_MODULES=tasks,plane` (fixtures rebuild the 2026-10-18 workspace: 34 open,
  Mark 23, Mickey 5, Elijah 2, no one 4). Team view looked at in Day and Dusk at 1440 and 375.
- **Not done:** the live check (Mark pastes his key in Settings → Plane, tests, mirrors the 7 real projects and
  compares the counts and that `/browse/KEY-N/` links open); `app.json` still lacks `plane` (run with
  `TRAVERSE_MODULES=tasks,plane`). Settings → Plane and PersonPicker were tried in a browser (You first, Elijah and
  Mickey from Plane, "Use “ana” as a name" giving ref null, keyboard choice giving `plane:<id>`), but no screen
  uses PersonPicker yet: chunk 3's task page is where assignees will pick with it.

### Chunk 6 · Linking (M)

- Link a Traverse project to a Plane project, with the state mapping (§3.2) chosen per project.
- "Bring into Traverse" on Plane items, singly or by filter ("everything assigned to me").
- Linked tasks follow Plane for untouched fields; "Changed in Plane" and "Removed in Plane" on the rest.

**Done when:** Mark's 23 Plane items are in Traverse as linked tasks, and editing one in Plane updates its local
copy within a pull.

**Result (2026-10-20, branch `chunk-6/linking`).**
- **Contracts** (`core/server/contracts.py`, shared): `work.project_arrived`, `work.arrived`, `work.updated_elsewhere`,
  `work.removed_elsewhere`, and `WORK_FIELDS` (text, notes, status, priority, start_on, due_on, assignee_ref,
  assignee_name). `core/server/links.py` gains `targets()` and `pairs()`.
- **`tasks`** (shared): migration step 3, `tasks_synced` (base, conflicts, removed_at); `synced.py` handles the
  contracts. Per field group: unchanged there → nothing; changed only there → the task takes it; same change both
  sides → agreed; different changes → kept yours, flagged with theirs. "Use Plane's" sets yours to theirs; "Keep
  mine" makes theirs the base, so yours is a change of your own (chunk 7 sends it). Removed there → marked, never
  deleted. Unlink keeps the task. The API adds `synced` to items and `synced_with` to projects; `POST/DELETE
  /api/tasks/{id}/synced`. New item source `linked`. Screens: a "Linked to Plane" panel on the task page with the
  "Changed in Plane" and "Removed in Plane" states, chips on task rows, "Linked to Plane: …" on the project page.
- **`plane`**: migration step 2, `plane_links`; `linking.py` (state map preset per §3.2: To do → the project's default
  state if it's unstarted, else the first unstarted; Doing → first started; Waiting → a started state named like
  wait/block/hold/review, else Doing's; Done, Dropped → first completed, cancelled. A state reads as the status mapped
  to it, else its group's). `html.py` turns description_html into Markdown. After a pull that changed anything, every
  linked item is published again (tasks ignores what didn't change). API: `GET /api/plane/links`, `POST/PATCH/DELETE
  /api/plane/links/{project}`, `POST /api/plane/bring` (`{items}` or `{mine: true}`). Screens: **Linking**
  (`#/plane/links`): bring in everything assigned to you, and per project link (new or existing), unlink, the state
  map, bring in yours or all; the Team view's items get "Bring in" / "In Traverse" and "Bring these N into Traverse"
  for whatever the filters show. Bringing in from an unlinked project makes its Traverse project first (said in the
  confirm).
- **Verified:** 218 tests (19 new: contracts in isolation, and the whole path against the fake Plane, including a
  Plane edit followed after a pull, a conflict, a removal and its return, the state map, and only GETs reaching Plane).
  Live on 2026-10-20 (backup first): "Bring in your 23" made Business Development 9, Infrastructure 4, Hardware 3,
  Operations 3, Marketing 2, Customer Relationships 1, Software 1, all `core:me`, 12 Doing and 11 To do, matching the
  Team view; a live pull afterwards: 31 GETs, nothing changed, no flags. The "Changed in Plane" panel, Keep mine and
  Unlink were tried on a test link to an example task, then removed. **Not yet tried:** an actual edit in Plane
  followed by a pull (Traverse doesn't write to Plane, so that edit is Mark's).
- Later: following a Plane item moved to another linked project; Plane's other assignees beyond the one shown
  (chunk 7 merges lists); comments.

### Chunk 7 · Push to Plane (L)

The heart of D3, built test-first against a fake Plane:

- "Send to Plane" on a task, a selection, or a project ("Send 4 changes"). Each publishes `work.share_requested`.
- The push job: work out the changed fields against the base, re-read the item, stop on conflict, merge lists,
  then write. New items are created in the linked project. Traverse updates can be posted as comments.
- The review screen (`#/plane/outbox`): every waiting push with its field-by-field preview, Send and Discard, and
  conflicts with keep-Plane's / send-mine / edit.
- `plane_pushes` log and Undo. The dry-run setting.
- Tests for every rule in §3.3, including: a teammate's edit to another field survives; a teammate's edit to the
  same field stops the push; an assignee added in Plane survives a push that adds another; the client has no delete.

**Done when:** an item created and edited in Traverse appears in Plane after Mark approves it, and in a sandbox
Plane project (the "Cold Connect" demo project, if Mark agrees) a change made in Plane between pull and push is
never overwritten.

**Result (2026-10-20, branch `chunk-7/push` from `chunk-6/linking`; the shared files are changed here, not sent to the
family yet).**
- **Contracts** (shared): `work.share_requested` as in §3.5; `work.arrived` gains `local_ref`, `work.updated_elsewhere`
  gains `take`; `links.targets_of()` for list pages. **`tasks`** (shared): `synced.share()` and `POST /api/tasks/{id}/share`,
  and items carry `sharing` (where their changes wait). The task page's Linked panel has "Send it (these N) to Plane",
  then "Waiting for you to send it… Review and send"; a task in a linked project that isn't in Plane yet says "Only in
  Traverse so far" with "Send to Plane". Task rows and board cards show "N changes to send" or "Waiting to send".
- **`plane`**, migration step 3: `plane_pushes` (the outbox and the log: each field's Traverse and Plane values before
  and after, when you approved it, when it was sent) and `plane_sent` (what a Plane value means in Traverse after a
  push, for as long as Plane keeps it: a state sent as Waiting reads back as Waiting, not Doing; a merged assignee list
  as Mickey; notes through HTML. Forgotten once Plane changes it). `push.py`: a request becomes a push with one entry
  per field (status through the project's state map; notes as HTML by `html.to_html`, the inverse of chunk 6's
  `to_markdown`, left out until you include them, per §7; assignees as an addition and a removal; someone not in Plane
  or a status with no state shows why and can't be sent). Its job is parked as Needs you. Send reads the item again;
  any field Plane changed since stops it with both values: **Keep Plane's** (the task takes it), **Send mine instead**,
  or edit the task. Otherwise one PATCH of only those fields, assignees as Plane's list now plus yours minus the one
  you replaced; then it reads the item back, logs it, updates the mirror and the task's base. A new item is a POST into
  the linked project, and the task becomes its linked copy; a POST whose answer was lost is found again, not made twice.
  **Undo** is a new push of the "before" values with the same preview and check; a new item can't be undone (that would
  be a delete). **Dry run** (`plane.dry_run`) is **on by default**, and anything but an explicit off counts as on: Send
  reads and checks, says what it would write, writes nothing, and the push stays waiting. An item's mirror row only
  moves forward in Plane's time, so a pull read before a push can't put the old values back. Pushes run one at a time.
- **Client**: `work_item` (GET one), `update_work_item` (PATCH, only the fields in `WRITABLE`), `create_work_item`
  (POST). Writes go through `_send`, which refuses anything but PATCH or POST; a PATCH is retried after Plane's own
  errors and timeouts, a POST never is. `test_the_client_has_no_way_to_delete` checks the source: no DELETE or PUT, no
  method named like deleting, `.post`/`.patch` only inside `_send`, reached only from the two writing methods.
- **Screens**: the **Outbox** (`#/plane/outbox`, in the sidebar with a count): Waiting and Sent, a Dry run banner, and
  per push the task, the Plane item (or the project a new one goes into) and each field with a switch, "In Plane now"
  and "Will be", plus why notes are left out, "Plane has this already" and "Plane has changed this since you asked".
  A stopped push shows what you last saw, Plane now and yours. Sent shows before → after, "sent over a change in Plane,
  as you chose", when you approved it, and Undo. Settings → Plane has the Dry run switch, and no longer says Traverse
  only reads.
- **Verified**: `scripts/check` passes: 252 tests, among them 23 push tests covering every rule in §3.3 end to end
  against the fake Plane (which now takes PATCH and POST, records every write and refuses DELETE and PUT), 7 new client
  tests and 5 contract tests in tasks; types; build; style. (In a shell where `ANTHROPIC_API_KEY` is set, one inbox
  test fails because the AI label then includes a model; it passes without it, and isn't touched here.)
  On dev data in a browser (a backup first, `traverse-20261020-181450-manual.db`, and a copy from before the
  migration): a priority change on OPERATIONS-10, "Send it to Plane", the Outbox, Check (dry run). Traverse read the
  item from Cold Connect's Plane (one GET, so the live single-item read works) and found Plane had High already (the
  copy was from the morning): "Send would write nothing". Discarded. Only GETs reached Plane.
  In a sandbox (a throwaway data folder and the fake Plane over HTTP): a teammate's new due date stopped a push, then
  Send mine instead sent it; Elijah, added in Plane meanwhile, stayed when the assignee went from Mark to Mickey; Undo
  put both fields back; a new task in Software was added (one POST) and became its linked copy; Day and Dusk, 375px
  and wide. Found and fixed (with a test): Undo of a push sent over a teammate's change put the task back to its old
  base instead of Plane's value.
- **Not done**: the live half of done-when needs Mark: turn dry run off and approve one push (say, a new item in the
  "Cold Connect" demo project, §8). Descriptions haven't been written to the real Plane (it may keep its editor's own
  copy of a description; they're left out of a push until included). Posting Traverse updates as comments, sending a
  selection or a project's "Send N changes", and milestones in Plane (§8) aren't built. The shared files go to the
  family with `scripts/sync-family --push` when Mark says.

### Chunk 8 · Board view and drag (M)

Blueprint chunk 5. Dragging between columns changes status locally; for linked tasks, that change waits to be sent.

**Done when:** drag between columns updates status, the order sticks, and linked tasks show "1 change to send".

**Result (2026-10-19, family bf6d30a).**
- **The board** (`#/tasks/projects/<id>/board`, its own address so it can use the full width): To do, Doing, Waiting
  and Done, each headed by its name and count, on `inset-surface`. Cards (`rounded-lg bg-surface border shadow-sm`)
  show the title, milestone, Blocked/Urgent/High, subtasks, the due label and someone else's avatar; they lift 1px on
  hover and fade while dragged, and a forest line shows where a card will land. Dropped tasks stay off the board; the
  List view keeps them.
- **Moving:** a card dropped in another column changes status and place in one request (`move` takes `within:
  "project"`, which orders across milestones, and a `status`). The project's **List view** follows your order now
  (open first, done last): drag a task to reorder it, or into another milestone's group to move it there; an empty
  group takes a drop and says so while you drag.
- **Keyboard:** on the board, arrows move between cards, Alt + ← → moves a card to the next column, Alt + ↑ ↓ up or
  down; in lists, Alt + ↑ ↓ moves a task. Focus stays on what you moved.
- **Verified:** a module test (a card dropped after another milestone's card keeps its milestone and takes the
  column's status; 116 tests in all). In a browser on example tasks: dragging a card into the empty Waiting column
  ("Drop here" while over it); Alt + → then Alt + ↑ on a card (status and order changed, focus kept); the order after
  a reload; dragging a task into another milestone's group in the List view; Alt + ↑ there. The drags were made with
  the browser's own drag events from a script, since an automated pointer can't start a native drag.
- **Not yet:** "linked tasks show 1 change to send" needs Plane links (chunk 7). Native drag doesn't work with touch
  in WebKit, so on a phone-sized window the board moves only by keyboard, or from the task page's status.

### Chunk 9 · Inbox (L)

- `inbox` module: paste text, drop a file, or (chunk 11) capture from Claude. Each capture is a row in
  `inbox_captures` with its source.
- An `inbox/extract` job (`ai.structured`) proposes work items: text, assignee (from the people directory), due
  date, project, priority, and the sentence it came from.
- The review screen: accept, edit or drop each proposal. Accepted ones publish `actions.found` with `details`, and
  `tasks` files them into the project.

**Done when:** a pasted Slack thread becomes three proposed tasks with the right people, and accepting them files
them into the right project.

**Result (2026-10-19).**
- **`modules/inbox`** (Traverse's own module): `inbox_captures` (source paste, file, claude or trailmix; title, raw
  text, status new → review → done, where it came from), `inbox_proposals` (text, assignee name, due day, priority on
  Plane's 0–4 scale, the sentence it came from; proposed, accepted or dropped) and `inbox_imports` (each Trailmix
  meeting seen, by uid). Random text ids throughout.
- **Capture:** paste, or a .txt, .md or .eml file (the page reads the file and sends its text, so no upload
  dependency). An email keeps its From, To, Cc and Date lines, and its date is the day "Friday" is read from.
  Over 60,000 characters is refused with a sentence saying why.
- **The `inbox/extract` job** (never in a request) calls `ai.structured` with a small schema and shows which AI wrote
  the proposals ("Proposed by Ollama · qwen2.5:7b"). Reading again replaces only proposals still waiting.
- **Review** (`#/inbox/<id>`): accept, edit (who, due, priority) or drop each one, Accept all, and bring a dropped one
  back. Accepting publishes `actions.found` with `source_ref` `inbox:<id>` and the items as dicts. Each announcement
  carries everything accepted from the capture so far (tasks replaces a source's untouched items), except items
  you've since deleted in Tasks, which would otherwise come back. Your own name becomes `core:me`.
- **Projects:** the picker finds them through `GET /api/search` (the tasks module marks project hits with the
  snippet "Project"; if that changes, `inbox/web/api.ts` follows it), and choosing one adds
  `inbox:<id> → tasks:<project id>` (kind `about`), so tasks files the items there. No call to the tasks API, no
  read of its tables.
- Also: a Home card, the sidebar's Inbox with a count of captures waiting for review, search, describe, export, a
  backup count and an empty state.
- **Small local models, learned on qwen2.5:7b:** counting from a date put "next Tuesday" on the wrong day, so the
  prompt carries a table of when-words with their dates ("next Tuesday = 2026-10-27"), and the model copies the
  words (`when_said`, `urgency_said`) before the values it reads from them. A due day or a priority stands only when
  those words are really in the text (it made up the meeting's own day as a due date, and priorities from nothing).
  Naming the reader in the prompt pulled every "I" in a chat towards them, so it's only said for meetings.
- **Verified:** 21 tests with the fake AI (`fake_structured`), including the done-when: a pasted Slack thread
  becomes three proposals with Elijah, Mickey and Mark and their days, and accepting them files them into the chosen
  project. A real run on Ollama (qwen2.5:7b) through the screen: the right three people, Friday 23, tomorrow (Tue
  20) and next Tuesday (27); picking "Acme launch" and Accept all filed all three there, with Mark's as `core:me`.
  Left over: "urgent" in Mark's message also landed on Elijah's item (priority is editable before accepting).
  Screens checked in Day and Dusk at 375px and 1440px.
- **Not yet:** `app.json` doesn't list `inbox`, so a plain `scripts/check` skips its tests; run it with
  `TRAVERSE_MODULES=tasks,inbox` (140 pass) until `inbox` is added. Assignees are names until the people directory
  (chunk 5). F6 (AI cost) isn't in yet, so a cloud provider's extractions aren't priced.

### Chunk 10 · Meetings from Trailmix (S–M)

A recurring job reads summarized meetings from Trailmix's API and drops their action items into the inbox, linked
to the meeting. Off when Trailmix isn't running or the setting is off. (If the apps ever combine, The Lodge already imports
meetings, so this switches off there; see §7.)

**Done when:** yesterday's recorded meeting's action items wait in the inbox, each saying which meeting it came from.

**Result (2026-10-19).**
- **The `inbox/trailmix` job**, every five minutes while Settings → Inbox → "Meetings from Trailmix" is on (off by
  default, and paused while off). It reads `GET /api/meetings`, then `GET /api/meetings/{id}` for each finished meeting
  from the last two weeks (the list has no uid), and skips any uid it has seen, even when its capture was deleted or
  Trailmix's ids change. Each meeting's open action items (ticked ones are done) become one capture, titled with
  the meeting, dated by it (so "Friday" means the Friday after the meeting), with "Open in Trailmix", and read like
  any other capture. The capture also links to `meetings:<uid>`, for a meetings module later (ARCHITECTURE.md §13).
- Only GETs; Trailmix and its repository are untouched. When Trailmix isn't running nothing happens, and Settings
  says so ("Trailmix isn't running"), with Check now. A Trailmix that asks for a sign-in is reported, not tried.
- **Verified:** 5 tests against a fake Trailmix (an httpx mock transport that fails any request that isn't a GET).
  Live and read-only on this Mac: Trailmix had 124 meetings, 13 finished in the last two weeks; the 6 with open
  action items came in as captures (and a seventh, recorded that morning, came in on its own a few minutes later),
  each saying its meeting and date, and Ollama read them into proposals. This was a development copy with its own
  data; Mark's real Traverse data wasn't touched.

### Chunk 11 · MCP server (M)

- `core/server/mcp.py` in `TrailmixFamily`: streamable HTTP at `/mcp`, a local token from Settings, and an optional
  `Module.tools` field.
- Tools from `tasks` (my work, find, add), `plane` (team workload, propose a push) and `inbox` (capture).
- Settings shows the one-line command for Claude Code and the config for Claude Desktop, with Copy.

**Done when:** Claude Code, asked "what's on my plate this week and file the follow-ups from this thread", answers
from Traverse and leaves proposals in the inbox, and anything for Plane waits for approval.

**Result (2026-10-20, branch `chunk-11/mcp` from `chunk-7/push`; the shared files are changed here, not sent to the
family yet).**
- **The host** (shared): `core/server/mcp.py`, MCP's streamable HTTP at `POST /mcp` in its plainest form: each POST is
  one JSON-RPC message (or a batch) answered as JSON, with no sessions and no stream from the server (GET and DELETE
  are 405); protocol versions 2025-11-25 back to 2024-11-05. It answers `initialize` (with instructions: whose app it
  is, today's date, where an `href` opens), `ping`, `tools/list` and `tools/call`. **`Module.tools`** is a list of
  `mcp.Tool` (name, title, description, JSON Schema params, handler, `writes`); Claude sees `<module>_<name>`. Arguments
  are checked against the schema before the handler runs; a handler's `ValueError` comes back as its own sentence
  (`isError`), anything else as "Something went wrong in X" with the details in the log; each call is logged as
  "Claude used …". No new dependency (the `mcp` package would bring a dozen).
- **Who may ask:** off until Settings → Claude makes a token (`core.mcp_token`, 32 random bytes, a write-only secret:
  the page gets it once, inside the command and the config to copy, then only its last four characters). The Bearer
  token is compared in constant time, with half a second's wait after a wrong one; a request whose Origin isn't this
  Mac (a web page) is refused even with the token. `/mcp` is outside the app's sign-in, `/api/mcp` (Settings) behind
  it. A new token stops the old one; Turn off stops both.
- **Tools can't approve, so nothing reaches Plane from Claude:** while a tool runs (`mcp.calling()`), `jobs.go` and
  `jobs.retry` raise `PermissionError` (in the host, for every module's "Needs you"), `push.approve` refuses ("Claude
  can't send to Plane. Only you can, with Send in the outbox.") and the Plane client won't write. A proposed push
  parks as Needs you like one from the task page, and dry run stays whatever it was: no tool changes settings.
- **Claude Desktop** runs servers as commands, so `core/server/mcp_bridge.py` (standard library only) passes its
  stdin lines to `/mcp` and writes the answers back, and says "The app isn't running" when it isn't. Settings gives the
  config with this app's own Python (inside the Mac app: the bundled one) and `-B`, so nothing is written in the
  bundle. No npx or mcp-remote.
- **Tools.** `tasks` (shared): `tasks_my_plate` (yours or nobody's, open, grouped Late, Today, This week, Later and No
  date; `when` week, today, late, all or waiting; counts; a linked task says where and which changes aren't sent),
  `tasks_find` (words, a project by name or ref, or both; projects with progress), `tasks_add` (a project by name, "me"
  or a person from the people directory, priority by name; source `ai`), `tasks_propose_send` (the task page's "Send
  to Plane": `synced.share`, so it waits in the outbox). `plane`: `plane_team_workload` (from the mirror only: totals,
  each person and project, and the items of a person, "me", "no one", a project, or else the past-due ones),
  `plane_outbox` (what waits, field by field, and whether dry run is on; read only). `inbox`: `inbox_capture` (source
  "claude"; with Claude's own items they're proposals "Proposed by Claude", checked like an edit on the review screen;
  without them the app's AI reads it as it does a paste; a project ref files what's accepted).
- **Decided:** proposing a push is `tasks_propose_send`, not a plane tool. What changed since the base is tasks'
  knowledge, and plane could only ask tasks for it through a new contract that answers back, which events don't. The
  plane module's part is the outbox, and refusing to send from a tool. tasks' tool texts say "a team's tracker", not
  Plane (D5), so The Lodge gets the same tools. Claude reads the thread itself and brings its own proposals, rather
  than Traverse calling a second AI.
- **Settings → Claude** (host, after AI): off, "Let Claude use Traverse" and Turn on. Just turned on: the Claude Code
  command (`claude mcp add --scope user --transport http traverse http://127.0.0.1:<port>/mcp --header
  "Authorization: Bearer …"`) and the Claude Desktop JSON, each with Copy and "Copy it now: the token in it isn't shown
  again". Then "On, with the token ending …", Make a new token and Turn off (each asks first), and what Claude can do.
- **Verified:** `scripts/check` passes: 290 tests, 38 new. 17 for the host: the protocol, versions, batches, argument
  checks, the token, web pages refused, Settings showing the token once, the bridge (through a stand-in, and as a real
  process with the app down), and a tool that can't start waiting work. 5 for tasks' tools; 11 for the inbox's. 5 for
  plane's, among them **no tool can write to Plane**: every tool, called through `/mcp` with dry run *off*, including
  proposing an edit and a new item, and neither a write nor even a read reached the fake Plane; both pushes wait
  unapproved, and your Send in the app then writes one PATCH. Inside a tool, Send and the client both refuse, and the
  tools' own code never names a way to send, approve or change a setting. Types, build and style also pass.
  On the dev server (8795, `data/traverse.db`, backup `traverse-20261021-003340-manual.db` first; dry run on
  throughout): the Settings command, run as is against a throwaway Claude config, gave `✔ Connected`. Claude Desktop's
  config, run with an empty environment over stdin, answered `initialize` and `tools/list`. Claude Code (Opus 5.5, with
  only Traverse's server) was asked "What's on my plate this week? And file the follow-ups from this thread" with a
  #hardware Slack thread. It used `tasks_my_plate`, `tasks_find` twice and `inbox_capture`, and answered in 19 s: 4
  late (OPERATIONS-10 and BD-14 with their Plane links, and two of the dev data's example tasks) and 1 this week
  (another example; it said the three looked like sample data). It
  left 4 proposals in the inbox, filed to Hardware: Elijah's drop tests Thursday, your BOM update tomorrow, Mickey's
  quote Friday, and "Add the drop test plan to Plane" with no one, which it said nobody had agreed to. It didn't
  propose sending anything, since proposals aren't tasks yet. Asked next to add the drop test plan to Hardware and send
  it to Plane, it called `tasks_add` and `tasks_propose_send` and said it waits for your Send. It waits in the Outbox as
  a new item in Hardware, unapproved. Only GETs (the mirror's pulls) reached Plane all session. Settings → Claude was
  checked in Dusk at 1280px and 375px.
- **Left in the dev data** for you to look at: that capture (4 proposals) and the waiting push. Discard or accept them
  as you like. Claude's access is off again in the dev app.
- **Not done:** Claude Desktop itself wasn't run (its config was run the way Desktop runs it). Your own Claude Code and
  the installed app aren't set up yet: that's Settings → Claude in the installed app once it's rebuilt with this. A
  server install's commands still say 127.0.0.1. The shared files (`core/`, `modules/tasks/`, ARCHITECTURE.md) go to
  the family with `scripts/sync-family --push` when you say.

### Chunk 12 · AI in the app (M)

Blueprint chunk 8: status drafts per project (and, on approval, posted to Plane as a comment), break a task down.

**Done when:** a draft appears, says who wrote it, and can be edited, discarded or sent.

**Result (2026-10-21, branch `claude/chunk-12-ai-c80a35` from `chunk-11/mcp`; the shared files are changed here, not
sent to the family yet).**
- **Plane first:** its API (v1 and v2, developers.plane.so) has no project-level updates or status. What it has is
  comments on work items: `POST …/work-items/{id}/comments/` with `comment_html`, and `external_source`/`external_id`
  for an id of the caller's own. So a project's status goes to Plane as a comment on one of its linked tasks, which you
  choose.
- **Contracts** (shared): `work.comment_requested` (§3.5). It says nothing about Plane.
- **`tasks`** (shared), migration step 4: `tasks_drafts` (one per project for its status, one per task for its
  breakdown: body, suggested health and why, proposed subtasks as JSON, `written_by`, `edited`) and
  `tasks_updates.edited`. `drafts.py`: the `tasks/draft` job (lane "interactive", or "default" when the AI runs on this
  Mac) calls `ai.structured`. A status draft reads the project as plain facts: progress, each milestone (missed or
  not), what got done and added since the last status update (or the last two weeks), late, in progress, due in two
  weeks, flags (blocked by what, waiting on whom, removed or changed elsewhere) and the last three updates. It asks for
  the body first, then why, then the health (`StatusDraft`); a health it can't read is left empty. `tidy_body` drops a
  label with only "Nothing" under it and a "Health:" line (both seen from qwen2.5:7b). A breakdown asks for 2 to 8
  steps with minutes (`Breakdown`), drops ones the task already has, and rounds estimates (5 under an hour, 15 under a
  day). Drafting again replaces a draft; a breakdown keeps what you accepted or dropped. Posting makes it the project's
  status update (`author_ref` core:me, `written_by` the AI, `edited`), and its health the project's. Accepted steps are
  subtasks with source `ai` and `attributes.written_by`. `synced.comment()` publishes the contract, for a task's own
  comment or a project update on one of its linked tasks (checked before anything is posted), and refuses one that's
  there already; updates carry `shared` (waiting or posted, named by the other module). API: `GET/POST
  /api/tasks/projects/{id}/draft`, `GET/POST /api/tasks/{id}/breakdown`, `PATCH/DELETE /api/tasks/drafts/{id}`,
  `POST /api/tasks/drafts/{id}/post` (`share_on`), `PATCH /api/tasks/drafts/{id}/proposals/{pid}`, `POST
  /api/tasks/drafts/{id}/accept`, `POST /api/tasks/updates/{id}/share` (`item_id`).
- **`plane`**, migration step 4: `plane_pushes.update_ref`. A comment is a push of kind `comment`, parked as Needs you,
  its preview the words as Plane will show them, ending "*Drafted by Ollama · qwen2.5:7b*" when an AI drafted it.
  Asking again while it waits replaces the words. Send reads the item again (gone: it fails and says so), then one
  POST; dry run says "Send would add this comment to OPERATIONS-10" and writes nothing. A POST whose answer was lost is
  found again by Traverse's id (or the same words by you since the attempt), not added twice. No Undo, no edit: a
  comment stays as it is. **Client:** `comments()` (GET) and `create_comment()` (POST through `_send`, only
  `comment_html`, `external_source`, `external_id`); the no-delete test now also checks the only comment methods are
  reading and adding. Tools may not name `create_comment`.
- **Screens.** Project page, How it's going: "Draft a status", then the draft with "Drafted by Ollama · qwen2.5:7b"
  (", edited by you" once changed), the health it suggests and why, the text to edit, and "Only here" or "In Plane
  too, on <a linked task>", Discard, "Post update" or "Post, and offer to Plane". Posted updates say "Drafted by …,
  edited and posted by you", and "Waiting for you to send it to Plane · Review" or "Posted in Plane"; one not offered
  yet has "Post in Plane too, on…". Task page: "Break it down" by Subtasks, each proposal with its estimate, Accept,
  Edit, Drop, Accept all, Bring back; a subtask made from one says "Proposed by …". A linked task's comments have
  "Post in Plane too". Outbox: "Comment on <task> to <key>", the comment rendered, "Add the comment", and no Undo.
- **Verified:** `scripts/check` passes (309 tests, 19 new; types, build, style; the family-drift warning is expected):
  11 tasks tests with the fake AI (the prompt's facts, edit, discard, post with health and who wrote it, a failed draft and Try
  again, the breakdown end to end, the contract with a stand-in taker) and 7 new plane tests against the fake Plane (a
  comment waits, then one POST and nothing else; a status draft offered on a linked task; dry run; asking again;
  discard; a lost answer not doubled; an item gone; a deleted task; Claude can't send one), and one for the client. Live on
  this worktree's own copy of the dev data (dry run on; port 8799, since another session's Trailmix preflight had
  8797): two AI calls, both to Ollama qwen2.5:7b on this Mac, Settings' provider. "Draft a status" on Operations: At
  risk, "The late submission of OAIX Week 2 Deliverables…", with an empty Done section and the health repeated in the
  body (now tidied, tested on that text). Edited it, posted it with "In Plane too, on OAIX Week 2 Deliverables": the
  project went At risk, and the comment waits in the Outbox, unsent. "Break it down" on that task: six steps, 30 to 60
  minutes each; edited one (20 min), dropped one, accepted one. Only GETs reached Plane, and Send was never pressed.
  Checked at 375px and 1280px by measuring the page (this session wasn't on screen, so no screenshots): nothing wider
  than the screen, and the draft's controls on one row at 1280px.
- **Not done:** no comment has reached the real Plane; that's Mark's to send with dry run off, and it would be the
  first live use of the comments endpoint (whether Plane's comment list returns `external_id` is unconfirmed; the
  lost-answer check falls back to the same words by you). Plane's comments aren't shown on linked tasks yet (§3.1's
  other direction). A project update deleted with its project leaves a waiting comment in the outbox (its words are in
  the push). Claude has no tool to draft a status. The shared files (`core/server/contracts.py`, `modules/tasks/`) go
  to the family with `scripts/sync-family --push` when Mark says; `tasks` migration step 4 must reach the family
  before The Lodge takes this `tasks`.

### Chunk 13 · Home, search, export, Settings, auto-sync (M)

- Home: "What's next" and "Waiting to send". ⌘K across tasks, projects, Plane items and the inbox. Export includes
  every module.
- **Auto-sync** per linked project, off by default: sends changes to items you created in Traverse without asking,
  never deletes, and still parks any conflict for you.

**Done when:** with auto-sync on in the sandbox project, a local edit reaches Plane within a minute, and a
conflicting edit still waits.

### Chunk 14 · Mac (M)

Mark, `Mark.swift`, icon, build and install. **Done when:** Traverse.app installs beside The Lodge and both run.

## 6b. Family track

Shared host work, made in Traverse, sent to `TrailmixFamily` with `scripts/sync-family --push`, committed there, and
pinned in Traverse. The Lodge gets each one when Mark runs `scripts/sync-family` in it. The adoptions come from
`TRAILMIX-COMPARISON.md` §4, in its order.

### F1 · A backup before an update migrates the database (S)

Trailmix backs up once on the first start of each new version (`backup` before `migrate`). The family host backs up
daily, so an update could migrate the database with no fresh copy. On startup, before any migration, the host
compares `VERSION` with the version that last opened the database; when they differ, it makes a backup of kind
"before-update" (three kept), then records the new version.

**Done when:** starting a new version leaves a "Kept before an update" backup in Settings → Your data, starting the
same version again doesn't, and a fresh install makes none.

**Result (2026-10-18, family 5166181).** `backup.before_update()` runs first in the host's startup and
`backup.record_version()` after the migrations, keeping the version in an undeclared `core.opened_by_version`
setting. A failed backup is logged and never stops the app. Four tests (a new version once, a database with no
recorded version once, a fresh install never, three kept). On Traverse's preview database, which predated it,
the first restart made exactly one.

### F2 · Gemini's default model (S)

`ai.gemini_model` defaults to `gemini-flash-latest`, as in Trailmix. A model someone chose stays as it is.

**Result (2026-10-18, family 5166181).** Done, with its test updated.

### F3 · Family link: apps on one Mac share keys, preferences and data (M–L)

Mark wants every family app installed on his Mac to share API keys, basic preferences and data, and to stay
flexible and compatible later. The design uses two mechanisms, because keys and data behave differently:

**Keys and preferences: a shared file, readable while any one app is closed.**
- A family folder, `~/Library/Application Support/Trailmix Family/` (private to the user: 0700 folder, 0600 file),
  holds `family.db`, one small SQLite database that every family app on the Mac opens directly (WAL, so several can
  write).
- A fixed list of shared settings, in the host: the AI settings (`ai.*`: provider, fallback, models, keys, the Ollama
  address), `core.your_name`, `core.appearance` (Day, Dusk or System; today it's kept in the browser, so it moves to
  a setting, with the browser copy kept for the first paint) and, with F5, `core.lockdown`.
- Reading a shared setting gives the family's value; saving one writes it to the family and keeps a local copy, so
  backups, restores and a merged app still have everything. Keys stay write-only, as now.
- Settings has "Share keys and preferences with your other family apps", on by default. Off: this app keeps its own.
- A change in one app reaches the others' open screens within a few seconds (a change counter in `family.db`,
  checked the way `useLive` already polls).

**Data: live calls between running apps, on localhost only.**
- Each app writes its row in `family_apps` at startup and every minute: id, name, version, port and its **offers**,
  the questions it can answer for other apps (People: `people.search`, `people.get`; Traverse: `tasks.mine`,
  `tasks.create`, `projects.list`). `GET /api/family` lists the installed apps and which are running.
- A module declares offers in a new optional `Module.offers` field. A module in another app asks with
  `family.call("people.search", q="ana")`, which finds a running app that offers it and calls its
  `/api/family/call/<offer>`. When none is running it says so ("Open The Lodge to see your people"), and the
  screen still works.
- Calls carry a family token kept in `family.db`. Without it the endpoint refuses, so a web page in a browser can't
  reach an app's data through localhost.
- Data stays where it lives: no app copies another's tables. In a merged app, `family.call` answers from its own
  modules first, so the same code works in both shapes.
- Server installs (Docker) don't join unless `TRAILMIX_FAMILY_DIR` is set. Nothing leaves the Mac.

**Why not one or the other.** Live API calls alone would lose keys and preferences whenever the other app isn't
running; a shared file alone would mean one app reading another's tables, which breaks the family's main rule.
Splitting them keeps each app the owner of its data and still shares what's truly common.

**Done when:** a key saved in Traverse shows as set in The Lodge (once The Lodge has taken this family version);
changing your name or the appearance in one changes the other; Traverse's assignee picker lists The Lodge's people
while The Lodge is open, and says how to see them when it isn't; a call without the token gets 403.

**Result (2026-10-18, family f3b4e31 to 3a26cf7).**
- **Built as designed:** `core/server/family.py` (the family folder and `family.db`, shared settings, registry with a
  heartbeat, token, `call()`), `Module.offers`, settings that read and save shared keys through the family, the
  `GET /api/family` and `POST /api/family/call/<offer>` endpoints (the call endpoint passes the sign-in check and
  checks the family token itself), open screens refreshing on family changes, `core.appearance` as a setting (the
  browser keeps a copy for the first paint, and a choice made before the setting existed is kept), `<PREFIX>_PORT`,
  and Settings → "Your family apps". ARCHITECTURE.md describes it, and `Module.count` too.
- **The Lodge** has it on its own branch, `family/link` (85e43c5, pinned to 3a26cf7), with People offering
  `people.search` (names that start with the search first, then names with a word that does, then names that
  contain it, then other matches; you as `core:me`) and `people.get`. Not merged: main and the installed app are
  untouched. Mark's `shared-sheet` work in The Lodge's folder was left as it was.
- **Found on the way:** the shared `conftest.py` failed when `node_modules` was a link from elsewhere (now skipped),
  and the host's family tests assumed no real module offered `people.search` and that no app was called "lodge"
  (now a stand-in, "Faraway").
- **Verified:** 16 host tests and 4 People tests (91 and 224 in the two apps). End to end, with Traverse and The
  Lodge's branch running together on a throwaway family folder and a copy of The Lodge's data with every key and
  sync secret blanked: each app listed the other as open with its offers; a fake key saved in Traverse showed as set
  in The Lodge (the page got only the hint); your name and the appearance saved in The Lodge showed in Traverse, and
  switching to Day in Traverse's Settings turned The Lodge's window to Day within seconds; a People-only setting
  stayed in The Lodge; Traverse found The Lodge's people, and "mark" came back as `core:me`; calls without the token,
  or with a wrong one, got 403; with The Lodge stopped, it showed as closed, the call said "Open The Lodge to see
  this here.", and Traverse still had the shared key.
- **Not yet:** Traverse has no assignee picker until chunk 5; it will use `people.search` there. The installed apps
  haven't been rebuilt with this, so the real family folder hasn't been created yet.

### F4 · Updater and releases (M)

From Trailmix's `Updater.swift` and workflows: a beta channel, **Go back** to the previous version, skip a version,
no update in the middle of something the app marks as busy, and CI that publishes a pre-release which is promoted
after a few days with no blocking issue. Before Traverse's first release (chunk 14).

**Result (2026-10-19, on `claude/family-f4-updater-8da213`, not yet sent to the family).**
- **Updater** (`mac/Sources/AppHost/Updater.swift`): reads the repo's recent releases rather than "latest", and offers
  the newest version newer than itself. Pre-releases are offered only with **Beta updates** on, which is off by
  default. An update keeps the version it replaced in the data folder (`updates.noindex/previous/<Name>.app`).
  **Go back** returns to that version, checked the same way (same bundle ID, valid signature), and skips the one you
  left. **Skip this version** and **Offer X again** handle skipping. Before starting, and again before swapping (waiting
  up to a minute), it asks `GET /api/jobs/busy` and refuses while jobs are queued or running. The checksum, bundle ID
  and signature checks are unchanged. Choices live in `updates.noindex/choices.json`, so `<PREFIX>_DATA_DIR` keeps
  tests hermetic.
- **Rules apart from AppKit:** `mac/Sources/UpdateRules` (which version to offer, channel, skip, go back, reading
  GitHub's JSON, the busy answer) with 41 checks in `mac/Checks/UpdateChecks`, run by `swift run --package-path mac
  UpdateChecks` and by every `build-app.sh`. No XCTest needed.
- **Menu:** "Install version X…" with "Skip this version" under it, and an "Updates" submenu (Beta updates, Offer X
  again, Go back to X…, which asks first). The menu's items are now in sentence case (DESIGN.md §11).
- **Server:** `GET /api/jobs/busy` → `{"busy": jobs.busy()}`, with a test (busy while a job runs, not while one
  waits for you).
- **CI:** `release.yml` runs on a `v*` tag and refuses one that doesn't match `VERSION`. It builds, runs the smoke
  test, then publishes a pre-release to app.json's `updateRepo` (`RELEASE_TOKEN` for another repo). With no
  `updateRepo` it publishes nothing. `promote.yml` runs daily, calling `scripts/promote-beta.sh` (Trailmix's
  auto-promote, made generic): after 3 days with no open issue labelled `blocks release`, it promotes; it also
  takes a dry run or a tag by hand. `build-app.sh` now writes the version it was given into the bundle, so
  the server and Info.plist agree.
- **Smoke test, generic and cheap:** `scripts/smoke-test.sh <app> <dmg>` relabels a copy of the build as 0.0.1. With
  a stand-in for GitHub and the server, it checks that a beta isn't offered with Beta updates off, that nothing
  updates while busy, that with Beta updates on the beta installs and the old version is kept, that Go back returns
  to it and skips the new one, and that the skipped version isn't offered again.
- **Verified:** `swift build -c release` (no warnings); `build-app.sh --dmg`; UpdateChecks 41/41 (and they fail
  when a rule is broken); the smoke test passed on Traverse 0.1.0; `scripts/check-app.py` all good; `scripts/check`
  (115 tests, style clear, the expected family-drift note). The workflows parse, and their shell steps pass
  `bash -n` (no actionlint installed). `promote-beta.sh` was dry-run against fixtures for each case. `gh` returns
  an empty list for a label that doesn't exist yet.
- **Not done / for the family push:** `scripts/sync-family`'s `SHARED` list must gain `.github/workflows/promote.yml`,
  `scripts/promote-beta.sh` and `scripts/smoke-test.sh`, or `--push` leaves them behind (`mac/` is a folder, so it's
  covered). The workflows haven't run on GitHub. Go back is one step, from the kept copy: there's no download of
  older releases as in Trailmix, so a fresh install has nothing to go back to. CI doesn't run `check-app.py`. F5
  should make Lockdown stop the update check. Traverse's updates stay off until `updateRepo` names a repo its apps
  can read (a private repo's releases need a token). Spotted, not changed: the menu's "Inbox" opens `crm/inbox`,
  which Traverse doesn't have.

### F5 · Lockdown (M)

One switch, shared through the family link, that stops every cloud call: AI providers (at `ai.configured()`, the
one choke point), update checks and anything a module adds. From Trailmix's Lockdown.

### F6 · AI pricing and usage (M)

A host `pricing.py` and a usage table: what each AI call cost, by provider and module, with a running total in
Settings → AI. Before chunk 9, when the inbox starts spending money on extraction.

### F7 · Trailmix joins the family link (S–M, Mark's call)

Trailmix reads the shared keys and preferences from `family.db` and offers `meetings.recent` and `meetings.get`.
It's a change in Trailmix's own repository, independent of the rest. Until then, chunk 10 reads its local API.

## 7. Risks and spikes

| Risk | Plan |
| --- | --- |
| Plane's REST API differs from what its MCP tools show (field names, the work items vs issues paths, rate limits) | Spike at the start of chunk 5: read one project and one item with Mark's key and record the shapes as test fixtures |
| `description_html` is a whole-field write | The conflict check (rule 4), and descriptions are off the push by default until Mark turns them on per push |
| Two inboxes if the apps ever combine (People's and Traverse's) | Traverse's inbox is for work; The Lodge's meeting import already feeds `tasks` through `actions.found`, so the Trailmix bridge turns off when People is present |
| Chunk 0 touches The Lodge, which holds real data | Code-only change on a branch, a backup first, and The Lodge's full `scripts/check` before merging |
| Tasks v2 is shared code | Built only in `TrailmixFamily`; The Lodge takes it when Mark chooses (blueprint §3) |

## 8. Questions for later chunks

- **Milestones in Plane:** map Traverse milestones to Plane modules, Plane milestones, or keep them local? (Chunk 7.)
- **Sandbox:** may chunks 7 and 13 send real test pushes to the "Cold Connect" demo project in Plane?
- **Name and mark:** Traverse, "what's next, and who's on it", and the trail-across-a-slope mark are proposals.
- **Trailmix:** the most mature family app, but on its own architecture and shipping to users through GitHub
  releases. For now Traverse only talks to it over its local API (chunk 10). A comparison of Trailmix with the
  family host (what to adopt from it, and what porting it would take) is being written to
  `TRAILMIX-COMPARISON.md`; decide after reading it.

## 9. Not in this plan

- Two-way editing from Plane beyond "linked tasks follow Plane" (Plane webhooks would make pulls instant; later).
- Other team members using Traverse. Plane is their tool.
- Plane cycles, intake, pages and initiatives, beyond showing cycles in Team view.
- Taking the new `tasks` into The Lodge (blueprint chunk 10). Possible any time after chunk 4.

## 10. How to work through this

One chunk at a time, in order. Read the reference guides and `ARCHITECTURE.md` before each chunk. Run
`scripts/check` before calling a chunk done, record a short **Result** under it (as The Lodge's PLAN.md does), and
stop for Mark to look.
