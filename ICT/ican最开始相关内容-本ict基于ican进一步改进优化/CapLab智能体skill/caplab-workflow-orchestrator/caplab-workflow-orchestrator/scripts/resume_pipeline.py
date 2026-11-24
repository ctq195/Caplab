#!/usr/bin/env python3
"""Build and verify an evidence-gated XeLaTeX resume."""

from __future__ import annotations

import argparse
import json
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


from caplab_guards import body_fields, load_sources, validate_evidence, delivery_state, digest, downgrade_tutorial


WEIGHTS = {
    "job_match": 25,
    "technical_criticality": 20,
    "quantification": 15,
    "information_density": 15,
    "readability": 15,
    "fact_credibility": 10,
}
DISPLAY_NAMES = {
    "job_match": "岗位匹配度",
    "technical_criticality": "技术关键性",
    "quantification": "量化程度",
    "information_density": "信息密度",
    "readability": "可读性",
    "fact_credibility": "事实可信度",
}
PROFILES = {
    # normal reproduces the supplied 260608 TeX layout.
    "normal": {"margin": "1.35", "body": "10", "leading": "12", "baseline": "1.03", "header_after": "-0.6", "section_before": "0.55", "section_after": "0.3", "desc_after": "-0.25", "item_sep": "0.08", "top_sep": "0.15"},
    # relaxed is attempted when a one-page resume occupies less than 75% of the page.
    "relaxed": {"margin": "1.50", "body": "10.5", "leading": "13.3", "baseline": "1.10", "header_after": "-0.2", "section_before": "0.78", "section_after": "0.42", "desc_after": "-0.10", "item_sep": "0.22", "top_sep": "0.28"},
    "compact": {"margin": "1.30", "body": "9.5", "leading": "11.2", "baseline": "1.00", "header_after": "-0.65", "section_before": "0.45", "section_after": "0.22", "desc_after": "-0.28", "item_sep": "0.04", "top_sep": "0.10"},
    "tight": {"margin": "1.27", "body": "9", "leading": "10.5", "baseline": "0.98", "header_after": "-0.75", "section_before": "0.36", "section_after": "0.16", "desc_after": "-0.30", "item_sep": "0.02", "top_sep": "0.06"},
}
PROFILE_ORDER = tuple(PROFILES)
SPARSE_PAGE_THRESHOLD = 0.75
ALLOWED_BODY_EVIDENCE = {"direct", "transferable"}
TEMPLATE_MARKERS = {
    "@@MARGIN_CM@@", "@@BODY_SIZE_PT@@", "@@LEADING_PT@@", "@@BASELINE_STRETCH@@",
    "@@HEADER_AFTER_EM@@", "@@SECTION_BEFORE_EM@@", "@@SECTION_AFTER_EM@@",
    "@@DESC_AFTER_EM@@", "@@ITEM_SEP_EM@@", "@@TOP_SEP_EM@@", "@@BODY@@",
}


