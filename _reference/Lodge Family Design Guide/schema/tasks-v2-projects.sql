-- PROPOSED: step 2 of modules/tasks MIGRATIONS. It turns the family's Tasks module into the project manager.
-- Not built yet. Read 03-project-app-blueprint.md §3 for why projects live in the tasks module.
--
-- Paste this text, unchanged, as the second string in MIGRATIONS (modules/tasks/server/store.py). The host wraps it
-- in BEGIN/COMMIT and records tasks = version 2 in core_migrations. Once it has shipped in any app, never edit it:
-- later changes are step 3, 4… And make this change in ONE copy of modules/tasks that every family app takes
-- (02-data-and-storage.md §5). Two apps with different step 2s can never be merged.
--
-- Conventions (02-data-and-storage.md §4): random text ids from db.new_id(); *_at = an instant, UTC ISO-8601 with Z,
-- from db.now(); *_on = a calendar day, 'YYYY-MM-DD', no time zone; *_ref = "<module>:<id>" pointing outside this
-- module (no foreign key); *_name next to a ref = its label when it was set, so it still reads right when the other
-- module is off; JSON in TEXT columns; vocabularies (status, kind, health) are plain strings listed in Python.

CREATE TABLE tasks_projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    summary     TEXT,                              -- one line: what done looks like
    brief       TEXT NOT NULL DEFAULT '',          -- the longer write-up, markdown
    status      TEXT NOT NULL DEFAULT 'active',    -- planned | active | paused | done | dropped
    health      TEXT,                              -- on_track | at_risk | off_track; NULL = not judged yet
    start_on    TEXT,                              -- YYYY-MM-DD
    due_on      TEXT,                              -- YYYY-MM-DD
    owner_ref   TEXT,                              -- "core:me", "crm:<person id>"…; NULL = nobody yet
    owner_name  TEXT,
    attributes  TEXT NOT NULL DEFAULT '{}',        -- JSON: anything not worth a column yet
    tags        TEXT NOT NULL DEFAULT '[]',        -- JSON array, normalized like People's ("client-work")
    sort        REAL NOT NULL DEFAULT 0,           -- your order in lists (fractional: insert between = average)
    source      TEXT NOT NULL DEFAULT 'manual',    -- manual | ai | import | template
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    archived_at TEXT                               -- set = out of the lists, kept for history and search
);
CREATE INDEX tasks_projects_status ON tasks_projects(status, archived_at);

CREATE TABLE tasks_milestones (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES tasks_projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    due_on      TEXT,                              -- YYYY-MM-DD
    done_at     TEXT,
    sort        REAL NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX tasks_milestones_project ON tasks_milestones(project_id, sort);

-- The to-dos that exist today become work items. Every new column has a default, so old rows stay valid and
-- the code that reads only (id, text, done, source_ref) keeps working. `done` stays, and the store keeps it
-- equal to (status = 'done') in the one function that changes status.
ALTER TABLE tasks_items ADD COLUMN project_id    TEXT REFERENCES tasks_projects(id) ON DELETE SET NULL;
ALTER TABLE tasks_items ADD COLUMN milestone_id  TEXT REFERENCES tasks_milestones(id) ON DELETE SET NULL;
ALTER TABLE tasks_items ADD COLUMN parent_id     TEXT REFERENCES tasks_items(id) ON DELETE CASCADE;  -- subtasks
ALTER TABLE tasks_items ADD COLUMN status        TEXT NOT NULL DEFAULT 'todo';   -- todo | doing | waiting | done | dropped
ALTER TABLE tasks_items ADD COLUMN notes         TEXT NOT NULL DEFAULT '';       -- markdown
ALTER TABLE tasks_items ADD COLUMN priority      INTEGER NOT NULL DEFAULT 0;     -- 0 none, 1 low, 2 high, 3 urgent
ALTER TABLE tasks_items ADD COLUMN start_on      TEXT;                           -- YYYY-MM-DD
ALTER TABLE tasks_items ADD COLUMN due_on        TEXT;                           -- YYYY-MM-DD
ALTER TABLE tasks_items ADD COLUMN assignee_ref  TEXT;                           -- "core:me", "crm:<person id>"; NULL = nobody
ALTER TABLE tasks_items ADD COLUMN assignee_name TEXT;
ALTER TABLE tasks_items ADD COLUMN estimate_min  INTEGER;
ALTER TABLE tasks_items ADD COLUMN sort          REAL NOT NULL DEFAULT 0;
ALTER TABLE tasks_items ADD COLUMN attributes    TEXT NOT NULL DEFAULT '{}';
ALTER TABLE tasks_items ADD COLUMN tags          TEXT NOT NULL DEFAULT '[]';
ALTER TABLE tasks_items ADD COLUMN source        TEXT NOT NULL DEFAULT 'manual'; -- manual | action-item | ai | import
ALTER TABLE tasks_items ADD COLUMN completed_at  TEXT;
ALTER TABLE tasks_items ADD COLUMN updated_at    TEXT;
UPDATE tasks_items SET status       = CASE WHEN done THEN 'done' ELSE 'todo' END,
                       completed_at = CASE WHEN done THEN created_at END,
                       source       = CASE WHEN source_ref IS NULL THEN 'manual' ELSE 'action-item' END,
                       updated_at   = created_at;
CREATE INDEX tasks_items_project  ON tasks_items(project_id, status, sort);
CREATE INDEX tasks_items_assignee ON tasks_items(assignee_ref, status);
CREATE INDEX tasks_items_due      ON tasks_items(due_on) WHERE due_on IS NOT NULL;
CREATE INDEX tasks_items_parent   ON tasks_items(parent_id);

-- What has to happen first. Both ends are work items in this module, so this is a table, not a core link.
CREATE TABLE tasks_blockers (
    item_id     TEXT NOT NULL REFERENCES tasks_items(id) ON DELETE CASCADE,
    blocked_by  TEXT NOT NULL REFERENCES tasks_items(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (item_id, blocked_by),
    CHECK (item_id <> blocked_by)
);
CREATE INDEX tasks_blockers_by ON tasks_blockers(blocked_by);

-- Comments and status updates on a project or a work item: yours, or written by AI (written_by says which).
CREATE TABLE tasks_updates (
    id          TEXT PRIMARY KEY,
    project_id  TEXT REFERENCES tasks_projects(id) ON DELETE CASCADE,
    item_id     TEXT REFERENCES tasks_items(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL DEFAULT 'comment',   -- comment | status | summary
    body        TEXT NOT NULL,                     -- markdown
    health      TEXT,                              -- kind = status: the health it reported
    author_ref  TEXT,                              -- "core:me", "crm:<person id>"; NULL when AI wrote it
    author_name TEXT,
    written_by  TEXT,                              -- the AI provider that wrote it, shown next to it
    created_at  TEXT NOT NULL,
    CHECK ((project_id IS NULL) <> (item_id IS NULL))
);
CREATE INDEX tasks_updates_project ON tasks_updates(project_id, created_at);
CREATE INDEX tasks_updates_item    ON tasks_updates(item_id, created_at);

-- One search index for projects and work items (kind says which), fed by the store on every write.
CREATE VIRTUAL TABLE tasks_fts USING fts5(id UNINDEXED, kind UNINDEXED, title, body, tokenize='porter unicode61');
INSERT INTO tasks_fts (id, kind, title, body) SELECT id, 'item', text, notes FROM tasks_items;
