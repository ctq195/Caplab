#!/usr/bin/env python3
"""Build a deterministic DuMate ZIP with the Skill folder as its root."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path


EXCLUDED = {".DS_Store", "__pycache__"}


def included(path: Path) -> bool:
    return not any(part in EXCLUDED for part in path.parts) and path.suffix != ".pyc"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("output_zip", type=Path)
    args = parser.parse_args()
    root = args.skill_dir.resolve()
    output = args.output_zip.resolve()
    if not (root / "SKILL.md").is_file():
        raise SystemExit(f"missing SKILL.md: {root}")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [p for p in sorted(root.rglob("*")) if p.is_file() and included(p.relative_to(root)) and p.resolve() != output]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = Path(root.name) / path.relative_to(root)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | (0o755 if path.suffix == ".py" else 0o644)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    print(json.dumps({
        "status": "ok", "output": str(output), "root": root.name, "file_count": len(files),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest()
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
