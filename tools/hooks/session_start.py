#!/usr/bin/env python3
"""Global SessionStart hook — guides user to /vibe-init."""
import json, sys
from pathlib import Path

def main():
    banner = 'Vibe Commander available. Run /vibe-init "<your request>" to start a managed run.'

    # Check for active run
    current = Path(".ai") / "current"
    if current.exists():
        try:
            sf = current.resolve() / "state.json"
            if sf.exists():
                s = json.loads(sf.read_text())
                st = s.get("status", "?")
                if st not in ("DONE", "STUCK"):
                    banner += f" | Active run: {s.get('run_id','?')} ({st})"
        except Exception:
            pass

    print(json.dumps({"systemMessage": banner}))
    sys.exit(0)

if __name__ == "__main__":
    main()
