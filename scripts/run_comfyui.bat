@echo off
REM ============================================================
REM  ComfyUI launcher tuned for: GTX 1650 4GB / i5-8600K / 32GB
REM  Opens in your browser at http://127.0.0.1:8188
REM ============================================================

REM ---- EDIT THIS to your portable folder (the one containing run_nvidia_gpu.bat)
set "COMFY_PORTABLE=D:\ComfyUI\ComfyUI_windows_portable"

REM ---- How much VRAM to leave for Windows + the browser tab running the UI.
REM      Measure your real idle usage with the apps you keep open:
REM         nvidia-smi --query-gpu=memory.used --format=csv
REM      then set RESERVE to that value in GB, plus ~0.3 headroom.
REM      0.8  = lean desktop, Chrome hardware acceleration OFF
REM      1.2  = a few apps open  (starting point for this PC)
REM      1.8  = heavy: Chrome with HW accel, VS Code, overlays all running
set "RESERVE=1.2"

cd /d "%COMFY_PORTABLE%"
if not exist "python_embeded\python.exe" (
  echo [ERROR] Not found: %COMFY_PORTABLE%\python_embeded\python.exe
  echo Edit COMFY_PORTABLE at the top of this file.
  pause
  exit /b 1
)

REM Keeps allocator fragmentation from causing false OOM on a 4GB card
set "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"

python_embeded\python.exe -s ComfyUI\main.py ^
  --lowvram ^
  --reserve-vram %RESERVE% ^
  --use-pytorch-cross-attention ^
  --disable-smart-memory ^
  --fp16-vae ^
  --preview-method none ^
  --enable-cors-header "*" ^
  --listen 127.0.0.1

pause
