# Tuning, expectations, and troubleshooting

## The exact settings this workflow ships with

| Parameter | Value | Node |
|---|---|---|
| Resolution | **432 × 768** (exact 9:16) | `EmptyHunyuanLatentVideo` |
| Frame count | **33** | `EmptyHunyuanLatentVideo` |
| Native FPS | **16** | `SaveWEBM` |
| Clip length | **2.06 s** | 33 ÷ 16 |
| Steps | **4** | `KSampler` |
| CFG | **1.0** | `KSampler` |
| Sampler | **lcm** | `KSampler` |
| Scheduler | **simple** | `KSampler` |
| Denoise | **1.0** | `KSampler` |
| Shift | **5.0** | `ModelSamplingSD3` |
| LoRA strength | **1.0** | `LoraLoaderModelOnly` |
| VAE tile / overlap | **256 / 64** | `VAEDecodeTiled` |
| VAE temporal / overlap | **8 / 2** | `VAEDecodeTiled` |
| Text encoder device | **cpu** | `CLIPLoaderGGUF` |

Delivered to YouTube as **1080 × 1920 @ 32 fps H.264** after `finish_short.bat`.

---

## Why 432 × 768 specifically

Three constraints have to be satisfied at once, and this is the resolution that
satisfies all three:

1. **Exactly 9:16.** 432:768 reduces to 9:16 — no cropping, no letterboxing, no
   squeezed faces on upload.
2. **Divisible by 16.** Wan's VAE compresses 8× spatially, then the transformer
   patchifies 2×2. Anything not divisible by 16 gets silently padded and you lose
   edge detail.