class ResumeError(Exception):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ResumeError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ResumeError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResumeError("resume input must be a JSON object")
    return value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_content(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("meta", "candidate", "sections", "selected_evidence", "selection_log", "open_questions", "scorecard"):
        if key not in data:
            errors.append(f"missing top-level field: {key}")
    if errors:
        return errors

    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
        meta = {}
    for key in ("title", "language", "target_job", "tailoring_mode"):
        if not nonempty(meta.get(key)):
            errors.append(f"meta.{key} must be a non-empty string")
    if meta.get("language") not in {"zh-CN", "en", "bilingual"}:
        errors.append("meta.language must be zh-CN, en, or bilingual")
    if meta.get("tailoring_mode") not in {"jd_tailored", "general_direction"}:
        errors.append("meta.tailoring_mode must be jd_tailored or general_direction")
    if meta.get("tailoring_mode") == "jd_tailored" and not nonempty(meta.get("jd_source")):
        errors.append("meta.jd_source is required for jd_tailored resumes")
    if meta.get("tailoring_mode") == "general_direction" and not any(label in str(meta.get("target_job", "")).lower() for label in ("通用岗位方向", "general direction")):
        errors.append("general_direction target_job must be labeled as a general direction version")
    if meta.get("target_pages") not in {1, 2}:
        errors.append("meta.target_pages must be 1 or 2")
    if meta.get("target_pages") == 2 and not nonempty(meta.get("two_page_reason")):
        errors.append("meta.two_page_reason is required for a two-page resume")

    candidate = data.get("candidate", {})
    if not isinstance(candidate, dict):
        errors.append("candidate must be an object")
        candidate = {}
    for key in ("name", "headline"):
        if not nonempty(candidate.get(key)):
            errors.append(f"candidate.{key} must be a non-empty string")
    contacts = candidate.get("contact")
    if not isinstance(contacts, list) or any(not nonempty(item) for item in contacts):
        errors.append("candidate.contact must be an array of non-empty strings")

    selected = data.get("selected_evidence")
    if not isinstance(selected, list) or any(not nonempty(item) for item in selected):
        errors.append("selected_evidence must be an array of non-empty source IDs")
        selected_set: set[str] = set()
    else:
        selected_set = set(selected)
        if len(selected_set) != len(selected):
            errors.append("selected_evidence must not contain duplicates")

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections must be a non-empty array")
        sections = []
    section_ids: set[str] = set()
    item_ids: set[str] = set()
    for section_index, section in enumerate(sections):
        base = f"sections[{section_index}]"
        if not isinstance(section, dict):
            errors.append(f"{base} must be an object")
            continue
        if not nonempty(section.get("id")) or section.get("id") in section_ids:
            errors.append(f"{base}.id must be non-empty and unique")
        else:
            section_ids.add(section["id"])
        if not nonempty(section.get("title")):
            errors.append(f"{base}.title must be non-empty")
        kind = section.get("type")
        if kind not in {"entries", "lines"}:
            errors.append(f"{base}.type must be entries or lines")
        items = section.get("items")
        if not isinstance(items, list) or not items:
            errors.append(f"{base}.items must be a non-empty array")
            continue
        for item_index, item in enumerate(items):
            item_base = f"{base}.items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_base} must be an object")
                continue
            if not nonempty(item.get("id")) or item.get("id") in item_ids:
                errors.append(f"{item_base}.id must be non-empty and unique")
            else:
                item_ids.add(item["id"])
            if kind == "entries":
                for key in ("title",):
                    if not nonempty(item.get(key)):
                        errors.append(f"{item_base}.{key} must be non-empty")
                bullets = item.get("bullets")
                if not isinstance(bullets, list) or not bullets:
                    errors.append(f"{item_base}.bullets must be a non-empty array")
                    continue
                facts = [item, *bullets]
            else:
                for key in ("label", "text"):
                    if not nonempty(item.get(key)):
                        errors.append(f"{item_base}.{key} must be non-empty")
                facts = [item]
            for fact_index, fact in enumerate(facts):
                fact_base = f"{item_base}.fact[{fact_index}]"
                if not isinstance(fact, dict):
                    errors.append(f"{fact_base} must be an object")
                    continue
                if kind == "entries" and fact is not item and not nonempty(fact.get("text")):
                    errors.append(f"{fact_base}.text must be non-empty")
                if fact.get("evidence_status") not in ALLOWED_BODY_EVIDENCE:
                    errors.append(f"{fact_base}.evidence_status must be direct or transferable")
                if fact.get("confirmed") is not True:
                    errors.append(f"{fact_base}.confirmed must be true")
                source_ids = fact.get("source_ids")
                if not isinstance(source_ids, list) or not source_ids or any(not nonempty(source) for source in source_ids):
                    errors.append(f"{fact_base}.source_ids must be a non-empty array")
                else:
                    missing = set(source_ids) - selected_set
                    if missing:
                        errors.append(f"{fact_base}.source_ids not in selected_evidence: {sorted(missing)}")

    log = data.get("selection_log")
    if not isinstance(log, list):
        errors.append("selection_log must be an array")
    else:
        for index, item in enumerate(log):
            if not isinstance(item, dict) or not nonempty(item.get("item_id")) or item.get("decision") not in {"keep", "hide", "drop"} or not nonempty(item.get("reason")):
                errors.append(f"selection_log[{index}] must contain item_id, keep/hide/drop decision, and reason")
    questions = data.get("open_questions")
    if not isinstance(questions, list) or any(not nonempty(question) for question in questions):
        errors.append("open_questions must be an array of non-empty strings")
    elif len(questions) > 3:
        errors.append("open_questions must contain at most 3 high-value questions")

    scorecard = data.get("scorecard", {})
    if not isinstance(scorecard, dict):
        errors.append("scorecard must be an object")
        scorecard = {}
    if scorecard.get("hard_gate_passed") is not True:
        errors.append("scorecard.hard_gate_passed must be true before final PDF build")
    if scorecard.get("optimization_round") not in {1, 2, 3}:
        errors.append("scorecard.optimization_round must be 1, 2, or 3")
    dimensions = scorecard.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(WEIGHTS):
        errors.append(f"scorecard.dimensions must contain exactly: {sorted(WEIGHTS)}")
    else:
        for name, maximum in WEIGHTS.items():
            dimension = dimensions[name]
            if not isinstance(dimension, dict):
                errors.append(f"scorecard.dimensions.{name} must be an object")
                continue
            score = dimension.get("score")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= maximum:
                errors.append(f"scorecard.dimensions.{name}.score must be between 0 and {maximum}")
            for key in ("evidence", "deductions"):
                values = dimension.get(key)
                if not isinstance(values, list) or any(not nonempty(value) for value in values):
                    errors.append(f"scorecard.dimensions.{name}.{key} must be an array of strings")
    return errors


