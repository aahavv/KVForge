cmake_minimum_required(VERSION 3.20)
project(KVForge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# The compiler itself is plain C++20. The CUDA side (bench/, runtime/) is built
# by tools/build_cuda.ps1 with nvcc, because nvcc on Windows needs MSVC and the
# compiler does not.
add_library(kvf_core STATIC
  src/lexer.cpp
  src/parser.cpp
  src/ir.cpp
  src/machine.cpp
  src/calib.cpp
  src/format.cpp
  src/layout.cpp
  src/plan.cpp
  src/cost.cpp
  src/passes.cpp
  src/codegen.cpp
  src/emit.cpp
  src/fit.cpp
)
target_include_directories(kvf_core PUBLIC include)

add_executable(kvf src/main.cpp)
target_link_libraries(kvf PRIVATE kvf_core)

if(MSVC)
  target_compile_options(kvf_core PRIVATE /W4)
else()
  target_compile_options(kvf_core PRIVATE -Wall -Wextra -Wpedantic)
endif()
