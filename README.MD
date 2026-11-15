# Vigil

Vigil watches a few cameras on one machine, recognizes people you have
enrolled, logs what happened, and keeps the live view responsive while it
does the recognition. Everything runs locally. There is no account, no
cloud, and no network call after you download the model files.

Version 2.0 is a rewrite of an earlier tkinter and `face_recognition`
prototype. The new application is PySide6, dlib, OpenCV, and SQLite, packaged
as a single process with background workers.

## Screenshots

The feeds are four camera sample clips played from disk. The resident is
enrolled from the indoor clip; the delivery visitor at the front door is not
enrolled, so the console reports an unknown face. The person names shown are
demo labels, not real identities.

![Live page with four cameras and recognition overlays](docs/images/live-grid.jpg)

Four cameras on the Live page in a 2x2 grid. Each tile paints from its own
last-frame slot, so the display keeps its rate while the inference worker names
the people in view. The resident is known and the visitor at the front door is
unknown.

![Events page](docs/images/events.png)

The Events page keeps one row per visit with camera, type, person, and score.
Known faces, uncertain faces, strangers, and motion all land in the same log.

![Settings page](docs/images/settings.png)

The Settings page edits the TOML file in place. Camera, motion, zone, and
inference changes apply without a restart.

## What 2.0 does

- Live view of every enabled camera in a grid or a single-camera view.
- Motion gating: recognition runs only when a camera sees movement, so an
  idle camera costs almost nothing.
- Face detection with dlib CNN (or HOG when the CNN model is missing) and
  a ResNet embedding model.
- Tracklet decisions: a person is reported only after several observations
  agree, not after one lucky frame.
- Event log with camera, type, person, zone, score, and snapshot.
- People gallery with photo import that works even before the models are
  installed, enable/disable, and an embedding rebuild that fills missing
  vectors and takes effect without a restart.
- Grouping of repeated unknown visitors into clusters, with one event row per
  visit.
- Desktop tray notifications for known people and strangers, with a
  cooldown.
- TOML configuration through `%APPDATA%\Vigil\config.toml` and the
  Settings page. Camera, motion, zone, and inference edits apply without an
  application restart.
- A Diagnostics page with backend state, model presence, queue depth, thread
  liveness, database counts, and a config reload button.
- A developer JSON log with credentials, embeddings, and image bytes
  redacted.

Recording, NVR playback, remote access, user accounts, Telegram and email
delivery, WebRTC, cross-camera re-identification, anti-spoofing, and
encryption at rest are out of scope for 2.0.

## The latency promise

The display path never waits for inference. Each camera publishes into a
one-slot last-frame holder. The video tile reads that slot and paints. A
separate bounded queue feeds sampled copies to a single inference worker,
and that queue drops its oldest item instead of growing.

Measured on this machine at 30 fps with a 15 ms display poll:

| Inference delay | p50 | p95 | max |
|---|---|---|---|
| 0 ms | 16.0 ms | 32.0 ms | 47.0 ms |
| 150 ms | 16.0 ms | 46.0 ms | 62.0 ms |

The p95 difference is 14 ms. The regression test asserts p95 under 50 ms
and a difference under 50 ms with a 150 ms inference delay. A second,
burned-clock end-to-end test plays a real clip through the capture thread and
includes video decode; its p95 difference is 1.0 ms. Run the synthetic
harness with `python tools\latency_harness.py --seconds 10 --with-inference-delay 150`.
Details and caveats are in `docs/latency.md` and `docs/e2e-test-plan.md`.

## Requirements

- Windows 11 (the target), and the code should run on Linux, though the build
  scripts are PowerShell.
- CPython 3.9 or 3.12. The code supports both; 3.9 is what the bundled
  verification environment uses.
- Enough memory for the models you load. CNN face detection is the memory
  hungry part when several cameras use it.
- A webcam, an RTSP camera, or a video file. USB cameras appear as source
  `"0"`, `"1"`, and so on.
- Optional: an NVIDIA GPU and a dlib build compiled with CUDA.

## Install

The quick path on Windows:

```powershell
.\scripts\setup_env.ps1
```

The script creates `.venv`, installs the project with development extras,
and downloads the model files to `%LOCALAPPDATA%\Vigil\models`. Skip the
download with `-SkipModels` if you manage models yourself.

Manual path:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\fetch_models.py --dest "$env:LOCALAPPDATA\Vigil\models"
```

`dlib` is not a pip dependency because wheel availability varies. Install
it in the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install dlib
```

