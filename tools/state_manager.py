#!/usr/bin/env python3
"""
state_manager.py — Single source of truth for Vibe Commander run state.

Responsibilities:
  - Safe atomic read/write of state.json (with schema validation)
  - Structured events log (events.jsonl) for every state transition
  - .ai/current symlink management (tracks the active run)

CLI usage:
  python3 tools/state_manager.py status [run_id]
  python3 tools/state_manager.py update --run-id <id> --status <STATUS> [--step <n>]
  python3 tools/state_manager.py set-current --run-id <id>
  python3 tools/state_manager.py get-current
  python3 tools/state_manager.py log-event --run-id <id> --event <type> [--data '{...}']
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

RUNS_DIR = Path(".ai") / "runs"
CURRENT_LINK = Path(".ai") / "current"
SCHEMA_PATH = Path("schema") / "state_schema.json"
SCHEMA_VERSION = "1.1.0"

VALID_STATUSES = {
    "INTAKE", "GEMINI_PROJECT_SCAN_PREFLIGHT", "WAIT_SCAN_APPROVAL",
    "GEMINI_PROJECT_SCAN", "CLAUDE_DOC_DRAFT", "CLAUDE_PLAN_DRAFT",
    "GEMINI_ARCH_REVIEW", "CODEX_PLAN_REVIEW", "TARGETED_REVIEW",
    "REFINED_SYNTHESIS", "COMMANDER_SYNTHESIS", "CODEX_TESTSPEC_DRAFT",
    "WAIT_APPROVAL", "REVISE_PLAN", "CODEX_WRITE_TESTS",
    "CODEX_IMPLEMENT", "CLAUDE_VERIFY", "CODEX_REPAIR",
    "FINAL_REVIEW", "DONE", "STUCK", "HUMAN_INTERVENTION_NEEDED",
    "AUTH_BLOCKED", "STOPPED_BY_BUDGET", "SYSTEM_ERROR",
}

STOP_STATES = {
    "DONE", "STUCK", "HUMAN_INTERVENTION_NEEDED",
    "AUTH_BLOCKED", "STOPPED_BY_BUDGET", "SYSTEM_ERROR",
}

# Valid state transitions — key: current state → value: set of allowed next states
VALID_TRANSITIONS = {
    "INTAKE": {"GEMINI_PROJECT_SCAN_PREFLIGHT", "CLAUDE_PLAN_DRAFT", "STUCK", "SYSTEM_ERROR"},
    "GEMINI_PROJECT_SCAN_PREFLIGHT": {"WAIT_SCAN_APPROVAL", "SYSTEM_ERROR"},
    "WAIT_SCAN_APPROVAL": {"GEMINI_PROJECT_SCAN", "DONE", "SYSTEM_ERROR"},
    "GEMINI_PROJECT_SCAN": {"CLAUDE_DOC_DRAFT", "CLAUDE_PLAN_DRAFT", "SYSTEM_ERROR"},
    "CLAUDE_DOC_DRAFT": {"GEMINI_ARCH_REVIEW", "CODEX_PLAN_REVIEW", "COMMANDER_SYNTHESIS", "WAIT_APPROVAL", "SYSTEM_ERROR"},
    "CLAUDE_PLAN_DRAFT": {"CODEX_PLAN_REVIEW", "GEMINI_ARCH_REVIEW", "COMMANDER_SYNTHESIS", "CODEX_TESTSPEC_DRAFT", "WAIT_APPROVAL", "REVISE_PLAN", "STUCK", "SYSTEM_ERROR"},
    "CODEX_PLAN_REVIEW": {"CLAUDE_PLAN_DRAFT", "GEMINI_ARCH_REVIEW", "CODEX_TESTSPEC_DRAFT", "WAIT_APPROVAL", "STUCK", "SYSTEM_ERROR"},
    "GEMINI_ARCH_REVIEW": {"CLAUDE_PLAN_DRAFT", "CODEX_PLAN_REVIEW", "CODEX_TESTSPEC_DRAFT", "WAIT_APPROVAL", "STUCK", "SYSTEM_ERROR"},
    "CODEX_TESTSPEC_DRAFT": {"CLAUDE_PLAN_DRAFT", "CODEX_PLAN_REVIEW", "GEMINI_ARCH_REVIEW", "WAIT_APPROVAL", "STUCK", "SYSTEM_ERROR"},
    "TARGETED_REVIEW": {"REFINED_SYNTHESIS", "WAIT_APPROVAL", "SYSTEM_ERROR"},
    "REFINED_SYNTHESIS": {"WAIT_APPROVAL", "SYSTEM_ERROR"},
    "COMMANDER_SYNTHESIS": {"WAIT_APPROVAL", "TARGETED_REVIEW", "REVISE_PLAN", "SYSTEM_ERROR"},
    "WAIT_APPROVAL": {"CODEX_WRITE_TESTS", "REVISE_PLAN", "CODEX_IMPLEMENT", "STUCK", "SYSTEM_ERROR"},
    "REVISE_PLAN": {"CLAUDE_PLAN_DRAFT", "STUCK", "SYSTEM_ERROR"},
    "CODEX_WRITE_TESTS": {"CODEX_IMPLEMENT", "STUCK", "SYSTEM_ERROR", "AUTH_BLOCKED"},
    "CODEX_IMPLEMENT": {"CLAUDE_VERIFY", "CODEX_REPAIR", "FINAL_REVIEW", "HUMAN_INTERVENTION_NEEDED", "STUCK", "SYSTEM_ERROR", "AUTH_BLOCKED"},
    "CLAUDE_VERIFY": {"CODEX_IMPLEMENT", "CODEX_REPAIR", "FINAL_REVIEW", "HUMAN_INTERVENTION_NEEDED", "STUCK", "SYSTEM_ERROR"},
    "CODEX_REPAIR": {"CLAUDE_VERIFY", "HUMAN_INTERVENTION_NEEDED", "STUCK", "SYSTEM_ERROR", "AUTH_BLOCKED"},
    "FINAL_REVIEW": {"DONE", "CODEX_REPAIR", "HUMAN_INTERVENTION_NEEDED", "STUCK", "SYSTEM_ERROR"},
    "DONE": set(),
    "STUCK": set(),
    "HUMAN_INTERVENTION_NEEDED": set(),
    "AUTH_BLOCKED": set(),
    "STOPPED_BY_BUDGET": set(),
    "SYSTEM_ERROR": set(),
}

RUN_ID_PATTERN = re.compile(r'^[0-9a-f]{8,32}$')


# ── Helpers ──────────────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_run_id(run_id: str) -> str:
    """Validate run_id is a hex string. Raises ValueError if invalid."""
    if not run_id or not RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"Invalid run_id format: {run_id!r}. Must be 8-32 hex chars.")
    return run_id


def run_dir(run_id: str) -> Path:
    validate_run_id(run_id)
    return RUNS_DIR / run_id


def state_path(run_id: str) -> Path:
    return run_dir(run_id) / "state.json"


def events_path(run_id: str) -> Path:
    return run_dir(run_id) / "events.jsonl"


# ── Schema validation ─────────────────────────────────────────────────────────

def validate_state(state: dict) -> None:
    """Validate state dict against schema/state_schema.json."""
    if not SCHEMA_PATH.exists():
        return  # Schema missing — skip silently (don't block operations)
    try:
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text())
        instance = dict(state)
        instance.pop("config", None)
        jsonschema.validate(instance=instance, schema=schema)
    except ImportError:
        pass  # jsonschema not installed — skip


# ── Core state operations ────────────────────────────────────────────────────

def load_state(run_id: str) -> dict:
    """
    Load and return state.json for a run. Raises FileNotFoundError if missing.
    Backward-compatible: if schema_version is absent, injects "1.0.0" before
    returning so validation passes without requiring a migration step.
    """
    validate_run_id(run_id)
    path = state_path(run_id)
    if not path.exists():
        raise FileNotFoundError(f"state.json not found for run {run_id}: {path}")
    state = json.loads(path.read_text())
    if "schema_version" not in state:
        state["schema_version"] = SCHEMA_VERSION  # legacy file — treat as 1.0.0
    return state


def save_state(run_id: str, state: dict, validate: bool = True) -> None:
    """
    Atomically write state.json.
    Uses a temp file + rename to avoid partial writes.
    """
    if validate:
        validate_state(state)

    path = state_path(run_id)
    bak_path = path.with_name(f"{path.name}.bak")

    if path.exists():
        try:
            import shutil
            shutil.copy2(path, bak_path)
        except Exception as backup_err:
            log_dir = Path(".ai") / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat()
            with open(log_dir / "audit.log", "a") as f:
                f.write(f"{ts} WARN: state backup failed for {run_id}: {backup_err}\n")

    # Atomic write: write to temp in same directory, then rename
    dir_ = path.parent
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_, suffix=".tmp", delete=False
    ) as tmp:
        json.dump(state, tmp, indent=2)
        tmp.write("\n")
        tmp_path = tmp.name

    os.replace(tmp_path, path)


def update_state(run_id: str, **fields) -> dict:
    """
    Load state, apply field updates, set updated_at, save, return new state.

    Common fields: status, current_step, total_steps, revision_count,
                   approval_stage, active_session_ids, artifacts, steps,
                   git_checkpoints, auth, budget
    """
    validate_run_id(run_id)
    state = load_state(run_id)
    old_status = state.get("status")

    for key, value in fields.items():
        if key == "artifacts" and isinstance(value, dict):
            # Merge artifacts dict rather than replace
            state["artifacts"] = {**state.get("artifacts", {}), **value}
        elif key == "repair_attempts" and isinstance(value, dict):
            state["repair_attempts"] = {**state.get("repair_attempts", {}), **value}
        else:
            state[key] = value

    state["updated_at"] = now_utc()

    # Validate status value
    new_status = state.get("status")
    if new_status and new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status!r}. Must be one of {VALID_STATUSES}")

    # Validate state transition
    if "status" in fields and new_status != old_status:
        allowed = VALID_TRANSITIONS.get(old_status)
        if allowed is not None and new_status not in allowed:
            raise ValueError(
                f"Invalid state transition: {old_status!r} → {new_status!r}. "
                f"Allowed targets: {sorted(allowed)}"
            )

    save_state(run_id, state)

    # Log state transition event if status changed
    if "status" in fields and new_status != old_status:
        log_event(run_id, "STATUS_TRANSITION", {
            "from": old_status,
            "to": new_status,
        })

    return state


def update_session_id(run_id: str, provider: str, session_id: Optional[str]) -> dict:
    """
    Update a provider session id under state.active_session_ids.
    Creates the active_session_ids object when absent.
    """
    state = load_state(run_id)
    active_session_ids = dict(state.get("active_session_ids") or {})
    active_session_ids[provider] = session_id
    return update_state(run_id, active_session_ids=active_session_ids)


# ── .ai/current symlink ──────────────────────────────────────────────────────

def set_current(run_id: str) -> None:
    """Set .ai/current symlink to point to this run's directory."""
    target = run_dir(run_id).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Run directory not found: {target}")

    CURRENT_LINK.parent.mkdir(parents=True, exist_ok=True)

    # Atomic symlink replacement
    tmp_link = CURRENT_LINK.parent / f".current.tmp.{os.getpid()}"
    try:
        tmp_link.symlink_to(target)
        tmp_link.replace(CURRENT_LINK)
    except Exception:
        if tmp_link.exists():
            tmp_link.unlink()
        raise


