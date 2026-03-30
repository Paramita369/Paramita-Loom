#!/usr/bin/env python3
"""
run_status.py — Human-readable Vibe Commander run progress viewer.

Usage:
  python3 tools/run_status.py              # use .ai/current
  python3 tools/run_status.py <run_id>     # specific run
  python3 tools/run_status.py --json       # machine-readable
  python3 tools/run_status.py --list       # list all runs
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.state_manager import (
    load_state, load_events, get_current_run_id,
    RUNS_DIR, STOP_STATES,
)

STATUS_ICON = {
    "INTAKE":                    "📥",
    "CLAUDE_PLAN_DRAFT":         "📝",
    "GEMINI_ARCH_REVIEW":        "🔍",
    "CODEX_PLAN_REVIEW":         "🔎",
    "CODEX_TESTSPEC_DRAFT":      "🧪",
    "WAIT_APPROVAL":             "⏸ ",
    "REVISE_PLAN":               "🔄",
    "CODEX_WRITE_TESTS":         "✍️ ",
    "CODEX_IMPLEMENT":           "⚙️ ",
    "CLAUDE_VERIFY":             "✅",
    "CODEX_REPAIR":              "🔧",
    "FINAL_REVIEW":              "🏁",
    "DONE":                      "🎉",
    "STUCK":                     "🚨",
    "HUMAN_INTERVENTION_NEEDED": "🆘",
    "AUTH_BLOCKED":              "🔐",
    "STOPPED_BY_BUDGET":         "💰",
    "SYSTEM_ERROR":              "💥",
}

STEP_ICON = {"pending": "○", "in_progress": "●", "done": "✓", "failed": "✗"}


def fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        elif secs < 3600:
            return f"{secs // 60}m ago"
        elif secs < 86400:
            return f"{secs // 3600}h ago"
        else:
            return f"{secs // 86400}d ago"
    except Exception:
        return iso


def print_run(run_id: str, output_json: bool = False):
    try:
        state = load_state(run_id)
        events = load_events(run_id)
    except FileNotFoundError:
        print(f"Run not found: {run_id}", file=sys.stderr)
        sys.exit(1)

    if output_json:
        print(json.dumps({
            "run_id": run_id,
            "status": state.get("status"),
            "current_step": state.get("current_step"),
            "total_steps": state.get("total_steps"),
            "revision_count": state.get("revision_count"),
            "request": state.get("request"),
            "updated_at": state.get("updated_at"),
            "events": events,
            "artifacts": state.get("artifacts"),
            "steps": state.get("steps"),
        }, indent=2))
        return

    status = state.get("status", "?")
    icon = STATUS_ICON.get(status, "❓")
    is_stopped = status in STOP_STATES

    print()
    print(f"  Run ID  : {run_id}")
    print(f"  Request : {state.get('request', '?')[:72]}")
    print(f"  Status  : {icon} {status}")
    print(f"  Updated : {fmt_time(state.get('updated_at', ''))}")

    if state.get("total_steps", 0) > 0:
        print(f"  Progress: step {state.get('current_step', 0)} / {state.get('total_steps', 0)}")

    if state.get("revision_count", 0) > 0:
        print(f"  Revisions: {state['revision_count']} (max 3)")

    repair = state.get("repair_attempts", {})
    if repair:
        print(f"  Repairs : {repair}")

    # Steps
    steps = state.get("steps", [])
    if steps:
        print()
        print("  Steps:")
        for s in steps:
            icon_s = STEP_ICON.get(s.get("status", ""), "?")
            print(f"    {icon_s} [{s.get('id','?')}] {s.get('title','?')} — {s.get('status','?')}")

    # Key artifacts
    artifacts = {k: v for k, v in (state.get("artifacts") or {}).items() if v}
    if artifacts:
        print()
        print("  Artifacts:")
        for k, v in artifacts.items():
            print(f"    · {k}: {v}")

    # Recent events
    if events:
        print()
        print(f"  Events ({len(events)} total, last 3):")
        for ev in events[-3:]:
            ts = fmt_time(ev.get("ts", ""))
            evt = ev.get("event", "?")
            data = ev.get("data", {})
            detail = ""
            if "from" in data and "to" in data:
                detail = f" {data['from']} → {data['to']}"
            elif data:
                detail = f" {str(data)[:50]}"
            print(f"    [{ts}] {evt}{detail}")

    if is_stopped:
        print()
        print(f"  ⚠️  Run is in a STOP state: {status}")
        if status == "STUCK":
            print("     Revision count exceeded. Manual intervention required.")
        elif status == "HUMAN_INTERVENTION_NEEDED":
            print("     Repair attempts exceeded. Manual intervention required.")
        elif status == "AUTH_BLOCKED":
            print("     Run: python3 tools/auth/auth_doctor.py")

    print()


def list_runs():
    if not RUNS_DIR.exists():
        print("No runs found (.ai/runs/ does not exist)")
        return

    current = get_current_run_id()
    runs = sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    runs = [r for r in runs if r.is_dir() and (r / "state.json").exists()]

    if not runs:
        print("No runs found.")
        return

    print(f"\n  {'RUN ID':<12} {'STATUS':<32} {'UPDATED':<12} {'REQUEST'}")
    print(f"  {'-'*12} {'-'*32} {'-'*12} {'-'*40}")
    for r in runs:
        try:
            state = json.loads((r / "state.json").read_text())
            status = state.get("status", "?")
            updated = fmt_time(state.get("updated_at", ""))
            request = state.get("request", "")[:40]
            marker = " ◄ current" if r.name == current else ""
            icon = STATUS_ICON.get(status, "")
            print(f"  {r.name:<12} {icon} {status:<30} {updated:<12} {request}{marker}")
        except Exception:
            print(f"  {r.name:<12} (unreadable)")
    print()


def main():
    parser = argparse.ArgumentParser(description="run_status.py — view Vibe Commander run progress")
    parser.add_argument("run_id", nargs="?", help="Run ID (default: .ai/current)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", action="store_true", help="List all runs")
    args = parser.parse_args()

    if args.list:
        list_runs()
        return

    run_id = args.run_id or get_current_run_id()
    if not run_id:
        print("No run_id specified and .ai/current is not set.", file=sys.stderr)
        print("Usage: python3 tools/run_status.py <run_id>", file=sys.stderr)
        print("       python3 tools/run_status.py --list", file=sys.stderr)
        sys.exit(1)

    print_run(run_id, output_json=args.json)


if __name__ == "__main__":
    main()
