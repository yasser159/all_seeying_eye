# all_seeying_eye

Desktop diagnostics viewer for Expo/Metro logs with a strict core/UI split.

## What It Does
- Ingests structured `[Diagnostics]` JSON logs from:
  1. WebSocket (recommended): your app pushes logs directly to the desktop app.
  2. Metro: the desktop app can spawn Metro and parse logs from its stdout.
- Shows a chronological log timeline with filtering, copy-as-JSON, and a details pane.
- Sends macOS notifications for `warn` and `error` (with an action to open the app).

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you do not have Python 3.12 installed, PySide6 will not install on Python 3.13+.

## Setup (Python 3.13 installed)

Install Python 3.12 first (recommended), then run:

```bash
cd /Users/yasser159/code/devtools/all_seeying_eye
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Start the UI:

```bash
PYTHONPATH=src python -m all_seeing_eye
```

Then, pick a source in the UI:
- WebSocket tab: click `Start Listening` and send logs to the shown `ws://...` URL.
- Metro tab: set the Expo project directory and click `Start Metro`.

## CLI Modes (Optional)

Start Metro via CLI (spawns Metro, parses `[Diagnostics]` JSON lines):

```bash
PYTHONPATH=src python -m all_seeing_eye --project "/Users/yasser159/code/React/diabetic_watch_react"
```

Start a WebSocket ingest server (default ws://127.0.0.1:8765):

```bash
PYTHONPATH=src python -m all_seeing_eye --ws --ws-port 8765
```

If PySide6 is not installed, you can run headless mode:

```bash
PYTHONPATH=src python -m all_seeing_eye.headless --ws --ws-port 8765
```

Send a diagnostics payload from the app or a script:

```bash
python - <<'PY'
import asyncio
import json
import websockets

payload = {"ts": "2026-02-06T16:33:17.514Z", "level": "error", "message": "TestError", "data": {"detail": "boom"}}

async def main():
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        await ws.send(json.dumps(payload))

asyncio.run(main())
PY
```

## Notes
- Core pipeline runs without any UI dependency.
- UI is PySide6 and is optional for headless use.
