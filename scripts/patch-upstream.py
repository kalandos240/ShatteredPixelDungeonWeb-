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


# WebGL never supports client-side vertex arrays. Noosa's legacy fast paths
# pass FloatBuffer/ShortBuffer directly to GL, so adapt those paths to reusable
# dynamic GPU buffers only on the web backend.
noosa_script = root / "SPD-classes/src/main/java/com/watabou/noosa/NoosaScript.java"
noosa_text = noosa_script.read_text(encoding="utf-8")

old_fields = """\tprivate Camera lastCamera;
\t
\tpublic NoosaScript() {"""
new_fields = """\tprivate Camera lastCamera;

\tprivate int webVertexBuffer = -1;
\tprivate int webIndexBuffer = -1;

\tprivate boolean webGL() {
\t\treturn Gdx.app.getType() == com.badlogic.gdx.Application.ApplicationType.WebGL;
\t}

\tprivate void bindWebVertices(FloatBuffer vertices) {
\t\tif (webVertexBuffer == -1) {
\t\t\twebVertexBuffer = Gdx.gl.glGenBuffer();
\t\t}
\t\t((Buffer)vertices).position(0);
\t\tGdx.gl.glBindBuffer(Gdx.gl.GL_ARRAY_BUFFER, webVertexBuffer);
\t\tGdx.gl.glBufferData(Gdx.gl.GL_ARRAY_BUFFER, vertices.limit() * Float.SIZE / 8,
\t\t\t\tvertices, Gdx.gl.GL_DYNAMIC_DRAW);
\t\taXY.vertexBuffer(2, 4, 0);
\t\taUV.vertexBuffer(2, 4, 2);
\t}

\tprivate void releaseWebVertices() {
\t\tGdx.gl.glBindBuffer(Gdx.gl.GL_ARRAY_BUFFER, 0);
\t}

\tprivate void bindWebIndices(ShortBuffer indices) {
\t\tif (webIndexBuffer == -1) {
\t\t\twebIndexBuffer = Gdx.gl.glGenBuffer();
\t\t}
\t\t((Buffer)indices).position(0);
\t\tGdx.gl.glBindBuffer(Gdx.gl.GL_ELEMENT_ARRAY_BUFFER, webIndexBuffer);
\t\tGdx.gl.glBufferData(Gdx.gl.GL_ELEMENT_ARRAY_BUFFER, indices.limit() * Short.SIZE / 8,
\t\t\t\tindices, Gdx.gl.GL_DYNAMIC_DRAW);
\t}

\tpublic NoosaScript() {"""
if old_fields in noosa_text:
    noosa_text = noosa_text.replace(old_fields, new_fields, 1)
elif new_fields not in noosa_text:
    raise SystemExit("Could not locate NoosaScript field insertion point")

old_draw_elements = """\tpublic void drawElements( FloatBuffer vertices, ShortBuffer indices, int size ) {

\t\t((Buffer)vertices).position( 0 );
\t\taXY.vertexPointer( 2, 4, vertices );

\t\t((Buffer)vertices).position( 2 );
\t\taUV.vertexPointer( 2, 4, vertices );

\t\tQuad.releaseIndices();
\t\tGdx.gl20.glDrawElements( Gdx.gl20.GL_TRIANGLES, size, Gdx.gl20.GL_UNSIGNED_SHORT, indices );
\t\tQuad.bindIndices();
\t}"""
new_draw_elements = """\tpublic void drawElements( FloatBuffer vertices, ShortBuffer indices, int size ) {

\t\tif (webGL()) {
\t\t\tbindWebVertices(vertices);
\t\t\tQuad.releaseIndices();
\t\t\tbindWebIndices(indices);
\t\t\tGdx.gl20.glDrawElements(Gdx.gl20.GL_TRIANGLES, size, Gdx.gl20.GL_UNSIGNED_SHORT, 0);
\t\t\tQuad.bindIndices();
\t\t\treleaseWebVertices();
\t\t\treturn;
\t\t}

\t\t((Buffer)vertices).position( 0 );
\t\taXY.vertexPointer( 2, 4, vertices );

\t\t((Buffer)vertices).position( 2 );
\t\taUV.vertexPointer( 2, 4, vertices );

\t\tQuad.releaseIndices();
\t\tGdx.gl20.glDrawElements( Gdx.gl20.GL_TRIANGLES, size, Gdx.gl20.GL_UNSIGNED_SHORT, indices );
\t\tQuad.bindIndices();
\t}"""
if old_draw_elements in noosa_text:
    noosa_text = noosa_text.replace(old_draw_elements, new_draw_elements, 1)
elif new_draw_elements not in noosa_text:
    raise SystemExit("Could not locate NoosaScript.drawElements")

