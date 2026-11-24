"""CapLab ID 体系与常量。

基线：caplab-workflow-orchestrator v2.1.1 / state schema 1.1.0。
所有常量与原 scripts/caplab_state.py 保持一致，避免协议漂移。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

SCHEMA_VERSION = "1.1.0"
SKILL_VERSION = "2.1.1"
ALLOWED_SKILL_VERSIONS = frozenset({SKILL_VERSION})

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

STAGE_TO_ACTOR = {
    "profile_intake": "caplab-profile-intake",
    "profile_confirmation": "caplab-profile-confirmation",
    "path_convergence": "caplab-path-convergence",
    "path_evidence_cycle": "caplab-path-evidence-cycle",
    "evidence_review": "caplab-evidence-review",
}

# 每个 actor 唯一可写路径前缀
WRITE_PREFIXES = {
    "caplab-profile-intake": ("/sections/intake",),
    "caplab-profile-confirmation": ("/sections/profile",),
    "caplab-path-convergence": ("/sections/path_decision",),
    "caplab-path-evidence-cycle": ("/sections/cycle_plan",),
    "caplab-evidence-review": ("/sections/reviews",),
    "caplab-workflow-orchestrator": ("/active_stage", "/workflow_status", "/invalidations"),
}

# 早期区变更时，下游区被标记为 stale
SECTION_DEPENDENCIES = {
    "intake": ("profile", "path_decision", "cycle_plan", "reviews"),
    "profile": ("path_decision", "cycle_plan", "reviews"),
    "path_decision": ("cycle_plan", "reviews"),
    "cycle_plan": ("reviews",),
    "reviews": (),
}

FORBIDDEN_KEYS = frozenset({
    "fit_score", "success_probability", "career_probability",
    "bank_card_number", "identity_card_number",
})
VALID_SECTION_STATUSES = frozenset({
    "empty", "draft", "confirmed", "accepted", "active", "partial", "stale", "closed",
})
VALID_WORKFLOW_STATUSES = frozenset({
    "active", "waiting_confirmation", "paused", "closed", "blocked", "invalid",
})
PATCH_KEYS = frozenset({
    "patch_id", "actor_skill", "skill_version", "base_revision", "operation",
    "changes", "referenced_ids", "requires_confirmation", "summary",
})
STATE_KEYS = frozenset({
    "schema_version", "state_id", "revision", "parent_revision", "active_stage",
    "workflow_status", "sections", "section_meta", "id_registry",
    "confirmation_events", "invalidations", "applied_patch_ids", "rollback_of", "updated_at",
})


def now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def next_id(state: dict, prefix: str) -> str:
    """基于 id_registry 生成下一个全局唯一 ID（原子性由调用方的事务保证）。"""
    if prefix not in ID_PREFIXES:
        raise ValueError(f"unknown id prefix: {prefix}")
    value = int(state.get("id_registry", {}).get(prefix, 0)) + 1
    state.setdefault("id_registry", {})[prefix] = value
    return f"{prefix}-{value:06d}"


def parse_pointer(pointer: str) -> list[str]:
    if pointer == "/":
        return []
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.lstrip("/").split("/")]


def pointer_value(target, pointer: str):
    value = target
    for part in parse_pointer(pointer):
        if isinstance(value, list):
            if part == "-":
                return None
            try:
                value = value[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value
