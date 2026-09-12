@echo off
REM ========================================================
REM  Market Radar Automation - Portable Edition
REM ========================================================

REM Switch to script directory
cd /d "%~dp0"

REM Auto-detect Python path
if exist "%~dp0backend\venv\Scripts\python.exe" (
    set PY_PATH="%~dp0backend\venv\Scripts\python.exe"
) else if exist "%~dp0..\radar_env\python.exe" (
    set PY_PATH="%~dp0..\radar_env\python.exe"
) else (
    set PY_PATH=python
)

echo [1/5] Using Python: %PY_PATH%

REM Run Stock ETL
echo.
echo [2/5] Running Stock ETL...
%PY_PATH% -m backend.data_updater
if %ERRORLEVEL% neq 0 (
    echo [WARN] Stock ETL failed with code %ERRORLEVEL%
)

REM Run Macro ETL
echo.
echo [3/5] Running Macro ETL...
%PY_PATH% -m backend.scrapers.macro
if %ERRORLEVEL% neq 0 (
    echo [WARN] Macro ETL failed with code %ERRORLEVEL%
)

REM Run Event Scraper
echo.
echo [4/5] Running Event Scraper...
%PY_PATH% -m backend.event_scraper
if %ERRORLEVEL% neq 0 (
    echo [WARN] Event Scraper failed with code %ERRORLEVEL%
)

REM Run Global Intelligence ETL
echo.
echo [5/5] Running Global Intelligence ETL...
%PY_PATH% -m backend.global_updater
if %ERRORLEVEL% neq 0 (
    echo [WARN] Global ETL failed with code %ERRORLEVEL%
)

echo.
echo ===================================================
echo  [Done] System Update Complete!
echo ===================================================
pause