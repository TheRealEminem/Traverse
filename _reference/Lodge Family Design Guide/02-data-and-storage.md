# Data and storage

How The Lodge keeps its data, and the conventions the project app must follow so that, one day, both can live in
one database without a rewrite. Every table, column and rule here is taken from The Lodge's code as it stands
(13 October 2026, commit `aa02159`). Anything that doesn't exist yet is marked **Proposed**.

The full schema is in [`schema/lodge-schema.sql`](schema/lodge-schema.sql). The project app's tables are in
[`schema/tasks-v2-projects.sql`](schema/tasks-v2-projects.sql).

---

## 1. The shape

**One app is one process with one SQLite file.** No ORM, no Postgres, no server to install. The Python server
(FastAPI) owns the file. The web app and the Mac app only talk to it over HTTP.

| Where | Data folder |
| --- | --- |
| The Mac app | `~/Library/Application Support/<app name>/` (The Lodge: `~/Library/Application Support/The Lodge/`) |
| Development (`scripts/dev`) | `<repo>/data/` |
| Docker | `/data` (a volume) |
| Any of them, overridden | `<PREFIX>_DATA_DIR` (The Lodge: `LODGE_DATA_DIR`) |

```
<data folder>/                  private to you: the folder is 700, the files 600
  lodge.db                      the database, named after app.json "id" (WAL mode: lodge.db-wal and -shm beside it)
  backups/                      lodge-20261013-091500.db: one a day (kept 14), "-manual" (kept 20), "-before-restore" (kept 5)
  exports/                      lodge-export-20261013-091500.json: everything as plain JSON, without settings or keys
  <module id>/                  a module's own files (audio, attachments). None in The Lodge yet
```

The database file name comes from `app.json` `id`, so the project app gets its own (`<its id>.db`) and the two never
touch while they're separate apps.

## 2. Who owns what

A module is one folder (`modules/<id>/`) and owns everything named after its id. This is what makes merging
mechanical: nothing two modules own can collide, because every name starts with the owner's id.

| Thing | Name | The Lodge today |
| --- | --- | --- |
| Tables | `<id>_*` | `crm_entities`, `crm_relationships`… · `tasks_items` |
| Settings | `<id>.<name>` | `crm.extraction_provider`, `crm.granola_days`… |
| API | `/api/<id>/…` | `/api/crm/people`, `/api/tasks` |
| Pages | `#/<id>/…` | `#/crm/e/<id>`, `#/tasks` |
| Events | `<id>.<thing>.<happened>` | `crm.changed`, `crm.inbox.changed`, `tasks.changed` |
| Background jobs | `core_jobs.module = '<id>'` | `crm/extract`, `crm/granola_sync`, `crm/overview`… |
| Files | `<data folder>/<id>/` | none yet |
| Refs to its things | `"<id>:<row id>"` | `crm:3f2a…`, `tasks:9c1e…` |

The host (`core/`) owns `core_*` tables, the `core.*` and `ai.*` settings, `/api/*` outside module paths, and
`core.*` events.

**The rule that keeps this true:** a module never imports another module, never reads or writes another
module's tables, and never calls another module's API from the server. It reaches the rest of the app only
through the host (§8).

