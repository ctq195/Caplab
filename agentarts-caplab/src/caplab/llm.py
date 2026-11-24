"""模型调用抽象：云端走 MaaS OpenAI 兼容端点，本地测试可注入 FakeLLM。

模型端点仅作为推理能力；赛题合规由 AgentArts 平台的真实运行、Trace 与
版本信息证明，而不是"只调一个华为模型端点"。
"""
from __future__ import annotations

import json
import os
from typing import Any, Protocol


class LLM(Protocol):
    def invoke(self, system: str, user: str, temperature: float = 0.35) -> str: ...


class MaaSLLM:
    """OpenAI 兼容 /chat/completions，凭证从环境变量读取，禁止落盘。"""

    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None):
        self.base_url = base_url or os.getenv("MAAS_BASE_URL", "")
        self.model = model or os.getenv("MAAS_MODEL", "")
        self.api_key = api_key or os.getenv("MAAS_API_KEY", "")

    def invoke(self, system: str, user: str, temperature: float = 0.35) -> str:
        if not (self.base_url and self.model and self.api_key):
            raise RuntimeError("MAAS_BASE_URL / MAAS_MODEL / MAAS_API_KEY must be set")
        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=90.0)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"


class FakeLLM:
    """离线测试用：按当前阶段返回确定性的补丁与回复，不发网络请求。"""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def invoke(self, system: str, user: str, temperature: float = 0.35) -> str:
        self.calls.append({"system": system[:200], "user": user})
        # 识别阶段：优先读取 system 提示词中的显式 CURRENT_STAGE 标记
        import re
        match = re.search(r"当前阶段（CURRENT_STAGE）：(\w+)", system)
        stage = match.group(1) if match else "profile_intake"
        if "确认" in user and stage:
            return json.dumps({"reply": "好的，已记录。", "patch": None}, ensure_ascii=False)
        return json.dumps({
            "reply": f"[{stage}] 请告诉我最近一次与本轮决策相关的具体事件。",
            "patch": None,
        }, ensure_ascii=False)


def build_llm(llm: LLM | None = None) -> LLM:
    if llm is not None:
        return llm
    if os.getenv("CAPLAB_OFFLINE") == "1":
        return FakeLLM()
    return MaaSLLM()
