import importlib.util
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eval_recognition.py"


def load_script():
    spec = importlib.util.spec_from_file_location("eval_recognition", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluation = load_script()


def test_acceptance_and_rejection_report_both_sides():
    values = [0.1, 0.2, 0.3, 0.4]
    assert evaluation.acceptance(values, 0.2) == "2/4 (50.0%)"
    assert evaluation.rejection(values, 0.3) == "2/4 (50.0%)"
    assert evaluation.acceptance([], 0.2) is None
    assert evaluation.rejection([], 0.2) is None


def test_calibration_separates_clean_distributions():
    result = evaluation.calibrate([0.1, 0.2, 0.3], [0.5, 0.6, 0.7])
    assert result["eer"] == 0.0
    assert result["youden_threshold"] == 0.3
    assert result["suggested_known"] == 0.3
    assert result["suggested_unknown"] > result["suggested_known"]


def test_calibration_reports_overlap_and_keeps_a_band():
    result = evaluation.calibrate([0.2, 0.3, 0.4, 0.5], [0.25, 0.35, 0.45, 0.55])
    assert result["eer"] > 0
    assert result["suggested_unknown"] > result["suggested_known"]
    assert result["youden_genuine_accept"] >= result["youden_impostor_accept"]
    assert result["sweep"]
    assert all(0.2 <= row["threshold"] <= 0.6 for row in result["sweep"])


def test_evaluate_scores_min_and_top3_mean():
    labels = ["A", "A", "A", "B", "B", "B"]
    vectors = [
        np.array([0.0, 0.0]),
        np.array([1.0, 0.0]),
        np.array([2.0, 0.0]),
        np.array([10.0, 0.0]),
        np.array([11.0, 0.0]),
        np.array([12.0, 0.0]),
    ]
    smallest = evaluation.evaluate(labels, vectors, "min")
    averaged = evaluation.evaluate(labels, vectors, "top3_mean")
    assert smallest["top1_correct"] == 6
    assert averaged["top1_correct"] == 6
    assert smallest["genuine"][0] == 1.0
    assert averaged["genuine"][0] == 1.5
    assert len(smallest["genuine"]) == 6


def test_evaluate_skips_genuine_when_a_person_has_one_image():
    result = evaluation.evaluate(
        ["only", "A", "A"],
        [np.array([0.0, 0.0]), np.array([1.0, 0.0]), np.array([2.0, 0.0])],
        "min",
    )
    assert len(result["genuine"]) == 2
    assert len(result["impostor"]) == 3


def test_calibration_needs_both_distributions():
    assert evaluation.calibrate([], [0.5]) is None
    assert evaluation.calibrate([0.2], []) is None
