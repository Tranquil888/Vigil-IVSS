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
files unless you pass `--force`.

```powershell
python scripts\fetch_models.py --dest D:\models --force
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
| CNN file missing | Detection falls back to the HOG detector. The status says HOG is in use. |
| Landmark file missing | Detection works, embedding is disabled. The status says why. |
| ResNet file missing | Detection works, embedding is disabled. The status says why. |
| All files present | Detection and recognition run. The status reports CPU or GPU. |

Recognition requires both the landmark predictor and the ResNet model. Without
them the People page still stores names and photos, but importing a photo
returns a message that the recognition model is unavailable, and no new
embedding is written.

## Embeddings

Each imported photo contributes one normalized 128-d vector. Vectors are
stored in the `embedding` table with `model_id = "dlib_resnet_v1"` and
`model_version = "1"`. The gallery is rebuilt from enabled people only, in
memory, and is swapped atomically.

If the model version changes, old vectors stay in the database under the old
`model_id`. They do not match anything until you delete and re-import the
photos, or provide a migration that recomputes them. There is no automatic
re-embedding in 2.0.

## CUDA

A dlib wheel from PyPI is usually a CPU build. A CUDA build reports
`dlib.DLIB_USE_CUDA` and at least one device through
`dlib.cuda.get_num_devices()`. The backend status shows `cuda` when both are
true.

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
