$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$venvDir = Join-Path $repoRoot '.venv-xtquant-backfill'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirementsFile = Join-Path $repoRoot 'requirements-xtquant-host.txt'

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Args,
        [string]$FailureMessage
    )

    & $Exe @Args
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

$pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue

if ($pyLauncher) {
    $bootstrapExe = $pyLauncher.Source
    $bootstrapArgs = @('-3.11')
} elseif ($pythonCommand) {
    $bootstrapExe = $pythonCommand.Source
    $bootstrapArgs = @()
} else {
    throw "Python 3.11 was not found. Please install Python 3.11 and run this script again."
}

if (!(Test-Path $venvDir)) {
    Write-Host "Creating isolated xtquant backfill virtualenv: $venvDir"
    Invoke-Checked $bootstrapExe ($bootstrapArgs + @('-m', 'venv', $venvDir)) "Virtualenv creation failed."
}

if (!(Test-Path $venvPython)) {
    throw "Virtualenv creation failed. Missing: $venvPython"
}

& $venvPython -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "pip is not available inside $venvDir. Use a standard Python 3.11 build or run the host service with a preconfigured Python environment."
}

Write-Host "Upgrading pip..."
Invoke-Checked $venvPython @('-m', 'pip', 'install', '--upgrade', 'pip') "pip upgrade failed."

Write-Host "Installing xtquant backfill dependencies..."
Invoke-Checked $venvPython @('-m', 'pip', 'install', '-r', $requirementsFile) "Dependency installation failed."

Write-Host ""
Write-Host "Install complete."
Write-Host "Start command: powershell -ExecutionPolicy Bypass -File scripts\start_xtquant_backfill_host_service.ps1"
