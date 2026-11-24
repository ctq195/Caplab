#!/usr/bin/env python3
"""Create and maintain isolated CapLab test archives identified by SAVE-NNNNNN."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import hmac
import os
import re
from pathlib import Path
from functools import wraps


SAVE_ID = re.compile(r"^SAVE-[0-9]{6}$")
CONFIG = Path(__file__).resolve().parents[1] / "assets" / "test-mode-config.json"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def checked_root(value: str) -> Path:
    root = Path(value).resolve()
    if root.name != ".caplab-test-archives":
        raise ValueError("archive root must end with .caplab-test-archives")
    return root


def archive_path(root: Path, save_id: str) -> Path:
    if not SAVE_ID.fullmatch(save_id):
        raise ValueError("save_id must match SAVE-NNNNNN")
    return root / save_id


def authorize(access_code: str) -> None:
    expected = str(json.loads(CONFIG.read_text(encoding="utf-8"))["access_code"])
    if not hmac.compare_digest(str(access_code), expected):
        raise PermissionError("invalid test archive access code")


def create_archive(root: Path, access_code: str) -> dict:
    authorize(access_code)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".create.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    except FileExistsError as exc:
        raise RuntimeError("another SAVE allocation is in progress") from exc
    try:
        maximum = max(
            (int(path.name.split("-", 1)[1]) for path in root.iterdir() if path.is_dir() and SAVE_ID.fullmatch(path.name)),
            default=0,
        )
        save_id = f"SAVE-{maximum + 1:06d}"
        target = root / save_id
        target.mkdir(mode=0o700)
        metadata = {
            "schema_version": "1.0.0",
            "save_id": save_id,
            "mode": "isolated_test_session",
            "status": "active",
            "created_at": now_iso(),
            "closed_at": None,
            "formal_state_link": None,
            "cross_test_memory_allowed": False,
        }
        atomic_json(target / "session.json", metadata)
        return metadata
    finally:
        lock.unlink(missing_ok=True)


def load_metadata(root: Path, save_id: str) -> tuple[Path, dict]:
    target = archive_path(root, save_id)
    path = target / "session.json"
    if not path.is_file():
        raise FileNotFoundError(f"unknown test archive: {save_id}")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if metadata.get("save_id") != save_id:
        raise ValueError("archive metadata id mismatch")
    return target, metadata


def serialized(func):
    @wraps(func)
    def wrapped(root, save_id, *args, **kwargs):
        target = archive_path(root, save_id)
        lock = target / ".write.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("archive mutation already in progress") from exc
        os.close(fd)
        try:
            return func(root, save_id, *args, **kwargs)
        finally:
            lock.unlink(missing_ok=True)
    return wrapped

@serialized
def pause_archive(root, save_id, access_code):
    authorize(access_code)
    target, metadata = load_metadata(root, save_id)
    if metadata.get("status") == "closed":
        raise ValueError("closed archive cannot be paused")
    metadata.update(status="paused", recording_paused=True)
    atomic_json(target / "session.json", metadata)
    return metadata

@serialized
def resume_archive(root, save_id, access_code, confirmed=False):
    authorize(access_code)
    target, metadata = load_metadata(root, save_id)
    if confirmed is not True:
        raise ValueError("explicit user confirmation is required to resume")
    if metadata.get("status") != "paused":
        raise ValueError("only a paused archive may resume")
    metadata.update(status="active", recording_paused=False)
    atomic_json(target / "session.json", metadata)
    return metadata

@serialized
def append_event(root: Path, save_id: str, role: str, text: str, access_code: str) -> dict:
    authorize(access_code)
    target, metadata = load_metadata(root, save_id)
    if metadata.get("status") != "active":
        raise ValueError(f"archive is not active: {save_id}")
    event = {"at": now_iso(), "role": role, "text": text}
    with (target / "transcript.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"save_id": save_id, "status": "appended"}


@serialized
def close_archive(root: Path, save_id: str, access_code: str) -> dict:
    authorize(access_code)
    target, metadata = load_metadata(root, save_id)
    metadata["status"] = "closed"
    metadata["closed_at"] = now_iso()
    atomic_json(target / "session.json", metadata)
    return metadata


def show_archive(root: Path, save_id: str, access_code: str) -> dict:
    authorize(access_code)
    target, metadata = load_metadata(root, save_id)
    transcript = []
    transcript_path = target / "transcript.jsonl"
    if transcript_path.is_file():
        transcript = [json.loads(line) for line in transcript_path.read_text(encoding="utf-8").splitlines() if line]
    return {"metadata": metadata, "transcript": transcript}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--root", required=True)
    create.add_argument("--access-code", required=True)
    append = sub.add_parser("append")
    append.add_argument("--root", required=True)
    append.add_argument("--save-id", required=True)
    append.add_argument("--role", choices=("user", "assistant", "system_event"), required=True)
    append.add_argument("--text", required=True)
    append.add_argument("--access-code", required=True)
    close = sub.add_parser("close")
    close.add_argument("--root", required=True)
    close.add_argument("--save-id", required=True)
    close.add_argument("--access-code", required=True)
    show = sub.add_parser("show")
    show.add_argument("--root", required=True)
    show.add_argument("--save-id", required=True)
    show.add_argument("--access-code", required=True)
    for command in ("pause", "resume"):
        item = sub.add_parser(command)
        item.add_argument("--root", required=True)
        item.add_argument("--save-id", required=True)
        item.add_argument("--access-code", required=True)
        if command == "resume":
            item.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    root = checked_root(args.root)
    if args.command == "create":
        result = create_archive(root, args.access_code)
    elif args.command == "append":
        result = append_event(root, args.save_id, args.role, args.text, args.access_code)
    elif args.command == "pause":
        result = pause_archive(root, args.save_id, args.access_code)
    elif args.command == "resume":
        result = resume_archive(root, args.save_id, args.access_code, args.confirm)
    elif args.command == "close":
        result = close_archive(root, args.save_id, args.access_code)
    else:
        result = show_archive(root, args.save_id, args.access_code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
