# Web / Yandex Games port notes

## Baseline

The port is pinned to Shattered Pixel Dungeon 4.0.1 at upstream commit
`e9defd0444c96d2fce3de5ec297c3398be8b7c55`.

The browser target uses gdx-teavm 1.6.1 and libGDX 1.14.2. The generated
worktree patches upstream's libGDX version from 1.14.0 to 1.14.2 because that
is the supported pair for gdx-teavm 1.6.1.

## Working browser milestone

The current CI exercises a real Chromium/WebGL runtime, not only compilation.
It verifies:

- TeaVM JavaScript generation and JavaScript syntax;
- all packaged assets and browser FreeType startup;
- first interactive scene + Yandex `LoadingAPI.ready()`;
- Yandex SDK language propagation;
- a real new Warrior run through level generation into `GameScene`;
- browser-safe Noosa VBO rendering paths;
- local save creation in IndexedDB;
- a full page reload followed by restore of that save back into `GameScene`;
- Yandex `game_api_pause` / `game_api_resume` and Gameplay API state;
- archive shape and the 100 MB uncompressed-size limit.

The latest validated package contains 476 files and is about 79.5 MB
uncompressed.

## Browser compatibility fixes already applied

- libGDX 1.14.2 onscreen-keyboard API adaptation;
- WebGL-safe device detection;
- web FreeType + Droid Sans fallback font;
- manual Unicode block checks where TeaVM regex does not support the desktop
  expressions;
- WebGL VBO paths for Noosa drawing instead of client-side vertex arrays;
- plain JSON Bundle writes on WebGL because TeaVM/JZlib gzip finalization is
  unreliable; Bundle reads remain compatible with both gzip and plain JSON;
- TeaVM reflection metadata limited to class lookup/no-arg construction needed
  by Shattered's Bundle format;
- browser actor-fiber compatibility for font measurement;
- browser-local preferences and save files isolated with dedicated storage
  prefixes.

## Yandex Games integration

Implemented:

- SDK bootstrap through `/sdk.js`;
- `LoadingAPI.ready()`;
- initial language from `ysdk.environment.i18n.lang` when the player has not
  selected a language yet;
- `GameplayAPI.start()` / `stop()` tied to real `GameScene` state;
- `game_api_pause` / `game_api_resume` handling;
- rendering, music and sound pause while the platform pauses the game;
- production ZIP validation for root `index.html`, filenames, required assets
  and uncompressed package size.

The web build intentionally does not install Shattered's native update/news
services, so it does not perform desktop-store update checks or automatic
external news requests.

## Next compatibility passes

1. Validate responsive portrait/landscape resizing and Russian SDK locale in CI.
2. Add deeper gameplay smoke coverage beyond floor 1 (movement, combat and
   floor transition).
3. Decide cloud-save strategy. Yandex Player data is limited, while Shattered
   can have multiple sizable run files; local IndexedDB remains the source of
   truth until a safe sync format is designed.
4. Validate Firefox/Safari-specific behavior where CI infrastructure permits.
5. Decide monetization policy and only then add fullscreen/rewarded ads at safe
   non-gameplay transition points.
6. Produce final moderation checklist and upload bundle.
