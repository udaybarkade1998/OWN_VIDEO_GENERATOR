#!/usr/bin/env python3
"""
OWN Video Generator - local helper server.

Serves the UI and gives it the two things a browser cannot do on its own:
  * see whether the model files exist on disk
  * download them into ComfyUI's models folder, with live progress

Uses only the standard library, so it runs on ComfyUI's embedded Python
and needs nothing installed.

    python ovg_server.py --comfy-root "D:\\ComfyUI\\ComfyUI_windows_portable\\ComfyUI"
"""

import argparse
import http.server
import json
import os
import socketserver
import threading
import time
import platform
import struct
import urllib.request
from pathlib import Path

PLATFORM = platform.system()

# ---------------------------------------------------------------- model list

HF = "https://huggingface.co"

# Models are grouped by mode so the UI can download only what that mode needs.
VIDEO_MODELS = [
    {
        "key": "unet",
        "name": "wan2.1_t2v_1.3B_fp16.safetensors",
        "subdir": "diffusion_models",
        "size": 2838303560,
        "what": "Wan 2.1 T2V 1.3B video model (FP16)",
        "url": f"{HF}/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/"
               "split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors",
    },
    {
        "key": "clip",
        "name": "umt5-xxl-encoder-Q5_K_M.gguf",
        "subdir": "text_encoders",
        "size": 4145878880,
        "what": "UMT5-XXL text encoder (Q5_K_M, runs on CPU)",
        "url": f"{HF}/city96/umt5-xxl-encoder-gguf/resolve/main/umt5-xxl-encoder-Q5_K_M.gguf",
    },
    {
        "key": "vae",
        "name": "wan_2.1_vae.safetensors",
        "subdir": "vae",
        "size": 253815318,
        "what": "Wan 2.1 VAE",
        "url": f"{HF}/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/"
               "split_files/vae/wan_2.1_vae.safetensors",
    },
    {
        "key": "lora_dmd",
        "name": "Wan2_1_self_forcing_dmd_1_3B_lora_rank_32_fp16.safetensors",
        "subdir": "loras",
        "size": 91233416,
        "what": "Self-Forcing DMD speed LoRA",
        "url": f"{HF}/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan2_1_self_forcing_1_3B/"
               "Wan2_1_self_forcing_dmd_1_3B_lora_rank_32_fp16.safetensors",
    },
    {
        "key": "lora_causvid",
        "name": "Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors",
        "subdir": "loras",
        "size": 91233416,
        "what": "CausVid bidirectional speed LoRA",
        "url": f"{HF}/Kijai/WanVideo_comfy/resolve/main/"
               "Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors",
    },
]

IMAGE_MODELS = [
    {
        "key": "sdxl",
        "name": "sd_xl_base_1.0.safetensors",
        "subdir": "checkpoints",
        "size": 6938078334,
        "what": "SDXL base 1.0 - image model (includes its text encoders)",
        "url": f"{HF}/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/"
               "sd_xl_base_1.0.safetensors",
    },
    {
        "key": "sdxl_lightning",
        "name": "sdxl_lightning_4step_lora.safetensors",
        "subdir": "loras",
        "size": 393854592,
        "what": "SDXL-Lightning 4-step LoRA - 4 steps instead of 30",
        "url": f"{HF}/ByteDance/SDXL-Lightning/resolve/main/"
               "sdxl_lightning_4step_lora.safetensors",
    },
    {
        "key": "sdxl_vae",
        "name": "sdxl_vae.safetensors",
        "subdir": "vae",
        "size": 334641162,
        "what": "SDXL VAE (fp16-fix build)",
        "url": f"{HF}/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors",
    },
]

MODEL_SETS = {"video": VIDEO_MODELS, "image": IMAGE_MODELS}


def models_for(mode):
    return MODEL_SETS.get(mode, VIDEO_MODELS)

COMFY_ROOT = None
UI_DIR = None

# ------------------------------------------------------------ download state

STATE = {
    "active": False,
    "current": None,
    "done_keys": [],
    "error": None,
    "files": {},     # key -> {got, total, speed}
    "started": 0,
    "mode": None,
}
LOCK = threading.Lock()

CONNECTIONS = 16          # HuggingFace throttles per connection; parallel ranges fix it
CHUNK = 1 << 20


def target_path(m):
    return Path(COMFY_ROOT) / "models" / m["subdir"] / m["name"]


