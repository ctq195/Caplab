#!/usr/bin/env python3
"""Qianfan chat assist for CapLab (v2.0.1, optional enhancement).

During path convergence, this script calls a Qianfan / OpenAI-compatible
chat-completions endpoint to draft an evidence synthesis for candidate paths
(support / against / gaps). The output is a DRAFT ONLY:

- every source reference must come from the provided retrieval evidence;
- the rule layer validates the draft (no invented Source_ID/Claim_ID,
  no decisions, no scoring of persons) and nothing is written to state
  without explicit user confirmation.

When the API is not configured the script exits with code 3 and a clear
message; the stage module then falls back to its template-based comparison.

Privacy: the payload is limited to confirmed profile facts + candidate path
IDs + retrieved evidence summaries. Never send full transcripts, complete
profiles, health, family or financial details.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Optional

import caplab_encoder  # reuse api_config_from()


def chat_completion(
    cfg: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    timeout: int = 60,
) -> str:
    model = cfg.get("chat_model") or "ernie-speed-128k"
    base_url = (cfg.get("base_url") or "https://qianfan.baidubce.com/v2").rstrip("/")
    api_key = cfg.get("api_key")
    if not api_key:
        raise RuntimeError("api_key is not set in the API config")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected chat API response: {str(result)[:300]}") from exc


def _load_json_arg(value: str) -> Any:
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def synthesize_evidence(
    cfg: dict[str, Any],
    profile_summary: str,
    paths: list[str],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    system_prompt = (
        "你是 CapLab 生涯决策助手。只依据用户提供的检索证据做候选路径的"
        "支持/反对证据归纳与缺口识别。硬性要求：\n"
        "1. 每条归纳必须引用证据中的 Source_ID 或 Claim_ID，不得编造来源；\n"
        "2. 不给职业打分、排序或做排除性结论，不诊断用户；\n"
        "3. 识别信息缺口并转成待用户确认的问题，不做假设；\n"
        "4. 输出严格 JSON：{\"per_path\": {\"<PTH-xxx>\": {\"support\": "
        "[{\"source\":\"SRC-xxx\",\"claim\":\"...\"}], \"against\": [], "
        "\"gaps\": [\"...\"], \"needs_user_confirmation\": true}}, "
        "\"notes\": [\"...\"]}。"
    )
    user_prompt = json.dumps({
        "profile_summary": profile_summary,
        "candidate_paths": paths,
        "retrieved_evidence": evidence,
    }, ensure_ascii=False, indent=2)

    raw = chat_completion(cfg, system_prompt, user_prompt)
    try:
        draft = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise RuntimeError("chat API returned non-JSON; refusing to use as draft")
        draft = json.loads(raw[start:end + 1])

    # rule-layer validation of the draft
    known_sources = {e.get("Source_ID") for e in evidence if e.get("Source_ID")}
    known_claims = {c for e in evidence for c in (e.get("Claim_IDs") or [])}
    problems: list[str] = []
    for pid, item in (draft.get("per_path") or {}).items():
        for side in ("support", "against"):
            for ref in item.get(side, []):
                sid = str(ref.get("source", ""))
                if sid.startswith("SRC") and sid not in known_sources:
                    problems.append(f"{pid} {side} invents source {sid}")
                if str(ref.get("source", "")).startswith("CLM") and ref.get("source") not in known_claims:
                    problems.append(f"{pid} {side} invents claim {ref.get('source')}")
    if problems:
        raise RuntimeError("draft failed rule-layer validation: " + "; ".join(problems[:5]))

    return {
        "draft": True,
        "model": cfg.get("chat_model"),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "per_path": draft.get("per_path", {}),
        "notes": draft.get("notes", []),
        "validated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="caplab_qianfan_assist",
        description="Draft evidence synthesis for candidate paths via Qianfan chat API (draft only).",
    )
    parser.add_argument("--config", default=None, help="Path to the API config JSON")
    parser.add_argument("--profile-summary", required=True, help="Short confirmed profile summary")
    parser.add_argument("--paths", required=True, help="Comma-separated candidate path IDs")
    parser.add_argument("--evidence", required=True,
                        help="Retrieved evidence: JSON string or path to a JSON file "
                             "(list of {Source_ID, Claim_IDs, title, text_preview, evidence_level})")
    parser.add_argument("--out", default=None, help="Write the validated draft to this file")
    args = parser.parse_args()

    cfg = caplab_encoder.api_config_from(Path(args.config) if args.config else None)
    if cfg is None:
        print(json.dumps({
            "ok": False, "reason": "no API config; template fallback remains",
        }, ensure_ascii=False, indent=2))
        return 3

    evidence = _load_json_arg(args.evidence)
    if not isinstance(evidence, list):
        print("ERROR: --evidence must be a list of evidence objects", file=sys.stderr)
        return 2

    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    try:
        draft = synthesize_evidence(cfg, args.profile_summary, paths, evidence)
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(draft, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
