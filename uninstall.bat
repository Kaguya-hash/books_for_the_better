@echo off
setlocal EnableDelayedExpansion

:: =========================================================
:: Books for the Better - Uninstaller
::
:: This file gets copied into the install folder by setup.bat
:: and is what Windows runs when the user clicks "Uninstall" in
:: Settings > Apps > Installed apps.
:: =========================================================

:: ---- App identity (must match setup.bat) ----
set "APP_NAME=BooksForTheBetter"
set "APP_DISPLAY_NAME=Books for the Better"
set "SHORTCUT_NAME=%APP_DISPLAY_NAME%.lnk"

:: ---- Install paths ----
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\%APP_NAME%"
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

:: ---- Windows registration ----
set "UNINSTALL_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APP_NAME%"

:: =========================================================
:: Main flow
:: =========================================================

call :RelaunchFromTempIfNeeded
if errorlevel 1 exit /b 0

echo ==========================================================
echo Uninstalling %APP_DISPLAY_NAME%...
echo ==========================================================
echo.

call :RemoveShortcuts
call :RemoveRegistration
call :RemoveInstallDir

echo [OK] %APP_DISPLAY_NAME% was removed.
pause
exit /b 0

:: =========================================================
:: Subroutines
:: =========================================================

:RelaunchFromTempIfNeeded
:: We can't delete INSTALL_DIR while this very .bat is running from
:: inside it (Windows keeps the file locked). So: if we're not already
:: running from %TEMP%, copy ourselves there and relaunch - the TEMP
:: copy is free to delete the real install folder. When this happens,
:: the whole script exits here and the TEMP copy takes over.
echo %~dp0 | findstr /I /C:"%TEMP%" >nul
if errorlevel 1 (
    set "SELFCOPY=%TEMP%\%APP_NAME%_uninstall.bat"
    copy /y "%~f0" "!SELFCOPY!" >nul
    start "" cmd /c "!SELFCOPY!"
    exit /b 1
)
exit /b 0

:RemoveShortcuts
:: Removes the Start Menu shortcut, and the Desktop one if a real
:: Desktop folder can be located.
if exist "%STARTMENU_DIR%\%SHORTCUT_NAME%" del /q "%STARTMENU_DIR%\%SHORTCUT_NAME%"

set "DESKTOP_DIR="
for /f "delims=" %%D in ('powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')"') do set "DESKTOP_DIR=%%D"
if defined DESKTOP_DIR if exist "%DESKTOP_DIR%\%SHORTCUT_NAME%" del /q "%DESKTOP_DIR%\%SHORTCUT_NAME%"
exit /b 0

:RemoveRegistration
:: Removes the "Installed apps" entry created by setup.bat.
reg delete "%UNINSTALL_KEY%" /f >nul 2>&1
exit /b 0

:RemoveInstallDir
:: Deletes the app's per-user install folder (programa, python_dist,
:: this uninstaller's original copy, everything).
if exist "%INSTALL_DIR%" rd /s /q "%INSTALL_DIR%"
exit /b 0
