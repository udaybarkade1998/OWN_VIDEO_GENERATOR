@echo off
REM ============================================================
REM  One-click: starts ComfyUI, waits for it, then opens the UI.
REM ============================================================
echo Starting ComfyUI...
start "ComfyUI" cmd /c "%~dp0run_comfyui.bat"

echo Waiting for ComfyUI to come up on port 8188...
set /a tries=0
:wait
set /a tries+=1
if %tries% gtr 120 (
  echo.
  echo [ERROR] ComfyUI did not start within 4 minutes.
  echo Check the ComfyUI window for errors.
  pause
  exit /b 1
)
powershell -NoProfile -Command "try{ (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',8188); exit 0 }catch{ exit 1 }" >nul 2>&1
if errorlevel 1 (
  timeout /t 2 /nobreak >nul
  goto wait
)

echo ComfyUI is up. Opening the UI...
timeout /t 2 /nobreak >nul
call "%~dp0run_ui.bat"
