#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace factorio {

struct Position {
    double x{};
    double y{};
};

struct Entity {
    std::uint32_t number{};
    std::string name;
    Position position;
    std::vector<std::uint32_t> neighbours;
};

struct Blueprint {
    std::string label;
    std::vector<Entity> entities;
    std::uint64_t version{562949955780608ULL};

    [[nodiscard]] std::string to_json() const;
};

std::string json_escape(const std::string& value);

}  // namespace factorio
