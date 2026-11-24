"""单进程本地演示的持久化业务状态；云端继续使用 PostgreSQL。"""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from ..protocol.patch import PatchError, empty_state, validate_state


class LocalRepository:
    def __init__(self, filename: Path, templates: Path):
        self.filename = filename
        self.templates = templates
        with closing(sqlite3.connect(filename)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS revisions
                (owner TEXT, chat TEXT, revision INTEGER, state TEXT,
                 PRIMARY KEY(owner, chat, revision))""")

    def load(self, session_id, user_id):
        with closing(sqlite3.connect(self.filename)) as conn:
            row = conn.execute("SELECT state FROM revisions WHERE owner=? AND chat=? ORDER BY revision DESC LIMIT 1",
                               (user_id, session_id)).fetchone()
        return json.loads(row[0]) if row else empty_state(self.templates)

    def save(self, session_id, user_id, state, patch_id=None):
        errors = validate_state(state)
        if errors:
            raise PatchError(errors)
        with closing(sqlite3.connect(self.filename)) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO revisions VALUES (?,?,?,?)",
                         (user_id, session_id, state["revision"], json.dumps(state, ensure_ascii=False)))

    def revision(self, session_id, user_id, rev):
        with closing(sqlite3.connect(self.filename)) as conn:
            row = conn.execute("SELECT state FROM revisions WHERE owner=? AND chat=? AND revision=?",
                               (user_id, session_id, rev)).fetchone()
        return json.loads(row[0]) if row else None

    def list_sessions(self, user_id):
        with closing(sqlite3.connect(self.filename)) as conn:
            return [row[0] for row in conn.execute("SELECT DISTINCT chat FROM revisions WHERE owner=? ORDER BY chat", (user_id,))]
