import numpy as np

from vigil.analysis.quality import assess_quality
from vigil.config.models import FaceConfig


def test_flat_crop_is_rejected_by_blur():
    image = np.full((120, 120, 3), 128, dtype=np.uint8)
    quality = assess_quality(image, (20, 20, 80, 80), FaceConfig())
    assert quality.blur < 5
    assert quality.score < 0.1


def test_sharp_textured_crop_scores_higher_than_flat():
    flat = np.full((120, 120, 3), 128, dtype=np.uint8)
    checker = np.indices((120, 120)).sum(axis=0) % 2 * 255
    checker = np.repeat(checker[:, :, None], 3, axis=2).astype(np.uint8)

    flat_quality = assess_quality(flat, (20, 20, 80, 80), FaceConfig())
    sharp_quality = assess_quality(checker, (20, 20, 80, 80), FaceConfig())
    assert sharp_quality.score > flat_quality.score


def test_face_px_is_the_smaller_side_of_the_rect():
    image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    quality = assess_quality(image, (10, 10, 40, 100), FaceConfig())
    assert quality.face_px == 40


def test_small_faces_score_lower_than_large_faces():
    checker = np.indices((400, 400)).sum(axis=0) % 2 * 255
    checker = np.repeat(checker[:, :, None], 3, axis=2).astype(np.uint8)

    small = assess_quality(checker, (0, 0, 50, 50), FaceConfig())
    large = assess_quality(checker, (0, 0, 200, 200), FaceConfig())
    assert large.score > small.score
