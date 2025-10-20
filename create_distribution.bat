@echo off
echo Creating DCS Lua Runner GUI Distribution Package...
echo ================================================

REM Prompt for version number
set /p VERSION=Enter version number (e.g., 1.0, 1.1, 2.0): 
if "%VERSION%"=="" (
    echo No version specified. Using default v1.0
    set VERSION=1.0
)

REM Set distribution directory name
set DIST_DIR=DCS_Lua_Runner_GUI_v%VERSION%

echo.
echo Creating distribution package: %DIST_DIR%
echo.

REM Step 1: Rebuild executable with latest code
echo ================================================
echo Step 1/2: Building executable with latest code...
echo ================================================
echo Running PyInstaller to create fresh executable...
pyinstaller build_exe.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build executable!
    echo Please check that PyInstaller is installed and build_exe.spec is correct.
    pause
    exit /b 1
)
echo Executable built successfully!
echo.

REM Step 2: Create distribution package
echo ================================================
echo Step 2/2: Creating distribution package...
echo ================================================

REM Create distribution directory
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

REM Copy executable
copy "dist\DCS_Lua_Runner_GUI.exe" "%DIST_DIR%\"

REM Copy documentation and setup files
copy "README.md" "%DIST_DIR%\"
copy "dcs-fiddle-server.lua" "%DIST_DIR%\"
copy "LICENSE" "%DIST_DIR%\"
copy "QUICK_START.md" "%DIST_DIR%\" 2>nul

REM Create installation guide
echo Creating installation guide...

echo # DCS Lua Runner GUI v%VERSION% - Installation Guide > "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo ## Quick Start >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo 1. **Double-click** `DCS_Lua_Runner_GUI.exe` to start the application >> "%DIST_DIR%\INSTALLATION.md"
echo 2. **Configure settings** in the Settings tab: >> "%DIST_DIR%\INSTALLATION.md"
echo    - For local DCS: Leave "Run Code Locally" checked >> "%DIST_DIR%\INSTALLATION.md"
echo    - For remote DCS: Uncheck local and enter server details >> "%DIST_DIR%\INSTALLATION.md"
echo 3. **Write Lua code** in the editor >> "%DIST_DIR%\INSTALLATION.md"
echo 4. **Press F5** to run code or **F8** for selected code >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo ## DCS Setup Required >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo **You must install the DCS Fiddle server script for this to work:** >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo 1. **Copy** `dcs-fiddle-server.lua` to: >> "%DIST_DIR%\INSTALLATION.md"
echo    `%%USERPROFILE%%\Saved Games\[DCS_VERSION]\Scripts\Hooks\` >> "%DIST_DIR%\INSTALLATION.md"
echo    ^(Create the `Scripts\Hooks` folder if it doesn't exist^) >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo 2. **De-sanitize Mission Scripting** by editing: >> "%DIST_DIR%\INSTALLATION.md"
echo    `[DCS_INSTALL]\Scripts\MissionScripting.lua` >> "%DIST_DIR%\INSTALLATION.md"
echo    Comment out the require and package lines: >> "%DIST_DIR%\INSTALLATION.md"
echo    ```lua >> "%DIST_DIR%\INSTALLATION.md"
echo    --  _G['require'] = nil >> "%DIST_DIR%\INSTALLATION.md"
echo    --  _G['package'] = nil >> "%DIST_DIR%\INSTALLATION.md"
echo    ``` >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo ## Features >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo - ✅ **Standalone executable** - No Python installation required >> "%DIST_DIR%\INSTALLATION.md"
echo - 🎨 **Dark theme** with syntax highlighting >> "%DIST_DIR%\INSTALLATION.md"
echo - 🔗 **Local and remote** DCS server support >> "%DIST_DIR%\INSTALLATION.md"
echo - 🔒 **Authentication** for remote servers >> "%DIST_DIR%\INSTALLATION.md"
echo - ⚙️ **Mission and GUI** environment support >> "%DIST_DIR%\INSTALLATION.md"
echo - 📁 **File operations** - Open, save, create Lua files >> "%DIST_DIR%\INSTALLATION.md"
echo - 📊 **Result formatting** - Lua tables or JSON >> "%DIST_DIR%\INSTALLATION.md"
echo - ⌨️ **Keyboard shortcuts** - F5 to run, F8 for selected >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo ## Troubleshooting >> "%DIST_DIR%\INSTALLATION.md"
echo. >> "%DIST_DIR%\INSTALLATION.md"
echo - **Connection errors**: Check DCS Fiddle server is installed and running >> "%DIST_DIR%\INSTALLATION.md"
echo - **Permission errors**: Run as administrator if needed >> "%DIST_DIR%\INSTALLATION.md"
echo - **Antivirus warnings**: Add exception for the executable >> "%DIST_DIR%\INSTALLATION.md"

echo.
echo ================================================
echo Distribution package created successfully!
echo Location: %DIST_DIR%\
echo Version: v%VERSION%
echo ================================================
echo.
pause
