# Web / Yandex Games port status

## Baseline

The port is pinned to Shattered Pixel Dungeon 4.0.1 at upstream commit
`e9defd0444c96d2fce3de5ec297c3398be8b7c55`.

The browser target uses gdx-teavm 1.6.1 and libGDX 1.14.2. The generated
worktree patches upstream libGDX 1.14.0 to 1.14.2 because that is the supported
pair for the selected gdx-teavm release.

The generated derivative build is named **Shattered Pixel Dungeon Web** with
package id `com.kalandos240.shatteredpixeldungeonweb`.

## Implemented browser compatibility

### Rendering

Shattered's Noosa renderer contains native OpenGL paths which pass Java
`FloatBuffer` / `ShortBuffer` objects directly to vertex attribute and
indexed draw calls. WebGL does not support those client-side arrays.

The web worktree patch converts those paths to reusable VBO/EBO uploads on the
WebGL backend while leaving native behavior unchanged.

The TextInput SpriteBatch workaround is likewise switched from
`VertexArray` to `VertexBufferObject` only on WebGL.

### Fonts

The web module uses `gdx-freetype-web`. Shattered's Droid Sans CJK fallback
font normally lives in the desktop assets, so the preparation script copies it
into the generated core web assets.

### JVM / TeaVM compatibility

Implemented compatibility fixes include:

- libGDX 1.14.2 `TextField.OnscreenKeyboard` API changes;
- `ApplicationType` device detection in place of `SharedLibraryLoader.os`;
- a lightweight TeaVM `ReflectionSupplier` which preserves runtime class-name
  lookup and no-argument construction without registering all game methods and
  fields;
- WebGL save files written as plain Bundle JSON because TeaVM's JZlib
  `Deflater` fails while finalizing Shattered's GZIP stream;
- cooperative TeaVM actor-fiber handling without native `Thread.wait()` from
  the browser RAF callback;
- browser-safe font measurement from TeaVM actor fibers.

## Saving

Preferences are namespaced under `shattered-pixel-dungeon`.

Local game files are stored by gdx-teavm in IndexedDB under
`shattered-pixel-dungeon-files`.

Shattered normally performs authoritative saves at level transitions and
pause points. For the browser target, completed hero turns additionally trigger
`Dungeon.saveAll()`. This starts persistence early enough that an ordinary
browser refresh after a completed action restores the newest state instead of
the previous checkpoint.

The CI browser test currently proves:

1. start a deterministic new Warrior run;
2. load floor 1;
3. transition normally to floor 2;
4. move the hero through the TeaVM actor fiber;
5. observe the completed-turn autosave;
6. refresh the page without injecting a synthetic pause;
7. restore the same floor and hero tile from IndexedDB.

## Yandex Games integration

Implemented:

- `/sdk.js` in the production `index.html`;
- `YaGames.init()` before Shattered message initialization;
- platform language from `ysdk.environment.i18n.lang` on first launch;
- preservation of a player's manually selected language afterward;
- Indonesian `id` → Shattered's historical `in` language-code mapping;
- `LoadingAPI.ready()` only after an interactive scene exists;
- `GameplayAPI.start()` while `GameScene` is active;
- `GameplayAPI.stop()` outside gameplay and while platform-paused;
- `game_api_pause` and `game_api_resume` handling;
- music/SFX pause and resume around platform interruption;
- rendering stopped while Yandex has the game paused.

External navigation is disabled on the web platform. Support/news external
entry points are hidden, About keeps the upstream credits but removes clickable
external-domain labels on WebGL, the Goo supporter nag is disabled, and the
victory supporter CTA is removed from the Yandex target.

## Automated browser coverage

`scripts/smoke-yandex.sh` starts the built game under ChromeDriver with a
localhost-only mock Yandex SDK. The mock is created only after production ZIP
validation and is not packaged.

The current smoke test verifies:

- generated JavaScript parses successfully;
- WebGL initialization;
- `LoadingAPI.ready()`;
- Russian platform locale is applied;
- first `GameScene` on floor 1;
- normal transition to floor 2;
- actor-fiber movement;
- completed-turn autosave;
- IndexedDB save restore after refresh;
- real W3C keyboard input -> DOM -> gdx-teavm WebInput -> Shattered controls;
- real W3C touch pointer -> DOM -> gdx-teavm WebInput -> CellSelector;
- Yandex pause/resume and Gameplay API state;
- canvas equals the actual browser inner viewport;
- portrait and landscape resize while remaining in `GameScene`;
- no uncaught JavaScript rejection or surfaced TeaVM fatal error.

The latest successful run validated a 478-file bundle of roughly 79.6 MB
uncompressed.

## Archive validation

`scripts/validate-yandex.py` checks the release ZIP for:

- one root `index.html`;
- no spaces/Cyrillic in archive paths;
- uncompressed size <= 100 MB;
- Yandex SDK injection;
- main TeaVM JavaScript bundle;
- FreeType runtime;
- required fonts;
- `LICENSE.txt`;
- `SOURCE_CODE.txt`;
- expected Yandex integration markers in compiled JavaScript.

## Remaining compatibility work

The first playable browser vertical slice is complete, but broader game
coverage is still needed:

1. longer runs across regions, bosses, quests, special levels and challenges;
2. inventory, alchemy, text input and settings interaction coverage;
3. music/SFX behavior on multiple desktop and mobile browsers;
4. testing in the real Yandex Games draft/sandbox environment;
5. cloud-save feasibility and conflict policy;
6. optional monetization/leaderboards;
7. final store branding assets, screenshots and moderation checklist.

Cloud Player Data is not yet enabled. Yandex limits `player.setData()` to
200 KB of player data and rate-limits writes, so full Shattered saves must be
measured/compressed and checkpointed rather than uploaded every turn.
