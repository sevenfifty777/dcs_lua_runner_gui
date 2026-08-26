# DCS Lua Runner GUI Security and Protocol Modernization Plan

Date: 2026-08-26
Status: Proposed; production Caddy topology and firewall posture confirmed;
implementation not started
Primary repository: `C:\Users\thierry\Documents\GitHub\dcs_lua_runner_gui`

## 1. Overview

The DCS Lua Runner GUI is a Windows application that sends Lua source code to a
LuaSocket HTTP server running inside DCS World. The server executes the code in
either the Mission scripting environment or the Hooks/GameGUI environment and
returns a JSON-encoded result.

This project is intentionally an arbitrary-code-execution tool. Its legitimate
purpose is DCS mission development, inspection, debugging, and administration.
That purpose cannot be preserved while treating submitted Lua as untrusted.
The security objective is therefore to ensure that only explicitly authorized
clients can reach the execution endpoint, that the transport cannot block the
DCS simulation thread, and that secrets and submitted Lua are not leaked through
configuration files, URLs, logs, or release artifacts.

The target production topology keeps Caddy as the public HTTPS boundary. Caddy
will authenticate clients, and the DCS Lua servers will listen only on a private
loopback interface. The legacy base64-in-GET protocol will be replaced with a
bounded, versioned POST protocol.

## 2. Confirmed Decisions

The following decisions are part of this plan:

1. Caddy remains responsible for public HTTPS termination.
2. The existing Caddy certificate-issuance mechanism remains unchanged.
3. The optional `caddy-dns/route53` module will **not** be installed or used at
   this stage.
4. Existing AWS Route53 A records remain unchanged.
5. Public client authentication should be implemented at Caddy, not with
   custom cryptography inside DCS Lua.
6. Mutual TLS (mTLS) is the recommended production authentication method.
7. Caddy will authenticate itself to the private Lua backend with a separate,
   high-entropy internal proxy token.
8. The Lua listeners will bind to `127.0.0.1` when Caddy and DCS run on the same
   host.
9. Submitted Lua will be carried in an HTTPS POST body, not in a URL.
10. Legacy GET support will be temporary, explicitly configured, and disabled
    after migration.
11. No working credential, private key, or internal token may be committed or
    copied into a release directory.
12. Caddy, both dashboards, and both DCS Lua listeners run on the same Windows
    server and use hostname-based routing.
13. The confirmed public-to-private mappings are:
    - `redacted-dashboard1.example.com` to `127.0.0.1:3001`;
    - `lso-board.example.com` to `127.0.0.1:8090`;
    - `mission.example.com` to `127.0.0.1:12080`;
    - `dcs-lua-gui.example.com` to `127.0.0.1:12081`.
14. The server firewall already permits inbound TCP 80 and 443 only. Direct
    external access to TCP 3001, 8090, 12080, and 12081 is blocked and must
    remain blocked throughout deployment and rollback.
15. Lua Runner mTLS, request filtering, and proxy-token headers will be scoped
    exclusively to `mission.example.com` and `dcs-lua-gui.example.com`. They
    must not be applied to either dashboard hostname.

If Caddy and DCS are not on the same host, decision 8 changes to a private
interface plus firewall rules that permit connections only from the Caddy host.
All other security layers remain applicable.

## 3. Existing Architecture

```text
main.py
  -> gui/main_window.py
  -> core/dcs_client.py
  -> HTTP GET /<base64-lua>?env=default
  -> dcs-fiddle-server.lua
       -> port 12080: Mission environment
       -> port 12081: Hooks/GameGUI environment
  -> loadstring() or net.dostring_in()
  -> custom JSON response
  -> GUI Results tab
```

The environment selected by the Python application is currently determined by
the destination port. The Python client always sends `env=default`:

- port 12080 executes `default` inside the Mission environment;
- port 12081 executes `default` inside the Hooks/GameGUI environment.

The Hooks copy of the Lua script starts the GUI listener and uses
`onSimulationStart` to load the same script into the Mission environment. The
Mission copy starts its listener and polls it through `timer.scheduleFunction`.
This lifecycle must be preserved.

## 4. Target Architecture

```text
DCS Lua Runner GUI
  | HTTPS
  | verifies Caddy's public server certificate
  | presents an mTLS client certificate
  v
Caddy public endpoint on TCP 443
  | validates the client certificate
  | accepts only the versioned API route and method
  | applies request-size limits
  | removes untrusted authentication headers
  | adds an internal proxy token
  v
127.0.0.1:12080                  127.0.0.1:12081
Mission Lua server               Hooks/GameGUI Lua server
  |                                |
  +------ bounded nonblocking HTTP state machine ------+
                           |
                           v
                 validated Lua execution
                           |
                           v
                 structured JSON response
```

### 4.1 Security boundaries

The layers have separate responsibilities:

