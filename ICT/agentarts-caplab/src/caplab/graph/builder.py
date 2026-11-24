"""LangGraph 总控图构建。

五阶段是一个图中的路由分支，不是五个自由对话 Agent。
确认与消息从不同节点进入同一张图，待确认草稿随 checkpoint 保存。
"""
from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from ..llm import LLM
from ..persistence.repository import StateRepository
from ..protocol.ids import now
from .nodes.orchestrator import make_context
from .state import GraphState


def build_graph(repo: StateRepository, llm: LLM, checkpointer=None) -> Any:
    ctx = make_context(repo, llm)

    graph = StateGraph(GraphState)
    graph.add_node("load_state", ctx["load_state"])
    graph.add_node("route", ctx["route"])
    graph.add_node("stage_reasoning", ctx["stage_reasoning"])
    graph.add_node("propose_patch", ctx["propose_patch"])
    graph.add_node("finish", ctx["finish"])
    graph.add_node("apply_patch", ctx["apply_patch"])

    graph.add_conditional_edges(START, lambda state: "apply_patch" if state.get("confirmation_decision") else "load_state", ["apply_patch", "load_state"])
    graph.add_edge("load_state", "route")
    graph.add_edge("route", "stage_reasoning")
    graph.add_edge("stage_reasoning", "propose_patch")

    # 所有轮次都经过 finish 生成展示块；无补丁轮次不进入确认门。
    graph.add_edge("propose_patch", "finish")
    graph.add_edge("finish", END)
    graph.add_edge("apply_patch", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def initial_input(session_id: str, user_id: str, message: str, tier: str = "free") -> GraphState:
    return {
        "session_id": session_id,
        "user_id": user_id,
        "message": message,
        "confirmation_decision": "",
        "proposed_patch": None,
        "errors": [],
        "knowledge_tier": tier,
        "request_id": now(),
    }
