"""会话上下文解析：session_id / user_id / request_id 的来源与隔离。

AgentArts ExecuteRuntime 通过 Header X-Hw-Agentarts-Session-Id 传递会话 ID；
RequestContext 由 SDK 注入 session_id/request_id。user_id 必须由服务端鉴权
后解析，不能信任客户端自报。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class RequestContext:
    session_id: str
    user_id: str
    request_id: str = ""


def build_context(payload: dict, sdk_context=None) -> RequestContext:
    """从 SDK 上下文与请求体构建隔离上下文。

    - session_id 优先取 SDK context（平台注入），其次取 Header 映射的字段，
      最后取 payload.session_id；缺失时拒绝（禁止降级为全局会话）。
    - user_id 只接受服务端注入字段（SDK context.user_id 或 payload._server_user_id），
      不接受 payload.user_id 这类客户端自报字段。
    """
    sdk_session = getattr(sdk_context, "session_id", None) if sdk_context else None
    sdk_user = getattr(sdk_context, "user_id", None) if sdk_context else None
    sdk_request = getattr(sdk_context, "request_id", None) if sdk_context else None

    session_id = (
        sdk_session
        or payload.get("session_id")
        or payload.get("sessionId")
    )
    user_id = sdk_user or payload.get("_server_user_id")
    if not session_id or not SESSION_RE.match(str(session_id)):
        raise ValueError("valid session_id is required (X-Hw-Agentarts-Session-Id)")
    if not user_id:
        raise ValueError("user_id must be resolved by server-side auth, not client payload")
    return RequestContext(
        session_id=str(session_id),
        user_id=str(user_id),
        request_id=str(sdk_request or payload.get("request_id", "")),
    )


def inject_baggage(ctx: RequestContext) -> None:
    """OTel Baggage 注入，使平台 Trace 可按会话/用户维度分析。"""
    try:
        from opentelemetry.baggage import set_baggage
        from opentelemetry import context as ctx_api

        baggage = set_baggage("session_id", ctx.session_id)
        baggage = set_baggage("user_id", ctx.user_id, baggage)
        ctx_api.attach(baggage)
    except ImportError:
        pass
