# Plan gap analysis

Compared `Vigil_new_plan.md` with the tree at commit `a7c1b05` on
`feat/3-rewrite-vigil`. The purpose is to separate what the MVP already
proves, what is only partly built, and what was deliberately changed.

Legend:

- **Done**: implemented and covered by tests.
- **Partial**: the main path exists, but a named part of the plan does not.
- **Missing**: no implementation.
- **Deviation**: implemented differently from the plan, with a recorded reason.

## 0. Architectural invariant

**Done.** `LatestFrame` holds one frame and `put` never blocks. The capture
supervisor publishes every decoded frame to it, samples inference separately
through `DropOldestQueue(4)`, and the video tile only calls `latest()`. The
display path imports no dlib code. Guarded by
`tests/test_latency_invariant.py` and the new `tests/e2e` latency test.

## 1. MVP scope

| Deliverable | State | Evidence and gap |
|---|---|---|
| Decoupled capture and display | Done | `video/capture.py`, `core/queues.py`, `gui/widgets/video.py` |
| dlib CNN plus ResNet, tracklet decisions | Partial | Backend, tracker, and decisions exist. The pipeline embeds every quality-passing observation instead of only the best K. |
| Motion zones and MOG2 fallback | Partial | Zones, MOG2, global-change suppression, and cooldown exist. `motion.preroll_s` is a config field with no ring buffer behind it. |
| Event log and developer log | Partial | SQLite events and a rotating redacted JSON log exist. `storage.event_retention_days` is never applied. |
| Person dataset and index rebuild | Done | People page, photo import, embeddings, gallery rebuild |
| Unknown grouping | Partial | The grouper merges similar tracklets, but each tracklet still produces its own event row. The plan asks for one log entry per visit. Clusters live in memory and are only rehydrated when a new cluster row is written. |
| TOML and Pydantic config | Done | Strict models, defaults, TOML round trip |
| Five GUI pages | Partial | Pages exist. There is no zone polygon editor, and the camera page does not expose per-camera motion or zone overrides. |
| Tray notification and optional sound | Done | `notify/notifier.py`, `gui/tray.py` |
| PyInstaller `--onedir`, CPU and CUDA builds, first-run probe | Partial | Bundle and scripts exist. No installer, no portable zip, no diagnostics page, and no CUDA build tested on the reference GPU. |

## 2. Reference hardware and CUDA path

| Item | State | Gap |
|---|---|---|
| CUDA 12.9, cuDNN 9, dlib-gpu 20.0.1 cp312 | Partial | Local verification used CPython 3.9.23, dlib 20.0.0, and a CUDA 11 runtime. The release target is not tested. |
| Startup CUDA probe | Partial | `probe_backend` checks `DLIB_USE_CUDA` and `dlib.cuda.get_num_devices()`. It does not check cuDNN, and it does not switch to HOG or motion-only when CUDA is absent. |
| Visible warning on CPU fallback | Done | Status bar and settings page show the backend reason in warning color. |
| `inference.device` honored at runtime | Missing | The value is validated but dlib chooses its device from its own build. Documented as intent, not a runtime switch. |

## 3. Technology stack

| Item | State | Gap |
|---|---|---|
| CPython 3.12.x | Partial | `requires-python >= 3.9`; CI covers 3.9 and 3.12; local verification used 3.9.23. |
| dlib 20.0.1 | Partial | Local 20.0.0. |
| OpenCV 4.12 or 4.13 | Done | Local 4.12.0, `opencv-python-headless`. |
| PySide6 6.11.2 | Partial | Local 6.9.3 because Qt 6.10+ collides with conda ICU. Documented in `docs/packaging.md`. |
| SQLAlchemy 2.x and Alembic | Partial | SQLAlchemy Core is used. Alembic is a dev dependency only; the schema is created with `metadata.create_all`. |
| Pydantic 2 and tomlkit | Done | Strict models and comment-preserving writes |
| NumPy 2.x | Partial | The range allows 1.26 through 2.x. Local is 1.x. |
| `cryptography` and `keyring` for camera secrets | Missing | Camera URLs are stored in plain TOML. No keyring or encrypted fallback exists. |
| PyInstaller 6.22.0, `--onedir` | Partial | Local 6.22.3, onedir works. |
| No ONNX, FAISS, go2rtc, Telegram, SMTP | Done | None are present. |

## 4. Thread and queue layout

| Item | State | Gap |
|---|---|---|
| One capture thread per camera | Done | `CameraManager` |
| `DisplayQueue` capacity 1, overwrite | Done | Implemented as `LatestFrame` |
| Motion sampled every second frame | Done | `motion.sample_every` |
| Inference sampled at `analysis_fps` | Done | `FrameSampler` |
| Inference queue bounded at 4, oldest dropped | Done | `DropOldestQueue` |
| GUI reads newest frame only | Done | `VideoTile` timer |
| Reconnect state machine and backoff | Done | `video/state.py`, `video/capture.py` |
| Reconnect closes tracklets and resets motion | Missing | Neither is wired to a reconnect. Tracklets close by gap timeout; the MOG2 model keeps its old background. |
| GUI shows "No signal" over the last frame | Deviation | The tile blanks the image and draws "No signal". It does not keep the last frame behind the text. |

## 5. Face pipeline

