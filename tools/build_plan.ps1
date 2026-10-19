# Build and run the kernel the compiler generated for one spec.
#
#   kvf plan examples\llama3_8b_gqa_32k.kv --out out\llama3
#   powershell -File tools\build_plan.ps1 -Dir out\llama3 [-Arch 120] [-NoRun]
#
# Compiles the generated decode_<name>.cu together with the driver, which makes
# test data in the plan's format and layout, checks the kernel against a
# double-precision reference, times it, and prints measured against predicted.
param(
  [Parameter(Mandatory = $true)][string]$Dir,
  [string]$Arch = "89,120",
  [switch]$NoRun
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dirFull = (Resolve-Path $Dir).Path
$kernel = Get-ChildItem "$dirFull\decode_*.cu" | Select-Object -First 1
if (-not $kernel) { throw "no decode_*.cu in ${dirFull}; run kvf plan first" }
$gencode = @()
foreach ($a in $Arch.Split(",")) { $gencode += "-gencode"; $gencode += "arch=compute_$a,code=sm_$a" }
$exe = Join-Path $dirFull "bench.exe"
& "$root\tools\nvcc.cmd" -O3 -std=c++17 -lineinfo @gencode -I $dirFull -I "$root\runtime" `
  -o $exe "$root\runtime\kvf_driver.cu" $kernel.FullName 2>&1 | Where-Object { $_ -notmatch "vswhere|operable program|^kvf_driver.cu$|^decode_.*\.cu$" }
if ($LASTEXITCODE -ne 0) { throw "nvcc failed" }
Write-Host "built $exe"
if (-not $NoRun) { & $exe }
