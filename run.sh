#!/usr/bin/env bash
# OWN Video Generator - launcher for macOS and Linux.
# Windows users: run  run.bat  (or  python run.py) instead.
set -e
cd "$(dirname "$0")"

PY=""
for c in python3.12 python3.11 python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "No Python found. Install Python 3.11 or 3.12."
  echo "  macOS:  brew install python@3.12"
  exit 1
fi

# PyTorch has no stable wheels for 3.14 yet and most custom nodes fail to build
V=$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')
case "$V" in
  3.10|3.11|3.12|3.13) ;;
  *) echo "[!] Python $V may be too new for PyTorch. 3.11 or 3.12 is safest." ;;
esac

exec "$PY" run.py "$@"
