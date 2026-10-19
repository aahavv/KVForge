import importlib
import os
import subprocess
import sys

print("python", sys.version.split()[0])
for name in ("flashinfer", "flashinfer_jit_cache"):
    try:
        m = importlib.import_module(name)
        print(name, getattr(m, "__version__", "?"), os.path.dirname(m.__file__))
    except Exception as e:
        print(name, "NOT importable:", str(e)[:100])

try:
    import flashinfer.jit.env as env
    for attr in dir(env):
        if "AOT" in attr or "CUDA" in attr or "WORKSPACE" in attr:
            print("env.%s = %s" % (attr, getattr(env, attr)))
except Exception as e:
    print("env error", str(e)[:120])

try:
    import flashinfer_jit_cache as jc
    base = os.path.dirname(jc.__file__)
    for root, dirs, files in os.walk(base):
        depth = root[len(base):].count(os.sep)
        if depth <= 2:
            print("  " * depth + os.path.basename(root) + "/", len(files), "files")
        if depth > 2:
            dirs[:] = []
except Exception as e:
    print("jit cache walk:", str(e)[:100])

out = subprocess.run(["bash", "-c", "ls ~/kvbench/lib/python3.12/site-packages | grep -i -E 'flashinfer|nvidia' | head -30; gcc --version | head -1; which nvcc || echo 'no nvcc'"], capture_output=True, text=True)
print(out.stdout)
