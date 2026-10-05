/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import com.badlogic.gdx.Files;
import com.shatteredpixel.shatteredpixeldungeon.ShatteredPixelDungeon;
import com.watabou.noosa.Game;
import com.watabou.utils.FileUtils;

public class WebShatteredPixelDungeon extends ShatteredPixelDungeon {

    private boolean gameReadySent;

    public WebShatteredPixelDungeon() {
        super(new WebPlatformSupport());
    }

    @Override
    public void create() {
        Game.version = "4.0.1-web";
        Game.versionCode = 920;

        // gdx-teavm maps local files to browser-local persistent storage.
        FileUtils.setDefaultFileProperties(Files.FileType.Local, "");

        super.create();
    }

    @Override
    public void render() {
        super.render();

        // Yandex Game Ready must be sent when the game is actually interactive,
        // not merely when the JavaScript bundle has downloaded.
        if (!gameReadySent && Game.scene() != null) {
            gameReadySent = true;
            YandexGamesSdk.gameReady();
        }
    }
}
