# OWN Video Generator

Local, free AI video generation for YouTube Shorts on a **GTX 1650 4 GB / i5-8600K / 32 GB**.

Runs entirely in your browser via ComfyUI. No cloud, no subscription, no watermark,
no upload of your prompts.

## The stack

| Layer | Choice | Why |
|---|---|---|
| Model | **Wan 2.1 T2V 1.3B** (FP16, 2.84 GB) | Best video model that genuinely fits in 4 GB |
| Speed LoRA | **Self-Forcing DMD 1.3B** rank 32 | 4 steps instead of 30 — the difference between 5 min and 45 min |
| Text encoder | **UMT5-XXL Q5_K_M GGUF** on the **CPU** | 4.15 GB instead of 11 GB, and costs 0 VRAM |
| UI | **ComfyUI portable** → `127.0.0.1:8188` | Browser-based, embedded Python, nothing else to install |
| Finishing | ffmpeg (CPU) | Upscale + interpolate without touching VRAM |

## Output

**432 × 768 @ 16 fps, 33 frames (2.06 s)** generated →
**1080 × 1920 @ 32 fps H.264** delivered.

Exact 9:16, no crop, ready to upload.

## Start here

1. **[docs/SETUP.md](docs/SETUP.md)** — installation, step by step.
   Steps 1–3 are the anti-crash configuration. Do not skip them.
2. **[docs/TUNING.md](docs/TUNING.md)** — every setting explained, the up/down tuning
   ladder, honest speed and quality expectations, troubleshooting table.
3. **[prompts/prompt_pack.md](prompts/prompt_pack.md)** — prompts written around what
   this model is actually good at.

## Quick version

```powershell
# 1. Extract ComfyUI_windows_portable_nvidia.7z to D:\ComfyUI\
#    https://github.com/Comfy-Org/ComfyUI/releases/latest

# 2. Start it once, then: Manager -> Custom Nodes -> install "ComfyUI-GGUF" -> Restart

# 3. Download the models (~7.3 GB, resumable)
powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI_windows_portable\ComfyUI"

# 4. Edit COMFY_PORTABLE and RESERVE at the top of scripts\run_comfyui.bat, then run it
scripts\run_comfyui.bat

# 5. Drag workflows\wan21_1.3b_shorts_432x768.json onto the canvas, prompt, Run

# 6. Finish the clip for Shorts (CPU only - queue the next one while this encodes)
scripts\finish_short.bat "D:\ComfyUI\...\output\short_00001.webm"
```

## What to expect, honestly

- **~4–9 minutes** per 2-second clip once warm; roughly **5–10 clips/hour**.
  (Estimated from your GPU's specs — time your first run and calibrate.)
- **Good at:** landscapes, water, fire, smoke, neon streets, macro texture, abstract,
  slow camera moves, single subjects, atmosphere and lighting.
- **Bad at:** text (always garbled), hands, faces, crowds, fast action. No setting fixes this.
- **Roughly 25–40% of Kling quality**, at 2 seconds instead of 10. For atmospheric
  B-roll that trade works. For people talking, it does not.
- A 30-second Short is **12–15 keeper clips**, about 2–3 hours of generation. Cutting
  on the music beat makes short clips read as deliberate editing rather than a limit.

Full detail in [docs/TUNING.md](docs/TUNING.md).

## Hardware notes specific to this PC

The GTX 1650 is Turing **SM75** — no tensor cores, no FP8. So SageAttention,
FlashAttention and `fp8_e4m3fn` weights are all off the table; this setup uses FP16
with PyTorch SDPA instead.

Three things measured on this machine that needed fixing, all covered in SETUP:

- **1594 MiB of 4096 MiB VRAM was already in use** at idle by the desktop, Chrome,
  VS Code and the NVIDIA overlay. Moving the display to the idle Intel UHD 630 iGPU
  is the single biggest win available.
- **Pagefile was 9 GB** — too small for `--lowvram` block streaming.
- **System Python is 3.14.3**, which PyTorch has no stable wheels for. The portable
  build ships its own embedded Python, which sidesteps it entirely.
