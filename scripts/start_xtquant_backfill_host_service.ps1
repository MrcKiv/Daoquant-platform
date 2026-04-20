$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $repoRoot 'runtime'
$venvPython = Join-Path $repoRoot '.venv-xtquant-backfill\Scripts\python.exe'
$outLog = Join-Path $runtimeDir 'xtquant_backfill_host_service.out.log'
$errLog = Join-Path $runtimeDir 'xtquant_backfill_host_service.err.log'

function Test-PythonRuntime {
    param([string]$PythonExe)

    if (!(Test-Path $PythonExe)) {
        return $false
    }

    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process `
            -FilePath $PythonExe `
            -ArgumentList '-c', '"import xtquant, sqlalchemy, pymysql"' `
            -Wait `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $stdoutFile `
            -RedirectStandardError $stderrFile

        return $process.ExitCode -eq 0
    } finally {
        Remove-Item $stdoutFile, $stderrFile -ErrorAction SilentlyContinue
    }
}

if (!(Test-Path $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

if (Test-PythonRuntime $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python runtime was not found. Run scripts\install_xtquant_backfill_host.ps1 first."
    }

    if (!(Test-PythonRuntime $pythonCommand.Source)) {
        throw "No usable Python runtime with xtquant dependencies was found. Install the host worker dependencies first."
    }

    Write-Host "Falling back to the system Python runtime because the isolated virtualenv is not ready."
    $pythonExe = $pythonCommand.Source
}

Set-Location $repoRoot
& $pythonExe -u xtquant_backfill_host_service.py 1>> $outLog 2>> $errLog
