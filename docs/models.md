# Models

Vigil uses three dlib model files. They are data files, not Python packages,
and they are never downloaded at run time.

| File | Role | Minimum size checked |
|---|---|---|
| `mmod_human_face_detector.dat` | CNN face detector | 7,000,000 bytes |
| `shape_predictor_68_face_landmarks.dat` | 68 point landmarks, needed for alignment | 95,000,000 bytes |
| `dlib_face_recognition_resnet_model_v1.dat` | ResNet, produces the 128-d embedding | 20,000,000 bytes |

The size check is a floor, not an exact match. It catches a truncated
download or an HTML error page saved under a `.dat` name. The upstream files
can be regenerated without breaking the check.

## Fetch them

```powershell
python scripts\fetch_models.py --dest "$env:LOCALAPPDATA\Vigil\models"
```

The script downloads each `.bz2` from dlib.net, decompresses it to a
temporary file, checks the size, and moves it into place. It deletes the
archive unless you pass `--keep-archive`. It refuses to overwrite existing
files unless you pass `--force`. If the Python TLS stack cannot reach dlib.net,
the script retries with `curl` when it is on `PATH`.

```powershell
python scripts\fetch_models.py --dest D:\models --force
```

A `models` folder in the repository root is ignored by git. It is a convenient
local target when you run the app from a checkout:

```powershell
python scripts\fetch_models.py --dest models
```

The canonical URLs are kept in `scripts/fetch_models.py`:

- `https://dlib.net/files/mmod_human_face_detector.dat.bz2`
- `https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2`
- `https://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2`

## Where Vigil looks

`face.models_dir` in the config sets the directory. When it is empty, Vigil
uses `<data dir>/models`, which is `%LOCALAPPDATA%\Vigil\models` unless you
set `VIGIL_DATA_DIR` or `storage.data_dir`.

An empty `face.models_dir` with a custom data directory follows the data
directory. A relative path in `face.models_dir` is resolved against the
process working directory, not the data directory, so prefer an absolute
path when the two differ.

## What happens when a file is missing

Vigil probes the backend at startup and on settings refresh. It degrades
instead of crashing:

| Situation | Result |
|---|---|
| `face.detector = "none"` | Face recognition is off. Motion events still work. |
| dlib not installed | Backend unavailable, motion events still work. The status says dlib is missing. |
| No CUDA device | Detection uses HOG. Embeddings still work on the CPU when the other two files are present. The status says why. |
| CUDA present, cuDNN missing | Detection uses HOG. The status says cuDNN was not found. |
| CNN file missing | Detection falls back to the HOG detector. The status says HOG is in use. |
| Landmark file missing | Detection works, embedding is disabled. The status says why. |
| ResNet file missing | Detection works, embedding is disabled. The status says why. |
| All files present | Detection and recognition run. The status reports CPU or GPU. |

Recognition requires both the landmark predictor and the ResNet model. Without
them the People page still stores names and photos. An imported photo is saved
to the person folder and shown in the list even when no embedding could be
computed. When the models are installed later, open People and press
Rebuild embeddings to fill in the missing vectors without importing the photos
again.

## Embeddings

Each imported photo contributes one normalized 128-d vector. Vectors are
stored in the `embedding` table with `model_id = "dlib_resnet_v1"` and
`model_version = "1"`. The gallery is rebuilt from enabled people only, in
memory, and is swapped atomically.

If the model version changes, old vectors stay in the database under the old
`model_id`. The People page Rebuild embeddings button embeds every stored photo
that has no vector for the current model. It reports how many were added,
already indexed, and failed, so a partially installed model set is visible
instead of silent.

## CUDA

A dlib wheel from PyPI is usually a CPU build. A CUDA build reports
`dlib.DLIB_USE_CUDA` and at least one device through
`dlib.cuda.get_num_devices()`. The backend status shows `cuda` when both are
true.

dlib exposes no call that reports whether cuDNN is present, so Vigil probes the
usual library names (`cudnn64_9.dll`, `cudnn_ops64_9.dll`, and the version 8
and Linux equivalents) with `ctypes.CDLL`. The result is best effort: a missing
library forces the detector to HOG, while a library that loads but fails later
shows up as an inference error in the Diagnostics report.

`inference.device` accepts `auto`, `cpu`, `cuda`, and `cuda:N`, and the value
is validated at startup. The current dlib backend does not switch the
inference device at run time: dlib uses CUDA when it was compiled with CUDA
and a device is visible, otherwise it runs on the CPU. Treat the field as a
declaration of intent, not a runtime switch. The Settings page reports what
dlib actually selected.

CUDA builds also need the matching runtime DLLs at run time. `build_cuda.ps1`
copies `cudnn64_9.dll`, `cudart64_12.dll`, and `cublasLt64_12.dll` when they
are present and warns when one is missing. A CUDA 11 installation will not
provide the `_12` names, so check the exact versions your dlib build expects.
The application still starts and falls back to CPU when the DLLs are absent,
provided dlib itself can load.

## License

The files are downloaded from dlib.net, not redistributed with Vigil. Check
dlib.net for the terms that apply to each model file before commercial use.
