# AGENTS.md — Project Leroy

Agent-focused context for working on Project Leroy. This is **not** a README —
see [README.md](README.md) for human-facing documentation. The two are
intentionally separate: README is for users/contributors, this file is for
AI coding agents dropped into the repo.

---

## Project overview

Project Leroy is an AI-powered birdwatcher: real-time bird detection, photo
capture, species classification, and web-based visitations gallery, running
on a Raspberry Pi 5 with the AI Kit (Hailo-8L) and a Pi HQ camera.

**Architecture:**

- Detection loop: `leroy.py` → `hailo_inference.py` (YOLO on Hailo-8L) + `camera_manager.py` (picamera2 dual-resolution)
- Photo storage: UUID filenames + companion JSON metadata, no database
- Classification: `classify.py` (MobileNet on Hailo-8L) — runs periodically
- Web UI: vanilla JS, served by nginx on port 8080, reads `/var/www/html/visitations.json`
- Service: `systemd` unit `leroy.service` runs `run.sh` → `leroy.py`; supervised by `hailort.service`

**History (matters for context):** The project was refactored from Google Coral
Edge TPU to Raspberry Pi AI Kit (Hailo-8L) in late 2025/early 2026. All
EdgeTPU/pycoral code is intentionally removed — do not reintroduce it.

---

## Hardware & runtime environment

- **Target:** Raspberry Pi 5 (8GB) + Raspberry Pi AI Kit (Hailo-8L) + Pi HQ Camera
- **OS:** Debian Bookworm, 64-bit (aarch64), kernel 6.12 (`rpi-2712`)
- **Python venv:** `venv/` at project root, currently Python 3.13
  - `pyvenv.cfg` says `version = 3.13`
  - `include-system-site-packages = false` (intentional)
- **System packages used (NOT in venv):** `python3-opencv`, `python3-picamera2`, `python3-numpy`, `python3-pil` — installed via `apt`
- **Hailo stack:** `hailo-all`, `hailort` 4.23.0, `hailort-pcie-driver` 4.23.0, `python3-hailort` 4.23.0-1, `hailo-tappas-core` 5.1.0
- **CPU temperature observed:** 85.1°C (185.2°F) — at throttle threshold. Verify cooling before long runs. Current thresholds pause at 80°C (176°F) and resume at 75°C (167°F).

---

## Setup commands

- **Activate venv:** `source venv/bin/activate`
- **Run all tests (Docker, no Hailo needed):** `make docker-pi5-test`
- **Run a single test:** `make docker-pi5-test-file TEST=tests.test_foo`
- **Lint:** `make docker-pi5-lint` (flake8 in Docker; rules in `.flake8`)
- **Build Docker image:** `make docker-pi5-build`
- **Local web preview:** `make web-preview` (nginx on `http://localhost:8080`)
- **Tail app log:** `make tail` (follows `storage/results.log`)

> **Note:** Docker-based commands run inside `docker-compose.pi5.yml` and do
> NOT have access to the Hailo device. They are for code/test verification
> only. To run against real hardware, you must be on the Pi.

---

## Service operations — READ-ONLY for agents

You may **observe** the service, but you must **not** change its state
without explicit user approval.

- **Check status:** `make service_status` — preferred, includes last few log lines
- **Live logs:** `make service_logs` (follows journald)
- **Recent logs (this boot):** `make service_recent_logs`
- **Application log file:** `tail -f storage/results.log` or `make tail`

**DO NOT** run, under any circumstances, without explicit user instruction:

- `make service_start`
- `make service_stop`
- `make service_restart`
- `systemctl start|stop|restart leroy.service`
- `systemctl daemon-reload`
- `install-pi5.sh` (reinstalls Hailo drivers from scratch)
- Any edit to `/etc/systemd/system/leroy.service` (the source of truth is `service/leroy.service` in this repo)

The service is now fully functional (see Known issues). Restarts are not needed
unless explicitly requested by the user.

---

## Code conventions

