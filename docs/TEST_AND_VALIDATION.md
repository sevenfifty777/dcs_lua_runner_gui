# Test and Validation Runbook

## Source Checks

From an isolated Windows CPython 3.11 environment:

```powershell
python -m pip install -r requirements.lock
python -m compileall -q core gui utils main.py tests
python -m unittest discover -s tests -v
python -m pip check
python -m pip_audit --no-deps -r requirements.lock
git diff --check
```

The audit tool is not an application dependency. Install the reviewed
`pip-audit` version separately in the validation environment when it is not
already available.

## Build Checks

```powershell
.\create_distribution.bat 2.0-dev
```

The build must use PyInstaller 6.22.2, compare the packaged and root Lua hashes,
reject runtime configuration/secrets, and run the packaged `--version` smoke
test. Review `build\build_exe\warn-build_exe.txt`; platform-only and unused
optional imports may be expected, but required imports are release blockers.

## Caddy and Network Checks

Follow `docs/CADDY_MTLS_SETUP.md`. Validate the complete active Caddyfile, not
only the Fiddle snippets. Confirm:

- dashboard and LSO behavior is unchanged;
- only the two Fiddle hostnames require the client certificate;
- untrusted or missing client certificates fail the TLS handshake;
- direct external connections to ports 12080 and 12081 fail; when the optional
  dashboards are deployed, ports 3001 and 8090 also remain blocked externally;
- Caddy reaches the exact loopback backend for each hostname;
- an incoming forged `X-DCS-Proxy-Token` cannot replace Caddy's value;
- normal access logs contain neither bodies nor secrets.

## Live DCS Matrix

Run against both Mission and Hooks/GameGUI where the API exists:

- authenticated health;
- scalar and no-return execution;
- nested, empty, sparse, and mixed-key tables;
- syntax and runtime errors;
- invalid route, method, token, UTF-8, content length, and oversized body;
- partial/slow requests without a DCS frame stall;
- maximum permitted and rejected response sizes;
- mission load/unload/restart, pause/resume, and full DCS restart;
- Caddy reload, client-certificate replacement, and proxy-token rotation.

Measure DCS frame behavior while slow clients are connected. Review logs for
request IDs and status only; submitted source must not appear.

## Release Gate

Do not promote the development executable until Lua syntax testing, active
Caddy validation, both live DCS environments, both dashboards, firewall
reachability, certificate rotation, token rotation, and rollback have all been
recorded with timestamps and observed results.
