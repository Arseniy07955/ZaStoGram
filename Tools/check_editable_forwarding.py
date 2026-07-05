#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/EditableForwardDraft.java"
PREVIEW_PARAMS = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/MessagePreviewParams.java"
PREVIEW_VIEW = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/Components/MessagePreviewView.java"
CHAT_ACTIVITY = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java"
SEND_HELPER = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java"
STRINGS = ROOT / "TMessagesProj/src/main/res/values/strings.xml"
STRINGS_RU = ROOT / "TMessagesProj/src/main/res/values-ru/strings.xml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    draft = read(DRAFT)
    params = read(PREVIEW_PARAMS)
    view = read(PREVIEW_VIEW)
    chat = read(CHAT_ACTIVITY)
    helper = read(SEND_HELPER)
    strings = read(STRINGS)
    strings_ru = read(STRINGS_RU)

    for token in (
        "public class EditableForwardDraft",
        "enum GroupingMode",
        "ALBUM",
        "SEPARATE_POSTS",
        "public static class Item",
        "setCaption(",
        "setGroupingMode(",
        "buildPreviewMessages(",
        "getSelectedItems()",
        "canCopy(",
    ):
        require(token in draft, f"EditableForwardDraft must contain {token}", failures)

    require("EditableForwardDraft editableForwardDraft" in params, "MessagePreviewParams must own the editable draft", failures)
    require("enableEditableForwarding(" in params, "MessagePreviewParams must enable editable forwarding", failures)
    require("disableEditableForwarding(" in params, "MessagePreviewParams must disable editable forwarding", failures)
    require("rebuildForwardPreviewFromDraft(" in params, "MessagePreviewParams must rebuild forward previews from the draft", failures)
    require("editableForwardDraft.buildPreviewMessages" in params, "Preview rebuild must use draft-built messages", failures)

    require("EditableForwardMode" in view, "MessagePreviewView must expose editable mode UI", failures)
    require("EditableForwardSeparatePosts" in view, "MessagePreviewView must expose separate-posts grouping UI", failures)
    require("showEditableForwardCaptionEditor(" in view, "MessagePreviewView must edit per-item captions", failures)
    require("messagePreviewParams.editEditableForwardCaption" in view, "Caption editor must write through MessagePreviewParams", failures)
    require("setGroupingMode(EditableForwardDraft.GroupingMode.SEPARATE_POSTS" in view, "Separate-posts button must set draft grouping", failures)
    require("setGroupingMode(EditableForwardDraft.GroupingMode.ALBUM" in view, "Album button must set draft grouping", failures)

    require("EditableForwardDraft editableForwardDraft" in chat, "ChatActivity forward boundary must accept the draft", failures)
    require("sendEditableForwardDraft(" in chat, "ChatActivity must call the dedicated editable send path", failures)
    require("messagePreviewParams.getEditableForwardDraftForSend()" in chat, "ChatActivity must consume draft from MessagePreviewParams", failures)

    require("int sendEditableForwardDraft(" in helper, "SendMessagesHelper must expose dedicated editable-copy sending", failures)
    require("EditableForwardDraft.Item" in helper, "SendMessagesHelper must send draft items", failures)
    require('params.put("groupId"' in helper, "Editable album sending must pass groupId through SendMessageParams", failures)
    require('params.put("final", "1")' in helper, "Editable album sending must mark final grouped item", failures)
    method_start = helper.find("int sendEditableForwardDraft(")
    method_window = helper[method_start:method_start + 4000] if method_start >= 0 else ""
    require("processForwardFromMyName(" not in method_window, "Editable path must not fall back to server-forward helper inside the dedicated method", failures)

    for name in (
        "EditableForwardMode",
        "EditableForwardAlbum",
        "EditableForwardSeparatePosts",
        "EditableForwardEditCaption",
        "EditableForwardCaptionHint",
        "EditableForwardUnsupported",
    ):
        require(f'name="{name}"' in strings, f"base strings must define {name}", failures)
        require(f'name="{name}"' in strings_ru, f"Russian strings must define {name}", failures)

    if failures:
        print("Editable forwarding guard failed:", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print("Editable forwarding guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