def normalized_text(value: Any) -> str:
    text = str(value or "")
    return text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")


def latex_escape(value: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in normalized_text(value))


def render_body(data: dict[str, Any]) -> str:
    candidate = data["candidate"]
    separator = r" \quad | \quad "
    headline = separator.join(latex_escape(part.strip()) for part in normalized_text(candidate["headline"]).split(" | "))
    contact = separator.join(latex_escape(item) for item in candidate["contact"])
    lines = [f"\\ResumeHeader{{{latex_escape(candidate['name'])}}}{{{headline}}}{{{contact}}}"]
    lines.extend(["\\ResumeSection{求职意向}", latex_escape(data["meta"]["target_job"])])
    for section in data["sections"]:
        lines.append(f"\\ResumeSection{{{latex_escape(section['title'])}}}")
        if section["type"] == "entries":
            for item in section["items"]:
                details = " - ".join(part for part in (normalized_text(item.get("subtitle")), normalized_text(item.get("location"))) if part)
                lines.append(f"\\ResumeEntry{{{latex_escape(item['title'])}}}{{{latex_escape(item.get('date', ''))}}}{{{latex_escape(details)}}}")
                lines.append("\\begin{itemize}")
                lines.extend(f"  \\item {latex_escape(bullet['text'])}" for bullet in item["bullets"])
                lines.append("\\end{itemize}")
        else:
            lines.append("\\begin{itemize}")
            lines.extend(f"\\ResumeLine{{{latex_escape(item['label'])}}}{{{latex_escape(item['text'])}}}" for item in section["items"])
            lines.append("\\end{itemize}")
    return "\n".join(lines)


def render_tex(template: str, data: dict[str, Any], profile: str) -> str:
    missing = sorted(marker for marker in TEMPLATE_MARKERS if marker not in template)
    if missing:
        raise ResumeError(f"template missing markers: {missing}")
    settings = PROFILES[profile]
    replacements = {
        "@@MARGIN_CM@@": settings["margin"], "@@BODY_SIZE_PT@@": settings["body"], "@@LEADING_PT@@": settings["leading"],
        "@@BASELINE_STRETCH@@": settings["baseline"], "@@HEADER_AFTER_EM@@": settings["header_after"],
        "@@SECTION_BEFORE_EM@@": settings["section_before"], "@@SECTION_AFTER_EM@@": settings["section_after"],
        "@@DESC_AFTER_EM@@": settings["desc_after"], "@@ITEM_SEP_EM@@": settings["item_sep"],
        "@@TOP_SEP_EM@@": settings["top_sep"], "@@BODY@@": render_body(data),
    }
    result = template
    for marker, value in replacements.items():
        result = result.replace(marker, value)
    return result


def resolve_executable(value: str | None) -> str | None:
    if not value:
        return None
    if "/" in value:
        path = Path(value)
        return str(path) if path.is_file() else None
    return shutil.which(value)


