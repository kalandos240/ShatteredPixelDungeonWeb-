#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/.work/shattered-pixel-dungeon/web/build/yandex"
PORT="${SPD_SMOKE_PORT:-8765}"
DOM_OUT="$ROOT/.work/yandex-smoke-dom.html"
CHROME_LOG="$ROOT/.work/yandex-smoke-chrome.log"

if [[ ! -f "$DIST/index.html" ]]; then
  echo "Missing built Yandex distribution: $DIST" >&2
  exit 1
fi

# The production archive loads /sdk.js from Yandex. For localhost smoke tests,
# provide a minimal SDK-compatible mock after archive validation so the test
# exercises the real Yandex initialization branch without shipping this file.
cat > "$DIST/sdk.js" <<'JS'
(function () {
  const listeners = {};
  const ysdk = {
    environment: { i18n: { lang: "en" } },
    features: {
      LoadingAPI: {
        ready: function () {
          document.documentElement.setAttribute("data-yandex-loading-ready", "true");
        }
      },
      GameplayAPI: {
        start: function () {
          document.documentElement.setAttribute("data-yandex-gameplay", "started");
        },
        stop: function () {
          document.documentElement.setAttribute("data-yandex-gameplay", "stopped");
        }
      }
    },
    on: function (name, callback) {
      listeners[name] = callback;
    }
  };
  window.__spdSmokeYandexListeners = listeners;
  window.YaGames = {
    init: function () {
      return Promise.resolve(ysdk);
    }
  };
})();
JS

BROWSER=""
for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
  if command -v "$candidate" >/dev/null 2>&1; then
    BROWSER="$(command -v "$candidate")"
    break
  fi
done

if [[ -z "$BROWSER" ]]; then
  echo "No Chromium/Chrome executable found for browser smoke test." >&2
  exit 1
fi

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DIST" \
  >"$ROOT/.work/yandex-smoke-http.log" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 50); do
  if curl --silent --fail "http://127.0.0.1:$PORT/index.html" >/dev/null; then
    break
  fi
  sleep 0.1
done

echo "Smoke browser: $("$BROWSER" --version 2>/dev/null || true)"

set +e
timeout 90 "$BROWSER" \
  --headless=new \
  --no-sandbox \
  --disable-dev-shm-usage \
  --no-first-run \
  --no-default-browser-check \
  --autoplay-policy=no-user-gesture-required \
  --enable-unsafe-swiftshader \
  --use-gl=angle \
  --use-angle=swiftshader \
  --virtual-time-budget=30000 \
  --dump-dom "http://127.0.0.1:$PORT/" \
  >"$DOM_OUT" 2>"$CHROME_LOG"
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo "Headless browser exited with status $STATUS" >&2
  tail -200 "$CHROME_LOG" >&2 || true
  exit "$STATUS"
fi

if ! grep -q 'data-spd-game-ready="true"' "$DOM_OUT" \
    || ! grep -q 'data-yandex-loading-ready="true"' "$DOM_OUT"; then
  echo "Browser smoke test did not reach Shattered Pixel Dungeon + Yandex LoadingAPI ready." >&2
  echo "--- Chrome log ---" >&2
  tail -200 "$CHROME_LOG" >&2 || true
  echo "--- DOM tail ---" >&2
  tail -100 "$DOM_OUT" >&2 || true
  exit 1
fi

echo "Browser smoke test reached Game Ready and Yandex LoadingAPI.ready()."
