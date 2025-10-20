"""
Settings Manager for DCS Lua Runner GUI.
Handles saving and loading application configuration.
"""

import json
import os
from typing import Dict, Any

class SettingsManager:
    """Manages application settings persistence."""
    
    def __init__(self, settings_file: str = "dcs_lua_runner_settings.json"):
        self.settings_file = settings_file
        self.default_settings = {
            # Connection settings
            'server_address': '',
            'server_address_gui': '',
            'server_port': 12080,
            'server_port_gui': 12081,
            'use_https': False,
            'web_auth_username': 'username',
            'web_auth_password': 'password',
            
            # Execution settings
            'run_code_locally': True,
            'run_in_mission_env': True,
            
            # Display settings
            'return_display_format': 'lua',  # 'lua' or 'json'
            
            # UI settings
            'window_width': 1200,
            'window_height': 800,
            'editor_font_size': 12,
            'editor_font_family': 'Consolas'
        }
        
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file, return defaults if file doesn't exist."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_settings = self.default_settings.copy()
                merged_settings.update(settings)
                return merged_settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings: {e}")
                return self.default_settings.copy()
        else:
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except IOError as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_connection_info(self, settings: Dict[str, Any]) -> str:
        """Get formatted connection information string."""
        if settings.get('run_code_locally', True):
            address = '127.0.0.1'
            port = 12080 if settings.get('run_in_mission_env', True) else 12081
        else:
            if settings.get('run_in_mission_env', True):
                address = settings.get('server_address', '127.0.0.1')
                port = settings.get('server_port', 12080)
            else:
                address = settings.get('server_address_gui', settings.get('server_address', '127.0.0.1'))
                port = settings.get('server_port_gui', settings.get('server_port', 12080) + 1)
        
        protocol = 'https' if settings.get('use_https', False) and not settings.get('run_code_locally', True) else 'http'
        env = 'Mission' if settings.get('run_in_mission_env', True) else 'GUI'
        location = 'Local' if settings.get('run_code_locally', True) else 'Remote'
        
        return f"{location} | {env} | {protocol}://{address}:{port}"
