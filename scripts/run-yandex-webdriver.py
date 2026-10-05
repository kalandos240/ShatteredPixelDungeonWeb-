#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

if len(sys.argv) != 5:
    raise SystemExit(
        "usage: run-yandex-webdriver.py <webdriver-url> <browser-binary> <game-url> <dom-out>"
    )

webdriver = sys.argv[1].rstrip("/")
browser = sys.argv[2]
game_url = sys.argv[3]
dom_out = Path(sys.argv[4])


def call(method: str, path: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webdriver + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"WebDriver {method} {path} failed: {error.code} {body}") from error


session_id = None
last_state = {}
try:
    created = call(
        "POST",
        "/session",
        {
            "capabilities": {
                "alwaysMatch": {
                    "browserName": "chrome",
                    "pageLoadStrategy": "eager",
                    "goog:chromeOptions": {
                        "binary": browser,
                        "args": [
                            "--headless=new",
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--no-first-run",
                            "--no-default-browser-check",
                            "--autoplay-policy=no-user-gesture-required",
                            "--disable-background-timer-throttling",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding",
                            "--enable-unsafe-swiftshader",
                            "--use-gl=angle",
                            "--use-angle=swiftshader",
                            "--window-size=1280,720",
                        ],
                    },
                }
            }
        },
    )
    session_id = created["value"]["sessionId"]

    call(
        "POST",
        f"/session/{session_id}/timeouts",
        {"pageLoad": 60000, "script": 30000, "implicit": 0},
    )
    call("POST", f"/session/{session_id}/url", {"url": game_url})

    state_script = r"""
const root = document.documentElement;
const canvas = document.getElementById('canvas');
return {
  ready: root && root.getAttribute('data-spd-game-ready'),
  yandexReady: root && root.getAttribute('data-yandex-loading-ready'),
  gameplay: root && root.getAttribute('data-yandex-gameplay'),
  webgl: root && root.getAttribute('data-spd-webgl'),
  error: root && root.getAttribute('data-spd-smoke-error'),
  rejection: root && root.getAttribute('data-spd-smoke-rejection'),
  stack: root && root.getAttribute('data-spd-smoke-stack'),
  loadEvent: root && root.getAttribute('data-spd-load-event'),
  raf: root && root.getAttribute('data-spd-raf'),
  readyState: document.readyState,
  canvasWidth: canvas ? canvas.width : 0,
  canvasHeight: canvas ? canvas.height : 0,
  saveReady: root && root.getAttribute('data-spd-save-ready'),
  smokeLoaded: root && root.getAttribute('data-spd-smoke-loaded'),
  scene: root && root.getAttribute('data-spd-smoke-scene'),
  javaFatal: root && root.getAttribute('data-spd-java-fatal'),
  language: root && root.getAttribute('data-spd-smoke-language')
};
"""

    def wait_for_state(label, predicate, timeout=120):
        global last_state
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                last_state = call(
                    "POST",
                    f"/session/{session_id}/execute/sync",
                    {"script": state_script, "args": []},
                )["value"]
            except Exception as error:
                last_state = {"webdriverError": str(error)}

            if last_state.get("error") or last_state.get("rejection") or last_state.get("javaFatal"):
                raise RuntimeError(
                    "Browser runtime failure: "
                    + json.dumps(last_state, ensure_ascii=False, sort_keys=True)
                )

            if predicate(last_state):
                print(
                    f"Browser smoke state ({label}): "
                    + json.dumps(last_state, ensure_ascii=False, sort_keys=True)
                )
                return

            time.sleep(0.5)

        raise RuntimeError(
            f"Timed out waiting for {label}: "
            + json.dumps(last_state, ensure_ascii=False, sort_keys=True)
        )

    wait_for_state(
        "first GameScene + save",
        lambda state: (
            state.get("ready") == "true"
            and state.get("yandexReady") == "true"
            and state.get("gameplay") == "started"
            and state.get("saveReady") == "true"
            and state.get("smokeLoaded") == "false"
            and state.get("language") == "ru"
        ),
    )

    # Reload the same origin. gdx-teavm rehydrates local files from IndexedDB
    # before the application listener starts, so smoke mode must now choose
    # CONTINUE and restore the serialized run instead of creating a new one.
    call("POST", f"/session/{session_id}/refresh", {})
    wait_for_state(
        "reloaded GameScene from IndexedDB save",
        lambda state: (
            state.get("ready") == "true"
            and state.get("yandexReady") == "true"
            and state.get("gameplay") == "started"
            and state.get("saveReady") == "true"
            and state.get("smokeLoaded") == "true"
        ),
    )

    # Exercise the same Yandex pause/resume events used around ads and platform
    # interruptions. A paused game must stop GameplayAPI and resume it again.
    call(
        "POST",
        f"/session/{session_id}/execute/sync",
        {
            "script": """
                var fn = window.__spdSmokeYandexListeners
                    && window.__spdSmokeYandexListeners['game_api_pause'];
                if (!fn) throw new Error('missing game_api_pause listener');
                fn();
                return true;
            """,
            "args": [],
        },
    )
    wait_for_state(
        "Yandex game_api_pause",
        lambda state: state.get("gameplay") == "stopped",
        timeout=30,
    )

    call(
        "POST",
        f"/session/{session_id}/execute/sync",
        {
            "script": """
                var fn = window.__spdSmokeYandexListeners
                    && window.__spdSmokeYandexListeners['game_api_resume'];
                if (!fn) throw new Error('missing game_api_resume listener');
                fn();
                return true;
            """,
            "args": [],
        },
    )
    wait_for_state(
        "Yandex game_api_resume",
        lambda state: (
            state.get("gameplay") == "started"
            and state.get("scene") == "com.shatteredpixel.shatteredpixeldungeon.scenes.GameScene"
        ),
        timeout=30,
    )

    # Exercise responsive layout at phone-like portrait and landscape sizes.
    # This catches scene resets/font relayout bugs which are invisible in the
    # default desktop viewport but matter for Yandex mobile distribution.
    call(
        "POST",
        f"/session/{session_id}/window/rect",
        {"width": 430, "height": 900},
    )
    wait_for_state(
        "mobile portrait resize",
        lambda state: (
            state.get("gameplay") == "started"
            and state.get("scene") == "com.shatteredpixel.shatteredpixeldungeon.scenes.GameScene"
            and int(state.get("canvasHeight") or 0) > int(state.get("canvasWidth") or 0)
        ),
        timeout=30,
    )

    call(
        "POST",
        f"/session/{session_id}/window/rect",
        {"width": 900, "height": 430},
    )
    wait_for_state(
        "mobile landscape resize",
        lambda state: (
            state.get("gameplay") == "started"
            and state.get("scene") == "com.shatteredpixel.shatteredpixeldungeon.scenes.GameScene"
            and int(state.get("canvasWidth") or 0) > int(state.get("canvasHeight") or 0)
        ),
        timeout=30,
    )

finally:
    if session_id is not None:
        try:
            html = call(
                "POST",
                f"/session/{session_id}/execute/sync",
                {"script": "return document.documentElement.outerHTML;", "args": []},
            ).get("value", "")
            dom_out.write_text(html or "", encoding="utf-8")
        except Exception as error:
            print(f"Could not capture final DOM: {error}", file=sys.stderr)
        try:
            call("DELETE", f"/session/{session_id}")
        except Exception as error:
            print(f"Could not close WebDriver session: {error}", file=sys.stderr)
