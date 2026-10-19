import os
import flashinfer.jit.env as env

print("AOT providers:", env.FLASHINFER_AOT_PROVIDERS)
print("AOT dirs:", env.FLASHINFER_AOT_DIRS)
sp = os.path.expanduser("~/kvbench/lib/python3.12/site-packages/flashinfer_jit_cache/providers/sm120f")
print("provider dir exists:", os.path.exists(sp))
for root, dirs, files in os.walk(sp):
    depth = root[len(sp):].count(os.sep)
    if depth <= 2:
        print("  " * depth + os.path.basename(root) + "/", len(files), "files", [f for f in files[:3]])
    if depth >= 2:
        dirs[:] = []
dec = []
for root, dirs, files in os.walk(sp):
    for f in files:
        if "decode" in f.lower():
            dec.append(os.path.join(root, f)[len(sp):])
print("decode-related files:", len(dec))
for f in dec[:25]:
    print("  ", f)

import inspect
src = inspect.getsource(env)
i = src.find("AOT_PROVIDERS")
print(src[max(0, i - 600): i + 900])
