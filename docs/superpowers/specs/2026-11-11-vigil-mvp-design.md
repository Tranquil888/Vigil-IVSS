# Vigil MVP: design decisions

**Status:** approved direction, built from `Vigil_new_plan.md`.
**Date:** 2026-11-11.

## Intent

Replace the current tkinter prototype with a desktop surveillance app whose
display path cannot be slowed down by face recognition. The prototype lagged
because capture and inference shared one blocking loop. This rewrite makes the
separation structural, not a frame-skipping trick.

The product is a local, offline app for a small site: a handful of cameras, a
person gallery, a reviewable event log, and a desktop alert. It runs on Windows
with an RTX 3050 and falls back to CPU or motion-only without hiding the fact.

## The invariant

Capture drains continuously. Display reads the newest frame and never waits.
Inference consumes sampled copies asynchronously. Nothing on the display path
calls into dlib, and no display queue grows.

This is enforced by three concrete mechanisms:

1. `LatestFrame` holds one frame. `put` overwrites, never blocks.
2. The inference queue is bounded at 4 and drops its oldest item when full.
3. The GUI timer only reads the latest frame and a TTL-limited overlay store.

The regression harness measures frame age at the display consumer and asserts
that adding a 150 ms inference consumer changes p95 age by less than 50 ms.

## Goals

- Four 1080p cameras display live with face recognition on, without display lag.
- One decision per face visit, not one per frame, with a calibrated threshold band.
- A person can be added, edited, deleted, and given photos without retraining.
- Unknown faces are grouped into one stranger event per visit.
- Events, snapshots, and a developer log are separate and retained separately.
- Every screen has empty, loading, and error states.
- The app starts fast: the window appears before dlib finishes loading.

## Non-goals (MVP)

Recording and NVR, process isolation, envelope encryption and audit logs, a
calibration wizard UI (the math ships, the wizard does not), Telegram or email,
go2rtc or WebRTC display, a plugin SDK, a REST API, PostgreSQL, cross-camera
re-identification, and anti-spoofing. Each is listed in the plan's phase table.

## Anti-goals

- A display loop that waits on any worker for any reason.
- A decision made from a single frame.
- A silent CPU fallback that looks like a working GPU install.
- A notification per frame.
- A GUI that only looks right in the happy path.

## Constraints

| Constraint | Value |
|---|---|
| OS | Windows 11 |
| Reference GPU | RTX 3050, compute capability 8.6, CUDA 12.9, cuDNN 9 |
| Release runtime | CPython 3.12, PySide6 6.11, PyInstaller 6.22 `--onedir` |
| Local verification runtime | conda env `dlib-cuda`, CPython 3.9.23, dlib 20.0.0 with CUDA, PySide6 6.10.3 |
| Source compatibility | 3.9 and 3.12. No `match`, no PEP 604 unions at runtime. |
| Display | PySide6 widgets only. No QML, no WebEngine. |
| Storage | SQLite in WAL mode, one writer thread, separate read connection |
| Config | TOML read with `tomllib` (3.11+) or `tomli`, written with `tomlkit` |

The 3.9 target is a verification convenience. Release wheels and packaging
target 3.12. Nothing in the code may depend on 3.9-only behavior.

## Visual identity: dark operator console

Chosen because the app runs in dim rooms next to bright monitors, and because
video is the content. Chrome recedes; the picture is the brightest thing on
screen. This is not "dark because tech", it is the lighting condition of the
job.

**Dial: ENERGY 1 / RHYTHM 2 / MOTION 1.**

- ENERGY 1: quiet surfaces, one accent, no decorative gradients or glow.
- RHYTHM 2: grid and single view differ in density; pages share one shell.
- MOTION 1: hover, focus, and state transitions only. No entrance animations.

### Palette

| Token | Value | Use |
|---|---|---|
| `bg` | `#12161A` | Window background |
| `panel` | `#1A2026` | Panels, table rows, toolbars |
| `panel_alt` | `#202832` | Hover, selected row base |
| `line` | `#2A323A` | Borders and dividers |
| `text` | `#E6EDF3` | Primary text |
| `muted` | `#93A1AE` | Secondary text, timestamps |
| `accent` | `#2FB6A8` | Live state, focus ring, primary action |
| `warn` | `#E0A458` | Uncertain recognition, offline warning |
| `danger` | `#E0605A` | Errors, unknown stranger marker |

Contrast: `text` on `bg` is 14.6:1, `muted` on `panel` is 6.4:1, `accent` on
`bg` is 7.3:1, `warn` on `bg` is 9.1:1, `danger` on `bg` is 5.4:1. All pass
WCAG AA for normal text.

### Type

System UI font: Segoe UI Variable, falling back to Segoe UI. Reason: native
Windows rendering at 11 to 13 px, no bundled font, no license surface.

