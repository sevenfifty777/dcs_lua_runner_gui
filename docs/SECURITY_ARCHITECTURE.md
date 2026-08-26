# Security Architecture

## Purpose

DCS Lua Runner is an authenticated remote-code-execution tool. It authorizes
who may submit code; it does not sandbox or make submitted Lua safe. Every
holder of an accepted client private key must be treated as a DCS server
administrator.

The Lua Hook and data-only Lua config are installed on the DCS dedicated
server, not on DCS player clients. The desktop GUI is the remote operator
client. On the server, DCS auto-loads only `Scripts\Hooks\dcs-fiddle-server.lua`;
that Hook explicitly loads `Scripts\DCSLuaRunner\dcs-fiddle-config.lua`.

## Trust Boundaries

```text
Internet
  |
  | TLS server authentication + required client certificate
  v
Caddy on TCP 443
  |
  | loopback HTTP + X-DCS-Proxy-Token
  v
DCS LuaSocket listeners on 127.0.0.1:12080 and 127.0.0.1:12081
  |
  | authorized arbitrary Lua
  v
DCS Mission and Hooks/GameGUI environments
```

The optional main dashboard (`127.0.0.1:3001`) and LSO dashboard
(`127.0.0.1:8090`) are separate applications, not DCS Lua Runner dependencies.
When those applications share the Caddy instance, their site blocks do not
inherit Fiddle mTLS, route restrictions, or proxy headers.

## Controls

| Layer | Control |
| --- | --- |
| Internet edge | Public TLS, hostname routing, required and verified client certificate |
| Caddy routes | Only execute POST and health GET are proxied; request body is bounded |
| Backend identity | Caddy overwrites the internal proxy-token header |
| Host network | DCS listeners are loopback-only; backend ports remain externally blocked |
| Lua HTTP parser | Strict HTTP/1.1 framing, duplicate-header rejection, exact length, deadlines and client cap |
| Execution | One execution begins per poll cycle; source is never logged |
| Results | Bounded, deterministic JSON with typed-table collision protection |
| GUI | HTTPS only, mTLS required, server verification cannot be disabled, redirects and environment proxies disabled |
| Settings | Allow-listed schema in per-user application data; no password or proxy token |
| Release | Exact dependencies, secret checks, Lua hash comparison, packaged smoke test |

## Secrets and Keys

- `DCS_FIDDLE_PROXY_TOKEN` is shared only by Caddy and the DCS configuration.
- Each operator gets a unique client certificate and private key.
- The client-CA private key stays offline.
- The Caddy server holds only the client-CA certificate.
- The GUI settings contain paths to certificate files, never key contents.

## Residual Risk

An authorized Lua request can block DCS, alter missions, access desanitized
modules, read or change host data available to the DCS account, and initiate
network connections. Lua that is already executing cannot be reliably
preempted. mTLS compromise, local administrator compromise, Caddy service
compromise, or DCS account compromise can therefore lead to full execution
access. Use short-lived client certificates, isolated server accounts, backups,
restricted egress, and administrative review of every submitted script.
