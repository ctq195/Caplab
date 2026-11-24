#!/usr/bin/env python3
"""Parse explicit CapLab test archive create/read commands before other routing."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "assets" / "test-mode-config.json"


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    for key in ("create_prefix", "read_prefix", "access_code", "save_id_pattern"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError(f"{key} must be a non-empty string")
    if not config["access_code"].isdigit():
        raise ValueError("access_code must contain digits only")
    re.compile(f"^(?:{config['save_id_pattern']})$")
    return config


def classify(text: str, config: dict) -> dict:
    current = normalized(text)
    create_prefix = re.escape(normalized(config["create_prefix"]))
    read_prefix = re.escape(normalized(config["read_prefix"]))
    code = re.escape(config["access_code"])
    save_pattern = config["save_id_pattern"]
    create_match = re.fullmatch(rf"{create_prefix}\s+{code}\s*:\s*(.+)", current, re.IGNORECASE | re.DOTALL)
    read_match = re.fullmatch(
        rf"{read_prefix}\s+({save_pattern})\s+{code}(?:\s*:\s*(.*))?",
        current,
        re.IGNORECASE | re.DOTALL,
    )
    resembles_command = bool(re.match(rf"(?:{create_prefix}|{read_prefix})\b", current, re.IGNORECASE))
    if create_match:
        return {
            "mode": "isolated_test_session",
            "action": "create",
            "accepted": True,
            "save_id": None,
            "test_input": create_match.group(1).strip(),
            "memory_policy": "new_save_only_no_formal_or_cross_save_memory",
            "allowed_knowledge": "bundled_public_seed_only",
            "formal_state_io_allowed": False,
            "requires_fresh_platform_session": True,
        }
    if read_match:
        return {
            "mode": "isolated_test_session",
            "action": "read",
            "accepted": True,
            "save_id": read_match.group(1).upper(),
            "test_input": (read_match.group(2) or "").strip(),
            "memory_policy": "named_save_only_no_formal_or_cross_save_memory",
            "allowed_knowledge": "bundled_public_seed_only",
            "formal_state_io_allowed": False,
            "requires_fresh_platform_session": True,
        }
    if resembles_command:
        return {
            "mode": "test_command_rejected",
            "action": None,
            "accepted": False,
            "save_id": None,
            "test_input": "",
            "reason": "invalid syntax, access code, SAVE id, or missing create payload",
            "formal_state_io_allowed": False,
        }
    return {
        "mode": "normal",
        "action": None,
        "accepted": False,
        "save_id": None,
        "test_input": "",
        "formal_state_io_allowed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(json.dumps(classify(args.text, load_config(args.config)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
