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
- **Creates loopback listeners** - Local software can reach the DCS Lua service
- **Remote code execution** - A compromised authorized client can run arbitrary Lua
- **Authentication is critical** - Protect and revoke client keys promptly
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
- **HTTPS Execution**: Run code through dedicated Caddy endpoints
- **Environment Support**: Execute in Mission or GUI scripting environments
- **Strong Authentication**: Mutual TLS client certificates plus a private
  Caddy-to-DCS proxy token
- **Result Formatting**: Display results as Lua tables or JSON
- **Settings Persistence**: Save and load connection settings
- **File Operations**: Open, save, and manage Lua files


## Based On

This application replicates the functionality of:
- [DCS Lua Runner VSCode Extension](https://github.com/omltcat/dcs-lua-runner)
- [DCS Fiddle Web Interface](https://github.com/flying-dice/dcs-fiddle)

## Requirements

- Python 3.10 or higher when running from source
- DCS World with the secure Lua Runner server and external configuration installed
- Caddy serving the Mission and Hooks endpoints over HTTPS
- A trusted client certificate and ACL-protected unencrypted PEM private key
- Required Python packages (see requirements.txt)

## Installation

### Option 1: Windows Executable

The checked-in v1.0 executable uses the retired GET/Basic protocol and is not
compatible with the secure server. Do not deploy it. A v2 executable must be
rebuilt and validated from the updated source before release. A local
`v2.0-dev` package may be produced for controlled testing, but it is not a
production release until the Caddy and live DCS gates pass.

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

For release builds, use an isolated virtual environment and install the fully
resolved Windows `requirements.lock`. `requirements-build.txt` records the
direct build inputs. The build script requires the pinned PyInstaller version
before it will create an artifact.

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
- 🔐 **Protect client private keys** with restrictive Windows ACLs
- 🚪 **Disable when not needed** - re-enable sanitization after use
- 📊 **Monitor system activity** while running scripts

### Installation Steps

You need to install the DCS Fiddle server script in your DCS installation:

1. **Download** the `dcs-fiddle-server.lua` script (included in this repository)
2. **Copy** to `%USERPROFILE%\Saved Games\<DCS VERSION>\Scripts\Hooks\`
3. Copy `dcs-fiddle-config.lua.example` beside it as
   `dcs-fiddle-config.lua`.
4. Generate a cryptographically random proxy token containing at least 256 bits
   of entropy and place it in the untracked configuration. Supply the same value
   to the Caddy Windows service as `DCS_FIDDLE_PROXY_TOKEN`.
5. Keep `bind_ip = "127.0.0.1"`, Mission port 12080, and Hooks port 12081.
6. **⚠️ De-sanitize Mission Scripting** (edit `DCS_INSTALL\Scripts\MissionScripting.lua`):
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

The Lua ports must never be published. The topology below uses reserved
`example.com` placeholders; replace them with your own DNS names:

```text
fiddle.example.com     -> Caddy HTTPS + mTLS -> 127.0.0.1:12080
fiddle-gui.example.com -> Caddy HTTPS + mTLS -> 127.0.0.1:12081
```

Only TCP 80 and 443 are publicly allowed. TCP 3001, 8090, 12080, and 12081 are
blocked externally. Use [deploy/Caddyfile.example](deploy/Caddyfile.example) as
the starting point, then follow
[docs/CADDY_MTLS_SETUP.md](docs/CADDY_MTLS_SETUP.md) and validate the active
Caddyfile before reload.

The complete design and rollout references are
[security architecture](docs/SECURITY_ARCHITECTURE.md),
[protocol v2](docs/PROTOCOL_V2.md),
[v1 migration](docs/MIGRATION_V1_TO_V2.md), and
[test/validation](docs/TEST_AND_VALIDATION.md).

The GUI presents a client certificate to Caddy. Caddy injects a separate
`X-DCS-Proxy-Token` header for the loopback Lua service. The GUI never receives
or stores that internal token.

## Usage

1. **Run the application**:
   ```bash
   python main.py or launch DCS_Lua_Runner_GUI.exe
   ```

2. **Configure connection settings** in the Settings tab:
   - Mission and Hooks HTTPS URLs
   - Client certificate and private-key paths
   - Optional private CA bundle; leave empty for normal public Web PKI
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
- **Mission/GUI**: Toggle DCS environment
- **Lua/JSON**: Toggle result format

### Settings Tab
- **Connection Settings**: Dedicated Mission and Hooks HTTPS endpoints
- **Mutual TLS**: CA bundle, client certificate, and client private-key paths
- **Execution Settings**: Mission or Hooks/GUI environment
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

Settings are saved to `%APPDATA%\DCSLuaRunner\settings.json`. The file contains:
- Connection settings
- Certificate and private-key paths, but no passwords, tokens, or key contents
- Window size and preferences
- Execution defaults

When a legacy settings file is found, non-secret values are migrated and the
legacy plaintext password file is replaced with a migration marker after the new
settings file is saved.

## Troubleshooting

### Connection Issues
- Verify DCS Fiddle server is running
- Check the two HTTPS endpoint settings
- Verify Caddy can reach the loopback backend
- Verify the client certificate chains to the CA trusted by Caddy
- Verify the private key is readable by the current Windows user

### Script Errors
- Check Lua syntax in the editor
- Verify DCS environment (Mission vs GUI)
- Check DCS logs for detailed error information

### Installation Issues
- Ensure Python 3.10+ is installed
- Install dependencies: `pip install -r requirements.txt`
- Run from the correct directory

## License

MIT License - Based on the original DCS Fiddle project by JonathanTurnock and john681611.

## Credits

- Original DCS Fiddle: [JonathanTurnock](https://github.com/JonathanTurnock) and [john681611](https://github.com/john681611)
- DCS Lua Runner VSCode Extension: [omltcat](https://github.com/omltcat)
- GUI Implementation: Created for standalone Windows application
