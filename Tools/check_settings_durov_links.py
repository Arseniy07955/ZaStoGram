#!/usr/bin/env python3
"""Static guard for the custom help links in Settings."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_ACTIVITY = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java"
STRINGS = ROOT / "TMessagesProj/src/main/res/values/strings.xml"


EXPECTED_STRINGS = {
    "DurovLalka": "TelegaNew info",
    "OurChannel": "Наш канал",
    "OurVpn": "Наш VPN",
}

EXPECTED_LINKS = {
    24: ("OurChannel", "settings_channel", "https://t.me/senkapopkavpn"),
    25: ("OurVpn", "settings_privacy", "https://t.me/SenkapopkaVpnBot"),
}


def main() -> int:
    java = SETTINGS_ACTIVITY.read_text(encoding="utf-8")
    strings = STRINGS.read_text(encoding="utf-8")
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    for name, value in EXPECTED_STRINGS.items():
        require(
            f'<string name="{name}">{value}</string>' in strings,
            f"Missing string resource {name}={value}",
        )

    require(
        "items.add(UItem.asHeader(getString(R.string.DurovLalka)))" in java,
        "Settings help section must include the custom DurovLalka header",
    )

    for item_id, (string_name, icon_name, url) in EXPECTED_LINKS.items():
        require(
            re.search(
                rf"SettingCell\.Factory\.of\({item_id},[^;]+R\.drawable\.{icon_name},\s*getString\(R\.string\.{string_name}\)\)",
                java,
                re.DOTALL,
            )
            is not None,
            f"Settings item {item_id} must use {string_name} with {icon_name}",
        )
        require(
            re.search(
                rf"case {item_id}:\s+Browser\.openUrl\(getParentActivity\(\), \"{re.escape(url)}\"\);\s+break;",
                java,
                re.DOTALL,
            )
            is not None,
            f"Settings item {item_id} must open {url}",
        )

    require(
        "https://t.me/zapretvpns_bot" not in java,
        "Zapret VPNs sponsor link must live in the chat list, not Settings",
    )

    if errors:
        print("Settings Durov links check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Settings Durov links check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
