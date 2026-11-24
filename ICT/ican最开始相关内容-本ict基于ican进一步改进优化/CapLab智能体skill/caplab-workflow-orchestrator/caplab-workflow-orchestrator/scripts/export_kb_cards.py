#!/usr/bin/env python3
"""Export the v2.3.0 knowledge base (xlsx) into plain JSON card files (v2.0.1).

Why: the runtime and the index builder read JSON, not xlsx. JSON cards are
    - human-readable (open in any editor / DuMate preview),
    - index-buildable without openpyxl (build_prebuilt_index.py --cards),
    - diff-able / git-friendly,
    - shareable as files inside a DuMate conversation.

Output layout (identical for free/paid):
  <out>/<tier>/
    index.json       # tier, kb_version, counts, sheet list
    sources.json     # Source_ID -> record
    claims.json      # Claim_ID  -> [record, ...]
    tags.json        # tag group -> [{tag, definition}, ...]
    documents.json   # one card per knowledge row (same doc schema as the index)

Usage (maintainer machine):
  python scripts/export_kb_cards.py \
      --excel "CapLab公共知识库_v2.3.0_免费版.xlsx" \
      --tier free --out assets/knowledge-cards
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


def export_cards(excel_path: Path, tier: str, out_dir: Path, kb_version: str = "") -> None:
    if not excel_path.is_file():
        raise SystemExit(f"ERROR: Excel file not found: {excel_path}")

    print(f"Loading Excel: {excel_path.name}")
    documents, source_map, claim_map, tag_map = rag.load_excel_to_documents(excel_path)
    print(f"  documents={len(documents)} sources={len(source_map)} claims={sum(len(v) for v in claim_map.values())}")

    if not kb_version:
        kb_version = rag.detect_kb_version(excel_path)

    index: dict[str, Any] = {
        "format": "caplab-knowledge-cards",
        "format_version": "1.0.0",
        "tier": tier,
        "kb_version": kb_version or "unknown",
        "exported_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "excel_filename": excel_path.name,
        "excel_sha256": rag.file_sha256(excel_path),
        "document_count": len(documents),
        "source_count": len(source_map),
        "claim_count": sum(len(v) for v in claim_map.values()),
        "tag_group_count": len(tag_map),
        "sheets": sorted(set(doc["sheet"] for doc in documents)),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    rag.atomic_write(out_dir / "index.json", index)
    rag.atomic_write(out_dir / "documents.json", documents)
    rag.atomic_write(out_dir / "sources.json", source_map)
    rag.atomic_write(out_dir / "claims.json", claim_map)
    rag.atomic_write(out_dir / "tags.json", tag_map)
    print(f"CARDS saved to: {out_dir}")
    print(f"  tier={tier} kb={kb_version} docs={len(documents)} files=5")


def main() -> int:
    parser = argparse.ArgumentParser(prog="export_kb_cards", description="Export xlsx knowledge base to JSON cards (v2.0.1)")
    parser.add_argument("--excel", required=True)
    parser.add_argument("--tier", required=True, choices=["free", "paid"])
    parser.add_argument("--out", required=True)
    parser.add_argument("--kb-version", default="")
    args = parser.parse_args()
    export_cards(Path(args.excel), args.tier, Path(args.out).resolve() / args.tier, args.kb_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
