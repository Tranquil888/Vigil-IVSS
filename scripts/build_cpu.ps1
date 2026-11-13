param(
    [string]$Python = "python",
    [string]$DistPath = "dist",
    [string]$WorkPath = "build",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    & $Python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed. Run: $Python -m pip install -e `".[dev]`""
    }

    $pyArgs = @(
        "-m", "PyInstaller",
        "packaging/vigil.spec",
        "--noconfirm",
        "--distpath", $DistPath,
        "--workpath", $WorkPath
    )
    if ($Clean) {
        $pyArgs += "--clean"
    }

    & $Python @pyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }

    Write-Host "Built $Root\$DistPath\Vigil"
}
finally {
    Pop-Location
}
