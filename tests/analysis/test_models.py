"""Optional checks that need the downloaded dlib model files.

Run them with:

    dlib-env\\Scripts\\python.exe -m pytest tests/analysis/test_models.py -q -m models

The directory can be overridden with ``VIGIL_MODELS_DIR``.
"""

import os
from pathlib import Path

import pytest

from vigil.analysis.backend import CNN_MODEL, DlibBackend

MODELS = Path(os.environ.get("VIGIL_MODELS_DIR", "models")).resolve()
HAS_MODELS = (MODELS / CNN_MODEL).is_file()

pytestmark = [
    pytest.mark.models,
    pytest.mark.skipif(
        not HAS_MODELS, reason="dlib models are not downloaded in %s" % MODELS
    ),
]


def test_cnn_detector_and_resnet_models_load():
    backend = DlibBackend(MODELS, detector="dlib_cnn")

    assert backend.status.available is True
    assert backend.can_embed is True
    if not backend.status.cuda:
        pytest.skip("this machine has no CUDA, so the probe chose HOG")
    if not backend.status.cudnn:
        pytest.skip("this machine has CUDA but no cuDNN, so the probe chose HOG")
    assert backend.status.detector == "dlib_cnn"

    rect = backend.detect(_face_like_image())
    assert isinstance(rect, list)


def _face_like_image():
    """A blank frame is enough to exercise the CNN graph without a subject."""
    import numpy as np

    return np.zeros((64, 64, 3), dtype=np.uint8)
