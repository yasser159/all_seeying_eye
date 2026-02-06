# all_seeying_eye

Desktop diagnostics viewer for Expo/Metro logs with a strict core/UI split.

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

Start Metro via the app (parses `[Diagnostics]` JSON lines):

```bash
python -m all_seeing_eye --project "/Users/yasser159/code/React/diabetic_watch_react"
```

If Metro is already running, you can pipe its output:

```bash
# Example: run Expo in another terminal and pipe logs
python -m all_seeing_eye --stdin
```

Start a WebSocket ingest server (default ws://127.0.0.1:8765):

```bash
python -m all_seeing_eye --ws --ws-port 8765
```

If PySide6 is not installed, you can run headless mode:

```bash
python -m all_seeing_eye.headless --ws --ws-port 8765
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
