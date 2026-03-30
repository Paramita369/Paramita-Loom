#!/usr/bin/env python3
"""
bootstrap_google.py — First-time setup guide for Google / Gemini credentials.

Usage:
  python3 tools/auth/bootstrap_google.py
"""

import os
import sys


def main():
    print("=== Google / Gemini Authentication Setup ===\n")

    print("Option 1: API Key  (Recommended — simplest)")
    print("  1. Go to: https://makersuite.google.com/app/apikey")
    print("  2. Create a new API key")
    print("  3. Add to your shell profile:")
    print("       export GEMINI_API_KEY='your-key-here'")
    print("  4. Reload shell: source ~/.zshrc (or ~/.bashrc)\n")

    print("Option 2: Application Default Credentials (ADC)")
    print("  1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install")
    print("  2. Run: gcloud auth application-default login")
    print("  3. Set project: gcloud config set project YOUR_PROJECT_ID\n")

    # Check current state
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"✓ GEMINI_API_KEY is set ({api_key[:8]}...)")
        print("  Run auth doctor to verify: python3 tools/auth/auth_doctor.py")
        sys.exit(0)

    try:
        import google.auth
        credentials, project = google.auth.default()
        print(f"✓ ADC credentials found (project: {project})")
        sys.exit(0)
    except Exception:
        pass

    print("✗ No credentials found. Follow Option 1 or Option 2 above.")
    sys.exit(1)


if __name__ == "__main__":
    main()
