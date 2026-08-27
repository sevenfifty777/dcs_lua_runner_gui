# Caddy and Mutual TLS Deployment Guide

This is a step-by-step Windows guide for deploying DCS Lua Runner behind Caddy.
It is written for server operators; no software-development or certificate
background is assumed.

Follow the sections in order. Do not use real passwords, private keys, tokens,
or production hostnames in this repository, chat, screenshots, or logs.

## What This Setup Does

```text
Authorized GUI workstation
        |
        | HTTPS on TCP 443 + operator client certificate
        v
Caddy on the DCS server
        |
        | private loopback HTTP + internal proxy token
        v
DCS Lua Runner on 127.0.0.1:12080 and 127.0.0.1:12081
```

Caddy provides the public HTTPS connection and requires an approved client
certificate for the two Lua Runner hostnames. DCS accepts traffic only from
loopback and requires a separate internal token that only Caddy and DCS know.

This setup does not make submitted Lua safe. Anyone holding an approved client
private key can execute Lua with the permissions available to DCS and must be
treated as a DCS server administrator.

## The Three Machine Roles

One physical PC can perform more than one role, but keep the roles separate in
your mind because different files belong in different places.

| Role | Where | What happens there |
| --- | --- | --- |
| CA workstation | A trusted administrative PC that can be taken offline | Creates the client CA and signs operator certificates |
| DCS/Caddy server | The Windows server running DCS and Caddy | Holds the public CA certificate, DCS Hook/config, Caddyfile, and proxy token |
| GUI workstation | Each authorized operator's Windows PC | Runs DCS Lua Runner GUI and holds that operator's client certificate/private key |

The DCS Lua files are server-side files. Do not install them in a player's DCS
client Saved Games profile. The client private key belongs on the GUI
workstation, not in DCS Saved Games.

## Download Only the Files You Need

You do **not** need to clone the repository or transfer the GUI distribution
folder to the server. Download these three individual files from GitHub:

| File to download | Used on | Purpose |
| --- | --- | --- |
| [`dcs-fiddle-server.lua`](../dcs-fiddle-server.lua) | DCS/Caddy server | Executable DCS Hook |
| [`dcs-fiddle-config.lua.example`](../dcs-fiddle-config.lua.example) | DCS/Caddy server | Configuration template; rename the copied file to `dcs-fiddle-config.lua` |
| [`deploy/Caddyfile.example`](../deploy/Caddyfile.example) | DCS/Caddy server | Reference from which to merge the two Fiddle site blocks into the existing active Caddyfile |

On GitHub, open each link, select **Download raw file**, and transfer only those
three files to the DCS/Caddy server. Do not replace the active Caddyfile with the
example: it may already contain the DCS and LSO dashboard sites.

The CA workstation later needs one additional non-secret file,
[`deploy/client-cert-ext.cnf`](../deploy/client-cert-ext.cnf). Download that one
file directly to the CA workstation when Section 5 tells you to do so. It is not
installed on the server.

## Files and Whether They Are Secret

| File/value | Secret? | Final location |
| --- | --- | --- |
| `client-cert-ext.cnf` | No | CA workstation only; retain for future certificate issuance |
| `fiddle-client-ca.key.pem` | **Yes, critical** | Encrypted and stored offline on the CA workstation |
| `fiddle-client-ca.cert.pem` | No | CA archive and `C:\Caddy\pki` on the DCS/Caddy server |
| `fiddle-client-ca.cert.srl` | Preserve it | Offline CA archive |
| `operator01.key.pem` | **Yes** | Only operator01's GUI workstation |
| `operator01.csr.pem` | No | Temporary CA-workstation file; remove after recording issuance |
| `operator01.cert.pem` | No | Operator01's GUI workstation and CA issuance archive |
| `DCS_FIDDLE_PROXY_TOKEN` | **Yes** | Caddy service environment and DCS server config only |
| `dcs-fiddle-config.lua` | **Yes; contains the token** | DCS dedicated server only |

