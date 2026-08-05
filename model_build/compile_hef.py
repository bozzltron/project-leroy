#!/usr/bin/env python3
"""Compile the iNaturalist 964-species bird classifier to a Hailo-8L HEF.

MUST be run on an x86_64 Linux machine with the Hailo Dataflow Compiler
(DFC) installed -- NOT on the Raspberry Pi (DFC does not run on ARM).
See README.md in this directory for the full workflow.

Primary input model: inat_bird_qdq.onnx
  This is the Coral TFLite converted to ONNX with tflite2onnx, with its
  activation QuantizeLinear/DequantizeLinear layers kept intact. Those
  layers are load-bearing: the source model's depthwise weights are large
  (~181) and only stay numerically stable because activation quantization
  clamps intermediate values. DFC understands the Q/DQ layers and uses
  them (plus its own calibration) when re-quantizing for Hailo.

  **IMPORTANT:** Do NOT run onnx-simplifier on this model. onnx-simplifier
  would fold/strip the Q/DQ pairs and the resulting float graph diverges
  (verified: activations reach ~1e10, predicts a constant wrong class).

  The entry input pair was stripped, so the ONNX input is a FLOAT tensor
  expecting values (raw_uint8 - 128) / 128. The on-chip
  `normalization([128,128,128],[128,128,128])` in model_script.alls
  converts the HEF's uint8 pixel input (0-255) into that float, so:
    - calibration data = raw uint8 images (0-255)  [NOT pre-normalized]
    - inference input  = raw uint8 images (0-255)
  This matches the DFC guidance: "if a normalization layer has been added
  to the model [.alls], the calibration set should not be normalized."

Fallback input model: mobilenet_v2_1.0_224_inat_bird_quant.tflite
  If DFC rejects the Q/DQ ONNX (it may classify it as an already-quantized
  model), parse the raw TFLite instead via translate_tf_model().

Usage:
    python3 compile_hef.py [--model inat_bird_qdq.onnx|tflite] [--out inat_bird.hef]
"""
import argparse
import glob
import os
import sys

import numpy as np

MODEL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_script.alls")
CALIB_NPZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inat_bird_calib.npz")
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
TFLITE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "all_models", "mobilenet_v2_1.0_224_inat_bird_quant.tflite")


def load_calibration(path: str) -> np.ndarray:
    """Load the calibration dataset as a raw-uint8 (N, 224, 224, 3) array.

    Accepts either a pre-built .npz/.npy (from make_calibration_npz.py) or a
    directory of PNG/JPG crops, which are read, resized to 224x224 and stacked.
    The data stays raw uint8 (0-255) -- on-chip normalization in model_script.alls
    handles (x-128)/128, per DFC guidance that a model-script normalization means
    the calibration set should NOT be pre-normalized.
    """
    if not os.path.exists(path):
        print(f"calibration dataset not found ({path}); run make_calibration_npz.py first")
        sys.exit(1)
    if os.path.isdir(path):
        from PIL import Image
        files = sorted(glob.glob(os.path.join(path, "*.png")) +
                       glob.glob(os.path.join(path, "*.jpg")) +
                       glob.glob(os.path.join(path, "*.jpeg")))
        if not files:
            sys.exit(f"no images in calibration dir: {path}")
        images = []
        for f in files:
            img = Image.open(f).convert("RGB").resize((224, 224), Image.LANCZOS)
            images.append(np.asarray(img, dtype=np.uint8))
        return np.stack(images)
    with np.load(path) as npz:
        return npz[npz.files[0]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="inat_bird_qdq.onnx",
                        help="onnx (default) or a .tflite path")
    parser.add_argument("--out", default="inat_bird.hef")
    parser.add_argument("--hw-arch", default="hailo8l",
                        help="hailo8l for the Pi AI Kit; hailo8 for Hailo-8")
    parser.add_argument("--calib", default=CALIB_NPZ,
                        help=".npz/.npy (raw uint8) or a dir of PNG/JPG crops")
    args = parser.parse_args()

    from hailo_sdk_client import ClientRunner

    calib_data = load_calibration(args.calib)
    print(f"calibration data: {calib_data.shape} {calib_data.dtype}")
    print(f"hw arch: {args.hw_arch}")

    runner = ClientRunner(hw_arch=args.hw_arch)

    if args.model.endswith(".tflite"):
        print(f"parsing TFLite: {args.model}")
        hn, npz = runner.translate_tf_model(args.model, "inat_bird")
    else:
        model_path = args.model
        if not os.path.isabs(model_path):
            model_path = os.path.join(MODEL_DIR, model_path)
        print(f"parsing ONNX: {model_path}")
        try:
            hn, npz = runner.translate_onnx_model(model_path, "inat_bird")
        except Exception as exc:  # noqa: BLE001 -- surface parse failures
            print(f"ONNX parse failed ({exc}); trying the raw TFLite instead")
            hn, npz = runner.translate_tf_model(TFLITE, "inat_bird")

    runner.load_model_script(MODEL_SCRIPT)

    runner.optimize(calib_data)
    runner.save_har("inat_bird_quantized_model.har")

    hef = runner.compile()
    with open(args.out, "wb") as f:
        f.write(hef)
    print(f"HEF written: {args.out}")


if __name__ == "__main__":
    main()
