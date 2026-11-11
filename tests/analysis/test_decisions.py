from vigil.analysis.decisions import (
    ObservationVote,
    decide_observation,
    decide_tracklet,
)
from vigil.analysis.gallery import PersonScore
from vigil.config.models import FaceConfig


def scores(*pairs):
    return [PersonScore(person_id=pid, distance=distance) for pid, distance in pairs]


def votes(*triples):
    return [
        ObservationVote(decision=decision, person_id=person, distance=distance, weight=weight)
        for decision, person, distance, weight in triples
    ]


def test_clear_best_match_is_known():
    vote = decide_observation(scores((1, 0.4), (2, 0.9)), FaceConfig())
    assert vote.decision == "known"
    assert vote.person_id == 1


def test_a_thin_margin_is_uncertain():
    vote = decide_observation(scores((1, 0.50), (2, 0.52)), FaceConfig())
    assert vote.decision == "uncertain"


def test_beyond_unknown_threshold_is_unknown():
    vote = decide_observation(scores((1, 0.8)), FaceConfig())
    assert vote.decision == "unknown"


def test_inside_the_band_is_uncertain():
    vote = decide_observation(scores((1, 0.65)), FaceConfig())
    assert vote.decision == "uncertain"


def test_empty_gallery_is_unknown():
    vote = decide_observation([], FaceConfig())
    assert vote.decision == "unknown"
    assert vote.person_id is None


def test_two_agreeing_votes_name_the_person():
    decision = decide_tracklet(
        votes(("known", 1, 0.5, 10.0), ("known", 1, 0.5, 8.0)),
        FaceConfig(min_votes=2),
    )
    assert decision.decision == "known"
    assert decision.person_id == 1
    assert decision.score == 0.5


def test_a_single_vote_cannot_name_a_person():
    decision = decide_tracklet(
        votes(("known", 1, 0.4, 100.0)),
        FaceConfig(min_votes=2, uncertain_policy="review"),
    )
    assert decision.decision == "uncertain"


def test_weighted_mean_and_margin_pick_the_stronger_person():
    decision = decide_tracklet(
        votes(
            ("known", 1, 0.5, 10.0),
            ("known", 1, 0.5, 10.0),
            ("known", 2, 0.6, 1.0),
        ),
        FaceConfig(min_votes=2, margin=0.05),
    )
    assert decision.decision == "known"
    assert decision.person_id == 1


def test_unknown_votes_win_when_there_is_no_candidate():
    decision = decide_tracklet(
        votes(("unknown", None, 0.9, 10.0), ("unknown", None, 0.85, 10.0)),
        FaceConfig(min_votes=2),
    )
    assert decision.decision == "unknown"


def test_uncertain_policy_unknown_is_honoured():
    decision = decide_tracklet(
        votes(("uncertain", None, 0.65, 10.0)),
        FaceConfig(min_votes=2, uncertain_policy="unknown"),
    )
    assert decision.decision == "unknown"


def test_uncertain_policy_ignore_is_honoured():
    decision = decide_tracklet(
        votes(("uncertain", None, 0.65, 10.0)),
        FaceConfig(min_votes=2, uncertain_policy="ignore"),
    )
    assert decision.decision == "ignored"
