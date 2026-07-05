#!/usr/bin/env python3
"""Guard structured plugin settings used by exteraGram-compatible plugins."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PLUGIN = ROOT / "TMessagesProj/src/main/python/base_plugin.py"


class FakeContext:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.reloads = 0

    def getSetting(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def setSetting(self, key: str, value: object) -> None:
        self.values[key] = value

    def reloadSettings(self) -> None:
        self.reloads += 1


def fail(errors: list[str]) -> int:
    print("Plugin structured settings check failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def load_base_plugin():
    spec = importlib.util.spec_from_file_location("base_plugin_under_test", BASE_PLUGIN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BASE_PLUGIN.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BasePlugin


def main() -> int:
    BasePlugin = load_base_plugin()
    plugin = BasePlugin()
    context = FakeContext()
    plugin._context = context

    errors: list[str] = []
    default_data = {"manual": [], "subs": [], "active_uri": ""}

    missing = plugin.get_setting("vless_data", default_data)
    if not isinstance(missing, dict):
        errors.append("dict defaults must round-trip as dicts when the setting is missing")
    elif missing != default_data:
        errors.append("dict defaults must keep their original contents")

    data = {
        "manual": [{"name": "primary", "uri": "vless://user@example.com:443?type=tcp#Main"}],
        "subs": [],
        "active_uri": "vless://user@example.com:443?type=tcp#Main",
    }
    plugin.set_setting("vless_data", data, reload_settings=True)
    stored = context.values.get("vless_data")
    if not isinstance(stored, str):
        errors.append("structured settings must be serialized before entering SharedPreferences")
    elif "vless://user@example.com:443" not in stored:
        errors.append("serialized structured settings must preserve nested values")
    if context.reloads != 1:
        errors.append("set_setting(..., reload_settings=True) must still request a UI reload")

    restored = plugin.get_setting("vless_data", default_data)
    if restored != data:
        errors.append("JSON-serialized dict settings must deserialize back to dicts")

    context.values["vless_data"] = (
        "{'manual': [{'name': 'legacy', 'uri': 'vless://legacy@example.com:443'}], "
        "'subs': [], 'active_uri': ''}"
    )
    legacy = plugin.get_setting("vless_data", default_data)
    if not isinstance(legacy, dict) or legacy.get("manual", [{}])[0].get("name") != "legacy":
        errors.append("legacy Python-repr dict settings must be migrated instead of returning a string")

    plugin.set_setting("nodes", ["a", {"b": 2}])
    restored_list = plugin.get_setting("nodes", [])
    if restored_list != ["a", {"b": 2}]:
        errors.append("list settings must serialize and deserialize like dict settings")

    if errors:
        return fail(errors)

    print("Plugin structured settings check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
