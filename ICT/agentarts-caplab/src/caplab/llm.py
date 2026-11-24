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
        if stage == "profile_intake":
            state_text, message_text = user.split("\n\n用户本轮消息：", 1)
            revision = int(re.search(r'"revision":\s*(\d+)', state_text).group(1))
            message = message_text.split("\n\n", 1)[0].strip()
            goal_match = re.search(r'"decision_question":\s*("(?:[^"\\]|\\.)*")', state_text)
            if goal_match and not message.startswith("新目标："):
                goal = json.loads(goal_match.group(1))
                steps_text = user.rsplit("个人行动清单（本人报告，独立于知识库）：", 1)[-1].split("\n", 1)[0]
                steps = json.loads(steps_text)
                if steps:
                    completed = sum(bool(step["done"]) for step in steps)
                    remaining = 100 - int(100 * completed / len(steps) + 0.5)
                    return json.dumps({"reply": f"“{goal}”的行动清单已经完成 {completed}/{len(steps)} 项，还差 {remaining}%。下一步想聊哪项行动？", "patch": None}, ensure_ascii=False)
                return json.dumps({"reply": f"你已确认想探索“{goal}”。你可以在目标卡中记下一个小行动，完成后勾选。想换方向时，发“新目标：”加上你的想法。", "patch": None}, ensure_ascii=False)
            message = message.removeprefix("新目标：").strip()
            return json.dumps({
                "reply": "我把你这次想探索的问题整理成了草稿。看看是否准确，确认后就可以拆成小行动。",
                "patch": {"actor_skill": "caplab-profile-intake", "base_revision": revision,
                          "summary": message, "changes": [{"op": "set", "path": "/sections/intake/decision_question",
                                                            "value": message}]},
            }, ensure_ascii=False)
        return json.dumps({
            "reply": f"[{stage}] 请告诉我最近一次与本轮决策相关的具体事件。",
            "patch": None,
        }, ensure_ascii=False)


def build_llm(llm: LLM | None = None) -> LLM:
    if llm is not None:
        return llm
    if os.getenv("CAPLAB_OFFLINE") == "1" and not all(os.getenv(k) for k in ("MAAS_BASE_URL", "MAAS_MODEL", "MAAS_API_KEY")):
        return FakeLLM()
    return MaaSLLM()