old_draw_quad = """\tpublic void drawQuad( FloatBuffer vertices ) {

\t\t((Buffer)vertices).position( 0 );
\t\taXY.vertexPointer( 2, 4, vertices );

\t\t((Buffer)vertices).position( 2 );
\t\taUV.vertexPointer( 2, 4, vertices );
\t\t
\t\tGdx.gl20.glDrawElements( Gdx.gl20.GL_TRIANGLES, Quad.SIZE, Gdx.gl20.GL_UNSIGNED_SHORT, 0 );
\t}"""
new_draw_quad = """\tpublic void drawQuad( FloatBuffer vertices ) {

\t\tif (webGL()) {
\t\t\tbindWebVertices(vertices);
\t\t\tGdx.gl20.glDrawElements(Gdx.gl20.GL_TRIANGLES, Quad.SIZE, Gdx.gl20.GL_UNSIGNED_SHORT, 0);
\t\t\treleaseWebVertices();
\t\t\treturn;
\t\t}

\t\t((Buffer)vertices).position( 0 );
\t\taXY.vertexPointer( 2, 4, vertices );

\t\t((Buffer)vertices).position( 2 );
\t\taUV.vertexPointer( 2, 4, vertices );
\t\t
\t\tGdx.gl20.glDrawElements( Gdx.gl20.GL_TRIANGLES, Quad.SIZE, Gdx.gl20.GL_UNSIGNED_SHORT, 0 );
\t}"""
if old_draw_quad in noosa_text:
    noosa_text = noosa_text.replace(old_draw_quad, new_draw_quad, 1)
elif new_draw_quad not in noosa_text:
    raise SystemExit("Could not locate NoosaScript.drawQuad(FloatBuffer)")

old_draw_set = """\tpublic void drawQuadSet( FloatBuffer vertices, int size ) {
\t\t
\t\tif (size == 0) {
\t\t\treturn;
\t\t}

\t\t((Buffer)vertices).position( 0 );
\t\taXY.vertexPointer( 2, 4, vertices );

\t\t((Buffer)vertices).position( 2 );
\t\taUV.vertexPointer( 2, 4, vertices );
\t\t
\t\tGdx.gl20.glDrawElements( Gdx.gl20.GL_TRIANGLES, Quad.SIZE * size, Gdx.gl20.GL_UNSIGNED_SHORT, 0 );
\t}"""
new_draw_set = """\tpublic void drawQuadSet( FloatBuffer vertices, int size ) {
\t\t
\t\tif (size == 0) {
\t\t\treturn;
\t\t}

\t\tif (webGL()) {
\t\t\tbindWebVertices(vertices);
\t\t\tGdx.gl20.glDrawElements(Gdx.gl20.GL_TRIANGLES, Quad.SIZE * size, Gdx.gl20.GL_UNSIGNED_SHORT, 0);
\t\t\treleaseWebVertices();
\t\t\treturn;
\t\t}

\t\t((Buffer)vertices).position( 0 );
\t\taXY.vertexPointer( 2, 4, vertices );

\t\t((Buffer)vertices).position( 2 );
\t\taUV.vertexPointer( 2, 4, vertices );
\t\t
\t\tGdx.gl20.glDrawElements( Gdx.gl20.GL_TRIANGLES, Quad.SIZE * size, Gdx.gl20.GL_UNSIGNED_SHORT, 0 );
\t}"""
if old_draw_set in noosa_text:
    noosa_text = noosa_text.replace(old_draw_set, new_draw_set, 1)
elif new_draw_set not in noosa_text:
    raise SystemExit("Could not locate NoosaScript.drawQuadSet(FloatBuffer)")

old_get = """\tpublic static NoosaScript get() {
\t\treturn Script.use( NoosaScript.class );
\t}"""
new_get = """\t@Override
\tpublic void delete() {
\t\tif (webVertexBuffer != -1) {
\t\t\tGdx.gl.glDeleteBuffer(webVertexBuffer);
\t\t\twebVertexBuffer = -1;
\t\t}
\t\tif (webIndexBuffer != -1) {
\t\t\tGdx.gl.glDeleteBuffer(webIndexBuffer);
\t\t\twebIndexBuffer = -1;
\t\t}
\t\tsuper.delete();
\t}

\tpublic static NoosaScript get() {
\t\treturn Script.use( NoosaScript.class );
\t}"""
if old_get in noosa_text:
    noosa_text = noosa_text.replace(old_get, new_get, 1)
elif new_get not in noosa_text:
    raise SystemExit("Could not locate NoosaScript.get()")

noosa_script.write_text(noosa_text, encoding="utf-8")
