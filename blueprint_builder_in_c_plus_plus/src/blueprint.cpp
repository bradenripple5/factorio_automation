#include "blueprint.hpp"

#include <cmath>
#include <iomanip>
#include <sstream>

namespace factorio {

std::string json_escape(const std::string& value) {
    std::ostringstream output;
    for (const unsigned char character : value) {
        switch (character) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (character < 0x20) {
                    output << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                           << static_cast<int>(character) << std::dec;
                } else {
                    output << character;
                }
        }
    }
    return output.str();
}

namespace {
void write_number(std::ostringstream& output, const double value) {
    if (std::floor(value) == value) {
        output << static_cast<long long>(value);
    } else {
        output << std::setprecision(12) << value;
    }
}
}  // namespace

std::string Blueprint::to_json() const {
    std::ostringstream output;
    output << "{\"blueprint\":{\"item\":\"blueprint\",\"label\":\""
           << json_escape(label) << "\",\"version\":" << version
           << ",\"icons\":["
           << "{\"signal\":{\"type\":\"item\",\"name\":\"solar-panel\"},\"index\":1},"
           << "{\"signal\":{\"type\":\"item\",\"name\":\"substation\"},\"index\":2}],"
           << "\"entities\":[";
    for (std::size_t index = 0; index < entities.size(); ++index) {
        if (index != 0) output << ',';
        const auto& entity = entities[index];
        output << "{\"entity_number\":" << entity.number << ",\"name\":\""
               << json_escape(entity.name) << "\",\"position\":{\"x\":";
        write_number(output, entity.position.x);
        output << ",\"y\":";
        write_number(output, entity.position.y);
        output << '}';
        if (!entity.neighbours.empty()) {
            output << ",\"neighbours\":[";
            for (std::size_t neighbour = 0; neighbour < entity.neighbours.size(); ++neighbour) {
                if (neighbour != 0) output << ',';
                output << entity.neighbours[neighbour];
            }
            output << ']';
        }
        output << '}';
    }
    output << "]}}";
    return output.str();
}

}  // namespace factorio
