#include "solar.hpp"

#include <algorithm>
#include <cmath>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

namespace factorio {
namespace {
constexpr int panel_size = 3;
constexpr int supply_diameter = 18;
constexpr double panel_output_kw = 60.0;

std::vector<int> axis_positions(const int length) {
    const int count = std::max(1, static_cast<int>(std::ceil(length / 18.0)));
    if (count == 1) return {static_cast<int>(std::floor(length / 2.0 + 0.5))};
    std::vector<int> result;
    const double first = supply_diameter / 2.0;
    const double last = length - supply_diameter / 2.0;
    for (int index = 0; index < count; ++index) {
        result.push_back(static_cast<int>(std::round(first + index * (last - first) / (count - 1))));
    }
    return result;
}

struct Layout {
    std::vector<std::pair<int, int>> poles;
    std::set<std::pair<int, int>> blocked;
};

Layout layout(const int columns, const int rows) {
    if (columns < 1 || rows < 1) throw std::invalid_argument("columns and rows must be positive");
    Layout result;
    const auto xs = axis_positions(columns * panel_size);
    const auto ys = axis_positions(rows * panel_size);
    for (const int y : ys) for (const int x : xs) result.poles.emplace_back(x, y);
    for (const auto& [x, y] : result.poles) {
        const int approximate_column = x / panel_size;
        const int approximate_row = y / panel_size;
        for (int row = std::max(0, approximate_row - 2); row < std::min(rows, approximate_row + 3); ++row) {
            for (int column = std::max(0, approximate_column - 2); column < std::min(columns, approximate_column + 3); ++column) {
                const double panel_x = column * panel_size + 1.5;
                const double panel_y = row * panel_size + 1.5;
                if (std::abs(panel_x - x) < 2.5 && std::abs(panel_y - y) < 2.5) {
                    result.blocked.emplace(column, row);
                }
            }
        }
    }
    return result;
}
}  // namespace

SolarStats solar_stats(const int columns, const int rows) {
    const auto value = layout(columns, rows);
    const auto panels = static_cast<std::size_t>(columns) * rows - value.blocked.size();
    return {panels, value.poles.size(), panels * panel_output_kw / 1000.0};
}

Blueprint make_solar_array(const int columns, const int rows) {
    const auto value = layout(columns, rows);
    const auto stats = solar_stats(columns, rows);
    Blueprint blueprint;
    blueprint.label = "Solar array " + std::to_string(columns) + "x" + std::to_string(rows)
        + " - " + std::to_string(stats.peak_output_mw) + " MW";
    blueprint.entities.reserve(stats.solar_panels + stats.substations);
    for (int row = 0; row < rows; ++row) {
        for (int column = 0; column < columns; ++column) {
            if (!value.blocked.contains({column, row})) {
                blueprint.entities.push_back({
                    static_cast<std::uint32_t>(blueprint.entities.size() + 1), "solar-panel",
                    {column * panel_size + 1.5, row * panel_size + 1.5}, {}
                });
            }
        }
    }
    const auto xs = axis_positions(columns * panel_size);
    const auto ys = axis_positions(rows * panel_size);
    const std::uint32_t first_pole = static_cast<std::uint32_t>(blueprint.entities.size() + 1);
    for (std::size_t row = 0; row < ys.size(); ++row) {
        for (std::size_t column = 0; column < xs.size(); ++column) {
            std::vector<std::uint32_t> neighbours;
            const auto number = first_pole + static_cast<std::uint32_t>(row * xs.size() + column);
            if (column > 0) neighbours.push_back(number - 1);
            if (column + 1 < xs.size()) neighbours.push_back(number + 1);
            if (row > 0) neighbours.push_back(number - static_cast<std::uint32_t>(xs.size()));
            if (row + 1 < ys.size()) neighbours.push_back(number + static_cast<std::uint32_t>(xs.size()));
            blueprint.entities.push_back({number, "substation", {static_cast<double>(xs[column]), static_cast<double>(ys[row])}, neighbours});
        }
    }
    return blueprint;
}

}  // namespace factorio