| Layer | Responsibility |
| --- | --- |
| Public DNS | Direct the configured hostname to Caddy |
| Caddy HTTPS | Encrypt transport and prove server identity |
| Caddy mTLS | Authenticate the Lua Runner client |
| Firewall | Permit public TCP 80/443 and deny direct external access to TCP 3001, 8090, 12080, and 12081 |
| Loopback binding | Keep the DCS HTTP service off public interfaces |
| Internal proxy token | Ensure the Lua endpoint accepts only the configured proxy |
| Lua protocol parser | Enforce method, path, size, timeout, and schema limits |
| DCS execution handler | Select the environment and return structured results |

## 5. Findings Addressed by This Plan

The implementation must address all of the following findings from the initial
review:

- public binding to `0.0.0.0`;
- placeholder credentials in the Lua source;
- plaintext Basic Authentication inside Lua;
- local GUI requests not authenticating while the Lua server requires auth;
- spoofable Host-header local bypass;
- code placed in GET URLs;
- code written verbatim to DCS logs;
- blocking reads and writes on accepted LuaSocket clients;
- no request, header, body, or response limits;
- incomplete HTTP responses without `Content-Length`;
- case-sensitive HTTP header parsing;
- missing or inaccurate error statuses;
- unreliable handling of `net.dostring_in` failures;
- custom JSON collisions and silent key loss;
- invalid Python JSON-to-Lua formatting;
- Tkinter updates performed from a worker thread;
- plaintext application passwords in settings files;
- inconsistent local HTTPS status and execution behavior;
- unused dependencies and dead code;
- no automated tests;
- root and packaged Lua scripts diverging;
- local non-placeholder settings being at risk of accidental distribution.

## 6. Phase 1: Deployment Inventory and Rollback

No production configuration will be changed before this phase is complete.

### 6.1 Required inventory

Record:

- active Caddy version;
- active Caddy executable path and SHA-256 hash;
- active Caddyfile path;
- public Mission hostname, confirmed as `mission.example.com`;
- public GUI hostname, confirmed as `dcs-lua-gui.example.com`;
- dashboard hostname, confirmed as `redacted-dashboard1.example.com`;
- LSO dashboard hostname, confirmed as `lso-board.example.com`;
- current certificate issuer and expiration;
- current Caddy-to-DCS upstream routes;
- whether Caddy and DCS run on the same host;
- Windows service accounts for Caddy and DCS;
- current firewall rules confirming that TCP 80/443 are allowed and TCP 3001,
  8090, 12080, and 12081 are blocked externally;
- installed Lua server path under Saved Games;
- hash of the deployed Lua server;
- hash of both repository Lua copies;
- current application executable and settings locations.

### 6.2 Read-only verification commands

Representative commands include:

```powershell
caddy version
caddy list-modules
caddy validate --config C:\path\to\Caddyfile
Get-FileHash C:\path\to\caddy.exe -Algorithm SHA256
netstat -ano | findstr ":80 :443 :3001 :8090 :12080 :12081"
```

Exact paths must be resolved from the active deployment before commands are
executed.

### 6.3 Rollback package

Create a recoverable backup containing:

- Caddy executable;
- Caddyfile;
- deployed Lua server;
- current GUI executable;
- non-secret application settings;
- firewall-rule export;
- exact service restart/reload commands.

Secrets must not be copied into the repository or documentation.

### 6.4 Acceptance criteria

- The actual public and backend ports are confirmed.
- The owning processes are confirmed.
- Firewall exports confirm that only TCP 80/443 are publicly allowed and that
  TCP 3001, 8090, 12080, and 12081 remain externally blocked.
- The deployed Lua file is identified.
- A tested Caddy rollback command is documented.
- A tested application/Lua rollback procedure is documented.

## 7. Phase 2: Lua Server Configuration Redesign

Primary file:

```text
dcs-fiddle-server.lua
```

### 7.1 External configuration

Move deployment-specific configuration to an untracked file such as:

```text
Saved Games\DCS\Scripts\Hooks\dcs-fiddle-config.lua
```

Provide only a tracked example:

```text
dcs-fiddle-config.lua.example
```

The real configuration will define:

- bind address;
- Mission port;
- GUI port;
- internal proxy token;
- request-header limit;
- request-body limit;
- response-size limit;
- maximum clients;
- client deadline;
- log level;
- legacy protocol flag.

### 7.2 Fail-closed behavior

The server must refuse to start if:

- the configuration cannot be loaded;
- the internal proxy token is missing;
- the token is still an example value;
- a port is outside the valid range;
- a size or timeout limit is invalid;
- production mode attempts to bind to a public interface without an explicit
  override.

No default username, password, or production token will exist in source.

### 7.3 Mission bootstrap

The Hooks environment will load and validate configuration once. When the
mission starts, it will safely load the Mission copy of the server with the
validated configuration.

The bootstrap must:

- quote Windows paths safely;
- support spaces and apostrophes in paths;
- avoid logging the internal proxy token;
- avoid leaving mutable public configuration globals;
- preserve the documented `onSimulationStart` callback lifecycle.

### 7.4 Acceptance criteria

- Source contains no working credential or token.
- Missing configuration stops startup clearly.
- Both environments use the intended ports.
- Mission bootstrap works with representative Windows paths.
- The server binds to loopback in production.

