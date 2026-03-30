#!/usr/bin/env python3
"""
Global PreToolUse hook — Write/Edit governance gate.

Blocks Write/Edit tools (R1/R2). Logs Bash commands for audit.
Run-existence enforcement removed — framework activation is now via /vibe-init skill.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def log(entry):
    log_dir = Path(".ai") / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(log_dir / "audit.log", "a") as f:
        f.write(f"{ts} {entry}\n")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Block Write/Edit always (R1/R2)
    if tool_name in ("Write", "Edit"):
        log(f"BLOCKED {tool_name}: {str(tool_input)[:150]}")
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"[GOVERNANCE R1/R2] {tool_name} is forbidden. "
                "All file changes must go through the approved workflow.\n"
                "Use /vibe-init to start a managed run, then /vibe-step to implement."
            ),
        }))
        sys.exit(0)

    # Audit log for Bash
    if tool_name == "Bash":
        log(f"BASH: {tool_input.get('command', '')[:300]}")

    print(json.dumps({"decision": "allow"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
