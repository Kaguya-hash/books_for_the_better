@echo off
setlocal EnableDelayedExpansion

:: =========================================================
:: Books for the Better - Uninstaller
:: This file gets copied into the install folder by setup.bat
:: and is what Windows runs when the user clicks "Uninstall" in
:: Settings > Apps > Installed apps.
:: =========================================================

set "APP_NAME=BooksForTheBetter"
set "APP_DISPLAY_NAME=Books for the Better"
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\%APP_NAME%"
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "UNINSTALL_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APP_NAME%"

:: We can't delete INSTALL_DIR while this very .bat is running from
:: inside it (Windows keeps the file locked). So: if we're not already
:: running from %TEMP%, copy ourselves there and relaunch - the TEMP
:: copy is free to delete the real install folder.
echo %~dp0 | findstr /I /C:"%TEMP%" >nul
if errorlevel 1 (
    set "SELFCOPY=%TEMP%\%APP_NAME%_uninstall.bat"
    copy /y "%~f0" "!SELFCOPY!" >nul
    start "" cmd /c "!SELFCOPY!"
    exit /b 0
)

echo ==========================================================
echo Uninstalling %APP_DISPLAY_NAME%...
echo ==========================================================
echo.

set "DESKTOP_DIR="
for /f "delims=" %%D in ('powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')"') do set "DESKTOP_DIR=%%D"

if exist "%STARTMENU_DIR%\conversor_booklet.lnk" del /q "%STARTMENU_DIR%\conversor_booklet.lnk"
if defined DESKTOP_DIR if exist "%DESKTOP_DIR%\conversor_booklet.lnk" del /q "%DESKTOP_DIR%\conversor_booklet.lnk"

reg delete "%UNINSTALL_KEY%" /f >nul 2>&1

if exist "%INSTALL_DIR%" rd /s /q "%INSTALL_DIR%"

echo [OK] %APP_DISPLAY_NAME% was removed.
pause
