"""Build a recognition gallery and test videos from ChokePoint face archives.

    python scripts/build_chokepoint.py --archive test-dataset/P1E.tar

ChokePoint ships 96x96 face crops, not full scene frames. Each crop lives at
``<sequence>_<camera>/<subject>/<frame>.pgm``, where the sequence is something
like ``P1E_S1_C1``: portal 1, entering, session 1, camera 1. Portals 1 and 2
are different subject sets, so the gallery labels subjects ``P1-0001`` and
``P2-0001`` to keep the ids apart. Within one portal the same subject id is
used for entering and leaving sequences, so both conditions share a label.

The gallery is one folder per label with a spread of crops across sequences.
``eval_recognition.py`` can score it directly. Videos merge every subject in a
sequence back into frame order, so one file walks through many identities.
The face is pasted onto a larger canvas with a slow sway, because a 96x96 crop
on its own gives the motion detector almost nothing to see.

Archives may be passed as the tar file or as a folder holding exactly one tar.
Set ``--archive`` more than once to mix portals or conditions.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np

IMAGE_SUFFIXES = {".pgm", ".jpg", ".jpeg", ".png", ".bmp"}


def resolve_archive(path: Path) -> Path:
    """Accept a tar file or the folder the downloader created around it."""
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted(
            child
            for child in path.iterdir()
            if child.is_file()
            and (child.name.endswith(".tar") or child.name.endswith(".tar.xz"))
        )
        if len(candidates) == 1:
            return candidates[0]
        raise ValueError(
            "%s holds %d archives; pass one of them" % (path, len(candidates))
        )
    raise ValueError("archive not found: %s" % path)


def parse_member(name: str) -> Optional[Tuple[str, str, int]]:
    """Return (sequence, subject, frame) for a face crop member, else None."""
    parts = name.split("/")
    if len(parts) != 3:
        return None
    sequence, subject, filename = parts
    if Path(filename).suffix.lower() not in IMAGE_SUFFIXES:
        return None
    stem = Path(filename).stem
    if not stem.isdigit():
        return None
    return sequence, subject, int(stem)


def portal_of(sequence: str) -> str:
    """P1E_S1_C1 -> P1, P2L_S4_C3 -> P2."""
    head = sequence.split("_")[0]
    return head[:2] if len(head) >= 2 else head


def label_of(sequence: str, subject: str) -> str:
    return "%s-%s" % (portal_of(sequence), subject)


def pick_evenly(items: Sequence, limit: int) -> List:
    """Take a deterministic spread instead of the first N items."""
    if limit <= 0 or len(items) <= limit:
        return list(items)
    step = len(items) / float(limit)
    return [items[int(index * step)] for index in range(limit)]


def build_timeline(members: Iterable[Tuple[str, str, int, tarfile.TarInfo]]):
    """Merge subject folders into one frame-ordered list for a sequence.

    Only one subject is in front of a camera at a time, so frame numbers are
    stable keys. Repeated frames keep the first subject seen.
    """
    by_sequence: Dict[str, Dict[int, Tuple[str, tarfile.TarInfo]]] = defaultdict(dict)
    for sequence, subject, frame, member in members:
        by_sequence[sequence].setdefault(frame, (subject, member))
    return {
        sequence: sorted(
            ((frame, subject, member) for frame, (subject, member) in frames.items()),
            key=lambda item: item[0],
        )
        for sequence, frames in by_sequence.items()
    }


def contiguous_blocks(
    frames: Sequence[int], max_gap: int = 2, min_length: int = 8
) -> List[List[int]]:
    """Split frame numbers into runs, dropping sparse or very short runs."""
    blocks: List[List[int]] = []
    current: List[int] = []
    for frame in frames:
        if current and frame - current[-1] > max_gap:
            blocks.append(current)
            current = []
        current.append(frame)
    if current:
        blocks.append(current)
    return [block for block in blocks if len(block) >= min_length]


def compose_frame(
    face: np.ndarray, width: int, height: int, scale: int, index: int
) -> np.ndarray:
    """Paste one crop onto a gray canvas and sway it enough to trip motion."""
    canvas = np.full((height, width, 3), 40, dtype=np.uint8)
    size = int(round(face.shape[1] * scale))
    resized = cv2.resize(face, (size, size), interpolation=cv2.INTER_CUBIC)
    max_x = max(0, width - size)
    max_y = max(0, height - size)
    sway_x = int(round(0.10 * max_x * math.sin(2.0 * math.pi * index / 45.0)))
    sway_y = int(round(0.10 * max_y * math.sin(2.0 * math.pi * index / 70.0)))
    x = max(0, min(max_x, max_x // 2 + sway_x))
    y = max(0, min(max_y, max_y // 2 + sway_y))
    canvas[y : y + size, x : x + size] = resized
    return canvas


def decode(tar: tarfile.TarFile, member: tarfile.TarInfo) -> Optional[np.ndarray]:
    handle = tar.extractfile(member)
    if handle is None:
        return None
    data = handle.read()
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def collect(tar: tarfile.TarFile):
    faces: Dict[str, List[Tuple[str, int, tarfile.TarInfo]]] = defaultdict(list)
    timeline_members: List[Tuple[str, str, int, tarfile.TarInfo]] = []
    for member in tar.getmembers():
        if not member.isfile():
            continue
        parsed = parse_member(member.name)
        if parsed is None:
            continue
        sequence, subject, frame = parsed
        faces[label_of(sequence, subject)].append((sequence, frame, member))
        timeline_members.append((sequence, subject, frame, member))
    for items in faces.values():
        items.sort(key=lambda item: (item[0], item[1]))
    return faces, build_timeline(timeline_members)


def write_faces(
    tar: tarfile.TarFile,
    faces: Dict[str, List[Tuple[str, int, tarfile.TarInfo]]],
    out: Path,
    per_person: int,
    verbose: bool,
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for label in sorted(faces):
        chosen = pick_evenly(faces[label], per_person)
        folder = out / label
        folder.mkdir(parents=True, exist_ok=True)
        saved = 0
        for index, (sequence, frame, member) in enumerate(chosen):
            image = decode(tar, member)
            if image is None:
                continue
            name = "f%03d_%s_%08d.jpg" % (index, sequence, frame)
            path = folder / name
            if not cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError("could not write %s" % path)
            saved += 1
        counts[label] = saved
        if verbose:
            print("  faces %-10s %3d/%3d crops" % (label, saved, len(faces[label])))
    return counts


def write_videos(
    tar: tarfile.TarFile,
    timelines: Dict[str, List[Tuple[int, str, tarfile.TarInfo]]],
    out: Path,
    canvas_width: int,
    canvas_height: int,
    scale: int,
    fps: float,
    max_frames: int,
    max_videos: int,
    minimum_run: int,
    verbose: bool,
) -> List[dict]:
    out.mkdir(parents=True, exist_ok=True)
    written: List[dict] = []
    for sequence in sorted(timelines):
        if max_videos and len(written) >= max_videos:
            break
        timeline = timelines[sequence]
        lookup = {frame: (subject, member) for frame, subject, member in timeline}
        blocks = contiguous_blocks([item[0] for item in timeline], min_length=minimum_run)
        if not blocks:
            if verbose:
                print("  video %-12s skipped: no run of %d frames" % (sequence, minimum_run))
            continue
        frames: List[Tuple[int, str, tarfile.TarInfo]] = []
        for block in blocks:
            frames.extend((frame, *lookup[frame]) for frame in block)
        if max_frames:
            frames = frames[:max_frames]
        path = out / ("%s.mp4" % sequence)
        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (canvas_width, canvas_height),
        )
        if not writer.isOpened():
            raise RuntimeError("OpenCV cannot write %s" % path)
        used = 0
        subjects: Counter = Counter()
        try:
            for index, (frame, subject, member) in enumerate(frames):
                face = decode(tar, member)
                if face is None:
                    continue
                writer.write(
                    compose_frame(face, canvas_width, canvas_height, scale, index)
                )
                subjects[subject] += 1
                used += 1
        finally:
            writer.release()
        if used == 0:
            path.unlink(missing_ok=True)
            continue
        written.append(
            {
                "path": str(path),
                "sequence": sequence,
                "frames": used,
                "fps": fps,
                "seconds": round(used / fps, 2),
                "subjects": sorted(subjects),
            }
        )
        if verbose:
            print(
                "  video %-12s %4d frames %.1fs subjects=%d"
                % (sequence, used, used / fps, len(subjects))
            )
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        action="append",
        default=[],
        help="ChokePoint face tar, or a folder holding one; repeatable",
    )
    parser.add_argument("--faces-out", default="data/chokepoint/faces")
    parser.add_argument("--videos-out", default="data/chokepoint/videos")
    parser.add_argument(
        "--manifest",
        default="",
        help="defaults to <faces-out>-manifest.json beside the gallery",
    )
    parser.add_argument(
        "--faces-per-person",
        type=int,
        default=12,
        help="crops per label, spread across sequences; 0 keeps every crop",
    )
    parser.add_argument("--video-width", type=int, default=640)
    parser.add_argument("--video-height", type=int, default=480)
    parser.add_argument("--video-scale", type=int, default=3)
    parser.add_argument("--video-fps", type=float, default=15.0)
    parser.add_argument("--video-max-frames", type=int, default=900)
    parser.add_argument("--video-max-count", type=int, default=6)
    parser.add_argument("--video-min-run", type=int, default=8)
    parser.add_argument("--no-videos", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    archives = args.archive or ["test-dataset/P1E.tar"]
    resolved = []
    for raw in archives:
        try:
            resolved.append(resolve_archive(Path(raw)))
        except ValueError as err:
            print(str(err), file=sys.stderr)
            return 2

    faces_out = Path(args.faces_out)
    videos_out = Path(args.videos_out)
    manifest_path = (
        Path(args.manifest)
        if args.manifest
        else faces_out.parent / ("%s-manifest.json" % faces_out.name)
    )
    verbose = not args.quiet

    face_counts: Dict[str, int] = {}
    videos: List[dict] = []
    per_archive = []
    for archive in resolved:
        if verbose:
            print("archive %s" % archive)
        try:
            with tarfile.open(str(archive)) as tar:
                faces, timelines = collect(tar)
                if not faces:
                    print("  no face crops in %s" % archive, file=sys.stderr)
                    return 3
                counts = write_faces(tar, faces, faces_out, args.faces_per_person, verbose)
                for label, count in counts.items():
                    face_counts[label] = face_counts.get(label, 0) + count
                if not args.no_videos:
                    videos.extend(
                        write_videos(
                            tar,
                            timelines,
                            videos_out,
                            args.video_width,
                            args.video_height,
                            args.video_scale,
                            args.video_fps,
                            args.video_max_frames,
                            args.video_max_count,
                            args.video_min_run,
                            verbose,
                        )
                    )
                per_archive.append(
                    {
                        "archive": str(archive),
                        "sequences": len(timelines),
                        "labels": len(faces),
                    }
                )
        except (OSError, tarfile.TarError) as err:
            print("cannot read %s: %s" % (archive, err), file=sys.stderr)
            return 3

    manifest = {
        "archives": per_archive,
        "faces_out": str(faces_out),
        "people": face_counts,
        "images": sum(face_counts.values()),
        "videos": videos,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("ChokePoint build")
    print("  people   %d" % len(face_counts))
    print("  images   %d" % sum(face_counts.values()))
    print("  videos   %d" % len(videos))
    print("  gallery  %s" % faces_out)
    print("  manifest %s" % manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
