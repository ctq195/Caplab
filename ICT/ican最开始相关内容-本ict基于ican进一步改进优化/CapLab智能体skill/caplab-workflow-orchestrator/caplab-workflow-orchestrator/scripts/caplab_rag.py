#!/usr/bin/env python3
"""CapLab local hybrid RAG retrieval (v2.1.0, free/paid tier aware).

Loads the UniPath public knowledge base (Excel) into a structured JSON index,
builds BGE dense vectors plus a Chinese-aware sparse index, fuses their ranks,
and returns traceable results with Source_ID, Claim_ID, and sheet/row provenance.

Reproducibility design (v2.1.0):
- A prebuilt index (documents/sparse/dense embeddings) ships with the Skill, so
  a fresh workspace can `init --prebuilt` with ZERO model download or encoding.
- Query encoding runs through three automatic channels:
    1. local_onnx  - bundled int8 BGE model via onnxruntime (offline, ~30 MB)
    2. api         - Qianfan / OpenAI-compatible embedding API (online, optional)
    3. (none)      - explicit sparse TF-IDF fallback, never silently masked
- The API channel is skipped unless its dimension equals the index dimension.
- Rebuilding the index from Excel is still supported for maintainers:
  `init --excel ... --allow-download` (local torch) or `--embedding-api <cfg>`.

Design principles:
- Dense retrieval uses BAAI/bge-small-zh-v1.5 and NumPy cosine similarity.
- Sparse retrieval remains available as an explicit degraded fallback.
- Each Excel row becomes a "document" with sheet, row number, and field values.
- Keyword scoring uses a TF-IDF-like approach with Chinese-aware tokenisation.
- Tag filtering uses the 17_标签词表 sheet for controlled vocabulary.
- Source tracing via 15_来源索引 and 16_事实来源 for provenance.
- Results always include provenance fields for auditability.

CLI commands:
  init   --excel <path> --index-dir <dir>        Build index from Excel.
         --prebuilt <dir>                        Copy a prebuilt index bundle.
  search --index-dir <dir> --query <text>        Search the index.
  stats  --index-dir <dir>                       Show coverage statistics.
  export --index-dir <dir> --sheet <name>        Export a sheet as JSON.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

openpyxl = None

SCRIPT_VERSION = "2.1.1"
INDEX_VERSION = "3.0.0"
DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
RRF_K = 60

# Sheets that contain actual knowledge content (not metadata/audit)
CONTENT_SHEETS = {
    "02_人物案例", "03_本科后去向", "04_路径节点", "05_访谈洞察",
    "06_招聘岗位", "07_岗位要求", "08_目标对象", "09_目标要求",
    "10_路径模板", "11_证据规则", "12_行动模板", "13_机会窗口",
    "14_风险情境", "18_KB卡片", "23_理论依据",
    "24_目标实例", "25_窗口实例", "26_申请事件", "27_路径冲突",
    "28_领域覆盖", "29_要求证据映射", "30_差距判定规则",
    "33_考研项目详情", "34_考公考试批次", "35_考公职位详情",
    "37_留学项目详情", "38_留学申请轮次",
}

# Reference sheets for provenance lookup
SOURCE_SHEET = "15_来源索引"
CLAIM_SHEET = "16_事实来源"
TAG_SHEET = "17_标签词表"

# Fields that are considered "text content" for search indexing
TEXT_FIELD_HINTS = (
    "标题", "卡片文本", "具体事实", "姓名", "主路径", "当前角色", "可迁移经验",
    "日常核心任务", "门槛", "进入方式", "学校", "学院", "专业名称", "初试科目",
    "复试内容", "关键时间", "使用边界", "定义", "内容", "描述", "备注",
    "岗位名称", "任职要求", "职责", "洞察", "经验", "建议",
    "适用人群", "使用警告", "不可复制条件", "关键转折", "进入资产",
)

# Fields to exclude from indexing (IDs, metadata, dates)
EXCLUDE_FIELD_HINTS = (
    "_ID", "版本", "核验日期", "生成版本", "卡片字数", "信息完整度",
    "缺失字段", "Max_row", "Max_col",
)

# Chinese stopwords
STOPWORDS = frozenset([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
    "看", "好", "自己", "这", "那", "他", "她", "它", "们", "什么", "怎么",
    "可以", "能", "做", "想", "被", "把", "给", "让", "使", "从", "向", "对",
    "但", "而", "与", "或", "如果", "因为", "所以", "虽然", "然后", "还是",
    "已经", "正在", "将要", "可能", "应该", "必须", "需要", "比如", "例如",
    "以及", "并且", "通过", "关于", "对于", "根据", "按照", "随着",
])


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def detect_tier_from_filename(excel_path: Path, explicit: str | None = None) -> str:
    """Resolve the knowledge base tier from an explicit flag or the Excel file name.

    Paid files are named with 付费/paid/premium, free files with 免费/free/basic.
    Returns one of: paid, free, unknown.
    """
    if explicit:
        value = explicit.strip().lower()
        if value in ("paid", "付费", "premium", "pro"):
            return "paid"
        if value in ("free", "免费", "basic"):
            return "free"
        return "unknown"
    name = excel_path.name
    lowered = name.lower()
    if "付费" in name or "paid" in lowered or "premium" in lowered:
        return "paid"
    if "免费" in name or "free" in lowered or "basic" in lowered:
        return "free"
    return "unknown"


def detect_kb_version(excel_path: Path) -> str:
    """Read the knowledge base version (e.g. 2.3.0) from the 00_总览 sheet header."""
    try:
        if openpyxl is None:
            import openpyxl as _openpyxl
            globals()["openpyxl"] = _openpyxl
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        target = wb["00_总览"] if "00_总览" in wb.sheetnames else wb.worksheets[0]
        for row in target.iter_rows(max_row=8, values_only=True):
            for cell in row:
                if cell and isinstance(cell, str):
                    match = re.search(r"v?(\d+\.\d+\.\d+)", cell)
                    if match:
                        wb.close()
                        return match.group(1)
        wb.close()
    except Exception:
        pass
    return ""


def workspace_paths(workspace: Path | None, index_dir: Path) -> tuple[Path | None, Path | None]:
    if workspace is None:
        return None, None
    base = workspace.resolve() / ".caplab"
    deps = base / "deps"
    models = base / "models"
    if deps.exists() and str(deps) not in sys.path:
        sys.path.insert(0, str(deps))
    return deps, models


def load_dense_runtime(workspace: Path | None, index_dir: Path):
    _, models = workspace_paths(workspace, index_dir)
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "dense dependencies are unavailable; run bootstrap.py setup after user confirmation"
        ) from exc
    return np, SentenceTransformer, models


def load_encoder(
    workspace: Path | None,
    index_dir: Path,
    model_name: str,
    allow_download: bool,
):
    np, sentence_transformer, models = load_dense_runtime(workspace, index_dir)
    kwargs: dict[str, Any] = {"device": "cpu"}
    if models is not None:
        models.mkdir(parents=True, exist_ok=True)
        kwargs["cache_folder"] = str(models)
    if not allow_download:
        kwargs["local_files_only"] = True
    try:
        encoder = sentence_transformer(model_name, **kwargs)
    except TypeError:
        kwargs.pop("local_files_only", None)
        if not allow_download:
            os.environ["HF_HUB_OFFLINE"] = "1"
        encoder = sentence_transformer(model_name, **kwargs)
    return np, encoder


def encode_texts(encoder: Any, texts: list[str]):
    return encoder.encode(
        texts,
        batch_size=32,
        show_progress_bar=len(texts) > 64,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def tokenize(text: str) -> list[str]:
    """Chinese-aware tokenisation: split on non-alphanumeric-CJK boundaries,
    then further split CJK runs into bigrams for better matching."""
    if not text or not isinstance(text, str):
        return []
    text = str(text).strip().lower()
    if not text:
        return []
    # Split on punctuation and whitespace (keep CJK and alphanumeric)
    segments = re.split(r'[^\w\u4e00-\u9fff]+', text)
    tokens: list[str] = []
    for seg in segments:
        if not seg:
            continue
        # ASCII alphanumeric token
        if re.match(r'^[a-z0-9]+$', seg):
            if len(seg) >= 2 and seg not in STOPWORDS:
                tokens.append(seg)
            continue
        # CJK segment: extract bigrams + unigrams
        cjk_chars = re.findall(r'[\u4e00-\u9fff]', seg)
        for i in range(len(cjk_chars)):
            char = cjk_chars[i]
            if char not in STOPWORDS:
                tokens.append(char)
            if i + 1 < len(cjk_chars):
                bigram = cjk_chars[i] + cjk_chars[i + 1]
                if bigram not in STOPWORDS:
                    tokens.append(bigram)
        # Also try to keep mixed alphanumeric chunks
        mixed = re.findall(r'[a-z0-9]+', seg)
        for m in mixed:
            if len(m) >= 2 and m not in STOPWORDS:
                tokens.append(m)
    return tokens


def row_fingerprint(sheet: str, row_num: int) -> str:
    raw = f"{sheet}:{row_num}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def is_text_field(field_name: str) -> bool:
    """Determine if a field should be indexed as text content."""
    if not field_name:
        return False
    upper = field_name.upper()
    for hint in EXCLUDE_FIELD_HINTS:
        if hint.upper() in upper:
            return False
    for hint in TEXT_FIELD_HINTS:
        if hint in field_name:
            return True
    # Default: index fields that are not pure ID fields
    if field_name.endswith("_ID") or field_name.endswith("_IDs"):
        return False
    return True


def load_excel_to_documents(excel_path: Path) -> tuple[list[dict], dict[str, dict], dict[str, list[dict]], dict[str, list[dict]]]:
    """Load Excel into document list, source map, claim map, and tag map."""
    if openpyxl is None:
        try:
            import openpyxl as _openpyxl
            globals()["openpyxl"] = _openpyxl
        except ImportError:
            print("ERROR: openpyxl is required for indexing. Install with: pip install openpyxl", file=sys.stderr)
            sys.exit(2)
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    documents: list[dict] = []
    source_map: dict[str, dict] = {}
    claim_map: dict[str, list[dict]] = {}
    tag_map: dict[str, list[dict]] = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 5:
            continue
        # Row 4 (index 3) is the header row in most sheets
        header_row = None
        header_idx = None
        for idx in range(min(5, len(rows))):
            row = rows[idx]
            if row and any(c and isinstance(c, str) and (
                "_ID" in str(c) or "标题" in str(c) or "Card_ID" in str(c)
                or "标签组" in str(c) or "Source_ID" in str(c) or "Claim_ID" in str(c)
                or "字段名" in str(c)
            ) for c in row):
                header_row = [str(c).strip() if c else "" for c in row]
                header_idx = idx
                break
        if not header_row:
            continue

        # Build column index map
        col_map: dict[int, str] = {}
        for ci, col_name in enumerate(header_row):
            if col_name:
                col_map[ci] = col_name

        is_content = sheet_name in CONTENT_SHEETS

        if sheet_name == SOURCE_SHEET:
            for ri in range(header_idx + 1, len(rows)):
                row = rows[ri]
                if not row or not row[0]:
                    continue
                record = {}
                for ci, name in col_map.items():
                    if ci < len(row) and row[ci] is not None:
                        record[name] = str(row[ci]).strip()
                sid = record.get("Source_ID", "")
                if sid:
                    source_map[sid] = record

        elif sheet_name == CLAIM_SHEET:
            for ri in range(header_idx + 1, len(rows)):
                row = rows[ri]
                if not row or not row[0]:
                    continue
                record = {}
                for ci, name in col_map.items():
                    if ci < len(row) and row[ci] is not None:
                        record[name] = str(row[ci]).strip()
                cid = record.get("Claim_ID", "")
                if cid:
                    claim_map.setdefault(cid, []).append(record)

        elif sheet_name == TAG_SHEET:
            current_group = ""
            for ri in range(header_idx + 1, len(rows)):
                row = rows[ri]
                if not row:
                    continue
                group = str(row[0]).strip() if row[0] else ""
                value = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                definition = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                if group:
                    current_group = group
                if value:
                    tag_map.setdefault(current_group, []).append({
                        "tag": value,
                        "definition": definition,
                    })

        elif is_content:
            for ri in range(header_idx + 1, len(rows)):
                row = rows[ri]
                if not row or not row[0]:
                    continue
                record = {}
                text_parts: list[str] = []
                source_ids: list[str] = []
                claim_ids: list[str] = []
                entity_id = ""
                title = ""
                tags = ""

                for ci, name in col_map.items():
                    if ci >= len(row) or row[ci] is None:
                        continue
                    val = str(row[ci]).strip()
                    if not val:
                        continue
                    record[name] = val

                    if name in ("Source_ID", "Source_IDs"):
                        for s in re.split(r'[;，,]', val):
                            s = s.strip()
                            if s:
                                source_ids.append(s)
                    elif name in ("Claim_ID", "Claim_IDs"):
                        for c in re.split(r'[;，,]', val):
                            c = c.strip()
                            if c:
                                claim_ids.append(c)
                    elif name in ("Person_ID", "Detail_ID", "Card_ID", "Target_Instance_ID"):
                        if not entity_id:
                            entity_id = val
                    elif name == "标题":
                        title = val
                    elif name == "检索标签":
                        tags = val

                    if is_text_field(name):
                        text_parts.append(val)

                if not text_parts:
                    continue

                full_text = " ".join(text_parts)
                tokens = tokenize(full_text)

                doc = {
                    "doc_id": f"{sheet_name}#{ri + 1}",
                    "sheet": sheet_name,
                    "row": ri + 1,
                    "entity_id": entity_id,
                    "title": title or text_parts[0][:60] if text_parts else "",
                    "tags": tags,
                    "source_ids": source_ids,
                    "claim_ids": claim_ids,
                    "fields": record,
                    "text": full_text,
                    "tokens": tokens,
                    "token_set": list(set(tokens)),
                    "fingerprint": row_fingerprint(sheet_name, ri + 1),
                }
                documents.append(doc)

    wb.close()
    return documents, source_map, claim_map, tag_map


def build_inverted_index(documents: list[dict]) -> dict[str, list[tuple[int, int]]]:
    """Build inverted index: token -> [(doc_index, term_freq), ...]"""
    index: dict[str, list[tuple[int, int]]] = {}
    for di, doc in enumerate(documents):
        token_freq: dict[str, int] = {}
        for token in doc["tokens"]:
            token_freq[token] = token_freq.get(token, 0) + 1
        for token, freq in token_freq.items():
            index.setdefault(token, []).append((di, freq))
    return index


def compute_idf(documents: list[dict], inverted_index: dict[str, list[tuple[int, int]]]) -> dict[str, float]:
    """Compute IDF for each token."""
    n_docs = len(documents)
    idf: dict[str, float] = {}
    for token, postings in inverted_index.items():
        df = len(postings)
        idf[token] = math.log((n_docs + 1) / (df + 1)) + 1.0
    return idf


def search_index(
    documents: list[dict],
    inverted_index: dict[str, list[tuple[int, int]]],
    idf: dict[str, float],
    query: str,
    sheet_filter: str | None = None,
    tag_filter: str | None = None,
    top_k: int = 10,
    min_score: float = 0.01,
    allowed_indices: set[int] | None = None,
) -> list[dict]:
    """Search the index with a query string. Returns ranked results with provenance."""
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # Accumulate scores per document
    scores: dict[int, float] = {}
    matched_terms: dict[int, set[str]] = {}

    for token in query_tokens:
        postings = inverted_index.get(token)
        if not postings:
            continue
        token_idf = idf.get(token, 1.0)
        for di, freq in postings:
            if allowed_indices is not None and di not in allowed_indices:
                continue
            doc = documents[di]
            # Apply filters
            if sheet_filter and sheet_filter not in doc["sheet"]:
                continue
            if tag_filter and tag_filter not in doc.get("tags", ""):
                continue
            # TF-IDF score
            tf = 1.0 + math.log(freq)
            score = tf * token_idf
            scores[di] = scores.get(di, 0.0) + score
            matched_terms.setdefault(di, set()).add(token)

    # Boost: documents with more unique query token matches get a boost
    for di in scores:
        coverage_ratio = len(matched_terms[di]) / len(query_tokens)
        scores[di] *= (0.5 + 0.5 * coverage_ratio)

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results: list[dict] = []
    for di, score in ranked[:top_k]:
        if score < min_score:
            break
        doc = documents[di]
        results.append({
            "rank": len(results) + 1,
            "doc_index": di,
            "score": round(score, 4),
            "sparse_score": round(score, 6),
            "matched_terms": sorted(matched_terms[di]),
            "doc_id": doc["doc_id"],
            "sheet": doc["sheet"],
            "row": doc["row"],
            "entity_id": doc["entity_id"],
            "title": doc["title"],
            "tags": doc["tags"],
            "source_ids": doc["source_ids"],
            "claim_ids": doc["claim_ids"],
            "text_preview": doc["text"][:300],
            "fields": doc["fields"],
        })
    return results


def dense_search(
    documents: list[dict],
    embeddings: Any,
    query_vector: Any,
    sheet_filter: str | None,
    tag_filter: str | None,
    limit: int,
    allowed_indices: set[int] | None = None,
) -> list[dict[str, Any]]:
    scores = embeddings @ query_vector
    candidates: list[tuple[int, float]] = []
    for index, score in enumerate(scores.tolist()):
        if allowed_indices is not None and index not in allowed_indices:
            continue
        doc = documents[index]
        if sheet_filter and sheet_filter not in doc["sheet"]:
            continue
        if tag_filter and tag_filter not in doc.get("tags", ""):
            continue
        candidates.append((index, float(score)))
    candidates.sort(key=lambda item: item[1], reverse=True)
    return [
        {"doc_index": index, "rank": rank, "dense_score": score}
        for rank, (index, score) in enumerate(candidates[:limit], 1)
    ]


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    sparse_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fused: dict[int, dict[str, Any]] = {}
    for mode, results in (("dense", dense_results), ("sparse", sparse_results)):
        for rank, result in enumerate(results, 1):
            index = int(result["doc_index"])
            item = fused.setdefault(index, {
                "doc_index": index,
                "dense_score": None,
                "sparse_score": None,
                "final_score": 0.0,
            })
            item[f"{mode}_score"] = result.get(f"{mode}_score", result.get("score"))
            item["final_score"] += 1.0 / (RRF_K + rank)
    return sorted(fused.values(), key=lambda item: item["final_score"], reverse=True)


def dedupe_key(document: dict[str, Any]) -> str:
    if document.get("entity_id"):
        return f"entity:{document['entity_id']}"
    normalized = re.sub(r"\s+", "", document.get("text", "")).lower()[:240]
    sources = ",".join(sorted(document.get("source_ids", [])))
    return hashlib.sha1(f"{sources}|{normalized}".encode("utf-8")).hexdigest()


def build_hybrid_results(
    documents: list[dict[str, Any]],
    fused_results: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fused in fused_results:
        document = documents[int(fused["doc_index"])]
        key = dedupe_key(document)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "rank": len(results) + 1,
            "dense_score": None if fused["dense_score"] is None else round(float(fused["dense_score"]), 6),
            "sparse_score": None if fused["sparse_score"] is None else round(float(fused["sparse_score"]), 6),
            "final_score": round(float(fused["final_score"]), 8),
            "doc_id": document["doc_id"],
            "sheet": document["sheet"],
            "row": document["row"],
            "entity_id": document.get("entity_id", ""),
            "title": document.get("title", ""),
            "tags": document.get("tags", ""),
            "source_ids": document.get("source_ids", []),
            "claim_ids": document.get("claim_ids", []),
            "timeliness_status": document.get("fields", {}).get("时效状态", document.get("fields", {}).get("当前有效性", "")),
            "text_preview": document.get("text", "")[:500],
            "fields": document.get("fields", {}),
        })
        if len(results) >= top_k:
            break
    return results


def enrich_with_provenance(results: list[dict], source_map: dict, claim_map: dict) -> list[dict]:
    """Add source and claim details to search results for traceability."""
    for result in results:
        sources = []
        for sid in result.get("source_ids", []):
            if sid in source_map:
                src = source_map[sid]
                sources.append({
                    "Source_ID": sid,
                    "title": src.get("标题", ""),
                    "type": src.get("来源类型", ""),
                    "publisher": src.get("发布者", ""),
                    "date": src.get("日期", ""),
                    "url": src.get("URL/路径", ""),
                    "evidence_level": src.get("一级证据层级", ""),
                    "validity": src.get("版本状态", ""),
                })
        result["sources"] = sources

        claims = []
        for cid in result.get("claim_ids", []):
            if cid in claim_map:
                for claim in claim_map[cid]:
                    claims.append({
                        "Claim_ID": cid,
                        "type": claim.get("Claim类型", ""),
                        "field": claim.get("字段/主题", ""),
                        "fact": claim.get("具体事实", "")[:200],
                        "status": claim.get("事实状态", ""),
                        "source_id": claim.get("Source_ID", ""),
                        "evidence_level": claim.get("证据等级", ""),
                    })
        result["claims"] = claims
        evidence_levels = [item.get("evidence_level", "") for item in sources + claims]
        result["evidence_level"] = next((level for level in evidence_levels if level), "")

    return results


PREBUILT_FILES = (
    "index_meta.json", "documents.json", "sparse_index.json",
    "sources.json", "claims.json", "tags.json", "embeddings.npy",
)


def command_init_prebuilt(args: argparse.Namespace) -> None:
    """Copy a prebuilt index bundle (ships with the Skill) into the workspace.

    ZERO model download / encoding on the target machine: the target only
    copies JSON + npy files. The bundle's tier / kb_version are reported so
    the caller can verify consistency with the workspace knowledge base.
    """
    from caplab_index import install_index
    report = install_index(args.prebuilt, args.index_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def command_init(args: argparse.Namespace) -> None:
    if getattr(args, "prebuilt", None):
        return command_init_prebuilt(args)
    if not getattr(args, "excel", None):
        print("ERROR: either --excel or --prebuilt is required for init", file=sys.stderr)
        sys.exit(2)
    excel_path = Path(args.excel).resolve()
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}", file=sys.stderr)
        sys.exit(1)

    index_dir = Path(args.index_dir).resolve()
    index_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading Excel: {excel_path}")
    tier = detect_tier_from_filename(excel_path, getattr(args, "tier", None))
    kb_version = detect_kb_version(excel_path)
    documents, source_map, claim_map, tag_map = load_excel_to_documents(excel_path)

    print(f"  Documents indexed: {len(documents)}")
    print(f"  Sources loaded: {len(source_map)}")
    print(f"  Claims loaded: {sum(len(v) for v in claim_map.values())}")
    print(f"  Tag groups: {len(tag_map)}")
    print(f"  Knowledge base tier: {tier}")
    print(f"  Knowledge base version: {kb_version}")

    inverted_index = build_inverted_index(documents)
    idf = compute_idf(documents, inverted_index)

    print(f"  Inverted index tokens: {len(inverted_index)}")

    dense_enabled = not args.sparse_only
    embedding_dimension = 0
    embedding_source = "none"
    if dense_enabled:
        workspace = Path(args.workspace).resolve() if args.workspace else None
        # channel 1: local sentence-transformers (maintainer rebuild path)
        try:
            np, encoder = load_encoder(workspace, index_dir, args.model, args.allow_download)
            embeddings = encode_texts(encoder, [doc["text"] for doc in documents]).astype("float32")
            embedding_source = f"local:{args.model}"
        except Exception as exc:
            # channel 2: Qianfan / OpenAI-compatible embedding API (optional)
            api_cfg_path = getattr(args, "embedding_api", None)
            import caplab_encoder
            api_cfg = caplab_encoder.api_config_from(Path(api_cfg_path) if api_cfg_path else None)
            if api_cfg is not None:
                import numpy as np
                texts = [doc["text"] for doc in documents]
                print(f"  Encoding {len(texts)} documents via API model {api_cfg.get('embedding_model')} ...")
                vectors = [caplab_encoder.encode_api(text, api_cfg) for text in texts]
                embeddings = np.asarray(vectors, dtype="float32")
                embedding_source = f"api:{api_cfg.get('embedding_model')}"
            else:
                print(
                    f"WARNING: local encoder unavailable ({exc}); building a sparse-only index. "
                    "For a dense index use --allow-download (local torch) or --embedding-api <config>.",
                    file=sys.stderr,
                )
                dense_enabled = False
        if dense_enabled:
            embedding_dimension = int(embeddings.shape[1])
            atomic_save_npy(index_dir / "embeddings.npy", embeddings, np)
            print(f"  Dense embeddings: {embeddings.shape[0]} x {embeddings.shape[1]} (source: {embedding_source})")

    # Save index files
    index_meta = {
        "index_version": INDEX_VERSION,
        "script_version": SCRIPT_VERSION,
        "tier": tier,
        "kb_version": kb_version,
        "created_at": now_iso(),
        "excel_path": str(excel_path),
        "excel_filename": excel_path.name,
        "excel_sha256": file_sha256(excel_path),
        "document_count": len(documents),
        "source_count": len(source_map),
        "claim_count": sum(len(v) for v in claim_map.values()),
        "tag_group_count": len(tag_map),
        "token_count": len(inverted_index),
        "dense_enabled": dense_enabled,
        "embedding_model": args.model if dense_enabled and embedding_source.startswith("local") else None,
        "embedding_source": embedding_source if dense_enabled else "none",
        "embedding_dimension": embedding_dimension,
        "retrieval": "bge_dense+tfidf_sparse+rrf" if dense_enabled else "tfidf_sparse_only",
        "sheets_indexed": sorted(set(doc["sheet"] for doc in documents)),
    }

    atomic_write(index_dir / "index_meta.json", index_meta)
    atomic_write(index_dir / "documents.json", documents)
    atomic_write(index_dir / "sparse_index.json", {
        "inverted_index": {k: v for k, v in inverted_index.items()},
        "idf": idf,
    })
    atomic_write(index_dir / "sources.json", source_map)
    atomic_write(index_dir / "claims.json", claim_map)
    atomic_write(index_dir / "tags.json", tag_map)

    from caplab_index import seal_index
    seal_index(index_dir)
    print(f"Index saved to: {index_dir}")
    print(f"INITIALIZED {len(documents)} documents, {len(inverted_index)} tokens, dense={dense_enabled}")


def command_search(args: argparse.Namespace) -> None:
    from caplab_access import select_index
    index_dir, access = select_index(args)
    meta = load_json(index_dir / "index_meta.json")
    documents = load_json(index_dir / "documents.json")
    sparse_bundle = load_json(index_dir / "sparse_index.json")
    inverted_index = sparse_bundle["inverted_index"]
    idf = sparse_bundle["idf"]
    source_map = load_json(index_dir / "sources.json")
    claim_map = load_json(index_dir / "claims.json")

    from caplab_quality import filter_documents
    allowed, quality, quality_report = filter_documents(documents, source_map, claim_map)

    # Convert inverted_index keys back from JSON (string keys)
    inverted_index_typed: dict[str, list[tuple[int, int]]] = {}
    for token, postings in inverted_index.items():
        inverted_index_typed[token] = [tuple(p) for p in postings]
    idf_typed = {k: float(v) for k, v in idf.items()}

    candidate_limit = max(args.top_k * 10, 50)
    sparse_results = search_index(
        documents, inverted_index_typed, idf_typed,
        query=args.query,
        sheet_filter=args.sheet,
        tag_filter=args.tag,
        top_k=candidate_limit,
        min_score=args.min_score,
        allowed_indices=allowed,
    )
    retrieval_mode = "sparse_fallback"
    degradation_reason = None
    embedding_channel = "none"
    dense_results: list[dict[str, Any]] = []
    embeddings_path = index_dir / "embeddings.npy"
    if meta.get("dense_enabled") and embeddings_path.exists() and not args.sparse_only:
        try:
            import numpy as np
            import caplab_encoder
            workspace = Path(args.workspace).resolve() if args.workspace else None
            onnx_dirs: list[Path] = []
            if workspace is not None:
                onnx_dirs.append(workspace / ".caplab" / "models")
            onnx_dirs.append(Path(__file__).resolve().parent.parent / "assets" / "models")
            api_cfg = caplab_encoder.api_config_from(
                Path(args.api_config) if getattr(args, "api_config", None) else None
            )
            expected_dim = int(meta.get("embedding_dimension") or 0) or None
            query_vector, channel, note = caplab_encoder.encode_query(
                args.query, onnx_dirs=onnx_dirs, api_cfg=api_cfg, expected_dim=expected_dim,
            )
            embedding_channel = channel
            if query_vector is not None:
                embeddings = np.load(embeddings_path, mmap_mode="r")
                if len(embeddings) != len(documents):
                    raise RuntimeError("embedding row count does not match documents")
                dense_results = dense_search(
                    documents, embeddings, query_vector,
                    args.sheet, args.tag, candidate_limit, allowed_indices=allowed,
                )
                retrieval_mode = "api_embedding" if channel == "api" else "hybrid_dense_sparse"
            else:
                degradation_reason = (
                    f"dense query encoding unavailable ({note}); using sparse fallback"
                )
        except Exception as exc:
            degradation_reason = str(exc)
    elif args.sparse_only:
        degradation_reason = "sparse-only mode requested"
    else:
        degradation_reason = "dense index or embeddings.npy is unavailable"

    fused = reciprocal_rank_fusion(dense_results, sparse_results)
    results = build_hybrid_results(documents, fused, args.top_k)
    results = enrich_with_provenance(results, source_map, claim_map)

    by_id = {d["doc_id"]: quality[i] for i, d in enumerate(documents)}
    for result in results:
        result["quality"] = by_id[result["doc_id"]]

    output = {
        "quality_filter": quality_report,
        "coverage_status": "results_available" if results else "insufficient_eligible_evidence",
        "user_access": access,
        "query": args.query,
        "sheet_filter": args.sheet,
        "tag_filter": args.tag,
        "retrieval_mode": retrieval_mode,
        "degraded": retrieval_mode == "sparse_fallback",
        "degradation_reason": degradation_reason,
        "embedding_channel": embedding_channel,
        "total_results": len(results),
        "index_meta": {
            "document_count": meta["document_count"],
            "index_version": meta["index_version"],
            "tier": meta.get("tier", "unknown"),
            "kb_version": meta.get("kb_version", ""),
            "created_at": meta["created_at"],
            "embedding_model": meta.get("embedding_model"),
            "embedding_dimension": meta.get("embedding_dimension", 0),
            "excel_sha256": meta.get("excel_sha256", ""),
        },
        "results": results,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


def command_stats(args: argparse.Namespace) -> None:
    index_dir = Path(args.index_dir).resolve()
    meta = load_json(index_dir / "index_meta.json")
    documents = load_json(index_dir / "documents.json")
    tag_map = load_json(index_dir / "tags.json")

    # Count documents per sheet
    sheet_counts: dict[str, int] = {}
    for doc in documents:
        sheet_counts[doc["sheet"]] = sheet_counts.get(doc["sheet"], 0) + 1

    print(f"=== CapLab RAG Index Statistics ===")
    print(f"Index version: {meta['index_version']}")
    print(f"Script version: {meta['script_version']}")
    print(f"Knowledge base tier: {meta.get('tier', 'unknown')}")
    print(f"Knowledge base version: {meta.get('kb_version', '') or 'unknown'}")
    print(f"Created at: {meta['created_at']}")
    print(f"Excel source: {meta['excel_filename']}")
    print(f"Total documents: {meta['document_count']}")
    print(f"Total sources: {meta['source_count']}")
    print(f"Total claims: {meta['claim_count']}")
    print(f"Tag groups: {meta['tag_group_count']}")
    print(f"Indexed tokens: {meta['token_count']}")
    print(f"Dense enabled: {meta.get('dense_enabled', False)}")
    print(f"Embedding model: {meta.get('embedding_model') or 'none'}")
    print(f"Embedding source: {meta.get('embedding_source') or 'none'}")
    print(f"Embedding dimension: {meta.get('embedding_dimension', 0)}")
    print(f"Excel SHA-256: {meta.get('excel_sha256', 'unknown')}")
    print()
    print("Documents per sheet:")
    for sheet, count in sorted(sheet_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sheet}: {count}")
    print()
    print("Tag groups:")
    for group, tags in tag_map.items():
        print(f"  {group}: {len(tags)} tags")


def command_export(args: argparse.Namespace) -> None:
    from caplab_access import select_index
    index_dir, access = select_index(args)
    documents = load_json(index_dir / "documents.json")

    from caplab_quality import filter_documents
    allowed, quality, report = filter_documents(documents, load_json(index_dir / "sources.json"), load_json(index_dir / "claims.json"))
    filtered = [dict(doc, quality=quality[i]) for i, doc in enumerate(documents) if i in allowed and args.sheet in doc["sheet"]]
    if not filtered:
        print(f"No documents found for sheet: {args.sheet}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else Path.cwd() / "caplab-export.json"
    atomic_write(output_path, filtered)
    print(f"Exported {len(filtered)} documents to {output_path}")


# --- Utility functions ---

def atomic_write(path: Path, value: Any) -> None:
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_save_npy(path: Path, value: Any, np: Any) -> None:
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".npy", dir=path.parent)
    os.close(fd)
    try:
        np.save(tmp_name, value, allow_pickle=False)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="caplab_rag", description="CapLab hybrid vector RAG (v2.1.1)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Build index from Excel, or copy a prebuilt bundle")
    p.add_argument("--excel", default=None, help="Path to the Excel knowledge base file (rebuild path)")
    p.add_argument("--prebuilt", default=None, help="Copy a prebuilt index bundle; zero model download/encoding")
    p.add_argument("--index-dir", required=True, help="Directory to store the index files")
    p.add_argument("--workspace", default=None, help="CapLab workspace containing .caplab/deps and models")
    p.add_argument("--model", default=DEFAULT_MODEL, help="SentenceTransformers model name or local path")
    p.add_argument("--allow-download", action="store_true", help="Allow model download after explicit user approval")
    p.add_argument("--embedding-api", default=None,
                   help="Path to an API config JSON (Qianfan/OpenAI-compatible) used to rebuild dense vectors")
    p.add_argument("--sparse-only", action="store_true", help="Build a sparse-only degraded index")
    p.add_argument("--tier", default=None, choices=["free", "paid", "免费", "付费"],
                   help="Knowledge base tier; auto-detected from the Excel file name when omitted")
    p.set_defaults(func=command_init)

    p = sub.add_parser("search", help="Search the knowledge base")
    p.add_argument("--index-dir", default=None, help="Optional index; must match user entitlement")
    p.add_argument("--user-id", default=None)
    p.add_argument("--session-id", default=None)
    p.add_argument("--query", required=True, help="Search query text")
    p.add_argument("--workspace", default=None, help="CapLab workspace containing .caplab/deps and models")
    p.add_argument("--sheet", default=None, help="Filter by sheet name (partial match)")
    p.add_argument("--tag", default=None, help="Filter by tag (partial match)")
    p.add_argument("--top-k", type=int, default=10, help="Maximum number of results")
    p.add_argument("--min-score", type=float, default=0.01, help="Minimum score threshold")
    p.add_argument("--api-config", default=None,
                   help="Path to an API config JSON for the api embedding channel (optional)")
    p.add_argument("--sparse-only", action="store_true", help="Force explicit sparse fallback")
    p.set_defaults(func=command_search)

    p = sub.add_parser("stats", help="Show index coverage statistics")
    p.add_argument("--index-dir", required=True, help="Path to the index directory")
    p.set_defaults(func=command_stats)

    p = sub.add_parser("export", help="Export a sheet as JSON")
    p.add_argument("--index-dir", default=None)
    p.add_argument("--workspace", default=None)
    p.add_argument("--user-id", default=None)
    p.add_argument("--session-id", default=None)
    p.add_argument("--sheet", required=True, help="Sheet name to export (partial match)")
    p.add_argument("--output", default=None, help="Output file path")
    p.set_defaults(func=command_export)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
