#!/usr/bin/env python3
"""Build the PREBUILT index bundles that ship inside the Skill (v2.0.1).

Run once by the maintainer on a machine that has the bundled int8 ONNX model.
The output uses exactly the same file layout as `caplab_rag.py init`, so a
target workspace can consume it via `init --prebuilt` with zero download and
zero encoding:

  <out>/free/  and  <out>/paid/
    index_meta.json  documents.json  sparse_index.json
    sources.json     claims.json     tags.json  embeddings.npy

Document vectors are produced by the SAME int8 ONNX model that will encode
queries at runtime (caplab_encoder.encode_onnx), so both live in one space.

Usage (preferred — JSON cards, no openpyxl):
  python scripts/export_kb_cards.py \
      --excel "CapLab公共知识库_v2.3.0_免费版.xlsx" \
      --tier free --out assets/knowledge-cards
  python scripts/build_prebuilt_index.py \
      --cards assets/knowledge-cards/free \
      --model-dir assets/models/bge-small-zh-v1.5-int8 \
      --tier free --out assets/prebuilt_index

Usage (legacy — direct from xlsx, needs openpyxl):
  python scripts/build_prebuilt_index.py \
      --excel "CapLab公共知识库_v2.3.0_免费版.xlsx" \
      --model-dir assets/models/bge-small-zh-v1.5-int8 \
      --tier free --out assets/prebuilt_index
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caplab_rag as rag
import caplab_encoder


def load_cards_to_documents(cards_dir: Path) -> tuple[list[dict], dict[str, dict], dict[str, list[dict]], dict[str, list[dict]]]:
    """Load the JSON card source (export_kb_cards.py output) — no openpyxl needed."""
    for name in ("index.json", "documents.json", "sources.json", "claims.json", "tags.json"):
        if not (cards_dir / name).is_file():
            raise SystemExit(f"ERROR: cards file missing: {cards_dir / name}")
    documents = json.loads((cards_dir / "documents.json").read_text(encoding="utf-8"))
    source_map = json.loads((cards_dir / "sources.json").read_text(encoding="utf-8"))
    claim_map = json.loads((cards_dir / "claims.json").read_text(encoding="utf-8"))
    tag_map = json.loads((cards_dir / "tags.json").read_text(encoding="utf-8"))
    return documents, source_map, claim_map, tag_map


def build_bundle(
    excel_path: Path | None,
    cards_dir: Path | None,
    model_dir: Path,
    tier: str,
    out_dir: Path,
    kb_version: str = "",
) -> None:
    if not (model_dir / "model_quantized.onnx").is_file():
        raise SystemExit(f"ERROR: ONNX model not found in {model_dir}")

    source_kind: str
    if cards_dir is not None:
        source_kind = "cards"
        print(f"Loading cards: {cards_dir.name}")
        documents, source_map, claim_map, tag_map = load_cards_to_documents(cards_dir)
        if not kb_version:
            try:
                kb_version = str(json.loads((cards_dir / "index.json").read_text(encoding="utf-8")).get("kb_version", ""))
            except Exception:
                kb_version = ""
    else:
        if excel_path is None or not excel_path.is_file():
            raise SystemExit("ERROR: need --excel or --cards")
        source_kind = "excel"
        print(f"Loading Excel: {excel_path.name}")
        documents, source_map, claim_map, tag_map = rag.load_excel_to_documents(excel_path)
        if not kb_version:
            kb_version = rag.detect_kb_version(excel_path)
    print(f"  documents={len(documents)} sources={len(source_map)} claims={sum(len(v) for v in claim_map.values())}")

    inverted_index = rag.build_inverted_index(documents)
    idf = rag.compute_idf(documents, inverted_index)
    print(f"  inverted tokens={len(inverted_index)}")

    # dense: encode EVERY document with the same int8 ONNX model used at query time
    print(f"  encoding {len(documents)} documents with {model_dir.name} ...")
    vectors = []
    for i, doc in enumerate(documents, 1):
        vector, channel, note = caplab_encoder.encode_query(
            doc["text"], onnx_dirs=[model_dir], api_cfg=None,
        )
        if vector is None:
            raise SystemExit(f"ERROR: document {i} encoding failed: {note}")
        if channel != "local_onnx":
            raise SystemExit(f"ERROR: expected local_onnx channel, got {channel}")
        vectors.append(vector)
        if i % 50 == 0:
            print(f"    {i}/{len(documents)}")
    import numpy as np
    embeddings = np.asarray(vectors, dtype="float32")
    print(f"  embeddings {embeddings.shape}")

    index_meta: dict[str, Any] = {
        "index_version": rag.INDEX_VERSION,
        "script_version": rag.SCRIPT_VERSION,
        "tier": tier,
        "kb_version": kb_version or "unknown",
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_type": source_kind,
        "excel_path": str(excel_path.resolve()) if excel_path else "",
        "excel_filename": excel_path.name if excel_path else "",
        "excel_sha256": rag.file_sha256(excel_path) if excel_path else "",
        "cards_dir": str(cards_dir) if cards_dir else "",
        "document_count": len(documents),
        "source_count": len(source_map),
        "claim_count": sum(len(v) for v in claim_map.values()),
        "tag_group_count": len(tag_map),
        "token_count": len(inverted_index),
        "dense_enabled": True,
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "embedding_source": "local_onnx:assets/models/bge-small-zh-v1.5-int8",
        "embedding_dimension": int(embeddings.shape[1]),
        "retrieval": "bge_dense+tfidf_sparse+rrf",
        "sheets_indexed": sorted(set(doc["sheet"] for doc in documents)),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    rag.atomic_write(out_dir / "index_meta.json", index_meta)
    rag.atomic_write(out_dir / "documents.json", documents)
    rag.atomic_write(out_dir / "sparse_index.json", {
        "inverted_index": inverted_index,
        "idf": idf,
    })
    rag.atomic_write(out_dir / "sources.json", source_map)
    rag.atomic_write(out_dir / "claims.json", claim_map)
    rag.atomic_write(out_dir / "tags.json", tag_map)
    rag.atomic_save_npy(out_dir / "embeddings.npy", embeddings, np)

    from caplab_index import seal_index
    seal_index(out_dir)
    print(f"PREBUILT bundle saved to: {out_dir}")
    print(f"  tier={tier} kb={kb_version} docs={len(documents)} dim={embeddings.shape[1]}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="build_prebuilt_index", description="Build prebuilt RAG index bundles (v2.0.1)")
    parser.add_argument("--excel", help="knowledge base xlsx (maintainer path, needs openpyxl)")
    parser.add_argument("--cards", help="JSON card source dir (export_kb_cards.py output, no openpyxl)")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--tier", required=True, choices=["free", "paid"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--kb-version", default="")
    args = parser.parse_args()
    if not args.excel and not args.cards:
        parser.error("need --excel or --cards")
    out_dir = Path(args.out).resolve() / args.tier
    out_dir.mkdir(parents=True, exist_ok=True)
    build_bundle(
        Path(args.excel) if args.excel else None,
        Path(args.cards) if args.cards else None,
        Path(args.model_dir), args.tier,
        out_dir, args.kb_version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
