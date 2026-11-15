# Packaging

Vigil ships as a PyInstaller one-directory bundle. The executable is
`dist\Vigil\Vigil.exe`; the `_internal` folder next to it must travel with
it. Models are not bundled.

## Build

```powershell
python -m pip install -e ".[dev]"
.\scripts\build_cpu.ps1
```

For a CUDA bundle:

```powershell
.\scripts\build_cuda.ps1
```

Both scripts run `packaging/vigil.spec`. `build_cuda.ps1` calls
`build_cpu.ps1`, then copies `cudnn64_9.dll`, `cudart64_12.dll`, and
`cublasLt64_12.dll` into `dist\Vigil\_internal` when it can find them. A
missing DLL produces a warning, not a failed build.

## Portable zip

```powershell
.\scripts\build_portable.ps1 -Version 2.0 -Force
```

The script wraps the whole `dist\Vigil` folder, not only the executable, in
`dist\Vigil-portable-2.0.zip` and writes a `.sha256` file next to it. The zip
keeps the `Vigil` folder as its root.

## Installer

```powershell
winget install JRSoftware.InnoSetup
.\scripts\build_installer.ps1 -Version 2.0
```

`packaging\vigil.iss` installs the bundle under `{autopf}\Vigil`, adds a Start
menu entry, and offers an optional desktop shortcut. The script searches the
usual Inno Setup locations, fails with instructions when `iscc.exe` is absent,
and never downloads the compiler itself. The output is
`dist\installer\Vigil-2.0-setup.exe` plus a `.sha256` file.

## Release check

```powershell
.\scripts\release_check.ps1 -ModelsDir "$env:LOCALAPPDATA\Vigil\models"
```

The check verifies the executable, the bundle size, the portable zip, the
installer, an isolated offscreen start, a clean stderr, the absence of
`app.unhandled` in the run log, and, when `-ModelsDir` is given, that the
frozen app selected the CNN backend on CUDA.

The spec:

- Builds one directory (`COLLECT`), not a one-file archive.
- Uses `packaging/entry.py` as the script and `src` as the import path.
- Collects `vigil`, `cv2`, `sqlalchemy`, `pydantic`, `tomlkit`, `psutil`, and
  `cryptography`.
- Collects `dlib` only when it imports in the build environment.
- Bundles the checkmark PNGs under `vigil/gui/resources`.
- Bundles the three CUDA DLLs when they are present in `CUDA_PATH`,
  `CUDA_HOME`, the conda prefix, or the NVIDIA pip packages.
- Removes ICU DLLs that come from the conda prefix. A conda `icuuc.dll`
  can shadow the ICU that a newer Qt links, and that collision ends in
  `0xc0000139` before the first window appears. ICU files shipped inside
  PySide6 under their own versioned names are kept.
- Disables the console window (`console=False`).
- Excludes `tkinter`, `legacy`, and `tests`.

## Result on this machine

Recorded on 15 November 2026:

- PyInstaller 6.22.3, PyInstaller hooks 2026.10.
- CPython 3.9.23 from a conda environment with a dlib build for CUDA.
- PySide6-Essentials 6.9.3, OpenCV 4.12.0, dlib 20.0.0 with CUDA.
- Build time: about 70 seconds with `--clean`.
- Bundle size: about 939 MB. dlib, OpenCV, Qt, and the CUDA math libraries
  account for most of it. The portable zip is 541.9 MB and the installer is
  331.9 MB.
- `dist\Vigil\_internal` contains the checkmark PNGs, the dlib package
  directory, `cudart64_110.dll`, `cudnn64_9.dll`, `cublas64_11.dll`, and
  `cublasLt64_11.dll`. The two cublas files alone are about 603 MB, because
  this machine has a CUDA 11 runtime and PyInstaller followed dlib's DLL
  dependencies. There is no `cublasLt64_12.dll`, because CUDA 12 is not
  installed. `build_cuda.ps1` reports that as a warning.
- No ICU DLL is present in the bundle. The spec drops ICU files that come
  from the conda prefix.

The build was smoke tested by starting `Vigil.exe` with
`QT_QPA_PLATFORM=offscreen`, waiting eight seconds, and checking that the
process was still alive. It was. The developer log contained only the
expected warnings for the missing landmark and ResNet models, which means
the window, the Qt plugin load, and the backend probe all worked. No fatal
exception appeared.

That smoke test does not replace a click-through on a real display. Run the
executable on the target machine before distributing it. The portable zip was
also extracted into an empty folder and started with `PATH` reduced to
`%SystemRoot%\System32;%SystemRoot%` and no `PYTHONHOME` or `PYTHONPATH`; it
stayed alive and selected the CNN backend on the GPU.

## Why PySide6 6.9.3 locally

Qt 6.10 links ICU with unversioned symbols on Windows. In this conda
environment, OpenCV loads conda ICU 75 in the same process, and the two
cannot coexist. The first stylesheet call dies with `0xc0000139`. PySide6
6.9.3 has no ICU dependency on Windows and works.

`pyproject.toml` allows `PySide6-Essentials>=6.7`. The release target is
PySide6 6.11 on CPython 3.12, built in a clean environment. If you build with
6.10 or newer, test the stylesheet path before shipping, and keep the
unversioned ICU filter in the spec.

## Distributing

Copy the whole `dist\Vigil` folder. Do not copy only the executable. On first
run the application creates its data directory under `%LOCALAPPDATA%\Vigil`.
Fetch the model files on the target machine or copy an existing `models`
folder and point `face.models_dir` at it.

The bundle is unsigned. Windows SmartScreen may warn on first launch. Sign
the executable if that matters for your deployment.

## Reproducing the build

```powershell
.\scripts\setup_env.ps1 -SkipModels
.\scripts\build_cpu.ps1 -Clean
dist\Vigil\Vigil.exe
```

The `-Clean` switch clears the PyInstaller work directory first. Use it when
you change the spec, the dependencies, or the Python version. Incremental
builds are faster but can keep stale binaries.
