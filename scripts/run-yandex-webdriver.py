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
  canvasHeight: canvas ? canvas.height : 0
};
"""

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            last_state = call(
                "POST",
                f"/session/{session_id}/execute/sync",
                {"script": state_script, "args": []},
            )["value"]
        except Exception as error:
            last_state = {"webdriverError": str(error)}

        if last_state.get("ready") == "true" and last_state.get("yandexReady") == "true":
            print("Browser smoke state: " + json.dumps(last_state, ensure_ascii=False, sort_keys=True))
            break

        if last_state.get("error") or last_state.get("rejection"):
            raise RuntimeError(
                "Browser runtime failure: "
                + json.dumps(last_state, ensure_ascii=False, sort_keys=True)
            )

        time.sleep(0.5)
    else:
        raise RuntimeError(
            "Timed out waiting for Game Ready + LoadingAPI.ready(): "
            + json.dumps(last_state, ensure_ascii=False, sort_keys=True)
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