## 8. Phase 3: Versioned HTTP Protocol

### 8.1 Endpoint

Introduce:

```http
POST /v1/execute?env=default HTTP/1.1
Content-Type: text/plain; charset=utf-8
Content-Length: <bytes>
X-DCS-Proxy-Token: <internal-token>
X-Request-ID: <identifier>

<raw UTF-8 Lua source>
```

Base64 is unnecessary because the Lua source is carried in the request body.

### 8.2 Request validation

The server will:

- accept only `POST` for `/v1/execute`;
- require a supported HTTP version;
- normalize header names to lowercase;
- reject malformed or duplicate security-sensitive headers;
- require one valid `Content-Length`;
- reject chunked transfer encoding initially;
- enforce a configurable body limit;
- validate UTF-8 where practical;
- require the internal proxy token;
- allow only known execution environments;
- require or generate a bounded request ID;
- ignore request bodies for rejected requests only after safely closing the
  connection.

Recommended initial limits:

| Limit | Initial value |
| --- | --- |
| Request line | 2 KiB |
| Combined headers | 8 KiB |
| Lua body | 256 KiB |
| JSON response | 2 MiB |
| Concurrent connections | 8 |
| Incomplete request deadline | 5 seconds |

These values must be confirmed against actual usage before implementation.

### 8.3 Health endpoint

Add:

```http
GET /healthz
```

It returns only:

- protocol version;
- environment name;
- readiness state.

It must not return mission names, player data, paths, credentials, code, or DCS
configuration details. Whether it requires mTLS remains a Caddy decision; it
must always require the internal proxy token at the Lua layer.

### 8.4 Response schema

Success:

```json
{
  "ok": true,
  "request_id": "example-id",
  "result": null
}
```

Failure:

```json
{
  "ok": false,
  "request_id": "example-id",
  "error": {
    "kind": "runtime_error",
    "message": "sanitized error message"
  }
}
```

Supported error kinds should include:

- `bad_request`;
- `authentication_failed`;
- `unsupported_method`;
- `unsupported_environment`;
- `payload_too_large`;
- `server_busy`;
- `syntax_error`;
- `runtime_error`;
- `serialization_error`;
- `internal_error`.

### 8.5 HTTP response requirements

Every response must include:

- valid status line;
- `Content-Type: application/json; charset=utf-8`;
- `Content-Length`;
- `Connection: close`;
- `Cache-Control: no-store`;
- request ID where available.

CORS will be disabled by default. Browser compatibility will not override the
security model.

### 8.6 Legacy protocol

During migration only:

- legacy GET may be enabled by explicit configuration;
- it remains loopback-only;
- it is marked deprecated in logs without logging source code;
- its removal date is recorded before deployment.

After the new GUI is deployed and validated, legacy GET must be disabled and
the base64 implementation removed.

## 9. Phase 4: Nonblocking LuaSocket Server

### 9.1 State machine

Replace the synchronous one-request handler with bounded connection states:

```text
accepted
  -> reading_headers
  -> reading_body
  -> ready_to_execute
  -> writing_response
  -> closed
```

Each client record contains:

- socket;
- peer address;
- receive buffer;
- send buffer;
- send offset;
- parsed headers;
- expected content length;
- state;
- creation time;
- deadline;
- request ID.

### 9.2 Nonblocking operation

- Set every accepted socket to nonblocking mode immediately.
- Read a bounded amount per server tick.
- Preserve partial reads rather than treating them as errors.
- Preserve partial writes and resume at the next tick.
- Close expired, malformed, or oversized connections.
- Cap active clients.
- Never wait indefinitely for a line, body, or send completion.

### 9.3 Execution serialization

DCS execution remains on the DCS thread. Only one submitted Lua chunk will be
executed at a time. Additional ready requests receive `429 Server Busy` rather
than creating concurrent mutation of DCS state.

The Mission server will retain `timer.scheduleFunction` polling. The Hooks
server will retain `onSimulationFrame`, with minimal work performed per frame.

### 9.4 Shutdown and cleanup

- Close all client sockets during server shutdown/reload when callbacks permit.
- Close the listening socket before rebinding.
- Remove expired client records.
- Ensure errors cannot leave unreachable open sockets.

### 9.5 Acceptance criteria

- An incomplete TCP client cannot freeze DCS.
- Partial request delivery succeeds within the deadline.
- Partial response sends complete correctly.
- More than the maximum clients are rejected cleanly.
- Malformed connections are closed without breaking later requests.

## 10. Phase 5: Authentication and Secret Handling

### 10.1 Public authentication: mTLS

Caddy will require and verify a client certificate for the Lua Runner endpoints.

Recommended model:

- a dedicated private CA for Lua Runner clients;
- one client certificate per workstation or operator;
- distinct certificate serial numbers;
- documented issuance, expiration, renewal, and revocation;
- server certificate validation always enabled in the client;
- no `verify=False` option.

The public server certificate managed by Caddy is separate from the private
client-authentication CA.