3. **Upscales by exactly 2.5× to 1080 × 1920.** A clean integer-ish ratio means
   Lanczos has an easy job. Compare 480×832 (Wan's own default), which is *not* 9:16
   and needs an awkward 2.25× plus a crop.

It also sits close to Wan 2.1's 480p training area (331k px vs 399k px), so you stay
inside the distribution the model actually learned. Go much below this and coherence
falls apart fast — see the ladder below.

## Why frames cost more than pixels

The transformer attends over the whole spatiotemporal token sequence, so cost is
**quadratic in total tokens**, and frames multiply tokens just like pixels do:

| Setting | Latent | Tokens | Attention cost |
|---|---|---|---|
| 432×768, 33f | 54×96×9 | 11,664 | 1.0× (baseline) |
| 480×832, 33f | 60×104×9 | 14,040 | ~1.4× |
| 432×768, 49f | 54×96×13 | 16,848 | **~2.1×** |
| 432×768, 81f | 54×96×21 | 27,216 | ~5.4× |

**Going from 2 s to 3 s costs you more than raising the resolution does.** If you have
headroom to spend, spend it on resolution first — it shows up in the final upload.

Frame count must always be **4n+1** (Wan's VAE compresses 4× temporally):
17, 21, 25, 29, **33**, 37, 41, 45, 49…

---

## The tuning ladder

**If it runs and you have VRAM headroom** (check `nvidia-smi` during a run), climb up:

| Step | Change | Cost |
|---|---|---|
| 1 | Resolution → **480 × 848** | +40% time, visibly sharper |
| 2 | Steps → **6** | +50% time, better detail and motion |
| 3 | Frames → **49** (3.06 s) | +110% time |
| 4 | Resolution → **576 × 1024** | likely OOM on 4 GB — try only with the monitor on the iGPU |

**If you get OOM or it takes forever**, climb down in this order:

| Step | Change |
|---|---|
| 1 | Frames 33 → **25** (1.56 s) — cheapest win, quadratic saving |
| 2 | `VAEDecodeTiled` tile_size 256 → **192**, temporal_size 8 → **4** |
| 3 | Resolution → **384 × 688** (still ~9:16, still ÷16) |
| 4 | `RESERVE` in the .bat → raise by 0.3 |
| 5 | Swap `--lowvram` → **`--novram`** in the .bat (much slower, nearly always fits) |
| 6 | Text encoder → `umt5-xxl-encoder-Q4_K_M.gguf` (3.66 GB, saves RAM not VRAM) |

Do **not** go below 384 px wide. Wan 2.1 1.3B degrades sharply outside its training
range — you get mush and temporal flicker, not just softness.

---

## Sampler alternatives

The shipped `lcm` / `simple` / 4 steps / CFG 1.0 / shift 5.0 is a safe default for the
Self-Forcing DMD LoRA. Worth trying:

| Variation | When |
|---|---|
| sampler → `euler`, scheduler → `beta` | Motion looks mushy or smeared |
| shift → `3.0` | Too much drift/warping |
| shift → `8.0` | Too static, want more motion |
| steps → `6`, LoRA strength → `0.8` | Detail looks over-smoothed by the distillation |
| Swap LoRA → `Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors`, steps `6` | Alternative distill; sometimes better on camera motion |

**CFG must stay at 1.0** while a distill LoRA is active. Raising it doubles your
generation time (it re-enables the negative-prompt pass) and produces artifacts,
because these LoRAs are CFG-distilled. If you want real CFG, bypass the LoRA node and
use 25–30 steps at CFG 6 — expect roughly 6× the time.

---

## Honest expectations

### Speed

These are **estimates from your card's specs**, not measurements — the GTX 1650 has
~2.9 TFLOPS FP32 and **no tensor cores**, putting it roughly 8–10× behind an RTX 3060
for FP16 diffusion. There are also GDDR5 (128 GB/s) and GDDR6 (192 GB/s) versions of
the 1650, and at `--lowvram` you are partly bandwidth-bound, so your mileage will vary.

| Stage | Expected |
|---|---|
| First run of a session (model load from disk) | **+1–3 min** one time |
| Generation, 432×768 / 33f / 4 steps, warm | **~4–9 min** |
| Tiled VAE decode | ~30–60 s of that |
| `finish_short.bat` (CPU, ffmpeg) | ~40–90 s, in parallel |
| Realistic throughput | **roughly 5–10 clips/hour** |

**Time your first run and adjust the ladder from the real number** — don't take my
estimate as fact. Watch the ComfyUI console; it prints per-step `it/s`.

If a run takes dramatically longer than this, you are almost certainly spilling into
sysmem fallback. Drop frames to 25 and re-check.

### Quality — what you are actually getting

Wan 2.1 T2V 1.3B is genuinely the best thing that fits in 4 GB, and it is still a
1.3-billion-parameter model at 432 px. Be realistic:

**It does these well:**
- Landscapes, nature, weather, clouds, water, fire, smoke
- Slow deliberate camera moves — push-in, drift, tilt, orbit
- Close-up textures and macro shots
- Abstract, atmospheric, cinematic B-roll
- One clear subject with simple motion
- Lighting and mood — god rays, golden hour, neon, fog

**It does these badly, and no setting will fix it:**
- **Text** — always garbled. Add it in an editor afterwards.
- **Hands and fingers** — expect deformity
- **Faces at 432 px wide** — soft, and they drift between frames
- Crowds, multiple interacting subjects
- Fast or complex action, dancing, sports
- Anything needing precise object permanence over the clip

**Set against Kling / Veo / Sora:** you are getting maybe 25–40% of that quality, at
2 seconds instead of 10, in 5–10 minutes instead of 30 seconds. What you get in
exchange is unlimited free generations with no queue, no watermark, and no upload of
your prompts. For atmospheric Shorts B-roll that is a real trade. For anything with
people talking, it is not.

**Practical workflow:** generate 5–10 variations of the same prompt with different
seeds, keep the 1–2 that work, and cut them together. A 30-second Short is 12–15 of
these clips. That is the realistic path to a publishable video on this hardware, and
it is how the 2-second limit stops being a limit.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `CUDA out of memory` | Climb down the ladder. Confirm Sysmem Fallback is on (SETUP step 2). |
| `no kernel image is available` | Wrong CUDA build — get the `_cu126` portable asset. |
| Red node: `CLIPLoaderGGUF` | ComfyUI-GGUF not installed. SETUP step 5. |
| Node says model not found | File in the wrong folder. Check the table in SETUP step 6, then **Refresh** in the UI. |
| Output is black or solid green | VAE precision. Change `--fp16-vae` to `--fp32-vae` in the .bat. |
| Output is static, barely moves | Raise shift to 8.0; add explicit camera motion to the prompt. |
| Output is a flickering mess | Steps too low or resolution too low. Steps → 6, confirm width ≥ 432. |
| Whole PC freezes during a run | Pagefile too small (SETUP step 3), or `RESERVE` too low. |
| Very slow, GPU sits near 30% | Sysmem-fallback spilling. Cut frames to 25. |
| Downloads stall at 0% | ProtonVPN. Disconnect it and retry — the script resumes. |
| Browser tab makes generation slower | Expected — the ComfyUI tab is itself on the GPU unless you did SETUP step 1. |

## Files in this repo

| Path | What |
|---|---|
| [workflows/wan21_1.3b_shorts_432x768.json](../workflows/wan21_1.3b_shorts_432x768.json) | The ComfyUI workflow — drag onto the canvas |
| [scripts/run_comfyui.bat](../scripts/run_comfyui.bat) | Launcher with the tuned arguments |
| [scripts/download_models.ps1](../scripts/download_models.ps1) | Downloads all 5 model files |
| [scripts/finish_short.bat](../scripts/finish_short.bat) | 432×768@16 → 1080×1920@32 MP4 |
| [scripts/finish_short_fast.bat](../scripts/finish_short_fast.bat) | Same, no motion interpolation |
| [prompts/prompt_pack.md](../prompts/prompt_pack.md) | Prompts shaped to this model's strengths |
