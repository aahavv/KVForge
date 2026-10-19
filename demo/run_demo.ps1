# KVForge live demo (about 2 minutes on the RTX 5060 Laptop).
#
#   powershell -ExecutionPolicy Bypass -File demo\run_demo.ps1
#   powershell -ExecutionPolicy Bypass -File demo\run_demo.ps1 -Pause   # waits for Enter between steps
#
# One Llama-3-8B attention layer (32 query heads, 8 KV heads, d 128, 32k tokens),
# compiled three ways from three small .kv programs:
#   1 baseline  everything pinned by hand (the naive kernel)
#   2 lossless  layout and partition left as '?', fp16 only
#   3 budget    same plus "max_rel_err = 0.02", so int8 / int4 may be chosen
# For each: kvf plans it with the measured machine file and the frozen cost-model
# constants, writes CUDA, nvcc compiles it, and the driver checks the result
# against a double-precision reference and times it.
param([switch]$Pause, [string]$Arch = "120")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$kvf = Join-Path $root "build\kvf.exe"
$machine = "machines\rtx5060-laptop.gpu"
$calib = "model\constants_rtx5060.cal"

function Step($t) {
  Write-Host ""
  Write-Host ("=" * 78) -ForegroundColor Cyan
  Write-Host "  $t" -ForegroundColor Cyan
  Write-Host ("=" * 78) -ForegroundColor Cyan
  if ($Pause) { Read-Host "  (Enter to continue)" | Out-Null }
}

Step "0. The machine, as measured by bw_probe (no datasheet numbers)"
& $kvf machine $machine

$runs = @(
  @{ n = "1_baseline"; t = "1. Naive kernel: everything pinned by hand" },
  @{ n = "2_lossless"; t = "2. Compiler chooses layout + partition (fp16 only)" },
  @{ n = "3_budget";   t = "3. Compiler may also choose int8/int4, within 2% error" }
)
$res = @()
foreach ($r in $runs) {
  Step $r.t
  Write-Host "--- program demo\$($r.n).kv ---" -ForegroundColor Yellow
  Get-Content "demo\$($r.n).kv" | Write-Host
  $out = "out\demo\$($r.n)"
  New-Item -ItemType Directory -Force $out | Out-Null
  $rep = & $kvf plan "demo\$($r.n).kv" --machine $machine --calib $calib --out $out --top 5 | Out-String
  if ($LASTEXITCODE -ne 0) { throw "kvf plan failed" }
  # print the decision part of the report only; the full report is in $out\report.txt
  $show = ($rep -split "`n") | Where-Object { $_ -match "^(Search space|Candidates|  format:|  layout:|  partition:|  accuracy:|  T_total)" }
  Write-Host "--- compiler decision ---" -ForegroundColor Yellow
  $show | Write-Host
  Write-Host "--- generated CUDA: $out\$((Get-ChildItem "$out\decode_*.cu").Name) ; compiling and running ---" -ForegroundColor Yellow
  $run = & powershell -ExecutionPolicy Bypass -File tools\build_plan.ps1 -Dir $out -Arch $Arch | Out-String
  $run.Trim() | Write-Host
  $m = [regex]::Match($run, "time:\s+([\d.]+) us")
  $p = [regex]::Match($run, "predicted ([\d.]+) us")
  $pl = [regex]::Match($run, "plan:\s+(.+)")
  $acc = [regex]::Match($run, "accuracy: relative error vs exact fp32 attention ([\d.e-]+)")
  $res += [pscustomobject]@{
    step = $r.n; plan = $pl.Groups[1].Value.Trim()
    measured_us = [double]$m.Groups[1].Value; predicted_us = [double]$p.Groups[1].Value
    error = $(if ($acc.Success) { $acc.Groups[1].Value } else { "exact (fp16)" })
    verified = $(if ($run -match "PASS") { "PASS" } else { "FAIL" })
  }
}

Step "Summary: same layer, same GPU, three programs"
$base = $res[0].measured_us
$res | ForEach-Object { $_ | Add-Member speedup ("{0:N2}x" -f ($base / $_.measured_us)) }
$res | Format-Table step, plan, verified, error, predicted_us, measured_us, speedup -AutoSize | Out-String | Write-Host
Write-Host "Every number above was just measured on this GPU; the cost model's constants were"
Write-Host "fitted once and not changed (model\constants_rtx5060.cal). Reports: out\demo\*\report.txt"
