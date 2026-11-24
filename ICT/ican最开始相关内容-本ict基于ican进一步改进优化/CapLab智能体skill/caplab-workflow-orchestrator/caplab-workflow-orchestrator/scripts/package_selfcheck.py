#!/usr/bin/env python3
"""Self-check the self-contained CapLab DuMate Skill package."""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import zipfile
from pathlib import Path


REQUIRED = [
    "scripts/caplab_kb_autopilot.py", "tests/test_kb_autopilot.py",
    "references/dialogue-rendering.md", "references/knowledge/kb-autopilot.md",
    "references/knowledge/kb-source-notes.md",
    "references/knowledge/source-material/CapLab_KB_Autopilot_v1.1_original.md",
    "scripts/caplab_guards.py", "scripts/caplab_turn.py", "references/runtime-guards.md",
    "references/schemas/artifact-delivery.schema.json", "tests/test_runtime_guards.py",
    "scripts/caplab_index.py", "scripts/caplab_quality.py", "references/demo-operations.md",
    "assets/prebuilt_index/free/index_manifest.json", "assets/prebuilt_index/paid/index_manifest.json",
    "tests/test_release_regressions.py",
    "scripts/resume_pipeline.py", "assets/resume/resume-template.tex",
    "references/schemas/resume-content.schema.json", "references/capabilities/resume/scoring-rubric.md",
    "references/capabilities/resume/resume-content-schema.md", "tests/test_resume_pipeline.py",
    "tests/fixtures/resume-synthetic.json",
    "SKILL.md", "agents/openai.yaml", "scripts/caplab_access.py", "references/vip-access.md", "tests/cases.json", "requirements.txt", "qianfan-config.example.json",
    "references/workflow.md", "references/state-protocol.md", "references/knowledge-maintainer.md",
    "references/schemas/caplab-state.schema.json", "references/schemas/caplab-patch.schema.json",
    "references/stages/profile-intake.md", "references/stages/profile-confirmation.md",
    "references/stages/path-convergence.md", "references/stages/path-evidence-cycle.md",
    "references/stages/evidence-review.md", "references/stages/cold-start.md",
    "references/rag-knowledge-protocol.md", "references/initialization.md",
    "references/knowledge-tiers.md", "references/test-mode.md", "references/ocr-input-limits.md",
    "references/external-resources.md", "references/privacy-and-sharing.md",
    "references/capabilities/resume/resume.md", "references/capabilities/interview/interview.md",
    "references/capabilities/expert-report/expert-report.md",
    "references/shared/psychological-mechanisms.md", "references/shared/personal-facts.md",
    "scripts/caplab_state.py", "scripts/caplab_rag.py", "scripts/caplab_encoder.py",
    "scripts/bootstrap.py", "scripts/caplab_test_mode.py", "scripts/caplab_test_archive.py",
    "scripts/caplab_profile.py",
    "docs/评审复现说明.md",
    "references/methods/dialogic-self-understanding.md", "references/methods/li-kaipi-dialogue-patterns.md",
    "scripts/evaluate_retrieval.py", "scripts/build_skill_zip.py", "tests/retrieval_cases.json",
    "assets/templates/source-record.json", "assets/templates/person-case.json",
    "assets/templates/occupation-card.json", "assets/templates/pathway-card.json",
    "assets/templates/intake-draft.json", "assets/test-mode-config.json",
    "assets/models/bge-small-zh-v1.5-int8/model_quantized.onnx",
    "assets/prebuilt_index/free/index_meta.json", "assets/prebuilt_index/free/embeddings.npy",
    "assets/prebuilt_index/paid/index_meta.json", "assets/prebuilt_index/paid/embeddings.npy",
    "assets/knowledge-cards/free/index.json", "assets/knowledge-cards/free/documents.json",
    "assets/knowledge-cards/paid/index.json", "assets/knowledge-cards/paid/documents.json",
    "scripts/export_kb_cards.py",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=None)
    args = parser.parse_args()
    root = args.skill_dir.resolve()
    errors = []
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required file: {relative}")
            continue
        if path.suffix in {".md", ".json", ".py", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            placeholder = "TO" + "DO"
            if placeholder in text:
                errors.append(f"placeholder remains in: {relative}")
    for path in root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid JSON {path.relative_to(root)}: {exc}")
    for path in root.rglob("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"invalid Python {path.relative_to(root)}: {exc}")
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"link escapes package in {path.relative_to(root)}: {target}")
                continue
            if not resolved.is_file():
                errors.append(f"broken link in {path.relative_to(root)}: {target}")
    skill = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").exists() else ""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill, re.DOTALL)
    if not match or not re.search(r"^name:\s*caplab-workflow-orchestrator\s*$", match.group(1), re.MULTILINE):
        errors.append("invalid orchestrator frontmatter name")
    frontmatter = match.group(1) if match else ""
    required_metadata = {
        "displayName": "CapLab 生涯探索助手",
        "version": "2.2.0",
        "level": "L1",
        "category": "教育",
        "allow_implicit_invocation": "true",
    }
    for key, expected in required_metadata.items():
        pattern = rf"^\s*{re.escape(key)}:\s*[\"']?{re.escape(expected)}[\"']?\s*$"
        if not re.search(pattern, frontmatter, re.MULTILINE):
            errors.append(f"missing or invalid DuMate metadata: {key}={expected}")
    if "版本：2.2.0" not in skill:
        errors.append("SKILL.md body version is not 2.2.0")
    for marker in ["版本与能力边界", "知识库版本", "免费版知识库", "付费版知识库", "检索通道与可复现性"]:
        if marker not in skill:
            errors.append(f"SKILL.md missing marker: {marker}")
    for marker in ["Save 31415926", "sparse_fallback", "local_onnx", "api"]:
        if marker not in skill:
            errors.append(f"SKILL.md missing v2.2.0 marker: {marker}")
    deprecated_paths = [
        root / "scripts/psychological_growth.py",
        root / "references/methods/psychological-growth-assessment.md",
        root / "tests/test_psychological_growth.py",
    ]
    for path in deprecated_paths:
        if path.exists():
            errors.append(f"deprecated standalone assessment remains: {path.relative_to(root)}")
    if "CAPLAB-PGA-1" in skill or "心理成长自评" in skill:
        errors.append("SKILL.md still presents psychology as a standalone assessment")
    cases = json.loads((root / "tests/cases.json").read_text(encoding="utf-8")) if (root / "tests/cases.json").exists() else {}
    categories = {case.get("category") for case in cases.get("test_cases", [])}
    if not {"happy_path", "negative", "confirmation", "rollback"}.issubset(categories):
        errors.append("orchestrator cases lack required categories")
    if cases.get("version") != "2.2.0":
        errors.append("tests/cases.json version is not 2.2.0")
    import sys
    sys.path.insert(0, str(root / "scripts"))
    from caplab_index import validate_index
    for tier in ("free", "paid"):
        try:
            validate_index(root / "assets/prebuilt_index" / tier)
        except Exception as exc:
            errors.append(f"index integrity {tier}: {exc}")
    if args.zip_path:
        zip_path = args.zip_path.resolve()
        if not zip_path.is_file():
            errors.append(f"zip does not exist: {zip_path}")
        else:
            with zipfile.ZipFile(zip_path) as archive:
                names = [name for name in archive.namelist() if name and not name.endswith("/")]
            roots = {name.split("/", 1)[0] for name in names}
            if roots != {root.name}:
                errors.append(f"zip must have exactly one root named {root.name}: {sorted(roots)}")
            if f"{root.name}/SKILL.md" not in names:
                errors.append("zip root does not contain SKILL.md")
            if any("/dist/" in f"/{name}" or name.lower().endswith(".zip") for name in names):
                errors.append("zip contains nested dist or zip artifacts")
    print(json.dumps({"status": "ok" if not errors else "failed", "skill_dir": str(root), "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
