# Calibration

Vigil ships default thresholds that work as a starting point. They are not
calibrated for your cameras, your lighting, or your photo set. This page
describes how to measure the distance distribution of your own gallery and
pick a threshold that matches the false-accept rate you are willing to live
with.

## What the distance means

The ResNet model returns a 128-dimensional vector. Vigil normalizes every
vector to unit length, then scores a query against each enrolled person with
Euclidean distance:

```
distance = || query - enrolled ||

         = sqrt(2 - 2 * cosine_similarity)
```

The scale runs from 0 (identical) to 2 (opposite). A smaller distance is a
better match.

The gallery keeps every enrolled vector for a person. With
`face.gallery_score = "min"`, the person's score is the distance to their
nearest vector. With `top3_mean`, it is the mean of the three nearest
vectors. `min` is more permissive and noisier. `top3_mean` needs at least a
few photos per person to be meaningful.

`decide_observation` compares the best person's score with two thresholds:

- At or below `known_threshold` with a clear margin: a known vote.
- At or above `unknown_threshold`: an unknown vote.
- Between them: an uncertain vote.

`decide_tracklet` then aggregates the votes. A person needs at least
`min_votes` known votes and a mean distance at or below `known_threshold`,
and the runner-up person must be worse by at least `margin`. One frame can
never produce a known event on its own.

The defaults are `known_threshold = 0.6`, `unknown_threshold = 0.7`, and
`margin = 0.05`. The gap between the two thresholds is the uncertain band
and must stay positive. Vigil refuses to load a config where
`unknown_threshold <= known_threshold`.

## Leave-one-out measurement

The goal is two distance lists:

- **Genuine**: distance from one photo of a person to the nearest other
  photo of the same person.
- **Impostor**: distance from one photo of a person to the nearest photo of
  any other person.

The impostor list uses the nearest other person, because that is exactly
what the gallery does when it picks the best match. A threshold chosen
against an average over all impostors would be too optimistic.

For each enrolled photo:

1. Remove that photo from the gallery, keeping the rest of the person's
   photos and every other person.
2. Score it with the same mode you configured (`min` or `top3_mean`).
3. Record the distance to the same person, if another photo exists, as a
   genuine sample.
4. Record the distance to the nearest other person as an impostor sample.

Leave-one-out matters most when a person has only one photo. That photo
cannot contribute a genuine sample, and it should not be compared with
itself.

## Read your own database

The application can run while you read the database, because SQLite is in
WAL mode. Use the same interpreter that has NumPy installed:

```python
import sqlite3
from pathlib import Path

import numpy as np

MODEL_ID = "dlib_resnet_v1"
db = Path.home() / "AppData" / "Local" / "Vigil" / "vigil.db"

conn = sqlite3.connect(str(db))
rows = conn.execute(
    "SELECT person_id, vector FROM embedding WHERE model_id = ?",
    (MODEL_ID,),
).fetchall()

gallery = {}
for person_id, blob in rows:
    gallery.setdefault(int(person_id), []).append(
        np.frombuffer(blob, dtype="<f4").astype(np.float32)
    )

for person_id, vectors in gallery.items():
    gallery[person_id] = [v / np.linalg.norm(v) for v in vectors]

genuine = []
impostor = []

for person_id, vectors in gallery.items():
    for index, query in enumerate(vectors):
        same = [v for i, v in enumerate(vectors) if i != index]
        if same:
            genuine.append(min(float(np.linalg.norm(v - query)) for v in same))

        rivals = [
            float(np.linalg.norm(v - query))
            for other_id, other in gallery.items()
            if other_id != person_id
            for v in other
        ]
        if rivals:
            impostor.append(min(rivals))

print("genuine samples", len(genuine))
print("impostor samples", len(impostor))
if genuine:
    print("genuine p50", round(float(np.percentile(genuine, 50)), 3))
    print("genuine p95", round(float(np.percentile(genuine, 95)), 3))
if impostor:
    print("impostor p5", round(float(np.percentile(impostor, 5)), 3))
    print("impostor p1", round(float(np.percentile(impostor, 1)), 3))
```

The `top3_mean` variant is the mean of the three smallest same-person
distances in the `same` list.

## Choose a threshold from a target false-accept rate

A false accept means an impostor lands at or below `known_threshold`. To hold
the rate at or below a target `far`, choose the threshold at the matching
quantile of the impostor distribution:

```python
threshold = float(np.quantile(impostor, far))
```

For example, `far = 0.01` means at most one percent of the measured impostor
samples would be accepted. Use the nearest-impostor list, not all pairs.

Then check the genuine side at that threshold:

```python
if genuine:
    accept_rate = sum(1 for d in genuine if d <= threshold) / len(genuine)
    print("genuine accept rate", round(accept_rate, 3))
```

A threshold that meets the false-accept target but rejects most genuine
photos is not useful. Add more photos per person, improve lighting, or accept
a higher false-accept rate.

Set `unknown_threshold` above `known_threshold`. The band should cover the
part of the impostor distribution that is close to the known threshold, so
borderline faces become uncertain instead of jumping to a confident name.
A common starting point is the known threshold plus `0.05` to `0.10`, but the
measured distributions decide.

## Check the margin

`margin` protects against two enrolled people who look similar to the model.
Compute the difference between the best and second-best person for genuine
queries. If many genuine samples have a gap below the configured margin, the
system will report them as uncertain even though the correct person is on
top. Either enlarge the photo sets so the winner is clearer, or lower the
margin and accept more confusion between those two people.

## Workflow

1. Enroll at least three photos per person, from different angles and
   lighting, when you can.
2. Run the script above and note the quantiles.
3. Pick `known_threshold` from the impostor quantile for your target false
   accept rate.
4. Pick `unknown_threshold` above the known threshold and below the
   confident impostor region.
5. Check the genuine accept rate and the margin distribution.
6. Put the values in Settings, save, and watch the Events page for a few
   days.
7. Recalibrate after adding a camera, moving a camera, or changing a large
   part of the photo set.

## Limits

- The measurement only covers photos that were already detected and
  embedded. Blurry, small, or turned faces may fail the quality gate before
  scoring, and those failures do not appear in the distributions.
- Cosine distance does not model lighting, age, or camera differences. It
  measures what the ResNet considers similar.
- An unknown cluster uses `unknown_merge_threshold` to group repeated
  strangers. That threshold is separate from the known/unknown band and is
  not part of the false-accept calculation.
- Do not tune thresholds against the same photos used for enrollment. The
  numbers will look better than reality. Use leave-one-out as above, or hold
  out a set of photos per person.
