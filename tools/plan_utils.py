#!/usr/bin/env python3

import re


REQUIRED_SECTIONS = [
    "Goal", "Motivation", "Affected Files", "Risk Areas",
    "Rollback Strategy", "Open Questions", "Out of Scope", "Test Coverage Plan"
]

PLAN_TEMPLATE = {
    "Goal": "<what this change achieves>",
    "Motivation": "<why now>",
    "Affected Files": "<list files and scope>",
    "Risk Areas": "<security / data loss / breaking change / performance>",
    "Rollback Strategy": "<concrete rollback steps>",
    "Open Questions": "<unknowns / assumptions>",
    "Out of Scope": "<explicitly excluded>",
    "Test Coverage Plan": "<specific test points>",
}

PLAN_TEMPLATE_MD = "\n\n".join(f"## {k}\n{v}" for k, v in PLAN_TEMPLATE.items())


def validate_plan_structure(plan_text: str) -> dict:
    """
    Check plan has all required sections with substantive content.
    Returns: {valid: bool, missing_sections: list, empty_sections: list, score: int (0-100)}
    """
    missing = []
    empty = []
    for section in REQUIRED_SECTIONS:
        # Find section header (## Section or # Section)
        pattern = re.compile(
            rf"^#{{1,3}}\s+{re.escape(section)}\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        match = pattern.search(plan_text)
        if not match:
            missing.append(section)
            continue
        # Extract content after header until next header
        start = match.end()
        next_header = re.search(r"^#{1,3}\s+\w", plan_text[start:], re.MULTILINE)
        content = plan_text[start:start + next_header.start()] if next_header else plan_text[start:]
        content = content.strip()
        if len(content) < 20:
            empty.append(section)

    total = len(REQUIRED_SECTIONS)
    present = total - len(missing)
    non_empty = present - len(empty)
    score = int((non_empty / total) * 100)
    valid = len(missing) == 0 and len(empty) == 0

    return {"valid": valid, "missing_sections": missing, "empty_sections": empty, "score": score}
