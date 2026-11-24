"""知识卡加载与分层过滤。

基线：assets/knowledge-cards/{free,paid}/{documents,sources,claims,tags,index}.json。
免费/付费物理隔离：未授权时不得读取 paid 目录，也不得复用旧的 paid 检索结果。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CARD_ROOT = Path(__file__).resolve().parents[3] / "assets" / "knowledge-cards"
VALID_QUALITY = {"verified", "official", "historical_reference"}
EXCLUDED_QUALITY = {"rejected", "pending_review", "expired", "needs_seasonal_check"}


def load_cards(tier: str) -> dict[str, Any]:
    if tier not in {"free", "paid"}:
        raise ValueError("tier must be free or paid")
    root = CARD_ROOT / tier
    result: dict[str, Any] = {}
    for name in ("documents", "sources", "claims", "tags", "index"):
        path = root / f"{name}.json"
        if path.exists():
            result[name] = json.loads(path.read_text(encoding="utf-8"))
    return result


def quality_ok(card: dict) -> bool:
    quality = str(card.get("quality", "")).lower()
    if quality in EXCLUDED_QUALITY:
        return False
    return True
