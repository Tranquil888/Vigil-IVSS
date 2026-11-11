import numpy as np

from vigil.analysis.unknowns import StrangerGrouper


def unit(vector):
    vector = np.asarray(vector, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def test_similar_visits_join_one_cluster():
    grouper = StrangerGrouper(window_s=60, threshold=0.6)
    first = grouper.assign("front", unit([1, 0, 0]), now=100.0)
    second = grouper.assign("front", unit([0.99, 0.01, 0]), now=130.0)
    assert first.id == second.id
    assert second.n_visits == 2


def test_different_faces_get_different_clusters():
    grouper = StrangerGrouper(window_s=60, threshold=0.6)
    first = grouper.assign("front", unit([1, 0, 0]), now=100.0)
    second = grouper.assign("front", unit([0, 1, 0]), now=110.0)
    assert first.id != second.id


def test_after_the_window_a_new_cluster_starts():
    grouper = StrangerGrouper(window_s=60, threshold=0.6)
    first = grouper.assign("front", unit([1, 0, 0]), now=100.0)
    second = grouper.assign("front", unit([1, 0, 0]), now=200.0)
    assert first.id != second.id


def test_clusters_do_not_cross_cameras():
    grouper = StrangerGrouper(window_s=60, threshold=0.6)
    first = grouper.assign("front", unit([1, 0, 0]), now=100.0)
    second = grouper.assign("back", unit([1, 0, 0]), now=101.0)
    assert first.id != second.id


def test_new_cluster_is_flagged_as_new():
    grouper = StrangerGrouper(window_s=60, threshold=0.6)
    assert grouper.assign("front", unit([1, 0, 0]), now=1.0).is_new is True
    assert grouper.assign("front", unit([1, 0, 0]), now=2.0).is_new is False
