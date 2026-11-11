# SDD ledger — plan: docs/superpowers/plans/2026-11-11-vigil-mvp.md

Spec: docs/superpowers/specs/2026-11-11-vigil-mvp-design.md
Branch: feat/3-rewrite-vigil (in-place rewrite, chosen by user)
Runtime for verification: conda env dlib-cuda via dlib-env\Scripts\python.exe (CPython 3.9.23, dlib 20.0.0 CUDA)

## Pre-flight

- Task 5 produces `Frame`, Task 8 consumes it; Task 2 defines it. Consistent.
- Task 2 produces `EventRecord`, Task 3 writes it, Task 8 emits it. Fields listed once in Task 2 and matched in Task 3. Consistent.
- Task 7 produces `OverlayStore` in Task 8, consumed by Task 9. The plan puts OverlayStore in Task 8 and the GUI consumes it in Task 9. Consistent.
- Task 1 produces `VigilConfig`, consumed by Tasks 5, 6, 7, 8, 9. Consistent.

## Task log

- Task 0: complete (2b2f5a6). Package skeleton, pyproject, CI, tests import the `vigil` package.
- Task 1: complete (226d46d). Strict Pydantic config, TOML load/save, paths, example config.
- Task 2: complete (37a033c). `LatestFrame`, `DropOldestQueue`, `EventBus`, records, clock.
- Task 3: complete (2173979). SQLite schema, database, DB writer thread, reader, embeddings, snapshots.
- Task 4: complete (e25b7de). Redaction, rotating JSON developer log, retention pruning.
- Task 5: complete (e783f44). Sources, capture supervisor, backoff state machine, camera manager.
- Task 6: complete (3f0a1e8). Polygon zones, MOG2 motion worker, per-camera motion gating and events.
- Task 7: complete (82f9e20). Backend probe, quality gate, IoU tracker, gallery, decisions, stranger grouping.
- Task 8: complete. Inference pipeline, overlay store, notifier, app context, process entry point.
  - Ruling: the pipeline embeds each quality-passing observation immediately and keeps the best `best_k` votes by weight, instead of storing crops and embedding only when the tracklet closes. One weighted decision per tracklet is unchanged, the inference queue never holds images for longer than one frame, and memory stays bounded.
  - Ruling: test 5 in `tests/analysis/test_pipeline.py` now feeds two frames before `stop()`. A single observed vote cannot satisfy the documented `min_votes` rule without weakening the tracklet decision.

