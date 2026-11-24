#!/usr/bin/env python3
"""Deterministic state runtime for the CapLab DuMate workspace.

The CLI deliberately uses only the Python standard library so it can run in a
minimal DuMate workspace.  It validates permissions and transitions itself;
the JSON Schema files are the portable public contract.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


from caplab_profile import intake_errors, sections_errors, downgrade_legacy, empty_personal
from caplab_bootstrap import ensure_knowledge, require_ready, BootstrapError, knowledge_workspace

SCHEMA_VERSION = "1.1.0"
SKILL_VERSION = "2.2.0"
# Earlier patches require re-proposal against the current state; saved history is unchanged.
ALLOWED_SKILL_VERSIONS = {SKILL_VERSION}
ID_PREFIXES = ("CAP", "SRC", "INT", "PRO", "HYP", "PTH", "GAP", "CYC", "OBS", "REV", "CFM", "PAT")
ID_RE = re.compile(r"^(CAP|SRC|INT|PRO|HYP|PTH|GAP|CYC|OBS|REV|CFM|PAT)-([0-9]{6})$")
STAGES = (
    "profile_intake",
    "profile_confirmation",
    "path_convergence",
    "path_evidence_cycle",
    "evidence_review",
    "closed",
    "blocked",
)
SECTION_OWNERS = {
    "intake": "caplab-profile-intake",
    "profile": "caplab-profile-confirmation",
    "path_decision": "caplab-path-convergence",
    "cycle_plan": "caplab-path-evidence-cycle",
    "reviews": "caplab-evidence-review",
}
WRITE_PREFIXES = {
    "caplab-profile-intake": ("/sections/intake",),
    "caplab-profile-confirmation": ("/sections/profile",),
    "caplab-path-convergence": ("/sections/path_decision",),
    "caplab-path-evidence-cycle": ("/sections/cycle_plan",),
    "caplab-evidence-review": ("/sections/reviews",),
    "caplab-workflow-orchestrator": ("/active_stage", "/workflow_status", "/invalidations"),
}
SECTION_DEPENDENCIES = {
    "intake": ("profile", "path_decision", "cycle_plan", "reviews"),
    "profile": ("path_decision", "cycle_plan", "reviews"),
    "path_decision": ("cycle_plan", "reviews"),
    "cycle_plan": ("reviews",),
    "reviews": (),
}
FORBIDDEN_KEYS = {"fit_score", "success_probability", "career_probability", "bank_card_number", "identity_card_number"}
VALID_SECTION_STATUSES = {"empty", "draft", "confirmed", "accepted", "active", "partial", "stale", "closed"}
VALID_WORKFLOW_STATUSES = {"active", "waiting_confirmation", "paused", "closed", "blocked", "invalid"}
PATCH_KEYS = {"patch_id", "actor_skill", "skill_version", "base_revision", "operation", "changes", "referenced_ids", "requires_confirmation", "summary"}
STATE_KEYS = {
    "schema_version", "state_id", "revision", "parent_revision", "active_stage", "workflow_status", "sections",
    "section_meta", "id_registry", "confirmation_events", "invalidations", "applied_patch_ids", "rollback_of", "updated_at"
}


class CapLabError(Exception):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapLabError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapLabError(f"invalid JSON {path}: {exc}") from exc


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


@contextmanager
def state_lock(root: Path):
    lock = root / "audit" / ".caplab-state.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise CapLabError(f"state is locked by another operation: {lock}") from exc
    try:
        os.write(fd, f"pid={os.getpid()} at={now()}\n".encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state_id": "CAP-000001",
        "revision": 0,
        "parent_revision": None,
        "active_stage": "profile_intake",
        "workflow_status": "active",
        "sections": {"intake": load_json(Path(__file__).resolve().parents[1] / "assets/templates/intake-draft.json"), "profile": {}, "path_decision": {}, "cycle_plan": {}, "reviews": []},
        "section_meta": {
            name: {"status": "empty", "section_revision": None, "owner_skill": owner}
            for name, owner in SECTION_OWNERS.items()
        },
        "id_registry": {prefix: (1 if prefix == "CAP" else 0) for prefix in ID_PREFIXES},
        "confirmation_events": [],
        "invalidations": [],
        "applied_patch_ids": [],
        "rollback_of": None,
        "updated_at": None,
    }


def state_path(root: Path) -> Path:
    return root / "caplab_state.json"


def iter_items(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_items(child)


def collect_ids(value: Any) -> list[str]:
    ids: list[str] = []
    for item in iter_items(value):
        if not isinstance(item, dict):
            continue
        for key, candidate in item.items():
            if (key == "id" or key.endswith("_id")) and isinstance(candidate, str) and ID_RE.match(candidate):
                ids.append(candidate)
    return ids


def collect_identity_ids(value: Any) -> list[str]:
    """Collect object identities without mistaking scalar references for owners."""
    identities: list[str] = []
    identity_keys = {
        "id", "record_id", "conflict_id", "hypothesis_id", "path_id", "gap_id",
        "cycle_id", "observation_id", "review_id", "confirmation_id"
    }
    for item in iter_items(value):
        if not isinstance(item, dict):
            continue
        for key, candidate in item.items():
            if key in identity_keys and isinstance(candidate, str) and ID_RE.match(candidate):
                identities.append(candidate)
        # source_id is an identity only on a source record, not on every claim.
        source_id = item.get("source_id")
        if isinstance(source_id, str) and ID_RE.match(source_id) and any(
            key in item for key in ("source_type", "url", "publisher", "checked_at")
        ):
            identities.append(source_id)
    return identities


def collect_reference_values(value: Any) -> list[str]:
    refs: list[str] = []
    for item in iter_items(value):
        if not isinstance(item, dict):
            continue
        for key, candidate in item.items():
            if key.endswith("_ids") and isinstance(candidate, list):
                refs.extend(x for x in candidate if isinstance(x, str) and ID_RE.match(x))
            elif (key.endswith("_reference") or key in {"source_id", "path_id", "gap_id", "cycle_id"}) and isinstance(candidate, str) and ID_RE.match(candidate):
                refs.append(candidate)
    return refs


def forbidden_key_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                errors.append(f"forbidden key {path}.{key}")
            errors.extend(forbidden_key_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(forbidden_key_errors(child, f"{path}[{index}]"))
    return errors


def validate_state(state: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state must be an object"]
    required = {
        "schema_version", "state_id", "revision", "parent_revision", "active_stage", "workflow_status",
        "sections", "section_meta", "id_registry", "confirmation_events", "invalidations", "applied_patch_ids", "updated_at"
    }
    errors.extend(f"missing root field {key}" for key in sorted(required - set(state)))
    errors.extend(f"unknown root field {key}" for key in sorted(set(state) - STATE_KEYS))
    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported schema_version {state.get('schema_version')!r}")
    if not isinstance(state.get("revision"), int) or state.get("revision", -1) < 0:
        errors.append("revision must be a non-negative integer")
    if state.get("active_stage") not in STAGES:
        errors.append(f"invalid active_stage {state.get('active_stage')!r}")
    if state.get("workflow_status") not in VALID_WORKFLOW_STATUSES:
        errors.append(f"invalid workflow_status {state.get('workflow_status')!r}")
    sections = state.get("sections")
    if not isinstance(sections, dict):
        errors.append("sections must be an object")
        sections = {}
    for name in SECTION_OWNERS:
        if name not in sections:
            errors.append(f"missing section {name}")
    if "reviews" in sections and not isinstance(sections["reviews"], list):
        errors.append("sections.reviews must be an array")
    meta = state.get("section_meta")
    if not isinstance(meta, dict):
        errors.append("section_meta must be an object")
        meta = {}
    for name, owner in SECTION_OWNERS.items():
        item = meta.get(name)
        if not isinstance(item, dict):
            errors.append(f"missing section_meta.{name}")
            continue
        if item.get("owner_skill") != owner:
            errors.append(f"section_meta.{name}.owner_skill must be {owner}")
        if item.get("status") not in VALID_SECTION_STATUSES:
            errors.append(f"invalid section_meta.{name}.status")
        sr = item.get("section_revision")
        if sr is not None and (not isinstance(sr, int) or sr > state.get("revision", -1)):
            errors.append(f"section_meta.{name}.section_revision cannot exceed current revision")
    registry = state.get("id_registry", {})
    for prefix in ID_PREFIXES:
        if not isinstance(registry.get(prefix), int) or registry.get(prefix, -1) < 0:
            errors.append(f"id_registry.{prefix} must be a non-negative integer")
    # References repeat legitimately; only object identity keys participate in duplicate detection.
    identity_ids = collect_identity_ids({"sections": sections, "confirmation_events": state.get("confirmation_events", []), "invalidations": state.get("invalidations", [])})
    duplicates = sorted({identifier for identifier in identity_ids if identity_ids.count(identifier) > 1})
    errors.extend(f"duplicate identity id {identifier}" for identifier in duplicates)
    known = set(identity_ids) | {state.get("state_id")} | set(state.get("applied_patch_ids", []))
    for ref in collect_reference_values(sections):
        if ref not in known:
            errors.append(f"dangling reference {ref}")
    for identifier in identity_ids + list(state.get("applied_patch_ids", [])):
        match = ID_RE.match(identifier)
        if match and registry.get(match.group(1), 0) < int(match.group(2)):
            errors.append(f"id_registry is behind {identifier}")
    if len(state.get("applied_patch_ids", [])) != len(set(state.get("applied_patch_ids", []))):
        errors.append("applied_patch_ids contains duplicates")
    errors.extend(sections_errors(sections, state.get("section_meta", {})))
    errors.extend(forbidden_key_errors(state))
    return errors


def validate_patch(patch: Any, state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(patch, dict):
        return ["patch must be an object"]
    required = {"patch_id", "actor_skill", "skill_version", "base_revision", "operation", "changes", "referenced_ids", "requires_confirmation"}
    errors.extend(f"missing patch field {key}" for key in sorted(required - set(patch)))
    errors.extend(f"unknown patch field {key}" for key in sorted(set(patch) - PATCH_KEYS))
    match = ID_RE.match(str(patch.get("patch_id", "")))
    if not match or match.group(1) != "PAT":
        errors.append("patch_id must match PAT-000001")
    actor = patch.get("actor_skill")
    if actor not in WRITE_PREFIXES:
        errors.append(f"unknown actor_skill {actor!r}")
    if patch.get("operation") != "propose_patch":
        errors.append("operation must be propose_patch")
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", str(patch.get("skill_version", ""))):
        errors.append("skill_version must be semantic x.y.z")
    if patch.get("skill_version") not in ALLOWED_SKILL_VERSIONS:
        errors.append("skill_version must be 2.2.0; re-propose legacy patches with current revision and reconfirm; do not edit saved history")
    if patch.get("requires_confirmation") is not True:
        errors.append("requires_confirmation must be true")
    if patch.get("base_revision") != state.get("revision"):
        errors.append(f"stale base_revision {patch.get('base_revision')}; current revision is {state.get('revision')}")
    changes = patch.get("changes")
    if not isinstance(changes, list) or not changes:
        errors.append("changes must be a non-empty array")
        changes = []
    for index, change in enumerate(changes):
        if not isinstance(change, dict) or change.get("op") not in {"set", "append"} or not isinstance(change.get("path"), str):
            errors.append(f"invalid change at index {index}")
            continue
        allowed = WRITE_PREFIXES.get(actor, ())
        path = change["path"]
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in allowed):
            errors.append(f"actor {actor} cannot write {path}")
        if change.get("op") == "append" and "value" not in change:
            errors.append(f"append change {index} requires value")
        if change.get("op") == "set" and "value" not in change:
            errors.append(f"set change {index} requires value")
    intake = state.get("sections", {}).get("intake", {})
    profile = state.get("sections", {}).get("profile", {})
    path_decision = state.get("sections", {}).get("path_decision", {})
    cycle_plan = state.get("sections", {}).get("cycle_plan", {})
    if actor == "caplab-profile-confirmation" and not (
        intake.get("intake_ready") is True and intake.get("confirmation_status") == "confirmed"
    ):
        errors.append("profile confirmation requires confirmed, ready intake")
    if actor == "caplab-path-convergence" and not (
        profile.get("profile_ready") is True and profile.get("confirmation_status") == "confirmed"
    ):
        errors.append("path convergence requires confirmed, ready profile")
    if actor == "caplab-path-evidence-cycle" and not (
        path_decision.get("accepted") is True and path_decision.get("evidence_gaps")
    ):
        errors.append("evidence cycle requires an accepted path decision with an evidence gap")
    if actor == "caplab-evidence-review" and not (
        cycle_plan.get("review_ready") is True or cycle_plan.get("execution_records")
    ):
        errors.append("evidence review requires execution information or review_ready=true")
    if patch.get("patch_id") in state.get("applied_patch_ids", []):
        return errors
    known_ids = set(collect_identity_ids(state)) | {state.get("state_id")} | set(state.get("applied_patch_ids", []))
    replaceable_ids = set()
    for change in changes:
        if change.get("op") == "set":
            replaceable_ids.update(collect_identity_ids(pointer_value(state, change.get("path", ""))))
    identities = []
    for change in changes:
        identities.extend(collect_identity_ids(change.get("value")))
    duplicates = {
        identifier for identifier in identities
        if identities.count(identifier) > 1 or (identifier in known_ids and identifier not in replaceable_ids)
    }
    errors.extend(f"duplicate or reused id {identifier}" for identifier in sorted(duplicates))
    available = known_ids | set(identities)
    for ref in patch.get("referenced_ids", []):
        if ref not in available:
            errors.append(f"patch references unknown id {ref}")
    if actor in SECTION_OWNERS.values() and actor != SECTION_OWNERS["intake"]:
        if needs_candidates(intake):
            errors.append("candidate directions need confirmation through intake before formal progression")
        if intake_errors(intake, require_ready=True) or state["section_meta"]["intake"]["status"] == "stale":
            errors.append("formal stages require confirmed, ready intake and complete personal facts")
        order = list(SECTION_OWNERS)
        actor_section = next(k for k, v in SECTION_OWNERS.items() if v == actor)
        if any(state["section_meta"][k]["status"] == "stale" for k in order[:order.index(actor_section)]):
            errors.append("upstream stage is stale; return to earliest affected stage")
    errors.extend(forbidden_key_errors(patch))
    if not errors:
        try:
            projected = copy.deepcopy(state)
            for change in changes:
                apply_change(projected, change)
            changed = touched_sections(patch)
            invalidate_dependents(projected, changed, state["revision"], patch["patch_id"])
            for section in changed:
                projected["section_meta"][section]["status"] = section_status(section, projected["sections"][section])
            update_registry(projected, patch)
            errors.extend(validate_state(projected))
        except (CapLabError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            errors.append(f"invalid projected patch: {exc}")
    return errors


def parse_pointer(pointer: str) -> list[str]:
    if pointer == "/":
        return []
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.lstrip("/").split("/")]


def pointer_value(target: Any, pointer: str) -> Any:
    value = target
    for part in parse_pointer(pointer):
        if isinstance(value, list):
            if part == "-":
                return None
            value = value[int(part)]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def apply_change(target: Any, change: dict[str, Any]) -> None:
    parts = parse_pointer(change["path"])
    if not parts:
        raise CapLabError("root replacement is not allowed")
    parent = target
    for part in parts[:-1]:
        if isinstance(parent, list):
            parent = parent[int(part)]
        else:
            if part not in parent or parent[part] is None:
                parent[part] = {}
            parent = parent[part]
    leaf = parts[-1]
    value = copy.deepcopy(change.get("value"))
    if change["op"] == "set":
        if isinstance(parent, list):
            parent[int(leaf)] = value
        else:
            parent[leaf] = value
    elif change["op"] == "append":
        if isinstance(parent, list):
            if leaf == "-":
                parent.append(value)
            else:
                parent[int(leaf)].append(value)
        else:
            parent.setdefault(leaf, [])
            if not isinstance(parent[leaf], list):
                raise CapLabError(f"append target is not a list: {change['path']}")
            parent[leaf].append(value)


def touched_sections(patch: dict[str, Any]) -> set[str]:
    result = set()
    for change in patch["changes"]:
        parts = parse_pointer(change["path"])
        if len(parts) >= 2 and parts[0] == "sections" and parts[1] in SECTION_OWNERS:
            result.add(parts[1])
    return result


def section_status(section: str, data: Any) -> str:
    if not data:
        return "empty"
    if section == "intake":
        if data.get("confirmation_status") == "confirmed" and data.get("intake_ready") is True:
            return "confirmed"
        return "partial" if data.get("confirmation_status") == "partial" else "draft"
    if section == "profile":
        if data.get("confirmation_status") == "confirmed" and data.get("profile_ready") is True:
            return "confirmed"
        return "partial" if data.get("confirmation_status") == "partially_confirmed" else "draft"
    if section == "path_decision":
        return "accepted" if data.get("accepted") is True else "draft"
    if section == "cycle_plan":
        status = data.get("plan_status", "draft")
        return "active" if status in {"selected", "in_progress", "waiting"} else ("closed" if status == "stopped" else "draft")
    if section == "reviews":
        return "active" if data else "empty"
    return "draft"


def invalidate_dependents(state: dict[str, Any], changed: set[str], revision: int, patch_id: str) -> None:
    dependents: set[str] = set()
    for section in changed:
        dependents.update(SECTION_DEPENDENCIES[section])
    dependents -= changed
    for section in sorted(dependents):
        meta = state["section_meta"][section]
        if meta["status"] != "empty":
            previous = meta["status"]
            meta["status"] = "stale"
            invalidation_id = f"INV-{revision:06d}-{len(state['invalidations']) + 1:03d}"
            state["invalidations"].append({
                "invalidation_id": invalidation_id,
                "section": section,
                "previous_status": previous,
                "caused_by_patch_id": patch_id,
                "revision": revision,
                "recorded_at": now(),
            })


def update_registry(state: dict[str, Any], value: Any) -> None:
    for identifier in collect_ids(value):
        match = ID_RE.match(identifier)
        if match:
            state["id_registry"][match.group(1)] = max(state["id_registry"].get(match.group(1), 0), int(match.group(2)))


def save_revision(root: Path, state: dict[str, Any]) -> None:
    atomic_json(root / "history" / f"revision-{state['revision']:06d}.json", state)


def load_state(root: Path) -> dict[str, Any]:
    state = load_json(state_path(root))
    errors = validate_state(state)
    if errors:
        raise CapLabError("state validation failed:\n- " + "\n- ".join(errors))
    return state


def initialize_state(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = state_path(root)
    if path.exists() and not args.force:
        raise CapLabError(f"state already exists: {path}")
    state = empty_state()
    with state_lock(root):
        atomic_json(path, state)
        save_revision(root, state)
        for relative in ("audit/pending", "audit/confirmations"):
            (root / relative).mkdir(parents=True, exist_ok=True)
    print(f"INITIALIZED {path}")


def command_validate(args: argparse.Namespace) -> None:
    path = Path(args.state).resolve() if args.state else state_path(Path(args.root).resolve())
    errors = validate_state(load_json(path))
    if errors:
        raise CapLabError("\n".join(errors))
    print(f"VALID {path}")


def command_propose(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    require_ready(knowledge_workspace(root))
    state = load_state(root)
    patch = load_json(Path(args.patch))
    if patch.get("patch_id") in state["applied_patch_ids"]:
        print(f"ALREADY_APPLIED {patch['patch_id']} revision={state['revision']}")
        return
    errors = validate_patch(patch, state)
    if errors:
        raise CapLabError("patch validation failed:\n- " + "\n- ".join(errors))
    atomic_json(root / "audit" / "pending" / f"{patch['patch_id']}.json", patch)
    print(f"PROPOSED {patch['patch_id']} base_revision={patch['base_revision']}")
    print(patch.get("summary", "No summary supplied; inspect the exact patch before confirmation."))


def next_confirmation_id(state: dict[str, Any], root: Path) -> str:
    maximum = state["id_registry"].get("CFM", 0)
    for path in (root / "audit" / "confirmations").glob("CFM-*.json"):
        match = ID_RE.match(path.stem)
        if match:
            maximum = max(maximum, int(match.group(2)))
    return f"CFM-{maximum + 1:06d}"


def command_confirm(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    state = load_state(root)
    pending = root / "audit" / "pending" / f"{args.patch_id}.json"
    patch = load_json(pending)
    if patch.get("base_revision") != state["revision"] and patch["patch_id"] not in state["applied_patch_ids"]:
        raise CapLabError("cannot confirm a patch based on an old revision")
    confirmation_id = next_confirmation_id(state, root)
    event = {
        "confirmation_id": confirmation_id,
        "patch_id": args.patch_id,
        "decision": args.decision,
        "scope": patch.get("referenced_ids", []),
        "confirmation_text": args.text.strip(),
        "recorded_at": now(),
    }
    if not event["confirmation_text"]:
        raise CapLabError("confirmation text cannot be empty")
    atomic_json(root / "audit" / "confirmations" / f"{confirmation_id}.json", event)
    print(f"RECORDED {confirmation_id} decision={args.decision} patch={args.patch_id}")


def find_confirmation(root: Path, patch_id: str) -> dict[str, Any]:
    events = []
    for path in (root / "audit" / "confirmations").glob("CFM-*.json"):
        event = load_json(path)
        if event.get("patch_id") == patch_id:
            events.append(event)
    if not events:
        raise CapLabError(f"no confirmation event for {patch_id}")
    events.sort(key=lambda item: item["confirmation_id"])
    return events[-1]


def command_apply(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    require_ready(knowledge_workspace(root))
    with state_lock(root):
        state = load_state(root)
        if args.patch_id in state["applied_patch_ids"]:
            print(f"ALREADY_APPLIED {args.patch_id} revision={state['revision']}")
            return
        patch = load_json(root / "audit" / "pending" / f"{args.patch_id}.json")
        errors = validate_patch(patch, state)
        if errors:
            raise CapLabError("patch validation failed:\n- " + "\n- ".join(errors))
        event = find_confirmation(root, args.patch_id)
        if event["decision"] != "confirm":
            raise CapLabError(f"patch cannot apply after decision={event['decision']}; submit a revised patch")
        updated = copy.deepcopy(state)
        for change in patch["changes"]:
            apply_change(updated, change)
        new_revision = state["revision"] + 1
        changed = touched_sections(patch)
        invalidate_dependents(updated, changed, new_revision, args.patch_id)
        for section in changed:
            updated["section_meta"][section]["status"] = section_status(section, updated["sections"][section])
            updated["section_meta"][section]["section_revision"] = new_revision
        updated["parent_revision"] = state["revision"]
        updated["revision"] = new_revision
        updated["updated_at"] = now()
        updated["confirmation_events"].append(event)
        updated["applied_patch_ids"].append(args.patch_id)
        update_registry(updated, {"patch_id": args.patch_id, "confirmation": event, "changes": patch["changes"]})
        updated["active_stage"] = route_for(updated)[0]
        errors = validate_state(updated)
        if errors:
            raise CapLabError("resulting state is invalid:\n- " + "\n- ".join(errors))
        atomic_json(state_path(root), updated)
        save_revision(root, updated)
    print(f"APPLIED {args.patch_id} revision={new_revision}")


def needs_candidates(intake: dict[str, Any]) -> bool:
    return intake.get("candidate_generation_needed") is True or intake.get("candidate_paths") == []


def auxiliary_for(state: dict[str, Any]) -> str | None:
    intake = state["sections"]["intake"]
    if (state["workflow_status"] not in {"blocked", "invalid"}
            and state["section_meta"]["intake"]["status"] != "stale"
            and not intake_errors(intake, require_ready=True) and needs_candidates(intake)):
        return "caplab-cold-start"
    return None


def route_for(state: dict[str, Any]) -> tuple[str, str]:
    if state["workflow_status"] in {"blocked", "invalid"}:
        return "blocked", "workflow is blocked or invalid"
    if intake_errors(state["sections"]["intake"], require_ready=True):
        return "profile_intake", "personal facts or key timepoints are missing/unconfirmed"
    if needs_candidates(state["sections"]["intake"]):
        return "profile_intake", "candidate directions need cold-start exploration and intake confirmation"
    for section, stage in (
        ("intake", "profile_intake"),
        ("profile", "profile_confirmation"),
        ("path_decision", "path_convergence"),
        ("cycle_plan", "path_evidence_cycle"),
    ):
        if state["section_meta"][section]["status"] == "stale":
            return stage, f"{section} or its dependency is stale"
    intake = state["sections"]["intake"]
    if not (intake.get("intake_ready") is True and intake.get("confirmation_status") == "confirmed"):
        return "profile_intake", "intake is not confirmed and ready"
    profile = state["sections"]["profile"]
    if not (profile.get("profile_ready") is True and profile.get("confirmation_status") == "confirmed"):
        return "profile_confirmation", "profile is not confirmed and ready"
    path = state["sections"]["path_decision"]
    if path.get("accepted") is not True:
        return "path_convergence", "path decision is not accepted"
    cycle = state["sections"]["cycle_plan"]
    if not cycle or cycle.get("plan_status") == "draft":
        return "path_evidence_cycle", "evidence cycle has not been selected"
    if cycle.get("review_ready") is True or cycle.get("execution_records"):
        return "evidence_review", "new execution information is ready for review"
    if cycle.get("plan_status") in {"selected", "in_progress", "waiting"}:
        return "path_evidence_cycle", "cycle is selected, in progress, or waiting"
    return "closed", "no further route is required"


def command_route(args: argparse.Namespace) -> None:
    require_ready(knowledge_workspace(Path(args.root).resolve()))
    state = load_state(Path(args.root).resolve())
    stage, reason = route_for(state)
    print(json.dumps({"active_stage": stage, "auxiliary_route": auxiliary_for(state), "reason": reason, "revision": state["revision"]}, ensure_ascii=False))


def command_rollback(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    with state_lock(root):
        current = load_state(root)
        if args.revision < 0 or args.revision > current["revision"]:
            raise CapLabError("rollback revision is outside available history")
        target = load_json(root / "history" / f"revision-{args.revision:06d}.json")
        if target.get("schema_version") == "1.0.0":
            target = downgrade_legacy(target)
        target_errors = validate_state(target)
        if target_errors:
            raise CapLabError("target history snapshot is invalid")
        updated = copy.deepcopy(target)
        new_revision = current["revision"] + 1
        confirmation_id = f"CFM-{current['id_registry'].get('CFM', 0) + 1:06d}"
        event = {
            "confirmation_id": confirmation_id,
            "patch_id": f"PAT-{current['id_registry'].get('PAT', 0) + 1:06d}",
            "decision": "confirm",
            "scope": [f"revision-{args.revision:06d}"],
            "confirmation_text": args.text.strip(),
            "recorded_at": now(),
        }
        if not event["confirmation_text"]:
            raise CapLabError("rollback confirmation text cannot be empty")
        updated["revision"] = new_revision
        updated["parent_revision"] = current["revision"]
        updated["rollback_of"] = args.revision
        updated["updated_at"] = now()
        updated["id_registry"] = copy.deepcopy(current["id_registry"])
        updated["confirmation_events"] = copy.deepcopy(current["confirmation_events"]) + [event]
        updated["applied_patch_ids"] = copy.deepcopy(current["applied_patch_ids"])
        update_registry(updated, event)
        updated["active_stage"] = route_for(updated)[0]
        errors = validate_state(updated)
        if errors:
            raise CapLabError("rollback result invalid:\n- " + "\n- ".join(errors))
        atomic_json(state_path(root), updated)
        save_revision(root, updated)
    print(f"ROLLED_BACK target={args.revision} new_revision={new_revision}")


def unwrap_legacy(value: dict[str, Any], key: str) -> dict[str, Any]:
    if key in value and isinstance(value[key], dict):
        return value[key]
    return value


def command_migrate(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    if state_path(root).exists() and not args.force:
        raise CapLabError("target state exists; use --force only after preserving it")
    state = empty_state()
    mappings = {
        "intake": (args.intake, "intake"),
        "profile": (args.profile, "profile"),
        "path_decision": (args.path_decision, "path_decision"),
        "cycle_plan": (args.cycle_plan, "cycle_plan"),
    }
    for section, (source, legacy_key) in mappings.items():
        if source:
            value = unwrap_legacy(load_json(Path(source)), legacy_key)
            state["sections"][section] = value
            state["section_meta"][section]["status"] = section_status(section, value)
            state["section_meta"][section]["section_revision"] = 1
    if args.review:
        value = unwrap_legacy(load_json(Path(args.review)), "review")
        state["sections"]["reviews"] = [value]
        state["section_meta"]["reviews"]["status"] = "active"
        state["section_meta"]["reviews"]["section_revision"] = 1
    state["revision"] = 1
    state["parent_revision"] = 0
    state["updated_at"] = now()
    update_registry(state, state["sections"])
    state = downgrade_legacy(state)
    errors = validate_state(state)
    if errors:
        raise CapLabError("migration result invalid:\n- " + "\n- ".join(errors))
    root.mkdir(parents=True, exist_ok=True)
    with state_lock(root):
        atomic_json(state_path(root), state)
        save_revision(root, state)
    print(f"MIGRATED {state_path(root)} revision=1; original facts retained; schema 1.1.0 intake reconfirmation required")


def command_bootstrap(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    if state_path(root).exists():
        old = load_json(state_path(root))
        if old.get("schema_version") != SCHEMA_VERSION:
            raise CapLabError("legacy state requires explicit upgrade-state --text before bootstrap")
        load_state(root)
    report = ensure_knowledge(knowledge_workspace(root), args.seed, args.allow_temporary)
    if not state_path(root).exists():
        with context_stdout():
            initialize_state(argparse.Namespace(root=str(root), force=False))
    state = load_state(root)
    print(json.dumps({**report, "schema_version": SCHEMA_VERSION, "revision": state["revision"],
                      "active_stage": route_for(state)[0]}, ensure_ascii=False, indent=2))


@contextmanager
def context_stdout():
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def command_upgrade(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    if not args.text.strip():
        raise CapLabError("migration requires explicit confirmation text")
    with state_lock(root):
        old = load_json(state_path(root))
        if old.get("schema_version") == SCHEMA_VERSION:
            load_state(root)
            print("ALREADY_UPGRADED")
            return
        if old.get("schema_version") != "1.0.0":
            raise CapLabError("only schema 1.0.0 can be upgraded")
        updated = downgrade_legacy(old)
        updated["revision"] = old["revision"] + 1
        updated["parent_revision"] = old["revision"]
        updated["updated_at"] = now()
        updated["section_meta"]["intake"]["section_revision"] = updated["revision"]
        event = {"confirmation_id": next_confirmation_id(old, root),
                 "patch_id": f"PAT-{old['id_registry']['PAT'] + 1:06d}", "decision": "confirm",
                 "scope": ["schema-1.0.0-to-1.1.0"], "confirmation_text": args.text.strip(), "recorded_at": now()}
        updated["confirmation_events"].append(event)
        updated["applied_patch_ids"].append(event["patch_id"])
        update_registry(updated, event)
        errors = validate_state(updated)
        if errors:
            raise CapLabError("migration blocked: " + "; ".join(errors))
        backup = root / "audit" / "migrations" / f"schema-1.0.0-revision-{old['revision']:06d}.json"
        if backup.exists() and load_json(backup) != old:
            raise CapLabError("migration backup already exists with different content")
        atomic_json(backup, old)
        history = root / "history" / f"revision-{old['revision']:06d}.json"
        if not history.exists():
            atomic_json(history, old)
        atomic_json(state_path(root), updated)
        save_revision(root, updated)
    print(f"UPGRADED schema=1.1.0 revision={updated['revision']}; personal facts require confirmation")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="caplab_state", description="CapLab state protocol runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("bootstrap", "init"):
        p = sub.add_parser(command); p.add_argument("--root", required=True); p.add_argument("--seed"); p.add_argument("--allow-temporary", action="store_true"); p.set_defaults(func=command_bootstrap)
    p = sub.add_parser("upgrade-state"); p.add_argument("--root", required=True); p.add_argument("--text", required=True); p.set_defaults(func=command_upgrade)
    p = sub.add_parser("validate"); p.add_argument("--root"); p.add_argument("--state"); p.set_defaults(func=command_validate)
    p = sub.add_parser("propose"); p.add_argument("--root", required=True); p.add_argument("--patch", required=True); p.set_defaults(func=command_propose)
    p = sub.add_parser("confirm"); p.add_argument("--root", required=True); p.add_argument("--patch-id", required=True); p.add_argument("--decision", required=True, choices=("confirm", "partial", "revise", "reject")); p.add_argument("--text", required=True); p.set_defaults(func=command_confirm)
    p = sub.add_parser("apply"); p.add_argument("--root", required=True); p.add_argument("--patch-id", required=True); p.set_defaults(func=command_apply)
    p = sub.add_parser("rollback"); p.add_argument("--root", required=True); p.add_argument("--revision", required=True, type=int); p.add_argument("--text", required=True); p.set_defaults(func=command_rollback)
    p = sub.add_parser("route"); p.add_argument("--root", required=True); p.set_defaults(func=command_route)
    p = sub.add_parser("migrate"); p.add_argument("--root", required=True); p.add_argument("--intake"); p.add_argument("--profile"); p.add_argument("--path-decision"); p.add_argument("--cycle-plan"); p.add_argument("--review"); p.add_argument("--force", action="store_true"); p.set_defaults(func=command_migrate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "validate" and not args.root and not args.state:
        print("ERROR: validate requires --root or --state", file=sys.stderr)
        return 2
    try:
        args.func(args)
        return 0
    except (CapLabError, BootstrapError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
