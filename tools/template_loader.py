"""Template loader for AI code generation standards.

Loads code standards templates with a priority cascade:
  1. Project override: .ai/code_standards.md
  2. Language-specific: templates/{language}_standards.md
  3. Global: templates/code_standards.md
  4. Fallback: empty string (no standards)

Templates are cached after first load to avoid repeated I/O.
"""

import os
import re
from functools import lru_cache
from pathlib import Path

__all__ = ["load_standards", "detect_language", "clear_cache"]

# Maximum characters for injected standards (roughly ~1000 tokens)
MAX_STANDARDS_CHARS = int(os.environ.get("VIBE_MAX_STANDARDS_CHARS", "4000"))

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PROJECT_OVERRIDE = Path(".ai") / "code_standards.md"


def detect_language(content: str) -> str:
    """Detect programming language from step/plan content.

    Uses simple heuristics as a fallback. Prefer passing --language explicitly.

    Args:
        content: Text content from a plan step or file listing.

    Returns:
        One of: "python", "typescript", "generic".
    """
    if not content:
        return "generic"

    text = content.lower()

    # Python signals
    py_signals = [".py", "import ", "def ", "class ", "pytest", "python", "__init__"]
    py_score = sum(1 for s in py_signals if s in text)

    # TypeScript/JavaScript signals
    ts_signals = [".ts", ".tsx", ".js", ".jsx", "export ", "interface ", "const ", "typescript", "npm", "react"]
    ts_score = sum(1 for s in ts_signals if s in text)

    if py_score > ts_score and py_score >= 2:
        return "python"
    if ts_score > py_score and ts_score >= 2:
        return "typescript"
    return "generic"


@lru_cache(maxsize=8)
def _load_file(path: str) -> str:
    """Read a file and return its content. Cached by absolute path string."""
    p = Path(path)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8")
    return ""


def load_standards(language: str = "python", project_override: str = None) -> str:
    """Load code standards template with priority cascade.

    Priority:
        1. project_override path (if provided and exists)
        2. .ai/code_standards.md (project-level override)
        3. templates/{language}_standards.md (language-specific)
        4. templates/code_standards.md (global)
        5. "" (empty — no standards)

    If language-specific exists, it is APPENDED to global (not replacing).

    Args:
        language: Target language ("python", "typescript", "generic").
        project_override: Optional explicit path to override file.

    Returns:
        Standards text, truncated to MAX_STANDARDS_CHARS if needed.
    """
    # 1. Explicit override path
    if project_override:
        override = _load_file(str(Path(project_override).resolve()))
        if override:
            return _truncate(override)

    # 2. Project-level override (.ai/code_standards.md)
    proj = _load_file(str(PROJECT_OVERRIDE.resolve()))
    if proj:
        return _truncate(proj)

    # 3. Global + language-specific (combined)
    global_path = TEMPLATES_DIR / "code_standards.md"
    lang_path = TEMPLATES_DIR / f"{language}_standards.md"

    global_standards = _load_file(str(global_path.resolve()))
    lang_standards = _load_file(str(lang_path.resolve()))

    if global_standards and lang_standards:
        combined = global_standards.rstrip() + "\n\n---\n\n" + lang_standards
        return _truncate(combined)
    if global_standards:
        return _truncate(global_standards)
    if lang_standards:
        return _truncate(lang_standards)

    # 4. Nothing found
    return ""


def _truncate(text: str) -> str:
    """Truncate text to MAX_STANDARDS_CHARS, cutting at last section boundary."""
    if len(text) <= MAX_STANDARDS_CHARS:
        return text

    # Try to cut at a section boundary (## heading)
    truncated = text[:MAX_STANDARDS_CHARS]
    last_section = truncated.rfind("\n## ")
    if last_section > len(truncated) // 2:
        return truncated[:last_section].rstrip() + "\n\n[... truncated for context limit]"
    return truncated.rstrip() + "\n\n[... truncated for context limit]"


def clear_cache() -> None:
    """Clear the template file cache. Useful for testing."""
    _load_file.cache_clear()
