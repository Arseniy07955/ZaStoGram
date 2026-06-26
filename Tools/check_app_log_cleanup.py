#!/usr/bin/env python3
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
FILE_LOG = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/FileLog.java"
APPLICATION_LOADER = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def extract_method(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        return ""
    brace = text.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return ""


def main() -> int:
    failures: list[str] = []
    file_log = read(FILE_LOG)
    application_loader = read(APPLICATION_LOADER)

    on_create = extract_method(application_loader, "public void onCreate()")
    cleanup_logs = extract_method(file_log, "public static void cleanupLogs()")

    require(cleanup_logs, "FileLog.cleanupLogs() must exist", failures)
    require(on_create, "ApplicationLoader.onCreate() must exist", failures)
    require(
        "FileLog.cleanupLogs();" in on_create,
        "ApplicationLoader.onCreate() must clear app log files on every process start",
        failures,
    )
    if "FileLog.cleanupLogs();" in on_create and 'FileLog.d("app start time' in on_create:
        require(
            on_create.index("FileLog.cleanupLogs();") < on_create.index('FileLog.d("app start time'),
            "app log cleanup must happen before the first FileLog.d() creates fresh session files",
            failures,
        )
    require(
        "ensureInitied();" not in cleanup_logs,
        "cleanupLogs() must not initialize FileLog before deleting stale files",
        failures,
    )
    require(
        re.search(r"\bFileLog\s+instance\s*=\s*Instance\s*;", cleanup_logs) is not None,
        "cleanupLogs() must use the existing FileLog instance without creating one",
        failures,
    )
    require(
        "tlRequestsFile" in cleanup_logs,
        "cleanupLogs() must preserve the current MTProto request log when called after init",
        failures,
    )
    require(
        "!file.isFile()" in cleanup_logs,
        "cleanupLogs() must delete only regular log files and leave subdirectories alone",
        failures,
    )

    if failures:
        print("app log cleanup guard failed:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print("app log cleanup guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
