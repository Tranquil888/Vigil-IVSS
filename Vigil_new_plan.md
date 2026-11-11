# Intelligent Video Surveillance System — Build Plan for Opencode

**Reference hardware:** Windows 11, NVIDIA RTX 3050 (Ampere, compute capability 8.6).
**Model backend:** dlib CNN detector + ResNet embedder (your working prototype), with CUDA where available and CPU fallback. YuNet/SFace and ArcFace are deferred to Phase 3 as optional plugins.
**Revision note:** This plan supersedes the previous document. It incorporates the dlib decision, the RTX 3050 reference target, and corrections from verification. Confidence tags: **[H]** verified from a primary or official source, **[M]** well-established or secondary source, **[L]** estimate or unverified.

---

## 0. Non-negotiable architectural invariant

The previous prototype lagged because display and inference shared a blocking loop. WebRTC “fixed” it by removing display from that loop, not by fixing the pipeline. The fix is structural:

**Capture drains continuously. Display reads only the newest frame and never waits. Inference consumes sampled copies asynchronously. No stage on the display path may call into dlib, and no queue on the display path may grow.**

Every design choice below either implements this invariant or is deferred until it is proven.

---

## 1. Scope: what Opencode builds first

### 1.1 MVP (must ship)

| Area | Deliverable |
|---|---|
| **Decoupled capture + display** | One capture thread per camera; bounded latest-frame-wins display queue; Qt video widget; no inference on the display path |
| **dlib face recognition** | dlib CNN detector + ResNet embedder, CUDA if available; tracklet aggregation (one decision per face visit, not per frame); configurable Euclidean threshold (default 0.6) |
| **Motion detection** | Zone polygons; MOG2 background subtraction on sub-stream; motion-only mode as fallback |
| **Event log + developer log** | SQLite `events` table; rotating text log; strict separation of concerns |
| **Person dataset** | Add/edit/delete person; import photos; rebuild embedding index (no fine-tuning) |
| **Unknown-face grouping** | Group tracklets by time window and embedding similarity into one stranger event per visit |
| **Config** | TOML with Pydantic validation; defaults for camera, inference, motion, matching |
| **Minimal GUI** | Camera grid, single-camera view, event list, person management, settings pages; PySide6, no QML, no WebEngine |
| **Local notifications** | Desktop tray toast + optional sound (works with no external account) |
| **Packaging** | PyInstaller `--onedir`; CPU build and CUDA build; first-run hardware probe |

### 1.2 Explicitly out of MVP (Phase 2+)

Recording/NVR, multi-process supervisor with shared-memory rings, envelope encryption and audit logs, calibration wizard, Telegram/email, go2rtc/WebRTC display, plugin SDK, REST API, PostgreSQL, cross-camera re-identification, anti-spoofing.

The MVP uses **threads, not processes**, for capture, motion, inference, and DB writes. Process isolation is Phase 2, once the single-process architecture is proven to fix the lag. This keeps the first build tractable for Opencode and gives you a working product sooner.

---

## 2. Reference hardware and CUDA path

| Property | Value |
|---|---|
| GPU | RTX 3050 (Ampere) |
| Compute capability | **8.6**  |
| CUDA toolkit to install | **CUDA 12.9** (matches the conda-forge dlib-gpu build; CUDA 13.0 is also available but raises driver requirements) |
| cuDNN | **cuDNN 9** (required by dlib 20.0.1 CUDA builds) |
| dlib build | `dlib-gpu` 20.0.1 from conda-forge, `cuda129py312` variant (Python 3.12)  |
| Expected detector latency | ~50 ms per frame on GPU, versus ~500 ms on CPU  |
| Expected VRAM footprint | ~1.6–1.8 GB for dlib CNN at 2048×2048 input  — well within the 3050’s 4–8 GB |

