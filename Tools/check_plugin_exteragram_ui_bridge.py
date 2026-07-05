#!/usr/bin/env python3
"""Static guard for exteraGram plugin-settings UI bridge compatibility."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "TMessagesProj/src/main/java/com/exteragram/messenger/plugins/PluginsController.java"
UI_BRIDGE = ROOT / "TMessagesProj/src/main/java/com/exteragram/messenger/plugins/ui/PluginSettingsActivity.java"


def fail(errors: list[str]) -> int:
    print("Plugin exteraGram UI bridge check failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def main() -> int:
    errors: list[str] = []

    try:
        controller = CONTROLLER.read_text(encoding="utf-8")
    except FileNotFoundError:
        controller = ""
        errors.append(f"Missing {CONTROLLER.relative_to(ROOT)}")

    if "openPluginSettings(String id)" not in controller:
        errors.append("PluginsController bridge must expose openPluginSettings(String id)")
    if "openPluginSettings(String id, BaseFragment from)" not in controller:
        errors.append("PluginsController bridge must expose openPluginSettings(String id, BaseFragment from)")
    if "com.exteragram.messenger.plugins.ui.PluginSettingsActivity" not in controller:
        errors.append("PluginsController bridge must present the exteraGram-compatible UI bridge")

    try:
        ui_bridge = UI_BRIDGE.read_text(encoding="utf-8")
    except FileNotFoundError:
        ui_bridge = ""
        errors.append(f"Missing {UI_BRIDGE.relative_to(ROOT)}")

    if "package com.exteragram.messenger.plugins.ui;" not in ui_bridge:
        errors.append("UI bridge must live in com.exteragram.messenger.plugins.ui")
    if "extends org.telegram.ui.Plugins.PluginSettingsActivity" not in ui_bridge:
        errors.append("UI bridge must extend ZaStoGram's PluginSettingsActivity")
    if "PluginSettingsActivity(Plugin plugin)" not in ui_bridge:
        errors.append("UI bridge must accept exteraGram Plugin objects")
    if "createView(Context context)" not in ui_bridge:
        errors.append("UI bridge must declare createView so plugin getDeclaredMethods() hooks can see it")

    if errors:
        return fail(errors)

    print("Plugin exteraGram UI bridge check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