> **Module id is not app name.** The People module's id is `crm` and it lives in an app called The Lodge. Ids are
> permanent (they're in every table name and every ref), so choose them for the feature, not for the product. The
> project app's module is `tasks` (see the blueprint), whatever the app ends up being called.

## 3. Ids and refs

- **Every row gets a random text id** from `db.new_id()`: a UUID4 as 32 hex characters (`"3f2a9c…"`). Never an
  autoincrement number. Two separate apps' rows can then be copied into one database without colliding.
- **Ids are unique across all of a module's tables**, not just within one table (UUIDs make this free). So a ref
  doesn't need a type in it: `describe("tasks:<id>")` looks the id up in each of its tables.
- **A ref names a thing anywhere in the app:** `"<module id>:<row id>"`, built with `links.ref(module, id)`.
  Refs are how one module points at another's things: in `core_links`, in event payloads, and in `*_ref` columns.
- **There are no foreign keys between modules.** Inside a module, use real `REFERENCES … ON DELETE …`
  (foreign keys are on for every connection). Across modules, store a ref and expect it to dangle: the other
  module may be turned off, or the thing deleted.
- **Proposed: `core:me`**, the host's ref for whoever owns this copy of the app. It's described by the
  `core.your_name` setting, so "assigned to me" works in an app that has no People module. Where People is on, its
  `is_self` person is the same person (blueprint §6).

## 4. Column conventions

| Kind of value | Column | Stored as | Example |
| --- | --- | --- | --- |
| Id | `id TEXT PRIMARY KEY` | `db.new_id()` | `3f2a9c0e…` |
| An instant | `*_at` | UTC ISO-8601 ending in `Z`, from `db.now()` | `2026-10-13T16:05:09.412Z` |
| A calendar day | `*_on` | `YYYY-MM-DD`, no time, no zone | `2026-10-20` |
| A thing elsewhere | `*_ref` | `"<module>:<id>"`, no foreign key | `crm:3f2a…`, `core:me` |
| Its label | `*_name`, next to the ref | the name when it was set | `Ana Ruiz` |
| Yes or no | `INTEGER NOT NULL DEFAULT 0` | `0` / `1` | `done`, `is_self` |
| Open-ended fields | `attributes TEXT NOT NULL DEFAULT '{}'` | JSON object | `{"title": "Founder", "email": "…"}` |
| Tags | `tags TEXT NOT NULL DEFAULT '[]'` | JSON array, normalized | `["angel-investor"]` |
| A choice from a list | `kind`, `status` | plain lowercase string, listed in Python | `"meeting"`, `"doing"` |
| Where a row came from | `source TEXT NOT NULL DEFAULT 'manual'` | plain string | `manual`, `ai`, `granola`, `spreadsheet` |
| Who (or which AI) wrote it | `written_by` | AI provider label | `Claude (Anthropic)` |
| Your order | `sort REAL NOT NULL DEFAULT 0` | fractional: between two = their average | `1.5` |
| Long text | `TEXT` | Markdown | notes, briefs, summaries |
| Search | `<id>_fts` virtual table | FTS5, `tokenize='porter unicode61'`, re-fed on every write | `crm_fts`, `tasks_fts` |

More detail on a few of these:

- **Instants vs days.** A due date is a day on the calendar, not a moment. Store it as `YYYY-MM-DD` in an `_on`
  column and never convert it to UTC. Parse it at noon in the browser (`new Date(\`${d}T12:00:00\`)`, as People's
  `formatDate` does) so it can't slip a day. *Legacy:* People's relationships keep days in `started_at`/`ended_at`.
  New tables use `_on` for days.
- **Two timestamp precisions exist.** `db.now()` writes milliseconds (`…09.412Z`). People's own `iso()` writes
  microseconds (`…09.412345Z`) so rows imported in the same millisecond keep their order. Within one column that's
  fine. **When you merge timestamps from two modules** (an activity feed), parse them before comparing. Plain string
  order puts `.412Z` after `.412345Z`. New modules use `db.now()`.
- **Tags are normalized everywhere the same way:** lowercase, spaces become hyphens, at most 64 characters,
  duplicates dropped (`"Angel Investor"` → `"angel-investor"`). People does this in `store.normalize_tags`. Shared
  tags only work if every module normalizes identically, so promote that function to the host when a second
  module uses tags.
- **Vocabularies are strings, not tables or enums.** People's node and edge kinds are a Python dict
  (`modules/crm/server/kinds.py`), served to the web app at `GET /api/crm/meta`. Adding a kind needs no migration.
  Do the same for statuses, priorities and update kinds.
- **`attributes` before columns.** A field that only some rows have, or that might not last, goes in the JSON. Give it a
  column once you filter, sort or index on it. People indexes JSON directly when it must
  (`lower(json_extract(attributes, '$.email'))`).
- **`source` on everything an import or the AI can create.** It lets you take back one source's work ("remove
  everything that came from Granola"), and it tells people where something came from.
- **A label beside every ref.** `links.linked()` and `module.describe()` leave out things whose module is off. A
  `*_name` column means a task still says "Waiting on Ana Ruiz" in the standalone project app.

## 5. Migrations, and the one-lineage rule

Each module has a `MIGRATIONS` list: SQL strings, one per schema step. On startup the host runs the steps a
database hasn't seen, each in its own transaction, and records how many it has run in `core_migrations`:

```sql
CREATE TABLE core_migrations (module TEXT PRIMARY KEY, version INTEGER NOT NULL);
-- The Lodge today: core 1 · crm 4 · tasks 1
```

- **Append-only.** Never edit, reorder or remove a step that has shipped. Add a new one, even to fix a typo.
- **Old rows must stay valid.** New columns get defaults. Backfill in the same step (`UPDATE … SET …`).
- **Restores rely on it:** an older backup is brought up to date by running the steps it's missing.

> **The one-lineage rule (the most important rule in this guide).** `core_migrations` stores only a *count* per
> module. If The Lodge's `modules/tasks` and the project app's `modules/tasks` each grow a different step 2, both
> databases say `tasks = 2` and mean different schemas. No merge can fix that. So every family module has **exactly
> one source of truth**, and every app takes that module from it. The same goes for `core/`. Practically: the
> project app is where `tasks` grows from now on, and The Lodge copies `modules/tasks` from it. Neither app ever adds a
> migration to a module it doesn't own. See the blueprint, §2.

## 6. The host's tables

```sql
CREATE TABLE core_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);   -- "<namespace>.<name>" -> JSON
CREATE TABLE core_jobs (
    id TEXT PRIMARY KEY, module TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL,  -- target: the row it works on
    status TEXT NOT NULL,          -- queued | running | waiting | done | error
    stage TEXT, wait_reason TEXT, approved INTEGER NOT NULL DEFAULT 0, forced INTEGER NOT NULL DEFAULT 0,
    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE core_links (
    from_ref TEXT NOT NULL, to_ref TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'related', created_at TEXT NOT NULL,
    PRIMARY KEY (from_ref, to_ref, kind));
```

- **`core_settings`** holds every module's settings as JSON values. Secrets (names ending `_api_key`, `_token`,
  `_secret`) are stored here too, so a backup contains keys, but they're never sent to the web app. An export leaves
  settings out entirely.
