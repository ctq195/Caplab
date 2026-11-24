"""离线验证：补丁协议、路由、确认门、回退、会话隔离、权限分层。

这些是本适配的核心确定性逻辑，必须代码化通过，不能依赖 LLM 声明。
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.caplab.persistence.repository import InMemoryRepository, build_repository  # noqa: E402
from src.caplab.protocol.ids import SKILL_VERSION  # noqa: E402
from src.caplab.protocol.patch import (  # noqa: E402
    PatchError, apply_confirmed, empty_state, propose, rollback, route_for, validate_patch,
)
from src.caplab.session.access import (  # noqa: E402
    MemoryEntitlement, assert_paid_allowed, exact_vip_command, resolve_tier,
)

TEMPLATES = ROOT / "assets" / "templates"


@pytest.fixture
def state():
    return empty_state(TEMPLATES)


def test_empty_state_valid(state):
    from src.caplab.protocol.schema_validation import validate_state
    assert validate_state(state) == []
    assert state["revision"] == 0
    assert state["active_stage"] == "profile_intake"


def test_route_starts_at_intake(state):
    stage, _ = route_for(state)
    assert stage == "profile_intake"


def test_propose_rejects_cross_section_write(state):
    patch = {
        "patch_id": "PAT-000001", "actor_skill": "caplab-profile-intake",
        "skill_version": SKILL_VERSION, "base_revision": 0,
        "operation": "propose_patch",
        "changes": [{"op": "set", "path": "/sections/profile", "value": {"x": 1}}],
        "referenced_ids": [], "requires_confirmation": True, "summary": "越权写入",
    }
    errors = validate_patch(patch, state)
    assert any("cannot write" in e for e in errors)


def test_propose_rejects_stale_revision(state):
    patch = {
        "patch_id": "PAT-000001", "actor_skill": "caplab-profile-intake",
        "skill_version": SKILL_VERSION, "base_revision": 99,
        "operation": "propose_patch",
        "changes": [{"op": "set", "path": "/sections/intake/decision_question", "value": "测试问题"}],
        "referenced_ids": [], "requires_confirmation": True, "summary": "过期修订",
    }
    errors = validate_patch(patch, state)
    assert any("stale base_revision" in e for e in errors)


def test_propose_rejects_forbidden_key(state):
    patch = {
        "patch_id": "PAT-000001", "actor_skill": "caplab-profile-intake",
        "skill_version": SKILL_VERSION, "base_revision": 0,
        "operation": "propose_patch",
        "changes": [{"op": "set", "path": "/sections/intake/decision_question",
                     "value": {"text": "x", "fit_score": 0.9}}],
        "referenced_ids": [], "requires_confirmation": True, "summary": "禁止字段",
    }
    assert any("forbidden" in e for e in validate_patch(patch, state))


def valid_intake_patch(state) -> dict:
    return {
        "patch_id": "PAT-000001", "actor_skill": "caplab-profile-intake",
        "skill_version": SKILL_VERSION, "base_revision": state["revision"],
        "operation": "propose_patch",
        "changes": [{"op": "set", "path": "/sections/intake/decision_question",
                     "value": "毕业后做测试开发还是读研"}],
        "referenced_ids": [], "requires_confirmation": True,
        "summary": "记录决策问题",
    }


def test_propose_preview_does_not_mutate(state):
    original = copy.deepcopy(state)
    patch = valid_intake_patch(state)
    preview = propose(patch, state)
    assert preview["patch_id"] == "PAT-000001"
    assert state == original
    assert preview["preview"]["sections"]["intake"]["decision_question"] == "毕业后做测试开发还是读研"


def test_apply_requires_explicit_confirmation_text(state):
    patch = valid_intake_patch(state)
    with pytest.raises(PatchError) as exc:
        apply_confirmed(state, patch, "confirm", "")
    assert any("silence is not confirmation" in e for e in exc.value.errors)


def test_apply_creates_new_revision_and_audit(state):
    patch = valid_intake_patch(state)
    updated = apply_confirmed(state, patch, "confirm", "我确认这个决策问题")
    assert updated["revision"] == 1
    assert updated["parent_revision"] == 0
    assert updated["applied_patch_ids"] == ["PAT-000001"]
    assert len(updated["confirmation_events"]) == 1
    assert updated["confirmation_events"][0]["decision"] == "confirm"


def test_reject_does_not_change_revision_but_keeps_audit(state):
    patch = valid_intake_patch(state)
    updated = apply_confirmed(state, patch, "reject", "我不同意这个补丁")
    assert updated["revision"] == 0
    assert updated["sections"]["intake"]["decision_question"] is None
    assert updated["confirmation_events"][0]["decision"] == "reject"


def test_rollback_creates_new_revision_without_deleting_history(state):
    patch = valid_intake_patch(state)
    applied = apply_confirmed(state, patch, "confirm", "确认")
    snapshot = repo_snapshot(applied)
    rolled = rollback(applied, 0, snapshot, "我明确同意回到 revision 0")
    assert rolled["revision"] == 2
    assert rolled["rollback_of"] == 0
    assert rolled["applied_patch_ids"] == ["PAT-000001"]


def repo_snapshot(applied):
    return empty_state(TEMPLATES)


def test_repository_session_isolation():
    repo: InMemoryRepository = build_repository()
    a = repo.load("session-A", "user-1")
    b = repo.load("session-B", "user-1")
    c = repo.load("session-A", "user-2")
    a["revision"] = 7
    repo.save("session-A", "user-1", a)
    # 用合法 revision 保存以避免校验失败，这里只验证 key 隔离
    assert repo.list_sessions("user-1") == ["session-A", "session-B"]
    assert repo.list_sessions("user-2") == ["session-A"]
    assert b["revision"] == 0 and c["revision"] == 0


def test_tier_never_trusts_client_payload():
    store = MemoryEntitlement()
    assert resolve_tier("我想看付费知识", store, "u1", demo_switch=False) == "free"
    assert exact_vip_command(" ICANDumate_VIP:enabled") is None
    assert exact_vip_command("ICANDumate_VIP:enabled ") is None
    assert exact_vip_command("ICANDumate_VIP:enabled") == "paid"
    assert resolve_tier("ICANDumate_VIP:enabled", store, "u1", demo_switch=False) == "free"
    assert resolve_tier("ICANDumate_VIP:enabled", store, "u1", demo_switch=True) == "paid"
    with pytest.raises(PermissionError):
        assert_paid_allowed("free", "paid")


def test_output_guard_rejects_definite_attribution():
    from src.caplab.graph.nodes.orchestrator import _guard_reply
    assert _guard_reply("你的真实动机就是逃避") 
    assert _guard_reply("这不妨碍你现在就拿它去投递")
    assert _guard_reply("从你的描述看，害怕失败可能是因素之一") == []
