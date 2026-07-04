# Editable Forwarding Design

## Goal

Add a clean editable forwarding mode to ZaStoGram Android so a user can forward media as editable copies, choose whether selected media stays grouped as an album or becomes separate posts, and edit captions per media item before sending.

## User Experience

The existing forwarding options preview remains the entry point. It gains a clear mode for editable forwarding instead of replacing normal Telegram forwarding.

In editable forwarding mode the user can:

- Keep normal forwarding options for sender/caption visibility when they do not need edits.
- Switch to editable copy sending when they want control over captions or grouping.
- Choose the media grouping policy:
  - `Album`: preserve the selected media group where possible.
  - `Separate posts`: remove album grouping so each photo/video is sent as its own post.
- Tap a previewed media message and edit that item's caption.
- Apply or cancel changes before the network send begins.

For channels with linked discussions, `Separate posts` makes each media item a separate channel post, so comments attach below each item instead of only under the last album message.

## Architecture

The feature should use a separate forwarding draft model rather than adding more boolean flags to `ChatActivity` or `SendMessagesHelper`.

The model owns the user-editable state. The UI reads and mutates the model, and the send layer consumes a finished draft. Normal forwarding stays on the existing `TL_messages_forwardMessages` path.

### Core Model

Create the focused editable-forwarding model in `TMessagesProj/src/main/java/org/telegram/messenger/EditableForwardDraft.java` with these public types:

- `EditableForwardDraft`
- `EditableForwardDraft.Item`
- `EditableForwardDraft.GroupingMode`

Responsibilities:

- Keep the original `MessageObject` for each selected message.
- Track whether each message is selected.
- Store edited caption text and caption entities per item.
- Store grouping mode as `ALBUM` or `SEPARATE_POSTS`.
- Know whether the draft has edits that require copy sending.
- Build send-ready items for the send layer without mutating the original `MessageObject`.

The draft must not share mutable `TLRPC.Message` or media state in a way that lets preview edits alter source chat history.

### Preview Integration

`MessagePreviewParams` should own an optional editable forwarding draft for `forwardMessages`.

When the forwarding preview opens:

- Build the draft from the currently selected messages.
- Keep preview messages derived from the draft, not directly from original messages when editable mode is active.
- Rebuild preview grouping when the user switches between `Album` and `Separate posts`.
- Preserve existing selected-message behavior.

`MessagePreviewView` should expose the controls:

- A forwarding menu action for editable forwarding.
- A grouping control inside editable mode.
- Item-level caption editing when the user taps or selects a media item with a caption surface.

The UI should not directly decide how to send. It should update the draft and let `ChatActivity` pass the draft to `SendMessagesHelper`.

### Sending Flow

`ChatActivity.forwardMessages(...)` should branch only at the boundary:

- If there is no editable draft, continue using the existing `sendMessage(ArrayList<MessageObject>, ..., forwardFromMyName, hideCaption, ...)` path.
- If the draft requires editable copy sending, call a dedicated `SendMessagesHelper` method with the draft and existing send context: dialog id, notify, schedule date, topic/thread, mono forum peer, paid stars, and suggestion params.

`SendMessagesHelper` should add a dedicated editable-copy entry point instead of overloading the normal forwarding path with many special cases.

The editable-copy send path should:

- Reuse existing media send mechanisms where possible.
- Copy photos/videos/documents with edited captions.
- Preserve media spoilers and supported per-message metadata.
- Respect target chat send permissions before sending.
- Apply album grouping only when `GroupingMode.ALBUM` is selected and the selected items can be grouped.
- Send each item without a shared grouped id when `GroupingMode.SEPARATE_POSTS` is selected.
- Fall back to normal forwarding only when the user did not enter editable-copy mode.

## Behavior Rules

Normal forwarding remains unchanged.

Editable forwarding is copy sending. That means the forwarded-author header is intentionally absent when the user chooses editable mode, because Telegram server-side forwarding does not support arbitrary per-item caption edits and grouping rewrites.

If a source message cannot be copied cleanly through existing media send paths, editable mode must mark that item unsupported and show a visible explanation before send. The user can still leave editable mode and use normal forwarding for that item.

If the user chooses `Album` but selects messages from multiple unrelated media groups, the model should group only compatible contiguous media items and send incompatible items separately.

If the user chooses `Separate posts`, every selected media item must be sent without the original grouped id.

If captions are hidden through the old forwarding option and the user enters editable mode, the editable draft should start with empty captions. If the user later leaves editable mode, the old hide-caption behavior should still apply to normal forwarding.

## Error Handling

Permission failures should reuse existing send-media alert behavior where possible.

Draft creation should reject unsupported items before sending. Unsupported items include messages whose media cannot be resent by the local copy path, service/action messages, and media blocked by destination permissions.

Scheduled sending and paid-message confirmation should happen before actual send requests, matching current forwarding behavior.

The implementation should not mutate original message captions, entities, grouped ids, reply markup, or media objects.

## Testing

Use focused source guards and unit-style tests where the Android build is too heavy.

Minimum coverage:

- Draft creation keeps original messages unchanged.
- Per-item caption edits appear in preview messages and send-ready items.
- `Album` preserves grouping for compatible media.
- `Separate posts` clears grouping for each item.
- Normal forwarding still calls the existing forward path when editable mode is inactive.
- Editable mode calls the dedicated copy-send path.
- Hide-caption plus editable mode starts with empty draft captions.
- Unsupported message types are excluded or rejected before send.

Practical verification for this checkout:

- Run the focused tests or guard script added for the draft/model behavior.
- Run `git diff --check -- <touched files>`.
- If Java-only files are touched and a narrow compile command is available, run it; otherwise state the source-only proof boundary.

## Out Of Scope

This design does not add after-send message editing.

This design does not change Telegram server-side forwarding semantics.

This design does not promise comments under each item while preserving one album post, because linked discussion comments are controlled by the channel post structure. Per-item comments require separate posts.
