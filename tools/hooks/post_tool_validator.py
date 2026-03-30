#!/usr/bin/env python3
"""
PostToolUse hook — Validates wrapper script outputs.

Warns if codex_worker.py or gemini_planner.py returned
a critical status (auth_blocked, fatal_error).

Claude Code hook protocol:
  - Receives tool result as JSON on stdin
  - Output JSON with optional "message" field for warnings
  - Exit 0 always (post-use hooks are advisory)
"""

import json
import os
import sys
from datetime import datetime, timezone

WRAPPER_SCRIPTS = ("codex_worker.py", "gemini_planner.py", "auth_doctor.py")
CRITICAL_STATUSES = ("fatal_error", "auth_blocked", "system_error")


def log(entry: str):
    log_dir = ".ai/logs"
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(f"{log_dir}/audit.log", "a") as f:
        f.write(f"{ts} {entry}\n")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    command = tool_input.get("command", "")

    # Only validate wrapper script invocations
    if not any(script in command for script in WRAPPER_SCRIPTS):
        sys.exit(0)

    stdout = tool_response.get("stdout", "")
    if not stdout.strip():
        sys.exit(0)

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        log(f"WARN: Wrapper output not valid JSON. Command: {command[:100]}")
        sys.exit(0)

    status = result.get("status", "unknown")

    if status in CRITICAL_STATUSES:
        summary = result.get("summary", "no summary")
        log(f"CRITICAL: wrapper={command[:80]} status={status} summary={summary}")
        print(json.dumps({
            "message": (
                f"[GOVERNANCE] Wrapper returned critical status: {status}\n"
                f"Summary: {summary}\n"
                "Update state.json and check .ai/logs/audit.log"
            )
        }))

    elif status == "retryable_error":
        summary = result.get("summary", "")
        log(f"WARN: wrapper={command[:80]} status=retryable_error summary={summary}")

    sys.exit(0)


if __name__ == "__main__":
    main()
