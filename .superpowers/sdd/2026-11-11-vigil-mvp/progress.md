# SDD ledger — plan: docs/superpowers/plans/2026-11-11-vigil-mvp.md

Spec: docs/superpowers/specs/2026-11-11-vigil-mvp-design.md
Branch: feat/3-rewrite-vigil (in-place rewrite, chosen by user)
Runtime for verification: conda env dlib-cuda via dlib-env\Scripts\python.exe (CPython 3.9.23, dlib 20.0.0 CUDA)

## Pre-flight

- Task 5 produces `Frame`, Task 8 consumes it; Task 2 defines it. Consistent.
- Task 2 produces `EventRecord`, Task 3 writes it, Task 8 emits it. Fields listed once in Task 2 and matched in Task 3. Consistent.
- Task 7 produces `OverlayStore` in Task 8, consumed by Task 9. The plan puts OverlayStore in Task 8 and the GUI consumes it in Task 9. Consistent.
- Task 1 produces `VigilConfig`, consumed by Tasks 5, 6, 7, 8, 9. Consistent.
