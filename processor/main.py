"""
ANTs N4 bias field correction, one subject per T1w image.

Inputs (INPUT_DIR/<name>/ when linked, else found anywhere under INPUT_DIR
by BIDS suffix):
  image  <sub>[_<entities>]_T1w.nii.gz   required
  mask   <sub>[_<entities>]_mask.nii.gz  optional, matched by subject label

Outputs:
  OUTPUT_DIR/corrected/<sub>_desc-n4_T1w.nii.gz        (+ provenance.json)
  OUTPUT_DIR/biasfield/<sub>_desc-biasfield_T1w.nii.gz
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import nibabel as nib
import numpy as np

from processor import bids_names as bn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("processor-ants-n4")

APP = "processor-ants-n4"
TOOL = "N4BiasFieldCorrection"
OUTPUTS = ["corrected", "biasfield"]
PARAMS = ("SHRINK_FACTOR", "BSPLINE_FITTING_MM", "ITERATIONS", "CONVERGENCE_THRESHOLD", "THREADS")
DEFAULTS = {
    "SHRINK_FACTOR": "4",
    "BSPLINE_FITTING_MM": "180",
    "ITERATIONS": "50x50x50x50",
    "CONVERGENCE_THRESHOLD": "0.0",
    "THREADS": "4",
}


def app_version() -> str:
    for candidate in (Path(__file__).resolve().parent.parent / "VERSION", Path("/processor/VERSION")):
        if candidate.is_file():
            return candidate.read_text().strip()
    return "unknown"


def tool_version() -> str:
    try:
        out = subprocess.run([TOOL, "--version"], check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        log.warning("could not read the %s version: %s", TOOL, exc)
        return "unknown"
    for line in out.splitlines():
        if "Version" in line:
            return line.split(":", 1)[-1].strip()
    return out.strip().splitlines()[0] if out.strip() else "unknown"


def read_params() -> dict:
    raw = {k: os.environ.get(k, DEFAULTS[k]).strip() or DEFAULTS[k] for k in PARAMS}
    params = {
        "SHRINK_FACTOR": int(raw["SHRINK_FACTOR"]),
        "BSPLINE_FITTING_MM": int(raw["BSPLINE_FITTING_MM"]),
        "ITERATIONS": raw["ITERATIONS"],
        "CONVERGENCE_THRESHOLD": float(raw["CONVERGENCE_THRESHOLD"]),
        "THREADS": int(raw["THREADS"]),
    }
    if params["SHRINK_FACTOR"] < 1 or params["THREADS"] < 1 or params["BSPLINE_FITTING_MM"] < 1:
        raise ValueError(f"SHRINK_FACTOR, BSPLINE_FITTING_MM and THREADS must be >= 1, got {raw}")
    if not all(tok.isdigit() for tok in params["ITERATIONS"].split("x")):
        raise ValueError(f"ITERATIONS must look like 50x50x50x50, got {raw['ITERATIONS']!r}")
    return params


def n4_command(image: Path, mask: Path | None, corrected: Path, biasfield: Path, p: dict) -> list[str]:
    cmd = [TOOL, "-d", "3", "-i", str(image)]
    if mask is not None:
        cmd += ["-x", str(mask)]
    cmd += [
        "-s", str(p["SHRINK_FACTOR"]),
        "-b", f"[{p['BSPLINE_FITTING_MM']}]",
        "-c", f"[{p['ITERATIONS']},{p['CONVERGENCE_THRESHOLD']}]",
        "-o", f"[{corrected},{biasfield}]",
        "-v", "1",
    ]
    return cmd


def bias_field_range(biasfield: Path, image: Path, mask: Path | None) -> dict:
    """min/max/ratio of the bias field inside the mask (or, without one, where the image is > 0)."""
    field = np.asarray(nib.load(str(biasfield)).dataobj, dtype=np.float64)
    if mask is not None:
        region = np.asarray(nib.load(str(mask)).dataobj) > 0
        within = "mask"
    else:
        region = np.asarray(nib.load(str(image)).dataobj) > 0
        within = "image>0"
    if region.shape != field.shape:
        log.warning("bias field %s and %s differ in shape; using the whole field", field.shape, within)
        region = np.ones_like(field, dtype=bool)
    vals = field[region]
    vals = vals[np.isfinite(vals) & (vals > 0)]
    if vals.size == 0:
        return {"within": within, "voxels": 0, "min": None, "max": None, "ratio": None}
    lo, hi = float(vals.min()), float(vals.max())
    return {"within": within, "voxels": int(vals.size), "min": lo, "max": hi, "ratio": hi / lo}


def process_subject(sub: str, image: Path, mask: Path | None, out_corrected: Path, out_bias: Path,
                    params: dict, input_dir: Path, output_dir: Path) -> dict:
    corrected = out_corrected / bn.derived_name(image, "T1w", desc="n4")
    biasfield = out_bias / bn.derived_name(image, "T1w", desc="biasfield")
    cmd = n4_command(image, mask, corrected, biasfield, params)
    log.info("[%s] %s", sub, " ".join(cmd))
    t0 = time.monotonic()
    subprocess.run(cmd, check=True)
    seconds = round(time.monotonic() - t0, 1)
    for f in (corrected, biasfield):
        if not f.is_file() or f.stat().st_size == 0:
            raise RuntimeError(f"{TOOL} exited 0 but did not write {f.name}")
    rng = bias_field_range(biasfield, image, mask)
    log.info("[%s] done in %ss; bias field within %s: min %.4g max %.4g ratio %.3f",
             sub, seconds, rng["within"], rng["min"] or float("nan"), rng["max"] or float("nan"),
             rng["ratio"] or float("nan"))
    inputs = [str(image.relative_to(input_dir))]
    if mask is not None:
        inputs.append(str(mask.relative_to(input_dir)))
    return {
        "subject": sub,
        "inputs": inputs,
        "outputs": [str(corrected.relative_to(output_dir)), str(biasfield.relative_to(output_dir))],
        "command": cmd,
        "seconds": seconds,
        "biasFieldRange": rng,
    }


def main() -> int:
    started = datetime.now(timezone.utc)
    input_dir = os.environ.get("INPUT_DIR")
    output_dir = os.environ.get("OUTPUT_DIR")
    if not input_dir or not output_dir:
        log.error("INPUT_DIR and OUTPUT_DIR must be set")
        return 2
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if not input_dir.is_dir():
        log.error("INPUT_DIR %s is not a folder", input_dir)
        return 2
    try:
        params = read_params()
    except ValueError as exc:
        log.error("bad parameter: %s", exc)
        return 2
    os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = str(params["THREADS"])
    log.info("%s %s, %s %s, parameters %s", APP, app_version(), TOOL, tool_version(), params)

    out_corrected = bn.output_dir_for(output_dir, OUTPUTS, "corrected")
    out_bias = bn.output_dir_for(output_dir, OUTPUTS, "biasfield")

    images = bn.by_subject(bn.find_input_files(input_dir, "image", ["T1w"]))
    masks = bn.by_subject(bn.find_input_files(input_dir, "mask", ["mask"]))
    if not images:
        found = sorted(str(p.relative_to(input_dir)) for p in input_dir.rglob("*") if p.is_file())
        log.error("no T1w image (*_T1w.nii[.gz]) found under %s; files present: %s",
                  input_dir, ", ".join(found) or "(none)")
        return 1
    log.info("%d subject(s): %s; masks for: %s", len(images), ", ".join(sorted(images)),
             ", ".join(sorted(masks)) or "(none)")
    for sub in sorted(masks):
        if sub not in images:
            log.warning("mask for %s has no matching image; ignored", sub)

    subjects, failures = [], []
    for sub in sorted(images):
        image, mask = images[sub], masks.get(sub)
        if mask is None and masks:
            log.warning("[%s] no mask for this subject; N4 runs without one", sub)
        try:
            subjects.append(process_subject(sub, image, mask, out_corrected, out_bias, params, input_dir, output_dir))
        except (subprocess.CalledProcessError, RuntimeError, OSError, ValueError) as exc:
            log.error("[%s] failed: %s", sub, exc)
            failures.append({"subject": sub, "inputs": [str(image.relative_to(input_dir))], "error": str(exc)})

    provenance = {
        "app": APP,
        "appVersion": app_version(),
        "tool": TOOL,
        "toolVersion": tool_version(),
        "startedAt": started.isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "parameters": params,
        "subjects": subjects,
        "failures": failures,
    }
    with open(out_corrected / "provenance.json", "w") as fh:
        json.dump(provenance, fh, indent=2)

    log.info("%d of %d subject(s) corrected", len(subjects), len(images))
    if not subjects:
        log.error("every subject failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
