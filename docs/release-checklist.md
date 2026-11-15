# Release checklist

The MVP blockers from `docs/plan-gap-analysis.md` and how each one is closed.
Items that need a second machine or physical cameras are marked manual, and the
procedure is written so the result can be recorded without guesswork.

## 1. Camera secrets

Status: closed in software.

A camera URL with a `user:password@host` pair is moved out of the TOML file.
`save_config` encrypts the source into `%LOCALAPPDATA%\Vigil\secrets.json` and
writes `source = "vault"` to the config. On Windows the store uses DPAPI, so the
ciphertext is tied to the Windows account that saved it. Other platforms use
Fernet with `secrets.key` next to the store.

Verify:

```powershell
# 1. Add a camera with rtsp://user:pass@host/stream and save it.
Select-String -Path "$env:APPDATA\Vigil\config.toml" -Pattern "source"
# source = "vault"

# 2. Confirm the password is not in the config or the store text.
Select-String -Path "$env:APPDATA\Vigil\config.toml","$env:LOCALAPPDATA\Vigil\secrets.json" -Pattern "pass"
# no output

# 3. Restart the app. The camera opens with the stored URL.
```

`python -m pytest tests/test_secrets.py -q` covers the round trip, the vault
token, the save path, a missing entry, and a corrupt store.

## 2. CPU build and CUDA bundle

Status: portable and installer scripts are closed in software. The reference-GPU
run is recorded. A pristine Windows VM remains manual.

CPU bundle:

```powershell
.\scripts\build_cpu.ps1 -Clean
.\scripts\release_check.ps1
```

Portable extraction check on this machine: the portable zip was extracted into
an empty directory, `PATH` was reduced to `%SystemRoot%\System32;%SystemRoot%`,
`PYTHONHOME` and `PYTHONPATH` were removed, and `Vigil.exe` was started. It
stayed alive for 12 seconds and logged
`face backend selected: dlib_cnn cuda=True cudnn=True ready on GPU` with no
`app.unhandled` line. This proves the bundle does not need the development
environment. It does not replace a pristine Windows install.

Clean Windows VM: copy `dist\Vigil` or the portable zip to a machine with no
Python, no conda, and no CUDA. Extract it, run `Vigil.exe`, add a camera, and
confirm the window opens, the Diagnostics page reports the backend, and the log
has no `app.unhandled` line. Record the Windows build, the bundle size, and the
backend line here.

CUDA on the RTX 3050:

```powershell
.\scripts\build_cuda.ps1 -Clean
.\scripts\release_check.ps1
```

On the reference machine, start the app, open Diagnostics, and record the
detector name, `DLIB_USE_CUDA`, the device count, and the cuDNN probe result.
The local machine for this pass has an RTX 3050 with 8 GB, driver 610.88, and
dlib 20.0.0 with `DLIB_USE_CUDA = True`.

## 3. Installer and portable zip

Status: closed in software. The portable zip is built here. The installer
script is complete, but Inno Setup is a manual install on the build machine.

Portable:

```powershell
.\scripts\build_portable.ps1 -Version 2.0 -Force
```

The result is `dist\Vigil-portable-2.0.zip` plus a `.sha256` file. It contains
the whole `Vigil` folder, not only the executable.

Installer:

```powershell
# One-time, on the build machine:
winget install JRSoftware.InnoSetup
.\scripts\build_installer.ps1 -Version 2.0
```

The script fails with instructions when `iscc.exe` is absent. It never
downloads the compiler. The result is `dist\installer\Vigil-2.0-setup.exe` plus
a `.sha256` file.

Recorded on 15 November 2026 from commit `5d1850a`:

```text
dist\Vigil-portable-2.0.zip    541.9 MB
sha256  121062C76C53F6D213871AEB8453CEE899910E3373C6B5D7872188B833E01109

dist\installer\Vigil-2.0-setup.exe   331.9 MB
sha256  615FA6D8B0C9133F20C47F065E5A5BB9C3E653994B4E6E9A20B071E64707A6A5
```

`scripts\release_check.ps1 -ModelsDir "$env:LOCALAPPDATA\Vigil\models"` passed
all nine checks against that bundle, including
`face backend selected: dlib_cnn cuda=True cudnn=True ready on GPU`.

## 4. Four 1080p cameras

Status: the software path is measured with four 1080p video files. Four
physical cameras remain manual.

```powershell
python tools/video_latency_probe.py --video-dir data\latency-1080p --cameras 4 --seconds 15 --max-p95 100
```

The probe opens four real capture threads, plays each 1920x1080 file in real
time, consumes inference on a slow thread, and samples only `LatestFrame`.
`tests/e2e/test_latency.py` and `tests/test_latency_invariant.py` guard the same
invariant.

For the physical run, point four `[[cameras]]` entries at the real streams,
start the app, and read the Diagnostics page. The display p95 must stay within
50 ms of the same four cameras with `face.detector = "none"`. Record the
camera models, resolution, frame rate, and both p95 values.

## Remainder

Only these items cannot be closed from this machine:

- Clean Windows VM run.
- Physical four-camera run.
- Inno Setup compile, if the release build machine does not have it.

Everything else in this checklist has a script, a test, or a recorded run.
