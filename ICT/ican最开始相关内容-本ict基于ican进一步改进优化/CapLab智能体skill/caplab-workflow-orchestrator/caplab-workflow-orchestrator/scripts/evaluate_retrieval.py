#!/usr/bin/env python3
"""Evaluate a built CapLab index against the versioned retrieval cases."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=Path(__file__).resolve().parents[1] / "tests" / "retrieval_cases.json")
    parser.add_argument("--sparse-only", action="store_true")
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()
    suite = json.loads(args.cases.read_text(encoding="utf-8"))
    rag_script = Path(__file__).resolve().parent / "caplab_rag.py"
    outcomes = []
    for case in suite["cases"]:
        command = [
            sys.executable, str(rag_script), "search", "--index-dir", str(args.index_dir),
            "--workspace", str(args.workspace), "--query", case["query"], "--top-k", "5",
        ]
        if args.user_id and args.session_id:
            command += ["--user-id", args.user_id, "--session-id", args.session_id]
        if args.sparse_only:
            command.append("--sparse-only")
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", env=environment,
        )
        if completed.returncode:
            outcomes.append({"id": case["id"], "passed": False, "error": completed.stderr.strip()})
            continue
        payload = json.loads(completed.stdout)
        sheets = [item["sheet"] for item in payload["results"]]
        passed = any(sheet in case["expected_sheets"] for sheet in sheets)
        outcomes.append({"id": case["id"], "passed": passed, "sheets": sheets, "mode": payload["retrieval_mode"]})
    passed_count = sum(item["passed"] for item in outcomes)
    pass_rate = passed_count / len(outcomes) if outcomes else 0.0
    report = {"passed": passed_count, "total": len(outcomes), "pass_rate": pass_rate, "target": suite["target_pass_rate"], "cases": outcomes}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if pass_rate >= float(suite["target_pass_rate"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
