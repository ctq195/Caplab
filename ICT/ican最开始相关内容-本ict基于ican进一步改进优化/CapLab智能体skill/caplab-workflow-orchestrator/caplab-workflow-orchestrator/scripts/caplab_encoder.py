#!/usr/bin/env python3
"""Query-side encoders for CapLab hybrid RAG (v2.0.1).

Three channels are available; the caller (caplab_rag.py) tries them in order
and records which one actually ran:

  1. local_onnx  - Bundled int8 BGE model (assets/models/bge-small-zh-v1.5-int8)
                   run through onnxruntime. Fully offline, no torch, ~30 MB.
  2. api         - Qianfan / any OpenAI-compatible embedding API. Online,
                   configured via a JSON file or environment variables.
  3. (none)      - Caller falls back to sparse TF-IDF retrieval and says so.

Dimension consistency: the API model's embedding dimension MUST equal the
index's embedding_dimension recorded in index_meta.json. If it does not, the
api channel is skipped and the caller is told exactly why. The local ONNX
channel always produces 512-dim vectors matching the prebuilt BGE index.
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Optional


class EncoderError(Exception):
    """Raised when a requested encoding channel cannot run."""


# --- model discovery -------------------------------------------------------

def onnx_model_dir(candidates: list[Optional[Path]]) -> Optional[Path]:
    """Return the first candidate directory containing a usable int8 ONNX model."""
    for base in candidates:
        if base is None:
            continue
        base = Path(base)
        if not base.is_dir():
            continue
        # accept either a direct model dir or a nested bge-small-zh-v1.5-int8 dir
        for cand in (base, base / "bge-small-zh-v1.5-int8"):
            if not cand.is_dir():
                continue
            if (cand / "model_quantized.onnx").is_file() and (
                (cand / "tokenizer.json").is_file() or (cand / "vocab.txt").is_file()
            ):
                return cand
    return None


def api_config_from(cfg_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Load the embedding/chat API config from file or environment variables.

    Priority: explicit --api-config file > <workspace>/.caplab/qianfan-config.json
              > environment variables (CAPLAB_API_BASE_URL, CAPLAB_API_KEY,
                CAPLAB_EMBEDDING_MODEL, CAPLAB_CHAT_MODEL, CAPLAB_EMBEDDING_DIM).
    Returns None when no usable API credentials are configured.
    """
    candidates: list[Path] = []
    if cfg_path is not None:
        candidates.append(Path(cfg_path))
    candidates.append(Path(".caplab") / "qianfan-config.json")
    for cand in candidates:
        if cand.is_file():
            try:
                cfg = json.loads(cand.read_text(encoding="utf-8"))
                if cfg.get("api_key") and (cfg.get("base_url") or cfg.get("embedding_model")):
                    return cfg
            except Exception:
                continue

    base_url = os.environ.get("CAPLAB_API_BASE_URL")
    api_key = os.environ.get("CAPLAB_API_KEY")
    if not api_key:
        return None
    cfg: dict[str, Any] = {"api_key": api_key}
    if base_url:
        cfg["base_url"] = base_url
    if os.environ.get("CAPLAB_EMBEDDING_MODEL"):
        cfg["embedding_model"] = os.environ["CAPLAB_EMBEDDING_MODEL"]
    if os.environ.get("CAPLAB_CHAT_MODEL"):
        cfg["chat_model"] = os.environ["CAPLAB_CHAT_MODEL"]
    if os.environ.get("CAPLAB_EMBEDDING_DIM"):
        try:
            cfg["embedding_dimension"] = int(os.environ["CAPLAB_EMBEDDING_DIM"])
        except ValueError:
            pass
    return cfg


# --- local ONNX channel -----------------------------------------------------

def _load_tokenizer(model_dir: Path):
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise EncoderError(
            "tokenizers is required for the local ONNX channel; "
            "install with: pip install tokenizers"
        ) from exc
    tok_path = model_dir / "tokenizer.json"
    if tok_path.is_file():
        return Tokenizer.from_file(str(tok_path))
    raise EncoderError(f"tokenizer.json not found in {model_dir}")


def _load_session(model_dir: Path):
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise EncoderError(
            "onnxruntime is required for the local ONNX channel; "
            "install with: pip install onnxruntime"
        ) from exc
    onnx_path = model_dir / "model_quantized.onnx"
    if not onnx_path.is_file():
        onnx_path = model_dir / "model.onnx"
    if not onnx_path.is_file():
        raise EncoderError(f"no onnx model found in {model_dir}")
    so = ort.SessionOptions()
    so.log_severity_level = 3
    try:
        return ort.InferenceSession(str(onnx_path), sess_options=so, providers=["CPUExecutionProvider"])
    except Exception as exc:
        raise EncoderError(f"failed to load ONNX session: {exc}") from exc


