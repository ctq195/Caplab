"""CapLab AgentArts 运行时入口。

云端：AgentArtsRuntimeApp + @app.entrypoint 暴露 POST /invocations，
      @app.ping 健康检查；context 提供 session_id/request_id。
本地：CAPLAB_OFFLINE=1 时用 FastAPI 等价入口，便于无云资源时验证协议。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncGenerator

from dotenv import load_dotenv

load_dotenv()

from src.caplab.graph.builder import build_graph, initial_input
from src.caplab.llm import build_llm
from src.caplab.persistence.repository import build_repository
from src.caplab.session.access import MemoryEntitlement, PostgresEntitlement, resolve_tier
from src.caplab.session.context import build_context
from src.caplab.observability.otel import setup_tracing, span, tag_baggage

DATABASE_URL = os.getenv("DATABASE_URL")
DEMO_SWITCH = os.getenv("CAPLAB_DEMO_VIP_SWITCH", "0") == "1"
OFFLINE = os.getenv("CAPLAB_OFFLINE", "0") == "1"

repo = build_repository(DATABASE_URL, Path(__file__).resolve().parent / "assets" / "templates")
entitlements = (
    PostgresEntitlement(DATABASE_URL) if DATABASE_URL else MemoryEntitlement()
)
llm = build_llm()
graph = build_graph(repo, llm, os.getenv("DATABASE_URL"))
tracer = setup_tracing()


def _tier(message: str, user_id: str) -> str:
    return resolve_tier(message, entitlements, user_id, demo_switch=DEMO_SWITCH)


def handle(payload: dict[str, Any], sdk_context=None) -> dict[str, Any]:
    """同步处理一次 invocation。"""
    with span(tracer, "caplab.invocation"):
        try:
            ctx = build_context(payload, sdk_context)
            tag_baggage(ctx.session_id, ctx.user_id)
            tier = _tier(str(payload.get("message", "")), ctx.user_id)
            with span(tracer, "caplab.graph", {"caplab.stage": "routing", "caplab.tier": tier}):
                result = graph.invoke(
                    initial_input(ctx.session_id, ctx.user_id, str(payload.get("message", "")), tier),
                    config={"configurable": {"thread_id": f"{ctx.user_id}:{ctx.session_id}"}},
                )
            return {
                "status": "success",
                "response": result.get("reply", ""),
                "display_block": result.get("display_block", ""),
                "revision": result.get("state", {}).get("revision"),
                "active_stage": result.get("active_stage"),
                "awaiting_confirmation": bool(result.get("awaiting_confirmation")),
                "errors": result.get("errors", []),
                "session_id": ctx.session_id,
                "request_id": ctx.request_id,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "response": f"执行出错：{exc}"}


def handle_confirm(payload: dict[str, Any], sdk_context=None) -> dict[str, Any]:
    """确认门恢复入口：服务端校验确认文本后应用补丁。"""
    try:
        ctx = build_context(payload, sdk_context)
        thread = f"{ctx.user_id}:{ctx.session_id}"
        decision = str(payload.get("decision", ""))
        text = str(payload.get("confirmation_text", ""))
        scope = payload.get("scope")
        if not text.strip():
            return {"status": "error", "response": "缺少明确确认文本，沉默不算确认"}
        current = graph.get_state({"configurable": {"thread_id": thread}})
        values = dict(current.values or {})
        values.update({
            "confirmation_decision": decision,
            "confirmation_text": text,
            "confirmation_scope": scope or [],
        })
        result = graph.invoke(values, config={"configurable": {"thread_id": thread}})
        return {
            "status": "success",
            "response": result.get("reply", ""),
            "revision": result.get("state", {}).get("revision"),
            "errors": result.get("errors", []),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "response": f"确认失败：{exc}"}


# ---------------- 云端 SDK 入口 ----------------
if not OFFLINE:
    try:
        from agentarts.sdk import AgentArtsRuntimeApp, RequestContext
        from agentarts.sdk.runtime.model import PingStatus

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        async def handler(payload: dict, context: RequestContext = None) -> dict:
            if payload.get("action") == "confirm":
                return handle_confirm(payload, context)
            return handle(payload, context)

        @app.ping
        def health_check() -> PingStatus:
            return PingStatus.HEALTHY

        if __name__ == "__main__":
            app.run(host="0.0.0.0", port=int(os.getenv("AGENT_RUN_PORT", 8080)))

    except ImportError:
        # SDK 未安装时给出明确提示，不伪称已接入平台
        app = None
        if __name__ == "__main__":
            raise SystemExit(
                "agentarts-sdk is not installed. Install it or set CAPLAB_OFFLINE=1 for local validation."
            )


# ---------------- 本地开发入口 ----------------
if OFFLINE:
    from fastapi import FastAPI

    app = FastAPI(title="CapLab Local Validation")

    @app.get("/ping")
    def ping():
        return {"status": "HEALTHY"}

    @app.post("/invocations")
    async def invocations(payload: dict):
        if payload.get("action") == "confirm":
            return handle_confirm(payload)
        return handle(payload)

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("AGENT_RUN_PORT", 8080)))
