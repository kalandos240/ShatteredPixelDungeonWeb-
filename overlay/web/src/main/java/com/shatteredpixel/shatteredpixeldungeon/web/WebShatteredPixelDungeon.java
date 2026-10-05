/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import com.badlogic.gdx.Files;
import com.shatteredpixel.shatteredpixeldungeon.Dungeon;
import com.shatteredpixel.shatteredpixeldungeon.GamesInProgress;
import com.shatteredpixel.shatteredpixeldungeon.SPDSettings;
import com.shatteredpixel.shatteredpixeldungeon.ShatteredPixelDungeon;
import com.shatteredpixel.shatteredpixeldungeon.actors.hero.HeroClass;
import com.shatteredpixel.shatteredpixeldungeon.messages.Languages;
import com.shatteredpixel.shatteredpixeldungeon.levels.features.LevelTransition;
import com.shatteredpixel.shatteredpixeldungeon.scenes.GameScene;
import com.shatteredpixel.shatteredpixeldungeon.scenes.InterlevelScene;
import com.shatteredpixel.shatteredpixeldungeon.ui.ActionIndicator;
import com.watabou.noosa.Game;
import com.watabou.noosa.audio.Music;
import com.watabou.noosa.audio.Sample;
import com.watabou.utils.FileUtils;
import com.watabou.utils.GameSettings;
import org.teavm.jso.JSBody;

import java.util.Locale;

public class WebShatteredPixelDungeon extends ShatteredPixelDungeon {

    private final String platformLanguage;
    private final boolean smokeMode = isLocalSmokeMode();

    private boolean created;
    private boolean smokeRunStarted;
    private boolean smokeLoadedExisting;
    private int smokeReportedDepth = -1;
    private boolean smokeAdvanceConsumed;
    private boolean platformPaused;
    private boolean gameReadySent;
    private Boolean gameplayActive;

    public WebShatteredPixelDungeon(String platformLanguage) {
        super(new WebPlatformSupport());
        this.platformLanguage = platformLanguage;
    }

    @Override
    public void create() {
        Game.version = smokeMode ? "4.0.1-web-INDEV" : "4.0.1-web";
        Game.versionCode = 920;

        // gdx-teavm maps local files to browser-local persistent storage.
        FileUtils.setDefaultFileProperties(Files.FileType.Local, "");

        applyInitialPlatformLanguage();
        if (smokeMode) {
            YandexGamesSdk.smokeLanguage(SPDSettings.language().code());
        }
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

        if (smokeMode && gameReadySent && !smokeRunStarted) {
            startSmokeRun();
        }

        syncGameplayState();
        if (smokeMode && Game.scene() != null) {
            YandexGamesSdk.smokeScene(Game.scene().getClass().getName());
        }
        reportSmokeGameState();
        maybeAdvanceSmokeFloor();
    }

    private void startSmokeRun() {
        smokeRunStarted = true;
        GamesInProgress.curSlot = 1;
        Dungeon.hero = null;
        Dungeon.daily = false;
        Dungeon.dailyReplay = false;

        smokeLoadedExisting = GamesInProgress.gameExists(GamesInProgress.curSlot);
        if (smokeLoadedExisting) {
            GamesInProgress.setUnknown(GamesInProgress.curSlot);
            InterlevelScene.mode = InterlevelScene.Mode.CONTINUE;
        } else {
            GamesInProgress.selectedClass = HeroClass.WARRIOR;
            Dungeon.initSeed();
            ActionIndicator.clearAction();
            InterlevelScene.mode = InterlevelScene.Mode.DESCEND;
        }

        Game.switchScene(InterlevelScene.class);
    }

    private void reportSmokeGameState() {
        if (!smokeMode || !(Game.scene() instanceof GameScene)
                || smokeReportedDepth == Dungeon.depth) {
            return;
        }

        boolean saveReady = GamesInProgress.gameExists(GamesInProgress.curSlot);
        if (saveReady) {
            smokeReportedDepth = Dungeon.depth;
            YandexGamesSdk.smokeGameSceneReady(smokeLoadedExisting, true, Dungeon.depth);
        }
    }

    private void maybeAdvanceSmokeFloor() {
        if (!smokeMode || smokeAdvanceConsumed || smokeLoadedExisting
                || !(Game.scene() instanceof GameScene)
                || Dungeon.depth != 1 || !YandexGamesSdk.smokeAdvanceRequested()) {
            return;
        }

        LevelTransition exit = Dungeon.level.getTransition(LevelTransition.Type.REGULAR_EXIT);
        if (exit == null) {
            throw new IllegalStateException("Smoke test could not find the floor 1 exit");
        }

        smokeAdvanceConsumed = true;
        if (!Dungeon.level.activateTransition(Dungeon.hero, exit)) {
            throw new IllegalStateException("Smoke test could not activate the floor 1 exit");
        }
    }

    @JSBody(script =
            "return window.location && window.location.hostname === '127.0.0.1'" +
            "  && new URLSearchParams(window.location.search).get('spd-smoke') === '1';")
    private static native boolean isLocalSmokeMode();

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
