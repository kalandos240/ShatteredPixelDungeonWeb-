#!/usr/bin/env python3
from pathlib import Path
import shutil
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


# TeaVM itself receives a dedicated out-of-process heap in web/build.gradle.
# Keep the regular Gradle daemon at upstream's 2 GB and disable parallel
# workers so the compiler process has enough room on CI.
gradle_properties = root / "gradle.properties"
gradle_properties_text = gradle_properties.read_text(encoding="utf-8")
gradle_properties_text = gradle_properties_text.replace(
    "org.gradle.jvmargs=-Xmx2048m -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8",
    "org.gradle.jvmargs=-Xmx2048m -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8"
)
gradle_properties_text = gradle_properties_text.replace(
    "org.gradle.parallel=true",
    "org.gradle.parallel=false"
)
gradle_properties.write_text(gradle_properties_text, encoding="utf-8")


# SharedLibraryLoader.os does not exist in the TeaVM libGDX emulation.
# Device checks should use the backend-neutral ApplicationType API.
device_compat = root / "SPD-classes/src/main/java/com/watabou/utils/DeviceCompat.java"
device_compat_text = device_compat.read_text(encoding="utf-8")
device_compat_text = device_compat_text.replace(
    "import com.badlogic.gdx.Gdx;\nimport com.badlogic.gdx.Input;\nimport com.badlogic.gdx.utils.Os;\nimport com.badlogic.gdx.utils.SharedLibraryLoader;",
    "import com.badlogic.gdx.Application;\nimport com.badlogic.gdx.Gdx;\nimport com.badlogic.gdx.Input;"
)
device_compat_text = device_compat_text.replace(
    """\tpublic static boolean isAndroid(){
\t\treturn SharedLibraryLoader.os == Os.Android;
\t}

\tpublic static boolean isiOS(){
\t\treturn SharedLibraryLoader.os == Os.IOS;
\t}

\tpublic static boolean isDesktop(){
\t\treturn SharedLibraryLoader.os == Os.Windows || SharedLibraryLoader.os == Os.MacOsX || SharedLibraryLoader.os == Os.Linux;
\t}""",
    """\tpublic static boolean isAndroid(){
\t\treturn Gdx.app.getType() == Application.ApplicationType.Android;
\t}

\tpublic static boolean isiOS(){
\t\treturn Gdx.app.getType() == Application.ApplicationType.iOS;
\t}

\tpublic static boolean isDesktop(){
\t\treturn Gdx.app.getType() == Application.ApplicationType.Desktop
\t\t\t\t|| Gdx.app.getType() == Application.ApplicationType.HeadlessDesktop;
\t}"""
)
device_compat.write_text(device_compat_text, encoding="utf-8")


# The desktop/iOS platform support uses Droid Sans for CJK glyph coverage, but
# upstream keeps the binary font under desktop assets instead of core assets.
# Copy it into the generated web asset tree without duplicating the 3.6 MB font
# in this overlay repository.
web_font_source = root / "desktop/src/main/assets/fonts/droid_sans.ttf"
web_font_target = root / "core/src/main/assets/fonts/droid_sans.ttf"
if not web_font_source.is_file():
    raise SystemExit(f"Missing upstream fallback font: {web_font_source}")
web_font_target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(web_font_source, web_font_target)


# Shattered forces SpriteBatch to client-side VertexArray in TextInput as a
# native-driver workaround. WebGL forbids that glVertexAttribPointer(Buffer)
# path, so use a VBO for the browser while preserving upstream behavior on
# native platforms.
text_input_text = text_input.read_text(encoding="utf-8")
old_vertex_type = "SpriteBatch.overrideVertexType = Mesh.VertexDataType.VertexArray;"
new_vertex_type = (
    "SpriteBatch.overrideVertexType = "
    "Gdx.app.getType() == com.badlogic.gdx.Application.ApplicationType.WebGL "
    "? Mesh.VertexDataType.VertexBufferObject "
    ": Mesh.VertexDataType.VertexArray;"
)
if old_vertex_type in text_input_text:
    text_input_text = text_input_text.replace(old_vertex_type, new_vertex_type, 1)
elif new_vertex_type not in text_input_text:
    raise SystemExit("Could not locate SpriteBatch vertex type workaround")
text_input.write_text(text_input_text, encoding="utf-8")
