#!/usr/bin/env python3
"""Static guard: opening ContactsActivity must not auto-request contacts permission."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTACTS_ACTIVITY = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ContactsActivity.java"


def extract_method_body(java: str, signature: str) -> str:
    start = java.find(signature)
    if start < 0:
        return ""
    brace_start = java.find("{", start)
    if brace_start < 0:
        raise ValueError(f"missing method body for: {signature}")

    depth = 0
    for index in range(brace_start, len(java)):
        char = java[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return java[brace_start + 1:index]

    raise ValueError(f"unterminated method body for: {signature}")


def main() -> int:
    java = CONTACTS_ACTIVITY.read_text(encoding="utf-8")
    errors: list[str] = []

    try:
        body = extract_method_body(java, "public void onBecomeFullyVisible()")
    except ValueError as exc:
        print(f"contacts permission prompt check failed: {exc}")
        return 1

    banned_tokens = {
        "createContactsPermissionDialog": "must not show the contacts permission explainer when contacts open",
        "askForPermissons(": "must not auto-request contacts permission when contacts open",
        "Manifest.permission.READ_CONTACTS": "must not check READ_CONTACTS from the open-contact lifecycle hook",
        "requestPermissions(": "must not invoke the Android permission prompt from the open-contact lifecycle hook",
    }
    for token, message in banned_tokens.items():
        if token in body:
            errors.append(message)

    if errors:
        print("contacts permission prompt check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("contacts permission prompt check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
