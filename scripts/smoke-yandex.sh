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
diagnostics = r"""<script>
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
  try {
    var probeCanvas = document.getElementById('canvas');
    var probeGl = probeCanvas && probeCanvas.getContext('webgl');
    document.documentElement.setAttribute('data-spd-webgl', probeGl ? 'true' : 'false');
  } catch (probeError) {
    document.documentElement.setAttribute('data-spd-webgl', 'error:' + spdSmokeText(probeError));
  }
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
    environment: { i18n: { lang: "ru" } },
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

DRIVER="$(command -v chromedriver || true)"
if [[ -z "$DRIVER" ]]; then
  echo "ChromeDriver is required for the browser readiness smoke test." >&2
  exit 1
fi

echo "Smoke driver: $("$DRIVER" --version 2>/dev/null || true)"

"$DRIVER" --port=9515 --allowed-ips=127.0.0.1 \
  >"$CHROME_LOG" 2>&1 &
DRIVER_PID=$!
trap 'kill "$DRIVER_PID" "$SERVER_PID" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 100); do
  if curl --silent --fail "http://127.0.0.1:9515/status" >/dev/null; then
    break
  fi
  sleep 0.1
done

set +e
python3 "$ROOT/scripts/run-yandex-webdriver.py" \
  "http://127.0.0.1:9515" \
  "$BROWSER" \
  "http://127.0.0.1:$PORT/?spd-smoke=1" \
  "$DOM_OUT"
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo "Browser smoke test failed with status $STATUS." >&2
  echo "--- ChromeDriver log ---" >&2
  tail -200 "$CHROME_LOG" >&2 || true
  echo "--- HTTP log tail ---" >&2
  tail -160 "$ROOT/.work/yandex-smoke-http.log" >&2 || true
  if [[ -f "$DOM_OUT" ]]; then
    echo "--- DOM tail ---" >&2
    tail -100 "$DOM_OUT" >&2 || true
  fi
  exit "$STATUS"
fi

echo "Browser smoke test reached Game Ready and Yandex LoadingAPI.ready()."