### 10.2 Backend authentication

Caddy will overwrite the upstream header:

```http
X-DCS-Proxy-Token: <random internal value>
```

The Lua backend will reject requests without an exact valid token. It will not
trust `Host`, `X-Forwarded-Host`, or any claimed local address header.

The token must:

- contain at least 256 bits of randomness;
- be generated with a cryptographically secure tool;
- be stored outside Git;
- be available to Caddy through its service configuration;
- be available to DCS through the untracked Lua configuration;
- be rotatable independently from client certificates;
- never appear in logs or diagnostics.

### 10.3 Caddy upstream behavior

Caddy configuration will:

- accept only the documented route and method;
- remove incoming `Authorization` if unused;
- overwrite the proxy-token header;
- proxy Mission and GUI to separate loopback ports;
- preserve the request body and content length;
- avoid logging request bodies;
- avoid logging credentials;
- return a generic response for unknown routes.

### 10.4 Concrete Caddy configuration step

The repository baseline at `Caddy/Caddyfile` has four independent hostname site
blocks and matches the supplied production layout. Phase 1 must still compare
its hash with the active server Caddyfile before treating the repository copy as
the deployment source:

| Public hostname | Backend | Purpose | Planned Caddy authentication |
| --- | --- | --- | --- |
| `redacted-dashboard1.example.com` | `127.0.0.1:3001` | Main DCS web dashboard | Preserve existing application authentication |
| `lso-board.example.com` | `127.0.0.1:8090` | LSO greenie-board dashboard | Preserve current behavior; audit separately if required |
| `mission.example.com` | `127.0.0.1:12080` | Mission Lua execution | Require and verify an mTLS client certificate |
| `dcs-lua-gui.example.com` | `127.0.0.1:12081` | Hooks/GameGUI Lua execution | Require and verify an mTLS client certificate |

The two dashboard blocks must not import the Lua Runner TLS client-authentication
policy, Lua API route restrictions, `Authorization` removal, or internal proxy
token. The dashboards have independent application behavior, including the main
dashboard's login, OAuth callback, authenticated APIs, and streaming responses.

The implementation will replace ambiguous `localhost` upstreams with explicit
IPv4 loopback addresses. The planned Caddyfile shape is:

```caddyfile
redacted-dashboard1.example.com {
	reverse_proxy 127.0.0.1:3001
}

lso-board.example.com {
	reverse_proxy 127.0.0.1:8090
}

mission.example.com {
	tls {
		client_auth {
			mode require_and_verify
			trust_pool file C:/Caddy/pki/fiddle-client-ca.pem
		}
	}

	@execute {
		method POST
		path /v1/execute
	}

	@health {
		method GET
		path /healthz
	}

	handle @execute {
		request_body {
			max_size 256KB
		}
		reverse_proxy 127.0.0.1:12080 {
			header_up -Authorization
			header_up X-DCS-Proxy-Token {env.DCS_FIDDLE_PROXY_TOKEN}
		}
	}

	handle @health {
		reverse_proxy 127.0.0.1:12080 {
			header_up -Authorization
			header_up X-DCS-Proxy-Token {env.DCS_FIDDLE_PROXY_TOKEN}
		}
	}

	handle {
		respond "Not found" 404
	}
}

dcs-lua-gui.example.com {
	tls {
		client_auth {
			mode require_and_verify
			trust_pool file C:/Caddy/pki/fiddle-client-ca.pem
		}
	}

	@execute {
		method POST
		path /v1/execute
	}

	@health {
		method GET
		path /healthz
	}

	handle @execute {
		request_body {
			max_size 256KB
		}
		reverse_proxy 127.0.0.1:12081 {
			header_up -Authorization
			header_up X-DCS-Proxy-Token {env.DCS_FIDDLE_PROXY_TOKEN}
		}
	}

	handle @health {
		reverse_proxy 127.0.0.1:12081 {
			header_up -Authorization
			header_up X-DCS-Proxy-Token {env.DCS_FIDDLE_PROXY_TOKEN}
		}
	}

	handle {
		respond "Not found" 404
	}
}
```

This is a deployment template, not a source of secret values. Before use:

1. Confirm the active Caddy version supports the shown `client_auth`,
   `trust_pool file`, and `request_body` syntax. `request_body max_size` requires
   Caddy 2.10.0 or later. If the installed version is older, retain the mandatory
   Lua-layer request-size limit and evaluate a separately approved Caddy upgrade.
2. Replace `C:/Caddy/pki/fiddle-client-ca.pem` with the resolved ACL-protected
   client-CA certificate path. The CA private key must not be stored on the DCS
   server unless that server is deliberately chosen as the issuing system.
3. Set `DCS_FIDDLE_PROXY_TOKEN` in the Caddy Windows service environment or its
   approved secret-loading mechanism. Never put the token value in the tracked
   Caddyfile, this plan, command history, or logs.
4. Ensure the untracked DCS Lua configuration contains the same internal token
   and fails closed if it is absent or empty.