**Build path decision.** Use the **conda-forge `dlib-gpu` binary**, not a source build. Source builds against cuDNN 9 on Windows are fragile: cuDNN 9’s installer creates version subdirectories, and dlib’s CMake detection frequently fails to find cuDNN unless `CMAKE_PREFIX_PATH`, `CMAKE_INCLUDE_PATH`, and `CMAKE_LIBRARY_PATH` all point at the versioned include/lib folders . The conda-forge build removes that failure mode. Document the conda environment as the supported GPU build path; keep a source-build recipe only as a fallback for users who cannot use conda.

**CPU fallback.** If CUDA or cuDNN is missing, dlib silently runs the CNN on CPU, which is too slow for real-time multi-camera use. The application must **detect this at startup** by checking `dlib.DLIB_USE_CUDA` and `dlib.cuda.get_num_devices()`, and if CUDA is unavailable, either switch the detector to HOG or disable face recognition and fall back to motion-only mode, with a visible warning.

---

## 3. Technology stack (MVP)

| Layer | Choice | Version | Confidence and notes |
|---|---|---|---|
| Python | CPython | **3.12.x** | PySide6 6.11.x supports 3.12 ; conda-forge dlib-gpu has a cp312 Windows build  |
| Face backend | **dlib** | **20.0.1** | CNN detector + ResNet embedder. GPU: `dlib-gpu` conda-forge `cuda129py312`. CPU: `dlib` from PyPI (source-only, needs CMake + VS Build Tools) |
| Video capture | OpenCV | **4.x** (pin patch after testing; 4.12 or 4.13) | `opencv-python-headless` for workers; FFmpeg backend for RTSP. Headless avoids Qt plugin clashes with PySide6 |
| GUI | **PySide6-Essentials** | **6.11.2** | Current stable series for Python 3.12 on Windows . Pin after Phase 0 |
| Database | **SQLite** (WAL) + SQLAlchemy 2.x + Alembic | SQLAlchemy 2.0.x; Alembic 1.20.x | Single writer thread; readers use separate connections |
| Config | **TOML** + **Pydantic v2** + `tomlkit` | Pydantic 2.14.x | `tomllib` reads; `tomlkit` preserves comments on write. This is a deliberate choice over YAML for round-trip comment safety and strict typing — state it in the repo |
| Numeric | NumPy | 2.x (pin against OpenCV/dlib wheel) | Binary compatibility is the common breakage point |
| Crypto (secrets) | `cryptography` + `keyring` | Latest compatible | Camera credentials in OS keyring; fallback encrypted file |
| Packaging | **PyInstaller** | **6.22.0** | `--onedir` only; CUDA DLLs must be added explicitly with `--add-binary`  |
| Notifications (MVP) | Qt tray toast | built into PySide6 | No external dependency; Telegram/email are Phase 2 |

**Explicitly not in the MVP stack:** ONNX Runtime, FAISS, go2rtc, Telegram bot framework, SMTP. Adding them later is a plugin concern, not an architectural change.

---

## 4. System architecture (MVP, single process, threads)

### 4.1 Thread and queue layout

```
Main thread (Qt event loop)
  ├── CameraManager (owns N capture threads)
  │     CaptureThread[camera] ──► DisplayQueue[camera] (size 1, overwrite)
  │                        └──► MotionSampler (every 2nd frame) ──► MotionEvent queue
  │                        └──► InferenceSampler (every Nth frame) ──► InferenceQueue (size 4)
  │
  ├── InferenceThread (dlib detector + embedder)
  │     consumes InferenceQueue, emits Observations ──► IdentityTracker
  │
  ├── IdentityTracker (tracklet aggregation, known/unknown decision)
  │     emits Events ──► EventBus
  │
  ├── DBWriterThread
  │     consumes EventBus, writes SQLite
  │
  └── NotifierThread
        consumes EventBus, shows tray toast with rate limiting

GUI timer (display FPS)
  └── reads DisplayQueue[camera].latest(), paints QImage, draws overlays if fresh (TTL 1 s)
```

