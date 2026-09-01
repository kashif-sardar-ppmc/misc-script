param(
    [string]$ProjectDir = "C:\scripts\attendance_console",
    [string]$TaskName = "PPMC Attendance Console Sync"
)

$ErrorActionPreference = "Stop"

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$BatchPath = Join-Path $ProjectDir "run_attendance_sync.bat"
$LogDir = Join-Path $ProjectDir "log"
$InstallLog = Join-Path $LogDir "scheduler_install.log"

if (-not (Test-Path -LiteralPath $BatchPath)) {
    throw "Batch file not found: $BatchPath. Copy the attendance_console folder to $ProjectDir first."
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Installing scheduled task '$TaskName'." | Out-File -FilePath $InstallLog -Append -Encoding utf8

$taskRun = "`"$BatchPath`""
$createArgs = @(
    "/Create",
    "/TN", $TaskName,
    "/TR", $taskRun,
    "/SC", "HOURLY",
    "/MO", "2",
    "/RU", "SYSTEM",
    "/RL", "HIGHEST",
    "/F"
)

& schtasks.exe @createArgs | Tee-Object -FilePath $InstallLog -Append
if ($LASTEXITCODE -ne 0) {
    throw "Task creation failed. See $InstallLog"
}

& schtasks.exe /Query /TN $TaskName /V /FO LIST | Tee-Object -FilePath $InstallLog -Append
if ($LASTEXITCODE -ne 0) {
    throw "Task verification failed. See $InstallLog"
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$task.Settings = $settings
$task.Actions[0].WorkingDirectory = $ProjectDir
$task | Set-ScheduledTask | Out-Null

& schtasks.exe /Query /TN $TaskName /V /FO LIST | Tee-Object -FilePath $InstallLog -Append
if ($LASTEXITCODE -ne 0) {
    throw "Task settings verification failed. See $InstallLog"
}

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Scheduled task installed successfully." | Out-File -FilePath $InstallLog -Append -Encoding utf8
Write-Host "Scheduled task installed: $TaskName"
Write-Host "Runs every 2 hours."
Write-Host "Attendance logs: $LogDir\attendance_yyyy-MM-dd.log"
