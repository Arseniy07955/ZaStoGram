package org.telegram.messenger;

import android.text.TextUtils;
import android.util.SparseBooleanArray;

import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.TLRPC;

import java.util.ArrayList;

public class EditableForwardDraft {

    public enum GroupingMode {
        ALBUM,
        SEPARATE_POSTS
    }

    public static class Item {
        public final MessageObject source;
        public final int id;
        public boolean selected;
        public boolean supported;
        public String unsupportedReason;
        public String caption;
        public ArrayList<TLRPC.MessageEntity> entities;

        private Item(MessageObject source, boolean selected, boolean hideCaption) {
            this.source = source;
            this.id = source.getId();
            this.selected = selected;
            this.supported = canCopy(source);
            this.unsupportedReason = supported ? null : "unsupported";
            if (!hideCaption && source.messageOwner != null) {
                caption = source.messageOwner.message;
                entities = copyEntities(source.messageOwner.entities);
            } else {
                caption = "";
                entities = null;
            }
        }

        public boolean setCaption(String caption, ArrayList<TLRPC.MessageEntity> entities) {
            this.caption = caption == null ? "" : caption;
            this.entities = copyEntities(entities);
            return true;
        }
    }

    private final ArrayList<Item> items = new ArrayList<>();
    private GroupingMode groupingMode = GroupingMode.ALBUM;
    private boolean enabled = true;

    public EditableForwardDraft(ArrayList<MessageObject> messages, SparseBooleanArray selectedIds, boolean hideCaptions) {
        if (messages == null) {
            return;
        }
        for (int i = 0; i < messages.size(); i++) {
            MessageObject messageObject = messages.get(i);
            if (messageObject == null || messageObject.messageOwner == null) {
                continue;
            }
            boolean selected = selectedIds == null || selectedIds.get(messageObject.getId(), false);
            items.add(new Item(messageObject, selected, hideCaptions));
        }
    }

    public void setGroupingMode(GroupingMode groupingMode) {
        this.groupingMode = groupingMode == null ? GroupingMode.ALBUM : groupingMode;
    }

    public GroupingMode getGroupingMode() {
        return groupingMode;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public ArrayList<Item> getItems() {
        return items;
    }

    public ArrayList<MessageObject> getSourceMessages() {
        ArrayList<MessageObject> messages = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            messages.add(items.get(i).source);
        }
        return messages;
    }

    public void syncSelectedIds(SparseBooleanArray selectedIds) {
        if (selectedIds == null) {
            return;
        }
        for (int i = 0; i < items.size(); i++) {
            Item item = items.get(i);
            item.selected = selectedIds.get(item.id, false);
        }
    }

    public boolean hasUnsupportedSelectedItems() {
        for (int i = 0; i < items.size(); i++) {
            Item item = items.get(i);
            if (item.selected && !item.supported) {
                return true;
            }
        }
        return false;
    }

    public boolean setCaption(int messageId, String caption, ArrayList<TLRPC.MessageEntity> entities) {
        Item item = findItem(messageId);
        return item != null && item.setCaption(caption, entities);
    }

    public Item findItem(int messageId) {
        for (int i = 0; i < items.size(); i++) {
            Item item = items.get(i);
            if (item.id == messageId) {
                return item;
            }
        }
        return null;
    }

    public ArrayList<Item> getSelectedItems() {
        ArrayList<Item> selectedItems = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            Item item = items.get(i);
            if (item.selected) {
                selectedItems.add(item);
            }
        }
        return selectedItems;
    }

    public ArrayList<MessageObject> buildPreviewMessages(int currentAccount, long dialogId, MessagePreviewParams params) {
        ArrayList<MessageObject> previewMessages = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            MessageObject preview = buildPreviewMessage(currentAccount, dialogId, items.get(i));
            if (preview != null) {
                previewMessages.add(0, preview);
            }
        }
        return previewMessages;
    }

    public static boolean canCopy(MessageObject messageObject) {
        if (messageObject == null || messageObject.messageOwner == null || messageObject.getId() <= 0) {
            return false;
        }
        TLRPC.Message owner = messageObject.messageOwner;
        TLRPC.MessageMedia media = owner.media;
        if (media == null || media instanceof TLRPC.TL_messageMediaEmpty || media instanceof TLRPC.TL_messageMediaWebPage) {
            return !TextUtils.isEmpty(owner.message);
        }
        return media.photo instanceof TLRPC.TL_photo || media.document instanceof TLRPC.TL_document;
    }

    private MessageObject buildPreviewMessage(int currentAccount, long dialogId, Item item) {
        MessageObject source = item.source;
        if (source == null || source.messageOwner == null) {
            return null;
        }
        TLRPC.Message original = source.messageOwner;
        TLRPC.TL_message message = new TLRPC.TL_message();
        message.id = original.id;
        message.date = ConnectionsManager.getInstance(currentAccount).getCurrentTime();
        message.dialog_id = dialogId;
        message.peer_id = original.peer_id;
        message.from_id = new TLRPC.TL_peerUser();
        message.from_id.user_id = UserConfig.getInstance(currentAccount).getClientUserId();
        message.message = item.caption == null ? "" : item.caption;
        ArrayList<TLRPC.MessageEntity> previewEntities = copyEntities(item.entities);
        if (previewEntities != null) {
            message.entities = previewEntities;
        }
        message.media = original.media;
        message.action = original.action;
        message.out = true;
        message.unread = false;
        message.invert_media = original.invert_media;
        message.via_bot_id = original.via_bot_id;
        message.restriction_reason = original.restriction_reason;
        message.attachPath = original.attachPath == null ? "" : original.attachPath;
        if (message.media != null) {
            message.flags |= TLRPC.MESSAGE_FLAG_HAS_MEDIA;
        }
        if (message.entities != null && !message.entities.isEmpty()) {
            message.flags |= TLRPC.MESSAGE_FLAG_HAS_ENTITIES;
        }
        if (groupingMode == GroupingMode.ALBUM && original.grouped_id != 0) {
            message.grouped_id = original.grouped_id;
            message.flags |= 131072;
        }
        MessageObject previewMessage = new MessageObject(currentAccount, message, true, false);
        previewMessage.hideSendersName = true;
        return previewMessage;
    }

    private static ArrayList<TLRPC.MessageEntity> copyEntities(ArrayList<TLRPC.MessageEntity> entities) {
        if (entities == null || entities.isEmpty()) {
            return null;
        }
        return new ArrayList<>(entities);
    }
}