Never copy `fiddle-client-ca.key.pem` to the DCS/Caddy server or a GUI
workstation. Caddy needs only the public `fiddle-client-ca.cert.pem` file.

## Values You Must Decide Before Starting

Write these values in a private administrator note. Do not add the note to Git.

| Example | Replace with |
| --- | --- |
| `<CaddyServiceName>` | Actual Windows service name used by Caddy |
| `C:\Caddy\Caddyfile` | Actual active Caddyfile path |
| `C:\Caddy\caddy.exe` | Actual Caddy executable path |
| `<DCS server version>` | Actual Saved Games directory, such as `DCS.openbeta_server` |
| `fiddle.example.com` | Real Mission Lua Runner hostname |
| `fiddle-gui.example.com` | Real Hooks/GameGUI Lua Runner hostname |
| `operator01` | A unique name for the first authorized operator/workstation |

Commands containing angle-bracket placeholders are not ready to paste until
you replace those placeholders.

## 1. Back Up and Record the Existing Server

**Run this section on: DCS/Caddy server**

Perform the deployment during a maintenance window. An invalid Caddyfile can
affect all sites served by the same Caddy service, including the existing DCS
and LSO dashboards.

Record:

- Caddy executable path and version;
- Caddy Windows service name and service account;
- active Caddyfile path;
- Caddy data/configuration directories;
- DCS Windows runtime account and its Saved Games directory.

Make a dated backup of the active Caddyfile and existing Caddy PKI directory.
Do not overwrite the only known-good backup.

Display the relevant listeners:

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object LocalPort -in 80,443,3001,8090,12080,12081 |
    Sort-Object LocalPort
```

Only TCP 80 and 443 are public. TCP 3001, 8090, 12080, and 12081 must remain
blocked externally. The Lua Runner will refuse to bind to anything except
`127.0.0.1`.

## 2. Create the Public DNS Records

**Perform this section at: your DNS provider**

Create two public DNS A records pointing to the public IP address of the server
running Caddy:

| Purpose | Repository placeholder | Private Caddy backend |
| --- | --- | --- |
| Mission Lua Runner | `fiddle.example.com` | `127.0.0.1:12080` |
| Hooks/GameGUI Lua Runner | `fiddle-gui.example.com` | `127.0.0.1:12081` |

The Route53 Caddy DNS module is not required for ordinary public A records.
Caddy can continue obtaining public HTTPS certificates through its existing
HTTP/HTTPS validation process.

The example Caddyfile also contains optional dashboard blocks:

| Optional application | Placeholder | Backend |
| --- | --- | --- |
| Main DCS dashboard | `dcs-dashboard.example.com` | `127.0.0.1:3001` |
| LSO dashboard | `lso-dashboard.example.com` | `127.0.0.1:8090` |

Those dashboards are not DCS Lua Runner dependencies. Preserve their existing
hostnames and authentication behavior if they are already deployed. Mutual TLS
must apply only to the two Fiddle/Lua Runner hostnames.

## 3. Install the DCS Dedicated-Server Lua Files

**Run this section on: DCS dedicated server**

Use the Saved Games profile of the Windows account that actually runs DCS. If
you are logged in as a different administrator, `%USERPROFILE%` points to the
wrong account; navigate explicitly to the DCS runtime account's profile.

Use File Explorer to create the destination directories if they do not already
exist. Copy `dcs-fiddle-server.lua` without renaming it to:

```text
C:\Users\<DCS-server-account>\Saved Games\<DCS server version>\Scripts\Hooks\dcs-fiddle-server.lua
```

Copy `dcs-fiddle-config.lua.example` to the separate configuration directory,
then rename that copied file to `dcs-fiddle-config.lua`:

```text
C:\Users\<DCS-server-account>\Saved Games\<DCS server version>\Scripts\DCSLuaRunner\dcs-fiddle-config.lua
```

Edit the copied config:

- keep `bind_ip = "127.0.0.1"`;
- keep `mission_port = 12080`;
- keep `gui_port = 12081`;
- leave the proxy-token placeholder temporarily; Section 4 generates the real
  value and tells you exactly how to insert it;
- keep the Lua quotation marks around the token value.

Do not place `dcs-fiddle-config.lua` in `Scripts\Hooks`. DCS auto-loads Lua
files from Hooks; `dcs-fiddle-server.lua` explicitly loads the data-only config
from `Scripts\DCSLuaRunner`.

If an older `Scripts\Hooks\dcs-fiddle-config.lua` exists, back it up outside
Hooks and remove the Hooks copy before restarting DCS. Do not leave two active
copies.

The Mission environment also requires the server-side Mission Scripting setup
described in the root `README.md`. This is performed on the DCS server
installation, not on a player's DCS client.

Do not restart DCS while the config still contains the token placeholder. The
restart and listener check occur after Section 4 installs the real token.

## 4. Generate the Internal Proxy Token

**Run this section on: DCS/Caddy server (recommended)**

The token authenticates Caddy to the loopback DCS Lua service. It is not the
GUI password and must never be copied to a GUI workstation.

Open a private Windows PowerShell 5.1 or PowerShell 7 window and paste this
entire block:

```powershell
$proxyToken = $null
$tokenBytes = New-Object byte[] 32
$randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $randomGenerator.GetBytes($tokenBytes)
    $proxyToken = [Convert]::ToBase64String($tokenBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
} finally {
    $randomGenerator.Dispose()
}

