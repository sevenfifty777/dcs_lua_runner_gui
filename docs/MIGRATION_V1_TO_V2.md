# Migration from v1 to Secure v2

This is a coordinated cutover. The secure Lua server intentionally does not
retain the legacy GET/Basic endpoint, because leaving it enabled would preserve
the original remote-code-execution weakness.

## Before the Window

1. Back up the active Caddyfile, old Hook Lua file, and non-secret application
   configuration to a restricted rollback directory.
2. Record Caddy version, executable path, service identity, environment method,
   and all current listeners.
3. Issue individual client certificates and stage the client-CA certificate.
4. Generate the separate internal token and stage it in both DCS and the Caddy
   service environment.
5. Keep the old v1 executable out of use. Do not copy its settings or password.

## Cutover

1. Install `dcs-fiddle-server.lua` and the populated, untracked
   `dcs-fiddle-config.lua` in Saved Games Hooks.
2. Restart DCS and confirm ports 12080 and 12081 listen only on loopback.
3. Merge the two Fiddle blocks from `deploy/Caddyfile.example` into the active
   Caddyfile. Leave both dashboard blocks unchanged.
4. Validate the complete Caddy configuration, reload, and run dashboard smoke
   tests immediately.
5. Configure the v2 GUI certificate paths and run Test Connection for Mission
   and Hooks before executing code.

## Settings Migration

On first run, the GUI looks for the old working-directory
`dcs_lua_runner_settings.json` only when the new per-user settings do not exist.
It imports HTTPS hosts, ports, display preferences, and target environment. It
does not copy the Basic-auth username or password. After the new file is saved,
the legacy file is replaced with a non-secret migration marker. Any migration
failure is shown to the operator and defaults are used fail-closed.

The new file is `%APPDATA%\DCSLuaRunner\settings.json`. Add the client
certificate and key paths manually and validate them with Test Connection.

## Rollback

Restore the known-good full Caddyfile and validate it before reload. Restore the
old Hook only if operational rollback is explicitly accepted, restart DCS, and
keep all backend ports externally blocked. Never publish port 12080 or 12081 to
make an old client work. Treat any return to the v1 protocol as a temporary
high-risk state and restrict access by an independent network control.
