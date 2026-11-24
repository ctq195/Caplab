"""图级离线验证：LangGraph 编排、五阶段路由、确认门与输出块。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.caplab.graph.builder import build_graph, initial_input  # noqa: E402
from src.caplab.llm import FakeLLM  # noqa: E402
from src.caplab.persistence.repository import InMemoryRepository  # noqa: E402


@pytest.fixture
def graph():
    repo = InMemoryRepository(ROOT / "assets" / "templates")
    llm = FakeLLM()
    return build_graph(repo, llm), repo, llm


def test_graph_runs_and_returns_stage_output(graph):
    g, repo, llm = graph
    result = g.invoke(
        initial_input("s1", "u1", "我想梳理一下毕业后方向"),
        config={"configurable": {"thread_id": "u1:s1"}},
    )
    assert result["active_stage"] == "profile_intake"
    assert result["state"]["revision"] == 0
    assert result["awaiting_confirmation"] and result["proposed_patch"]
    assert "当前 revision" in result["display_block"]
    assert result.get("errors", []) == []
    assert llm.calls, "FakeLLM should have been invoked"


def test_graph_knowledge_tier_is_carried(graph):
    g, repo, llm = graph
    result = g.invoke(
        initial_input("s2", "u2", "继续", tier="paid"),
        config={"configurable": {"thread_id": "u2:s2"}},
    )
    assert "付费版 v2.3.0" in result["display_block"]


def test_graph_session_isolation(graph):
    g, repo, llm = graph
    g.invoke(initial_input("iso-s", "user-A", "A 的消息"),
             config={"configurable": {"thread_id": "user-A:iso-s"}})
    g.invoke(initial_input("iso-s", "user-B", "B 的消息"),
             config={"configurable": {"thread_id": "user-B:iso-s"}})
    a = repo.load("iso-s", "user-A")
    b = repo.load("iso-s", "user-B")
    assert a["state_id"] == b["state_id"] == "CAP-000001"
    assert repo.list_sessions("user-A") == ["iso-s"]
    assert repo.list_sessions("user-B") == ["iso-s"]
