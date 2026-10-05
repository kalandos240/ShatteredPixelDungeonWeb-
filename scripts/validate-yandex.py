#!/usr/bin/env python3
from pathlib import Path
import re
import sys
import zipfile

MAX_UNCOMPRESSED_BYTES = 100_000_000
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")

if len(sys.argv) != 2:
    raise SystemExit("usage: validate-yandex.py <bundle.zip>")

archive = Path(sys.argv[1]).resolve()
if not archive.is_file():
    raise SystemExit(f"Bundle does not exist: {archive}")

with zipfile.ZipFile(archive) as zf:
    files = [info for info in zf.infolist() if not info.is_dir()]
    names = [info.filename for info in files]
    total_uncompressed = sum(info.file_size for info in files)

    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise SystemExit(
            f"Uncompressed bundle is too large: {total_uncompressed} bytes "
            f"(limit {MAX_UNCOMPRESSED_BYTES})"
        )

    index_files = [name for name in names if name == "index.html"]
    nested_indexes = [name for name in names if name != "index.html" and name.endswith("/index.html")]
    if len(index_files) != 1 or nested_indexes:
        raise SystemExit(
            "Yandex bundle must contain exactly one index.html at archive root; "
            f"root={len(index_files)}, nested={nested_indexes}"
        )

    bad_names = [
        name for name in names
        if " " in name or CYRILLIC_RE.search(name)
    ]
    if bad_names:
        raise SystemExit(
            "Archive contains file/folder names with spaces or Cyrillic: "
            + ", ".join(bad_names[:20])
        )

    required = {
        "shattered-pixel-dungeon.js",
        "scripts/freetype.js",
        "assets/fonts/pixel_font.ttf",
        "assets/fonts/droid_sans.ttf",
    }
    missing = sorted(required.difference(names))
    if missing:
        raise SystemExit("Missing required web files: " + ", ".join(missing))

    html = zf.read("index.html").decode("utf-8")
    if 'src="/sdk.js"' not in html:
        raise SystemExit("index.html does not load the Yandex Games SDK from /sdk.js")
    if 'id="canvas"' not in html:
        raise SystemExit("index.html does not contain the libGDX canvas")

    js = zf.read("shattered-pixel-dungeon.js").decode("utf-8", errors="ignore")
    sdk_markers = [
        "LoadingAPI",
        "GameplayAPI",
        "game_api_pause",
        "game_api_resume",
        "environment",
        "i18n",
    ]
    missing_markers = [marker for marker in sdk_markers if marker not in js]
    if missing_markers:
        raise SystemExit(
            "Compiled JavaScript is missing expected Yandex integration markers: "
            + ", ".join(missing_markers)
        )

print(
    f"Validated {archive.name}: {len(files)} files, "
    f"{total_uncompressed / 1_000_000:.1f} MB uncompressed"
)
