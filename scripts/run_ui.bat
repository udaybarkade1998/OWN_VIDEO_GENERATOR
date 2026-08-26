@echo off
REM ============================================================
REM  Serves the OWN Video Generator UI at http://127.0.0.1:8189
REM  Also provides the model-download API the setup screen uses.
REM  ComfyUI must be running (scripts\run_comfyui.bat).
REM ============================================================

set "COMFY_PORTABLE=D:\ComfyUI\ComfyUI_windows_portable"
set "PY=%COMFY_PORTABLE%\python_embeded\python.exe"
if not exist "%PY%" set "PY=python"

echo Opening http://127.0.0.1:8189
start "" http://127.0.0.1:8189
"%PY%" "%~dp0ovg_server.py" --comfy-root "%COMFY_PORTABLE%\ComfyUI" --port 8189
pause
