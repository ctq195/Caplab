"""CapLab AgentArts 运行时入口。

云端：AgentArtsRuntimeApp + @app.entrypoint 暴露 POST /invocations，
      @app.ping 健康检查；context 提供 session_id/request_id。
本地：CAPLAB_OFFLINE=1 时用 FastAPI 等价入口，便于无云资源时验证协议。
"""
from __future__ import annotations

import os
import atexit
import secrets
import hmac
from contextlib import ExitStack
from threading import RLock
from pathlib import Path
from typing import Any, AsyncGenerator

from dotenv import load_dotenv

load_dotenv()
# Optional local demo: reuse the existing server-side model configuration.
if os.getenv("CAPLAB_USE_WEB_MODEL") == "1" and os.getenv("CAPLAB_OFFLINE") == "1":
    from dotenv import dotenv_values
    web_env = dotenv_values(Path(__file__).parent.parent / "CaplabWeb-existing/projects/.env.local")
    for suffix in ("BASE_URL", "MODEL", "API_KEY"):
        value = web_env.get(f"DEEPSEEK_{suffix}")
        if value:
            os.environ.setdefault(f"MAAS_{suffix}", value)
    if not all(os.getenv(f"MAAS_{suffix}") for suffix in ("BASE_URL", "MODEL", "API_KEY")):
        raise RuntimeError("本地模型配置不完整")

from src.caplab.graph.builder import build_graph, initial_input
from src.caplab.llm import build_llm, FakeLLM
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
resources = ExitStack()
atexit.register(resources.close)
saver = None
if DATABASE_URL:
    from langgraph.checkpoint.postgres import PostgresSaver
    saver = resources.enter_context(PostgresSaver.from_conn_string(DATABASE_URL))
    saver.setup()
elif OFFLINE:
    from langgraph.checkpoint.sqlite import SqliteSaver
    from src.caplab.persistence.local import LocalRepository
    local_dir = Path(os.getenv("CAPLAB_LOCAL_DATA") or Path(__file__).parent / ".cache")
    local_dir.mkdir(exist_ok=True, parents=True)
    saver = resources.enter_context(SqliteSaver.from_conn_string(str(local_dir / "checkpoint.sqlite")))
    repo = LocalRepository(local_dir / "business.sqlite", Path(__file__).parent / "assets/templates")
graph = build_graph(repo, llm, saver)
# 单进程验证服务按会话串行处理消息与确认。
session_locks = [RLock() for _ in range(64)]
tracer = setup_tracing()


def _tier(message: str, user_id: str) -> str:
    return resolve_tier(message, entitlements, user_id, demo_switch=DEMO_SWITCH)


def handle(payload: dict[str, Any], sdk_context=None) -> dict[str, Any]:
    try:
        ctx = build_context(payload, sdk_context)
        thread = f"{ctx.user_id}:{ctx.session_id}"
        config = {"configurable": {"thread_id": thread}}
        with session_locks[hash(thread) % len(session_locks)], span(tracer, "caplab.invocation"):
            tag_baggage(ctx.session_id, ctx.user_id)
            current = dict(graph.get_state(config).values or {})
            action = payload.get("action", "message")
            pending = current.get("awaiting_confirmation", False)
            if action == "confirm":
                if payload.get("token") != current.get("proposal_token") or not payload.get("token"):
                    raise ValueError("草稿已更新，请重新查看")
                decision = payload.get("decision")
                if decision not in {"confirm", "reject", "revise"}:
                    raise ValueError("请选择确认或退回草稿")
                if pending:
                    patch = current["proposed_patch"]
                    latest = repo.load(ctx.session_id, ctx.user_id)
                    if latest["revision"] != patch["base_revision"]:
                        raise ValueError("草稿版本已变化")
                    current = graph.invoke({"confirmation_decision": decision,
                                            "confirmation_text": payload.get("confirmation_text", ""),
                                            "state": latest, "errors": []}, config)
                elif not current.get("state", {}).get("confirmation_events") or current["state"]["confirmation_events"][-1]["decision"] != decision:
                    raise ValueError("当前没有匹配的待确认事项")
            elif action in {"message", "propose_goal"}:
                if pending:
                    raise ValueError("请先确认、修改或放下当前草稿")
                message = str(payload.get("message", "")).strip()
                if not message:
                    raise ValueError("请输入消息")
                turn = initial_input(ctx.session_id, ctx.user_id, message, _tier(message, ctx.user_id))
                turn["requested_goal"] = message if action == "propose_goal" else ""
                goal = repo.load(ctx.session_id, ctx.user_id)["sections"]["intake"].get("decision_question")
                turn["action_steps"] = [
                    {"title": step["title"], "done": bool(step["done"])}
                    for step in payload.get("steps", []) if step.get("goal") == goal
                ][:20]
                current = graph.invoke(turn, config)
            elif action != "status":
                raise ValueError("未知操作")
            state = repo.load(ctx.session_id, ctx.user_id)
            patch = current.get("proposed_patch") if current.get("awaiting_confirmation") else None
            errors = current.get("errors", []) if action != "status" else []
            return {
                "status": "error" if errors else "success",
                "response": ("草稿未通过校验，请重新表述。" if errors else current.get("reply", "")),
                "display_block": current.get("display_block", ""),
                "model_mode": "demo" if isinstance(llm, FakeLLM) else "live",
                "revision": state["revision"], "active_stage": state["active_stage"],
                "awaiting_confirmation": bool(patch), "errors": errors,
                "proposal": {"token": current["proposal_token"], "summary": patch.get("summary"),
                             "changes": patch["changes"]} if patch else None,
                "confirmed_goal": state["sections"]["intake"].get("decision_question"),
                "session_id": ctx.session_id, "request_id": ctx.request_id,
            }
    except ValueError as exc:
        return {"status": "error", "response": str(exc)}
    except Exception:
        return {"status": "error", "response": "智能体暂时无法处理本轮请求，请检查模型和存储服务。"}


# ---------------- 云端 SDK 入口 ----------------
if not OFFLINE:
    try:
        from agentarts.sdk import AgentArtsRuntimeApp, RequestContext
        from agentarts.sdk.runtime.model import PingStatus

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        async def handler(payload: dict, context: RequestContext = None) -> dict:
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
    from fastapi import FastAPI, Header, HTTPException

    # The offline gateway is local, but callers still need the server credential.
    key_dir = Path(os.getenv("CAPLAB_LOCAL_DATA") or Path(__file__).parent / ".cache")
    key_dir.mkdir(exist_ok=True, parents=True)
    key_file = key_dir / "gateway.token"
    if not key_file.exists():
        with key_file.open("x", encoding="ascii") as out:
            out.write(secrets.token_urlsafe(32))
    gateway_token = key_file.read_text(encoding="ascii").strip()
    app = FastAPI(title="CapLab Local Validation")

    @app.get("/ping")
    def ping():
        return {"status": "HEALTHY"}

    @app.post("/invocations")
    async def invocations(payload: dict, authorization: str = Header(default="")):
        if not hmac.compare_digest(authorization, f"Bearer {gateway_token}"):
            raise HTTPException(status_code=401, detail="authenticated gateway required")
        return handle(payload)

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("AGENT_RUN_PORT", 8080)))
