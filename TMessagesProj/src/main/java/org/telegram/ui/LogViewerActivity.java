/*
 * ZaStoGram — просмотр одного файла лога.
 */

package org.telegram.ui;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Typeface;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.messenger.Utilities;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.ActionBarMenu;
import org.telegram.ui.ActionBar.ActionBarMenuItem;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;

import java.io.File;
import java.io.RandomAccessFile;
import java.util.ArrayList;

public class LogViewerActivity extends BaseFragment {

    private static final long MAX_BYTES = 1_500_000L;

    private static final int MENU_SHARE = 1;
    private static final int MENU_COPY = 2;

    private final File file;
    private TextView textView;
    private String loadedContent = "";

    public LogViewerActivity(Bundle args) {
        super(args);
        String path = args != null ? args.getString("path") : null;
        file = path != null ? new File(path) : null;
    }

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setAllowOverlayTitle(true);
        actionBar.setTitle(file != null ? file.getName() : LocaleController.getString(R.string.ZaLogsTitle));
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                } else if (id == MENU_SHARE) {
                    if (file != null && file.exists()) {
                        ArrayList<File> files = new ArrayList<>();
                        files.add(file);
                        LogsActivity.shareFiles(getParentActivity(), files);
                    }
                } else if (id == MENU_COPY) {
                    copyToClipboard();
                }
            }
        });

        ActionBarMenu menu = actionBar.createMenu();
        ActionBarMenuItem other = menu.addItem(0, R.drawable.ic_ab_other);
        other.addSubItem(MENU_SHARE, LocaleController.getString(R.string.ZaLogsShare));
        other.addSubItem(MENU_COPY, LocaleController.getString(R.string.ZaLogsCopyAll));

        ScrollView scrollView = new ScrollView(context);
        scrollView.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
        scrollView.setFillViewport(true);

        textView = new TextView(context);
        textView.setTextIsSelectable(true);
        textView.setTypeface(Typeface.MONOSPACE);
        textView.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 11);
        textView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        textView.setPadding(AndroidUtilities.dp(12), AndroidUtilities.dp(12), AndroidUtilities.dp(12), AndroidUtilities.dp(12));
        textView.setText(LocaleController.getString(R.string.Loading));
        scrollView.addView(textView, LayoutHelper.createScroll(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.TOP | Gravity.LEFT));

        fragmentView = scrollView;

        loadContent();
        return fragmentView;
    }

    private void loadContent() {
        if (file == null) {
            return;
        }
        Utilities.globalQueue.postRunnable(() -> {
            String content;
            try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {
                long len = raf.length();
                long start = len > MAX_BYTES ? len - MAX_BYTES : 0;
                raf.seek(start);
                byte[] buf = new byte[(int) (len - start)];
                raf.readFully(buf);
                content = new String(buf, "UTF-8");
                if (start > 0) {
                    content = LocaleController.getString(R.string.ZaLogsTruncated) + "\n\n" + content;
                }
            } catch (Throwable e) {
                content = String.valueOf(e);
            }
            final String finalContent = content;
            AndroidUtilities.runOnUIThread(() -> {
                loadedContent = finalContent;
                if (textView != null) {
                    textView.setText(finalContent.length() == 0 ? LocaleController.getString(R.string.ZaLogsEmpty) : finalContent);
                }
            });
        });
    }

    private void copyToClipboard() {
        try {
            Context context = getParentActivity();
            if (context == null) {
                return;
            }
            ClipboardManager clipboard = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
            if (clipboard != null) {
                clipboard.setPrimaryClip(ClipData.newPlainText("log", loadedContent));
                Toast.makeText(context, LocaleController.getString(R.string.ZaLogsCopied), Toast.LENGTH_SHORT).show();
            }
        } catch (Exception ignore) {
        }
    }
}
