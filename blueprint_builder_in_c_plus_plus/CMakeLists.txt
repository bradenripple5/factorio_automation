cmake_minimum_required(VERSION 3.20)
project(factorio_blueprint_builder LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(MINGW AND EXISTS "C:/msys64/ucrt64/include/zlib.h")
    set(ZLIB_INCLUDE_DIR "C:/msys64/ucrt64/include")
    set(ZLIB_LIBRARY "C:/msys64/ucrt64/lib/libz.a")
endif()
find_package(ZLIB REQUIRED)

add_executable(blueprint_builder
    src/main.cpp
    src/blueprint.cpp
    src/codec.cpp
    src/solar.cpp
    src/station.cpp
)
target_include_directories(blueprint_builder PRIVATE include)
target_link_libraries(blueprint_builder PRIVATE ZLIB::ZLIB)

if(MSVC)
    target_compile_options(blueprint_builder PRIVATE /W4 /permissive-)
else()
    target_compile_options(blueprint_builder PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME solar_20x10 COMMAND blueprint_builder solar 20 10 --no-clipboard)
add_test(NAME station_defaults COMMAND blueprint_builder station-plan advanced-circuit copper-cable)