**Rules that Opencode must enforce:**

- `DisplayQueue` has capacity 1. Writing a new frame overwrites the old one; there is no blocking put.
- The GUI timer never calls into `InferenceThread`, `IdentityTracker`, or the DB.
- `InferenceQueue` is bounded at 4. When full, the **oldest** sampled frame is dropped, never the newest display frame.
- Capture thread runs at stream rate and never sleeps waiting for inference.
- Every queue operation is non-blocking or has a timeout; no thread waits on another without a deadline.

### 4.2 Camera reconnect

Per-camera state machine: `INIT → CONNECTING → STREAMING → STALLED → BACKOFF → CONNECTING`.

- Watchdog: if no frame arrives for `stall_timeout_s` (default 10 s), close the capture handle and reopen.
- Exponential backoff with jitter: 1 s up to 60 s.
- On reconnect, close open tracklets for that camera and reset the motion background model.
- GUI shows “No signal” over the last frame; `camera_offline` event only after `offline_notify_after_s` (default 120 s).

### 4.3 Frame sampling defaults

| Sampler | Default | Rationale |
|---|---|---|
| Capture | stream native rate | Must drain the socket to avoid the unbounded-buffer lag |
| Motion | every 2nd frame | MOG2 on 320 px grayscale is cheap |
| Face inference | `analysis_fps = 5` | 5 fps is enough for tracklet aggregation; dlib CNN at ~50 ms on GPU supports this comfortably |
| Display paint | 15 fps grid / 30 fps single view | Independent of inference |

Expose all four in config. On a 3050, a user can raise `analysis_fps` to 10–15 if they accept higher GPU use; the architecture does not change.

---

## 5. dlib face recognition pipeline

### 5.1 Stages

1. **Motion gate.** Run face detection only when motion fires inside a zone (default). Continuous mode is available as an opt-in for users who want it.
2. **Detect.** dlib CNN face detector on the sampled frame, downscaled so the longest side is at most 800 px. Map detections back to full resolution for snapshots.
3. **Track.** Per-camera IoU tracker links detections across sampled frames into **tracklets**. A tracklet is one continuous appearance of one face.
4. **Quality gate.** For each observation, compute face size in pixels, blur (Laplacian variance), and a yaw proxy from dlib’s 68 landmarks. Observations below `min_face_px_embed` (default 64) are tracked but not embedded.
5. **Embed.** dlib ResNet embedder produces a 128-D vector. L2-normalize. Embed only the best K observations per tracklet (default 5).
6. **Match.** Euclidean distance to each enrolled person’s embedding. Person score = minimum distance (or mean of top-3 distances; expose `gallery_score = min | top3_mean`).
7. **Tracklet decision** (§5.3).
8. **Unknown grouping** (§5.4).

### 5.2 Thresholds for dlib

dlib’s ResNet embedding is commonly used with a Euclidean-distance threshold of **0.6** for same-identity decisions. This is the community default and is well understood, but it must be **calibrated against your enrollment set** — dlib does not publish a single universal threshold. The calibration procedure is simple and belongs in the MVP:

- From enrolled photos, compute genuine distances (same person, leave-one-out) and impostor distances (different enrolled people).
- Plot both distributions.
- Choose `known_threshold` for a target false-accept rate (start at 1 in 1,000 observations).
- Store the chosen threshold per `model_id`.

| Parameter | Default | Meaning |
|---|---|---|
| `known_threshold` | 0.6 (calibrate) | Max distance to name a person |
| `unknown_threshold` | 0.7 (calibrate) | Min distance beyond which a face is definitely unknown |
| `margin` | 0.05 | Required gap between best and second-best person |
| `min_votes` | 2 | Agreeing quality observations before naming |
| `uncertain_policy` | `review` | What to do between thresholds: `review`, `unknown`, `ignore` |

