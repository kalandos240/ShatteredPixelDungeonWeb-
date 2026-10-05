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


# TeaVM 0.15.0's JZlib-backed Deflater can return Z_BUF_ERROR (-5) while
# finishing Shattered's GZIP save stream. Bundle.read already supports both
# gzip and plain JSON, so write plain JSON only on WebGL and preserve gzip on
# every native backend.
bundle = root / "SPD-classes/src/main/java/com/watabou/utils/Bundle.java"
bundle_text = bundle.read_text(encoding="utf-8")
bundle_text = bundle_text.replace(
    "package com.watabou.utils;\n\nimport com.watabou.noosa.Game;",
    "package com.watabou.utils;\n\nimport com.badlogic.gdx.Application;\nimport com.badlogic.gdx.Gdx;\nimport com.watabou.noosa.Game;"
)
old_bundle_write = """\tpublic static boolean write( Bundle bundle, OutputStream stream ){
\t\treturn write(bundle, stream, compressByDefault);
\t}"""
new_bundle_write = """\tpublic static boolean write( Bundle bundle, OutputStream stream ){
\t\tboolean compress = compressByDefault;
\t\tif (Gdx.app != null && Gdx.app.getType() == Application.ApplicationType.WebGL) {
\t\t\tcompress = false;
\t\t}
\t\treturn write(bundle, stream, compress);
\t}"""
if old_bundle_write in bundle_text:
    bundle_text = bundle_text.replace(old_bundle_write, new_bundle_write, 1)
elif new_bundle_write not in bundle_text:
    raise SystemExit("Could not locate Bundle.write default compression path")
bundle.write_text(bundle_text, encoding="utf-8")


# Native Shattered forbids font measurement on its real actor OS thread because
# font generation touches graphics state owned by the render thread. TeaVM's
# JavaScript threads are cooperative fibers on the browser event loop, so this
# native-thread guard produces false positives after restoring a run.
rendered_text = root / "SPD-classes/src/main/java/com/watabou/noosa/RenderedText.java"
rendered_text_source = rendered_text.read_text(encoding="utf-8")
rendered_text_source = rendered_text_source.replace(
    "import com.badlogic.gdx.graphics.Color;",
    "import com.badlogic.gdx.Application;\nimport com.badlogic.gdx.Gdx;\nimport com.badlogic.gdx.graphics.Color;",
    1
)
old_actor_guard = """\t\tif (Thread.currentThread().getName().equals("SHPD Actor Thread")){
\t\t\tthrow new RuntimeException("Text measured from the actor thread!");
\t\t}"""
new_actor_guard = """\t\tif (Gdx.app.getType() != Application.ApplicationType.WebGL
\t\t\t\t&& Thread.currentThread().getName().equals("SHPD Actor Thread")){
\t\t\tthrow new RuntimeException("Text measured from the actor thread!");
\t\t}"""
if old_actor_guard in rendered_text_source:
    rendered_text_source = rendered_text_source.replace(old_actor_guard, new_actor_guard, 1)
elif new_actor_guard not in rendered_text_source:
    raise SystemExit("Could not locate RenderedText actor-thread guard")
rendered_text.write_text(rendered_text_source, encoding="utf-8")


# GameScene coordinates a real actor OS thread with Thread.wait()/notify() on
# native platforms. TeaVM models Java threads as cooperative browser fibers.
# Calling Thread.wait() while GameScene is being destroyed from the browser
# requestAnimationFrame callback hits "Suspension point reached from
# non-threading context". Browser JavaScript is single-threaded here, so an
# interrupt is enough to stop/reschedule the actor fiber; never block the
# render callback waiting for it.
game_scene = root / "core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/scenes/GameScene.java"
game_scene_text = game_scene.read_text(encoding="utf-8")
old_wait_for_actor = """\tpublic boolean waitForActorThread(int msToWait, boolean interrupt){
\t\tif (actorThread == null || !actorThread.isAlive()) {
\t\t\treturn true;
\t\t}
\t\tsynchronized (actorThread) {
\t\t\tif (interrupt) actorThread.interrupt();
\t\t\ttry {
\t\t\t\tactorThread.wait(msToWait);
\t\t\t} catch (InterruptedException e) {
\t\t\t\tShatteredPixelDungeon.reportException(e);
\t\t\t}
\t\t\treturn !Actor.processing();
\t\t}
\t}"""
new_wait_for_actor = """\tpublic boolean waitForActorThread(int msToWait, boolean interrupt){
\t\tif (actorThread == null || !actorThread.isAlive()) {
\t\t\treturn true;
\t\t}

\t\tif (com.badlogic.gdx.Gdx.app.getType() == com.badlogic.gdx.Application.ApplicationType.WebGL) {
\t\t\tif (interrupt) actorThread.interrupt();
\t\t\treturn true;
\t\t}

\t\tsynchronized (actorThread) {
\t\t\tif (interrupt) actorThread.interrupt();
\t\t\ttry {
\t\t\t\tactorThread.wait(msToWait);
\t\t\t} catch (InterruptedException e) {
\t\t\t\tShatteredPixelDungeon.reportException(e);
\t\t\t}
\t\t\treturn !Actor.processing();
\t\t}
\t}"""

if old_wait_for_actor in game_scene_text:
    game_scene_text = game_scene_text.replace(old_wait_for_actor, new_wait_for_actor, 1)
elif new_wait_for_actor not in game_scene_text:
    raise SystemExit("Could not locate GameScene actor-thread wait block")
game_scene.write_text(game_scene_text, encoding="utf-8")
