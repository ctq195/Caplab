"""可溯源检索：保留 Source_ID/Claim_ID、quality 与 retrieval_mode 明示。

云端以平台知识库为主时可替换本实现，但输出契约必须保持：
retrieval_mode / embedding_channel / Source_ID / Claim_ID / quality / 时效状态。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .loader import load_cards, quality_ok


@dataclass
class RetrievalResult:
    query: str
    retrieval_mode: str
    embedding_channel: str
    items: list[dict[str, Any]]
    tier: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "retrieval_mode": self.retrieval_mode,
            "embedding_channel": self.embedding_channel,
            "tier": self.tier,
            "items": self.items,
        }


class CardRetriever:
    """基于随包 JSON 知识卡的轻量检索（关键词/TF-IDF 降级）。"""

    def __init__(self, tier: str):
        self.tier = tier
        self.cards = load_cards(tier)

    def search(self, query: str, top_k: int = 8) -> RetrievalResult:
        documents = self.cards.get("documents", {})
        if isinstance(documents, dict):
            docs = list(documents.values())
        elif isinstance(documents, list):
            docs = documents
        else:
            docs = []

        terms = [t for t in query.lower().split() if len(t) >= 2]
        scored: list[tuple[float, dict]] = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if not quality_ok(doc):
                continue
            text = " ".join(str(v) for v in doc.values() if isinstance(v, str)).lower()
            score = sum(text.count(t) for t in terms) / (len(terms) or 1)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        items = [
            {
                "score": round(score, 4),
                "Source_ID": doc.get("source_id") or doc.get("sourceId") or doc.get("Source_ID"),
                "Claim_ID": doc.get("claim_id") or doc.get("claimId") or doc.get("Claim_ID"),
                "quality": doc.get("quality", "unknown"),
                "text": str(doc.get("text") or doc.get("content") or "")[:800],
            }
            for score, doc in scored[:top_k]
        ]
        return RetrievalResult(
            query=query,
            retrieval_mode="keyword_fallback",
            embedding_channel="none",
            items=items,
            tier=self.tier,
        )


def search(query: str, tier: str, top_k: int = 8) -> RetrievalResult:
    return CardRetriever(tier).search(query, top_k)