The uncertain band between `unknown_threshold` and `known_threshold` is what prevents a poor-quality frame from either misnaming a person or raising a false stranger alarm. Do not collapse it.

### 5.3 Tracklet aggregation

Frigate’s implementation is the right reference: it collects recognition scores across the whole person object’s lifecycle, **weights them by face area**, and assigns a name only when recognition is confident and consistent. The MVP adopts the same idea in a simpler form:

- Weight each observation’s distance by `face_area × quality_score`.
- Tracklet score = weighted mean distance for each enrolled person.
- Apply `known_threshold`, `margin`, and `min_votes` at tracklet end (or when the tracklet is mature).
- If the tracklet ends uncertain, apply `uncertain_policy`.

This is why your InsightFace prototype misclassified known faces as strangers: single-frame decisions with an uncalibrated threshold. Tracklet aggregation plus calibration fixes the decision logic regardless of which embedding model is used.

### 5.4 Unknown grouping (one event per visit, not per frame)

1. A tracklet yields one **visit record**: best K crops, quality-weighted mean embedding, start and end times.
2. Tracklets on the same camera within `unknown_merge_window_s` (default 60 s) whose mean embeddings are within `unknown_merge_threshold` (default 0.6) join one **stranger event**.
3. A brief occlusion gap (up to ~10 s) with a similar embedding re-links instead of creating a second event.
4. One stranger event = one log entry = at most one notification (subject to the notification rate limit).

### 5.5 Why not fine-tune dlib

Fine-tuning the ResNet requires many labeled images per person, a training pipeline, and risks forgetting and over-fitting. It also makes CUDA packaging worse. Pretrained embeddings plus a diverse enrolled gallery is the standard approach for open-set recognition at this scale. **Reject fine-tuning for the MVP.** Adding or removing a photo updates only that person’s rows in the embedding index; a full rebuild re-embeds all photos and is triggered only when the model changes.

---

## 6. Motion detection

- **Algorithm:** MOG2 background subtraction (shadow detection off) on a grayscale frame downscaled to at most 320 px wide. `running_avg` and `frame_diff` are alternatives for very weak hardware.
- **Zones:** user-drawn polygons rasterized once into binary masks. Exclusion polygons mask timestamp overlays and swaying vegetation.
- **Trigger:** changed-pixel ratio ≥ `zone.threshold_pct` (default 2%) **and** largest contour ≥ `min_area_px` (default 150) **and** sustained for `min_duration_frames` (default 3). Motion ends after `cooldown_s` (default 5) without changes.
- **Global-change suppression:** if more than 50% of the frame changes at once (lightning, IR-cut switch), suppress the trigger and reinitialize the background.
- **Pre-roll:** the event snapshot may come from a 2-second ring buffer before the trigger.

Motion detection is the **fallback tier**: users without a CUDA GPU can run motion-only mode and still get events, notifications, and logs.

---

## 7. Database and logging

### 7.1 Schema (SQLite, WAL, foreign keys on)

| Table | Key columns |
|---|---|
| `schema_meta` | `key`, `value` |
| `camera` | `id` (slug), `name`, `created_at` |
| `person` | `id`, `name`, `notes`, `enabled`, `created_at`, `updated_at` |
| `person_image` | `id`, `person_id`, `path`, `sha256`, `quality`, `added_at` |
| `embedding` | `id`, `person_id`, `person_image_id`, `model_id`, `model_version`, `dim`, `vector` |
| `tracklet` | `id`, `camera_id`, `started_at`, `ended_at`, `decision`, `person_id`, `agg_score`, `n_obs` |
| `event` | `id`, `ts_start`, `ts_end`, `camera_id`, `type`, `zone`, `person_id`, `tracklet_id`, `unknown_cluster_id`, `score`, `snapshot_id`, `dedupe_key` |
| `snapshot` | `id`, `path`, `sha256`, `width`, `height`, `created_at` |
| `unknown_cluster` | `id`, `first_seen`, `last_seen`, `n_visits`, `centroid`, `model_id` |
| `notification` | `id`, `event_id`, `channel`, `status`, `reason`, `created_at` |

