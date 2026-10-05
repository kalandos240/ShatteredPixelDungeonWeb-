/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import com.badlogic.gdx.Files;
import com.shatteredpixel.shatteredpixeldungeon.SPDSettings;
import com.shatteredpixel.shatteredpixeldungeon.ShatteredPixelDungeon;
import com.shatteredpixel.shatteredpixeldungeon.messages.Languages;
import com.shatteredpixel.shatteredpixeldungeon.scenes.GameScene;
import com.watabou.noosa.Game;
import com.watabou.noosa.audio.Music;
import com.watabou.noosa.audio.Sample;
import com.watabou.utils.FileUtils;
import com.watabou.utils.GameSettings;

import java.util.Locale;

public class WebShatteredPixelDungeon extends ShatteredPixelDungeon {

    private final String platformLanguage;

    private boolean created;
    private boolean platformPaused;
    private boolean gameReadySent;
    private Boolean gameplayActive;

    public WebShatteredPixelDungeon(String platformLanguage) {
        super(new WebPlatformSupport());
        this.platformLanguage = platformLanguage;
    }

    @Override
    public void create() {
        Game.version = "4.0.1-web";
        Game.versionCode = 920;

        // gdx-teavm maps local files to browser-local persistent storage.
        FileUtils.setDefaultFileProperties(Files.FileType.Local, "");

        applyInitialPlatformLanguage();
        super.create();

        created = true;
        if (platformPaused) {
            applyPlatformPause();
        }
    }

    private void applyInitialPlatformLanguage() {
        if (platformLanguage == null || platformLanguage.isEmpty()
                || GameSettings.contains(SPDSettings.KEY_LANG)) {
            return;
        }

        String code = platformLanguage.toLowerCase(Locale.ROOT);
        // Java historically uses "in" for Indonesian while Yandex returns
        // the ISO 639-1 code "id". Shattered's language enum uses "in".
        if ("id".equals(code)) {
            code = "in";
        }

        SPDSettings.language(Languages.matchCode(code));
    }

    public void onYandexPause() {
        if (platformPaused) {
            return;
        }

        platformPaused = true;
        if (created) {
            applyPlatformPause();
        }
        syncGameplayState();
    }

    private void applyPlatformPause() {
        super.pause();
        Music.INSTANCE.pause();
        Sample.INSTANCE.pause();
    }

    public void onYandexResume() {
        if (!platformPaused) {
            return;
        }

        platformPaused = false;
        if (created) {
            super.resume();
            if (SPDSettings.music()) {
                Music.INSTANCE.resume();
            }
            if (SPDSettings.soundFx()) {
                Sample.INSTANCE.resume();
            }
        }
        syncGameplayState();
    }

    @Override
    public void render() {
        if (platformPaused) {
            return;
        }

        super.render();

        // Yandex Game Ready must be sent when the game is actually interactive,
        // not merely when the JavaScript bundle has downloaded.
        if (!gameReadySent && Game.scene() != null) {
            gameReadySent = true;
            YandexGamesSdk.gameReady();
        }

        syncGameplayState();
    }

    private void syncGameplayState() {
        boolean active = created && !platformPaused && Game.scene() instanceof GameScene;
        if (gameplayActive != null && gameplayActive == active) {
            return;
        }

        gameplayActive = active;
        if (active) {
            YandexGamesSdk.gameplayStart();
        } else {
            YandexGamesSdk.gameplayStop();
        }
    }
}
