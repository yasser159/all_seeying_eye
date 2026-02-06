# Plan
- [x] Define data source: tail Metro logs vs. in-app diagnostics stream; pick transport (WebSocket) and message schema
- [x] Implement core (headless) log pipeline: ingest -> normalize -> store -> notify; no UI dependencies
- [x] Implement UI shell in PySide6: Diagnostics screen with chronological log list + open actions
- [x] Add macOS notifications with action to open Diagnostics screen
- [x] Add WebSocket ingest mode (core-only) to accept diagnostics payloads
- [x] Wire CLI args + README for WebSocket mode
- [x] Verify WebSocket ingest with a sample payload
- [x] Add UI Start/Stop controls and running indicator for intercepting errors

# Review
- [ ] Evidence: core runs without UI and emits verbose structured logs
- [ ] Evidence: Diagnostics screen shows live chronological history
- [ ] Evidence: notification action opens Diagnostics screen
- [x] Evidence: WebSocket ingest accepts diagnostics payloads (TestError via ws://127.0.0.1:8765)
- [ ] Risks/notes: Notification action not yet manually clicked.
