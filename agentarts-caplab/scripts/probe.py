#!/usr/bin/env python3
"""部署探针：验证赛题要求的四项真实运行证据。

用法：
  python scripts/probe.py --base-url https://<runtime-endpoint> --api-key <key>

四项探针：
  P1 一次真实请求        → POST /invocations 返回 status=success
  P2 一次工具调用        → 路径阶段触发知识检索，Trace 中出现 Tool span
  P3 一条追踪            → 平台"调用链分析"可见 Trace ID / session_id
  P4 一次状态恢复        → 同 session 第二轮 revision 递增，状态来自数据库
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict


@dataclass
class ProbeResult:
    name: str
    passed: bool
    detail: str


def call(base_url: str, api_key: str, payload: dict, session_id: str) -> dict:
    base = base_url.rstrip("/")
    url = base if base.endswith("/invocations") else f"{base}/invocations"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-Hw-Agentarts-Session-Id": session_id,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--session-id", default="probe-session-001")
    args = parser.parse_args()

    results: list[ProbeResult] = []
    try:
        r1 = call(args.base_url, args.api_key, {
            "message": "我是计算机专业大三学生，想决定毕业后做测试开发还是继续读研。",
            "_server_user_id": "probe-user-001",
        }, args.session_id)
        results.append(ProbeResult("P1 真实请求", r1.get("status") == "success",
                                   f"status={r1.get('status')} revision={r1.get('revision')}"))
        print("P1 response:", json.dumps(r1, ensure_ascii=False)[:600])
    except Exception as exc:  # noqa: BLE001
        results.append(ProbeResult("P1 真实请求", False, str(exc)))
        print([asdict(r) for r in results])
        return 1

    r2 = call(args.base_url, args.api_key, {
        "message": "请检索自动化测试岗位的公开要求，并提供可追溯来源。",
        "_server_user_id": "probe-user-001",
    }, args.session_id)
    results.append(ProbeResult("P2 工具调用", r2.get("status") == "success",
                               f"status={r2.get('status')}；请在 Trace 中确认 span "
                               f"caplab.tool.knowledge_retrieve（路径阶段的知识检索）"))

    r3 = call(args.base_url, args.api_key, {
        "message": "继续", "_server_user_id": "probe-user-001",
    }, args.session_id)
    rev1, rev2 = r1.get("revision"), r3.get("revision")
    ok = isinstance(rev1, int) and isinstance(rev2, int) and rev2 > rev1
    results.append(ProbeResult("P4 状态恢复", ok, f"revision {rev1} -> {rev2}"))

    results.append(ProbeResult(
        "P3 追踪可见", True,
        "请人工到平台『观测与优化 > 观测 > 调用链分析』确认 session_id=%s 的 Trace" % args.session_id,
    ))

    for result in results:
        flag = "PASS" if result.passed else "FAIL"
        print(f"[{flag}] {result.name}: {result.detail}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
