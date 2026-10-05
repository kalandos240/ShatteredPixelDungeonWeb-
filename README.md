# ShatteredPixelDungeonWeb

Web/Yandex Games port of **Shattered Pixel Dungeon**.

This repository is a reproducible web-port overlay over the official upstream source. The upstream tree stays pinned and auditable while browser/Yandex-specific changes live here.

## Upstream baseline

- Upstream: `00-Evan/shattered-pixel-dungeon`
- Version: `4.0.1`
- Commit: `e9defd0444c96d2fce3de5ec297c3398be8b7c55`
- License: GPL-3.0-or-later
- Derivative build name: **Shattered Pixel Dungeon Web**
- Derivative package id: `com.kalandos240.shatteredpixeldungeonweb`

## Current web port

The current `main` branch builds and runs Shattered Pixel Dungeon in Chromium through
**gdx-teavm 1.6.1** and libGDX **1.14.2**.

Implemented and CI-tested:

- WebGL renderer compatibility for Shattered's legacy Noosa client-buffer paths;
- browser FreeType fonts, including Droid Sans fallback for CJK glyphs;
- TeaVM-compatible runtime reflection used by Shattered's Bundle loading;
- real `GameScene` startup and transition from floor 1 to floor 2;
- TeaVM actor-fiber processing;
- real browser keyboard input through TeaVM/libGDX;
- real browser touch input through TeaVM/libGDX;
- browser-local preferences and IndexedDB save files;
- completed-turn autosaves on web;
- save/reload round-trip after a normal browser refresh;
- Yandex Games SDK initialization;
- `LoadingAPI.ready()` when the game is actually interactive;
- `GameplayAPI.start()/stop()` based on real gameplay state;
- `game_api_pause` / `game_api_resume` handling with game/audio pause;
- first-run language selection from `ysdk.environment.i18n.lang`;
- responsive portrait/landscape canvas sizing;
- Yandex moderation hardening: external navigation is disabled in the web target and supporter/news external entry points are hidden;
- GPL license and corresponding-source notice included in the upload bundle;
- automated archive validation and headless Chrome smoke tests.

The latest validated bundle contains 478 files and is about **79.6 MB uncompressed**, below the current 100 MB Yandex Games archive limit.

## Build

```bash
./scripts/prepare-worktree.sh
./scripts/build-yandex.sh
```

The final archive is written to:

```text
.work/ShatteredPixelDungeonWeb-Yandex.zip
```

The generated upstream worktree lives under `.work/` and is intentionally not committed.

## Browser smoke test

After building:

```bash
./scripts/smoke-yandex.sh
```

The CI smoke test uses a localhost-only Yandex SDK mock and verifies the actual browser pipeline, including WebGL, Game Ready, Russian platform locale, two dungeon floors, save/reload, keyboard input, touch input, pause/resume, and portrait/landscape resizing. The mock SDK is added only after archive validation and is never included in the production ZIP.

## Remaining work

The core browser port is runnable, but this is still an active port. Remaining work includes broader gameplay coverage across items, talents, bosses and special levels; longer-session audio/input testing; production testing inside the real Yandex Games sandbox; and optional platform features such as cloud saves, ads and leaderboards.

## License / source

Shattered Pixel Dungeon is licensed under the GNU GPL v3 or later. This repository contains modified web/Yandex-port code and reproducible build scripts under the same license terms.

The generated Yandex bundle includes `LICENSE.txt` and `SOURCE_CODE.txt`, which identify the pinned upstream revision and the corresponding source repository.
