#include "station.hpp"

#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace factorio {

std::vector<Station> build_station_tree(
    const std::vector<std::string>& products,
    const IngredientMap& ingredients,
    const unsigned trains_per_station
) {
    if (trains_per_station == 0) throw std::invalid_argument("trains per station must be positive");
    std::vector<Station> stations;
    stations.reserve(products.size());
    for (std::size_t index = 0; index < products.size(); ++index) {
        if (products[index].empty()) throw std::invalid_argument("station product cannot be empty");
        std::ostringstream id;
        id << products[index] << '-' << std::setw(3) << std::setfill('0') << index + 1;
        stations.push_back({products[index], id.str(), trains_per_station, {}, {}});
    }

    std::unordered_map<std::string, std::vector<std::size_t>> producers;
    for (std::size_t index = 0; index < stations.size(); ++index) {
        producers[stations[index].product].push_back(index);
    }
    std::unordered_map<std::string, std::size_t> next_producer;
    for (std::size_t consumer = 0; consumer < stations.size(); ++consumer) {
        const auto recipe = ingredients.find(stations[consumer].product);
        if (recipe == ingredients.end()) continue;
        for (const auto& ingredient : recipe->second) {
            const auto matches = producers.find(ingredient);
            if (matches == producers.end() || matches->second.empty()) continue;
            auto& cursor = next_producer[ingredient];
            const auto producer = matches->second[cursor++ % matches->second.size()];
            if (producer == consumer) continue;
            stations[producer].children.push_back(consumer);
            stations[consumer].parents.push_back(producer);
        }
    }
    return stations;
}

}  // namespace factorio