- **Python:** 3.9+ syntax compatibility (the install script may run on 3.9; venv is 3.13)
- **Linting:** flake8, see `.flake8`. Rules in effect: `max-line-length = 120`, excludes `venv,.git,__pycache__,web`, and ignores 25+ codes including E501/W503/E402/F401/F841.
- **File structure:**
  - `leroy.py` — main entry, detection loop
  - `hailo_inference.py` — Hailo-8L NPU wrapper (detection + classification)
  - `camera_manager.py` — picamera2 dual-resolution camera manager
  - `visitations.py` — visitation state machine (in-memory, per-process)
  - `visitation.py` — visitation *processing* (post-classification, web JSON generation)
  - `photo.py` / `photo_metadata.py` — UUID-based photo capture and metadata
  - `classify.py` — batch classification runner
  - `active_learning.py` — non-bird false-positive collection (squirrels, cats, dogs)
  - `bluesky_poster.py` — optional Bluesky (atproto) posting
  - `utils.py` — shared helpers (label loading, image clarity, etc.)
  - `config.py` — env-based configuration
- **Tests:** `tests/` directory, run via `python3 -m unittest discover tests`
- **No database.** All state is filesystem + JSON.
- **Configuration:** env vars in `leroy.env` (gitignored). Template: `leroy.env.example`. Always update both.
- **Commit messages:** short imperative subject, optional body explaining why.

---

## Hailo SDK notes (HailoRT 4.23.0)

- **Correct API for loading a model and running inference:**
  ```python
  from hailo_platform import (
      VDevice, HEF, ConfigureParams, HailoStreamInterface,
      InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams
  )

  device = VDevice()
  hef = HEF(model_path)
  configure_params = ConfigureParams.create_from_hef(hef, HailoStreamInterface.PCIe)
  network_group = device.configure(hef, configure_params)[0]
  network_group_params = network_group.create_params()
  network_group.activate(network_group_params)

  input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
  output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.UINT8)
  infer_vstreams = InferVStreams(network_group, input_vstreams_params, output_vstreams_params)

  # Input must be uint8 with batch dimension (1, H, W, C)
  input_array = np.ascontiguousarray(preprocessed_frame[np.newaxis, ...])
  output = infer_vstreams.infer([input_array])
  # For YOLO with NMS, output is a list of per-class arrays, not separate named tensors
  ```
  This pattern is confirmed working on the Pi 5 + AI Kit with HailoRT 4.23.0.
- **Use `VDevice`, not `Device`.** In HailoRT 4.23.0, only `VDevice` has the `configure(hef, configure_params)` method. `Device` has only `control`, `device_id`, `loaded_network_groups`, `read_log`, `release`, `scan`.
- **ConfigureParams requires a stream interface.** `ConfigureParams.create_from_hef(hef, interface)` takes the HEF and a `HailoStreamInterface` value. For the Pi AI Kit use `HailoStreamInterface.PCIe`.
- **Activate the network group before inference.** Call `network_group.activate(network_group.create_params())` before creating `InferVStreams`.
- **Create `InferVStreams` with `InputVStreamParams.make()` and `OutputVStreamParams.make()`**, not by inspecting tensors manually. Use `format_type=FormatType.UINT8` for the input.
- **Reuse `InferVStreams` across frames** — creating a fresh one per inference is wasteful. Keep one per (device, network_group, input/output vstream names).
- **Input array must be `uint8` with a batch dimension of shape `(1, H, W, C)`.** Wrap with `np.ascontiguousarray(...)` and `[np.newaxis, ...]` before passing to `infer_vstreams.infer([input_array])`.
- **Output tensor names vary by model** — never hardcode. Use heuristics or inspect the HEF at load time. If output shape/names are unknown, log them and fail loud, not silent.
- **NMS output is a list of per-class arrays**, not separate named tensors. Postprocess accordingly.
- **HEF models are device-specific:**
  - Hailo-8L (Pi AI Kit, ~13 TOPS) — what this project uses
  - Hailo-8 (~26 TOPS) — NOT compatible
  - Hailo-10 — NOT compatible
  - Mismatched HEFs raise error code 93 (`HEF_NOT_COMPATIBLE`)
- **Driver/runtime version drift is a known pain point** — `fix_hailo_version.sh` exists for this reason. Driver and `hailort` must match.

---

## Models

| File | Size | Purpose |
|------|------|---------|
| `all_models/yolov11s.hef` | ~25 MB | Detection (COCO 80 classes). Bird = class 15. |
| `all_models/yolo11s.txt` | 624 B | COCO labels for detection. |
| `all_models/mobilenet_v3.hef` | ~10 MB | Classification (ImageNet-1k). ~59 bird species. |
| `all_models/mobilenet_v3.txt` | 21 KB | ImageNet-1000 labels for classification. |

