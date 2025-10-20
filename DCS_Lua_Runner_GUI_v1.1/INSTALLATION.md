# DCS Lua Runner GUI v1.1 - Installation Guide 
 
## Quick Start 
 
1. **Double-click** `DCS_Lua_Runner_GUI.exe` to start the application 
2. **Configure settings** in the Settings tab: 
   - For local DCS: Leave "Run Code Locally" checked 
   - For remote DCS: Uncheck local and enter server details 
3. **Write Lua code** in the editor 
4. **Press F5** to run code or **F8** for selected code 
 
## DCS Setup Required 
 
**You must install the DCS Fiddle server script for this to work:** 
 
1. **Copy** `dcs-fiddle-server.lua` to: 
   `%USERPROFILE%\Saved Games\[DCS_VERSION]\Scripts\Hooks\` 
   (Create the `Scripts\Hooks` folder if it doesn't exist) 
 
2. **De-sanitize Mission Scripting** by editing: 
   `[DCS_INSTALL]\Scripts\MissionScripting.lua` 
   Comment out the require and package lines: 
   ```lua 
   --  _G['require'] = nil 
   --  _G['package'] = nil 
   ``` 
 
## Features 
 
- ✅ **Standalone executable** - No Python installation required 
- 🎨 **Dark theme** with syntax highlighting 
- 🔗 **Local and remote** DCS server support 
- 🔒 **Authentication** for remote servers 
- ⚙️ **Mission and GUI** environment support 
- 📁 **File operations** - Open, save, create Lua files 
- 📊 **Result formatting** - Lua tables or JSON 
- ⌨️ **Keyboard shortcuts** - F5 to run, F8 for selected 
 
## Troubleshooting 
 
- **Connection errors**: Check DCS Fiddle server is installed and running 
- **Permission errors**: Run as administrator if needed 
- **Antivirus warnings**: Add exception for the executable 
