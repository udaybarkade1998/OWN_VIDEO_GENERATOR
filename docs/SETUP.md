# Setup — Wan 2.1 T2V 1.3B on a GTX 1650 4GB

Follow in order. Steps 1–3 are not optional: they are what makes the difference
between "runs" and "crashes".

---

## 0. What your machine actually reports

Measured on this PC, not assumed:

| Component | Value | Verdict |
|---|---|---|
| GPU | GeForce GTX 1650, **4096 MiB** | Turing SM75 |
| **VRAM already in use at idle** | **1594 MiB** | ⚠ only ~2.5 GB free |
| CPU | i5-8600K, **6 cores / 6 threads** (no HT) | fine; offload is RAM-bound |
| RAM | 32 GB @ 2133 MHz (4×8) — 14 GB free | good |
| Driver | 591.86 (CUDA 13.1) | current |
| Pagefile | **9216 MB** | ⚠ too small |
| System Python | **3.14.3** | ⚠ too new for PyTorch |
| iGPU | Intel UHD 630, **active** | ⚠ unused — this is your free win |
| Disk | C: 141 GB free, D: 204 GB free | fine |

Three things above will bite you. Steps 1–3 fix them.

### Why SM75 matters

The GTX 1650 has **no tensor cores** and **no FP8 units**. So:

- Do **not** install SageAttention or FlashAttention — they require Ampere (SM80+).
- Do **not** use `fp8_e4m3fn` model files — they get upcast, costing speed *and* memory.
- **Do** use FP16 weights + PyTorch SDPA cross-attention. That is what this setup uses.

---

## 1. Free your VRAM — biggest single win

You are burning **1594 MiB of 4096 MiB** before generating anything. That is 39% of
your card lost to the Windows desktop, Chrome, VS Code and the NVIDIA overlay.

**Best fix: move the monitor to the motherboard.**

Your i5-8600K has Intel UHD 630 and it is already enabled. Unplug the 3440×1440
display from the GTX 1650 and plug it into the **motherboard's HDMI/DisplayPort**.
The GTX 1650 then becomes a pure compute card with ~3.9 GB free instead of ~2.5 GB.

> Use the motherboard's **DisplayPort** if it has one — UHD 630 over HDMI 1.4 is
> limited to 30 Hz at 3440×1440, while DisplayPort gives you 60 Hz.

**If you will not move the cable**, do these instead (recovers roughly 700–900 MiB):

1. Settings → System → Display → Graphics → set **Chrome**, **VS Code** and
   **Edge WebView** to **Power saving (Intel UHD 630)**.
2. Chrome → Settings → System → turn **off** "Use graphics acceleration when available".
3. NVIDIA App → Settings → Features → **In-Game Overlay: Off**
   (`NVIDIA Overlay.exe` was holding VRAM at idle on your machine).
4. Settings → System → Display → Graphics → Advanced →
   **Hardware-accelerated GPU scheduling: Off**.

Then set `RESERVE` in `scripts\run_comfyui.bat` to match:

- monitor on the **iGPU** → `set "RESERVE=0.6"`
- monitor still on the **GTX** → `set "RESERVE=1.8"`

Check your idle usage any time:

```
nvidia-smi --query-gpu=memory.used,memory.free --format=csv
```

---

## 2. Stop hard OOM crashes (NVIDIA Control Panel)

Right-click desktop → **NVIDIA Control Panel** → *Manage 3D Settings* →
**Program Settings** tab → **Add** → browse to your portable's
`python_embeded\python.exe`.

Set for that program:

| Setting | Value |
|---|---|
| **CUDA — Sysmem Fallback Policy** | **Prefer Sysmem Fallback** |
| Power management mode | Prefer maximum performance |
| Low Latency Mode | Off |

**Sysmem Fallback is the anti-crash switch.** When a step would exceed 4 GB, the
driver spills into system RAM instead of throwing `CUDA out of memory` and killing
the run. It costs speed on the spilling step — that trade is exactly what you asked
for ("realistically run without crashes").

> If you would rather get a clean instant error than a silently slow run, set it to
> *Prefer No Sysmem Fallback*. Don't do that until you are comfortable with the
> tuning ladder in [TUNING.md](TUNING.md).

---

## 3. Raise the pagefile

`--lowvram` streams model blocks between VRAM and system RAM. With a browser open,
your 9 GB pagefile is the weak link.

