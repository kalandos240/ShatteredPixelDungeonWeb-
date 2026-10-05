/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import org.teavm.jso.JSBody;
import org.teavm.jso.JSFunctor;
import org.teavm.jso.JSObject;

public final class YandexGamesSdk {

    @JSFunctor
    public interface ReadyCallback extends JSObject {
        void onReady(String languageCode);
    }

    @JSFunctor
    public interface EventCallback extends JSObject {
        void run();
    }

    private YandexGamesSdk() {
    }

    /**
     * Initializes Yandex Games before the libGDX application starts, so
     * environment.i18n.lang is available before Shattered loads messages.
     * Local/non-Yandex hosting falls back to a normal launch.
     */
    @JSBody(params = {"ready"}, script =
            "(function() {" +
            "  if (typeof YaGames === 'undefined') {" +
            "    console.warn('[SPD Web] Yandex Games SDK is unavailable; running without platform services.');" +
            "    ready(null);" +
            "    return;" +
            "  }" +
            "  YaGames.init().then(function(ysdk) {" +
            "    window.__spdYsdk = ysdk;" +
            "    window.__spdYandexPaused = false;" +
            "    ysdk.on('game_api_pause', function() {" +
            "      window.__spdYandexPaused = true;" +
            "      if (window.__spdYandexPauseCb) window.__spdYandexPauseCb();" +
            "    });" +
            "    ysdk.on('game_api_resume', function() {" +
            "      window.__spdYandexPaused = false;" +
            "      if (window.__spdYandexResumeCb) window.__spdYandexResumeCb();" +
            "    });" +
            "    var lang = ysdk.environment && ysdk.environment.i18n" +
            "      ? ysdk.environment.i18n.lang : null;" +
            "    ready(lang || null);" +
            "  }).catch(function(error) {" +
            "    console.error('[SPD Web] YaGames.init() failed', error);" +
            "    ready(null);" +
            "  });" +
            "})();")
    public static native void init(ReadyCallback ready);

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
            "(function() {" +
            "  window.__spdGameReady = true;" +
            "  if (document && document.documentElement) {" +
            "    document.documentElement.setAttribute('data-spd-game-ready', 'true');" +
            "  }" +
            "  var ysdk = window.__spdYsdk;" +
            "  if (!ysdk) {" +
            "    window.__spdPendingGameReady = true;" +
            "    return;" +
            "  }" +
            "  var features = ysdk.features;" +
            "  if (features && features.LoadingAPI && features.LoadingAPI.ready) {" +
            "    features.LoadingAPI.ready();" +
            "  }" +
            "})();")
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
