# Build the CUDA side of KVForge: bw_probe, and the sweep harness with the
# dispatch table the compiler generates.
#
#   powershell -File tools\build_cuda.ps1 [-Targets probe,sweep] [-Dims 128]
#                                         [-Groups 1,4] [-Arch 89,120] [-Jobs 6]
#
# The default architectures build one fat binary that runs on both an Ada GPU
# (sm_89, e.g. RTX 4060) and a Blackwell GPU (sm_120, e.g. RTX 5060), so the same
# executable can be handed to a machine that has no CUDA toolkit installed.
param(
  [string[]]$Targets = @("probe", "sweep"),
  [string]$Dims = "128",
  [string]$Groups = "1,4",
  [string]$Arch = "89,120",
  [int]$Jobs = 6,
  [string]$OutDir = ""
)
$ErrorActionPreference = "Stop"
# `-File` passes "probe,sweep" as one string; split it.
$Targets = @($Targets | ForEach-Object { $_ -split "," })
$root = Split-Path -Parent $PSScriptRoot
$nvcc = Join-Path $root "tools\nvcc.cmd"
$out = if ($OutDir) { $OutDir } else { Join-Path $root "build\cuda" }
New-Item -ItemType Directory -Force -Path $out | Out-Null

$gencode = @()
foreach ($a in $Arch.Split(",")) { $gencode += "-gencode"; $gencode += "arch=compute_$a,code=sm_$a" }
$common = @("-O3", "-std=c++17", "-lineinfo") + $gencode

function Invoke-Nvcc([string[]]$NvccArgs) {
  & $nvcc @NvccArgs
  if ($LASTEXITCODE -ne 0) { throw "nvcc failed: $($NvccArgs -join ' ')" }
}

if ($Targets -contains "probe") {
  Write-Host "building bw_probe"
  Invoke-Nvcc ($common + @("-o", "$out\bw_probe.exe", "$root\bench\bw_probe.cu"))
}

if ($Targets -contains "sweep") {
  $kvf = Join-Path $root "build\kvf.exe"
  $gen = Join-Path $root "gen"
  & $kvf emit-dispatch --out $gen --d $Dims --g $Groups --quant | Out-Null
  $sources = Get-ChildItem "$gen\kvf_dispatch*.cu"
  $sources += Get-Item "$root\bench\sweep.cu"
  Write-Host "compiling $($sources.Count) translation units, $Jobs at a time"
  $running = @()
  $objs = @()
  foreach ($s in $sources) {
    $obj = Join-Path $out ($s.BaseName + ".obj")
    $objs += $obj
    $argList = @("-c") + $common + @("-I", "$root\runtime", "-o", $obj, $s.FullName)
    $p = Start-Process -FilePath $nvcc -ArgumentList $argList -NoNewWindow -PassThru
    $null = $p.Handle  # cache the handle so ExitCode is readable after exit
    $running += $p
    while (($running | Where-Object { -not $_.HasExited }).Count -ge $Jobs) { Start-Sleep -Milliseconds 500 }
  }
  $running | ForEach-Object { $_.WaitForExit() }
  $bad = $running | Where-Object { $_.ExitCode -ne 0 }
  if ($bad) { throw "$($bad.Count) translation unit(s) failed to compile" }
  Write-Host "linking sweep.exe"
  Invoke-Nvcc ($common + @("-o", "$out\sweep.exe") + $objs)
}
Write-Host "done: $out"