def remote_size(url):
    """Ask the server how big the file really is. Never trust a hardcoded size:
    getting it wrong by even a few bytes truncates the download silently."""
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as r:
        n = r.headers.get("X-Linked-Size") or r.headers.get("Content-Length")
        return int(n)


def safetensors_ok(path):
    """Parse the header and confirm every tensor actually fits in the file.
    Catches truncation that a size comparison cannot."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            if not (0 < n < size):
                return False
            head = json.loads(f.read(n))
        end = max(v["data_offsets"][1] for k, v in head.items() if k != "__metadata__")
        return 8 + n + end == size
    except Exception:
        return False


def gguf_ok(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"GGUF"
    except Exception:
        return False


def have(m):
    """Complete and structurally valid under its final name."""
    p = target_path(m)
    if not p.exists() or p.stat().st_size == 0:
        return False
    if p.suffix == ".safetensors":
        return safetensors_ok(p)
    if p.suffix == ".gguf":
        return gguf_ok(p) and p.stat().st_size == m["size"]
    return p.stat().st_size == m["size"]


def partial_bytes(m):
    """Bytes already fetched into a leftover .part from an interrupted run."""
    p = target_path(m)
    part = p.with_suffix(p.suffix + ".part")
    return part.stat().st_size if part.exists() else 0


def _range_worker(url, path, start, end, key, lock):
    """Fetch one byte range and write it at its offset."""
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "r+b") as f:
        f.seek(start)
        while True:
            buf = r.read(CHUNK)
            if not buf:
                break
            f.write(buf)
            with lock:
                STATE["files"][key]["got"] += len(buf)


def download_one(m):
    key, url = m["key"], m["url"]
    try:
        total = remote_size(url)              # authoritative
    except Exception:
        total = m["size"]                     # fall back to the listed estimate
    path = target_path(m)
    part = path.with_suffix(path.suffix + ".part")
    path.parent.mkdir(parents=True, exist_ok=True)

    with LOCK:
        STATE["current"] = key
        STATE["files"][key] = {"got": 0, "total": total, "speed": 0}

    # Preallocate so the range workers can seek and write in place. This happens
    # on the .part file, never the real name, so a half-written model can never
    # be mistaken for a complete one.
    with open(part, "wb") as f:
        f.truncate(total)

    span = total // CONNECTIONS
    lock = threading.Lock()
    threads = []
    for i in range(CONNECTIONS):
        a = i * span
        b = (total - 1) if i == CONNECTIONS - 1 else (a + span - 1)
        t = threading.Thread(target=_range_worker,
                             args=(url, part, a, b, key, lock), daemon=True)
        t.start()
        threads.append(t)

    t0, last, lastb = time.time(), time.time(), 0
    while any(t.is_alive() for t in threads):
        time.sleep(0.5)
        now = time.time()
        with LOCK:
            got = STATE["files"][key]["got"]
            if now - last >= 1.0:
                STATE["files"][key]["speed"] = (got - lastb) / (now - last)
                last, lastb = now, got
    for t in threads:
        t.join()

    got = part.stat().st_size
    downloaded = STATE["files"][key]["got"]
    if got != total or downloaded < total:
        part.unlink(missing_ok=True)
        raise IOError(f"{m['name']}: wrote {downloaded} of {total} bytes - incomplete")
    if part.suffix == ".part" and path.suffix == ".safetensors" and not safetensors_ok(part):
        part.unlink(missing_ok=True)
        raise IOError(f"{m['name']}: downloaded but the safetensors header does not "
                      f"match the file - treating as corrupt")
    part.replace(path)                      # atomic: only now does it "exist"
    with LOCK:
        STATE["files"][key]["got"] = total
        STATE["done_keys"].append(key)


def download_all(mode):
    try:
        for m in models_for(mode):
            if have(m):
                with LOCK:
                    if m["key"] not in STATE["done_keys"]:
                        STATE["done_keys"].append(m["key"])
                        STATE["files"][m["key"]] = {"got": m["size"],
                                                    "total": m["size"], "speed": 0}
                continue
            download_one(m)
    except Exception as e:                                   # noqa: BLE001
        with LOCK:
            STATE["error"] = f"{type(e).__name__}: {e}"
    finally:
        with LOCK:
            STATE["active"] = False
            STATE["current"] = None


# ------------------------------------------------------------------ handler

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(UI_DIR), **kw)

    def log_message(self, fmt, *args):
        pass                                                  # keep the console clean

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/gallery"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            limit = int((qs.get("limit") or ["300"])[0])
            kind = (qs.get("kind") or ["all"])[0]
            out = Path(COMFY_ROOT) / "output"
            exts = {"image": {".png", ".jpg", ".jpeg", ".webp"},
                    "video": {".webm", ".mp4", ".gif"}}
            want = exts.get(kind) or (exts["image"] | exts["video"])
            items = []
            if out.is_dir():
                for f in out.rglob("*"):
                    if not f.is_file() or f.suffix.lower() not in want:
                        continue
                    try:
                        st = f.stat()
                    except OSError:
                        continue
                    items.append({
                        "filename": f.name,
                        "subfolder": str(f.parent.relative_to(out)).replace("\\", "/")
                                     if f.parent != out else "",
                        "size": st.st_size,
                        "mtime": int(st.st_mtime),
                        "kind": "video" if f.suffix.lower() in exts["video"] else "image",
                    })
            items.sort(key=lambda x: x["mtime"], reverse=True)
            return self._json({"output_dir": str(out), "count": len(items),
                               "items": items[:limit]})

        if self.path.startswith("/api/status"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            mode = (qs.get("mode") or ["video"])[0]
            if mode not in MODEL_SETS:
                mode = "video"
            models = []
            for m in models_for(mode):
                p = target_path(m)
                models.append({
                    "key": m["key"], "name": m["name"], "what": m["what"],
                    "size": m["size"], "have": have(m),
                    "partial": partial_bytes(m) > 0,
                    "dir": str(p.parent),
                })
            with LOCK:
                st = json.loads(json.dumps(STATE))
            ready = {k: all(have(x) for x in v) for k, v in MODEL_SETS.items()}
            return self._json({
                "comfy_root": str(COMFY_ROOT),
                "output_dir": str(Path(COMFY_ROOT) / "output"),
                "mode": mode,
                "models": models,
                "all_present": all(m["have"] for m in models),
                "missing_bytes": sum(m["size"] for m in models if not m["have"]),
                "ready": ready,
                "sizes": {k: sum(x["size"] for x in v) for k, v in MODEL_SETS.items()},
                "platform": PLATFORM,
                "download": st,
            })
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/delete"):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                return self._json({"ok": False, "error": "bad json"}, 400)
            out = (Path(COMFY_ROOT) / "output").resolve()
            removed, failed = [], []
            for name in body.get("files", [])[:200]:
                try:
                    # resolve and confirm it is really inside output/ - never
                    # let a crafted name escape the folder
                    t = (out / name).resolve()
                    if out not in t.parents and t.parent != out:
                        failed.append(name); continue
                    t.unlink()
                    removed.append(name)
                except Exception:
                    failed.append(name)
            return self._json({"ok": True, "removed": removed, "failed": failed})

        if self.path.startswith("/api/download"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            mode = (qs.get("mode") or ["video"])[0]
            if mode not in MODEL_SETS:
                mode = "video"
            with LOCK:
                if STATE["active"]:
                    return self._json({"ok": False, "reason": "already running"}, 409)
                STATE.update(active=True, error=None, done_keys=[],
                             files={}, started=time.time(), mode=mode)
            threading.Thread(target=download_all, args=(mode,), daemon=True).start()
            return self._json({"ok": True, "mode": mode})
        return self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    global COMFY_ROOT, UI_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy-root", required=True,
                    help=r'e.g. D:\ComfyUI\ComfyUI_windows_portable\ComfyUI')
    ap.add_argument("--ui-dir", default=str(Path(__file__).resolve().parent.parent / "ui"))
    ap.add_argument("--port", type=int, default=8189)
    args = ap.parse_args()

    COMFY_ROOT = Path(args.comfy_root)
    UI_DIR = Path(args.ui_dir)
    if not (COMFY_ROOT / "models").is_dir():
        raise SystemExit(f"No models folder under {COMFY_ROOT} - wrong --comfy-root?")
    if not (UI_DIR / "index.html").is_file():
        raise SystemExit(f"No index.html in {UI_DIR}")

    print(f"UI          : http://127.0.0.1:{args.port}")
    print(f"ComfyUI root: {COMFY_ROOT}")
    print(f"Clips saved : {COMFY_ROOT / 'output'}")
    for mode, ms in MODEL_SETS.items():
        ok = sum(1 for m in ms if have(m))
        tot_gb = sum(m["size"] for m in ms) / 1e9
        print(f"{mode:<12}: {ok}/{len(ms)} models present ({tot_gb:.1f} GB total)")
    with Server(("127.0.0.1", args.port), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
