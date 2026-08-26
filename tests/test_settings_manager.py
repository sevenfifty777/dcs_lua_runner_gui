"""Unit tests for versioned and secret-free settings persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.settings_manager import SCHEMA_VERSION, SettingsError, SettingsManager


class SettingsManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        directory = Path(self.temporary_directory.name)
        self.settings_file = directory / "new" / "settings.json"
        self.legacy_file = directory / "dcs_lua_runner_settings.json"
        self.manager = SettingsManager(self.settings_file, self.legacy_file)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_save_settings_never_accepts_password_fields(self) -> None:
        settings = self.manager.default_settings.copy()
        settings["web_auth_password"] = "must-not-be-saved"

        with self.assertRaises(SettingsError):
            self.manager.save_settings(settings)

        self.assertFalse(self.settings_file.exists())

    def test_migration_sanitizes_legacy_password_file(self) -> None:
        self.legacy_file.write_text(
            json.dumps(
                {
                    "server_address": "fiddle.example.com",
                    "server_address_gui": "fiddle-gui.example.com",
                    "server_port": 443,
                    "server_port_gui": 443,
                    "use_https": True,
                    "web_auth_username": "legacy-user",
                    "web_auth_password": "legacy-password",
                    "run_in_mission_env": False,
                }
            ),
            encoding="utf-8",
        )

        settings = self.manager.load_settings()

        self.assertEqual(settings["mission_url"], "https://fiddle.example.com")
        self.assertEqual(settings["gui_url"], "https://fiddle-gui.example.com")
        self.assertFalse(settings["run_in_mission_env"])
        saved = self.settings_file.read_text(encoding="utf-8")
        sanitized_legacy = self.legacy_file.read_text(encoding="utf-8")
        self.assertNotIn("legacy-password", saved)
        self.assertNotIn("legacy-password", sanitized_legacy)
        self.assertNotIn("web_auth_password", saved)
        self.assertEqual(json.loads(sanitized_legacy)["migrated"], True)

    def test_invalid_non_https_endpoint_is_rejected(self) -> None:
        settings = self.manager.default_settings.copy()
        settings["mission_url"] = "http://fiddle.example.com"

        with self.assertRaises(SettingsError):
            self.manager.validate_settings(settings)

    def test_saved_settings_are_versioned_and_allow_listed(self) -> None:
        settings = self.manager.default_settings.copy()

        self.assertTrue(self.manager.save_settings(settings))

        saved = json.loads(self.settings_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
        self.assertNotIn("password", " ".join(saved.keys()).lower())

    def test_current_settings_with_forbidden_secret_field_fail_closed(self) -> None:
        settings = self.manager.default_settings.copy()
        settings["proxy_token"] = "must-not-be-loaded"
        self.settings_file.parent.mkdir(parents=True)
        self.settings_file.write_text(json.dumps(settings), encoding="utf-8")

        loaded = self.manager.load_settings()

        self.assertEqual(loaded, self.manager.default_settings)
        self.assertIn("must not contain", self.manager.last_error or "")


if __name__ == "__main__":
    unittest.main()
