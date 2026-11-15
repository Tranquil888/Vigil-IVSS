# Gray-box test plan

The automated suite in `docs/e2e-test-plan.md` proves the event path from the
outside. This plan proves it from the inside: while the real workers run, it
reads queue depths, thread liveness, event rows, and backend state. It needs no
debugger and no camera. The hardware runs at the end are the only steps that
need a real machine.

## Tools

| Tool | What it gives you |
|---|---|
| `scripts/graybox_probe.py` | Builds `AppContext`, optionally runs the workers for N seconds, prints the diagnostics report |
| `src/vigil/diagnostics.py` | The same report as plain data, used by the Diagnostics page and the probe |
| Diagnostics page | Live report, Copy report, and Reload config |
| `scripts/eval_recognition.py` | Top-1 accuracy and genuine/impostor distances from a folder-per-person dataset |
| `tests/e2e` | Real threads, real queues, real SQLite, no GPU |

Use the verification interpreter:

```powershell
$py = "dlib-env\Scripts\python.exe"
```

## 1. Queue invariants

Pass criteria:

- `LatestFrame` holds one frame. There is no queue depth to grow.
- The inference queue depth returns to zero after capture stops.
- `inference.dropped` rises when inference is slower than capture, and
  `inference.stale_frames` rises when the queue holds a frame past
  `inference.max_frame_age_s`.
- No stat is unbounded except the counters themselves.

Run with a synthetic camera and a real backend:

```powershell
& $py scripts\graybox_probe.py --run 30 --fake-camera --json |
    ConvertFrom-Json |
    Select-Object -ExpandProperty runtime
```

Record `inference.queued`, `inference.dropped`, and the per-camera
`inference_sent`. A four-slot queue that stays full while `dropped` stays flat
means the consumer is not keeping up and the sampler is not the cause.

The automated guards are `tests/core/test_queues.py`,
`tests/test_latency_invariant.py`, and `tests/e2e/test_latency.py`.

## 2. Thread liveness

The context owns the database writer, the notifier, the inference worker, one
capture thread per enabled camera, and one motion worker per camera with
motion enabled. `AppContext.stats()` lists every one with an `alive` flag.

Pass criteria:

- Before shutdown, every worker that should run reports `alive: true`.
- During a live reload, no thread is left behind. The count before and after
  matches the new camera set.
- After `shutdown()`, every worker reports `alive: false` and the process
  exits without a join warning in the log.

Check a restart after a camera is disabled:

1. Start with two enabled cameras, confirm five or more live threads.
2. Disable one camera in Cameras, save.
3. The Diagnostics page should show one fewer capture thread and the camera
   list should match the config.

## 3. Database rows

Open the database read-only and check the shape, not only the count:

```powershell
& $py -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('select type,count(*) from event group by type').fetchall())" `
    "$env:LOCALAPPDATA\Vigil\vigil.db"
```

Pass criteria:

- One unknown visit produces one `event` row. Later tracklets in the same
  visit extend `ts_end` and increase `unknown_cluster.n_visits`; they do not
  add a second row with the same `dedupe_key`.
- A `known_face` event points at the person it matched. A `stranger` event
  points at an unknown cluster, not at a person.
- Every event with a snapshot has a snapshot row whose file exists.
- Tracklet, snapshot, and cluster rows with no event reference are removed by
  retention, not left behind.
- A restart with the same data directory keeps the rows and does not create a
  second camera row.

The automated guards are `tests/storage/test_writer.py`,
`tests/analysis/test_pipeline.py`, and `tests/e2e/test_pipeline.py`.

## 4. Retention

Set `storage.event_retention_days = 1`, write an event dated two days ago, and
start the context. The writer prunes at startup and once per hour.

Pass criteria:

- The old event, its tracklet, its cluster, and its snapshot row are gone.
- The snapshot file on disk is gone.
- Events newer than the cutoff stay.

The automated guard is
`tests/storage/test_writer.py::test_retention_prunes_old_events_and_releases_snapshot_files`.

## 5. Log redaction

Generate a motion event, a stranger event, and a known event, then search the
developer log:

```powershell
Select-String -Path "$env:LOCALAPPDATA\Vigil\logs\vigil.log" `
    -Pattern "password|rtsp://|embedding|base64|data:image"
```

