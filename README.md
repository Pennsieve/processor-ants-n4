# processor-ants-n4

N4 bias field correction of T1-weighted MRI with
[ANTs](https://github.com/ANTsX/ANTs) 2.6.5 `N4BiasFieldCorrection`. Step 3 of the
Clinical Brain MRI workflow: it takes the skull-stripped T1w from SynthStrip (and, optionally,
its brain mask) and writes the corrected image plus the estimated bias field, one subject per
image.

## Ports

| Port | Kind | Files | Notes |
|---|---|---|---|
| `image` | input, required | `<sub>[_<entities>]_T1w.nii.gz` | one per subject, e.g. `sub-01_desc-brain_T1w.nii.gz`; found in `INPUT_DIR/image/`, else anywhere under `INPUT_DIR` by the `T1w` suffix |
| `mask` | input, optional | `<sub>[_<entities>]_mask.nii.gz` | matched to the image by subject label (the part before the first `_`); N4 fits the field inside it (`-x`) |
| `corrected` | output | `corrected/<sub>_desc-n4_T1w.nii.gz`, `corrected/provenance.json` | |
| `biasfield` | output | `biasfield/<sub>_desc-biasfield_T1w.nii.gz` | the multiplicative field N4 divided out |

Per subject the app runs

```
N4BiasFieldCorrection -d 3 -i <image> [-x <mask>] -s SHRINK_FACTOR -b [BSPLINE_FITTING_MM] \
  -c [ITERATIONS,CONVERGENCE_THRESHOLD] -o [<corrected>,<biasfield>] -v 1
```

then reads the bias field back and logs its min, max and max/min ratio inside the mask (or,
without a mask, where the image is > 0). That range goes into `provenance.json` as
`subjects[].biasFieldRange`, with the exact command and the time taken. A subject that fails
is logged and skipped; the run exits 1 only when every subject failed, or when no T1w image was
found at all.

## Parameters

| Parameter | Type | Default | |
|---|---|---|---|
| `SHRINK_FACTOR` | integer | `4` | downsampling for the field estimate (`-s`) |
| `BSPLINE_FITTING_MM` | integer | `180` | B-spline mesh spacing in mm (`-b`) |
| `ITERATIONS` | string | `50x50x50x50` | max iterations per level, coarse to fine (`-c`) |
| `CONVERGENCE_THRESHOLD` | number | `0.0` | convergence threshold (`-c`); 0 runs all iterations |
| `THREADS` | integer | `4` | `ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS` |

## Runtime

Container only (`computeTypes: [standard]`): 2 vCPU, 8 GiB, 30 min timeout. A 1 mm T1w takes
about a minute on native amd64 hardware. The image is `antsx/ants:2.6.5` plus Debian
`python3`, NiBabel and NumPy; it runs as uid 1000 and needs no network.

## Running it locally

```sh
sh sample-input/fetch-sample.sh   # one CC0 T1w from OpenNeuro into data/input/image/
make run                          # builds (linux/amd64) and runs over data/input/, output in data/output/
```

On an arm64 Mac the amd64 image runs under emulation and is several times slower. `make test`
runs the wrapper with the local Python instead (needs ANTs and `nibabel` installed).

## Citation

- Tustison NJ et al. N4ITK: improved N3 bias correction. IEEE Trans Med Imaging 2010;29:1310.
- Tustison NJ et al. The ANTsX ecosystem for quantitative biological and medical imaging. Sci Rep 2021;11:9068.

See `THIRD_PARTY.md` for licences. This repo is Apache-2.0, copyright 2026 Pennsieve.
