@echo off
echo Creating DCS Lua Runner GUI Distribution Package...
echo ================================================

REM Create distribution directory
if exist "DCS_Lua_Runner_GUI_v1.0" rmdir /s /q "DCS_Lua_Runner_GUI_v1.0"
mkdir "DCS_Lua_Runner_GUI_v1.0"

REM Copy executable
copy "dist\DCS_Lua_Runner_GUI.exe" "DCS_Lua_Runner_GUI_v1.0\"

REM Copy documentation and setup files
copy "README.md" "DCS_Lua_Runner_GUI_v1.0\"
copy "dcs-fiddle-server.lua" "DCS_Lua_Runner_GUI_v1.0\"
copy "LICENSE" "DCS_Lua_Runner_GUI_v1.0\"
copy "QUICK_START.md" "DCS_Lua_Runner_GUI_v1.0\" 2>nul

REM Create installation guide
echo Creating installation guide...

echo # DCS Lua Runner GUI v1.0 - Installation Guide > "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo ## Quick Start >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo 1. **Double-click** `DCS_Lua_Runner_GUI.exe` to start the application >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo 2. **Configure settings** in the Settings tab: >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    - For local DCS: Leave "Run Code Locally" checked >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    - For remote DCS: Uncheck local and enter server details >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo 3. **Write Lua code** in the editor >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo 4. **Press F5** to run code or **F8** for selected code >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo ## DCS Setup Required >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo **You must install the DCS Fiddle server script for this to work:** >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo 1. **Copy** `dcs-fiddle-server.lua` to: >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    `%%USERPROFILE%%\Saved Games\[DCS_VERSION]\Scripts\Hooks\` >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    ^(Create the `Scripts\Hooks` folder if it doesn't exist^) >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo 2. **De-sanitize Mission Scripting** by editing: >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    `[DCS_INSTALL]\Scripts\MissionScripting.lua` >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    Comment out the require and package lines: >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    ```lua >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    --  _G['require'] = nil >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    --  _G['package'] = nil >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo    ``` >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo ## Features >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - ✅ **Standalone executable** - No Python installation required >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - 🎨 **Dark theme** with syntax highlighting >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - 🔗 **Local and remote** DCS server support >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - 🔒 **Authentication** for remote servers >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - ⚙️ **Mission and GUI** environment support >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - 📁 **File operations** - Open, save, create Lua files >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - 📊 **Result formatting** - Lua tables or JSON >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - ⌨️ **Keyboard shortcuts** - F5 to run, F8 for selected >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo ## Troubleshooting >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo. >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - **Connection errors**: Check DCS Fiddle server is installed and running >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - **Permission errors**: Run as administrator if needed >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"
echo - **Antivirus warnings**: Add exception for the executable >> "DCS_Lua_Runner_GUI_v1.0\INSTALLATION.md"

echo.
echo Distribution package created successfully!
echo Location: DCS_Lua_Runner_GUI_v1.0\
echo.
pause
