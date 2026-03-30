#!/usr/bin/env python3
"""
codex_worker.py — The ONLY component allowed to write to the repo.

All repo changes must go through this script → Codex CLI.
Output: JSON only to stdout. Artifacts written to .ai/runs/<run_id>/

Usage:
  python3 tools/codex_worker.py <action> --run-id <id> --input <file> [options]

Actions:
  review-plan       Codex reviews the plan (read-only)
  draft-testspec    Codex drafts a test specification (read-only)
  write-tests       Codex writes test files (WRITES to repo)
  implement-step    Codex implements a step (WRITES to repo)
  review-code       Codex reviews a diff (read-only)
  repair-step       Codex repairs a failing step (WRITES to repo)
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from typing import Optional

ACTIONS = [
    "review-plan",
    "draft-testspec",
    "write-tests",
    "implement-step",
    "review-code",
    "repair-step",
]


LOGGER = logging.getLogger(__name__)

RUN_ID_PATTERN = re.compile(r'^[0-9a-f]{8,32}$')

MODEL = os.environ.get('CODEX_MODEL') or 'gpt-5.4'  # Single model for all tasks — overrides ~/.codex/config.toml

# Per-task config.
# NOTE: reasoning_effort is kept as *intent documentation* but is NOT passed to the
# Codex CLI (the installed version does not support --reasoning-effort).
# When a future CLI version adds this flag, re-enable it in run_codex().
TASK_CONFIG: dict[str, dict] = {
    "review-plan":    {"model": "gpt-5.4-mini"},
    "repair-step":    {"model": "gpt-5.4"},
    "implement-step": {"model": "gpt-5.4"},
    "draft-testspec": {"model": "gpt-5.4-mini"},
    "review-code":    {"model": "gpt-5.4-mini"},
    "write-tests":    {"model": "gpt-5.4"},
}


def _normalize_model_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def validate_run_id(run_id: str) -> str:
    """Validate run_id is a hex string. Raises ValueError if invalid."""
    if not run_id or not RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"Invalid run_id format: {run_id!r}. Must be 8-32 hex chars.")
    return run_id


def resolve_model(task_name: str) -> str:
    if os.getenv("CODEX_DISABLE_MODEL_TIERING", "").lower() == "true":
        LOGGER.debug("Resolved Codex model=%s source=%s task=%s", MODEL, "disable_model_tiering", task_name)
        return MODEL

    task_cfg = TASK_CONFIG.get(task_name, {})
    task_model = _normalize_model_value(task_cfg.get("model"))
    if task_model is not None:
        LOGGER.debug("Resolved Codex model=%s source=%s task=%s", task_model, "task_config", task_name)
        return task_model

    env_model = _normalize_model_value(os.environ.get("CODEX_MODEL"))
    if env_model is not None:
        LOGGER.debug("Resolved Codex model=%s source=%s task=%s", env_model, "env", task_name)
        return env_model

    default_model = _normalize_model_value(MODEL) or "gpt-5.4"
    LOGGER.debug("Resolved Codex model=%s source=%s task=%s", default_model, "module_default", task_name)
    return default_model


def call_validate_plan_structure(plan_text: str) -> dict:
    """Import plan_utils and validate plan structure. Returns validation result dict."""
    try:
        from tools.plan_utils import validate_plan_structure
        return validate_plan_structure(plan_text)
    except Exception as e:
        return {"valid": False, "missing_sections": [], "empty_sections": [], "score": 50, "error": str(e)}


def calculate_confidence_score(
    result: dict = None,
    plan_text: str = "",
    *,
    structure_score: int = None,
    severity_penalty: int = None,
    rollback_score: int = None,
    test_plan_score: int = None,
) -> int:
    """Public scorer supporting both computed and component-based calls."""
    if structure_score is not None:
        total = (
            max(0, structure_score)
            + max(0, severity_penalty or 0)
            + max(0, rollback_score or 0)
            + max(0, test_plan_score or 0)
        )
        return min(100, total)
    validation = call_validate_plan_structure(plan_text)
    derived_structure_score = int(validation.get("score", 50) * 0.30)
    issues = (result or {}).get("issues", [])
    high_count = sum(1 for i in issues if i.get("severity") == "high")
    derived_severity_score = max(0, 30 - high_count * 15)
    derived_rollback_score = 20 if plan_text and "rollback" in plan_text.lower() else 0
    derived_test_score = 20 if plan_text and "test" in plan_text.lower() else 0
    return min(100, derived_structure_score + derived_severity_score + derived_rollback_score + derived_test_score)


def run_codex_parallel(tasks: list[dict]) -> list[dict]:
    """
    Run multiple read-only Codex calls in parallel (subagent pattern).
    Each task dict: {
        "prompt": str,
        "write": bool,   # must be False for all parallel tasks (R4)
        "key": str,
        "model": str,    # optional — overrides default MODEL
    }
    Returns list of {"key": str, "result": dict} in original order.

    Use for independent read-only operations only (R4: no parallel writes).
    Example: run review-plan + gemini check-trigger simultaneously.
    """
    import concurrent.futures

    def _run_one(task):
        return {
            "key": task["key"],
            "result": run_codex(
                task["prompt"],
                write=task.get("write", False),
                model=task.get("model"),
            ),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [executor.submit(_run_one, t) for t in tasks]
        return [f.result() for f in concurrent.futures.as_completed(futures)]


DEFAULT_TIMEOUT = 300  # seconds; override via --timeout CLI flag


def resolve_timeout(run_id: str, cli_timeout: Optional[int]) -> int:
    if cli_timeout is not None:
        return cli_timeout

    try:
        from tools import state_manager

        state = state_manager.load_state(run_id)
        configured = (state.get("config") or {}).get("codex_timeout")
        if configured is None:
            return DEFAULT_TIMEOUT
        return int(configured)
    except Exception:
        return DEFAULT_TIMEOUT


def run_codex(
    prompt: str,
    write: bool = False,
    session_id: str = None,
    model: str = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    Invoke codex exec and return result dict.

    write=False   → -s read-only   (plan review, testspec, code review)
    write=True    → --full-auto    (write-tests, implement, repair)
    session_id    → resumes via `codex exec resume <id>`
    model         → override default MODEL via -m flag
    timeout       → seconds before the subprocess is killed (default 300)
    """
    import tempfile

    effective_model = model or MODEL

    # Write last message to a temp file so we can parse it reliably
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        output_file = tmp.name

    if session_id:
        cmd = ["codex", "exec", "resume", session_id,
               "-m", effective_model, "-o", output_file]
        if write:
            cmd += ["--full-auto"]
        else:
            cmd += ["-s", "read-only"]
        if prompt.strip():
            cmd.append(prompt.strip())
        stdin_input = None
    else:
        cmd = ["codex", "exec", "-m", effective_model, "-o", output_file]
        if write:
            cmd += ["--full-auto"]
        else:
            cmd += ["-s", "read-only"]
        stdin_input = prompt

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=stdin_input, timeout=timeout)
        returncode = proc.returncode
    except FileNotFoundError:
        return {
            "status": "fatal_error",
            "summary": "codex CLI not found. Run: npm install -g @openai/codex",
            "exit_code": 127,
        }
    except subprocess.TimeoutExpired:
        # Kill the entire process group to avoid orphaned child processes
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), __import__("signal").SIGTERM)
            except Exception:
                proc.kill()
            proc.wait()
        return {
            "status": "retryable_error",
            "summary": f"Codex execution timed out after {timeout} seconds.",
            "timeout": timeout,
        }

    if returncode != 0:
        # Read output file anyway — may have partial result
        pass

    # Read the last-message output file
    last_message = ""
    try:
        with open(output_file) as f:
            last_message = f.read().strip()
        os.unlink(output_file)
    except Exception:
        pass

    if not last_message:
        return {
            "status": "retryable_error" if returncode != 0 else "ok",
            "summary": stderr[:300] or "Codex returned no output.",
            "exit_code": returncode,
        }

    # Try to parse as JSON (when we requested JSON output in prompt)
    try:
        return json.loads(last_message)
    except json.JSONDecodeError:
        return {
            "status": "ok",
            "summary": last_message[:300],
            "details_md": last_message,
            "raw": True,
        }