Pass criteria:

- No camera password appears, even when the source URL contains one.
- No embedding vector and no image bytes appear.
- The event name and the camera id still appear, so the log stays useful.
- Rotation still happens at 10 MB with five files.

The automated guard is `tests/telemetry/test_redaction.py`.

## 6. Backend status

The probe checks three separate facts: dlib is importable, CUDA is compiled in
and has a device, and a cuDNN library can be loaded. A missing CNN file, CUDA,
or cuDNN falls back to HOG instead of failing at the first frame.

| Setup | Expected detector | Expected reason |
|---|---|---|
| All three files, CUDA, cuDNN | `dlib_cnn` | `ready on GPU` |
| All three files, CPU only | `dlib_hog` | CUDA is not available |
| CUDA present, cuDNN missing | `dlib_hog` | cuDNN was not found |
| CNN file missing | `dlib_hog` | CNN model missing at path |
| Landmark or ResNet file missing | detector unchanged | recognition is disabled, missing file |

Pass criteria:

- The Diagnostics page shows detector, CUDA, cuDNN, embedding, and the reason.
- The status bar uses warning color when the reason names a fallback.
- The CNN path is exercised, not only HOG. On this machine:

```powershell
& $py -m pytest tests\analysis\test_models.py -q -m models
& $py scripts\eval_recognition.py --dataset data\dataset --models models `
    --limit-per-person 4 --require-cnn
```

`--require-cnn` exits non-zero when the probe chose HOG, so a passing run is
evidence that the CNN model loaded and produced embeddings.

## 7. Live configuration apply

A save from Cameras or Settings writes the TOML file and calls
`AppContext.apply_config()`. The Diagnostics page can also re-read the file
with Reload config.

What rebuilds and what does not:

| Change | Result |
|---|---|
| Add, remove, enable, disable a camera | Capture and motion workers rebuild |
| Camera source, motion section, zones | Capture and motion workers rebuild |
| `inference.analysis_fps` | Capture sampler interval updates in place |
| `inference.queue_size` | Inference queue resizes, dropping oldest first |
| Face thresholds, tracker, grouping | Inference worker adopts them, live tracklets keep state |
| Person name | Live overlays and notifications see it through the shared map |
| Detector, device, model directory | Face backend reloads |
| Snapshot quality, retention | Snapshot store and writer adopt them |

Pass criteria:

- Changing analysis fps does not interrupt the live tile.
- Enabling a camera makes a new tile appear without an application restart.
- Changing the detector from `dlib_cnn` to `dlib_hog` changes the status line
  and the Diagnostics report after one apply.
- A reload from the TOML file updates the Settings widgets, not only the
  workers.
- No stale thread survives a rebuild.

The automated guards are `tests/test_app_context.py`,
`tests/core/test_queues.py`, and `tests/gui`.

## 8. Recognition dataset evaluation

The dataset is one subfolder per person. The script embeds up to
`--limit-per-person` images per person and scores leave-one-out. It reports the
top-1 result, both distance distributions, the equal error point, the Youden
point, and suggested thresholds.

```powershell
& $py scripts\eval_recognition.py --dataset data\dataset --models models `
    --limit-per-person 12 --gallery-score min --require-cnn --json
```

Pass criteria:

- The backend line names `dlib_cnn`, and the script exits zero.
- Top-1 accuracy, the genuine distance distribution, and the impostor distance
  distribution are recorded with the run date and the dataset size.
- The chosen `known_threshold` sits between the genuine and impostor
  distributions, with a margin. A threshold that accepts every measured
  impostor is a calibration failure, even when accuracy looks good.

Recorded on 2026-11-14 with ChokePoint portal 1 (`test-dataset\P1E.tar`),
25 people, 12 crops per person across 12 camera sequences:

