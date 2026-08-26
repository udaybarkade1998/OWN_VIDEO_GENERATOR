@echo off
REM ============================================================
REM  Serves the OWN Video Generator UI at http://127.0.0.1:8189
REM  ComfyUI must already be running (scripts\run_comfyui.bat).
REM ============================================================

set "UIDIR=%~dp0..\ui"

REM Prefer ComfyUI's embedded Python so your system Python 3.14 is never involved.
set "COMFY_PORTABLE=D:\ComfyUI\ComfyUI_windows_portable"
set "PY=%COMFY_PORTABLE%\python_embeded\python.exe"
if not exist "%PY%" set "PY=python"

echo Serving UI from "%UIDIR%"
echo Open:  http://127.0.0.1:8189
echo.
start "" http://127.0.0.1:8189
"%PY%" -m http.server 8189 --bind 127.0.0.1 --directory "%UIDIR%"