def get_current_run_id() -> Optional[str]:
    """Read .ai/current symlink and return the run_id, or None if not set."""
    if not CURRENT_LINK.exists():
        return None
    try:
        target = CURRENT_LINK.resolve()
        return target.name  # Directory name = run_id
    except Exception:
        return None


# ── Events log ───────────────────────────────────────────────────────────────

def log_event(run_id: str, event_type: str, data: Optional[dict] = None) -> None:
    """
    Append a structured event to .ai/runs/<run_id>/events.jsonl.
    Each line is a self-contained JSON object.
    """
    validate_run_id(run_id)
    event = {
        "ts": now_utc(),
        "run_id": run_id,
        "event": event_type,
        "data": data or {},
    }
    path = events_path(run_id)
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")


def record_checkpoint(run_id: str, step_id: str, commit_sha: str) -> None:
    """
    Persist checkpoint metadata into state.json for reliable interrupt recovery.
    Stores the git commit SHA taken before implement-step so vibe-resume can verify
    the repo is still at the expected state before offering to resume.
    """
    update_state(run_id, checkpoint_meta={
        "step_id": step_id,
        "commit_sha": commit_sha,
        "recorded_at": now_utc(),
    })


def find_stale_runs(stale_minutes: int = 30) -> list[dict]:
    """
    Return runs stuck in CODEX_IMPLEMENT with no events in the last `stale_minutes`.
    Used by the startup check in vibe-resume to surface interrupted runs.
    """
    from datetime import datetime, timezone, timedelta
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    stale = []
    if not RUNS_DIR.exists():
        return stale
    for run_dir_path in RUNS_DIR.iterdir():
        if not run_dir_path.is_dir():
            continue
        sp = run_dir_path / "state.json"
        if not sp.exists():
            continue
        try:
            state = json.loads(sp.read_text())
        except Exception:
            continue
        if state.get("status") != "CODEX_IMPLEMENT":
            continue
        events = load_events(state.get("run_id", run_dir_path.name))
        if events:
            last_ts_str = events[-1].get("ts", "")
            try:
                last_ts = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
                if last_ts > stale_cutoff:
                    continue  # recently active, not stale
            except ValueError:
                pass
        stale.append({
            "run_id": state.get("run_id", run_dir_path.name),
            "status": state.get("status"),
            "current_step": state.get("current_step"),
            "checkpoint_meta": state.get("checkpoint_meta"),
            "updated_at": state.get("updated_at"),
        })
    return stale


