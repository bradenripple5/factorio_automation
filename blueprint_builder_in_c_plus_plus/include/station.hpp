#pragma once

#include <cstddef>
#include <string>
#include <unordered_map>
#include <vector>

namespace factorio {

struct Station {
    std::string product;
    std::string id;
    unsigned trains_per_station{1};
    std::vector<std::size_t> parents;
    std::vector<std::size_t> children;
};

using IngredientMap = std::unordered_map<std::string, std::vector<std::string>>;

[[nodiscard]] std::vector<Station> build_station_tree(
    const std::vector<std::string>& products,
    const IngredientMap& ingredients = {},
    unsigned trains_per_station = 1
);

}  // namespace factorio
