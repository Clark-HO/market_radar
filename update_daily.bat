@echo off
REM ========================================================
REM  Market Radar Automation - E: Drive Edition
REM ========================================================

REM 1. Configured Python Path (E: Drive)
set PY_PATH=E:\antigravity\radar_env\python.exe

echo [1/3] Checking Environment on E: Drive...
if exist "%PY_PATH%" (
    echo  Target Python found: %PY_PATH%
) else (
    echo  [ERROR] Python path not found at %PY_PATH% !
    echo  Did you create the env on E:?
    pause
    exit /b
)

REM 2. Run ETL (Stocks)
echo.
echo [2/3] Running Stock ETL...
"%PY_PATH%" -m backend.data_updater

REM 3. Run ETL (Macro)
echo.
echo [3/3] Running Macro ETL...
"%PY_PATH%" -m backend.scrapers.macro

echo.
echo ===================================================
echo  [Done] System Updated Successfully!
echo ===================================================
pause