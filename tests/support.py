import numpy as np

from vigil.analysis.backend import BackendStatus


class FakeBackend:
    status = BackendStatus(True, False, "fake", "test backend")
    can_embed = True

    def __init__(self, vector=None, rects=None):
        self.vector = (
            np.asarray(vector, dtype=np.float32)
            if vector is not None
            else np.array([1.0, 0.0, 0.0], dtype=np.float32)
        )
        self.rects = list(rects) if rects is not None else None
        self.embed_calls = 0
        self.detect_calls = 0

    def detect(self, image):
        self.detect_calls += 1
        return list(self.rects) if self.rects is not None else [(0, 0, 80, 80)]

    def landmarks(self, image, rect):
        return None

    def embed(self, image, rect):
        self.embed_calls += 1
        return self.vector


def unit(vector):
    vector = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(vector))
    return vector if norm == 0 else vector / norm
