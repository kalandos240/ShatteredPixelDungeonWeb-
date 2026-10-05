# ShatteredPixelDungeonWeb

Web/Yandex Games port of **Shattered Pixel Dungeon**.

This repository is being built as a reproducible port overlay over the official upstream source so the browser-specific code can evolve independently while upstream stays pinned and auditable.

## Upstream baseline

- Upstream: `00-Evan/shattered-pixel-dungeon`
- Version: `4.0.1`
- Commit: `e9defd0444c96d2fce3de5ec297c3398be8b7c55`
- License: GPL-3.0-or-later

## Current port milestone

The first milestone establishes:

- reproducible checkout of the pinned upstream source;
- a libGDX browser target through **gdx-teavm**;
- browser FreeType/controller backends;
- browser-local save/preferences plumbing;
- Yandex Games SDK bootstrap and `LoadingAPI.ready()` signalling;
- a build task that produces a Yandex-ready static bundle.

The browser port uses libGDX 1.14.2 together with gdx-teavm 1.6.1. The upstream project currently uses libGDX 1.14.0, so the preparation script applies the small version bump only inside the generated worktree.

## Build flow

```bash
./scripts/prepare-worktree.sh
./scripts/build-yandex.sh
```

The generated upstream worktree lives under `.work/` and is intentionally not committed. Port-specific source files live in `overlay/`.

## Status

This is an active port. The initial target is a compiling/runnable title/menu build in a browser; save compatibility, audio, input edge-cases, ads, cloud saves, leaderboards and production moderation integration are handled as subsequent milestones.

## License / modification notice

Shattered Pixel Dungeon is licensed under the GNU GPL v3 or later. This repository contains web-port modifications made in 2026 and is distributed under the same license terms. See `LICENSE.txt` and the upstream project for original copyright notices.
