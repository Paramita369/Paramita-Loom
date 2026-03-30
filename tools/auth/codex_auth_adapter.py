#!/usr/bin/env python3
"""
OpenAI Codex CLI authentication adapter.
Supports OAuth login (via codex login) and OPENAI_API_KEY.
Does NOT manage OAuth refresh — uses provider-native auth only.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional


def _get_oauth_status() -> Optional[dict]:
    """Read ~/.codex/auth.json to check OAuth login status."""
    auth_file = Path.home() / ".codex" / "auth.json"
    if not auth_file.exists():
        return None
    try:
        data = json.loads(auth_file.read_text())
        auth_mode = data.get("auth_mode", "unknown")
        # Has tokens = OAuth session active
        if data.get("tokens"):
            return {"type": f"oauth/{auth_mode}", "auth_mode": auth_mode}
        # Has API key stored in auth.json
        if data.get("OPENAI_API_KEY"):
            return {"type": "api_key_stored"}
    except Exception:
        pass
    return None


def check_health() -> dict:
    """Check if Codex CLI is installed and authenticated."""
    # 1. Check codex binary
    which = subprocess.run(["which", "codex"], capture_output=True, text=True)
    if which.returncode != 0:
        return {
            "status": "blocked",
            "error": "codex CLI not found",
            "provider": "codex",
            "fix": "Run: npm install -g @openai/codex",
        }

    # 2. Get version
    version_result = subprocess.run(
        ["codex", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    version = version_result.stdout.strip() if version_result.returncode == 0 else "unknown"

    # 3. Check OAuth login first (preferred), then fall back to env API key
    oauth = _get_oauth_status()
    if oauth:
        return {
            "status": "ok",
            "provider": "codex",
            "version": version,
            "auth_type": oauth["type"],
        }

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return {
            "status": "ok",
            "provider": "codex",
            "version": version,
            "auth_type": "env_api_key",
        }

    return {
        "status": "blocked",
        "error": "No auth found. Run `codex login` or set OPENAI_API_KEY.",
        "provider": "codex",
        "version": version,
        "fix": "Run: codex login",
    }
