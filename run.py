#!/usr/bin/env python3
"""
OWN Video Generator - cross-platform launcher (Windows / macOS / Linux).

Starts ComfyUI with settings tuned for the machine it finds itself on,
starts the helper server that the UI uses to download models, and opens
the browser.

    python run.py                       first run asks where ComfyUI is
    python run.py --comfy-root PATH     set it explicitly (remembered)
    python run.py --no-browser          don't open a tab
    python run.py --reserve 1.2         override VRAM left free (NVIDIA)

The chosen paths are remembered in ovg_config.json next to this file.
"""

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "ovg_config.json"
COMFY_PORT = 8188
UI_PORT = 8189

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"


# ------------------------------------------------------------------ config

def load_config():
    if CONFIG.is_file():
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def guess_comfy_roots():
    """Common install locations, most likely first."""
    home = Path.home()
    cands = []
    if IS_WIN:
        for drive in ("D:", "C:", "E:"):
            cands += [
                Path(f"{drive}/ComfyUI/ComfyUI_windows_portable/ComfyUI"),
                Path(f"{drive}/ComfyUI_windows_portable/ComfyUI"),
                Path(f"{drive}/ComfyUI"),
            ]
    cands += [
        home / "ComfyUI",
        home / "Documents/ComfyUI",
        home / "Developer/ComfyUI",
        HERE.parent / "ComfyUI",
    ]
    return [c for c in cands if (c / "main.py").is_file() and (c / "models").is_dir()]


def find_comfy_python(root: Path):
    """The interpreter that can import torch for this ComfyUI install."""
    # Windows portable ships an embedded Python next to the ComfyUI folder
    emb = root.parent / "python_embeded" / ("python.exe" if IS_WIN else "python")
    if emb.is_file():
        return str(emb)
    # a venv inside the ComfyUI folder
    for sub in ("venv", ".venv"):
        v = root / sub / ("Scripts/python.exe" if IS_WIN else "bin/python")
        if v.is_file():
            return str(v)
    return sys.executable


# ------------------------------------------------------------------ tuning

def gpu_profile(py):
    """Ask the target interpreter what hardware it has."""
    probe = (
        "import json,sys\n"
        "out={'torch':None,'backend':'cpu','name':'','vram_gb':0.0,'sm':''}\n"
        "try:\n"
        "    import torch\n"
        "    out['torch']=torch.__version__\n"
        "    if torch.cuda.is_available():\n"
        "        out['backend']='cuda'\n"
        "        out['name']=torch.cuda.get_device_name(0)\n"
        "        out['vram_gb']=round(torch.cuda.get_device_properties(0).total_memory/1e9,2)\n"
        "        c=torch.cuda.get_device_capability(0); out['sm']='sm_%d%d'%c\n"
        "    elif getattr(torch.backends,'mps',None) and torch.backends.mps.is_available():\n"
        "        out['backend']='mps'; out['name']='Apple Silicon (MPS)'\n"
        "except Exception as e:\n"
        "    out['error']=str(e)\n"
        "print(json.dumps(out))\n"
    )
    try:
        r = subprocess.run([py, "-c", probe], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"torch": None, "backend": "cpu", "name": "", "vram_gb": 0.0, "sm": ""}


def build_args(prof, reserve):
    """
    Arguments tuned per backend.

    --fp32-vae is non-negotiable everywhere: Wan's VAE decodes causally in
    time, and in fp16 the chain overflows after frame 1, leaving every later
    frame a flat constant while ComfyUI still reports success.
    """
    args = ["--use-pytorch-cross-attention", "--fp32-vae",
            "--preview-method", "none", "--enable-cors-header", "*",
            "--listen", "127.0.0.1", "--port", str(COMFY_PORT)]
    env = dict(os.environ)

    if prof["backend"] == "cuda":
        vram = prof.get("vram_gb", 0)
        if vram <= 6:
            args = ["--lowvram", "--disable-smart-memory",
                    "--reserve-vram", str(reserve)] + args
        elif vram <= 10:
            args = ["--normalvram", "--reserve-vram", str(reserve)] + args
        env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    elif prof["backend"] == "mps":
        # Apple Silicon shares one memory pool, so there is no separate VRAM
        # budget to reserve. Some ops still have no MPS kernel; the fallback
        # keeps those on the CPU instead of crashing the run.
        env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        try:
            import psutil                                  # optional
            gb = psutil.virtual_memory().total / 1e9
        except Exception:
            gb = 16
        if gb < 24:
            args = ["--lowvram"] + args

    else:
        args = ["--cpu"] + args

    return args, env


# ------------------------------------------------------------------ helpers

def port_open(port, host="127.0.0.1"):
    with socket.socket() as s:
        s.settimeout(0.6)
        return s.connect_ex((host, port)) == 0


