# DCS Lua Runner GUI Quick Start

This application executes arbitrary Lua inside DCS. Use it only with trusted
code and keep the DCS backend listeners private.

## 1. Install the DCS dedicated-server files

Perform this step on the **DCS dedicated server**, using the Saved Games profile
of the Windows account that runs the DCS server. Do not install these Lua files
in a player's DCS client Saved Games profile.

Copy the executable Hook script to:

```text
%USERPROFILE%\Saved Games\<DCS server version>\Scripts\Hooks\dcs-fiddle-server.lua
```

Create the separate configuration directory, then copy and rename the example
to:

```text
%USERPROFILE%\Saved Games\<DCS server version>\Scripts\DCSLuaRunner\dcs-fiddle-config.lua
```

The config intentionally stays outside `Scripts\Hooks`: DCS auto-loads the
server Hook, and that Hook explicitly loads the data-only config. Do not put
the renamed `.lua` config in `Scripts\Hooks`.

Edit the new configuration:

- keep `bind_ip = "127.0.0.1"`;
- keep Mission port 12080 and Hooks port 12081;
- replace the proxy-token placeholder with at least 256 bits of random data;
- do not commit or share the populated file.

The same proxy token must be available to the Caddy Windows service as
`DCS_FIDDLE_PROXY_TOKEN`.

If NSSM manages Caddy, run `nssm edit <CaddyServiceName>`, open the
**Environment** tab, leave **Replace default environment** unchecked, preserve
the existing entries, and add `DCS_FIDDLE_PROXY_TOKEN=<same token>`. Save and
restart the Caddy service. Do not use a machine-wide variable unless a
service-specific environment is unavailable.

## 2. Configure Caddy

Start from `deploy/Caddyfile.example` and follow
`docs/CADDY_MTLS_SETUP.md`. That guide is the authoritative beginner-oriented
procedure: it identifies the machine for every step, explains every certificate
file, and includes the required copy/transfer commands. Do not use this Quick
Start as a substitute for the full guide during the first deployment.

Keep the tracked example unchanged; copy or merge it into the private active
Caddyfile on the server and replace these site addresses there:

- `https://fiddle.example.com` -> `127.0.0.1:12080`;
- `https://fiddle-gui.example.com` -> `127.0.0.1:12081`.

Create matching public DNS records pointing to Caddy. If you use the dashboard
blocks from the template, also replace `dcs-dashboard.example.com` and
`lso-dashboard.example.com`; preserve existing dashboard blocks when already
deployed. Those dashboard blocks are optional examples and are not required by
DCS Lua Runner; omit them when Caddy does not serve those applications. Enter
the two real Lua Runner URLs again in the GUI Settings tab. They are saved per
user in `%APPDATA%\DCSLuaRunner\settings.json`; do not insert them into the
tracked source defaults or JSON template.

Before reload:

1. Install the client-CA certificate at the path referenced by the Caddyfile.
2. Confirm the Caddy service can read that certificate and its proxy-token
   environment variable.
3. Run `caddy validate --config C:\path\to\Caddyfile`.
4. Back up the active Caddyfile.
5. Run `caddy reload --config C:\path\to\Caddyfile`.

Only TCP 80 and 443 should be publicly reachable. Keep TCP 3001, 8090, 12080,
and 12081 blocked externally.

## 3. Configure the GUI

Open the Settings tab and provide:

- Mission URL, replacing the placeholder `https://fiddle.example.com`;
- Hooks/GUI URL, replacing the placeholder `https://fiddle-gui.example.com`;
- client certificate PEM file;
- matching unencrypted client private-key PEM file;
- optional CA bundle when the public server certificate is not trusted by the
  Windows/Python trust store.

Protect the private key with Windows filesystem ACLs. The GUI never stores the
Caddy-to-DCS proxy token.

## 4. Start DCS and test

Restart DCS after installing or changing the Hook script. Then:

1. Select Mission and execute `return timer.getTime()`.
2. Select GUI and execute a GameGUI-safe expression.
3. Confirm results contain no TLS or authentication errors.
4. Check DCS and Caddy logs without recording submitted Lua or credentials.

Use F5 to run all editor content and F8 to run the selected text.

## Troubleshooting

- TLS validation failure: check the hostname, server certificate, and optional
  CA bundle.
- Client certificate rejected: confirm it chains to the client CA configured in
  the relevant Caddy site block and is not expired or revoked.
- HTTP 401 from the Lua backend: confirm Caddy and DCS loaded the same proxy
  token; never place that token in the GUI.
- Connection failure: confirm Caddy is listening on 443 and the relevant DCS
  loopback listener started successfully.
- HTTP 413: the Lua source exceeds the configured 256 KiB request limit.

See `README.md`, `docs/PLAN.md`, and `docs/IMPLEMENTATION.md` for full details.