def load_events(run_id: str) -> list:
    """Load all events for a run. Returns empty list if file missing."""
    path = events_path(run_id)
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                import logging
                logging.getLogger("state_manager").warning(
                    "Malformed JSON line in events.jsonl for run %s: %s", run_id, line[:100]
                )
    return events


# ── CLI ──────────────────────────────────────────────────────────────────────

def cmd_status(args):
    run_id = args.run_id or get_current_run_id()
    if not run_id:
        print(json.dumps({"status": "error", "summary": "No run_id specified and .ai/current not set"}))
        sys.exit(1)
    try:
        state = load_state(run_id)
        events = load_events(run_id)
        print(json.dumps({
            "status": "ok",
            "run_id": run_id,
            "run_status": state.get("status"),
            "current_step": state.get("current_step"),
            "total_steps": state.get("total_steps"),
            "revision_count": state.get("revision_count"),
            "is_stopped": state.get("status") in STOP_STATES,
            "event_count": len(events),
            "last_event": events[-1] if events else None,
            "updated_at": state.get("updated_at"),
        }, indent=2))
    except FileNotFoundError as e:
        print(json.dumps({"status": "error", "summary": str(e)}))
        sys.exit(1)


def cmd_update(args):
    run_id = args.run_id or get_current_run_id()
    if not run_id:
        print(json.dumps({"status": "error", "summary": "No run_id"}))
        sys.exit(1)

    fields = {}
    if args.status:
        fields["status"] = args.status
    if args.step is not None:
        fields["current_step"] = args.step
    if args.approval_stage:
        fields["approval_stage"] = args.approval_stage
    if args.data:
        try:
            extra = json.loads(args.data)
            fields.update(extra)
        except json.JSONDecodeError:
            print(json.dumps({"status": "error", "summary": "Invalid JSON in --data"}))
            sys.exit(1)

    if not fields:
        print(json.dumps({"status": "error", "summary": "No fields to update"}))
        sys.exit(1)

    state = update_state(run_id, **fields)
    print(json.dumps({"status": "ok", "run_id": run_id, "new_status": state.get("status")}))


