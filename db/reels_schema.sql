-- Reels Agent — Schéma SQLite (source of truth, sur OVH VPS)
-- Lancer: sqlite3 reels.db < reels_schema.sql
PRAGMA foreign_keys = ON;

-- === Taxonomie évolutive : fixe + suggestions promouvables ===
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    type        TEXT CHECK(type IN ('fixed','suggested','promoted')) DEFAULT 'suggested',
    parent_id   INTEGER REFERENCES categories(id),
    usage_count INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO categories(name, type) VALUES ('Dev / IA', 'fixed');
INSERT OR IGNORE INTO categories(name, type) VALUES ('Business', 'fixed');
INSERT OR IGNORE INTO categories(name, type) VALUES ('Motivation', 'fixed');
INSERT OR IGNORE INTO categories(name, type) VALUES ('Lifestyle', 'fixed');
INSERT OR IGNORE INTO categories(name, type) VALUES ('Sorties / Adresses', 'fixed');
INSERT OR IGNORE INTO categories(name, type) VALUES ('Fitness', 'fixed');
INSERT OR IGNORE INTO categories(name, type) VALUES ('Autre', 'fixed');

-- === Queue des liens en attente (remplie par Hermès via tool enqueue_reel) ===
CREATE TABLE IF NOT EXISTS pending_reels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT NOT NULL,
    platform      TEXT DEFAULT 'instagram',
    tg_message_id TEXT,
    user_note     TEXT,
    status        TEXT CHECK(status IN ('pending','processing','done','failed')) DEFAULT 'pending',
    error         TEXT,
    added_at      TEXT DEFAULT (datetime('now')),
    reel_id       INTEGER REFERENCES reels(id)
);

-- === Reels traités (source of truth, ce qu'Hermès requête) ===
CREATE TABLE IF NOT EXISTS reels (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    url              TEXT UNIQUE NOT NULL,
    platform         TEXT NOT NULL,
    creator          TEXT,
    title            TEXT,
    thumbnail_url    TEXT,
    duration_sec     INTEGER,
    language         TEXT,
    transcript       TEXT,
    summary          TEXT,
    key_points       TEXT,
    category_id     INTEGER REFERENCES categories(id),
    tags             TEXT,
    needs_vision     INTEGER DEFAULT 0,
    vision_analysis  TEXT,
    raw_metadata     TEXT,
    notion_page_id   TEXT,
    notion_synced_at TEXT,
    processed_at     TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reels_category ON reels(category_id);
CREATE INDEX IF NOT EXISTS idx_reels_created  ON reels(created_at);

-- Recherche plein-texte (FTS5) sur transcript + summary
CREATE VIRTUAL TABLE IF NOT EXISTS reels_fts USING fts5(
    transcript, summary, content='reels', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS reels_ai AFTER INSERT ON reels BEGIN
    INSERT INTO reels_fts(rowid, transcript, summary) VALUES (new.id, new.transcript, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS reels_ad AFTER DELETE ON reels BEGIN
    INSERT INTO reels_fts(reels_fts, rowid, transcript, summary) VALUES('delete', old.id, old.transcript, old.summary);
END;
CREATE TRIGGER IF NOT EXISTS reels_au AFTER UPDATE ON reels BEGIN
    INSERT INTO reels_fts(reels_fts, rowid, transcript, summary) VALUES('delete', old.id, old.transcript, old.summary);
    INSERT INTO reels_fts(rowid, transcript, summary) VALUES (new.id, new.transcript, new.summary);
END;

-- === Suggestions de catégories par l'IA (validation humaine via Hermès) ===
CREATE TABLE IF NOT EXISTS category_suggestions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    suggested_name TEXT NOT NULL,
    reel_id        INTEGER REFERENCES reels(id),
    status         TEXT CHECK(status IN ('pending','accepted','rejected')) DEFAULT 'pending',
    proposed_at    TEXT DEFAULT (datetime('now'))
);
