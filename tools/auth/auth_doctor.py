#!/usr/bin/env python3
"""
auth_doctor.py — Health check for all provider credentials.

Usage:
  python3 tools/auth/auth_doctor.py

Output: JSON report to stdout.
Exit 0 if all providers OK, exit 1 if any blocked.
"""

import json
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.auth import codex_auth_adapter, google_auth_adapter


def main():
    report = {
        "providers": {
            "google": google_auth_adapter.check_health(),
            "codex": codex_auth_adapter.check_health(),
        }
    }

    all_ok = all(v["status"] == "ok" for v in report["providers"].values())
    blocked = [k for k, v in report["providers"].items() if v["status"] == "blocked"]

    report["overall"] = "ok" if all_ok else "degraded"
    report["ready_to_run"] = all_ok
    if blocked:
        report["action_required"] = [
            report["providers"][k].get("fix", f"Fix {k} auth")
            for k in blocked
        ]

    print(json.dumps(report, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