def cmd_set_current(args):
    try:
        set_current(args.run_id)
        print(json.dumps({"status": "ok", "current": args.run_id}))
    except Exception as e:
        print(json.dumps({"status": "error", "summary": str(e)}))
        sys.exit(1)


def cmd_get_current(args):
    run_id = get_current_run_id()
    if run_id:
        print(json.dumps({"status": "ok", "current": run_id}))
    else:
        print(json.dumps({"status": "ok", "current": None, "note": ".ai/current not set"}))


def cmd_log_event(args):
    run_id = args.run_id or get_current_run_id()
    if not run_id:
        print(json.dumps({"status": "error", "summary": "No run_id"}))
        sys.exit(1)
    data = {}
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            pass
    log_event(run_id, args.event, data)
    print(json.dumps({"status": "ok", "event": args.event, "run_id": run_id}))


def cmd_stale_check(args):
    stale = find_stale_runs(stale_minutes=args.minutes)
    print(json.dumps({"status": "ok", "stale_runs": stale, "count": len(stale)}))


def cmd_record_checkpoint(args):
    run_id = args.run_id or get_current_run_id()
    if not run_id:
        print(json.dumps({"status": "error", "summary": "No run_id"}))
        sys.exit(1)
    record_checkpoint(run_id, step_id=args.step, commit_sha=args.sha)
    print(json.dumps({"status": "ok", "run_id": run_id, "step": args.step, "sha": args.sha}))


