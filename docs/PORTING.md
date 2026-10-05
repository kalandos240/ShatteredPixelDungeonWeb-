# Web / Yandex Games port notes

## Baseline

The port is pinned to Shattered Pixel Dungeon 4.0.1 at upstream commit
`e9defd0444c96d2fce3de5ec297c3398be8b7c55`.

The browser target uses gdx-teavm 1.6.1 and libGDX 1.14.2. The generated
worktree patches upstream's libGDX version from 1.14.0 to 1.14.2 because that
is the supported pair for gdx-teavm 1.6.1.

## Milestone 0 — bootstrap

Implemented:

- reproducible upstream checkout;
- `:web` TeaVM JavaScript target;
- browser FreeType backend;
- browser controller backend;
- local browser file storage as the default save location;
- Yandex Games SDK initialization;
- `LoadingAPI.ready()` after the first interactive scene exists;
- Yandex-ready static distribution/ZIP.

## Next compatibility passes

1. Compile the complete upstream class graph under TeaVM and fix unsupported
   JVM APIs/reflection registrations.
2. Validate all assets, fonts, music and sound effects in Chromium/Firefox.
3. Validate save/load, rankings and run history against browser-local storage.
4. Add correct gameplay markup at actual GameScene/menu/pause transitions.
5. Add Yandex pause/resume event handling and ad-safe audio pausing.
6. Add optional Yandex cloud saves, leaderboards and ads.
7. Produce a moderation checklist and final upload bundle.

## Deliberate omissions in Milestone 0

`GameplayAPI.start()` and `GameplayAPI.stop()` bridge methods exist but are
not called yet. Sending them at approximate lifecycle events would create
incorrect gameplay markup; they will be wired to real scene transitions in a
later pass.
