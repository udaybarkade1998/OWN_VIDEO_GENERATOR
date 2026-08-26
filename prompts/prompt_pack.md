# Prompt pack — shaped to what Wan 2.1 1.3B does well

## The formula

Wan responds to a specific ordering. Use it:

```
[shot type] + [subject] + [subject motion] + [camera motion] + [lighting] + [atmosphere] + [film look]
```

Concrete example:

> Cinematic vertical shot, a lone red maple leaf floating on dark still water,
> slowly rotating, camera drifting slowly downward, soft overcast light,
> light mist on the surface, shallow depth of field, film grain, 35mm

### Rules that actually matter

- **Always name a camera motion.** Without one the model tends to produce a near-still
  image. Use: *slow push in / drifting forward / slow pan left / tilting up /
  orbiting slowly / tracking alongside / static locked-off shot*.
- **One subject, one action.** Two subjects interacting is where 1.3B falls apart.
- **Say "vertical"** early — it nudges composition toward the 9:16 frame.
- **Describe light explicitly.** It is the single biggest lever on perceived quality:
  *golden hour, god rays, volumetric, backlit, rim light, neon reflections, overcast diffuse*.
- **Keep it 25–60 words.** Longer prompts do not help at 1.3B; they dilute.
- **Never prompt for text.** It will be garbled. Add titles in your editor.
- **Motion adverbs should be slow.** *Slowly, gently, gradually, drifting.* Fast motion
  breaks temporal coherence at this size.

The negative prompt in the workflow is already the official Wan one — leave it alone
unless you have a specific artifact to fight.

---

## Ready-to-use prompts

### Nature and landscape — the model's strongest category

> Cinematic vertical shot, slow tracking camera drifting forward through a misty pine forest at sunrise, thick volumetric god rays cutting between the trunks, soft golden light, drifting fog, shallow depth of field, film grain, 35mm

> Vertical aerial shot slowly pushing in over a turquoise glacial lake surrounded by dark jagged peaks, thin clouds drifting below, crisp cold morning light, cinematic color grade

> Vertical macro shot of morning dew on a spiderweb, droplets trembling gently, camera slowly drifting right, backlit by low golden sunlight, dark blurred background, extreme shallow depth of field

> Cinematic vertical shot of tall grass rippling in slow waves across a hillside, camera tracking slowly left, warm late afternoon backlight, dust motes in the air, soft haze

### Water, fire, smoke — great temporal behaviour

> Vertical slow motion shot of a single water droplet falling into a black reflective pool, concentric ripples spreading outward, camera static and locked off, dramatic single side light, deep shadows

> Cinematic vertical close-up of orange embers rising from a campfire into the night, camera slowly tilting up, glowing sparks drifting, dark blue background, shallow focus

> Vertical shot of thick white smoke curling slowly through a dark room, camera drifting slowly forward, single hard beam of light cutting through it, high contrast, moody

> Vertical shot of an ocean wave curling and breaking in slow motion, camera tracking alongside, late golden hour backlight through the water, spray catching the light

### Urban and neon — strong at night, hides detail weakness

> Cinematic vertical shot of rain falling on a neon-lit city street at night, reflections rippling in dark puddles, camera slowly pushing forward, pink and cyan neon glow, dense atmosphere, anamorphic

> Vertical shot looking straight up between tall glass skyscrapers, camera slowly rotating, low clouds passing overhead, cold blue morning light, symmetrical composition

> Vertical shot of a rain-covered window at night, city bokeh lights blurred behind it, droplets slowly running down the glass, camera static, warm orange and blue tones

### Abstract and texture — very reliable, great filler B-roll

> Vertical macro shot of iridescent oil swirling slowly on dark water, colours shifting through purple and gold, camera drifting slowly, soft even light

> Vertical shot of black ink diffusing slowly into clear water, tendrils spreading organically, camera slowly pushing in, bright clean backlight, white background

> Vertical shot of thick colourful paint slowly folding into itself, deep saturated reds and blues, camera static macro, soft studio light, glossy texture

