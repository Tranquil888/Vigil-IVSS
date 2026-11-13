"""Measure face recognition against a folder-per-person image dataset.

    python scripts/eval_recognition.py --dataset data/dataset --models models

Each subfolder of the dataset is one person. Images are detected and embedded
with the configured dlib backend, then scored leave-one-out: the nearest
embedding from another image decides the label. The report includes top-1
accuracy and the genuine and impostor distance distributions, so thresholds can
be calibrated from evidence instead of guesswork.

The script never writes to the database and never imports a person.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

from vigil.analysis.backend import DlibBackend

SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def gather(root: Path, limit: int) -> Dict[str, List[Path]]:
    groups: Dict[str, List[Path]] = {}
    for person_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        images = sorted(
            path
            for path in person_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUFFIXES
        )
        if images:
            groups[person_dir.name] = images[:limit]
    return groups


def embed_dataset(backend, groups, verbose: bool = True):
    labels: List[str] = []
    vectors: List[np.ndarray] = []
    skipped: List[str] = []
    started = time.monotonic()

    for label, paths in groups.items():
        for index, path in enumerate(paths, start=1):
            image = cv2.imread(str(path))
            if image is None:
                skipped.append("%s (unreadable)" % path)
                continue
            try:
                rects = backend.detect(image)
            except Exception as err:
                skipped.append("%s (%s)" % (path, err))
                continue
            if not rects:
                skipped.append("%s (no face)" % path)
                continue
            largest = max(rects, key=lambda rect: int(rect[2]) * int(rect[3]))
            vector = backend.embed(image, largest)
            if vector is None:
                skipped.append("%s (no embedding)" % path)
                continue
            labels.append(label)
            vectors.append(np.asarray(vector, dtype=np.float32).reshape(-1))
            if verbose:
                print(
                    "\r  %-24s %d/%d  embeddings=%d  skipped=%d"
                    % (label, index, len(paths), len(vectors), len(skipped)),
                    end="",
                    flush=True,
                )
    if verbose and vectors:
        print()
    return labels, vectors, skipped, time.monotonic() - started


def evaluate(labels: List[str], vectors: List[np.ndarray]):
    count = len(vectors)
    if count < 2:
        return {
            "top1": 0,
            "top1_correct": 0,
            "top1_total": 0,
            "genuine": [],
            "impostor": [],
        }

    matrix = np.vstack(vectors)
    distances = np.linalg.norm(matrix[:, None, :] - matrix[None, :, :], axis=2)
    np.fill_diagonal(distances, np.inf)

    genuine: List[float] = []
    impostor: List[float] = []
    correct = 0
    for index, label in enumerate(labels):
        nearest = int(np.argmin(distances[index]))
        if labels[nearest] == label:
            correct += 1

        same = [
            distances[index, other]
            for other in range(count)
            if other != index and labels[other] == label
        ]
        different = [
            distances[index, other]
            for other in range(count)
            if labels[other] != label
        ]
        if same:
            genuine.append(float(min(same)))
        if different:
            impostor.append(float(min(different)))

    return {
        "top1": correct / float(count),
        "top1_correct": correct,
        "top1_total": count,
        "genuine": genuine,
        "impostor": impostor,
    }


def summarize(values: List[float]):
    if not values:
        return {"n": 0, "mean": None, "p90": None, "min": None, "max": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "p90": float(np.percentile(array, 90)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def acceptance(values: List[float], threshold: float) -> Optional[str]:
    if not values:
        return None
    accepted = sum(1 for value in values if value <= threshold)
    return "%d/%d (%.1f%%)" % (
        accepted,
        len(values),
        100.0 * accepted / float(len(values)),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/dataset", help="folder with one subfolder per person")
    parser.add_argument("--models", default="models", help="directory with the three dlib model files")
    parser.add_argument(
        "--detector",
        default="dlib_cnn",
        choices=["dlib_cnn", "dlib_hog"],
        help="requested detector; the probe may fall back to HOG",
    )
    parser.add_argument("--max-detect-side", type=int, default=800)
    parser.add_argument("--limit-per-person", type=int, default=8)
    parser.add_argument("--known-threshold", type=float, default=0.6)
    parser.add_argument("--unknown-threshold", type=float, default=0.7)
    parser.add_argument("--require-cnn", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    dataset = Path(args.dataset)
    if not dataset.is_dir():
        print("Dataset directory not found: %s" % dataset, file=sys.stderr)
        return 2

    backend = DlibBackend(
        Path(args.models),
        detector=args.detector,
        max_detect_side=args.max_detect_side,
    )
    status = backend.status
    if not status.available or not backend.can_embed:
        print("Backend cannot embed: %s" % status.reason, file=sys.stderr)
        return 3
    if args.require_cnn and status.detector != "dlib_cnn":
        print(
            "CNN was required but the backend chose %s: %s"
            % (status.detector, status.reason),
            file=sys.stderr,
        )
        return 3

    groups = gather(dataset, int(args.limit_per_person))
    if not groups:
        print("No person folders with images under %s" % dataset, file=sys.stderr)
        return 2

    labels, vectors, skipped, elapsed = embed_dataset(backend, groups)
    result = evaluate(labels, vectors)
    genuine = summarize(result["genuine"])
    impostor = summarize(result["impostor"])
    payload = {
        "backend": {
            "detector": status.detector,
            "cuda": status.cuda,
            "cudnn": status.cudnn,
            "reason": status.reason,
        },
        "dataset": str(dataset.resolve()),
        "people": len(groups),
        "images": sum(len(paths) for paths in groups.values()),
        "embeddings": len(vectors),
        "skipped": len(skipped),
        "skipped_detail": skipped,
        "elapsed_s": round(elapsed, 2),
        "top1": result["top1"],
        "top1_correct": result["top1_correct"],
        "top1_total": result["top1_total"],
        "genuine": genuine,
        "impostor": impostor,
        "known_threshold": args.known_threshold,
        "unknown_threshold": args.unknown_threshold,
        "genuine_at_known": acceptance(result["genuine"], args.known_threshold),
        "impostor_at_known": acceptance(result["impostor"], args.known_threshold),
        "impostor_at_unknown": acceptance(result["impostor"], args.unknown_threshold),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload["top1_total"] else 4

    print("Vigil recognition check")
    print(
        "  backend    detector=%s cuda=%s cudnn=%s"
        % (status.detector, status.cuda, status.cudnn)
    )
    print("  reason     %s" % status.reason)
    print("  dataset    %s" % payload["dataset"])
    print(
        "  data       %d people, %d images, %d embeddings, %d skipped"
        % (
            payload["people"],
            payload["images"],
            payload["embeddings"],
            payload["skipped"],
        )
    )
    if skipped:
        for line in skipped[:10]:
            print("    skip %s" % line)
    print(
        "  top-1      %d/%d (%.1f%%)"
        % (
            result["top1_correct"],
            result["top1_total"],
            100.0 * result["top1"],
        )
    )
    print(
        "  genuine    n=%s mean=%s p90=%s"
        % (genuine["n"], _number(genuine["mean"]), _number(genuine["p90"]))
    )
    print(
        "  impostor   n=%s mean=%s min=%s"
        % (impostor["n"], _number(impostor["mean"]), _number(impostor["min"]))
    )
    print(
        "  known<=%.3f  genuine accept %s, impostor accept %s"
        % (
            args.known_threshold,
            payload["genuine_at_known"],
            payload["impostor_at_known"],
        )
    )
    print(
        "  unknown<=%.3f  impostor accept %s (the rest become strangers)"
        % (args.unknown_threshold, payload["impostor_at_unknown"])
    )
    print("  elapsed    %.2f s" % elapsed)
    return 0 if result["top1_total"] else 4


def _number(value) -> str:
    return "n/a" if value is None else "%.3f" % value


if __name__ == "__main__":
    raise SystemExit(main())
