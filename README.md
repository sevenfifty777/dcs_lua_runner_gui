# DCS Lua Runner GUI

A standalone Windows GUI application for executing Lua code in DCS World, replacing the need for VSCode extension or web interface.

## ⚠️ **SECURITY WARNING** ⚠️

**CRITICAL: This application requires DCS desanitization and may expose your system to significant security risks. Please read all warnings before proceeding.**

### **Major Security Risks**

#### **🔓 DCS Desanitization Risks**
- **Removes DCS security restrictions** - Allows unrestricted Lua execution
- **Full system access** - Scripts can access files, network, and system functions
- **No sandboxing** - Malicious code can damage your system or steal data
- **Persistent changes** - Effects remain until manually reverted

#### **🌐 Network Exposure Risks** 
- **Opens network ports** - DCS Fiddle server listens on network interfaces
- **Remote code execution** - Anyone with access can run arbitrary Lua code on your system
- **Credential vulnerabilities** - Weak authentication may be bypassed
- **Data exposure** - Mission files and system information may be accessible remotely

#### **⚡ DCS Fiddle Specific Risks**
- **Unrestricted API access** - Full DCS scripting environment exposure
- **Mission interference** - Can affect running missions and multiplayer sessions  
- **Performance impact** - May cause DCS instability or crashes
- **Log exposure** - Sensitive information may be logged or transmitted

### **🛡️ Risk Mitigation**

**ONLY proceed if you:**
- ✅ **Understand the security implications** completely
- ✅ **Trust all code** you plan to execute  
- ✅ **Use on isolated systems** (not production/online gaming PCs)
- ✅ **Have proper backups** of your DCS installation
- ✅ **Use strong authentication** for remote access
- ✅ **Restrict network access** (firewall rules, VPN-only access)
- ✅ **Monitor system activity** when running unknown scripts

**⛔ DO NOT USE if:**
- ❌ You don't understand the technical implications
- ❌ Your Sever contains sensitive personal/work data  
- ❌ You plan to run untrusted code from others
- ❌ You use the same PC for online banking/shopping

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

### ⚠️ **CRITICAL SECURITY NOTICE** ⚠️

**The following steps will DISABLE DCS security protections. This creates serious security vulnerabilities:**

- **🔥 REMOVES SANDBOXING** - Scripts gain full system access
- **💾 FILE SYSTEM ACCESS** - Can read/write/delete any files on your computer  
- **🌐 NETWORK ACCESS** - Can make network connections to any server
- **⚙️ SYSTEM COMMANDS** - Can execute system commands and programs
- **🔓 PERSISTENT CHANGES** - Security remains disabled until manually restored

**💡 SECURITY BEST PRACTICES:**
- 🔒 **Backup your DCS installation** before proceeding
- 🏠 **Use on isolated/offline systems only** 
- 👀 **Review ALL code before execution** - never run untrusted scripts
- 🔐 **Use strong passwords** for remote access
- 🚪 **Disable when not needed** - re-enable sanitization after use
- 📊 **Monitor system activity** while running scripts

### Installation Steps

You need to install the DCS Fiddle server script in your DCS installation:

1. **Download** the `dcs-fiddle-server.lua` script (included in this repository)
2. **Copy** to `%USERPROFILE%\Saved Games\<DCS VERSION>\Scripts\Hooks\`
3. **⚠️ De-sanitize Mission Scripting** (edit `DCS_INSTALL\Scripts\MissionScripting.lua`):
   ```lua
   do
       sanitizeModule('os')
       sanitizeModule('io')
       sanitizeModule('lfs')
   --  _G['require'] = nil      -- ⚠️ SECURITY: This enables require() function
       _G['loadlib'] = nil
   --  _G['package'] = nil      -- ⚠️ SECURITY: This enables package loading
   end
   ```

**🔄 TO RESTORE SECURITY:** Uncomment these lines (remove `--`) when finished:
```lua
_G['require'] = nil     -- Restore this line to disable require()
_G['package'] = nil     -- Restore this line to disable package loading
```

### Remote Access Configuration

### 🚨 **EXTREME SECURITY RISK** 🚨

**Enabling remote access creates MAXIMUM SECURITY EXPOSURE:**

- **🌍 INTERNET ACCESSIBLE** - Your PC becomes accessible from anywhere on the network/internet
- **💻 REMOTE CODE EXECUTION** - Anyone with credentials can run ANY Lua code on your system
- **🔓 UNSECURED BY DEFAULT** - Basic authentication is easily bypassed or bruted
- **📊 DATA EXFILTRATION** - All DCS data, logs, and accessible files can be stolen
- **🎯 ATTACK VECTOR** - Creates entry point for malicious actors

**🛡️ MANDATORY SECURITY MEASURES:**

1. **🔥 FIREWALL RULES** - Block port 12080 from internet, allow only specific IPs
2. **🔐 STRONG CREDENTIALS** - Use complex passwords (20+ characters, mixed case, numbers, symbols)  
3. **🏠 LOCAL NETWORK ONLY** - Never expose to internet (`BIND_IP = '127.0.0.1'` for local only)
4. **📱 VPN ACCESS** - Use VPN for remote access instead of direct exposure
5. **⏰ TIME LIMITS** - Disable when not actively needed
6. **👀 MONITORING** - Watch logs for unauthorized access attempts

**⚠️ CONFIGURATION OPTIONS:**

```lua
-- SAFER: Local access only (recommended)
FIDDLE.BIND_IP = '127.0.0.1'  -- Local computer only
FIDDLE.PORT = 12080           

-- DANGEROUS: Network/Internet access (high risk)
FIDDLE.BIND_IP = '0.0.0.0'    -- ⚠️ EXPOSES TO NETWORK/INTERNET
FIDDLE.PORT = 12080           

-- MANDATORY: Strong authentication
FIDDLE.AUTH = true                    -- ⚠️ NEVER set to false
FIDDLE.USERNAME = 'ComplexUsername123'    -- Use unique, complex username  
FIDDLE.PASSWORD = 'VeryLongComplexPassword456!'  -- 20+ character password
```

**🔴 NEVER DO THIS:**
```lua
FIDDLE.AUTH = false           -- ⚠️ NEVER disable authentication
FIDDLE.PASSWORD = 'password'  -- ⚠️ NEVER use weak passwords
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
