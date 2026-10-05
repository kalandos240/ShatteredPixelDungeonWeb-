/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import org.teavm.jso.JSBody;
import org.teavm.jso.JSFunctor;
import org.teavm.jso.JSObject;
import org.teavm.jso.core.JSPromise;
import org.teavm.jso.core.JSString;

public final class YandexGamesSdk {

    @JSFunctor
    public interface EventCallback extends JSObject {
        void run();
    }

    private YandexGamesSdk() {
    }

    /**
     * Waits for Yandex Games inside TeaVM's own async/fiber machinery. This is
     * important because constructing WebApplication can itself suspend; doing
     * that work directly from a raw Promise callback loses TeaVM's Java thread
     * context.
     */
    public static String init() {
        JSString language = initPromise().await();
        return language == null ? null : language.stringValue();
    }

    @JSBody(script =
            "if (typeof YaGames === 'undefined') {" +
            "  console.warn('[SPD Web] Yandex Games SDK is unavailable; running without platform services.');" +
            "  return Promise.resolve(null);" +
            "}" +
            "return YaGames.init().then(function(ysdk) {" +
            "  window.__spdYsdk = ysdk;" +
            "  window.__spdYandexPaused = false;" +
            "  ysdk.on('game_api_pause', function() {" +
            "    window.__spdYandexPaused = true;" +
            "    if (window.__spdYandexPauseCb) window.__spdYandexPauseCb();" +
            "  });" +
            "  ysdk.on('game_api_resume', function() {" +
            "    window.__spdYandexPaused = false;" +
            "    if (window.__spdYandexResumeCb) window.__spdYandexResumeCb();" +
            "  });" +
            "  var lang = ysdk.environment && ysdk.environment.i18n" +
            "    ? ysdk.environment.i18n.lang : null;" +
            "  return lang || null;" +
            "}, function(error) {" +
            "  console.error('[SPD Web] YaGames.init() failed', error);" +
            "  return null;" +
            "});")
    private static native JSPromise<JSString> initPromise();

    /**
     * Binds Java-side pause/resume handling after the libGDX app exists.
     * If a startup ad paused the platform before binding, replay that pause.
     */
    @JSBody(params = {"pause", "resume"}, script =
            "window.__spdYandexPauseCb = pause;" +
            "window.__spdYandexResumeCb = resume;" +
            "if (window.__spdYandexPaused && pause) pause();")
    public static native void bindLifecycle(EventCallback pause, EventCallback resume);

    @JSBody(script =
            "window.__spdGameReady = true;" +
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-game-ready', 'true');" +
            "}" +
            "var ysdk = window.__spdYsdk;" +
            "if (!ysdk) {" +
            "  window.__spdPendingGameReady = true;" +
            "  return;" +
            "}" +
            "var features = ysdk.features;" +
            "if (features && features.LoadingAPI && features.LoadingAPI.ready) {" +
            "  features.LoadingAPI.ready();" +
            "}")
    public static native void gameReady();

    @JSBody(script =
            "var ysdk = window.__spdYsdk;" +
            "if (ysdk && ysdk.features && ysdk.features.GameplayAPI && ysdk.features.GameplayAPI.start) {" +
            "  ysdk.features.GameplayAPI.start();" +
            "}")
    public static native void gameplayStart();

    @JSBody(script =
            "var ysdk = window.__spdYsdk;" +
            "if (ysdk && ysdk.features && ysdk.features.GameplayAPI && ysdk.features.GameplayAPI.stop) {" +
            "  ysdk.features.GameplayAPI.stop();" +
            "}")
    public static native void gameplayStop();

    @JSBody(params = {"loadedExisting", "saveReady", "depth"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-save-ready', saveReady ? 'true' : 'false');" +
            "  document.documentElement.setAttribute('data-spd-smoke-loaded', loadedExisting ? 'true' : 'false');" +
            "  document.documentElement.setAttribute('data-spd-smoke-depth', String(depth));" +
            "}")
    public static native void smokeGameSceneReady(boolean loadedExisting, boolean saveReady, int depth);

    @JSBody(script =
            "return window.__spdSmokeAdvance === true;")
    public static native boolean smokeAdvanceRequested();

    @JSBody(script =
            "return window.__spdSmokeMove === true;")
    public static native boolean smokeMoveRequested();

    @JSBody(params = {"position", "ready"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-smoke-hero-pos', String(position));" +
            "  document.documentElement.setAttribute('data-spd-smoke-hero-ready', ready ? 'true' : 'false');" +
            "}")
    public static native void smokeHeroState(int position, boolean ready);

    @JSBody(params = {"heroPos"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-smoke-turn-saved', String(heroPos));" +
            "}")
    public static native void smokeTurnSaved(int heroPos);

    @JSBody(params = {"key"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-smoke-key', key || 'unknown');" +
            "}")
    public static native void smokeKeyboardTarget(String key);

    @JSBody(params = {"x", "y"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-smoke-touch-x', String(x));" +
            "  document.documentElement.setAttribute('data-spd-smoke-touch-y', String(y));" +
            "}")
    public static native void smokeTouchTarget(int x, int y);

    @JSBody(params = {"sceneName"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-smoke-scene', sceneName || 'unknown');" +
            "}")
    public static native void smokeScene(String sceneName);

    @JSBody(params = {"language"}, script =
            "if (document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-smoke-language', language || 'unknown');" +
            "}")
    public static native void smokeLanguage(String language);

    @JSBody(params = {"message"}, script =
            "if (window.location && window.location.hostname === '127.0.0.1'" +
            "    && new URLSearchParams(window.location.search).get('spd-smoke') === '1'" +
            "    && document && document.documentElement) {" +
            "  document.documentElement.setAttribute('data-spd-java-fatal', message || 'unknown Java error');" +
            "}")
    public static native void smokeFatalError(String message);
}
