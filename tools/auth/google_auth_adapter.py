#!/usr/bin/env python3
"""
Google / Gemini authentication adapter.
Supports Gemini CLI OAuth (primary), GEMINI_API_KEY, and ADC.
"""

import os
import subprocess
from typing import Optional


def _check_gemini_cli() -> Optional[dict]:
    """Check if Gemini CLI is installed and responsive."""
    which = subprocess.run(["which", "gemini"], capture_output=True, text=True)
    if which.returncode != 0:
        return None
    version_result = subprocess.run(
        ["gemini", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if version_result.returncode == 0:
        return {"type": "gemini_cli_oauth", "version": version_result.stdout.strip()}
    return None


def check_health() -> dict:
    """Check if Gemini auth is working. Returns health report dict."""
    # 1. Gemini CLI OAuth (preferred — user's actual setup)
    cli = _check_gemini_cli()
    if cli:
        return {
            "status": "ok",
            "provider": "google",
            "auth_type": cli["type"],
            "version": cli["version"],
        }

    # 2. API key fallback
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return {
            "status": "ok",
            "provider": "google",
            "auth_type": "api_key",
        }

    # 3. ADC fallback
    try:
        import google.auth
        _, project = google.auth.default()
        return {
            "status": "ok",
            "provider": "google",
            "auth_type": "adc",
            "project": project,
        }
    except Exception:
        pass

    return {
        "status": "blocked",
        "error": "No Gemini auth found. gemini CLI not installed, no GEMINI_API_KEY, no ADC.",
        "provider": "google",
        "fix": "Install Gemini CLI: npm install -g @google/generative-ai-cli  OR  set GEMINI_API_KEY",
    }
