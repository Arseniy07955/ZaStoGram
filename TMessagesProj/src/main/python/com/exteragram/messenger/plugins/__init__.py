"""Java class shims for exteraGram plugin imports."""

from java import jclass


Plugin = jclass("com.exteragram.messenger.plugins.Plugin")
PluginsController = jclass("com.exteragram.messenger.plugins.PluginsController")
