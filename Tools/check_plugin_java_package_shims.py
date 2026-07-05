#!/usr/bin/env python3
"""Guard Python shim packages for plugins importing com.exteragram Java classes."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PY_ROOT = ROOT / "TMessagesProj/src/main/python"

REQUIRED_FILES = {
    "com/__init__.py": [],
    "com/exteragram/__init__.py": [],
    "com/exteragram/messenger/__init__.py": [],
    "com/exteragram/messenger/plugins/__init__.py": [
        'Plugin = jclass("com.exteragram.messenger.plugins.Plugin")',
        'PluginsController = jclass("com.exteragram.messenger.plugins.PluginsController")',
    ],
    "com/exteragram/messenger/plugins/ui/__init__.py": [
        'PluginSettingsActivity = jclass("com.exteragram.messenger.plugins.ui.PluginSettingsActivity")',
    ],
}


def main() -> int:
    errors: list[str] = []
    for relative, literals in REQUIRED_FILES.items():
        path = PY_ROOT / relative
        if not path.exists():
            errors.append(f"Missing Python package shim: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for literal in literals:
            if literal not in text:
                errors.append(f"{path.relative_to(ROOT)} must contain {literal}")

    if errors:
        print("Plugin Java package shim guard failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Plugin Java package shim guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
