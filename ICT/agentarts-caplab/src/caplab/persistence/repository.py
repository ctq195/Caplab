"""状态仓储：本地内存实现（离线测试）与 PostgreSQL 实现（云端运行时）。

云端硬约束：禁止依赖本地文件系统。所有状态、修订历史、确认审计、
失效标记与 LangGraph checkpoint 必须落在外部存储。接口一致，便于切换。
"""
from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any, Protocol

from ..protocol.ids import now
from ..protocol.patch import PatchError, empty_state, validate_state


class StateRepository(Protocol):
    def load(self, session_id: str, user_id: str) -> dict[str, Any]: ...
    def save(self, session_id: str, user_id: str, state: dict[str, Any],
             patch_id: str | None = None) -> None: ...
    def revision(self, session_id: str, user_id: str, rev: int) -> dict[str, Any] | None: ...
    def list_sessions(self, user_id: str) -> list[str]: ...


class InMemoryRepository:
    """离线测试用。进程内隔离，不写磁盘。"""

    def __init__(self, template_dir: Path | None = None):
        self._template_dir = template_dir or (
            Path(__file__).resolve().parents[3] / "assets" / "templates"
        )
        self._lock = threading.RLock()
        self._current: dict[tuple[str, str], dict] = {}
        self._history: dict[tuple[str, str], dict[int, dict]] = {}

    def _key(self, session_id: str, user_id: str) -> tuple[str, str]:
        if not session_id or not user_id:
            raise ValueError("session_id and user_id are required for isolation")
        return user_id, session_id

    def load(self, session_id: str, user_id: str) -> dict[str, Any]:
        key = self._key(session_id, user_id)
        with self._lock:
            if key not in self._current:
                state = empty_state(self._template_dir)
                self._current[key] = state
                self._history[key] = {0: copy.deepcopy(state)}
            return copy.deepcopy(self._current[key])

    def save(self, session_id: str, user_id: str, state: dict[str, Any],
             patch_id: str | None = None) -> None:
        errors = validate_state(state)
        if errors:
            raise PatchError(errors)
        key = self._key(session_id, user_id)
        with self._lock:
            if key not in self._history:
                self._history[key] = {}
            self._history[key][state["revision"]] = copy.deepcopy(state)
            self._current[key] = copy.deepcopy(state)

    def revision(self, session_id: str, user_id: str, rev: int) -> dict[str, Any] | None:
        key = self._key(session_id, user_id)
        with self._lock:
            snapshot = self._history.get(key, {}).get(rev)
            return copy.deepcopy(snapshot) if snapshot else None

    def list_sessions(self, user_id: str) -> list[str]:
        with self._lock:
            return sorted(s for u, s in self._current if u == user_id)


class PostgresRepository:
    """云端实现。需要 psycopg[binary]；表结构见 sql/001_init.sql。"""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def _connect(self):
        import psycopg
        return psycopg.connect(self._dsn)

    def _key(self, session_id: str, user_id: str) -> tuple[str, str]:
        if not session_id or not user_id:
            raise ValueError("session_id and user_id are required for isolation")
        return user_id, session_id

    def load(self, session_id: str, user_id: str) -> dict[str, Any]:
        user_id, session_id = self._key(session_id, user_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT state_json FROM caplab_state WHERE user_id=%s AND session_id=%s",
                (user_id, session_id),
            )
            row = cur.fetchone()
            if row:
                return (json.loads(row[0]) if isinstance(row[0], str) else row[0])
        state = empty_state(Path(__file__).resolve().parents[3] / "assets" / "templates")
        self.save(session_id, user_id, state)
        return state

    def save(self, session_id: str, user_id: str, state: dict[str, Any],
             patch_id: str | None = None) -> None:
        errors = validate_state(state)
        if errors:
            raise PatchError(errors)
        user_id, session_id = self._key(session_id, user_id)
        payload = json.dumps(state, ensure_ascii=False)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO caplab_state (user_id, session_id, revision, state_json, updated_at)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (user_id, session_id) DO UPDATE SET
                     revision=EXCLUDED.revision, state_json=EXCLUDED.state_json, updated_at=EXCLUDED.updated_at""",
                (user_id, session_id, state["revision"], payload, now()),
            )
            cur.execute(
                """INSERT INTO caplab_revision (user_id, session_id, revision, patch_id, state_json, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (user_id, session_id, state["revision"], patch_id, payload, now()),
            )
            for event in state.get("confirmation_events", []):
                cur.execute(
                    """INSERT INTO caplab_confirmation
                       (user_id, session_id, confirmation_id, patch_id, decision, scope, confirmation_text, recorded_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id, session_id, confirmation_id) DO NOTHING""",
                    (user_id, session_id, event["confirmation_id"], event.get("patch_id"),
                     event.get("decision"), json.dumps(event.get("scope", [])),
                     event.get("confirmation_text", ""), event.get("recorded_at", now())),
                )
            for inv in state.get("invalidations", []):
                cur.execute(
                    """INSERT INTO caplab_invalidation
                       (user_id, session_id, section, caused_by_patch, caused_by_section, at_revision)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (user_id, session_id, inv["section"], inv.get("caused_by_patch"),
                     inv.get("caused_by_section"), inv.get("at_revision")),
                )

    def revision(self, session_id: str, user_id: str, rev: int) -> dict[str, Any] | None:
        user_id, session_id = self._key(session_id, user_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT state_json FROM caplab_revision WHERE user_id=%s AND session_id=%s AND revision=%s",
                (user_id, session_id, rev),
            )
            row = cur.fetchone()
            return (json.loads(row[0]) if isinstance(row[0], str) else row[0]) if row else None

    def list_sessions(self, user_id: str) -> list[str]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT session_id FROM caplab_state WHERE user_id=%s", (user_id,))
            return sorted(r[0] for r in cur.fetchall())


def build_repository(dsn: str | None = None, template_dir: Path | None = None):
    """云上设置 DATABASE_URL 时用 PostgreSQL，否则用内存仓储（仅本地测试）。"""
    if dsn:
        return PostgresRepository(dsn)
    return InMemoryRepository(template_dir)
