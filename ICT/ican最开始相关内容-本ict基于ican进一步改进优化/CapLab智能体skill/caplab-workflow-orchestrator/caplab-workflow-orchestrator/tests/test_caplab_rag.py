from __future__ import annotations

import argparse
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "caplab_rag.py"
SPEC = importlib.util.spec_from_file_location("caplab_rag", SCRIPT)
rag = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(rag)


def document(index: int, text: str, entity: str, source: str) -> dict:
    tokens = rag.tokenize(text)
    return {
        "doc_id": f"sheet#{index}", "sheet": "测试表", "row": index,
        "entity_id": entity, "title": text, "tags": "测试",
        "source_ids": [source], "claim_ids": [], "fields": {},
        "text": text, "tokens": tokens, "token_set": list(set(tokens)),
        "fingerprint": str(index),
    }


class HybridRagTests(unittest.TestCase):
    def test_rrf_combines_dense_and_sparse_ranks(self):
        fused = rag.reciprocal_rank_fusion(
            [{"doc_index": 1, "dense_score": 0.9}, {"doc_index": 0, "dense_score": 0.7}],
            [{"doc_index": 0, "sparse_score": 8.0}, {"doc_index": 2, "sparse_score": 4.0}],
        )
        self.assertEqual(fused[0]["doc_index"], 0)
        self.assertIsNotNone(fused[0]["dense_score"])
        self.assertIsNotNone(fused[0]["sparse_score"])

    def test_dense_search_respects_filters(self):
        docs = [document(1, "人工智能应用开发", "E1", "S1"), document(2, "公务员考试", "E2", "S2")]
        docs[1]["sheet"] = "考公表"
        embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
        results = rag.dense_search(docs, embeddings, np.asarray([0.0, 1.0]), "考公", None, 5)
        self.assertEqual([item["doc_index"] for item in results], [1])

    def test_result_deduplication_prefers_entity_id(self):
        docs = [document(1, "人工智能项目", "E1", "S1"), document(2, "人工智能项目详情", "E1", "S1")]
        fused = [
            {"doc_index": 0, "dense_score": 0.9, "sparse_score": 3, "final_score": .03},
            {"doc_index": 1, "dense_score": 0.8, "sparse_score": 2, "final_score": .02},
        ]
        self.assertEqual(len(rag.build_hybrid_results(docs, fused, 5)), 1)

    def test_search_explicitly_reports_sparse_fallback(self):
        docs = [document(1, "人工智能应用开发岗位", "E1", "S1")]
        inverted = rag.build_inverted_index(docs)
        idf = rag.compute_idf(docs, inverted)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            from fixtures import make_index
            make_index(root, docs=docs, sources={"S1": {"标题": "官方岗位", "一级证据层级": "A"}})
            args = argparse.Namespace(
                index_dir=str(root), query="人工智能应用", sheet=None, tag=None,
                top_k=5, min_score=0.01, workspace=None, allow_download=False, sparse_only=False,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                rag.command_search(args)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["retrieval_mode"], "sparse_fallback")
            self.assertTrue(payload["degraded"])
            self.assertEqual(payload["results"][0]["dense_score"], None)
            self.assertEqual(payload["results"][0]["sources"][0]["Source_ID"], "S1")


if __name__ == "__main__":
    unittest.main()
