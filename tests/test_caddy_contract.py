"""Static topology and security checks for the deployable Caddy template."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CADDYFILE = ROOT / "deploy" / "Caddyfile.example"


class CaddyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = CADDYFILE.read_text(encoding="utf-8")

    def test_all_backends_are_explicit_loopback_addresses(self) -> None:
        for port in (3001, 8090, 12080, 12081):
            self.assertIn(f"reverse_proxy 127.0.0.1:{port}", self.source)
        self.assertNotIn("reverse_proxy localhost:", self.source)

    def test_mtls_is_scoped_only_to_fiddle_sites(self) -> None:
        dashboard_prefix = self.source.split("fiddle.example.com", 1)[0]
        self.assertNotIn("client_auth", dashboard_prefix)
        self.assertEqual(self.source.count("mode require_and_verify"), 2)

    def test_proxy_token_is_runtime_only_and_injected_on_fiddle_routes(self) -> None:
        self.assertEqual(self.source.count("{env.DCS_FIDDLE_PROXY_TOKEN}"), 4)
        self.assertEqual(self.source.count("header_up -Authorization"), 4)
        self.assertNotIn("CHANGE_ME", self.source)

    def test_execute_route_is_post_only_and_bounded(self) -> None:
        self.assertEqual(self.source.count("method POST"), 2)
        self.assertEqual(self.source.count("path /v1/execute"), 2)
        self.assertEqual(self.source.count("max_size 256KB"), 2)


if __name__ == "__main__":
    unittest.main()
