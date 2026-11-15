# -*- mode: python ; coding: utf-8 -*-
"""One-directory PyInstaller bundle for Vigil.

The bundle is a GUI application with no console window. Models are not
bundled: they are downloaded by scripts/fetch_models.py and live in the data
directory. Browse the frozen output under dist/Vigil.
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"

datas = []
binaries = []
hiddenimports = []


def collect(package):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_hidden)


# PySide6 brings its own hook and a huge module set. Only the runtime support
# packages and the pure Python dependencies are collected explicitly.
for name in (
    "vigil",
    "cv2",
    "sqlalchemy",
    "pydantic",
    "tomlkit",
    "psutil",
    "cryptography",
):
    collect(name)

hiddenimports.extend(collect_submodules("sqlalchemy.dialects.sqlite"))

# The checkmark assets are loaded by theme.py at run time, not imported.
RESOURCES = SRC / "vigil" / "gui" / "resources"
if RESOURCES.is_dir():
    datas.append((str(RESOURCES), "vigil/gui/resources"))

# dlib is optional. A CPU build without dlib still runs in motion-only mode.
try:
    import dlib  # noqa: F401
except ImportError:
    pass
else:
    collect("dlib")

CUDA_DLLS = ("cudnn64_9.dll", "cudart64_12.dll", "cublasLt64_12.dll")


def cuda_dirs():
    dirs = []
    for variable in ("CUDA_PATH", "CUDA_HOME"):
        value = os.environ.get(variable)
        if value:
            dirs.append(Path(value) / "bin")
    prefix = Path(sys.prefix)
    dirs.append(prefix / "Library" / "bin")
    dirs.append(prefix / "bin")
    site = prefix / "Lib" / "site-packages"
    for pattern in ("nvidia/cudnn/bin", "nvidia/cuda_runtime/bin", "nvidia/cublas/bin"):
        dirs.extend(site.glob(pattern))
    return dirs


# CUDA runtime libraries travel with the bundle when they are on this machine.
# The model still selects CPU when CUDA is unavailable at run time.
for dll_name in CUDA_DLLS:
    for directory in cuda_dirs():
        candidate = directory / dll_name
        if candidate.is_file():
            binaries.append((str(candidate), "."))
            break


def is_conda_icu(entry):
    """Drop ICU DLLs copied from the conda prefix.

    Conda's unversioned icuuc.dll can shadow the ICU a newer Qt links, and
    the matching icudt data file is tens of megabytes the app does not need
    when Qt 6.9 has no ICU dependency. ICU files shipped inside PySide6 stay
    under their own versioned names.
    """
    source = Path(entry[1])
    conda_bin = (Path(sys.prefix) / "Library" / "bin").resolve()
    try:
        in_conda = source.resolve().parent == conda_bin
    except OSError:
        in_conda = False
    return in_conda and source.name.lower().startswith("icu")


a = Analysis(
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "legacy", "tests"],
    noarchive=False,
)

a.binaries = [entry for entry in a.binaries if not is_conda_icu(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Vigil",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Vigil",
)
