param(
    [string]$ProjectDir = "C:\scripts\attendance_console"
)

$ErrorActionPreference = "Stop"

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$LogDir = Join-Path $ProjectDir "log"
$SetupLog = Join-Path $LogDir "remote_setup.log"
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Requirements = Join-Path $ProjectDir "requirements.txt"
$SchedulerInstaller = Join-Path $ProjectDir "install_attendance_scheduler.ps1"

function Write-SetupLog {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    $line | Out-File -FilePath $SetupLog -Append -Encoding utf8
}

if (-not (Test-Path -LiteralPath $ProjectDir)) {
    throw "Project folder not found: $ProjectDir"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Write-SetupLog "Starting remote desktop setup."

$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
$pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue

if (-not $pythonCommand -and -not $pyLauncher) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Python is not installed and winget is not available. Install Python 3 manually, then run this script again."
    }

    Write-SetupLog "Python not found. Installing Python 3.12 with winget."
    & winget.exe install --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Python installation failed. See $SetupLog"
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-SetupLog "Creating virtual environment."
    if ($pyLauncher) {
        & py.exe -3 -m venv (Join-Path $ProjectDir ".venv")
    } else {
        & python.exe -m venv (Join-Path $ProjectDir ".venv")
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed. See $SetupLog"
    }
}

Write-SetupLog "Upgrading pip."
& $VenvPython -m pip install --upgrade pip | Tee-Object -FilePath $SetupLog -Append
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed. See $SetupLog"
}

Write-SetupLog "Installing project requirements."
& $VenvPython -m pip install -r $Requirements | Tee-Object -FilePath $SetupLog -Append
if ($LASTEXITCODE -ne 0) {
    throw "Requirement installation failed. See $SetupLog"
}

Write-SetupLog "Installing scheduled task."
& powershell.exe -ExecutionPolicy Bypass -File $SchedulerInstaller -ProjectDir $ProjectDir | Tee-Object -FilePath $SetupLog -Append
if ($LASTEXITCODE -ne 0) {
    throw "Scheduled task installation failed. See $SetupLog"
}

Write-SetupLog "Remote desktop setup completed successfully."
Write-Host "Setup completed."
Write-Host "Scheduler logs: $LogDir\attendance_yyyy-MM-dd.log"
Write-Host "Setup logs: $SetupLog"
