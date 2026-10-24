cmake_minimum_required(VERSION 3.15)
project(hd-seed-search)
set(CMAKE_CXX_STANDARD 20)

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 4)
    message(FATAL_ERROR "hd-seed-search must be built 32-bit: cmake -A Win32")
endif()

# Link the C++ runtime statically so it runs without the VC++ redistributable
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

add_compile_definitions(_CRT_SECURE_NO_WARNINGS WIN32_LEAN_AND_MEAN NOMINMAX)

# Only the struct layouts are used, so just the headers
set(HDDLL_INCLUDE ${CMAKE_CURRENT_SOURCE_DIR}/3rdparty/HDDLL/src)

add_executable(hd-seed-search src/launcher.cpp)

add_library(hd-seed-search-hook SHARED src/hook.cpp)
target_include_directories(hd-seed-search-hook PRIVATE ${HDDLL_INCLUDE})
