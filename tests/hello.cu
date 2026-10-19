// Toolchain check: compile for the local GPU, run a kernel, read it back.
#include <cstdio>
#include <cuda_runtime.h>
__global__ void add(const int *a, int *b) { b[threadIdx.x] = a[threadIdx.x] + 1; }
int main() {
  cudaDeviceProp p;
  if (cudaGetDeviceProperties(&p, 0) != cudaSuccess) { std::puts("no CUDA device"); return 1; }
  std::printf("device: %s  cc %d.%d  SMs %d  mem %.1f GB  L2 %d KB\n", p.name, p.major, p.minor,
              p.multiProcessorCount, p.totalGlobalMem / 1e9, p.l2CacheSize / 1024);
  int h[32], *da, *db;
  for (int i = 0; i < 32; ++i) h[i] = i;
  cudaMalloc(&da, 128); cudaMalloc(&db, 128);
  cudaMemcpy(da, h, 128, cudaMemcpyHostToDevice);
  add<<<1, 32>>>(da, db);
  cudaMemcpy(h, db, 128, cudaMemcpyDeviceToHost);
  int bad = 0;
  for (int i = 0; i < 32; ++i) bad += h[i] != i + 1;
  std::printf("kernel result: %s\n", bad ? "WRONG" : "ok");
  return bad;
}
