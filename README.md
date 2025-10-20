# DCS Lua Runner GUI

A standalone Windows GUI application for executing Lua code in DCS World, replacing the need for VSCode extension or web interface.

## Features

- **Lua Code Editor**: Syntax highlighting and line numbers for Lua code
- **Local/Remote Execution**: Run code on local DCS instance or remote servers
- **Environment Support**: Execute in Mission or GUI scripting environments
- **Authentication**: Username/password authentication for remote servers
- **Result Formatting**: Display results as Lua tables or JSON
- **Settings Persistence**: Save and load connection settings
- **File Operations**: Open, save, and manage Lua files


## Based On

This application replicates the functionality of:
- [DCS Lua Runner VSCode Extension](https://github.com/omltcat/dcs-lua-runner)
- [DCS Fiddle Web Interface](https://github.com/flying-dice/dcs-fiddle)

## Requirements

- Python 3.7 or higher
- DCS World with DCS Fiddle server script installed
- Required Python packages (see requirements.txt)

## Installation

### Option 1: Windows Executable (Recommended)
1. **Download** the latest release from the `DCS_Lua_Runner_GUI_v1.0` folder
2. **Double-click** `DCS_Lua_Runner_GUI.exe` to start the application
3. **Setup DCS Fiddle Server**: Follow the DCS setup instructions below

### Option 2: Run from Python Source
1. **Clone or Download** this repository
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   python main.py
   ```
4. **Setup DCS Fiddle Server**: Follow the DCS setup instructions below

## DCS Setup

You need to install the DCS Fiddle server script in your DCS installation:

1. **Download** the `dcs-fiddle-server.lua` script (included in this repository)
2. **Copy** to `%USERPROFILE%\Saved Games\<DCS VERSION>\Scripts\Hooks\`
3. **De-sanitize Mission Scripting** (edit `DCS_INSTALL\Scripts\MissionScripting.lua`):
   ```lua
   do
       sanitizeModule('os')
       sanitizeModule('io')
       sanitizeModule('lfs')
   --  _G['require'] = nil
       _G['loadlib'] = nil
   --  _G['package'] = nil
   end
   ```

### Remote Access Configuration

To enable remote access, modify `dcs-fiddle-server.lua`:

```lua
FIDDLE.PORT = 12080         -- keep at 12080 for compatibility
FIDDLE.BIND_IP = '0.0.0.0'  -- enable remote access
FIDDLE.AUTH = true          -- enable authentication (recommended)
FIDDLE.USERNAME = 'your_username'    -- set your username
FIDDLE.PASSWORD = 'your_password'    -- set your password
```

## Usage

1. **Run the application**:
   ```bash
   python main.py
   ```

2. **Configure connection settings** in the Settings tab:
   - Server address and port
   - Authentication credentials
   - Execution environment preferences
   - **IMPORTANT**: Click "Save Settings" after entering all connection details to persist your configuration

3. **Write or load Lua code** in the editor

4. **Execute code** using:
   - `F5` - Run all code
   - `F8` - Run selected code
   - Toolbar buttons
   - Menu options

5. **View results** in the Results tab with syntax highlighting

## Interface Overview

### Toolbar
- **📁 Load File**: Load Lua file with options (replace, append, or insert at cursor)
- **▶ Run**: Execute all code in editor
- **▶ Selected**: Execute selected code only
- **Local/Remote**: Toggle execution target
- **Mission/GUI**: Toggle DCS environment
- **Lua/JSON**: Toggle result format

### Settings Tab
- **Connection Settings**: Server address, ports, HTTPS
- **Authentication**: Username and password for remote access
- **Execution Settings**: Local/remote and environment toggles
- **Display Settings**: Result format preferences

### Code Editor
- Syntax highlighting for Lua code
- Line numbers
- Standard editing features (cut, copy, paste, undo)
- File operations (new, open, save)

### Results Tab
- Timestamped execution results
- Syntax highlighting for results
- Success/error indication
- Scrollable output with clear option

## Keyboard Shortcuts

- `Ctrl+N` - New file
- `Ctrl+O` - Open file
- `Ctrl+S` - Save file
- `Ctrl+Shift+S` - Save as
- `F5` - Run code
- `F8` - Run selected code
- `Ctrl+X` - Cut
- `Ctrl+C` - Copy
- `Ctrl+V` - Paste
- `Ctrl+A` - Select all

## Example Lua Code

```lua
-- Get mission information
local mission_time = timer.getTime()
local theatre = env.mission.theatre

-- Get player information
local player = world.getPlayer()
if player then
    local pos = player:getPosition().p
    return {
        mission_time = mission_time,
        theatre = theatre,
        player_name = player:getName(),
        player_position = {
            x = pos.x,
            y = pos.y,
            z = pos.z
        }
    }
else
    return {
        mission_time = mission_time,
        theatre = theatre,
        message = "No player found"
    }
end
```

## Configuration File

Settings are automatically saved to `dcs_lua_runner_settings.json` in the application directory. This includes:
- Connection settings
- Authentication credentials
- Window size and preferences
- Execution defaults

## Troubleshooting

### Connection Issues
- Verify DCS Fiddle server is running
- Check server address and port settings
- Ensure firewall allows connections (for remote access)
- Verify authentication credentials

### Script Errors
- Check Lua syntax in the editor
- Verify DCS environment (Mission vs GUI)
- Check DCS logs for detailed error information

### Installation Issues
- Ensure Python 3.7+ is installed
- Install dependencies: `pip install -r requirements.txt`
- Run from the correct directory

## License

MIT License - Based on the original DCS Fiddle project by JonathanTurnock and john681611.

## Credits

- Original DCS Fiddle: [JonathanTurnock](https://github.com/JonathanTurnock) and [john681611](https://github.com/john681611)
- DCS Lua Runner VSCode Extension: [omltcat](https://github.com/omltcat)
- GUI Implementation: Created for standalone Windows application
