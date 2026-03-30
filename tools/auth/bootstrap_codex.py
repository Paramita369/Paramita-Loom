#!/usr/bin/env python3
"""
bootstrap_codex.py — First-time setup guide for OpenAI Codex CLI.

Usage:
  python3 tools/auth/bootstrap_codex.py
"""

import os
import subprocess
import sys


def check(label: str, cmd: list) -> str | None:
    """Run a command and return stdout, or None on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def main():
    print("=== OpenAI Codex CLI Setup ===\n")
    all_ok = True

    # Node.js
    node = check("node", ["node", "--version"])
    if node:
        print(f"✓ Node.js: {node}")
    else:
        print("✗ Node.js not found")
        print("  Install from: https://nodejs.org")
        all_ok = False

    # npm
    npm = check("npm", ["npm", "--version"])
    if npm:
        print(f"✓ npm: {npm}")
    else:
        print("✗ npm not found (usually bundled with Node.js)")
        all_ok = False

    # Codex CLI
    codex = check("codex", ["codex", "--version"])
    if codex:
        print(f"✓ Codex CLI: {codex}")
    else:
        print("✗ Codex CLI not found")
        print("  Install: npm install -g @openai/codex")
        all_ok = False

    # OPENAI_API_KEY
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print(f"✓ OPENAI_API_KEY is set ({api_key[:8]}...)")
    else:
        print("✗ OPENAI_API_KEY not set")
        print("  1. Get key from: https://platform.openai.com/api-keys")
        print("  2. Add to shell: export OPENAI_API_KEY='your-key-here'")
        print("  3. Reload shell: source ~/.zshrc (or ~/.bashrc)")
        all_ok = False

    print()
    if all_ok:
        print("All checks passed! Codex CLI is ready.")
        print("Run auth doctor: python3 tools/auth/auth_doctor.py")
        sys.exit(0)
    else:
        print("Fix the issues above, then re-run this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
