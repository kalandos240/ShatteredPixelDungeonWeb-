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
  innerWidth: window.innerWidth || 0,
  innerHeight: window.innerHeight || 0,
  saveReady: root && root.getAttribute('data-spd-save-ready'),
  smokeLoaded: root && root.getAttribute('data-spd-smoke-loaded'),
  scene: root && root.getAttribute('data-spd-smoke-scene'),
  javaFatal: root && root.getAttribute('data-spd-java-fatal'),
  language: root && root.getAttribute('data-spd-smoke-language'),
  depth: root && root.getAttribute('data-spd-smoke-depth'),
  heroPos: root && root.getAttribute('data-spd-smoke-hero-pos'),
  heroReady: root && root.getAttribute('data-spd-smoke-hero-ready'),
  keyboardKey: root && root.getAttribute('data-spd-smoke-key'),
  touchX: root && root.getAttribute('data-spd-smoke-touch-x'),
  touchY: root && root.getAttribute('data-spd-smoke-touch-y'),
  turnSaved: root && root.getAttribute('data-spd-smoke-turn-saved'),
  saveBytes: root && root.getAttribute('data-spd-smoke-save-bytes')
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
            and state.get("depth") == "1"
            and int(state.get("canvasWidth") or 0) == int(state.get("innerWidth") or -1)
            and int(state.get("canvasHeight") or 0) == int(state.get("innerHeight") or -1)
        ),
    )

    call(
        "POST",
        f"/session/{session_id}/execute/sync",
        {
            "script": "window.__spdSmokeAdvance = true; return true;",
            "args": [],
        },
    )
    wait_for_state(
        "second-floor GameScene + save",
        lambda state: (
            state.get("gameplay") == "started"
            and state.get("saveReady") == "true"
            and state.get("smokeLoaded") == "false"
            and state.get("scene") == "com.shatteredpixel.shatteredpixeldungeon.scenes.GameScene"
            and state.get("depth") == "2"
            and state.get("heroReady") == "true"
            and state.get("heroPos") is not None
        ),
    )

    cloud_probe_script = r"""
const done = arguments[arguments.length - 1];
(async function () {
  try {
    const request = indexedDB.open('shattered-pixel-dungeon-files', 1);
    const db = await new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('IndexedDB open failed'));
    });

    const records = await new Promise((resolve, reject) => {
      const out = [];
      const tx = db.transaction('FILE_DATA', 'readonly');
      const store = tx.objectStore('FILE_DATA');
      const cursorRequest = store.openCursor();
      cursorRequest.onsuccess = () => {
        const cursor = cursorRequest.result;
        if (!cursor) return;
        const key = String(cursor.key);
        if (key === 'game1' || key.startsWith('game1/')) {
          const value = cursor.value || {};
          let bytes = new Uint8Array(0);
          if (value.contents) {
            bytes = new Uint8Array(
              value.contents.buffer,
              value.contents.byteOffset || 0,
              value.contents.byteLength || value.contents.length || 0
            );
          }
          out.push({key, type: Number(value.type || 0), bytes: new Uint8Array(bytes)});
        }
        cursor.continue();
      };
      tx.oncomplete = () => resolve(out);
      tx.onerror = () => reject(tx.error || new Error('IndexedDB read failed'));
      tx.onabort = () => reject(tx.error || new Error('IndexedDB read aborted'));
    });

    db.close();

    records.sort((a, b) => a.key.localeCompare(b.key));
    const encoder = new TextEncoder();
    let rawBytes = 0;
    let packedBytes = 12;
    const encodedKeys = [];
    for (const record of records) {
      const keyBytes = encoder.encode(record.key);
      encodedKeys.push(keyBytes);
      rawBytes += record.bytes.length;
      packedBytes += 2 + 1 + 4 + keyBytes.length + record.bytes.length;
    }

    const packed = new Uint8Array(packedBytes);
    const magic = encoder.encode('SPDCLOUD1\n');
    packed.set(magic, 0);
    let offset = 12;
    const view = new DataView(packed.buffer);
    for (let i = 0; i < records.length; i++) {
      const record = records[i];
      const keyBytes = encodedKeys[i];
      view.setUint16(offset, keyBytes.length, true); offset += 2;
      packed[offset++] = record.type & 0xff;
      view.setUint32(offset, record.bytes.length, true); offset += 4;
      packed.set(keyBytes, offset); offset += keyBytes.length;
      packed.set(record.bytes, offset); offset += record.bytes.length;
    }

    if (typeof CompressionStream !== 'function') {
      done({files: records.length, rawBytes, packedBytes, gzipBytes: null, base64Bytes: null});
      return;
    }

    const compressedBuffer = await new Response(
      new Blob([packed]).stream().pipeThrough(new CompressionStream('gzip'))
    ).arrayBuffer();
    const gzipBytes = compressedBuffer.byteLength;
    const base64Bytes = Math.ceil(gzipBytes / 3) * 4;
    done({files: records.length, rawBytes, packedBytes, gzipBytes, base64Bytes});
  } catch (error) {
    done({error: String(error && (error.stack || error.message) || error)});
  }
})();
"""
    cloud_probe = call(
        "POST",
        f"/session/{session_id}/execute/async",
        {"script": cloud_probe_script, "args": []},
    )["value"]
    if cloud_probe.get("error"):
        raise RuntimeError("Cloud-save size probe failed: " + cloud_probe["error"])
    print(
        "Cloud-save size probe (slot 1): "
        + json.dumps(cloud_probe, ensure_ascii=False, sort_keys=True)
    )

    start_pos = last_state["heroPos"]
    call(
        "POST",
        f"/session/{session_id}/execute/sync",
        {
            "script": "window.__spdSmokeMove = true; return true;",
            "args": [],
        },
    )
    wait_for_state(
        "hero movement through actor fiber",
        lambda state: (
            state.get("depth") == "2"
            and state.get("heroReady") == "true"
            and state.get("heroPos") is not None
            and state.get("heroPos") != start_pos
        ),
        timeout=30,
    )
    moved_pos = last_state["heroPos"]

    # Web builds autosave when a hero turn finishes. Wait until that exact
    # moved position has been serialized, then refresh immediately without a
    # synthetic Yandex pause. This guards against losing the last completed
    # action on an ordinary browser reload.
    wait_for_state(
        "completed-turn web autosave",
        lambda state: state.get("turnSaved") == moved_pos,
        timeout=30,
    )

    # Reload the same origin. gdx-teavm rehydrates local files from IndexedDB
    # before the application listener starts; smoke mode must now choose
    # CONTINUE and restore the moved hero tile.
    call("POST", f"/session/{session_id}/refresh", {})
    wait_for_state(
        "reloaded GameScene from IndexedDB save",
        lambda state: (
            state.get("ready") == "true"
            and state.get("yandexReady") == "true"
            and state.get("gameplay") == "started"
            and state.get("saveReady") == "true"
            and state.get("smokeLoaded") == "true"
            and state.get("depth") == "2"
            and state.get("heroReady") == "true"
            and state.get("heroPos") == moved_pos
        ),
    )

    # Exercise the real browser keyboard path: WebDriver key event -> DOM ->
    # gdx-teavm WebInput -> Shattered KeyBindings/CellSelector -> actor fiber.
    wait_for_state(
        "safe keyboard move target",
        lambda state: state.get("keyboardKey") in {"UP", "DOWN", "LEFT", "RIGHT"},
        timeout=30,
    )
    keyboard_start_pos = last_state["heroPos"]
    webdriver_keys = {
        "UP": "\ue013",
        "DOWN": "\ue015",
        "LEFT": "\ue012",
        "RIGHT": "\ue014",
    }
    key_value = webdriver_keys[last_state["keyboardKey"]]
    call(
        "POST",
        f"/session/{session_id}/actions",
        {
            "actions": [{
                "type": "key",
                "id": "keyboard",
                "actions": [
                    {"type": "keyDown", "value": key_value},
                    {"type": "pause", "duration": 80},
                    {"type": "keyUp", "value": key_value},
                ],
            }]
        },
    )
    wait_for_state(
        "keyboard movement through WebInput",
        lambda state: (
            state.get("depth") == "2"
            and state.get("heroReady") == "true"
            and state.get("heroPos") is not None
            and state.get("heroPos") != keyboard_start_pos
        ),
        timeout=30,
    )

    # Exercise Chrome's native touch pointer path. The game exposes a safe
    # adjacent tile's screen coordinates; WebDriver taps it as pointerType
    # "touch", which must flow through WebInput touchstart/touchend and
    # CellSelector before the actor fiber changes hero position.
    wait_for_state(
        "safe touch move target",
        lambda state: (
            state.get("touchX") is not None
            and state.get("touchY") is not None
        ),
        timeout=30,
    )
    touch_start_pos = last_state["heroPos"]
    touch_x = int(last_state["touchX"])
    touch_y = int(last_state["touchY"])
    call(
        "POST",
        f"/session/{session_id}/actions",
        {
            "actions": [{
                "type": "pointer",
                "id": "finger",
                "parameters": {"pointerType": "touch"},
                "actions": [
                    {
                        "type": "pointerMove",
                        "duration": 0,
                        "origin": "viewport",
                        "x": touch_x,
                        "y": touch_y,
                    },
                    {"type": "pointerDown", "button": 0},
                    {"type": "pause", "duration": 100},
                    {"type": "pointerUp", "button": 0},
                ],
            }]
        },
    )
    wait_for_state(
        "touch movement through WebInput",
        lambda state: (
            state.get("depth") == "2"
            and state.get("heroReady") == "true"
            and state.get("heroPos") is not None
            and state.get("heroPos") != touch_start_pos
        ),
        timeout=30,
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
            and int(state.get("canvasWidth") or 0) == int(state.get("innerWidth") or -1)
            and int(state.get("canvasHeight") or 0) == int(state.get("innerHeight") or -1)
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
            and int(state.get("canvasWidth") or 0) == int(state.get("innerWidth") or -1)
            and int(state.get("canvasHeight") or 0) == int(state.get("innerHeight") or -1)
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
