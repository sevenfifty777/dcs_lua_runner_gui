"""Secure HTTPS client for the versioned DCS Lua Runner protocol."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests


DEFAULT_MAX_REQUEST_BYTES = 256 * 1024
DEFAULT_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
RESPONSE_CHUNK_BYTES = 64 * 1024


class DCSClientError(RuntimeError):
    """Raised when connection settings or a server response are invalid."""


class DCSClient:
    """Send authenticated Lua execution requests through Caddy."""

    def __init__(self, session: requests.Session | None = None) -> None:
        if session is None:
            session = requests.Session()
            session.trust_env = False
        self._session = session

    def run_lua(self, lua_code: str, settings: Mapping[str, Any]) -> tuple[bool, Any]:
        """Execute Lua and return the existing GUI-compatible success tuple."""
        try:
            payload = lua_code.encode("utf-8")
            max_request_bytes = self._bounded_integer(
                settings.get("max_request_bytes", DEFAULT_MAX_REQUEST_BYTES),
                "max_request_bytes",
                1,
                1024 * 1024,
            )
            if len(payload) > max_request_bytes:
                raise DCSClientError(
                    f"Lua source is {len(payload)} bytes; limit is {max_request_bytes} bytes"
                )

            base_url = self._selected_base_url(settings)
            endpoint = self._endpoint_url(base_url, "/v1/execute?env=default")
            certificate = self._client_certificate(settings)
            verify = self._tls_verification(settings)
            timeout = self._timeouts(settings)
            request_id = str(uuid.uuid4())

            response = self._session.post(
                endpoint,
                data=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "text/plain; charset=utf-8",
                    "X-Request-ID": request_id,
                },
                cert=certificate,
                verify=verify,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
            response_data = self._read_json_response(response, settings, request_id)

            if (
                200 <= response.status_code < 300
                and response_data.get("ok") is True
                and "result" in response_data
            ):
                return True, response_data.get("result")

            error = response_data.get("error")
            if (
                response_data.get("ok") is False
                and isinstance(error, dict)
                and isinstance(error.get("kind"), str)
                and isinstance(error.get("message"), str)
            ):
                kind = error["kind"]
                message = error["message"]
                return False, f"{kind}: {message}"
            return False, f"HTTP {response.status_code}: invalid error response"
        except DCSClientError as error:
            return False, str(error)
        except requests.exceptions.SSLError:
            return False, "TLS validation failed; check the server name, CA bundle, and client certificate"
        except requests.exceptions.Timeout:
            return False, "Request timed out; DCS may be busy or the connection may be incomplete"
        except requests.exceptions.ConnectionError:
            return False, "Connection failed; check the HTTPS endpoint and Caddy availability"
        except requests.exceptions.RequestException as error:
            return False, f"HTTPS request failed: {error}"

    def check_health(self, settings: Mapping[str, Any]) -> tuple[bool, Any]:
        """Query the selected environment's authenticated health endpoint."""
        try:
            endpoint = self._endpoint_url(self._selected_base_url(settings), "/healthz")
            request_id = str(uuid.uuid4())
            response = self._session.get(
                endpoint,
                headers={"Accept": "application/json", "X-Request-ID": request_id},
                cert=self._client_certificate(settings),
                verify=self._tls_verification(settings),
                timeout=self._timeouts(settings),
                allow_redirects=False,
                stream=True,
            )
            data = self._read_json_response(response, settings, request_id)
            expected_environment = (
                "mission" if settings.get("run_in_mission_env", True) else "hooks"
            )
            if (
                response.status_code == 200
                and data.get("ok") is True
                and data.get("ready") is True
                and data.get("environment") == expected_environment
            ):
                return True, data
            return False, f"Health check returned HTTP {response.status_code}"
        except DCSClientError as error:
            return False, str(error)
        except requests.exceptions.SSLError:
            return False, "TLS validation failed; check the server name, CA bundle, and client certificate"
        except requests.exceptions.Timeout:
            return False, "Health check timed out"
        except requests.exceptions.ConnectionError:
            return False, "Connection failed; check the HTTPS endpoint and Caddy availability"
        except requests.exceptions.RequestException as error:
            return False, f"HTTPS health check failed: {error}"

    def _selected_base_url(self, settings: Mapping[str, Any]) -> str:
        key = "mission_url" if settings.get("run_in_mission_env", True) else "gui_url"
        value = settings.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DCSClientError(f"{key} is required")
        return value.strip()

    @staticmethod
    def _endpoint_url(base_url: str, endpoint: str) -> str:
        parsed = urlsplit(base_url)
        if parsed.scheme.lower() != "https":
            raise DCSClientError("Only HTTPS endpoints are permitted")
        if not parsed.hostname or parsed.username or parsed.password:
            raise DCSClientError("Endpoint must contain a hostname and must not contain credentials")
        if parsed.query or parsed.fragment:
            raise DCSClientError("Endpoint base URL cannot contain a query or fragment")
        if parsed.path not in ("", "/"):
            raise DCSClientError("Endpoint base URL cannot contain a path")
        endpoint_parts = endpoint.split("?", 1)
        endpoint_path = endpoint_parts[0]
        endpoint_query = endpoint_parts[1] if len(endpoint_parts) == 2 else ""
        return urlunsplit(("https", parsed.netloc, endpoint_path, endpoint_query, ""))

    @staticmethod
    def _resolve_file(settings: Mapping[str, Any], key: str, required: bool) -> str | None:
        value = settings.get(key, "")
        if not isinstance(value, str):
            raise DCSClientError(f"{key} must be a file path")
        value = value.strip()
        if not value:
            if required:
                raise DCSClientError(f"{key} is required for mTLS")
            return None
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise DCSClientError(f"{key} does not point to a readable file")
        return str(path)

    def _client_certificate(self, settings: Mapping[str, Any]) -> tuple[str, str]:
        certificate = self._resolve_file(settings, "client_cert_file", required=True)
        private_key = self._resolve_file(settings, "client_key_file", required=True)
        if certificate is None or private_key is None:
            raise DCSClientError("Both client certificate and private key are required for mTLS")
        return certificate, private_key

    def _tls_verification(self, settings: Mapping[str, Any]) -> bool | str:
        ca_bundle = self._resolve_file(settings, "ca_bundle", required=False)
        return ca_bundle or True

    def _timeouts(self, settings: Mapping[str, Any]) -> tuple[float, float]:
        connect = self._bounded_number(
            settings.get("connect_timeout_seconds", 5),
            "connect_timeout_seconds",
            0.5,
            60,
        )
        read = self._bounded_number(
            settings.get("read_timeout_seconds", 30),
            "read_timeout_seconds",
            1,
            300,
        )
        return connect, read

    def _read_json_response(
        self,
        response: requests.Response,
        settings: Mapping[str, Any],
        expected_request_id: str,
    ) -> dict[str, Any]:
        max_response_bytes = self._bounded_integer(
            settings.get("max_response_bytes", DEFAULT_MAX_RESPONSE_BYTES),
            "max_response_bytes",
            1024,
            8 * 1024 * 1024,
        )
        declared_length = response.headers.get("Content-Length")
        if declared_length:
            if not declared_length.isdigit():
                response.close()
                raise DCSClientError("Server returned an invalid Content-Length")
            if int(declared_length) > max_response_bytes:
                response.close()
                raise DCSClientError("Server response exceeds the configured limit")

        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=RESPONSE_CHUNK_BYTES):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_response_bytes:
                    raise DCSClientError("Server response exceeds the configured limit")
                chunks.append(chunk)
        finally:
            response.close()

        content_type = response.headers.get("Content-Type", "").lower()
        media_type = content_type.split(";", 1)[0].strip()
        if media_type != "application/json":
            raise DCSClientError(f"Server returned unexpected Content-Type: {content_type or 'missing'}")
        try:
            decoded = json.loads(
                b"".join(chunks).decode("utf-8"),
                object_pairs_hook=self._object_without_duplicate_keys,
                parse_constant=self._reject_nonfinite_json_number,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise DCSClientError("Server returned invalid UTF-8 JSON") from error
        if not isinstance(decoded, dict):
            raise DCSClientError("Server response must be a JSON object")
        if decoded.get("request_id") != expected_request_id:
            raise DCSClientError("Server response request ID does not match the request")
        header_request_id = response.headers.get("X-Request-ID")
        if header_request_id != expected_request_id:
            raise DCSClientError("Server response header request ID does not match the request")
        return decoded

    @staticmethod
    def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    @staticmethod
    def _reject_nonfinite_json_number(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    @staticmethod
    def _bounded_integer(value: Any, name: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise DCSClientError(f"{name} must be an integer from {minimum} through {maximum}")
        return value

    @staticmethod
    def _bounded_number(value: Any, name: str, minimum: float, maximum: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DCSClientError(f"{name} must be a number")
        numeric = float(value)
        if not minimum <= numeric <= maximum:
            raise DCSClientError(f"{name} must be from {minimum} through {maximum}")
        return numeric

    def format_result_as_lua(self, result: Any) -> str:
        """Render ordinary JSON and typed-table envelopes as Lua values."""
        return self._format_lua_value(result, 0)

    def _format_lua_value(self, value: Any, depth: int) -> str:
        indent = "    " * depth
        child_indent = "    " * (depth + 1)
        if value is None:
            return "nil"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if isinstance(value, float) and not math.isfinite(value):
                raise DCSClientError("Cannot format a non-finite number as Lua")
            return repr(value)
        if isinstance(value, str):
            return self._lua_quote(value)
        if isinstance(value, list):
            if not value:
                return "{}"
            items = [f"{child_indent}{self._format_lua_value(item, depth + 1)}" for item in value]
            return "{\n" + ",\n".join(items) + f"\n{indent}}}"
        if isinstance(value, dict):
            if value.get("__dcs_type") == "table" and isinstance(value.get("entries"), list):
                entries: list[str] = []
                for entry in value["entries"]:
                    if not isinstance(entry, dict) or set(entry) != {"key_type", "key", "value"}:
                        raise DCSClientError("Invalid typed-table response")
                    key_type = entry["key_type"]
                    key_value = entry["key"]
                    if key_type == "number":
                        valid_key = isinstance(key_value, (int, float)) and not isinstance(key_value, bool)
                    elif key_type == "string":
                        valid_key = isinstance(key_value, str)
                    elif key_type == "boolean":
                        valid_key = isinstance(key_value, bool)
                    else:
                        valid_key = False
                    if not valid_key:
                        raise DCSClientError("Invalid typed-table key")
                    key = self._format_lua_value(key_value, depth + 1)
                    rendered = self._format_lua_value(entry["value"], depth + 1)
                    entries.append(f"{child_indent}[{key}] = {rendered}")
                return "{}" if not entries else "{\n" + ",\n".join(entries) + f"\n{indent}}}"
            if not value:
                return "{}"
            fields = []
            for key in sorted(value):
                rendered_key = self._lua_quote(str(key))
                rendered_value = self._format_lua_value(value[key], depth + 1)
                fields.append(f"{child_indent}[{rendered_key}] = {rendered_value}")
            return "{\n" + ",\n".join(fields) + f"\n{indent}}}"
        raise DCSClientError(f"Unsupported result type: {type(value).__name__}")

    @staticmethod
    def _lua_quote(value: str) -> str:
        escapes = {
            "\\": "\\\\",
            '"': '\\"',
            "\a": "\\a",
            "\b": "\\b",
            "\f": "\\f",
            "\n": "\\n",
            "\r": "\\r",
            "\t": "\\t",
            "\v": "\\v",
        }
        output: list[str] = ['"']
        for character in value:
            if character in escapes:
                output.append(escapes[character])
            elif ord(character) < 32 or ord(character) == 127:
                output.append(f"\\{ord(character):03d}")
            else:
                output.append(character)
        output.append('"')
        return "".join(output)