def page_count(pdf: Path, pdfinfo: str | None) -> int | None:
    if not pdfinfo:
        return None
    result = subprocess.run([pdfinfo, str(pdf)], text=True, capture_output=True)
    if result.returncode:
        return None
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def extracted_in_order(extracted: str, expected: list[str]) -> bool:
    extracted = re.sub(r"\s+", "", normalized_text(extracted))
    cursor = 0
    for value in expected:
        normalized = re.sub(r"\s+", "", normalized_text(value))
        position = extracted.find(normalized, cursor)
        if position < 0:
            return False
        cursor = position + len(normalized)
    return True


def extract_pdf_text(pdf_path: Path, pdftotext: str | None) -> str | None:
    if pdftotext:
        result = subprocess.run([pdftotext, str(pdf_path), "-"], text=True, capture_output=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as document:
            return "\n".join(page.extract_text() or "" for page in document.pages)
    except (ImportError, OSError, ValueError):
        return None


def content_height_ratio(pdf_path: Path) -> float | None:
    """Return the first page's vertical text extent divided by page height."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as document:
            if not document.pages or not document.pages[0].chars:
                return None
            page = document.pages[0]
            top = min(float(char["top"]) for char in page.chars)
            bottom = max(float(char["bottom"]) for char in page.chars)
            return round((bottom - top) / float(page.height), 3)
    except (ImportError, KeyError, OSError, TypeError, ValueError, ZeroDivisionError):
        return None


def compile_attempt(tex: str, profile: str, latexmk: str, pdfinfo: str | None, pdftotext: str | None, expected_text: list[str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"caplab-resume-{profile}-") as folder:
        root = Path(folder)
        tex_path = root / "resume.tex"
        tex_path.write_text(tex, encoding="utf-8")
        result = subprocess.run(
            [latexmk, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-outdir={root}", str(tex_path)],
            cwd=root, text=True, capture_output=True,
        )
        log_path = root / "resume.log"
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else result.stdout + "\n" + result.stderr
        pdf_path = root / "resume.pdf"
        attempt: dict[str, Any] = {
            "profile": profile, "returncode": result.returncode, "compiled": result.returncode == 0 and pdf_path.is_file(),
            "overfull_boxes": len(re.findall(r"Overfull \\[hv]box", log)),
            "missing_glyphs": len(re.findall(r"Missing character:", log)),
            "log_tail": "\n".join(log.splitlines()[-30:]), "tex": tex,
        }
        if attempt["compiled"]:
            attempt["pages"] = page_count(pdf_path, pdfinfo)
            attempt["content_height_ratio"] = content_height_ratio(pdf_path)
            attempt["pdf_bytes"] = pdf_path.read_bytes()
            attempt["log"] = log
            extracted = extract_pdf_text(pdf_path, pdftotext)
            attempt["text_extractable"] = extracted_in_order(extracted, expected_text) if extracted is not None else None
        return attempt


def total_score(data: dict[str, Any]) -> float:
    return round(sum(float(data["scorecard"]["dimensions"][name]["score"]) for name in WEIGHTS), 1)


def optimization_reasons(data: dict[str, Any], report: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    total = total_score(data)
    if total < 85:
        reasons.append(f"总分 {total:g} 低于 85")
    for name, maximum in WEIGHTS.items():
        score = float(data["scorecard"]["dimensions"][name]["score"])
        if score < maximum * 0.6:
            reasons.append(f"{DISPLAY_NAMES[name]}低于该维度满分的 60%")
    if not report.get("compiled"):
        reasons.append("PDF 未成功编译")
    if report.get("pages") is None:
        reasons.append("未能确认 PDF 实际页数")
    elif report["pages"] > data["meta"]["target_pages"]:
        reasons.append(f"实际 {report['pages']} 页，超过目标 {data['meta']['target_pages']} 页")
    if report.get("overfull_boxes", 0):
        reasons.append("LaTeX 日志存在 overfull box")
    if report.get("missing_glyphs", 0):
        reasons.append("LaTeX 日志存在缺失字形")
    if report.get("text_extractable") is False:
        reasons.append("PDF 文本提取顺序检查失败")
    if report.get("text_extractable") is None:
        reasons.append("未能检查 PDF 文本提取顺序")
    ratio = report.get("content_height_ratio")
    if report.get("pages") == 1 and isinstance(ratio, (int, float)) and ratio < SPARSE_PAGE_THRESHOLD:
        reasons.append(
            f"正文占页高约 {ratio * 100:.1f}%，低于 75%；已优先放宽间距，"
            "如仍需扩充，只能从已确认材料补充动作、技术对象、个人决策或结果描述"
        )
    return reasons


def scorecard_markdown(data: dict[str, Any], report: dict[str, Any]) -> str:
    if report.get("evidence_status") == "blocked":
        return "# 简历草稿：事实待核验\n\n证据未通过，评分不计入有效分数，不可正式投递。\n\n" + "\n".join(
            "- " + error for error in report.get("evidence_errors", [])) + "\n"
    lines = ["# 简历评分与构建报告", "", f"- 目标岗位：{data['meta']['target_job']}", f"- 目标页数：{data['meta']['target_pages']}"]
    if data["meta"].get("two_page_reason"):
        lines.append(f"- 两页理由：{data['meta']['two_page_reason']}")
    lines.extend([
        f"- 优化轮次：{data['scorecard']['optimization_round']}/3",
        f"- 事实硬门槛：{'通过' if data['scorecard']['hard_gate_passed'] else '未通过'}",
        f"- 导出状态：{report['export_status']}",
        f"- 排版档位：{report.get('profile') or '未编译'}",
        f"- 实际页数：{report.get('pages') if report.get('pages') is not None else '未确认'}",
        f"- 正文占页高度：{report.get('content_height_ratio') * 100:.1f}%" if isinstance(report.get("content_height_ratio"), (int, float)) else "- 正文占页高度：未确认",
        "", "## 六维评分", "", "| 维度 | 得分 | 满分 | 证据 | 扣分原因 |", "|---|---:|---:|---|---|",
    ])
    for name, maximum in WEIGHTS.items():
        dimension = data["scorecard"]["dimensions"][name]
        evidence = "；".join(dimension["evidence"]) or "无"
        deductions = "；".join(dimension["deductions"]) or "无"
        lines.append(f"| {DISPLAY_NAMES[name]} | {dimension['score']} | {maximum} | {evidence} | {deductions} |")
    lines.extend(["", f"**总分：{total_score(data):g}/100**", "", "## 选择记录", ""])
    if data["selection_log"]:
        lines.extend(f"- `{item['decision']}` {item['item_id']}：{item['reason']}" for item in data["selection_log"])
    else:
        lines.append("- 无")
    lines.extend(["", "## 待确认问题", ""])
    if data["open_questions"]:
        lines.extend(f"- {question}" for question in data["open_questions"][:3])
    else:
        lines.append("- 无")
    lines.extend(["", "## 仍需优化", ""])
    reasons = report.get("optimization_reasons", [])
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    elif report.get("export_status") == "generated_verified":
        lines.append("- 无；编译、页数、文本提取和视觉检查均已完成。")
    else:
        lines.append("- 无自动检查问题；仍需完成视觉检查。")
    lines.extend(["", "> 本评分仅用于当前简历内部优化，不是 ATS 官方评分、录用概率或招聘方判断。", ""])
    return "\n".join(lines)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output_dir.resolve()
    if (output / "build-report.json").exists():
        previous = read_json(output / "build-report.json")
        previous.update(delivery_state(render_passed=False, evidence_errors=["rebuild pending"],
            content_status="draft", open_questions=True, score_passed=False))
        previous.update(export_status="generated_unverified", score_total=None)
        write_json(output / "build-report.json", previous)
        (output / "resume-scorecard.md").write_text("# 重建待验收\n\n本轮重建尚未通过，不可作为 ready 交付。\n", encoding="utf-8")
    data = read_json(args.input.resolve())
    errors = validate_content(data)
    if errors:
        raise ResumeError("invalid resume content:\n- " + "\n- ".join(errors))
    if not isinstance(data.get("fact_bindings", {}), dict):
        raise ResumeError("fact_bindings must be an object")
    sources = load_sources(getattr(args, "sources_dir", None))
    downgrades = []
    for pointer, value in list(body_fields(data)):
        binding = data.get("fact_bindings", {}).get(pointer, {})
        source = sources.get(binding.get("source_id"), {}) if isinstance(binding, dict) else {}
        replacement = downgrade_tutorial(value, source.get("text", ""))
        if replacement != value:
            target = data
            parts = pointer.strip("/").split("/")
            for part in parts[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            target[parts[-1]] = replacement
            downgrades.append({"path": pointer, "before": value, "after": replacement})
    evidence_errors = validate_evidence(data, sources)
    # Explicitly supplied evidence must validate before any new output is built.
    # Legacy files without source records remain readable/buildable as drafts.
    output = args.output_dir.resolve()
    if evidence_errors and getattr(args, "sources_dir", None):
        if (output / "build-report.json").exists():
            old_report = read_json(output / "build-report.json")
            old_report.update(delivery_state(render_passed=False, evidence_errors=evidence_errors,
                content_status="draft", open_questions=True, score_passed=False))
            old_report["export_status"] = "generated_unverified"
            old_report["evidence_errors"] = evidence_errors
            write_json(output / "build-report.json", old_report)
        raise ResumeError("evidence validator blocked build:\n- " + "\n- ".join(evidence_errors))
    output.mkdir(parents=True, exist_ok=True)
    default_template = Path(__file__).resolve().parents[1] / "assets" / "resume" / "resume-template.tex"
    template_path = args.template.resolve() if args.template else default_template
    template = template_path.read_text(encoding="utf-8")
    normal_tex = render_tex(template, data, "normal")
    write_json(output / "resume-content.json", data)

    latexmk = None if args.skip_compile else resolve_executable(args.latexmk)
    pdfinfo = resolve_executable(args.pdfinfo)
    pdftotext = resolve_executable(args.pdftotext)
    attempts: list[dict[str, Any]] = []
    if latexmk:
        expected_text = [data["candidate"]["name"], "求职意向", *[section["title"] for section in data["sections"]]]
        normal_attempt = compile_attempt(normal_tex, "normal", latexmk, pdfinfo, pdftotext, expected_text)
        attempts.append(normal_attempt)
        normal_fits = (
            normal_attempt["compiled"] and normal_attempt.get("pages") is not None
            and normal_attempt["pages"] <= data["meta"]["target_pages"]
            and not normal_attempt["overfull_boxes"] and not normal_attempt["missing_glyphs"]
        )
        normal_sparse = (
            normal_fits and data["meta"]["target_pages"] == 1
            and isinstance(normal_attempt.get("content_height_ratio"), (int, float))
            and normal_attempt["content_height_ratio"] < SPARSE_PAGE_THRESHOLD
        )
        if normal_sparse:
            attempts.append(compile_attempt(render_tex(template, data, "relaxed"), "relaxed", latexmk, pdfinfo, pdftotext, expected_text))
        elif not normal_fits:
            for profile in ("compact", "tight"):
                attempt = compile_attempt(render_tex(template, data, profile), profile, latexmk, pdfinfo, pdftotext, expected_text)
                attempts.append(attempt)
                if attempt["compiled"] and attempt.get("pages") is not None and attempt["pages"] <= data["meta"]["target_pages"] and not attempt["overfull_boxes"] and not attempt["missing_glyphs"]:
                    break

    compiled = [attempt for attempt in attempts if attempt["compiled"]]
    if compiled:
        normal_sparse = bool(
            attempts and attempts[0].get("compiled") and attempts[0].get("pages") == 1
            and isinstance(attempts[0].get("content_height_ratio"), (int, float))
            and attempts[0]["content_height_ratio"] < SPARSE_PAGE_THRESHOLD
        )

        def rank(attempt: dict[str, Any]) -> tuple[int, int, int, int, float, int]:
            pages = attempt.get("pages")
            within = pages is not None and pages <= data["meta"]["target_pages"]
            warnings = attempt["overfull_boxes"] + attempt["missing_glyphs"]
            ratio = attempt.get("content_height_ratio")
            sparse_penalty = 0
            if normal_sparse:
                sparse_penalty = 0 if isinstance(ratio, (int, float)) and ratio >= SPARSE_PAGE_THRESHOLD else 1
            ratio_gap = abs(0.82 - ratio) if normal_sparse and isinstance(ratio, (int, float)) else 0.0
            profile_rank = PROFILE_ORDER.index(attempt["profile"])
            return (
                0 if within else 1, warnings, sparse_penalty,
                pages if pages is not None else 999, ratio_gap, profile_rank if within else -profile_rank,
            )
        chosen = min(compiled, key=rank)
        (output / "resume.tex").write_text(chosen["tex"], encoding="utf-8")
        (output / "resume.pdf").write_bytes(chosen["pdf_bytes"])
        (output / "resume.log").write_text(chosen["log"], encoding="utf-8")
        report: dict[str, Any] = {key: chosen.get(key) for key in ("profile", "compiled", "pages", "content_height_ratio", "overfull_boxes", "missing_glyphs", "text_extractable")}
    else:
        # A failed rebuild must not expose a PDF left by a previous build.
        for stale_name in ("resume.pdf", "resume.log"):
            (output / stale_name).unlink(missing_ok=True)
        (output / "resume.tex").write_text(normal_tex, encoding="utf-8")
        report = {
            "profile": "normal", "compiled": False, "pages": None, "overfull_boxes": 0,
            "content_height_ratio": None, "missing_glyphs": 0, "text_extractable": None,
            "compile_error": "latexmk with XeLaTeX is unavailable or all compilation attempts failed",
        }
        if attempts:
            report["attempts"] = [{key: item.get(key) for key in ("profile", "returncode", "compiled", "log_tail")} for item in attempts]
    report.update({
        "schema_version": "1.0.0", "skill_version": "2.2.0", "target_pages": data["meta"]["target_pages"],
        "score_total": total_score(data) if not evidence_errors else None, "visual_reviewed": False, "export_status": "generated_unverified",
        "artifacts": {
            "content": str(output / "resume-content.json"), "tex": str(output / "resume.tex"),
            "pdf": str(output / "resume.pdf") if (output / "resume.pdf").is_file() else None,
            "scorecard": str(output / "resume-scorecard.md"),
        },
    })
    report.update(delivery_state(render_passed=False, evidence_errors=evidence_errors,
        content_status="draft", open_questions=data["open_questions"], score_passed=False))
    report["evidence_errors"] = evidence_errors
    report["automatic_downgrades"] = downgrades
    report["source_digest"] = digest(sources)
    report["template_digest"] = hashlib.sha256(template.encode()).hexdigest()
    report["artifact_hashes"] = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
        for name in ("resume-content.json", "resume.tex", "resume.pdf", "resume.log") if (output / name).exists()}
    report["schema_version"] = "1.1.0"
    report["optimization_reasons"] = optimization_reasons(data, report) + evidence_errors
    write_json(output / "build-report.json", report)
    (output / "resume-scorecard.md").write_text(scorecard_markdown(data, report), encoding="utf-8")
    return report


def verify(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output_dir.resolve()
    data = read_json(output / "resume-content.json")
    report = read_json(output / "build-report.json")
    errors = validate_content(data)
    try:
        sources = load_sources(getattr(args, "sources_dir", None))
        evidence_errors = validate_evidence(data, sources) if not errors else ["invalid content structure"]
    except (ValueError, OSError) as exc:
        sources = {}
        evidence_errors = [str(exc)]
    errors.extend(evidence_errors)
    trusted_template = Path(__file__).resolve().parents[1] / "assets/resume/resume-template.tex"
    if hashlib.sha256(trusted_template.read_bytes()).hexdigest() != report.get("template_digest"):
        errors.append("custom/unbound template requires review; rebuild with packaged template")
    if digest(sources) != report.get("source_digest"):
        errors.append("source records changed or missing; rebuild required")
    for name in ("resume-content.json", "resume.tex", "resume.pdf", "resume.log"):
        path = output / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != report.get("artifact_hashes", {}).get(name):
            errors.append(f"artifact changed or not bound to build: {name}")
    # Revoke a previous ready state before validation, including failed re-verification.
    report.update(delivery_state(render_passed=False, evidence_errors=evidence_errors,
        content_status="draft", open_questions=True, score_passed=False))
    report["export_status"] = "generated_unverified"
    report["evidence_errors"] = evidence_errors
    write_json(output / "build-report.json", report)
    if validate_content(data):
        raise ResumeError("invalid saved resume content: " + "; ".join(errors))
    if report.get("compiled") is not True:
        errors.append("current build did not compile a PDF")
    for name in ("resume.tex", "resume.pdf", "resume.log"):
        if not (output / name).is_file():
            errors.append(f"missing artifact: {name}")
    pdfinfo = resolve_executable(args.pdfinfo)
    pdf_path = output / "resume.pdf"
    pages = page_count(pdf_path, pdfinfo) if pdf_path.is_file() else None
    if pages is None:
        errors.append("unable to verify PDF page count")
    elif pages > data["meta"]["target_pages"]:
        errors.append(f"PDF has {pages} pages, target is {data['meta']['target_pages']}")
    log_text = (output / "resume.log").read_text(errors="replace") if (output / "resume.log").exists() else ""
    if report.get("overfull_boxes") or re.search(r"Overfull \\[hv]box", log_text):
        errors.append("LaTeX log contains overfull boxes")
    if report.get("missing_glyphs") or "Missing character:" in log_text:
        errors.append("LaTeX log contains missing glyphs")
    pdftotext = resolve_executable(args.pdftotext)
    extracted = extract_pdf_text(pdf_path, pdftotext) if pdf_path.is_file() else None
    expected_text = [value for _, value in body_fields(data)]
    report["text_extractable"] = extracted_in_order(extracted, expected_text) if extracted is not None else None
    report["content_height_ratio"] = content_height_ratio(pdf_path) if pdf_path.is_file() else None
    if report.get("text_extractable") is not True:
        errors.append("PDF text extraction order was not verified")
    if total_score(data) < 85:
        errors.append("resume score is below 85")
    for name, maximum in WEIGHTS.items():
        if float(data["scorecard"]["dimensions"][name]["score"]) < maximum * 0.6:
            errors.append(f"{name} score is below 60% of its maximum")
    if not args.visual_reviewed:
        errors.append("visual review confirmation is required")
    if not getattr(args, "content_reviewed", False):
        errors.append("content review is required")
    if data["open_questions"]:
        errors.append("unresolved content questions remain")
    if errors:
        render_passed = bool(report.get("compiled") and pages is not None
            and pages <= data["meta"]["target_pages"] and args.visual_reviewed
            and report.get("text_extractable") is True and not report.get("overfull_boxes")
            and not report.get("missing_glyphs") and not re.search(r"Overfull \\[hv]box|Missing character:", log_text)
            and not any("artifact" in error or "template" in error for error in errors))
        report.update(delivery_state(render_passed=render_passed, evidence_errors=evidence_errors,
            content_status="reviewed" if getattr(args, "content_reviewed", False) else "draft",
            open_questions=data["open_questions"], score_passed=False))
        report["score_total"] = None if evidence_errors else total_score(data)
        report["validation_errors"] = errors
        write_json(output / "build-report.json", report)
        (output / "resume-scorecard.md").write_text(scorecard_markdown(data, report), encoding="utf-8")
        raise ResumeError("resume cannot be marked generated_verified:\n- " + "\n- ".join(errors))
    report.update(delivery_state(render_passed=True, evidence_errors=[], content_status="passed",
        open_questions=False, score_passed=True))
    report["validation_errors"] = []
    report.update({"pages": pages, "visual_reviewed": True, "export_status": "generated_verified"})
    report["optimization_reasons"] = optimization_reasons(data, report)
    write_json(output / "build-report.json", report)
    (output / "resume-scorecard.md").write_text(scorecard_markdown(data, report), encoding="utf-8")
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--input", type=Path, required=True)
    build_parser.add_argument("--output-dir", type=Path, required=True)
    build_parser.add_argument("--template", type=Path)
    build_parser.add_argument("--latexmk", default="latexmk")
    build_parser.add_argument("--pdfinfo", default="pdfinfo")
    build_parser.add_argument("--pdftotext", default="pdftotext")
    build_parser.add_argument("--skip-compile", action="store_true")
    build_parser.add_argument("--sources-dir", type=Path)
    build_parser.set_defaults(func=build)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--output-dir", type=Path, required=True)
    verify_parser.add_argument("--pdfinfo", default="pdfinfo")
    verify_parser.add_argument("--pdftotext", default="pdftotext")
    verify_parser.add_argument("--visual-reviewed", action="store_true")
    verify_parser.add_argument("--sources-dir", type=Path, required=True)
    verify_parser.add_argument("--content-reviewed", action="store_true")
    verify_parser.set_defaults(func=verify)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        payload = args.func(args)
    except (ResumeError, ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "ok", **payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
