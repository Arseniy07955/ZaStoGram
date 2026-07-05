#!/usr/bin/env python3
"""Static guard for exteraGram-facing android_utils compatibility exports."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANDROID_UTILS = ROOT / "TMessagesProj/src/main/python/android_utils.py"


def fail(errors: list[str]) -> int:
    print("Plugin android_utils contract check failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def call_name(node: ast.AST | None) -> str | None:
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


def assigned_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def main() -> int:
    try:
        source = ANDROID_UTILS.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fail([f"Missing {ANDROID_UTILS.relative_to(ROOT)}"])

    tree = ast.parse(source, filename=str(ANDROID_UTILS))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    names = assigned_names(tree)
    errors: list[str] = []

    if 'Runnable = jclass("java.lang.Runnable")' not in source:
        errors.append("android_utils must resolve java.lang.Runnable through jclass for dynamic_proxy")

    runnable = classes.get("_Runnable")
    if runnable is None:
        errors.append("android_utils must keep _Runnable proxy wrapper")
    elif not has_dynamic_proxy_base(runnable, "Runnable"):
        errors.append("_Runnable must proxy java.lang.Runnable")

    if "R" not in names or "R = _Runnable" not in source:
        errors.append("android_utils must export R = _Runnable for exteraGram plugins")

    run_on_ui_thread = functions.get("run_on_ui_thread")
    if run_on_ui_thread is None:
        errors.append("android_utils must export run_on_ui_thread")
    else:
        args = [arg.arg for arg in run_on_ui_thread.args.args]
        if args[:2] != ["fn", "delay"]:
            errors.append("run_on_ui_thread signature must accept fn, delay")

    for listener in ("OnClickListener", "OnLongClickListener"):
        if listener not in classes:
            errors.append(f"android_utils must export {listener}")

    if errors:
        return fail(errors)

    print("Plugin android_utils contract check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
