#!/usr/bin/env python3
"""Static guard for exteraGram text_formatting compatibility."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_FORMATTING = ROOT / "TMessagesProj/src/main/python/extera_utils/text_formatting.py"

ENTITY_TYPES = {
    "CODE",
    "PRE",
    "STRIKETHROUGH",
    "TEXT_LINK",
    "BOLD",
    "ITALIC",
    "UNDERLINE",
    "SPOILER",
    "CUSTOM_EMOJI",
    "BLOCKQUOTE",
}

TL_CLASSES = {
    "TL_messageEntityCode",
    "TL_messageEntityPre",
    "TL_messageEntityStrike",
    "TL_messageEntityTextUrl",
    "TL_messageEntityBold",
    "TL_messageEntityItalic",
    "TL_messageEntityUnderline",
    "TL_messageEntitySpoiler",
    "TL_messageEntityCustomEmoji",
    "TL_messageEntityBlockquote",
}


def fail(errors: list[str]) -> int:
    print("Plugin text_formatting contract check failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def class_bases(cls: ast.ClassDef) -> set[str]:
    bases: set[str] = set()
    for base in cls.bases:
        if isinstance(base, ast.Name):
            bases.add(base.id)
        elif isinstance(base, ast.Attribute):
            bases.add(base.attr)
    return bases


def main() -> int:
    try:
        source = TEXT_FORMATTING.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fail([f"Missing {TEXT_FORMATTING.relative_to(ROOT)}"])

    tree = ast.parse(source, filename=str(TEXT_FORMATTING))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    errors: list[str] = []

    entity_type = classes.get("TLEntityType")
    if entity_type is None:
        errors.append("text_formatting must export TLEntityType")
    else:
        if "Enum" not in class_bases(entity_type):
            errors.append("TLEntityType must be an Enum")
        members = {
            target.id
            for node in entity_type.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for member in sorted(ENTITY_TYPES - members):
            errors.append(f"TLEntityType is missing {member}")

    raw_entity = classes.get("RawEntity")
    if raw_entity is None:
        errors.append("text_formatting must export RawEntity")
    else:
        if "@dataclass" not in source:
            errors.append("RawEntity must be a dataclass")
        if not any(isinstance(node, ast.FunctionDef) and node.name == "to_tl_entity"
                   for node in raw_entity.body):
            errors.append("RawEntity must convert itself to a TLRPC.MessageEntity")

    if "parse_text" not in functions:
        errors.append("text_formatting must export parse_text")
    else:
        args = [arg.arg for arg in functions["parse_text"].args.args]
        if args[:3] != ["text", "parse_mode", "is_caption"]:
            errors.append("parse_text signature must start with text, parse_mode, is_caption")

    for literal in TL_CLASSES:
        if literal not in source:
            errors.append(f"text_formatting must construct TLRPC.{literal}")

    for literal in ("HTMLParser", "_parse_markdown", "_utf16_len"):
        if literal not in source:
            errors.append(f"text_formatting must include {literal}")

    if not errors:
        spec = importlib.util.spec_from_file_location("_zasto_text_formatting", TEXT_FORMATTING)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        if module._utf16_len("x\U0001f600") != 3:
            errors.append("_utf16_len must count non-BMP characters as two UTF-16 code units")

        html_text, html_entities = module._parse_html('<b>Hi</b> <a href="https://e.test">link</a>')
        if html_text != "Hi link":
            errors.append("_parse_html must strip supported tags while preserving text")
        html_types = {entity.type.name for entity in html_entities}
        if {"BOLD", "TEXT_LINK"} - html_types:
            errors.append("_parse_html must produce BOLD and TEXT_LINK raw entities")

        md_text, md_entities = module._parse_markdown('**Hi** [link](https://e.test)')
        if md_text != "Hi link":
            errors.append("_parse_markdown must strip basic Markdown markers while preserving text")
        md_types = {entity.type.name for entity in md_entities}
        if {"BOLD", "TEXT_LINK"} - md_types:
            errors.append("_parse_markdown must produce BOLD and TEXT_LINK raw entities")

    if errors:
        return fail(errors)

    print("Plugin text_formatting contract check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
