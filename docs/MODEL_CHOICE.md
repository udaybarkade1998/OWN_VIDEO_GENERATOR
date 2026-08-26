# Why Wan 2.1 T2V 1.3B — the alternatives, measured

Checked August 2026 against actual HuggingFace file sizes, not blog claims.

## The structural finding

**Open video models moved upmarket during 2025–2026 and left 4 GB behind.**

Everything released recently targets 12–32 GB cards:

| Model | Released | Size | Minimum VRAM |
|---|---|---|---|
| LTX-2.5 / LTX-2.3 | 2026 | 22B | 8 GB at Q4, 12 GB realistically |
| LTX-Video 0.9.8 distilled | 2025 | 13B | ~10 GB |
| Wan 2.2 T2V/I2V-A14B | 2025 | 14B | 6–8 GB with aggressive offload |
| Wan 2.2 TI2V-5B | 2025 | 5B | 8 GB |

None of these fit 4 GB. The viable small models are all from early-to-mid 2025 —
that generation is where the 4 GB tier stopped being served. **Wan 2.1 1.3B is the
high-water mark for your card, and waiting for something better at this size is not
a plan; the trend is going the other way.**

## The three real candidates, by weight budget

You have ~2.5 GB free VRAM (or ~3.9 GB with the display on the iGPU).

| Model | DiT weights | VAE | Total | Fits? |
|---|---|---|---|---|
| **Wan 2.1 T2V 1.3B FP16** | **2.84 GB** *(unquantized)* | **0.25 GB** | **3.09 GB** | ✅ |
| LTX 0.9.6 distilled 2B Q5_K_M | 1.48 GB | 2.49 GB | 3.97 GB | ⚠ tight |
| LTX 0.9.6 distilled 2B Q8_0 | 2.09 GB | 2.49 GB | 4.58 GB | ⚠ VAE must swap |
| Wan 2.2 TI2V-5B Q4_K_S | 3.12 GB | **1.41 GB** | 4.53 GB | ❌ thrashes |
| Wan 2.2 TI2V-5B Q3_K_M | 2.55 GB | 1.41 GB | 3.96 GB | ❌ Q3 quality collapse |

## The decisive argument

**Wan 2.1 1.3B is the only model in this class you can run at full FP16 precision on
4 GB.** Every alternative requires quantization deep enough to eat the advantage of
being a bigger model in the first place.

A 5B at Q4 is not reliably better than a 1.3B at FP16 — you are trading real
parameters for damaged ones. And Wan 2.2's VAE is **1.41 GB versus 0.25 GB**, a 5.6×
tax paid out of the exact budget you cannot afford.

Three more reasons Wan 2.2 TI2V-5B loses here specifically:

1. It is trained natively at **720p / 24 fps**. Running it at 432×768 puts you far
   outside its distribution — you pay for 5B parameters and get worse output than the
   1.3B that was trained at 480p.
2. Its 4-step distill LoRA ecosystem is thinner than Wan 2.1 1.3B's.
3. The high-compression VAE that makes it efficient at 720p gives back much less at
   the small resolutions you are forced into.

## The one genuine trade-off: LTX 0.9.6 distilled

This is the only alternative worth taking seriously, and it is a **speed** play, not
a quality play:

| | Wan 2.1 1.3B | LTX 0.9.6 distilled 2B |
|---|---|---|
| Est. time / 2 s clip | ~4–9 min | **~1–3 min** |
| Prompt adherence | **Good** | Weak — needs very long, very literal prompts |
| Motion quality | **Coherent** | Faster but smearier on complex scenes |
| Native resolution | 480p | 768×512 |
| Max clip length | short | **much longer** (257 frames) |
| VAE compression | 8×8×4 | 32×32×8 (why it's fast) |
| Ecosystem / LoRAs | **Mature** | Abandoned — no 2B successor after 0.9.6 |

**When LTX would be the better choice:** you care more about volume than per-clip
quality. Since a 30-second Short needs 12–15 keepers, a 3× speedup is worth real
consideration — it turns a 2–3 hour batch into under an hour.

**Why it is still second choice:** its 2.49 GB VAE eats the memory the smaller DiT
saves, its prompt adherence is materially worse (you will discard more clips, which
partly cancels the speed win), and Lightricks abandoned the 2B line — 0.9.6 from
April 2025 is the last one.

## Verdict

Keep **Wan 2.1 T2V 1.3B FP16 + Self-Forcing DMD 4-step LoRA**. It wins on quality per
VRAM, it is the only full-precision option that fits, it has the most mature ComfyUI
support, and the tiny 0.25 GB VAE leaves headroom for the resolution and frame count
that actually show up in the final upload.

If throughput becomes the bottleneck once you have run real batches, LTX 0.9.6
distilled is the fallback to test — but decide that from your own measured numbers,
not in advance.