5. Back up the active Caddyfile and record its path and hash.
6. Run `caddy validate --config C:\path\to\Caddyfile` using the exact production
   Caddy executable and service environment.
7. Confirm the existing dashboard routes before reload.
8. Apply the validated file with `caddy reload --config C:\path\to\Caddyfile`.
   Do not stop and restart Caddy for an ordinary configuration update.
9. Run the Caddy and dashboard non-regression tests in Phase 12 immediately after
   reload.

The firewall is already correctly positioned for this topology: inbound TCP 80
and 443 are allowed, while direct external access to TCP 3001, 8090, 12080, and
12081 is blocked. The deployment must verify and preserve those rules; it must
not temporarily open a backend port for testing or rollback.

### 10.5 Basic Authentication fallback

If mTLS is rejected for operational reasons, the fallback is Caddy Basic
Authentication over HTTPS using:

- an Argon2id password hash in Caddy;
- a randomly generated high-entropy password;
- Windows Credential Manager on the GUI machine;
- the same loopback and internal-token protections.

Plaintext Basic Authentication inside Lua will not remain as the production
mechanism.

### 10.6 Route53 decision

The `caddy-dns/route53` module is deferred and out of scope. This plan assumes
Caddy's existing certificate issuance continues to work with the current A
records and HTTPS configuration.

No AWS IAM identity, Route53 TXT automation, wildcard certificate migration, or
custom Caddy binary will be introduced in this implementation.

## 11. Phase 6: DCS Execution and Logging

### 11.1 Execution behavior

For `env=default`:

- compile with `loadstring`;
- distinguish syntax errors from runtime errors;
- execute through protected calls;
- capture the first return value;
- serialize the result through the new encoder.

For explicitly supported non-default environments:

- validate the environment against an allowlist;
- call `net.dostring_in` only where supported;
- treat reported DCS errors as failed HTTP requests;
- do not return status 200 for execution failure.

### 11.2 Logging policy

Logs may contain:

- request ID;
- target environment;
- peer classification;
- request size;
- duration;
- success or error category;
- server startup and shutdown state.

Logs must not contain:

- submitted Lua source;
- proxy tokens;
- passwords;
- certificate private keys;
- Authorization headers;
- player-identifying data unless the submitted script explicitly returns it to
  the authenticated client.

### 11.3 Residual execution risk

An authenticated request can still:

- mutate the mission;
- read available DCS state;
- invoke permitted filesystem or network APIs;
- terminate or destabilize scripts;
- enter an infinite loop and freeze DCS.

Client and network timeouts cannot cancel Lua that has already begun executing.
Instruction-budget enforcement may be investigated separately, but it must not
be claimed as safe until verified against DCS's embedded Lua runtime and native
DCS API calls.

## 12. Phase 7: Result Serialization

### 12.1 Remove unused codecs

After legacy protocol removal:

- remove the base64 encoder and decoder;
- remove the unused JSON decoder;
- keep the JSON encoder private rather than global where practical;
- remove dead helpers and unused client-ID code.

### 12.2 Typed mixed-key tables

Sequential arrays may remain JSON arrays. String-key tables may remain JSON
objects. Tables that cannot be represented without ambiguity will use an
explicit envelope:

```json
{
  "__dcs_type": "table",
  "entries": [
    {
      "key_type": "number",
      "key": 1,
      "value": "first"
    },
    {
      "key_type": "string",
      "key": "_name",
      "value": "example"
    }
  ]
}
```

This avoids numeric/string collisions and silent underscore-key loss.

### 12.3 Special values

Define and test behavior for:

- nil/no return;
- empty tables;
- sparse arrays;
- functions;
- userdata;
- threads;
- NaN and infinities;
- circular references;
- excessive nesting.

Unsupported values should return a structured serialization error or an
explicit typed representation. They must not be silently discarded.

### 12.4 Determinism and limits

- Sort string object keys for stable output where practical.
- Impose a maximum nesting depth.
- Impose a maximum encoded-response size.
- Track circular references with path information.

## 13. Phase 8: Python Client Modernization

Primary file:

```text
core/dcs_client.py
```

### 13.1 Connection profiles

Introduce a typed connection profile containing:

- profile name;
- Mission URL;
- GUI URL;
- authentication mode;
- client certificate path;
- client private-key path;
- optional private CA bundle path;
- connect timeout;
- response timeout;
- maximum accepted response size.

Remote profiles must use HTTPS. Loopback HTTP may exist only as an explicitly
enabled development profile.

### 13.2 HTTP client

- Use a persistent `requests.Session`.
- Send raw Lua with `POST`.
- Set the expected content type.
- Generate a request ID.
- Present the configured client certificate and key.
- Keep server-certificate verification enabled.
- Use separate connect and read timeouts.
- Validate response status, content type, size, and schema.
- Never automatically retry execution requests.
- Produce specific connection, TLS, authentication, timeout, protocol, syntax,
  runtime, and serialization errors.

### 13.3 Client certificate storage

Python Requests supports PEM client certificates but requires an unencrypted
private key. The first implementation may use an ACL-protected PEM key file,
provided that:

