#!/usr/bin/env python3
"""
gemini_planner.py — Gemini architecture advisor wrapper.

Uses Gemini CLI (OAuth) as primary. Falls back to Python SDK + API key.
READ-ONLY: Never outputs repo patches or code.
Output: JSON only to stdout. Artifacts written to .ai/runs/<run_id>/review/

Exit codes:
  0  — success or skipped (below threshold)
  30 — auth failure
  50 — fatal crash
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Per-task-type trigger configuration.
# Each entry defines keywords and file_threshold that cause Gemini to activate.
# Mirrors the TASK_CONFIG pattern in codex_worker.py — one source of truth per task context.
GEMINI_TRIGGER_CONFIG: dict[str, dict] = {
    # Plan-level review (vibe-feature, parallel step 6) — broadest keyword set
    "plan-review": {
        "keywords": ["api", "schema", "auth", "security", "migration", "database", "interface", "oauth"],
        "file_threshold": 5,
    },
    # Per-step pre-implement check (vibe-step, before codex_worker implement-step)
    # Narrower keywords: only high-risk implementation concerns
    "implement-step": {
        "keywords": ["auth", "security", "migration", "database", "schema", "oauth"],
        "file_threshold": 8,
    },
    # Final diff review (vibe-review, after full diff is generated)
    "final-review": {
        "keywords": ["api", "schema", "auth", "security", "migration", "database", "interface", "oauth"],
        "file_threshold": 10,
    },
    "project-scan": {
        "keywords": [],
        "file_threshold": 0,
    },
    "targeted-review": {
        "keywords": [],
        "file_threshold": 0,
    },
}

# Used when --task-type is not provided (backwards-compatible default)
_DEFAULT_TASK_TYPE = "plan-review"
LOGGER = logging.getLogger(__name__)
_gemini_cli_available = None


def should_trigger(
    plan_content: str,
    file_estimates: int = 0,
    force: bool = False,
    task_type: str = None,
) -> tuple[bool, str]:
    """Determine if Gemini review should be triggered. Returns (triggered, reason)."""
    if force:
        return True, "forced"
    cfg = GEMINI_TRIGGER_CONFIG.get(task_type or _DEFAULT_TASK_TYPE,
                                    GEMINI_TRIGGER_CONFIG[_DEFAULT_TASK_TYPE])
    if file_estimates > cfg["file_threshold"]:
        return True, f"file_impact={file_estimates} > threshold({cfg['file_threshold']})"
    content_lower = plan_content.lower()
    matched = [kw for kw in cfg["keywords"] if kw in content_lower]
    if matched:
        return True, f"keywords_matched={matched}"
    return False, "below_threshold"


GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or 'gemini-2.5-pro'  # Strongest Pro model — used by both CLI and SDK


def _normalize_model_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def resolve_model(task_name: Optional[str] = None, configured_model: Optional[str] = None) -> str:
    task_model = _normalize_model_value(configured_model)
    if task_model is not None:
        LOGGER.debug("Resolved Gemini model=%s source=%s task=%s", task_model, "task_config", task_name)
        return task_model

    env_model = _normalize_model_value(os.environ.get("GEMINI_MODEL"))
    if env_model is not None:
        LOGGER.debug("Resolved Gemini model=%s source=%s task=%s", env_model, "env", task_name)
        return env_model

    default_model = _normalize_model_value(GEMINI_MODEL) or "gemini-2.5-pro"
    LOGGER.debug("Resolved Gemini model=%s source=%s task=%s", default_model, "module_default", task_name)
    return default_model


def is_gemini_cli_available() -> bool:
    global _gemini_cli_available

    if _gemini_cli_available is not None:
        return _gemini_cli_available

    try:
        result = subprocess.run(
            ["gemini", "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except FileNotFoundError:
        _gemini_cli_available = False
        return False
    except subprocess.TimeoutExpired:
        return False

    if result.returncode == 0:
        _gemini_cli_available = True
        return True

    return False


def _reset_gemini_cli_cache() -> None:
    global _gemini_cli_available
    _gemini_cli_available = None


def run_gemini_cli(prompt: str) -> str:
    """
    Invoke Gemini CLI in non-interactive mode.
    Returns raw text output.
    """
    model_name = resolve_model()
    result = subprocess.run(
        ["gemini", "-m", model_name, "-p", prompt, "--output-format", "json", "--approval-mode", "plan"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gemini CLI exited {result.returncode}: {result.stderr[:300]}")
    return result.stdout.strip()


SDK_TIMEOUT = 120  # seconds for SDK calls; CLI already has timeout=120


def run_gemini_sdk(prompt: str, timeout: int = SDK_TIMEOUT) -> str:
    """Fallback: call Gemini via Python SDK + API key."""
    import concurrent.futures
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set and Gemini CLI unavailable.")
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("pip install google-generativeai  (Gemini CLI also not available)")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(resolve_model())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(model.generate_content, prompt)
        try:
            response = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(f"Gemini SDK call timed out after {timeout} seconds.")
    return response.text.strip()


def run_gemini_sdk_search(query: str, timeout: int = SDK_TIMEOUT) -> str:
    """
    Call Gemini via Python SDK with Google Search grounding.
    CLI does NOT support web search — this is SDK-only.
    Requires GEMINI_API_KEY in environment.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set — web-search requires the Python SDK "
            "(Gemini CLI does not support Google Search grounding)"
        )
    try:
        import google.generativeai as genai
        from google.generativeai.types import Tool
    except ImportError:
        raise RuntimeError("pip install google-generativeai")
    import concurrent.futures
    genai.configure(api_key=api_key)
    search_tool = Tool(google_search_retrieval={})
    model = genai.GenerativeModel(resolve_model(), tools=[search_tool])
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(model.generate_content, query)
        try:
            response = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(f"Gemini SDK search timed out after {timeout} seconds.")
    return response.text.strip()


