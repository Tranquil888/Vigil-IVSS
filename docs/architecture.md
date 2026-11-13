# Architecture

Vigil is one process with a small number of long-lived threads. There is no
child process, no local server, and no IPC. A camera frame is a Python object
that travels through queues; the display reads only the newest one.

## Threads

| Thread | Count | Owns | Never does |
|---|---|---|---|
| Qt main | 1 | windows, pages, timers, tray, painting | dlib, database writes, blocking waits |
| Capture supervisor | one per enabled camera | one video source, `LatestFrame`, sampling | inference, painting |
| Motion worker | one per camera with motion enabled | background model, zone masks | inference, database writes |
| Inference worker | 1 for all cameras | tracker, gallery decisions, snapshots | painting, database writes |
| DB writer | 1 | every event insert | inference, painting |
| Notifier | 1 | cooldowns, toast callbacks | inference, database writes |

The notifier delivers toasts by emitting a Qt signal. `ToastBridge` in
`gui/shell.py` queues that signal onto the GUI thread, so a worker never
touches a widget.

## Data flow

```
camera -> CaptureSupervisor -+-> LatestFrame(1) ---------------> VideoTile timer
                             |
                             +-> motion queue (2) -> MotionWorker -> motion gate
                             |                                         |
                             +-> inference queue (4) <-----------------+
                                        |
                                        v
                                 InferenceWorker
                                   -> tracker
                                   -> quality gate
                                   -> embedding + gallery
                                   -> EventBus ------> DBWriterThread -> SQLite
                                                \----> Notifier -> tray toast
                                                \----> OverlayStore -> VideoTile
```

The capture supervisor publishes every frame to `LatestFrame`. It publishes
a copy to the motion queue every `motion.sample_every` frames. It publishes
to the inference queue only when the motion gate is open and the time-based
sampler is due. The sampler uses `inference.analysis_fps`, not the camera
frame rate, so a 25 fps camera at 5 analysis fps sends one frame in five.

`LatestFrame` has a capacity of one. `put` replaces the previous frame and
returns immediately. `latest` never waits. `DropOldestQueue` drops its oldest
item when full, so a slow consumer increases the drop counter, not latency.

The display tile polls at `display.grid_fps` or `display.single_fps` and
calls `latest()` on its timer. It does not consume a queue and cannot
back up. `tests/test_latency_invariant.py` guards this with a p95 budget, and
`tests/e2e/test_latency.py` repeats the check with a burned-clock video, a
real capture thread, and a 150 ms inference delay.

## Clocks

- `Frame.captured_at` is monotonic. It measures age and timeouts.
- `Frame.wall_time` is epoch time. It is written to the database and shown
  in the UI.
- Overlay expiry is monotonic.
- Event timestamps are epoch floats.

Keeping the two clocks separate avoids wall-clock jumps breaking the stall
detector or the latency measurement.

## Database

SQLite in WAL mode with `foreign_keys=ON` and `synchronous=NORMAL`. The
schema is created at startup by `storage.schema.create_schema`.

- `DBWriterThread` is the only writer of events, tracklets, clusters, and
  notifications. It reads `EventRecord` objects from its own bus
  subscription and writes them one at a time. Duplicate `dedupe_key` values
  are skipped before insert, and a unique index backs that check.
- `Reader` opens its own connection for the GUI. It never writes.
- `PeopleStore` and `EmbeddingStore` are used by the GUI for short,
  user-initiated transactions: create a person, add a photo, disable a
  person, rebuild the gallery. These writes are small and cannot contend
  with the event burst enough to matter. Event writes still go through the
  single writer thread.

Tables:

| Table | Holds |
|---|---|
| `schema_meta` | schema version |
| `camera` | camera ids and names |
| `person` | name, notes, enabled flag |
| `person_image` | imported photo path, sha256, quality |
| `embedding` | normalized vector blob, model id, dimension |
| `tracklet` | one row per decided tracklet |
| `event` | motion, known face, stranger, uncertain, camera online/offline |
| `snapshot` | JPEG path and hash |
| `unknown_cluster` | centroid, first and last seen, visit count |
| `notification` | delivery channel, status, reason |

Embeddings are stored as little-endian float32 blobs and are never written to
the developer log. The gallery is rebuilt from enabled people only.

## Failure behavior

- A camera that will not open enters `BACKOFF`, retries with exponential
  backoff plus jitter, and publishes `camera_offline` after
  `capture.offline_notify_after_s`. A reconnect publishes `camera_online`.
- A camera that opens but stops delivering frames for
  `capture.stall_timeout_s` is treated as stalled and reconnects.
- A missing CNN model downgrades detection to HOG. A missing shape or ResNet
  model disables embedding and recognition, and the settings page shows the
  reason. A missing dlib leaves motion events working.
- A full inference queue drops old frames. The result is fewer observations,
  not a slower display.
- During shutdown the context stops capture first, then inference, the
  notifier, and the writer. The event bus and overlays are closed last.

## Configuration boundary

`config/models.py` is the only schema. `config/loader.py` merges a partial
TOML file over the defaults and writes it back with tomlkit, preserving
comments in scalar sections. Arrays of tables (`[[cameras]]`) are rebuilt on
save, which is the documented cost of editing structured camera data.

The GUI reads a `VigilConfig` object and the read-only views exposed by
`AppContext`. It never constructs a worker, never imports dlib, and never
opens the database directly.

## Where the invariants live

| Invariant | Enforced by |
|---|---|
| capture drains continuously | `CaptureSupervisor._publish`, no blocking calls |
| display reads only the newest frame | `LatestFrame` capacity 1, tile timer |
| inference consumes sampled copies | `FrameSampler`, `DropOldestQueue` |
| no display-path dlib calls | GUI imports; `VideoTile` only reads overlays |
| one DB writer | `DBWriterThread`, GUI writes limited to people edits |
| secrets and vectors stay out of logs | `telemetry/redaction.py` |
| thresholds are configurable | `config/models.py` and the Settings page |
