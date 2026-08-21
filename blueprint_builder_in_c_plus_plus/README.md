# Blueprint Builder in C++

Native, dependency-light port of the performance-sensitive blueprint-building core.
The Python application remains unchanged.

Implemented now:

- `Station` value type with stable IDs, train count, and graph relationships.
- Fully powered standalone solar arrays.
- Deterministic entity numbering and substation wiring.
- Factorio JSON, zlib compression, Base64 blueprint strings, and Windows clipboard output.
- CMake tests.

The production-station template transformer is the next parity layer. It needs a
native JSON parser before the large saved station templates can be transformed
without calling Python.

## Build

From an MSYS2 UCRT64 terminal:

```sh
cmake -S . -B build -G "MinGW Makefiles"
cmake --build build
ctest --test-dir build --output-on-failure
```

From PowerShell, make sure `C:\msys64\ucrt64\bin` is on `PATH`, then run the
same commands from this directory.

## Use

```sh
build/blueprint_builder.exe solar 20 10
build/blueprint_builder.exe solar 20 10 --json
build/blueprint_builder.exe station-plan advanced-circuit copper-cable --trains 1
```