- only the intended Windows user can read it;
- its path, not its contents, is stored in settings;
- permission validation is included in setup diagnostics;
- the limitation is clearly documented.

Encrypted PKCS#12 or Windows Certificate Store integration is a separate design
decision because it may require a new dependency or a different HTTP backend.

### 13.4 Lua result formatting

Replace the current string-replacement formatter with a recursive formatter
that produces valid Lua syntax for:

- strings with correct escaping;
- booleans and nil;
- finite numbers;
- sequential arrays;
- string-key tables;
- typed mixed-key tables.

## 14. Phase 9: Settings Security

Primary file:

```text
core/settings_manager.py
```

### 14.1 Versioned settings schema

Add a schema version and validated profile list. Store only non-secret values:

- profile names;
- endpoint URLs;
- certificate and CA paths;
- UI preferences;
- timeout and display preferences.

Do not store:

- passwords;
- internal proxy tokens;
- private-key contents;
- AWS credentials.

### 14.2 Migration

When old settings are detected:

- import addresses, ports, environment, and display preferences;
- construct candidate HTTPS URLs;
- do not automatically carry forward plaintext passwords;
- warn the user that old password authentication has been removed;
- create a backup without displaying its contents;
- require validation before saving the new schema.

### 14.3 Storage location and writes

- Store user settings in a deterministic per-user application-data directory.
- Do not depend on the process working directory.
- Write UTF-8 explicitly.
- Validate types and ranges.
- Save atomically through a temporary file and replacement.
- Apply restrictive permissions where Windows supports them.

## 15. Phase 10: GUI Corrections

Primary file:

```text
gui/main_window.py
```

### 15.1 Connection interface

- Replace the Local/Remote toggle with a connection-profile selector.
- Preserve Mission/GUI target selection.
- Add certificate, private-key, and CA file selectors.
- Add a non-destructive Test Connection action using `/healthz`.
- Display endpoint, HTTPS verification, mTLS status, and target environment.
- Clearly mark development-only direct HTTP profiles.

### 15.2 Thread safety

- Perform HTTP work in a background worker.
- Perform every Tkinter widget update through the main event loop.
- Prevent simultaneous executions from a single window.
- Handle application closure while a request is active.
- Re-enable controls through one main-thread completion path.

### 15.3 Settings and file behavior

- Validate settings without requiring users to save before testing.
- Track the current editor filename.
- Make `Ctrl+S` save the current file.
- Keep Save As separate.
- Report file errors without bare exception handlers.

### 15.4 Syntax highlighting

- Decide whether to keep the current regex highlighter or actually use Pygments.
- If the regex implementation remains, remove the unused Pygments dependency.
- Prevent later syntax tags from overriding comments and strings incorrectly.
- Avoid full-document rescans on every keystroke for large scripts.

## 16. Phase 11: Error Handling and Code Quality

- Add useful type hints to Python functions.
- Replace broad and bare exception handlers with specific handling.
- Avoid silently swallowing clipboard and UI errors.
- Introduce structured Python logging without secrets.
- Remove unused imports, globals, constants, and functions.
- Break large GUI methods into focused components.
- Separate protocol, transport, execution, serialization, and UI responsibilities.
- Preserve existing behavior unless a documented migration changes it.

## 17. Phase 12: Automated Testing

### 17.1 Python unit tests

Cover:

- Mission and GUI endpoint selection;
- remote HTTPS enforcement;
- certificate and key validation;
- POST request construction;
- request IDs;
- server-certificate verification;
- authentication failures;
- connect and read timeouts;
- malformed and oversized responses;
- status/error mapping;
- no automatic execution retry;
- settings migration;
- atomic settings writes;
- valid recursive Lua formatting;
- typed mixed-key result handling;
- main-thread GUI scheduling.

### 17.2 Lua unit tests

Use a dependency-free Lua 5.1-compatible test harness for pure functions:

- request-line parsing;
- case-insensitive headers;
- duplicate header rejection;
- content-length validation;
- body-size limits;
- proxy-token verification;
- environment allowlist;
- partial reads;
- partial writes;
- connection deadlines;
- client-cap enforcement;
- response construction;
- string escaping;
- arrays and objects;
- mixed-key tables;
- circular-reference detection;
- excessive-depth detection;
- error classification.

DCS-specific calls should be behind small adapters so pure logic can run outside
DCS.

### 17.3 Caddy tests

- Active Caddyfile validates.
- `redacted-dashboard1.example.com` still reaches `127.0.0.1:3001` without a
  Lua Runner client certificate.
- Main dashboard health, password login, Discord OAuth initiation/callback,
  Bearer/cookie-authenticated requests, and SSE streams still behave as before.
- `lso-board.example.com` still reaches `127.0.0.1:8090`, and `/` plus
  `/api/passes` retain their previous behavior.
- Neither dashboard upstream receives `X-DCS-Proxy-Token` or Lua Runner header
  rewriting.
