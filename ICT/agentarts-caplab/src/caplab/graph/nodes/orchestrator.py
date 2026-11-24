"""固定流程节点：预处理 → 校验 → 路由 → 阶段推理 → propose → 确认门 → apply → 回验。

采用 LangGraph interrupt 实现确认门：等待用户明确确认时图中断，状态写入
持久化 checkpoint；恢复时由服务端校验确认文本，绝不从沉默推断确认。
"""
from __future__ import annotations

import json
from typing import Any

from ...knowledge.retriever import search as retrieve_cards
from ...llm import LLM
from ...observability.otel import setup_tracing, span
from ...persistence.repository import StateRepository
from ...protocol.ids import SKILL_VERSION, STAGE_TO_ACTOR, next_id, now
from ...protocol.patch import (
    PatchError, apply_confirmed, propose, rollback, route_for, validate_state,
)
from ..prompts import output_display_block, system_prompt
from ..state import GraphState

# 输出门正则（迁移 caplab_guards.py 的关键守卫）
_DEFINITE_ATTRIBUTION = ["你的真实动机就是", "你其实只是", "你本质上", "你就是在逃避"]
_ABSOLUTE_CLAIM = ["一定能", "必然", "肯定能上岸", "这不妨碍你现在就拿它去投递"]


def _guard_reply(text: str) -> list[str]:
    errors: list[str] = []
    for phrase in _DEFINITE_ATTRIBUTION:
        if phrase in text:
            errors.append(f"definite attribution forbidden: {phrase}")
    for phrase in _ABSOLUTE_CLAIM:
        if phrase in text:
            errors.append(f"absolute claim forbidden: {phrase}")
    return errors