For CUDA, use a conda environment where dlib is built with CUDA enabled, then
install the project into that environment. Vigil reports `cuda` in the
backend status only when dlib was built with CUDA and `dlib.cuda.get_num_devices()`
returns at least one device.

Start the application:

```powershell
.\.venv\Scripts\python.exe -m vigil.app
```

The installed console script `vigil` runs the same entry point.

## First run

1. Start Vigil. With no config file it uses the shipped defaults and shows
   an empty camera list.
2. Check the status bar at the bottom of the window. It reports the face
   backend and whether it runs on CPU or GPU. If the models are missing, the
   status says so and recognition is disabled; motion events still work. The
   Diagnostics page has the same information in full, plus queue depth, thread
   liveness, and database counts.
3. Open Cameras and add your first camera.
4. Open People and add someone, then import one or more photos of them.
5. Watch the Live page. A recognized face appears with a name; a stranger
   appears as `Unknown`.
6. Review the Events page.

Configuration and data live outside the repository:

| Path | Contents |
|---|---|
| `%APPDATA%\Vigil\config.toml` | configuration written by the Settings page |
| `%LOCALAPPDATA%\Vigil\vigil.db` | SQLite database (events, people, embeddings, clusters) |
| `%LOCALAPPDATA%\Vigil\logs\` | rotating developer log |
| `%LOCALAPPDATA%\Vigil\snapshots\` | event snapshots |
| `%LOCALAPPDATA%\Vigil\people\` | imported person photos |
| `%LOCALAPPDATA%\Vigil\models\` | the three dlib model files |

Set `VIGIL_CONFIG` to use a different config file and `VIGIL_DATA_DIR` to
move the data directory. `storage.data_dir` in the config does the same for
data.

`app.start_minimized = true` keeps the window in the tray for background
launches such as autostart. A terminal launch always opens the main window,
and the window opens when no tray icon is available, so the app cannot start
hidden with no way back.

## Cameras

The Cameras page edits `[[cameras]]` entries. A camera needs an id (lowercase
letters, digits, `_`, `-`), a display name, and a source:

- `"0"` for the first local camera.
- `"rtsp://user:password@192.168.1.10:554/stream2"` for RTSP.
- A file path for a recorded clip.

A source may list several video files, one per line. Files play in order, the
playlist loops, and frames are paced to the file's frame rate, so a folder of
clips behaves like a camera that never goes offline:

```toml
[[cameras]]
id = "door"
name = "Door clips"
source = '''
C:\clips\door-morning.mp4
C:\clips\door-evening.mp4
'''
```

Camera, motion, zone, and inference changes apply when you save. A camera or
motion change rebuilds the capture and motion workers, and the live tiles come
back on the new cameras. An analysis fps or queue size change is applied in
place. A detector, device, or model directory change reloads the face backend.
If you edit `config.toml` outside the app, use Reload config on the Diagnostics
page. Adding a person, importing a photo, or disabling a person takes effect
immediately.

The camera secret store keeps a password out of `config.toml`. Saving a source
such as `rtsp://user:password@host/stream` encrypts the full URL into
`secrets.json` in the data directory and the config keeps `source = "vault"`.
On Windows the store uses DPAPI, so only the same Windows account can read it.
On other platforms it uses Fernet with a `secrets.key` file. The app resolves
the entry in memory when capture starts. Removing a camera also removes its
secret.

Each camera can override the global motion section with `[cameras.motion]`
and define polygon zones:

```toml
[[cameras.zones]]
name = "walkway"
points = [[0.30, 0.35], [0.80, 0.35], [0.85, 0.90], [0.25, 0.90]]
threshold_pct = 2.0
exclude = false
```

Points are normalized to `0..1` so the zone survives a resolution change.
An `exclude = true` zone subtracts a region, for example a timestamp overlay
or a tree that moves in the wind.

Recognition is gated by motion by default. If a camera has no usable motion
signal, set `motion.enabled = false` for that camera and rely on the
analysis frame rate.

## People and recognition

Open People, add a person, and import photos. A photo is copied into the
person folder even when the model files are not installed yet. If the backend
can embed it, the embedding is written immediately and the gallery is rebuilt
from enabled people only. If it cannot, the photo stays on file and a later
Rebuild embeddings fills in the missing vector. Disabling a person removes them
from matching without deleting their data.

The defaults are a starting point, not a guarantee:

