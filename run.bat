@echo off
REM OWN Video Generator - launcher for Windows.
REM macOS / Linux users: run  ./run.sh  instead.
cd /d "%~dp0"

REM Prefer ComfyUI's embedded Python when the portable build is present,
REM so the system Python version never matters.
set "PY=python"
if exist "D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe" (
  set "PY=D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe"
)
"%PY%" run.py %*
if errorlevel 1 pause
