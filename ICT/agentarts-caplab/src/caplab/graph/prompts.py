"""按阶段加载镜像内只读提示词资源。

云端沙箱不保证本地磁盘持久，但镜像内的只读文件随镜像发布，可安全读取。
基线来自 Skill 的 SKILL.md + references/stages/*.md，逐字复制，不改写口径。
"""
from __future__ import annotations

from pathlib import Path

_PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"

STAGE_FILES = {
    "profile_intake": "stages/profile-intake.md",
    "profile_confirmation": "stages/profile-confirmation.md",
    "path_convergence": "stages/path-convergence.md",
    "path_evidence_cycle": "stages/path-evidence-cycle.md",
    "evidence_review": "stages/evidence-review.md",
}

SUPPORT_FILES = [
    "SKILL-source.md",
    "workflow.md",
    "state-protocol.md",
    "runtime-guards.md",
    "shared/personal-facts.md",
    "shared/psychological-mechanisms.md",
    "methods/dialogic-self-understanding.md",
]


def stage_prompt(stage: str) -> str:
    name = STAGE_FILES.get(stage)
    if not name:
        return ""
    return (_PROMPT_ROOT / name).read_text(encoding="utf-8")


def support_prompt(name: str) -> str:
    return (_PROMPT_ROOT / name).read_text(encoding="utf-8")


def system_prompt(stage: str) -> str:
    """组装当前轮的 system 提示词：总控规则 + 当前阶段规则 + 关键方法。"""
    parts = [
        "# CapLab Workflow Orchestrator（基线 v2.1.1）",
        f"当前阶段（CURRENT_STAGE）：{stage}",
        "你是 CapLab 生涯探索助手的总控编排器。你管理状态与路由，不代替五个业务阶段作出画像、路径或复盘判断。",
        "关键纪律：一轮只问一个关键问题；沉默不算确认；未确认信息不得写为事实；不输出能力排名或就业风险等级；遇到即时危险停止流程转向真人支持。",
        "",
        support_prompt("workflow.md"),
        "",
        "## 当前阶段规则（严格遵守，不得跳过阶段）",
        stage_prompt(stage),
        "",
        "## 贯穿式对话方法",
        support_prompt("methods/dialogic-self-understanding.md"),
        "",
        "## 状态与确认规则摘要",
        support_prompt("state-protocol.md"),
    ]
    text = "\n".join(parts)
    # 提示词预算：避免超出模型上下文，总控文件较长时截断但保留阶段全文
    max_chars = 24000
    if len(text) > max_chars:
        head = "\n".join(parts[:5])
        tail = "\n".join(parts[5:])
        text = head + "\n[总控规则已按长度裁剪]\n" + tail[:max_chars - len(head) - 40]
    return text


def output_display_block(state: dict, preview: dict | None, patch_id: str | None,
                         tier: str, retrieval_mode: str = "none") -> str:
    tier_label = "付费版" if tier == "paid" else "免费版"
    return "\n".join([
        f"当前 revision：{state['revision']}",
        f"当前阶段：{state['active_stage']}",
        f"知识库版本：{tier_label} v2.3.0",
        f"检索模式：{retrieval_mode}",
        "拟变更摘要：" + ((preview or {}).get("summary") or "无"),
        "受影响字段与依赖：" + ", ".join((preview or {}).get("affected_sections", [])),
        f"精确补丁：{patch_id or '无'}",
        "等待选择：确认 / 修改 / 拒绝",
    ])
