#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_URL="https://github.com/00-Evan/shattered-pixel-dungeon.git"
UPSTREAM_COMMIT="e9defd0444c96d2fce3de5ec297c3398be8b7c55"
WORK_ROOT="$ROOT/.work"
WORKTREE="$WORK_ROOT/shattered-pixel-dungeon"

mkdir -p "$WORK_ROOT"

if [[ ! -d "$WORKTREE/.git" ]]; then
  rm -rf "$WORKTREE"
  git clone --filter=blob:none --no-checkout "$UPSTREAM_URL" "$WORKTREE"
fi

git -C "$WORKTREE" fetch --depth 1 origin "$UPSTREAM_COMMIT"
git -C "$WORKTREE" reset --hard "$UPSTREAM_COMMIT"
git -C "$WORKTREE" clean -fdx

cp -a "$ROOT/overlay/." "$WORKTREE/"
python3 "$ROOT/scripts/patch-upstream.py" "$WORKTREE"

printf 'Prepared Shattered Pixel Dungeon web worktree at %s\n' "$WORKTREE"
