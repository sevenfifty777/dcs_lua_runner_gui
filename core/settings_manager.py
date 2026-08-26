"""Versioned, secret-free settings persistence for DCS Lua Runner GUI."""

from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 2
APP_DIRECTORY_NAME = "DCSLuaRunner"
SETTINGS_FILENAME = "settings.json"
LEGACY_SETTINGS_FILENAME = "dcs_lua_runner_settings.json"


class SettingsError(ValueError):
    """Raised when settings cannot be validated or saved."""


class SettingsManager:
    """Load, validate, migrate, and atomically save application settings."""

    def __init__(
        self,
        settings_file: str | Path | None = None,
        legacy_settings_file: str | Path | None = None,
    ) -> None:
        self.settings_file = Path(settings_file) if settings_file else self._default_settings_file()
        self.legacy_settings_file = (
            Path(legacy_settings_file)
            if legacy_settings_file
            else Path.cwd() / LEGACY_SETTINGS_FILENAME
        )
        self.last_error: str | None = None
        self.default_settings: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "mission_url": "https://mission.example.com",
            "gui_url": "https://dcs-lua-gui.example.com",
            "client_cert_file": "",
            "client_key_file": "",
            "ca_bundle": "",
            "connect_timeout_seconds": 5,
            "read_timeout_seconds": 30,
            "max_request_bytes": 262144,
            "max_response_bytes": 2097152,
            "run_in_mission_env": True,
            "return_display_format": "lua",
            "window_width": 1200,
            "window_height": 800,
            "editor_font_size": 12,
            "editor_font_family": "Consolas",
        }

    @staticmethod
    def _default_settings_file() -> Path:
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return base / APP_DIRECTORY_NAME / SETTINGS_FILENAME

    def load_settings(self) -> dict[str, Any]:
        """Load current settings, migrating the legacy application file once."""
        self.last_error = None
        if self.settings_file.is_file():
            return self._load_current_file()
        if self.legacy_settings_file.is_file():
            return self._migrate_legacy_file()
        return self.default_settings.copy()

    def _load_current_file(self) -> dict[str, Any]:
        try:
            raw = self._read_json_object(self.settings_file)
            return self.validate_settings(raw)
        except SettingsError as error:
            self.last_error = f"Could not load settings: {error}"
            LOGGER.warning("Could not load settings: %s", error)
            return self.default_settings.copy()
        except OSError as error:
            self.last_error = f"Could not load settings: {error}"
            LOGGER.error("Could not read settings", exc_info=True)
            return self.default_settings.copy()

    def _migrate_legacy_file(self) -> dict[str, Any]:
        try:
            legacy = self._read_json_object(self.legacy_settings_file)
            migrated = self._convert_legacy_settings(legacy)
            if not self.save_settings(migrated):
                raise SettingsError(self.last_error or "new settings could not be saved")
            try:
                self._sanitize_legacy_file()
            except SettingsError as error:
                self.last_error = str(error)
                LOGGER.error("Legacy settings still require manual removal", exc_info=True)
            return migrated
        except (OSError, SettingsError) as error:
            self.last_error = f"Could not migrate legacy settings: {error}"
            LOGGER.error("Could not migrate legacy settings", exc_info=True)
            return self.default_settings.copy()

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as settings_handle:
                raw = json.load(settings_handle)
        except json.JSONDecodeError as error:
            raise SettingsError("file does not contain valid JSON") from error
        if not isinstance(raw, dict):
            raise SettingsError("settings root must be a JSON object")
        return raw

    def _convert_legacy_settings(self, legacy: Mapping[str, Any]) -> dict[str, Any]:
        migrated = self.default_settings.copy()
        mission_host = str(legacy.get("server_address", "")).strip()
        gui_host = str(legacy.get("server_address_gui", mission_host)).strip()
        use_https = legacy.get("use_https") is True

        if mission_host and use_https:
            migrated["mission_url"] = self._legacy_url(
                mission_host, legacy.get("server_port", 443)
            )
        if gui_host and use_https:
            migrated["gui_url"] = self._legacy_url(
                gui_host, legacy.get("server_port_gui", 443)
            )

        for key in (
            "run_in_mission_env",
            "return_display_format",
            "window_width",
            "window_height",
            "editor_font_size",
            "editor_font_family",
        ):
            if key in legacy:
                migrated[key] = legacy[key]

        return self.validate_settings(migrated)

    @staticmethod
    def _legacy_url(host: str, port_value: Any) -> str:
        if "://" in host:
            parsed = urlsplit(host)
            host = parsed.hostname or ""
        try:
            port = int(port_value)
        except (TypeError, ValueError) as error:
            raise SettingsError("legacy server port is invalid") from error
        if not 1 <= port <= 65535:
            raise SettingsError("legacy server port is outside the valid range")
        suffix = "" if port == 443 else f":{port}"
        return f"https://{host}{suffix}"

    def validate_settings(self, settings: Mapping[str, Any]) -> dict[str, Any]:
        """Return a normalized allow-listed settings object."""
        forbidden = {"web_auth_username", "web_auth_password", "password", "proxy_token"}
        if forbidden.intersection(settings):
            raise SettingsError("settings must not contain passwords or proxy tokens")

        normalized = self.default_settings.copy()
        normalized.update({key: settings[key] for key in normalized if key in settings})
        normalized["schema_version"] = SCHEMA_VERSION

        for key in ("mission_url", "gui_url"):
            value = normalized[key]
            if not isinstance(value, str):
                raise SettingsError(f"{key} must be text")
            value = value.strip().rstrip("/")
            parsed = urlsplit(value)
            if parsed.scheme.lower() != "https" or not parsed.hostname:
                raise SettingsError(f"{key} must be an HTTPS URL with a hostname")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise SettingsError(f"{key} cannot contain credentials, a query, or a fragment")
            if parsed.path not in ("", "/"):
                raise SettingsError(f"{key} cannot contain a path")
            normalized[key] = value

        for key in ("client_cert_file", "client_key_file", "ca_bundle", "editor_font_family"):
            if not isinstance(normalized[key], str):
                raise SettingsError(f"{key} must be text")
            normalized[key] = normalized[key].strip()

        self._validate_integer(normalized, "connect_timeout_seconds", 1, 60)
        self._validate_integer(normalized, "read_timeout_seconds", 1, 300)
        self._validate_integer(normalized, "max_request_bytes", 1, 1048576)
        self._validate_integer(normalized, "max_response_bytes", 1024, 8388608)
        self._validate_integer(normalized, "window_width", 640, 7680)
        self._validate_integer(normalized, "window_height", 480, 4320)
        self._validate_integer(normalized, "editor_font_size", 8, 48)

        if not isinstance(normalized["run_in_mission_env"], bool):
            raise SettingsError("run_in_mission_env must be true or false")
        if normalized["return_display_format"] not in ("lua", "json"):
            raise SettingsError("return_display_format must be lua or json")
        return normalized

    @staticmethod
    def _validate_integer(settings: Mapping[str, Any], key: str, minimum: int, maximum: int) -> None:
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise SettingsError(f"{key} must be an integer from {minimum} through {maximum}")

    def save_settings(self, settings: Mapping[str, Any]) -> bool:
        """Validate and atomically save only non-secret settings."""
        normalized = self.validate_settings(settings)

        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.settings_file.parent,
                prefix=f".{self.settings_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                json.dump(normalized, temporary, indent=2, sort_keys=True)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.chmod(temporary_path, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(temporary_path, self.settings_file)
            self.last_error = None
            return True
        except OSError as error:
            self.last_error = f"Could not save settings: {error}"
            LOGGER.error("Could not save settings", exc_info=True)
            if temporary_path and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    LOGGER.warning("Could not remove temporary settings file", exc_info=True)
            return False

    def _sanitize_legacy_file(self) -> None:
        marker = {
            "schema_version": SCHEMA_VERSION,
            "migrated": True,
            "settings_file": str(self.settings_file),
        }
        temporary = self.legacy_settings_file.with_suffix(".json.migration.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as legacy_handle:
                json.dump(marker, legacy_handle, indent=2)
                legacy_handle.write("\n")
                legacy_handle.flush()
                os.fsync(legacy_handle.fileno())
            os.replace(temporary, self.legacy_settings_file)
        except OSError as error:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    LOGGER.warning("Could not remove temporary legacy marker", exc_info=True)
            raise SettingsError("new settings were saved but the legacy password file could not be sanitized") from error

    def get_connection_info(self, settings: Mapping[str, Any]) -> str:
        """Return a non-secret summary for the status bar."""
        environment = "Mission" if settings.get("run_in_mission_env", True) else "Hooks/GUI"
        key = "mission_url" if settings.get("run_in_mission_env", True) else "gui_url"
        endpoint = str(settings.get(key, "Not configured"))
        certificate_status = "mTLS configured" if (
            settings.get("client_cert_file") and settings.get("client_key_file")
        ) else "mTLS certificate required"
        return f"{environment} | {endpoint} | {certificate_status}"
