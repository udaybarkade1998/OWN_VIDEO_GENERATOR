@echo off
REM Same as finish_short.bat but skips motion interpolation.
REM ~5 seconds instead of ~60, at the cost of choppier motion.
if "%~1"=="" ( echo Usage: finish_short_fast.bat "path\to\clip.webm" & pause & exit /b 1 )
ffmpeg -y -i "%~1" ^
  -vf "scale=1080:1920:flags=lanczos,unsharp=5:5:0.5:5:5:0.0,fps=32" ^
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart ^
  -an "%~dpn1_1080x1920_fast.mp4"
echo Done -^> "%~dpn1_1080x1920_fast.mp4"
pause
