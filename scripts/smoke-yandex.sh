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

if command -v node >/dev/null 2>&1; then
  node --check "$DIST/shattered-pixel-dungeon.js"
fi

# The production archive loads /sdk.js from Yandex. For localhost smoke tests,
# provide a minimal SDK-compatible mock after archive validation so the test
# exercises the real Yandex initialization branch without shipping this file.
python3 - "$DIST/index.html" <<'PY'
from pathlib import Path
import sys

index = Path(sys.argv[1])
html = index.read_text(encoding="utf-8")
diagnostics = """<script>
function spdSmokeText(value) {
  return String(value == null ? '' : value)
      .replace(/[\r\n\t]+/g, ' ')
      .slice(0, 6000);
}
window.addEventListener('error', function (event) {
  var message = event && event.message ? event.message : 'unknown-error';
  document.documentElement.setAttribute('data-spd-smoke-error', spdSmokeText(message));
  if (event && event.error && event.error.stack) {
    document.documentElement.setAttribute('data-spd-smoke-stack', spdSmokeText(event.error.stack));
  }
});
window.addEventListener('unhandledrejection', function (event) {
  var reason = event && event.reason ? event.reason : 'unknown-rejection';
  document.documentElement.setAttribute('data-spd-smoke-rejection', spdSmokeText(reason));
  if (reason && reason.stack) {
    document.documentElement.setAttribute('data-spd-smoke-stack', spdSmokeText(reason.stack));
  }
});
window.addEventListener('load', function () {
  document.documentElement.setAttribute('data-spd-load-event', 'true');
  setTimeout(function () {
    document.documentElement.setAttribute('data-spd-timeout', 'true');
  }, 100);
  requestAnimationFrame(function () {
    document.documentElement.setAttribute('data-spd-raf', 'true');
  });
});
</script>
"""
html = html.replace("</head>", diagnostics + "</head>", 1)
index.write_text(html, encoding="utf-8")
PY

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
  --disable-background-timer-throttling \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --run-all-compositor-stages-before-draw \
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
  if grep -q 'data-spd-smoke-error=' "$DOM_OUT" || grep -q 'data-spd-smoke-rejection=' "$DOM_OUT"; then
    echo "Captured JavaScript runtime failure:" >&2
    grep -o 'data-spd-smoke-\(error\|rejection\|stack\)="[^"]*"' "$DOM_OUT" >&2 || true
  fi
  echo "--- Chrome log ---" >&2
  tail -200 "$CHROME_LOG" >&2 || true
  echo "--- HTTP log tail ---" >&2
  tail -120 "$ROOT/.work/yandex-smoke-http.log" >&2 || true
  echo "--- DOM tail ---" >&2
  tail -100 "$DOM_OUT" >&2 || true
  exit 1
fi

echo "Browser smoke test reached Game Ready and Yandex LoadingAPI.ready()."
