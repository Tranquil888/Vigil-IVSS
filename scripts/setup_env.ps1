param(
    [string]$Python = "python",
    [string]$Venv = ".venv",
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Test-Path $Venv)) {
        & $Python -m venv $Venv
    }
    $VenvPython = Join-Path $Root "$Venv\Scripts\python.exe"

    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed"
    }

    if (-not $SkipModels) {
        $Models = Join-Path $env:LOCALAPPDATA "Vigil\models"
        & $VenvPython scripts\fetch_models.py --dest $Models
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Model download failed. Vigil will start in motion-only mode."
        }
    }

    Write-Host ""
    Write-Host "Environment ready in $Root\$Venv"
    Write-Host "Start Vigil with: $VenvPython -m vigil.app"
    Write-Host "Run the tests with: $VenvPython -m pytest -q"
}
finally {
    Pop-Location
}
