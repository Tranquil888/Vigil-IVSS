from vigil.analysis.backend import BackendStatus, probe_backend
from vigil.config.models import FaceConfig


def test_probe_without_models_never_raises(tmp_path):
    status = probe_backend(FaceConfig(detector="dlib_cnn"), tmp_path)
    assert isinstance(status, BackendStatus)
    if status.available:
        assert status.detector == "dlib_hog"
        assert "missing" in status.reason.lower()
    else:
        assert status.detector == "none"


def test_probe_with_explicit_none_detector(tmp_path):
    status = probe_backend(FaceConfig(detector="none"), tmp_path)
    assert status.detector == "none"
    assert status.available is False


def test_backend_status_reports_cuda_honestly(tmp_path):
    status = probe_backend(FaceConfig(detector="dlib_hog"), tmp_path)
    assert isinstance(status.cuda, bool)
