# Try KVForge on any model: asks for the model's attention numbers, writes the
# .kv program, compiles it, builds the generated kernel, checks it and times it,
# and compares with the naive kernel for the same model.
#
#   powershell -ExecutionPolicy Bypass -File demo\try_model.ps1                 # asks questions
#   powershell -ExecutionPolicy Bypass -File demo\try_model.ps1 -Model qwen2.5-7b -N 8192 -Batch 4
#   powershell -ExecutionPolicy Bypass -File demo\try_model.ps1 -H 32 -Hkv 8 -D 128 -N 32768 -Batch 1 -MaxErr 0.02
#
# H      query heads per layer          (from the model's config: num_attention_heads)
# Hkv    key/value heads per layer      (num_key_value_heads)
# D      numbers per head               (head_dim = hidden_size / num_attention_heads)
# N      context length: tokens already in the cache
# Batch  how many conversations are decoded together
# MaxErr accuracy budget; 0 = lossless fp16 only, 0.02 lets int8 in, 0.2 lets int4 in
param(
  [string]$Model = "", [int]$H = 0, [int]$Hkv = 0, [int]$D = 0,
  [int]$N = 0, [int]$Batch = 0, [double]$MaxErr = -1,
  [switch]$NoBaseline, [string]$Arch = "120",
  [string]$Machine = "machines\rtx5060-laptop.gpu"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$kvf = Join-Path $root "build\kvf.exe"
$calib = "model\constants_rtx5060.cal"

# Attention shapes of some public models (from their published config files).
$presets = [ordered]@{
  "llama3-8b"   = @(32, 8, 128);  "llama3-70b"  = @(64, 8, 128)
  "mistral-7b"  = @(32, 8, 128);  "llama2-7b"   = @(32, 32, 128)
  "qwen2.5-7b"  = @(28, 4, 128);  "llama3.2-1b" = @(32, 8, 64)
  "tinyllama"   = @(32, 4, 64)
}
function Ask($q, $def) { $a = Read-Host "$q [$def]"; if ($a -eq "") { $def } else { $a } }

$interactive = ($Model -eq "" -and $H -eq 0)
if ($interactive) {
  Write-Host "Models with known shapes: $($presets.Keys -join ', ')"
  Write-Host "or type 'custom' to enter the numbers yourself."
  $Model = Ask "Model" "llama3-8b"
}
if ($Model -ne "" -and $Model -ne "custom") {
  if (-not $presets.Contains($Model)) { throw "unknown model '$Model'; known: $($presets.Keys -join ', ')" }
  $H, $Hkv, $D = $presets[$Model]
} elseif ($H -eq 0) {
  $H = [int](Ask "Query heads H" 32); $Hkv = [int](Ask "Key/value heads H_kv" 8); $D = [int](Ask "Head size d (64 or 128)" 128)
}
if ($N -eq 0) { $N = if ($interactive) { [int](Ask "Context length n (tokens)" 32768) } else { 32768 } }
if ($Batch -eq 0) { $Batch = if ($interactive) { [int](Ask "Batch (conversations at once)" 1) } else { 1 } }
if ($MaxErr -lt 0) { $MaxErr = if ($interactive) { [double](Ask "Accuracy budget (0 = lossless, 0.02 = allow int8, 0.2 = allow int4)" 0.02) } else { 0.02 } }

# fp16 cache of one layer: K and V, H_kv heads, d numbers, 2 bytes each
$mb = 2.0 * $Hkv * $D * $N * $Batch * 2 / 1MB
Write-Host ""
Write-Host ("One attention layer: H={0} H_kv={1} d={2} n={3} batch={4}  ->  KV cache {5:N0} MB per layer in fp16" -f $H, $Hkv, $D, $N, $Batch, $mb) -ForegroundColor Cyan
if ($mb -gt 2048) { throw "that cache does not fit comfortably in this GPU's 8 GB with the test data; lower n or batch" }

$tag = ("H{0}_{1}_d{2}_n{3}_b{4}" -f $H, $Hkv, $D, $N, $Batch)
$dir = "out\try\$tag"
New-Item -ItemType Directory -Force "$dir\pick", "$dir\naive" | Out-Null
$budget = if ($MaxErr -gt 0) { "target max_rel_err = $MaxErr`n" } else { "" }
$pick = @"
# written by demo\try_model.ps1
$budget
decode model(H: $H, H_kv: $Hkv, d: $D, n: $N, batch: $Batch) {
  Q: query<H, d, f32>
  K: kvcache<n, d, ?, ?, ?>
  V: kvcache<n, d, ?, ?, ?>
  O = decode_attn(Q, K, V, scale = auto, splits = ?, gqa_pack = ?)
}
"@
$naive = @"
# written by demo\try_model.ps1: the naive kernel, everything pinned
decode model(H: $H, H_kv: $Hkv, d: $D, n: $N, batch: $Batch) {
  Q: query<H, d, f32>
  K: kvcache<n, d, f16, token_major, contiguous>
  V: kvcache<n, d, f16, token_major, contiguous>
  O = decode_attn(Q, K, V, scale = auto, splits = 1, gqa_pack = false)
}
"@
Set-Content -Encoding ascii "$dir\pick\model.kv" $pick
Set-Content -Encoding ascii "$dir\naive\model.kv" $naive
Write-Host "--- the program the compiler gets ($dir\pick\model.kv) ---" -ForegroundColor Yellow
Write-Host $pick

function Run($sub, $label) {
  $rep = & $kvf plan "$dir\$sub\model.kv" --machine $Machine --calib $calib --out "$dir\$sub" --top 5 | Out-String
  if ($LASTEXITCODE -ne 0) { throw "kvf plan failed" }
  Write-Host "--- $label : compiler decision ---" -ForegroundColor Yellow
  ($rep -split "`n") | Where-Object { $_ -match "^(Candidates|  format:|  layout:|  partition:|  accuracy:|  T_total)" } | Write-Host
  Write-Host "--- building, checking and timing the generated kernel ---" -ForegroundColor Yellow
  $run = & powershell -ExecutionPolicy Bypass -File tools\build_plan.ps1 -Dir "$dir\$sub" -Arch $Arch | Out-String
  $run.Trim() | Write-Host
  return [double]([regex]::Match($run, "time:\s+([\d.]+) us").Groups[1].Value)
}
$t = Run "pick" "KVForge"
if (-not $NoBaseline) {
  $t0 = Run "naive" "naive kernel (for comparison)"
  Write-Host ""
  Write-Host ("RESULT: naive {0:N1} us, KVForge {1:N1} us  ->  {2:N2}x faster" -f $t0, $t, ($t0 / $t)) -ForegroundColor Green
}
Write-Host "Full reasoning: $dir\pick\report.txt"
