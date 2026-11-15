param(
    [string]$DistPath = "dist",
    [string]$Bundle = "Vigil",
    [string]$Version = "2.0",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $Root (Join-Path $DistPath $Bundle)
$exe = Join-Path $source "Vigil.exe"
if (-not (Test-Path $exe)) {
    throw "No bundle at $source. Build it first: .\scripts\build_cpu.ps1"
}

$outputDir = Join-Path $Root $DistPath
$target = Join-Path $outputDir ("Vigil-portable-$Version.zip")
if (Test-Path $target) {
    if (-not $Force) {
        throw "$target exists. Pass -Force to replace it."
    }
    Remove-Item $target -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
Write-Host "Compressing $source"
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $source,
    $target,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)

$hash = (Get-FileHash -Path $target -Algorithm SHA256).Hash
$name = Split-Path -Leaf $target
Set-Content -Path "$target.sha256" -Value "$hash  $name" -Encoding ascii

$size = [math]::Round((Get-Item $target).Length / 1MB, 1)
Write-Host "Portable bundle: $target ($size MB)"
Write-Host "SHA256: $hash"