def encode_onnx(
    query: str,
    model_dir: Path,
    max_len: int = 512,
) -> list[float]:
    """Encode a single query with the bundled int8 BGE model.

    Mirrors the prebuilt index's normalisation (no query instruction, CLS
    pooling, L2 normalise) so the vector lives in the same space.
    """
    import numpy as np

    tokenizer = _load_tokenizer(model_dir)
    session = _load_session(model_dir)

    tokenizer.enable_truncation(max_length=max_len)
    tokenizer.enable_padding(length=max_len, pad_id=0, pad_token="[PAD]")
    encoded = tokenizer.encode(query)

    input_ids = np.asarray([encoded.ids], dtype=np.int64)
    attention_mask = np.asarray([encoded.attention_mask], dtype=np.int64)
    try:
        outputs = session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": np.zeros_like(input_ids),
            },
        )
    except Exception as exc:
        raise EncoderError(f"ONNX inference failed: {exc}") from exc

    # sentence-transformers uses last_hidden_state with CLS pooling for BERT
    last_hidden = outputs[0]
    if last_hidden.ndim == 3:
        vector = last_hidden[0, 0, :].astype("float32")
    elif last_hidden.ndim == 2:
        vector = last_hidden[0].astype("float32")
    else:
        raise EncoderError(f"unexpected ONNX output shape: {last_hidden.shape}")

    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector = vector / norm
    return [float(x) for x in vector]


# --- API channel -------------------------------------------------------------

def encode_api(query: str, cfg: dict[str, Any], timeout: int = 30) -> list[float]:
    """Encode a single query via an OpenAI-compatible embedding endpoint."""
    model = cfg.get("embedding_model")
    if not model:
        raise EncoderError("embedding_model is not set in the API config")
    base_url = (cfg.get("base_url") or "https://qianfan.baidubce.com/v2").rstrip("/")
    api_key = cfg.get("api_key")
    if not api_key:
        raise EncoderError("api_key is not set in the API config")

    url = f"{base_url}/embeddings"
    payload = {"model": model, "input": query}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise EncoderError(f"embedding API request failed: {exc}") from exc

    try:
        vector = result["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise EncoderError(f"unexpected embedding API response: {str(result)[:300]}") from exc
    if not isinstance(vector, list) or not vector:
        raise EncoderError("embedding API returned an empty vector")

    # L2 normalise so cosine similarity via dot product stays valid
    norm = math.sqrt(sum(float(x) * float(x) for x in vector))
    if norm > 0:
        vector = [float(x) / norm for x in vector]
    return vector


# --- dispatcher --------------------------------------------------------------

def encode_query(
    query: str,
    *,
    onnx_dirs: Optional[list[Optional[Path]]] = None,
    api_cfg: Optional[dict[str, Any]] = None,
    expected_dim: Optional[int] = None,
) -> tuple[Optional[list[float]], str, Optional[str]]:
    """Try channels in order: local ONNX -> API.

    Returns (vector, channel, note). channel is one of
    'local_onnx', 'api', or '' (nothing available). note explains skips/errors.
    """
    if not query or not query.strip():
        return None, "", "empty query"

    # 1. local ONNX (preferred: offline, deterministic, no per-call cost)
    if onnx_dirs:
        model_dir = onnx_model_dir(list(onnx_dirs))
        if model_dir is not None:
            try:
                vector = encode_onnx(query.strip(), model_dir)
                dim = len(vector)
                if expected_dim is not None and dim != expected_dim:
                    return None, "", (
                        f"local ONNX model dimension {dim} != index dimension {expected_dim}"
                    )
                return vector, "local_onnx", f"model={model_dir.name}"
            except EncoderError as exc:
                note = str(exc)
        else:
            note = "no bundled ONNX model found"
    else:
        note = "no model search path provided"

    # 2. API
    if api_cfg:
        try:
            vector = encode_api(query.strip(), api_cfg)
            dim = len(vector)
            cfg_dim = api_cfg.get("embedding_dimension")
            if cfg_dim is not None and dim != int(cfg_dim):
                return None, "", (
                    f"API model dimension {dim} != configured dimension {cfg_dim}"
                )
            if expected_dim is not None and dim != expected_dim:
                return None, "", (
                    f"API model dimension {dim} != index dimension {expected_dim}; "
                    "rebuild the index with this API model to use the api channel"
                )
            return vector, "api", f"model={api_cfg.get('embedding_model')}"
        except EncoderError as exc:
            note = f"{note}; api: {exc}"
    else:
        note = f"{note}; no API config"

    return None, "", note


def main() -> int:
    parser = __import__("argparse").ArgumentParser(
        prog="caplab_encoder",
        description="Encode one query with the local ONNX channel (self-test).",
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--api-config", default=None)
    args = parser.parse_args()

    cfg = api_config_from(Path(args.api_config) if args.api_config else None)
    dirs = [Path(args.model_dir)] if args.model_dir else []
    vector, channel, note = encode_query(args.query, onnx_dirs=dirs, api_cfg=cfg)
    if vector is None:
        print(json.dumps({"ok": False, "channel": channel, "note": note}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "ok": True,
        "channel": channel,
        "note": note,
        "dimension": len(vector),
        "head": [round(x, 6) for x in vector[:8]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
