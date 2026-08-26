# DCS Lua Runner Protocol v2

The application protocol version reported by the server is `1`; the product
migration is called v2 because it replaces the legacy GUI and GET/Basic design.
There is no legacy endpoint in the secure server.

## Execute

```http
POST /v1/execute?env=default HTTP/1.1
Content-Type: text/plain; charset=utf-8
Accept: application/json
X-Request-ID: <1-64 letters, digits, dot, underscore, or hyphen>
X-DCS-Proxy-Token: <Caddy-injected token>
Content-Length: <UTF-8 byte count>

<raw UTF-8 Lua source>
```

The GUI sends all headers except `X-DCS-Proxy-Token`; Caddy overwrites that
header before proxying. The Lua body limit is 256 KiB by default. Transfer
encoding, duplicate security-sensitive headers, unexpected query parameters,
invalid UTF-8, and trailing bytes are rejected.

Successful response:

```json
{
  "ok": true,
  "request_id": "same-request-id",
  "result": 42
}
```

Error response:

```json
{
  "ok": false,
  "request_id": "same-request-id",
  "error": {
    "kind": "syntax_error",
    "message": "sanitized diagnostic"
  }
}
```

Every Lua response uses JSON UTF-8, an exact `Content-Length`,
`Connection: close`, `Cache-Control: no-store`, and the request ID in both the
body and response header. The GUI rejects a mismatch, duplicate JSON object
keys, non-finite JSON numbers, an unexpected media type, or an oversized body.

## Health

```http
GET /healthz HTTP/1.1
Accept: application/json
X-Request-ID: <request-id>
X-DCS-Proxy-Token: <Caddy-injected token>
```

```json
{
  "ok": true,
  "request_id": "same-request-id",
  "protocol_version": 1,
  "environment": "mission",
  "ready": true
}
```

`environment` is `mission` on port 12080 and `hooks` on port 12081.

## Status Classes

| Status | Meaning |
| --- | --- |
| 200 | Health or execution succeeded |
| 400 | Invalid framing, query, UTF-8, or unsupported environment |
| 401 | Missing or incorrect internal proxy token |
| 404 | Unknown backend route |
| 405 | Wrong backend method |
| 408 | Incomplete request exceeded its deadline |
| 411 | Execute request has no Content-Length |
| 413 | Source body exceeds the limit |
| 415 | Execute media type is not UTF-8 text/plain |
| 422 | Lua compilation failed |
| 429 | Another execution was selected in the same poll cycle |
| 431 | Header section exceeds the limit |
| 500 | Lua runtime or result serialization failed |
| 503 | Connection cap reached |
| 505 | Protocol is not HTTP/1.1 |

## Lua Table Encoding

- Sequential positive integer keys become JSON arrays.
- String-key tables become JSON objects.
- Sparse, mixed-key, Boolean-key, and reserved-marker tables use:

```json
{
  "__dcs_type": "table",
  "entries": [
    {"key_type": "number", "key": 1, "value": "one"},
    {"key_type": "string", "key": "1", "value": "text one"}
  ]
}
```

The reserved `__dcs_type` key forces typed encoding, preventing a normal Lua
table from being mistaken for a protocol envelope. Unsupported values,
circular references, invalid UTF-8 strings, excessive depth, non-finite numbers,
and oversized encoded results return a serialization error.
