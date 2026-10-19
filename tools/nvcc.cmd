@echo off
rem nvcc on Windows needs MSVC's cl.exe on PATH. This wrapper loads the MSVC x64
rem environment for the Visual Studio Build Tools install, then forwards to nvcc.
set "PATH=%PATH%;C:\Program Files (x86)\Microsoft Visual Studio\Installer"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 exit /b 1
"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.4\bin\nvcc.exe" %*
