"""v2.0.1 bootstrap shim: knowledge readiness == prebuilt RAG index readiness.

Keeps the v1.4.1 interface (BootstrapError, knowledge_workspace, ensure_knowledge,
require_ready) that caplab_state.py / caplab_knowledge.py rely on, but the
"knowledge" being checked is now the RAG index under <workspace>/.caplab/
knowledge_index (built by `caplab_rag.py init --prebuilt` or from Excel).

The v1.4.1 built-in seed installation is gone; passing --seed is accepted and
ignored with a warning (no bundled seed exists in v2.0.1).
Windows-safe: no fcntl locks.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


class BootstrapError(Exception):
    pass


def knowledge_workspace(state_root):
    """V1 layout: state and knowledge are siblings under .caplab."""
    state_root = Path(state_root).resolve()
    if state_root.name == "state" and state_root.parent.name == ".caplab":
        return state_root.parent
    return state_root


def default_seed():
    raise BootstrapError("v2.0.1 removed the built-in knowledge seed; use caplab_rag.py init --prebuilt")


def _index_dir(workspace) -> Path:
    return Path(workspace).resolve() / "knowledge_index"


def _index_meta(workspace) -> dict | None:
    index = _index_dir(workspace)
    if not index.exists():
        return None
    from caplab_index import validate_index, IndexError
    try:
        return validate_index(index)
    except (IndexError, OSError) as exc:
        raise BootstrapError(f"index integrity failed: {exc}") from exc


def inspect_knowledge(workspace, require_provenance=True):
    meta = _index_meta(workspace)
    if meta is None:
        if require_provenance:
            raise BootstrapError("knowledge index missing; run caplab_rag.py init --prebuilt")
        return {"knowledge_root": str(_index_dir(workspace)), "source_count": 0, "card_count": 0,
                "card_status_counts": {}, "origin": "unregistered_existing"}
    return {
        "knowledge_root": str(_index_dir(workspace)),
        "source_count": meta.get("source_count", 0),
        "card_count": meta.get("document_count", 0),
        "card_status_counts": {"indexed": meta.get("document_count", 0)},
        "origin": "prebuilt_index",
        "tier": meta.get("tier"),
        "kb_version": meta.get("kb_version"),
        "dense_enabled": meta.get("dense_enabled", False),
    }


def ensure_knowledge(workspace, seed=None, allow_temporary=False):
    """Ensure the RAG index is ready. No download, no encoding.

    Returns a report dict compatible with caplab_state.command_bootstrap:
    {status, source_count, card_count, ...}. If the index is missing and this
    is a temporary/test call, returns status 'index_missing' instead of
    raising; otherwise raises BootstrapError with the exact remedy.
    """
    root = Path(workspace).resolve()
    temporary_roots = (Path("/tmp").resolve(), Path(tempfile.gettempdir()).resolve(), Path("/private/var/folders"))
    if not allow_temporary and any(root == p or p in root.parents for p in temporary_roots):
        raise BootstrapError("temporary workspace refused; --allow-temporary is for tests only")
    root.mkdir(parents=True, exist_ok=True)
    if seed:
        print("WARNING: v2.0.1 ignores --seed (built-in seed removed)", file=sys.stderr)
    meta = _index_meta(root)
    if meta is None:
        raise BootstrapError(
            "knowledge index missing; run caplab_rag.py init --prebuilt "
            "<skill>/assets/prebuilt_index/<free|paid>"
        )
    return {"status": "reused", "source_count": meta.get("source_count", 0),
            "card_count": meta.get("document_count", 0),
            "tier": meta.get("tier"), "kb_version": meta.get("kb_version"),
            "dense_enabled": meta.get("dense_enabled", False),
            "knowledge_root": str(_index_dir(root))}


def require_ready(root):
    try:
        return inspect_knowledge(root)
    except (BootstrapError, OSError, ValueError, KeyError, TypeError) as exc:
        raise BootstrapError(f"knowledge unavailable or not ready: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description="CapLab v2.0.1 bootstrap shim (prebuilt index readiness)")
    parser.add_argument("--root", required=True)
    parser.add_argument("--seed")
    parser.add_argument("--allow-temporary", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(ensure_knowledge(args.root, args.seed, args.allow_temporary),
                         ensure_ascii=False, indent=2))
        return 0
    except (BootstrapError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
