# Caddy and Mutual TLS Deployment Guide

This guide deploys the secure DCS Lua Runner endpoints without changing the
authentication behavior of the existing DCS and LSO dashboards. Complete it in
a maintenance window: an invalid global Caddy configuration can affect every
site even when only the Fiddle blocks were edited.

## Security Model

```text
GUI -- HTTPS + client certificate --> Caddy :443
    -- loopback HTTP + proxy token --> DCS :12080 or :12081
```

- Caddy continues to obtain the public server certificates normally. The
  Route53 DNS module is not required for the current A-record configuration.
- The client certificate authenticates the GUI to Caddy.
- A separate random token authenticates Caddy to the loopback Lua service.
- TCP 12080 and 12081 remain externally blocked. If the optional dashboards are
  present, TCP 3001 and 8090 also remain externally blocked. Only TCP 80 and 443
  are public.
- The client-CA private key is kept offline. It is never installed on the DCS
  server or GUI workstation.

## 1. Inventory and Back Up

Record the active Caddy executable, service identity, configuration path, data
directory, and version. Then copy the active Caddyfile and PKI directory to a
restricted backup location. Do not overwrite the only known-good copy.

Confirm the current listeners on the DCS server:

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object LocalPort -in 80,443,3001,8090,12080,12081 |
    Sort-Object LocalPort
```

The two Lua Runner backends, plus any optional dashboard backends hosted on the
same server, should listen only on `127.0.0.1`. The Lua server itself refuses any
other bind address.

## 2. Configure Your Hostnames

Keep real deployment hostnames out of this public repository. Put them in the
following private or external locations:

1. Create the required public DNS records at your DNS provider and point them to
   the server running Caddy.
2. Copy or merge `deploy/Caddyfile.example` into the active Caddyfile on the
   server, such as `C:\Caddy\Caddyfile`. Replace the site address at the opening
   line of each applicable block:

   | Purpose | Public placeholder | Private backend | Required here? |
   | --- | --- | --- | --- |
   | Main DCS dashboard | `dcs-dashboard.example.com` | `127.0.0.1:3001` | No; optional shared-Caddy example |
   | LSO dashboard | `lso-dashboard.example.com` | `127.0.0.1:8090` | No; optional shared-Caddy example |
   | Mission Lua Runner | `fiddle.example.com` | `127.0.0.1:12080` | Yes |
   | Hooks/GameGUI Lua Runner | `fiddle-gui.example.com` | `127.0.0.1:12081` | Yes |

   The dashboard blocks are not dependencies of DCS Lua Runner. Include them
   only if this Caddy instance also serves those applications. If they already
   have working blocks, preserve their existing addresses and authentication;
   otherwise omit both optional blocks.
3. In each GUI workstation's Settings tab, enter the real Mission and
   Hooks/GUI URLs with `https://` and no path. The GUI stores them in
   `%APPDATA%\DCSLuaRunner\settings.json`.

Do not put production hostnames in `core/settings_manager.py` or
`dcs_lua_runner_settings.json.tpl`; those tracked files intentionally retain
reserved examples. Public hostnames do not belong in `dcs-fiddle-config.lua`,
because the Lua listeners remain on loopback behind Caddy.

## 3. Generate the Internal Proxy Token

Run this in a private PowerShell session on the server. It creates a 256-bit,
unpadded base64url value accepted by the Lua configuration:

```powershell
$tokenBytes = [byte[]]::new(32)
[Security.Cryptography.RandomNumberGenerator]::Fill($tokenBytes)
$proxyToken = [Convert]::ToBase64String($tokenBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
```

Put the value in both locations, without committing it:

1. Set `proxy_token` in the private deployed file
   `%USERPROFILE%\Saved Games\<DCS version>\Scripts\Hooks\dcs-fiddle-config.lua`.
2. Set `DCS_FIDDLE_PROXY_TOKEN` in the environment of the Windows service that
   runs Caddy.

### NSSM-managed Caddy service

Prefer a service-specific NSSM environment entry over a machine-wide Windows
environment variable. This limits routine exposure to the Caddy service and
avoids making the token available to unrelated processes started later.

1. From an elevated terminal, run `nssm edit <CaddyServiceName>`.
2. Open the **Environment** tab.
3. Leave **Replace default environment** unchecked so NSSM adds to, rather than
   replaces, the normal service environment.
4. Preserve every existing entry and add a new line:

   ```text
   DCS_FIDDLE_PROXY_TOKEN=<same generated value used in dcs-fiddle-config.lua>
   ```

5. Save the service configuration and restart the Caddy service. A Caddy config
   reload alone does not recreate the Windows process environment.