if ($proxyToken -notmatch '^[A-Za-z0-9_-]{43}$') {
    throw 'Generated proxy token has an unexpected format.'
}
$proxyToken
```

Expected result: one line containing exactly 43 characters. Letters, numbers,
hyphen (`-`), and underscore (`_`) are valid. The replacement is `'_'`, not
`'\_'`. Do not use a result if any error appeared during generation.

The same exact token goes into two server-side locations:

1. In `dcs-fiddle-config.lua`, Lua requires quotation marks:

   ```lua
   proxy_token = "paste-the-generated-token-here",
   ```

2. In the NSSM Caddy service environment, do **not** add quotation marks:

   ```text
   DCS_FIDDLE_PROXY_TOKEN=paste-the-same-generated-token-here
   ```

Do not add spaces around `=` and do not add a trailing `=` to the token.

### Add the token to an NSSM-managed Caddy service

1. Open an elevated PowerShell window.
2. Run `nssm edit <CaddyServiceName>` after replacing the placeholder.
3. Open the **Environment** tab.
4. Leave **Replace default environment** unchecked.
5. Preserve every existing entry.
6. Add the `DCS_FIDDLE_PROXY_TOKEN=...` line shown above.
7. Save the NSSM configuration.

Do not put the token directly on an `nssm set` command line because command
history and process inspection can expose it. A Caddy configuration reload does
not refresh a Windows service environment; restart the Caddy service after the
Caddyfile is ready.

The service-specific environment is preferable to a machine-wide environment
variable. NSSM stores it as `AppEnvironmentExtra`. Restrict service-management
access to administrators. See the [NSSM environment documentation](https://nssm.cc/usage#environment)
and [Caddy environment-variable documentation](https://caddyserver.com/docs/caddyfile/concepts#environment-variables).

After the token has been placed in both server-side locations, restart DCS and
confirm the two listeners:

```powershell
Get-NetTCPConnection -State Listen |
    Where-Object LocalPort -in 12080,12081 |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

Expected addresses:

```text
127.0.0.1:12080
127.0.0.1:12081
```

Stop if either listener uses `0.0.0.0` or a public address. Then clear the
temporary PowerShell variables:

```powershell
[Array]::Clear($tokenBytes, 0, $tokenBytes.Length)
$proxyToken = $null
$randomGenerator = $null
```

## 5. Prepare OpenSSL and the Offline CA Directory

**Run this section on: CA workstation**

