import numpy as np

from vigil.analysis.gallery import Gallery


def unit(vector):
    vector = np.asarray(vector, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def test_min_score_uses_the_closest_image_of_a_person():
    gallery = Gallery()
    gallery.add(1, unit([1.0, 0.0, 0.0]))
    gallery.add(1, unit([0.0, 1.0, 0.0]))
    gallery.add(2, unit([0.0, 0.0, 1.0]))

    scores = gallery.score(unit([0.9, 0.1, 0.0]), mode="min")
    assert scores[0].person_id == 1
    assert scores[0].distance < scores[1].distance


def test_top3_mean_is_more_forgiving_than_min():
    gallery = Gallery()
    gallery.add_person(1, np.vstack([unit([1, 0, 0]), unit([0, 1, 0]), unit([0, 0, 1])]))
    query = unit([0.6, 0.6, 0.0])

    minimum = gallery.score(query, mode="min")[0].distance
    average = gallery.score(query, mode="top3_mean")[0].distance
    assert average >= minimum


def test_remove_person_drops_the_gallery_entries():
    gallery = Gallery()
    gallery.add(1, unit([1, 0, 0]))
    gallery.remove_person(1)
    assert gallery.score(unit([1, 0, 0])) == []


def test_empty_gallery_scores_nothing():
    assert Gallery().score(unit([1, 0, 0])) == []


def test_scores_are_sorted_by_distance():
    gallery = Gallery()
    gallery.add(1, unit([1, 0, 0]))
    gallery.add(2, unit([0, 1, 0]))
    scores = gallery.score(unit([0.9, 0.1, 0]))
    assert [score.person_id for score in scores] == [1, 2]


def test_replace_swaps_the_whole_gallery_in_one_step():
    gallery = Gallery({1: np.atleast_2d(unit([1, 0, 0]))})
    gallery.replace({2: np.atleast_2d(unit([0, 1, 0]))})

    assert gallery.person_ids() == [2]
    assert gallery.score(unit([1, 0, 0]))[0].person_id == 2


def test_replace_with_an_empty_gallery_leaves_nothing_to_score():
    gallery = Gallery({1: np.atleast_2d(unit([1, 0, 0]))})
    gallery.replace({})
    assert gallery.score(unit([1, 0, 0])) == []
