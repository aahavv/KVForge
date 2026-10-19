# Smoke tests for the kvf compiler (no GPU needed): every example must plan,
# machine files must load, and every malformed program must be rejected with a
# non-zero exit and the right message, rather than silently mis-planned.
#
#   powershell -File tests\smoke.ps1
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$kvf = Join-Path $root "build\kvf.exe"
$tmp = Join-Path $env:TEMP ("kvf_smoke_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
Set-Location $root
$script:pass = 0
$script:fail = 0

function Ok($name)  { Write-Host "  PASS  $name"; $script:pass++ }
function Bad($name, $why) { Write-Host "  FAIL  $name ($why)"; $script:fail++ }

function Expect-Ok($name, [string[]]$kvfArgs) {
  $o = & $kvf @kvfArgs 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0) { Ok $name } else { Bad $name ($o.Trim().Split("`n")[0]) }
}
function Expect-Err($name, $needle, [string[]]$kvfArgs) {
  $o = & $kvf @kvfArgs 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0) { Bad $name "expected failure, got success" }
  elseif ($o -match [regex]::Escape($needle)) { Ok $name }
  else { Bad $name "wrong message: $($o.Trim().Split("`n")[0])" }
}
function Spec($file, $body) { Set-Content -Path (Join-Path $tmp $file) -Value $body -Encoding ascii; return (Join-Path $tmp $file) }

Write-Host "examples plan:"
foreach ($f in Get-ChildItem "examples\*.kv") {
  Expect-Ok $f.Name @("plan", $f.FullName, "--out", (Join-Path $tmp $f.BaseName), "--top", "3")
}
Write-Host "machine files load:"
foreach ($f in Get-ChildItem "machines\*.gpu") { Expect-Ok $f.Name @("machine", $f.FullName) }
Write-Host "roofline:"
Expect-Ok "roofline" @("roofline", "examples\mha_4k.kv")

Write-Host "semantics:"
# The planner must honour a pinned splits value even when gqa_pack is free.
$o = & $kvf plan examples\paged_batch8.kv --out (Join-Path $tmp "pin") --top 400 2>&1 | Out-String
if ($o -match "splits=4" -and $o -notmatch "splits=1 " -and $o -notmatch "splits=8") { Ok "pinned splits honoured with gqa_pack free" }
else { Bad "pinned splits honoured with gqa_pack free" "other split counts appeared" }
# The accuracy gate must keep int4 out when the limit is tight.
$o = & $kvf plan examples\llama3_8b_gqa_32k.kv --out (Join-Path $tmp "gate") --max-err 0.02 --top 3 2>&1 | Out-String
if ($o -match "format:\s+int8" ) { Ok "accuracy limit 0.02 selects int8, not int4" } else { Bad "accuracy limit" "unexpected format" }
# With no limit and no --quant only the lossless format is searched.
$o = & $kvf plan examples\paged_batch8.kv --out (Join-Path $tmp "lossless") --top 3 2>&1 | Out-String
if ($o -match "lossy formats excluded") { Ok "lossy formats excluded without an accuracy budget" } else { Bad "lossless default" "lossy formats were searched" }

Write-Host "rejections:"
$hdr = 'target machine = "machines/generic-gpu.gpu"'
Expect-Err "H not a multiple of H_kv" "multiple of H_kv" @("plan", (Spec "a.kv" "$hdr`ndecode bad(H: 30, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, f16, token_major, contiguous> V: kvcache<n, d, f16, token_major, contiguous> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x1")
Expect-Err "typo in a target key" "unknown machine key" @("plan", (Spec "b.kv" "target bw_peek_gbs = 40`ndecode bad(H: 8, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, f16, token_major, contiguous> V: kvcache<n, d, f16, token_major, contiguous> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x2")
Expect-Err "unknown format name" "unknown KV format" @("plan", (Spec "c.kv" "$hdr`ndecode bad(H: 8, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, fp16, token_major, contiguous> V: kvcache<n, d, fp16, token_major, contiguous> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x3")
Expect-Err "cache shape must be <n, d>" "cache shape" @("plan", (Spec "d.kv" "$hdr`ndecode bad(H: 8, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, 64, f16, token_major, contiguous> V: kvcache<n, d, f16, token_major, contiguous> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x4")
Expect-Err "K and V must agree on what is free" "both pin a format" @("plan", (Spec "e.kv" "$hdr`ndecode bad(H: 8, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, f16, token_major, contiguous> V: kvcache<n, d, ?, ?, ?> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x5")
Expect-Err "undeclared cache" "not declared" @("plan", (Spec "f.kv" "$hdr`ndecode bad(H: 8, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, f16, token_major, contiguous> V: kvcache<n, d, f16, token_major, contiguous> O = decode_attn(Q, K, W) }"), "--out", "$tmp\x6")
Expect-Err "unsupported head dimension" "d = 64 or d = 128" @("plan", (Spec "g.kv" "$hdr`ndecode bad(H: 8, H_kv: 8, d: 96, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, f16, token_major, contiguous> V: kvcache<n, d, f16, token_major, contiguous> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x7")
Expect-Err "quantization group must divide d" "divide d" @("plan", (Spec "h.kv" "$hdr`ndecode bad(H: 8, H_kv: 8, d: 64, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, int8:128, token_major, contiguous> V: kvcache<n, d, int8:128, token_major, contiguous> O = decode_attn(Q, K, V) }"), "--out", "$tmp\x8")
Expect-Err "gqa_pack needs g in {2,4,8}" "gqa_pack = true needs" @("plan", (Spec "i.kv" "$hdr`ndecode bad(H: 24, H_kv: 8, d: 128, n: 1024) { Q: query<H, d, f32> K: kvcache<n, d, f16, token_major, contiguous> V: kvcache<n, d, f16, token_major, contiguous> O = decode_attn(Q, K, V, gqa_pack = true) }"), "--out", "$tmp\x9")

Write-Host ""
Write-Host "$script:pass passed, $script:fail failed"
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
if ($script:fail -gt 0) { exit 1 }
