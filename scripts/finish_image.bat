@echo off
REM ============================================================
REM  Turns an SDXL image (832x1216 or similar) into a
REM  1080x1920 YouTube Shorts still.
REM
REM  Usage:  finish_image.bat "C:\path\to\image_00001_.png"
REM
REM  Upscales to cover 1080x1920, then centre-crops. SDXL is not
REM  trained at 9:16, so generating there shrinks or duplicates the
REM  subject - generate at a native ratio and crop here instead.
REM ============================================================
if "%~1"=="" ( echo Usage: finish_image.bat "path\to\image.png" & pause & exit /b 1 )
ffmpeg -y -i "%~1" ^
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,unsharp=5:5:0.4:5:5:0.0" ^
  "%~dpn1_1080x1920.png"
if errorlevel 1 ( echo [ERROR] ffmpeg failed. Is ffmpeg on PATH?  winget install Gyan.FFmpeg & pause & exit /b 1 )
echo Done -^> "%~dpn1_1080x1920.png"
pause
