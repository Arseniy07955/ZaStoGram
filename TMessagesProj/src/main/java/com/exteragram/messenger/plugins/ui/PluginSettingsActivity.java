package com.exteragram.messenger.plugins.ui;

import android.content.Context;
import android.view.View;

import com.exteragram.messenger.plugins.Plugin;

/**
 * exteraGram-compatible class name for plugins which instantiate their settings screen directly.
 */
public class PluginSettingsActivity extends org.telegram.ui.Plugins.PluginSettingsActivity {

    public PluginSettingsActivity(Plugin plugin) {
        super(plugin != null ? plugin.getId() : "");
    }

    public PluginSettingsActivity(String pluginId) {
        super(pluginId);
    }

    @Override
    public View createView(Context context) {
        return super.createView(context);
    }
}
