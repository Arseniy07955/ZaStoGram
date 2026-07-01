#!/usr/bin/env python3
"""Static guard for exteraGram-facing client_utils compatibility exports."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT_UTILS = ROOT / "TMessagesProj/src/main/python/client_utils.py"


def fail(errors: list[str]) -> int:
    print("Plugin client_utils contract check failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def has_dynamic_proxy_base(cls: ast.ClassDef, interface: str) -> bool:
    for base in cls.bases:
        if not isinstance(base, ast.Call):
            continue
        if call_name(base.func) != "dynamic_proxy":
            continue
        if base.args and call_name(base.args[0]) == interface:
            return True
    return False


def main() -> int:
    try:
        source = CLIENT_UTILS.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fail([f"Missing {CLIENT_UTILS.relative_to(ROOT)}"])

    tree = ast.parse(source, filename=str(CLIENT_UTILS))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    errors: list[str] = []

    request_callback = classes.get("RequestCallback")
    if request_callback is None:
        errors.append("client_utils must export RequestCallback for exteraGram plugins")
    else:
        if not has_dynamic_proxy_base(request_callback, "RequestDelegate"):
            errors.append("RequestCallback must proxy org.telegram.tgnet.RequestDelegate")
        if not any(isinstance(node, ast.FunctionDef) and node.name == "run"
                   for node in request_callback.body):
            errors.append("RequestCallback must implement run(response, error)")

    if "RequestCallback(on_complete)" not in source:
        errors.append("send_request must wrap Python callbacks with RequestCallback")

    if errors:
        return fail(errors)

    print("Plugin client_utils contract check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
