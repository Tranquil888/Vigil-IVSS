"""Observation and tracklet decisions. Never decides from one frame."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..config.models import FaceConfig
from ..core.records import Decision
from .gallery import PersonScore


@dataclass
class ObservationVote:
    decision: str
    person_id: Optional[int]
    distance: Optional[float]
    weight: float = 1.0


@dataclass
class TrackletDecision:
    decision: str
    person_id: Optional[int] = None
    score: Optional[float] = None


def decide_observation(
    scores: List[PersonScore], config: FaceConfig
) -> ObservationVote:
    if not scores:
        return ObservationVote(Decision.UNKNOWN, None, None)
    best = scores[0]
    runner_up = scores[1] if len(scores) > 1 else None

    if best.distance <= config.known_threshold:
        clear_margin = (
            runner_up is None
            or runner_up.distance - best.distance >= config.margin
        )
        if clear_margin:
            return ObservationVote(Decision.KNOWN, best.person_id, best.distance)
        return ObservationVote(Decision.UNCERTAIN, None, best.distance)

    if best.distance >= config.unknown_threshold:
        return ObservationVote(Decision.UNKNOWN, None, best.distance)

    return ObservationVote(Decision.UNCERTAIN, None, best.distance)


def _policy(config: FaceConfig) -> str:
    return {
        "review": Decision.UNCERTAIN,
        "unknown": Decision.UNKNOWN,
        "ignore": Decision.IGNORED,
    }.get(config.uncertain_policy, Decision.UNCERTAIN)


def decide_tracklet(
    votes: List[ObservationVote], config: FaceConfig
) -> TrackletDecision:
    per_person: Dict[int, Dict[str, float]] = {}
    unknown_weight = 0.0
    uncertain_weight = 0.0

    for vote in votes:
        weight = max(0.0, float(vote.weight))
        if vote.decision == Decision.KNOWN and vote.person_id is not None:
            entry = per_person.setdefault(
                vote.person_id, {"count": 0.0, "weight": 0.0, "distance": 0.0}
            )
            entry["count"] += 1
            entry["weight"] += weight
            entry["distance"] += weight * float(vote.distance or 0.0)
        elif vote.decision == Decision.UNKNOWN:
            unknown_weight += weight
        elif vote.decision == Decision.UNCERTAIN:
            uncertain_weight += weight

    means = []
    for person_id, entry in per_person.items():
        if entry["weight"] <= 0:
            continue
        means.append((entry["distance"] / entry["weight"], person_id))
    means.sort()

    candidates = [
        (mean_distance, person_id)
        for mean_distance, person_id in means
        if per_person[person_id]["count"] >= config.min_votes
        and mean_distance <= config.known_threshold
    ]

    if candidates:
        best_distance, best_person = candidates[0]
        runner_up_distance = next(
            (mean for mean, person_id in means if person_id != best_person),
            None,
        )
        if runner_up_distance is None or runner_up_distance - best_distance >= config.margin:
            return TrackletDecision(Decision.KNOWN, best_person, best_distance)

    if unknown_weight > 0 and unknown_weight >= uncertain_weight:
        return TrackletDecision(Decision.UNKNOWN)

    return TrackletDecision(_policy(config))