def wait_for(port, timeout=600, what="service"):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if port_open(port):
            return True
        time.sleep(1.5)
        if int(time.time() - t0) % 30 == 0:
            print(f"   still waiting for {what} ({int(time.time()-t0)}s)…")
    return False


def prompt_for_root():
    print("\nWhere is ComfyUI installed?")
    print("  (the folder containing main.py and models/)")
    if not IS_WIN:
        print("  Don't have it yet? Install with:")
        print("    git clone https://github.com/comfyanonymous/ComfyUI")
        print("    cd ComfyUI && python -m venv venv && source venv/bin/activate")
        print("    pip install -r requirements.txt")
        if IS_MAC:
            print("    # PyTorch on Apple Silicon already includes MPS support")
    raw = input("\nPath: ").strip().strip('"').strip("'")
    return Path(raw).expanduser() if raw else None


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy-root")
    ap.add_argument("--reserve", type=float)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--comfy-only", action="store_true")
    args = ap.parse_args()

    cfg = load_config()

    # ---- locate ComfyUI
    root = None
    if args.comfy_root:
        root = Path(args.comfy_root).expanduser()
    elif cfg.get("comfy_root"):
        root = Path(cfg["comfy_root"])
    if root is None or not (root / "main.py").is_file():
        found = guess_comfy_roots()
        if found:
            root = found[0]
            print(f"Found ComfyUI at {root}")
        else:
            root = prompt_for_root()
    if root is None or not (root / "main.py").is_file():
        sys.exit(f"ComfyUI not found. Pass --comfy-root /path/to/ComfyUI")
    if not (root / "models").is_dir():
        sys.exit(f"{root} has no models/ folder - is that really the ComfyUI folder?")

    cfg["comfy_root"] = str(root)
    save_config(cfg)

    py = find_comfy_python(root)
    print(f"ComfyUI     : {root}")
    print(f"Python      : {py}")

    # ---- hardware
    prof = gpu_profile(py)
    if not prof.get("torch"):
        print("\n[!] That interpreter cannot import torch.")
        print("    Install ComfyUI's requirements into it first:")
        print(f"      {py} -m pip install -r {root / 'requirements.txt'}")
        sys.exit(1)
    label = prof["name"] or prof["backend"]
    extra = f", {prof['vram_gb']} GB, {prof['sm']}" if prof["backend"] == "cuda" else ""
    print(f"Hardware    : {label}{extra}  (torch {prof['torch']})")

    if prof["backend"] == "cuda" and prof.get("sm") in ("sm_50", "sm_60", "sm_61", "sm_70"):
        print("[!] This GPU is older than Turing; recent CUDA builds dropped it.")

    reserve = args.reserve if args.reserve is not None else cfg.get("reserve", 0.8)

    # ---- custom node the workflows need
    if not (root / "custom_nodes" / "ComfyUI-GGUF").is_dir():
        print("\n[!] ComfyUI-GGUF is missing - the video workflow needs it for the")
        print("    quantized text encoder. Install it with:")
        print(f"      cd {root / 'custom_nodes'}")
        print("      git clone https://github.com/city96/ComfyUI-GGUF.git")
        print(f"      {py} -m pip install -r ComfyUI-GGUF/requirements.txt")

    # ---- start ComfyUI
    procs = []
    if port_open(COMFY_PORT):
        print(f"ComfyUI     : already running on :{COMFY_PORT}")
    else:
        cargs, env = build_args(prof, reserve)
        print(f"Launching   : main.py {' '.join(cargs)}")
        procs.append(subprocess.Popen([py, "-s", str(root / "main.py")] + cargs,
                                      cwd=str(root), env=env))
        print(f"Waiting for ComfyUI on :{COMFY_PORT} (first start loads slowly)…")
        if not wait_for(COMFY_PORT, 900, "ComfyUI"):
            for p in procs:
                p.terminate()
            sys.exit("ComfyUI did not start. Check its output above.")
        print("ComfyUI     : up")

    if args.comfy_only:
        procs[0].wait() if procs else None
        return

    # ---- start the helper + UI
    if port_open(UI_PORT):
        print(f"UI          : already running on :{UI_PORT}")
    else:
        procs.append(subprocess.Popen(
            [sys.executable, str(HERE / "scripts" / "ovg_server.py"),
             "--comfy-root", str(root), "--port", str(UI_PORT)]))
        wait_for(UI_PORT, 60, "UI server")

    url = f"http://127.0.0.1:{UI_PORT}"
    print(f"\n  Open {url}\n")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    print("Ctrl+C to stop everything.")
    try:
        while True:
            time.sleep(1)
            for p in procs:
                if p.poll() is not None:
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("\nStopping…")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
