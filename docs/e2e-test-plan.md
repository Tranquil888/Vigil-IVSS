# End-to-end test plan

The unit and integration suites prove individual modules. This plan covers
the paths that only exist when a capture thread, the queues, the workers, the
database, and the GUI run together. It is split into an automated suite that
runs on any machine and a manual matrix for hardware and packaging gates.

The comparison that produced this plan is in `docs/plan-gap-analysis.md`.

## Automated suite

```powershell
# All end-to-end tests
python -m pytest tests\e2e -q -m e2e

# The whole project, including end-to-end tests
python -m pytest -q
```

The suite needs no camera, no GPU, and no model files. GUI tests set
`QT_QPA_PLATFORM=offscreen` in `tests/e2e/conftest.py`. The video test needs
an OpenCV build with MJPG or an equivalent codec; the helper falls back to
XVID and mp4v before it skips.

## What the suite proves

| Test file | Real path exercised | Plan section |
|---|---|---|
| `test_clock_video.py` | Burned-clock encode, decode, and JPEG survival | 11.3 |
| `test_latency.py` | Paced video source, capture thread, `LatestFrame`, display consumer, 150 ms inference delay | 0, 4.1, 11.3 |
| `test_pipeline.py` | Capture, motion, inference, tracklet decision, event bus, SQLite, snapshots, unknown cluster | 4, 5, 6, 7 |
| `test_pipeline.py` | Camera open failure, backoff, offline and online events | 4.2 |
| `test_pipeline.py` | Unavailable face backend, motion-only operation, display still live | 2, 6 |
| `test_pipeline.py` | Restart with the same data directory, event persistence, one camera row | 7 |
| `test_display.py` | `LatestFrame` to `QImage`, paint and grab, stale frame, overlay TTL | 9 |
| `test_display.py` | Static guard that no GUI module imports dlib | 0 |

## Gray-box checks

The queue, thread, database, retention, redaction, backend, and live reload
checks are in `docs/graybox-test-plan.md`. They use `scripts/graybox_probe.py`
and the Diagnostics page, and they are the intended follow-up to a green
automated suite.

Recognition quality is measured separately against a folder-per-person
dataset:

```powershell
python scripts\eval_recognition.py --dataset data\dataset --models models `
    --limit-per-person 8 --require-cnn
