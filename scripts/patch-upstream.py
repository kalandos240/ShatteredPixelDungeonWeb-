#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-upstream.py <upstream-worktree>")

root = Path(sys.argv[1]).resolve()

settings = root / "settings.gradle"
settings_text = settings.read_text(encoding="utf-8")

plugin_management = """pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

"""

if "pluginManagement {" not in settings_text:
    settings_text = plugin_management + settings_text

if "include ':web'" not in settings_text:
    settings_text = settings_text.rstrip() + "\n\ninclude ':web'\n"

settings.write_text(settings_text, encoding="utf-8")

build = root / "build.gradle"
build_text = build.read_text(encoding="utf-8")

old = "gdxVersion = '1.14.0'"
new = "gdxVersion = '1.14.2'"
if old in build_text:
    build_text = build_text.replace(old, new, 1)
elif new not in build_text:
    raise SystemExit("Could not locate the expected upstream gdxVersion declaration")

build.write_text(build_text, encoding="utf-8")


# libGDX 1.14.1+ changed TextField.OnscreenKeyboard from show(boolean)
# to show(TextField) + close(). Adapt Shattered's platform delegation.
text_input = root / "SPD-classes/src/main/java/com/watabou/noosa/TextInput.java"
text_input_text = text_input.read_text(encoding="utf-8")
old_keyboard = """\t\ttextField.setOnscreenKeyboard(new TextField.OnscreenKeyboard() {
\t\t\t@Override
\t\t\tpublic void show(boolean visible) {
\t\t\t\tGame.platform.setOnscreenKeyboardVisible(visible, multiline);
\t\t\t}
\t\t});"""
new_keyboard = """\t\ttextField.setOnscreenKeyboard(new TextField.OnscreenKeyboard() {
\t\t\t@Override
\t\t\tpublic void show(TextField textField) {
\t\t\t\tGame.platform.setOnscreenKeyboardVisible(true, multiline);
\t\t\t}

\t\t\t@Override
\t\t\tpublic void close() {
\t\t\t\tGame.platform.setOnscreenKeyboardVisible(false, multiline);
\t\t\t}
\t\t});"""

if old_keyboard in text_input_text:
    text_input_text = text_input_text.replace(old_keyboard, new_keyboard, 1)
elif new_keyboard not in text_input_text:
    raise SystemExit("Could not locate TextField.OnscreenKeyboard compatibility block")

text_input.write_text(text_input_text, encoding="utf-8")
