"""Download the datasets used to test face recognition.

    python scripts/fetch_dataset.py --preset faces-52  --dest data
    python scripts/fetch_dataset.py --preset obama-videos --dest data
    python scripts/fetch_dataset.py --preset all --dest data

The files land in a layout the test tools already understand:

- ``data/faces-52/<person>/*.jpg`` for ``scripts/eval_recognition.py``
- ``data/videos/obama/*.mp4`` for a camera whose source lists the files

Nothing is downloaded at run time. Repeat runs skip files whose size already
matches the remote copy, so the fetch is resumable without a database.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, NamedTuple, Optional

CHUNK_SIZE = 1 << 20
USER_AGENT = "Vigil-dataset-fetch/2.0"
API_ROOT = "https://huggingface.co/api/datasets"
FILE_ROOT = "https://huggingface.co/datasets"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
VIDEO_SUFFIXES = (".mp4", ".m4v", ".avi", ".mkv", ".mov", ".webm")


class Preset(NamedTuple):
    name: str
    repo: str
    root: str
    target: str
    strip: str
    suffixes: tuple
    purpose: str


PRESETS = {
    "faces-52": Preset(
        name="faces-52",
        repo="DeviL1337/face_recognition_52",
        root="dataset",
        target="faces-52",
        strip="dataset/",
        suffixes=IMAGE_SUFFIXES,
        purpose="52 people, ten photos each, for threshold calibration",
    ),
    "obama-videos": Preset(
        name="obama-videos",
        repo="masawho/obama-face-videos",
        root="obama",
        target="videos",
        strip="",
        suffixes=VIDEO_SUFFIXES,
        purpose="five short clips, for video recognition and latency runs",
    ),
}


class Remote(NamedTuple):
    path: str
    local: Path
    size: int


def human_size(value: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return "%.1f %s" % (value, unit)
        value /= 1024.0
    return "%.1f GB" % value


def curl_path() -> Optional[str]:
    return shutil.which("curl")


def fetch_json(url: str) -> list:
    curl = curl_path()
    if curl is not None:
        result = subprocess.run(
            [curl, "-sS", "-L", "-A", USER_AGENT, url],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise OSError("curl failed: %s" % (message or result.returncode))
        return json.loads(result.stdout.decode("utf-8"))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def list_tree(preset: Preset) -> List[Remote]:
    url = "%s/%s/tree/main/%s?recursive=true&expand=false" % (
        API_ROOT,
        preset.repo,
        preset.root,
    )
    entries = fetch_json(url)
    remotes = []
    for entry in entries:
        if entry.get("type") != "file":
            continue
        path = entry.get("path") or ""
        if not path.lower().endswith(preset.suffixes):
            continue
        relative = path[len(preset.strip) :] if preset.strip else path
        if not relative:
            continue
        remotes.append(
            Remote(
                path=path,
                local=Path(preset.target) / relative,
                size=int(entry.get("size") or 0),
            )
        )
    return sorted(remotes, key=lambda item: item.path)


def _download_curl(url: str, partial: Path, attempts: int) -> None:
    curl = curl_path()
    result = subprocess.run(
        [
            curl,
            "-fL",
            "--retry",
            str(max(1, attempts)),
            "-A",
            USER_AGENT,
            "-o",
            str(partial),
            url,
        ],
        capture_output=True,
        timeout=1800,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise OSError("curl failed: %s" % (message or result.returncode))


def _download_urllib(url: str, partial: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        expected = response.headers.get("Content-Length")
        total = int(expected) if expected and expected.isdigit() else 0
        written = 0
        with partial.open("wb") as handle:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                if total:
                    print(
                        "\r  %5.1f%%  %s of %s"
                        % (
                            100.0 * written / total,
                            human_size(written),
                            human_size(total),
                        ),
                        end="",
                        flush=True,
                    )
        if total:
            print()
        if written == 0:
            raise OSError("the server returned an empty file")


def download(url: str, target: Path, attempts: int = 3) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    use_curl = curl_path() is not None
    error: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            if use_curl:
                _download_curl(url, partial, attempts)
            else:
                _download_urllib(url, partial)
            if not partial.is_file() or partial.stat().st_size == 0:
                raise OSError("the server returned an empty file")
            os.replace(str(partial), str(target))
            return
        except (urllib.error.URLError, OSError, subprocess.SubprocessError) as err:
            error = err
            if partial.exists():
                partial.unlink()
            if attempt < attempts:
                print("  retry %d/%d after %s" % (attempt + 1, attempts, err))
                time.sleep(attempt)
    raise OSError("download failed: %s" % error)


def sync_preset(
    preset: Preset,
    dest: Path,
    force: bool,
    dry_run: bool,
) -> int:
    print("%s: %s" % (preset.name, preset.purpose))
    print("  from https://huggingface.co/datasets/%s" % preset.repo)
    remotes = list_tree(preset)
    if not remotes:
        print("  no matching files in the repository", file=sys.stderr)
        return 1

    planned = []
    skipped = 0
    total_bytes = 0
    for remote in remotes:
        target = dest / remote.local
        if (
            not force
            and target.is_file()
            and (remote.size <= 0 or target.stat().st_size == remote.size)
        ):
            skipped += 1
            continue
        planned.append((remote, target))
        total_bytes += remote.size

    print(
        "  %d file(s): %d to download (%s), %d already present"
        % (len(remotes), len(planned), human_size(total_bytes), skipped)
    )
    if dry_run:
        for remote, target in planned:
            print("  would fetch %s -> %s" % (remote.path, target))
        return 0

    failures = 0
    for index, (remote, target) in enumerate(planned, start=1):
        url = "%s/%s/resolve/main/%s" % (FILE_ROOT, preset.repo, remote.path)
        print("[%d/%d] %s" % (index, len(planned), remote.path))
        try:
            download(url, target)
        except OSError as err:
            failures += 1
            print("  failed: %s" % err, file=sys.stderr)
            continue
    print(
        "  done: %d downloaded, %d already present, %d failed"
        % (len(planned) - failures, skipped, failures)
    )
    return 1 if failures else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        default="faces-52",
        choices=sorted(PRESETS) + ["all"],
        help="dataset to fetch (default: faces-52)",
    )
    parser.add_argument(
        "--dest",
        default="data",
        help="root directory that receives the files (default: data)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="download again even when a file already matches the remote size",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the planned files without downloading them",
    )
    args = parser.parse_args(argv)

    names = sorted(PRESETS) if args.preset == "all" else [args.preset]
    dest = Path(args.dest).expanduser()
    status = 0
    for name in names:
        if sync_preset(PRESETS[name], dest, args.force, args.dry_run):
            status = 1
        print()
    if not status:
        print("Datasets are ready under %s" % dest.resolve())
    return status


if __name__ == "__main__":
    sys.exit(main())
