@echo off
setlocal EnableDelayedExpansion

:: =========================================================
:: Books for the Better - Setup
:: Installs the app to a stable per-user folder
:: (%%LOCALAPPDATA%%\Programs\...) instead of running in-place.
:: If the "programa" folder isn't found next to this script,
:: it is downloaded directly from GitHub straight into that
:: final folder - so, worst case, this .bat file alone is
:: enough to install the app.
:: =========================================================

set "APP_NAME=BooksForTheBetter"
set "APP_DISPLAY_NAME=Books for the Better"
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\%APP_NAME%"
set "PROGRAM_DIR=%INSTALL_DIR%\programa"
set "PYTHON_DIR=%PROGRAM_DIR%\python_dist"
set "PYTHON_ZIP=%TEMP%\python_embed_%APP_NAME%.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "SOURCE_PROGRAM_DIR=%~dp0programa"
set "GITHUB_OWNER=Kaguya-hash"
set "GITHUB_REPO=books_for_the_better"
set "GITHUB_BRANCH=main"
set "REPO_ZIP_URL=https://codeload.github.com/%GITHUB_OWNER%/%GITHUB_REPO%/zip/refs/heads/%GITHUB_BRANCH%"
set "REPO_TEMP_ZIP=%TEMP%\%APP_NAME%_repo_download.zip"
set "REPO_TEMP_EXTRACT=%TEMP%\%APP_NAME%_repo_extract"
set "UNINSTALL_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\%APP_NAME%"

echo ==========================================================
echo %APP_DISPLAY_NAME% - Setup
echo ==========================================================
echo.

:: 0. Get "programa" into place - either from next to this script,
:: or straight from GitHub if it's missing.
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

if exist "%SOURCE_PROGRAM_DIR%" (
    echo [OK] Found local "programa" folder next to this script.
    call :InstallFromLocal
    if errorlevel 1 exit /b 1
) else (
    echo [!] "programa" folder not found next to this script.
    echo [*] Downloading it directly from GitHub...
    echo ^(%GITHUB_OWNER%/%GITHUB_REPO%, branch: %GITHUB_BRANCH%^)
    call :InstallFromGitHub
    if errorlevel 1 exit /b 1
)
echo.

:: 1. Download and extract portable Python if not already installed
echo Checking for standalone local Python...
if not exist "%PYTHON_DIR%\python.exe" (
    echo [!] Local Python not found. Downloading standalone Python package...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'"

    echo Extracting portable Python...
    powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"
    del "%PYTHON_ZIP%"

    echo Enabling library support and local path search...
    powershell -Command "(Get-Content '%PYTHON_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python311._pth'"
    powershell -Command "Add-Content '%PYTHON_DIR%\python311._pth' '..'"

    echo Downloading and configuring pip...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"
    "%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
    del "%PYTHON_DIR%\get-pip.py"
)
echo [OK] Standalone Python ready inside "%PYTHON_DIR%"
echo.

:: 2. Install requirements strictly inside the installed "programa" folder
if exist "%PROGRAM_DIR%\requirements.txt" (
    echo Installing dependencies from requirements.txt...
    "%PYTHON_DIR%\python.exe" -m pip install -r "%PROGRAM_DIR%\requirements.txt"
)
echo.

:: 3. Create a shortcut in the Start Menu (so it also shows up in Windows search)
echo Creating Start Menu shortcut...
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if exist "%PROGRAM_DIR%\icon.ico" (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTMENU_DIR%\conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.IconLocation = '%PROGRAM_DIR%\icon.ico,0'; $s.Save()"
) else (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTMENU_DIR%\conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.Save()"
)

:: 4. Also place a shortcut on the real Desktop, if Windows can find it
echo Looking for Desktop folder...
set "DESKTOP_DIR="
for /f "delims=" %%D in ('powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')"') do set "DESKTOP_DIR=%%D"

if defined DESKTOP_DIR if exist "%DESKTOP_DIR%" (
    echo [OK] Desktop found at "%DESKTOP_DIR%" - creating shortcut there too...
    if exist "%PROGRAM_DIR%\icon.ico" (
        powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_DIR%\conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.IconLocation = '%PROGRAM_DIR%\icon.ico,0'; $s.Save()"
    ) else (
        powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_DIR%\conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.Save()"
    )
) else (
    echo [!] Desktop folder not found - skipping. Start Menu shortcut is still available.
)
echo.

