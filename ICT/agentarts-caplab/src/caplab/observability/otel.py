"""可观测：OTel Baggage 注入 + 手动 Span 埋点。

平台侧开启"日志记录/调用链/指标"后，可在"观测与优化 > 观测 > 调用链分析"
看到 LangGraph 节点状态转换与 Tool span。SemConv 命名遵循 OTel 惯例。
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


def setup_tracing(service_name: str = "caplab-agentarts") -> Any:
    """初始化 TracerProvider。平台探针已注入时复用全局 provider。"""
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(service_name)
        return tracer
    except ImportError:
        return None


@contextmanager
def span(tracer: Any, name: str, attrs: dict[str, str] | None = None) -> Iterator[None]:
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(name) as current:
        for key, value in (attrs or {}).items():
            current.set_attribute(key, value)
        yield


def tag_baggage(session_id: str, user_id: str) -> None:
    try:
        from opentelemetry.baggage import set_baggage
        from opentelemetry import context as ctx_api

        baggage = set_baggage("session_id", session_id)
        baggage = set_baggage("user_id", user_id, baggage)
        ctx_api.attach(baggage)
    except ImportError:
        pass
