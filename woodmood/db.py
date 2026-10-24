from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def now():
    return datetime.now(timezone.utc).isoformat()


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
 id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
 description TEXT NOT NULL, images TEXT NOT NULL, published_at TEXT,
 manual_order INTEGER UNIQUE CHECK(manual_order > 0), fingerprint TEXT NOT NULL,
 discovered_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 needs_review INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS drafts (
 id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id),
 platform TEXT NOT NULL, caption TEXT NOT NULL, images TEXT NOT NULL,
 source_fingerprint TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('draft','ready','scheduled')),
 scheduled_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(project_id, platform)
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scans (
 id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL, discovered INTEGER NOT NULL DEFAULT 0, error TEXT
);
CREATE TABLE IF NOT EXISTS plans (
 id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, content TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def event(self, conn, kind, detail):
        conn.execute("INSERT INTO events(kind,detail,created_at) VALUES(?,?,?)",
                     (kind, json.dumps(detail, ensure_ascii=False), now()))

    def projects(self):
        with self.connect() as c:
            rows = c.execute("""SELECT * FROM projects ORDER BY
              CASE WHEN manual_order IS NOT NULL THEN 0 WHEN published_at IS NOT NULL THEN 1 ELSE 2 END,
              manual_order, published_at, id""").fetchall()
            return [self.decode_project(r) for r in rows]

    @staticmethod
    def decode_project(row):
        item = dict(row)
        item["images"] = json.loads(item["images"])
        return item

    def drafts(self):
        with self.connect() as c:
            rows = c.execute("""SELECT drafts.*, projects.title, projects.url,
                 projects.needs_review FROM drafts JOIN projects ON projects.id=drafts.project_id
                 ORDER BY drafts.id""").fetchall()
            return [{**dict(r), "images": json.loads(r["images"])} for r in rows]

    def history(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")]

    def latest_scan(self):
        with self.connect() as c:
            row = c.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1").fetchone()
            return dict(row) if row else None
