# ShatteredPixelDungeonWeb

Web/Yandex Games port of **Shattered Pixel Dungeon**.

This repository is a reproducible browser-port overlay over the official
upstream source. The upstream game stays pinned and auditable while web-only
compatibility changes live here.

## Upstream baseline

- Upstream: `00-Evan/shattered-pixel-dungeon`
- Version: `4.0.1`
- Commit: `e9defd0444c96d2fce3de5ec297c3398be8b7c55`
- License: GPL-3.0-or-later

## Current status

The TeaVM/WebGL port now builds and passes an automated Chromium gameplay
smoke test. CI creates a fresh run, reaches `GameScene`, writes its save to
IndexedDB, reloads the page, restores the same run, and verifies Yandex
pause/resume + Gameplay API behavior.

The Yandex bundle also includes:

- browser FreeType and the required fallback fonts;
- Yandex SDK bootstrap and `LoadingAPI.ready()`;
- automatic first-run language selection from the Yandex environment;
- browser-safe WebGL rendering compatibility patches;
- archive validation against the current Yandex packaging rules.

The current validated archive is roughly 79.5 MB uncompressed, below the
100 MB Yandex Games limit.

## Build flow

```bash
./scripts/prepare-worktree.sh
./scripts/build-yandex.sh
```

The generated upstream worktree lives under `.work/` and is intentionally
not committed. Port-specific source files live in `overlay/`.

For the detailed compatibility history and remaining milestones, see
`docs/PORTING.md`.

## License / modification notice

Shattered Pixel Dungeon is licensed under the GNU GPL v3 or later. This
repository contains web-port modifications made in 2026 and is distributed
under the same license terms. See `LICENSE.txt` and the upstream project for
original copyright notices.