- **`core_jobs`** is the queue of background work: one row per piece of work on one thing. It's working state, not
  data you'd carry between apps.
- **`core_links`** is the one place cross-module relationships live: `crm:<meeting>` → `tasks:<task>`, kind
  `action-item`. The host stores the pair, and each side's module describes its own end. Link kinds are plain
  strings. Kinds in use or proposed:

| Kind | From → to | Meaning | Status |
| --- | --- | --- | --- |
| `related` | any → any | the default | in use |
| `action-item` | where it was found → `tasks:<item>` | this task came out of that note or meeting | in use (tasks) |
| `about` | `tasks:<project>` → `crm:<org or topic>` | the project is for this client, or on this topic | proposed |
| `assigned` | `tasks:<item>` → `crm:<person>` | they're doing it (kept in step with `assignee_ref`) | proposed |
| `owner` | `tasks:<project>` → `crm:<person>` | they answer for it (kept in step with `owner_ref`) | proposed |
| `stakeholder` | `tasks:<project>` → `crm:<person>` | someone with a stake in it who isn't doing the work | proposed |
| `discussed-in` | `tasks:<project>` → `crm:<meeting>` (later `meetings:<id>`) | it came up in this meeting | proposed |

Use `core_links` only **between modules**. Relationships inside one module (task → project, task blocked by task,
person works at organization) are that module's own columns and tables, with real foreign keys.

## 7. The Lodge's tables

### People (`crm_*`): a graph in plain tables

Everything People knows is a **node** (`crm_entities`) or an **edge** (`crm_relationships`).

