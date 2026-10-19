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
| 3 | My tasks, quick add, the task page | M | ☐ |
| 4 | Projects list and project page, milestones, progress | M | ☐ |
| 5 | Plane connection and a read-only mirror; Team view; the people directory | M–L | ☐ |
| 6 | Linking: Traverse projects ↔ Plane projects, bringing Plane items in, "Changed in Plane" | M | ☐ |
| 7 | **Push to Plane**: previews, changed fields only, conflict stops, log and undo | L | ☐ |
| 8 | Board view and drag | M | ☐ |
| 9 | Inbox: capture anything, AI proposes work items, you review | L | ☐ |
| 10 | Meetings from Trailmix | S–M | ☐ |
| 11 | MCP server in the host: Claude Desktop and Claude Code can use Traverse | M | ☐ |
| 12 | AI in the app: status drafts, break a task down | M | ☐ |
| 13 | Home card, search, export, Settings, the auto-sync switch | M | ☐ |
| 14 | Mac: mark, menu, build and install beside The Lodge | M | ☐ |

Milestones: **A** "it runs" = 0–1 · **B** "my work, locally" = 2–4 · **C** "sees the team" = 5–6 ·
**D** "shares with the team" = 7–8 · **E** "AI does the typing" = 9–12 · **F** "shipped" = 13–14.

Sizes are relative effort (S ≈ one sitting, M ≈ a few, L ≈ many), not calendar time.

**Family track** (§6b): work on the shared host in `TrailmixFamily`, done from Traverse and taken by The Lodge when
Mark chooses. Asked for 2026-10-18: the Trailmix adoptions from `TRAILMIX-COMPARISON.md`, and family apps on one
Mac sharing data, keys and basic preferences.

| # | Family chunk | Size | When | Status |
| --- | --- | --- | --- | --- |
| F1 | A backup before an update migrates the database | S | with chunk 1 | ☑ 2026-10-18 (family 5166181) |
| F2 | Gemini's default model (`gemini-2.5-flash` is closed to new accounts) | S | with chunk 1 | ☑ 2026-10-18 (family 5166181) |
| F3 | **Family link:** shared keys and preferences, a registry of installed apps, app-to-app data calls | M–L | after chunk 1 | ☑ 2026-10-18 (family 3a26cf7); The Lodge has it on its `family/link` branch |
| F4 | Updater: beta channel, Go back, skip a version; CI publishes a pre-release and promotes it later | M | before chunk 14 | ☐ |
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
- "Send to Plane" on a task publishes a contract **`work.share_requested`** `{ref, fields, base}` with the task's
  shareable fields. `plane` receives it and queues the push job. `tasks` doesn't know Plane exists; any future
  sharing module (Linear, GitHub Issues) could listen to the same contract.
- After a pull, `plane` publishes **`work.updated_elsewhere`** `{ref, fields, source}` for linked items. `tasks`
  applies untouched fields and flags the rest.
- "Bring into Traverse" publishes `actions.found` with `details` (assignee, due date, project), as any source does,
  plus the link.

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

### Chunk 4 · Projects (M)

Blueprint chunk 4: projects list with health and progress, the project page (overview, list), milestones.

**Done when:** a real Cold Connect project, with milestones and tasks, reads right.

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

### Chunk 8 · Board view and drag (M)

Blueprint chunk 5. Dragging between columns changes status locally; for linked tasks, that change waits to be sent.

**Done when:** drag between columns updates status, the order sticks, and linked tasks show "1 change to send".

### Chunk 9 · Inbox (L)

- `inbox` module: paste text, drop a file, or (chunk 11) capture from Claude. Each capture is a row in
  `inbox_captures` with its source.
- An `inbox/extract` job (`ai.structured`) proposes work items: text, assignee (from the people directory), due
  date, project, priority, and the sentence it came from.
- The review screen: accept, edit or drop each proposal. Accepted ones publish `actions.found` with `details`, and
  `tasks` files them into the project.

**Done when:** a pasted Slack thread becomes three proposed tasks with the right people, and accepting them files
them into the right project.

### Chunk 10 · Meetings from Trailmix (S–M)

A recurring job reads summarized meetings from Trailmix's API and drops their action items into the inbox, linked
to the meeting. Off when Trailmix isn't running or the setting is off. (If the apps ever combine, The Lodge already imports
meetings, so this switches off there; see §7.)

**Done when:** yesterday's recorded meeting's action items wait in the inbox, each saying which meeting it came from.

### Chunk 11 · MCP server (M)

- `core/server/mcp.py` in `TrailmixFamily`: streamable HTTP at `/mcp`, a local token from Settings, and an optional
  `Module.tools` field.
- Tools from `tasks` (my work, find, add), `plane` (team workload, propose a push) and `inbox` (capture).
- Settings shows the one-line command for Claude Code and the config for Claude Desktop, with Copy.

**Done when:** Claude Code, asked "what's on my plate this week and file the follow-ups from this thread", answers
from Traverse and leaves proposals in the inbox, and anything for Plane waits for approval.

### Chunk 12 · AI in the app (M)

Blueprint chunk 8: status drafts per project (and, on approval, posted to Plane as a comment), break a task down.

**Done when:** a draft appears, says who wrote it, and can be edited, discarded or sent.

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
