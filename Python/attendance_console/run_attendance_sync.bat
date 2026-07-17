@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Force UTF-8 for Python console output.
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_DIR=D:\PPMC\Projects\misc-script\Python\attendance_console"
set "SCRIPT_PATH=%PROJECT_DIR%\sync_attendance.py"
set "LOG_DIR=C:\logs"
set "LOG_FILE=%LOG_DIR%\attendance_scheduler.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

cd /d "%PROJECT_DIR%" || exit /b 1

echo.>>"%LOG_FILE%"
echo ============================================================>>"%LOG_FILE%"
echo Started: %DATE% %TIME%>>"%LOG_FILE%"

REM Sunday=0, Monday=1, Tuesday=2 ... Saturday=6
for /f %%D in ('powershell.exe -NoProfile -Command "[int](Get-Date).DayOfWeek"') do set "DAY_NUMBER=%%D"

if "!DAY_NUMBER!"=="1" (
    echo Mode: Monday - option 1, then 7 days>>"%LOG_FILE%"
    (
        echo 1
        echo 7
    ) | python -X utf8 "%SCRIPT_PATH%" --daily >>"%LOG_FILE%" 2>&1

    set "EXIT_CODE=!ERRORLEVEL!"
) else (
    echo Mode: Daily - option 3, yesterday only>>"%LOG_FILE%"
    echo 3 | python -X utf8 "%SCRIPT_PATH%" --daily >>"%LOG_FILE%" 2>&1

    set "EXIT_CODE=!ERRORLEVEL!"
)

echo Finished: %DATE% %TIME%>>"%LOG_FILE%"
echo Exit code: !EXIT_CODE!>>"%LOG_FILE%"
echo ============================================================>>"%LOG_FILE%"

exit /b !EXIT_CODE!