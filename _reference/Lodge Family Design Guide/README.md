# The Lodge family: design guide

How The Lodge looks, behaves and stores its data, written down so the next app (a project manager) can be built as
a sibling now and folded into one app with The Lodge later, without rewriting either.

Taken from The Lodge's code on 13 October 2026 (version 0.1.0, commit `aa02159`). Anything not built yet is marked
**Proposed**.

## What's in here

| File | What it is |
| --- | --- |
| [`design-guide.html`](design-guide.html) | **Start here.** The visual guide: open it in a browser. Colors, the status language, type, components, patterns, the data map and the marks, drawn with The Lodge's real tokens. Switch Day and Dusk at the top. |
| [`01-ui-and-ux.md`](01-ui-and-ux.md) | How every family app looks, moves and talks, plus the patterns The Lodge's screens use |
| [`02-data-and-storage.md`](02-data-and-storage.md) | How data is stored: one SQLite file, module-owned tables, random ids, refs, links, events, every table The Lodge has, and how two apps merge |
| [`03-project-app-blueprint.md`](03-project-app-blueprint.md) | The project manager specified as a family module: what to do in The Lodge first, the data model, screens, how it ties into People, and the build order |
| `tokens/` | The design tokens as files to copy: `tokens.css` (verbatim from the app), `tokens.json` (Day and Dusk, for other tools), `tailwind.config.js`, `Brand.swift` (native) |
| `schema/` | `lodge-schema.sql` (The Lodge's exact schema) · `tasks-v2-projects.sql` (the project tables, tested against a copy of it) · `contracts-proposed.py` · `export-example.json` |
| `assets/` | `lodge-mark.svg` · `project-app-mark.svg` (a proposal: a cairn on the family's sky tile) |

## Portability in seven rules

If the project app keeps these, merging it with The Lodge is a matter of copying rows.

1. **Same host.** Both apps run the same `core/`. Start from The Lodge's, which is well ahead of the old starter, and
   never edit it inside one app.
2. **One copy of every shared module.** `core_migrations` only counts steps, so two different "step 2"s for the
   same module can never be merged. The project app is where the `tasks` module grows, and The Lodge takes it from there.
3. **Everything a module owns starts with its id:** tables `tasks_*`, settings `tasks.*`, API `/api/tasks`, pages
   `#/tasks/…`, events `tasks.*`.
4. **Random text ids, never autoincrement,** and things elsewhere are named by refs: `"crm:<id>"`, `"tasks:<id>"`.
5. **No module touches another's tables.** They meet through the host: links, events and contracts, search, describe,
   and (proposed) a people directory.
6. **Schema changes are appended, never edited.** Days are `_on`, instants are `_at`, and a ref keeps a readable name
   beside it.
7. **The same tokens and kit.** The project app reuses The Lodge's palette exactly, and sets itself apart only
   through its name, mark, scene and motif.

## The three decisions worth checking

The blueprint makes three calls that shape everything else. Read its §2, §3 and §6 before building:

- **Projects live in the existing Tasks module** (grown up), not in a new module. That gives one place for all work,
  and action items from your meetings keep flowing in as they do today.
- **Before starting, move The Lodge's look out of `core/`** into an `identity/` folder, and keep shared code in one
  place (a `TrailmixFamily` folder), so the two apps can't drift.
- **People are referenced, never copied.** A small host "people directory" lets the project app pick from The Lodge's
  People when it's there, and use plain names when it isn't.

## Prompt for an AI agent starting the project app

> This app is part of the Trailmix family and must stay mergeable with The Lodge. Before changing anything, read
> README.md, 01-ui-and-ux.md, 02-data-and-storage.md and 03-project-app-blueprint.md in the "Lodge Family Design Guide"
> folder, then ARCHITECTURE.md, core/server/module.py, core/web/registry.ts and modules/tasks. Build in the order of the
> blueprint's §11 and stop at each "done when". Projects live in the tasks module (append migration step 2 from
> schema/tasks-v2-projects.sql; never edit a shipped step). Never import another module, read its tables or call its
> API from the server. Use the kit's tokens, classes and components, design for Day and Dusk, and run scripts/check
> before you finish.
