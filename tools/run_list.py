#!/usr/bin/env python3
"""
run_list.py — List all Vibe Commander runs with their status.

Usage:
  python3 tools/run_list.py [--json]

Output (default): aligned table sorted by updated_at descending.
Output (--json):  JSON array, one object per run.

Exit codes:
  0 — always (missing/malformed state.json entries shown as (error))
"""

import argparse
import glob
import json
import os
import sys

RUNS_DIR = os.path.join(".ai", "runs")
RUN_ID_WIDTH = 12
STATUS_WIDTH = 28
STEP_WIDTH = 6


def load_runs() -> list[dict]:
    """Scan .ai/runs/*/state.json and return a list of run summaries."""
    pattern = os.path.join(RUNS_DIR, "*", "state.json")
    rows = []
    for path in sorted(glob.glob(pattern)):
        run_id = os.path.basename(os.path.dirname(path))
        try:
            with open(path) as f:
                state = json.load(f)
            rows.append({
                "run_id": run_id,
                "status": state.get("status", "unknown"),
                "current_step": state.get("current_step", 0),
                "total_steps": state.get("total_steps", 0),
                "updated_at": state.get("updated_at", ""),
            })
        except Exception:
            rows.append({
                "run_id": run_id,
                "status": "(error)",
                "current_step": None,
                "total_steps": None,
                "updated_at": "",
            })
    # Sort: newest first (updated_at descending); error rows go to bottom
    rows.sort(key=lambda r: r["updated_at"] or "", reverse=True)
    return rows


def print_table(rows: list[dict]) -> None:
    header = (
        f"{'RUN_ID':<{RUN_ID_WIDTH}}  "
        f"{'STATUS':<{STATUS_WIDTH}}  "
        f"{'STEP':<{STEP_WIDTH}}  "
        f"UPDATED_AT"
    )
    separator = "-" * len(header)
    print(header)
    print(separator)
    for r in rows:
        step_str = (
            f"{r['current_step']}/{r['total_steps']}"
            if r["current_step"] is not None
            else "-"
        )
        run_id_display = r["run_id"][:RUN_ID_WIDTH]
        print(
            f"{run_id_display:<{RUN_ID_WIDTH}}  "
            f"{r['status']:<{STATUS_WIDTH}}  "
            f"{step_str:<{STEP_WIDTH}}  "
            f"{r['updated_at']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="run_list.py — list all Vibe Commander runs")
    parser.add_argument("--json", action="store_true", help="Output as JSON array")
    args = parser.parse_args()

    if not os.path.isdir(RUNS_DIR):
        if args.json:
            print("[]")
        else:
            print_table([])
        return

    rows = load_runs()

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
