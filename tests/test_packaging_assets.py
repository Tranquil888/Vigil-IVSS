"""Packaging assets: model fetch, spec, and build scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODEL_URLS = (
    "https://dlib.net/files/mmod_human_face_detector.dat.bz2",
    "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2",
    "https://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2",
)
CUDA_DLLS = ("cudnn64_9.dll", "cudart64_12.dll", "cublasLt64_12.dll")


def test_fetch_models_lists_the_three_canonical_urls():
    text = (ROOT / "scripts" / "fetch_models.py").read_text(encoding="utf-8")

    for url in MODEL_URLS:
        assert url in text


def test_fetch_models_refuses_to_overwrite_without_force(tmp_path):
    existing = tmp_path / "shape_predictor_68_face_landmarks.dat"
    existing.write_bytes(b"keep me")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "fetch_models.py"),
            "--dest",
            str(tmp_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0
    assert "--force" in (result.stdout + result.stderr)
    assert existing.read_bytes() == b"keep me"


def test_spec_builds_a_onedir_bundle():
    text = (ROOT / "packaging" / "vigil.spec").read_text(encoding="utf-8")

    assert "COLLECT(" in text
    assert "entry.py" in text
    assert "dlib" in text


def test_spec_and_cuda_script_list_the_cuda_dlls():
    spec = (ROOT / "packaging" / "vigil.spec").read_text(encoding="utf-8")
    script = (ROOT / "scripts" / "build_cuda.ps1").read_text(encoding="utf-8")

    for dll in CUDA_DLLS:
        assert dll in spec
        assert dll in script


def test_app_entry_enables_frozen_multiprocessing():
    text = (ROOT / "src" / "vigil" / "app.py").read_text(encoding="utf-8")

    assert "multiprocessing.freeze_support()" in text


def test_build_scripts_exist():
    for name in ("build_cpu.ps1", "build_cuda.ps1", "setup_env.ps1"):
        assert (ROOT / "scripts" / name).is_file()