Use a currently supported and patched OpenSSL 3.5 LTS release. The minimum for
this guide is OpenSSL 3.5.8; before issuing production certificates, check the
official OpenSSL advisories for a newer required patch.

If OpenSSL comes from Git for Windows, define its full path and check it:

```powershell
$OpenSSL = 'C:\Program Files\Git\usr\bin\openssl.exe'
& $OpenSSL version
```

Do not continue with production issuance unless the command reports OpenSSL
3.5.8 or a later supported 3.5.x patch. The official OpenSSL download page
primarily provides source archives; do not download an unverified Windows
binary from a search result.

Create a new empty CA working directory:

```powershell
$CaDirectory = 'C:\Secure\DCSFiddleCA'
$CaIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name

if (Test-Path -LiteralPath $CaDirectory) {
    throw "CA directory already exists; choose a new empty directory: $CaDirectory"
}
New-Item -ItemType Directory -Path $CaDirectory
icacls.exe $CaDirectory /inheritance:r
icacls.exe $CaDirectory /grant:r "${CaIdentity}:(OI)(CI)(F)"
```

Using the GitHub link in **Download Only the Files You Need**, download
`client-cert-ext.cnf` directly into `C:\Secure\DCSFiddleCA`. No repository clone
or GUI distribution folder is needed. Confirm the final name is exactly
`client-cert-ext.cnf`, not `client-cert-ext.cnf.txt`.

Then return to PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Secure\DCSFiddleCA'
Get-ChildItem -LiteralPath .
```

Expected result: `client-cert-ext.cnf` appears in the file listing.

### What `client-cert-ext.cnf` does

This small, non-secret text file is included in the repository. It tells OpenSSL
to mark an issued operator certificate as:

- an end-user certificate, not another CA;
- usable for digital signatures;
- usable specifically for TLS client authentication.

It is read only while signing operator certificates. It is not installed on
Caddy, DCS, or the GUI workstation. Keep it in the offline CA directory so all
future operator certificates use the same rules.

The certificate-signing command uses `-extfile .\client-cert-ext.cnf`, so run it
from `C:\Secure\DCSFiddleCA` as shown in this guide.

## 6. Create the Client Certificate Authority

**Run this section on: CA workstation, inside `C:\Secure\DCSFiddleCA`**

The CA is the authority Caddy trusts to approve operator certificates. The CA
private key is encrypted and must remain offline.

Create the encrypted CA private key:

```powershell
& $OpenSSL genpkey `
    -algorithm EC `
    -pkeyopt ec_paramgen_curve:P-256 `
    -aes-256-cbc `
    -out .\fiddle-client-ca.key.pem
```

OpenSSL asks for a passphrase twice. Use a strong unique passphrase, store it in
an approved password manager, and do not put it in a script or command line.
Losing it prevents future client-certificate issuance.

Create the public CA certificate:

```powershell
& $OpenSSL req `
    -x509 `
    -new `
    -sha256 `
    -key .\fiddle-client-ca.key.pem `
    -days 3650 `
    -out .\fiddle-client-ca.cert.pem `
    -subj '/CN=DCS Fiddle Client CA' `
    -addext 'basicConstraints=critical,CA:TRUE,pathlen:0' `
    -addext 'keyUsage=critical,keyCertSign,cRLSign' `
    -addext 'subjectKeyIdentifier=hash'
```

OpenSSL asks for the CA-key passphrase. The certificate lifetime is 3,650 days,
approximately ten years.

Inspect the result:

```powershell
& $OpenSSL x509 `
    -in .\fiddle-client-ca.cert.pem `
    -noout `
    -subject `
    -issuer `
    -serial `
    -dates
```

The subject and issuer should both contain `DCS Fiddle Client CA` because this
is a self-signed CA certificate.

## 7. Issue One Certificate Per GUI Operator

**Run this section on: CA workstation, inside `C:\Secure\DCSFiddleCA`**

The example uses `operator01`. Choose a unique, non-sensitive identifier for
each person or workstation. Do not share one operator private key between
multiple people.

Create the operator's unencrypted private key:

```powershell
& $OpenSSL genpkey `
    -algorithm EC `
    -pkeyopt ec_paramgen_curve:P-256 `
    -out .\operator01.key.pem
```

