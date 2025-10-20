=== DCS Lua Runner GUI v1.0 - Quick Start Guide ===

🚀 GETTING STARTED
==================

1. Double-click "DCS_Lua_Runner_GUI.exe" to start the application
2. The application will open with a dark theme interface
3. Sample Lua code is already loaded in the editor

⚙️ BASIC SETUP
===============

FOR LOCAL DCS (Default):
- Leave "Run Code Locally" checked in Settings tab
- Make sure DCS is running with dcs-fiddle-server.lua installed

FOR REMOTE DCS:
- Uncheck "Run Code Locally" in Settings tab
- Enter server address, port, username, and password
- Configure authentication in the remote DCS server

🎯 USAGE
=========

RUNNING CODE:
- Press F5 to run all code in the editor
- Press F8 to run only selected code
- Click the ▶ Run button in the toolbar
- Use Run menu options

EDITING:
- Type Lua code directly in the left panel
- Syntax highlighting automatically applies
- Line numbers are shown on the left
- Standard shortcuts work (Ctrl+C, Ctrl+V, etc.)

FILE OPERATIONS:
- Ctrl+O to open .lua files
- Ctrl+S to save current code
- File menu for New, Open, Save As

RESULTS:
- View results in the Results tab (right panel)
- Results show timestamp and success/error status
- Syntax highlighting for both Lua and JSON formats
- Toggle format with the Lua/JSON button

📋 REQUIRED DCS SETUP
======================

YOU MUST INSTALL THE DCS FIDDLE SERVER SCRIPT:

1. Copy "dcs-fiddle-server.lua" to:
   %USERPROFILE%\Saved Games\DCS.openbeta\Scripts\Hooks\
   (or your DCS version folder like DCS, DCS.release_server, etc.)

2. Edit DCS Mission Scripting file:
   [DCS Install]\Scripts\MissionScripting.lua
   Comment out these lines:
   --  _G['require'] = nil
   --  _G['package'] = nil

3. Restart DCS World

🔧 QUICK SETTINGS
==================

TOOLBAR BUTTONS:
- ▶ Run: Execute all code
- ▶ Selected: Execute selected code only
- Local/Remote: Toggle between local DCS and remote server
- Mission/GUI: Toggle between Mission and GUI environments
- Lua/JSON: Toggle result display format

KEYBOARD SHORTCUTS:
- F5: Run all code
- F8: Run selected code
- Ctrl+S: Save file
- Ctrl+O: Open file
- Ctrl+N: New file

❗ TROUBLESHOOTING
==================

CONNECTION ERRORS:
- Check DCS is running
- Verify dcs-fiddle-server.lua is installed
- For remote: check server address, port, and credentials
- Check Windows Firewall settings

ANTIVIRUS WARNINGS:
- Add DCS_Lua_Runner_GUI.exe to antivirus exceptions
- The executable is safe (built with PyInstaller)

PERMISSION ERRORS:
- Run as administrator if needed
- Check file permissions in DCS directories

EXAMPLE CODE:
- The editor starts with sample code you can run immediately
- Try: return env.mission.theatre
- Or: return timer.getTime()

📚 MORE INFO
=============

- Full documentation: README.md
- Installation details: INSTALLATION.md
- Based on DCS Fiddle project (MIT License)
- No Python installation required for the executable

🎉 ENJOY!
=========

You now have a standalone DCS Lua development environment!
Perfect for mission scripting, debugging, and testing Lua code in DCS World.
