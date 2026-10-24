from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3


class OperationConflict(ValueError):
    pass


class Journal:
    """Never automatically replay an ambiguous external browser action."""
    def __init__(self, path):
        self.path = path
        with self.connection() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS operations(
                key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, kind TEXT NOT NULL,
                state TEXT NOT NULL, result TEXT, created_at TEXT NOT NULL)''')
            # An in-flight action may have reached a platform before the process stopped.
            c.execute("UPDATE operations SET state='uncertain' WHERE state='running'")

    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.path, timeout=20)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def begin(self, key, fingerprint, kind):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM operations WHERE key=?', (key,)).fetchone()
            if row:
                if row['fingerprint'] != fingerprint:
                    raise OperationConflict('Operation ID was already used for another request')
                if row['state'] == 'done':
                    return json.loads(row['result'])
                raise OperationConflict('Previous action is uncertain or failed; inspect the page before another attempt')
            c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',
                      (key, fingerprint, kind, 'running', None, datetime.now(timezone.utc).isoformat()))
        return None

    def finish(self, key, state, result=None):
        with self.connection() as c:
            c.execute('UPDATE operations SET state=?,result=? WHERE key=?',
                      (state, json.dumps(result) if result is not None else None, key))

    def get(self, key):
        with self.connection() as c:
            row = c.execute('SELECT key,kind,state,created_at FROM operations WHERE key=?', (key,)).fetchone()
            return dict(row) if row else None