```
crm_entities ──< crm_relationships >── crm_entities      (source_id → target_id, kind, strength 1–5)
     │  │
     │  ├──< crm_notes          dated notes on a node (evidence_id: the meeting or document it came from)
     │  ├──< crm_overviews      one AI-written overview per person (fingerprint = what it was written from)
     │  └──< crm_questions      questions asked about a person, and their AI answers
     └── crm_fts                search over name, summary, aliases and details
crm_inbox     everything that came in (notes, documents, spreadsheets, meetings): raw text, AI proposal, result
crm_views     saved views of the network: a name and the groups switched on
crm_sync      where each automatic sync (Granola, calendars) got to
```

**Node kinds** (`crm_entities.kind`): `person`, `organization`, `meeting` (an event), `document` (an event),
`topic`. Events use `occurred_at`. Exactly one person may have `is_self = 1`: you.

**Edge kinds** (`crm_relationships.kind`), read source → target:

| Kind | Reads | Between |
| --- | --- | --- |
| `works_at` | works at / employs | person → organization |
| `advises` | advises / advised by | person → person or organization |
| `invested_in` | invested in / backed by | person or organization → organization |
| `introduced_by` | introduced by / introduced | person → person |
| `knows` | knows (both ways) | person ↔ person |
| `reports_to` | reports to / manages | person → person |
| `attended` | attended / attended by | person → meeting |
| `discussed_in` | discussed in | anything → meeting |
| `authored` | authored / authored by | person or organization → document |
| `mentioned_in` | mentioned in / mentions | anything → document |
| `about` | subject of / about | anything → document |
| `partner_of` | partner of (both ways) | organization ↔ organization |
| `part_of` | part of / includes | organization or topic → organization or topic |
| `related_to` | related to (both ways) | anything ↔ anything |

**`attributes` keys in use:** `title`, `email`, `phone`, `location`, `industry`, `website`, `linkedin_url`,
`aliases` (other names, kept on merge), `doc_type`, `research` (the research flag and what you did about it). Email
is indexed. It's how a person is matched across sources, and how the project app will find them (blueprint §6).

**Not stored:** how well you know someone (the tier: strong, working, light, indirect, none) is worked out from the
graph on every request (`connections.py`). Only a rating you set by hand is saved.

**`crm_inbox.status`** goes `pending → processing → review → applied`, or ends at `failed`, `discarded` or
`skipped`. `content_hash` stops the same file being read twice.

### Tasks (`tasks_items`)

```sql
CREATE TABLE tasks_items (
    id TEXT PRIMARY KEY, text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0,
    source_ref TEXT,               -- where it came from ("crm:<meeting id>"), if anywhere
    created_at TEXT NOT NULL);
```

Tasks are made by hand, or from the shared `actions.found` contract: People publishes it when a meeting or note
it reads has action items. The project app grows this table (blueprint §4). It doesn't replace it.

## 8. How modules share, without touching each other's tables

| You need to… | Use | Example |
| --- | --- | --- |
| Say "this happened", to anyone listening | **Event**: `events.publish("<id>.thing.happened", {...})` | `crm.changed` |
| Agree on a meaning that two modules share | **Contract** in `core/server/contracts.py` | `actions.found`, `item.deleted` |
| Keep a lasting relationship, shown on both sides | **Link**: `links.add(from_ref, to_ref, kind)` | meeting → task |
| Show another module's thing by name | **Describe**: `module.describe(ref)` → `{title, href}` | a task's "from: Coffee with Ana" |
| Be found from the one search box | **Search**: `Module.search(q, limit)` | ⌘K finds people and tasks |
| Do slow work | **Job**: `jobs.enqueue(module, kind, target)` | AI extraction, syncs |
| Find people from any module | **People directory**: `people.find(q)` | **Proposed** (blueprint §6) |

Events are synchronous and must be quick. Anything slow is enqueued as a job. Every publish also moves the change
counter (`GET /api/changes`) that open screens poll every 2 seconds, so any module's change refreshes any screen.

**Contracts today:**

```python
ACTIONS_FOUND = "actions.found"   # {source_ref: "<module>:<id>", items: ["Send Ana the deck", …]}
ITEM_DELETED  = "item.deleted"    # {ref: "<module>:<id>"}
```

Proposed additions for the project app are in [`schema/contracts-proposed.py`](schema/contracts-proposed.py).