Indexes: `event(ts_start)`, `event(camera_id, ts_start)`, `event(type, ts_start)`, `event(dedupe_key)`, `tracklet(camera_id, started_at)`, `embedding(person_id, model_id)`.

**Write discipline:** a single DB writer thread consumes a queue. The GUI reads through its own read-only connection. This avoids “database is locked” without requiring multi-process machinery in the MVP.

### 7.2 Two logs

| Log | Storage | Content | Retention |
|---|---|---|---|
| **Event log** | SQLite `event` table | Recognitions, strangers, motion, camera offline | 90 days (configurable) |
| **Developer log** | Rotating JSON-lines file (10 MB × 5) | Lifecycle, reconnects, queue depths, inference ms, exceptions | 14 days |

The developer log must **never** contain camera URLs with passwords, embeddings, or face image data. Add a redaction filter and a test that asserts it.

---

## 8. Configuration

TOML with Pydantic validation. Precedence: defaults → global config → camera override → zone override → runtime toggles (not persisted unless saved).

Core MVP parameters:

| Key | Default | Notes |
|---|---|---|
| `inference.device` | `auto` | `auto`, `cpu`, `cuda:0`; auto-detected at first run |
| `inference.analysis_fps` | 5 | Per camera; raise on a 3050 if desired |
| `face.detector` | `dlib_cnn` | `dlib_cnn`, `dlib_hog` |
| `face.known_threshold` | 0.6 | Calibrated; see §5.2 |
| `face.unknown_threshold` | 0.7 | Calibrated |
| `face.min_face_px` | 48 | Detection |
| `face.min_face_px_embed` | 64 | Embedding |
| `face.best_k` | 5 | Observations embedded per tracklet |
| `face.uncertain_policy` | `review` | `review`, `unknown`, `ignore` |
| `motion.fps` | every 2nd frame | MOG2 on 320 px |
| `motion.threshold_pct` | 2.0 | Per zone |
| `display.grid_fps` | 15 | Independent of inference |
| `notify.desktop_enabled` | true | Tray toast; no external account |
| `notify.stranger_cooldown_s` | 120 | Deduplication window |

Every parameter has a reset-to-default control and an “Advanced” visibility toggle in the UI.

---

## 9. GUI (PySide6, “antislop”)

- **Pages:** Cameras, Live (grid + single view), Events, People, Settings.
- **Startup:** build the window before workers finish loading; lazy-import dlib and model code; show “starting cameras” placeholders. This directly addresses the “lightweight, fast” requirement.
- **Video rendering:** Qt `QImage` from the latest NumPy frame; no CPU-bound scaling beyond a single `QPixmap` conversion. Use `QOpenGLWidget` only if profiling shows the raster path is a bottleneck on the 3050.
- **Overlays:** boxes, names, and track IDs drawn from a small shared structure with a 1-second TTL; if analytics dies, overlays expire and the video keeps playing.
- **No modal dialogs** for common actions. Camera add/edit and zone editing are inline or panel-based.
- **Dark/light theme** follows the OS. No custom skin.

---

## 10. Packaging

- **PyInstaller 6.22.0, `--onedir` only.** Onefile unpacks on every start and triggers antivirus heuristics.
- **Two builds:**
  - **CPU build:** OpenCV, dlib CPU, PySide6, SQLite. No CUDA.
  - **CUDA build:** same core plus `dlib-gpu` and its CUDA/cuDNN runtime dependencies. Add `cudnn64_9.dll`, `cudart64_12.dll`, `cublasLt64_12.dll`, and related DLLs explicitly with `--add-binary` — PyInstaller does not discover them automatically, and the resulting failure mode is “works in dev, CPU-only after packaging”.
