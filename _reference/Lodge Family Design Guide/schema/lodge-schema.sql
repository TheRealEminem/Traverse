-- The Lodge: the whole database schema, exactly as the migrations build it (app.json modules: crm, tasks).
-- Generated on 2026-10-13 from a fresh database (commit aa02159), with: sqlite3 lodge.db .schema
-- One file per app: ~/Library/Application Support/The Lodge/lodge.db (WAL mode). Read 02-data-and-storage.md first.
--
-- Owners:  core_*  the host (core/server/db.py)      crm_*  People (modules/crm/server/store.py)
--          tasks_*  Tasks (modules/tasks/server/store.py)
-- Applied versions today: core 1, crm 4, tasks 1 (table core_migrations).

CREATE TABLE core_migrations (module TEXT PRIMARY KEY, version INTEGER NOT NULL);
CREATE TABLE core_settings (
        key   TEXT PRIMARY KEY,        -- "<namespace>.<name>", e.g. "ai.provider", "notes.auto_summarize"
        value TEXT NOT NULL            -- JSON
    );
CREATE TABLE core_jobs (
        id          TEXT PRIMARY KEY,
        module      TEXT NOT NULL,
        kind        TEXT NOT NULL,     -- what to do, e.g. "summarize"
        target      TEXT NOT NULL,     -- the id of the thing it's done to
        status      TEXT NOT NULL,     -- queued | running | waiting | done | error
        stage       TEXT,              -- progress in words while running ("Summarizing part 2 of 3")
        wait_reason TEXT,              -- why it's waiting ("Needs you", "Not enough free memory")
        approved    INTEGER NOT NULL DEFAULT 0,
        forced      INTEGER NOT NULL DEFAULT 0,
        error       TEXT,
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
CREATE INDEX core_jobs_target ON core_jobs(module, target);
CREATE TABLE core_links (
        from_ref   TEXT NOT NULL,      -- "<module>:<id>"
        to_ref     TEXT NOT NULL,
        kind       TEXT NOT NULL DEFAULT 'related',
        created_at TEXT NOT NULL,
        PRIMARY KEY (from_ref, to_ref, kind)
    );
CREATE INDEX core_links_to ON core_links(to_ref);
CREATE TABLE crm_entities (
        id          TEXT PRIMARY KEY,
        kind        TEXT NOT NULL,
        name        TEXT NOT NULL,
        summary     TEXT,
        attributes  TEXT NOT NULL DEFAULT '{}',      -- JSON: title, email, aliases, ...
        tags        TEXT NOT NULL DEFAULT '[]',      -- JSON array
        occurred_at TEXT,                            -- meetings and documents
        is_self     INTEGER NOT NULL DEFAULT 0,      -- the owner's own person record ("me")
        source      TEXT NOT NULL DEFAULT 'manual',  -- manual | ai | ingest | spreadsheet | linkedin | webhook | demo
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
CREATE INDEX crm_entities_kind ON crm_entities(kind);
CREATE INDEX crm_entities_name ON crm_entities(name COLLATE NOCASE);
CREATE INDEX crm_entities_occurred ON crm_entities(occurred_at);
CREATE INDEX crm_entities_email ON crm_entities(lower(json_extract(attributes, '$.email')));
CREATE UNIQUE INDEX crm_entities_single_self ON crm_entities(is_self) WHERE is_self = 1;
CREATE TABLE crm_relationships (
        id          TEXT PRIMARY KEY,
        source_id   TEXT NOT NULL REFERENCES crm_entities(id) ON DELETE CASCADE,
        target_id   TEXT NOT NULL REFERENCES crm_entities(id) ON DELETE CASCADE,
        kind        TEXT NOT NULL,
        properties  TEXT NOT NULL DEFAULT '{}',
        strength    INTEGER NOT NULL DEFAULT 3 CHECK (strength BETWEEN 1 AND 5),
        started_at  TEXT,
        ended_at    TEXT,
        source      TEXT NOT NULL DEFAULT 'manual',
        evidence_id TEXT REFERENCES crm_entities(id) ON DELETE SET NULL,  -- the meeting or document it came from
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL,
        UNIQUE (source_id, target_id, kind),
        CHECK (source_id <> target_id)
    );
CREATE INDEX crm_relationships_source ON crm_relationships(source_id);
CREATE INDEX crm_relationships_target ON crm_relationships(target_id);
CREATE INDEX crm_relationships_kind ON crm_relationships(kind);
CREATE TABLE crm_notes (
        id          TEXT PRIMARY KEY,
        entity_id   TEXT NOT NULL REFERENCES crm_entities(id) ON DELETE CASCADE,
        body        TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        source      TEXT NOT NULL DEFAULT 'manual',
        evidence_id TEXT REFERENCES crm_entities(id) ON DELETE SET NULL,
        created_at  TEXT NOT NULL
    );
CREATE INDEX crm_notes_entity ON crm_notes(entity_id);
CREATE TABLE crm_inbox (
        id           TEXT PRIMARY KEY,
        source       TEXT NOT NULL,       -- manual_note | webhook | linkedin_csv | document | spreadsheet | meeting
        status       TEXT NOT NULL,       -- pending | processing | review | applied | failed | discarded | skipped
        content_hash TEXT,                -- so re-imports and "(1)" copies are skipped
        title        TEXT,
        occurred_at  TEXT,
        raw_text     TEXT,
        payload      TEXT NOT NULL DEFAULT '{}',
        proposal     TEXT,
        result       TEXT,
        error        TEXT,
        extractor    TEXT,
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL
    );
CREATE INDEX crm_inbox_status ON crm_inbox(status);
CREATE INDEX crm_inbox_hash ON crm_inbox(content_hash);
CREATE VIRTUAL TABLE crm_fts USING fts5(id UNINDEXED, name, summary, aliases, details, tokenize='porter unicode61')
/* crm_fts(id,name,summary,aliases,details) */;
CREATE TABLE crm_views (
        id         TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        wells      TEXT NOT NULL DEFAULT '[]',   -- JSON array of group ids ("org:…", "topic:…", "tag:…")
        created_at TEXT NOT NULL
    );
CREATE TABLE crm_sync (
        name       TEXT PRIMARY KEY,
        state      TEXT NOT NULL DEFAULT '{}',   -- JSON
        updated_at TEXT NOT NULL
    );
CREATE TABLE crm_overviews (
        id          TEXT PRIMARY KEY,
        entity_id   TEXT NOT NULL UNIQUE REFERENCES crm_entities(id) ON DELETE CASCADE,
        body        TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        written_by  TEXT NOT NULL,
        created_at  TEXT NOT NULL
    );
CREATE TABLE crm_questions (
        id          TEXT PRIMARY KEY,
        entity_id   TEXT NOT NULL REFERENCES crm_entities(id) ON DELETE CASCADE,
        question    TEXT NOT NULL,
        answer      TEXT,
        status      TEXT NOT NULL DEFAULT 'queued',   -- queued, done, error
        error       TEXT,
        written_by  TEXT,
        created_at  TEXT NOT NULL,
        answered_at TEXT
    );
CREATE INDEX crm_questions_entity ON crm_questions(entity_id, created_at);
CREATE TABLE tasks_items (
        id          TEXT PRIMARY KEY,
        text        TEXT NOT NULL,
        done        INTEGER NOT NULL DEFAULT 0,
        source_ref  TEXT,                 -- where it came from ("notes:<id>"), if anywhere
        created_at  TEXT NOT NULL
    );
CREATE INDEX tasks_items_source ON tasks_items(source_ref);
