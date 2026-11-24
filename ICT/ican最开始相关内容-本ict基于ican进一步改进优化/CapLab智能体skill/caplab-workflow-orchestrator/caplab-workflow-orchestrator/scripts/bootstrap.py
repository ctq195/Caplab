#!/usr/bin/env python3
"""Prepare workspace-local lightweight dependencies for CapLab (v2.0.1).

v2.0.1 removes the torch / sentence-transformers / HuggingFace download chain
that made first-run heavy and fragile. Dense retrieval now runs from:

  - a PREBUILT index (ships with the Skill; zero download / encoding), and
  - query encoding through either the bundled int8 ONNX model (~30 MB, offline)
    or an optional Qianfan / OpenAI-compatible embedding API.

`check` reports four readiness groups:
  - dependencies : numpy, onnxruntime, tokenizers (small wheels; openpyxl is maintainer-only)
  - index        : RAG index present (index_meta.json + embeddings.npy)
  - model        : bundled ONNX model found (skill assets or .caplab/models)
  - workspace    : state file, knowledge base Excel, optional API config
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

LIGHT_REQUIREMENTS = ("numpy", "onnxruntime", "tokenizers")
MINIMUM_REQUIREMENTS = ("numpy",)
MAINTAINER_REQUIREMENTS = ("openpyxl",)  # only needed to build indexes from xlsx directly


def paths(workspace: Path) -> dict[str, Path]:
    base = workspace.resolve() / ".caplab"
    return {
        "base": base,
        "deps": base / "deps",
        "models": base / "models",
        "index": base / "knowledge_index",
        "state": base / "state",
    }


def dependency_status(deps: Path) -> dict[str, bool]:
    sys.path.insert(0, str(deps))
    return {name: importlib.util.find_spec(name) is not None for name in LIGHT_REQUIREMENTS}


def maintainer_dependency_status(deps: Path) -> dict[str, bool]:
    sys.path.insert(0, str(deps))
    return {name: importlib.util.find_spec(name) is not None for name in MAINTAINER_REQUIREMENTS}


def bundled_model_dir() -> Path:
    """Skill-bundled ONNX model directory (assets/models)."""
    return Path(__file__).resolve().parent.parent / "assets" / "models"


def onnx_model_ready(*dirs: Path) -> bool:
    """True if any candidate directory holds a usable int8 BGE ONNX bundle."""
    for base in dirs:
        for cand in (base, base / "bge-small-zh-v1.5-int8"):
            if cand.is_dir() and (cand / "model_quantized.onnx").is_file() and (
                (cand / "tokenizer.json").is_file() or (cand / "vocab.txt").is_file()
            ):
                return True
    return False


def index_ready(index_dir: Path) -> bool:
    from caplab_index import validate_index, IndexError
    try:
        validate_index(index_dir)
        return True
    except (IndexError, OSError):
        return False


def api_config_ready(workspace: Path) -> bool:
    try:
        import caplab_encoder
    except Exception:
        return False
    return caplab_encoder.api_config_from(workspace / ".caplab" / "qianfan-config.json") is not None


def find_kb_excel(workspace: Path) -> list[str]:
    if not workspace.is_dir():
        return []
    names = [
        "CapLab公共知识库_v2.3.0_免费版.xlsx",
        "CapLab公共知识库_v2.3.0_付费版.xlsx",
        "公共知识库_免费版.xlsx",
        "公共知识库_付费版.xlsx",
        "公共知识库.xlsx",
    ]
    return [name for name in names if (workspace / name).is_file()]


def command_check(args: argparse.Namespace) -> int:
    target = paths(args.workspace)
    status = dependency_status(target["deps"])
    minimum_ok = all(status[name] for name in MINIMUM_REQUIREMENTS)
    full_ok = all(status.values())
    maintainer_status = maintainer_dependency_status(target["deps"])

    index = index_ready(target["index"])
    model = onnx_model_ready(bundled_model_dir(), target["models"])
    api = api_config_ready(args.workspace)
    excel = find_kb_excel(args.workspace)
    state_ready = (target["state"] / "caplab_state.json").is_file()

    output = {
        "workspace": str(args.workspace.resolve()),
        "paths": {key: str(value) for key, value in target.items()},
        "dependencies": status,
        "maintainer_dependencies": maintainer_status,
        "minimum_dependencies_ok": minimum_ok,
        "full_dependencies_ok": full_ok,
        "index_ready": index,
        "onnx_model_ready": model,
        "api_config_ready": api,
        "kb_excel_files": excel,
        "state_ready": state_ready,
        # ready = minimum deps + index present + (onnx model or api)
        "ready": index,
        "dense_runtime_available": full_ok and model or minimum_ok and api,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ready"] else 2


def command_setup(args: argparse.Namespace) -> int:
    if not args.confirm:
        print(
            "BLOCKED: setup installs workspace-local packages; "
            "rerun with --confirm after explicit user approval.",
            file=sys.stderr,
        )
        return 3
    target = paths(args.workspace)
    for value in target.values():
        value.mkdir(parents=True, exist_ok=True)
    requirements = Path(__file__).resolve().parent.parent / "requirements.txt"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--target", str(target["deps"]), "-r", str(requirements)],
        check=True,
    )
    return command_check(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CapLab workspace bootstrap (v2.0.1, lightweight)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("check", command_check), ("setup", command_setup)):
        item = sub.add_parser(name)
        item.add_argument("--workspace", type=Path, required=True)
        if name == "setup":
            item.add_argument("--confirm", action="store_true")
        item.set_defaults(func=func)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
