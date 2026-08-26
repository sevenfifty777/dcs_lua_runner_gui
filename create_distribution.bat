@echo off
setlocal

if "%~1"=="" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_distribution.ps1"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_distribution.ps1" -Version "%~1"
)

if errorlevel 1 (
    echo Distribution build failed.
    exit /b 1
)

echo Distribution build completed successfully.
endlocal
