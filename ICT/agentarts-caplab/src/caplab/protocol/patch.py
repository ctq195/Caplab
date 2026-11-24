"""补丁协议：propose / confirm / apply / rollback 的确定性校验内核。

从 Skill scripts/caplab_state.py 迁移，改为纯函数 + 状态对象，便于在
LangGraph 节点与持久化仓储中复用。所有校验保留代码化，不交给 LLM。
"""
from __future__ import annotations

import copy
from typing import Any

from .ids import (
    ALLOWED_SKILL_VERSIONS, ID_RE, PATCH_KEYS, SECTION_DEPENDENCIES,
    SECTION_OWNERS, WRITE_PREFIXES, next_id, now, parse_pointer, pointer_value,
)
from .schema_validation import forbidden_key_errors, validate_state

STAGE_ORDER = list(SECTION_OWNERS)


class PatchError(ValueError):
    """补丁校验失败，携带错误列表供上层展示。"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def empty_state(template_dir) -> dict[str, Any]:
    import json
    from pathlib import Path

    intake = json.loads((Path(template_dir) / "intake-draft.json").read_text(encoding="utf-8"))
    return {
        "schema_version": "1.1.0",
        "state_id": "CAP-000001",
        "revision": 0,
        "parent_revision": None,
        "active_stage": "profile_intake",
        "workflow_status": "active",
        "sections": {
            "intake": intake, "profile": {}, "path_decision": {},
            "cycle_plan": {}, "reviews": [],
        },
        "section_meta": {
            name: {"status": "empty", "section_revision": 0, "owner_skill": owner}
            for name, owner in SECTION_OWNERS.items()
        },
        "id_registry": {p: (1 if p == "CAP" else 0) for p in
                        ("CAP", "SRC", "INT", "PRO", "HYP", "PTH", "GAP", "CYC", "OBS", "REV", "CFM", "PAT")},
        "confirmation_events": [],
        "invalidations": [],
        "applied_patch_ids": [],
        "rollback_of": None,
        "updated_at": now(),
    }


def apply_change(target: Any, change: dict[str, Any]) -> None:
    parts = parse_pointer(change["path"])
    if not parts:
        if change.get("op") != "set":
            raise PatchError(["root change must use set"])
        target.clear()
        target.update(copy.deepcopy(change["value"]))
        return
    parent = target
    for part in parts[:-1]:
        if isinstance(parent, list):
            parent = parent[int(part)]
        else:
            if part not in parent or not isinstance(parent[part], (dict, list)):
                parent[part] = {}
            parent = parent[part]
    key = parts[-1]
    if isinstance(parent, list):
        if change["op"] == "append" or key == "-":
            parent.append(copy.deepcopy(change["value"]))
        else:
            parent[int(key)] = copy.deepcopy(change["value"])
    else:
        if change["op"] == "append":
            parent.setdefault(key, [])
            if not isinstance(parent[key], list):
                raise PatchError([f"append target {change['path']} is not an array"])
            parent[key].append(copy.deepcopy(change["value"]))
        else:
            parent[key] = copy.deepcopy(change["value"])


def collect_identity_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        if ID_RE.match(value):
            found.add(value)
    elif isinstance(value, dict):
        for sub in value.values():
            found |= collect_identity_ids(sub)
    elif isinstance(value, list):
        for sub in value:
            found |= collect_identity_ids(sub)
    return found


def touched_sections(patch: dict[str, Any]) -> set[str]:
    changed: set[str] = set()
    for change in patch.get("changes", []):
        parts = parse_pointer(change.get("path", ""))
        if len(parts) >= 2 and parts[0] == "sections" and parts[1] in SECTION_OWNERS:
            changed.add(parts[1])
    return changed


def _section_status(section: str, value: Any) -> str:
    if not value or (isinstance(value, dict) and not value):
        return "empty"
    if isinstance(value, list):
        return "active" if value else "empty"
    if isinstance(value, dict):
        if section in ("intake", "profile"):
            if value.get("confirmation_status") == "confirmed" and value.get(f"{'intake' if section == 'intake' else 'profile'}_ready") is True:
                return "confirmed"
        if section == "path_decision" and value.get("accepted") is True:
            return "accepted"
        return "draft"
    return "draft"


def invalidate_dependents(state: dict, changed: set[str], revision: int, patch_id: str) -> None:
    for section in changed:
        for dependent in SECTION_DEPENDENCIES.get(section, ()):
            meta = state["section_meta"].get(dependent)
            if meta and meta.get("status") in {"confirmed", "accepted", "active", "partial"}:
                meta["status"] = "stale"
                state.setdefault("invalidations", []).append({
                    "section": dependent,
                    "caused_by_patch": patch_id,
                    "caused_by_section": section,
                    "at_revision": revision,
                })


def _needs_candidates(intake: dict) -> bool:
    return bool(intake.get("candidate_generation_needed")) and not intake.get("candidate_paths")


def _intake_errors(intake: dict, require_ready: bool = False) -> list[str]:
    errors: list[str] = []
    if not intake.get("decision_question"):
        errors.append("decision_question missing")
    if not intake.get("major", {}).get("name"):
        errors.append("major name unconfirmed")
    facts = intake.get("personal_facts", {})
    for key in ("education_level", "institution_name", "enrollment_year", "graduation_year"):
        if not facts.get(key, {}).get("value"):
            errors.append(f"personal_facts.{key} unconfirmed")
    if not facts.get("key_timepoints", {}).get("events"):
        errors.append("key_timepoints missing")
    if require_ready and not (intake.get("intake_ready") is True and intake.get("confirmation_status") == "confirmed"):
        errors.append("intake not confirmed and ready")
    return errors


def route_for(state: dict[str, Any]) -> tuple[str, str]:
    """与 Skill route_for 一致的五阶段准入路由。"""
    if state["workflow_status"] in {"blocked", "invalid"}:
        return "blocked", "workflow is blocked or invalid"
    if _intake_errors(state["sections"]["intake"], require_ready=True):
        return "profile_intake", "personal facts or key timepoints are missing/unconfirmed"
    if _needs_candidates(state["sections"]["intake"]):
        return "profile_intake", "candidate directions need cold-start exploration and intake confirmation"
    for section, stage in (
        ("intake", "profile_intake"), ("profile", "profile_confirmation"),
        ("path_decision", "path_convergence"), ("cycle_plan", "path_evidence_cycle"),
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


def validate_patch(patch: Any, state: dict[str, Any]) -> list[str]:
    """propose 硬校验：权限、revision、ID、引用、禁止字段、业务准入。"""
    errors: list[str] = []
    if not isinstance(patch, dict):
        return ["patch must be an object"]
    required = {"patch_id", "actor_skill", "skill_version", "base_revision",
                "operation", "changes", "referenced_ids", "requires_confirmation"}
    errors.extend(f"missing patch field {k}" for k in sorted(required - set(patch)))
    errors.extend(f"unknown patch field {k}" for k in sorted(set(patch) - PATCH_KEYS))
    match = ID_RE.match(str(patch.get("patch_id", "")))
    if not match or match.group(1) != "PAT":
        errors.append("patch_id must match PAT-000001")
    actor = patch.get("actor_skill")
    if actor not in WRITE_PREFIXES:
        errors.append(f"unknown actor_skill {actor!r}")
    if patch.get("operation") != "propose_patch":
        errors.append("operation must be propose_patch")
    if patch.get("skill_version") not in ALLOWED_SKILL_VERSIONS:
        errors.append("skill_version must be 2.1.1; re-propose legacy patches and reconfirm")
    if patch.get("requires_confirmation") is not True:
        errors.append("requires_confirmation must be true")
    if patch.get("base_revision") != state.get("revision"):
        errors.append(f"stale base_revision {patch.get('base_revision')}; current revision is {state.get('revision')}")

    changes = patch.get("changes")
    if not isinstance(changes, list) or not changes:
        errors.append("changes must be a non-empty array")
        changes = []
    for i, change in enumerate(changes):
        if not isinstance(change, dict) or change.get("op") not in {"set", "append"} or not isinstance(change.get("path"), str):
            errors.append(f"invalid change at index {i}")
            continue
        allowed = WRITE_PREFIXES.get(actor, ())
        path = change["path"]
        if not any(path == p or path.startswith(p + "/") for p in allowed):
            errors.append(f"actor {actor} cannot write {path}")
        if "value" not in change:
            errors.append(f"change {i} requires value")

    intake = state["sections"]["intake"]
    profile = state["sections"]["profile"]
    path_decision = state["sections"]["path_decision"]
    cycle_plan = state["sections"]["cycle_plan"]
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
        errors.append("patch_id already applied")
    known_ids = set(collect_identity_ids(state)) | {state["state_id"]} | set(state["applied_patch_ids"])
    replaceable_ids: set[str] = set()
    for change in changes:
        if change.get("op") == "set":
            replaceable_ids |= collect_identity_ids(pointer_value(state, change.get("path", "")))
    identities: list[str] = []
    for change in changes:
        identities.extend(collect_identity_ids(change.get("value")))
    duplicates = {
        ident for ident in identities
        if identities.count(ident) > 1 or (ident in known_ids and ident not in replaceable_ids)
    }
    errors.extend(f"duplicate or reused id {ident}" for ident in sorted(duplicates))
    available = known_ids | set(identities)
    for ref in patch.get("referenced_ids", []):
        if ref not in available:
            errors.append(f"patch references unknown id {ref}")

    if actor in SECTION_OWNERS.values() and actor != SECTION_OWNERS["intake"]:
        if _needs_candidates(intake):
            errors.append("candidate directions need confirmation through intake before formal progression")
        if _intake_errors(intake, require_ready=True) or state["section_meta"]["intake"]["status"] == "stale":
            errors.append("formal stages require confirmed, ready intake and complete personal facts")
        actor_section = next(k for k, v in SECTION_OWNERS.items() if v == actor)
        if any(state["section_meta"][k]["status"] == "stale" for k in STAGE_ORDER[:STAGE_ORDER.index(actor_section)]):
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
                projected["section_meta"][section]["status"] = _section_status(section, projected["sections"][section])
            projected["applied_patch_ids"] = list(state["applied_patch_ids"]) + [patch["patch_id"]]
            errors.extend(validate_state(projected))
        except Exception as exc:  # noqa: BLE001 - 原实现同样兜底所有投影异常
            errors.append(f"invalid projected patch: {exc}")
    return errors


def propose(patch: dict, state: dict) -> dict:
    errors = validate_patch(patch, state)
    if errors:
        raise PatchError(errors)
    preview = copy.deepcopy(state)
    for change in patch["changes"]:
        apply_change(preview, change)
    return {
        "patch_id": patch["patch_id"],
        "base_revision": state["revision"],
        "summary": patch.get("summary", ""),
        "affected_sections": sorted(touched_sections(patch)),
        "preview": preview,
    }


CONFIRM_DECISIONS = {"confirm", "partial", "revise", "reject"}


def apply_confirmed(state: dict, patch: dict, decision: str, text: str,
                    scope: list[str] | None = None) -> dict:
    """在用户明确确认后原子应用补丁，返回新状态（调用方负责事务提交）。"""
    if decision not in CONFIRM_DECISIONS:
        raise PatchError([f"decision must be one of {sorted(CONFIRM_DECISIONS)}"])
    if not text or not text.strip():
        raise PatchError(["confirmation text must not be empty; silence is not confirmation"])
    errors = validate_patch(patch, state)
    if errors:
        raise PatchError(errors)
    next_state = copy.deepcopy(state)
    if decision == "reject":
        event = {
            "confirmation_id": next_id(next_state, "CFM"),
            "patch_id": patch["patch_id"],
            "decision": "reject",
            "scope": scope or sorted(touched_sections(patch)),
            "confirmation_text": text.strip(),
            "recorded_at": now(),
        }
        next_state["confirmation_events"].append(event)
        return next_state

    changes = patch["changes"]
    if decision == "partial":
        allowed = set(scope or [])
        if not allowed:
            raise PatchError(["partial confirmation requires an explicit scope"])
        changes = [c for c in changes if any(
            parse_pointer(c["path"])[:len(parse_pointer(s))] == parse_pointer(s)
            for s in allowed
        )]
        if not changes:
            raise PatchError(["partial confirmation scope matches no change"])

    for change in changes:
        apply_change(next_state, change)
    changed = {p[1] for c in changes if len(p := parse_pointer(c["path"])) >= 2 and p[0] == "sections" and p[1] in SECTION_OWNERS}
    invalidate_dependents(next_state, changed, state["revision"], patch["patch_id"])
    for section in changed:
        next_state["section_meta"][section]["status"] = _section_status(section, next_state["sections"][section])

    new_revision = state["revision"] + 1
    next_state["revision"] = new_revision
    next_state["parent_revision"] = state["revision"]
    next_state["applied_patch_ids"] = list(state["applied_patch_ids"]) + [patch["patch_id"]]
    next_state["confirmation_events"].append({
        "confirmation_id": next_id(next_state, "CFM"),
        "patch_id": patch["patch_id"],
        "decision": decision,
        "scope": scope or sorted(changed),
        "confirmation_text": text.strip(),
        "recorded_at": now(),
    })
    next_state["updated_at"] = now()
    next_state["active_stage"], _ = route_for(next_state)
    errors = validate_state(next_state)
    if errors:
        raise PatchError(errors)
    return next_state


def rollback(state: dict, target_revision: int, snapshot: dict, text: str) -> dict:
    """非破坏性回退：恢复目标快照数据，保留 ID 注册表与确认历史，生成新 revision。"""
    if not text or not text.strip():
        raise PatchError(["rollback confirmation text must not be empty"])
    if target_revision < 0 or target_revision > state["revision"]:
        raise PatchError(["rollback revision is outside available history"])
    errors = validate_state(snapshot)
    if errors:
        raise PatchError([f"target history snapshot is invalid: {e}" for e in errors])
    next_state = copy.deepcopy(snapshot)
    new_revision = state["revision"] + 1
    next_state["revision"] = new_revision
    next_state["parent_revision"] = state["revision"]
    next_state["rollback_of"] = target_revision
    next_state["updated_at"] = now()
    next_state["id_registry"] = copy.deepcopy(state["id_registry"])
    next_state["confirmation_events"] = copy.deepcopy(state["confirmation_events"]) + [{
        "confirmation_id": next_id(next_state, "CFM"),
        "patch_id": next_id(next_state, "PAT"),
        "decision": "confirm",
        "scope": [f"revision-{target_revision:06d}"],
        "confirmation_text": text.strip(),
        "recorded_at": now(),
    }]
    next_state["applied_patch_ids"] = copy.deepcopy(state["applied_patch_ids"])
    next_state["active_stage"], _ = route_for(next_state)
    errors = validate_state(next_state)
    if errors:
        raise PatchError(errors)
    return next_state