This key is deliberately unencrypted because the Python HTTPS client cannot
prompt for a PEM passphrase. Windows file permissions will protect it on the
GUI workstation.

Create the certificate signing request:

```powershell
& $OpenSSL req `
    -new `
    -sha256 `
    -key .\operator01.key.pem `
    -out .\operator01.csr.pem `
    -subj '/CN=dcs-fiddle-operator01'
```

Sign the request with the CA:

```powershell
& $OpenSSL x509 `
    -req `
    -sha256 `
    -in .\operator01.csr.pem `
    -CA .\fiddle-client-ca.cert.pem `
    -CAkey .\fiddle-client-ca.key.pem `
    -CAcreateserial `
    -days 90 `
    -extfile .\client-cert-ext.cnf `
    -out .\operator01.cert.pem
```

OpenSSL asks for the CA-key passphrase. The operator certificate lifetime is 90
days.

Verify the issued certificate:

```powershell
& $OpenSSL verify `
    -purpose sslclient `
    -CAfile .\fiddle-client-ca.cert.pem `
    .\operator01.cert.pem
```

Expected result:

```text
operator01.cert.pem: OK
```

Display its identity and validity dates:

```powershell
& $OpenSSL x509 `
    -in .\operator01.cert.pem `
    -noout `
    -subject `
    -issuer `
    -serial `
    -dates
```

Expected files now include:

```text
client-cert-ext.cnf
fiddle-client-ca.key.pem
fiddle-client-ca.cert.pem
fiddle-client-ca.cert.srl
operator01.key.pem
operator01.csr.pem
operator01.cert.pem
```

## 8. Transfer Only the Correct Certificate Files

**Transfer from: CA workstation**

Use an approved secure transfer method. Do not use chat, ordinary email, a
public file share, or a source repository.

### To the DCS/Caddy server

Transfer only:

```text
fiddle-client-ca.cert.pem
```

Place it at:

```text
C:\Caddy\pki\fiddle-client-ca.cert.pem
```

Create `C:\Caddy\pki` first if needed and ensure the Windows account running
Caddy can read the public certificate.

### To operator01's GUI workstation

Transfer only:

```text
operator01.cert.pem
operator01.key.pem
```

Place them in a new dedicated directory such as:

```text
C:\Secure\DCSFiddle
```

Do not transfer `fiddle-client-ca.key.pem` to either destination.

After transfers and verification, remove `operator01.csr.pem` if it is not part
of your issuance records. Retain the CA certificate, encrypted CA key, serial
file, extension file, and certificate inventory in an offline backup.

## 9. Restrict the Operator Private-Key Permissions

**Run this section on: operator01's GUI workstation**

The private key is unencrypted, so Windows permissions must prevent other
ordinary user accounts from reading it.

Open PowerShell as the same Windows account that will run DCS Lua Runner GUI:

```powershell
$KeyPath = 'C:\Secure\DCSFiddle\operator01.key.pem'
$OperatorIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name