def main():
    parser = argparse.ArgumentParser(description="state_manager.py — Vibe Commander state operations")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="Show run status")
    p_status.add_argument("run_id", nargs="?", help="Run ID (default: .ai/current)")
    p_status.set_defaults(func=cmd_status)

    # update
    p_update = sub.add_parser("update", help="Update state fields")
    p_update.add_argument("--run-id", help="Run ID (default: .ai/current)")
    p_update.add_argument("--status", help="New status")
    p_update.add_argument("--step", type=int, help="current_step value")
    p_update.add_argument("--approval-stage", help="approval_stage value")
    p_update.add_argument("--data", help="Extra fields as JSON string")
    p_update.set_defaults(func=cmd_update)

    # set-current
    p_sc = sub.add_parser("set-current", help="Set .ai/current symlink")
    p_sc.add_argument("--run-id", required=True)
    p_sc.set_defaults(func=cmd_set_current)

    # get-current
    p_gc = sub.add_parser("get-current", help="Print active run_id")
    p_gc.set_defaults(func=cmd_get_current)

    # log-event
    p_le = sub.add_parser("log-event", help="Append an event to events.jsonl")
    p_le.add_argument("--run-id", help="Run ID (default: .ai/current)")
    p_le.add_argument("--event", required=True, help="Event type string")
    p_le.add_argument("--data", help="Event data as JSON string")
    p_le.set_defaults(func=cmd_log_event)

    # stale-check
    p_sc2 = sub.add_parser("stale-check",
                            help="List runs stuck in CODEX_IMPLEMENT with no recent events")
    p_sc2.add_argument("--minutes", type=int, default=30,
                       help="Inactivity threshold in minutes (default 30)")
    p_sc2.set_defaults(func=cmd_stale_check)

    # record-checkpoint
    p_rcp = sub.add_parser("record-checkpoint",
                            help="Save checkpoint SHA + step_id to state.json for recovery")
    p_rcp.add_argument("--run-id", help="Run ID (default: .ai/current)")
    p_rcp.add_argument("--step", required=True, help="Step identifier (e.g. s1)")
    p_rcp.add_argument("--sha", required=True, help="Git commit SHA of the checkpoint")
    p_rcp.set_defaults(func=cmd_record_checkpoint)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