- `known_threshold = 0.28`: maximum distance for a known match.
- `unknown_threshold = 0.38`: minimum distance for a stranger. Distances
  between the two thresholds land in the uncertain band.
- `margin = 0.05`: the best person must beat the runner-up by this much.
- `min_votes = 2`: at least this many observations must agree before a
  tracklet is reported as a known person.
- `best_k = 5`: the number of highest-quality observations kept per
  tracklet.

The thresholds were calibrated on 25-person ChokePoint face sets and a local
photo set, not copied from a library default. The old 0.6 default accepted
every measured impostor. Read `docs/calibration.md` before trusting these
numbers with your camera, lighting, and photo set: a large gallery may need a
lower `known_threshold`, and a small high-quality gallery can afford a higher
one.

## Models

The three files and their roles are described in `docs/models.md`. Fetch
them once:

```powershell
python scripts\fetch_models.py --dest "$env:LOCALAPPDATA\Vigil\models"
```

The script checks decompressed sizes and refuses to overwrite existing files
without `--force`. It retries with `curl` when the Python TLS stack cannot reach
dlib.net. Vigil never downloads models at run time. If a file is missing, the
backend degrades in a visible way instead of failing at the first frame. A
`models` folder in the repository root is ignored by git and is a convenient
target when running from a checkout.

The Diagnostics page shows which files are present, whether CUDA and cuDNN are
available, and which detector is actually in use. A CNN request falls back to
HOG when CUDA, cuDNN, or the CNN file is missing, and the page says why.

## Configuration

The Settings page covers every field that has a GUI control and writes the
TOML file back without dropping comments outside camera arrays. Advanced
fields are hidden behind the Advanced checkbox.

`config.example.toml` documents the shipped defaults. The important sections:

- `[inference]`: device selection, analysis fps, queue size, maximum frame
  age.
- `[face]`: detector, thresholds, vote rules, tracking, unknown grouping.
- `[motion]`: MOG2 settings, sampling stride, zone thresholds, cooldown.
- `[display]`: grid and single-view refresh rates, overlay lifetime.
- `[notify]`: desktop toasts and stranger cooldown.
- `[capture]`: open timeout, stall timeout, exponential backoff.
- `[storage]`: data directory, retention, snapshot quality.

## Diagnostics

The Diagnostics page is a live, read-only report. It refreshes every 2.5
seconds while it is open and shows:

- Paths for the database, models, people photos, and snapshots.
- Which of the three model files are present.
- Detector, CUDA, cuDNN, embedding availability, and the backend reason.
- Event, notification, person, snapshot, and unknown cluster counts.
- Thread liveness, per-camera state, queue depth, and drops.

Copy report puts the same text on the clipboard for a support note. Reload
config re-reads the TOML file, applies it to the workers, and refreshes the
Settings and Cameras editors. Use it after editing the file outside the app.

The same report is available without the GUI:

```powershell
.\.venv\Scripts\python.exe scripts\graybox_probe.py --json
.\.venv\Scripts\python.exe scripts\graybox_probe.py --run 30 --fake-camera
```

The second form starts the real workers against a synthetic camera, so the
queue and thread numbers are live. `docs/graybox-test-plan.md` lists the pass
criteria.

## Build a bundle

```powershell
.\scripts\build_cpu.ps1
.\scripts\build_cuda.ps1
```

Both produce `dist\Vigil\Vigil.exe` as a one-directory bundle. The CUDA
script additionally copies CUDA runtime DLLs when it finds them and warns
when one is missing. Models are not bundled. See `docs/packaging.md` for the
build details and the Qt/ICU note.

Release artifacts:

```powershell
.\scripts\build_portable.ps1 -Version 2.0
.\scripts\build_installer.ps1 -Version 2.0
.\scripts\release_check.ps1 -ModelsDir "$env:LOCALAPPDATA\Vigil\models"
```

The portable script wraps the whole `dist\Vigil` folder in
`dist\Vigil-portable-2.0.zip`. The installer script needs Inno Setup 6 (one
`winget install JRSoftware.InnoSetup`) and writes
`dist\installer\Vigil-2.0-setup.exe`. Both write a `.sha256` file. The release
check starts the frozen app in an isolated data directory, fails on a fatal
startup error or an `app.unhandled` log line, and, with `-ModelsDir`, confirms
that the bundle selected the CNN backend on CUDA.

## UI

