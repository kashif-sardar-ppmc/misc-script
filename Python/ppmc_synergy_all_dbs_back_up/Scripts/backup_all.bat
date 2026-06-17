@echo off
setlocal

REM ==========================================
REM BACKUP CONFIGURATION - CHANGE HERE ONLY
REM ==========================================
set "PG_HOST=localhost"
set "PG_PORT=5432"
set "PG_USER=postgres"
set "PGPASSWORD=postgres"
set "PGBIN=C:\Program Files\PostgreSQL\16\bin"
set "BACKUP_ROOT=C:\pg_backup"

REM Schedule mode: DAILY, ALTERNATE, WEEKLY
set "SCHEDULE=DAILY"

REM If WEEKLY - set the day: MON TUE WED THU FRI SAT SUN
set "WEEKLY_DAY=SUN"
REM ==========================================

REM Get today's date and day
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "MYDATE=%%i"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format ddd"') do set "TODAY_DAY=%%i"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).Day"') do set "TODAY_NUM=%%i"

REM ==========================================
REM CHECK IF BACKUP SHOULD RUN TODAY
REM ==========================================
set "RUN_BACKUP=NO"

if "%SCHEDULE%"=="DAILY" (
    set "RUN_BACKUP=YES"
)

if "%SCHEDULE%"=="ALTERNATE" (
    set /a "MOD=%TODAY_NUM% %% 2"
    if "%MOD%"=="1" set "RUN_BACKUP=YES"
)

if "%SCHEDULE%"=="WEEKLY" (
    if /i "%TODAY_DAY%"=="%WEEKLY_DAY%" set "RUN_BACKUP=YES"
)

if "%RUN_BACKUP%"=="NO" (
    echo Backup skipped today [%MYDATE%] - Schedule: %SCHEDULE%
    echo Skipped: %MYDATE% - %SCHEDULE% >> "%BACKUP_ROOT%\backup_log.txt"
    goto END
)

REM ==========================================
REM RUN BACKUP
REM ==========================================
set "BACKUP_DIR=%BACKUP_ROOT%\%MYDATE%"
mkdir "%BACKUP_DIR%" 2>nul

echo ==========================================
echo Backup Date : %MYDATE%
echo Schedule    : %SCHEDULE%
echo Server      : %PG_HOST%:%PG_PORT%
echo ==========================================

echo Started: %MYDATE% - %SCHEDULE% >> "%BACKUP_ROOT%\backup_log.txt"

"%PGBIN%\psql.exe" -U %PG_USER% -h %PG_HOST% -p %PG_PORT% -Atc "SELECT datname FROM pg_database WHERE datistemplate = false;" > "%TEMP%\dblist.txt"

for /f "usebackq tokens=1" %%d in ("%TEMP%\dblist.txt") do (
    echo Backing up: %%d
    "%PGBIN%\pg_dump.exe" -U %PG_USER% -h %PG_HOST% -p %PG_PORT% -F c -b -f "%BACKUP_DIR%\%%d.backup" %%d
    if errorlevel 1 (
        echo FAILED: %%d
        echo   FAILED: %%d >> "%BACKUP_ROOT%\backup_log.txt"
    ) else (
        echo OK: %%d
        echo   OK: %%d >> "%BACKUP_ROOT%\backup_log.txt"
    )
)

del "%TEMP%\dblist.txt"
set "PGPASSWORD="

echo ==========================================
echo Backup completed: %BACKUP_DIR%
echo ==========================================
echo Completed: %MYDATE% >> "%BACKUP_ROOT%\backup_log.txt"
echo ---------------------------------------- >> "%BACKUP_ROOT%\backup_log.txt"

:END
pause