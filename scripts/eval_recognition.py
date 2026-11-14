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


def embed_dataset(backend, groups, verbose: bool = True, stream=None):
    labels: List[str] = []
    vectors: List[np.ndarray] = []
    skipped: List[str] = []
    started = time.monotonic()
    output = stream if stream is not None else sys.stdout

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
                    file=output,
                    flush=True,
                )
    if verbose and vectors:
        print(file=output)
    return labels, vectors, skipped, time.monotonic() - started


def evaluate(labels: List[str], vectors: List[np.ndarray], mode: str = "min"):
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
        per_person = {}
        for other_label in set(labels):
            row = sorted(
                distances[index, other]
                for other in range(count)
                if labels[other] == other_label and other != index
            )
            if not row:
                continue
            if mode == "top3_mean":
                per_person[other_label] = float(np.mean(row[:3]))
            else:
                per_person[other_label] = float(row[0])

        winner = min(per_person, key=per_person.get)
        if winner == label:
            correct += 1

        same = per_person.get(label)
        if same is not None and same != float("inf"):
            genuine.append(float(same))
        different = [
            value for other_label, value in per_person.items() if other_label != label
        ]
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


def rejection(values: List[float], threshold: float) -> Optional[str]:
    """Share of values at or beyond the unknown threshold."""
    if not values:
        return None
    rejected = sum(1 for value in values if value >= threshold)
    return "%d/%d (%.1f%%)" % (
        rejected,
        len(values),
        100.0 * rejected / float(len(values)),
    )


def calibrate(
    genuine: List[float],
    impostor: List[float],
    target_genuine: float = 0.97,
) -> Optional[dict]:
    """Pick thresholds from measured distances instead of copying a default.

    ``known`` is the Youden point: the threshold with the best genuine accept
    rate minus impostor accept rate. ``unknown`` covers ``target_genuine`` of
    genuine pairs, so anything farther away is a stranger. The uncertain band
    sits between the two and is the part a reviewer should see.
    """
    if not genuine or not impostor:
        return None
    candidates = sorted({round(float(value), 4) for value in genuine + impostor})
    rows = []
    for threshold in candidates:
        genuine_accept = sum(1 for value in genuine if value <= threshold) / float(
            len(genuine)
        )
        impostor_accept = sum(1 for value in impostor if value <= threshold) / float(
            len(impostor)
        )
        rows.append((threshold, genuine_accept, impostor_accept))

    youden = max(rows, key=lambda row: row[1] - row[2])
    eer_row = min(rows, key=lambda row: abs(row[1] - (1.0 - row[2])))
    cover = [row for row in rows if row[1] >= target_genuine]
    unknown_row = cover[0] if cover else rows[-1]

    known = round(youden[0], 2)
    unknown = round(unknown_row[0], 2)
    if unknown <= known:
        unknown = round(known + 0.05, 2)

    sweep = []
    for step in range(20, 61, 2):
        threshold = step / 100.0
        sweep.append(
            {
                "threshold": threshold,
                "genuine_accept": round(
                    sum(1 for value in genuine if value <= threshold)
                    / float(len(genuine)),
                    4,
                ),
                "impostor_accept": round(
                    sum(1 for value in impostor if value <= threshold)
                    / float(len(impostor)),
                    4,
                ),
            }
        )
    return {
        "eer": round(((1.0 - eer_row[1]) + eer_row[2]) / 2.0, 4),
        "eer_threshold": round(eer_row[0], 2),
        "eer_genuine_accept": round(eer_row[1], 4),
        "eer_impostor_accept": round(eer_row[2], 4),
        "youden_threshold": round(youden[0], 2),
        "youden_genuine_accept": round(youden[1], 4),
        "youden_impostor_accept": round(youden[2], 4),
        "suggested_known": known,
        "suggested_unknown": unknown,
        "target_genuine": target_genuine,
        "sweep": sweep,
    }


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
    parser.add_argument(
        "--gallery-score",
        default="min",
        choices=["min", "top3_mean"],
        help="match face.gallery_score",
    )
    parser.add_argument("--known-threshold", type=float, default=0.6)
    parser.add_argument("--unknown-threshold", type=float, default=0.7)
    parser.add_argument(
        "--target-genuine",
        type=float,
        default=0.97,
        help="share of genuine pairs the suggested unknown threshold must cover",
    )
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

    labels, vectors, skipped, elapsed = embed_dataset(
        backend, groups, stream=sys.stderr if args.json else None
    )
    result = evaluate(labels, vectors, args.gallery_score)
    genuine = summarize(result["genuine"])
    impostor = summarize(result["impostor"])
    calibration = calibrate(
        result["genuine"], result["impostor"], args.target_genuine
    )
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
        "gallery_score": args.gallery_score,
        "top1": result["top1"],
        "top1_correct": result["top1_correct"],
        "top1_total": result["top1_total"],
        "genuine": genuine,
        "impostor": impostor,
        "known_threshold": args.known_threshold,
        "unknown_threshold": args.unknown_threshold,
        "genuine_at_known": acceptance(result["genuine"], args.known_threshold),
        "impostor_at_known": acceptance(result["impostor"], args.known_threshold),
        "genuine_at_unknown": acceptance(result["genuine"], args.unknown_threshold),
        "impostor_at_unknown": acceptance(result["impostor"], args.unknown_threshold),
        "impostor_rejected_at_unknown": rejection(
            result["impostor"], args.unknown_threshold
        ),
        "calibration": calibration,
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
    print("  scoring    %s" % payload["gallery_score"])
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
        "  unknown>=%.3f  impostors rejected %s, genuine kept %s"
        % (
            args.unknown_threshold,
            payload["impostor_rejected_at_unknown"],
            payload["genuine_at_unknown"],
        )
    )
    if calibration:
        print(
            "  EER        %.1f%% at %.2f (genuine accept %.1f%%, impostor accept %.1f%%)"
            % (
                100.0 * calibration["eer"],
                calibration["eer_threshold"],
                100.0 * calibration["eer_genuine_accept"],
                100.0 * calibration["eer_impostor_accept"],
            )
        )
        print(
            "  suggested  known=%.2f (genuine %.1f%%, impostor %.1f%%)"
            % (
                calibration["suggested_known"],
                100.0 * calibration["youden_genuine_accept"],
                100.0 * calibration["youden_impostor_accept"],
            )
        )
        print(
            "             unknown=%.2f covers %.1f%% of genuine pairs"
            % (calibration["suggested_unknown"], 100.0 * calibration["target_genuine"])
        )
    print("  elapsed    %.2f s" % elapsed)
    return 0 if result["top1_total"] else 4


def _number(value) -> str:
    return "n/a" if value is None else "%.3f" % value


if __name__ == "__main__":
    raise SystemExit(main())
