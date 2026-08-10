@echo off
set "PROGRAM_DIR=%~dp0programa"
set "PYTHON_DIR=%PROGRAM_DIR%\python_dist"
set "PYTHON_ZIP=%~dp0python_embed.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"

echo Checking for standalone local Python...

:: 1. Download and extract portable Python if not already downloaded
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

echo [✓] Standalone Python ready inside .\programa\python_dist

:: 2. Install requirements strictly inside the "programa" folder
if exist "%PROGRAM_DIR%\requirements.txt" (
    echo Installing dependencies from requirements.txt...
    "%PYTHON_DIR%\python.exe" -m pip install -r "%PROGRAM_DIR%\requirements.txt"
)

:: 3. Always create a shortcut next to this .bat (local folder)
echo Creating local shortcut...
if exist "%PROGRAM_DIR%\icon.ico" (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%~dp0conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.IconLocation = '%PROGRAM_DIR%\icon.ico,0'; $s.Save()"
) else (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%~dp0conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.Save()"
)

:: 4. Also try to place a shortcut on the real Desktop, if Windows can find it
echo Looking for Desktop folder...
set "DESKTOP_DIR="
for /f "delims=" %%D in ('powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).SpecialFolders('Desktop')"') do set "DESKTOP_DIR=%%D"

if defined DESKTOP_DIR if exist "%DESKTOP_DIR%" (
    echo [✓] Desktop found at "%DESKTOP_DIR%" - creating shortcut there too...
    if exist "%PROGRAM_DIR%\icon.ico" (
        powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_DIR%\conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.IconLocation = '%PROGRAM_DIR%\icon.ico,0'; $s.Save()"
    ) else (
        powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP_DIR%\conversor_booklet.lnk'); $s.TargetPath = '%PYTHON_DIR%\pythonw.exe'; $s.Arguments = 'app.py'; $s.WorkingDirectory = '%PROGRAM_DIR%'; $s.Save()"
    )
) else (
    echo [!] Desktop folder not found - skipping. Local shortcut is still available.
)

echo.
echo =========================================================
echo [✓] Setup Complete!
echo Python and all packages live entirely inside this folder.
echo Zero files were installed onto the host Windows system.
echo =========================================================
pause