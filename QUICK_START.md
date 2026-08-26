# DCS Lua Runner GUI Quick Start

This application executes arbitrary Lua inside DCS. Use it only with trusted
code and keep the DCS backend listeners private.

## 1. Install the DCS files

Copy these files to `%USERPROFILE%\Saved Games\<DCS version>\Scripts\Hooks\`:

- `dcs-fiddle-server.lua`
- `dcs-fiddle-config.lua.example`, renamed to `dcs-fiddle-config.lua`

Edit the new configuration:

- keep `bind_ip = "127.0.0.1"`;
- keep Mission port 12080 and Hooks port 12081;
- replace the proxy-token placeholder with at least 256 bits of random data;
- do not commit or share the populated file.

The same proxy token must be available to the Caddy Windows service as
`DCS_FIDDLE_PROXY_TOKEN`.

## 2. Configure Caddy

Start from `deploy/Caddyfile.example` and follow
`docs/CADDY_MTLS_SETUP.md`. The template preserves the two dashboard routes and
adds mTLS only to the following reserved example hostnames. Replace them with
your own DNS names before deployment:

- `https://fiddle.example.com` -> `127.0.0.1:12080`;
- `https://fiddle-gui.example.com` -> `127.0.0.1:12081`.

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
