"""JSON Schema / 业务准入校验。

保留原 Skill 的互补校验原则：JSON Schema 通过 ≠ 业务准入通过。
Schema 文件直接来自 Skill 基线，业务校验在本模块以纯函数实现。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ids import (
    FORBIDDEN_KEYS, ID_RE, SCHEMA_VERSION, STAGES, STATE_KEYS,
    VALID_SECTION_STATUSES, VALID_WORKFLOW_STATUSES,
    SECTION_OWNERS, now,
)

_SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))


def schema_errors(value: Any, schema: dict, path: str = "$") -> list[str]:
    """递归校验 JSON Schema 子集（type/required/properties/enum/const/items/additionalProperties）。
    避免引入 jsonschema 依赖导致镜像膨胀；如需完整校验可替换为 jsonschema.validate。
    """
    errors: list[str] = []
    types = schema.get("type")
    if types:
        expected = types if isinstance(types, list) else [types]
        ok = False
        for t in expected:
            if t == "object" and isinstance(value, dict):
                ok = True
            elif t == "array" and isinstance(value, list):
                ok = True
            elif t == "string" and isinstance(value, str):
                ok = True
            elif t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
                ok = True
            elif t == "integer" and isinstance(value, int) and not isinstance(value, bool):
                ok = True
            elif t == "boolean" and isinstance(value, bool):
                ok = True
            elif t == "null" and value is None:
                ok = True
        if not ok:
            return [f"{path}: expected type {expected}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']!r}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: too short")
        if "pattern" in schema:
            import re
            if not re.search(schema["pattern"], value):
                errors.append(f"{path}: does not match pattern {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field {key}")
        props = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for key, sub in props.items():
            if key in value:
                errors.extend(schema_errors(value[key], sub, f"{path}.{key}"))
        for key, sub_value in value.items():
            if key in props:
                continue
            matched = False
            for pattern, sub_schema in patterns.items():
                import re
                if re.search(pattern, key):
                    matched = True
                    errors.extend(schema_errors(sub_value, sub_schema, f"{path}.{key}"))
                    break
            if matched:
                continue
            if schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected field {key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(schema_errors(sub_value, schema["additionalProperties"], f"{path}.{key}"))
    if isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                errors.extend(schema_errors(item, item_schema, f"{path}[{i}]"))
    return errors


def validate_state_business(state: Any) -> list[str]:
    """业务状态校验，对齐原 caplab_state.validate_state + caplab_profile 关键门槛。"""
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state must be an object"]
    for key in ("schema_version", "state_id", "revision", "active_stage",
                "workflow_status", "sections", "section_meta", "id_registry"):
        if key not in state:
            errors.append(f"missing state field {key}")
    if errors:
        return errors
    if state["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not ID_RE.match(str(state["state_id"])) or not str(state["state_id"]).startswith("CAP-"):
        errors.append("state_id must match CAP-000001")
    if not isinstance(state["revision"], int) or state["revision"] < 0:
        errors.append("revision must be a non-negative integer")
    if state["active_stage"] not in STAGES:
        errors.append(f"active_stage must be one of {STAGES}")
    if state["workflow_status"] not in VALID_WORKFLOW_STATUSES:
        errors.append("invalid workflow_status")
    if not isinstance(state["sections"], dict) or set(state["sections"]) != set(SECTION_OWNERS):
        errors.append("sections must contain exactly intake/profile/path_decision/cycle_plan/reviews")
    if not isinstance(state["section_meta"], dict) or set(state["section_meta"]) != set(SECTION_OWNERS):
        errors.append("section_meta must cover all five sections")
    for name, meta in state["section_meta"].items():
        if not isinstance(meta, dict) or meta.get("status") not in VALID_SECTION_STATUSES:
            errors.append(f"invalid status for section_meta.{name}")
    for prefix, value in state["id_registry"].items():
        if not isinstance(value, int) or value < 0:
            errors.append(f"invalid id_registry counter for {prefix}")
    return errors


def validate_state_schema(state: dict) -> list[str]:
    """用随包 schema 做结构校验（schema 文件为权威公共契约）。"""
    try:
        schema = load_schema("caplab-state.schema.json")
    except FileNotFoundError:
        return []
    return schema_errors(state, schema)


def validate_state(state: dict) -> list[str]:
    return validate_state_business(state) + validate_state_schema(state)


def forbidden_key_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, sub in value.items():
            if key in FORBIDDEN_KEYS:
                errors.append(f"{path}.{key}: forbidden field")
            errors.extend(forbidden_key_errors(sub, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            errors.extend(forbidden_key_errors(item, f"{path}[{i}]"))
    return errors
