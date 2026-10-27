import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, text

from .config import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DATA_DIR / 'assistant.db'}", connect_args={"check_same_thread": False})


def now():
    return datetime.now(UTC).isoformat()


def initialize():
    with engine.begin() as conn:
        for statement in [
            "CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT, updated_at TEXT)",
            "CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, sources TEXT, created_at TEXT)",
            "CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, title TEXT, body TEXT, tags TEXT, updated_at TEXT)",
            "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(id UNINDEXED, title, body, tags)",
            "CREATE TABLE IF NOT EXISTS scenes (id TEXT PRIMARY KEY, request TEXT, result TEXT, created_at TEXT)",
        ]:
            conn.execute(text(statement))


def rows(sql, **params):
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(text(sql), params).mappings()]


def execute(sql, **params):
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def save_message(cid, role, content, sources=None):
    execute(
        "INSERT INTO messages VALUES (:id,:cid,:role,:content,:sources,:created)",
        id=str(uuid4()),
        cid=cid,
        role=role,
        content=content,
        sources=json.dumps(sources or []),
        created=now(),
    )
    execute("UPDATE conversations SET updated_at=:updated WHERE id=:id", updated=now(), id=cid)


def save_note(title, body, tags, note_id=None):
    note_id = note_id or str(uuid4())
    params = dict(id=note_id, title=title, body=body, tags=json.dumps(tags), updated=now())
    with engine.begin() as conn:
        conn.execute(text("INSERT OR REPLACE INTO notes VALUES (:id,:title,:body,:tags,:updated)"), params)
        conn.execute(text("DELETE FROM notes_fts WHERE id=:id"), params)
        conn.execute(text("INSERT INTO notes_fts VALUES (:id,:title,:body,:tags)"), params)
    return note_id
