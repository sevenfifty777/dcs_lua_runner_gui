"""
DCS Client module for handling HTTP communication with DCS servers.
Based on the VSCode extension functionality.
"""

import base64
import json
import requests
from typing import Dict, Any, Optional, Tuple


class DCSClient:
    """Handles communication with DCS Fiddle servers."""
    
    def __init__(self):
        self.timeout = 3.0
        
    def run_lua(self, lua_code: str, settings: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Execute Lua code on DCS server.
        
        Args:
            lua_code: The Lua code to execute
            settings: Dictionary containing connection settings
            
        Returns:
            Tuple of (success: bool, result: Any)
        """
        try:
            # Encode Lua code to base64
            lua_base64 = base64.b64encode(lua_code.encode('utf-8')).decode('ascii')
            
            # Build server URL
            protocol = 'https' if settings.get('use_https', False) else 'http'
            
            if settings.get('run_code_locally', True):
                server_address = '127.0.0.1'
                server_port = 12080 if settings.get('run_in_mission_env', True) else 12081
                use_auth = False
            else:
                if settings.get('run_in_mission_env', True):
                    server_address = settings.get('server_address', '127.0.0.1')
                    server_port = settings.get('server_port', 12080)
                else:
                    server_address = settings.get('server_address_gui', settings.get('server_address', '127.0.0.1'))
                    server_port = settings.get('server_port_gui', settings.get('server_port', 12080) + 1)
                use_auth = True
            
            url = f"{protocol}://{server_address}:{server_port}/{lua_base64}?env=default"
            
            # Prepare request parameters
            request_kwargs = {
                'timeout': self.timeout
            }
            
            # Add authentication if needed
            if use_auth and not settings.get('run_code_locally', True):
                username = settings.get('web_auth_username', 'username')
                password = settings.get('web_auth_password', 'password')
                request_kwargs['auth'] = (username, password)
            
            # Make request
            response = requests.get(url, **request_kwargs)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return True, data['result']
                else:
                    return True, "SUCCESSFUL EXECUTION - NO RETURN VALUE"
            elif response.status_code == 500:
                # Internal server error with error details
                try:
                    error_data = response.json()
                    return False, error_data.get('error', 'Internal server error')
                except:
                    return False, 'Internal server error occurred'
            else:
                return False, f"HTTP {response.status_code}: {response.reason}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout - check server connection"
        except requests.exceptions.ConnectionError:
            return False, "Connection error - check server address and port"
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def format_result_as_lua(self, result: Any) -> str:
        """
        Convert JSON result to Lua table format.
        Based on the VSCode extension's formatting logic.
        """
        if result is None:
            return "nil"
        
        json_string = json.dumps(result, indent=4)
        
        # Convert JSON syntax to Lua syntax
        lua_string = json_string
        lua_string = lua_string.replace('null', 'nil')  # Replace null with nil
        lua_string = lua_string.replace('"_([0-9]+(?:\\.[0-9]+)?)": ', '[\\1] = ')  # Replace "_n": with [n] =
        lua_string = lua_string.replace('"([0-9]+(?:\\.[0-9]+)?)": ', '[\\1] = ')   # Replace "n": with [n] =
        
        # Replace "key": with ["key"] = for string keys
        import re
        lua_string = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"\s*:', r'["\1"] =', lua_string)
        
        # Replace array brackets with table brackets
        lua_string = lua_string.replace('[', '{').replace(']', '}')
        
        return lua_string
