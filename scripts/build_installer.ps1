param(
    [string]$Version = "2.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $Root "dist\Vigil\Vigil.exe"
if (-not (Test-Path $bundle)) {
    throw "No bundle at $bundle. Build it first: .\scripts\build_cpu.ps1"
}

$candidates = @()
$command = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($command) {
    $candidates += $command.Source
}
foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
    if ($base) {
        $candidates += (Join-Path $base "Inno Setup 6\ISCC.exe")
    }
}
if ($env:LOCALAPPDATA) {
    $candidates += (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
}
$iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) {
    throw @"
Inno Setup 6 is not installed. Install it from https://jrsoftware.org/isdl.php
(or use winget install JRSoftware.InnoSetup), then run this script again.
The repository does not download the compiler because the network budget is
limited and the tool is a manual, one-time step.
"@
}

Push-Location $Root
try {
    & $iscc "/Qp" "/DMyAppVersion=$Version" "packaging\vigil.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "ISCC failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$installer = Join-Path $Root "dist\installer\Vigil-$Version-setup.exe"
if (-not (Test-Path $installer)) {
    throw "ISCC reported success but $installer is missing"
}
$hash = (Get-FileHash -Path $installer -Algorithm SHA256).Hash
$name = Split-Path -Leaf $installer
Set-Content -Path "$installer.sha256" -Value "$hash  $name" -Encoding ascii
$size = [math]::Round((Get-Item $installer).Length / 1MB, 1)
Write-Host "Installer: $installer ($size MB)"
Write-Host "SHA256: $hash"
