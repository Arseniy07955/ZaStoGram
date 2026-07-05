"""Basic text formatting helpers for exteraGram-compatible plugins."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html.parser import HTMLParser
import re


class TLEntityType(Enum):
    CODE = "code"
    PRE = "pre"
    STRIKETHROUGH = "strikethrough"
    TEXT_LINK = "text_link"
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    SPOILER = "spoiler"
    CUSTOM_EMOJI = "custom_emoji"
    BLOCKQUOTE = "blockquote"


@dataclass
class RawEntity:
    type: TLEntityType
    offset: int
    length: int
    url: str | None = None
    language: str | None = None
    document_id: int | None = None
    collapsed: bool = False

    def to_tl_entity(self):
        from org.telegram.tgnet import TLRPC

        factories = {
            TLEntityType.CODE: TLRPC.TL_messageEntityCode,
            TLEntityType.PRE: TLRPC.TL_messageEntityPre,
            TLEntityType.STRIKETHROUGH: TLRPC.TL_messageEntityStrike,
            TLEntityType.TEXT_LINK: TLRPC.TL_messageEntityTextUrl,
            TLEntityType.BOLD: TLRPC.TL_messageEntityBold,
            TLEntityType.ITALIC: TLRPC.TL_messageEntityItalic,
            TLEntityType.UNDERLINE: TLRPC.TL_messageEntityUnderline,
            TLEntityType.SPOILER: TLRPC.TL_messageEntitySpoiler,
            TLEntityType.CUSTOM_EMOJI: TLRPC.TL_messageEntityCustomEmoji,
            TLEntityType.BLOCKQUOTE: TLRPC.TL_messageEntityBlockquote,
        }
        entity = factories[self.type]()
        entity.offset = int(self.offset)
        entity.length = int(self.length)
        if self.type is TLEntityType.TEXT_LINK:
            entity.url = self.url or ""
        elif self.type is TLEntityType.PRE:
            entity.language = self.language or ""
        elif self.type is TLEntityType.CUSTOM_EMOJI:
            entity.document_id = int(self.document_id or 0)
        elif self.type is TLEntityType.BLOCKQUOTE:
            entity.collapsed = bool(self.collapsed)
        return entity


def _utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _entity_length(start: int, end: int) -> int:
    return max(0, end - start)


class _HtmlEntityParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.entities: list[RawEntity] = []
        self.stack: list[tuple[str, TLEntityType, int, dict[str, object]]] = []

    @property
    def current_offset(self) -> int:
        return _utf16_len("".join(self.parts))

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs}
        tag = tag.lower()
        if tag == "br":
            self.parts.append("\n")
            return

        mapping = {
            "b": TLEntityType.BOLD,
            "strong": TLEntityType.BOLD,
            "i": TLEntityType.ITALIC,
            "em": TLEntityType.ITALIC,
            "u": TLEntityType.UNDERLINE,
            "s": TLEntityType.STRIKETHROUGH,
            "del": TLEntityType.STRIKETHROUGH,
            "strike": TLEntityType.STRIKETHROUGH,
            "code": TLEntityType.CODE,
            "pre": TLEntityType.PRE,
            "spoiler": TLEntityType.SPOILER,
            "tg-spoiler": TLEntityType.SPOILER,
            "blockquote": TLEntityType.BLOCKQUOTE,
            "a": TLEntityType.TEXT_LINK,
            "emoji": TLEntityType.CUSTOM_EMOJI,
        }
        entity_type = mapping.get(tag)
        if entity_type is None:
            return

        meta: dict[str, object] = {}
        if entity_type is TLEntityType.TEXT_LINK:
            href = attrs_dict.get("href")
            if not href:
                return
            meta["url"] = href
        elif entity_type is TLEntityType.PRE:
            language = attrs_dict.get("language") or ""
            class_name = attrs_dict.get("class") or ""
            if not language and isinstance(class_name, str):
                match = re.search(r"(?:^|\s)language-([A-Za-z0-9_+-]+)", class_name)
                if match:
                    language = match.group(1)
            meta["language"] = language
        elif entity_type is TLEntityType.CUSTOM_EMOJI:
            document_id = attrs_dict.get("id") or attrs_dict.get("document_id")
            if not document_id:
                return
            meta["document_id"] = int(document_id)
        elif entity_type is TLEntityType.BLOCKQUOTE:
            meta["collapsed"] = "collapsed" in attrs_dict or "expandable" in attrs_dict

        self.stack.append((tag, entity_type, self.current_offset, meta))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            start_tag, entity_type, start, meta = self.stack[index]
            if start_tag != tag:
                continue
            del self.stack[index]
            end = self.current_offset
            length = _entity_length(start, end)
            if length <= 0:
                return
            self.entities.append(RawEntity(
                entity_type,
                start,
                length,
                url=meta.get("url"),
                language=meta.get("language"),
                document_id=meta.get("document_id"),
                collapsed=bool(meta.get("collapsed", False)),
            ))
            return


def _add_entity(entities: list[RawEntity], entity_type: TLEntityType, start: int, end: int, **kwargs) -> None:
    length = _entity_length(start, end)
    if length > 0:
        entities.append(RawEntity(entity_type, start, length, **kwargs))


def _parse_inline_markdown(text: str) -> tuple[str, list[RawEntity]]:
    out: list[str] = []
    entities: list[RawEntity] = []
    index = 0

    def offset() -> int:
        return _utf16_len("".join(out))

    def append_plain(value: str) -> None:
        out.append(value)

    def append_parsed(value: str) -> tuple[int, int]:
        start = offset()
        inner_text, inner_entities = _parse_inline_markdown(value)
        append_plain(inner_text)
        for entity in inner_entities:
            entity.offset += start
            entities.append(entity)
        return start, offset()

    while index < len(text):
        if text.startswith("```", index):
            close = text.find("```", index + 3)
            if close >= 0:
                block = text[index + 3:close]
                language = ""
                if "\n" in block:
                    first, rest = block.split("\n", 1)
                    if re.fullmatch(r"[A-Za-z0-9_+-]+", first.strip()):
                        language = first.strip()
                        block = rest
                start = offset()
                append_plain(block)
                _add_entity(entities, TLEntityType.PRE, start, offset(), language=language)
                index = close + 3
                continue

        emoji_match = re.match(r"!\[([^\]]*)\]\(tg://emoji\?id=(\d+)\)", text[index:])
        if emoji_match:
            label, document_id = emoji_match.groups()
            start = offset()
            append_plain(label)
            _add_entity(entities, TLEntityType.CUSTOM_EMOJI, start, offset(), document_id=int(document_id))
            index += emoji_match.end()
            continue

        link_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", text[index:])
        if link_match:
            label, url = link_match.groups()
            start, end = append_parsed(label)
            _add_entity(entities, TLEntityType.TEXT_LINK, start, end, url=url)
            index += link_match.end()
            continue

        matched = False
        for marker, entity_type in (
            ("**", TLEntityType.BOLD),
            ("__", TLEntityType.UNDERLINE),
            ("||", TLEntityType.SPOILER),
            ("`", TLEntityType.CODE),
            ("*", TLEntityType.BOLD),
            ("_", TLEntityType.ITALIC),
            ("~", TLEntityType.STRIKETHROUGH),
        ):
            if not text.startswith(marker, index):
                continue
            close = text.find(marker, index + len(marker))
            if close < 0:
                continue
            start, end = append_parsed(text[index + len(marker):close])
            _add_entity(entities, entity_type, start, end)
            index = close + len(marker)
            matched = True
            break
        if matched:
            continue

        append_plain(text[index])
        index += 1

    return "".join(out), entities


def _parse_markdown(text: str) -> tuple[str, list[RawEntity]]:
    out: list[str] = []
    entities: list[RawEntity] = []

    def offset() -> int:
        return _utf16_len("".join(out))

    for line in text.splitlines(True):
        collapsed = False
        quote = False
        if line.startswith("**> "):
            quote = True
            collapsed = True
            line = line[4:]
        elif line.startswith("> "):
            quote = True
            line = line[2:]

        start = offset()
        parsed, line_entities = _parse_inline_markdown(line)
        out.append(parsed)
        for entity in line_entities:
            entity.offset += start
            entities.append(entity)
        if quote:
            _add_entity(entities, TLEntityType.BLOCKQUOTE, start, offset(), collapsed=collapsed)

    return "".join(out), entities


def _parse_html(text: str) -> tuple[str, list[RawEntity]]:
    parser = _HtmlEntityParser()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts), parser.entities


def parse_text(text: str, parse_mode: str | None = "HTML", is_caption: bool = False) -> dict[str, object]:
    if text is None:
        text = ""
    text = str(text)
    key = "caption" if is_caption else "message"

    if parse_mode is None:
        return {key: text, "entities": []}

    mode = str(parse_mode).strip().lower()
    if mode in ("html", "htm"):
        parsed, raw_entities = _parse_html(text)
    elif mode in ("markdown", "md"):
        parsed, raw_entities = _parse_markdown(text)
    else:
        raise ValueError("unsupported parse_mode: %s" % parse_mode)

    return {
        key: parsed,
        "entities": [entity.to_tl_entity() for entity in raw_entities],
    }
