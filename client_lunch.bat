@echo off
REM run_client.bat — run python -m client.app_main using the local venv if present

REM Change to the directory where this .bat is located
pushd "%~dp0"
setlocal

REM Try to detect common venv folders (.venv or venv)
set "VENV_DIR="
if exist ".venv\Scripts\activate.bat" set "VENV_DIR=.venv"
if not defined VENV_DIR if exist "venv\Scripts\activate.bat" set "VENV_DIR=venv"

if defined VENV_DIR (
    echo Activating local venv "%VENV_DIR%".
    REM activate the venv (this modifies PATH for this script session)
    call "%VENV_DIR%\Scripts\activate.bat"
    echo Running: python -m client.app_main
    python -m client.app_main
    goto :cleanup
)

REM If no activate script, try directly invoking venv python executables
if exist ".venv\Scripts\python.exe" (
    echo Using .venv\Scripts\python.exe
    ".venv\Scripts\python.exe" -m client.app_main
    goto :cleanup
)
if exist "venv\Scripts\python.exe" (
    echo Using venv\Scripts\python.exe
    "venv\Scripts\python.exe" -m client.app_main
    goto :cleanup
)

REM Last resort: try system python
echo No local venv detected. Attempting system python...
python -m client.app_main
if errorlevel 1 (
    echo.
    echo Failed to start client with system python.
    echo Make sure you have Python installed or create a virtualenv in ".venv" or "venv".
    pause
)

:cleanup
endlocal
popd
exit /b
