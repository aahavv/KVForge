"""Extract per-kernel register and shared-memory usage from a compiled binary.

    python tools/dump_resources.py build/cuda/sweep.exe machines/resources_sm120.csv

The compiler's cost model needs to know how many thread blocks fit on one SM, and
that depends on the registers each generated kernel uses. nvcc knows this after
compilation; this script reads it back with cuobjdump, so the table is static
build information, not a measurement.
"""
import csv
import re
import subprocess
import sys

CUOBJDUMP = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.4\bin\cuobjdump.exe"
# kvf::decode_partial<FMT, D, G, U, ORD, PAGED, FINAL>
PAT = re.compile(r"decode_partial(?:ILi(\d+)E)(?:ILi)?")


def main(exe, out):
    text = subprocess.run([CUOBJDUMP, "--dump-resource-usage", exe], capture_output=True, text=True, check=True).stdout
    rows = {}
    name = None
    for line in text.splitlines():
        m = re.search(r"Function (_ZN3kvf14decode_partialILi(\d+)ELi(\d+)ELi(\d+)ELi(\d+)ELi(\d+)ELb(\d)ELb(\d)E)", line)
        if m:
            name = tuple(int(x) for x in m.groups()[1:])
            continue
        if name and "REG:" in line:
            reg = int(re.search(r"REG:(\d+)", line).group(1))
            smem = int(re.search(r"SHARED:(\d+)", line).group(1))
            rows[name] = (reg, smem)
            name = None
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fmt", "d", "g", "u", "ord", "paged", "final", "regs", "smem"])
        for k in sorted(rows):
            w.writerow(list(k) + list(rows[k]))
    print("wrote %s (%d kernels, regs %d..%d)" % (out, len(rows), min(r for r, _ in rows.values()), max(r for r, _ in rows.values())))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