### Single subject with motion — works if you keep it simple

> Cinematic vertical shot of a lone wolf standing on a snowy ridge, fur moving in the wind, camera slowly orbiting, overcast diffuse light, falling snow, muted cold colour grade

> Vertical shot of a hot air balloon drifting slowly across a pale dawn sky, camera slowly tilting up to follow, soft pink and orange gradient, thin high clouds

> Vertical shot of a single candle flame flickering gently in a dark room, camera slowly pushing in, warm orange glow falling off into black, shallow depth of field

---

## Building a real 30-second Short

At 2 seconds per clip you need **12–15 keepers**. Plan for that:

1. Pick a theme (one of the categories above) and write **5 prompt variations**.
2. Queue each **3 times with different seeds** — set the KSampler seed control to
   `randomize` and hit Run three times. That's 15 clips queued.
3. Let it run — roughly **2–3 hours** at 5–10 clips/hour. Work on something else;
   with the monitor on the iGPU the machine stays responsive.
4. Keep the ~60% that hold together. Discard flicker and warping without hesitation —
   it is free to generate more.
5. Run `finish_short.bat` on the keepers.
6. Cut them together in any free editor (DaVinci Resolve, CapCut, Shotcut), add music
   and any text overlays **there**, not in the prompt.

**Cutting on the beat hides a lot.** Two-second clips cut to a music beat read as
deliberate editing rather than a technical limit — this is the main reason short clips
are not the problem they sound like.

---

# Image prompts (SDXL)

Different model, different rules. SDXL is **not** Wan — no camera motion needed,
and it responds to comma-separated tags more than flowing sentences.

## What actually matters

**Use SDXL's own aspect ratios.** This is the single biggest quality lever and it
has nothing to do with your prompt. SDXL was trained on fixed resolution buckets
around 1 megapixel. Push it taller than 832×1216 and it either shrinks the subject
to a speck or duplicates it to fill the frame:

| Resolution | Result |
|---|---|
| **832 × 1216** | ✅ default — tallest bucket that still behaves |
| **896 × 1152** | ✅ most detail, slightly wider |
| 768 × 1344 | ⚠ starts duplicating |
| 720 × 1280 | ❌ subject shrinks badly, or you get two of it |

Generate at a native ratio, then `scripts/finish_image.bat` (or `.sh`) upscales and
centre-crops to 1080×1920 for Shorts.

**8 steps, not 4.** With the Lightning LoRA, 8 steps is visibly sharper than 4 for
about 15 extra seconds. 4 is for drafts.

**Length.** 15–40 words. "best car" gives you a generic stock photo — the model has
nothing to work with. Name the subject, the lens, the light, and the mood.

## Formula

```
[subject] + [what it's doing / how it sits] + [setting] +
[lighting] + [lens / camera] + [style words]
```

> a vintage orange muscle car parked on a tree-lined street, low angle,
> golden hour light, shallow depth of field, highly detailed, 35mm photo

## Things SDXL cannot do

- **Text and logos.** "channel logo with the text Ud2056 Gaming" will never work —
  it produces letter-shaped noise. Generate the artwork, add real text in Canva,
  Photoshop or your video editor.
- **Maps, diagrams, charts.** "india map" gives you a vaguely map-shaped blob.
  Use a real map image.
- **Accurate counts.** "five birds" gives you some birds.
- **Specific real people.** Not reliably, and it's a bad idea for a public channel.

## Useful style suffixes

| Want | Append |
|---|---|
| Photoreal | `35mm photo, shallow depth of field, natural light, highly detailed` |
| Cinematic | `cinematic lighting, anamorphic, film grain, colour graded` |
| Product shot | `studio lighting, seamless background, product photography, sharp focus` |
| Illustration | `digital illustration, clean linework, vibrant colours, flat shading` |
| Thumbnail punch | `dramatic rim light, high contrast, bold colours, centred composition` |

## Negative prompt

Already applied for you, including anti-duplication terms
(`duplicate, repeated subject, collage, split screen, grid`). You don't need to
add anything unless you're fighting a specific artifact.
