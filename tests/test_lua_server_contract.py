"""Static security contract tests for the DCS-hosted Lua server."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_SOURCE = ROOT / "dcs-fiddle-server.lua"
CONFIG_EXAMPLE = ROOT / "dcs-fiddle-config.lua.example"


class LuaServerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SERVER_SOURCE.read_text(encoding="utf-8")

    def test_server_has_no_basic_auth_or_embedded_credentials(self) -> None:
        self.assertNotIn("FIDDLE.USERNAME", self.source)
        self.assertNotIn("FIDDLE.PASSWORD", self.source)
        self.assertNotIn("Basic%s+", self.source)
        self.assertNotIn("base64.decode", self.source)

    def test_server_requires_loopback_and_external_proxy_token(self) -> None:
        self.assertIn('bind_ip ~= "127.0.0.1"', self.source)
        self.assertIn('rawget(raw, "proxy_token")', self.source)
        self.assertIn('headers["x-dcs-proxy-token"]', self.source)

    def test_server_uses_versioned_post_protocol_and_bounded_states(self) -> None:
        self.assertIn('request.path == "/v1/execute"', self.source)
        self.assertIn('method ~= "POST"', self.source)
        self.assertIn('state = "reading_headers"', self.source)
        self.assertIn('client.state = "reading_body"', self.source)
        self.assertIn('client.state = "ready_to_execute"', self.source)
        self.assertIn('client.state = "writing_response"', self.source)
        self.assertIn("is_valid_utf8(lua_source)", self.source)

    def test_reserved_typed_table_marker_cannot_collide(self) -> None:
        self.assertIn('key == "__dcs_type"', self.source)
        self.assertIn('uses_reserved_envelope_key', self.source)

    def test_server_does_not_log_submitted_lua(self) -> None:
        self.assertNotIn("Processing Command", self.source)
        self.assertNotIn('log_info(lua_source)', self.source)

    def test_server_loads_data_config_outside_auto_loaded_hooks(self) -> None:
        config_source = CONFIG_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn(
            'CONFIG_RELATIVE_PATH = "Scripts\\\\DCSLuaRunner\\\\dcs-fiddle-config.lua"',
            self.source,
        )
        self.assertIn(
            'HOOKS_RELATIVE_DIRECTORY = "Scripts\\\\Hooks\\\\"',
            self.source,
        )
        self.assertNotIn('CONFIG_FILENAME = "dcs-fiddle-config.lua"', self.source)
        self.assertIn("Keep this data-only file outside Scripts\\Hooks", config_source)
        self.assertIn("DCS DEDICATED SERVER-SIDE CONFIGURATION", config_source)


if __name__ == "__main__":
    unittest.main()
