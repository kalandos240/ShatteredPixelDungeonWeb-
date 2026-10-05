#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREE="$ROOT/.work/shattered-pixel-dungeon"
DIST="$WORKTREE/web/build/yandex"
ZIP="$ROOT/.work/ShatteredPixelDungeonWeb-Yandex.zip"

if [[ ! -d "$WORKTREE/.git" ]]; then
  bash "$ROOT/scripts/prepare-worktree.sh"
fi

(
  cd "$WORKTREE"
  ./gradlew :web:yandexDist --stacktrace
)

python3 - "$DIST" "$ZIP" <<'PY'
from pathlib import Path
import sys
import zipfile

dist = Path(sys.argv[1])
archive = Path(sys.argv[2])

if not (dist / "index.html").is_file():
    raise SystemExit(f"Yandex distribution is missing index.html: {dist}")

archive.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in sorted(dist.rglob("*")):
        if path.is_file():
            zf.write(path, path.relative_to(dist))

print(f"Yandex bundle: {archive}")
PY

python3 "$ROOT/scripts/validate-yandex.py" "$ZIP"
