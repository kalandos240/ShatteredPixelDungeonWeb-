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
}
