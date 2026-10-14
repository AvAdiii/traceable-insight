import json
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path: Path | str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text())


def insert_children(conn, roster: list[dict]) -> None:
    conn.executemany(
        "INSERT INTO children VALUES (:child_id, :first, :surname, :class, :age, :gender)", roster)


def insert_lines(conn, lines) -> dict[tuple[str, str], int]:
    """Insert SourceLines; return (source_file, ref) -> line_id."""
    ids = {}
    for l in lines:
        cur = conn.execute(
            "INSERT INTO source_lines (source_file, ref, kind, text, meta) VALUES (?,?,?,?,?)",
            (l.source_file, l.ref, l.kind, l.text, json.dumps(l.meta, ensure_ascii=False)))
        ids[(l.source_file, l.ref)] = cur.lastrowid
    return ids


def insert_mention(conn, line_id: int, surface: str, status: str, child_id, score,
                   candidates) -> int:
    cur = conn.execute(
        "INSERT INTO mentions (line_id, surface, status, child_id, score, candidates) "
        "VALUES (?,?,?,?,?,?)",
        (line_id, surface, status, child_id, score, json.dumps(candidates)))
    return cur.lastrowid


def insert_fact(conn, fact: dict) -> int:
    cur = conn.execute(
        "INSERT INTO facts (line_id, mention_id, child_id, type, date, quote, summary, value, "
        "extractor) VALUES (:line_id, :mention_id, :child_id, :type, :date, :quote, :summary, "
        ":value, :extractor)",
        {**fact, "value": json.dumps(fact.get("value", {}))})
    return cur.lastrowid


def overrides(conn) -> dict[tuple[str, str, str], str]:
    rows = conn.execute("SELECT source_file, ref, surface, child_id FROM link_overrides")
    return {(r[0], r[1], r[2]): r[3] for r in rows}


def set_meta(conn, **kv) -> None:
    conn.executemany("INSERT OR REPLACE INTO run_meta VALUES (?, ?)",
                     [(k, json.dumps(v)) for k, v in kv.items()])
