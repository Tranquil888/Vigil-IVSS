param(
    [string]$BundlePath = "dist\Vigil",
    [int]$Seconds = 8,
    [string]$ModelsDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $Root $BundlePath
$exe = Join-Path $bundle "Vigil.exe"
$failures = @()

function Check($name, $ok, $detail) {
    if ($ok) {
        Write-Host "PASS  $name  $detail"
    }
    else {
        Write-Host "FAIL  $name  $detail"
        $script:failures += $name
    }
}

Check "bundle executable" (Test-Path $exe) $exe
if (-not (Test-Path $exe)) {
    Write-Host "Build the bundle first: .\scripts\build_cpu.ps1"
    exit 1
}

$size = [math]::Round((Get-ChildItem $bundle -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Check "bundle size" ($size -gt 100) "$size MB"

$portable = Get-ChildItem (Join-Path $Root "dist") -Filter "Vigil-portable-*.zip" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
Check "portable zip" ($null -ne $portable) $(if ($portable) { $portable.FullName } else { "missing" })

$installer = Get-ChildItem (Join-Path $Root "dist\installer") -Filter "Vigil-*-setup.exe" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
Check "installer" ($null -ne $installer) $(if ($installer) { $installer.FullName } else { "missing (run scripts\build_installer.ps1 on a machine with Inno Setup)" })

# Run in an isolated data directory so the log belongs to this launch only.
$runDir = Join-Path $env:TEMP "vigil-release-check"
Remove-Item $runDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $runDir | Out-Null
$configPath = Join-Path $runDir "config.toml"
if ($ModelsDir) {
    $models = (Resolve-Path $ModelsDir).Path.Replace("\", "\\")
    @"
[app]
theme = "dark"
[face]
detector = "dlib_cnn"
models_dir = "$models"
"@ | Set-Content -Path $configPath -Encoding utf8
}

$env:VIGIL_CONFIG = $configPath
$env:VIGIL_DATA_DIR = $runDir
$env:QT_QPA_PLATFORM = "offscreen"
$out = Join-Path $runDir "stdout.txt"
$err = Join-Path $runDir "stderr.txt"
$process = Start-Process -FilePath $exe -PassThru -RedirectStandardOutput $out `
    -RedirectStandardError $err -WindowStyle Hidden
Start-Sleep -Seconds $Seconds
$alive = -not $process.HasExited
if ($alive) {
    Stop-Process -Id $process.Id -Force
}
Check "bundle starts" $alive "alive after $Seconds s"

$stderr = if (Test-Path $err) { Get-Content $err -Raw } else { "" }
$fatal = $stderr -match "Traceback|ImportError|DLL load failed|0xc0000139"
Check "no fatal startup error" (-not $fatal) $(if ($fatal) { $stderr.Trim() } else { "clean" })

$log = Join-Path $runDir "logs\vigil.log"
Check "run log exists" (Test-Path $log) $log
if (Test-Path $log) {
    $lines = Get-Content $log
    $unhandled = $lines | Select-String -Pattern '"event": "app.unhandled"'
    Check "no unhandled exception in the log" (-not $unhandled) $(if ($unhandled) { "app.unhandled present" } else { "clean" })
    if ($ModelsDir) {
        $backend = $lines | Select-String -Pattern '"event": "face.backend"' | Select-Object -Last 1
        $gpu = $backend -and ($backend.Line -match "ready on GPU")
        Check "CNN backend on CUDA" $gpu $(if ($backend) { $backend.Line } else { "no face.backend line" })
    }
}

Write-Host ""
Write-Host "The clean-VM run and the four physical 1080p cameras remain manual steps."
Write-Host "Use docs\release-checklist.md for the recorded procedure."
if ($failures.Count -gt 0) {
    Write-Host "Failures: $($failures -join ', ')"
    exit 1
}
exit 0