Get-Item -LiteralPath $KeyPath -ErrorAction Stop
icacls.exe $KeyPath
icacls.exe $KeyPath /inheritance:r
icacls.exe $KeyPath /grant:r "${OperatorIdentity}:(R)"
icacls.exe $KeyPath
```

Review the final output. Broad groups such as `Everyone`, `Users`, or
`Authenticated Users` must not retain access. If they appear as explicit
permissions, remove them through **File Properties > Security > Advanced**.
Do not proceed until the intended operator account can read the file.

This ACL is not encryption. Malware running as the same operator or a local
administrator can still access the key. Short-lived, separate operator
certificates limit the impact of a lost key.

## 10. Configure the Active Caddyfile

**Run this section on: DCS/Caddy server**

The tracked `deploy\Caddyfile.example` contains placeholders, not production
DNS names. Merge only the needed blocks into the private active Caddyfile.

For the two Lua Runner blocks:

1. Replace `fiddle.example.com` with the real Mission hostname.
2. Replace `fiddle-gui.example.com` with the real Hooks/GameGUI hostname.
3. Confirm the CA path is:

   ```caddyfile
   trust_pool file C:/Caddy/pki/fiddle-client-ca.cert.pem
   ```

4. Keep the backends as `127.0.0.1:12080` and `127.0.0.1:12081`.
5. Keep `{env.DCS_FIDDLE_PROXY_TOKEN}` unchanged. It means Caddy reads the
   token from its Windows service environment.

Do not add mutual TLS or `X-DCS-Proxy-Token` handling to the DCS dashboard or
LSO dashboard blocks. Their existing behavior should remain unchanged.

The template uses the experimental `request_body max_size` directive, which
requires Caddy 2.10 or later. Check the exact executable used by the service:

```powershell
& 'C:\Caddy\caddy.exe' version
```

If the server uses an older Caddy version, stop and plan the Caddy upgrade. Do
not blindly remove security directives from the production configuration.

## 11. Validate and Restart Caddy Safely

**Run this section on: DCS/Caddy server**

First back up the active Caddyfile, then validate it:

```powershell
& 'C:\Caddy\caddy.exe' validate --config 'C:\Caddy\Caddyfile'
& 'C:\Caddy\caddy.exe' adapt --config 'C:\Caddy\Caddyfile' --pretty
```

Expected validation result: no error. Review the adapted output and confirm it
contains both Lua Runner hostnames and any existing dashboard sites you intend
to preserve.

The template deliberately uses `{env.DCS_FIDDLE_PROXY_TOKEN}`. Caddy resolves
this form at runtime from the environment of the running service; it is
different from the parse-time `{$NAME}` syntax. Therefore, the validation shell
does not need the real token.

For the first deployment, or whenever the NSSM token changes, restart the
Windows service so the Caddy process receives the new service environment:

```powershell
Restart-Service -Name '<CaddyServiceName>'
Get-Service -Name '<CaddyServiceName>'
```

Replace the placeholder with the actual service name. Expected service status:
`Running`.

If the service does not start, restore the backed-up Caddyfile and restart the
service again. Do not expose ports 12080 or 12081 as a workaround.

For later Caddyfile-only changes where the NSSM token did not change, use
`caddy reload` for a graceful configuration update after validation:

```powershell
& 'C:\Caddy\caddy.exe' reload --config 'C:\Caddy\Caddyfile'
```

## 12. Configure the DCS Lua Runner GUI

**Run this section on: each authorized GUI workstation**

Open the application Settings tab and enter:

| GUI field | Value |
| --- | --- |
| Mission URL | `https://<real Mission hostname>` |
| Hooks/GUI URL | `https://<real Hooks hostname>` |
| Client certificate | `C:\Secure\DCSFiddle\operator01.cert.pem` |
| Client private key | `C:\Secure\DCSFiddle\operator01.key.pem` |
| CA bundle | Leave empty when Caddy uses a normally trusted public HTTPS certificate |

The GUI does not need and must never receive `DCS_FIDDLE_PROXY_TOKEN` or the
client-CA private key.

Use the GUI's connection test for both environments. A browser without an
approved client certificate should be rejected by the two Fiddle hostnames;
that rejection is expected.

## 13. Deployment Smoke Tests

Complete every applicable test before considering the deployment successful:

| Test | Expected result |
| --- | --- |
| GUI connection test to Mission hostname | Successful authenticated health response |
| GUI connection test to Hooks/GameGUI hostname | Successful authenticated health response |
| Fiddle hostname without a client certificate | TLS connection rejected |
| Fiddle hostname with an untrusted certificate | TLS connection rejected |
| Mission execution of `return timer.getTime()` | Structured successful result |
| Direct external TCP 12080 and 12081 | Blocked |
| Direct external TCP 3001 and 8090 | Blocked |
| Main DCS dashboard HTTPS/login | Unchanged and functional |
| LSO dashboard HTTPS/API | Unchanged and functional |