- Missing client certificate is rejected.
- Untrusted client certificate is rejected.
- Trusted client certificate reaches `/healthz`.
- Unknown routes return a generic response.
- GET execution is rejected.
- Oversized requests are rejected.
- Incoming proxy-token headers are overwritten.
- Caddy reaches the correct loopback port for each environment.
- Caddy access logs do not contain request bodies or secrets.

### 17.4 Security tests

- Only TCP 80 and 443 are reachable externally.
- TCP 3001, 8090, 12080, and 12081 are unreachable externally before, during,
  and after deployment.
- `mission.example.com` and `dcs-lua-gui.example.com` require a trusted client
  certificate, while neither dashboard hostname unexpectedly requires one.
- A forged Host header grants no bypass.
- A forged `X-Forwarded-Host` grants no bypass.
- A forged internal token is rejected.
- A slow/incomplete connection cannot block DCS.
- Lua source does not appear in URLs or normal logs.
- Release artifacts contain no real settings or credentials.

### 17.5 Live DCS validation

Perform non-destructive checks in both environments:

```lua
return timer.getTime()
```

Use an appropriate GameGUI time query for the Hooks environment after checking
the DCS API reference.

Also validate:

- syntax error;
- runtime error;
- no return value;
- string, number, and boolean returns;
- nested table;
- empty table;
- sparse table;
- mixed numeric/string keys;
- large allowed result;
- rejected oversized result;
- mission change;
- simulation pause/resume;
- DCS restart;
- Caddy reload;
- client-certificate rotation;
- internal-token rotation.

## 18. Phase 13: Dependency and Build Review

### 18.1 Python dependencies

- Replace open-ended application dependency ranges with the repository's chosen
  reproducible versioning policy.
- Commit an appropriate lock or constraints file.
- Remove Pygments if unused.
- Do not add a certificate-storage dependency without checking its maintenance,
  release age, install behavior, and current advisories.
- Run the selected Python dependency audit.

### 18.2 PyInstaller

- Rebuild only after source validation succeeds.
- Confirm the executable uses the same source revision.
- Record Python and PyInstaller versions.
- Verify the executable signature/hash as applicable.
- Test settings storage from the packaged executable.

### 18.3 Distribution consistency

The distribution process must:

- delete and recreate only the exact versioned distribution directory;
- copy the root Lua file after tests pass;
- verify root and packaged Lua hashes match;
- copy only settings templates;
- reject real settings files;
- scan the package for credential-like values;
- include the security and migration documentation;
- run a packaged smoke test.

## 19. Phase 14: Documentation

Update:

- `README.md`;
- `QUICK_START.md`;
- distribution installation guide;
- settings template.

Add:

```text
docs/SECURITY_ARCHITECTURE.md
docs/PROTOCOL_V2.md
docs/CADDY_MTLS_SETUP.md
docs/MIGRATION_V1_TO_V2.md
docs/TEST_AND_VALIDATION.md
```

Documentation must cover:

- threat model;
- architecture and trust boundaries;
- client certificate issuance;
- certificate renewal and revocation;
- internal-token generation and rotation;
- Windows ACL configuration;
- firewall configuration;
- Caddy validation and reload;
- DCS installation;
- settings migration;
- health checks;
- log locations and safe diagnostics;
- rollback;
- residual arbitrary-code-execution risk.

## 20. Phase 15: Staged Deployment

### 20.1 Preparation

1. Complete backups and rollback documentation.
2. Export and verify the existing firewall rules showing public TCP 80/443 and
   denied external TCP 3001, 8090, 12080, and 12081.
3. Record baseline health, authentication, OAuth, API, and streaming behavior
   for both dashboards.
4. Generate the private client-authentication CA.
5. Issue the first client certificate.
6. Generate the internal proxy token.
7. Store secrets with appropriate Windows ACLs.
8. Build and test the updated GUI and Lua server.

### 20.2 Compatibility stage

1. Deploy the new Lua server with version 2 enabled.
2. Keep legacy GET temporarily available only if required for rollback.
3. Keep all DCS listeners private.
4. Apply the four-host Caddy configuration from Phase 5, adding mTLS and the
   proxy token only to the two `fiddle` hostnames.
5. Validate the full Caddyfile before reload.
6. Reload Caddy gracefully.
7. Re-run both dashboard baselines and stop the rollout if either changes.
8. Test both Lua Runner `/healthz` endpoints with the client certificate.

### 20.3 Application cutover

1. Deploy the updated Python application or executable.
2. Import non-secret settings into a connection profile.
3. Validate Mission execution.
4. Validate GUI execution.
5. Confirm errors are structured correctly.
6. Confirm logs contain no submitted source or secrets.

### 20.4 Lockdown

1. Disable legacy GET.
2. Remove old Lua Basic Authentication credentials.
3. Remove the Host-header bypass.
4. Confirm that TCP 3001, 8090, 12080, and 12081 remain denied externally and
   that only TCP 80/443 are public.
5. Rotate any credentials previously present in local distribution settings.
6. Rebuild the release package.
7. Verify package contents and hashes.