Win+R → `sysdm.cpl` → Advanced → Performance **Settings** → Advanced →
Virtual memory **Change** → untick *Automatically manage* → select **D:** (more free
space, and it keeps write churn off your system drive) → **Custom size**:

- Initial size: `32768`
- Maximum size: `65536`

Set → OK → **reboot**.

---

## 4. Install ComfyUI (portable — browser UI, nothing else to install)

Download the latest Windows portable NVIDIA build:

**https://github.com/Comfy-Org/ComfyUI/releases/latest**
→ asset `ComfyUI_windows_portable_nvidia.7z` (~2.1 GB)

Extract with 7-Zip to a **short path on D:**, e.g. `D:\ComfyUI\`.
You should end up with `D:\ComfyUI\ComfyUI_windows_portable\`.

> **This is why your Python 3.14.3 does not matter.** The portable ships its own
> embedded Python. Do **not** `pip install` into your system Python, and do **not**
> use the git/manual install route — PyTorch has no stable 3.14 wheels and most
> custom nodes will fail to build against it. The portable sidesteps all of that.

> If ComfyUI starts but errors with `no kernel image is available for execution`,
> that build's CUDA arch list didn't include your card. Re-download the
> `ComfyUI_windows_portable_nvidia_cu126.7z` asset instead — cu126 definitely
> includes SM75.

You do **not** need the ComfyUI Desktop app. The portable serves its UI to your
browser at `http://127.0.0.1:8188`.

---

## 5. Install the one required custom node

Start ComfyUI once (`run_nvidia_gpu.bat` inside the portable folder), then in the
browser UI: **Manager → Custom Nodes Manager → search `GGUF` → install
"ComfyUI-GGUF" (city96) → Restart**.

That is the only custom node this workflow needs. It loads the quantized text
encoder, which is what keeps the 11 GB UMT5 encoder off your GPU entirely.

No Manager button? Install it manually, then restart:

```
cd D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes
git clone https://github.com/Comfy-Org/ComfyUI-Manager.git
```

---

## 6. Download the models (~7.3 GB)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI_windows_portable\ComfyUI"
```

It resumes on interruption and skips anything already downloaded.
**Turn ProtonVPN off first** — it frequently throttles or breaks HuggingFace CDN pulls.

| File | Goes to | Size |
|---|---|---|
| `wan2.1_t2v_1.3B_fp16.safetensors` | `models\diffusion_models\` | 2.84 GB |
| `umt5-xxl-encoder-Q5_K_M.gguf` | `models\text_encoders\` | 4.15 GB |
| `wan_2.1_vae.safetensors` | `models\vae\` | 254 MB |
| `Wan2_1_self_forcing_dmd_1_3B_lora_rank_32_fp16.safetensors` | `models\loras\` | 91 MB |
| `Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors` | `models\loras\` | 91 MB |

**Why these exact files, on your card:**

- **FP16 (not GGUF) for the video model.** The 1.3B is only 2.84 GB at FP16.
  Quantizing it would save ~1 GB but visibly costs quality, and there is no published
  GGUF for Wan 2.1 T2V 1.3B anyway. Spend your VRAM budget here.
- **GGUF (not FP16) for the text encoder.** UMT5-XXL is 11 GB at FP16. Q5_K_M is
  4.15 GB with no meaningful prompt-fidelity loss, and `--lowvram` keeps it
  off the GPU, so it costs effectively **0 VRAM** during sampling. This is the single biggest saving in the stack.
- **Not the `fp8_e4m3fn` encoder** that ComfyUI's official example uses — your SM75
  card has no FP8 units, so you would get the worst of both worlds.

---

## 7. Load the workflow and run

1. Launch with **`scripts\run_comfyui.bat`** (edit `COMFY_PORTABLE` and `RESERVE` at
   the top first). It opens your browser automatically.
2. Drag **`workflows\wan21_1.3b_shorts_432x768.json`** onto the ComfyUI canvas.
3. Type your prompt into the **Positive prompt** node.
4. Click **Run**.

Output lands in `ComfyUI\output\` as `short_00001.webm` — 432×768 at 16 fps.

5. Finish it for Shorts:

```
scripts\finish_short.bat "D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\output\short_00001.webm"
```

That produces `short_00001_1080x1920.mp4` — 1080×1920, 32 fps, H.264.

Needs ffmpeg: `winget install Gyan.FFmpeg` (then reopen your terminal).

The finishing step is **CPU-only and uses zero VRAM**, so queue your next clip in
ComfyUI while it encodes — your 6 cores are otherwise idle during generation.