| Stage | State | Gap |
|---|---|---|
| Motion gate, continuous opt-in | Done | `motion.enabled = false` acts as continuous mode; there is no separate mode switch. |
| CNN detection downscaled to 800 px | Done | `DlibBackend.detect` |
| Per-camera IoU tracker | Done | `analysis/tracker.py` |
| Quality gate: size, blur, yaw | Partial | Size and blur are used. The pipeline never passes landmarks to `assess_quality`, so the yaw proxy is always zero. |
| Embed best K observations | Deviation | Every quality-passing observation is embedded immediately; only the best `best_k` votes are kept. Recorded in the ledger. |
| Euclidean match, min or top-3 mean | Done | `analysis/gallery.py` |
| Tracklet decision, margin, min votes, uncertain band | Done | `analysis/decisions.py` |
| Unknown grouping by window and centroid | Partial | Merging works. One event per visit is not enforced. |
| No fine-tuning | Done | Embeddings only |

Threshold defaults match the plan, the uncertain band is validated, and
`docs/calibration.md` documents the calibration procedure. Per-model threshold
storage is missing: there is no model or calibration table.

## 6. Motion

MOG2, 320 px grayscale, polygon masks, threshold plus contour area plus
sustained frames, cooldown, and global-change suppression are implemented.
Pre-roll is not. Motion-only operation works because motion events do not
depend on the face backend.

## 7. Database and logs

| Item | State | Gap |
|---|---|---|
| Schema tables and indexes | Done | `storage/schema.py` matches the plan |
| WAL, foreign keys, busy timeout | Done | `make_engine` |
| Single event writer thread | Done | `storage/writer.py` |
| GUI read-only connection | Done | `storage/reader.py` |
| Rotating JSON developer log, 10 MB by 5 | Done | `telemetry/logging_setup.py` |
| Redaction filter and test | Done | `tests/telemetry/test_redaction.py` |
| 90-day event retention | Missing | The setting is stored but no pruning job reads it. |

GUI people edits write through `PeopleStore` on the GUI thread. This is a
recorded ruling and is limited to small user-initiated transactions.

## 8. Configuration

All core defaults from the plan exist. The Settings page exposes every global
section, per-row reset, and an Advanced toggle. Camera and zone overrides are
validated but not editable in the UI, and there is no zone polygon editor.

## 9. GUI

| Item | State | Gap |
|---|---|---|
| Five pages | Done | Cameras, Live, Events, People, Settings |
| Window before workers, lazy dlib import | Partial | `app.py` builds `AppContext` before `MainWindow`. That probes dlib and opens the database before the first paint. |
| `QImage` from the latest frame | Done | `VideoTile` |
| Overlays with a one-second TTL | Done | `OverlayStore` |
| No modal dialogs for common actions | Partial | Remove camera and delete person use `QMessageBox.question`. |
| Dark/light follows the OS | Partial | The setting supports `system`, but the shipped default is `dark`. |
| No custom skin | Deviation | The operator console has a deliberate dark theme and a teal live accent. |

## 10. Packaging

The `--onedir` bundle, CPU and CUDA scripts, explicit CUDA DLL collection, and
`multiprocessing.freeze_support()` are present. Missing: Inno Setup installer,
portable zip, first-run diagnostics page, cuDNN probe, a clean-VM test, and a
CUDA test on the RTX 3050. The local bundle is 927 MB because it pulls CUDA 11
cublas DLLs from dlib.

## 11. Sprint order

Steps 1 through 8 are implemented. Step 3 is partly closed:
`tests/e2e/test_latency.py` burns a clock into a video, plays it through the
real capture thread, and decodes the frame at the display consumer. The
residual deviation is that it reads `LatestFrame` rather than a screenshot of
the Qt window; `tests/e2e/test_display.py` checks the offscreen paint path
separately. Step 9 is partial: the CPU bundle was built and smoke tested on
this machine, not on a clean VM. Step 10 is partial: the CUDA script exists,
but the reference GPU run has not happened.

The sprint success criterion, four 1080p cameras with face recognition and a
glass-to-glass p95 within 50 ms of the same setup without recognition, has not
been demonstrated.

## Deliberate deviations

1. `LatestFrame` replaces the planned `DisplayQueue`; the behavior is the same.
2. Every quality-passing observation is embedded immediately; only the best K
   votes are kept. This keeps the inference queue from holding images.
3. The synthetic harness measures queue age. The E2E harness adds a
   burned-clock video, real capture, decode, and a display consumer. Qt paint
   is verified separately offscreen, not inside the latency number.
4. Local PySide6 is 6.9.3 to avoid the conda ICU collision.
5. The GUI has a custom dark operator theme rather than the OS theme alone.
6. People edits bypass the event writer thread; event writes do not.

## MVP blockers

These are the gaps that still stop the plan's definition of done:

1. One event row per unknown visit, not one per tracklet.
2. Event retention pruning.
3. CUDA absence must visibly fall back to HOG or motion-only, and the probe
   must report cuDNN state.
4. First-run diagnostics page.
5. Camera secrets in the OS keyring or an encrypted fallback.
6. Verified CPU build on a clean Windows VM and a CUDA build on the RTX 3050.
7. Installer and portable zip.
8. Reference-hardware latency run with four 1080p cameras.

The end-to-end harness and the manual matrix are in
`docs/e2e-test-plan.md`.