def run_gemini(prompt: str, timeout: int = SDK_TIMEOUT) -> str:
    """Try Gemini CLI first, fall back to SDK."""
    if is_gemini_cli_available():
        return run_gemini_cli(prompt)

    try:
        return run_gemini_sdk(prompt, timeout=timeout)
    except FileNotFoundError:
        return run_gemini_sdk(prompt, timeout=timeout)
    except RuntimeError:
        raise


def parse_json_response(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    text = text.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"status": "ok", "summary": text[:300], "raw": True}


SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?'),
    re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?(\S{8,})["\']?'),
    re.compile(r'(?i)(secret[_-]?key|secret)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?'),
    re.compile(r'(?i)(token|access[_-]?token)\s*[=:]\s*["\']?([A-Za-z0-9_\.\-]{16,})["\']?'),
    re.compile(r'sk-[A-Za-z0-9]{32,}'),
    re.compile(r'ghp_[A-Za-z0-9]{36,}'),
    re.compile(r'AIza[A-Za-z0-9_\-]{35}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40})["\']?'),
    re.compile(r'sk_(live|test)_[A-Za-z0-9]{24,}'),
    re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'gho_[A-Za-z0-9]{36,}'),
    re.compile(r'ghs_[A-Za-z0-9]{36,}'),
    re.compile(r'xox[bpoas]-[A-Za-z0-9\-]{10,}'),
]

INCLUDE_EXTENSIONS = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".ts", ".js"}
EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".ai"}
EXCLUDE_SUFFIXES = {".lock", ".min.js", ".pyc", ".egg-info"}


def redact_secrets(content: str) -> tuple[str, int]:
    """Redact secret-like strings. Returns (redacted_content, redaction_count)."""
    count = 0
    for pattern in SECRET_PATTERNS:
        n_before = len(pattern.findall(content))
        if n_before:
            content = pattern.sub("[REDACTED]", content)
            count += n_before
    return content, count


def collect_repo_files(repo_root: str, max_kb: int) -> tuple[list[str], int, int]:
    """
    Walk repo_root, collect files matching INCLUDE_EXTENSIONS,
    excluding EXCLUDE_DIRS and EXCLUDE_SUFFIXES.
    Truncates at max_kb total size.
    Returns (relative_file_paths, total_bytes, truncated_count).
    """
    import pathlib

    root = pathlib.Path(repo_root).resolve()
    collected = []
    total_bytes = 0
    max_bytes = max_kb * 1024
    truncated = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError):
            continue
        parts = set(path.relative_to(root).parts[:-1])
        if parts & EXCLUDE_DIRS:
            continue
        name = path.name
        if any(name.endswith(s) for s in EXCLUDE_SUFFIXES):
            continue
        if path.suffix not in INCLUDE_EXTENSIONS:
            continue
        size = path.stat().st_size
        if total_bytes + size > max_bytes:
            truncated += 1
            break
        collected.append(str(path.relative_to(root)))
        total_bytes += size

    return collected, total_bytes, truncated


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
    from tools.plan_utils import validate_plan_structure

    derived_structure_score = 0
    if plan_text:
        validation = validate_plan_structure(plan_text)
        derived_structure_score = int(validation["score"] * 0.30)

    concerns = (result or {}).get("arch_concerns", [])
    high_count = sum(1 for concern in concerns if concern.get("severity") == "high")
    derived_severity_score = max(0, 30 - high_count * 15)
    derived_rollback_score = 20 if plan_text and "rollback" in plan_text.lower() and len(plan_text) > 100 else 0
    derived_test_score = 20 if plan_text and "test" in plan_text.lower() and len(plan_text) > 100 else 0

    return min(
        100,
        derived_structure_score + derived_severity_score + derived_rollback_score + derived_test_score,
    )


