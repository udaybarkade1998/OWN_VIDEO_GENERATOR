@echo off
REM ============================================================
REM  Turns a raw ComfyUI clip (432x768 @ 16fps) into a
REM  YouTube Shorts master: 1080x1920 @ 32fps H.264 MP4
REM
REM  Usage:  finish_short.bat "C:\path\to\short_00001.webm"
REM
REM  Runs entirely on the CPU - uses zero VRAM, so you can
REM  queue the next clip in ComfyUI while this encodes.
REM ============================================================

if "%~1"=="" (
  echo Usage: finish_short.bat "path\to\clip.webm"
  pause
  exit /b 1
)

set "IN=%~1"
set "OUT=%~dpn1_1080x1920.mp4"

REM Motion-interpolate FIRST at low res (cheap), THEN upscale (sharper result).
ffmpeg -y -i "%IN%" ^
  -vf "minterpolate=fps=32:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5:5:5:0.0" ^
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -movflags +faststart ^
  -an "%OUT%"

if errorlevel 1 (
  echo.
  echo [ERROR] ffmpeg failed. Is ffmpeg on your PATH?  winget install Gyan.FFmpeg
  pause
  exit /b 1
)

echo.
echo Done -^> "%OUT%"
pause
