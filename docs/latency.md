# Display latency

Vigil promises that the picture on screen never waits for face recognition.
The camera thread publishes each frame into a one-slot `LatestFrame`; the
display timer reads that slot and never blocks. Inference receives sampled
copies through a separate bounded queue that drops its oldest item. A 150 ms
model therefore adds no queue depth to the display.

## What the harness measures

Frame age is the time between `Frame.captured_at` and the moment the display
consumer reads the newest frame, in milliseconds. It is not end-to-end
capture latency: USB transfer and camera exposure happen before a `Frame`
exists. The harness isolates the part Vigil controls.

`tools/latency_harness.py` offers two modes over the real `LatestFrame` and
`DropOldestQueue` classes:

- Real time (default): a producer thread publishes at the requested fps, a
  dummy inference consumer sleeps for the requested delay, and the calling
  thread polls the display slot every `--display-interval-ms`.
- Simulated (`--simulated`): the same calls are advanced on a virtual clock
  in event order. No sleeping, no scheduling noise, so the regression tests
  are deterministic.

Percentiles use linear interpolation over the sorted samples. `n` is the
number of display polls, not the number of frames. At 30 fps with a 15 ms
poll over 10 s, `n` is 666 or 667 and exactly 300 frames are produced.

## Running it

```powershell
python tools\latency_harness.py --seconds 10
python tools\latency_harness.py --seconds 10 --with-inference-delay 150
python tools\latency_harness.py --seconds 10 --with-inference-delay 150 --max-p95 50
```

`--max-p95` returns exit code 1 when the budget is exceeded, so a machine
check can run it without parsing the output. `--json` prints one object.

## Recorded numbers

Measured on Windows 11, CPython 3.9.23, 30 fps, 15 ms display poll, 10 s per
run, no GPU work in the harness:

| Mode | Inference delay | p50 | p95 | p99 | max | n |
|------|-----------------|-----|-----|-----|-----|---|
| Real time | 0 ms | 16.0 ms | 32.0 ms | 47.0 ms | 47.0 ms | 666 |
| Real time | 150 ms | 16.0 ms | 46.0 ms | 47.0 ms | 62.0 ms | 666 |
| Simulated | 0 ms | 15.0 ms | 30.0 ms | 31.7 ms | 31.7 ms | 667 |
| Simulated | 150 ms | 15.0 ms | 30.0 ms | 31.7 ms | 31.7 ms | 667 |

The p95 delta between the two real-time runs is 14 ms, below the 50 ms
budget. Real-time values cluster on multiples of about 15.6 ms because that
is the Windows timer granularity on this machine; the 62 ms maximum is one
late scheduler tick, not a queue buildup. The simulated run has no timer and
shows the structural ceiling: one poll interval plus one frame interval.

The harness uses a synthetic producer rather than a video file. A file adds
decode jitter that has nothing to do with the invariant under test, and the
display consumer cannot tell a decoded frame from a synthetic one. Decode
cost belongs to the capture benchmark, not this one.

## Regression tests

`tests/test_latency_invariant.py` runs the simulated path at 300 frames and
asserts `p95 < 50 ms`, that the percentiles are ordered, and that a 150 ms
inference delay changes p95 by less than 50 ms. A short real-time run checks
that the threaded path produces samples. These tests fail if someone puts the
display behind the inference queue, holds a lock across a model call, or
replaces the last-frame slot with a growing queue.

## What breaks the promise

- Reading frames from the inference queue instead of the display slot.
- Calling detection or embedding from the Qt thread.
- Shrinking the display poll far below the camera interval: age cannot drop
  below the frame interval, so extra polls only cost CPU.
- Raising `display.grid_fps` without checking that tiles stay hidden when the
  grid page is not visible.