### 20.5 Observation period

Retain rollback artifacts through multiple successful DCS sessions, including:

- mission load and unload;
- mission restart;
- DCS restart;
- Caddy reload;
- main dashboard login and SSE reconnection;
- LSO dashboard refresh and `/api/passes` retrieval;
- application restart.

## 21. Rollback Strategy

Rollback must not depend on editing multiple live files under pressure.

Recommended rollback sequence:

1. Stop new client requests.
2. Restore the previous Caddyfile.
3. Validate and reload Caddy.
4. Restore the previous Lua server.
5. Restart DCS if the Lua hook cannot be safely reloaded.
6. Restore the previous GUI executable if necessary.
7. Verify only the previous endpoints are active.
8. Preserve failed-version logs after checking that they contain no secrets.

Rollback must not reopen TCP 3001, 8090, 12080, or 12081 publicly. If
compatibility is needed, route the old protocol through Caddy under the previous
authentication policy. Restoring the Caddyfile must not change the established
main-dashboard or LSO-dashboard routes.

## 22. Acceptance Criteria for Completion

The modernization is complete only when all of these are true:

- Caddy is the only public network entry point, on TCP 80 and 443.
- TCP 3001, 8090, 12080, and 12081 remain externally blocked.
- The main dashboard and LSO dashboard continue to work through their existing
  dedicated hostnames without inheriting Lua Runner authentication or headers.
- DCS Lua ports are loopback-only or restricted exclusively to the Caddy host.
- Remote execution requires a trusted client certificate or an explicitly
  approved strong fallback.
- Lua validates a separate internal proxy token.
- No real credential exists in tracked source or release artifacts.
- Lua source is never placed in a URL.
- Lua source and authentication data are absent from normal logs.
- Slow and incomplete network clients cannot block DCS.
- Request headers, bodies, clients, deadlines, nesting, and responses are
  bounded.
- HTTP methods, paths, headers, statuses, and response framing are valid.
- Mission and GUI failures produce accurate structured errors.
- Mixed-key tables are encoded without collision or silent data loss.
- Python renders valid Lua results.
- Tkinter widgets are updated only on the main thread.
- Old plaintext settings are migrated without retaining the password.
- Automated unit and protocol tests pass.
- Caddy security tests pass.
- Live Mission and GUI tests pass.
- Root and packaged Lua files are identical.
- Rollback has been documented and exercised.

## 23. Out of Scope

The following work is explicitly out of scope for this implementation:

- installing or configuring `caddy-dns/route53`;
- changing Route53 A records;
- migrating to wildcard certificates;
- replacing Caddy's current public certificate issuer;
- implementing cryptographic algorithms in Lua;
- making arbitrary submitted Lua safe;
- guaranteeing cancellation of Lua already executing inside DCS;
- adding general DCS gameplay or mission-management features;
- replacing Caddy with another reverse proxy;
- broad GUI redesign unrelated to security and reliability;
- silently changing unrelated repository formatting.

## 24. Open Deployment Questions

The following deployment facts are now confirmed:

- Caddy and all four upstream services run on the same Windows host.
- Caddy uses a separate hostname for every service.
- The Mission and Hooks/GameGUI public hostnames are `mission.example.com` and
  `dcs-lua-gui.example.com`.
- The two dashboard hostnames are `redacted-dashboard1.example.com` and
  `lso-board.example.com`.
- Only TCP 80/443 are publicly allowed; TCP 3001, 8090, 12080, and 12081 are
  externally blocked.

These remaining questions must be answered during Phase 1 because they affect
the final configuration but not the overall architecture:

1. What exact Caddy version and service environment are active, and does that
   version support every directive in the proposed template?
2. Is an ACL-protected unencrypted PEM client key acceptable for the first mTLS
   implementation?
3. How many separate GUI workstations or operators need certificates?
4. What request and response sizes are required by real Lua workflows?
5. Is a short legacy GET compatibility window required?
6. Should `/healthz` require mTLS publicly, or be restricted by another Caddy
   policy?

Recommended defaults are: same-host loopback proxying, separate Mission and GUI
hostnames, mTLS on every endpoint including health, one certificate per client,
256 KiB requests, 2 MiB responses, and the shortest practical legacy window.

## 25. Authoritative References

- [Caddy TLS and client authentication](https://caddyserver.com/docs/caddyfile/directives/tls)
- [Caddy reverse proxy and upstream header handling](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Caddy request-body limits](https://caddyserver.com/docs/caddyfile/directives/request_body)
- [Caddy validation and reload commands](https://caddyserver.com/docs/command-line)
- [Caddy Basic Authentication fallback](https://caddyserver.com/docs/caddyfile/directives/basic_auth)
- [Python Requests TLS and client certificates](https://requests.readthedocs.io/en/stable/user/advanced/)
- [LuaSocket TCP and timeout behavior](https://lunarmodules.github.io/luasocket/tcp.html)
- [DCS Lua Runner upstream setup](https://github.com/omltcat/dcs-lua-runner/blob/master/INSTALL.md)
