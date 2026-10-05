/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import com.github.xpenatan.gdx.teavm.backends.web.WebApplication;
import com.github.xpenatan.gdx.teavm.backends.web.WebApplicationConfiguration;

public final class WebLauncher {

    private WebLauncher() {
    }

    public static void main(String[] args) {
        launch(YandexGamesSdk.init());
    }

    private static void launch(String languageCode) {
        WebApplicationConfiguration config = new WebApplicationConfiguration("canvas");
        config.width = 0;
        config.height = 0;
        config.showDownloadLogs = false;

        // Keep Shattered's settings and IndexedDB save files isolated from
        // other web apps that may share the same origin.
        config.storagePrefix = "shattered-pixel-dungeon";
        config.localStoragePrefix = "shattered-pixel-dungeon-files";

        // gdx-freetype-web resolves scripts relative to its scripts/ folder.
        config.preloadListener = assetLoader -> assetLoader.loadScript("freetype.js");

        WebShatteredPixelDungeon game = new WebShatteredPixelDungeon(languageCode);
        new WebApplication(game, config) {
            @Override
            protected void onError(Throwable error) {
                YandexGamesSdk.smokeFatalError(error == null ? "unknown Java error" : error.toString());
                super.onError(error);
            }
        };

        YandexGamesSdk.bindLifecycle(game::onYandexPause, game::onYandexResume);
    }
}