The operator console follows `docs/DESIGN.md`: grayscale surfaces, one green
accent for active states and primary actions, red for alerts, square corners,
and both a dark and a light scheme. Button positions and page logic are
unchanged; the theme is a stylesheet plus square monochrome icons.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers config, queues, storage, capture backoff, motion zones,
tracking, decisions, unknown grouping, the pipeline, the notifier, the GUI
pages, live config apply, and the display latency invariant. GUI tests run with
`QT_QPA_PLATFORM=offscreen`.

The CNN and ResNet files are checked only when they are present:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\analysis\test_models.py -q -m models
```

Recognition quality against a folder-per-person dataset:

```powershell
.\.venv\Scripts\python.exe scripts\eval_recognition.py --dataset data\dataset `
    --models models --limit-per-person 12 --gallery-score min --require-cnn
```

The ChokePoint cropped-face tars can be turned into a gallery and looping test
videos without extracting the archives by hand:

```powershell
.\.venv\Scripts\python.exe scripts\build_chokepoint.py `
    --archive test-dataset\P1E.tar
.\.venv\Scripts\python.exe scripts\eval_recognition.py `
    --dataset data\chokepoint\faces --models models --limit-per-person 12 `
    --gallery-score min --detector dlib_cnn --require-cnn --json
```

Four file-backed cameras, a slow inference consumer, and a display latency
report:

```powershell
.\.venv\Scripts\python.exe tools\video_latency_probe.py `
    --video-dir data\chokepoint\videos --cameras 4 --seconds 15 `
    --inference-delay-ms 150 --json
```

A live gray-box report from a synthetic camera:

```powershell
.\.venv\Scripts\python.exe scripts\graybox_probe.py --run 30 --fake-camera
```

End-to-end tests live in `tests/e2e`. They use a synthetic burned-clock video,
real threads, and a real SQLite file, and need no camera or GPU:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\e2e -q -m e2e
```

The automated coverage, the gray-box checks, and the manual hardware matrix are
in `docs/e2e-test-plan.md` and `docs/graybox-test-plan.md`.

Source layout:

```
src/vigil/
  analysis/   backend, quality gate, tracker, gallery, decisions, pipeline
  config/     Pydantic models, TOML load and save
  core/       queues, records, event bus, composition root
  gui/        PySide6 shell, pages, widgets, theme, tray
  notify/     desktop notifier thread
  storage/    schema, writer, reader, embeddings, people, snapshots
  telemetry/  redaction, rotating JSON log
  video/      sources, capture supervisor, camera manager
  diagnostics.py  shared runtime report for the page and the probe
tools/        latency harness
scripts/      environment, model fetch, gray-box probe, recognition eval, build
packaging/    PyInstaller spec and entry point
```

`docs/architecture.md` explains the thread model and the queues.
`docs/calibration.md` explains threshold selection.
`docs/models.md` explains the three model files.
`docs/latency.md` explains the display measurement.
`docs/e2e-test-plan.md` explains the end-to-end suite and the manual gates.
`docs/graybox-test-plan.md` explains the queue, thread, database, backend, live
reload, and dataset checks.

## Troubleshooting

**The backend says recognition is disabled.** The shape predictor and ResNet
files are missing. Run the fetch script and check `face.models_dir`. Detection
can still work through HOG, but there is nothing to match against. Photos
imported before the fix are still on disk; open People and press Rebuild
embeddings to fill in their vectors.

**The status says HOG when I asked for the CNN detector.** The CNN detector
needs CUDA, cuDNN, and the CNN model file. The Diagnostics page names whichever
one is missing. On a CPU-only machine HOG is the intended fallback.

**Qt fails with `0xc0000139` at startup in a conda environment.** A conda
`icuuc.dll` is shadowing a Qt build that needs its own ICU. Install
PySide6-Essentials 6.9.3 in that environment or use a venv without conda
DLLs on the search path. The frozen bundle filters unversioned conda ICU
DLLs for the same reason.

**A camera never connects.** The supervisor retries with exponential backoff
and publishes an offline event after `capture.offline_notify_after_s`. Check
the source string, the password in the URL, and whether another process holds
the camera.

**The live view stutters but events keep arriving.** Check `display.grid_fps`
and the number of visible tiles. A hidden grid page skips its tile timers.
The inference worker is not in the display path, so model speed is not the
cause.

## License

MIT. The repository does not include a LICENSE file yet. The dlib model
files are downloaded from dlib.net and are not redistributed here; check
dlib.net for the terms that apply to each file.
