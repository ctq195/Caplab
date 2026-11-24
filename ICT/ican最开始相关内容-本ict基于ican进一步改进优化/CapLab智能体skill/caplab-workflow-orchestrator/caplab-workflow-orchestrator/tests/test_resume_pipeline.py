"""Tests for the evidence-gated LaTeX resume pipeline."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import resume_pipeline as resume


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "resume-synthetic.json"


class ResumePipelineTests(unittest.TestCase):
    def data(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_valid_and_score_is_86(self):
        data = self.data()
        self.assertEqual(resume.validate_content(data), [])
        self.assertEqual(resume.total_score(data), 86)

    def test_latex_escape_and_ascii_dash_normalization(self):
        escaped = resume.latex_escape("R&D_100% #1 — C++")
        self.assertEqual(escaped, r"R\&D\_100\% \#1 - C++")

    def test_unconfirmed_or_supportable_fact_is_rejected(self):
        data = self.data()
        fact = data["sections"][1]["items"][0]
        fact["confirmed"] = False
        fact["evidence_status"] = "supportable"
        errors = resume.validate_content(data)
        self.assertTrue(any("evidence_status" in error for error in errors))
        self.assertTrue(any("confirmed" in error for error in errors))

    def test_two_pages_requires_a_reason(self):
        data = self.data()
        data["meta"]["target_pages"] = 2
        self.assertTrue(any("two_page_reason" in error for error in resume.validate_content(data)))

    def test_tailored_version_requires_jd_source_and_general_version_requires_label(self):
        data = self.data()
        data["meta"]["tailoring_mode"] = "jd_tailored"
        self.assertTrue(any("jd_source" in error for error in resume.validate_content(data)))
        data = self.data()
        data["meta"]["target_job"] = "AI应用开发工程师"
        self.assertTrue(any("general direction" in error for error in resume.validate_content(data)))

    def test_only_three_high_value_questions_are_allowed(self):
        data = self.data()
        data["open_questions"].append("第四个低优先级问题")
        self.assertTrue(any("at most 3" in error for error in resume.validate_content(data)))

    def test_failed_fact_gate_is_rejected(self):
        data = self.data()
        data["scorecard"]["hard_gate_passed"] = False
        self.assertTrue(any("hard_gate_passed" in error for error in resume.validate_content(data)))

    def test_build_without_latex_keeps_json_and_tex_only(self):
        with tempfile.TemporaryDirectory() as folder:
            args = Namespace(
                input=FIXTURE, output_dir=Path(folder), template=None, latexmk="/definitely/missing/latexmk",
                pdfinfo="/definitely/missing/pdfinfo", pdftotext="/definitely/missing/pdftotext", skip_compile=False,
            )
            report = resume.build(args)
            self.assertEqual(report["export_status"], "generated_unverified")
            self.assertFalse(report["compiled"])
            self.assertTrue((Path(folder) / "resume-content.json").is_file())
            self.assertTrue((Path(folder) / "resume.tex").is_file())
            self.assertTrue((Path(folder) / "resume-scorecard.md").is_file())
            self.assertFalse((Path(folder) / "resume.pdf").exists())

    def test_failed_rebuild_does_not_advertise_stale_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "resume.pdf").write_bytes(b"stale old PDF")
            (output / "resume.log").write_text("stale log")
            report = resume.build(Namespace(
                input=FIXTURE, output_dir=output, template=None, latexmk="missing",
                pdfinfo="pdfinfo", pdftotext="pdftotext", skip_compile=True,
            ))
            self.assertFalse((output / "resume.pdf").exists())
            self.assertIsNone(report["artifacts"]["pdf"])
            self.assertFalse(report["compiled"])
            self.assertEqual(report["skill_version"], "2.2.0")

    @unittest.skipUnless(shutil.which("latexmk") and shutil.which("xelatex") and shutil.which("pdfinfo"), "XeLaTeX toolchain unavailable")
    def test_regression_fixture_compiles_to_one_page(self):
        with tempfile.TemporaryDirectory() as folder:
            args = Namespace(
                input=FIXTURE, output_dir=Path(folder), template=None, latexmk="latexmk",
                pdfinfo="pdfinfo", pdftotext="pdftotext", skip_compile=False,
            )
            report = resume.build(args)
            self.assertTrue(report["compiled"])
            self.assertEqual(report["pages"], 1)
            self.assertEqual(report["overfull_boxes"], 0)
            self.assertEqual(report["missing_glyphs"], 0)
            self.assertIsInstance(report["content_height_ratio"], float)
            self.assertTrue((Path(folder) / "resume.pdf").is_file())

    @unittest.skipUnless(shutil.which("latexmk") and shutil.which("xelatex") and shutil.which("pdfinfo"), "XeLaTeX toolchain unavailable")
    def test_sparse_resume_uses_relaxed_profile(self):
        data = self.data()
        data["sections"] = data["sections"][:1]
        data["sections"][0]["items"][0]["bullets"] = data["sections"][0]["items"][0]["bullets"][:1]
        with tempfile.TemporaryDirectory() as folder:
            input_path = Path(folder) / "sparse.json"
            input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            report = resume.build(Namespace(
                input=input_path, output_dir=Path(folder) / "output", template=None, latexmk="latexmk",
                pdfinfo="pdfinfo", pdftotext="pdftotext", skip_compile=False,
            ))
            self.assertEqual(report["pages"], 1)
            self.assertEqual(report["profile"], "relaxed")
            self.assertIsInstance(report["content_height_ratio"], float)
            self.assertLess(report["content_height_ratio"], resume.SPARSE_PAGE_THRESHOLD)
            self.assertTrue(any("已确认材料" in reason for reason in report["optimization_reasons"]))

    @unittest.skipUnless(shutil.which("latexmk") and shutil.which("xelatex") and shutil.which("pdfinfo"), "XeLaTeX toolchain unavailable")
    def test_dense_resume_reports_content_reduction_instead_of_illegal_shrinking(self):
        data = self.data()
        original = data["sections"][2]["items"]
        dense = []
        for index in range(10):
            for item in original:
                copied = copy.deepcopy(item)
                copied["id"] = f"{item['id']}-{index}"
                dense.append(copied)
        data["sections"][2]["items"] = dense
        with tempfile.TemporaryDirectory() as folder:
            input_path = Path(folder) / "dense.json"
            input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            output = Path(folder) / "output"
            report = resume.build(Namespace(
                input=input_path, output_dir=output, template=None, latexmk="latexmk",
                pdfinfo="pdfinfo", pdftotext="/definitely/missing/pdftotext", skip_compile=False,
            ))
            self.assertGreater(report["pages"], 1)
            self.assertEqual(report["profile"], "tight")
            self.assertTrue(any("超过目标" in reason for reason in report["optimization_reasons"]))


if __name__ == "__main__":
    unittest.main()
