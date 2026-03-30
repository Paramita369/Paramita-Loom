#!/usr/bin/env python3
"""Initialize a new Vibe Commander run."""

import argparse
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCHEMA_VERSION = "1.1.0"
RUNS_DIR = Path(".ai") / "runs"
SCHEMA_PATH = Path("schema") / "state_schema.json"
SUBDIRS = (
    "plan",
    "plan/steps",
    "review",
    "tests",
    "impl",
    "verify",
    "repair",
    "logs",
)


def generate_run_id() -> str:
    return secrets.token_hex(8)


def now_iso8601_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_initial_state(run_id: str, request: str) -> dict:
    timestamp = now_iso8601_utc()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": "INTAKE",
        "created_at": timestamp,
        "updated_at": timestamp,
        "request": request,
        "approval_stage": None,
        "current_step": 0,
        "total_steps": 0,
        "revision_count": 0,
        "repair_attempts": {},
        "auth": {"gemini": "unknown", "codex": "unknown"},
        "budget": {
            "claude": {"used": "unknown", "max": None},
            "gemini": {"used": "unknown", "max": None},
            "codex": {"used": "unknown", "max": None},
        },
        "active_session_ids": {"codex": None},
        "artifacts": {
            "plan_draft": None,
            "arch_review": None,
            "contract": None,
            "plan_review": None,
            "testspec": None,
            "approved_plan": None,
        },
        "steps": [],
        "git_checkpoints": [],
    }


def cleanup_orphan_runs(runs_dir: Path = RUNS_DIR, logger=None) -> None:
    logger = logger or logging.getLogger(__name__)

    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        import tools.state_manager as state_manager
    except Exception:
        return
    finally:
        try:
            _sys.path.pop(0)
        except Exception:
            pass

    try:
        repo_root = runs_dir.parent.parent
        old_runs_dir = state_manager.RUNS_DIR
        old_schema_path = state_manager.SCHEMA_PATH
        state_manager.RUNS_DIR = runs_dir
        state_manager.SCHEMA_PATH = repo_root / "schema" / "state_schema.json"

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for run_dir in runs_dir.iterdir() if runs_dir.exists() else ():
            if not run_dir.is_dir():
                continue

            state_path = run_dir / "state.json"
            run_id = run_dir.name
            try:
                state = json.loads(state_path.read_text())
                run_id = state.get("run_id", run_id)
                status = state.get("status")
                if status == "STUCK":
                    continue
                if status != "INTAKE":
                    continue

                created_at_raw = state["created_at"]
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                if created_at >= cutoff:
                    continue

                state_manager.update_state(run_id, status="STUCK")
                state_manager.log_event(
                    run_id,
                    "ORPHAN_CLEANUP",
                    {
                        "run_id": run_id,
                        "from": "INTAKE",
                        "to": "STUCK",
                        "reason": "intake_run_older_than_24h",
                    },
                )
            except Exception as exc:
                try:
                    logger.warning("Failed orphan cleanup for run %s at %s: %s", run_id, state_path, exc)
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        try:
            state_manager.RUNS_DIR = old_runs_dir
            state_manager.SCHEMA_PATH = old_schema_path
        except Exception:
            pass


def validate_state(state: dict) -> None:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=state, schema=schema)


def create_run_directory() -> tuple[str, Path]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        run_id = generate_run_id()
        run_dir = RUNS_DIR / run_id
        try:
            run_dir.mkdir()
            return run_id, run_dir
        except FileExistsError:
            continue


def initialize_run(request: str, set_current: bool = True) -> str:
    import sys as _sys, os as _os
    _sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.state_manager import set_current as sm_set_current, log_event

    run_id, run_dir = create_run_directory()

    for subdir in SUBDIRS:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    state = build_initial_state(run_id, request)
    validate_state(state)

    (run_dir / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    (run_dir / "plan" / "request.md").write_text(request)

    # Write first event to events.jsonl
    log_event(run_id, "RUN_CREATED", {"request": request[:200]})

    # Set .ai/current symlink so tools default to this run
    if set_current:
        try:
            sm_set_current(run_id)
        except Exception:
            pass  # Non-fatal — run still created successfully

    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a new Vibe Commander run")
    parser.add_argument("request", help="Request text for the run")
    parser.add_argument("--no-set-current", action="store_true",
                        help="Do not update .ai/current symlink")
    args = parser.parse_args()

    try:
        cleanup_orphan_runs()
    except Exception:
        pass

    run_id = initialize_run(args.request, set_current=not args.no_set_current)
    print(run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
