# Running on Windows and macOS

One launcher, `run.py`, works on both. It detects your hardware and picks
ComfyUI's arguments to match, so you don't hand-tune anything.

```
Windows :  run.bat          (or  python run.py)
macOS   :  ./run.sh         (or  python3 run.py)
Linux   :  ./run.sh
```

First run asks where ComfyUI is and remembers it in `ovg_config.json`.

---

## What the launcher decides for you

| Detected | Arguments used |
|---|---|
| NVIDIA, ≤6 GB VRAM | `--lowvram --disable-smart-memory --reserve-vram 0.8` |
| NVIDIA, 6–10 GB | `--normalvram --reserve-vram` |
| NVIDIA, >10 GB | defaults |
| **Apple Silicon (MPS)** | `PYTORCH_ENABLE_MPS_FALLBACK=1`, plus `--lowvram` under 24 GB RAM |
| No GPU | `--cpu` |

`--fp32-vae` is passed **on every platform**. It is not an optimisation knob —
Wan's VAE decodes causally in time, and in fp16 the chain overflows after the
first frame, leaving every later frame a flat constant while ComfyUI still
reports success. See [TUNING.md](TUNING.md).

---

## What is genuinely portable

| Piece | Windows | macOS |
|---|---|---|
| `run.py` launcher | ✅ | ✅ |
| Helper server + model downloader | ✅ | ✅ stdlib only |
| The browser UI | ✅ | ✅ |
| Model files (`.safetensors`, `.gguf`) | ✅ | ✅ identical |
| Workflows | ✅ | ✅ |
| `scripts/*.bat` | ✅ | ❌ superseded by `run.py` |
| ComfyUI itself | portable build | **must be installed separately** |

So: cloning this repo on a Mac gets you everything **except ComfyUI**, which
you install once (below). The models then download through the UI exactly as
they do on Windows.

---

## Installing ComfyUI on macOS

Apple Silicon only — Intel Macs have no usable GPU backend for this.

```bash
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# the video workflow needs this one custom node
cd custom_nodes
git clone https://github.com/city96/ComfyUI-GGUF.git
pip install -r ComfyUI-GGUF/requirements.txt
```

PyTorch's macOS wheels already include MPS support — there is no CUDA step.

Then from this repo:

```bash
./run.sh --comfy-root ~/ComfyUI
```

It remembers the path, so afterwards `./run.sh` is enough.

---

## What differs on a Mac

**Unified memory is the big one.** An M-series Mac shares memory between CPU
and GPU, so a 16 GB Mac has far more usable "VRAM" than a 4 GB GTX 1650. You
can raise resolution and frame count well past the Windows defaults in this
repo — start at 480×848 / 49 frames rather than 432×768 / 33.

**Speed is workload-dependent.** M-series GPUs have strong memory bandwidth but
fewer raw FLOPS than a modern discrete NVIDIA card. Expect an M1/M2 Pro to land
somewhere near a GTX 1650 for diffusion, and M3/M4 Max to be several times
quicker. Measure rather than assume — the UI calibrates itself after one run,
and it keeps separate calibration per machine because it lives in that
browser's local storage.

**No `nvidia-smi`.** Use Activity Monitor's GPU tab, or `sudo powermetrics
--samplers gpu_power`, to watch utilisation.

**Some ops fall back to CPU.** `PYTORCH_ENABLE_MPS_FALLBACK=1` is set for you.
Without it, an op with no MPS kernel aborts the whole run.

---

## Python version

PyTorch has no stable wheels for **Python 3.14**, and most custom nodes fail to
build against it. Use **3.11 or 3.12**.

On Windows this is handled for you: the ComfyUI portable build ships its own
embedded Python (3.13), and `run.bat` prefers it, so whatever is installed
system-wide is irrelevant. On macOS, create the venv with a supported version:

```bash
brew install python@3.12
python3.12 -m venv venv
```

---

## Ports

| Port | What |
|---|---|
| 8188 | ComfyUI engine |
| 8189 | This project's UI and model-download API |

Both bind to `127.0.0.1` only — nothing is exposed to your network.
