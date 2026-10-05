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
        YandexGamesSdk.init();

        WebApplicationConfiguration config = new WebApplicationConfiguration("canvas");
        config.width = 0;
        config.height = 0;
        config.showDownloadLogs = false;

        // gdx-freetype-web ships its browser runtime as this support script.
        config.preloadListener = assetLoader -> assetLoader.loadScript("freetype.js");

        new WebApplication(new WebShatteredPixelDungeon(), config);
    }
}