Also confirm:

- Caddy logs do not contain the proxy token;
- DCS logs do not contain submitted Lua source;
- both Lua listeners remain on `127.0.0.1`;
- only TCP 80 and 443 are public.

## 14. Certificate Expiration and Renewal

| Certificate | Lifetime in this guide | Renewal responsibility |
| --- | --- | --- |
| Client CA certificate | 3,650 days (about ten years) | CA administrator |
| Operator client certificate | 90 days | CA administrator/operator |
| Public HTTPS certificate | Managed automatically by Caddy | Caddy |

Check a certificate's exact dates:

```powershell
& $OpenSSL x509 -in .\operator01.cert.pem -noout -subject -issuer -serial -dates
```

Issue a replacement operator certificate around 14 days before expiry. Install
and test the replacement before removing the old certificate/key.

If an operator private key is lost or suspected compromised, do not wait for
expiry. Disable the Fiddle site blocks if necessary, rotate the internal proxy
token, and replace the client CA plus all authorized client certificates. The
static Caddy trust pool does not provide individual online certificate
revocation by itself.

## 15. Troubleshooting

### `openssl` is not recognized

Use the full executable path through the `$OpenSSL` variable:

```powershell
$OpenSSL = 'C:\Program Files\Git\usr\bin\openssl.exe'
& $OpenSSL version
```

### `client-cert-ext.cnf` cannot be found

Download the individual non-secret file using the link near the start of this
guide and save it as `C:\Secure\DCSFiddleCA\client-cert-ext.cnf`. In PowerShell,
change to that directory and verify the file exists before repeating the full
signing command from Section 7:

```powershell
Set-Location -LiteralPath 'C:\Secure\DCSFiddleCA'
Test-Path -LiteralPath '.\client-cert-ext.cnf'
```

Expected result: `True`.

### `RandomNumberGenerator.Fill` does not exist

Windows PowerShell 5.1 does not provide that static method. Use the documented
`Create()` and `GetBytes()` token command in Section 4.

### Client certificate is rejected

Check:

- the GUI uses the matching `operator01.cert.pem` and `operator01.key.pem`;
- the certificate has not expired;
- `openssl verify -purpose sslclient` returns `OK`;
- Caddy reads `C:\Caddy\pki\fiddle-client-ca.cert.pem`;
- the operator certificate was signed by that exact CA.

### Lua backend returns HTTP 401

Caddy and `dcs-fiddle-config.lua` do not have identical proxy-token values, or
Caddy was reloaded without the service environment. Check the two server-side
locations without printing the token into logs, then restart the Caddy service
and DCS.

### Port 12080 or 12081 is not listening

Check the DCS log for configuration errors and confirm:

- `dcs-fiddle-server.lua` is in the DCS runtime account's `Scripts\Hooks`;
- `dcs-fiddle-config.lua` is in that account's `Scripts\DCSLuaRunner`;
- the config does not contain the placeholder token;
- DCS was restarted after the file changes;
- the server-side Mission Scripting requirements are configured.

### Caddy validation succeeds but the service does not start

Confirm the service account can read the active Caddyfile and public CA
certificate. Confirm the NSSM Environment tab contains the unquoted
`DCS_FIDDLE_PROXY_TOKEN=...` entry and restart the service. Restore the backed-up
Caddyfile if the problem persists.

## 16. Rollback

If the Fiddle endpoints fail but both dashboards remain healthy:

1. Stop new GUI requests.
2. Restore or remove only the two Fiddle site blocks.
3. Validate the complete Caddyfile.
4. Restart the Caddy service.
5. Keep TCP 12080 and 12081 externally blocked.

If any existing Caddy-hosted dashboard is affected, restore the entire
known-good Caddyfile, validate it, restart Caddy, and repeat both dashboard
smoke tests.
