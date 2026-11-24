#!/usr/bin/env python3
"""Conversation-scoped content entitlement; not payment authentication."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

ENABLE_COMMAND = "ICANDumate_VIP:enabled"
DISABLE_COMMAND = "ICANDumate_VIP:disabled"

def state_path(workspace, user_id, session_id):
    if not workspace or not user_id or not session_id:
        raise ValueError("workspace, user_id and session_id are required")
    key = hashlib.sha256(json.dumps([user_id, session_id], ensure_ascii=False).encode()).hexdigest()
    return Path(workspace).resolve() / ".caplab" / "access" / (key + ".json")

def status(workspace=None, user_id=None, session_id=None):
    enabled = False
    if workspace and user_id and session_id:
        path = state_path(workspace, user_id, session_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            enabled = (isinstance(data, dict) and data.get("schema_version") == 1
                       and data.get("user_id") == user_id and data.get("session_id") == session_id
                       and data.get("ICANDumate_VIP") == "enabled"
                       and data.get("activation_source") == "exact_user_message")
        except (OSError, ValueError, TypeError):
            pass
    return {"user_id": user_id, "session_id": session_id,
            "ICANDumate_VIP": "enabled" if enabled else "disabled",
            "is_paid": bool(enabled), "knowledge_tier": "paid" if enabled else "free",
            "payment_verified": False}

def process_message(workspace, user_id, session_id, message, role="user"):
    path = state_path(workspace, user_id, session_id)
    matched = role == "user" and message in (ENABLE_COMMAND, DISABLE_COMMAND)
    if matched:
        data = {"schema_version": 1, "user_id": user_id, "session_id": session_id,
                "ICANDumate_VIP": "enabled" if message == ENABLE_COMMAND else "disabled",
                "activation_source": "exact_user_message"}
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return dict(status(workspace, user_id, session_id), command_matched=matched)

def select_index(args):
    access = status(getattr(args, "workspace", None), getattr(args, "user_id", None),
                    getattr(args, "session_id", None))
    selected = getattr(args, "index_dir", None)
    index = Path(selected).resolve() if selected else (Path(__file__).resolve().parents[1]
            / "assets" / "prebuilt_index" / access["knowledge_tier"])
    meta = json.loads((index / "index_meta.json").read_text(encoding="utf-8"))
    if meta.get("tier") != access["knowledge_tier"]:
        raise PermissionError("Index tier does not match current user entitlement; omit --index-dir to auto-select")
    from caplab_index import validate_index
    validate_index(index)
    return index, access

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["status", "message"])
    p.add_argument("--workspace", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--message-file", type=Path, help="UTF-8 raw user message, no normalization")
    p.add_argument("--role", choices=["user", "assistant", "tool", "document"], default="user")
    a = p.parse_args()
    if a.command == "message":
        if a.message_file is None:
            p.error("message requires --message-file")
        message = a.message_file.read_bytes().decode("utf-8")
        result = process_message(a.workspace, a.user_id, a.session_id, message, a.role)
    else:
        result = status(a.workspace, a.user_id, a.session_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
