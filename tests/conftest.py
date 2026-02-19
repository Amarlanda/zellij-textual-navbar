"""Pytest configuration for navbar E2E tests."""

from __future__ import annotations

import os
import sys


def pytest_configure(config):
    """Print visual mode status."""
    headless = os.environ.get("ATT_HEADLESS", "1") != "0"
    if not headless:
        sys.stderr.write(
            "\n\033[1;36m"
            "  ╔═══════════════════════════════════════════════╗\n"
            "  ║  🖱️  VISIBLE MODE — watch the tests run!       ║\n"
            "  ║  Cursor moves, buttons click, tabs switch     ║\n"
            "  ╚═══════════════════════════════════════════════╝"
            "\033[0m\n\n"
        )
        sys.stderr.flush()
