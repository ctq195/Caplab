"""LangGraph 图状态定义。

对齐 Skill 五阶段协议：图状态承载业务 state + 当前轮次的提议补丁与
确认决定。业务事实只在 confirm/apply 后写入，模型不能自行声明已确认。
"""
from __future__ import annotations

from typing import Any, TypedDict


class TurnResolution(TypedDict, total=False):
    base_revision: int
    response: str
    handled_intents: dict[str, str]
    deferred_intents: dict[str, str]
    commitment_updates: dict[str, Any]


class GraphState(TypedDict, total=False):
    # ---- 平台注入 ----
    session_id: str
    user_id: str
    request_id: str
    knowledge_tier: str          # free / paid，由服务端判定
    message: str                 # 当前原始用户消息

    # ---- 业务状态（来自仓储）----
    state: dict[str, Any]        # caplab_state.json 等价物
    active_stage: str
    route_reason: str

    # ---- 提议与确认 ----
    proposed_patch: dict[str, Any] | None
    proposal_token: str
    patch_preview: dict[str, Any]
    affected_sections: list[str]
    confirmation_decision: str   # confirm/partial/revise/reject
    confirmation_text: str
    confirmation_scope: list[str]
    awaiting_confirmation: bool

    # ---- 输出 ----
    reply: str
    display_block: str
    errors: list[str]
    requested_goal: str
    action_steps: list[dict[str, Any]]
    recent_dialogue: list[dict[str, str]]
    stage_prompt: str
    trace_tags: dict[str, str]
