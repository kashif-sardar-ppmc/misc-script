@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Force UTF-8 for Python console output.
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "SCRIPT_PATH=%PROJECT_DIR%\sync_attendance.py"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "LOG_DIR=%PROJECT_DIR%\log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d "%PROJECT_DIR%" || exit /b 1

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

for /f %%D in ('powershell.exe -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "RUN_DATE=%%D"
set "LOG_FILE=%LOG_DIR%\attendance_%RUN_DATE%.log"

echo.>>"%LOG_FILE%"
echo ============================================================>>"%LOG_FILE%"
echo Started: %DATE% %TIME%>>"%LOG_FILE%"

REM Sunday=0, Monday=1, Tuesday=2 ... Saturday=6
for /f %%D in ('powershell.exe -NoProfile -Command "[int](Get-Date).DayOfWeek"') do set "DAY_NUMBER=%%D"

if "!DAY_NUMBER!"=="1" (
    echo Mode: Monday - all employees, option 1, then 7 days>>"%LOG_FILE%"
    (
        echo 1
        echo 1
        echo 7
    ) | "%PYTHON_EXE%" -X utf8 "%SCRIPT_PATH%" --daily >>"%LOG_FILE%" 2>&1

    set "EXIT_CODE=!ERRORLEVEL!"
) else (
    echo Mode: Daily - all employees, option 3, yesterday only>>"%LOG_FILE%"
    (
        echo 1
        echo 3
    ) | "%PYTHON_EXE%" -X utf8 "%SCRIPT_PATH%" --daily >>"%LOG_FILE%" 2>&1

    set "EXIT_CODE=!ERRORLEVEL!"
)

echo Finished: %DATE% %TIME%>>"%LOG_FILE%"
echo Exit code: !EXIT_CODE!>>"%LOG_FILE%"
echo ============================================================>>"%LOG_FILE%"

exit /b !EXIT_CODE!
