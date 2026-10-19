# Build the package a second machine runs to produce ground truth for the
# transfer experiment.
#
#   powershell -File tools\make_friend_package.ps1 [-Arch 89] [-Name rtx4060]
#
# The package holds bw_probe (measures the GPU's machine file), sweep (times every
# plan of the shape suite), the plan lists, and one script that runs both. The
# target machine needs only an NVIDIA driver: the executables are built with the
# CUDA runtime linked in statically and with SASS for the requested architecture.
param(
  [string]$Arch = "89",
  [string]$Name = "rtx4060"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pkg = Join-Path $root "dist\kvforge_$Name"
$outDir = Join-Path $root "build\cuda_$Arch"
if (Test-Path $pkg) { Remove-Item -Recurse -Force $pkg }
New-Item -ItemType Directory -Force -Path "$pkg\plans" | Out-Null

& powershell -NoProfile -File "$root\tools\build_cuda.ps1" -Targets probe,sweep -Dims "128,64" -Groups "1,4,8" -Arch $Arch -OutDir $outDir
if ($LASTEXITCODE -ne 0) { throw "build failed" }

Copy-Item "$outDir\bw_probe.exe" $pkg
Copy-Item "$outDir\sweep.exe" $pkg
Get-ChildItem "$root\results\plans" -Directory | ForEach-Object {
  Copy-Item "$($_.FullName)\plans.csv" "$pkg\plans\$($_.Name).csv"
}

Set-Content -Path "$pkg\run.bat" -Encoding ascii -Value @"
@echo off
echo KVForge benchmark for a second GPU. This takes roughly 30 minutes.
echo Plug the computer in, close games and browsers, and do not use it meanwhile.
echo.
bw_probe.exe --name $Name --out machine_$Name.gpu
if errorlevel 1 goto fail
set PLANS=
for %%f in (plans\*.csv) do call set PLANS=%%PLANS%%,%%f
sweep.exe --plans %PLANS:~1% --out sweep_$Name.csv --reps 20 --warmup 3
if errorlevel 1 goto fail
echo.
echo Done. Send these two files back:
echo    machine_$Name.gpu
echo    sweep_$Name.csv
pause
exit /b 0
:fail
echo Something failed. Send a screenshot of this window.
pause
exit /b 1
"@

Set-Content -Path "$pkg\README.txt" -Encoding ascii -Value @"
KVForge second-GPU benchmark
============================
1. Plug the computer in (a laptop on battery throttles the GPU).
2. Close games, browsers and anything else that uses the GPU.
3. Double-click run.bat and leave it alone until it says Done (about 30 minutes).
4. Send back machine_$Name.gpu and sweep_$Name.csv.

Needs only an up-to-date NVIDIA driver. Nothing is installed and nothing is
changed on the computer. If Windows says an application control policy blocked
a file, tell us before changing any security setting.
"@

Compress-Archive -Path "$pkg\*" -DestinationPath "$pkg.zip" -Force
Write-Host "package: $pkg.zip"