```

The recorded smoke result and the threshold caveat are in
`docs/graybox-test-plan.md`.

## The burned-clock measurement

`tests/e2e/clock_video.py` writes a clip with a 32-bit millisecond value on
every frame. The value is encoded as high-contrast blocks at the bottom-left,
with a four-bit marker so a frame without a clock is rejected. The strip is
machine-readable instead of OCR text, and it survives JPEG and the paint
path.

`PacedVideoSource` plays the file at 30 fps and records a monotonic base for
frame zero. A frame whose burned value is `N * 1000 / fps` is due at
`base + N / fps`. The display consumer reads `LatestFrame` every 15 ms,
decodes the burned value, and records the difference. That number includes
video decode, queue handoff, and the display poll. It does not include camera
exposure or USB transfer, which happen before a frame exists.

Inference runs in a separate thread. In the delayed run it sleeps 150 ms per
frame, so the four-slot inference queue fills and drops frames. The assertion
is that the display p95 changes by less than 50 ms and that the queue drop
counter is greater than zero, so the test cannot pass by accident when the
inference consumer is idle.

## Recorded result

Windows 11, CPython 3.9.23, 640x360 MJPG clip at 30 fps, 2 s per run, 15 ms
display poll:

| Run | Samples | p50 | p95 | p99 | Inference drops |
|---|---|---|---|---|---|
| No inference delay | 122 | 32.0 ms | 48.0 ms | 50.0 ms | 0 |
| 150 ms inference delay | 122 | 33.5 ms | 49.0 ms | 50.0 ms | 16 |

The p95 delta is 1.0 ms against a 50 ms budget. The absolute values are
higher than the synthetic harness in `docs/latency.md` because they include
MJPG decode. That is the point of this test: it measures a frame that was
actually encoded, decoded, captured, and read by the display consumer.

### Four file-backed cameras

`tools/video_latency_probe.py` repeats the same idea with four real
`VideoFileSource` capture threads, a 15 ms display poll, and a 150 ms inference
consumer. Recorded on 2026-11-14 with four ChokePoint face clips:

| Measure | Value |
|---|---|
| Display frame age | p50 32 ms, p95 63 ms, p99 78 ms, max 110 ms |
| Samples | 3730 over 15.3 s |
| Per-camera frames | 226 to 229, reconnects 0 |
| Inference dropped | 164 |

The queue dropped 164 frames while the display p95 stayed at 63 ms. This is a
file-backed four-camera load, not the four 1080p hardware run below.

## Manual hardware matrix

These runs cannot be made deterministic in a repository test. Record the
date, machine, camera models, and the commands used.

### 1. Reference GPU, four 1080p cameras

- Machine: Windows 11, RTX 3050, CUDA 12.9, cuDNN 9, dlib-gpu 20.0.1 cp312.
- Cameras: four RTSP streams at 1080p, sub-stream for analysis.
- Run the burned-clock clip on one camera and the three real streams on the
  others, or place the clock in a corner of the scene.
- Measure once with `face.detector = "dlib_cnn"` and recognition enabled, then
  once with `face.detector = "none"` and motion only.
- Pass: p95 difference under 50 ms, all four tiles live, inference queue
  depth returns to zero, no display tile shows a growing delay.
- Record `context.stats()` and the developer log for the run.

### 2. CPU-only machine

- No CUDA build. Start with the three model files present and then remove the
  ResNet file.
- Pass: the status bar names the missing file, recognition is disabled, motion
  events still reach the Events page, and the live view stays responsive.

### 3. Camera loss and recovery

- Pull the network cable or stop the RTSP server for longer than
  `capture.offline_notify_after_s`.
- Pass: the tile shows "No signal", one `camera_offline` event appears after
  the configured delay, reconnecting publishes `camera_online`, and no
  duplicate offline events appear for the same outage.

### 4. Database and log

- Generate motion and stranger events, then inspect `vigil.db` and
  `logs/vigil.log`.
- Pass: event, tracklet, snapshot, and unknown cluster rows are consistent;
  the log contains no camera password, embedding vector, or image bytes; the
  log rotates at 10 MB and keeps five files.

### 5. Clean Windows VM, CPU build

- Copy `dist\Vigil` to a VM without Python or Visual C++ redistributables.
- Pass: the executable starts, the window paints, a local camera or clip
  plays, and the event log writes. No `0xc0000139`, no missing DLL dialog.

### 6. CUDA build on the reference GPU

- Build with the conda-forge `dlib-gpu` environment, copy the bundle to the
  RTX 3050 machine, and start it.
- Pass: the Diagnostics page reports CUDA and cuDNN as available, the detector
  reports `dlib_cnn`, and the bundle does not silently fall back to CPU or HOG
  without a visible warning.
- The frozen bundle was started here with the installed model directory and
  logged `face backend selected: dlib_cnn cuda=True cudnn=True ready on GPU`.
  A run on the separate release machine is still open.

## Pass criteria for the MVP

1. Automated suite green, including the 50 ms latency delta assertion.
2. Four 1080p cameras live on the reference GPU with recognition enabled.
3. Glass-to-glass p95 within 50 ms of the same setup with recognition off.
4. CPU-only fallback is visible and motion events still work.
5. Camera offline and recovery events are correct.
6. Clean-VM CPU bundle starts and runs; CUDA bundle reports GPU correctly.
7. No secret, embedding, or image bytes in the developer log.

## Known blockers

The automated suite does not cover these because they are product gaps or need
hardware, not because the harness is missing:

- The clean-VM run of the CPU bundle. The CUDA bundle runs on the reference
  RTX 3050 and reports the CNN backend on the GPU.
- No four-camera hardware run, so the 50 ms gate has only been shown with
  synthetic or file-backed cameras, including the four-video probe above.
- Recognition thresholds are calibrated on ChokePoint and the local photo set
  (`known_threshold = 0.28`, `unknown_threshold = 0.38`), but every deployment
  still needs its own gallery measurement. `docs/calibration.md` has the
  procedure and the gallery-size caveat.

The closed items, one unknown visit per row, retention pruning, CUDA and cuDNN
fallback, the Diagnostics page, and recognition threshold calibration now have
tests or a recorded probe run.
The full list is in `docs/plan-gap-analysis.md`.
