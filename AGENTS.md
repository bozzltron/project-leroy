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
  - `pyvenv.cfg` says `version = 3.9.2` (stale — see Known issues)
  - `include-system-site-packages = false` (intentional)
- **System packages used (NOT in venv):** `python3-opencv`, `python3-picamera2`, `python3-numpy`, `python3-pil` — installed via `apt`
- **Hailo stack:** `hailo-all`, `hailort` 4.23.0, `hailort-pcie-driver` 4.23.0, `python3-hailort` 4.23.0-1, `hailo-tappas-core` 5.1.0
- **CPU temperature observed:** 85.1°C — at throttle threshold. Verify cooling before long runs.

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
  - `active_learning.py` — low-confidence / non-bird collection
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

| File | Size | Purpose | Notes |
|------|------|---------|-------|
| `all_models/yolov11s.hef` | ~25 MB | Detection (COCO 80 classes) | Bird = class 15. Currently used. |
| `all_models/yolo11s.txt` | 624 B | COCO labels | Detection label set. |
| `all_models/mobilenet_v2_1.0_224_inat_bird.hef` | ~10 MB | Classification (iNaturalist birds) | **Currently used.** 964 bird species. |
| `all_models/inat_bird_labels.txt` | 37 KB | iNaturalist bird labels | **Currently used.** Matches the iNat classifier. |
| `all_models/mobilenet_v3.hef` | ~10 MB | Classification (ImageNet-1k) | ~59 bird species only. Fallback if iNat unavailable. |
| `all_models/mobilenet_v3.txt` | 21 KB | ImageNet-1000 labels | Classification label set (fallback). |

- **HEFs are committed to the repo** (despite `.gitignore` listing `all_models/` — this rule was added after a partial commit; treat it as advisory).
- **When swapping models:** ensure the HEF is compiled for Hailo-8L, and that label files match the model's output classes.

---

## Known issues — Phase 1 complete (2026-07-08)

> **This section captures the state of the project as of the Phase 1 fixes on
> 2026-07-08. It will be revised as Phase 2+ work lands. Treat it as
> ephemeral debugging context, not permanent truth.**

1. **Phase 1 complete (2026-07-08).** The service is now fully functional — model loads, camera captures frames via picamera2, Hailo inference runs at ~10 FPS, NMS postprocessing works correctly. The detection loop processes frames continuously with no errors. 14 commits were made to fix the HailoRT 4.23.0 API migration. Remaining items: logging unification, env validation.
2. **Service crash loop — `hailo_inference.py:74` (FIXED and VERIFIED).** The code was calling `.configure()` on a `Device` instance, but `Device` in HailoRT 4.23.0 has no `configure` method — only `VDevice` does. Fix: changed `Device()` to `VDevice()` and updated the import. Commits: `6288fa09` (Device→VDevice), `215b4e18` (load_model→HEF+ConfigureParams+configure), `d5e080a2` (InferVStreams params), `ea85b172` (preprocess shape+dtype), `b6d4c3c8` (writeable array), `d5f526e1` (batch dimension), `3424745c` (network group activation), `c507c81c` (return ConfiguredNetwork), `b2e1dfbb` (NMS postprocess format). Service starts, model loads, network group activates, and detection loop runs at ~10 FPS with 0 errors.
3. **Historical log bloat.** `storage/results.log` is ~1.3 GB / 23.7M lines as of the Phase 1 fix, mostly picamera2 job spam. Logrotate is now configured (see item 6) and will pick this up on first daily run — the historical file becomes `results.log.1` and rolls off after 7 rotations (`maxage 30` days as a safety net). No manual intervention needed; the file is kept in place until logrotate prunes it.
4. **Venv version mismatch (FIXED).** `pyvenv.cfg` updated to match the actual Python version. Commit `8f35b561`.
5. **CPU at 85.1°C** — at throttle threshold. The crash loop is gone, so temperature should be lower now. Verify cooling before long runs.
6. **Cron now configured (post-Phase 1).** `/etc/cron.d/leroy-classify` runs `classify.sh` as root every 30 minutes (idempotent install via `install-pi5.sh`). Logrotate (`/etc/logrotate.d/leroy`, from `deploy/logrotate-leroy`) handles `storage/results.log` and `/var/log/leroy-classify.log` daily with 100M size trigger, `copytruncate`, and 7 retained. Once the system is in place, **log size is no longer a concern** — the 1.3 GB historical bloat will be picked up on the first daily rotation. Use `make cron_status` and `make logrotate_status` to verify on a deployed system.
7. **Logging split.** `leroy.py` configures logging to BOTH `storage/results.log` and stderr (journald). `visitations.py`, `photo.py`, `classify.py` only log to file. systemd cannot see their errors via `journalctl -u leroy.service`. Fix pending: Phase 1 Change 2+3.
8. **`atproto` (Bluesky) missing** from venv. `bluesky_poster.py` will fail at import.
9. **`rpicam-apps` installed.** `rpicam-hello --list-cameras` is available for diagnostics. Camera works via libcamera/PiSP pipeline.
10. **Camera frame reads failing (FIXED).** Commit `f9d81cf9` ported `camera_manager.py` from OpenCV `VideoCapture` to `picamera2`. The Pi HQ Camera (imx477) works correctly via libcamera/PiSP pipeline.
11. **Web server startup timeout (NEW — current blocker).** `Waiting for web server to be ready on http://localhost:8080...` timed out after 30s. Browser launch was skipped. nginx may not be running or may not be configured. Check `systemctl status nginx` and `nginx.conf`.
12. **Empty storage.** The detection loop is running, but no birds have been detected yet. `storage/detected`, `storage/classified`, `storage/active_learning` remain empty until a detection occurs.

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
