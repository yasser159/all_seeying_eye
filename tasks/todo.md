# Plan
- [x] Add Metro health indicator (port 8081 listener) and “Check” UI
- [x] Add Metro start modes (expo start vs devlog expo) so capture is reliable
- [x] Verify: start Metro, confirm 8081 listener, confirm diagnostics logs ingest (requires app run)

# Review
- [x] Evidence: port probe works (8081 listening detected after Metro start)
- [x] Evidence: Metro-runner supports both commands (npm start, devlog:expo)
- [ ] Evidence: diagnostics logs ingest requires the Expo app to run and emit `[Diagnostics]` lines
- [ ] Risks/notes:
