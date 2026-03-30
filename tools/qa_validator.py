import os, re, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LESSONS_FILE = Path(".ai/lessons_learned.md")
MAX_ENTRIES = 50
COMPACT_TO = 25

SANITIZE_PATTERNS = [
    (re.compile(r"\b[\w./\\-]+\.(py|json|md|toml|yaml|yml|ts|js)\b"), "<file>"),
    (re.compile(r"\[REDACTED\]"), "<redacted>"),
    (re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*[=:]\s*\S+"), r"\1=<secret>"),
]


def _sanitize(text: str) -> str:
    for pattern, replacement in SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _count_entries(content: str) -> int:
    return content.count("\n## Run ")


def _compact(content: str) -> str:
    """Keep only the most recent COMPACT_TO entries."""
    parts = re.split(r"(?=\n## Run )", content)
    header = parts[0] if not parts[0].startswith("\n## Run") else ""
    entries = [p for p in parts if p.strip().startswith("## Run")]
    kept = entries[-COMPACT_TO:]
    compacted_count = len(entries) - len(kept)
    summary = f"\n## [Compacted: {compacted_count} older entries removed on {datetime.now(timezone.utc).date()}]\n"
    return header + summary + "".join(kept)


def append_lessons(
    run_id: str = "",
    summary: str = "",
    root_cause: str = "",
    prevention: str = "",
    tags: Optional[list] = None,
    lesson: Optional[str] = None,
    lessons_path: Optional[Path] = None,
) -> None:
    target = lessons_path or LESSONS_FILE
    if lesson is not None and not summary:
        summary = lesson
    tags = tags or []
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text() if target.exists() else "# Vibe Commander — Lessons Learned\n"
    if _count_entries(existing) >= MAX_ENTRIES:
        existing = _compact(existing)
    tag_str = " ".join(f"[{t}]" for t in tags)
    entry = (
        f"\n## Run {run_id or 'manual'} — {datetime.now(timezone.utc).date()}\n"
        f"**Tags**: {tag_str}\n"
        f"**What went wrong**: {_sanitize(summary)}\n"
        f"**Root cause**: {_sanitize(root_cause)}\n"
        f"**Prevention**: {_sanitize(prevention)}\n"
    )
    target.write_text(existing + entry)


def read_relevant_lessons(tags: list, max_entries: int = 10, lessons_path: Optional[Path] = None) -> str:
    target = lessons_path or LESSONS_FILE
    if not target.exists():
        return ""
    content = target.read_text()
    blocks = re.split(r"(?=\n## Run )", content)
    matched = []
    all_entries = []
    for block in blocks:
        if not block.strip().startswith("## Run"):
            continue
        all_entries.append(block.strip())
        if any(f"[{t}]" in block for t in tags):
            matched.append(block.strip())
    selected = matched if matched else all_entries
    return "\n\n".join(reversed(selected[-max_entries:]))


def compress_verify_reports(run_id: str) -> dict:
    """
    Compress verify report context for runs with many reports.
    Keeps the three most recent reports intact and summarizes older ones while
    preserving each report's status and errors fields.
    """
    verify_dir = Path(".ai") / "runs" / run_id / "verify"
    report_paths = sorted(verify_dir.glob("*_verify_report.json"))
    if len(report_paths) <= 3:
        return {
            "compressed": False,
            "report_count": len(report_paths),
            "reports": [str(path) for path in report_paths],
        }

    older_reports = []
    for path in report_paths[:-3]:
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            payload = {"status": "invalid_json", "errors": [f"Could not parse {path.name}"]}

        older_reports.append({
            "report": path.name,
            "status": payload.get("status"),
            "errors": payload.get("errors", []),
            "summary": payload.get("summary", ""),
        })

    recent_reports = []
    for path in report_paths[-3:]:
        try:
            recent_reports.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            recent_reports.append({
                "status": "invalid_json",
                "errors": [f"Could not parse {path.name}"],
                "summary": "",
            })

    compressed_payload = {
        "compressed": True,
        "report_count": len(report_paths),
        "compressed_reports": older_reports,
        "recent_reports": recent_reports,
    }
    output_path = verify_dir / "compressed_verify_reports.json"
    output_path.write_text(json.dumps(compressed_payload, indent=2) + "\n")
    compressed_payload["artifact"] = str(output_path)
    return compressed_payload
