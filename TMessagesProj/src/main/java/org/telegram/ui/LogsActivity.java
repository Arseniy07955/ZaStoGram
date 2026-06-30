/*
 * ZaStoGram — экран логов: список всех файлов логов с возможностью
 * выборочного просмотра, отправки и удаления, плюс тумблер логирования.
 */

package org.telegram.ui;

import android.app.Activity;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.CheckBox;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.BuildVars;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.messenger.Utilities;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.ActionBarMenu;
import org.telegram.ui.ActionBar.ActionBarMenuItem;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Cells.HeaderCell;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Cells.TextInfoPrivacyCell;
import org.telegram.ui.Cells.TextSettingsCell;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.RecyclerListView;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public class LogsActivity extends BaseFragment {

    private static final int SUBITEM_SELECT_ALL = 1;
    private static final int SUBITEM_SEND_SELECTED = 2;
    private static final int SUBITEM_SEND_ALL = 3;
    private static final int SUBITEM_DELETE_SELECTED = 4;
    private static final int SUBITEM_DELETE_ALL = 5;
    private static final int SUBITEM_NEW_FILE = 6;

    private static final int VIEW_TYPE_CHECK = 0;
    private static final int VIEW_TYPE_INFO = 1;
    private static final int VIEW_TYPE_HEADER = 2;
    private static final int VIEW_TYPE_FILE = 3;
    private static final int VIEW_TYPE_EMPTY = 4;
    private static final int VIEW_TYPE_SETTINGS = 5;

    private RecyclerListView listView;
    private ListAdapter adapter;
    private ActionBarMenuItem otherItem;

    private final ArrayList<File> files = new ArrayList<>();
    private final HashSet<String> selected = new HashSet<>();
    private String currentPrefix;

    private int rowCount;
    private int enableRow;
    private int limitRow;
    private int enableInfoRow;
    private int filesHeaderRow;
    private int filesStartRow;
    private int filesEndRow;
    private int emptyRow;
    private int footerRow;

    @Override
    public boolean onFragmentCreate() {
        loadFiles();
        return super.onFragmentCreate();
    }

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setAllowOverlayTitle(true);
        actionBar.setTitle(LocaleController.getString(R.string.ZaLogsTitle));
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                } else if (id == SUBITEM_SELECT_ALL) {
                    selectAllOrNone();
                } else if (id == SUBITEM_SEND_SELECTED) {
                    shareFiles(getParentActivity(), collectSelected());
                } else if (id == SUBITEM_SEND_ALL) {
                    shareFiles(getParentActivity(), new ArrayList<>(files));
                } else if (id == SUBITEM_DELETE_SELECTED) {
                    confirmDelete(true);
                } else if (id == SUBITEM_DELETE_ALL) {
                    confirmDelete(false);
                } else if (id == SUBITEM_NEW_FILE) {
                    newLogFile();
                }
            }
        });

        ActionBarMenu menu = actionBar.createMenu();
        otherItem = menu.addItem(0, R.drawable.ic_ab_other);
        otherItem.addSubItem(SUBITEM_SELECT_ALL, LocaleController.getString(R.string.ZaLogsSelectAll));
        otherItem.addSubItem(SUBITEM_SEND_SELECTED, LocaleController.getString(R.string.ZaLogsSendSelected));
        otherItem.addSubItem(SUBITEM_SEND_ALL, LocaleController.getString(R.string.ZaLogsSendAll));
        otherItem.addSubItem(SUBITEM_DELETE_SELECTED, LocaleController.getString(R.string.ZaLogsDeleteSelected));
        otherItem.addSubItem(SUBITEM_DELETE_ALL, LocaleController.getString(R.string.ZaLogsDeleteAll));
        otherItem.addSubItem(SUBITEM_NEW_FILE, LocaleController.getString(R.string.ZaLogsNewFile));

        FrameLayout frameLayout = new FrameLayout(context);
        fragmentView = frameLayout;
        frameLayout.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));

        listView = new RecyclerListView(context);
        listView.setVerticalScrollBarEnabled(false);
        listView.setLayoutManager(new LinearLayoutManager(context, LinearLayoutManager.VERTICAL, false));
        adapter = new ListAdapter(context);
        listView.setAdapter(adapter);
        frameLayout.addView(listView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT));

        listView.setOnItemClickListener((view, position) -> {
            if (position == enableRow) {
                toggleLogging();
            } else if (position == limitRow) {
                showLimitDialog();
            } else if (filesStartRow != -1 && position >= filesStartRow && position < filesEndRow) {
                File f = files.get(position - filesStartRow);
                if (f != null && f.exists()) {
                    Bundle b = new Bundle();
                    b.putString("path", f.getAbsolutePath());
                    presentFragment(new LogViewerActivity(b));
                }
            }
        });

        updateMenu();
        return fragmentView;
    }

    @Override
    public void onResume() {
        super.onResume();
        loadFiles();
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
        updateMenu();
    }

    private void loadFiles() {
        files.clear();
        File current = FileLog.getCurrentLogFile();
        currentPrefix = null;
        if (current != null) {
            String name = current.getName();
            int dot = name.indexOf('.');
            currentPrefix = dot > 0 ? name.substring(0, dot) : name;
        }
        File dir = AndroidUtilities.getLogsDir();
        if (dir != null) {
            File[] arr = dir.listFiles();
            if (arr != null) {
                for (File f : arr) {
                    if (f == null || !f.isFile()) {
                        continue;
                    }
                    if ("logs.zip".equals(f.getName())) {
                        continue;
                    }
                    files.add(f);
                }
            }
        }
        Collections.sort(files, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
        HashSet<String> present = new HashSet<>();
        for (File f : files) {
            present.add(f.getAbsolutePath());
        }
        selected.retainAll(present);
        updateRows();
    }

    private void updateRows() {
        rowCount = 0;
        enableRow = rowCount++;
        limitRow = rowCount++;
        enableInfoRow = rowCount++;
        if (files.isEmpty()) {
            filesHeaderRow = -1;
            filesStartRow = -1;
            filesEndRow = -1;
            emptyRow = rowCount++;
        } else {
            emptyRow = -1;
            filesHeaderRow = rowCount++;
            filesStartRow = rowCount;
            rowCount += files.size();
            filesEndRow = rowCount;
        }
        footerRow = rowCount++;
    }

    private void updateMenu() {
        if (otherItem == null) {
            return;
        }
        boolean hasSelection = !selected.isEmpty();
        if (hasSelection) {
            otherItem.showSubItem(SUBITEM_SEND_SELECTED);
            otherItem.showSubItem(SUBITEM_DELETE_SELECTED);
        } else {
            otherItem.hideSubItem(SUBITEM_SEND_SELECTED);
            otherItem.hideSubItem(SUBITEM_DELETE_SELECTED);
        }
        actionBar.setTitle(hasSelection
                ? LocaleController.formatString(R.string.ZaLogsSelectedCount, selected.size())
                : LocaleController.getString(R.string.ZaLogsTitle));
    }

    private ArrayList<File> collectSelected() {
        ArrayList<File> result = new ArrayList<>();
        for (File f : files) {
            if (selected.contains(f.getAbsolutePath())) {
                result.add(f);
            }
        }
        return result;
    }

    private void selectAllOrNone() {
        if (selected.size() >= files.size()) {
            selected.clear();
        } else {
            selected.clear();
            for (File f : files) {
                selected.add(f.getAbsolutePath());
            }
        }
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
        updateMenu();
    }

    private void toggleLogging() {
        BuildVars.LOGS_ENABLED = !BuildVars.LOGS_ENABLED;
        ApplicationLoader.applicationContext
                .getSharedPreferences("systemConfig", Context.MODE_PRIVATE)
                .edit().putBoolean("logsEnabled", BuildVars.LOGS_ENABLED).commit();
        if (BuildVars.LOGS_ENABLED) {
            FileLog.ensureInitied();
        }
        loadFiles();
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
        updateMenu();
    }

    private void newLogFile() {
        if (!BuildVars.LOGS_ENABLED) {
            if (getParentActivity() != null) {
                Toast.makeText(getParentActivity(), LocaleController.getString(R.string.ZaLogsEnable), Toast.LENGTH_SHORT).show();
            }
            return;
        }
        FileLog.rotateLog(true);
        if (getParentActivity() != null) {
            Toast.makeText(getParentActivity(), LocaleController.getString(R.string.ZaLogsNewFileDone), Toast.LENGTH_SHORT).show();
        }
        AndroidUtilities.runOnUIThread(() -> {
            loadFiles();
            if (adapter != null) {
                adapter.notifyDataSetChanged();
            }
        }, 500);
    }

    private String limitValueText() {
        int n = FileLog.getMaxLogFiles();
        return n <= 0 ? LocaleController.getString(R.string.ZaLogsKeepUnlimited) : String.valueOf(n);
    }

    private void showLimitDialog() {
        if (getParentActivity() == null) {
            return;
        }
        final int[] values = {10, 25, 50, 100, 0};
        String[] labels = new String[values.length];
        for (int i = 0; i < values.length; i++) {
            labels[i] = values[i] <= 0 ? LocaleController.getString(R.string.ZaLogsKeepUnlimited) : String.valueOf(values[i]);
        }
        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity());
        builder.setTitle(LocaleController.getString(R.string.ZaLogsKeep));
        builder.setItems(labels, (dialog, which) -> {
            int n = values[which];
            ApplicationLoader.applicationContext
                    .getSharedPreferences("systemConfig", Context.MODE_PRIVATE)
                    .edit().putInt("logsMaxFiles", n).commit();
            if (adapter != null) {
                adapter.notifyItemChanged(limitRow);
            }
            Utilities.globalQueue.postRunnable(() -> FileLog.pruneOldLogs(n));
            AndroidUtilities.runOnUIThread(() -> {
                loadFiles();
                if (adapter != null) {
                    adapter.notifyDataSetChanged();
                }
                updateMenu();
            }, 300);
        });
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        showDialog(builder.create());
    }

    private void confirmDelete(boolean selectedOnly) {
        if (getParentActivity() == null) {
            return;
        }
        final ArrayList<File> targets = new ArrayList<>();
        ArrayList<File> source = selectedOnly ? collectSelected() : new ArrayList<>(files);
        for (File f : source) {
            // Не удаляем файлы текущей живой сессии, чтобы не сломать запись лога.
            if (currentPrefix != null && f.getName().startsWith(currentPrefix)) {
                continue;
            }
            targets.add(f);
        }
        if (targets.isEmpty()) {
            Toast.makeText(getParentActivity(), LocaleController.getString(R.string.ZaLogsNothingSelected), Toast.LENGTH_SHORT).show();
            return;
        }
        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity());
        builder.setTitle(LocaleController.getString(R.string.ZaLogsDeleteTitle));
        builder.setMessage(LocaleController.getString(selectedOnly ? R.string.ZaLogsDeleteSelectedMsg : R.string.ZaLogsDeleteAllMsg));
        builder.setPositiveButton(LocaleController.getString(R.string.Delete), (dialog, which) -> {
            for (File f : targets) {
                try {
                    f.delete();
                } catch (Exception ignore) {
                }
                selected.remove(f.getAbsolutePath());
            }
            loadFiles();
            if (adapter != null) {
                adapter.notifyDataSetChanged();
            }
            updateMenu();
        });
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        AlertDialog dialog = builder.create();
        showDialog(dialog);
        View positive = dialog.getButton(DialogInterface.BUTTON_POSITIVE);
        if (positive instanceof TextView) {
            ((TextView) positive).setTextColor(Theme.getColor(Theme.key_text_RedBold));
        }
    }

    private void onSelectionToggled(File file) {
        if (file == null) {
            return;
        }
        String path = file.getAbsolutePath();
        if (selected.contains(path)) {
            selected.remove(path);
        } else {
            selected.add(path);
        }
        updateMenu();
    }

    private static String typeLabel(String name) {
        if (name.contains("_mtproto")) {
            return "MTProto";
        }
        if (name.contains("_net")) {
            return "Network";
        }
        if (name.contains("_tonlib")) {
            return "TON";
        }
        if (name.endsWith(".hprof")) {
            return "Heap dump";
        }
        return "Log";
    }

    /**
     * Зипует переданные файлы (или отправляет один файл напрямую) и открывает
     * системный диалог «Поделиться». Используется и просмотрщиком одного файла.
     */
    public static void shareFiles(Activity activity, ArrayList<File> source) {
        if (activity == null) {
            return;
        }
        if (source == null || source.isEmpty()) {
            Toast.makeText(activity, LocaleController.getString(R.string.ZaLogsNothingSelected), Toast.LENGTH_SHORT).show();
            return;
        }
        final AlertDialog progressDialog = new AlertDialog(activity, AlertDialog.ALERT_TYPE_SPINNER);
        progressDialog.setCanCancel(false);
        progressDialog.show();
        final ArrayList<File> input = new ArrayList<>(source);
        Utilities.globalQueue.postRunnable(() -> {
            File toSend = null;
            String mime = "text/plain";
            boolean ok = false;
            try {
                ArrayList<File> existing = new ArrayList<>();
                for (File f : input) {
                    if (f != null && f.exists() && f.isFile()) {
                        existing.add(f);
                    }
                }
                if (existing.isEmpty()) {
                    AndroidUtilities.runOnUIThread(progressDialog::dismiss);
                    return;
                }
                if (existing.size() == 1) {
                    toSend = existing.get(0);
                    mime = "text/plain";
                    ok = true;
                } else {
                    File dir = AndroidUtilities.getLogsDir();
                    File zip = new File(dir, "logs.zip");
                    if (zip.exists()) {
                        zip.delete();
                    }
                    ZipOutputStream out = null;
                    try {
                        out = new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(zip)));
                        byte[] data = new byte[1024 * 64];
                        for (File f : existing) {
                            BufferedInputStream origin = new BufferedInputStream(new FileInputStream(f), data.length);
                            try {
                                out.putNextEntry(new ZipEntry(f.getName()));
                                int count;
                                while ((count = origin.read(data, 0, data.length)) != -1) {
                                    out.write(data, 0, count);
                                }
                            } finally {
                                origin.close();
                            }
                        }
                    } finally {
                        if (out != null) {
                            out.close();
                        }
                    }
                    toSend = zip;
                    mime = "message/rfc822";
                    ok = true;
                }
            } catch (Exception e) {
                FileLog.e(e);
            }
            final File finalFile = toSend;
            final String finalMime = mime;
            final boolean finalOk = ok;
            AndroidUtilities.runOnUIThread(() -> {
                try {
                    progressDialog.dismiss();
                } catch (Exception ignore) {
                }
                if (!finalOk || finalFile == null) {
                    Toast.makeText(activity, LocaleController.getString(R.string.ErrorOccurred), Toast.LENGTH_SHORT).show();
                    return;
                }
                try {
                    Uri uri;
                    if (Build.VERSION.SDK_INT >= 24) {
                        uri = FileProvider.getUriForFile(activity, ApplicationLoader.getApplicationId() + ".provider", finalFile);
                    } else {
                        uri = Uri.fromFile(finalFile);
                    }
                    Intent i = new Intent(Intent.ACTION_SEND);
                    if (Build.VERSION.SDK_INT >= 24) {
                        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    }
                    i.setType(finalMime);
                    i.putExtra(Intent.EXTRA_SUBJECT, "Logs from " + LocaleController.getInstance().getFormatterStats().format(System.currentTimeMillis()));
                    i.putExtra(Intent.EXTRA_STREAM, uri);
                    activity.startActivityForResult(Intent.createChooser(i, "Select app to send logs"), 500);
                } catch (Exception e) {
                    FileLog.e(e);
                }
            });
        });
    }

    private class ListAdapter extends RecyclerListView.SelectionAdapter {

        private final Context mContext;

        ListAdapter(Context context) {
            mContext = context;
        }

        @Override
        public int getItemCount() {
            return rowCount;
        }

        @Override
        public boolean isEnabled(RecyclerView.ViewHolder holder) {
            int pos = holder.getAdapterPosition();
            if (pos == enableRow || pos == limitRow) {
                return true;
            }
            return filesStartRow != -1 && pos >= filesStartRow && pos < filesEndRow;
        }

        @Override
        public RecyclerView.ViewHolder onCreateViewHolder(android.view.ViewGroup parent, int viewType) {
            View view;
            switch (viewType) {
                case VIEW_TYPE_CHECK:
                    view = new TextCheckCell(mContext);
                    view.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
                    break;
                case VIEW_TYPE_SETTINGS:
                    view = new TextSettingsCell(mContext);
                    view.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
                    break;
                case VIEW_TYPE_HEADER:
                    view = new HeaderCell(mContext);
                    view.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));
                    break;
                case VIEW_TYPE_INFO:
                case VIEW_TYPE_EMPTY:
                    view = new TextInfoPrivacyCell(mContext);
                    break;
                case VIEW_TYPE_FILE:
                default:
                    view = new LogCell(mContext);
                    break;
            }
            view.setLayoutParams(new RecyclerView.LayoutParams(RecyclerView.LayoutParams.MATCH_PARENT, RecyclerView.LayoutParams.WRAP_CONTENT));
            return new RecyclerListView.Holder(view);
        }

        @Override
        public void onBindViewHolder(RecyclerView.ViewHolder holder, int position) {
            switch (holder.getItemViewType()) {
                case VIEW_TYPE_CHECK: {
                    TextCheckCell cell = (TextCheckCell) holder.itemView;
                    cell.setTextAndCheck(LocaleController.getString(R.string.ZaLogsEnable), BuildVars.LOGS_ENABLED, true);
                    break;
                }
                case VIEW_TYPE_SETTINGS: {
                    TextSettingsCell cell = (TextSettingsCell) holder.itemView;
                    cell.setTextAndValue(LocaleController.getString(R.string.ZaLogsKeep), limitValueText(), false);
                    break;
                }
                case VIEW_TYPE_HEADER: {
                    ((HeaderCell) holder.itemView).setText(LocaleController.getString(R.string.ZaLogsFilesHeader));
                    break;
                }
                case VIEW_TYPE_INFO: {
                    TextInfoPrivacyCell cell = (TextInfoPrivacyCell) holder.itemView;
                    if (position == enableInfoRow) {
                        cell.setText(LocaleController.getString(R.string.ZaLogsEnableInfo));
                        cell.setBackgroundDrawable(Theme.getThemedDrawable(mContext, R.drawable.greydivider_top, Theme.getColor(Theme.key_windowBackgroundGrayShadow)));
                    } else {
                        cell.setText(LocaleController.getString(R.string.ZaLogsFooter));
                        cell.setBackgroundDrawable(Theme.getThemedDrawable(mContext, R.drawable.greydivider_bottom, Theme.getColor(Theme.key_windowBackgroundGrayShadow)));
                    }
                    break;
                }
                case VIEW_TYPE_EMPTY: {
                    TextInfoPrivacyCell cell = (TextInfoPrivacyCell) holder.itemView;
                    cell.setText(LocaleController.getString(R.string.ZaLogsEmpty));
                    cell.setBackgroundDrawable(Theme.getThemedDrawable(mContext, R.drawable.greydivider_bottom, Theme.getColor(Theme.key_windowBackgroundGrayShadow)));
                    break;
                }
                case VIEW_TYPE_FILE:
                default: {
                    int idx = position - filesStartRow;
                    if (idx < 0 || idx >= files.size()) {
                        break;
                    }
                    File f = files.get(idx);
                    boolean current = currentPrefix != null && f.getName().startsWith(currentPrefix);
                    boolean checked = selected.contains(f.getAbsolutePath());
                    boolean divider = idx < files.size() - 1;
                    ((LogCell) holder.itemView).setData(f, current, checked, divider);
                    break;
                }
            }
        }

        @Override
        public int getItemViewType(int position) {
            if (position == enableRow) {
                return VIEW_TYPE_CHECK;
            }
            if (position == limitRow) {
                return VIEW_TYPE_SETTINGS;
            }
            if (position == enableInfoRow || position == footerRow) {
                return VIEW_TYPE_INFO;
            }
            if (position == filesHeaderRow) {
                return VIEW_TYPE_HEADER;
            }
            if (position == emptyRow) {
                return VIEW_TYPE_EMPTY;
            }
            return VIEW_TYPE_FILE;
        }
    }

    private class LogCell extends FrameLayout {

        private final CheckBox checkBox;
        private final TextView titleView;
        private final TextView subtitleView;
        private File file;
        private boolean needDivider;

        LogCell(Context context) {
            super(context);
            setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));

            FrameLayout checkContainer = new FrameLayout(context);
            checkContainer.setOnClickListener(v -> {
                if (file == null) {
                    return;
                }
                boolean now = !selected.contains(file.getAbsolutePath());
                checkBox.setChecked(now);
                onSelectionToggled(file);
            });
            addView(checkContainer, LayoutHelper.createFrame(56, LayoutHelper.MATCH_PARENT, Gravity.LEFT | Gravity.TOP));

            checkBox = new CheckBox(context);
            checkBox.setClickable(false);
            checkBox.setFocusable(false);
            checkBox.setButtonTintList(ColorStateList.valueOf(Theme.getColor(Theme.key_switchTrackChecked)));
            checkContainer.addView(checkBox, LayoutHelper.createFrame(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT, Gravity.CENTER));

            titleView = new TextView(context);
            titleView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
            titleView.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 16);
            titleView.setMaxLines(1);
            titleView.setSingleLine(true);
            titleView.setEllipsize(TextUtils.TruncateAt.END);
            addView(titleView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.LEFT | Gravity.TOP, 60, 9, 16, 0));

            subtitleView = new TextView(context);
            subtitleView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText2));
            subtitleView.setTextSize(TypedValue.COMPLEX_UNIT_DIP, 13);
            subtitleView.setMaxLines(1);
            subtitleView.setSingleLine(true);
            subtitleView.setEllipsize(TextUtils.TruncateAt.END);
            addView(subtitleView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.LEFT | Gravity.TOP, 60, 33, 16, 0));
        }

        void setData(File f, boolean current, boolean checked, boolean divider) {
            file = f;
            titleView.setText(LocaleController.getInstance().getFormatterStats().format(f.lastModified()));
            String sub = typeLabel(f.getName()) + " · " + AndroidUtilities.formatFileSize(f.length());
            if (current) {
                sub += " · " + LocaleController.getString(R.string.ZaLogsCurrent);
            }
            subtitleView.setText(sub);
            checkBox.setChecked(checked);
            needDivider = divider;
            setWillNotDraw(!divider);
            requestLayout();
        }

        @Override
        protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
            super.onMeasure(
                    MeasureSpec.makeMeasureSpec(MeasureSpec.getSize(widthMeasureSpec), MeasureSpec.EXACTLY),
                    MeasureSpec.makeMeasureSpec(AndroidUtilities.dp(60) + (needDivider ? 1 : 0), MeasureSpec.EXACTLY));
        }

        @Override
        protected void onDraw(Canvas canvas) {
            if (needDivider && Theme.dividerPaint != null) {
                canvas.drawLine(AndroidUtilities.dp(60), getMeasuredHeight() - 1, getMeasuredWidth(), getMeasuredHeight() - 1, Theme.dividerPaint);
            }
        }
    }
}
