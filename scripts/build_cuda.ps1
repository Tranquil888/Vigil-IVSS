param(
    [string]$Python = "python",
    [string]$DistPath = "dist",
    [string]$WorkPath = "build",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$CudaDlls = @("cudnn64_9.dll", "cudart64_12.dll", "cublasLt64_12.dll")

$SourceDirs = @()
if ($env:CUDA_PATH) { $SourceDirs += (Join-Path $env:CUDA_PATH "bin") }
if ($env:CUDA_HOME) { $SourceDirs += (Join-Path $env:CUDA_HOME "bin") }
if ($env:CONDA_PREFIX) { $SourceDirs += (Join-Path $env:CONDA_PREFIX "Library\bin") }

& (Join-Path $PSScriptRoot "build_cpu.ps1") `
    -Python $Python -DistPath $DistPath -WorkPath $WorkPath -Clean:$Clean

$Target = Join-Path $Root "$DistPath\Vigil\_internal"
foreach ($Dll in $CudaDlls) {
    $InBundle = Join-Path $Target $Dll
    if (Test-Path $InBundle) {
        Write-Host "CUDA: $Dll already bundled"
        continue
    }
    $Copied = $false
    foreach ($Dir in $SourceDirs) {
        $Candidate = Join-Path $Dir $Dll
        if (Test-Path $Candidate) {
            Copy-Item $Candidate $Target -Force
            Write-Host "CUDA: copied $Dll from $Dir"
            $Copied = $true
            break
        }
    }
    if (-not $Copied) {
        Write-Warning "CUDA: $Dll not found; the bundle will fall back to CPU"
    }
}

Write-Host "CUDA build ready at $Target"
Write-Host "Set inference.device = `"cuda:0`" in config.toml to require GPU inference."
