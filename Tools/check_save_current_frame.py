#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PEER_STORIES = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/Stories/PeerStoriesView.java"
PHOTO_VIEWER = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/PhotoViewer.java"
MEDIA = ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/MediaController.java"
STRINGS = ROOT / "TMessagesProj/src/main/res/values/strings.xml"
STRINGS_RU = ROOT / "TMessagesProj/src/main/res/values-ru/strings.xml"


def require(text, needle, label):
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle}")


def main():
    peer_stories = PEER_STORIES.read_text(encoding="utf-8", errors="ignore")
    photo_viewer = PHOTO_VIEWER.read_text(encoding="utf-8", errors="ignore")
    media = MEDIA.read_text(encoding="utf-8", errors="ignore")
    strings = STRINGS.read_text(encoding="utf-8", errors="ignore")
    strings_ru = STRINGS_RU.read_text(encoding="utf-8", errors="ignore")

    require(strings, 'name="SaveCurrentFrame"', "English current-frame string")
    require(strings_ru, 'name="SaveCurrentFrame"', "Russian current-frame string")
    require(media, "saveBitmapToGallery(", "bitmap gallery-save helper")
    require(media, "bitmap.compress(Bitmap.CompressFormat.JPEG", "JPEG frame export")
    require(peer_stories, "saveCurrentFrameToGallery()", "stories frame-save handler")
    require(peer_stories, "captureCurrentFrameBitmap()", "stories frame capture helper")
    require(peer_stories, "MediaController.saveBitmapToGallery(", "stories bitmap save path")
    require(photo_viewer, "gallery_menu_save_current_frame", "video viewer menu id")
    require(photo_viewer, "saveCurrentFrameToGallery()", "video viewer frame-save handler")
    require(photo_viewer, "getCurrentVideoFrameBitmap()", "video viewer frame capture helper")
    require(photo_viewer, "MediaController.saveBitmapToGallery(", "video viewer bitmap save path")

    print("save current frame contract OK")


if __name__ == "__main__":
    main()