NSSM stores `AppEnvironmentExtra` in the service configuration. Restrict access
to Administrators and the Caddy service identity. Prefer the NSSM editor over a
command containing the token because command lines and shell history can expose
secret values. See the official [NSSM environment documentation](https://nssm.cc/usage#environment)
and [Caddy environment-variable documentation](https://caddyserver.com/docs/caddyfile/concepts#environment-variables).

A machine-wide Windows environment variable can work after a full Caddy service
restart, but it is broader than necessary and is not recommended here. If the
two token values differ or either is missing, the Lua backend fails closed with
HTTP 401.

Clear the temporary PowerShell variables when finished:

```powershell
[Array]::Clear($tokenBytes, 0, $tokenBytes.Length)
$proxyToken = $null
```

## 4. Create a Dedicated Client CA

The following commands require an already-installed, trusted OpenSSL 3.x
executable. Run them on an offline administrative workstation, not on the DCS
server. Protect the working directory and keep the CA key encrypted and offline.

```powershell
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -aes-256-cbc -out fiddle-client-ca.key.pem
openssl req -x509 -new -sha256 -key fiddle-client-ca.key.pem -days 3650 -out fiddle-client-ca.cert.pem -subj "/CN=DCS Fiddle Client CA" -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,keyCertSign,cRLSign" -addext "subjectKeyIdentifier=hash"
```

Create a separate, short-lived certificate for each authorized GUI. Requests
needs an unencrypted PEM client key, so compensate with restrictive filesystem
ACLs and never send the key through chat or email.

```powershell
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out operator01.key.pem
openssl req -new -sha256 -key operator01.key.pem -out operator01.csr.pem -subj "/CN=dcs-fiddle-operator01"
openssl x509 -req -sha256 -in operator01.csr.pem -CA fiddle-client-ca.cert.pem -CAkey fiddle-client-ca.key.pem -CAcreateserial -days 90 -extfile deploy\client-cert-ext.cnf -out operator01.cert.pem
openssl verify -purpose sslclient -CAfile fiddle-client-ca.cert.pem operator01.cert.pem
```

Transfer only these artifacts:

- DCS/Caddy server: `fiddle-client-ca.cert.pem`.
- Authorized GUI workstation: `operator01.cert.pem` and
  `operator01.key.pem`.

Delete the CSR when issuance records are complete. Retain the encrypted CA key
and serial file in the offline CA backup. Issue a new certificate rather than
sharing one client key between operators.

On each GUI workstation, restrict the key to the current account. First verify
the exact path, then run from an elevated PowerShell window:

```powershell
icacls.exe C:\Secure\DCSFiddle\operator01.key.pem /inheritance:r
icacls.exe C:\Secure\DCSFiddle\operator01.key.pem /grant:r "$($env:USERNAME):(R)"
```

Review the resulting ACL with `icacls.exe <path>` before using the key.

## 5. Stage the Lua Files

Place these files in the DCS Saved Games Hooks directory:

- `dcs-fiddle-server.lua`
- `dcs-fiddle-config.lua`, copied from the example and populated locally

Keep both ports and loopback binding as shipped. Ensure the DCS account can read
the files, then restart DCS. Verify locally that ports 12080 and 12081 are bound
to `127.0.0.1`, not `0.0.0.0` or a public address.

## 6. Stage and Validate Caddy

Merge the two Fiddle blocks from `deploy/Caddyfile.example` into the active
configuration. The two dashboard blocks are optional examples: preserve their
existing configuration if those applications are already served by Caddy, or
omit them entirely. Update the client-CA path if needed; Caddy requires only the
CA certificate.

The template uses `request_body max_size`, which requires Caddy 2.10 or later.
If production is older, upgrade through the normal controlled process or omit
that directive temporarily; the Lua server independently enforces 256 KiB.

Validate the complete file with the exact executable and environment used by
the Windows service:

```powershell
caddy version
caddy validate --config C:\Caddy\Caddyfile
caddy adapt --config C:\Caddy\Caddyfile --pretty
```

Do not reload if validation reports any error or if the adapted configuration
does not contain both Fiddle sites plus any optional dashboard sites you chose
to retain. After validation, reload using the existing service procedure.

## 7. Smoke Tests

Test from an authorized GUI workstation and from a client without a
certificate.

Expected results:

| Test | Expected result |
| --- | --- |
| Fiddle endpoint without a client certificate | TLS handshake rejected |
| Fiddle endpoint with an untrusted certificate | TLS handshake rejected |
| Authenticated `GET /healthz` | HTTP 200 structured JSON |
| Authenticated `POST /v1/execute?env=default` | HTTP 200 or structured Lua error |
| Unsupported Fiddle path | HTTP 404 |
| Direct external TCP 12080/12081 | Blocked |
| Main dashboard HTTPS/login, when deployed | Unchanged and functional |
| LSO dashboard HTTPS, when deployed | Unchanged and functional |

Also confirm Caddy logs do not contain the proxy token and DCS logs do not
contain submitted Lua source.

## 8. Rotation and Revocation

- Renew each client certificate before its short expiry.
- If a client key is lost or suspected compromised, disable the Fiddle site
  blocks immediately, rotate the internal proxy token, and replace the client
  CA plus all authorized client certificates. The static Caddy file trust pool
  does not by itself provide an online revocation service.
- Rotate the proxy token after administrator turnover, suspected server
  compromise, or accidental disclosure.
- Keep an inventory containing certificate subject, serial, operator, issue
  date, expiry, and revocation/replacement status. Do not record private keys.

## 9. Rollback

If Fiddle fails but both dashboards are healthy, restore only the prior Fiddle
site blocks or temporarily remove them, validate the complete Caddyfile, and
reload. Do not expose ports 12080 or 12081 as a workaround.

If any Caddy-hosted dashboard is affected, restore the entire known-good
Caddyfile and use the established service reload/restart procedure. Re-run the
dashboard smoke tests after rollback.
