# Building the iNaturalist bird HEF for Hailo-8L

This directory contains everything needed to compile the Coral
iNaturalist 964-species bird classifier into a Hailo-8L HEF for the
Raspberry Pi AI Kit.

**The compile step must run on an x86_64 Linux machine with the Hailo
Dataflow Compiler (DFC) installed — NOT on the Pi.** DFC is x86-only
and needs a Hailo PCIe device attached for full flow. The Pi's job is
model prep + validation (already done here).

## Status

- [x] TFLite model staged: `../all_models/mobilenet_v2_1.0_224_inat_bird_quant.tflite`
- [x] Labels staged: `../all_models/inat_bird_labels.txt` (965: 964 species + `background`)
- [x] Calibration dataset: `inat_bird_calib.npz` (68 real camera photos, clean crops, 224x224 uint8)
- [x] DFC input model: `inat_bird_qdq.onnx` (validated — matches TFLite 12/12 top-1)
- [x] Model script: `model_script.alls` (on-chip normalization `(x-128)/128`)
- [ ] **HEF compile on x86 DFC host** — the only remaining step
- [ ] Copy HEF to `all_models/inat_bird.hef`, point classify at it, re-run classification

## Input model choice

`inat_bird_qdq.onnx` is the TFLite converted with `tflite2onnx`, with
activation QuantizeLinear/DequantizeLinear layers **kept intact**
(minus the entry input pair). This is intentional:

- The source model's depthwise weights are large (~absmax 182) and only
  stay numerically stable because activation quantization clamps
  intermediate values. A fully dequantized float graph diverges
  (activations reach ~1e10) and predicts a constant wrong class.
- The Q/DQ layer ranges are the *true* quantization ranges Hailo needs
  to re-quantize correctly. Do not strip them.

`inat_bird_tflite2onnx_raw.onnx` is the untouched converter output
(source for regenerating the Q/DQ variant if needed).

## Running the compile

On the x86 DFC host:

```bash
# 1. Get the project sources + model build artifacts. Either:
#    (a) clone this repo (model_build/ is committed, including the .onnx
#        and .npz), or
#    (b) copy model_build/ from the Pi:
#        scp -r pi:/path/to/project-leroy/model_build ./
#    No file from all_models/ is required: the primary path uses only
#    model_build/inat_bird_qdq.onnx. (The TFLite fallback needs the
#    .tflite, which is gitignored — copy it from the Pi if needed.)

# 2. Install the Hailo AI Software Suite. Either pull the official Docker
#    image (no --device / --gpus / --privileged / PCIe device needed
#    for compilation) or install the DFC wheel + hailo_sdk_client:
git clone https://github.com/.../project-leroy   # or scp -r
cd model_build

# Official image route (recommended):
#   docker run -it --rm -v "$PWD":/local/shared_with_docker \
#       hailo8_ai_sw_suite_2025-10:1
# Then inside the container:  python3 compile_hef.py

# Direct wheel route:
pip install hailo_dataflow_compiler-*.whl
python3 compile_hef.py
```

The compile prints `[info] PCIe: No Hailo PCIe device was found` — **this
is expected and harmless during compilation** (a physical Hailo device is
only needed for inference, not for DFC compilation).

# 3. Compile. Primary path parses the Q/DQ ONNX; if DFC rejects it as an
#    already-quantized model it falls back to the raw TFLite.
python3 compile_hef.py
# -> writes inat_bird.hef

# 4. Verify the HEF loads on-device (run on a Pi with the AI Kit):
#    hailortcli run inat_bird.hef --input-format uint8
```

Expected: input shape `[1,224,224,3]` uint8 (the on-chip normalization
in `model_script.alls` converts raw pixels to `(x-128)/128`), output
`[1,965]` softmax quantized to uint8.

## Fallbacks if the ONNX path fails

1. **DFC rejects Q/DQ graph**: `compile_hef.py` already falls back to
   `translate_tf_model` on the raw TFLite. DFC's TFLite parser handles
   the native quantization. This is the classic documented flow.
2. **Calibration too small**: Hailo recommends ~100-1000 images. If 68
   crops don't quantize well, collect more `storage/detected` crops
   and re-run `make_calibration_npz.py`.
3. **Compile time**: with `compiler_optimization_level=max` a
   MobileNetV2 compiles in ~10-40 min on a modern x86 host. Use
   `performance_param(compiler_optimization_level=O1)` in
   `model_script.alls` for faster compiles.

## After the HEF exists (on the Pi)

1. Copy `inat_bird.hef` → `all_models/inat_bird.hef`.
2. Point the classifier at it: set `LEROY_CLASSIFICATION_MODEL` /
   `LEROY_CLASSIFICATION_LABELS` in `leroy.env`
   (`all_models/inat_bird.hef` / `all_models/inat_bird_labels.txt`).
3. Re-classify existing photos:
   `python3 classify.py --dir=storage/detected --classification-model all_models/inat_bird.hef --classification-labels all_models/inat_bird_labels.txt`
4. Regenerate the gallery: `python3 visitation.py --dir=/var/www/html/classified`.
5. Verify: no ImageNet-only species (e.g. "hammerhead shark") remain;
   cardinals show as `Cardinalis cardinalis (Northern Cardinal)`.

## Ground-truth verification (done)

`inat_bird_qdq.onnx` was validated against the TFLite interpreter on
all 68 calibration crops: **top-1 agreement 68/68, top-5 68/68**.
Cardinal photos → `Cardinalis cardinalis`, doves → `Zenaida asiatica`.
