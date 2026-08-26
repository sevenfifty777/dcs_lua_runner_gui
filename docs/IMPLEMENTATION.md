# DCS Lua Runner Security Modernization Implementation Log

Date started: 2026-08-26

## Scope

This log tracks implementation of `docs/PLAN.md`. The work secures the
arbitrary-code execution boundary while preserving DCS Mission and Hooks
execution. It does not make submitted Lua safe and it does not audit the main
DCS dashboard or LSO dashboard application code.

## Confirmed Deployment Baseline

| Public hostname placeholder | Private backend |
| --- | --- |
| `dcs-dashboard.example.com` | `127.0.0.1:3001` |
| `lso-dashboard.example.com` | `127.0.0.1:8090` |
| `fiddle.example.com` | `127.0.0.1:12080` |
| `fiddle-gui.example.com` | `127.0.0.1:12081` |

All `example.com` names in this repository are reserved documentation
placeholders. Supply the real deployment hostnames through private
configuration. The two dashboard rows are optional shared-Caddy context, not
DCS Lua Runner requirements.

The server firewall permits inbound TCP 80 and 443. Direct external access to
TCP 3001, 8090, 12080, and 12081 is already blocked and must remain blocked.

## Runtime and Dependency Baseline

- Target operating system: Windows, on the DCS/Caddy host and GUI workstations.
- Python source now requires Python 3.10 or later.
- Runtime dependencies are pinned to Requests 2.34.2 and Pygments 2.21.0.
- The build dependency is pinned separately to PyInstaller 6.22.2.
- `requirements.lock` records the complete Windows CPython 3.11 resolution.
- No new third-party dependency has been added; Pygments was already declared
  and is now used by the editor.
- The active Caddy version remains to be recorded on the production server.
- Caddy `request_body max_size` requires Caddy 2.10.0 or later. The Lua server
  enforces its own limit regardless of Caddy support.

## Milestone 1: Secure Protocol and Client Foundation

Implemented:

- Replaced Basic Authentication, Host-header bypass, base64 GET execution, and
  source-embedded credentials in `dcs-fiddle-server.lua`.
- Added fail-closed `dcs-fiddle-config.lua` loading with a non-secret example.
- Enforced `127.0.0.1` binding and a separate 256-bit internal proxy token.
- Added `POST /v1/execute?env=default` and authenticated `GET /healthz`.
- Added request-line, header, body, response, client-count, nesting, and deadline
  limits.
- Replaced blocking per-client reads/writes with an incremental LuaSocket state
  machine.
- Preserved Mission `timer.scheduleFunction` polling and Hooks callbacks, while
  throttling `onSimulationFrame` work.
- Removed request-source logging.
- Added deterministic JSON output, explicit typed envelopes for ambiguous Lua
  tables, and structured syntax/runtime/serialization errors.
- Replaced the Python GET/Basic client with HTTPS POST, mTLS, strict server
  certificate verification, response limits, and disabled redirects.
- Replaced plaintext password settings with versioned endpoint and certificate
  path settings under `%APPDATA%\DCSLuaRunner\settings.json`.
- Added atomic settings writes and legacy-password migration/sanitization.
- Corrected Tkinter worker-thread widget access.
- Added an authenticated, non-destructive connection test and current-file Save
  behavior.
- Replaced per-keystroke regex highlighting with debounced Pygments Lua lexing.
- Added a deployable, secret-free Caddy template under `deploy/`.
- Replaced the legacy distribution batch logic with a bounded PowerShell build,
  Lua hash verification, secret checks, and a packaged `--version` smoke test.
- The build refuses PyInstaller older than 6.22.2. The previously installed
  6.14.0 is affected by GHSA-9fxf-4qw3-ghmr; upstream fixes the issue in 6.22.1.
- Added standard-library unit tests for the Python client, settings migration,
  and Lua security contract.

## Files Added

- `dcs-fiddle-config.lua.example`
- `deploy/Caddyfile.example`
- `deploy/client-cert-ext.cnf`
- `tests/__init__.py`
- `tests/test_dcs_client.py`
- `tests/test_settings_manager.py`
- `tests/test_lua_server_contract.py`
- `docs/IMPLEMENTATION.md`
- `docs/CADDY_MTLS_SETUP.md`
- `docs/SECURITY_ARCHITECTURE.md`
- `docs/PROTOCOL_V2.md`
- `docs/MIGRATION_V1_TO_V2.md`
- `docs/TEST_AND_VALIDATION.md`
- `scripts/build_distribution.ps1`
- `requirements-build.txt`
- `requirements.lock`

## Security Notes

- Never commit `dcs-fiddle-config.lua`, a client private key, the client-CA
  private key, or `DCS_FIDDLE_PROXY_TOKEN`.
- The Caddy server needs the client-CA certificate, not its private key.
- The Requests client requires an unencrypted PEM private key. Restrict that key
  to the intended Windows user with filesystem ACLs.
- The same proxy token is loaded by Caddy and DCS, but is never sent by the GUI.
- The GUI does not provide a TLS-verification bypass.
- Client-certificate issuance, ACL protection, rotation, smoke testing, and
  rollback are documented without generating or committing any real key.

## Validation Status

Completed in this environment:

- Python 3.11.9 byte-compilation succeeded.
- `python -m unittest discover -s tests -v`: 22 tests passed.
- An isolated virtual environment resolved `requirements.lock`; `pip check`
  reported no conflicts and `pip-audit 2.10.1` reported no known
  vulnerabilities in the locked application/build packages.
- The settings JSON template parsed successfully.
- The PowerShell distribution script parsed successfully.
- PyInstaller 6.22.2 built and smoke-tested
  `DCS_Lua_Runner_GUI_v2.0-dev`; root and packaged Lua SHA-256 matched at
  `E0E073B06305B853808B927F181EF67296599C86DDA03AE3CA2BBE5779591A76`.

Pending:

- Lua syntax and behavioral tests, because no standalone Lua interpreter is
  currently available on `PATH`.
- Caddy validation, because the active production Caddy executable, version,
  CA certificate, and service environment are not available in this workspace.
- Live Mission and Hooks execution, which requires deployment to a controlled
  DCS instance and a DCS restart.

PyInstaller reported only platform-specific or optional imports as missing;
the targeted Pygments and Requests hooks completed and the packaged version
smoke test passed. The old tracked v1.0 package remains a historical artifact
and must not be deployed.

These validations must be completed before production cutover. Static source,
secret, artifact-consistency, and Git whitespace checks are run from the
workspace where possible.

The global Python environment's `pip check` also reported an unrelated existing
`fastmcp`/`mcp` version conflict. The application does not use either package;
release builds should use an isolated virtual environment created from
`requirements-build.txt`.
