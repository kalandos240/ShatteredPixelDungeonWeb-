/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import org.teavm.jso.JSBody;

public final class YandexGamesSdk {

    private YandexGamesSdk() {
    }

    @JSBody(script =
            "(function() {" +
            "  if (window.__spdYandexInitStarted) return;" +
            "  window.__spdYandexInitStarted = true;" +
            "  if (typeof YaGames === 'undefined') {" +
            "    console.warn('[SPD Web] Yandex Games SDK is unavailable; running without platform services.');" +
            "    return;" +
            "  }" +
            "  YaGames.init().then(function(ysdk) {" +
            "    window.__spdYsdk = ysdk;" +
            "    if (window.__spdPendingGameReady) {" +
            "      window.__spdPendingGameReady = false;" +
            "      var features = ysdk.features;" +
            "      if (features && features.LoadingAPI && features.LoadingAPI.ready) {" +
            "        features.LoadingAPI.ready();" +
            "      }" +
            "    }" +
            "  }).catch(function(error) {" +
            "    console.error('[SPD Web] YaGames.init() failed', error);" +
            "  });" +
            "})();")
    public static native void init();

    @JSBody(script =
            "(function() {" +
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
