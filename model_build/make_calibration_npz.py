#!/usr/bin/env python3
"""Build the DFC calibration dataset (.npz) from our real bird photos.

The calibration images are the actual 224x224 bird crops captured by this
project's camera -- a subset of the deployment distribution, which is what
Hailo recommends for quantization. No annotations are required.

Run on the Pi (or on the x86 DFC host) before compiling:
    python3 make_calibration_npz.py [calib_dir] [out.npz]
"""
import glob
import os
import sys

import numpy as np
from PIL import Image


def main() -> None:
    calib_dir = sys.argv[1] if len(sys.argv) > 1 else "calibration"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "inat_bird_calib.npz"

    files = sorted(glob.glob(os.path.join(calib_dir, "*.png")))
    if not files:
        sys.exit(f"no PNGs found in {calib_dir}")

    images = []
    for f in files:
        img = Image.open(f).convert("RGB").resize((224, 224), Image.LANCZOS)
        images.append(np.asarray(img, dtype=np.uint8))

    data = np.stack(images)  # (N, 224, 224, 3) uint8
    np.savez(out_path, data)
    print(f"wrote {len(files)} calibration images -> {out_path} (shape {data.shape}, dtype {data.dtype})")


if __name__ == "__main__":
    main()