def make_context(repo: StateRepository, llm: LLM):
    """构造节点函数闭包，共享仓储与模型实例。"""
    tracer = setup_tracing()

    def load_state(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        user_id = state["user_id"]
        business = repo.load(session_id, user_id)
        errors = validate_state(business)
        if errors:
            return {**state, "errors": errors, "reply": "状态校验失败，已停止业务推理。"}
        return {**state, "state": business}

    def route(state: GraphState) -> GraphState:
        stage, reason = route_for(state["state"])
        return {
            **state,
            "active_stage": stage,
            "route_reason": reason,
            "trace_tags": {
                "session_id": state["session_id"],
                "user_id": state["user_id"],
                "stage": stage,
                "revision": str(state["state"]["revision"]),
            },
        }

    def stage_reasoning(state: GraphState) -> GraphState:
        stage = state["active_stage"]
        if stage in {"closed", "blocked"}:
            reply = (
                "当前存在阻碍继续流程的情况，已暂停生涯探索。"
                "如需支持请联系学校心理中心或可信赖的真人。"
                if stage == "blocked" else "当前阶段已闭环，如需调整请告诉我具体变化。"
            )
            return {**state, "reply": reply}
        prompt = system_prompt(stage)
        # 可溯源检索：真实工具调用 + Tool span（探针 P2 的证据来源）
        retrieval_note = ""
        with span(tracer, "caplab.tool.knowledge_retrieve", {
            "caplab.tier": state.get("knowledge_tier", "free"),
            "caplab.stage": stage,
        }):
            try:
                retrieval = retrieve_cards(state["message"], state.get("knowledge_tier", "free"), top_k=5)
                if retrieval.items:
                    lines = [
                        f"- Source_ID={it.get('Source_ID')} Claim_ID={it.get('Claim_ID')} "
                        f"quality={it.get('quality')}: {it.get('text', '')[:200]}"
                        for it in retrieval.items
                    ]
                    retrieval_note = (
                        f"\n\n知识卡检索结果（retrieval_mode={retrieval.retrieval_mode}, "
                        f"embedding_channel={retrieval.embedding_channel}）：\n" + "\n".join(lines)
                    )
            except Exception as exc:  # 检索失败不阻断主流程，但显式暴露
                retrieval_note = f"\n\n知识卡检索失败：{exc}"
        user_input = (
            f"当前状态（JSON）：\n{json.dumps(state['state'], ensure_ascii=False)[:6000]}\n\n"
            f"用户本轮消息：{state['message']}{retrieval_note}\n\n"
            "请只输出 JSON：{\"reply\": \"给用户的自然语言回复\", \"patch\": null 或补丁对象}。"
            "补丁对象字段：patch_id(PAT-000001), actor_skill, skill_version(2.1.1), "
            "base_revision, operation(propose_patch), changes([{op,path,value}]), "
            "referenced_ids([]), requires_confirmation(true), summary。"
            "如果没有足够证据形成正式补丁，patch 必须为 null。"
        )
        raw = llm.invoke(prompt, user_input)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"reply": raw, "patch": None}
        reply = str(parsed.get("reply", ""))
        errors = _guard_reply(reply)
        if errors:
            return {**state, "errors": errors, "reply": "本轮回复未通过措辞守卫，请重新表述。"}
        return {
            **state,
            "reply": reply,
            "proposed_patch": parsed.get("patch"),
            "stage_prompt": prompt[:200],
        }

    def propose_patch(state: GraphState) -> GraphState:
        patch = state.get("proposed_patch")
        if not patch:
            return {**state, "awaiting_confirmation": False}
        try:
            patch = dict(patch)
            patch.setdefault("patch_id", next_id(state["state"], "PAT"))
            patch.setdefault("skill_version", SKILL_VERSION)
            patch.setdefault("base_revision", state["state"]["revision"])
            patch.setdefault("operation", "propose_patch")
            patch.setdefault("referenced_ids", [])
            patch.setdefault("requires_confirmation", True)
            preview = propose(patch, state["state"])
            return {
                **state,
                "proposed_patch": patch,
                "patch_preview": preview["preview"],
                "affected_sections": preview["affected_sections"],
                "awaiting_confirmation": True,
            }
        except PatchError as exc:
            return {**state, "errors": exc.errors, "proposed_patch": None, "awaiting_confirmation": False}

    def finish(state: GraphState) -> GraphState:
        business = state["state"]
        display = output_display_block(
            business,
            {"summary": (state.get("proposed_patch") or {}).get("summary", ""),
             "affected_sections": state.get("affected_sections", [])},
            (state.get("proposed_patch") or {}).get("patch_id"),
            state.get("knowledge_tier", "free"),
        )
        return {**state, "display_block": display}

    def apply_patch(state: GraphState) -> GraphState:
        """恢复后执行：用户明确确认才落库。"""
        decision = state.get("confirmation_decision", "")
        text = state.get("confirmation_text", "")
        patch = state.get("proposed_patch")
        if not patch:
            return {**state, "errors": ["no patch to confirm"]}
        try:
            if decision == "rollback":
                target = int(state.get("confirmation_scope", [0])[0]) if state.get("confirmation_scope") else 0
                snapshot = repo.revision(state["session_id"], state["user_id"], target)
                if not snapshot:
                    raise PatchError([f"revision {target} not found"])
                updated = rollback(state["state"], target, snapshot, text)
            else:
                updated = apply_confirmed(
                    state["state"], patch, decision, text,
                    scope=state.get("confirmation_scope"),
                )
            repo.save(state["session_id"], state["user_id"], updated, patch.get("patch_id"))
            stage, reason = route_for(updated)
            return {
                **state,
                "state": updated,
                "active_stage": stage,
                "route_reason": reason,
                "awaiting_confirmation": False,
                "reply": f"已确认。补丁 {patch.get('patch_id')} 已应用，revision {state['state']['revision']} → {updated['revision']}。下一阶段：{stage}。",
            }
        except PatchError as exc:
            return {**state, "errors": exc.errors}

    return {
        "load_state": load_state,
        "route": route,
        "stage_reasoning": stage_reasoning,
        "propose_patch": propose_patch,
        "finish": finish,
        "apply_patch": apply_patch,
    }
