#pragma once

#include "blueprint.hpp"

#include <cstddef>

namespace factorio {

struct SolarStats {
    std::size_t solar_panels{};
    std::size_t substations{};
    double peak_output_mw{};
};

[[nodiscard]] SolarStats solar_stats(int columns, int rows);
[[nodiscard]] Blueprint make_solar_array(int columns, int rows);

}  // namespace factorio
