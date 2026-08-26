@echo off
REM Kept for convenience - the real launcher is run.bat / run.py at the repo root,
REM which works on Windows, macOS and Linux and tunes itself to your hardware.
call "%~dp0..\run.bat" %*