def main():
    parser = argparse.ArgumentParser(description="gemini_planner.py — Gemini advisor")
    parser.add_argument("action", choices=["arch-review", "api-contract", "check-trigger", "web-search", "project-scan", "targeted-review"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--concerns-file", help="JSON file with list of high-severity concerns for targeted-review")
    parser.add_argument("--file-estimates", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Force trigger regardless of threshold")
    parser.add_argument(
        "--mode",
        choices=["preflight", "scan"],
        default="scan",
        help="project-scan mode: preflight (estimate only) or scan (full Gemini call)",
    )
    parser.add_argument("--repo-root", default=".", help="Root directory to scan (default: current directory)")
    parser.add_argument("--max-kb", type=int, default=300, help="Max total KB to include in scan (default: 300)")
    parser.add_argument(
        "--task-type",
        choices=list(GEMINI_TRIGGER_CONFIG.keys()),
        default=None,
        help=f"Task context for trigger rules. Choices: {list(GEMINI_TRIGGER_CONFIG.keys())}. "
             f"Default: {_DEFAULT_TASK_TYPE}",
    )
    parser.add_argument("--plan-file", help="Original plan file for targeted-review context")
    parser.add_argument(
        "--timeout", type=int, default=SDK_TIMEOUT,
        help=f"Timeout in seconds for SDK calls (default {SDK_TIMEOUT}). CLI path uses its own 120s limit.",
    )
    args = parser.parse_args()

    run_dir = f".ai/runs/{args.run_id}/review"
    os.makedirs(run_dir, exist_ok=True)

    # Load input
    input_content = ""
    if args.input:
        if not os.path.exists(args.input):
            print(json.dumps({"status": "fatal_error", "summary": f"Input not found: {args.input}"}))
            sys.exit(50)
        with open(args.input) as f:
            input_content = f.read()

    # ── check-trigger ────────────────────────────────────────────────────────
    if args.action == "check-trigger":
        # LLM calls are forbidden here; this action only evaluates local trigger rules.
        triggered, reason = should_trigger(
            input_content, args.file_estimates, args.force, args.task_type
        )
        print(json.dumps({
            "status": "ok",
            "triggered": triggered,
            "reason": reason,
            "task_type": args.task_type or _DEFAULT_TASK_TYPE,
        }))
        return

    # Check trigger threshold for review actions only (not web-search, which runs unconditionally)
    # arch-review is always-on at plan stage per CLAUDE.md — no trigger gate.
    # Only api-contract and other conditional actions use the trigger threshold.
    if args.action in ("api-contract",):
        triggered, reason = should_trigger(
            input_content, args.file_estimates, args.force, args.task_type
        )
        if not triggered:
            print(json.dumps({
                "status": "skipped",
                "summary": f"Gemini review not triggered — {reason}",
            }))
            return

    # ── arch-review ──────────────────────────────────────────────────────────
    if args.action == "arch-review":
        prompt = f"""You are a senior software architect reviewing an implementation plan.

RULES:
- Do NOT suggest code implementations or patches
- Focus on: architecture structure, scalability, risks, missing considerations, security concerns
- Be concise and specific

Output ONLY valid JSON (no markdown fences) with these exact fields:
  status: "ok"
  summary: string (100-300 chars, key finding)
  arch_concerns: array of objects (each: concern, severity (low/medium/high), suggestion)
  risk_level: "low" | "medium" | "high"
  recommendation: "approve" | "revise" | "reject"
  details_md: string (full markdown analysis)

PLAN TO REVIEW:
{input_content}"""

        try:
            raw = run_gemini(prompt, timeout=args.timeout)
            result = parse_json_response(raw)
            input_content_for_score = input_content  # already loaded
            result["confidence_score"] = calculate_confidence_score(result, input_content_for_score)
        except RuntimeError as e:
            print(json.dumps({"status": "auth_blocked", "summary": str(e)}))
            sys.exit(30)
        except Exception as e:
            result = {"status": "retryable_error", "summary": str(e)[:200]}

        artifact = f"{run_dir}/arch_review.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps({**result, "artifact": artifact}))

    # ── api-contract ─────────────────────────────────────────────────────────
    elif args.action == "api-contract":
        prompt = f"""You are a senior software architect formalizing an API contract.

RULES:
- Do NOT suggest code implementations
- Extract and formalize all interfaces, inputs, outputs, and constraints

Output ONLY valid JSON (no markdown fences) with these exact fields:
  status: "ok"
  summary: string (100-300 chars)
  interfaces: array of objects (each: name, inputs, outputs, constraints, notes)
  contract_md: string (full markdown API contract document)

PLAN:
{input_content}"""

        try:
            raw = run_gemini(prompt, timeout=args.timeout)
            result = parse_json_response(raw)
        except RuntimeError as e:
            print(json.dumps({"status": "auth_blocked", "summary": str(e)}))
            sys.exit(30)
        except Exception as e:
            result = {"status": "retryable_error", "summary": str(e)[:200]}

        contract_md = result.get("contract_md", "")
        if contract_md:
            with open(f"{run_dir}/contract.md", "w") as f:
                f.write(contract_md)

        artifact = f"{run_dir}/contract.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps({**result, "artifact": artifact}))

    # ── web-search ────────────────────────────────────────────────────────────
    elif args.action == "web-search":
        # CLI does not support Google Search grounding — SDK-only path.
        if not input_content:
            print(json.dumps({"status": "fatal_error",
                               "summary": "web-search requires --input with the search query"}))
            sys.exit(50)
        try:
            raw = run_gemini_sdk_search(input_content, timeout=args.timeout)
            result = parse_json_response(raw)
        except RuntimeError as e:
            print(json.dumps({"status": "auth_blocked", "summary": str(e)}))
            sys.exit(30)
        except Exception as e:
            result = {"status": "retryable_error", "summary": str(e)[:200]}

        artifact = f"{run_dir}/web_search.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps({**result, "artifact": artifact}))

    # ── project-scan ──────────────────────────────────────────────────────────
    elif args.action == "project-scan":
        import pathlib

        repo_root = args.repo_root if hasattr(args, "repo_root") else "."
        max_kb = args.max_kb if hasattr(args, "max_kb") else 300
        preflight_mode = getattr(args, "mode", "scan") == "preflight"
        root_path = pathlib.Path(repo_root).resolve()

        file_list, total_bytes, truncated = collect_repo_files(repo_root, max_kb)

        total_redacted = 0
        for fp in file_list:
            try:
                abs_fp = (root_path / fp).resolve()
                try:
                    abs_fp.relative_to(root_path)
                except ValueError:
                    continue
                with open(abs_fp, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                _, n = redact_secrets(content)
                total_redacted += n
            except OSError:
                pass

        total_kb = round(total_bytes / 1024, 1)
        estimated_tokens = int(total_bytes / 4)
        warnings = []
        if truncated > 0:
            warnings.append(f"{truncated} files excluded due to --max-kb={max_kb} budget cap")
        if total_redacted > 0:
            warnings.append(f"{total_redacted} potential secret(s) detected and will be redacted in scan mode")

        if getattr(args, "mode", "scan") == "preflight":
            artifact = f"{run_dir}/scan_preflight.json"
            result = {
                "status": "ok",
                "total_kb": total_kb,
                "file_count": len(file_list),
                "estimated_tokens": estimated_tokens,
                "redacted_count": total_redacted,
                "file_list": [str(fp) for fp in file_list],
                "warnings": warnings,
                "artifact": artifact,
            }
            with open(artifact, "w") as f:
                json.dump(result, f, indent=2)
            print(json.dumps(result))
            return

        preflight_artifact = f"{run_dir}/scan_preflight.json"
        if not os.path.exists(preflight_artifact):
            print(json.dumps({
                "status": "error",
                "summary": "project-scan requires preflight to run first. Run with --mode preflight first.",
            }))
            sys.exit(1)

        file_contents = []
        for fp in file_list:
            try:
                abs_fp = (root_path / fp).resolve()
                try:
                    abs_fp.relative_to(root_path)
                except ValueError:
                    continue
                with open(abs_fp, encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                redacted, _ = redact_secrets(raw)
                file_contents.append(f"=== FILE: {fp} ===\n{redacted}\n")
            except OSError:
                pass

        combined = "\n".join(file_contents)
        prompt = f"""You are a senior software architect. Analyze the following codebase files and produce a comprehensive project documentation report.

Output ONLY valid JSON (no markdown fences) with these exact fields:
  status: "ok"
  summary: string (150-400 chars overview)
  architecture_md: string (full markdown architecture overview)
  agent_roles: array of objects (each: name, role, tools, forbidden)
  data_flows: array of objects (each: from, to, description, artifact)
  state_machine_md: string (markdown state machine documentation)
  risks: array of objects (each: area, severity (low/medium/high), description)

CODEBASE FILES ({len(file_list)} files, {total_kb}KB):
{combined}"""

        try:
            raw = run_gemini(prompt, timeout=args.timeout)
            result = parse_json_response(raw)
        except RuntimeError as e:
            print(json.dumps({"status": "auth_blocked", "summary": str(e)}))
            sys.exit(30)
        except Exception as e:
            result = {"status": "retryable_error", "summary": str(e)[:200]}

        arch_md = result.get("architecture_md", "")
        if arch_md:
            with open(f"{run_dir}/project_scan_report.md", "w") as f:
                f.write(arch_md)

        artifact = f"{run_dir}/project_scan_report.json"
        result["artifact"] = artifact
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result))

    elif args.action == "targeted-review":
        concerns_list = []
        if args.concerns_file and os.path.exists(args.concerns_file):
            with open(args.concerns_file) as f:
                concerns_payload = json.load(f)
            if isinstance(concerns_payload, dict):
                concerns_list = concerns_payload.get("arch_concerns", [])
            else:
                concerns_list = concerns_payload

        plan_text = ""
        if args.plan_file and os.path.exists(args.plan_file):
            with open(args.plan_file) as f:
                plan_text = f.read()

        def _extract_targeted_context(text: str) -> str:
            sections = [
                "Goal", "Motivation", "Affected Files", "Risk Areas",
                "Rollback Strategy", "Open Questions", "Out of Scope", "Test Coverage Plan",
            ]
            chunks = []
            for section in sections:
                match = re.search(
                    rf"(^##\s+{re.escape(section)}\s*$.*?)(?=^##\s+|\Z)",
                    text,
                    re.MULTILINE | re.DOTALL | re.IGNORECASE,
                )
                if match:
                    chunks.append(match.group(1).strip())
            return "\n\n".join(chunks)[:3000]

        rollback_match = re.search(r'##\s+Rollback[^\n]*\n(.*?)(?=\n##|\Z)', plan_text, re.DOTALL | re.IGNORECASE)
        rollback_section = rollback_match.group(1).strip() if rollback_match else "(not specified)"
        focused_plan_text = _extract_targeted_context(plan_text)

        def _format_concern(c):
            if isinstance(c, dict):
                severity = c.get("severity", "?").upper()
                concern = c.get("concern", str(c))
                suggestion = c.get("suggestion", "")
                return f"- [{severity}] {concern}: {suggestion}"
            return f"- {c}"

        concerns_text = "\n".join(_format_concern(c) for c in concerns_list)

        prompt = f"""You are a senior software architect doing a TARGETED review.
Focus ONLY on these flagged high-severity concerns — do not re-review the whole plan.

FLAGGED CONCERNS TO RESOLVE:
{concerns_text}

ROLLBACK STRATEGY:
{rollback_section}

RELEVANT PLAN CONTEXT:
{focused_plan_text}

Output ONLY valid JSON with these exact fields:
  status: "ok"
  confidence_score: integer 0-100 (how confident you are the concerns are resolved)
  resolved_concerns: array of strings (concern descriptions now resolved)
  remaining_concerns: array of objects (each: concern, severity, suggestion)
  recommendation: "approve" | "revise"
  summary: string (100-200 chars)"""

        try:
            raw = run_gemini(prompt, timeout=args.timeout)
            result = parse_json_response(raw)
            if "confidence_score" not in result:
                result["confidence_score"] = calculate_confidence_score(result, focused_plan_text)
        except RuntimeError as e:
            print(json.dumps({"status": "auth_blocked", "summary": str(e)}))
            sys.exit(30)
        except Exception as e:
            result = {"status": "retryable_error", "summary": str(e)[:200]}

        artifact = f"{run_dir}/targeted_review.json"
        with open(artifact, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps({**result, "artifact": artifact}))


if __name__ == "__main__":
    main()
