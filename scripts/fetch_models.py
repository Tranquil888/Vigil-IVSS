"""Download the three dlib model files Vigil needs.

    python scripts/fetch_models.py --dest models

Nothing is downloaded by the application at run time. Fetch the files once,
point ``face.models_dir`` at them if they do not live in the default models
directory, and Vigil will report a degraded backend until they are present.
"""

from __future__ import annotations

import argparse
import bz2
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, NamedTuple, Optional

CHUNK_SIZE = 1 << 20
USER_AGENT = "Vigil-model-fetch/2.0"


class Model(NamedTuple):
    filename: str
    url: str
    min_bytes: int
    purpose: str


# Decompressed sizes are checked with a floor rather than an equality. The
# upstream files may be regenerated, but they never shrink by half.
MODELS = (
    Model(
        "mmod_human_face_detector.dat",
        "https://dlib.net/files/mmod_human_face_detector.dat.bz2",
        7_000_000,
        "CNN face detector",
    ),
    Model(
        "shape_predictor_68_face_landmarks.dat",
        "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2",
        95_000_000,
        "68 point landmark predictor",
    ),
    Model(
        "dlib_face_recognition_resnet_model_v1.dat",
        "https://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2",
        20_000_000,
        "ResNet face embedding model",
    ),
)


def human_size(count: int) -> str:
    size = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return "%.1f %s" % (size, unit)
        size /= 1024.0
    return "%.1f GB" % size


def existing_files(dest: Path) -> List[Path]:
    return [dest / model.filename for model in MODELS if (dest / model.filename).is_file()]


def download(url: str, target: Path) -> None:
    try:
        _download_urllib(url, target)
    except Exception:
        if not _download_curl(url, target):
            raise


def _download_curl(url: str, target: Path) -> bool:
    """Fallback for Python builds whose TLS stack cannot reach the mirror."""
    curl = shutil.which("curl")
    if not curl:
        return False
    print("  urllib failed, retrying with %s" % curl)
    result = subprocess.run(
        [curl, "-L", "--fail", "--retry", "3", "-o", str(target), url],
        stdout=subprocess.DEVNULL,
    )
    return (
        result.returncode == 0
        and target.is_file()
        and target.stat().st_size > 0
    )


def _download_urllib(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        expected = response.headers.get("Content-Length")
        total = int(expected) if expected and expected.isdigit() else 0
        written = 0
        with target.open("wb") as handle:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                if total:
                    print(
                        "\r  %5.1f%%  %s of %s"
                        % (100.0 * written / total, human_size(written), human_size(total)),
                        end="",
                        flush=True,
                    )
        if total:
            print()
        if written == 0:
            raise OSError("the server returned an empty file")


def extract(archive: Path, target: Path) -> int:
    written = 0
    with bz2.open(archive, "rb") as source, target.open("wb") as handle:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
    return written


def fetch_one(model: Model, dest: Path, keep_archive: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    final_path = dest / model.filename
    archive = dest / (model.filename + ".bz2")

    print("%s (%s)" % (model.filename, model.purpose))
    print("  from %s" % model.url)
    download(model.url, archive)

    handle, partial_name = tempfile.mkstemp(
        prefix=model.filename + ".", suffix=".part", dir=str(dest)
    )
    os.close(handle)
    partial = Path(partial_name)
    try:
        size = extract(archive, partial)
        if size < model.min_bytes:
            raise OSError(
                "%s is %s after extraction, expected at least %s"
                % (model.filename, human_size(size), human_size(model.min_bytes))
            )
        os.replace(str(partial), str(final_path))
    finally:
        if partial.exists():
            partial.unlink()
        if not keep_archive and archive.exists():
            archive.unlink()

    print("  wrote %s (%s)" % (final_path, human_size(final_path.stat().st_size)))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        default="models",
        help="directory that receives the three .dat files (default: models)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite model files that already exist",
    )
    parser.add_argument(
        "--keep-archive",
        action="store_true",
        help="keep the .bz2 downloads next to the extracted files",
    )
    args = parser.parse_args(argv)

    dest = Path(args.dest).expanduser()
    present = existing_files(dest)
    if present and not args.force:
        print("Refusing to overwrite %d existing file(s):" % len(present))
        for path in present:
            print("  %s" % path)
        print("Pass --force to replace them.")
        return 2

    for model in MODELS:
        try:
            fetch_one(model, dest, args.keep_archive)
        except urllib.error.URLError as err:
            print("Download failed for %s: %s" % (model.filename, err), file=sys.stderr)
            return 1
        except OSError as err:
            print("Cannot install %s: %s" % (model.filename, err), file=sys.stderr)
            return 1

    print()
    print("Models are ready in %s" % dest.resolve())
    print("Set face.models_dir in config.toml if this is not the default location.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
