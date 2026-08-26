<#
  Downloads every model needed by workflows/wan21_1.3b_shorts_432x768.json
  Total: ~7.3 GB

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\download_models.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI_windows_portable\ComfyUI"
#>
param(
  [Parameter(Mandatory=$true)][string]$ComfyRoot
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ComfyRoot)) { throw "ComfyRoot not found: $ComfyRoot" }
if (-not (Test-Path (Join-Path $ComfyRoot "models"))) { throw "No models\ folder under $ComfyRoot - is this the inner ComfyUI folder?" }

$files = @(
  @{ Url  = "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors"
     Dir  = "models\diffusion_models"; Name = "wan2.1_t2v_1.3B_fp16.safetensors"; Size = "2.84 GB" },

  @{ Url  = "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"
     Dir  = "models\vae"; Name = "wan_2.1_vae.safetensors"; Size = "254 MB" },

  @{ Url  = "https://huggingface.co/city96/umt5-xxl-encoder-gguf/resolve/main/umt5-xxl-encoder-Q5_K_M.gguf"
     Dir  = "models\text_encoders"; Name = "umt5-xxl-encoder-Q5_K_M.gguf"; Size = "4.15 GB" },

  @{ Url  = "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/LoRAs/Wan2_1_self_forcing_1_3B/Wan2_1_self_forcing_dmd_1_3B_lora_rank_32_fp16.safetensors"
     Dir  = "models\loras"; Name = "Wan2_1_self_forcing_dmd_1_3B_lora_rank_32_fp16.safetensors"; Size = "91 MB" },

  @{ Url  = "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors"
     Dir  = "models\loras"; Name = "Wan21_CausVid_bidirect2_T2V_1_3B_lora_rank32.safetensors"; Size = "91 MB (alternate LoRA)" }
)

foreach ($f in $files) {
  $destDir = Join-Path $ComfyRoot $f.Dir
  if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }
  $dest = Join-Path $destDir $f.Name

  if (Test-Path $dest) {
    Write-Host "[skip] $($f.Name) already present" -ForegroundColor DarkGray
    continue
  }

  Write-Host "[get ] $($f.Name)  ($($f.Size))" -ForegroundColor Cyan
  # curl.exe ships with Windows 11 and resumes properly on flaky connections
  & curl.exe -L --fail --retry 5 --retry-delay 3 -C - -o "$dest" $f.Url
  if ($LASTEXITCODE -ne 0) { throw "Download failed: $($f.Name)" }
}

Write-Host ""
Write-Host "All models present under $ComfyRoot\models" -ForegroundColor Green
