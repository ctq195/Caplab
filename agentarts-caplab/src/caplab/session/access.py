"""知识库分层权限：服务端判定，口令仅作演示开关且必须落库校验。

原 Skill 的 ICANDumate_VIP:enabled 口令是对话层演示开关，不是加密版权保护。
云端必须：1) 服务端解析身份；2) 授权表判定 tier；3) 未授权不得读付费知识。
"""
from __future__ import annotations

import re
from typing import Protocol

VIP_ENABLE = "ICANDumate_VIP:enabled"
VIP_DISABLE = "ICANDumate_VIP:disabled"


class EntitlementStore(Protocol):
    def tier_for(self, user_id: str) -> str: ...
    def set_tier(self, user_id: str, tier: str, granted_by: str) -> None: ...


class MemoryEntitlement:
    def __init__(self):
        self._tiers: dict[str, str] = {}

    def tier_for(self, user_id: str) -> str:
        return self._tiers.get(user_id, "free")

    def set_tier(self, user_id: str, tier: str, granted_by: str) -> None:
        if tier not in {"free", "paid"}:
            raise ValueError("tier must be free or paid")
        self._tiers[user_id] = tier


class PostgresEntitlement:
    def __init__(self, dsn: str):
        self._dsn = dsn

    def tier_for(self, user_id: str) -> str:
        import psycopg
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT knowledge_tier FROM caplab_entitlement WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else "free"

    def set_tier(self, user_id: str, tier: str, granted_by: str) -> None:
        import psycopg
        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO caplab_entitlement (user_id, knowledge_tier, granted_by)
                   VALUES (%s,%s,%s)
                   ON CONFLICT (user_id) DO UPDATE SET knowledge_tier=EXCLUDED.knowledge_tier,
                     granted_by=EXCLUDED.granted_by, granted_at=now()""",
                (user_id, tier, granted_by),
            )


def exact_vip_command(message: str) -> str | None:
    """精确匹配口令：不 trim、不 NFKC、不模糊匹配、不处理引文或附件。"""
    if message == VIP_ENABLE:
        return "paid"
    if message == VIP_DISABLE:
        return "free"
    return None


def resolve_tier(message: str, store: EntitlementStore, user_id: str,
                 demo_switch: bool = False) -> str:
    """返回当前知识库层级。demo_switch=False 时口令完全无效（生产推荐）。"""
    command = exact_vip_command(message)
    if demo_switch and command:
        store.set_tier(user_id, command, "demo-command")
    return store.tier_for(user_id)


def assert_paid_allowed(tier: str, requested: str) -> None:
    if requested == "paid" and tier != "paid":
        raise PermissionError("current user is not authorized for paid knowledge or paid model")
