-- A5 evidence store. Rebuilt on every pipeline run except link_overrides,
-- which holds the coordinator's review decisions and survives re-runs.

DROP TABLE IF EXISTS children;
DROP TABLE IF EXISTS source_lines;
DROP TABLE IF EXISTS mentions;
DROP TABLE IF EXISTS facts;
DROP TABLE IF EXISTS child_states;
DROP TABLE IF EXISTS run_meta;

CREATE TABLE children (
    child_id TEXT PRIMARY KEY,
    first TEXT NOT NULL,
    surname TEXT NOT NULL,
    class TEXT NOT NULL,
    age INTEGER,
    gender TEXT
);

CREATE TABLE source_lines (
    line_id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    ref TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}',
    UNIQUE (source_file, ref)
);

-- Every name occurrence and what A4 decided about it.
CREATE TABLE mentions (
    mention_id INTEGER PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES source_lines(line_id),
    surface TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('linked', 'review', 'unlinked', 'override')),
    child_id TEXT REFERENCES children(child_id),
    score REAL,
    candidates TEXT NOT NULL DEFAULT '[]'
);

-- One cited statement. quote is an exact substring of source_lines.text.
CREATE TABLE facts (
    fact_id INTEGER PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES source_lines(line_id),
    mention_id INTEGER REFERENCES mentions(mention_id),
    child_id TEXT REFERENCES children(child_id),
    type TEXT NOT NULL,
    date TEXT,
    quote TEXT NOT NULL,
    summary TEXT NOT NULL,
    value TEXT NOT NULL DEFAULT '{}',
    extractor TEXT NOT NULL
);

CREATE TABLE child_states (
    child_id TEXT PRIMARY KEY REFERENCES children(child_id),
    state TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '[]',
    rule_refs TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE run_meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS link_overrides (
    source_file TEXT NOT NULL,
    ref TEXT NOT NULL,
    surface TEXT NOT NULL,
    child_id TEXT NOT NULL,
    decided_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_file, ref, surface)
);

CREATE INDEX idx_facts_child ON facts(child_id);
CREATE INDEX idx_mentions_line ON mentions(line_id);