Timestamps and IDs use Cascadia Mono, falling back to Consolas. Reason: the
event table and diagnostics are columnar, and fixed-width digits stop rows
from shimmering as they update.

No uppercase tracked labels. Section headings are sentence case at 13 px
semibold. The window title uses the same family as the body.

### Composition

A left rail with five destinations: Cameras, Live, Events, People, Settings.
It is a navigation element, so it uses `QToolButton` with a text label under a
single glyph drawn from the app's own small icon set (camera, grid, list,
person, sliders). The rail is 88 px wide, icon 20 px, label 11 px. The content
area is the focal point on every screen.

Live grid tiles have a 16:9 slot, a 1 px `line` border, and a status strip
that is hidden unless the camera is not streaming. The single view drops the
grid and shows the largest possible picture with a compact overlay bar.

Empty states are written, not illustrated: one sentence saying what will
appear here and the action that makes it appear. No skeleton shimmer.

### Theme

Dark is the default because of the lighting condition above. The Settings page
offers System, Dark, Light. Light is a warm grey paper palette, not an
inverted dark theme: `bg #F4F5F3`, `panel #FFFFFF`, `text #1B232B`,
`accent #0F7F74`. Both themes are exercised in the GUI smoke test.

## Architecture decisions

### Threads, not processes

The MVP uses threads for capture, motion, inference, database writes, and
notifications. Workers communicate through queues and plain dataclasses so the
same interfaces can move behind `multiprocessing` in phase 2 without changing
call sites. `multiprocessing.freeze_support()` runs from day one.

### Capture is per camera, and cheap

One capture thread per camera reads at stream rate. It does no resizing, no
detection, no database work. It publishes:

- every frame to `LatestFrame` for display,
- every Nth frame to a bounded motion queue,
- time-sampled frames to a bounded inference queue when motion is active.

### Inference is one thread, always

One inference thread serves all cameras and processes frames in arrival order.
It never touches Qt. It emits observations to the identity tracker, which
emits event records to the bus. The tracker is owned by the inference thread,
so no lock is needed on tracklet state.

### Data model

SQLite tables follow the plan: `schema_meta`, `camera`, `person`,
`person_image`, `embedding`, `tracklet`, `event`, `snapshot`,
`unknown_cluster`, `notification`. Embeddings are stored as a 128-float
little-endian blob plus `dim`. The writer thread is the only writer.

A `dedupe_key` on `event` (camera, type, related id, time bucket) makes the
writer idempotent, so a retry cannot duplicate an event.

### Face backend

`DlibBackend` is the only module that imports dlib. It probes
`DLIB_USE_CUDA` and `cuda.get_num_devices()` at startup and reports a
`BackendStatus`. Missing CNN model file, missing CUDA, or a failed import
degrade to HOG or motion-only with a visible warning, never silently.

Model files live in `models/` and are fetched by `scripts/fetch_models.py`.
The app does not download models at runtime.

### Recognition decision

Per observation: distances to all gallery embeddings, per person score is min
or top-3 mean, choose best and runner-up. An observation votes known when the
best distance is within `known_threshold` and the margin to the runner-up is
at least `margin`; votes unknown when beyond `unknown_threshold`; otherwise it
is uncertain. The tracklet decision uses votes weighted by
`face_area * quality` and requires `min_votes`. Uncertain tracklets follow the
policy: `review`, `unknown`, or `ignore`.

### Motion

MOG2 on a grayscale frame at most 320 px wide, with polygon zones rasterized
once. Trigger needs changed ratio, contour area, and sustained frames. A global
change over `suppress_global_pct` resets the background instead of firing.

## Repository layout

```
src/vigil/
  app.py                 entry point, QApplication, freeze_support
  config/                Pydantic models, TOML load/save
  core/                  queues, bus, dataclasses, clock
  video/                 capture thread, camera state machine, manager
  analysis/              motion, zones, tracker, quality, dlib backend,
                         matcher, tracklet decisions, unknown grouping, pipeline
  storage/               schema, writer thread, reader, snapshots
  notify/                tray notifier
  telemetry/             developer log setup and redaction
  gui/                   shell, theme, pages, widgets
tests/                   unit and integration tests
tools/                   latency harness and model fetch
packaging/               PyInstaller spec and build scripts
legacy/                  the previous tkinter app, archived untouched
data/                    user data, unchanged and untracked
```

## Builder's calls

These are mine, not the user's, and are easy to change:

- Light theme is warm grey paper rather than a cooled inversion.
- The event table uses Cascadia Mono only for the timestamp column.
- The stranger grouper keeps clusters in memory and persists summaries.
- The latency harness measures display-queue frame age rather than filming a
  screen, and documents that limit.
