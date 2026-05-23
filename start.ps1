# LOL AI System - one-click start
# Usage: .\start.ps1   or double-click start.bat

param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
$Url = "http://127.0.0.1:5000"

function Find-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $py = @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    foreach ($p in $py) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    Write-Error "Python not found. Install from https://www.python.org/downloads/"
    exit 1
}

if (-not (Test-Path $VenvPython)) {
    Write-Host ">>> Creating virtual environment ..."
    & $Python -m venv (Join-Path $RepoRoot "venv")
}

Write-Host ">>> Installing dependencies (if needed) ..."
& $VenvPython -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $NoBrowser) {
    Write-Host ">>> Opening browser: $Url"
    Start-Process $Url
}

Write-Host ">>> Starting Flask server (Ctrl+C to stop)"
Write-Host ">>> $Url"
& $VenvPython run.py