:: 5. Install the uninstaller and register the app so it shows up in
:: Settings > Apps > Installed apps (per-user, HKCU - no admin needed).
echo Installing uninstaller...
if exist "%~dp0uninstall.bat" (
    copy /y "%~dp0uninstall.bat" "%INSTALL_DIR%\uninstall.bat" >nul
)
if not exist "%INSTALL_DIR%\uninstall.bat" (
    echo [!] uninstall.bat not found - the app will still work, but won't
    echo     appear in "Installed apps" until this is fixed.
) else (
    echo Registering app in Windows...
    reg add "%UNINSTALL_KEY%" /v "DisplayName" /t REG_SZ /d "%APP_DISPLAY_NAME%" /f >nul
    reg add "%UNINSTALL_KEY%" /v "UninstallString" /t REG_SZ /d "\"%INSTALL_DIR%\uninstall.bat\"" /f >nul
    reg add "%UNINSTALL_KEY%" /v "QuietUninstallString" /t REG_SZ /d "\"%INSTALL_DIR%\uninstall.bat\"" /f >nul
    reg add "%UNINSTALL_KEY%" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul
    reg add "%UNINSTALL_KEY%" /v "Publisher" /t REG_SZ /d "%GITHUB_OWNER%" /f >nul
    reg add "%UNINSTALL_KEY%" /v "DisplayVersion" /t REG_SZ /d "1.0.0" /f >nul
    reg add "%UNINSTALL_KEY%" /v "NoModify" /t REG_DWORD /d 1 /f >nul
    reg add "%UNINSTALL_KEY%" /v "NoRepair" /t REG_DWORD /d 1 /f >nul
    if exist "%PROGRAM_DIR%\icon.ico" (
        reg add "%UNINSTALL_KEY%" /v "DisplayIcon" /t REG_SZ /d "%PROGRAM_DIR%\icon.ico" /f >nul
    )
    echo [OK] App registered - it will now appear under "Installed apps".
)
echo.

echo ==========================================================
echo [OK] Setup Complete!
echo.
echo %APP_DISPLAY_NAME% is now installed at:
echo %INSTALL_DIR%
echo.
echo You can now delete the folder you downloaded/extracted this
echo setup.bat from - the app itself no longer depends on it.
echo Use the Desktop or Start Menu shortcut to open the app, or
echo uninstall it later from Settings ^> Apps ^> Installed apps.
echo ==========================================================
pause
exit /b 0

:: =========================================================
:: Subroutines
:: =========================================================

:InstallFromLocal
:: Copies the local "programa" folder (next to this script) into
:: the final install location. A copy here is unavoidable since
:: we must not touch/delete the user's original repo folder.
if exist "%PROGRAM_DIR%" (
    echo Refreshing application files ^(keeping existing Python install^)...
) else (
    echo [*] Installing app to "%INSTALL_DIR%"...
)
xcopy "%SOURCE_PROGRAM_DIR%" "%PROGRAM_DIR%\" /E /I /Y >nul
if errorlevel 1 (
    echo [!] Failed to copy application files. Aborting.
    pause
    exit /b 1
)
echo [OK] Files ready at "%PROGRAM_DIR%".
exit /b 0

:InstallFromGitHub
:: Downloads the repo zip, extracts it to a temp folder (unavoidable,
:: since the zip wraps everything in a "repo-branch" folder), then
:: moves the "programa" folder STRAIGHT into its final home - no
:: extra copy step. Only falls back to a merge-copy if an install
:: already exists at PROGRAM_DIR (so python_dist isn't wiped out).
if exist "%REPO_TEMP_ZIP%" del /q "%REPO_TEMP_ZIP%"
if exist "%REPO_TEMP_EXTRACT%" rd /s /q "%REPO_TEMP_EXTRACT%"

powershell -Command "try { Invoke-WebRequest -Uri '%REPO_ZIP_URL%' -OutFile '%REPO_TEMP_ZIP%' } catch { exit 1 }"
if not exist "%REPO_TEMP_ZIP%" (
    echo [!] Download failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Extracting downloaded repository...
powershell -Command "Expand-Archive -Path '%REPO_TEMP_ZIP%' -DestinationPath '%REPO_TEMP_EXTRACT%' -Force"
del "%REPO_TEMP_ZIP%"

set "DOWNLOADED_PROGRAM_DIR=%REPO_TEMP_EXTRACT%\%GITHUB_REPO%-%GITHUB_BRANCH%\programa"
if not exist "%DOWNLOADED_PROGRAM_DIR%\app.py" (
    echo [!] Could not find "programa" folder inside the downloaded repository.
    echo The repository layout may have changed - check %REPO_ZIP_URL%
    if exist "%REPO_TEMP_EXTRACT%" rd /s /q "%REPO_TEMP_EXTRACT%"
    pause
    exit /b 1
)

if exist "%PROGRAM_DIR%" (
    echo An install already exists - merging in the freshly downloaded files...
    xcopy "%DOWNLOADED_PROGRAM_DIR%" "%PROGRAM_DIR%\" /E /I /Y >nul
) else (
    echo [*] Moving downloaded "programa" folder straight to "%INSTALL_DIR%"...
    move "%DOWNLOADED_PROGRAM_DIR%" "%PROGRAM_DIR%" >nul
)

:: Also grab uninstall.bat from the same download, so the GitHub-only
:: install path (no local "programa" folder) still gets an uninstaller.
set "DOWNLOADED_ROOT=%REPO_TEMP_EXTRACT%\%GITHUB_REPO%-%GITHUB_BRANCH%"
if exist "%DOWNLOADED_ROOT%\uninstall.bat" (
    copy /y "%DOWNLOADED_ROOT%\uninstall.bat" "%INSTALL_DIR%\uninstall.bat" >nul
)

if exist "%REPO_TEMP_EXTRACT%" rd /s /q "%REPO_TEMP_EXTRACT%"
echo [OK] "programa" installed at "%PROGRAM_DIR%".
exit /b 0