| Measure | Value |
|---|---|
| Embeddings | 272 of 300 crops, 28 had no detectable face |
| Top-1 | 267/272, 98.2% |
| Genuine distance | mean 0.201, p90 0.294, max 0.426 |
| Impostor distance | mean 0.378, p90 0.433, min 0.258, max 0.464 |
| Equal error | 8.3% at 0.30 |
| Youden point | 0.28: genuine 87.5%, impostor 3.3% |

The P1L leaving condition was held out and scored at the thresholds chosen on
P1E: top-1 292/292 (100%), genuine mean 0.204, impostor mean 0.362. At
`known_threshold = 0.28` it accepted 92.1% of genuine pairs and 9.2% of
impostors. At `unknown_threshold = 0.35` it kept 100% of genuine pairs and
rejected 62.3% of impostors.

The local two-person photo set (`data/dataset`) gave 21 embeddings, 21/21 top-1,
genuine mean 0.136 (max 0.258), and impostor mean 0.447 (min 0.430). Every
threshold from 0.26 to 0.42 separated the two groups completely.

The shipped defaults are now `known_threshold = 0.28` and
`unknown_threshold = 0.38`. They are the Youden point of both ChokePoint
conditions, keep 98.9% of P1E genuine and 100% of P1L genuine pairs, and reject
55.5% and 44.2% of their impostors. The old 0.6 default accepted every measured
impostor. Full tables and the gallery-size caveat are in `docs/calibration.md`.

## 9. Four-video latency probe

`tools/video_latency_probe.py` builds four real capture threads around
`VideoFileSource`, consumes inference on a 150 ms thread, and polls every
`LatestFrame` at 15 ms. The videos are the six ChokePoint clips rebuilt by
`scripts/build_chokepoint.py`.

```powershell
& $py tools\video_latency_probe.py --video-dir data\chokepoint\videos `
    --cameras 4 --seconds 15 --inference-delay-ms 150 --json
```

Recorded on 2026-11-14:

| Measure | Value |
|---|---|
| Display frame age | p50 32 ms, p95 63 ms, p99 78 ms, max 110 ms |
| Samples | 3730 over 15.3 s (4 cameras at 15 ms polls) |
| Per-camera frames | 226 to 229, all reconnects 0 |
| Inference sent | 264 frames |
| Inference dropped | 164 |

The slow inference consumer filled the queue and dropped 164 frames while the
display p95 stayed at 63 ms. That is the display invariant under a file-backed
four-camera load. It does not replace the four 1080p hardware run below.

## 10. Hardware runs

These are the same gates as `docs/e2e-test-plan.md`, with the gray-box checks
added. Record the date, machine, camera models, and the report output.

1. **Four 1080p cameras on the reference GPU.** Run for ten minutes with
   recognition on. Record `runtime.inference.queued`, `dropped`, and
   `stale_frames` every minute. Pass: tiles stay live, queue depth returns to
   zero, thread count is stable, and p95 display latency stays within 50 ms of
   the same run with `face.detector = "none"`.
2. **CPU-only machine.** Start with all models, then remove the ResNet file.
   Pass: the detector is HOG, embeddings still work while the models are
   present, then recognition is disabled and motion events are still written
   after the file is removed. The live view stays responsive in both states.
3. **Clean Windows VM.** No Python, no Visual C++ redistributable. Pass: the
   bundle starts, paints, plays a clip, and writes an event.
4. **CUDA bundle on the RTX 3050.** Pass: Diagnostics reports `dlib_cnn`,
   CUDA yes, cuDNN yes, and the bundle does not silently fall back.
5. **Camera loss.** Pull the stream for longer than
   `capture.offline_notify_after_s`. Pass: one offline event, one online event,
   no duplicate offline rows.

## 11. What is still not automated

- A GPU and a physical camera in CI.
- The clean-VM start. The CUDA bundle and the release artifacts are checked
  locally by `scripts/release_check.ps1`.
- A four 1080p hardware run. The four-video file-backed probe is automated.

Everything else in this plan has a repository test or a recorded probe run.
