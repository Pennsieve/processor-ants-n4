# Sample input

No NIfTI files are committed. Fetch a CC0 T1w image from OpenNeuro (ds000117, sub-01) into
`data/input/image/` (gitignored) with:

```sh
sh sample-input/fetch-sample.sh
```

which runs

```sh
aws s3 cp --no-sign-request s3://openneuro.org/ds000117/sub-01/ses-mri/anat/sub-01_ses-mri_T1w.nii.gz data/input/image/sub-01_T1w.nii.gz
```

Then `make run`. To exercise the mask path, put a brain mask named `sub-01_desc-brain_mask.nii.gz`
(e.g. from the SynthStrip step) under `data/input/mask/`.
