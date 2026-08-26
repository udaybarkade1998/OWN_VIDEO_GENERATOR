#!/usr/bin/env bash
# Turns an SDXL image into a 1080x1920 YouTube Shorts still.
# Upscales to cover, then centre-crops. See finish_image.bat for why.
set -e
[ -z "$1" ] && { echo "Usage: ./finish_image.sh path/to/image.png"; exit 1; }
out="${1%.*}_1080x1920.png"
ffmpeg -y -i "$1" \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,unsharp=5:5:0.4:5:5:0.0" \
  "$out"
echo "Done -> $out"
