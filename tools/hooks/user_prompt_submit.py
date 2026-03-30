#!/usr/bin/env python3
"""
UserPromptSubmit hook — Injects Vibe Commander enforcement into model context.

Unlike SessionStart/systemMessage (UI-only), this hook outputs additionalContext
which is appended directly to the user message Claude reads — guaranteeing the
state machine reminder is in the active context before any tool call fires.
"""

import json
import sys
from pathlib import Path


def main():
    repo_root = Path(__file__).parent.parent.parent

    # Check for active run
    active_run_note = ""
    current_link = repo_root / ".ai" / "current"
    if current_link.exists():
        try:
            state_file = current_link.resolve() / "state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                status = state.get("status", "unknown")
                run_id = state.get("run_id", "?")
                step = state.get("current_step", 0)
                total = state.get("total_steps", "?")
                if status not in ("DONE", "STUCK"):
                    active_run_note = (
                        "\n[ACTIVE RUN: " + run_id + " | " + status
                        + " | step " + str(step) + "/" + str(total) + "]"
                        "\nResume: python3 tools/state_manager.py status"
                    )
        except Exception:
            pass

    context = (
        "[VIBE COMMANDER ENFORCEMENT]\n"
        "MANDATORY FIRST ACTION — before Agent, before Read, before ANY other tool:\n"
        "  Bash: python3 tools/new_run.py \"<one-line description>\"\n"
        "  -> get run_id -> follow state machine (INTAKE -> PLAN -> REVIEWS -> WAIT_APPROVAL -> IMPLEMENT)\n"
        "FORBIDDEN: Write tool, Edit tool, --yolo, skipping WAIT_APPROVAL\n"
        "Analysis request? -> Gemini project-scan flow (preflight first)"
        + active_run_note
    )

    print(json.dumps({"additionalContext": context}))
    sys.exit(0)


if __name__ == "__main__":
    main()
