"""Unit tests for the secure DCS HTTPS client."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from core.dcs_client import DCSClient


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any],
        echo_request_id: bool = True,
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.echo_request_id = echo_request_id
        self._body = b""
        self._set_payload(payload)
        self.closed = False

    def _set_payload(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(self._body)),
            "X-Request-ID": str(payload.get("request_id", "pending")),
        }

    def echo(self, request_id: str) -> None:
        if self.echo_request_id:
            self.payload["request_id"] = request_id
            self._set_payload(self.payload)

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self._body), chunk_size):
            yield self._body[offset : offset + chunk_size]

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        self.response.echo(kwargs["headers"]["X-Request-ID"])
        return self.response

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        self.response.echo(kwargs["headers"]["X-Request-ID"])
        return self.response


class DCSClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.certificate = directory / "client.crt"
        self.private_key = directory / "client.key"
        self.certificate.write_text("certificate", encoding="utf-8")
        self.private_key.write_text("private key", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def settings(self) -> dict[str, Any]:
        return {
            "mission_url": "https://mission.example.com",
            "gui_url": "https://dcs-lua-gui.example.com",
            "client_cert_file": str(self.certificate),
            "client_key_file": str(self.private_key),
            "ca_bundle": "",
            "connect_timeout_seconds": 5,
            "read_timeout_seconds": 30,
            "max_request_bytes": 262144,
            "max_response_bytes": 2097152,
            "run_in_mission_env": True,
        }

    def test_run_lua_posts_raw_utf8_with_mtls(self) -> None:
        response = FakeResponse(200, {"ok": True, "request_id": "request-1", "result": 42})
        session = FakeSession(response)
        client = DCSClient(session=session)  # type: ignore[arg-type]

        success, result = client.run_lua("return 'héllo'", self.settings())

        self.assertTrue(success)
        self.assertEqual(result, 42)
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://mission.example.com/v1/execute?env=default")
        self.assertEqual(kwargs["data"], "return 'héllo'".encode("utf-8"))
        self.assertEqual(kwargs["cert"], (str(self.certificate), str(self.private_key)))
        self.assertIs(kwargs["verify"], True)
        self.assertNotIn("Authorization", kwargs["headers"])
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(response.closed)

    def test_run_lua_returns_structured_server_error(self) -> None:
        response = FakeResponse(
            422,
            {
                "ok": False,
                "request_id": "request-2",
                "error": {"kind": "syntax_error", "message": "unexpected symbol"},
            },
        )
        client = DCSClient(session=FakeSession(response))  # type: ignore[arg-type]

        success, result = client.run_lua("not valid", self.settings())

        self.assertFalse(success)
        self.assertEqual(result, "syntax_error: unexpected symbol")

    def test_run_lua_rejects_http_before_sending(self) -> None:
        session = FakeSession(FakeResponse(200, {"ok": True, "result": None}))
        client = DCSClient(session=session)  # type: ignore[arg-type]
        settings = self.settings()
        settings["mission_url"] = "http://127.0.0.1:12080"

        success, result = client.run_lua("return 1", settings)

        self.assertFalse(success)
        self.assertIn("Only HTTPS", result)
        self.assertEqual(session.calls, [])

    def test_run_lua_rejects_oversized_source_before_sending(self) -> None:
        session = FakeSession(FakeResponse(200, {"ok": True, "result": None}))
        client = DCSClient(session=session)  # type: ignore[arg-type]
        settings = self.settings()
        settings["max_request_bytes"] = 4

        success, result = client.run_lua("return 1", settings)

        self.assertFalse(success)
        self.assertIn("limit is 4 bytes", result)
        self.assertEqual(session.calls, [])

    def test_format_result_restores_typed_table_keys(self) -> None:
        client = DCSClient(session=FakeSession(FakeResponse(200, {})))  # type: ignore[arg-type]
        result = {
            "__dcs_type": "table",
            "entries": [
                {"key_type": "number", "key": 1, "value": "first"},
                {"key_type": "string", "key": "_1", "value": "literal"},
            ],
        }

        rendered = client.format_result_as_lua(result)

        self.assertIn('[1] = "first"', rendered)
        self.assertIn('["_1"] = "literal"', rendered)

    def test_format_result_uses_lua_51_control_character_escapes(self) -> None:
        client = DCSClient(session=FakeSession(FakeResponse(200, {})))  # type: ignore[arg-type]

        rendered = client.format_result_as_lua("line\ncontrol:\x01 unicode:é")

        self.assertEqual(rendered, '"line\\ncontrol:\\001 unicode:é"')

    def test_run_lua_rejects_mismatched_response_request_id(self) -> None:
        response = FakeResponse(
            200,
            {"ok": True, "request_id": "different-request", "result": 42},
            echo_request_id=False,
        )
        client = DCSClient(session=FakeSession(response))  # type: ignore[arg-type]

        success, result = client.run_lua("return 42", self.settings())

        self.assertFalse(success)
        self.assertIn("request ID does not match", result)

    def test_check_health_uses_selected_gui_endpoint(self) -> None:
        response = FakeResponse(200, {"ok": True, "environment": "hooks", "ready": True})
        session = FakeSession(response)
        client = DCSClient(session=session)  # type: ignore[arg-type]
        settings = self.settings()
        settings["run_in_mission_env"] = False

        success, result = client.check_health(settings)

        self.assertTrue(success)
        self.assertEqual(result["environment"], "hooks")
        self.assertEqual(session.calls[0][1], "https://dcs-lua-gui.example.com/healthz")


if __name__ == "__main__":
    unittest.main()