def get_run_dir(run_id: str, subdir: str) -> str:
    validate_run_id(run_id)
    path = f".ai/runs/{run_id}/{subdir}"
    os.makedirs(path, exist_ok=True)
    return path


def git_checkpoint(run_id: str, step: str):
    """Create a git checkpoint commit before writing to the repo."""
    validate_run_id(run_id)
    safe_step = re.sub(r'[^a-zA-Z0-9_\-.]', '_', step)
    msg = f"checkpoint: before implement {safe_step} run {run_id}"
    subprocess.run(["git", "add", "-A"], capture_output=True, timeout=30)
    subprocess.run(
        ["git", "commit", "-m", msg, "--allow-empty"],
        capture_output=True,
        timeout=30,
    )


def git_diff_since_checkpoint() -> str:
    """Get diff since the last checkpoint commit."""
    result = subprocess.run(
        ["git", "diff", "HEAD~1"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def output(data: dict):
    print(json.dumps(data, indent=2))


def load_input(path: str) -> str:
    if not path:
        return ""
    if not os.path.exists(path):
        print(json.dumps({"status": "fatal_error", "summary": f"Input file not found: {path}"}))
        sys.exit(50)
    with open(path) as f:
        return f.read()


def ensure_repo_root_on_sys_path():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def main():
    ensure_repo_root_on_sys_path()
    from tools import state_manager

    parser = argparse.ArgumentParser(description="codex_worker.py — Codex CLI bridge")
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--run-id", required=True, help="Run ID (from state.json)")
    parser.add_argument("--input", help="Path to input file")
    parser.add_argument("--step", default="s1", help="Step identifier (e.g. s1, s2)")
    parser.add_argument("--session-id", help="Codex session ID for --resume")
    parser.add_argument("--timeout", type=int, default=None,
                        help=f"Subprocess timeout in seconds (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--language", default=None,
                        help="Target language for code standards (python, typescript, generic)")
    args = parser.parse_args()
    timeout = resolve_timeout(args.run_id, args.timeout)

    input_content = load_input(args.input)
    # Load code standards for prompt injection
    from tools.template_loader import load_standards, detect_language
    language = args.language or detect_language(input_content)
    standards_block = load_standards(language=language)
    standards_prefix = ""
    if standards_block:
        standards_prefix = f"## Code Standards (MUST follow)\n{standards_block}\n\n---\n\n"

    # ── review-plan ──────────────────────────────────────────────────────────
    if args.action == "review-plan":
        run_dir = get_run_dir(args.run_id, "plan")
        prompt = (
            f"{standards_prefix}"
            "Review this implementation plan. Output JSON with fields:\n"
            "  status (ok|retryable_error|fatal_error)\n"
            "  summary (100-300 chars)\n"
            "  issues[] (each: severity, description, suggestion)\n"
            "  overall_recommendation (approve|revise|reject)\n\n"
            f"PLAN:\n{input_content}"
        )
        result = run_codex(prompt, write=False,
                           model=resolve_model(args.action), timeout=timeout)
        plan_text = ""
        if args.input and os.path.exists(args.input):
            with open(args.input) as f:
                plan_text = f.read()

        validation = call_validate_plan_structure(plan_text)
        missing = validation.get("missing_sections", [])
        result["confidence_score"] = calculate_confidence_score(result, plan_text)

        if missing:
            warning_prefix = "Warning: plan is missing required sections: " + ", ".join(missing) + ". "
            result["summary"] = warning_prefix + result.get("summary", "")
            result["details_md"] = warning_prefix + result.get("details_md", "")
            result["plan_structure_warnings"] = [f"Missing section: {s}" for s in missing]
        artifact = f"{run_dir}/plan_review.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        output({**result, "artifact": artifact})

    # ── draft-testspec ───────────────────────────────────────────────────────
    elif args.action == "draft-testspec":
        run_dir = get_run_dir(args.run_id, "tests")
        prompt = (
            f"{standards_prefix}"
            "Draft a test specification for this plan. Output JSON with fields:\n"
            "  status, summary\n"
            "  testspec_md (full markdown test spec)\n"
            "  test_cases[] (each: id, description, type, acceptance_criteria)\n\n"
            f"PLAN:\n{input_content}"
        )
        result = run_codex(prompt, write=False,
                           model=resolve_model(args.action), timeout=timeout)
        testspec_md = result.get("testspec_md", "")
        if testspec_md:
            with open(f"{run_dir}/testspec.md", "w") as f:
                f.write(testspec_md)
        artifact = f"{run_dir}/testspec_draft.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        output({**result, "artifact": artifact})

    # ── write-tests ──────────────────────────────────────────────────────────
    elif args.action == "write-tests":
        run_dir = get_run_dir(args.run_id, "tests")
        prompt = (
            f"{standards_prefix}"
            "Write the actual test files based on this test specification.\n"
            "Create the files in the workspace. Follow existing project conventions.\n\n"
            f"TEST SPEC:\n{input_content}"
        )
        result = run_codex(prompt, write=True,
                           model=resolve_model(args.action), timeout=timeout)
        artifact = f"{run_dir}/tests_result.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        output({**result, "artifact": artifact})

    # ── implement-step ───────────────────────────────────────────────────────
    elif args.action == "implement-step":
        run_dir = get_run_dir(args.run_id, "impl")
        # Create git checkpoint before any writes
        git_checkpoint(args.run_id, args.step)
        prompt = (
            f"{standards_prefix}"
            "Implement this step. Make minimal changes to satisfy the requirements.\n"
            "Do not add features beyond what is specified.\n\n"
            f"STEP:\n{input_content}"
        )
        result = run_codex(prompt, write=True, session_id=args.session_id,
                           model=resolve_model(args.action), timeout=timeout)
        diff = git_diff_since_checkpoint()
        diff_file = f"{run_dir}/{args.step}_diff.patch"
        with open(diff_file, "w") as f:
            f.write(diff)
        result["diff_file"] = diff_file
        if result.get("status") == "ok":
            result["session_id"] = result.get("session_id") or args.session_id
            if result.get("session_id"):
                state_manager.update_session_id(args.run_id, "codex", result["session_id"])
        artifact = f"{run_dir}/impl_result.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        output({**result, "artifact": artifact})

    # ── review-code ──────────────────────────────────────────────────────────
    elif args.action == "review-code":
        run_dir = get_run_dir(args.run_id, "impl")
        prompt = (
            f"{standards_prefix}"
            "Review this code diff. Output JSON with fields:\n"
            "  status, summary\n"
            "  issues[] (each: severity, file, line, rule, fix)\n"
            "  overall_verdict (approve|request_changes)\n\n"
            f"DIFF:\n{input_content}"
        )
        result = run_codex(prompt, write=False,
                           model=resolve_model(args.action), timeout=timeout)
        artifact = f"{run_dir}/{args.step}_code_review.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        output({**result, "artifact": artifact})

    # ── repair-step ──────────────────────────────────────────────────────────
    elif args.action == "repair-step":
        run_dir = get_run_dir(args.run_id, "repair")
        git_checkpoint(args.run_id, f"{args.step}_repair")
        prompt = (
            f"{standards_prefix}"
            "Fix the issues identified in this verification report.\n"
            "Make minimal targeted changes only. Do not refactor unrelated code.\n\n"
            f"VERIFICATION REPORT:\n{input_content}"
        )
        result = run_codex(prompt, write=True, session_id=args.session_id,
                           model=resolve_model(args.action), timeout=timeout)
        diff = git_diff_since_checkpoint()
        diff_file = f"{run_dir}/{args.step}_repair_diff.patch"
        with open(diff_file, "w") as f:
            f.write(diff)
        result["diff_file"] = diff_file
        if result.get("status") == "ok":
            result["session_id"] = result.get("session_id") or args.session_id
            if result.get("session_id"):
                state_manager.update_session_id(args.run_id, "codex", result["session_id"])
        artifact = f"{run_dir}/repair_result.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        output({**result, "artifact": artifact})


if __name__ == "__main__":
    main()