- **First-run probe:** detect GPU, CUDA, and cuDNN; if the CUDA build cannot load them, start on CPU with a visible warning and a diagnostics page. Do not silently degrade.
- **`multiprocessing.freeze_support()`** in the entry point, even in the threaded MVP, so the later process-based Phase 2 works without a packaging rewrite.
- **Installer:** Inno Setup; portable zip as the zero-install option. Code-sign both if possible.

---

## 11. First sprint for Opencode (2 weeks)

This is the ordered list Opencode should implement. Do not skip step 3.

1. **Repo skeleton:** `pyproject.toml`, locked dependencies, `src/surveillance/`, tests, CI for Windows CPU build.
2. **Config loader:** Pydantic models, TOML defaults, one example `config.toml`.
3. **Latency regression harness:** burn a running millisecond clock into a test video; capture the displayed frame; compute glass-to-glass latency. Run once with no inference and once with a dummy 150 ms `sleep` in a separate thread. **Pass criterion: p95 latency difference < 50 ms.** This test is the executable form of the core requirement.
4. **Capture thread + display widget:** one camera, latest-frame-wins queue, Qt paint.
5. **SQLite schema + DB writer thread.**
6. **Motion detection on the sub-stream:** zones, MOG2, event emission to SQLite.
7. **dlib pipeline:** detector + embedder, tracklet aggregation, known/unknown/uncertain decision, stranger grouping.
8. **GUI pages:** Cameras, Live, Events, People, Settings.
9. **PyInstaller CPU build**; test on a clean Windows VM without Python.
10. **CUDA build script** using the conda-forge `dlib-gpu` environment; test on the RTX 3050.

**Sprint success criterion:** on the RTX 3050, four 1080p cameras display live video with dlib face recognition enabled, and glass-to-glass p95 latency is within 50 ms of the same setup with recognition disabled. That is the measurable proof that the original lag is fixed.

---

## 12. Roadmap after the MVP

| Phase | Focus | What it adds |
|---|---|---|
| **2** | Process isolation; calibration wizard; Telegram/email with rate limiting; main-stream on-demand view; Linux packages | Reliability at scale, notifications, cross-platform |
| **3** | Recording (event clips); optional go2rtc/WebRTC display; YuNet/SFace and ArcFace plugins; ONNX Runtime path | Feature parity with Frigate’s analytics and live-view options |
| **4** | Long-term unknown clusters; cross-camera re-ID; REST/web UI; PostgreSQL; ONVIF discovery | Multi-user and enterprise scenarios |

The competitive differentiator is not feature count — Frigate and Blue Iris are mature. It is **the guarantee that display never blocks on inference**, in a desktop app that runs offline, ships dlib by default (no model licensing trap), and exposes every performance knob.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| dlib + cuDNN 9 build fragility on Windows | Use conda-forge `dlib-gpu` 20.0.1 `cuda129py312` ; keep a source-build recipe only as fallback; verify `dlib.DLIB_USE_CUDA` at startup |
| dlib CNN too slow on CPU | HOG fallback or motion-only mode; startup warning |
| Threaded MVP later needs process isolation | Design queues and interfaces so the capture and inference workers can be moved to processes without changing call sites; call `freeze_support()` from day one |
| PyInstaller drops CUDA DLLs | Explicit `--add-binary` for `cudnn64_9.dll`, `cudart64_12.dll`, etc. ; CI smoke test that asserts GPU provider loads |
| Threshold miscalibration (your InsightFace experience) | Calibration procedure in §5.2; tracklet aggregation; uncertain band; never decide on one frame |
| Sub-stream too small for faces | Warn in the zone editor with an estimated face-pixel count; allow `analysis_stream = main` |
| Frigate-style aggregation is an inspiration, not a spec | Document the weighting scheme in code; do not claim Frigate compatibility |

---

Opencode can start at §11 step 1 immediately.