## 9. Settings and secrets

- Declared by each module with defaults (`Module.settings`) and allowed values (`Module.choices`), stored as
  `<id>.<name>`. The host owns `core.your_name` and the `ai.*` set (provider, fallback, models, keys).
- A default can be preset from the environment: `<PREFIX>_<NAMESPACE>_<NAME>` (`LODGE_AI_PROVIDER=anthropic`).
- Secrets end in `_api_key`, `_token` or `_secret`. They're write-only: the web app only ever sees `…1234`.
- **In a merged app**, `ai.*` and `core.*` exist once. Pick whose wins when merging (§11). Module settings never clash.

## 10. Backups, restore, export

- **Backups** are SQLite online backups of the whole file: consistent while the app writes, and complete (keys
  included). One a day is kept for 14 days, plus "Back up now" and one made automatically before any restore.
- **Restore** copies a backup over the live database, runs any migrations it's missing, and publishes
  `core.restored`, so modules that cache anything (People does) rebuild it.
- **Export** is each module's `Module.export()` gathered into one readable JSON file. It's what you'd use to move to
  another tool, or to check a merge. Shape (see [`schema/export-example.json`](schema/export-example.json)):

```json
{ "app": "lodge", "version": "0.1.0", "exported_at": "2026-10-13T16:05:09+00:00",
  "modules": { "crm": { "entities": [], "relationships": [], "notes": [], "views": [] },
               "tasks": { "projects": [], "milestones": [], "items": [], "updates": [], "blockers": [] } } }
```

JSON columns are exported as JSON (not as strings), and working state (inbox, jobs) is left out. Every module that
holds data people care about should implement `export`. The Tasks module doesn't yet, and the project app should add it.

## 11. Merging two family apps into one

The plan in `ARCHITECTURE.md` §13, made concrete. *Not written yet.* It's a script to write when the day comes,
and the conventions above are what make it short.

**Before:** both apps run the **same `core/`** and the **same version of every module they share** (the
one-lineage rule). Upgrade both apps first, so their `core_migrations` rows agree for every shared module.

**Then, into a fresh unified database:**

1. Start the unified app once on an empty data folder, with every module in `app.json`, so all tables exist at the
   newest version.
2. For each source database: `ATTACH` it, and check that its `core_migrations` version for each module equals the
   unified one. Stop if not.
3. Copy every `<module>_*` table with `INSERT OR IGNORE INTO main.t SELECT * FROM src.t` (ids are random, so
   nothing collides). Skip the FTS shadow tables and rebuild each FTS index afterwards from its table.
4. Copy `core_links` the same way (its primary key de-duplicates).
5. Copy `core_settings` for module namespaces. For `core.*` and `ai.*`, keep one app's values (ask which).
6. Don't copy `core_jobs`. Recurring jobs re-queue themselves.
7. Start the unified app. A one-off job then fills the people refs the project app stored as names only, matched by
   email (blueprint §6).

What the person sees afterwards: one sidebar with People, Projects and My tasks, one search box, one Home, and
everything they had in both apps.

## 12. Gaps to close in The Lodge before a merge

Small things that work for one app on its own but would bite once a second module points at people:

1. **People doesn't announce deletes.** `crm/store.delete_entity` should publish `item.deleted` with
   `crm:<id>` and call `links.forget(...)`, so other modules can drop or blank their refs.
2. **Merging two people strands refs.** `merge_entities` should publish the proposed `people.merged`
   (`{from_ref, into_ref}`) so modules rewrite their `*_ref` columns.
3. **Profiles don't show links.** Add `<LinkedList of={"crm:" + id} />` to the profile page so a person shows the
   projects and tasks linked to them, from whichever module.
4. **The host knows about People.** `core/server/backup.py` counts `crm_entities` to label backups. That should become
   an optional `Module.count` (or come from `export`), so `core/` stays the same in every app.
5. **The Tasks module has no `export`.** Add it with the project tables.
6. **The Lodge's look lives inside `core/`.** Palette, scene and copy should move to an identity layer. See the
   blueprint, §2.