**Note on iNaturalist bird classifier:** The original 2020 Coral-era
classifier (`mobilenet_v2_1.0_224_inat_bird`) had 964 bird species but
is not available as a pre-compiled HEF in the Hailo Model Explorer.
To get more species, the iNat model would need to be compiled locally
from the TFLite using the Hailo Dataflow Compiler — a non-trivial
process not currently supported by the installer.

- **HEFs are committed to the repo** (despite `.gitignore` listing `all_models/` — this rule was added after a partial commit; treat it as advisory).
- **When swapping models:** ensure the HEF is compiled for Hailo-8L, and that label files match the model's output classes.

---

## Known issues

### CPU temperature
The Pi 5 + AI Kit generates significant heat under sustained Hailo inference.
Active cooling is required for reliable operation. The detection loop includes
thermal protection: it pauses above 80°C (176°F) and resumes below 75°C (167°F).

### Bluesky posting requires manual install
`bluesky_poster.py` imports `atproto` at module load. If you want Bluesky
posting, install it manually: `source venv/bin/activate && pip install atproto`.
Without it, visitations are still processed and saved — only the social posting
step is skipped.

---

## What NOT to do

Strict rules. Violating these is a bug, not a style choice.

- **Do not** run `install-pi5.sh`. It reinstalls Hailo drivers and requires sudo.
- **Do not** start, stop, or restart `leroy.service` (or any related systemd unit) without explicit user instruction.
- **Do not** edit `/etc/systemd/system/leroy.service` directly. Edit `service/leroy.service` in this repo; the user can re-deploy manually.
- **Do not** reintroduce Coral / EdgeTPU / pycoral / `.tflite` code. This project is Hailo-only.
- **Do not** commit `.env`, `leroy.env`, or any file containing credentials or API tokens.
- **Do not** change model file paths in `leroy.env` without first verifying the HEF exists and is non-empty.
- **Do not** `git push --force` to `main` or `master`.
- **Do not** `pip install` system-wide. Use the venv (`source venv/bin/activate && pip install ...`).
- **Do not** run `pip install` against the system Python on the Pi.
- **Do not** delete `storage/results.log` without first archiving a copy. It has historical debugging value until the crash loop is fixed.
- **Do not** assume output tensor names, shapes, or layouts from HEF models. Inspect or log; never hardcode.
- **Do not** create a new `InferVStreams` per inference call. Reuse one per (network_group, vstream pair).
- **Do not** run heavy inference loops without first checking CPU temperature (`vcgencmd measure_temp`).

---

## Where things live

| What | Where |
|------|-------|
| Main entry | `leroy.py` |
| Model wrapper | `hailo_inference.py` |
| Camera | `camera_manager.py` |
| Classification | `classify.py` (via `classify.sh`) — runs every 30 min from `/etc/cron.d/leroy-classify` as root |
| Log rotation | `deploy/logrotate-leroy` (installed to `/etc/logrotate.d/leroy`) — daily, 100M size trigger, copytruncate, 7 retained |
| Visitation processing | `visitation.py` (post-classification web JSON gen) |
| Visitation runtime | `visitations.py` (in-memory state machine) |
| Photo storage | `photo.py` + `photo_metadata.py` |
| Active learning | `active_learning.py` |
| Web assets | `web/` (HTML, CSS, JS) |
| nginx config | `nginx.conf` (port 8080) |
| systemd unit | `service/leroy.service` (source of truth; deployed to `/etc/systemd/system/`) |
| Service entry | `run.sh` (validates venv + Hailo, sources env, execs `leroy.py`) |
| Environment | `leroy.env` (gitignored) / `leroy.env.example` (template) |
| Makefile | `./Makefile` — all common commands |
| Tests | `tests/` — `python3 -m unittest discover tests` |
| Models | `all_models/*.hef` + `*.txt` |
| Runtime state | `storage/` (gitignored) — detected photos, classified photos, logs, active learning, results.log |

---

## Quick reference: most useful commands

```bash
# Health check (READ-ONLY)
make service_status
make service_recent_logs
make tail
hailortcli scan
vcgencmd measure_temp
ls -la /dev/video*

# Tests (Docker, safe)
make docker-pi5-test
make docker-pi5-test-file TEST=tests.test_visitation_processing

# Lint (Docker, safe)
make docker-pi5-lint

# Web preview (local dev only)
make web-preview
```

---

*Last updated: 2026-07-08 — Phase 1 complete. Service running, detection loop active at ~10 FPS.*
